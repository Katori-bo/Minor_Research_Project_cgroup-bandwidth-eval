"""Build/package the declared candidate; never run a performance experiment."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

import gzip_candidate_prepare as selection

ROOT = selection.ROOT
BASE = ROOT / 'analysis/runtime_io_gzip_qualification/generation-01'
SOFTWARE = BASE / 'software'


def build():
    selection.verify()
    BASE.mkdir(parents=True, exist_ok=False)
    SOFTWARE.mkdir()
    compiler = subprocess.check_output(['gcc', '--version'], text=True)
    (SOFTWARE / 'compiler.txt').write_text(compiler)
    commands = []
    with (SOFTWARE / 'build.log').open('x') as log:
        for arm, enabled in (('reference', '0'), ('observed', '1')):
            argv = ['gcc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-pthread',
                    '-DOBSERVED=' + enabled, str(ROOT / 'diagnostic/gzip_service.c'),
                    '-o', str(SOFTWARE / ('server-' + arm))]
            commands.append(argv)
            subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        argv = ['gcc', '-O2', '-static', str(ROOT / 'diagnostic/kernel_start_gate.c'), '-o', str(SOFTWARE / 'gate')]
        commands.append(argv)
        subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        go = ROOT / 'analysis/runtime_io_imgproxy_feasibility/generation-01/software/toolchain/go/bin/go'
        env = dict(os.environ, GOTOOLCHAIN='local', GOENV='off', CGO_ENABLED='0', GOPROXY='off',
                   GOSUMDB='off', GOCACHE='/tmp/gzip-build-cache', GOMAXPROCS='2')
        for operation in ('build', 'vet'):
            argv = [str(go), operation]
            if operation == 'build': argv += ['-trimpath', '-o', str(SOFTWARE / 'client')]
            argv += ['.']
            commands.append(argv)
            subprocess.run(argv, cwd=ROOT / 'diagnostic/gzip_client', env=env, check=True,
                           stdout=log, stderr=subprocess.STDOUT, timeout=120)
    runtime = SOFTWARE / 'runtime'
    runtime.mkdir()
    for directory in ('application', 'input', 'usr/lib', 'usr/lib64', 'lib64'):
        (runtime / directory).mkdir(parents=True, exist_ok=True)
    shutil.copy2(selection.BASE / 'software/gzip', runtime / 'application/gzip')
    shutil.copy2(selection.BASE / 'input/corpus.ndjson', runtime / 'input/corpus.ndjson')
    shutil.copy2(SOFTWARE / 'gate', runtime / 'gate')
    for destination in ('usr/lib/libc.so.6', 'usr/lib64/ld-linux-x86-64.so.2', 'lib64/ld-linux-x86-64.so.2'):
        origin = Path('/usr/lib/libc.so.6') if destination.endswith('libc.so.6') else Path('/usr/lib64/ld-linux-x86-64.so.2')
        shutil.copy2(origin.resolve(), runtime / destination)
    # Shared-library closure is intentionally just libc and its interpreter.
    closures = {}
    for executable in (SOFTWARE / 'server-reference', SOFTWARE / 'server-observed', runtime / 'application/gzip'):
        value = subprocess.check_output(['readelf', '-d', str(executable)], text=True)
        needed = [line for line in value.splitlines() if '(NEEDED)' in line]
        if needed != [line for line in needed if '[libc.so.6]' in line] or len(needed) != 1:
            raise ValueError('Unexpected runtime dependency closure: ' + str(executable))
        closures[executable.name] = needed
    archives = {}
    for arm in ('reference', 'observed'):
        shutil.copy2(SOFTWARE / ('server-' + arm), runtime / 'server')
        path = SOFTWARE / ('runtime-' + arm + '.tar')
        with tarfile.open(path, 'w') as tar:
            for child in sorted(runtime.iterdir()): tar.add(child, arcname=child.name)
        archives[arm] = selection.sha(path)
    selection.save(SOFTWARE / 'manifest.json', dict(
        source_sha256=selection.sha(ROOT / 'diagnostic/gzip_service.c'), commands=commands,
        binaries={arm: selection.sha(SOFTWARE / ('server-' + arm)) for arm in ('reference', 'observed')},
        gzip_sha256=selection.sha(runtime / 'application/gzip'),
        client_sha256=selection.sha(SOFTWARE / 'client'), gate_sha256=selection.sha(SOFTWARE / 'gate'),
        runtime_files_sha256={str(p.relative_to(runtime)): selection.sha(p) for p in runtime.rglob('*')
                              if p.is_file() and p.name != 'server'}, runtime_tars_sha256=archives,
        dynamic_dependencies=closures, source_selection_seal_sha256=selection.sha(selection.BASE / 'selection-seal.json')))
    print('C service arms, Go client, startup gate and exact libc runtime archives built.')


def package():
    images = {}
    for arm in ('reference', 'observed'):
        argv = ['docker', 'import', '--change', 'ENTRYPOINT ["/gate", "--server"]',
                str(SOFTWARE / ('runtime-' + arm + '.tar')), 'research-gzip-qualification:' + arm]
        images[arm] = subprocess.check_output(argv, text=True, timeout=60).strip()
        if not images[arm].startswith('sha256:'): raise ValueError('Immutable Docker image identity missing')
    selection.save(SOFTWARE / 'images.json', images)
    print('Separate immutable gzip service images packaged.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('build', 'package'))
    globals()[p.parse_args().phase]()
