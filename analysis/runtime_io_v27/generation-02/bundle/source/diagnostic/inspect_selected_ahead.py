#!/usr/bin/env python3
"""Attribute dispatches in audited, retained pre-handler ready waits.

This is observed execution ordering. Queue source and pending flags are absent.
"""
import argparse
from collections import Counter, defaultdict
from pathlib import Path

import inspect_long_wait_events as raw
import inspect_scheduler_handoffs as handoff
import run


def roles(rows, requests):
    known = defaultdict(set)
    for r in requests['all_requests']:
        for key, role in (('handler_g', 'http'), ('worker_g', 'worker')):
            if key in r:
                known[r[key]].add(role)
    for e in rows:
        # Stack is the actor's stack; TransitionStack belongs to the target.
        for g,stack in ((e['actor_g'],e.get('Stack','')),
                        (e.get('target_g',-1),e.get('TransitionStack',''))):
            if g<0: continue
            if 'runtime.traceAdvance' in stack:
                known[g].add('trace_advancer')
            if 'runtime.traceStartReadCPU' in stack:
                known[g].add('trace_cpu_reader')
            if 'runtime/trace.(*traceMultiplexer).startLocked.func1' in stack or 'runtime/trace.Start.func' in stack:
                known[g].add('trace_reader')
            if 'runtime.gcBgMarkWorker' in stack:
                known[g].add('gc_worker')
            if 'net/http.(*Server).Serve' in stack and 'net/http.(*conn).serve' not in stack:
                known[g].add('listener')
            if 'net/http.(*connReader).backgroundRead' in stack:
                known[g].add('http_background_reader')
    return {g: next(iter(v)) if len(v) == 1 else 'ambiguous' for g, v in known.items()}


def summarize(rows, example, known):
    begin, end, target = example['wake_ns'], example['run_ns'], example['target_g']
    actual = [e for e in rows if e.get('old') == 'Runnable' and e.get('new') == 'Running'
              and begin <= e['time_ns'] < end]
    if any(e['target_g'] == target for e in actual):
        raise ValueError('target ran inside its claimed ready wait')
    wakes = [e for e in rows if e.get('target_g') == target and e['time_ns'] == begin
             and e.get('old') == 'Waiting' and e.get('new') == 'Runnable']
    starts = [e for e in rows if e.get('target_g') == target and e['time_ns'] == end
              and e.get('old') == 'Runnable' and e.get('new') == 'Running']
    if len(wakes) != 1 or len(starts) != 1:
        raise ValueError('ready-wait boundaries are missing or ambiguous')
    by_g = Counter(e['target_g'] for e in actual)
    return dict(**example, dispatches=len(actual),
        by_role=dict(Counter(known.get(e['target_g'], 'unclassified') for e in actual)),
        by_p=dict(Counter(e['p'] for e in actual)), unique_selected_goroutines=len(by_g),
        selected_goroutines=[dict(g=g, role=known.get(g, 'unclassified'), dispatches=n)
                             for g, n in by_g.most_common()],
        same_p_handoffs=handoff.handoffs(rows, begin, end),
        dispatch_evidence=[dict(time_ns=e['time_ns'], g=e['target_g'], p=e['p'], m=e['m'],
                               line=e['line'], role=known.get(e['target_g'], 'unclassified')) for e in actual])


