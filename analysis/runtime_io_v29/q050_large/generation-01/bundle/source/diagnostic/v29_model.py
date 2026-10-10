"""Declared calibration-only estimators and fresh-outcome comparison."""
import bisect
import math
import statistics as st
import v29_common as c
import v23_model as queue
import v24r3_model as bounds
from v27r3_model import interval_summary

METHODS=('whole','idle_corrected','busy','regression','quadratic')


def trial(derived,server,anchors,probe,cfg,design,expected_path):
    if probe is not None or cfg['counter_probe']:raise ValueError('V29 scientific data must use sampler off')
    s=derived['summary'];w=s['counter_window'];t=(w['after_ns']-w['before_ns'])/1e9
    cpu=w['delta']['usage_usec']/1e6
    row=dict(context=cfg['context'],trial=cfg['trial'],role=cfg['role'],block=cfg['block'],order=cfg['order'],
        low_rate=cfg['low_rate'],period_sec=cfg['burst_period_sec'],offers=s['offered'],
        completed=s['completed_computations'],cpu_sec=cpu,accounted_wall_sec=t,
        utilization=cpu/t,throughput_rps=s['completed_computations']/t,
        throttled_periods=w['delta']['nr_throttled'],
        all_successful=s['failure_fraction']==0 and s['warmup_all_successful'],
        miss_pct=None if s['timely_500_fraction'] is None else 100*(1-s['timely_500_fraction']))
    if cfg['role']=='idle':
        row.update(state_eligible=derived.get('idle') is True and s['offered']==0,queue_peak=0)
        return row
    mapping=derived['clocks'];origin=tuple(mapping['client_test_start_ns']+mapping['server_minus_client_'+k+'_ns'] for k in ('lower','upper'))
    jobs=server['events'];q=queue.series([j['admission_ns'] for j in jobs],[j['worker_start_ns'] for j in jobs])
    ends=sorted(j['completion_ns'] for j in jobs);row['queue_peak']=max(q[1],default=0)
    if cfg['role']=='steady':
        windows=design['steady_windows_sec'];counts=[bounds.completion_bounds(ends,origin,[window]) for window in windows]
        rates=[[x/(b-a) for x in count] for (a,b),count in zip(windows,counts)]
        steady=all(.95*cfg['rate']<=a<=b<=1.05*cfg['rate'] for a,b in rates)
        low=cfg['reference_low_rate'] in (15,30)
        row.update(steady_rate_bounds=rates,state_eligible=steady and row['queue_peak']<=(1 if low else 5)
            and (row['throttled_periods']==0 if low else True),whole_cpu_sec_per_job=cpu/row['completed'] if row['completed'] else None)
        return row
    windows=design['busy_windows_sec']['calibration' if cfg['role']=='mixed' else str(cfg['burst_period_sec'])]
    duration=sum(b-a for a,b in windows);counts=bounds.completion_bounds(ends,origin,windows)
    midpoint=st.mean(origin)
    count=sum(bisect.bisect_left(ends,midpoint+b*1e9)-bisect.bisect_left(ends,midpoint+a*1e9) for a,b in windows)
    minima=[queue.min_window(q,origin[0]+a*1e9,origin[1]+b*1e9) for a,b in windows]
    row.update(busy_queue_minima=minima,state_eligible=all(x>0 for x in minima),
        busy_capacity_rps=count/duration,busy_capacity_bounds_rps=[x/duration for x in counts],
        whole_cpu_sec_per_job=cpu/row['completed'] if row['completed'] else None)
    row['deadline_miss_pct']={str(ms): 100*sum(not r['success'] or r['e2e_ns']>ms*1_000_000 for r in derived['requests'])/s['offered'] for ms in c.DEADLINES_MS}
    return row


def solve(matrix,vector):
    n=len(vector);a=[list(row)+[v] for row,v in zip(matrix,vector)]
    for i in range(n):
        pivot=max(range(i,n),key=lambda j:abs(a[j][i]))
        if abs(a[pivot][i])<1e-12:raise ValueError('singular regression design')
        a[i],a[pivot]=a[pivot],a[i];d=a[i][i];a[i]=[x/d for x in a[i]]
        for j in range(n):
            if j!=i:
                d=a[j][i];a[j]=[x-d*y for x,y in zip(a[j],a[i])]
    return [row[-1] for row in a]


def ols(points,degree,intercept=True):
    powers=list(range(0 if intercept else 1,degree+1))
    a=[[sum(x**(i+j) for x,y in points) for j in powers] for i in powers]
    v=[sum(y*x**i for x,y in points) for i in powers]
    result=solve(a,v)
    return result if intercept else [0.0]+result


def loss(points,coefs):return sum((sum(a*x**i for i,a in enumerate(coefs))-y)**2 for x,y in points)


