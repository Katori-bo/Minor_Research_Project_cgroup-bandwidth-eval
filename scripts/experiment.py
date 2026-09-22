#!/usr/bin/env python3
"""Session-based runner. Standard-library only; no system settings are changed."""
import argparse
import csv
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import signal
import statistics
import subprocess as sp
import sys
import time
import urllib.request
from environment_controls import POLICY, power_settings, comparable_power, window_summary

ROOT = Path(__file__).resolve().parents[1]
LOADGEN = ROOT / 'tools/loadgen/bin/loadgen'
MONITOR = ROOT / 'scripts/monitor_host.py'
IMAGE = 'research-service:study-v2'
CPUS = '2,4'
CLIENT_CPUS = '0,1'
PORT = 18080


def command(args, **kwargs):
    return sp.run(list(map(str, args)), check=True, text=True, **kwargs)


def capture(args):
    return command(args, stdout=sp.PIPE).stdout.strip()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def read_stat(path):
    return {k: int(v) for k, v in (line.split() for line in path.read_text().splitlines())}


def cpu_topology():
    base = Path('/sys/devices/system/cpu')
    return {str(i): {
        'core': (base / f'cpu{i}/topology/core_id').read_text().strip(),
        'package': (base / f'cpu{i}/topology/physical_package_id').read_text().strip(),
        'siblings': (base / f'cpu{i}/topology/thread_siblings_list').read_text().strip()
    } for i in [0, 1, 2, 3, 4, 5]}


def check_topology():
    topo = cpu_topology()
    key = lambda i: (topo[str(i)]['package'], topo[str(i)]['core'])
    if key(2) == key(4) or {key(0), key(1)} & {key(2), key(4)}:
        raise RuntimeError('CPU topology differs from the study configuration; update CPU affinity first.')
    return topo


def temperatures():
    values = {}
    # Prefer the AMD package sensor when available; thermal zones may be ACPI zones.
    for hw in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            if hw.joinpath('name').read_text().strip() != 'k10temp':
                continue
            for sensor in hw.glob('temp*_input'):
                label_file = sensor.with_name(sensor.name.replace('_input', '_label'))
                label = label_file.read_text().strip() if label_file.exists() else sensor.stem
                values['k10temp:' + label] = int(sensor.read_text()) / 1000
        except OSError:
            pass
    if not values:
        for sensor in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
            try:
                values[str(sensor)] = int(sensor.read_text()) / 1000
            except OSError:
                pass
    return values


def settle(log_path, baseline=None, initial_idle=False, expected_power=None):
    start = time.monotonic()
    samples = []
    minimum = POLICY['initial_idle_sec'] if initial_idle else POLICY['window_sec']
    print(f'Settling: at least {minimum}s; checking a stable 60s temperature window.', flush=True)
    while True:
        elapsed = time.monotonic() - start
        vals = temperatures()
        current_power = power_settings()
        samples.append({'elapsed_sec': elapsed, 'timestamp': time.time(),
                        'temperatures': vals, 'power_settings': current_power})
        write_json(log_path, {'policy': POLICY, 'samples': samples, 'accepted': False})
        if not vals:
            raise RuntimeError('No readable temperature sensor.')
        if expected_power is not None and current_power != comparable_power(expected_power):
            raise RuntimeError('Power settings changed during settling; logs preserved.')
        # Include the sample just before the window boundary to cover a full minute.
        index = 0
        while index + 1 < len(samples) and samples[index + 1]['elapsed_sec'] <= elapsed - POLICY['window_sec']:
            index += 1
        summary = window_summary(samples[index:], baseline)
        if elapsed >= minimum and summary and summary['stable']:
            write_json(log_path, {'policy': POLICY, 'samples': samples, 'accepted': True, 'summary': summary})
            return summary
        if elapsed >= minimum + POLICY['timeout_sec']:
            raise RuntimeError('Temperature did not stabilize within the protocol timeout; inspect settling log.')
        if len(samples) % 12 == 1:
            print(f'Settling {elapsed:.0f}s: {vals}', flush=True)
        time.sleep(POLICY['sample_sec'])


