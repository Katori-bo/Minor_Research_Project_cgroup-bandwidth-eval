#!/usr/bin/env python3
"""Qualify once, freeze fresh calibration, collect once, and replay every record."""
import argparse
import json
import math
import os
from pathlib import Path
import secrets
import signal
import statistics as st
import sys
import time
import traceback

import nginx_rate_transfer_common as c
import nginx_rate_transfer_model as m
import nginx_prediction_study as old
import nginx_qualify as q
h = q.h


class FixedPolicy:
    """Read-only P0 checks. No privileged helper and no host policy mutation."""
    def __init__(self, directory):
        self.directory = directory
        self.original = c.read(c.BASE / 'policy-baseline.json')
        self.check()

    def check(self):
        import nginx_power_confirmation_guard as guard
        value = guard.snapshot(); guard.check_baseline(value)
        c.require(value == self.original, 'Fixed P0/full policy baseline changed')
        return dict(policy='P0', snapshot=value, monotonic=time.monotonic(), host_policy_writes=False)

    def set(self, policy):
        c.require(policy == 'P0', 'Only fixed P0 is allowed')
        return self.check()

    def close(self):
        try:
            c.save(self.directory / 'policy-final-check.json', self.check())
        except BaseException as exc:
            c.save(self.directory / 'policy-final-error.json', dict(error=str(exc), host_policy_writes=False))
            raise


def offer_budget(service, cfg, include_warmup):
    spans = (cfg['count'] - 1) * cfg['interval_ns'] / 1e9
    if include_warmup: spans += (cfg['warmup_count'] - 1) * cfg['interval_ns'] / 1e9
    c.require(time.monotonic() - service.started + spans + c.PROTOCOL['within_service_reserve_sec'] <
              c.PROTOCOL['service_active_sec'], 'Nominal offer schedule and reserve exceed remaining service lifetime')


def sibling_context():
    # Boundary context only: this is not a scheduler trace or exclusive-CPU proof.
    line = next(x for x in Path('/proc/stat').read_text().splitlines() if x.startswith('cpu3 '))
    return dict(cpu3_proc_stat=line, monotonic=time.monotonic(),
                siblings=Path('/sys/devices/system/cpu/cpu2/topology/thread_siblings_list').read_text().strip())


def integrity_exits(client, records):
    # Non-200 and incomplete transport responses are misses. Only a complete
    # HTTP-200 claiming our output can invalidate the integrity contract.
    return ['response_integrity'] if any(not o['success'] and r['Status'] == 200 and
        (not r['Error'] or r['Error'] == 'response exceeds body cap')
        for o, r in zip(records, client['Rows'])) else []


def counter_delta(case, prefix):
    counters = c.read(case / (prefix + '-counters.json'))
    delta = {k: counters['after'][k] - counters['before'][k] for k in counters['before']}
    c.require(delta == counters['delta'] and all(v >= 0 for v in delta.values()) and
        c.read(case / (prefix + '-before.json')) == counters['before'], 'Counter accounting differs')
    return delta


