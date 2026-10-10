"""Fixed-window composition comparison with bounded, block-level uncertainty."""
import bisect
import itertools
import math
import statistics as st
import v23_model as queue
import v24r3_model as retained
from kernel_bridge_analysis import clock_join

validate_samples=retained.validate_samples


def trial(derived, server, anchors, probe, config, design, expected_path):
    mapping=derived['clocks']
    origin=tuple(mapping['client_test_start_ns']+mapping['server_minus_client_'+k+'_ns'] for k in ('lower','upper'))
    jobs=server['events']
    q=queue.series([j['admission_ns'] for j in jobs],[j['worker_start_ns'] for j in jobs])
    ends=sorted(j['completion_ns'] for j in jobs)
    windows=design['windows']['busy']
    counts=retained.completion_bounds(ends,origin,windows)
    duration=sum(b-a for a,b in windows)
    middle=(origin[0]+origin[1])/2
    point=sum(bisect.bisect_left(ends,middle+b*1e9)-bisect.bisect_left(ends,middle+a*1e9) for a,b in windows)
    minima=[queue.min_window(q,origin[0]+a*1e9,origin[1]+b*1e9) for a,b in windows]
    whole=derived['summary']['cpu_usec_per_completed_work']
    misses=100*(1-derived['summary']['timely_500_fraction'])
    if not math.isfinite(whole) or whole<=0 or point<=0 or counts[0]<=0 or not math.isfinite(misses) or not 0<=misses<=100:
        raise ValueError('invalid whole cost or guaranteed busy throughput')
    row=dict(trial=config['trial'],size='small',block=config['block'],order=config['order'],
        low_rate=config['low_rate'],counter_probe=config['counter_probe'],recording_quality_pass=True,
        whole_cpu_usec_per_job=whole,miss_pct=misses,busy_capacity_rps=point/duration,
        busy_capacity_bounds_rps=[x/duration for x in counts],busy_queue_minima=minima,
        busy_queue_eligible=all(x>0 for x in minima),
        cohort_all_successful=derived['summary']['failure_fraction']==0 and derived['summary']['warmup_all_successful'])
    if probe is None:
        if config['counter_probe']:raise ValueError('sampler-on trial lacks counters')
        return row
    if not config['counter_probe']:raise ValueError('sampler-off trial has counter evidence')
    samples=validate_samples(probe,expected_path)
    joined=clock_join(anchors,mapping,server['clock_generation'])
    host_origin=tuple(mapping['client_test_start_ns']+joined['kernel_minus_client_'+k+'_ns'] for k in ('lower','upper'))
    for offset in (0,config['duration_sec']):
        retained.counter_bounds(samples,host_origin[0]+offset*1e9,host_origin[1]+offset*1e9)
    relevant=[r for r in samples if r['after_ns']>=host_origin[0] and r['before_ns']<=host_origin[1]+config['duration_sec']*1e9]
    if any(b['before_ns']-a['after_ns']>design['sampler']['max_gap_ms']*1e6 for a,b in zip(relevant,relevant[1:])):
        raise ValueError('measurement counter gap exceeds50ms')
    phases={name:retained.phase(samples,jobs,q,host_origin,origin,design['windows'][name],name=='busy') for name in ('busy','low')}
    phases['busy']['state_eligible']=row['busy_queue_eligible']
    phases['busy']['state_definition']='guaranteed_positive_waiting_queue'
    low=phases['low'];throttle=low['cpu_delta_bounds'].get('nr_throttled')
    low['state_eligible']=all(x<=1 for x in low['queue_maxima']) and throttle is not None and throttle[1]==0
    low['state_definition']='at_most_one_waiting_job_and_no_throttled_periods'
    delivery=phases['busy']['delivered_cpu_fraction_bounds']
    busy_cost=phases['busy']['cpu_usec_per_completion_bounds']
    row.update(phases=phases,measurement_quality=retained.window_quality(phases,design),
        busy_delivery_near_nominal=design['rules']['busy_delivery_min']<=delivery[0] and delivery[1]<=design['rules']['busy_delivery_max'],
        whole_over_busy_cost_bounds=[whole/busy_cost[1],whole/busy_cost[0]],
        low_over_busy_cost_bounds=[low['cpu_usec_per_completion_bounds'][0]/busy_cost[1],low['cpu_usec_per_completion_bounds'][1]/busy_cost[0]],
        acquisition_diagnostics=retained.acquisition_diagnostics(probe),sampler_own_cpu_ms=probe['own_cpu_ns']/1e6)
    return row


