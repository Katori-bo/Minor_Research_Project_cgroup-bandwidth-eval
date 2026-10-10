"""All-offered deadline outcomes with conservative publication-time brackets."""
from collections import Counter
import statistics

import parallelism_analysis as stock

DEADLINES_MS = (500, 1000)
MARGINS = dict(timely_fraction=.01, failure_fraction=.001, cpu_ratio=.05, p99_ratio=.10)


def classify(client, server, arm):
    if arm not in ('legacy','locked','bounded'): raise ValueError('unknown recorder arm')
    entry = stock.entry_analysis(client,server)
    if arm != 'legacy':
        if server.get('completion_protocol') != 'publication-brackets-v1' or server.get('recorder_mode') != arm:
            raise ValueError('wrong publication protocol/recorder')
        if server['record_errors'] or server['record_capacity'] < client['total_scheduled']:
            raise ValueError('record overflow, duplicate ID or capacity error')
    elif server.get('completion_protocol'):
        raise ValueError('legacy arm contains new observer')
    jobs = {e['id']:e for e in server['events']}
    entries = {e['id']:e for e in server['entry_events']}
    handlers = {h['id']:h for h in server['handler_events']}
    if len(handlers) != len(server['handler_events']): raise ValueError('duplicate handler')
    boundaries = {b['id']:b for b in server.get('completion_events',[])}
    if arm != 'legacy':
        if len(boundaries)!=len(server['completion_events']) or set(boundaries)!=set(jobs):
            raise ValueError('publication records do not conserve completed jobs')
        for rid,b in boundaries.items():
            stamps=[jobs[rid]['completion_ns']]+[b[k] for k in
                ('record_start_ns','record_lock_ns','record_end_ns','publish_start_ns','publish_end_ns')]
            if any(a>z for a,z in zip(stamps,stamps[1:])) or stamps[0]<0:
                raise ValueError('invalid boundary ordering')
            if rid in handlers and handlers[rid]['resume_ns'] < b['publish_start_ns']:
                raise ValueError('handler precedes publication start')
            # No requirement that resume >= publish_end: sender and receiver
            # can run concurrently after the buffered send linearizes.
    mapping=entry['mapping']
    rows=[];totals={}
    def bounds(stamp,request):
        common=mapping['client_test_start_ns']+request['ScheduledOffsetNs']
        return (stamp-mapping['server_minus_client_upper_ns']-common,
                stamp-mapping['server_minus_client_lower_ns']-common)
    for deadline_ms in DEADLINES_MS:
        deadline=deadline_ms*1_000_000;counts=Counter()
        for q in sorted(client['requests'],key=lambda q:q['ID']):
            rid=q['ID'];j=jobs.get(rid);h=handlers.get(rid);b=boundaries.get(rid)
            success=not q['Error'] and q['StatusCode']==200
            outcome='success' if success else ('rejected' if not q['Error'] and q['StatusCode']==503 else ('timeout' if q['TimedOut'] else 'error'))
            timely=success and q['EndToEndLatencyNs']<=deadline
            row=dict(id=rid,deadline_ms=deadline_ms,outcome=outcome,timely=timely,
                e2e_ns=q['EndToEndLatencyNs'],worker_observed=j is not None,handler_observed=h is not None,
                publication_class='unobserved',deadline_crossing='timely' if timely else 'work_unobserved',
                completion_to_resume_ns=None,record_lock_wait_ns=None,record_held_interval_ns=None,
                completion_to_publish_start_ns=None,publication_bracket_ns=None,
                publication_to_resume_lower_ns=None,publication_to_resume_upper_ns=None)
            e=entries.get(rid)
            for name,stamp in [('entry',e['entry_ns'] if e else None),
                               ('admission',j['admission_ns'] if j else None),
                               ('worker_start',j['worker_start_ns'] if j else None),
                               ('completion',j['completion_ns'] if j else None),
                               ('resume',h['resume_ns'] if h else None),
                               ('write_end',h['write_end_ns'] if h else None),
                               ('handler_exit',h['handler_exit_ns'] if h else None),
                               ('publish_start',b['publish_start_ns'] if b else None),
                               ('publish_end',b['publish_end_ns'] if b else None)]:
                lo,hi=bounds(stamp,q) if stamp is not None else (None,None)
                row[name+'_lower_ns'],row[name+'_upper_ns']=lo,hi
            if success and (not j or not h): raise ValueError('successful request lacks worker/handler evidence')
            if j and h:
                if not j['completion_ns']<=h['resume_ns']<=h['write_start_ns']<=h['write_end_ns']<=h['handler_exit_ns']:
                    raise ValueError('invalid handler stages')
                row['completion_to_resume_ns']=h['resume_ns']-j['completion_ns']
            if b:
                row.update(record_lock_wait_ns=b['record_lock_ns']-b['record_start_ns'],
                    record_held_interval_ns=b['record_end_ns']-b['record_lock_ns'],
                    completion_to_publish_start_ns=b['publish_start_ns']-j['completion_ns'],
                    publication_bracket_ns=b['publish_end_ns']-b['publish_start_ns'])
                if h:
                    row['publication_to_resume_lower_ns']=max(0,h['resume_ns']-b['publish_end_ns'])
                    row['publication_to_resume_upper_ns']=h['resume_ns']-b['publish_start_ns']
                row['publication_class']=('certainly_before' if row['publish_end_upper_ns']<=deadline else
                    ('certainly_after' if row['publish_start_lower_ns']>deadline else 'overlaps_deadline'))
            if not timely and j:
                if row['completion_upper_ns']<=deadline:
                    row['deadline_crossing']=('work_before_resume_after' if h and row['resume_lower_ns']>deadline else
                        ('work_before_resume_before' if h and row['resume_upper_ns']<=deadline else
                        ('work_before_resume_ambiguous' if h else 'work_before_resume_unobserved')))
                elif row['completion_lower_ns']>deadline: row['deadline_crossing']='work_after'
                else: row['deadline_crossing']='work_ambiguous'
            counts['offered']+=1;counts['failure']+=not success
            counts[row['deadline_crossing']]+=1
            # Keep failures/cancellations distinct from successful late delivery.
            if success and not timely and j and row['completion_upper_ns']<=deadline:
                counts['late_success_work_before']+=1
                if row['completion_upper_ns']<=deadline-50_000_000: counts['late_success_work_before_margin50ms']+=1
            rows.append(row)
        counts['timely']=sum(r['timely'] for r in rows if r['deadline_ms']==deadline_ms)
        totals[str(deadline_ms)]=dict(counts,timely_fraction=counts['timely']/entry['offered'],
            failure_fraction=counts['failure']/entry['offered'])
    return dict(offered=entry['offered'],missing_entry_count=entry['missing_entry_count'],mapping=mapping,
        arm=arm,deadlines=totals,requests=rows,
        limitation='Publication is bracketed. Handler execution is not runnable readiness. Lock/wall intervals include off-CPU time; cumulative quota counters cannot identify per-request throttling.')


