#!/usr/bin/env python3
"""Read the sealed follow-up results without changing them."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'results/followup/all-in-one-v2/full'
OUT = Path(__file__).resolve().parent


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * fraction) - 1]


def main():
    rows = list(csv.DictReader((SOURCE / 'analysis/trials.csv').open()))
    audit = list(csv.DictReader((SOURCE / 'analysis/attempt_audit.csv').open()))
    if len(rows) != 50 or any(r['valid'] != 'True' for r in audit):
        raise RuntimeError('Expected fifty validated source trials')
    details = []
    source_hashes = {'analysis/trials.csv': hashlib.sha256((SOURCE / 'analysis/trials.csv').read_bytes()).hexdigest(),
                     'analysis/attempt_audit.csv': hashlib.sha256((SOURCE / 'analysis/attempt_audit.csv').read_bytes()).hexdigest()}
    for row in rows:
        attempt = SOURCE / 'attempts' / row['run_id'] / row['attempt']
        source_hashes[str((attempt / 'complete.json').relative_to(SOURCE))] = hashlib.sha256(
            (attempt / 'complete.json').read_bytes()).hexdigest()
        seal = json.loads((attempt / 'complete.json').read_text())
        for filename, expected in seal['files'].items():
            actual = hashlib.sha256((attempt / filename).read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError(f'Changed source evidence: {attempt / filename}')
        lg = json.loads((attempt / 'loadgen.json').read_text())
        srv = json.loads((attempt / 'server_metrics.json').read_text())
        events = {event['id']: event for event in srv['events']}
        good = [q for q in lg['requests'] if q['StatusCode'] == 200 and not q['Error']]
        if len(good) != int(row['success']):
            raise RuntimeError(f'Success count mismatch: {row["run_id"]}')
        records = []
        for q in good:
            event = events.get(q['ID'])
            if not q['ServerTimingPresent'] or event is None:
                raise RuntimeError(f'Missing timing match: {row["run_id"]} request {q["ID"]}')
            if (q['QueueWaitNs'], q['ProcessingNs']) != (event['queue_wait_ns'], event['processing_ns']):
                raise RuntimeError(f'Timing mismatch: {row["run_id"]} request {q["ID"]}')
            remainder = q['EndToEndLatencyNs'] - q['QueueWaitNs'] - q['ProcessingNs']
            if remainder < 0:
                raise RuntimeError(f'Negative remainder: {row["run_id"]} request {q["ID"]}')
            records.append((q, remainder))
        by_latency = sorted(records, key=lambda item: item[0]['EndToEndLatencyNs'], reverse=True)
        top = by_latency[:max(1, math.ceil(len(by_latency) * .01))]
        remainders = [r for _, r in records]
        top_remainders = [r for _, r in top]
        burst_seconds = [0, 0]
        for q, _ in top:
            phase = (q['ScheduledOffsetNs'] / 1e9) % 10
            burst_seconds[int(phase >= 5)] += 1
        details.append(dict(run_id=row['run_id'], period_ms=row['period_ms'], workers=row['workers'],
                            pattern=row['pattern'], study=row['study'], success=len(good),
                            p99_e2e_ms=quantile([q['EndToEndLatencyNs'] for q, _ in records], .99) / 1e6,
                            p99_remainder_ms=quantile(remainders, .99) / 1e6,
                            top1pct_e2e_mean_ms=statistics.mean(q['EndToEndLatencyNs'] for q, _ in top) / 1e6,
                            top1pct_remainder_mean_ms=statistics.mean(top_remainders) / 1e6,
                            top1pct_remainder_fraction=statistics.mean(r / q['EndToEndLatencyNs'] for q, r in top),
                            top1pct_low_phase=burst_seconds[0], top1pct_high_phase=burst_seconds[1],
                            top1pct_mean_dispatch_lag_ms=statistics.mean(q['DispatchLagNs'] for q, _ in top) / 1e6,
                            top1pct_mean_completed_offset_s=statistics.mean(q['CompletedOffsetNs'] for q, _ in top) / 1e9,
                            p99_dispatch_lag_ms=quantile([q['DispatchLagNs'] for q, _ in records], .99) / 1e6,
                            throttled_period_fraction=row['throttled_period_fraction'],
                            rejection_fraction=row['rejection_fraction'], timeout_fraction=row['timeout_fraction']))
    OUT.mkdir(exist_ok=True)
    (OUT / 'existing_source_hashes.json').write_text(json.dumps(source_hashes, indent=2, sort_keys=True) + '\n')
    with (OUT / 'existing_trials.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    lines = ['# Existing follow-up: request timing audit', '',
             'Source: `results/followup/all-in-one-v2/full/`. All 50 accepted attempts were checked against their completion file hashes. Each successful client request was matched to its server event by ID.',
             '', 'The remainder is calculated **for each request**: end-to-end latency minus server queue wait minus elapsed processing. It contains client dispatch, HTTP handling, transport and response completion time. It does not identify which of these caused the delay.',
             '', '| Study B bursty condition | Mean trial p99 end-to-end | Mean trial p99 remainder | Mean remainder share among slowest 1% |',
             '|---|---:|---:|---:|']
    for period in ('100.0', '250.0'):
        for workers in ('1', '4'):
            group = [d for d in details if d['study'] == 'B' and d['pattern'] == 'bursty' and
                     d['period_ms'] == period and d['workers'] == workers]
            lines.append(f'| {period} ms, {workers} worker(s) | '
                         f'{statistics.mean(d["p99_e2e_ms"] for d in group):.1f} ms | '
                         f'{statistics.mean(d["p99_remainder_ms"] for d in group):.1f} ms | '
                         f'{statistics.mean(d["top1pct_remainder_fraction"] for d in group):.1%} |')
    worst = [d for d in details if d['study'] == 'B' and d['pattern'] == 'bursty' and
             d['period_ms'] == '100.0' and d['workers'] == '4']
    lines += ['', 'These p99 summaries are means of trial-level p99 values. The remainder p99 and end-to-end p99 select different requests; they must not be subtracted from one another.',
              '', f'In the 100 ms/four-worker cell, the mean dispatch lag among the slowest 1% was {statistics.mean(d["top1pct_mean_dispatch_lag_ms"] for d in worst):.3f} ms. '
              f'Their scheduled arrivals were split {sum(d["top1pct_low_phase"] for d in worst)} in low-rate halves and '
              f'{sum(d["top1pct_high_phase"] for d in worst)} in high-rate halves. '
              'These aggregate phase counts do not identify the delayed stage.',
              '', 'The existing client timing begins at scheduled dispatch and ends after the response body is consumed. Server timing begins just before enqueue and ends when SHA work finishes. The service handler then awaits the worker reply and writes the response. Neither the handler wait after work nor client HTTP phases are separately timed in these results.',
              '', 'Next diagnostic: measure handler entry-to-admission, work-finish-to-handler-resume, and client request-written-to-first-byte and body-read intervals using durations within each process. Cross-process timestamp subtraction is invalid. These measurements can narrow the remaining duration; aggregate cgroup counters alone cannot assign it to a request.', '']
    (OUT / 'existing_report.md').write_text('\n'.join(lines))
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib unavailable; wrote CSV and report without figure')
    else:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        labels = []
        for index, (period, workers) in enumerate(((100., 1), (100., 4), (250., 1), (250., 4))):
            group = [d for d in details if d['study'] == 'B' and d['pattern'] == 'bursty' and
                     float(d['period_ms']) == period and int(d['workers']) == workers]
            for offset, field, marker in ((-.10, 'p99_e2e_ms', 'o'), (.10, 'p99_remainder_ms', 'x')):
                ax.scatter([index + offset] * len(group), [d[field] for d in group],
                           marker=marker, alpha=.8, color='#225d87' if marker == 'o' else '#b04a35',
                           label=('End-to-end p99' if marker == 'o' else 'Remainder p99') if index == 0 else None)
            labels.append(f'{int(period)} ms / {workers} worker' + ('s' if workers > 1 else ''))
        ax.set_xticks(range(4), labels, rotation=15, ha='right')
        ax.set_ylabel('Trial p99 (ms)')
        ax.set_title('Completed follow-up: bursty traffic, all five trials per condition')
        ax.legend()
        ax.grid(axis='y', alpha=.2)
        fig.tight_layout()
        fig.savefig(OUT / 'existing_bursty_p99.png', dpi=180)
        fig.savefig(OUT / 'existing_bursty_p99.pdf')
        plt.close(fig)
    print(OUT / 'existing_report.md')


if __name__ == '__main__':
    main()
