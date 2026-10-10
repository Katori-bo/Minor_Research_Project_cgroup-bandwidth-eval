#!/usr/bin/env python3
"""Isolated CPU-quota experiment. Validation and pilot gates precede collection."""
import argparse
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
import subprocess as sp
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import experiment as old
from environment_controls import POLICY, comparable_power, power_settings, window_summary

HERE = ROOT / 'diagnostic'
IMAGE = 'quota-diagnostic-service:2'
CLIENT_IMAGE = 'quota-diagnostic-loadgen:1'
LOADGEN = HERE / 'bin/loadgen'
BUILD = HERE / 'bin/build.json'
ORIGINAL = ROOT / 'results/sessions/20260921-202841'
SCHEMA = 4


def put(path, value):
    old.write_json(path, value)


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(args):
    return old.capture(args)


def get(endpoint):
    with urllib.request.urlopen(f'http://127.0.0.1:{old.PORT}/{endpoint}', timeout=10) as response:
        return json.load(response)


def now():
    return dt.datetime.now().astimezone().isoformat()


def build_sources():
    return sorted(p for name in ('service', 'loadgen') for p in (HERE / name).iterdir()
                  if p.suffix == '.go' or p.name in ('go.mod', 'Dockerfile'))


def hashes(paths):
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def source_files():
    # Imported environment/monitor code is part of the experiment too.
    return sorted(set(build_sources() + list(HERE.glob('*.py')) + list(HERE.glob('*.sh')) +
                      list((HERE / 'analysis').glob('*.py')) +
                      [ROOT / 'scripts' / n for n in ('experiment.py', 'environment_controls.py', 'monitor_host.py')] +
                      [ROOT / 'docs' / 'diagnostic_protocol.md']))


def provenance():
    return hashes(source_files() + [LOADGEN, BUILD])


def image_id(image=IMAGE):
    return capture(['docker', 'image', 'inspect', '--format', '{{.Id}}', image])


def seal_build():
    put(BUILD, {'schema': SCHEMA, 'sources': hashes(build_sources()),
                'loadgen_sha256': sha(LOADGEN), 'image_id': image_id(),
                'client_image_id': image_id(CLIENT_IMAGE), 'built_at': now(),
                'compiler_image_id': image_id('golang:1.26.1-alpine')})


def verify_build():
    if not BUILD.exists() or not LOADGEN.exists():
        raise RuntimeError('Run ./diagnostic/build.sh first; build manifest is missing.')
    build = read(BUILD)
    if build['schema'] != SCHEMA or build['sources'] != hashes(build_sources()) or build['loadgen_sha256'] != sha(LOADGEN):
        raise RuntimeError('Binaries do not match source. Run ./diagnostic/build.sh.')
    if build['image_id'] != image_id() or build['client_image_id'] != image_id(CLIENT_IMAGE):
        raise RuntimeError('Diagnostic image changed. Run ./diagnostic/build.sh.')
    return build


def matrix():
    cal = read(ORIGINAL / 'calibration.json')
    rows = []
    rate = cal['high_rps']
    for period in (100000, 250000):
        for workers in (1, 4):
            gomaxprocs, pattern, study = 2, 'bursty', 'D'
            for rep in range(1, 6):
                rows.append(dict(study=study, period_us=period, quota_us=period // 2,
                    workers=workers, gomaxprocs=gomaxprocs, pattern=pattern, rate=rate,
                    burst_low=rate * .5, burst_high=rate * 1.5, iterations=cal['iterations'],
                    rep=rep, instrument=True, duration_sec=60, warmup_sec=20, timeout_sec=5,
                    client_trace=True,
                    run_id=f'{study}_p{period}_w{workers}_g{gomaxprocs}_{pattern}_r{rep}'))
    random.Random(20260928).shuffle(rows)
    return rows


def pilot_matrix():
    rows = matrix()
    def find(period, workers):
        return next(c for c in rows if (c['period_us'], c['workers']) == (period, workers))
    base = find(100000, 4)
    pilot = [dict(base, run_id=f'pilot_overhead_{i + 1}', instrument=enabled, client_trace=enabled)
             for i, enabled in enumerate((True, False, False, True))]
    pilot += [dict(find(100000, 1), run_id='pilot_p100000_w1_on', instrument=True, client_trace=True),
              dict(find(100000, 1), run_id='pilot_p100000_w1_off', instrument=False, client_trace=False)]
    return [dict(c, duration_sec=20, warmup_sec=10) for c in pilot]


