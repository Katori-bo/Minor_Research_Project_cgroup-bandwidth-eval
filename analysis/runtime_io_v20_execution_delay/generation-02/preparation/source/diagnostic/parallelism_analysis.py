#!/usr/bin/env python3
"""Bound entry delay for all offered outcomes; distinguish remedy from mechanism."""
import math
import statistics as stats

import analyze
import run


def clock_mapping(client, server):
    anchors=client['clock_anchors']
    labels={f'{phase}_{i}' for phase in ('start','stop') for i in range(3)}
    if len(anchors)!=6 or {a['label'] for a in anchors}!=labels:
        raise ValueError('six distinct clock anchors required')
    generations={a['generation'] for a in anchors}
    if generations!={server['clock_generation']}:raise ValueError('clock generation changed')
    start=client['client_test_start_ns'];end=start+round(client['elapsed_including_drain_sec']*1e9)
    lower=[];upper=[]
    for a in anchors:
        before,after,stamp=(a[k] for k in ('before_ns','after_ns','server_ns'))
        if min(before,stamp)<0 or after<before:raise ValueError('invalid clock bracket')
        if a['label'].startswith('start') and after>start:raise ValueError('start anchor inside arrivals')
        if a['label'].startswith('stop') and before<end:raise ValueError('stop anchor before client drain')
        lower.append(stamp-after);upper.append(stamp-before)
    lo,hi=max(lower),min(upper)
    if lo>hi or hi-lo>1_000_000:raise ValueError('clock mappings disagree or exceed 1 ms')
    return dict(server_minus_client_lower_ns=lo,server_minus_client_upper_ns=hi,
                uncertainty_ns=hi-lo,client_test_start_ns=start,generation=next(iter(generations)),
                assumption='same host Linux monotonic clock, unit slope, no time namespace or origin reset')


def entry_analysis(client, server):
    if server['entry_protocol']!='all-outcomes-v1' or server['runtime_variant']!='stock':
        raise ValueError('wrong entry protocol or runtime')
    if server['runtime_capture'] or server['custom_recording'] or server['worker_yield']:
        raise ValueError('runtime observer, tracing or yield enabled')
    if server['active_handlers'] or server['queue_len'] or server['completed']!=server['admitted']:
        raise ValueError('server not drained')
    mapping=clock_mapping(client,server)
    offered=client['total_scheduled'];requests=client['requests']
    if offered<1 or len(requests)!=offered or {q['ID'] for q in requests}!=set(range(offered)):
        raise ValueError('incomplete offered-request accounting')
    entries=server['entry_events'];by_id={e['id']:e for e in entries}
    if len(by_id)!=len(entries) or not set(by_id)<=set(range(offered)):
        raise ValueError('duplicate or unknown handler entry')
    if len(entries)!=server['admitted']+server['rejected']:
        raise ValueError('entry count differs from server outcomes')
    admitted={e['id'] for e in entries if e['admitted']}
    workers={e['id'] for e in server['events']}
    if admitted!=workers or len(admitted)!=server['admitted'] or len(workers)!=len(server['events']):
        raise ValueError('entry/worker admission mismatch')
    successful={h['id']:h for h in server['handler_events']}
    for e in entries:
        if not isinstance(e['admitted'],bool) or not 0<=e['entry_ns']<=e['exit_ns']:
            raise ValueError('invalid handler entry interval')
        if e['id'] in successful and e['entry_ns']!=successful[e['id']]['entry_ns']:
            raise ValueError('entry timestamp differs from existing handler timing')
    joined=[];certain=possible=0
    horizons={str(h):dict(certain_entered=0,possible_entered=0,missing_or_unobserved=0)
              for h in (1,5)}
    for q in sorted(requests,key=lambda q:q['ID']):
        e=by_id.get(q['ID']);ok=not q['Error'] and q['StatusCode'] in (200,503)
        if ok and (e is None or e['admitted']!=(q['StatusCode']==200)):
            raise ValueError('HTTP outcome missing or contradicts handler entry')
        outcome='success' if not q['Error'] and q['StatusCode']==200 else (
            'rejected' if not q['Error'] and q['StatusCode']==503 else ('timeout' if q['TimedOut'] else 'error'))
        row=dict(id=q['ID'],outcome=outcome,entry_observed=e is not None,
                 scheduled_ns=q['ScheduledOffsetNs'],dispatch_lag_ns=q['DispatchLagNs'])
        if e is None:
            row.update(scheduled_to_entry_lower_ns=None,scheduled_to_entry_upper_ns=None,
                       dispatch_to_entry_lower_ns=None,dispatch_to_entry_upper_ns=None)
            # A missing entry is unknown, not zero latency or certain non-entry.
            for h in horizons.values():h['possible_entered']+=1;h['missing_or_unobserved']+=1
        else:
            lo=e['entry_ns']-mapping['server_minus_client_upper_ns']-mapping['client_test_start_ns']
            hi=e['entry_ns']-mapping['server_minus_client_lower_ns']-mapping['client_test_start_ns']
            dispatch=q['ScheduledOffsetNs']+q['DispatchLagNs']
            if hi<dispatch:raise ValueError('entry certainly precedes client dispatch')
            if ok and lo>dispatch+q['HeadersOffsetNs']:raise ValueError('entry certainly follows HTTP response')
            row.update(scheduled_to_entry_lower_ns=max(0,lo-q['ScheduledOffsetNs']),
                       scheduled_to_entry_upper_ns=hi-q['ScheduledOffsetNs'],
                       dispatch_to_entry_lower_ns=max(0,lo-dispatch),dispatch_to_entry_upper_ns=hi-dispatch,
                       admitted=e['admitted'],server_entry_ns=e['entry_ns'],server_exit_ns=e['exit_ns'])
            certain+=row['scheduled_to_entry_lower_ns']>=1e9
            possible+=row['scheduled_to_entry_upper_ns']>=1e9
            for h,value in horizons.items():
                value['certain_entered']+=row['scheduled_to_entry_upper_ns']<=int(h)*1e9
                value['possible_entered']+=row['scheduled_to_entry_lower_ns']<=int(h)*1e9
        joined.append(row)
    missing=offered-len(entries)
    for value in horizons.values():
        value['certain_entered_fraction']=value['certain_entered']/offered
        value['possible_entered_fraction']=value['possible_entered']/offered
    return dict(mapping=mapping,offered=offered,entry_count=len(entries),missing_entry_count=missing,
        certainly_long_entry_count=certain,possibly_long_entry_count=possible+missing,
        certainly_long_entry_rate=certain/offered,possibly_long_entry_rate=(possible+missing)/offered,
        horizons_seconds=horizons,requests=joined,
        limitation='Entry delay includes network/HTTP processing; exact runnable-to-selection time is unavailable.')


