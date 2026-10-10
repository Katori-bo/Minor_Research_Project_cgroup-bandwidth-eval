#!/usr/bin/env python3
"""Offline retrospective applicability assessment; never collects measurements."""
import bisect
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import v28_common as c
import v28_model as model
from screen_passive_forecasting import fifo

OUT = ROOT/'analysis/runtime_io_passive_baseline_assessment/20261008'
SESSION = c.PARENT/'generation-01'
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, obj): c.save(p, obj)

def union_length(intervals):
    total = 0; end = None
    for a,b in sorted(intervals):
        if b < a: raise ValueError('negative interval')
        total += b-a if end is None or a >= end else max(0,b-end)
        end = b if end is None else max(end,b)
    return total

def response_fit(rows):
    # Ordinary affine load-dependent elapsed demand, no validation inputs.
    points = [(r['throughput_rps'], r['mean_worker_wall_sec']) for r in rows]
    a,b = model.ols(points, 1)
    max_x = max(x for x,y in points)
    candidates=[]
    if a > 0:
        if abs(b) < 1e-15: roots=[.5/a]
        elif a*a+2*b >= 0:
            roots=[(-a+math.sqrt(a*a+2*b))/(2*b),(-a-math.sqrt(a*a+2*b))/(2*b)]
        else: roots=[]
        for x in roots:
            if 0 < x <= 2*max_x and a+2*b*max(x,max_x)>0 and a+b*max(x,max_x)>0:
                candidates.append(x)
    if len(candidates)!=1:
        return dict(status='unavailable',reason='no unique admissible demand/capacity root',coefficients=[a,b])
    return dict(status='available',capacity_rps=candidates[0],coefficients=[a,b],
        residual_sum_squares=model.loss(points,[a,b]),extrapolation_ratio=candidates[0]/max_x,
        classification='ordinary load-dependent wall-demand adaptation, not a reproduced published algorithm',
        assumptions='elapsed worker time approximates CPU demand; affine demand transfers beyond observed loads; quota budget .5 becomes available service; shared FIFO approximation')

