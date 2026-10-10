#!/usr/bin/env python3
"""Rebuild the retained V12 prepared source verbatim, offline and without build cache."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

import build_parallelism as stock
import repeatability_analysis as analysis
import run

DEFAULT = run.ROOT / 'analysis/runtime_io_v16_repeatability_build'
COMPILER = stock.COMPILER
ARMS = analysis.ARMS


def dependencies():
    return sorted(set(stock.dependencies() + [Path(__file__), run.HERE / 'repeatability_analysis.py',
        run.HERE / 'completion_analysis.py', run.HERE / 'parallelism_analysis.py',
        run.HERE / 'run.py']))


def prepare(directory):
    # Frozen generated V12 source, including its original Dockerfile and tests.
    shutil.copytree(stock.DEFAULT / 'prepared/service', directory / 'service')
    if stock.prepared_hashes(directory / 'service') != stock.prepared_hashes(stock.DEFAULT / 'prepared/service'):
        raise ValueError('exact prepared source copy failed')


def audit(directory, images):
    out = directory / 'binary_audit'; out.mkdir()
    records = {}
    # Read V15 evidence too; do not rebuild or modify it.
    v15 = run.read(run.ROOT / 'analysis/runtime_io_v15_marker_verified_build/build.json')
    for arm, image in dict(legacy=images['legacy_a'], exact_rebuild=images['exact_rebuild'],
            v15_metadata_zero=v15['images']['rebuilt_zero']).items():
        binary = out / (arm + '.server')
        container = run.capture(['docker', 'create', image])
        try:
            run.capture(['docker', 'cp', container + ':/server', str(binary)])
        finally:
            run.capture(['docker', 'rm', container])
        prefix = ['docker', 'run', '--rm', '--network', 'none', '-v', str(out) + ':/audit:ro', COMPILER]
        for name, command in (
                ('build_info', ['go', 'version', '-m', '/audit/' + binary.name]),
                ('build_id', ['go', 'tool', 'buildid', '/audit/' + binary.name]),
                ('main_disassembly', ['go', 'tool', 'objdump', '-s', '^main\\.', '/audit/' + binary.name])):
            (out / (arm + '.' + name + '.txt')).write_text(run.capture(prefix + command))
        image_info = json.loads(run.capture(['docker', 'image', 'inspect', image]))[0]
        run.put(out / (arm + '.image.json'), image_info)
        records[arm] = dict(image=image, binary_sha256=run.sha(binary),
            build_id=(out / (arm + '.build_id.txt')).read_text().strip(),
            image_config=image_info['Config'], rootfs=image_info['RootFS'])
    a, z = records['legacy'], records['exact_rebuild']
    result = dict(passed=True, records=records, same_image_labels_identical=images['legacy_a'] == images['legacy_b'],
        exact_rebuild_binary_identical=a['binary_sha256'] == z['binary_sha256'],
        exact_rebuild_build_id_identical=a['build_id'] == z['build_id'],
        exact_rebuild_config_identical=a['image_config'] == z['image_config'],
        v15_zero_binary_identical=a['binary_sha256'] == records['v15_metadata_zero']['binary_sha256'],
        limitation='Identity is an audit result, not a behavioral equivalence claim. Image creation history '
        'can differ. Metadata-zero is historical audit evidence, not a performance arm.')
    run.put(out / 'audit.json', result)
    return result


def functional(directory, value):
    records = []
    for arm in ARMS:
        for g in (1, 2):
            out = directory / f'fixture_{arm}_g{g}'; out.mkdir()
            container = run.capture(['docker', 'create', '-e', f'GOMAXPROCS={g}', '-e', 'WORKERS=4',
                '-e', 'INSTRUMENT=1', '-p', '127.0.0.1::8080', value['images'][arm]])
            try:
                run.capture(['docker', 'start', container])
                port = run.capture(['docker', 'port', container, '8080/tcp']).split(':')[-1]
                base = f'http://127.0.0.1:{port}'
                def get(endpoint):
                    with urllib.request.urlopen(base + '/' + endpoint, timeout=10) as response:
                        return json.load(response)
                for _ in range(50):
                    try:
                        health = get('health'); break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise ValueError('fixture health timeout')
                with (out / 'client.log').open('w') as log:
                    subprocess.run([str(directory / 'loadgen'), '-url', base + '/work?iterations=10',
                        '-duration', '300ms', '-rate', '20', '-concurrency', '2',
                        '-output', str(out / 'loadgen.json')], stdout=log, stderr=subprocess.STDOUT,
                        check=True, timeout=20)
                for _ in range(100):
                    server = get('metrics')
                    if server['active_handlers'] == 0 and server['completed'] == server['admitted']:
                        break
                    time.sleep(.01)
                else:
                    raise ValueError('functional drain timeout')
                run.put(out / 'server_metrics.json', server)
                result = analysis.classify(run.read(out / 'loadgen.json'), server, arm)
                analysis.validate_state(health, arm)
                if health['go_version'] != 'go1.26.1' or health['gomaxprocs'] != g or result['offered'] != 6 or result['missing_entry_count']:
                    raise ValueError('functional fixture mismatch')
                records.append(dict(arm=arm, gomaxprocs=g, requests=6,
                    clock_uncertainty_ns=result['mapping']['uncertainty_ns']))
            finally:
                run.capture(['docker', 'rm', '-f', container])
    files = {str(p.relative_to(directory)): run.sha(p) for p in sorted(directory.glob('fixture_*/*')) if p.is_file()}
    run.put(directory / 'functional_verification.json', dict(passed=True, performance_run=False, records=records,
        build_sha256=run.sha(directory / 'build.json'), analyzer_sha256=run.sha(run.HERE / 'repeatability_analysis.py'),
        files_sha256=files))


def verify(directory=DEFAULT, fixtures=True):
    value = run.read(directory / 'build.json')
    if value['sources'] != run.hashes(dependencies()) or value['prepared_sha256'] != stock.prepared_hashes(directory / 'prepared'):
        raise ValueError('repeatability source changed')
    if value['original_prepared_service_sha256'] != stock.prepared_hashes(directory / 'prepared/service'):
        raise ValueError('exact-source rebuild was modified')
    if value['loadgen_sha256'] != run.sha(directory / 'loadgen') or value['compiler_image_id'] != COMPILER:
        raise ValueError('compiler/client changed')
    if set(value['images']) != set(ARMS) or value['images']['legacy_a'] != value['images']['legacy_b']:
        raise ValueError('A/A images differ')
    if value['build_cache_used'] or value['build_network'] != 'none':
        raise ValueError('rebuild must compile offline without cache')
    if run.image_id(COMPILER) != COMPILER:
        raise ValueError('retained compiler unavailable')
    for image in set(value['images'].values()):
        if run.image_id(image) != image:
            raise ValueError('image unavailable')
        labels = json.loads(run.capture(['docker', 'image', 'inspect', '--format', '{{json .Config.Labels}}', image]))
        if labels.get('research.runtime.variant') != 'stock':
            raise ValueError('non-stock image')
    if fixtures:
        check = run.read(directory / 'functional_verification.json')
        if not check['passed'] or check['performance_run'] or check['build_sha256'] != run.sha(directory / 'build.json') or check['analyzer_sha256'] != run.sha(run.HERE / 'repeatability_analysis.py'):
            raise ValueError('functional seal changed')
        if len(check['records']) != 6 or {(r['arm'], r['gomaxprocs']) for r in check['records']} != {(a, g) for a in ARMS for g in (1, 2)}:
            raise ValueError('six fixture cells required')
        seal = run.read(directory / 'verification.json')
        actual = {str(p.relative_to(directory)): run.sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.name != 'verification.json'}
        if not seal['passed'] or seal['files_sha256'] != actual:
            raise ValueError('build verification files changed')
        if not run.read(directory / 'binary_audit/audit.json')['passed']:
            raise ValueError('binary audit absent')
    return value


def build(directory):
    if directory.exists():
        raise ValueError('preserve existing build; use verify or another directory')
    legacy = stock.verify()
    directory.mkdir(parents=True)
    prepare(directory / 'prepared')
    tag = 'quota-exact-rebuild-service:16'
    command = ['docker', 'build', '--no-cache', '--pull=false', '--network', 'none',
        '--build-arg', 'COMPILER_IMAGE=' + COMPILER, '-t', tag, str(directory / 'prepared/service')]
    with (directory / 'exact_rebuild_build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    images = dict(legacy_a=legacy['images']['service'], legacy_b=legacy['images']['service'],
        exact_rebuild=run.image_id(tag))
    shutil.copy2(stock.DEFAULT / 'loadgen', directory / 'loadgen')
    value = dict(schema=1, at=run.now(), compiler_image_id=COMPILER, images=images,
        sources=run.hashes(dependencies()), prepared_sha256=stock.prepared_hashes(directory / 'prepared'),
        original_prepared_service_sha256=stock.prepared_hashes(stock.DEFAULT / 'prepared/service'),
        loadgen_sha256=run.sha(directory / 'loadgen'), legacy_build_sha256=run.sha(stock.DEFAULT / 'build.json'),
        build_cache_used=False, build_network='none', build_command=command)
    run.put(directory / 'build.json', value)
    result = audit(directory, images)
    print('Full rebuilt binary identical to legacy:', result['exact_rebuild_binary_identical'], flush=True)
    functional(directory, value)
    files = {str(p.relative_to(directory)): run.sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    run.put(directory / 'verification.json', dict(passed=True, files_sha256=files))
    verify(directory)
    print('V16 exact rebuild and six HTTP fixtures verified; no performance collection started.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build', 'verify'))
    parser.add_argument('--directory', type=Path, default=DEFAULT)
    args = parser.parse_args()
    if args.command == 'build':
        with run.acquire_experiment_lock():
            build(args.directory.resolve())
    else:
        verify(args.directory.resolve()); print('V16 build verified.')