def prepare_environment(session):
    path = session / 'environment.json'
    if path.exists():
        env = json.loads(path.read_text())
        if power_settings(include_profile=True) != env['power_settings']:
            raise RuntimeError('Power profile/settings differ from the original session.')
        settle(session / f'resume-settling-{time.time_ns()}.json', env['baseline_c'],
               initial_idle=True, expected_power=env['power_settings'])
        return
    settings = power_settings(include_profile=True)
    if settings['external_power'] and not any(v == '1' for v in settings['external_power'].values()):
        raise RuntimeError('External power is disconnected. Plug in before starting.')
    if settings.get('desktop_profile') not in (None, 'balanced'):
        raise RuntimeError('Select Balanced before starting this study; no setting was changed automatically.')
    summary = settle(session / 'initial-settling.json', initial_idle=True, expected_power=settings)
    write_json(path, {'policy': POLICY, 'power_settings': settings,
                     'baseline_c': {k: v['mean_c'] for k, v in summary['sensors'].items()}})


def provenance():
    files = list((ROOT / 'service').rglob('*.go')) + list((ROOT / 'tools/loadgen').glob('*.go'))
    files += list((ROOT / 'scripts').glob('*.py')) + list((ROOT / 'scripts').glob('*.sh')) + list((ROOT / 'analysis').glob('*v2.py')) + [ROOT / 'service/Dockerfile', LOADGEN]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}


def initialize(session, diagnostic):
    session.mkdir(parents=True, exist_ok=False)
    for folder in ['calibration', 'pilot', 'raw', 'processed', 'logs']:
        (session / folder).mkdir()
    metadata = {
        'created': dt.datetime.now().astimezone().isoformat(), 'diagnostic': diagnostic,
        'topology': check_topology(), 'server_cpus': CPUS, 'client_cpus': CLIENT_CPUS,
        'kernel': capture(['uname', '-a']), 'docker': capture(['docker', 'version']),
        'docker_info': capture(['docker', 'info']),
        'image_id': capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', IMAGE]),
        'source_sha256': provenance(), 'temperatures': temperatures(),
        'governors': {str(p): p.read_text().strip() for p in Path('/sys/devices/system/cpu').glob('cpufreq/policy*/scaling_governor')},
        'processes': capture(['ps', '-eo', 'pid,comm,pcpu']),
    }
    write_json(session / 'metadata.json', metadata)
    snapshot = session / 'source'
    for rel in metadata['source_sha256']:
        if rel == 'tools/loadgen/bin/loadgen':
            continue
        target = snapshot / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)


def cgroup_path(pid):
    for line in Path(f'/proc/{pid}/cgroup').read_text().splitlines():
        hierarchy, controllers, rel = line.split(':', 2)
        if hierarchy == '0' and controllers == '':
            return Path('/sys/fs/cgroup') / rel.lstrip('/')
    raise RuntimeError('Container does not have a cgroup v2 path')


def verify_limits(cg, period, quota):
    actual = cg.joinpath('cpu.max').read_text().strip()
    expected = f'{quota} {period}' if period else 'max 100000'
    if actual != expected:
        raise RuntimeError(f'cpu.max expected {expected!r}, got {actual!r}')
    limits = {}
    current = cg
    while current != Path('/sys/fs/cgroup'):
        row = {}
        for filename in ['cpu.max', 'cpu.max.burst', 'cpuset.cpus.effective']:
            p = current / filename
            if p.exists():
                row[filename] = p.read_text().strip()
        if current != cg and row.get('cpu.max', 'max').split()[0] != 'max':
            raise RuntimeError(f'Ancestor CPU cap at {current}: {row}')
        limits[str(current)] = row
        current = current.parent
    if limits[str(cg)].get('cpu.max.burst', '0') != '0':
        raise RuntimeError('Container burst allowance is nonzero')
    return limits


