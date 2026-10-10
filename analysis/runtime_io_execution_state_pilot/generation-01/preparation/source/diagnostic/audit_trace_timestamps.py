#!/usr/bin/env python3
"""Audit decoder fixups and derive an explicitly separate original-time dump.

The audit reader logs the time before its monotonic fixup without changing the
ordinary parsed output. Exact output equality to the pinned decoder is required.
No frozen evidence or qualification status is modified.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import inspect_http_cleanup as cleanup
import trace_analysis as trace
import run

TIME = re.compile(r'^RESEARCH_TIME raw=(\d+) decoded=(\d+) kind=(\w+)$')


def restore(blocks, timings):
    blocks, timings = list(blocks), list(timings)
    if len(blocks) != len(timings):
        raise ValueError('audit event count differs from parsed output')
    corrected, changes, dropped = [], [], Counter()
    for ordinal, (block, timing) in enumerate(zip(blocks, timings)):
        header, clock = trace.HEADER.match(block[0]), TIME.match(timing.strip())
        if not header or not clock or header[2] != clock[3] or int(header[3]) != int(clock[2]):
            raise ValueError('audit ledger does not match parsed event')
        raw, decoded = int(clock[1]), int(clock[2])
        if raw != decoded:
            changes.append(dict(event_index=ordinal, raw_ns=raw, decoded_ns=decoded,
                                adjustment_ns=decoded-raw, header=block[0].strip()))
        transition = trace.TRANSITION.search(header[4]) if header[2] == 'StateTransition' else None
        # Census repeats describe an existing state, not a new transition. They
        # can be emitted after other-generation events, so do not manufacture
        # timeline state changes from their position in the reader's output.
        if transition and transition[2] == transition[3]:
            dropped['same_state_census'] += 1
            continue
        block = list(block)
        block[0] = block[0].replace('Time=' + header[3], 'Time=' + str(raw), 1)
        corrected.append((raw, ordinal, block))
    corrected.sort(key=lambda row: (row[0], row[1]))
    return corrected, changes, dict(dropped)


def audit(attempt, baseline, decoder, output):
    output.mkdir(parents=True, exist_ok=False)
    ordinary, ledger = output/'ordinary.parsed.txt', output/'timestamp_ledger.txt'
    # Sync wall-clock formatting follows TZ; align formatting to the saved dump
    # without changing any trace timestamp or decoder ordering.
    with baseline.open() as stream:
        first_line = stream.readline()
    env = dict(os.environ)
    if re.search(r'Wall=\S+Z(?:\s|$)', first_line):
        env['TZ'] = 'UTC'
    with ordinary.open('w') as stdout, ledger.open('w') as stderr:
        subprocess.run([str(decoder), '-d=parsed', str(attempt/'runtime.trace')],
                       stdout=stdout, stderr=stderr, check=True, env=env)
    if run.sha(ordinary) != run.sha(baseline):
        raise ValueError('audit decoder differs from pinned parsed output')
    with ordinary.open() as stream, ledger.open() as timing:
        corrected, changes, dropped = restore(cleanup.blocks(stream), timing)
    restored = output/'original_time.parsed.txt'
    with restored.open('w') as stream:
        for _, _, block in corrected:
            stream.writelines(block)
    with restored.open() as stream:
        parsed = trace.parse_lines(stream)
    issues = []
    try:
        trace.scheduler_series(parsed)
    except ValueError as exc:
        issues.append(str(exc))
    status = run.read(attempt/'trace_status.json')
    try:
        mapping = trace.clock_map(status['clock_anchors'], parsed['anchors'])
    except ValueError as exc:
        issues.append(str(exc)); mapping = None
    summary = dict(attempt=str(attempt), output_matches_pinned=True,
        original_time_chain_valid=not issues, issues=issues,
        adjusted_events=len(changes), adjustments_over_1ms=sum(c['adjustment_ns']>1_000_000 for c in changes),
        maximum_adjustment_ns=max((c['adjustment_ns'] for c in changes), default=0),
        dropped=dropped, clock_mapping=mapping,
        adjustments_by_kind=dict(Counter(trace.HEADER.match(c['header'])[2] for c in changes)),
        largest_adjustments=sorted(changes, key=lambda c:c['adjustment_ns'], reverse=True)[:20],
        source_sha256=dict(runtime_trace=run.sha(attempt/'runtime.trace'), baseline=run.sha(baseline),
                          audit_decoder=run.sha(decoder), ledger=run.sha(ledger), restored=run.sha(restored)),
        eligible_for_full=False)
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    (output/'adjustments.json').write_text(json.dumps(changes, indent=2)+'\n')
    print(attempt.parent.name, 'max adjustment ms', summary['maximum_adjustment_ns']/1e6,
          'raw-time chain', 'PASS' if not issues else issues, flush=True)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--decoder', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audit(args.attempt.resolve(), args.baseline.resolve(), args.decoder.resolve(), args.output.resolve())
