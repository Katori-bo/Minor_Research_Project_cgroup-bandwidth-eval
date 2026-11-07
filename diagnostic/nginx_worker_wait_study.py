#!/usr/bin/env python3
"""External-terminal-only worker boundary/overhead qualification; no prediction."""
import argparse
import gzip
import json
import os
from pathlib import Path
import secrets
import signal
import sys
import time
import traceback
import statistics as st

import nginx_worker_wait_common as c
import nginx_worker_wait_model as m
import nginx_rate_transfer_study as reuse
import nginx_qualify as q
import nginx_power_confirmation_guard as policy
h = q.h


def switches():
    return {'sched_schedstats': Path('/proc/sys/kernel/sched_schedstats').read_text().strip()}


def check_live():
    baseline = c.read(c.BASE / 'policy-baseline.json')
    actual = policy.snapshot(); policy.check_baseline(actual)
    c.require(actual == baseline and switches() == c.read(c.BASE / 'switch-baseline.json'),
              'Fixed policy or scheduler switch changed')
    return dict(policy=actual, switches=switches(), monotonic_ns=time.monotonic_ns(), settings_written=False)


def initialize():
    c.verify_prior()
    old = c.read(q.n.BASE / 'bundle-seal.json')['baseline']
    baseline = h.common.baseline()
    c.require(all(old[k] == baseline[k] for k in ('kernel', 'topology')), 'New kernel/topology needs a separate design')
    actual = policy.snapshot(); policy.check_baseline(actual)
    c.require(switches()['sched_schedstats'] == '0', 'Qualification requires unchanged switch baseline 0')
    config = Path('/proc/config.gz')
    c.require(config.exists() and 'CONFIG_SCHED_INFO=y' in gzip.open(config, 'rt').read().splitlines(),
              'Declared per-task scheduling accounting unavailable')
    log = c.BASE.parent / 'preparation-tests.log'
    c.require(log.exists() and log.read_text().rstrip().endswith('OK'), 'Passing preparation tests required')
    c.BASE.mkdir(parents=True, exist_ok=False)
    c.save(c.BASE / 'protocol.json', c.PROTOCOL)
    c.save(c.BASE / 'schedule.json', c.schedule(secrets.randbits(128)))
    c.save(c.BASE / 'policy-baseline.json', actual)
    c.save(c.BASE / 'switch-baseline.json', switches())
    (c.BASE / 'tests.log').write_text(log.read_text())
    c.save(c.BASE / 'lineage.json', dict(prior_rate_campaign_sha256=c.sha(c.prior.BASE / 'campaign/evidence-seal.json'),
        qualification_only=True, fresh_services_required=True, historical_records_are_not_qualification=True,
        new_collection_started=False, candidate_seal_sha256=c.sha(c.ROOT / 'analysis/runtime_io_worker_wait_candidate/20261010/seal.json')))
    files = c.sources()
    for name in ('protocol.json', 'schedule.json', 'policy-baseline.json', 'switch-baseline.json', 'tests.log', 'lineage.json'):
        path = c.BASE / name; files[str(path.relative_to(c.ROOT))] = c.sha(path)
    c.save(c.BASE / 'preparation-seal.json', dict(baseline=baseline, files_sha256=files))
    c.verify_prepared()


def snapshot(expected):
    pid = expected['pid']
    path = Path(f'/proc/{pid}/task/{pid}')
    started = time.monotonic_ns()
    before = (path / 'stat').read_text()
    raw = (path / 'schedstat').read_text()
    after = (path / 'stat').read_text()
    finished = time.monotonic_ns()
    value = dict(read_started_ns=started, read_finished_ns=finished,
                 stat_before=before, stat_after=after, schedstat_raw=raw,
                 counters=m.w.parse_schedstat(raw))
    m.check_snapshot(value, expected)
    return value


def capture(case, name, expected):
    value = snapshot(expected)
    c.save(case / (name + '.json'), value)
    return value