def trial_row(order, config, attempt):
    row=analyze.trial_row(order,config,attempt)
    client=run.read(attempt/'loadgen.json');server=run.read(attempt/'server_metrics.json')
    entry=entry_analysis(client,server)
    good=[q for q in client['requests'] if q['StatusCode']==200 and not q['Error']]
    row.update(gomaxprocs=config['gomaxprocs'],parallelism_arm=config['parallelism_arm'],
        cohort_successful_rps=row['successful_rps'],
        successful_rps=sum(q['CompletedOffsetNs']<=config['duration_sec']*1e9 for q in good)/config['duration_sec'],
        successful_rps_including_drain=len(good)/client['elapsed_including_drain_sec'],
        error_fraction=client['total_errors']/client['total_scheduled'],
        failure_fraction=(client['total_503']+client['total_errors'])/client['total_scheduled'],
        entry_count=entry['entry_count'],missing_entry_count=entry['missing_entry_count'],
        certainly_long_entry_rate=entry['certainly_long_entry_rate'],
        possibly_long_entry_rate=entry['possibly_long_entry_rate'],clock_uncertainty_ns=entry['mapping']['uncertainty_ns'])
    for basis in ('scheduled','dispatch'):
        for bound in ('lower','upper'):
            values=[q[f'{basis}_to_entry_{bound}_ns'] for q in entry['requests'] if q['entry_observed']]
            row[f'p99_{basis}_to_entry_{bound}_ms']=analyze.pct(values,.99)
    row['p99_queue_all_completed_ms']=analyze.pct([e['queue_wait_ns'] for e in server['events']],.99)
    return row,entry


def comparison(rows):
    if len(rows)!=8 or len({r['run_id'] for r in rows})!=8:raise ValueError('eight independent trials required')
    cells={g:{r['rep']:r for r in rows if r['gomaxprocs']==g} for g in (1,2)}
    if any(set(cell)!=set(range(1,5)) for cell in cells.values()):raise ValueError('four complete pairs required')
    def med(g,key):
        values=[r[key] for r in cells[g].values()]
        return stats.median(values) if all(v is not None for v in values) else None
    def ratio(key):
        denom=med(2,key)
        numerator=med(1,key)
        return numerator/denom if denom and numerator is not None else None
    baseline=all(r['certainly_long_entry_rate']>0 for r in cells[2].values())
    coverage=all(r['trace_coverage'] is not None and r['trace_coverage']>=.99 for r in rows)
    pairs=[dict(block=b,entry_reduction_robust_to_bounds=
        cells[1][b]['possibly_long_entry_rate']<cells[2][b]['certainly_long_entry_rate']) for b in range(1,5)]
    denom=med(2,'certainly_long_entry_rate')
    long_ratio=med(1,'possibly_long_entry_rate')/denom if denom else None
    p99_ratio=ratio('p99_e2e_ms');throughput=ratio('successful_rps')
    failure_delta=med(1,'failure_fraction')-med(2,'failure_fraction')
    checks=dict(baseline_symptom_present=baseline,successful_client_trace_coverage=coverage,
        all_pairs_reduce_long_entry_under_clock_bounds=all(p['entry_reduction_robust_to_bounds'] for p in pairs),
        median_long_entry_reduction_at_least_half=long_ratio is not None and long_ratio<=.5,
        median_successful_p99_reduction_at_least_half=p99_ratio is not None and p99_ratio<=.5,
        failure_increase_at_most_point_one_percent=failure_delta<=.001,
        throughput_loss_at_most_five_percent=throughput is not None and throughput>=.95)
    return dict(passed=all(checks.values()),checks=checks,pairs=pairs,
        interpretation='inconclusive' if not baseline or not coverage else (
            'existing_remedy_passes_diagnostic_screen' if all(checks.values()) else 'partial_or_insufficient_mitigation'),
        conservative_long_entry_ratio=long_ratio,successful_p99_ratio=p99_ratio,
        successful_in_window_throughput_ratio=throughput,failure_fraction_difference=failure_delta,
        cpu_per_job_ratio=ratio('cpu_usec_per_completed_work'),
        limitation='Four pairs are descriptive; parallelism changes capacity as well as scheduling. No novelty or queue-mechanism claim.')
