#!/usr/bin/env python3
"""Reproduce a request-ID audit of the completed response-timing session."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as st

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / 'results/diagnostic/all-in-one-power-fix/full'
OUT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text())


def verify_attempt(directory):
    seal = read(directory / 'complete.json')
    actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()
              if p.is_file() and p.name != 'complete.json'}
    if seal['schema'] != 3 or actual != seal['files']:
        raise ValueError(f'Attempt seal mismatch: {directory}')


def quantile(values, fraction):
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * fraction) - 1]


def summarize_trial(config, client, result):
    """Use sealed raw inputs, never a potentially stale derived trials.csv."""
    requests = client['requests']
    successful = [q for q in requests if q['StatusCode'] == 200 and not q['Error']]
    rejected = sum(q['StatusCode'] == 503 and not q['Error'] for q in requests)
    if (len(successful), rejected, len(requests)) != (
            client['total_success'], client['total_503'], client['total_completed']):
        raise ValueError('Client outcome counts do not match raw requests')
    scheduled = client['total_scheduled']
    periods = result['cgroup_delta']['nr_periods']
    return dict(run_id=config['run_id'], period_ms=config['period_us'] / 1000,
                workers=config['workers'], success=len(successful),
                p50_e2e_ms=quantile([q['EndToEndLatencyNs'] for q in successful], .50) / 1e6,
                p99_e2e_ms=quantile([q['EndToEndLatencyNs'] for q in successful], .99) / 1e6,
                rejection_fraction=rejected / scheduled,
                timeout_fraction=sum(q['TimedOut'] for q in requests) / scheduled,
                throttled_period_fraction=result['cgroup_delta']['nr_throttled'] / periods)


def audit(session=SESSION, out=OUT):
    if not read(session / 'analysis/validation.json')['passed']:
        raise ValueError('Completed session did not pass validation')
    meta = read(session / 'metadata.json')
    matrix = read(session / 'matrix.json')
    matrix_hash = hashlib.sha256((session / 'matrix.json').read_bytes()).hexdigest()
    if meta['schema'] != 3 or meta['pilot'] or matrix_hash != meta['matrix_sha256']:
        raise ValueError('Expected the intact completed revision-2 full session')
    if len(matrix) != 20 or len({c['run_id'] for c in matrix}) != 20 or any(
            sorted(c['rep'] for c in matrix if (c['period_us'], c['workers']) == (period, workers)) != list(range(1, 6))
            for period in (100000, 250000) for workers in (1, 4)):
        raise ValueError('Expected five repetitions in each of four conditions')
    rows, trial_rows = [], []
    source_hashes = {str(p.relative_to(session)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (session / 'metadata.json', session / 'matrix.json')}
    for config in matrix:
        attempts = sorted((session / 'attempts' / config['run_id']).glob('[0-9][0-9][0-9]'))
        if len(attempts) != 1:
            raise ValueError(f'Expected one attempt for {config["run_id"]}')
        directory = attempts[0]
        verify_attempt(directory)
        source_hashes[str((directory / 'complete.json').relative_to(session))] = hashlib.sha256(
            (directory / 'complete.json').read_bytes()).hexdigest()
        client = read(directory / 'loadgen.json')
        server = read(directory / 'server_metrics.json')
        result = read(directory / 'result.json')
        if config != read(directory / 'config.json') or config != result['config']:
            raise ValueError(f'Config differs from frozen matrix: {directory}')
        trial_rows.append(summarize_trial(config, client, result))
        events = {e['id']: e for e in server['events']}
        handlers = {e['id']: e for e in server['handler_events']}
        if len(events) != len(server['events']) or len(handlers) != len(server['handler_events']):
            raise ValueError(f'Duplicate server ID: {directory}')
        requests = client['requests']
        if len({q['ID'] for q in requests}) != len(requests):
            raise ValueError(f'Duplicate client ID: {directory}')
        successful = [q for q in requests if q['StatusCode'] == 200 and not q['Error']]
        top_ids = {q['ID'] for q in sorted(successful, key=lambda q: q['EndToEndLatencyNs'],
                                            reverse=True)[:math.ceil(len(successful) * .01)]}
        ordered = sorted(successful, key=lambda q: q['EndToEndLatencyNs'])
        typical_ids = {q['ID'] for q in ordered[int(len(ordered)*.4):math.ceil(len(ordered)*.6)]}
        for q in successful:
            event, handler = events[q['ID']], handlers[q['ID']]
            if not (q['ServerTimingPresent'] and
                    0 <= handler['entry_ns'] <= handler['admission_ns'] == event['admission_ns'] <=
                    event['worker_start_ns'] < event['completion_ns'] <= handler['resume_ns'] and
                    event['queue_wait_ns'] == event['worker_start_ns'] - event['admission_ns'] and
                    event['processing_ns'] == event['completion_ns'] - event['worker_start_ns'] and
                    handler['pre_admission_ns'] == handler['admission_ns'] - handler['entry_ns'] and
                    handler['post_work_wait_ns'] == handler['resume_ns'] - event['completion_ns']):
                raise ValueError(f'Invalid server timing: {directory} ID {q["ID"]}')
            if (event['queue_wait_ns'], event['processing_ns'], handler['pre_admission_ns'],
                    handler['post_work_wait_ns']) != (q['QueueWaitNs'], q['ProcessingNs'],
                                                      q['PreAdmissionNs'], q['PostWorkWaitNs']):
                raise ValueError(f'Client/server duration mismatch: {directory} ID {q["ID"]}')
            if q['TraceIssue'] or not (0 <= q['GotConnOffsetNs'] <= q['WroteRequestOffsetNs']
                                        <= q['FirstByteOffsetNs'] <= q['HeadersOffsetNs']
                                        <= q['BodyDoneOffsetNs']):
                raise ValueError(f'Incomplete trace: {directory} ID {q["ID"]}')
            outside = q['EndToEndLatencyNs'] - sum(q[k] for k in
                ('PreAdmissionNs', 'QueueWaitNs', 'ProcessingNs', 'PostWorkWaitNs'))
            if outside < 0:
                raise ValueError(f'Negative per-request residual: {directory} ID {q["ID"]}')
            rows.append(dict(run_id=config['run_id'], period_ms=config['period_us'] // 1000,
                workers=config['workers'], request_id=q['ID'], top1pct=int(q['ID'] in top_ids),
                typical=int(q['ID'] in typical_ids), depth_at_admission=event['depth_at_admission'],
                phase_offset_sec=(q['ScheduledOffsetNs'] / 1e9) % 10,
                high_phase=int((q['ScheduledOffsetNs'] / 1e9) % 10 >= 5),
                e2e_ms=q['EndToEndLatencyNs'] / 1e6,
                dispatch_lag_ms=q['DispatchLagNs'] / 1e6,
                conn_ms=q['GotConnOffsetNs'] / 1e6,
                request_write_ms=q['WroteRequestOffsetNs'] / 1e6,
                write_to_first_byte_ms=(q['FirstByteOffsetNs'] - q['WroteRequestOffsetNs']) / 1e6,
                body_after_first_byte_ms=(q['BodyDoneOffsetNs'] - q['FirstByteOffsetNs']) / 1e6,
                queue_ms=q['QueueWaitNs'] / 1e6, processing_ms=q['ProcessingNs'] / 1e6,
                post_work_ms=q['PostWorkWaitNs'] / 1e6,
                outside_server_ms=outside / 1e6,
                outside_share=outside / q['EndToEndLatencyNs']))
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'completed_request_audit.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (out / 'completed_trials.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(trial_rows[0]))
        writer.writeheader()
        writer.writerows(trial_rows)
    (out / 'completed_source_hashes.json').write_text(json.dumps(dict(
        source=str(session), input_sha256=source_hashes,
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()), indent=2) + '\n')
    report = ['# Completed diagnostic: request-ID timing audit', '',
              f'Source: `{session}`. Every attempt seal and successful request/server ID was checked.',
              'Pilot requests are excluded. Trial summaries are recomputed from sealed raw data. '
              'Residuals are calculated for each request before grouping. Slowest-1% means pool the '
              'selected requests across trials; p50/p99 columns average trial quantiles.', '',
              '| Period | Workers | Mean trial p50 / p99 e2e | Slowest 1%: mean e2e / residual | Residual share | High-phase count | Mean dispatch lag |',
              '|---:|---:|---:|---:|---:|---:|---:|']
    cells = {}
    for period in (100, 250):
        for workers in (1, 4):
            cell = [r for r in rows if (r['period_ms'], r['workers']) == (period, workers)]
            slow = [r for r in cell if r['top1pct']]
            trial = [r for r in trial_rows if (float(r['period_ms']), int(r['workers'])) == (period, workers)]
            cells[period, workers] = (slow, trial)
            mean = lambda key: st.mean(r[key] for r in slow)
            report.append(f'| {period} ms | {workers} | '
                f'{st.mean(float(r["p50_e2e_ms"]) for r in trial):.1f} / '
                f'{st.mean(float(r["p99_e2e_ms"]) for r in trial):.1f} ms | '
                f'{mean("e2e_ms"):.1f} / {mean("outside_server_ms"):.1f} ms | '
                f'{mean("outside_share"):.1%} | {sum(r["high_phase"] for r in slow)}/{len(slow)} | '
                f'{mean("dispatch_lag_ms"):.3f} ms |')
    report += ['', '| Period | Workers | Slowest 1% mean queue / processing / post-work | '
               'Mean trial rejection / timeout | Mean throttled period fraction |',
               '|---:|---:|---:|---:|---:|']
    for (period, workers), (slow, trial) in cells.items():
        report.append(f'| {period} ms | {workers} | '
            f'{st.mean(r["queue_ms"] for r in slow):.1f} / '
            f'{st.mean(r["processing_ms"] for r in slow):.1f} / '
            f'{st.mean(r["post_work_ms"] for r in slow):.1f} ms | '
            f'{st.mean(float(r["rejection_fraction"]) for r in trial):.3%} / '
            f'{st.mean(float(r["timeout_fraction"]) for r in trial):.3%} | '
            f'{st.mean(float(r["throttled_period_fraction"]) for r in trial):.1%} |')
    report += ['', '| Period | Workers | Typical / slow mean queue depth at admission | '
               'Typical / slow mean write-to-first-byte | All successful requests in high phase |',
               '|---:|---:|---:|---:|---:|']
    for (period, workers), (slow, _) in cells.items():
        cell = [r for r in rows if (r['period_ms'], r['workers']) == (period, workers)]
        typical = [r for r in cell if r['typical']]
        report.append(f'| {period} ms | {workers} | '
            f'{st.mean(r["depth_at_admission"] for r in typical):.1f} / '
            f'{st.mean(r["depth_at_admission"] for r in slow):.1f} | '
            f'{st.mean(r["write_to_first_byte_ms"] for r in typical):.2f} / '
            f'{st.mean(r["write_to_first_byte_ms"] for r in slow):.2f} ms | '
            f'{st.mean(r["high_phase"] for r in cell):.1%} |')
    worst, _ = cells[100, 4]
    report += ['', 'Typical means the middle 40–60% of successful end-to-end latencies within each trial. '
        'Queue depth is an admission-time sample, not a continuous occupancy trace. '
        'High-phase counts should be read against the higher number of arrivals in that phase.', '',
        '## Location of the delay', '',
        f'The slowest successful requests in the 100 ms/four-worker cell average '
        f'{st.mean(r["e2e_ms"] for r in worst)/1000:.2f} s end to end and '
        f'{st.mean(r["outside_server_ms"] for r in worst)/1000:.2f} s outside the four measured server stages. '
        f'Mean request-write offset is {st.mean(r["request_write_ms"] for r in worst):.3f} ms; '
        f'mean first-byte-to-body-completion is {st.mean(r["body_after_first_byte_ms"] for r in worst):.3f} ms. '
        f'{sum(r["high_phase"] for r in worst)}/{len(worst)} selected requests were '
        'scheduled in the high-rate half of the burst.', '',
        'This audit cannot locate the remaining interval relative to handler entry or response writing. '
        'Client and server offsets have different monotonic origins and are never subtracted. '
        'Aggregate cgroup throttling does not identify the cause of an individual request.', '',
        'The trial CSV retains rejection and timeout fractions; they are not included in successful-request quantiles.', '']
    (out / 'completed_report.md').write_text('\n'.join(report))
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    values = [st.mean(float(r['p99_e2e_ms']) for r in trial_rows
                      if (float(r['period_ms']), int(r['workers'])) == cell)
              for cell in ((100, 1), (100, 4), (250, 1), (250, 4))]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(['100 ms / 1', '100 ms / 4', '250 ms / 1', '250 ms / 4'], values)
    ax.set_ylabel('Mean trial p99 end-to-end latency (ms)')
    ax.set_xlabel('CPU quota period / workers')
    ax.set_title('Completed diagnostic, five trials per condition')
    fig.tight_layout()
    fig.savefig(out / 'completed_p99.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    audit()