def inspect(output):
    if output.exists():
        raise ValueError('use a fresh output directory')
    prior = run.ROOT/'analysis/runtime_io_v9_investigation_20261003_final'
    provenance = run.read(prior/'provenance.json')['derived_files_and_sources_sha256']
    inputs = [prior/'ready_wait_examples.json', prior/'validation.json']
    for p in inputs:
        if run.sha(p) != provenance[str(p.relative_to(run.ROOT))]:
            raise ValueError('reviewed inputs changed')
    if not run.read(prior/'validation.json')['passed']:
        raise ValueError('prior review failed')
    examples = run.read(inputs[0]); results = []; hashes = {}
    for rid in sorted({e['run_id'] for e in examples}):
        audit = run.ROOT/'analysis/runtime_io_v9_timestamp_audit/v9'/rid
        summary = run.read(audit/'summary.json')
        dump = audit/'original_time.parsed.txt'
        attempt = Path(summary['attempt'])
        config=run.read(attempt/'config.json')
        if not run.validate(attempt,config,False):
            raise ValueError('sealed trial validation failed')
        if (not summary['original_time_chain_valid'] or not summary['output_matches_pinned']
            or run.sha(dump) != summary['source_sha256']['restored']
            or run.sha(attempt/'runtime.trace') != summary['source_sha256']['runtime_trace']):
            raise ValueError('timestamp-audited evidence changed')
        requests = run.read(audit/'original_time_requests.json')
        # Rebuild the request association from hashed evidence, not a cached join.
        import trace_analysis
        with dump.open() as stream:
            parsed = trace_analysis.parse_lines(stream)
        rebuilt = trace_analysis.build_analysis(run.read(attempt/'trace_status.json'),
            run.read(attempt/'loadgen.json'), run.read(attempt/'server_metrics.json'), parsed)
        if requests != rebuilt or not rebuilt['complete']:
            raise ValueError('request association differs from raw evidence')
        rows = [e for e in raw.events(dump) if e is not None]
        known = roles(rows, rebuilt)
        for e in examples:
            if e['run_id'] == rid:
                results.append(summarize(rows, e, known))
        hashes[rid] = dict(dump=run.sha(dump), audit_summary=run.sha(audit/'summary.json'),
            **{n: run.sha(attempt/n) for n in ('runtime.trace','trace_status.json','loadgen.json','server_metrics.json')})
        print('ATTRIBUTED', rid, flush=True)
    output.mkdir(parents=True)
    run.put(output/'selected_ahead.json', dict(examples=results, eligible_for_full=False))
    lines = ['# Work dispatched ahead of delayed HTTP handlers', '',
        'All 24 previously matched pre-handler examples use the audited original-time traces. '
        'The intervals overlap; counts must not be added across examples.', '',
        '| Trial | HTTP G | Next request | Ready wait ms | Dispatches | Worker | HTTP | Other/unclassified | Worker-reply handoffs |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for e in results:
        c=e['by_role']; other=e['dispatches']-c.get('worker',0)-c.get('http',0)
        lines.append(f'| {e["run_id"]} | {e["target_g"]} | {e["next_request_id"]} | '
            f'{e["latency_ns"]/1e6:.3f} | {e["dispatches"]} | {c.get("worker",0)} | '
            f'{c.get("http",0)} | {other} | {e["same_p_handoffs"]["counts"].get("worker_reply_handoffs",0)} |')
    lines += ['', 'The JSON retains every dispatch timestamp, G, M, P and source line, '
        'plus per-goroutine counts and same-P handoff examples. Roles come from request-task '
        'associations and runtime/HTTP stacks; unmatched goroutines stay unclassified.', '',
        'Dispatch means Runnable→Running, not continuous CPU execution. Work can already '
        'be running when the target wakes. These traces show what got turns, but do not '
        'record the pending flag or global/local/runnext selection branch. The v10 aggregate '
        'counters cannot be joined retrospectively to these v9 requests.', '',
        'A separate bounded decision recorder is needed to associate an actual fairness '
        'selection with a delayed HTTP G in the untraced workload. No correction, '
        'qualification gate or new performance collection is introduced.', '']
    (output/'report.md').write_text('\n'.join(lines))
    run.put(output/'provenance.json', dict(inputs=hashes,
        sources={str(p.relative_to(run.ROOT)):run.sha(p) for p in
                 (Path(__file__), Path(raw.__file__), Path(handoff.__file__))},
        reviewed_inputs={str(p):run.sha(p) for p in inputs}, eligible_for_full=False))
    run.put(output/'validation.json', dict(passed=True, examples=len(results),
        original_times_used=True, all_boundaries_matched=True, eligible_for_full=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=run.ROOT/'analysis/runtime_io_v11_selected_ahead')
    inspect(parser.parse_args().output.resolve())
