"""Fresh calibration, sealed ordinary timing forecasts and six-block V30 gates."""
from bisect import bisect_right
import math
import statistics as st
import sys
import v30_common as c
import v29_model as retained
import v23_model as fifo

sys.path.append(str(c.ROOT/'analysis'))
from periodic_budget_model import replay

PHASES=tuple(i*.001 for i in range(100))
PRIMARY='periodic_uniform_phase_calibrated_delay'
FLUID='fluid_busy'
calibrate=retained.calibrate


def trial(derived,server,anchors,probe,cfg,design,expected_path):
    if cfg['role']!='validation':return retained.trial(derived,server,anchors,probe,cfg,design,expected_path)
    if probe is not None or cfg['counter_probe']:raise ValueError('sampler must remain off')
    s=derived['summary'];w=s['counter_window'];wall=(w['after_ns']-w['before_ns'])/1e9
    # Raw replay already verifies clocks, resource state and every offered ID.
    # Deliberately no queue occupancy or minimum throughput eligibility filter.
    row=dict(context=c.ACTIVE,trial=cfg['trial'],role='validation',block=cfg['block'],order=cfg['order'],
             profile=cfg['profile'],offers=s['offered'],completed=s['completed_computations'],
             cpu_sec=w['delta']['usage_usec']/1e6,accounted_wall_sec=wall,state_eligible=True,
             all_successful=s['failure_fraction']==0 and s['warmup_all_successful'],
             failure_fraction=s['failure_fraction'],clock_uncertainty_ns=s['clock_uncertainty_ns'],
             queue_peak=s['logical_backlogs']['admitted_not_started']['peak'],
             throttled_periods=w['delta']['nr_throttled'])
    requests=derived['requests']
    row['deadline_miss_pct']={str(ms):100*sum(not r['success'] or r['e2e_ns']>ms*1000000 for r in requests)/s['offered'] for ms in c.DEADLINES_MS}
    failed=[r for r in requests if not r['success'] or r['e2e_ns']>25000000]
    row['stage_diagnostics_25ms']=dict(misses=len(failed),unsuccessful=sum(not r['success'] for r in failed),
        computation_certainly_after=sum(r['success'] and r['completion_after_offered_lower_ns']>25000000 for r in failed),
        computation_certainly_within_but_client_missed=sum(r['success'] and r['completion_after_offered_upper_ns']<=25000000 for r in failed),
        computation_boundary_ambiguous=sum(r['success'] and r['completion_after_offered_lower_ns']<=25000000<r['completion_after_offered_upper_ns'] for r in failed))
    return row


def fit_calibration(session,values,refs):
    result=calibrate(values,c.design())
    if not result['usable']:return result
    delays=[];trials=[];mixed=[r for r in values if r['role']=='mixed']
    result['capacity_sensitivity_rps']=[min(r['busy_capacity_bounds_rps'][0] for r in mixed),max(r['busy_capacity_bounds_rps'][1] for r in mixed)]
    configs={x['trial']:x for x in c.calibration_configs()}
    if set(refs)!=set(configs):raise ValueError('exact fresh calibration references required')
    for trial,ref in refs.items():
        cfg=configs[trial]
        if cfg['role']!='steady' or cfg['reference_low_rate'] not in (15,30):continue
        directory=c.resolve(session,ref['path']);c.verify_seal(directory)
        if c.digest(directory/'seal.json')!=ref['seal']:raise ValueError('calibration source changed')
        trials.append(trial)
        for r in c.read(directory/'derived.json')['requests']:
            if not r['success'] or r['queue_ns']>100000:continue
            delay=r['e2e_ns']-r['queue_ns']-r['processing_wall_ns']
            if delay<0:
                result.update(usable=False,decision='calibration_delay_unavailable',delay_status='negative residual; no clipping')
                return result
            delays.append(delay/1e9)
    if len(trials)!=4 or not delays:
        result.update(usable=False,decision='calibration_delay_unavailable',delay_status='four low-rate trials and nonempty residual sample required')
        return result
    result.update(delay_status='available',delay_sec=sorted(delays),delay_trials=sorted(trials),
                  delay_samples=len(delays),delay_mean_ms=1000*st.mean(delays))
    return result


