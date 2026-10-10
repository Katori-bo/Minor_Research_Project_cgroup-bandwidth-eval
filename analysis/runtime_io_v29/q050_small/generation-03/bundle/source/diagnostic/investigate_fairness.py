#!/usr/bin/env python3
"""Offline ordered investigation of saved v9 trials and the earlier v8 claims."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import statistics as stats

import analyze
import fairness_analysis as fairness
import fairness_study as study
import inspect_http_cleanup as cleanup
import inspect_long_wait_events as events
import run
import trace_analysis as trace


def pct(values, p=99):
    return sorted(values)[math.ceil(p*len(values)/100)-1] if values else None


def stage_rows(config, attempt):
    lg, server = run.read(attempt/'loadgen.json'), run.read(attempt/'server_metrics.json')
    handlers = {h['id']:h for h in server['handler_events']}
    jobs = {j['id']:j for j in server['events']}
    rows = []
    for q in lg['requests']:
        outcome = 'timeout' if q['TimedOut'] else 'error' if q['Error'] else \
                  'success' if q['StatusCode']==200 else 'rejected' if q['StatusCode']==503 else 'other'
        row = dict(run_id=config['run_id'], mode=config['runtime_mode'], rep=config['rep'],
                   request_id=q['ID'], outcome=outcome, e2e_ms=q['EndToEndLatencyNs']/1e6,
                   dispatch_ms=q['DispatchLagNs']/1e6, error=q['Error'], status=q['StatusCode'],
                   client_get_connection_ms=None, client_connection_to_request_write_ms=None,
                   client_request_write_to_first_byte_ms=None, client_first_byte_to_body_ms=None,
                   pre_admission_ms=None, queue_ms=None, processing_ms=None, post_work_ms=None,
                   resume_to_write_ms=None, application_write_ms=None, write_to_handler_exit_ms=None,
                   handler_span_ms=None, outside_handler_signed_ms=None, cleanup_ms=None,
                   final_socket_write_to_done_ms=None, worker_completed=q['ID'] in jobs,
                   completed_after_client_left=jobs.get(q['ID'],{}).get('client_gone_at_completion'))
        h, j = handlers.get(q['ID']), jobs.get(q['ID'])
        if not q['TraceIssue'] and 0 <= q['GotConnOffsetNs'] <= q['WroteRequestOffsetNs'] <= q['FirstByteOffsetNs'] <= q['BodyDoneOffsetNs']:
            row.update(client_get_connection_ms=q['GotConnOffsetNs']/1e6,
                client_connection_to_request_write_ms=(q['WroteRequestOffsetNs']-q['GotConnOffsetNs'])/1e6,
                client_request_write_to_first_byte_ms=(q['FirstByteOffsetNs']-q['WroteRequestOffsetNs'])/1e6,
                client_first_byte_to_body_ms=(q['BodyDoneOffsetNs']-q['FirstByteOffsetNs'])/1e6)
        if h and j:
            row.update(pre_admission_ms=h['pre_admission_ns']/1e6, queue_ms=j['queue_wait_ns']/1e6,
                       processing_ms=j['processing_ns']/1e6, post_work_ms=h['post_work_wait_ns']/1e6,
                       resume_to_write_ms=(h['write_start_ns']-h['resume_ns'])/1e6,
                       application_write_ms=(h['write_end_ns']-h['write_start_ns'])/1e6,
                       write_to_handler_exit_ms=(h['handler_exit_ns']-h['write_end_ns'])/1e6,
                       handler_span_ms=(h['handler_exit_ns']-h['entry_ns'])/1e6)
            parts = ('pre_admission_ms','queue_ms','processing_ms','post_work_ms','resume_to_write_ms',
                     'application_write_ms','write_to_handler_exit_ms')
            if abs(sum(row[k] for k in parts)-row['handler_span_ms'])>1e-6:
                raise ValueError('server-local handler partition does not reconcile')
            row['outside_handler_signed_ms']=row['e2e_ms']-row['handler_span_ms']
        rows.append(row)
    return rows


def repaired(attempt, audit):
    summary = run.read(audit/'summary.json')
    if not summary['output_matches_pinned'] or not summary['original_time_chain_valid']:
        raise ValueError('timestamp audit is not valid')
    if summary['source_sha256']['runtime_trace'] != run.sha(attempt/'runtime.trace'):
        raise ValueError('raw trace changed')
    dump = audit/'original_time.parsed.txt'
    if summary['source_sha256']['restored'] != run.sha(dump):
        raise ValueError('original-time dump changed')
    with dump.open() as stream:
        parsed = trace.parse_lines(stream)
    trace.scheduler_series(parsed)
    status, lg, server = [run.read(attempt/n) for n in
                         ('trace_status.json','loadgen.json','server_metrics.json')]
    requests = trace.build_analysis(status, lg, server, parsed)
    if not requests['complete']:
        raise ValueError('original-time request association incomplete')
    with dump.open() as stream:
        joined = cleanup.join(parsed, requests, server, cleanup.index_events(stream))
    waits = fairness.network_waits(dump, requests)
    for name, data in [('original_time_scheduler.json',parsed),('original_time_requests.json',requests),
                       ('http_cleanup.json',joined),('network_ready.json',waits)]:
        run.put(audit/name,data)
    return parsed, requests, joined, waits


def main(root, output):
    if output.exists():
        raise ValueError('use a fresh investigation output')
    session = root/'results/diagnostic/runtime-io-v9-fairness-1/session'
    study.verify_frozen(session)
    recovery = run.read(root/'analysis/runtime_io_v9_recovery_20261003/provenance.json')
    if not all(run.sha(session/name)==digest for name,digest in recovery['raw_sha256'].items()):
        raise ValueError('v9 raw inputs changed since full revalidation')
    audits = {}
    for path in (root/'analysis/runtime_io_v9_timestamp_audit').rglob('summary.json'):
        data=run.read(path);rid=Path(data['attempt']).parent.name
        if rid in audits:raise ValueError('duplicate successful timestamp audit '+rid)
        audits[rid]=path.parent
    rows, requests, counts, changes = [], [], [], []
    for order, config in enumerate(run.read(session/'matrix.json'),1):
        rid=config['run_id'];attempt=session/'attempts'/rid/'001'
        print('REANALYZE',rid,flush=True)
        row=analyze.trial_row(order,config,attempt)
        lg,server=run.read(attempt/'loadgen.json'),run.read(attempt/'server_metrics.json')
        row.update(runtime_mode=config['runtime_mode'],runtime_variant=config['runtime_variant'],
                   worker_yield=False,service_image=config['service_image'],rejected=lg['total_503'],
                   timeouts=sum(q['TimedOut'] for q in lg['requests']),errors=lg['total_errors'],
                   completed_jobs=server['completed'],error_fraction=lg['total_errors']/lg['total_scheduled'],
                   all_failure_fraction=(lg['total_503']+lg['total_errors'])/lg['total_scheduled'],
                   network_ready_p99_ms=None,cleanup_wait_p99_ms=None)
        local=stage_rows(config,attempt)
        if config['runtime_trace']:
            parsed,tr,joined,waits=repaired(attempt,audits[rid])
            row.update(network_ready_p99_ms=waits['network_ready_p99_ms'],
                       network_ready_max_ms=waits['network_ready_max_ms'],
                       network_ready_unresolved_count=waits['network_ready_unresolved_count'],
                       cleanup_wait_p99_ms=joined['wait_ms']['p99'])
            byid={r['id']:r for r in tr['all_requests']}
            for r in local:
                observed=byid.get(r['request_id'],{})
                for name,key in [('handler_exit_to_connection_done','cleanup_ms'),
                                  ('final_socket_write_to_connection_done','final_socket_write_to_done_ms')]:
                    v=observed.get('intervals',{}).get(name)
                    if v:r[key]=v['duration_ns']/1e6
            # Preserve exact examples of ready HTTP work and independent worker
            # progress. These are observations, not queue-slot/preempt-flag proof.
            worker_times=sorted(e['completion_ns'] for e in server['events'])
            clock=tr['clock_mapping'];offset=(clock['offset_low_ns']+clock['offset_high_ns'])//2
            for w in waits['longest_examples'][:3]:
                import bisect
                example=dict(run_id=rid,**w,
                    jobs_completed_during_wait=bisect.bisect_left(worker_times,w['run_ns']-offset)-
                                              bisect.bisect_left(worker_times,w['wake_ns']-offset))
                following=sorted((r for r in tr['all_requests'] if r.get('handler_g')==w['target_g'] and
                    parsed['tasks'][str(r['id'])]['handler_log_time']>=w['run_ns']),
                    key=lambda r:parsed['tasks'][str(r['id'])]['handler_log_time'])
                if following:
                    target=following[0];entry=target['intervals']['handler']['start_ns']
                    context=target['intervals'].get('connection_context_before_handler')
                    example.update(next_request_id=target['id'],next_request_outcome=target['outcome'],
                        first_run_to_handler_entry_low_ns=entry+clock['offset_low_ns']-w['run_ns'],
                        first_run_to_handler_entry_high_ns=entry+clock['offset_high_ns']-w['run_ns'],
                        preceding_connection_boundary_before_wake=(context['start_ns']+clock['offset_high_ns']<=w['wake_ns']) if context else None)
                counts.append(example)
            changes.append(dict(run_id=rid,**run.read(audits[rid]/'summary.json')))
        # Keep a common CSV schema for tracing off and on.
        row.setdefault('network_ready_max_ms',None);row.setdefault('network_ready_unresolved_count',None)
        rows.append(row);requests.extend(local)
    review=fairness.screens(rows)
    summaries=[]
    fields=('e2e_ms','dispatch_ms','client_get_connection_ms','client_connection_to_request_write_ms',
            'client_request_write_to_first_byte_ms','client_first_byte_to_body_ms',
            'pre_admission_ms','queue_ms','processing_ms','post_work_ms','resume_to_write_ms',
            'application_write_ms','write_to_handler_exit_ms','outside_handler_signed_ms','cleanup_ms')
    for config in run.read(session/'matrix.json'):
        local=[r for r in requests if r['run_id']==config['run_id']]
        good=[r for r in local if r['outcome']=='success']
        tail=sorted(good,key=lambda r:r['e2e_ms'],reverse=True)[:math.ceil(len(good)*.01)]
        item=dict(run_id=config['run_id'],mode=config['runtime_mode'],rep=config['rep'],
                  outcomes=dict(Counter(r['outcome'] for r in local)),tail_requests=len(tail))
        for field in fields:
            values=[r[field] for r in good if r[field] is not None]
            tailvalues=[r[field] for r in tail if r[field] is not None]
            item[field+'_p99']=pct(values)
            item[field+'_slowest_1pct_mean']=stats.mean(tailvalues) if tailvalues else None
        summaries.append(item)
    previous=root/'results/diagnostic/runtime-io-v8-yield-1'
    run.verify_session(previous,check_current=False)
    v8plan={r['run_id']:r for r in run.read(previous/'matrix.json')}
    oldreview=run.read(root/'analysis/runtime_io_v8_long_waits/review_final/summary.json')['trials']
    earlier=[]
    for item in oldreview:
        rid=item['run_id'];audit=audits[rid];attempt=Path(run.read(audit/'summary.json')['attempt'])
        print('RECHECK EARLIER FINDING',rid,flush=True)
        errors=run.validation_errors(attempt,v8plan[rid],False)
        if errors:raise ValueError(rid+': '+str(errors))
        parsed,tr,joined,waits=repaired(attempt,audit)
        clock=tr['clock_mapping'];offset=(clock['offset_low_ns']+clock['offset_high_ns'])//2
        remap={int(line.split()[2].split('=')[1]):int(line.split()[1].split('=')[1])
               for line in (audit/'timestamp_ledger.txt').read_text().splitlines()}
        begin,end=remap[item['ready_trace_ns']],remap[item['run_trace_ns']]
        transitions=parsed['transitions'][str(item['http_g'])]
        if not any(e[0]==begin and e[1:3]==['Waiting','Runnable'] for e in transitions):
            raise ValueError('selected old wake not preserved')
        if not any(e[0]==end and e[1:3]==['Runnable','Running'] for e in transitions):
            raise ValueError('selected old run not preserved')
        if end<begin or any(e[1]=='Runnable' and e[2]!='Runnable' for e in transitions if begin<e[0]<end):
            raise ValueError('old selected ready span is not continuous in raw time')
        srv=run.read(attempt/'server_metrics.json')
        certain=sum(begin-clock['offset_low_ns']<=e['completion_ns']<end-clock['offset_high_ns'] for e in srv['events'])
        possible=sum(begin-clock['offset_high_ns']<=e['completion_ns']<end-clock['offset_low_ns'] for e in srv['events'])
        earlier.append(dict(run_id=rid,old_ready_ms=item['full_ready_span_ms'],original_time_ready_ms=(end-begin)/1e6,
            worker_completion_certain=certain,worker_completion_possible=possible,
            old_worker_completions=item['worker_completion_certain'],
            request_id=item['request_id'],handler_g=item['http_g'],original_wake_ns=begin,original_run_ns=end,
            max_decoder_adjustment_ms=run.read(audit/'summary.json')['maximum_adjustment_ns']/1e6))
    # Recheck sealed inputs after all offline calculations.
    if not all(run.sha(session/name)==digest for name,digest in recovery['raw_sha256'].items()):
        raise ValueError('v9 raw inputs changed during investigation')
    output.mkdir(parents=True,exist_ok=False)
    for name,data in [('screens.json',review),('stage_summaries.json',summaries),('ready_wait_examples.json',counts),
                      ('earlier_findings_audit.json',earlier),('timestamp_audit_summary.json',changes)]:
        run.put(output/name,data)
    analyze.writecsv(output/'trials.csv',rows);analyze.writecsv(output/'contrasts.csv',fairness.contrasts(rows))
    analyze.writecsv(output/'request_stages.csv',requests)
    run.put(output/'validation.json',dict(passed=True,trials=16,earlier_traces=8,
        raw_inputs_unchanged=True,original_time_chains_valid=True,request_and_cleanup_joins_valid=True,
        original_workflow_changed=False,eligible_for_full=False,
        scope='Offline reanalysis with a separately audited original-time decoder; not a performance qualification gate.'))
    print('OFFLINE INVESTIGATION COMPLETE',output,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    main(run.ROOT,args.output.resolve())
