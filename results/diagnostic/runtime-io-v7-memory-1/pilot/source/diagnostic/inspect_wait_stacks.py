#!/usr/bin/env python3
"""Join saved post-handler waits to raw Go transition stacks without editing a trial."""
import argparse
import collections
import json
from pathlib import Path
import re
import subprocess
import tempfile
import trace_analysis
import run


def inspect(attempt):
    requests = run.read(attempt / 'trace_requests.json')
    parsed = run.read(attempt / 'trace_scheduler.json')
    mapping = requests['clock_mapping']
    offset = (mapping['offset_low_ns'] + mapping['offset_high_ns']) // 2
    windows = collections.defaultdict(list)
    for row in requests['all_requests']:
        span = row['intervals'].get('handler_exit_to_connection_done')
        if span:
            windows[str(span['goroutine'])].append((span['start_ns']+offset,span['end_ns']+offset))
    waits = {}
    for g, transitions in parsed['transitions'].items():
        for i, event in enumerate(transitions[:-1]):
            stamp, old, new, reason = event
            if new != 'Waiting': continue
            duration = sum(max(0,min(end,transitions[i+1][0])-max(begin,stamp))
                           for begin,end in windows[g])
            if duration: waits[g,stamp] = duration
    totals, counts = collections.Counter(), collections.Counter()
    writer_events = 0
    def consume(lines):
        nonlocal writer_events
        if not lines: return
        header = trace_analysis.HEADER.match(lines[0])
        if not header: return
        if any('main.(*cappedWriter).Write' in line for line in lines): writer_events += 1
        if header[2] != 'StateTransition': return
        transition = trace_analysis.TRANSITION.search(header[4])
        if not transition: return
        duration = waits.get((transition[1],int(header[3])))
        if not duration: return
        stack, inside = [], False
        for line in lines[1:]:
            if line.startswith('TransitionStack='): inside = True; continue
            if inside and line.startswith('Stack='): break
            if inside and line.strip(): stack.append(line.strip())
        key = '\n'.join(stack) or '(no transition stack)'
        totals[key] += duration
        counts[key] += 1
    command = ['docker','run','--rm','-v',f'{attempt}:/trace:ro','golang:1.26.1-alpine',
               'go','tool','trace','-d=parsed','/trace/runtime.trace']
    with tempfile.TemporaryFile(mode='w+') as errors:
        proc = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors,text=True)
        try:
            lines=[]
            for line in proc.stdout:
                if trace_analysis.HEADER.match(line): consume(lines); lines=[]
                lines.append(line)
            consume(lines)
            if proc.wait():
                errors.seek(0); raise RuntimeError(errors.read())
        finally:
            proc.stdout.close()
            if proc.poll() is None: proc.kill(); proc.wait()
    return dict(attempt=str(attempt),runtime_sha256=run.sha(attempt/'runtime.trace'),
                mapping_uncertainty_ns=mapping['uncertainty_ns'],
                scope='Waiting states intersecting handler_exit_to_connection_done; midpoint clock mapping',
                waits=[dict(stack=stack,overlap_ns=ns,transition_count=counts[stack])
                       for stack,ns in totals.most_common()],
                events_with_capped_writer_stack=writer_events,
                limits='Overlapping waits across goroutines are summed, not elapsed wall time. Stack occurrence counts are not CPU cost. Go Running does not prove OS CPU execution.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    attempt,output=args.attempt.resolve(),args.output.resolve()
    if output.is_relative_to(attempt): parser.error('output must be outside the sealed attempt')
    result=inspect(attempt)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(output)