def probabilities(latencies,delays=None):
    if delays is not None and (not delays or any(not math.isfinite(x) or x<0 for x in delays)):
        raise ValueError('finite nonnegative calibration delay distribution required')
    sorted_delays=sorted(delays) if delays is not None else None
    return {str(ms):[1. if x is None else
                    (float(x>ms/1000) if sorted_delays is None else
                     1-bisect_right(sorted_delays,ms/1000-x)/len(sorted_delays))
                    for x in latencies] for ms in c.DEADLINES_MS}


def percentage(grid):return {ms:100*st.mean(values) for ms,values in grid.items()}


def forecast_profile(cal,cfg):
    offsets=c.schedule(cfg);busy=cal['methods']['busy']['capacity_rps'];delay=cal['delay_sec']
    q=cfg['quota_us']/1e6;p=cfg['period_us']/1e6
    vectors={};summary={};unavailable={}
    for method,label in (('busy',FLUID),('quadratic','fluid_quadratic')):
        value=cal['methods'][method]
        if value['status']!='available':unavailable[label]=value;continue
        rows,_=fifo.simulate(offsets,value['capacity_rps'],cfg['burst_period_sec'])
        lat=[None if r['rejected'] else r['latency_sec'] for r in rows]
        vectors[label]=probabilities(lat)
        if method=='busy':vectors['fluid_busy_calibrated_delay']=probabilities(lat,delay)
    accumulated={str(ms):[0.]*len(offsets) for ms in c.DEADLINES_MS}
    accumulated_delay={str(ms):[0.]*len(offsets) for ms in c.DEADLINES_MS}
    envelope={str(ms):[100.,0.] for ms in c.DEADLINES_MS}
    capacities=sorted(set((cal['capacity_sensitivity_rps'][0],busy,cal['capacity_sensitivity_rps'][1])))
    for capacity in capacities:
        for initial in (0.,1.):
            for phase in PHASES:
                lat=replay(offsets,capacity,q,p,phase,initial);grid=probabilities(lat)
                for ms,values in grid.items():
                    value=100*st.mean(values);envelope[ms]=[min(envelope[ms][0],value),max(envelope[ms][1],value)]
                if capacity==busy and initial==1.:
                    dg=probabilities(lat,delay)
                    for ms in grid:
                        for i,value in enumerate(grid[ms]):accumulated[ms][i]+=value
                        for i,value in enumerate(dg[ms]):accumulated_delay[ms][i]+=value
                    if phase==0.:vectors['periodic_zero_phase_full_budget']=grid
    vectors['periodic_uniform_phase']={ms:[x/100 for x in values] for ms,values in accumulated.items()}
    vectors[PRIMARY]={ms:[x/100 for x in values] for ms,values in accumulated_delay.items()}
    vectors['discovery_switch']={str(ms):vectors[PRIMARY if (ms/1000)/p<=c.design()['model_switch_ratio'] else FLUID][str(ms)] for ms in c.DEADLINES_MS}
    for name,grid in vectors.items():
        percentages=percentage(grid);values=[percentages[str(ms)] for ms in c.DEADLINES_MS]
        summary[name]=dict(status='available',offers=len(offsets),deadline_miss_pct=percentages,
                           deadline_grid_monotone=all(a>=b for a,b in zip(values,values[1:])))
    for name,value in unavailable.items():summary[name]=dict(value)
    return summary,vectors,envelope


