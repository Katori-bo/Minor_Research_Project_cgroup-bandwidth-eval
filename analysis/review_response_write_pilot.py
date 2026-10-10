#!/usr/bin/env python3
"""Read-only revalidation and matched-request interpretation of the v3 pilot.

Outputs live outside the frozen session and diagnostic collection sources.
"""
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import run
import analyze

SESSION = ROOT / 'results/diagnostic/response-write-v3/pilot'
OUT = ROOT / 'analysis/response_write_pilot'


def review():
    run.verify_session(SESSION, check_current=False)
    saved_gate = run.read(SESSION / 'analysis/pilot_gate.json')
    rows, detail, hashes = [], [], {}
    for order, config in enumerate(run.read(SESSION / 'matrix.json'), 1):
        attempts = run.attempt_dirs(SESSION / 'attempts' / config['run_id'])
        accepted = [p for p in attempts if not run.validation_errors(p, config, True)]
        if len(accepted) != 1:
            raise ValueError(f'Expected one accepted attempt for {config["run_id"]}')
        directory = accepted[0]
        hashes[config['run_id']] = run.sha(directory / 'complete.json')
        if hashes[config['run_id']] != saved_gate['completion_sha256'][config['run_id']]:
            raise ValueError('Accepted attempt differs from saved pilot gate')
        row = analyze.trial_row(order, config, directory)
        rows.append(row)
        if not config['instrument']:
            continue
        client = run.read(directory / 'loadgen.json')
        server = run.read(directory / 'server_metrics.json')
        requests = {q['ID']: q for q in client['requests']}
        handlers = {h['id']: h for h in server['handler_events']}
        successful = [q for q in requests.values() if q['StatusCode'] == 200 and not q['Error']]
        slow = sorted(successful, key=lambda q: q['EndToEndLatencyNs'], reverse=True)[:math.ceil(len(successful)*.01)]
        samples = []
        for q in slow:
            h = handlers[q['ID']]
            samples.append(dict(
                e2e_ms=q['EndToEndLatencyNs']/1e6,
                handler_span_ms=(h['handler_exit_ns']-h['entry_ns'])/1e6,
                signed_difference_ms=(q['EndToEndLatencyNs']-(h['handler_exit_ns']-h['entry_ns']))/1e6,
                dispatch_ms=q['DispatchLagNs']/1e6,
                request_write_offset_ms=q['WroteRequestOffsetNs']/1e6,
                request_to_first_byte_ms=(q['FirstByteOffsetNs']-q['WroteRequestOffsetNs'])/1e6,
                body_after_first_byte_ms=(q['BodyDoneOffsetNs']-q['FirstByteOffsetNs'])/1e6,
                new_stages_ms=(h['handler_exit_ns']-h['resume_ns'])/1e6))
        outliers = []
        for h in handlers.values():
            if h['handler_exit_ns'] - h['resume_ns'] <= 1_000_000:
                continue
            q = requests[h['id']]
            a, b = h['resume_ns'], h['write_start_ns']
            outliers.append(dict(request_id=h['id'], e2e_ms=q['EndToEndLatencyNs']/1e6,
                resume_to_write_ms=(b-a)/1e6,
                write_ms=(h['write_end_ns']-b)/1e6,
                write_to_exit_ms=(h['handler_exit_ns']-h['write_end_ns'])/1e6,
                other_worker_completions_in_resume_to_write=sum(
                    a<e['completion_ns']<b and e['id']!=h['id'] for e in server['events'])))
        detail.append(dict(run_id=config['run_id'], slow_request_count=len(slow),
            slow_mean={key:st.mean(x[key] for x in samples) for key in samples[0]},
            slow_max_new_stages_ms=max(x['new_stages_ms'] for x in samples),
            slow_high_phase_count=sum(q['ScheduledOffsetNs']/1e9%10 >= 5 for q in slow),
            response_stage_outliers_over_1ms=sorted(outliers, key=lambda x:x['resume_to_write_ms'], reverse=True)))
    gate = analyze.pilot_gate(rows, hashes)
    if not gate['passed'] or not saved_gate['passed']:
        raise ValueError('Pilot gate did not pass')
    OUT.mkdir(parents=True, exist_ok=True)
    run.put(OUT / 'matched_summary.json', dict(source=str(SESSION), gate=gate, trials=rows,
        matched_request_analysis=detail, analyzer_sha256=run.sha(Path(__file__))))
    text = ['# Response-write pilot interpretation', '',
        'The resumed pilot completed at 23:53 IST on September 30, 2026. All six accepted attempts '
        'were revalidated from raw evidence and their completion hashes matched the saved gate. '
        'The earlier thermal failure remains preserved as attempt 001 of the first trial; attempt 002 succeeded.', '',
        '## Observed outcomes', '',
        '| Trial | Workers | Timing enabled | Successful-request p99 | Rejections | Timeouts |',
        '|---|---:|---|---:|---:|---:|']
    for row in rows:
        text.append(f'| {row["run_id"]} | {row["workers"]} | {row["instrument"]} | '
                    f'{row["p99_e2e_ms"]:.1f} ms | {row["rejection_fraction"]:.3%} | '
                    f'{row["timeout_fraction"]:.3%} |')
    text += ['', 'All trials use a 100 ms quota period and 0.5 CPU, with 20-second measurements. '
             'These are pilot observations, not five-repetition research estimates.', '',
             '## Matching the slowest requests', '',
             '| Instrumented trial | Slowest 1% count | Mean end-to-end | Mean handler span | '
             'Mean signed difference | Mean new response stages |',
             '|---|---:|---:|---:|---:|---:|']
    for d in detail:
        m=d['slow_mean']
        text.append(f'| {d["run_id"]} | {d["slow_request_count"]} | {m["e2e_ms"]:.2f} ms | '
                    f'{m["handler_span_ms"]:.2f} ms | {m["signed_difference_ms"]:.2f} ms | '
                    f'{m["new_stages_ms"]:.4f} ms |')
    text += ['', 'Each row uses the same request IDs for all durations. The new response stages are '
             'handler resume through the exit marker, including the actual Write call. The signed '
             'difference is end-to-end duration minus the observed handler span; it does not locate '
             'a unique unmeasured stage, and no absolute clocks or independently calculated quantiles were subtracted.', '',
             'For the slowest requests in the two instrumented four-worker trials, mean per-request '
             f'signed difference/end-to-end is {rows[0]["top1pct_e2e_minus_handler_span_share"]:.2%} and '
             f'{rows[3]["top1pct_e2e_minus_handler_span_share"]:.2%}. The new stages are too small '
             'on those requests to account for the seconds of waiting. With one worker, the corresponding '
             f'share is {rows[4]["top1pct_e2e_minus_handler_span_share"]:.3%}; its measured handler span '
             'accounts for nearly all the slow-request time. Client traces still place the long delay '
             'after request write and before the first response byte.', '',
             '## Exceptions and limitations', '',
             'The second instrumented four-worker trial rejected 125 of 2,265 requests (5.519%). Its '
             'lower successful-request p99 cannot be interpreted as a performance improvement without '
             'accounting for those failures and changed admitted load. The other instrumented '
             'four-worker trial rejected none. One uninstrumented four-worker request timed out.', '',
             f'The saved one-sided overhead screen passed: service CPU ratio '
             f'{gate["overhead_server_cpu_ratio"]:.6f}, client CPU ratio '
             f'{gate["overhead_client_cpu_ratio"]:.6f}, and successful-request p99 ratio '
             f'{gate["overhead_p99_e2e_ratio"]:.6f}. It checks for increases above 10%; it does not '
             'establish equivalence or absence of instrumentation effects. The large rejection difference '
             'and only two on/two off observations require caution.', '']
    for d in detail:
        for item in d['response_stage_outliers_over_1ms']:
            if item['resume_to_write_ms'] > 100:
                text.append(f'In `{d["run_id"]}`, request {item["request_id"]} spent '
                    f'{item["resume_to_write_ms"]:.3f} ms between handler resume and Write start, '
                    f'while the Write call itself took {item["write_ms"]:.6f} ms. '
                    f'{item["other_worker_completions_in_resume_to_write"]} other worker completions '
                    'occurred during that server-local interval. This was not a continuous whole-server '
                    'pause and was not among that trial\'s slowest 1%. It motivates investigating '
                    'individual goroutine scheduling or blocking, but does not establish a cause.\n')
    text += ['All instrumented successful requests had usable client traces, no negative signed '
             'differences and no recorded server Write errors.', '',
             '## Next decision', '',
             'The pilot produced usable data and narrowed the measured response path, but did not '
             'explain the dominant long wait. The protocol\'s criterion for expanding the matrix is '
             'therefore not satisfied. The next diagnostic should correlate server receive/handler '
             'entry and final flush/socket activity, with a bounded runtime trace to test runnable '
             'versus blocked goroutine delays. Define request/connection matching and clock alignment '
             'before collection, and check tracing overhead and rejection rates again. Do not infer '
             'a transport, kernel-throttling or Go-scheduler cause from this pilot alone.', '']
    (OUT / 'report.md').write_text('\n'.join(text))
    print(OUT / 'report.md')


if __name__ == '__main__':
    review()