def difference(high, low, metric):
    if metric=='whole_cpu_usec_per_job':
        point=100*(high[metric]/low[metric]-1)
        return [point,point]
    a=high['busy_capacity_bounds_rps'];b=low['busy_capacity_bounds_rps']
    return [100*(a[0]/b[1]-1),100*(a[1]/b[0]-1)]


def interval_summary(bounds, critical):
    """Enclose all paired-t intervals allowed by deterministic input bounds.

    SD is convex, so its maximum on the small 4D box occurs at a vertex.
    This deliberately uses the largest SD with both mean endpoints, avoiding
    treating midpoint estimates or individual jobs as independent repetitions.
    """
    if len(bounds)!=4 or any(len(b)!=2 or not all(math.isfinite(x) for x in b) or b[0]>b[1] for b in bounds):
        raise ValueError('four finite ordered block intervals required')
    points=[st.mean(b) for b in bounds]
    largest_sd=max(st.stdev(vertex) for vertex in itertools.product(*bounds))
    mean_bounds=[st.mean(b[k] for b in bounds) for k in (0,1)]
    half=critical*largest_sd/math.sqrt(4)
    return dict(n_blocks=4,block_bounds=bounds,midpoint_mean=st.mean(points),midpoint_sample_sd=st.stdev(points),
        mean_accounting_bounds=mean_bounds,maximum_sample_sd_over_accounting_bounds=largest_sd,
        model_based_95_interval=[mean_bounds[0]-half,mean_bounds[1]+half],
        assumptions='Independent approximately normal block contrasts; four blocks give only three degrees of freedom. No job-level replication or distribution-free guarantee.')