def forecast(calibration,configs):
    if not calibration['usable'] or calibration.get('delay_status')!='available':raise ValueError('fresh qualified calibration required')
    methods={};per_offer={};envelopes={};cache={}
    for cfg in configs:
        # Identical profiles repeated across blocks have identical prospective forecasts.
        if cfg['profile'] not in cache:cache[cfg['profile']]=forecast_profile(calibration,cfg)
        summary,vectors,envelope=cache[cfg['profile']]
        for name,value in summary.items():methods.setdefault(name,{})[cfg['trial']]=value
        for name,value in vectors.items():per_offer.setdefault(name,{})[cfg['trial']]=value
        envelopes[cfg['trial']]=envelope
    return dict(methods=methods,sampled_envelopes=envelopes,
                envelope_contract='Sampled phase/empty-full/capacity scenarios without added delay; not continuous bounds or confidence intervals'),per_offer


def report(rows,calibration,predictions,design,collection_complete=False):
    wanted={cfg['trial'] for cfg in c.validation_configs()}
    ids={r['trial'] for r in rows}
    if len(ids)!=len(rows) or not ids<=wanted:raise ValueError('duplicate/foreign validation rows')
    complete=collection_complete and ids==wanted
    result=dict(decision='comparison_incomplete',complete=complete,accepted_validation_trials=len(rows),
                calibration_usable=calibration['usable'],methods={},deadline_grid={},gates={},
                primary_deadline_ms=25,primary_miss_budget_pct=5,novelty_established=False,
                limits='One service and host; fresh held-out traffic patterns. Unknown phase is an assumed uniform prior. Six block t interval assumes approximately independent normal contrasts. No causal phase claim or hard service guarantee.')
    if not calibration['usable']:result['decision']=calibration.get('decision','calibration_qualification_failed');return result
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
        result['methods'][method]=dict(status='available',**result['deadline_grid'][method]['25'])
    result['sampled_envelope']={str(ms):dict(covered_trials=sum(predictions['sampled_envelopes'][r['trial']][str(ms)][0]<=r['deadline_miss_pct'][str(ms)]<=predictions['sampled_envelopes'][r['trial']][str(ms)][1] for r in rows),
        mean_width_pp=st.mean(predictions['sampled_envelopes'][r['trial']][str(ms)][1]-predictions['sampled_envelopes'][r['trial']][str(ms)][0] for r in rows) if rows else None) for ms in c.DEADLINES_MS}
    if not complete:return result
    if not all(r['state_eligible'] for r in rows):result['decision']='validation_qualification_failed';return result
    primary=result['methods'][PRIMARY]['errors'];fluid=result['methods'][FLUID]['errors']
    blocks=[]
    for block in range(1,7):
        a=[e for e in primary if e['block']==block];b=[e for e in fluid if e['block']==block]
        if len(a)!=3 or {e['profile'] for e in a}!={'A','B','C'}:raise ValueError('exact three profiles per block required')
        mae=st.mean(e['absolute_error_pp'] for e in a);other=st.mean(e['absolute_error_pp'] for e in b)
        blocks.append(dict(block=block,periodic_mae_pp=mae,fluid_mae_pp=other,improvement_pp=other-mae,
                           some_profile_slo_pass=any(e['observed_slo_pass'] for e in a)))
    contrasts=[x['improvement_pp'] for x in blocks];mean=st.mean(contrasts);margin=2.571*st.stdev(contrasts)/math.sqrt(6)
    gates=dict(complete_qualified_trials=True,periodic_mean_block_mae_le_3=st.mean(x['periodic_mae_pp'] for x in blocks)<=3,
               every_block_positive=all(x>0 for x in contrasts),improvement_95_lower_ge_5=mean-margin>=5,
               all_trial_slo_decisions_match=all(e['observed_slo_pass']==e['predicted_slo_pass'] for e in primary),
               some_profile_meets_slo_every_block=all(x['some_profile_slo_pass'] for x in blocks))
    result.update(blocks=blocks,paired_improvement=dict(mean_pp=mean,model_based_95_interval=[mean-margin,mean+margin],t_multiplier=2.571,df=5),gates=gates,
                  decision='short_deadline_prediction_confirmed' if all(gates.values()) else 'short_deadline_confirmation_failed_or_inconclusive')
    return result