def loadgen_args(config, seconds, output):
    args = ['taskset', '-c', CLIENT_CPUS, LOADGEN, '-url',
            f'http://127.0.0.1:{PORT}/work?iterations={config["iterations"]}',
            '-duration', f'{seconds}s', '-pattern', config['pattern'],
            '-rate', str(config['rate']), '-concurrency', '512', '-output', output]
    if config['pattern'] == 'bursty':
        args += ['-burst-low', str(config['burst_low']), '-burst-high', str(config['burst_high']), '-burst-period', '10s']
    return args


def assess(report):
    lg = report['loadgen_metrics']
    flags = []
    if lg['client_dropped']:
        flags.append('client_capacity_exceeded')
    if lg['missed_arrivals']:
        flags.append('scheduler_late')
    if lg['dispatch_lag_summary']['p99_ms'] > 2:
        flags.append('dispatch_lag_p99_above_2ms')
    if report['monitor_samples'] < max(1, report['config']['duration_sec'] * .7):
        flags.append('insufficient_monitor_samples')
    # Application errors remain outcomes, not automatic reasons to discard trials.
    return flags


def trial(session, phase, run_id, config, duration=60, warmup=20):
    run_dir = session / phase / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    name = f'quota-study-{os.getpid()}'
    monitor = None
    monitor_log = None
    created = False
    started = time.time()
    config = dict(config, duration_sec=duration, warmup_sec=warmup)
    write_json(run_dir / 'config.json', config)
    try:
        env_path = session / 'environment.json'
        if not env_path.exists():
            prepare_environment(session)
        environment = json.loads(env_path.read_text())
        power_before = power_settings(include_profile=True)
        if power_before != environment['power_settings']:
            raise RuntimeError('Power settings changed since the session baseline.')
        thermal = settle(run_dir / 'settling.json', environment['baseline_c'], expected_power=power_before)
        args = ['docker', 'run', '-d', '--rm', '--name', name, f'--cpuset-cpus={CPUS}',
                '-e', f'WORKERS={config["workers"]}', '-e', 'QUEUE_SIZE=128',
                '-p', f'127.0.0.1:{PORT}:8080']
        if config['period_us']:
            args += [f'--cpu-period={config["period_us"]}', f'--cpu-quota={config["quota_us"]}']
        capture(args + [IMAGE])
        created = True
        for _ in range(50):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=1) as response:
                    health = json.load(response)
                break
            except OSError:
                time.sleep(.2)
        else:
            raise RuntimeError('Service readiness timed out')
        if health['workers'] != config['workers'] or health['gomaxprocs'] != 2:
            raise RuntimeError(f'Unexpected service settings: {health}')
        pid = int(capture(['docker', 'inspect', '--format', '{{.State.Pid}}', name]))
        cg = cgroup_path(pid)
        limits = verify_limits(cg, config['period_us'], config['quota_us'])
        write_json(run_dir / 'limits.json', limits)
        if warmup:
            with (run_dir / 'warmup.log').open('w') as log:
                command(loadgen_args(config, warmup, run_dir / 'warmup.json'), stdout=log, stderr=sp.STDOUT)
        if power_settings(include_profile=True) != power_before:
            raise RuntimeError('Power settings changed during warm-up.')
        monitor_log = (run_dir / 'monitor.log').open('w')
        monitor = sp.Popen(['taskset', '-c', CLIENT_CPUS, sys.executable, str(MONITOR),
                            '--cgroup-path', '/' + str(cg.relative_to('/sys/fs/cgroup')),
                            '--output', str(run_dir / 'monitor.json')], stdout=monitor_log, stderr=sp.STDOUT)
        initial = read_stat(cg / 'cpu.stat')
        measurement_start_wall = time.time()
        start = time.monotonic()
        with (run_dir / 'loadgen.log').open('w') as log:
            command(loadgen_args(config, duration, run_dir / 'loadgen.json'), stdout=log, stderr=sp.STDOUT)
        elapsed = time.monotonic() - start
        final = read_stat(cg / 'cpu.stat')
        measurement_end_wall = time.time()
        power_after = power_settings(include_profile=True)
        monitor.send_signal(signal.SIGINT)
        monitor.wait(timeout=10)
        monitor = None
        samples = json.loads((run_dir / 'monitor.json').read_text())
        lg = json.loads((run_dir / 'loadgen.json').read_text())
        delta = {k: final[k] - initial.get(k, 0) for k in final}
        report = {
            'schema_version': 2, 'run_id': run_id, 'phase': phase,
            'trial_timestamp_start': started,
            'timestamp_start': measurement_start_wall, 'timestamp_end': measurement_end_wall, 'config': config,
            'cgroup_initial': initial, 'cgroup_final': final,
            'cgroup_metrics': {'delta': delta, 'elapsed_sec': elapsed,
                'cpu_usage_cores': delta['usage_usec'] / 1e6 / elapsed,
                'throttling_fraction': delta.get('nr_throttled', 0) / delta['nr_periods'] if delta.get('nr_periods') else None},
            'loadgen_metrics': {k: v for k, v in lg.items() if k != 'requests'},
            'monitor_samples': len(samples), 'temperatures_before': thermal,
            'power_before': power_before, 'power_after': power_after,
        }
        report['quality_flags'] = assess(report)
        if power_after != power_before or any(s.get('power_settings') != comparable_power(power_before) for s in samples):
            report['quality_flags'].append('power_settings_changed')
        # Keep under-load temperature/frequency behavior as evidence, not corrected latency.
        report['environment_trace'] = 'monitor.json'
        write_json(run_dir / 'result.json', report)
        print(f'{phase}/{run_id}: p99={lg["end_to_end_latency_summary"]["p99_ms"]:.2f}ms '
              f'cpu={report["cgroup_metrics"]["cpu_usage_cores"]:.3f} '
              f'throttled={delta.get("nr_throttled", 0)} flags={report["quality_flags"]}', flush=True)
        return report
    except BaseException as exc:
        write_json(run_dir / 'failure.json', {'error': str(exc), 'time': time.time()})
        raise
    finally:
        if monitor is not None and monitor.poll() is None:
            monitor.send_signal(signal.SIGINT)
            try:
                monitor.wait(timeout=5)
            except sp.TimeoutExpired:
                monitor.terminate()
                monitor.wait(timeout=5)
        if monitor_log:
            monitor_log.close()
        if created:
            sp.run(['docker', 'rm', '-f', name], stdout=sp.DEVNULL, stderr=sp.DEVNULL)


