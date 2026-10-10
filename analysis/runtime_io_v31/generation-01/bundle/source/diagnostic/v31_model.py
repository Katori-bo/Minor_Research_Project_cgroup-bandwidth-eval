"""Calibration-only paired latency CDF and predeclared V31 block comparisons."""
from bisect import bisect_right
import math
import statistics as st
import sys
import v31_common as c
import v29_model as retained
import v23_model as fifo

sys.path.append(str(c.ROOT/'analysis'))
from periodic_budget_model import replay

PHASES=tuple(i*.001 for i in range(100))
PRIMARY='joint_calibration_cdf'
COMPARATOR='periodic_uniform_phase_calibrated_delay'
FLUID='fluid_busy'
calibrate=retained.calibrate


def stage_counts(requests,ms):
    threshold=ms*1000000
    misses=[r for r in requests if not r['success'] or r['e2e_ns']>threshold]
    result=dict(misses=len(misses),unsuccessful=sum(not r['success'] for r in misses),
        computation_certainly_after=sum(r['success'] and r['completion_after_offered_lower_ns']>threshold for r in misses),
        computation_certainly_within_but_client_missed=sum(r['success'] and r['completion_after_offered_upper_ns']<=threshold for r in misses),
        computation_boundary_ambiguous=sum(r['success'] and r['completion_after_offered_lower_ns']<=threshold<r['completion_after_offered_upper_ns'] for r in misses))
    if sum(v for k,v in result.items() if k!='misses')!=result['misses']:raise ValueError('stage miss conservation failed')
    return result


def trial(derived,server,anchors,probe,cfg,design,expected_path):
    if cfg['role']!='validation':return retained.trial(derived,server,anchors,probe,cfg,design,expected_path)
    if probe is not None or cfg['counter_probe']:raise ValueError('sampler must remain off')
    s=derived['summary'];w=s['counter_window'];requests=derived['requests'];domain=design['scientific_domain']
    if len(requests)!=s['offered'] or not requests:raise ValueError('all offered rows required')
    low_queue=sum(r.get('worker_observed') is True and r.get('queue_ns') is not None
                  and 0<=r['queue_ns']<=domain['maximum_queue_ns'] for r in requests)
    throttling_ok=w['delta']['nr_throttled']<=domain['maximum_measurement_throttled_periods']
    queue_ok=low_queue/s['offered']>=domain['minimum_observed_low_queue_fraction']
    row=dict(context=c.ACTIVE,trial=cfg['trial'],role='validation',block=cfg['block'],order=cfg['order'],
        profile=cfg['profile'],offers=s['offered'],completed=s['completed_computations'],
        cpu_sec=w['delta']['usage_usec']/1e6,accounted_wall_sec=(w['after_ns']-w['before_ns'])/1e9,
        state_eligible=throttling_ok and queue_ok,scientific_domain_pass=throttling_ok and queue_ok,
        domain=dict(zero_measurement_throttling=throttling_ok,observed_low_queue_fraction=low_queue/s['offered'],
                    observed_low_queue_offers=low_queue,all_offers=s['offered'],low_queue_pass=queue_ok),
        all_successful=s['failure_fraction']==0 and s['warmup_all_successful'],failure_fraction=s['failure_fraction'],
        clock_uncertainty_ns=s['clock_uncertainty_ns'],queue_peak=s['logical_backlogs']['admitted_not_started']['peak'],
        throttled_periods=w['delta']['nr_throttled'])
    row['deadline_miss_pct']={str(ms):100*sum(not r['success'] or r['e2e_ns']>ms*1000000 for r in requests)/s['offered'] for ms in c.DEADLINES_MS}
    row['stage_diagnostics']={str(ms):stage_counts(requests,ms) for ms in c.DEADLINES_MS}
    return row


def distribution(values):
    ordered=sorted(values)
    return dict(n=len(values),mean=st.mean(values),p50=st.median(values),
                p95=ordered[math.ceil(.95*len(values))-1],p99=ordered[math.ceil(.99*len(values))-1],maximum=ordered[-1])


def empirical_probability(samples_ns,ms):
    if not samples_ns or any(not math.isfinite(x) or x<0 for x in samples_ns):raise ValueError('nonempty finite nonnegative timing samples required')
    return (len(samples_ns)-bisect_right(sorted(samples_ns),ms*1000000))/len(samples_ns)


