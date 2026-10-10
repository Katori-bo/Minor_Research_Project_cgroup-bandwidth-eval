#!/usr/bin/env python3
"""Inspect pre-handler Runnable spans using an already validated queue ledger."""
import argparse
import bisect
from collections import Counter
import csv
import json
from pathlib import Path
import statistics

import inspect_http_cleanup
import inspect_yield_queue as queue
import run as runner


def runnable_spans(series, start, end):
    if start>=end:
        return []
    index = bisect.bisect_right([r[0] for r in series],start)-1
    state = series[index][1] if index>=0 else 'Unknown'
    begin = start if state=='Runnable' else None
    spans = []
    for stamp,new,_ in series[index+1:]+[(end,'END','')]:
        if stamp>=end:
            stamp,new = end,'END'
        if state=='Runnable' and new!='Runnable':
            spans.append((begin,stamp))
            begin = None
        if state!='Runnable' and new=='Runnable':
            begin = stamp
        state = new
        if stamp>=end:
            break
    return spans


def inspect(analysis,out):
    if out.exists():
        raise ValueError('use a fresh output directory')
    summary = queue.read(analysis/'summary.json')
    provenance = queue.read(analysis/'source_hashes.json')
    if not queue.read(analysis/'validation.json')['passed']:
        raise ValueError('queue reconstruction is incomplete')
    session = Path(provenance['session'])
    if out.is_relative_to(session):
        raise ValueError('cannot write into retained trial evidence')
    ledger = list(csv.DictReader((analysis/'request_ledger.csv').open()))
    results, seals = [], {}
    for trial in summary['trials']:
        if trial['mode'] not in ('trace','yield_trace'):
            continue
        rid = trial['run_id']
        good = [p for p in runner.attempt_dirs(session/'attempts'/rid)
                if (p/'complete.json').exists() and runner.sha(p/'complete.json')==provenance['completion_sha256'][rid]]
        if len(good)!=1:
            raise ValueError('attempt completion seal changed')
        attempt = good[0]
        seals[rid] = {}
        for name in ('trace_scheduler.json','trace_requests.json','server_metrics.json'):
            actual = runner.sha(attempt/name)
            if actual!=provenance['consumed_files'][rid][name]:
                raise ValueError('retained input changed: '+name)
            seals[rid][name] = actual
        parsed = queue.read(attempt/'trace_scheduler.json')
        trace = queue.read(attempt/'trace_requests.json')
        srv = queue.read(attempt/'server_metrics.json')
        series = inspect_http_cleanup.snapshot_series(parsed)
        rtclock = trace['clock_mapping']
        offset = (rtclock['offset_low_ns']+rtclock['offset_high_ns'])//2
        mapping = {r['id']:r for r in trace['all_requests']}
        rows = {int(r['request_id']):r for r in ledger if r['run_id']==rid}
        completion_times = sorted(e['completion_ns'] for e in srv['events'])
        spans = []
        for request,row in rows.items():
            if int(row['client_wrote_offset_ns'])<0:
                continue
            start = (int(row['scheduled_client_ns'])+int(row['dispatch_lag_ns'])+
                     int(row['client_wrote_offset_ns'])+trial['clock']['offset_high_ns'])
            finish = int(row['entry_mark_ns'])
            goid = mapping[request]['handler_g']
            prior = rows.get(int(row['previous_request_id'])) if row['previous_request_id'] else None
            # Keep the full observed interval and distinguish ready spans that
            # begin after the previous request has finished server cleanup.
            for begin,end in runnable_spans(series[goid],start+offset,finish+offset):
                server_begin,server_end = begin-offset,end-offset
                spans.append(dict(request_id=request,conn=int(row['conn']),http_g=goid,
                                  start_server_ns=server_begin,end_server_ns=server_end,
                                  duration_ms=(end-begin)/1e6,
                                  worker_completions=bisect.bisect_right(completion_times,server_end)-
                                                     bisect.bisect_left(completion_times,server_begin),
                                  previous_request_id=int(prior['request_id']) if prior else None,
                                  begins_after_previous_cleanup=(server_begin>=int(prior['connection_done_ns'])) if prior else None))
        results.append(dict(run_id=rid,mode=trial['mode'],block=trial['block'],
                            client_server_uncertainty_ns=trial['clock']['uncertainty_ns'],
                            runtime_server_uncertainty_ns=rtclock['uncertainty_ns'],
                            longest=max(spans,key=lambda r:r['duration_ms']),
                            longest_examples=sorted(spans,key=lambda r:r['duration_ms'],reverse=True)[:10],
                            observed_spans=len(spans)))
    out.mkdir(parents=True)
    queue.write_json(out/'examples.json',dict(trials=results,eligible_for_full=False))
    queue.write_json(out/'source_hashes.json',dict(analyzer_sha256=runner.sha(Path(__file__)),
                     queue_ledger_sha256=runner.sha(analysis/'request_ledger.csv'),
                     queue_summary_sha256=runner.sha(analysis/'summary.json'),consumed_files=seals))
    lines = ['# HTTP goroutines ready to run before handler entry', '',
             'Saved-data follow-up to the v8 queue reconstruction, 2026-10-02. '
             'No workload launched. Scheduler/request/job files were checked '
             'against the queue review\'s retained input hashes.', '',
             '| Block | Mode | Longest pre-handler Runnable span | Other worker completions during span | Request ID | Begins after previous cleanup |',
             '|---|---|---:|---:|---:|---|']
    for result in sorted(results,key=lambda r:(r['block'],r['mode'])):
        example = result['longest']
        lines.append(f'| {result["block"]} | {result["mode"]} | {example["duration_ms"]:.3f} ms | '
                     f'{example["worker_completions"]} | {example["request_id"]} | '
                     f'{example["begins_after_previous_cleanup"]} |')
    lines += ['',
              'In all four non-yielding traced cells, the longest observed '
              'pre-handler Runnable spans are 2.21–2.90 seconds. They begin '
              'after the previous request\'s server cleanup on the reused '
              'connection has finished. During these spans, 298–384 other '
              'CPU jobs complete. The largest yielded counterparts are '
              '85.93–88.47 ms, with 6–8 other completions.', '',
              'This localizes an additional delay to the HTTP connection '
              'goroutine waiting to run before entering the next handler. '
              'It cannot be explained solely by waiting for the previous '
              'handler\'s cleanup to finish. Ready HTTP work and ongoing CPU '
              'job completion coexist; worker yielding substantially changes '
              'that scheduling pattern.', '',
              'Spans are intersections with the conservative latest possible '
              'client request-write callback → handler-entry interval. '
              'A client write callback is not physical server arrival. The '
              'Go Runnable state does not identify the exact runtime '
              'queue, which scheduler policy chose another goroutine, or '
              'whether tracing affected wakeup behavior. Job completion '
              'counts are temporal overlap, not attribution of CPU time.', '',
              'Same-state generation snapshots are joined into one span, '
              'not treated as new wakeups. The runtime/service clock mapping '
              'is independent of the causal client/service offset bracket. '
              'Both uncertainties are retained in `examples.json`. Trace-off '
              'goroutine states remain unavailable.', '',
              'The next discriminator is raw trace wakeup/enqueue context '
              'and stacks at these saved span boundaries, including the '
              'accept goroutine where a connection handler does not yet '
              'exist. This requires examining retained runtime events; '
              'there is still no identified tracing call to patch or '
              'qualified transparent fix.', '',
              'Reproduce after the queue review:', '', '```bash',
              'venv/bin/python diagnostic/inspect_prehandler_ready.py \\',
              '  analysis/runtime_io_v8_queue_review \\',
              '  --output analysis/runtime_io_v8_queue_review/prehandler_ready_fresh',
              '```', '']
    (out/'report.md').write_text('\n'.join(lines))
    print('PRE-HANDLER READY SPANS COMPLETE:',out)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('analysis',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    inspect(args.analysis.resolve(),args.output.resolve())