def create(session, pilot, build, pilot_session=None):
    # Resolve everything that can fail before making the immutable session directory.
    meta = {'schema': SCHEMA, 'created': now(), 'pilot': pilot,
            'source_sha256': provenance(), 'build': build, 'topology': old.check_topology(),
            'server_cpus': old.CPUS, 'client_cpus': old.CLIENT_CPUS,
            'kernel': capture(['uname', '-a']), 'docker_version': capture(['docker', 'version']),
            'python': sys.version, 'source_session': str(ORIGINAL),
            'source_calibration_sha256': sha(ORIGINAL / 'calibration.json'),
            'power_settings': power_settings(include_profile=True)}
    if pilot_session:
        meta['pilot_session'] = str(pilot_session)
        meta['pilot_gate_sha256'] = sha(pilot_session / 'analysis/pilot_gate.json')
    session.mkdir(parents=True, exist_ok=False)
    (session / 'attempts').mkdir()
    put(session / 'matrix.json', pilot_matrix() if pilot else matrix())
    meta['matrix_sha256'] = sha(session / 'matrix.json')
    put(session / 'metadata.json', meta)
    for path in source_files():
        target = session / 'source' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copy2(BUILD, session / 'build.json')
    shutil.copy2(ORIGINAL / 'calibration.json', session / 'original_calibration.json')


def attempt_dirs(base):
    return sorted((p for p in base.iterdir() if p.is_dir() and p.name.isdigit()), key=lambda p: int(p.name)) if base.exists() else []


def next_attempt(base):
    return max((int(p.name) for p in attempt_dirs(base)), default=0) + 1


def quality_flags(lg, samples, before, after, duration):
    flags = []
    if lg['client_dropped'] or lg['missed_arrivals'] or lg['dispatch_lag_summary']['p99_ms'] > 2:
        flags.append('loadgen_late_or_dropped')
    if len(samples) < max(1, math.ceil(duration * .7)):
        flags.append('monitor_coverage')
    if before != after or any(s.get('power_settings') != comparable_power(before) for s in samples):
        flags.append('power_changed')
    if any(not s.get('temps_c') or not s.get('cgroup_cpu_stat') for s in samples):
        flags.append('missing_monitor_sensor_or_cgroup')
    return flags


def response_event_valid(handler, worker):
    """Check server-local evidence, including writes whose clients failed.

    A write error is an outcome; it is not a reason to discard a trial. Client
    completion can precede the exit marker, so no cross-process nesting is assumed.
    """
    try:
        times = [handler[k] for k in ('entry_ns', 'admission_ns', 'resume_ns',
                                     'write_start_ns', 'write_end_ns', 'handler_exit_ns')]
        return (all(type(t) is int and t >= 0 for t in times) and times == sorted(times) and
                handler['id'] == worker['id'] and handler['admission_ns'] == worker['admission_ns'] and
                handler['resume_ns'] >= worker['completion_ns'] and
                handler['pre_admission_ns'] == handler['admission_ns'] - handler['entry_ns'] and
                handler['post_work_wait_ns'] == handler['resume_ns'] - worker['completion_ns'] and
                handler['write_calls'] == 1 and type(handler['write_bytes']) is int and
                handler['write_bytes'] >= 0 and isinstance(handler['write_error'], str))
    except (KeyError, TypeError):
        return False