def regression(points,quota,quadratic=False):
    # Scale throughput to prevent poorly conditioned powers in normal equations.
    scale=max(x for x,y in points);normalized=[(x/scale,y) for x,y in points]
    candidates=[]
    degree=2 if quadratic else 1
    for intercept in (True,False):
        coeff=ols(normalized,degree,intercept)
        b,d=coeff[:2];e=coeff[2] if quadratic else 0.0
        if b<0 or b>=quota or d<=0:continue
        if abs(e)<1e-12:root=(quota-b)/d
        else:
            disc=d*d-4*e*(b-quota)
            if disc<0:continue
            roots=[(-d+math.sqrt(disc))/(2*e),(-d-math.sqrt(disc))/(2*e)]
            roots=[x for x in roots if x>0 and d+2*e*x>0]
            if len(roots)!=1:continue
            root=roots[0]
        # A predeclared bounded extrapolation and monotonicity domain. No
        # clipping to historical busy capacity or validation outcomes.
        if root>2 or d+2*e*max(root,1)<=0:continue
        candidates.append((loss(normalized,coeff),coeff,root*scale))
    if quadratic:
        linear=regression(points,quota,False)
        if linear['status']=='available':
            coeff=[linear['intercept'],linear['demand_sec']*scale,0.0]
            candidates.append((loss(normalized,coeff),coeff,linear['capacity_rps']))
    if not candidates:return dict(status='unavailable',reason='no admissible monotonic fit/root within 2x calibration throughput')
    residual,coeff,root=min(candidates,key=lambda z:z[0]);b,d=coeff[:2]
    return dict(status='available',capacity_rps=root,intercept=b,demand_sec=d/scale,
        quadratic_sec2=coeff[2]/scale**2 if quadratic else 0.0,
        residual_sum_squares=residual,calibration_max_throughput_rps=scale,
        extrapolation_ratio=root/scale,fit='nonnegative_intercept_and_positive_demand_monotonic_capacity_root')


def calibrate(rows,design):
    wanted={s['id'] for s in design['trial_order'] if s['kind']!='validation'}
    if {r['trial'] for r in rows}!=wanted or len(rows)!=len(wanted):raise ValueError('exact independent calibration rows required')
    if any(r['role']=='validation' for r in rows):raise ValueError('validation data in calibration prohibited')
    ok=all(r['state_eligible'] and r['all_successful'] for r in rows)
    mixed=[r for r in rows if r['role']=='mixed'];idle=[r for r in rows if r['role']=='idle']
    capacities=[r['busy_capacity_rps'] for r in mixed]
    stable=min(capacities)>0 and (max(capacities)/min(capacities)-1)*100<=design['rules']['calibration_capacity_range_pct']
    result=dict(usable=ok and stable,state_and_cohort_pass=ok,busy_repeatability_pass=stable,
        calibration_trials=[r['trial'] for r in rows],methods={},novelty_established=False)
    if not result['usable']:result['decision']='calibration_qualification_failed';return result
    quota=design['quota_cpu'];b=st.mean(r['utilization'] for r in idle)
    cost=st.mean(r['whole_cpu_sec_per_job'] for r in mixed)
    corrected=st.mean((r['cpu_sec']-b*r['accounted_wall_sec'])/r['completed'] for r in mixed)
    result['idle_cpu_rate']=b
    result['methods']['whole']=dict(status='available',capacity_rps=quota/cost,cpu_sec_per_job=cost)
    result['methods']['busy']=dict(status='available',capacity_rps=st.mean(capacities),
        calibration_capacity_bounds_rps=[st.mean(r['busy_capacity_bounds_rps'][i] for r in mixed) for i in (0,1)])
    result['methods']['idle_corrected']=(dict(status='available',capacity_rps=(quota-b)/corrected,cpu_sec_per_job=corrected,background_cpu_rate=b)
        if corrected>0 and 0<=b<quota else dict(status='unavailable',reason='idle correction produced nonphysical demand or background'))
    points=[(r['throughput_rps'],r['utilization']) for r in rows if r['role'] in ('idle','steady')]
    for method,quadratic in (('regression',False),('quadratic',True)):
        result['methods'][method]=regression(points,quota,quadratic)
        result['methods'][method]['fit_trial_ids']=[r['trial'] for r in rows if r['role'] in ('idle','steady')]
    result['decision']='calibration_qualified';return result


def forecast(calibration,configs):
    if not calibration['usable']:raise ValueError('unqualified calibration cannot forecast')
    result={};per_id={}
    for method,value in calibration['methods'].items():
        if value['status']!='available':continue
        result[method]={};per_id[method]={}
        for cfg in configs:
            rows,summary=queue.simulate(c.schedule(cfg),value['capacity_rps'],cfg['burst_period_sec'])
            # The retained simulator's recovery diagnostics assume a half-cycle
            # phase split. They are intentionally omitted from this unequal-cycle study.
            result[method][cfg['trial']]={k:summary[k] for k in ('offers','capacity_rps','miss_pct','rejections','queue_peak')}
            result[method][cfg['trial']]['deadline_miss_pct']={str(ms): 100*sum(r['rejected'] or r['latency_sec']>ms/1000 for r in rows)/len(rows) for ms in c.DEADLINES_MS}
            per_id[method][cfg['trial']]=rows
    return result,per_id