def analyze(case, cfg):
    warm = m.outcomes(c.read(case / 'warmup.json'), cfg, 'warmup')
    records = m.outcomes(c.read(case / 'measurement.json'), cfg)
    delta = counter_delta(case, 'measurement')
    warm_delta = counter_delta(case, 'warmup')
    window = c.read(case / 'status-window.json'); before = window['before']; afters = window['after_checks']
    c.require(afters and q.drained(before) and q.drained(afters[-1]), 'Request drain differs')
    c.require(all(a['requests'] <= b['requests'] for a, b in zip([before, *afters], afters)),
              'Status counters reversed')
    served = afters[-1]['requests'] - before['requests'] - len(afters)
    c.require(sum(o['response_headers_observed'] for o in records) <= served <=
              sum(not o['dropped'] for o in records), 'Stock request conservation failed')
    lag = sorted(o['dispatch_lag_ns'] for o in records if not o['dropped'])
    raw = c.read(case / 'measurement.json')['Rows']; timeline = []
    for r in raw:
        if r['BodyDoneNs'] >= r['DispatchNs'] and r['Status'] > 0:
            timeline.extend([(r['DispatchNs'], 1), (r['BodyDoneNs'], -1)])
    active = maximum = 0
    for _, change in sorted(timeline):
        active += change; maximum = max(maximum, active)
    observations = []
    if delta['nr_throttled'] or delta['throttled_usec']: observations.append('measurement_throttling')
    if warm_delta['nr_throttled'] or warm_delta['throttled_usec']: observations.append('warmup_throttling')
    if maximum > 1: observations.append('client_response_overlap')
    if any(o['dropped'] for o in records): observations.append('client_inflight_cap')
    if not lag or lag[math.ceil(.99 * len(lag)) - 1] > 2000000 or max(lag) > 10000000:
        observations.append('dispatch_gate')
    if not all(o['success'] for o in [*records, *warm]): observations.append('unsuccessful_offers')
    exits = sorted(set(integrity_exits(c.read(case / 'measurement.json'), records) +
                       integrity_exits(c.read(case / 'warmup.json'), warm)))
    timing = [o['e2e_ns'] for o in records if o['success']]
    stages = {key: st.mean(r[b] - r[a] for r, o in zip(raw, records) if o['success'])
              if timing else None for key, a, b in [('dispatch_ns', 'ScheduledNs', 'DispatchNs'),
                ('headers_ns', 'DispatchNs', 'HeadersNs'), ('body_ns', 'HeadersNs', 'BodyDoneNs')]}
    return dict(config=cfg, outcomes=records, warmup_outcomes=warm, offers=len(records),
        successful=sum(o['success'] for o in records), domain_exits=exits,
        observations=observations, warmup_counter_delta=warm_delta,
        unsuccessful_counts=dict(measurement=sum(not o['success'] for o in records),
                                 warmup=sum(not o['success'] for o in warm)),
        failure_categories={prefix: dict(client_cap_drops=sum(o['dropped'] for o in obs),
            transport_errors=sum(bool(r['Error']) and not o['dropped'] for r, o in zip(client['Rows'], obs)),
            non200_responses=sum(r['Status'] > 0 and r['Status'] != 200 for r in client['Rows']))
            for prefix, client, obs in [('measurement', c.read(case / 'measurement.json'), records),
                                        ('warmup', c.read(case / 'warmup.json'), warm)]},
        measurement_counter_delta=delta, cpu_per_offer_us=delta['usage_usec'] / len(records),
        maximum_client_response_overlap=maximum, mean_stages_ns=stages,
        response_ns=dict(mean=st.mean(timing), median=st.median(timing),
            p99=sorted(timing)[math.ceil(.99 * len(timing)) - 1]) if timing else None,
        queue_observed=False)


def identity(case, cfg):
    q.identity(case)
    c.require(c.read(case / 'rate-sources-at-start.json') == c.sources(), 'Rate-transfer source identity differs')
    c.require(c.read(case / 'study-config.json') == cfg, 'Rate-transfer cohort configuration differs')
    baseline = c.read(c.BASE / 'policy-baseline.json')
    from nginx_power_confirmation_guard import check_baseline
    check_baseline(baseline)
    final = c.read(case / 'policy-final-check.json')
    c.require(final['snapshot'] == baseline and final['policy'] == 'P0' and
              not final['host_policy_writes'], 'Final unchanged P0 baseline differs')
    for phase in ('before-settling', 'before-warmup', 'before-measurement', 'after-measurement'):
        value = c.read(case / ('policy-' + phase + '.json'))
        c.require(value['policy'] == cfg['policy'] and
                  value['snapshot'] == baseline and not value['host_policy_writes'], 'Policy phase readback differs')
    before = c.read(case / 'policy-before-measurement.json')['monotonic']
    after = c.read(case / 'policy-after-measurement.json')['monotonic']
    c.require(before <= c.read(case / 'measurement-start.json')['monotonic'] <= after,
              'Policy/measurement boundaries differ')
    c.require(after <= final['monotonic'], 'Final policy check preceded measurement completion')