def config(iterations, rate, period=100000, workers=1, pattern='steady', **extras):
    return dict(iterations=iterations, rate=rate, period_us=period, quota_us=period // 2,
                workers=workers, pattern=pattern, burst_low=rate * .5, burst_high=rate * 1.5, **extras)


def stable_capacity(report):
    lg = report['loadgen_metrics']
    ratio = lg['successful_throughput_rps'] / report['config']['rate']
    drain = lg['elapsed_including_drain_sec'] - report['config']['duration_sec']
    data = json.loads((Path(report['_path']) / 'loadgen.json').read_text())['requests']
    good = sorted((r for r in data if r['StatusCode'] == 200 and not r['Error']), key=lambda r: r['ID'])
    chunk = max(1, len(good) // 4)
    first = statistics.median(r['EndToEndLatencyNs'] for r in good[:chunk]) / 1e6 if good else math.inf
    last = statistics.median(r['EndToEndLatencyNs'] for r in good[-chunk:]) / 1e6 if good else math.inf
    return (not report['quality_flags'] and ratio >= .98 and drain <= .5
            and not (lg['total_errors'] or lg['total_503']) and last - first <= max(5, first * .25))


def calibrate(session):
    # Persistent-connection HTTP timing, followed by actual cgroup CPU accounting.
    iterations = 40000
    probe = trial(session, 'calibration', 'work_probe', config(iterations, 20, period=0), duration=20, warmup=10)
    count = probe['loadgen_metrics']['total_success']
    cpu_per_request = probe['cgroup_metrics']['delta']['usage_usec'] / 1e6 / max(1, count)
    iterations = max(1000, round(iterations * .005 / cpu_per_request / 1000) * 1000)
    refined = trial(session, 'calibration', 'work_refined', config(iterations, 20, period=0), duration=20, warmup=10)
    cpu_per_request = refined['cgroup_metrics']['delta']['usage_usec'] / 1e6 / max(1, refined['loadgen_metrics']['total_success'])
    predicted = .5 / cpu_per_request
    lower = None
    upper = None
    for idx, multiplier in enumerate([.5, .7, .85, 1.0, 1.15, 1.35, 1.6, 2.0]):
        rate = round(predicted * multiplier, 2)
        name = f'capacity_{idx:02d}'
        r = trial(session, 'calibration', name, config(iterations, rate), duration=30, warmup=10)
        r['_path'] = str(session / 'calibration' / name)
        if set(r['quality_flags']) & {'scheduler_late', 'insufficient_monitor_samples', 'power_settings_changed'}:
            raise RuntimeError(f'Calibration load generator or monitor problem: {r["quality_flags"]}')
        if stable_capacity(r):
            lower = rate
        else:
            upper = rate
            break
    if lower is None or upper is None:
        raise RuntimeError('Could not bracket sustainable capacity. Inspect calibration; no fallback rates will be used.')
    for idx in range(3):
        rate = round((lower + upper) / 2, 2)
        name = f'capacity_refine_{idx}'
        r = trial(session, 'calibration', name, config(iterations, rate), duration=30, warmup=10)
        r['_path'] = str(session / 'calibration' / name)
        if set(r['quality_flags']) & {'scheduler_late', 'insufficient_monitor_samples', 'power_settings_changed'}:
            raise RuntimeError(f'Calibration instrumentation problem: {r["quality_flags"]}')
        if stable_capacity(r):
            lower = rate
        else:
            upper = rate
    result = {'iterations': iterations, 'capacity_stable_rps': lower, 'capacity_unstable_rps': upper,
              'moderate_rps': round(lower * .5, 2), 'high_rps': round(lower * .85, 2),
              'reference': '1 worker, 100ms period, 50ms quota; 30s calibration windows',
              'burst_multipliers': [.5, 1.5]}
    write_json(session / 'calibration.json', result)
    return result


def pilot(session, calibration):
    rows = []
    for period in [0, 10000, 100000]:
        for workers in [1, 4]:
            for pattern in ['steady', 'bursty']:
                cfg = config(calibration['iterations'], calibration['high_rps'], period, workers, pattern)
                rows.append(trial(session, 'pilot', f'p{period}_w{workers}_{pattern}', cfg, duration=60, warmup=20))
    checks = {'instrumentation_ok': all(not r['quality_flags'] for r in rows),
              'unlimited_no_own_throttling': all(r['cgroup_metrics']['delta'].get('nr_throttled', 0) == 0 for r in rows if not r['config']['period_us'])}
    # Absence of a predicted effect is an observation, never a reason to reject data.
    write_json(session / 'pilot_checks.json', checks)
    if not all(checks.values()):
        raise RuntimeError('Pilot instrumentation checks failed; inspect pilot_checks.json and raw logs.')


def preflight(session, calibration):
    checks = []
    for period in [10000, 50000, 100000, 250000]:
        cfg = config(calibration['iterations'], calibration['capacity_unstable_rps'] * 1.3, period, workers=4)
        r = trial(session, 'preflight', f'saturation_{period}', cfg, duration=30, warmup=10)
        usage = r['cgroup_metrics']['cpu_usage_cores']
        # Saturation intentionally overloads the service; client queue lag is expected.
        passed = .45 <= usage <= .55 and not (set(r['quality_flags']) & {'scheduler_late', 'insufficient_monitor_samples', 'power_settings_changed'})
        checks.append({'period_us': period, 'cpu_usage_cores': usage, 'passed': passed})
    write_json(session / 'preflight_checks.json', checks)
    if not all(c['passed'] for c in checks):
        raise RuntimeError('Saturation did not verify 0.5 CPU across all periods; inspect preflight.')


def matrix(calibration, seed=42):
    rows = []
    for period in [10000, 50000, 100000, 250000, 0]:
        for workers in [1, 2, 4]:
            for load in ['moderate', 'high']:
                for pattern in ['steady', 'bursty']:
                    for rep in range(1, 6):
                        rate = calibration[f'{load}_rps']
                        rows.append(config(calibration['iterations'], rate, period, workers, pattern,
                                           load=load, trial=rep, run_id=f'p{period}_w{workers}_{load}_{pattern}_r{rep}'))
    random.Random(seed).shuffle(rows)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['new', 'resume'])
    parser.add_argument('--session', type=Path)
    parser.add_argument('--diagnostic', action='store_true', help='Calibration and pilot only; applications may remain open.')
    parser.add_argument('--stop-after', choices=['calibration', 'preflight', 'pilot'], default='pilot', help='Diagnostic sessions only.')
    args = parser.parse_args()
    lock = (ROOT / '.experiment.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit('Another experiment runner holds the lock.')
    if args.action == 'new':
        session = args.session or ROOT / 'results/sessions' / dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        initialize(session, args.diagnostic)
    else:
        if not args.session:
            parser.error('resume requires --session')
        session = args.session.resolve()
        meta = json.loads((session / 'metadata.json').read_text())
        if meta['source_sha256'] != provenance():
            raise SystemExit('Code/binary changed since this session. Start a new session.')
        if meta['image_id'] != capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', IMAGE]):
            raise SystemExit('Container image changed since this session. Start a new session.')
        if meta['diagnostic']:
            raise SystemExit('Diagnostic sessions cannot be resumed into publication data; start a new session.')
    print(f'SESSION: {session}', flush=True)
    try:
        prepare_environment(session)
        if not (session / 'calibration.json').exists():
            cal = calibrate(session)
        else:
            cal = json.loads((session / 'calibration.json').read_text())
        if args.diagnostic and args.stop_after == 'calibration':
            write_json(session / 'status.json', {'state': 'diagnostic_complete', 'stage': 'calibration'})
            return
        if not (session / 'preflight_checks.json').exists():
            preflight(session, cal)
        elif not all(c['passed'] for c in json.loads((session / 'preflight_checks.json').read_text())):
            raise RuntimeError('Previous preflight checks failed; review before starting a new session.')
        if args.diagnostic and args.stop_after == 'preflight':
            write_json(session / 'status.json', {'state': 'diagnostic_complete', 'stage': 'preflight'})
            return
        if not (session / 'pilot_checks.json').exists():
            pilot(session, cal)
        if args.diagnostic:
            write_json(session / 'status.json', {'state': 'diagnostic_complete', 'stage': 'pilot'})
            return
        if not all(json.loads((session / 'pilot_checks.json').read_text()).values()):
            raise RuntimeError('Pilot checks failed.')
        matrix_file = session / 'matrix.json'
        if not matrix_file.exists():
            write_json(matrix_file, matrix(cal))
        rows = json.loads(matrix_file.read_text())
        for index, cfg in enumerate(rows, 1):
            result = session / 'raw' / cfg['run_id'] / 'result.json'
            if result.exists():
                saved = json.loads(result.read_text())
                if saved['quality_flags']:
                    raise RuntimeError(f'Flagged run requires review: {result}')
                continue
            print(f'MATRIX {index}/300', flush=True)
            record = trial(session, 'raw', cfg['run_id'], cfg)
            write_json(session / 'status.json', {'state': 'running', 'completed': index, 'total': 300, 'last_run': cfg['run_id']})
            if record['quality_flags']:
                raise RuntimeError(f'Instrumentation flagged {cfg["run_id"]}; preserved for review.')
        write_json(session / 'status.json', {'state': 'complete', 'completed': 300, 'total': 300})
        command([sys.executable, ROOT / 'analysis/analyze_v2.py', session])
    except BaseException as exc:
        write_json(session / 'status.json', {'state': 'interrupted', 'error': str(exc),
                   'completed': len(list((session / 'raw').glob('*/result.json'))), 'total': 300})
        raise


if __name__ == '__main__':
    main()
