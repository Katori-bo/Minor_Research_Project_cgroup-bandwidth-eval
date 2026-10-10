#!/usr/bin/env python3
"""Declare and check a fixed gzip candidate, without timing or quota experiments."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'analysis/runtime_io_gzip_candidate/generation-01'
DOC = ROOT / 'docs/runtime_io_gzip_candidate_qualification_plan_20261009.md'
ENV = {'LANG': 'C', 'LC_ALL': 'C', 'TZ': 'UTC'}
SOURCE_SHA256 = '9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48'
SPEC = dict(candidate='gnu-gzip-1.15-fixed-ndjson-generation-01',
    role='candidate selection and untimed correctness only; no performance qualification',
    input_records=4096, record_bytes=256, input_bytes=1048576,
    generator='xorshift32, seed 0x6d2b79f5, ten 8-hex words per record, sorted compact ASCII JSON padded before LF',
    command=['/application/gzip', '-n', '-6', '-c', '--', '/input/corpus.ndjson'],
    operation='one new GNU gzip process compresses the whole fixed corpus per offered request',
    upstream_version='1.15', upstream_commit='e6263160768c73f6117f3c1de78291a60f2cb796',
    upstream_source_url='https://ftp.gnu.org/gnu/gzip/gzip-1.15.tar.xz',
    upstream_source_sha256=SOURCE_SHA256,
    host_binary_provenance='Arch Linux installed gzip 1.15-1; retained binary, not a claimed source-reproducible build',
    selection_basis='Audit a finite native compression task with an explicit one-job completion boundary; do not select on model errors or favorable quota timings.',
    direct_correctness_invocations_cap=3, direct_invocation_timeout_sec=15,
    output_bytes_cap=2097152, correctness_retries=0,
    scientific_collection=False, performance_runner_implemented=False,
    qualification=dict(functional_created_cap=2, pilot_created_cap=12, retries=0,
        rate=5, interval_ns=200000000, warmup_offers=25, measurement_offers=200,
        pair_orders=['reference,observed', 'observed,reference'] * 3,
        limits={'cpu.max': '25000 100000', 'cpu.max.burst': '0', 'cpuset.cpus.effective': '2',
                'memory.max': '536870912', 'pids.max': '128'},
        queue_capacity=128, worker_jobs=1, client_inflight_cap=32,
        active_service_sec=120, total_sec=1200, cleanup_reserve_sec=120,
        dispatch_p99_ns=2000000, dispatch_max_ns=10000000,
        queue_le_100us_fraction=.99, measurement_throttled_periods=0,
        required_success_fraction=1, observer_cost_upper_relative=.05,
        pairs=6, t_multiplier=2.571, df=5,
        endpoints=['whole-cgroup CPU per offered request', 'median offered-to-full-body latency']),
    scope='Same-host compression workload/execution-stack transfer through a bespoke C service wrapper. No hardware, independent-team, or existing production HTTP-service transfer claim.')


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus():
    state = 0x6d2b79f5

    def step():
        nonlocal state
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        state &= 0xffffffff
        return state

    output = bytearray()
    for i in range(4096):
        words = ''.join(f'{step():08x}' for _ in range(10))
        value = dict(id=i, kind='metric', route=f'/api/v1/item/{i % 97}',
                     status=429 if i % 29 == 0 else 200,
                     bytes=1024 + (state & 65535), value=words)
        line = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
        if len(line) > 255:
            raise ValueError('Fixed corpus record overflow')
        output += line + b' ' * (255 - len(line)) + b'\n'
    if len(output) != SPEC['input_bytes']:
        raise ValueError('Fixed input size differs')
    return bytes(output)


def declare():
    BASE.mkdir(parents=True, exist_ok=False)
    (BASE / 'software').mkdir()
    (BASE / 'input').mkdir()
    # Commit the operation and dimensions before executing any compression.
    save(BASE / 'selection.json', SPEC)
    data = corpus()
    (BASE / 'input/corpus.ndjson').write_bytes(data)
    shutil.copy2('/usr/bin/gzip', BASE / 'software/gzip')
    version = subprocess.run([str(BASE / 'software/gzip'), '--version'], env=ENV,
                             capture_output=True, check=True, timeout=15).stdout.decode()
    if version.splitlines()[0] != 'gzip 1.15':
        raise ValueError('Pinned installed gzip version differs')
    package = subprocess.run(['pacman', '-Qi', 'gzip'], env=ENV,
                             capture_output=True, check=True, timeout=15).stdout.decode()
    (BASE / 'software/version.txt').write_text(version)
    (BASE / 'software/package.txt').write_text(package)
    save(BASE / 'identity.json', dict(input_sha256=sha(BASE / 'input/corpus.ndjson'),
        gzip_sha256=sha(BASE / 'software/gzip'), preparation_source_sha256=sha(Path(__file__)),
        plan_sha256=sha(DOC), performance_collected=False))
    print('Fixed gzip operation and input declared before compression; no timing collected.')


def validate_identity():
    if read(BASE / 'selection.json') != SPEC:
        raise ValueError('Declared operation changed')
    identity = read(BASE / 'identity.json')
    paths = {'input_sha256': BASE / 'input/corpus.ndjson', 'gzip_sha256': BASE / 'software/gzip',
             'preparation_source_sha256': Path(__file__), 'plan_sha256': DOC}
    for key, path in paths.items():
        if sha(path) != identity[key]:
            raise ValueError('Declared candidate changed: ' + key)
    return identity


def check():
    validate_identity()
    directory = BASE / 'correctness'
    directory.mkdir()  # No resume, overwrite or retries.
    data = (BASE / 'input/corpus.ndjson').read_bytes()
    lines = data.splitlines(keepends=True)
    if len(lines) != 4096 or any(len(line) != 256 for line in lines):
        raise ValueError('Corpus framing differs')
    for i, line in enumerate(lines):
        if json.loads(line)['id'] != i:
            raise ValueError('Corpus record identity differs')
    binary = str(BASE / 'software/gzip')
    command = [binary, '-n', '-6', '-c', '--', str(BASE / 'input/corpus.ndjson')]
    for index in (1, 2):
        result = subprocess.run(command, env=ENV, capture_output=True, timeout=15)
        (directory / f'compress-{index}.stderr').write_bytes(result.stderr)
        (directory / f'compress-{index}.gz').write_bytes(result.stdout)
        if result.returncode != 0 or result.stderr or len(result.stdout) > SPEC['output_bytes_cap']:
            raise ValueError('Bounded native compression failed')
    first = (directory / 'compress-1.gz').read_bytes()
    if first != (directory / 'compress-2.gz').read_bytes() or first[4:8] != b'\0\0\0\0':
        raise ValueError('Deterministic gzip output/header differs')
    result = subprocess.run([binary, '-d', '-c', '--', str(directory / 'compress-1.gz')],
                            env=ENV, capture_output=True, timeout=15)
    (directory / 'decompress.stderr').write_bytes(result.stderr)
    if result.returncode != 0 or result.stderr or result.stdout != data or gzip.decompress(first) != data:
        raise ValueError('Native/Python round-trip mismatch')
    save(directory / 'result.json', dict(passed=True, invocations=3,
        input_bytes=len(data), output_bytes=len(first), output_sha256=sha(directory / 'compress-1.gz'),
        independent_native_and_python_roundtrip=True, scientific_collection=False,
        performance_timing_collected=False, observer_cost_qualified=False))
    print('Three untimed native correctness calls passed; no quota or performance evidence.')


def seal():
    validate_identity()
    if not read(BASE / 'correctness/result.json')['passed']:
        raise ValueError('Correctness check missing')
    if sha(BASE / 'software/gzip-1.15.tar.xz') != SOURCE_SHA256:
        raise ValueError('Upstream source archive checksum differs')
    paths = [Path(__file__).resolve(), DOC]
    paths += [p for p in BASE.rglob('*') if p.is_file() and p.name != 'selection-seal.json']
    save(BASE / 'selection-seal.json', dict(role='selection and correctness seal; no qualified performance runner',
        files_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)},
        scientific_collection=False, observer_cost_qualified=False))
    print('Candidate selection, fixed input, native binary and correctness evidence sealed.')


def verify():
    validate_identity()
    for name, digest in read(BASE / 'selection-seal.json')['files_sha256'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Sealed selection changed: ' + name)
    print('Selection seal verifies; service implementation/qualification remain pending.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('declare', 'check', 'seal', 'verify'))
    args = parser.parse_args()
    globals()[args.phase]()