def trial(case, cfg, forecast=None, forecast_ref=None):
    case.mkdir(); policy = service = None
    c.save(case / 'study-config.json', cfg)
    c.save(case / 'sources-at-start.json', c.old.n.source_hashes())
    c.save(case / 'rate-sources-at-start.json', c.sources())
    c.save(case / 'trial-start.json', dict(monotonic=time.monotonic(), forecast_ref=forecast_ref))
    try:
        h.desktop_absent()
        policy = FixedPolicy(case)
        c.save(case / 'policy-before-settling.json', policy.set(cfg['policy']))
        time.sleep(10)
        service = old.Service(case, True, cfg)
        service.start()
        offer_budget(service, cfg, True)
        c.save(case / 'policy-before-warmup.json', policy.check())
        warm_before = h.fixtures.stat(service.group)
        c.save(case / 'warmup-before.json', warm_before)
        warm_started = time.monotonic()
        try:
            service.collect('warmup', 25)
        finally:
            c.save(case / 'warmup-timing.json', dict(started_monotonic=warm_started,
                finished_monotonic=time.monotonic()))
            warm_after = h.fixtures.stat(service.group)
            c.save(case / 'warmup-counters.json', dict(before=warm_before, after=warm_after,
                delta={k: warm_after[k] - warm_before[k] for k in warm_before}))
        warm_raw = c.read(case / 'warmup.json')
        c.require(not integrity_exits(warm_raw, m.outcomes(warm_raw, cfg, 'warmup')),
                  'Corrupt complete warmup response')
        status = service.status(); c.require(q.drained(status), 'Warmup did not drain')
        c.save(case / 'threads-before.json', service.guard())
        c.save(case / 'policy-before-measurement.json', policy.check())
        offer_budget(service, cfg, False)
        if forecast is not None:
            c.save(case / 'warmup-forecast.json', dict(predictions={str(d): m.predictions(forecast,
                cfg, m.outcomes(c.read(case / 'warmup.json'), cfg, 'warmup'), d)
                for d in [20565395, *c.PROTOCOL['secondary_deadlines_ns']]},
                sealed_monotonic=time.monotonic(), measurement_used=False, forecast_ref=forecast_ref))
        c.save(case / 'sibling-before.json', sibling_context())
        before = h.fixtures.stat(service.group); c.save(case / 'measurement-before.json', before)
        c.save(case / 'measurement-start.json', dict(monotonic=time.monotonic()))
        afters = []
        try:
            service.collect('measurement', cfg['count'])
            until = time.monotonic() + 3
            while True:
                afters.append(service.status())
                h.save(case / 'status-window.json', dict(before=status, after_checks=afters))
                if q.drained(afters[-1]): break
                c.require(time.monotonic() < until, 'Measured requests did not drain')
                time.sleep(.05)
        finally:
            after = h.fixtures.stat(service.group)
            c.save(case / 'measurement-counters.json', dict(before=before, after=after,
                delta={k: after[k] - before[k] for k in before}))
        c.save(case / 'sibling-after.json', sibling_context())
        c.save(case / 'policy-after-measurement.json', policy.check())
        c.save(case / 'threads-after.json', service.guard())
        result = analyze(case, cfg); c.save(case / 'result.json', result)
    except BaseException as exc:
        c.save(case / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        raise
    finally:
        try:
            if service is not None: service.close()
        finally:
            try:
                if policy is not None: policy.close()
            finally: q.evidence_seal(case)
    identity(case, cfg)
    return result


def replay_case(case, cfg, forecast=None, forecast_ref=None):
    c.verify_evidence(case); identity(case, cfg)
    start = c.read(case / 'trial-start.json')
    c.require(start['forecast_ref'] == forecast_ref, 'Forecast barrier differs')
    result = analyze(case, cfg)
    c.require(result == c.read(case / 'result.json'), 'Raw rate-transfer result replay differs')
    if forecast is not None:
        warm = c.read(case / 'warmup-forecast.json')
        timing = c.read(case / 'warmup-timing.json')
        c.require(start['monotonic'] <= timing['started_monotonic'] <= timing['finished_monotonic'] <=
                  warm['sealed_monotonic'], 'Warmup acquisition barrier differs')
        expected = {str(d): m.predictions(forecast, cfg, result['warmup_outcomes'], d)
                    for d in [20565395, *c.PROTOCOL['secondary_deadlines_ns']]}
        c.require(warm['predictions'] == expected and not warm['measurement_used'] and
                  warm['forecast_ref'] == forecast_ref and
                  forecast_ref['sealed_monotonic'] <= start['monotonic'] <=
                  warm['sealed_monotonic'] <= c.read(case / 'measurement-start.json')['monotonic'],
                  'Pre-outcome prediction barrier differs')
    return result


def initialize():
    c.verify_prior()
    original_baseline = c.read(c.old.BASE / 'bundle-seal.json')['baseline']
    baseline = h.common.baseline()
    c.require(all(original_baseline[k] == baseline[k] for k in ('kernel', 'topology')),
              'Candidate requires the declared kernel/topology; a new host needs a separate design')
    from nginx_power_confirmation_guard import snapshot, check_baseline
    policy_baseline = snapshot(); check_baseline(policy_baseline)
    tests = c.BASE.parent / 'preparation-tests.log'
    c.require(tests.exists() and tests.read_text().rstrip().endswith('OK'), 'Passing tests log required')
    c.BASE.mkdir(parents=True, exist_ok=False)
    with (c.BASE / 'tests.log').open('x') as f: f.write(tests.read_text())
    c.save(c.BASE / 'protocol.json', c.PROTOCOL)
    c.save(c.BASE / 'policy-baseline.json', policy_baseline)
    c.save(c.BASE / 'schedule.json', c.schedule(secrets.randbits(128)))
    c.save(c.BASE / 'lineage.json', dict(old_bundle_seal=c.sha(c.old.BASE / 'bundle-seal.json'),
        client_sha256=c.sha(c.old.n.SOFTWARE / 'client'), fresh_scientific_records=True,
        historical_data_is_calibration=False, original_baseline=original_baseline,
        power_confirmation_sha256=c.sha(c.previous.BASE / 'campaign/evidence-seal.json'),
        prior_result_known=True, target_population_changed_prospectively=False, new_rate_calibration=True, host_policy_writes=False,
        new_baseline=baseline, prior_boot_is_current_qualification=False))
    paths = [c.ROOT / name for name in c.FILES]
    paths += [c.BASE / name for name in ('protocol.json', 'policy-baseline.json', 'schedule.json', 'lineage.json', 'tests.log')]
    c.save(c.BASE / 'preparation-seal.json', dict(baseline=baseline,
        files_sha256={str(p.relative_to(c.ROOT)): c.sha(p) for p in paths}))
    c.verify_prepared()


def inventory(directory):
    path = c.ROOT / 'analysis/runtime_io_leftover_observer_audit' / ('nginx-rate-transfer-' + str(time.time_ns()) + '.json')
    h.cmd(['sudo', '-n', sys.executable, '-B', str(c.ROOT / 'diagnostic/leftover_observer_audit.py'),
           '--output', str(path)], timeout=60)
    c.require(c.old.n.prior.observer.review(path)['performance_eligible'], 'Root observer inventory ineligible')
    c.save(directory / 'observer-inventory.json', dict(path=str(path), sha256=c.sha(path)))


def verify_inventory(directory):
    value = c.read(directory / 'observer-inventory.json'); path = Path(value['path'])
    c.require(c.sha(path) == value['sha256'] and c.old.n.prior.observer.review(path)['performance_eligible'],
              'Observer inventory evidence differs')


def run_group(directory, configs, started, ceiling, forecast=None, forecast_ref=None):
    directory.mkdir(); rows = []
    try:
        for cfg in configs:
            c.require(time.monotonic() - started + 150 + 120 <= ceiling, 'Active and cleanup budget exhausted')
            c.verify_prepared(); h.desktop_absent()
            if forecast is not None:
                c.verify_evidence(directory.parent / 'forecast')
                c.require(c.sha(directory.parent / 'forecast/evidence-seal.json') ==
                          forecast_ref['evidence_seal_sha256'], 'Forecast changed before validation')
            print(f"Rate-transfer {cfg['role']} {cfg['index']}: {cfg['policy']} at {cfg['rate_rps']}/s", flush=True)
            case = directory / f"cohort-{cfg['index']}"
            result = trial(case, cfg, forecast, forecast_ref)
            c.require(replay_case(case, cfg, forecast, forecast_ref) == result, 'Immediate raw replay differs')
            rows.append(result)
            c.require(not result['domain_exits'], 'Rate-transfer technical integrity exit: ' + ','.join(result['domain_exits']))
            if result['observations']:
                print('  Retained observations: ' + ', '.join(result['observations']), flush=True)
        c.save(directory / 'summary.json', dict(complete=True, rows=rows))
    except BaseException as exc:
        c.save(directory / 'summary.json', dict(complete=False, rows=rows, error=str(exc), no_replacement=True))
        raise
    finally: q.evidence_seal(directory)
    return rows


def qualify(schedule):
    directory = c.BASE / 'qualification'; directory.mkdir(); started = time.monotonic()
    try:
        inventory(directory)
        rows = run_group(directory / 'smoke', schedule['qualification'], started, 600)
        c.save(directory / 'summary.json', dict(passed=True, rows=rows, elapsed_sec=time.monotonic() - started,
            scientific_collection=False, fixed_frequency=False, thermal_reset_verified=False))
    except BaseException as exc:
        c.save(directory / 'summary.json', dict(passed=False, error=str(exc), no_retry=True))
        raise
    finally: q.evidence_seal(directory)
    verify_qualification(schedule)
    c.save(c.BASE / 'qualified-seal.json', dict(preparation_sha256=c.sha(c.BASE / 'preparation-seal.json'),
        qualification_sha256=c.sha(directory / 'evidence-seal.json'), passed=True))


def verify_qualification(schedule):
    directory = c.BASE / 'qualification'; c.verify_evidence(directory); verify_inventory(directory)
    c.require(c.read(directory / 'summary.json')['passed'] and
              c.read(directory / 'summary.json')['elapsed_sec'] <= 600, 'Qualification unavailable')
    c.verify_evidence(directory / 'smoke')
    rows = [replay_case(directory / 'smoke' / f"cohort-{cfg['index']}", cfg)
            for cfg in schedule['qualification']]
    c.require(all(not r['domain_exits'] for r in rows) and rows ==
              c.read(directory / 'summary.json')['rows'], 'Smoke replay differs')


def freeze(calibration, schedule):
    c.verify_evidence(calibration)
    rows = [replay_case(calibration / f"cohort-{cfg['index']}", cfg) for cfg in schedule['calibration']]
    directory = calibration.parent / 'forecast'; directory.mkdir()
    forecast = m.fit(rows, schedule); c.save(directory / 'forecast.json', forecast)
    c.save(directory / 'provenance.json', dict(calibration_sha256=c.sha(calibration / 'evidence-seal.json'),
        acquisition_elapsed_sec=time.monotonic() - c.read(calibration / 'cohort-1/trial-start.json')['monotonic'],
        qualified_sha256=c.sha(c.BASE / 'qualified-seal.json'),
        preparation_sha256=c.sha(c.BASE / 'preparation-seal.json'), sealed_monotonic=time.monotonic(),
        validation_used=False))
    q.evidence_seal(directory)
    ref = dict(sealed_monotonic=c.read(directory / 'provenance.json')['sealed_monotonic'],
               evidence_seal_sha256=c.sha(directory / 'evidence-seal.json'))
    return forecast, ref


def verify_forecast(directory, schedule):
    calibration = directory.parent / 'calibration'
    c.verify_evidence(calibration); c.verify_evidence(directory)
    p = c.read(directory / 'provenance.json')
    c.require(not p['validation_used'] and p['calibration_sha256'] == c.sha(calibration / 'evidence-seal.json')
        and p['qualified_sha256'] == c.sha(c.BASE / 'qualified-seal.json') and
        p['preparation_sha256'] == c.sha(c.BASE / 'preparation-seal.json'), 'Forecast lineage differs')
    rows = [replay_case(calibration / f"cohort-{cfg['index']}", cfg) for cfg in schedule['calibration']]
    f = m.fit(rows, schedule); c.require(f == c.read(directory / 'forecast.json'), 'Fresh forecast replay differs')
    return f, dict(sealed_monotonic=p['sealed_monotonic'], evidence_seal_sha256=c.sha(directory / 'evidence-seal.json'))


def campaign(schedule):
    verify_qualification(schedule)
    qualified = c.read(c.BASE / 'qualified-seal.json')
    c.require(qualified['preparation_sha256'] == c.sha(c.BASE / 'preparation-seal.json') and
        qualified['qualification_sha256'] == c.sha(c.BASE / 'qualification/evidence-seal.json') and qualified['passed'],
        'Qualified bundle changed')
    directory = c.BASE / 'campaign'; directory.mkdir(); started = time.monotonic(); phase = 'inventory'
    c.save(directory / 'lifetime.json', dict(started_monotonic=started, protocol=c.PROTOCOL))
    try:
        inventory(directory); phase = 'calibration'
        run_group(directory / 'calibration', schedule['calibration'], started, 2700)
        phase = 'forecast'; forecast, ref = freeze(directory / 'calibration', schedule)
        c.require((forecast, ref) == verify_forecast(directory / 'forecast', schedule), 'Freeze replay differs')
        phase = 'validation'
        rows = run_group(directory / 'validation', schedule['validation'], started, 2700, forecast, ref)
        result = m.compare(rows, forecast, schedule)
        result['acquisition'] = dict(calibration_elapsed_sec=c.read(directory / 'forecast/provenance.json')['acquisition_elapsed_sec'],
            warmup_elapsed_sec=[c.read(directory / 'validation' / f"cohort-{cfg['index']}" / 'warmup-timing.json')['finished_monotonic'] -
                c.read(directory / 'validation' / f"cohort-{cfg['index']}" / 'warmup-timing.json')['started_monotonic']
                for cfg in schedule['validation']], equal_warmup_comparison_budget=False)
        c.require(time.monotonic() - started <= 2700, 'Campaign lifetime exceeded')
        c.save(directory / 'comparison.json', result)
        c.save(directory / 'summary.json', dict(complete=True, status=result['status'],
            elapsed_sec=time.monotonic() - started, measurement_offers=6000, total_offers=6450,
            novelty_established=False))
    except BaseException as exc:
        c.save(directory / 'summary.json', dict(complete=False, status='campaign_stopped', phase=phase,
            error=str(exc), elapsed_sec=time.monotonic() - started, no_replacement=True))
        raise
    finally: q.evidence_seal(directory)
    replay()
    print('Rate-transfer study completed: ' + result['status'], flush=True)
    print('Results: ' + str(directory / 'comparison.json'), flush=True)


def replay():
    schedule = c.verify_prepared(False); verify_qualification(schedule)
    directory = c.BASE / 'campaign'; c.verify_evidence(directory); verify_inventory(directory)
    summary = c.read(directory / 'summary.json')
    c.require(summary['complete'] and summary['elapsed_sec'] <= 2700, 'Complete campaign unavailable')
    forecast, ref = verify_forecast(directory / 'forecast', schedule)
    c.verify_evidence(directory / 'validation')
    rows = [replay_case(directory / 'validation' / f"cohort-{cfg['index']}", cfg, forecast, ref)
            for cfg in schedule['validation']]
    result = m.compare(rows, forecast, schedule)
    result['acquisition'] = dict(calibration_elapsed_sec=c.read(directory / 'forecast/provenance.json')['acquisition_elapsed_sec'],
        warmup_elapsed_sec=[c.read(directory / 'validation' / f"cohort-{cfg['index']}" / 'warmup-timing.json')['finished_monotonic'] -
            c.read(directory / 'validation' / f"cohort-{cfg['index']}" / 'warmup-timing.json')['started_monotonic']
            for cfg in schedule['validation']], equal_warmup_comparison_budget=False)
    c.require(result == c.read(directory / 'comparison.json') and result['status'] == summary['status'],
              'Final comparison replay differs')
    return result


def all_phases():
    schedule = c.verify_prepared(); h.desktop_absent(); os.sched_setaffinity(0, {0, 1})
    c.require(not (c.BASE / 'qualification').exists() and not (c.BASE / 'campaign').exists(),
              'Preserve prior attempts; no resume, retries or overwrites')
    qualify(schedule); campaign(schedule)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('initialize', 'verify', 'dry-run', 'all', 'replay'))
    args = parser.parse_args()
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP): signal.signal(signum, h.handle_signal)
    if args.phase == 'verify': c.verify_prepared(); print('Prepared source, protocol and randomized schedule verify.')
    elif args.phase == 'dry-run': print(json.dumps(c.verify_prepared(), indent=2))
    elif args.phase == 'all': all_phases()
    elif args.phase == 'replay': print(json.dumps(replay(), indent=2))
    else: initialize()