def main():
    if OUT.exists(): raise ValueError('preserve existing assessment')
    prior=ROOT/'analysis/runtime_io_passive_novelty_screen/20261008'
    c.verify_seal(prior)
    latest=read(SESSION/'latest_analysis.json'); original=SESSION/latest['path']; c.verify_seal(original)
    if sha(original/'seal.json')!=latest['seal']: raise ValueError('source reference')
    source=read(original/'report.json'); cal=read(SESSION/'calibration_review/report.json')
    protected=read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    preserved=read(prior/'design/preserved_documents_sha256.json')
    preserved.update({str(p.relative_to(ROOT)):sha(p) for p in prior.rglob('*') if p.is_file()})
    for name,h in {**protected,**preserved}.items():
        if sha(ROOT/name)!=h: raise ValueError('protected input changed: '+name)
    plan=dict(date='2026-10-08',status='retrospective_known_outcomes',script_sha256=sha(__file__),
        predictor_inputs='Only idle/steady calibration observations and their request events. Mixed/busy and validation measurements excluded.',
        methods=['single-worker BL/RPS/MLPS wall special case, strict-low and all nonbacklogged',
          'open single-queue event/exposure adaptation of MHE, exact and 10ms grid, strict-low and all nonbacklogged',
          'affine worker-wall demand versus throughput, strict-low and all nonbacklogged',
          'two-block CPU cross-validation selector between existing linear/quadratic fits'],
        quota_mappings=['unit-availability wall service (no quota correction)','conditional quota-scaled wall service (.5)'],
        response_root_rule='positive demand and monotonic required-CPU curve through root; unique root <=2x maximum input throughput',
        moving_horizon_step_ns=10000000,selection_loss='other-block utilization SSE; fit selected family on all twelve calibration rows',
        comparison_error_pp=3,uncertainty='ordinary block-maximum split-conformal residual calibration; 95% coverage sample-count feasibility only; no claimed guarantee',
        collection=False,custom_guard=False,novelty_established=False)
    save(OUT/'design/plan.json',plan);save(OUT/'design/preserved_sha256.json',preserved);c.seal(OUT/'design')
    rows=[]
    for row in source['trial_accounting']:
        if row['role'] not in ('idle','steady'): continue
        ref=cal['trial_refs'][row['trial']];d=SESSION/ref['path'];c.verify_seal(d)
        if sha(d/'seal.json')!=ref['seal']: raise ValueError('trial reference')
        server=read(d/'server_metrics.json');jobs=server['events'];v=dict(row)
        if jobs:
            if len(jobs)!=server['completed']: raise ValueError('event count')
            worker=[(j['worker_start_ns'],j['completion_ns']) for j in jobs]
            if any(b>a2 for (a,b),(a2,b2) in zip(sorted(worker),sorted(worker)[1:])):
                raise ValueError('single-worker assumption violated')
            if any(j['processing_ns']!=j['completion_ns']-j['worker_start_ns'] for j in jobs): raise ValueError('wall time inconsistency')
            v['worker_wall_ns']=sum(j['processing_ns'] for j in jobs)
            v['mean_worker_wall_sec']=v['worker_wall_ns']/len(jobs)/1e9
            v['worker_union_ns']=union_length(worker)
            # Open queue starts empty before first admission and ends drained.
            # Integrate min(number admitted but unfinished,1), including dispatch gaps.
            intervals=[(j['admission_ns'],j['completion_ns']) for j in jobs]
            start=min(a for a,b in intervals);end=max(b for a,b in intervals)
            v['queue_exposure_ns']=union_length(intervals)
            arrivals=sorted(a for a,b in intervals);departures=sorted(b for a,b in intervals)
            step=plan['moving_horizon_step_ns'];exposure=0
            for t in range(start,end,step):
                n=bisect.bisect_right(arrivals,t)-bisect.bisect_right(departures,t)
                if n<0:raise ValueError('negative occupancy')
                exposure+=min(n,1)*min(step,end-t)
            v['grid_queue_exposure_ns']=exposure
            v['event_window_sec']=(end-start)/1e9
            v['source_events_sha256']=sha(d/'server_metrics.json')
        rows.append(v)
    save(OUT/'inventory.json',rows)
    fits={}
    for scope,rr in [('strict_low',[r for r in rows if r['role']=='steady' and r['low_rate']<=30]),
                     ('all_nonbacklogged',[r for r in rows if r['role']=='steady'])]:
        jobs=sum(r['completed'] for r in rr)
        for feature,label in [('worker_wall_ns','worker_wall'),('queue_exposure_ns','queue_exposure_exact'),
                               ('grid_queue_exposure_ns','queue_exposure_10ms')]:
            sec=sum(r[feature] for r in rr)/1e9
            for quota,label2 in [(1.,'unit_wall'),(.5,'quota_scaled')]:
                fits[scope+'_'+label+'_'+label2]=dict(status='available',capacity_rps=quota*jobs/sec,
                    jobs=jobs,exposure_sec=sec,classification='wall-service special case/adaptation',
                    quota_mapping=label2,assumption='Unit wall availability transfers to future bursts' if quota==1 else 'Wall demand approximates CPU and quota-scaled service transfers to future bursts')
        fits[scope+'_affine_wall_demand']=response_fit(rr)
    all_points=[(r['throughput_rps'],r['utilization']) for r in rows]
    cv={}
    for label,quad in [('linear',False),('quadratic',True)]:
        folds=[]
        for b in (1,2):
            train=[(r['throughput_rps'],r['utilization']) for r in rows if r['block']==b]
            f=model.regression(train,.5,quad)
            if f['status']!='available': raise ValueError('CV fit unavailable')
            test=[(r['throughput_rps'],r['utilization']) for r in rows if r['block']!=b]
            coeff=[f['intercept'],f['demand_sec'],f.get('quadratic_sec2',0)]
            folds.append(dict(training_block=b,heldout_block=3-b,utilization_sse=model.loss(test,coeff)))
        cv[label]=dict(folds=folds,total_sse=sum(f['utilization_sse'] for f in folds))
    chosen=min(cv,key=lambda label:cv[label]['total_sse'])
    fits['calibration_block_cv_selector']=dict(model.regression(all_points,.5,chosen=='quadratic'),
        selected_family=chosen,classification='ordinary blocked cross-validation adaptation; not SARDE implementation')
    # Freeze predictor outputs before retrospective scoring.
    cfgs=c.validation_configs();vectors={cfg['trial']:c.schedule(cfg) for cfg in cfgs}
    predictions={k:{cfg['trial']:fifo(vectors[cfg['trial']],f['capacity_rps']) for cfg in cfgs}
        if f['status']=='available' else {} for k,f in fits.items()}
    save(OUT/'forecasts/report.json',dict(fits=fits,predictions=predictions,cross_validation=cv));c.seal(OUT/'forecasts')
    observed={r['trial']:r for r in source['trial_accounting'] if r['role']=='validation'}
    scores={}
    for name,f in fits.items():
        errors=[dict(trial=cfg['trial'],block=observed[cfg['trial']]['block'],
            observed_miss_pct=observed[cfg['trial']]['miss_pct'],predicted_miss_pct=predictions[name][cfg['trial']],
            error_pp=abs(predictions[name][cfg['trial']]-observed[cfg['trial']]['miss_pct']))
            for cfg in cfgs] if f['status']=='available' else []
        scores[name]=dict(fit=f,answered=len(errors),refused=16-len(errors),
            mae_pp=st.mean(e['error_pp'] for e in errors) if errors else None,
            max_error_pp=max((e['error_pp'] for e in errors),default=None),
            within_3pp=sum(e['error_pp']<=3 for e in errors),
            nonzero_within_3pp=sum(e['error_pp']<=3 and e['observed_miss_pct']>0 for e in errors),errors=errors)
    prior_scores=read(prior/'report.json')['baselines']
    residuals={}
    for name,ss in [('existing_quadratic',prior_scores['nonbacklogged_quadratic']),*scores.items()]:
        errors=ss['errors']
        if not errors: continue
        residuals[name]=[max(e['error_pp'] for e in errors if (e.get('block') or observed[e['trial']]['block'])==b) for b in (1,2,3,4)]
    conformal=[]
    for n in (1,2,3,4,16,19,59):
        rank=math.ceil((n+1)*.95-1e-12)
        conformal.append(dict(n_independent_calibration_episodes=n,coverage=.95,order_statistic_rank=rank,
            finite_if_rank_le_n=rank<=n,scope='count feasibility only; bounded [0,100] target admits full-range vacuous interval even when rank exceeds n'))
    contract=dict(status='candidate_contract_for_future_design_not_validated_guard',
        candidate='At matched allowed history and cost, predict offered-cohort burst miss fraction or refuse; justify useful accepted predictions when history does or does not constrain loaded service.',
        cold_start='No historical burst/overload labels or offline profiles. Any guarantee requires independently justified model/service bounds; low-load data alone do not validate extrapolation.',
        trained_deployment='Historical independent paired histories/future labels allowed and charged. Calibration and fresh test episodes must be separate from model/guard development.',
        output='Point miss percent plus interval/assumptions, or explicit insufficient-evidence reason. Known future schedule, workload, quota/period, affinity and initial queue are inputs.',
        provisional_success=dict(absolute_error_pp=3,minimum_total_answer_fraction=.5,minimum_nonzero_answer_fraction=.5,
            accepted_bad_prediction_probability_upper_bound=.05,confidence_for_bad_rate=.95,
            note='Proposed research criterion, not a result or user-specified production SLA. Marginal conformal coverage alone does not certify selected-case risk.'),
        comparison=['Existing nonlinear demand regression','response/event/exposure adaptations with explicit quota mapping',
            'ordinary blocked estimator selection','independent residual conformal intervals plus separately calibrated selection/risk control',
            'natural busy-window throughput if naturally present; charge any historical loaded profiles'],
        distinct_capability_required='Higher useful answer coverage at the same justified accepted-error risk and observation budget, or reduced budget at matched risk/coverage; include nonzero misses and unsupported histories.',
        missing_evidence='Independent paired permissible histories and future outcomes varying history support/resource state. Current two calibration and four validation blocks do not establish guard skill or state transfer.',
        instrumentation='Per-worker CPU or quota phase only if a specific predeclared discriminator needs it; observer neutrality must first be established.',
        collection=False)
    save(OUT/'capability_contract.json',contract)
    save(OUT/'uncertainty.json',dict(block_max_residuals_pp=residuals,split_conformal_count_check=conformal,
        interpretation='Residuals are descriptive known-outcome quantities, not fitted or tested new guards. Blocks not proven exchangeable. No accepted-case risk or prospective interval claim.'))
    report=dict(status='complete',date='2026-10-08',retrospective=True,new_collection=False,
        method_results=scores,cross_validation=cv,selected_family=chosen,
        verdict='stop_custom_method_and_new_collection_at_present_novelty_gate',
        reason='Passive inference and uncertainty/abstention are established. Tested adaptations do not establish a distinct reliable quota forecast capability. Published quota-unaware estimators have not been faithfully validated for this kernel system. A guard with useful coverage has no independent development/calibration/test evidence.',
        novelty_established=False,published_algorithm_defeat_claim=False)
    save(OUT/'report.json',report)
    for name,h in {**protected,**preserved}.items():
        if sha(ROOT/name)!=h:raise ValueError('protected evidence changed: '+name)
    save(OUT/'preservation.json',dict(status='pass',protected_files=len(protected),additional_files=len(preserved)))
    print(json.dumps(dict(verdict=report['verdict'],selected=chosen,
        results={k:{v:r[v] for v in ('answered','mae_pp','max_error_pp','within_3pp','nonzero_within_3pp')} for k,r in scores.items()}),indent=2))

if __name__=='__main__': main()