def check_content(d, config, pilot):
    """Recompute acceptance from raw evidence, rather than trust result.json flags."""
    errors = []
    def check(ok, message):
        if not ok:
            errors.append(message)
    try:
        r, lg, srv, settling, samples, limits = [read(d / n) for n in
            ('result.json', 'loadgen.json', 'server_metrics.json', 'settling.json', 'monitor.json', 'limits.json')]
        env = read(d.parents[2] / 'environment.json')
        check(read(d / 'config.json') == config == r['config'], 'config mismatch')
        check(r['run_id'] == config['run_id'], 'run ID mismatch')
        check(lg['duration_sec'] == config['duration_sec'] and lg['pattern'] == config['pattern'] and
              lg['target_rate'] == config['rate'] and
              lg['client_trace_enabled'] == config['client_trace'], 'arrival/trace configuration mismatch')
        check(lg['client_cpu_usec'] >= 0, 'client CPU accounting unavailable')
        if config['pattern'] == 'bursty':
            check(lg['burst_low_rate'] == config['burst_low'] and lg['burst_high_rate'] == config['burst_high'] and
                  lg['burst_period_sec'] == 10, 'burst configuration mismatch')
        req = lg['requests']
        check(len(req) == lg['total_dispatched'] == lg['total_completed'], 'client completed count')
        check(lg['total_scheduled'] == lg['total_dispatched'] + lg['client_dropped'], 'scheduled count')
        check(lg['total_scheduled'] == math.ceil(config['rate'] * config['duration_sec']), 'wrong offered count')
        ids = {q['ID'] for q in req}
        check(len(ids) == len(req) and ids == set(range(lg['total_scheduled'])), 'request IDs')
        good = [q for q in req if q['StatusCode'] == 200 and not q['Error']]
        rejected = [q for q in req if q['StatusCode'] == 503 and not q['Error']]
        check(len(good) == lg['total_success'] and len(rejected) == lg['total_503'] and
              len(req) - len(good) - len(rejected) == lg['total_errors'], 'outcome accounting')
        for q in req:
            check(q['DispatchLagNs'] >= 0 and q['ServiceLatencyNs'] >= 0 and
                  q['EndToEndLatencyNs'] >= q['ServiceLatencyNs'] and
                  q['CompletedOffsetNs'] == q['ScheduledOffsetNs'] + q['EndToEndLatencyNs'], 'client timing')
            check(not q['ServerTimingError'], 'malformed server timing header')
        check(srv['admitted'] + srv['rejected'] <= lg['total_dispatched'] and
              srv['admitted'] >= len(good) and srv['rejected'] >= len(rejected), 'server/client accounting')
        check(srv['completed'] == srv['admitted'] and srv['queue_len'] == srv['active_handlers'] == 0,
              'undrained work or handlers')
        if config['instrument']:
            events = {e['id']: e for e in srv['events']}
            handler_events = {e['id']: e for e in srv['handler_events']}
            check(len(events) == len(srv['events']) == srv['completed'] and set(events) <= ids, 'server event IDs/count')
            check(len(handler_events) == len(srv['handler_events']) and set(handler_events) <= set(events),
                  'handler event IDs/count')
            for h in handler_events.values():
                check(response_event_valid(h, events.get(h['id'])), 'response write event invalid')
            for e in events.values():
                check(0 <= e['admission_ns'] <= e['worker_start_ns'] < e['completion_ns'] and
                      e['queue_wait_ns'] == e['worker_start_ns'] - e['admission_ns'] and
                      e['processing_ns'] == e['completion_ns'] - e['worker_start_ns'], 'server event timing')
            check(sum(e['client_gone_at_completion'] for e in events.values()) == srv['client_gone_at_completion'],
                  'post-timeout completion accounting')
            for q in good:
                e = events.get(q['ID'])
                h = handler_events.get(q['ID'])
                check(q['ServerTimingPresent'] and e is not None and
                      (e['queue_wait_ns'], e['processing_ns'], e['depth_at_admission']) ==
                      (q['QueueWaitNs'], q['ProcessingNs'], q['QueueDepth']), 'header/event mismatch')
                check(h is not None and e is not None and
                      h['entry_ns'] <= h['admission_ns'] == e['admission_ns'] and
                      h['resume_ns'] >= e['completion_ns'] and
                      h['pre_admission_ns'] == h['admission_ns'] - h['entry_ns'] == q['PreAdmissionNs'] and
                      h['post_work_wait_ns'] == h['resume_ns'] - e['completion_ns'] == q['PostWorkWaitNs'],
                      'handler/event mismatch')
                check(q['PreAdmissionNs'] >= 0 and q['PostWorkWaitNs'] >= 0 and
                      q['BodyDoneOffsetNs'] >= q['HeadersOffsetNs'] and
                      q['ServiceLatencyNs'] == q['BodyDoneOffsetNs'] and
                      q['EndToEndLatencyNs'] >= q['QueueWaitNs'] + q['ProcessingNs'] +
                      q['PreAdmissionNs'] + q['PostWorkWaitNs'], 'diagnostic timing invalid')
                check(q['TraceIssue'] in ('', 'missing_callback', 'write_callback_after_first_byte',
                      'multiple_request_writes') and
                      q['TraceIssue'] != 'disabled' and
                      (q['WroteRequestOffsetNs'] < 0 or q['FirstByteOffsetNs'] < 0 or
                       q['WroteRequestOffsetNs'] <= q['FirstByteOffsetNs']),
                      'unclassified client trace event')
        else:
            check(not srv['events'] and not srv['handler_events'] and
                  not any(q['ServerTimingPresent'] for q in good) and
                  all(q['TraceIssue'] == 'disabled' for q in good), 'instrumentation was not off')
        for runtime in (r['runtime'], r['runtime_end'], srv):
            check((runtime['workers'], runtime['gomaxprocs'], runtime['queue_cap'], runtime['instrument']) ==
                  (config['workers'], config['gomaxprocs'], 128, config['instrument']), 'runtime mismatch')
            check(runtime['go_version'] == 'go1.26.1', 'unexpected Go runtime')
        check(limits == r['limits'], 'limits file mismatch')
        own = limits[r['cgroup_path']]
        check(own['cpu.max'] == f"{config['quota_us']} {config['period_us']}" and
              own['cpu.max.burst'] == '0' and own['cpuset.cpus.effective'] == old.CPUS, 'quota/affinity mismatch')
        check(all(v.get('cpu.max', '').startswith('max ') for k, v in limits.items() if k != r['cgroup_path']), 'ancestor cap')
        check(settling['accepted'] and settling['policy'] == POLICY, 'settling policy')
        thermal_samples = settling['samples']
        boundary = thermal_samples[-1]['elapsed_sec'] - POLICY['window_sec']
        index = 0
        while index + 1 < len(thermal_samples) and thermal_samples[index + 1]['elapsed_sec'] <= boundary:
            index += 1
        summary = window_summary(thermal_samples[index:], env['baseline_c'])
        check(summary is not None and summary['stable'], 'thermal window not accepted')
        check(all(s['power_settings'] == comparable_power(env['power_settings']) for s in thermal_samples), 'settling power changed')
        check(r['power_before'] == env['power_settings'], 'baseline power mismatch')
        flags = quality_flags(lg, samples, r['power_before'], r['power_after'], config['duration_sec'])
        check(not flags and not r['quality_flags'] and r['monitor_samples'] == len(samples), 'quality flags: ' + ','.join(flags))
        check(all(r['cgroup_delta'][k] == v - r['cgroup_initial'].get(k, 0) and r['cgroup_delta'][k] >= 0
                  for k, v in r['cgroup_final'].items()), 'cgroup counter delta')
        check(r['elapsed_sec'] > 0 and abs(r['cpu_usage_cores'] - r['cgroup_delta']['usage_usec'] / 1e6 / r['elapsed_sec']) < 1e-12,
              'CPU usage summary mismatch')
    except (ValueError, KeyError, IndexError, TypeError, StopIteration, OSError, ZeroDivisionError) as exc:
        errors.append(f'missing or malformed evidence: {exc}')
    return sorted(set(errors))