def compare(rows):
    cells={(r['rep'],r['recorder_arm']):r for r in rows}
    if len(rows)!=12 or len(cells)!=12 or set(cells)!={(b,a) for b in range(1,5) for a in ('legacy','locked','bounded')}:
        raise ValueError('four complete three-arm blocks required')
    comparisons={}
    for base,arm in (('legacy','locked'),('locked','bounded')):
        pairs=[]
        for block in range(1,5):
            a,z=cells[block,base],cells[block,arm]
            def ratio(key):
                return z[key]/a[key] if z[key] is not None and a[key] not in (None,0) else None
            p=dict(block=block,timely_fraction_delta=z['timely_500_fraction']-a['timely_500_fraction'],
                timely_1000_fraction_delta=z['timely_1000_fraction']-a['timely_1000_fraction'],
                failure_fraction_delta=z['failure_fraction']-a['failure_fraction'],
                cpu_ratio=ratio('cpu_usec_per_completed_work'),p99_ratio=ratio('p99_e2e_ms'),
                post_work_late_fraction_delta=z['post_work_late_fraction']-a['post_work_late_fraction'])
            p['within_screen']=abs(p['timely_fraction_delta'])<=MARGINS['timely_fraction'] and \
                abs(p['timely_1000_fraction_delta'])<=MARGINS['timely_fraction'] and \
                abs(p['failure_fraction_delta'])<=MARGINS['failure_fraction'] and \
                p['cpu_ratio'] is not None and abs(p['cpu_ratio']-1)<=MARGINS['cpu_ratio'] and \
                p['p99_ratio'] is not None and abs(p['p99_ratio']-1)<=MARGINS['p99_ratio']
            pairs.append(p)
        deltas={k:dict(median=statistics.median([p[k] for p in pairs]),
            minimum=min(p[k] for p in pairs),maximum=max(p[k] for p in pairs))
            for k in ('timely_fraction_delta','timely_1000_fraction_delta','failure_fraction_delta','post_work_late_fraction_delta')}
        comparisons[base+'_to_'+arm]=dict(pairs=pairs,block_deltas=deltas,within_screen=all(p['within_screen'] for p in pairs))
    marker_ok=comparisons['legacy_to_locked']['within_screen']
    recorder_ok=comparisons['locked_to_bounded']['within_screen']
    return dict(margins=MARGINS,comparisons=comparisons,
        decision=('marker_effect_requires_review' if not marker_ok else
                  ('recorder_effect_requires_review' if not recorder_ok else 'qualified_for_scoped_control_preparation')),
        limitation='Four discovery blocks and practical screens do not prove statistical equivalence. No policy/independent-control batch launches automatically.')