def independent_probability(workers_ns,residuals_ns,ms):
    if not workers_ns or not residuals_ns or any(not math.isfinite(x) or x<0 for x in workers_ns+residuals_ns):
        raise ValueError('nonempty finite nonnegative timing marginals required')
    residuals=sorted(residuals_ns)
    return sum(len(residuals)-bisect_right(residuals,ms*1000000-w) for w in workers_ns)/(len(workers_ns)*len(residuals))


def timing_grid(samples):
    totals=[r['total_ns'] for r in samples];workers=[r['worker_ns'] for r in samples];residuals=[r['residual_ns'] for r in samples]
    median=st.median(workers)
    return {PRIMARY:{str(ms):empirical_probability(totals,ms) for ms in c.DEADLINES_MS},
        'independent_worker_response_convolution':{str(ms):independent_probability(workers,residuals,ms) for ms in c.DEADLINES_MS},
        'median_worker_plus_response':{str(ms):empirical_probability([median+r for r in residuals],ms) for ms in c.DEADLINES_MS}}


def fit_calibration(session,values,refs):
    # Validate inventories before any fit, including failed-capacity cases.
    configs={x['trial']:x for x in c.calibration_configs()}
    if set(refs)!=set(configs):raise ValueError('exact fresh calibration references required; validation is prohibited')
    result=calibrate(values,c.design())
    if not result['usable']:return result
    paired=[];cohorts={};contract=c.design()['timing_calibration']
    mixed=[r for r in values if r['role']=='mixed']
    result['capacity_sensitivity_rps']=[min(r['busy_capacity_bounds_rps'][0] for r in mixed),max(r['busy_capacity_bounds_rps'][1] for r in mixed)]
    for trial,ref in refs.items():
        cfg=configs[trial]
        if cfg['role']!='steady' or cfg['reference_low_rate'] not in contract['reference_low_rates']:continue
        directory=c.resolve(session,ref['path']);c.verify_seal(directory)
        if c.digest(directory/'seal.json')!=ref['seal'] or c.read(directory/'config.json')!=cfg:
            raise ValueError('fresh calibration source/config changed')
        requests=c.read(directory/'derived.json')['requests'];selected=[]
        for r in requests:
            if not r['success'] or r['queue_ns']>contract['maximum_queue_ns']:continue
            worker=r['processing_wall_ns'];total=r['e2e_ns']-r['queue_ns'];residual=total-worker
            if any(not math.isfinite(x) or x<0 for x in (r['queue_ns'],worker,total,residual)):
                result.update(usable=False,decision='calibration_timing_unavailable',timing_status='negative/nonfinite stage; no clipping')
                return result
            selected.append(dict(id=r['id'],worker_ns=worker,residual_ns=residual,total_ns=total))
        cohorts[trial]=dict(offered=len(requests),accepted=len(selected),samples=selected)
        if not selected:
            result.update(usable=False,decision='calibration_timing_unavailable',timing_status='empty eligible calibration cohort',timing_cohorts=cohorts)
            return result
        paired.extend(dict(r,trial=trial) for r in selected)
    if len(cohorts)!=contract['cohort_count']:raise ValueError('exact four fresh timing cohorts required')
    delays=sorted(r['residual_ns']/1e9 for r in paired)
    for value in cohorts.values():value['deadline_miss_pct']={name:{ms:100*p for ms,p in grid.items()} for name,grid in timing_grid(value['samples']).items()}
    result.update(timing_status='available',paired_samples=paired,timing_cohorts=cohorts,
        timing_trial_count=len(cohorts),timing_samples=len(paired),delay_status='available',delay_sec=delays,
        delay_trials=sorted(cohorts),delay_samples=len(delays),delay_mean_ms=1000*st.mean(delays),
        timing_distributions_ns={name:distribution([r[name] for r in paired]) for name in ('worker_ns','residual_ns','total_ns')},
        sensitivity_contract='Four calibration trials; pooled requests are not experiment replicates. Per-cohort curves are descriptive.')
    return result


def probabilities(latencies,delays=None):
    if delays is not None and (not delays or any(not math.isfinite(x) or x<0 for x in delays)):
        raise ValueError('finite nonnegative calibration delay distribution required')
    ordered=sorted(delays) if delays is not None else None
    return {str(ms):[1. if x is None else (float(x>ms/1000) if ordered is None else
        (len(ordered)-bisect_right(ordered,ms/1000-x))/len(ordered)) for x in latencies] for ms in c.DEADLINES_MS}


