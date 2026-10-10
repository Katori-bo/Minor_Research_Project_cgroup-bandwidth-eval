#!/usr/bin/env python3
"""Validate and summarize the targeted timing diagnostic."""
import csv
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
    return values[math.ceil(p * len(values)) - 1] / 1e6


def writecsv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def boot(cells, transform, seed=761):
    rng = random.Random(seed)
    values = sorted(transform({k: rng.choices(v, k=len(v)) for k, v in cells.items()})
                    for _ in range(10000))
    return [values[249], values[9749]]


def interaction(cells):
    return (st.mean(cells[100, 4]) - st.mean(cells[100, 1])) - \
           (st.mean(cells[250, 4]) - st.mean(cells[250, 1]))


def response_durations(request, handler):
    """Signed per-request accounting; server exit need not precede client completion."""
    span = handler['handler_exit_ns'] - handler['entry_ns']
    return dict(resume_to_write=handler['write_start_ns'] - handler['resume_ns'],
                write_call=handler['write_end_ns'] - handler['write_start_ns'],
                write_to_exit=handler['handler_exit_ns'] - handler['write_end_ns'],
                e2e_minus_handler_span=request['EndToEndLatencyNs'] - span)


def trial_row(order, config, directory):
    report, lg, server = [runner.read(directory / name) for name in
                          ('result.json', 'loadgen.json', 'server_metrics.json')]
    good = [q for q in lg['requests'] if q['StatusCode'] == 200 and not q['Error']]
    handlers = {e['id']: e for e in server['handler_events']}
    response_samples = [response_durations(q, handlers[q['ID']])
                        for q in good if q['ServerTimingPresent']]
    trace_good = [q for q in good if config['client_trace'] and not q['TraceIssue'] and
                  q['GotConnOffsetNs'] >= 0 and q['WroteRequestOffsetNs'] >= 0 and
                  q['WroteRequestOffsetNs'] <= q['FirstByteOffsetNs'] <= q['HeadersOffsetNs'] <=
                  q['BodyDoneOffsetNs']]
    trace_coverage = len(trace_good) / len(good) if good and config['client_trace'] else None
    row = dict(order=order, run_id=config['run_id'], period_ms=config['period_us'] / 1000,
               workers=config['workers'], rep=config['rep'], instrument=config['instrument'],
               runtime_trace=config.get('runtime_trace', False), trace_storage=config.get('trace_storage', 'file'),
               client_trace=config['client_trace'], trace_coverage=trace_coverage,
               trace_issue_count=sum(bool(q['TraceIssue']) for q in good),
               attempt=directory.name, scheduled=lg['total_scheduled'], success=len(good),
               rejection_fraction=lg['total_503'] / lg['total_scheduled'],
               timeout_fraction=sum(q['TimedOut'] for q in lg['requests']) / lg['total_scheduled'],
               successful_rps=lg['total_success'] / config['duration_sec'],
               cpu_cores=report['cpu_usage_cores'], throttled_period_fraction=report['throttling_fraction'],
               cpu_usec_per_completed_work=report['cgroup_delta']['usage_usec'] / server['completed']
                   if server['completed'] else None,
               client_cpu_usec_per_scheduled=lg['client_cpu_usec'] / lg['total_scheduled'],
               queue_sample_max=server['queue_max'], completed_after_client_left=server['client_gone_at_completion'],
               server_write_errors=sum(bool(h['write_error']) for h in handlers.values()),
               negative_handler_difference_count=sum(r['e2e_minus_handler_span'] < 0 for r in response_samples))
    row['runtime_trace_complete'] = (runner.read(directory / 'trace_status.json')['complete']
        if config.get('runtime_trace') else None)
    if config.get('runtime_trace'):
        status = runner.read(directory / 'trace_status.json')
        matched = (runner.read(directory / 'trace_requests.json')['matched']
                   if runner.custom_recording(config) else [])
        row.update(runtime_trace_bytes=status['runtime_trace_bytes'],
                   runtime_trace_persisted_bytes=status.get('runtime_trace_persisted_bytes'),
                   runtime_trace_persistence_complete=status.get('runtime_trace_persistence_complete'),
                   io_events=len(status['io_events']), io_events_dropped=status['io_events_dropped'],
                   matched_slow_count=sum(r['group'] == 'slow' for r in matched),
                   matched_typical_count=sum(r['group'] == 'typical' for r in matched),
                   matched_slow_with_socket_write=sum(r['group'] == 'slow' and r['socket_write_count'] > 0 for r in matched))
    else:
        row.update(runtime_trace_bytes=None, runtime_trace_persisted_bytes=None,
                   runtime_trace_persistence_complete=None, io_events=None, io_events_dropped=None,
                   matched_slow_count=None, matched_typical_count=None,
                   matched_slow_with_socket_write=None)
    values = {'e2e': [q['EndToEndLatencyNs'] for q in good],
              'pre_admission': [q['PreAdmissionNs'] for q in good if q['ServerTimingPresent']],
              'queue': [q['QueueWaitNs'] for q in good if q['ServerTimingPresent']],
              'processing': [q['ProcessingNs'] for q in good if q['ServerTimingPresent']],
              'post_work': [q['PostWorkWaitNs'] for q in good if q['ServerTimingPresent']],
              'request_to_first_byte': [q['FirstByteOffsetNs'] - q['WroteRequestOffsetNs'] for q in trace_good]
                                        if trace_coverage is not None and trace_coverage >= .99 else [],
              'first_byte_to_body_done': [q['BodyDoneOffsetNs'] - q['FirstByteOffsetNs'] for q in trace_good]
                                          if trace_coverage is not None and trace_coverage >= .99 else [],
              'outside_measured_server': [q['EndToEndLatencyNs'] - q['PreAdmissionNs'] - q['QueueWaitNs'] -
                                          q['ProcessingNs'] - q['PostWorkWaitNs'] for q in good
                                          if q['ServerTimingPresent']]}
    values.update({key: [r[key] for r in response_samples] for key in
                   ('resume_to_write', 'write_call', 'write_to_exit', 'e2e_minus_handler_span')})
    for name, sample in values.items():
        for fraction in (.50, .95, .99):
            row[f'p{int(fraction*100)}_{name}_ms'] = pct(sample, fraction)
    if good:
        top = sorted(good, key=lambda q: q['EndToEndLatencyNs'], reverse=True)[:math.ceil(len(good)*.01)]
        row['top1pct_outside_server_share'] = (st.mean((q['EndToEndLatencyNs'] - q['PreAdmissionNs'] -
             q['QueueWaitNs'] - q['ProcessingNs'] - q['PostWorkWaitNs']) / q['EndToEndLatencyNs'] for q in top)
             if config['instrument'] else None)
        row['top1pct_e2e_minus_handler_span_share'] = (st.mean(
             response_durations(q, handlers[q['ID']])['e2e_minus_handler_span'] /
             q['EndToEndLatencyNs'] for q in top) if config['instrument'] else None)
    else:
        row['top1pct_outside_server_share'] = None
        row['top1pct_e2e_minus_handler_span_share'] = None
    return row


