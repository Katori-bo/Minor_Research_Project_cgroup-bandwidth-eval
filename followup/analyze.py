#!/usr/bin/env python3
"""Analyze validated trials and report a separate diagnostic pilot gate."""
import csv
import json
import math
from pathlib import Path
import random
import statistics as st
import sys

import run as runner


def pct(values, p):
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(p * len(values)) - 1)] / 1e6


def writecsv(path, rows):
    if rows:
        with path.open('w', newline='') as out:
            writer = csv.DictWriter(out, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def boot(cells, transform, seed=761):
    rng = random.Random(seed)
    values = sorted(transform({k: rng.choices(v, k=len(v)) for k, v in cells.items()}) for _ in range(10000))
    return [values[249], values[9749]]


def interaction(cells):
    return (st.mean(cells[100, 4]) - st.mean(cells[100, 1])) - (st.mean(cells[250, 4]) - st.mean(cells[250, 1]))


def ratio_of_ratios(cells):
    g = {k: st.mean(map(math.log, v)) for k, v in cells.items()}
    return math.exp((g[100, 4] - g[100, 1]) - (g[250, 4] - g[250, 1]))


def correlation(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 2:
        return None
    x, y = zip(*pairs)
    if len(set(x)) < 2 or len(set(y)) < 2:
        return None
    return st.correlation(x, y)


def trial_row(order, config, directory):
    report, lg, server = [runner.read(directory / n) for n in ('result.json', 'loadgen.json', 'server_metrics.json')]
    requests = lg['requests']
    good = [q for q in requests if q['StatusCode'] == 200 and not q['Error']]
    timed_out = sum(q['TimedOut'] for q in requests)
    n = lg['total_scheduled']
    seconds = config['duration_sec']
    row = dict(order=order, run_id=config['run_id'], study=config['study'], period_ms=config['period_us'] / 1000,
               workers=config['workers'], gomaxprocs=config['gomaxprocs'], pattern=config['pattern'],
               rep=config['rep'], instrument=config['instrument'], scheduled=n, success=len(good),
               successful_rps=sum(q['CompletedOffsetNs'] <= seconds * 1e9 for q in good) / seconds,
               cohort_success_rps=len(good) / seconds,
               successful_rps_including_client_drain=lg['successful_throughput_rps'],
               server_completed_rps_including_server_drain=server['completed'] / report['elapsed_sec'],
               rejection_fraction=lg['total_503'] / n, timeout_fraction=timed_out / n,
               other_error_fraction=(lg['total_errors'] - timed_out + lg['client_dropped']) / n,
               cpu_cores=report['cpu_usage_cores'], throttled_period_fraction=report['throttling_fraction'],
               throttled_usec=report['cgroup_delta'].get('throttled_usec', 0),
               cpu_usec_per_completed_work=report['cgroup_delta']['usage_usec'] / server['completed'] if server['completed'] else None,
               queue_sample_max=server['queue_max'], completed_after_client_left=server['client_gone_at_completion'],
               server_unseen_dispatched=report['server_unseen_dispatched'], attempt=directory.name,
               measurement_started_at=report['measurement_started_at'],
               start_temp_c=st.mean(v['mean_c'] for v in report['thermal']['sensors'].values()))
    distributions = {'e2e': [q['EndToEndLatencyNs'] for q in good],
        'queue_success': [q['QueueWaitNs'] for q in good if q['ServerTimingPresent']],
        'processing_success': [q['ProcessingNs'] for q in good if q['ServerTimingPresent']],
        'queue_all_completed': [e['queue_wait_ns'] for e in server['events']],
        'processing_all_completed': [e['processing_ns'] for e in server['events']]}
    for name, values in distributions.items():
        for quantile in (50, 95, 99, 100):
            row[f'p{quantile}_{name}_ms'] = pct(values, quantile / 100)
    return row


def pilot_gate(rows, completions):
    checks = {'all_planned_trials_validated': True}
    overhead = [r for r in rows if r['run_id'].startswith('pilot_overhead_')]
    on = [r['cpu_usec_per_completed_work'] for r in overhead if r['instrument']]
    off = [r['cpu_usec_per_completed_work'] for r in overhead if not r['instrument']]
    overhead_ratio = st.median(on) / st.median(off) if len(on) == len(off) == 2 and all(v and v > 0 for v in on + off) else None
    checks['overhead_screen_under_10pct'] = overhead_ratio is not None and overhead_ratio <= 1.10
    a = [r for r in rows if r['study'] == 'A']
    checks['A_both_execution_settings_saturated'] = len(a) == 2 and all(.45 <= r['cpu_cores'] <= .55 for r in a)
    checks['component_timing_observed'] = all(r['p99_queue_success_ms'] is not None and
        r['p99_processing_success_ms'] is not None for r in rows if r['instrument'])
    return {'passed': all(checks.values()), 'checks': checks, 'overhead_cpu_per_work_ratio': overhead_ratio,
            'completion_sha256': completions,
            'limits': 'Two instrumented/off trials each are a coarse overhead screen. Passing does not prove zero overhead or a mechanism.'}


def summarize_full(rows):
    estimates = {}
    for pattern in ('steady', 'bursty'):
        cells = {(p, w): [r['p99_e2e_ms'] for r in rows if r['study'] == 'B' and r['pattern'] == pattern and
                         r['period_ms'] == p and r['workers'] == w] for p in (100, 250) for w in (1, 4)}
        if any(len(v) != 5 or any(x is None or x <= 0 for x in v) for v in cells.values()):
            estimates[pattern] = {'unavailable': 'Missing trial p99, zero successes, or incomplete repetition set'}
            continue
        estimates[pattern] = {'interaction_ms': interaction(cells), 'interaction_ms_ci95': boot(cells, interaction),
                             'ratio_of_ratios': ratio_of_ratios(cells), 'ratio_of_ratios_ci95': boot(cells, ratio_of_ratios)}
    a = {}
    for metric in ('p99_processing_all_completed_ms', 'server_completed_rps_including_server_drain', 'successful_rps'):
        cells = {g: [r[metric] for r in rows if r['study'] == 'A' and r['gomaxprocs'] == g] for g in (1, 2)}
        if any(len(v) != 5 or any(x is None for x in v) for v in cells.values()):
            a[metric] = {'unavailable': 'Missing observations; no available-case substitution'}
            continue
        effect = lambda d: st.mean(d[2]) - st.mean(d[1])
        a[metric] = {'means': {str(k): st.mean(v) for k, v in cells.items()},
                     'g2_minus_g1': effect(cells), 'ci95': boot(cells, effect)}
    estimates['A'] = a
    # Within-condition residuals reduce confounding by treatment order.
    groups = {}
    for r in rows:
        key = (r['study'], r['period_ms'], r['workers'], r['gomaxprocs'], r['pattern'])
        groups.setdefault(key, []).append(r)
    residuals, order, temperature = [], [], []
    for group in groups.values():
        usable = [r for r in group if r['p99_e2e_ms'] is not None and r['p99_e2e_ms'] > 0]
        if not usable:
            continue
        center = st.mean(math.log(r['p99_e2e_ms']) for r in usable)
        for r in usable:
            residuals.append(math.log(r['p99_e2e_ms']) - center)
            order.append(r['order'])
            temperature.append(r['start_temp_c'])
    estimates['collection_order'] = {'correlation_order_within_condition_log_p99_residual': correlation(order, residuals),
        'correlation_temperature_within_condition_log_p99_residual': correlation(temperature, residuals),
        'interpretation': 'Descriptive diagnostics, not causal adjustments; constant series produce null.'}
    return estimates


def main(session):
    meta = runner.verify_session(session, check_current=False)
    plan = runner.read(session / 'matrix.json')
    out = session / 'analysis'
    out.mkdir(exist_ok=True)
    attempts, rows, issues, completions = [], [], [], {}
    for order, config in enumerate(plan, 1):
        good = []
        for directory in runner.attempt_dirs(session / 'attempts' / config['run_id']):
            errors = runner.validation_errors(directory, config, meta['pilot'])
            attempts.append({'run_id': config['run_id'], 'attempt': directory.name, 'valid': not errors,
                             'validation_errors': '; '.join(errors)})
            if not errors:
                good.append(directory)
        if len(good) != 1:
            issues.append(f'{config["run_id"]}: {len(good)} valid attempts')
            continue
        rows.append(trial_row(order, config, good[0]))
        completions[config['run_id']] = runner.sha(good[0] / 'complete.json')
    writecsv(out / 'attempt_audit.csv', attempts)
    if issues:
        runner.put(out / 'validation.json', {'passed': False, 'issues': issues})
        if meta['pilot']:
            runner.put(out / 'pilot_gate.json', {'passed': False, 'issues': issues})
        raise SystemExit('Incomplete or invalid trials: ' + '; '.join(issues))
    runner.put(out / 'validation.json', {'passed': True, 'issues': []})
    writecsv(out / 'trials.csv', rows)
    report = ['# Trial-level results', '', 'Pilot diagnostics only.' if meta['pilot'] else 'Each row is one independent trial.', '',
              '| Run | Successful p99 ms | Queue p99 ms | Processing p99 ms | Success/s in window | Rejected | Timeout |',
              '|---|---:|---:|---:|---:|---:|---:|']
    def format_value(value):
        return 'NA' if value is None else f'{value:.3f}'
    for r in rows:
        report.append('| ' + r['run_id'] + ' | ' + ' | '.join(format_value(r[k]) for k in
                      ('p99_e2e_ms', 'p99_queue_success_ms', 'p99_processing_success_ms', 'successful_rps',
                       'rejection_fraction', 'timeout_fraction')) + ' |')
    (out / 'report.md').write_text('\n'.join(report) + '\n')
    if meta['pilot']:
        gate = pilot_gate(rows, completions)
        runner.put(out / 'pilot_summary.json', {'diagnostic_only': True, 'trials': rows})
        runner.put(out / 'pilot_gate.json', gate)
        if not gate['passed']:
            raise SystemExit('Pilot needs review: ' + ', '.join(k for k, v in gate['checks'].items() if not v))
        print('Pilot validation and coarse overhead/saturation checks passed. See analysis/report.md and pilot_gate.json.')
    else:
        runner.put(out / 'estimates.json', summarize_full(rows))
        print('All 50 trials validated. Results:', out)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