def trial(case, cfg):
    case.mkdir(); service = None
    c.save(case / 'study-config.json', cfg)
    c.save(case / 'sources-at-start.json', q.n.source_hashes())
    c.save(case / 'worker-wait-sources-at-start.json', c.sources())
    c.save(case / 'trial-start.json', dict(monotonic_ns=time.monotonic_ns()))
    try:
        h.desktop_absent(); c.save(case / 'fixed-before.json', check_live())
        time.sleep(c.PROTOCOL['settling_sec'])
        service = reuse.old.Service(case, True, cfg); service.start()
        reuse.offer_budget(service, cfg, True)
        common_started = time.monotonic_ns()
        initial_status = service.status()
        c.require(q.drained(initial_status), 'Initial service not drained')
        time.sleep(c.PROTOCOL['quiet_sec'])
        scan = service.guard(); c.save(case / 'worker-selection-scan.json', scan)
        worker = m.w.select_worker(scan, service.manifest['nginx_sha256'])
        c.save(case / 'worker-identity.json', worker)
        c.save(case / 'common-boundary-control-cost.json', dict(started_ns=common_started,
            finished_ns=time.monotonic_ns(), includes_initial_status_quiet_and_selection=True,
            shared_by_both_arms=True))
        events = {}; observer = None; operations = []
        warm_before = h.fixtures.stat(service.group); c.save(case / 'warmup-before.json', warm_before)
        if cfg['arm'] == 'on':
            began = time.monotonic_ns()
            b = capture(case, 'worker-before', worker)
            operations.append(dict(started_ns=began, finished_ns=time.monotonic_ns()))
            observer = dict(before=b)
        events['warmup_call_started_ns'] = time.monotonic_ns()
        try:
            service.collect('warmup', 25)
        finally:
            events['warmup_call_finished_ns'] = time.monotonic_ns()
        if observer is not None:
            began = time.monotonic_ns()
            a = capture(case, 'worker-after', worker)
            feature = m.provisional(b, a, worker, 25)
            c.save(case / 'provisional-feature.json', feature)
            operations.append(dict(started_ns=began, finished_ns=time.monotonic_ns()))
            observer['after'] = a
        events['feature_saved_ns'] = time.monotonic_ns()
        warm_after = h.fixtures.stat(service.group)
        c.save(case / 'warmup-counters.json', dict(before=warm_before, after=warm_after,
               delta={k: warm_after[k] - warm_before[k] for k in warm_before}))
        if cfg['role'] == 'boundary':
            time.sleep(c.PROTOCOL['quiet_sec'])
            observer['idle_after'] = capture(case, 'worker-idle-after', worker)
        events['status_started_ns'] = time.monotonic_ns()
        status = service.status()
        events['status_finished_ns'] = time.monotonic_ns()
        c.require(q.drained(status) and status['requests'] - initial_status['requests'] - 1 == 25,
                  'Warmup conservation/control-request exclusion differs')
        c.save(case / 'warmup-request-accounting.json', dict(initial=initial_status, after=status,
            offered=25, control_requests_after_snapshot=1))
        c.save(case / 'threads-before.json', service.guard())
        raw = c.read(case / 'warmup.json'); warm = reuse.m.outcomes(raw, cfg, 'warmup')
        c.require(not reuse.integrity_exits(raw, warm), 'Warmup integrity failure')
        c.save(case / 'fixed-before-measurement.json', check_live())
        reuse.offer_budget(service, cfg, False)
        events['decision_sealed_ns'] = time.monotonic_ns()
        # This is only a boundary receipt; no predictive rule is executed.
        c.save(case / 'decision-boundary.json', dict(monotonic_ns=events['decision_sealed_ns'],
            warmup_only=True, predictive_usefulness_tested=False))
        before = h.fixtures.stat(service.group); c.save(case / 'measurement-before.json', before)
        events['measurement_started_ns'] = time.monotonic_ns()
        c.save(case / 'measurement-start.json', dict(monotonic_ns=events['measurement_started_ns']))
        c.save(case / 'events.json', events)
        if observer is not None:
            observer.update(events=events, operations=operations,
                observer_wall_ns=sum(x['finished_ns'] - x['started_ns'] for x in operations))
        afters = []
        try:
            service.collect('measurement', cfg['count'])
            until = time.monotonic() + 3
            while True:
                afters.append(service.status())
                c.save(case / 'status-window.json', dict(before=status, after_checks=afters))
                if q.drained(afters[-1]): break
                c.require(time.monotonic() < until, 'Target drain timeout')
                time.sleep(.05)
        finally:
            after = h.fixtures.stat(service.group)
            c.save(case / 'measurement-counters.json', dict(before=before, after=after,
                delta={k: after[k] - before[k] for k in before}))
        c.save(case / 'threads-after.json', service.guard())
        c.save(case / 'fixed-after.json', check_live())
        # This replay bundle is assembled later from already saved warmup-only
        # snapshots/features; its write is not part of the proposed live observer.
        if observer is not None: c.save(case / 'observer-evidence.json', observer)
        result = analyze(case, cfg); c.save(case / 'result.json', result)
    except BaseException as exc:
        c.save(case / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        raise
    finally:
        try:
            if service is not None: service.close()
        finally:
            try: c.save(case / 'fixed-final.json', check_live())
            finally: q.evidence_seal(case)
    identity(case, cfg)
    return result


def analyze(case, cfg):
    # Original raw accounting reconstructed with no threshold-based row deletion.
    r = reuse.analyze(case, cfg)
    if any(not x['success'] for x in r['outcomes'] + r['warmup_outcomes']):
        r['domain_exits'].append('qualification_unsuccessful_offers')
    events = c.read(case / 'events.json')
    receipt = c.read(case / 'decision-boundary.json')
    c.require(receipt['monotonic_ns'] == events['decision_sealed_ns'] <=
              events['measurement_started_ns'] and receipt['warmup_only'], 'Decision receipt differs')
    account = c.read(case / 'warmup-request-accounting.json')
    c.require(account['offered'] == 25 and account['after']['requests'] -
              account['initial']['requests'] - 1 == 25 and q.drained(account['after']), 'Warmup accounting differs')
    worker = c.read(case / 'worker-identity.json')
    scan = c.read(case / 'worker-selection-scan.json')
    c.require(m.w.select_worker(scan, worker['exe_sha256']) == worker, 'Worker selection replay differs')
    if cfg['arm'] == 'on':
        evidence = c.read(case / 'observer-evidence.json')
        c.require(evidence['events'] == events and evidence['before'] == c.read(case / 'worker-before.json') and
                  evidence['after'] == c.read(case / 'worker-after.json'), 'Observer evidence differs')
        checks = m.check_boundary(evidence, worker, r['warmup_counter_delta']['usage_usec'])
        c.require(checks['feature'] == c.read(case / 'provisional-feature.json'), 'Provisional feature replay differs')
        if cfg['role'] == 'boundary':
            c.require(evidence['idle_after'] == c.read(case / 'worker-idle-after.json'), 'Idle check differs')
        r['boundary_checks'] = checks
        r['observer_wall_ns'] = evidence['observer_wall_ns']
    else:
        c.require(not list(case.glob('worker-before.json')) and not (case / 'observer-evidence.json').exists(),
                  'Observer-off arm contains sampling')
        r['boundary_checks'] = None; r['observer_wall_ns'] = 0
    successful = [x['e2e_ns'] for x in r['outcomes'] if x['success']]
    warm = [x['e2e_ns'] for x in r['warmup_outcomes'] if x['success']]
    r.update(measurement_miss_pct=100 * reuse.m.miss_fraction(r['outcomes'], c.PROTOCOL['deadline_ns']),
        measurement_mean_ns=st.mean(successful) if successful else None,
        warmup_mean_ns=st.mean(warm) if warm else None, qualification_only=True,
        hardware_qualified=False, predictive_usefulness_tested=False)
    return r


def identity(case, cfg):
    q.identity(case)
    c.require(c.read(case / 'study-config.json') == cfg and
              c.read(case / 'worker-wait-sources-at-start.json') == c.sources(), 'New source/config identity differs')
    for name in ('fixed-before', 'fixed-before-measurement', 'fixed-after', 'fixed-final'):
        value = c.read(case / (name + '.json'))
        c.require(value['policy'] == c.read(c.BASE / 'policy-baseline.json') and
                  value['switches'] == c.read(c.BASE / 'switch-baseline.json') and
                  not value['settings_written'], 'Fixed settings readback differs')


def replay_case(case, cfg):
    c.verify_evidence(case); identity(case, cfg)
    r = analyze(case, cfg)
    c.require(r == c.read(case / 'result.json'), 'Raw qualification replay differs')
    return r


def inventory(directory):
    path = c.ROOT / 'analysis/runtime_io_leftover_observer_audit' / ('nginx-worker-wait-' + str(time.time_ns()) + '.json')
    h.cmd(['sudo', '-n', sys.executable, '-B', str(c.ROOT / 'diagnostic/leftover_observer_audit.py'),
           '--output', str(path)], timeout=60)
    c.require(q.n.prior.observer.review(path)['performance_eligible'], 'Observer inventory ineligible')
    c.save(directory / 'observer-inventory.json', dict(path=str(path), sha256=c.sha(path)))


def run_group(directory, configs, ceiling):
    directory.mkdir(); began = time.monotonic(); rows = []
    try:
        for cfg in configs:
            c.require(time.monotonic() - began + 150 + 120 <= ceiling, 'Phase budget/cleanup reserve exhausted')
            c.verify_prepared(); h.desktop_absent()
            print(f"Worker-wait {cfg['role']} {cfg['index']}: {cfg['arm']} at {cfg['rate_rps']}/s", flush=True)
            case = directory / f"cohort-{cfg['index']}"
            row = trial(case, cfg)
            c.require(replay_case(case, cfg) == row, 'Immediate qualification replay differs')
            rows.append(row)
            c.require(not row['domain_exits'], 'Technical qualification exit: ' + ','.join(row['domain_exits']))
        c.save(directory / 'summary.json', dict(complete=True, rows=rows, elapsed_sec=time.monotonic() - began))
    except BaseException as exc:
        c.save(directory / 'summary.json', dict(complete=False, rows=rows, elapsed_sec=time.monotonic() - began,
            error=str(exc), no_retry=True))
        raise
    finally: q.evidence_seal(directory)
    return rows


def replay():
    sched = c.verify_prepared(False); directory = c.BASE / 'qualification'
    c.verify_evidence(directory)
    ref = c.read(directory / 'observer-inventory.json'); path = Path(ref['path'])
    c.require(c.sha(path) == ref['sha256'] and q.n.prior.observer.review(path)['performance_eligible'], 'Inventory evidence differs')
    for group in ('boundary', 'overhead'):
        c.verify_evidence(directory / group)
        summary = c.read(directory / group / 'summary.json')
        rows = [replay_case(directory / group / f"cohort-{cfg['index']}", cfg) for cfg in sched[group]]
        c.require(summary['complete'] and summary['rows'] == rows and
                  summary['elapsed_sec'] <= c.PROTOCOL[group + '_seconds'] and
                  all(not r['domain_exits'] for r in rows), 'Group summary replay differs')
        if group == 'boundary':
            c.require(any(r['boundary_checks']['feature']['delta']['runnable_wait_ns'] > 0 for r in rows),
                      'No positive wait increment witnessed; availability unqualified')
        else: result = m.compare(rows, sched)
    c.require(result == c.read(directory / 'comparison.json'), 'Paired comparison replay differs')
    summary = c.read(directory / 'summary.json')
    c.require(summary['complete'] and summary['status'] == result['status'] and
              summary['qualified'] == result['qualified'], 'Final qualification receipt differs')
    return result


def all_phases():
    c.require(os.geteuid() != 0 and sys.stdin.isatty(), 'Run as normal user in external terminal')
    sched = c.verify_prepared(); h.desktop_absent(); os.sched_setaffinity(0, {0, 1})
    directory = c.BASE / 'qualification'; directory.mkdir()
    try:
        inventory(directory)
        rows = run_group(directory / 'boundary', sched['boundary'], c.PROTOCOL['boundary_seconds'])
        c.require(any(r['boundary_checks']['feature']['delta']['runnable_wait_ns'] > 0 for r in rows),
                  'No positive wait increment witnessed; stop without overhead collection')
        rows = run_group(directory / 'overhead', sched['overhead'], c.PROTOCOL['overhead_seconds'])
        result = m.compare(rows, sched); c.save(directory / 'comparison.json', result)
        c.save(directory / 'summary.json', dict(complete=True, status=result['status'], qualified=result['qualified'],
            total_offers=7890, discovery_started=False, predictive_usefulness_tested=False))
    except BaseException as exc:
        c.save(directory / 'summary.json', dict(complete=False, status='qualification_stopped',
            error=str(exc), no_retry=True, discovery_started=False))
        raise
    finally: q.evidence_seal(directory)
    replay()
    c.save(c.BASE / 'qualification-result.json', dict(complete=True, status=result['status'],
        qualified=result['qualified'], preparation_sha256=c.sha(c.BASE / 'preparation-seal.json'),
        evidence_sha256=c.sha(directory / 'evidence-seal.json'), predictive_usefulness_tested=False))
    print('Worker-wait qualification completed: ' + result['status'], flush=True)
    print('Results: ' + str(directory / 'comparison.json'), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('initialize', 'verify', 'dry-run', 'all', 'replay'))
    args = parser.parse_args()
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(signum, h.handle_signal)
    if args.phase == 'initialize': initialize()
    elif args.phase == 'verify': c.verify_prepared(); print('Prepared worker-wait qualification verifies; no hardware collection has been performed by this check.')
    elif args.phase == 'dry-run': print(json.dumps(c.verify_prepared(), indent=2))
    elif args.phase == 'all': all_phases()
    else: print(json.dumps(replay(), indent=2))