def forecast_profile(cal,cfg):
    offsets=c.schedule(cfg);busy=cal['methods']['busy']['capacity_rps'];delay=cal['delay_sec']
    q=cfg['quota_us']/1e6;p=cfg['period_us']/1e6;vectors={};unavailable={}
    for name,grid in timing_grid(cal['paired_samples']).items():vectors[name]={ms:[value]*len(offsets) for ms,value in grid.items()}
    for method,label in (('busy',FLUID),('quadratic','fluid_quadratic')):
        value=cal['methods'][method]
        if value['status']!='available':unavailable[label]=value;continue
        jobs,_=fifo.simulate(offsets,value['capacity_rps'],cfg['burst_period_sec'])
        vectors[label]=probabilities([None if r['rejected'] else r['latency_sec'] for r in jobs])
    accumulated={str(ms):[0.]*len(offsets) for ms in c.DEADLINES_MS}
    envelope={str(ms):[100.,0.] for ms in c.DEADLINES_MS}
    for capacity in sorted(set((cal['capacity_sensitivity_rps'][0],busy,cal['capacity_sensitivity_rps'][1]))):
        for initial in (0.,1.):
            for phase in PHASES:
                lat=replay(offsets,capacity,q,p,phase,initial);grid=probabilities(lat)
                for ms,values in grid.items():
                    value=100*st.mean(values);envelope[ms]=[min(envelope[ms][0],value),max(envelope[ms][1],value)]
                if capacity==busy and initial==1.:
                    dg=probabilities(lat,delay)
                    for ms in dg:
                        for i,value in enumerate(dg[ms]):accumulated[ms][i]+=value
                    if phase==0.:vectors['periodic_zero_phase_full_budget']=grid
    vectors[COMPARATOR]={ms:[x/len(PHASES) for x in values] for ms,values in accumulated.items()}
    summary={}
    for name,grid in vectors.items():
        percentages={ms:100*st.mean(values) for ms,values in grid.items()};values=[percentages[str(ms)] for ms in c.DEADLINES_MS]
        summary[name]=dict(status='available',offers=len(offsets),deadline_miss_pct=percentages,
                           deadline_grid_monotone=all(a>=b for a,b in zip(values,values[1:])))
    for name,value in unavailable.items():summary[name]=dict(value)
    return summary,vectors,envelope


def forecast(calibration,configs):
    if not calibration['usable'] or calibration.get('timing_status')!='available':raise ValueError('fresh qualified timing calibration required')
    if c.design()['phase_prior']!=dict(phases_sec=list(PHASES),initial_credit_fraction=1):raise ValueError('phase contract changed')
    methods={};per_offer={};envelopes={};cache={}
    for cfg in configs:
        if cfg['profile'] not in cache:cache[cfg['profile']]=forecast_profile(calibration,cfg)
        summary,vectors,envelope=cache[cfg['profile']]
        for name,value in summary.items():methods.setdefault(name,{})[cfg['trial']]=value
        for name,value in vectors.items():per_offer.setdefault(name,{})[cfg['trial']]=value
        envelopes[cfg['trial']]=envelope
    return dict(methods=methods,sampled_envelopes=envelopes,
        envelope_contract='Sampled phase/empty-full/capacity scenarios without added delay; descriptive, not confidence bounds'),per_offer


