#!/usr/bin/env python3
"""Independent numerical replay and preservation audit for passive assessment."""
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/runtime_io_passive_baseline_assessment/20261008'
SESSION=ROOT/'analysis/runtime_io_v28/generation-01'
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
import v23_model as q
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7):raise ValueError(f'{a} != {b}')

def merged(intervals):
    out=[]
    for a,b in sorted(intervals):
        if out and a<=out[-1][1]:out[-1][1]=max(out[-1][1],b)
        else:out.append([a,b])
    return out

def grid_integral(intervals,step,phase=0):
    # Integer count of left-grid points in each disjoint occupied interval.
    rr=merged(intervals);begin=rr[0][0]+phase;finish=rr[-1][1]
    if begin>=finish:return 0
    last=(finish-1-begin)//step;total=0
    for a,b in rr:
        lo=max(0,(a-begin+step-1)//step);hi=min(last,(b-1-begin)//step)
        if hi>=lo:total+=(hi-lo+1)*step
        if lo<=last<=hi:total-=max(0,begin+(last+1)*step-finish)
    return total

def main():
    c.verify_seal(OUT/'design');c.verify_seal(OUT/'forecasts')
    plan=read(OUT/'design/plan.json')
    if sha(ROOT/'analysis/assess_passive_baselines.py')!=plan['script_sha256']:raise ValueError('assessment script changed')
    protected=read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    additional=read(OUT/'design/preserved_sha256.json')
    for name,h in {**protected,**additional}.items():
        if sha(ROOT/name)!=h:raise ValueError('protected input changed')
    rows=read(OUT/'inventory.json');forecast=read(OUT/'forecasts/report.json');report=read(OUT/'report.json')
    refs=read(SESSION/'calibration_review/report.json')['trial_refs'];sensitivity=[]
    for r in rows:
        if r['role']=='idle':continue
        events=read(SESSION/refs[r['trial']]['path']/'server_metrics.json')['events']
        worker=sum(e['completion_ns']-e['worker_start_ns'] for e in events)
        if worker!=r['worker_wall_ns'] or worker!=r['worker_union_ns']:raise ValueError('worker integral')
        intervals=[(e['admission_ns'],e['completion_ns']) for e in events]
        area=sum(b-a for a,b in merged(intervals))
        if area!=r['queue_exposure_ns']:raise ValueError('queue integral')
        if grid_integral(intervals,10000000)!=r['grid_queue_exposure_ns']:raise ValueError('grid integration')
        diagnostics=[]
        for step in (1000000,2000000,5000000,10000000):
            for phase in (0,step//2):
                sampled=grid_integral(intervals,step,phase)
                diagnostics.append(dict(step_ns=step,origin_offset_ns=phase,exposure_ns=sampled,
                    relative_exposure_error_pct=100*(sampled/area-1)))
        sensitivity.append(dict(trial=r['trial'],exact_exposure_ns=area,grid_diagnostics=diagnostics,
            scope='Calibration-only quadrature diagnostic prompted by 10ms aliasing; no alternative tuned or scored forecast.'))
    points_checked=0
    for scope,rr in [('strict_low',[r for r in rows if r['role']=='steady' and r['low_rate']<=30]),
                     ('all_nonbacklogged',[r for r in rows if r['role']=='steady'])]:
        for feature,label in [('worker_wall_ns','worker_wall'),('queue_exposure_ns','queue_exposure_exact'),('grid_queue_exposure_ns','queue_exposure_10ms')]:
            total=sum(r[feature] for r in rr);n=sum(r['completed'] for r in rr)
            for quota,label2 in [(1,'unit_wall'),(.5,'quota_scaled')]:
                close(forecast['fits'][scope+'_'+label+'_'+label2]['capacity_rps'],quota*n*1e9/total);points_checked+=1
        with localcontext() as ctx:
            ctx.prec=55;points=[(Decimal(str(r['throughput_rps'])),Decimal(r['worker_wall_ns'])/Decimal(r['completed'])/Decimal(10**9)) for r in rr]
            n=Decimal(len(points));sx=sum(x for x,y in points);sy=sum(y for x,y in points)
            slope=(n*sum(x*y for x,y in points)-sx*sy)/(n*sum(x*x for x,y in points)-sx*sx)
            intercept=(sy-slope*sx)/n;f=forecast['fits'][scope+'_affine_wall_demand']
            close(float(intercept),f['coefficients'][0]);close(float(slope),f['coefficients'][1])
            root=(-intercept+(intercept*intercept+2*slope).sqrt())/(2*slope)
            if scope=='strict_low':
                if root<=2*max(x for x,y in points) or f['status']!='unavailable':raise ValueError('strict-low refusal')
            else:close(float(root),f['capacity_rps'])
            points_checked+=1
    # Independently derived high-precision OLS capacities from prior verifier.
    path=ROOT/'analysis/runtime_io_calibration_cost_assessment/20261008/verify_assessment.py'
    spec=importlib.util.spec_from_file_location('old_decimal_checker',path);check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
    for b in (1,2):
        train=[(r['throughput_rps'],r['utilization']) for r in rows if r['block']==b]
        candidates=check.fits(train)
        for label in ('linear','quadratic'):
            applicable=[v for v in candidates if label=='quadratic' or v[2].startswith('linear')]
            loss,root,kind=min(applicable)
            # Derive coefficients directly from independent moment equations.
            with localcontext() as ctx:
                ctx.prec=55;p=[(Decimal(str(x)),Decimal(str(y))) for x,y in train]
                s2=sum(x*x for x,y in p);s3=sum(x**3 for x,y in p);s4=sum(x**4 for x,y in p)
                y1=sum(x*y for x,y in p);y2=sum(x*x*y for x,y in p)
                intercept=Decimal(0)
                if kind=='linear_zero':d=y1/s2;e=Decimal(0)
                elif kind=='quadratic_zero':d=(y1*s4-y2*s3)/(s2*s4-s3*s3);e=(s2*y2-s3*y1)/(s2*s4-s3*s3)
                elif kind=='linear_intercept':
                    n=Decimal(len(p));sx=sum(x for x,y in p);sy=sum(y for x,y in p)
                    d=(n*y1-sx*sy)/(n*s2-sx*sx);intercept=(sy-d*sx)/n;e=Decimal(0)
                else:
                    sx=[sum((Decimal(1) if k==0 else x**k) for x,y in p) for k in range(5)]
                    sy=[sum((Decimal(1) if k==0 else x**k)*y for x,y in p) for k in range(3)]
                    matrix=[[sx[i+j] for j in range(3)] for i in range(3)];coeff=[]
                    for k in range(3):
                        replacement=[row[:] for row in matrix]
                        for i in range(3):replacement[i][k]=sy[i]
                        coeff.append(check.det(replacement)/check.det(matrix))
                    intercept,d,e=coeff
                held=[r for r in rows if r['block']!=b]
                residual=sum((intercept+d*Decimal(str(r['throughput_rps']))+e*Decimal(str(r['throughput_rps']))**2-Decimal(str(r['utilization'])))**2 for r in held)
                fold=next(f for f in forecast['cross_validation'][label]['folds'] if f['training_block']==b)
                close(float(residual),fold['utilization_sse'])
    winner=min(forecast['cross_validation'],key=lambda name:forecast['cross_validation'][name]['total_sse'])
    if winner!=report['selected_family'] or winner!='quadratic':raise ValueError('selection')
    close(check.fits([(r['throughput_rps'],r['utilization']) for r in rows])[0][1],forecast['fits']['calibration_block_cv_selector']['capacity_rps'])
    casechecks=0
    for name,f in forecast['fits'].items():
        if f['status']!='available':
            if report['method_results'][name]['answered']!=0:raise ValueError('unavailable scored')
            continue
        errors=[]
        for cfg in c.validation_configs():
            _,sim=q.simulate(c.schedule(cfg),f['capacity_rps'],cfg['burst_period_sec'])
            close(sim['miss_pct'],forecast['predictions'][name][cfg['trial']])
            er=next(e for e in report['method_results'][name]['errors'] if e['trial']==cfg['trial'])
            close(er['error_pp'],abs(sim['miss_pct']-er['observed_miss_pct']));errors.append(er['error_pp']);casechecks+=1
        close(st.mean(errors),report['method_results'][name]['mae_pp']);close(max(errors),report['method_results'][name]['max_error_pp'])
        if sum(x<=3 for x in errors)!=report['method_results'][name]['within_3pp']:raise ValueError('pass count')
    u=read(OUT/'uncertainty.json')
    for entry in u['split_conformal_count_check']:
        n=entry['n_independent_calibration_episodes'];rank=(95*(n+1)+99)//100
        if rank!=entry['order_statistic_rank'] or (rank<=n)!=entry['finite_if_rank_le_n']:raise ValueError('conformal count')
    result=dict(status='pass',assessment_source_hash_verified=True,protected_scientific_files=len(protected),additional_preserved_files=len(additional),
        raw_nonidle_event_integrals_checked=len(sensitivity),independent_demand_fit_checks=points_checked,
        independent_block_CV_checks=4,independent_forecast_case_checks=casechecks,
        split_conformal_rank_checks=len(u['split_conformal_count_check']),
        scientific_collection=False,published_full_algorithm_reproduction=False)
    c.save(OUT/'grid_sensitivity.json',sensitivity);c.save(OUT/'verification.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
