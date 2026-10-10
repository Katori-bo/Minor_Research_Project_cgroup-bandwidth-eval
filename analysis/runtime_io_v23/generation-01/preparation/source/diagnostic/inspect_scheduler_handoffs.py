#!/usr/bin/env python3
"""Inspect same-P handoff sequences in the previously validated long windows.

This describes observed ordering, not scheduler queue placement or CPU time.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import inspect_long_wait_events as raw_events
import inspect_yield_queue as queue
import run as runner


def handoffs(rows, begin, end):
    pending, running, exits, previous_dispatch = {}, {}, {}, {}
    counts, examples = Counter(), []
    for e in rows:
        if 'target_g' not in e or e['old']==e['new']:
            continue
        g, stamp, p = e['target_g'], e['time_ns'], e['p']
        if e['new']=='Runnable' and e['old'] in ('Waiting','NotExist'):
            pending[g] = e
        if e['old']=='Running':
            start = running.pop(g, None)
            if p>=0 and start is not None:
                exits[p] = (e, start)
        if e['old']=='Runnable' and e['new']=='Running':
            wake, previous = pending.pop(g,None), exits.get(p)
            if begin<=stamp<end:
                counts['all_dispatches'] += 1
                if wake and wake['p']==-1:
                    counts['no_P_wakeup_dispatches'] += 1
                if (wake and previous and previous_dispatch.get(p)==previous[1]
                    and previous[0]['new'] in ('Waiting','Runnable')
                    and wake['actor_g']==previous[0]['target_g'] and wake['p']==p
                    and previous[1]['time_ns']<=wake['time_ns']<=previous[0]['time_ns']<=stamp):
                    counts['same_P_waker_then_handoff'] += 1
                    category = ('worker_reply' if 'main.(*service).runJob' in wake['Stack']
                                else 'handler_admission' if 'main.(*service).workHandler' in wake['Stack']
                                else 'other')
                    counts[category+'_handoffs'] += 1
                    if sum(x['category']==category for x in examples)<3:
                        examples.append(dict(category=category,waker_start=previous[1],
                                             wake=wake,waker_exit=previous[0],target_start=e))
            running[g] = e
            if p>=0:
                previous_dispatch[p] = e
    return dict(counts=counts,examples=examples)


def inspect(review,dumps,output):
    if output.exists():
        raise ValueError('use a fresh output directory')
    validation = queue.read(review/'validation.json')
    if not validation.get('passed') or not validation.get('raw_dumps_match_sealed_scheduler'):
        raise ValueError('prior raw event review must be validated')
    hashes = queue.read(review/'source_hashes.json')
    summary = queue.read(review/'summary.json')
    trials, consumed = [], {}
    for t in summary['trials']:
        rid = t['run_id']
        path = dumps/(rid+'.parsed.txt')
        sha = runner.sha(path)
        if sha != hashes['inputs'][rid]['parsed_dump_sha256']:
            raise ValueError('decoded evidence changed: '+rid)
        rows = [e for e in raw_events.events(path) if e is not None]
        trials.append(dict(run_id=rid,mode=t['mode'],block=t['block'],
                           **handoffs(rows,t['ready_trace_ns'],t['run_trace_ns'])))
        consumed[rid] = sha
        print('HANDOFF REVIEW:',rid,dict(trials[-1]['counts']),flush=True)
    output.mkdir(parents=True)
    queue.write_json(output/'summary.json',dict(trials=trials,eligible_for_full=False,
                      interpretation='A same-P wake during the preceding running segment followed by '
                      'waker park/yield and target run is a handoff sequence; runnext use is not recorded.'))
    queue.write_json(output/'source_hashes.json',dict(analyzer_sha256=runner.sha(Path(__file__)),
                      raw_event_parser_sha256=runner.sha(Path(raw_events.__file__)),
                      prior_review_sha256=runner.sha(review/'summary.json'),
                      prior_validation_sha256=runner.sha(review/'validation.json'),
                      prior_provenance_sha256=runner.sha(review/'source_hashes.json'),dumps=consumed))
    queue.write_json(output/'validation.json',dict(passed=True,issues=[],trials=len(trials),
                      decoded_hashes_match_prior_validated_review=True,eligible_for_full=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--dumps',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    inspect(args.review.resolve(),args.dumps.resolve(),args.output.resolve())