def primary_report(rows,calibration,predictions,design,collection_complete=False):
    wanted={s['id'] for s in design['trial_order'] if s['kind']=='validation'}
    if len({r['trial'] for r in rows})!=len(rows) or not {r['trial'] for r in rows}<=wanted:raise ValueError('duplicate/foreign validation rows')
    complete=collection_complete and {r['trial'] for r in rows}==wanted
    result=dict(decision='comparison_incomplete',complete=complete,accepted_validation_trials=len(rows),
        calibration_usable=calibration['usable'],methods={},advantages={},novelty_established=False,
        limits='One service, one host and quota. Shared constant-rate FIFO model. Four validation blocks; t intervals assume independent approximately normal block errors. Quadratic baseline is a declared polynomial benchmark, not a reproduction of a published load-dependent algorithm.')
    if not calibration['usable']:result['decision']='calibration_qualification_failed';return result
    for method,value in calibration['methods'].items():
        if value['status']!='available':result['methods'][method]=value;continue
        errors=[]
        for r in rows:
            predicted=predictions[method][r['trial']]
            cap=value['capacity_rps'];lo,hi=r['busy_capacity_bounds_rps']
            capacity_error=max(abs(cap/x-1)*100 for x in (lo,hi)) if lo>0 else None
            errors.append(dict(trial=r['trial'],block=r['block'],deadline_error_pp=abs(predicted['miss_pct']-r['miss_pct']),
                capacity_error_pct=capacity_error,state_eligible=r['state_eligible'],all_successful=r['all_successful'],
                observed_miss_pct=r['miss_pct'],predicted_miss_pct=predicted['miss_pct'],
                predicted_capacity_rps=cap,observed_capacity_bounds_rps=[lo,hi]))
        qualified=complete and all(r['state_eligible'] and r['all_successful'] for r in rows)
        accuracy=qualified and all(e['deadline_error_pp']<=design['rules']['deadline_error_pp'] and
             e['capacity_error_pct'] is not None and e['capacity_error_pct']<=design['rules']['capacity_error_pct'] for e in errors)
        result['methods'][method]=dict(status='available',errors=errors,accuracy_pass=accuracy,
            deadline_mae_pp=st.mean(e['deadline_error_pp'] for e in errors) if errors else None)
    if not complete:return result
    if not all(r['state_eligible'] and r['all_successful'] for r in rows):result['decision']='validation_state_or_cohort_failed';return result
    for comparator in ('whole','idle_corrected','regression','quadratic'):
        if result['methods'][comparator]['status']!='available':continue
        busy={e['trial']:e for e in result['methods']['busy']['errors']}
        errors=result['methods'][comparator]['errors']
        contrasts=[st.mean(e['deadline_error_pp']-busy[e['trial']]['deadline_error_pp'] for e in errors if e['block']==block) for block in range(1,5)]
        interval=interval_summary([[x,x] for x in contrasts],design['analysis']['t_critical_95_df3'])
        interval['advantage_pass']=all(x>0 for x in contrasts) and interval['model_based_95_interval'][0]>=design['rules']['advantage_pp']
        result['advantages'][comparator]=interval
    if not result['methods']['busy']['accuracy_pass']:result['decision']='busy_predictive_screen_failed'
    elif any(result['methods'][m]['status']!='available' for m in ('regression','quadratic')):result['decision']='established_comparator_unavailable'
    elif any(result['methods'][m]['accuracy_pass'] for m in ('regression','quadratic')):result['decision']='established_comparator_adequate'
    elif all(result['advantages'][m]['advantage_pass'] for m in ('regression','quadratic')):result['decision']='busy_advantage_over_declared_comparators'
    else:result['decision']='predictive_advantage_inconclusive'
    return result


def report(rows,calibration,predictions,design,collection_complete=False):
    result=primary_report(rows,calibration,predictions,design,collection_complete)
    result['context']=c.ACTIVE
    result['generality_scope']='Single application and host; independently calibrated quota/work-size context. Sequential contexts are confounded with time; no causal cross-context effect or multi-application claim.'
    result['deadline_grid_status']='Prespecified secondary diagnostics; primary accuracy screen is 500ms only. No new phase mechanism or model is tested.'
    result['deadline_grid']={}
    if not calibration.get('usable') or not rows:return result
    for method,value in calibration['methods'].items():
        if value['status']!='available':continue
        result['deadline_grid'][method]={}
        for ms in c.DEADLINES_MS:
            errors=[dict(trial=r['trial'],block=r['block'],observed_miss_pct=r['deadline_miss_pct'][str(ms)],
                         predicted_miss_pct=predictions[method][r['trial']]['deadline_miss_pct'][str(ms)],
                         absolute_error_pp=abs(r['deadline_miss_pct'][str(ms)]-predictions[method][r['trial']]['deadline_miss_pct'][str(ms)])) for r in rows]
            result['deadline_grid'][method][str(ms)]=dict(errors=errors,mae_pp=st.mean(e['absolute_error_pp'] for e in errors),maximum_error_pp=max(e['absolute_error_pp'] for e in errors))
    return result
