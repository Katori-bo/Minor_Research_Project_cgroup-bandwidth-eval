#!/usr/bin/env python3
"""Retrospective passive-data/identifiability screen, not a new forecasting method."""
import bisect
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
import v28_model as model

OUT=ROOT/'analysis/runtime_io_passive_novelty_screen/20261008'
SESSION=c.PARENT/'generation-01'


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8):raise ValueError('replay mismatch')


def fifo(offsets,capacity):
    completed=[];head=0;end=0.;late=0
    for ns in offsets:
        arrival=ns/1e9
        while head<len(completed) and completed[head]<=arrival:head+=1
        if len(completed)-head>=129:late+=1;continue
        end=max(arrival,end)+1/capacity;completed.append(end);late+=end-arrival>.5
    return 100*late/len(offsets)


def main():
    if OUT.exists():raise ValueError('preserve existing passive screen')
    latest=read(SESSION/'latest_analysis.json');original=SESSION/latest['path'];c.verify_seal(original)
    if sha(original/'seal.json')!=latest['seal']:raise ValueError('analysis reference mismatch')
    saved=read(original/'report.json');cal=read(SESSION/'calibration_review/report.json')
    passive=[r for r in saved['trial_accounting'] if r['role'] in ('idle','steady')]
    low=[r for r in passive if r['low_rate']<=30]
    preserved=['docs/runtime_io_short_working_draft_v4.md','docs/runtime_io_short_working_draft_v5.md',
        'docs/runtime_io_paper_supporting_material_20261008.md','docs/runtime_io_v28_protocol.md',
        'docs/runtime_io_next_research_decision_20261008.md',
        'analysis/runtime_io_calibration_cost_assessment/20261008/report.json',
        'docs/runtime_io_calibration_cost_assessment_20261008.md']
    plan=dict(status='retrospective_known_validation',date='2026-10-08',source_analysis_seal=sha(original/'seal.json'),
        allowed_predictor_inputs='Twelve idle/steady calibration trials, or six strict-low trials at 0/15/30; no mixed/busy trial, validation outcome or historical capacity enters predictors.',
        script_sha256=sha(Path(__file__)),root_multipliers=[1.10,1.25,1.50],
        ordinary_baselines=['quota divided by pooled low-load CPU/job','quota divided by pooled low-load worker wall/job proxy',
            'V28 linear on twelve nonbacklogged observations','V28 quadratic on twelve nonbacklogged observations',
            'V28 quadratic on six strict-low observations'],
        ambiguity_family='One common monotone piecewise-linear required-CPU curve through pooled per-rate calibration knots; different positive-slope continuations above largest measured throughput. Conditional illustration only; not real CPU service guarantees.',
        validation_reference_pp=3,custom_guard=False,collection=False)
    c.save(OUT/'design/plan.json',plan)
    c.save(OUT/'design/preserved_documents_sha256.json',{p:sha(ROOT/p) for p in preserved});c.seal(OUT/'design')
    inventory=[];low_wall_sum=0;low_jobs=0
    for row in passive:
        if row['trial'] not in cal['trial_refs']:raise ValueError('noncalibration input')
        ref=cal['trial_refs'][row['trial']];d=SESSION/ref['path'];c.verify_seal(d)
        if sha(d/'seal.json')!=ref['seal']:raise ValueError('trial reference mismatch')
        server=read(d/'server_metrics.json');obs=read(d/'observations.json');monitor=read(d/'monitor.json')
        cpu=(obs['measurement_stop']['cpu_stat']['usage_usec']-obs['measurement_start']['cpu_stat']['usage_usec'])/1e6
        wall=(obs['measurement_stop']['after_ns']-obs['measurement_start']['before_ns'])/1e9
        close(cpu,row['cpu_sec']);close(wall,row['accounted_wall_sec']);close(server['completed']/wall,row['throughput_rps'])
        if not row['state_eligible'] or not row['all_successful'] or row['throttled_periods']!=0 or row['queue_peak']>1:
            raise ValueError('retained nonbacklogged eligibility changed')
        if row['role']=='steady':
            client=read(d/'loadgen.json');timely=sum(not q['Error'] and q['StatusCode']==200 and q['EndToEndLatencyNs']<=500000000 for q in client['requests'])
            if timely!=client['total_scheduled']:raise ValueError('nonbacklogged inputs have deadline misses')
        if row['role']=='steady' and row['low_rate']<=30:
            low_wall_sum+=sum(j['processing_ns'] for j in server['events'])/1e9;low_jobs+=server['completed']
        samples=[m for m in monitor if 'cgroup_cpu_stat' in m]
        inventory.append(dict(trial=row['trial'],rate=row['low_rate'],block=row['block'],completed=row['completed'],
            cpu_sec=cpu,accounted_wall_sec=wall,throughput_rps=row['throughput_rps'],utilization=row['utilization'],
            queue_peak=row['queue_peak'],throttled_periods=row['throttled_periods'],miss_pct=row['miss_pct'],
            request_worker_cpu_time_available=bool(server['events'] and 'worker_cpu_ns' in server['events'][0]),
            monitor_cpu_samples=len(samples),native_counter_available=(d/'counter.json').exists(),
            phase_resolved_quota_events_available=False))
    c.save(OUT/'inventory.json',inventory)
    nonidle_low=[r for r in low if r['role']=='steady']
    cpu_cost=sum(r['cpu_sec'] for r in nonidle_low)/sum(r['completed'] for r in nonidle_low)
    fits={
        'low_cpu_demand_law':dict(status='available',capacity_rps=.5/cpu_cost,assumption='Pooled aggregate low-load CPU/job represents loaded CPU demand; unvalidated transfer.'),
        'low_worker_wall_proxy':dict(status='available',capacity_rps=.5/(low_wall_sum/low_jobs),assumption='Low-load worker wall time approximates CPU demand; off-CPU time and loaded transfer unvalidated.'),
        'nonbacklogged_linear':model.regression([(r['throughput_rps'],r['utilization']) for r in passive],.5,False),
        'nonbacklogged_quadratic':model.regression([(r['throughput_rps'],r['utilization']) for r in passive],.5,True),
        'strict_low_quadratic':model.regression([(r['throughput_rps'],r['utilization']) for r in low],.5,True)}
    close(fits['nonbacklogged_linear']['capacity_rps'],saved['calibration']['methods']['regression']['capacity_rps'])
    close(fits['nonbacklogged_quadratic']['capacity_rps'],saved['calibration']['methods']['quadratic']['capacity_rps'])
    block_fits={str(b):model.regression([(r['throughput_rps'],r['utilization']) for r in passive if r['block']==b],.5,True) for b in (1,2)}
    knots=[dict(rate=r,throughput=st.mean(x['throughput_rps'] for x in passive if x['low_rate']==r),
        utilization=st.mean(x['utilization'] for x in passive if x['low_rate']==r)) for r in (0,15,30,60,90,120)]
    if any(a['throughput']>=b['throughput'] or a['utilization']>=b['utilization'] for a,b in zip(knots,knots[1:])):raise ValueError('nonmonotone knots')
    maximum=knots[-1]['throughput'];u_max=knots[-1]['utilization']
    family=[dict(multiplier=k,capacity_rps=k*maximum,extension_slope=(.5-u_max)/(k*maximum-maximum),
        observed_knots=knots,scope='Identical pooled utilization-throughput knots only; does not establish observational equivalence for all request/CPU traces or actual kernel behavior.') for k in plan['root_multipliers']]
    cfgs=c.validation_configs();vectors={cfg['trial']:c.schedule(cfg) for cfg in cfgs}
    forecast=lambda f:{cfg['trial']:fifo(vectors[cfg['trial']],f['capacity_rps']) for cfg in cfgs} if f['status']=='available' else {}
    predictions={name:forecast(fit) for name,fit in fits.items()}
    block_predictions={b:forecast(fit) for b,fit in block_fits.items()}
    family_predictions=[forecast(dict(status='available',capacity_rps=x['capacity_rps'])) for x in family]
    c.save(OUT/'forecasts/report.json',dict(fits=fits,predictions=predictions,block_fits=block_fits,
        block_predictions=block_predictions,ambiguity_family=family,ambiguity_predictions=family_predictions,
        status='retrospective_known_validation_not_a_new_predictor'));c.seal(OUT/'forecasts')
    observed={r['trial']:r for r in saved['trial_accounting'] if r['role']=='validation'}
    results={}
    for name,fit in fits.items():
        scores=[]
        for cfg in cfgs:
            pred=predictions[name].get(cfg['trial']);obs=observed[cfg['trial']]
            scores.append(dict(trial=cfg['trial'],observed_miss_pct=obs['miss_pct'],predicted_miss_pct=pred,
                error_pp=None if pred is None else abs(pred-obs['miss_pct'])))
        answered=[x for x in scores if x['error_pp'] is not None]
        results[name]=dict(fit=fit,answered=len(answered),declared=16,refused=16-len(answered),
            deadline_mae_pp=st.mean(x['error_pp'] for x in answered) if answered else None,
            deadline_max_error_pp=max((x['error_pp'] for x in answered),default=None),
            passes=sum(x['error_pp']<=3 for x in answered),errors=scores)
    instability=[];ambiguity=[]
    for cfg in cfgs:
        name=cfg['trial'];obs=observed[name]['miss_pct'];lo=min(v[name] for v in block_predictions.values());hi=max(v[name] for v in block_predictions.values())
        instability.append(dict(trial=name,observed_miss_pct=obs,prediction_band_pp=[lo,hi],
            distance_outside_band_pp=max(lo-obs,obs-hi,0),scope='Two-block sensitivity envelope, not a confidence or prediction interval.'))
        lo=min(p[name] for p in family_predictions);hi=max(p[name] for p in family_predictions)
        ambiguity.append(dict(trial=name,conditional_model_forecast_range_pp=[lo,hi],width_pp=hi-lo,
            cannot_uniformly_meet_3pp_under_this_family=hi-lo>6))
    report=dict(status='screen_complete',date='2026-10-08',type='retrospective_baseline_and_aggregate_identifiability_screen',
        input_trials=len(passive),strict_low_trials=len(low),input_measurement_offers=sum(r['offers'] for r in passive),
        input_deadline_misses=0,input_throttled_periods=0,input_max_waiting_queue=1,
        baselines=results,block_fit_capacities={b:v['capacity_rps'] for b,v in block_fits.items()},
        block_sensitivity=instability,aggregate_ambiguity=ambiguity,ambiguity_root_capacities_rps=[x['capacity_rps'] for x in family],
        ambiguity_scope='Conditional illustration for pooled U/X features and a shared constant-rate FIFO model, not a CPU-quota-system theorem or proof against richer passive estimators.',
        prospective_status=False,novelty_established=False,new_collection=False,
        decision='generic_claim_rejected_specific_guard_gap_unestablished',
        next='Bounded comparison against faithful/adapted response and transient passive estimators using existing rich traces, then specify candidate guard and frozen risk/coverage evaluation before collecting new data.')
    c.save(OUT/'report.json',report)
    protected=read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    for name,h in protected.items():
        if sha(ROOT/name)!=h:raise ValueError('protected scientific evidence changed')
    for name,h in read(OUT/'design/preserved_documents_sha256.json').items():
        if sha(ROOT/name)!=h:raise ValueError('preserved document changed')
    c.save(OUT/'preservation.json',dict(status='pass',protected_scientific_files=len(protected),additional_documents=len(preserved)))
    print(json.dumps(dict(decision=report['decision'],baselines={k:{q:v[q] for q in ('answered','refused','deadline_mae_pp','deadline_max_error_pp','passes')} for k,v in results.items()},
        block_fit_capacities=report['block_fit_capacities'],conditional_root_capacities=report['ambiguity_root_capacities_rps'],
        cases_ambiguous_over_6pp=sum(x['width_pp']>6 for x in ambiguity)),indent=2))


if __name__=='__main__':main()