def complete_attempt(d):
    put(d / 'complete.json', {'schema': SCHEMA, 'files': {p.name: sha(p) for p in sorted(d.iterdir())
         if p.is_file() and p.name != 'complete.json'}, 'completed_at': now()})


def validation_errors(d, config, pilot):
    if (d / 'failure.json').exists():
        return ['failed attempt']
    try:
        seal = read(d / 'complete.json')
        actual = {p.name: sha(p) for p in d.iterdir() if p.is_file() and p.name != 'complete.json'}
        if seal['schema'] != SCHEMA or seal['files'] != actual:
            return ['attempt file hashes changed']
    except (OSError, ValueError, KeyError):
        return ['missing or invalid completion marker']
    return check_content(d, config, pilot)


def validate(d, config, pilot):
    return not validation_errors(d, config, pilot)


def drain(timeout=30):
    end = time.monotonic() + timeout
    while True:
        state = get('health')
        if state['admitted'] == state['completed'] and state['queue_len'] == state['active_handlers'] == 0:
            return state
        if time.monotonic() >= end:
            raise RuntimeError('Service drain timed out; logs and partial metrics will be preserved')
        time.sleep(.1)


def run_client(config, seconds, output):
    args = ['taskset', '-c', old.CLIENT_CPUS, str(LOADGEN), '-url',
            f'http://127.0.0.1:{old.PORT}/work?iterations={config["iterations"]}',
            '-duration', f'{seconds}s', '-pattern', config['pattern'], '-rate', str(config['rate']),
            '-concurrency', '512', '-timeout', f'{config["timeout_sec"]}s',
            f'-trace-client={str(config["client_trace"]).lower()}', '-output', str(output)]
    if config['pattern'] == 'bursty':
        args += ['-burst-low', str(config['burst_low']), '-burst-high', str(config['burst_high']), '-burst-period', '10s']
    with output.with_suffix('.log').open('w') as log:
        process = sp.Popen(args, stdout=log, stderr=sp.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=seconds + 40)
            if code:
                raise RuntimeError(f'Load generator exited {code}')
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)


