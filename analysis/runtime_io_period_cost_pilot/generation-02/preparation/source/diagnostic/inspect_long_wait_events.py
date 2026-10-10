#!/usr/bin/env python3
"""Step 1: inspect raw Go events around saved pre-handler readiness extremes.

Read-only with respect to sealed trials. No workload or gate is created.
"""
import argparse
import bisect
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics

import inspect_http_cleanup
import inspect_yield_queue as queue
import run as runner
import trace_analysis

CONTEXT = re.compile(r'^M=(-?\d+) P=(-?\d+) G=(-?\d+) ')


def events(path):
    """Preserve raw headers, source lines, and actor/target stacks."""
    current, start = [], 0
    with path.open() as stream:
        for line_number, line in enumerate(stream,1):
            if trace_analysis.HEADER.match(line):
                if current:
                    yield decode(current,start)
                current, start = [], line_number
            current.append(line)
    if current:
        yield decode(current,start)


def decode(block,line):
    match = trace_analysis.HEADER.match(block[0])
    if not match:
        return None
    context = CONTEXT.match(block[0])
    result = dict(kind=match[2],time_ns=int(match[3]),detail=match[4],
                  m=int(context[1]),p=int(context[2]),actor_g=int(context[3]),
                  line=line,header=block[0].strip(),**inspect_http_cleanup.stacks(block))
    if result['kind']=='StateTransition':
        transition = trace_analysis.TRANSITION.search(match[4])
        if transition:
            g,old,new,reason = transition.groups()
            result.update(target_g=int(g),old=old,new=new,reason=reason)
    return result


def classify_wakeup(event,waiting_reason,worker_gs,http_gs,listener_gs):
    target, stack = event['target_g'],event['Stack']
    if target in worker_gs and 'main.(*service).workHandler' in stack:
        return 'handler_admission_to_worker'
    if target in http_gs and 'main.(*service).runJob' in stack:
        return 'worker_reply_to_http'
    if target in http_gs and waiting_reason=='network' and event['p']==-1:
        return 'no_P_network_to_http'
    if target in listener_gs and waiting_reason=='network':
        return 'network_to_listener'
    return 'other'


def wakeup_latencies(rows,begin,end,worker_gs,http_gs,listener_gs):
    """Match actual wake to first run, ignoring same-state census snapshots.

    Cohort membership is the wake time in [begin,end), even if first run occurs
    later. Running->Runnable preemptions are not fresh Waiting wakeups.
    """
    pending, reasons = {}, {}
    matched, unresolved = [], []
    for event in rows:
        if 'target_g' not in event:
            continue
        g,old,new,stamp = event['target_g'],event['old'],event['new'],event['time_ns']
        if new=='Waiting' and old!=new:
            reasons[g] = event['reason']
        if old=='Waiting' and new=='Runnable':
            if g in pending:
                raise ValueError('duplicate wake without a run')
            pending[g] = (event,classify_wakeup(event,reasons.get(g),worker_gs,http_gs,listener_gs))
        if old=='Runnable' and new=='Running' and g in pending:
            wake,category = pending.pop(g)
            if begin<=wake['time_ns']<end:
                matched.append(dict(category=category,target_g=g,
                                    wake_ns=wake['time_ns'],run_ns=stamp,
                                    latency_ns=stamp-wake['time_ns'],wake_line=wake['line'],
                                    run_line=event['line'],wake_m=wake['m'],wake_p=wake['p']))
    for g,(wake,category) in pending.items():
        if begin<=wake['time_ns']<end:
            unresolved.append(dict(target_g=g,category=category,wake_ns=wake['time_ns']))
    return matched,unresolved


def trace_maintenance_context(rows,preemptions):
    """Preserve timing associations; do not infer the preemption signal source."""
    advancers = {e['actor_g'] for e in rows if 'runtime.traceAdvance' in e['Stack']}
    observations = []
    for preemption in preemptions:
        stamp = preemption['time_ns']
        sync = next((e for e in rows if e['kind']=='Sync' and e['time_ns']>=stamp),None)
        advance = next((e for e in rows if e['time_ns']>=stamp and
                        'runtime.traceAdvance' in e['Stack']),None)
        starts = [e for e in rows if e.get('target_g') in advancers and
                  e.get('old')=='Runnable' and e.get('new')=='Running' and e['time_ns']<=stamp]
        preceding = max(starts,key=lambda e:e['time_ns']) if starts else None
        observations.append(dict(preemption=preemption,following_sync=sync,
                                 following_trace_advance_event=advance,
                                 preceding_advancer_start=preceding,
                                 sync_delta_us=(sync['time_ns']-stamp)/1000 if sync else None,
                                 advancer_start_to_preemption_us=(stamp-preceding['time_ns'])/1000
                                 if preceding else None))
    return observations


