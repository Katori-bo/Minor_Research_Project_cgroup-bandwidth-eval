"""Host02 apparatus overrides; scientific functions are retained separately."""
import json
import platform
import re
import shutil

PARENT = ROOT / 'runs/host02/study'
DESIGN = ROOT / 'assets/scientific_design'
CLIENT_BUILD = ROOT / 'assets/client_build'
SERVER_CPUS = (2, 3)
CONTROL_CPUS = (0, 1)


def verify_package():
    inventory = read(ROOT / 'package_seal.json')['files_sha256']
    for name, expected in inventory.items():
        p = resolve(ROOT, name)
        if p.is_symlink() or digest(p) != expected:
            raise ValueError('handoff package changed: ' + name)
    source = read(ROOT / 'package.json')['source_files']
    actual = {str(p.relative_to(ROOT)) for folder in ('diagnostic', 'scripts', 'analysis')
              for p in (ROOT / folder).rglob('*.py') if '__pycache__' not in p.parts}
    if actual != {n for n in source if n.endswith('.py')}:
        raise ValueError('source inventory changed; no added modules are allowed')
    return read(ROOT / 'package.json')


def design():
    verify_seal(DESIGN)
    value = read(DESIGN / 'design.json')
    original = read(ROOT / 'assets/original_complete_design.json')
    # Compare the entire scientific contract, allowing only declared CPU placement
    # and the explicitly predeclared secondary complete-response comparator.
    restored = json.loads(json.dumps(value))
    restored.pop('host_transfer')
    restored['secondary_models'].remove('ordinary_complete_response_cdf')
    for cfg in restored['calibration_configs'] + restored['validation_configs']:
        cfg['cpus'] = [2, 4]
    if restored != original:
        raise ValueError('host transfer altered the original scientific contract')
    return value


def source_hashes():
    return {name: digest(ROOT / name) for name in read(ROOT / 'package.json')['source_files']}


def verify_client_build():
    verify_seal(CLIENT_BUILD)
    m = read(CLIENT_BUILD / 'manifest.json')
    names = ('main.go', 'main_test.go', 'go.mod', 'parallelism_clock.go',
             'parallelism_clock_test.go')
    expected = {name: digest(ROOT / 'diagnostic/v27r2_loadgen' / name) for name in names}
    if (m['sources'] != expected or m['binary_sha256'] != digest(CLIENT_BUILD / 'loadgen')
            or not all(m[k] for k in ('test_passed', 'vet_passed', 'race_passed',
                                     'all_frozen_vectors_match_binary',
                                     'compiled_client_report_replay_passed'))):
        raise ValueError('retained client build receipts differ')
    for name, expected_hash in expected.items():
        if digest(CLIENT_BUILD / 'source' / name) != expected_hash:
            raise ValueError('retained client source differs')
    for pattern in ('steady', 'bursty'):
        folder = CLIENT_BUILD / ('compiled_report_' + pattern)
        verify_seal(folder)
        report = read(folder / 'report.json')
        if (not report['compiled_client_report_replay_passed'] or report['clock_fields_injected']
                or report['binary_sha256'] != m['binary_sha256'] or report['clock_anchors'] != 6):
            raise ValueError('retained client clock receipt differs')
    return m


def baseline():
    return dict(kernel=platform.release(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                topology={str(i): Path(f'/sys/devices/system/cpu/cpu{i}/topology/thread_siblings_list').read_text().strip()
                          for i in range(8)})


def monitor_minimum(cfg):
    return 80 if cfg['duration_sec'] == 60 else 45


def service_argv(image, qualification, name, config):
    return ['docker', 'create', '--name', name, '--cpuset-cpus', '2,3',
            '--cpu-period', str(config['period_us']), '--cpu-quota', str(config['quota_us']),
            '--mount', f'type=bind,src={qualification},dst=/qualification,readonly',
            '--entrypoint', '/qualification/gate', '-e', 'GOMAXPROCS=1',
            '-e', 'WORKERS=1', '-e', 'QUEUE_SIZE=128', '-e', 'INSTRUMENT=1',
            '-e', 'WORKER_YIELD=0', '-p', '127.0.0.1::8080', image, '--server']


def parse_cpu_list(value):
    """Parse Linux CPU-list notation without depending on its formatting."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing or empty CPU list')
    cpus = set()
    for entry in value.strip().split(','):
        if re.fullmatch(r'[0-9]+(?:-[0-9]+)?', entry) is None:
            raise ValueError('invalid CPU list: ' + repr(value))
        bounds = [int(part) for part in entry.split('-')]
        first, last = bounds[0], bounds[-1]
        if first > last:
            raise ValueError('descending CPU range: ' + repr(value))
        cpus.update(range(first, last + 1))
    return frozenset(cpus)


def resource_baseline(limits, host, config):
    cpu = {'cpu.max': f"{config['quota_us']} {config['period_us']}",
           'cpu.max.burst': '0'}
    if (any(limits.get(k) != v for k, v in cpu.items())
            or parse_cpu_list(limits.get('cpuset.cpus.effective')) != frozenset(SERVER_CPUS)):
        raise ValueError('host02 CPU quota, period, burst or cpuset differs')
    defaults = {k: host.get(k) for k in ('Memory', 'MemorySwap', 'PidsLimit')}
    if (defaults != dict(Memory=0, MemorySwap=0, PidsLimit=None)
            or limits.get('memory.max') != 'max'
            or host.get('CpuQuota') != config['quota_us']
            or host.get('CpuPeriod') != config['period_us']
            or parse_cpu_list(host.get('CpusetCpus')) != frozenset(SERVER_CPUS)):
        raise ValueError('extra resource overrides or CPU settings differ')
    pids = limits.get('pids.max')
    if pids != 'max' and (not isinstance(pids, str) or not pids.isdecimal() or int(pids) < 512):
        raise ValueError('host default PID capacity is insufficient')
    return dict(limits=dict(limits), host_config=defaults)


def validate_resources(limits, host, baseline, config):
    observed = resource_baseline(limits, host, config)
    if baseline is None or observed != baseline:
        raise ValueError('resource baseline must be freshly frozen by the unreleased host preflight')


def owned_directory(value):
    p = Path(value).absolute()
    if p.parent != PARENT or p.name != 'generation-01' or p.is_symlink() or p.resolve() != p:
        raise ValueError('use this package\'s runs/host02/study/generation-01; preserve attempts')
    return p