def report(trials, design, collection_complete=True):
    slots={r['id']:r for r in design['trial_order']}
    ids=[r['trial'] for r in trials]
    if len(set(ids))!=len(ids) or not set(ids)<=set(slots):raise ValueError('duplicate or foreign composition trial')
    for row in trials:
        slot=slots[row['trial']]
        if (row['size']!='small' or row['recording_quality_pass'] is not True
                or row['order']!=slot['collection_order'] or type(row['counter_probe']) is not bool
                or any(row[k]!=slot[k] for k in ('block','low_rate','counter_probe'))
                or any(not math.isfinite(row[k]) or row[k]<=0 for k in ('whole_cpu_usec_per_job','busy_capacity_rps'))
                or not math.isfinite(row['miss_pct']) or not 0<=row['miss_pct']<=100
                or len(row['busy_capacity_bounds_rps'])!=2
                or not 0<row['busy_capacity_bounds_rps'][0]<=row['busy_capacity_rps']<=row['busy_capacity_bounds_rps'][1]
                or any(not math.isfinite(x) for x in row['busy_capacity_bounds_rps'])
                or type(row['busy_queue_eligible']) is not bool or type(row['cohort_all_successful']) is not bool):
            raise ValueError('composition identity or recording quality differs')
        if row['counter_probe']:
            if set(row.get('phases',{}))!={'busy','low'} or row.get('measurement_quality',{}).get('pass_budget') is not True:
                raise ValueError('sampler-on phase recording quality missing')
        elif 'phases' in row:raise ValueError('off trial contains counter-phase evidence')
    recordings_complete=set(ids)==set(slots)
    complete=recordings_complete and collection_complete
    result=dict(decision='composition_incomplete',complete=complete,recording_quality_pass=recordings_complete,
        accepted_trials=len(trials),planned_trials=16,by_sampler={},observer_interaction={},
        composition_screen_pass=False,scientific_explanation_established=False,equivalence_established=False,novelty_established=False,
        limits='This is a bounded single-service composition screen. Model-based intervals require independent approximately normal block contrasts. No universal equivalence, runtime mechanism, deadline-sampler neutrality, estimator superiority or novelty is established. No follow-on collection is launched.')
    if not complete:return result
    cohort=all(r['cohort_all_successful'] for r in trials)
    state=all(r['busy_queue_eligible'] for r in trials) and all(all(p['state_eligible'] for p in r['phases'].values()) and r['busy_delivery_near_nominal'] for r in trials if r['counter_probe'])
    result.update(cohort_all_successful=cohort,all_required_states_eligible=state)
    contrasts={}
    for on in (False,True):
        label='on' if on else 'off'
        group={}
        for metric in ('whole_cpu_usec_per_job','busy_capacity_rps'):
            values=[];pairs=[]
            for block in range(1,5):
                a=next(r for r in trials if r['block']==block and r['counter_probe']==on and r['low_rate']==15)
                b=next(r for r in trials if r['block']==block and r['counter_probe']==on and r['low_rate']==30)
                values.append(difference(b,a,metric));pairs.append(dict(block=block,low15=a['trial'],low30=b['trial'],order='15_then_30' if a['order']<b['order'] else '30_then_15'))
            summary=interval_summary(values,design['analysis']['t_critical_95_df3'])
            summary['pairs']=pairs
            ci=summary['model_based_95_interval']
            if metric=='whole_cpu_usec_per_job':
                summary['screen_pass']=ci[0]>=design['rules']['whole_cost_min_increase_pct'] and all(b[0]>0 for b in values)
            else:
                margin=design['rules']['busy_capacity_margin_pct']
                summary['screen_pass']=ci[0]>=-margin and ci[1]<=margin and all(-margin<=b[0]<=b[1]<=margin for b in values)
            group[metric]=summary
            contrasts[(on,metric)]=values
        result['by_sampler'][label]=group
    for metric in ('whole_cpu_usec_per_job','busy_capacity_rps'):
        values=[[on[0]-off[1],on[1]-off[0]] for on,off in zip(contrasts[(True,metric)],contrasts[(False,metric)])]
        summary=interval_summary(values,design['analysis']['t_critical_95_df3'])
        margin=design['rules']['observer_interaction_margin_pp'];ci=summary['model_based_95_interval']
        summary['screen_pass']=ci[0]>=-margin and ci[1]<=margin
        result['observer_interaction'][metric]=summary
    # Off/on levels remain descriptive; only interaction screens the treatment contrast.
    result['observer_levels']={str(rate):{metric:interval_summary([
        difference(next(r for r in trials if r['block']==block and r['low_rate']==rate and r['counter_probe']),
                   next(r for r in trials if r['block']==block and r['low_rate']==rate and not r['counter_probe']),metric)
        for block in range(1,5)],design['analysis']['t_critical_95_df3'])
        for metric in ('whole_cpu_usec_per_job','busy_capacity_rps')} for rate in (15,30)}
    cost=all(g['whole_cpu_usec_per_job']['screen_pass'] for g in result['by_sampler'].values())
    busy=all(g['busy_capacity_rps']['screen_pass'] for g in result['by_sampler'].values())
    observer=all(g['screen_pass'] for g in result['observer_interaction'].values())
    result.update(cost_screen_pass=cost,busy_stability_screen_pass=busy,observer_interaction_screen_pass=observer)
    if not cohort:decision='cohort_outcomes_ineligible'
    elif not state:decision='mixed_state_qualification_failed'
    elif cost and busy and observer:decision='composition_screen_supported'
    elif any(g['busy_capacity_rps']['model_based_95_interval'][0]>design['rules']['busy_capacity_margin_pct'] or
             g['busy_capacity_rps']['model_based_95_interval'][1]<-design['rules']['busy_capacity_margin_pct'] for g in result['by_sampler'].values()):
        decision='busy_capacity_changed_materially'
    elif any(g['whole_cpu_usec_per_job']['model_based_95_interval'][1]<design['rules']['whole_cost_min_increase_pct'] for g in result['by_sampler'].values()):
        decision='composition_effect_below_target'
    elif not observer:decision='observer_interaction_unresolved'
    else:decision='composition_inconclusive'
    result.update(decision=decision,composition_screen_pass=decision=='composition_screen_supported')
    return result