def inspect(session,examples,dumps,output,decoder):
    if output.exists():
        raise ValueError('use a fresh output directory')
    if output.is_relative_to(session):
        raise ValueError('output must be outside retained session')
    meta = runner.verify_session(session,check_current=False)
    if not meta.get('yield_study'):
        raise ValueError('expected a yield study')
    configs = {c['run_id']:c for c in queue.read(session/'matrix.json')}
    prior_provenance = queue.read(examples.parent/'source_hashes.json')
    planned = queue.read(examples)['trials']
    accepted = {}
    for trial in planned:
        rid = trial['run_id']
        good = [p for p in runner.attempt_dirs(session/'attempts'/rid)
                if not runner.validation_errors(p,configs[rid],False)]
        if len(good)!=1:
            raise ValueError(rid+': expected one valid sealed attempt')
        accepted[rid] = good[0]
        if any(runner.sha(good[0]/name)!=expected
               for name,expected in prior_provenance['consumed_files'][rid].items()):
            raise ValueError(rid+': readiness source files changed')
    output.mkdir(parents=True)
    queue.write_json(output/'validation.json',dict(passed=False,issues=['inspection incomplete']))
    reports, wake_rows, source_hashes = [], [], {}
    for trial in planned:
        rid, example = trial['run_id'],trial['longest']
        attempt = accepted[rid]
        dump = dumps/(rid+'.parsed.txt')
        with dump.open() as stream:
            if trace_analysis.parse_lines(stream)!=queue.read(attempt/'trace_scheduler.json'):
                raise ValueError(rid+': decoder output differs from sealed scheduler evidence')
        raw = [e for e in events(dump) if e is not None]
        trace = queue.read(attempt/'trace_requests.json')
        srv = queue.read(attempt/'server_metrics.json')
        result = queue.read(attempt/'result.json')
        requests = {r['id']:r for r in trace['all_requests']}
        workers = {r['worker_g'] for r in trace['all_requests'] if 'worker_g' in r}
        http = {r['handler_g'] for r in trace['all_requests']}
        if len(workers)!=configs[rid]['workers']:
            raise ValueError(rid+': worker identities do not reconcile')
        clock = trace['clock_mapping']
        offset = (clock['offset_low_ns']+clock['offset_high_ns'])//2
        clipped_start = example['start_server_ns']+offset
        clipped_end = example['end_server_ns']+offset
        target = example['http_g']
        target_events = [e for e in raw if e.get('target_g')==target]
        wake = max((e for e in target_events if e['time_ns']<=clipped_start and
                    e['old']=='Waiting' and e['new']=='Runnable'),key=lambda e:e['time_ns'])
        start = next(e for e in target_events if e['time_ns']>=clipped_end and
                     e['old']=='Runnable' and e['new']=='Running')
        waiting = max((e for e in target_events if e['time_ns']<wake['time_ns'] and
                       e['old']=='Running' and e['new']=='Waiting'),key=lambda e:e['time_ns'])
        if any(e['old']=='Runnable' and e['new']!='Runnable' for e in target_events
               if wake['time_ns']<e['time_ns']<start['time_ns']):
            raise ValueError(rid+': selected ready span contains a state exit')
        begin,end = wake['time_ns'],start['time_ns']
        listener = {e['target_g'] for e in raw if 'target_g' in e and
                    ('net.(*TCPListener).Accept' in e['TransitionStack'] or
                     'net.(*TCPListener).accept' in e['TransitionStack'])}
        latencies, unresolved = wakeup_latencies(raw,begin,end,workers,http,listener)
        for row in latencies:
            wake_rows.append(dict(run_id=rid,mode=trial['mode'],block=trial['block'],**row))
        summaries = {}
        for category in sorted(set(r['category'] for r in latencies)):
            values = [r['latency_ns']/1e6 for r in latencies if r['category']==category]
            summaries[category] = dict(count=len(values),p50_ms=queue.percentile(values,50),
                                       p99_ms=queue.percentile(values,99),max_ms=max(values))
        state_changes = [e for e in raw if begin<=e['time_ns']<end and 'target_g' in e]
        worker_changes = [e for e in state_changes if e['target_g'] in workers]
        worker_preemptions = [e for e in worker_changes if e['old']=='Running' and
                              e['new']=='Runnable' and e['reason']=='preempted']
        worker_yields = [e for e in worker_changes if e['old']=='Running' and
                         e['new']=='Runnable' and e['reason']=='runtime.Gosched']
        other_runnable = Counter(e['reason'] for e in worker_changes if
                                 e['old']=='Running' and e['new']=='Runnable' and
                                 e['reason'] not in ('runtime.Gosched','preempted'))
        cohort_reply = [r for r in latencies if r['category']=='worker_reply_to_http']
        cohort_admission = [r for r in latencies if r['category']=='handler_admission_to_worker']
        markers = [e for e in state_changes if e['old']=='Runnable' and e['new']=='Running']
        worker_starts = sum(e['target_g'] in workers for e in markers)
        completion_times = sorted(e['completion_ns'] for e in srv['events'])
        # Certain/possible counts preserve the service/runtime offset bracket.
        completion_certain = queue.count_between(completion_times,begin-clock['offset_low_ns'],
                                                 end-clock['offset_high_ns'])
        completion_possible = queue.count_between(completion_times,begin-clock['offset_high_ns'],
                                                  end-clock['offset_low_ns']+1)
        request = requests[example['request_id']]
        handler_entry = request['intervals']['handler']['start_ns']
        resumed_to_entry = dict(low_ns=handler_entry+clock['offset_low_ns']-end,
                                high_ns=handler_entry+clock['offset_high_ns']-end)
        # Preserve concise context excerpts around initial wake and eventual run.
        boundary_excerpt = [e for e in raw if (begin-100_000<=e['time_ns']<=begin+500_000 or
                                               end-100_000<=e['time_ns']<=end+500_000)]
        queue.write_json(output/(rid+'_boundary_events.json'),boundary_excerpt)
        snippets = dict(waiting=waiting,wakeup=wake,first_run=start,
                        worker_reply_examples=[e for e in state_changes if
                            e['old']=='Waiting' and e['new']=='Runnable' and
                            'main.(*service).runJob' in e['Stack']][:3],
                        admission_examples=[e for e in state_changes if
                            e['old']=='Waiting' and e['new']=='Runnable' and
                            e['target_g'] in workers and 'main.(*service).workHandler' in e['Stack']][:3],
                        worker_yield_examples=worker_yields[:3],worker_preemption_examples=worker_preemptions[:3])
        report = dict(run_id=rid,mode=trial['mode'],block=trial['block'],request_id=example['request_id'],
                      conn=example['conn'],http_g=target,worker_gs=sorted(workers),listener_gs=sorted(listener),
                      runtime_godebug=result['runtime']['godebug'],go_version=result['runtime']['go_version'],
                      full_ready_span_ms=(end-begin)/1e6,ready_trace_ns=begin,run_trace_ns=end,
                      waiting_reason=waiting['reason'],wake_m=wake['m'],wake_p=wake['p'],
                      wake_actor_g=wake['actor_g'],wake_stack_available=bool(wake['Stack']),
                      recorded_worker_starts=worker_starts,
                      worker_completion_certain=completion_certain,worker_completion_possible=completion_possible,
                      worker_reply_wakeups=len(cohort_reply),handler_admission_wakeups=len(cohort_admission),
                      worker_preemptions=len(worker_preemptions),worker_yields=len(worker_yields),
                      trace_maintenance_context=trace_maintenance_context(raw,worker_preemptions),
                      other_worker_running_to_runnable=dict(other_runnable),
                      resumed_to_handler_entry=resumed_to_entry,
                      snapshot_count=sum(e['old']==e['new']=='Runnable' for e in target_events if begin<e['time_ns']<end),
                      wakeup_latency_cohorts=summaries,unresolved_wakeups=unresolved,raw_evidence=snippets)
        reports.append(report)
        source_hashes[rid] = dict(raw_trace_sha256=runner.sha(attempt/'runtime.trace'),
                                 completion_sha256=runner.sha(attempt/'complete.json'),
                                 parsed_dump_sha256=runner.sha(dump),
                                 sealed_scheduler_sha256=runner.sha(attempt/'trace_scheduler.json'),
                                 trace_requests_sha256=runner.sha(attempt/'trace_requests.json'))
        print('EVENT REVIEW:',rid,'ready span ms',report['full_ready_span_ms'],flush=True)
    queue.write_csv(output/'wakeups.csv',wake_rows)
    queue.write_json(output/'summary.json',dict(trials=reports,eligible_for_full=False))
    queue.write_json(output/'source_hashes.json',dict(analyzer_sha256=runner.sha(Path(__file__)),
                         decoder_sha256=runner.sha(decoder),compiler_image_id=meta['build']['compiler_image_id'],
                         readiness_examples_sha256=runner.sha(examples),inputs=source_hashes))
    queue.write_json(output/'validation.json',dict(passed=True,issues=[],trials=len(reports),
                         raw_dumps_match_sealed_scheduler=True,eligible_for_full=False))
    print('STEP 1 RAW EVENT REVIEW COMPLETE:',output)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session',type=Path)
    parser.add_argument('--examples',type=Path,required=True)
    parser.add_argument('--dumps',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--decoder',type=Path,required=True)
    args = parser.parse_args()
    inspect(args.session.resolve(),args.examples.resolve(),args.dumps.resolve(),
            args.output.resolve(),args.decoder.resolve())