def pilot_gate(rows, completions):
    on = [r for r in rows if r['run_id'].startswith('trace_overhead') and r['runtime_trace']]
    off = [r for r in rows if r['run_id'].startswith('trace_overhead') and not r['runtime_trace']]
    def ratio(field):
        a, b = [r[field] for r in on], [r[field] for r in off]
        return st.median(a) / st.median(b) if len(a) == len(b) == 2 and all(v is not None and v > 0 for v in a + b) else None
    service_cpu_ratio = ratio('cpu_usec_per_completed_work')
    client_cpu_ratio = ratio('client_cpu_usec_per_scheduled')
    latency_ratio = ratio('p99_e2e_ms')
    checks = {'all_six_trials_validated': len(rows) == 6,
              'server_cpu_overhead_under_10pct': service_cpu_ratio is not None and service_cpu_ratio <= 1.10,
              'client_cpu_overhead_under_10pct': client_cpu_ratio is not None and client_cpu_ratio <= 1.10,
              'p99_latency_screen_under_10pct': latency_ratio is not None and latency_ratio <= 1.10,
              'both_target_conditions_covered': {(r['period_ms'], r['workers']) for r in rows if r['runtime_trace']} ==
                    {(100., 1), (100., 4)},
              'all_diagnostic_timing_observed': all(r['trace_coverage'] is not None and
                    r['trace_coverage'] >= .99 and r['p99_pre_admission_ms'] is not None and
                    r['p99_post_work_ms'] is not None and
                    r['p99_resume_to_write_ms'] is not None and r['p99_write_call_ms'] is not None and
                    r['p99_write_to_exit_ms'] is not None and
                    r['p99_request_to_first_byte_ms'] is not None and
                    r['p99_first_byte_to_body_done_ms'] is not None for r in rows),
              'all_enabled_traces_complete': all(r['runtime_trace_complete'] for r in rows if r['runtime_trace']),
              'failure_rates_not_worse': max(r['rejection_fraction'] + r['timeout_fraction'] for r in on) <=
                  max(r['rejection_fraction'] + r['timeout_fraction'] for r in off) + .001}
    return {'passed': all(checks.values()), 'checks': checks,
            'overhead_server_cpu_ratio': service_cpu_ratio,
            'overhead_client_cpu_ratio': client_cpu_ratio,
            'overhead_p99_e2e_ratio': latency_ratio,
            'completion_sha256': completions,
            'limits': 'Two on and two off trials give only a coarse CPU/latency overhead screen; pilot latency is diagnostic only.'}


def summarize_full(rows):
    estimates = {}
    for metric in ('e2e', 'pre_admission', 'queue', 'processing', 'post_work',
                   'resume_to_write', 'write_call', 'write_to_exit',
                   'request_to_first_byte', 'first_byte_to_body_done', 'outside_measured_server',
                   'e2e_minus_handler_span'):
        column = f'p99_{metric}_ms'
        cells = {(p, w): [r[column] for r in rows if r['period_ms'] == p and r['workers'] == w]
                 for p in (100, 250) for w in (1, 4)}
        if any(len(v) != 5 or any(x is None for x in v) for v in cells.values()):
            estimates[metric] = {'unavailable': 'Missing observation or incomplete repetition set'}
            continue
        estimates[metric] = {'cell_mean_trial_p99_ms': {f'{p}ms_{w}workers': st.mean(v)
                          for (p, w), v in cells.items()}, 'interaction_ms': interaction(cells),
                          'interaction_ms_ci95': boot(cells, interaction)}
    return estimates