def run_attempt(session, config, pilot, number):
    base = session / 'attempts' / config['run_id']
    base.mkdir(parents=True, exist_ok=True)
    d = base / f'{number:03d}'
    d.mkdir(exist_ok=False)
    put(d / 'config.json', config)
    put(d / 'started.json', {'at': now(), 'runner_pid': os.getpid()})
    name = 'quota-diagnostic-' + hashlib.sha256(str(d).encode()).hexdigest()[:16]
    container = None
    monitor = None
    monitor_log = None
    try:
        env = read(session / 'environment.json')
        before = power_settings(include_profile=True)
        if before != env['power_settings']:
            raise RuntimeError('Power settings changed from baseline')
        thermal = old.settle(d / 'settling.json', env['baseline_c'], expected_power=before)
        args = ['docker', 'create', '--name', name, '--label', f'quota.diagnostic.session={session}',
                f'--cpuset-cpus={old.CPUS}', f'--cpu-period={config["period_us"]}', f'--cpu-quota={config["quota_us"]}',
                '-e', f'WORKERS={config["workers"]}', '-e', 'QUEUE_SIZE=128', '-e', f'GOMAXPROCS={config["gomaxprocs"]}',
                '-e', f'INSTRUMENT={int(config["instrument"])}', '-p', f'127.0.0.1:{old.PORT}:8080', IMAGE]
        container = capture(args)
        put(d / 'container.json', {'id': container, 'name': name, 'command': args})
        capture(['docker', 'start', container])
        for _ in range(50):
            try:
                health = get('health')
                break
            except OSError:
                time.sleep(.2)
        else:
            raise RuntimeError('Health timeout')
        if (health['workers'], health['gomaxprocs'], health['queue_cap'], health['instrument']) != (
                config['workers'], config['gomaxprocs'], 128, config['instrument']):
            raise RuntimeError('Runtime mismatch')
        pid = int(capture(['docker', 'inspect', '--format', '{{.State.Pid}}', container]))
        cg = old.cgroup_path(pid)
        limits = old.verify_limits(cg, config['period_us'], config['quota_us'])
        if limits[str(cg)]['cpuset.cpus.effective'] != old.CPUS:
            raise RuntimeError('Effective CPU affinity differs from protocol')
        put(d / 'limits.json', limits)
        run_client(config, config['warmup_sec'], d / 'warmup.json')
        drain()
        put(d / 'warmup_server_metrics.json', get('metrics'))
        request = urllib.request.Request(f'http://127.0.0.1:{old.PORT}/reset', method='POST')
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 204:
                raise RuntimeError('Metric reset failed')
        if power_settings(include_profile=True) != before:
            raise RuntimeError('Power changed during warmup')
        monitor_log = (d / 'monitor.log').open('w')
        monitor = sp.Popen(['taskset', '-c', old.CLIENT_CPUS, sys.executable, str(ROOT / 'scripts/monitor_host.py'),
            '--cgroup-path', '/' + str(cg.relative_to('/sys/fs/cgroup')), '--output', str(d / 'monitor.json')],
            stdout=monitor_log, stderr=sp.STDOUT, start_new_session=True)
        initial = old.read_stat(cg / 'cpu.stat')
        measurement_start = now()
        start = time.monotonic()
        run_client(config, config['duration_sec'], d / 'loadgen.json')
        client_end = old.read_stat(cg / 'cpu.stat')
        runtime_end = drain()
        final = old.read_stat(cg / 'cpu.stat')
        elapsed = time.monotonic() - start
        measurement_end = now()
        srv = get('metrics')
        put(d / 'server_metrics.json', srv)
        monitor.send_signal(signal.SIGINT)
        if monitor.wait(timeout=10) != 0:
            raise RuntimeError('Host monitor failed')
        monitor = None
        after = power_settings(include_profile=True)
        samples, lg = read(d / 'monitor.json'), read(d / 'loadgen.json')
        flags = quality_flags(lg, samples, before, after, config['duration_sec'])
        delta = {k: final[k] - initial.get(k, 0) for k in final}
        report = {'run_id': config['run_id'], 'config': config, 'limits': limits, 'cgroup_path': str(cg),
                  'runtime': health, 'runtime_end': runtime_end, 'cgroup_initial': initial, 'cgroup_client_end': client_end,
                  'cgroup_final': final, 'cgroup_delta': delta, 'elapsed_sec': elapsed,
                  'cpu_usage_cores': delta['usage_usec'] / 1e6 / elapsed,
                  'throttling_fraction': delta['nr_throttled'] / delta['nr_periods'] if delta.get('nr_periods') else None,
                  'quality_flags': flags, 'power_before': before, 'power_after': after, 'thermal': thermal,
                  'monitor_samples': len(samples), 'server_unseen_dispatched': lg['total_dispatched'] - srv['admitted'] - srv['rejected'],
                  'measurement_started_at': measurement_start, 'measurement_ended_at': measurement_end}
        put(d / 'result.json', report)
        errors = check_content(d, config, pilot)
        if errors:
            raise RuntimeError('; '.join(errors))
    except BaseException as exc:
        put(d / 'failure.json', {'error': str(exc) or type(exc).__name__, 'at': now()})
        if container:
            try:
                put(d / 'partial_server_metrics.json', get('metrics'))
            except Exception:
                pass
        raise
    finally:
        if monitor and monitor.poll() is None:
            monitor.send_signal(signal.SIGINT)
            try:
                monitor.wait(timeout=5)
            except sp.TimeoutExpired:
                monitor.terminate()
                monitor.wait(timeout=5)
        if monitor_log:
            monitor_log.close()
        if container:
            with (d / 'server.log').open('w') as log:
                sp.run(['docker', 'logs', container], stdout=log, stderr=sp.STDOUT)
            sp.run(['docker', 'rm', '-f', container], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    complete_attempt(d)
    return d


def verify_session(session, check_current=True):
    meta = read(session / 'metadata.json')
    if meta['schema'] != SCHEMA or sha(session / 'matrix.json') != meta['matrix_sha256']:
        raise RuntimeError('Session schema or frozen collection order changed')
    expected = pilot_matrix() if meta['pilot'] else matrix()
    if read(session / 'matrix.json') != expected:
        raise RuntimeError('Session matrix differs from frozen protocol')
    if check_current and meta['source_sha256'] != provenance():
        raise RuntimeError('Source, binary, protocol or dependency changed; start a new session')
    if sha(ORIGINAL / 'calibration.json') != meta['source_calibration_sha256']:
        raise RuntimeError('Original calibration changed')
    return meta


def require_pilot(session):
    meta = verify_session(session)
    gate = read(session / 'analysis/pilot_gate.json')
    if not meta['pilot'] or not gate['passed']:
        raise RuntimeError('Pilot has not passed its validation gate')
    for config in read(session / 'matrix.json'):
        good = [p for p in attempt_dirs(session / 'attempts' / config['run_id']) if validate(p, config, True)]
        if len(good) != 1 or gate['completion_sha256'].get(config['run_id']) != sha(good[0] / 'complete.json'):
            raise RuntimeError('Pilot evidence no longer matches its gate')


def acquire_experiment_lock(path=None):
    """Allow the all-stage coordinator to retain the same lock across child runners."""
    path = path or ROOT / '.experiment.lock'
    inherited = os.environ.get('CPU_QUOTA_EXPERIMENT_LOCK_FD')
    if inherited is None:
        lock = path.open('a')
    else:
        descriptor = int(inherited)
        actual, expected = os.fstat(descriptor), path.stat()
        if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
            raise RuntimeError('Inherited experiment lock belongs to a different file')
        lock = os.fdopen(os.dup(descriptor), 'a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        lock.close()
        raise
    return lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['new', 'resume', 'seal-build'])
    parser.add_argument('--session', type=Path)
    parser.add_argument('--pilot', action='store_true')
    parser.add_argument('--pilot-session', type=Path, help='Passed pilot required for a new full session')
    args = parser.parse_args()
    if args.action == 'seal-build':
        seal_build()
        return
    if args.action == 'resume' and not args.session:
        parser.error('resume requires --session')
    if args.action == 'new' and not args.pilot and not args.pilot_session:
        parser.error('full collection requires --pilot-session after the pilot passes analysis')
    # Share the existing runner lock so original and follow-up cannot contend for the same host/port.
    try:
        lock = acquire_experiment_lock()
    except BlockingIOError:
        raise SystemExit('Another experiment is running')
    def stop(signum, frame):
        raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM, stop)
    build = verify_build()
    session = (args.session or ROOT / 'results/diagnostic' / dt.datetime.now().strftime('%Y%m%d-%H%M%S')).resolve()
    if not session.is_relative_to(ROOT / 'results/diagnostic') or session == ROOT / 'results/diagnostic':
        parser.error('session must be a new subdirectory of results/diagnostic')
    if args.action == 'new':
        pilot_session = args.pilot_session.resolve() if args.pilot_session else None
        if not args.pilot:
            require_pilot(pilot_session)
        create(session, args.pilot, build, pilot_session)
    meta = verify_session(session)
    if meta['build']['image_id'] != build['image_id'] or old.check_topology() != meta['topology']:
        raise RuntimeError('Container image or CPU topology changed')
    # A SIGKILL/power loss can leave an owned container. Refuse to overlap it.
    orphan = capture(['docker', 'ps', '-a', '-q', '--filter', f'label=quota.diagnostic.session={session}'])
    if orphan:
        raise RuntimeError(f'Prior owned container(s) remain: {orphan}. Inspect and remove these before resuming.')
    print('SESSION:', session, flush=True)
    rows = read(session / 'matrix.json')
    pending = []
    for config in rows:
        dirs = attempt_dirs(session / 'attempts' / config['run_id'])
        good = [p for p in dirs if validate(p, config, meta['pilot'])]
        if len(good) > 1:
            raise RuntimeError('Multiple valid attempts for ' + config['run_id'])
        if not good:
            pending.append(config)
    if not pending:
        print('All trials already validate; no workload launched.', flush=True)
        return
    completed = len(rows) - len(pending)
    try:
        old.prepare_environment(session)
        for config in pending:
            print(f'RUN {completed + 1}/{len(rows)} {config["run_id"]}', flush=True)
            d = run_attempt(session, config, meta['pilot'], next_attempt(session / 'attempts' / config['run_id']))
            completed += 1
            put(session / 'status.json', {'completed': completed, 'total': len(rows), 'last': str(d), 'state': 'running'})
        put(session / 'status.json', {'completed': completed, 'total': len(rows), 'state': 'complete'})
    except BaseException as exc:
        put(session / 'status.json', {'completed': completed, 'total': len(rows), 'state': 'interrupted',
                                     'error': str(exc) or type(exc).__name__})
        raise


if __name__ == '__main__':
    main()
