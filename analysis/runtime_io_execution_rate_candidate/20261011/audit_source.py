#!/usr/bin/env python3
"""Read-only metadata capture; never opens counters or starts a workload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'analysis/runtime_io_execution_rate_candidate/20261011'
ASSESSMENT = ROOT / 'docs/runtime_io_execution_rate_candidate_20261011.md'
MANIFESTS = [
    'analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01/inputs_sha256.json',
    'analysis/runtime_io_nginx_worker_wait_qualification_review/20261010-generation01/inputs_sha256.json',
]
METADATA = [
    '/proc/sys/kernel/perf_event_paranoid',
    '/sys/bus/event_source/devices/msr/type',
    '/sys/bus/event_source/devices/msr/events/aperf',
    '/sys/bus/event_source/devices/msr/events/mperf',
    '/sys/bus/event_source/devices/msr/events/tsc',
    '/sys/devices/system/cpu/cpu2/topology/thread_siblings_list',
    '/sys/devices/system/cpu/cpu2/cpufreq/scaling_driver',
    '/sys/devices/system/cpu/cpu2/cpufreq/scaling_governor',
    '/sys/devices/system/cpu/cpu2/cpufreq/energy_performance_preference',
    '/sys/devices/system/cpu/cpu2/cpufreq/scaling_min_freq',
    '/sys/devices/system/cpu/cpu2/cpufreq/scaling_max_freq',
    '/sys/devices/system/cpu/cpu2/cpufreq/cpuinfo_cur_freq',
]
SOURCES = [
    ('AMD EPP is a hardware hint', 'https://docs.kernel.org/admin-guide/pm/amd-pstate.html'),
    ('Sysfs frequency attribution limits', 'https://docs.kernel.org/admin-guide/pm/cpufreq.html'),
    ('Perf access restrictions', 'https://docs.kernel.org/admin-guide/perf-security.html'),
    ('Busy-frequency ratio implementation', 'https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/kernel/cpu/aperfmperf.c'),
    ('Task-capable counting and exclusion limits; upstream, not installed binary verification', 'https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/events/msr.c'),
    ('ReTail: frequency-conditioned prediction and error-based retraining', 'https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf'),
    ('Earlier frequency-gradient end-to-end prediction; abstract inspected', 'https://experts.illinois.edu/en/publications/blackbox-prediction-of-the-impact-of-dvfs-on-end-to-end-performan/'),
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def read_metadata(path):
    try:
        return {'status': 'read', 'value': Path(path).read_text().strip()}
    except OSError as exc:
        return {'status': 'unavailable', 'errno': exc.errno}


def check_hashes(base, entries):
    for relative, expected in entries.items():
        path = (base / relative).resolve()
        if not path.is_relative_to(base.resolve()):
            raise ValueError('Hash path outside package/workspace: ' + relative)
        if digest(path) != expected:
            raise ValueError('Changed input: ' + relative)


def capture():
    if PACKAGE.exists():
        raise FileExistsError('Existing audit retained; use --verify')
    protected = {}
    counts = {}
    for relative in MANIFESTS:
        entries = json.loads((ROOT / relative).read_text())
        check_hashes(ROOT, entries)
        counts[relative] = len(entries)
        for name, value in entries.items():
            if name in protected and protected[name] != value:
                raise ValueError('Conflicting historical input: ' + name)
            protected[name] = value
        protected[relative] = digest(ROOT / relative)
    for relative in [
        'docs/runtime_io_execution_state_next_step.md',
        'docs/runtime_io_nginx_mechanism_decision_20261010.md',
        'docs/runtime_io_prevalidation_signals_assessment_20261010.md',
        'docs/runtime_io_warmup_precision_cost_assessment_20261011.md',
        'docs/runtime_io_execution_rate_candidate_20261011.md',
        'analysis/audit_execution_rate_capability.py',
    ]:
        protected[relative] = digest(ROOT / relative)
    metadata = {p: read_metadata(p) for p in METADATA}
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
    caps = int(status['CapEff'].strip(), 16)
    info = dict(line.split(':', 1) for line in Path('/proc/cpuinfo').read_text().split('\n\n')[0].splitlines() if ':' in line)
    identity_keys = ['vendor_id', 'cpu family', 'model', 'model name', 'stepping']
    identity = {k: v.strip() for k, v in ((k.strip(), v) for k, v in info.items()) if k in identity_keys}
    capability = {
        'captured_utc': datetime.now(timezone.utc).isoformat(),
        'kernel': platform.release(), 'uid': os.getuid(), 'cpu_identity': identity,
        'metadata': metadata, 'perf_binary': shutil.which('perf'),
        'CapEff': status['CapEff'].strip(), 'NoNewPrivs': status['NoNewPrivs'].strip(),
        'CAP_PERFMON_effective': bool(caps & (1 << 38)),
        'CAP_SYS_ADMIN_effective': bool(caps & (1 << 21)),
        'dev_cpu2_msr_exists': Path('/dev/cpu/2/msr').exists(),
        'hardware_events_opened': False, 'service_started': False,
        'host_settings_written': False, 'measurement_qualified': False,
        'predictive_usefulness_tested': False,
    }
    PACKAGE.mkdir(parents=True)
    dump(PACKAGE / 'capability.json', capability)
    dump(PACKAGE / 'prior_sources.json', {
        'accessed_date': '2026-10-11', 'search_scope': 'bounded, not exhaustive novelty review',
        'sources': [{'purpose': purpose, 'url': url} for purpose, url in SOURCES],
        'unresolved_sources': ['AMD architectural manual endpoint unavailable; processor-specific GHz normalization remains unverified'],
    })
    dump(PACKAGE / 'inputs_sha256.json', protected)
    shutil.copyfile(ASSESSMENT, PACKAGE / 'assessment_snapshot.md')
    shutil.copyfile(Path(__file__), PACKAGE / 'audit_source.py')
    dump(PACKAGE / 'verification_receipt.json', {
        'historical_manifest_counts': counts, 'protected_paths': len(protected),
        'historical_hashes_verified': True,
        'decision': 'measurement_design_only_predictive_campaign_not_justified',
        'qualification_pending': ['access', 'attribution', 'boundaries', 'precision', 'observer_cost', 'future_relation'],
    })
    dump(PACKAGE / 'seal.json', {'files_sha256': {
        str(p.relative_to(PACKAGE)): digest(p) for p in sorted(PACKAGE.iterdir()) if p.is_file()
    }})
    verify()


def verify():
    check_hashes(PACKAGE, json.loads((PACKAGE / 'seal.json').read_text())['files_sha256'])
    entries = json.loads((PACKAGE / 'inputs_sha256.json').read_text())
    check_hashes(ROOT, entries)
    print(json.dumps({'status': 'verified', 'protected_paths': len(entries),
                      'counter_access_or_measurement_tested': False,
                      'package': str(PACKAGE)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--capture', action='store_true')
    action.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    capture() if args.capture else verify()