def main(session):
    meta = runner.verify_session(session, check_current=False)
    if meta.get('components'):
        from component_analysis import analyze_components
        return analyze_components(session)
    plan = runner.read(session / 'matrix.json')
    out = session / 'analysis'
    out.mkdir(exist_ok=True)
    attempts, rows, issues, completions = [], [], [], {}
    for order, config in enumerate(plan, 1):
        good = []
        for directory in runner.attempt_dirs(session / 'attempts' / config['run_id']):
            errors = runner.validation_errors(directory, config, meta['pilot'])
            attempts.append({'run_id': config['run_id'], 'attempt': directory.name,
                             'valid': not errors, 'validation_errors': '; '.join(errors)})
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
    report = ['# Diagnostic trial results', '', 'Pilot observations are diagnostic only.' if meta['pilot'] else
              'Five independent trials per condition; per-request timing distributions are retained in raw attempts.', '',
              '| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 resume-to-write ms | p99 write-call ms | p99 write-to-exit ms | p99 signed e2e-minus-handler ms | Trace coverage | Rejections | Timeouts |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        keys = ('p99_e2e_ms', 'p99_pre_admission_ms', 'p99_queue_ms', 'p99_processing_ms',
                'p99_post_work_ms', 'p99_resume_to_write_ms', 'p99_write_call_ms',
                'p99_write_to_exit_ms', 'p99_e2e_minus_handler_span_ms', 'trace_coverage',
                'rejection_fraction', 'timeout_fraction')
        report.append('| ' + r['run_id'] + ' | ' + ' | '.join('NA' if r[k] is None else
                    (f'{r[k]:.3%}' if k in ('rejection_fraction', 'timeout_fraction') else f'{r[k]:.3f}')
                                                        for k in keys) + ' |')
    report += ['', 'Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.', '',
        'The handler exit marker is recorded after event storage and before unlocking/returning. '
        'The signed e2e-minus-handler value subtracts durations for the same request, not absolute clocks. '
        'It may be negative if client completion overlaps server cleanup; negative values and write errors '
        'are retained as outcomes. Neither a write return nor the exit marker proves delivery.', '',
        '| Run | Server write errors | Negative signed differences | Slowest 1% mean signed difference / e2e |',
        '|---|---:|---:|---:|']
    for r in rows:
        share = r['top1pct_e2e_minus_handler_span_share']
        report.append(f'| {r["run_id"]} | {r["server_write_errors"]} | '
                      f'{r["negative_handler_difference_count"]} | '
                      + ('NA' if share is None else f'{share:.3%}') + ' |')
    report += ['', '## Runtime and connection evidence', '',
               '| Run | Runtime trace | Bytes | I/O events | Dropped | Matched slow/typical | Slow with socket write |',
               '|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['runtime_trace']:
            report.append(f'| {r["run_id"]} | complete | {r["runtime_trace_bytes"]} | '
                          f'{r["io_events"]} | {r["io_events_dropped"]} | '
                          f'{r["matched_slow_count"]}/{r["matched_typical_count"]} | '
                          f'{r["matched_slow_with_socket_write"]} |')
        else:
            report.append(f'| {r["run_id"]} | disabled | NA | NA | NA | NA | NA |')
    report += ['', 'Per-request runnable, Go Running, synchronization/network wait and socket-write '
               'evidence is in each accepted attempt’s `trace_requests.json` and `trace_report.md`. Go Running can include OS descheduling or quota throttling and is not measured CPU execution. Runtime and service '
               'timestamps are aligned only through two bracketed clock logs; mapping uncertainty '
               'is reported there. Socket reads are retained at connection level because a read '
               'may contain partial or multiple HTTP requests. A successful socket Write does not '
               'prove delivery to the client. Client timing is compared through durations only.', '']
    if any(r['trace_storage'] == 'memory' for r in rows):
        report += ['Runtime traces use a fixed 64 MiB memory buffer allocated before capture. '
                   'After trace.Stop drains the writer, file persistence, Sync and Close remain inside '
                   'the final cgroup CPU accounting window. Buffer overflow or persistence failure '
                   'invalidates the attempt. This is a candidate instrumentation intervention; '
                   'functional validation does not establish reduced performance perturbation.', '']
    (out / 'report.md').write_text('\n'.join(report))
    if meta['pilot']:
        gate = pilot_gate(rows, completions)
        runner.put(out / 'pilot_gate.json', gate)
        if not gate['passed']:
            raise SystemExit('Pilot gate needs review: ' + ', '.join(k for k, v in gate['checks'].items() if not v))
    else:
        runner.put(out / 'estimates.json', summarize_full(rows))
    print('Validated', len(rows), 'trials:', out)


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