def report(rows,calibration,predictions,design,collection_complete=False):
    wanted={cfg['trial']:cfg for cfg in c.validation_configs()};ids={r['trial'] for r in rows}
    if len(ids)!=len(rows) or not ids<=wanted.keys():raise ValueError('duplicate/foreign validation rows')
    for r in rows:
        if any(r[k]!=wanted[r['trial']][k] for k in ('block','profile','order')):raise ValueError('validation block/profile/order differs')
    complete=collection_complete and ids==wanted.keys()
    result=dict(decision='comparison_incomplete',complete=complete,accepted_validation_trials=len(rows),
        calibration_usable=calibration['usable'],methods={},deadline_grid={},gates={},
        primary_deadline_ms=10,decision_deadlines_ms=[10,12],primary_miss_budget_pct=5,novelty_established=False,
        limits='One service and host in a declared low-queue unthrottled domain. Unknown phase has an assumed uniform prior. Six block t interval assumes approximately independent normal contrasts. Calibration requests are not replicates. No causal phase claim or hard guarantee.')
    if not calibration['usable']:result['decision']=calibration.get('decision','calibration_qualification_failed');return result
    if not predictions:return result
    for method,trials in predictions['methods'].items():
        if next(iter(trials.values()))['status']!='available':result['methods'][method]=next(iter(trials.values()));continue
        result['deadline_grid'][method]={}
        for ms in c.DEADLINES_MS:
            errors=[]
            for row in rows:
                observed=row['deadline_miss_pct'][str(ms)];predicted=trials[row['trial']]['deadline_miss_pct'][str(ms)]
                errors.append(dict(trial=row['trial'],block=row['block'],profile=row['profile'],observed_miss_pct=observed,
                    predicted_miss_pct=predicted,signed_error_pp=predicted-observed,absolute_error_pp=abs(predicted-observed),
                    observed_slo_pass=observed<=5,predicted_slo_pass=predicted<=5))
            result['deadline_grid'][method][str(ms)]=dict(errors=errors,mae_pp=st.mean(e['absolute_error_pp'] for e in errors) if errors else None,
                maximum_error_pp=max((e['absolute_error_pp'] for e in errors),default=None),
                slo_matches=sum(e['observed_slo_pass']==e['predicted_slo_pass'] for e in errors))
            result['deadline_grid'][method][str(ms)]['per_profile']={profile:dict(
                trials=len(selected),mae_pp=st.mean(e['absolute_error_pp'] for e in selected),
                maximum_error_pp=max(e['absolute_error_pp'] for e in selected),
                mean_observed_miss_pct=st.mean(e['observed_miss_pct'] for e in selected),
                mean_predicted_miss_pct=st.mean(e['predicted_miss_pct'] for e in selected))
                for profile in ('A','B','C') if (selected:=[e for e in errors if e['profile']==profile])}
        result['methods'][method]=dict(status='available',**result['deadline_grid'][method]['10'])
    result['scientific_domain_exits']=[r['trial'] for r in rows if not r['scientific_domain_pass']]
    if not complete:return result
    primary=result['methods'][PRIMARY]['errors'];comparison=result['methods'][COMPARATOR]['errors']
    blocks=[]
    for block in range(1,7):
        a=[e for e in primary if e['block']==block];b=[e for e in comparison if e['block']==block]
        if len(a)!=3 or {e['profile'] for e in a}!={'A','B','C'}:raise ValueError('exact three profiles per block required')
        mae=st.mean(e['absolute_error_pp'] for e in a);other=st.mean(e['absolute_error_pp'] for e in b)
        some=any(e['observed_slo_pass'] for e in result['deadline_grid'][PRIMARY]['12']['errors'] if e['block']==block)
        blocks.append(dict(block=block,cdf_mae_pp=mae,periodic_mae_pp=other,improvement_pp=other-mae,some_profile_slo_pass_12ms=some))
    contrasts=[x['improvement_pp'] for x in blocks];mean=st.mean(contrasts)
    multiplier=2.571;margin=multiplier*st.stdev(contrasts)/math.sqrt(6)
    gates=dict(complete_technically_qualified_trials=True,all_trials_inside_scientific_domain=not result['scientific_domain_exits'],
        cdf_mean_block_mae_le_3=st.mean(x['cdf_mae_pp'] for x in blocks)<=3,every_block_positive=all(x>0 for x in contrasts),
        improvement_95_lower_ge_5=mean-margin>=5,
        all_trial_slo_decisions_match_10ms=all(e['observed_slo_pass']==e['predicted_slo_pass'] for e in primary),
        all_trial_slo_decisions_match_12ms=all(e['observed_slo_pass']==e['predicted_slo_pass'] for e in result['deadline_grid'][PRIMARY]['12']['errors']),
        some_profile_meets_12ms_slo_every_block=all(x['some_profile_slo_pass_12ms'] for x in blocks))
    decision='low_queue_timing_prediction_confirmed' if all(gates.values()) else 'low_queue_timing_confirmation_failed_or_inconclusive'
    if result['scientific_domain_exits']:decision='scientific_domain_exit'
    result.update(blocks=blocks,paired_improvement=dict(mean_pp=mean,model_based_95_interval=[mean-margin,mean+margin],t_multiplier=multiplier,df=5),gates=gates,decision=decision)
    return result
