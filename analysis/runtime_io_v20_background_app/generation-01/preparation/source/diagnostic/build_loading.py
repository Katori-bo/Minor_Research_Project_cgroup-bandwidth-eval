#!/usr/bin/env python3
"""V17: retain both V16 images; prepare one common executable and startup probe."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

import build_repeatability as baseline
import build_parallelism as stock
import loading_analysis as analysis
import loading_identity as identity
import run

DEFAULT = run.ROOT / 'analysis/runtime_io_v17_loading_build'
COMPILER = stock.COMPILER
ARMS = analysis.ARMS


def dependencies():
    return sorted(set(baseline.dependencies() + [Path(__file__), run.HERE / 'loading_analysis.py',
        run.HERE / 'loading_identity.py'] + list((run.HERE / 'loading_probe').glob('*'))))


def bundle_hashes(directory):
    return {str(p.relative_to(directory)): run.sha(p) for p in sorted(directory.rglob('*'))
        if p.is_file() and p != directory / 'verification.json'}


def verify(directory=DEFAULT):
    value = run.read(directory / 'build.json')
    if value['sources'] != run.hashes(dependencies()): raise ValueError('loading source changed')
    if value['prepared_sha256'] != stock.prepared_hashes(directory / 'prepared'):
        raise ValueError('prepared source changed')
    if run.sha(directory / 'loadgen') != value['loadgen_sha256'] or value['compiler_image_id'] != COMPILER:
        raise ValueError('client/compiler changed')
    assets = directory / 'runtime_assets'
    if run.sha(assets / 'shared.server') != value['server_sha256'] or run.sha(assets / 'probe') != value['probe_sha256']:
        raise ValueError('runtime asset changed')
    if any(not p.stat().st_mode & 0o111 for p in (assets / 'shared.server', assets / 'probe')):
        raise ValueError('runtime asset not executable')
    images = value['images']
    if set(images) != set(ARMS) or images['legacy_packaged'] != images['legacy_shared'] or images['rebuilt_packaged'] != images['rebuilt_shared']:
        raise ValueError('loading image mapping changed')
    if run.image_id(COMPILER) != COMPILER: raise ValueError('compiler unavailable')
    for image in set(images.values()):
        if run.image_id(image) != image: raise ValueError('image unavailable')
    seal = run.read(directory / 'verification.json')
    if not seal['passed'] or seal['files_sha256'] != bundle_hashes(directory):
        raise ValueError('loading bundle seal changed')
    check = run.read(directory / 'functional_verification.json')
    if not check['passed'] or check['performance_run'] or check['build_sha256'] != run.sha(directory / 'build.json'):
        raise ValueError('functional seal mismatch')
    if len(check['records']) != 8 or {(r['arm'], r['gomaxprocs']) for r in check['records']} != {(a, g) for a in ARMS for g in (1, 2)}:
        raise ValueError('eight fixture cells required')
    return value


def functional(directory, value):
    records = []
    assets = directory / 'runtime_assets'
    for arm in ARMS:
        mode = analysis.MODES[arm]
        for g in (1, 2):
            out = directory / f'fixture_{arm}_g{g}'; out.mkdir()
            args = ['docker', 'create', '-e', f'GOMAXPROCS={g}', '-e', 'WORKERS=4', '-e', 'INSTRUMENT=1',
                '-p', '127.0.0.1::8080'] + identity.mount_arguments(assets, mode) + [value['images'][arm]]
            container = run.capture(args)
            try:
                run.capture(['docker', 'start', container])
                port = run.capture(['docker', 'port', container, '8080/tcp']).split(':')[-1]
                base = f'http://127.0.0.1:{port}'
                def get(endpoint):
                    with urllib.request.urlopen(base + '/' + endpoint, timeout=10) as response:
                        return json.load(response)
                for _ in range(50):
                    try: health = get('health'); break
                    except OSError: time.sleep(.1)
                else: raise ValueError('fixture health timeout')
                loading = identity.collect(container, assets, mode, value['images'][arm], value['server_sha256'], value['probe_sha256'])
                run.put(out / 'file_loading.json', loading)
                with (out / 'client.log').open('w') as log:
                    subprocess.run([str(directory / 'loadgen'), '-url', base + '/work?iterations=10',
                        '-duration', '300ms', '-rate', '20', '-concurrency', '2', '-output', str(out / 'loadgen.json')],
                        stdout=log, stderr=subprocess.STDOUT, check=True, timeout=20)
                for _ in range(100):
                    server = get('metrics')
                    if server['active_handlers'] == 0 and server['completed'] == server['admitted']: break
                    time.sleep(.01)
                else: raise ValueError('fixture drain timeout')
                run.put(out / 'server_metrics.json', server)
                result = analysis.classify(run.read(out / 'loadgen.json'), server, arm)
                analysis.validate_state(health, arm)
                if health['gomaxprocs'] != g or health['go_version'] != 'go1.26.1' or result['offered'] != 6 or result['missing_entry_count']:
                    raise ValueError('functional mismatch')
                records.append(dict(arm=arm, gomaxprocs=g, requests=6,
                    clock_uncertainty_ns=result['mapping']['uncertainty_ns'], loading_verified=True))
            finally: run.capture(['docker', 'rm', '-f', container])
    run.put(directory / 'functional_verification.json', dict(passed=True, performance_run=False,
        build_sha256=run.sha(directory / 'build.json'), records=records))


def build(directory):
    if directory.exists(): raise ValueError('preserve existing build; use verify or another directory')
    old = baseline.verify()
    directory.mkdir(parents=True)
    shutil.copytree(baseline.DEFAULT / 'prepared', directory / 'prepared')
    shutil.copytree(run.HERE / 'loading_probe', directory / 'prepared/loading_probe')
    shutil.copy2(baseline.DEFAULT / 'loadgen', directory / 'loadgen')
    assets = directory / 'runtime_assets'; assets.mkdir()
    binary_dir = directory / 'binary_audit'; binary_dir.mkdir()
    originals = dict(legacy=old['images']['legacy_a'], rebuilt=old['images']['exact_rebuild'])
    for label, image in originals.items():
        container = run.capture(['docker', 'create', image])
        try: run.capture(['docker', 'cp', container + ':/server', str(binary_dir / (label + '.server'))])
        finally: run.capture(['docker', 'rm', container])
        run.put(binary_dir / (label + '.image.json'), json.loads(run.capture(['docker', 'image', 'inspect', image]))[0])
    if run.sha(binary_dir / 'legacy.server') != run.sha(binary_dir / 'rebuilt.server'):
        raise ValueError('image binaries are not identical')
    shutil.copy2(binary_dir / 'legacy.server', assets / 'shared.server'); (assets / 'shared.server').chmod(0o755)
    command = ['docker', 'run', '--rm', '--network', 'none', '-e', 'CGO_ENABLED=0', '-e', 'GOPROXY=off',
        '-e', 'GOSUMDB=off', '-e', 'GOTOOLCHAIN=local', '-v', str(directory / 'prepared/loading_probe') + ':/src:ro',
        '-v', str(assets) + ':/out', '-w', '/src', COMPILER, 'sh', '-c',
        'go version && go test -count=1 -v ./... && go build -trimpath -o /out/probe .']
    with (directory / 'probe_build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    images = dict(legacy_packaged=originals['legacy'], rebuilt_packaged=originals['rebuilt'],
        legacy_shared=originals['legacy'], rebuilt_shared=originals['rebuilt'])
    value = dict(schema=1, at=run.now(), images=images, compiler_image_id=COMPILER,
        sources=run.hashes(dependencies()), prepared_sha256=stock.prepared_hashes(directory / 'prepared'),
        loadgen_sha256=run.sha(directory / 'loadgen'), server_sha256=run.sha(assets / 'shared.server'),
        probe_sha256=run.sha(assets / 'probe'), baseline_build_sha256=run.sha(baseline.DEFAULT / 'build.json'),
        baseline_verification_sha256=run.sha(baseline.DEFAULT / 'verification.json'), probe_build_command=command)
    run.put(directory / 'build.json', value)
    functional(directory, value)
    run.put(directory / 'verification.json', dict(passed=True, files_sha256=bundle_hashes(directory)))
    verify(directory)
    print('V17 assets and eight HTTP/loading fixtures verified; performance collection not started.', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('command', choices=('build', 'verify'))
    p.add_argument('--directory', type=Path, default=DEFAULT); a = p.parse_args()
    if a.command == 'build':
        with run.acquire_experiment_lock(): build(a.directory.resolve())
    else: verify(a.directory.resolve()); print('V17 bundle verified.')
