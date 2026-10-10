#!/usr/bin/env python3
"""Independent decimal moment equations and preservation/cost checks; read-only inputs."""
from decimal import Decimal, localcontext
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics as st

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SESSION=ROOT/'analysis/runtime_io_v28/generation-01'


def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-7):raise ValueError(f'{a} != {b}')


def det(a):
    return (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
        -a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
        +a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))


def fits(points):
    with localcontext() as ctx:
        ctx.prec=55
        p=[(Decimal(str(x)),Decimal(str(y))) for x,y in points]
        sx=[sum((Decimal(1) if k==0 else x**k) for x,y in p) for k in range(5)]
        sy=[sum((Decimal(1) if k==0 else x**k)*y for x,y in p) for k in range(3)]
        matrix=[[sx[i+j] for j in range(3)] for i in range(3)]
        determinant=det(matrix)
        full=[]
        for k in range(3):
            replaced=[row[:] for row in matrix]
            for i in range(3):replaced[i][k]=sy[i]
            full.append(det(replaced)/determinant)
        delta=sx[2]*sx[4]-sx[3]*sx[3]
        zero=[Decimal(0),(sy[1]*sx[4]-sy[2]*sx[3])/delta,(sx[2]*sy[2]-sx[3]*sy[1])/delta]
        denom=sx[0]*sx[2]-sx[1]*sx[1]
        slope=(sx[0]*sy[1]-sx[1]*sy[0])/denom
        linear=[(sy[0]-slope*sx[1])/sx[0],slope,Decimal(0)]
        linear_zero=[Decimal(0),sy[1]/sx[2],Decimal(0)]
        valid=[];maximum=max(x for x,y in p);quota=Decimal('.5')
        for label,coefs in [('quadratic_intercept',full),('quadratic_zero',zero),('linear_intercept',linear),('linear_zero',linear_zero)]:
            b,d,e=coefs
            if b<0 or b>=quota or d<=0:continue
            if abs(e*maximum**2)<Decimal('1e-12'):root=(quota-b)/d
            else:
                discriminant=d*d-4*e*(b-quota)
                if discriminant<0:continue
                roots=[(-d+discriminant.sqrt())/(2*e),(-d-discriminant.sqrt())/(2*e)]
                roots=[x for x in roots if x>0 and d+2*e*x>0]
                if len(roots)!=1:continue
                root=roots[0]
            if root>2*maximum or d+2*e*max(root,maximum)<=0:continue
            loss=sum((b+d*x+e*x*x-y)**2 for x,y in p)
            valid.append((float(loss),float(root),label))
        return sorted(valid)


def main():
    r=read(OUT/'report.json');plan=read(OUT/'design/plan.json');inventory=read(OUT/'inventory.json')
    original=read(ROOT/plan['original_report']);cal={x['trial']:x for x in original['trial_accounting'] if x['role']!='validation'}
    manifests=[read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json'),read(OUT/'design/preserved_documents_sha256.json')]
    checked=0
    for manifest in manifests:
        for name,expected in manifest.items():
            if sha(ROOT/name)!=expected:raise ValueError('changed protected input: '+name)
            checked+=1
    if sha(ROOT/'analysis/assess_calibration_cost.py')!=plan['script_sha256']:raise ValueError('declared source changed')
    forecasts=read(OUT/'subset_forecasts/predictions.json')
    if len(forecasts)!=len(plan['variants']) or len(r['variants'])!=len(plan['variants']):raise ValueError('missing declared variants')
    validation={x['trial']:x for x in original['trial_accounting'] if x['role']=='validation'}
    points_checked=0;costs_checked=0;errors_checked=0
    for v in r['variants']:
        spec=next(x for x in plan['variants'] if x['id']==v['id'])
        if v['trials']!=spec['trials']:raise ValueError('subset changed after declaration')
        if v['family']=='busy':
            close(v['fit']['capacity_rps'],st.mean(cal[t]['busy_capacity_rps'] for t in v['trials']))
        elif v['family']=='quadratic':
            points=[(cal[t]['throughput_rps'],cal[t]['utilization']) for t in v['trials']]
            candidates=fits(points)
            if not candidates and v['fit']['status']!='unavailable':raise ValueError('unavailable fit counted available')
            if candidates:
                close(candidates[0][1],v['fit']['capacity_rps'])
                close(candidates[0][0],v['fit']['residual_sum_squares'])
            points_checked+=1
        cost=v['costs'];values=[inventory['trials'][t] for t in v['trials']]
        for field in ('lifecycle_sec','measurement_offers','warmup_offers','measurement_cpu_sec','measurement_not_timely_500',
                      'warmup_not_timely_500','measurement_failures','warmup_failures','queued_request_seconds'):
            close(cost[field],sum(x[field] for x in values));costs_checked+=1
        close(cost['lifecycle_sum_plus_shared_initial_overhead_sec'],cost['lifecycle_sec']+inventory['initial_shared_collection_overhead_sec'])
        saved=next(x for x in forecasts if x['id']==v['id'])
        if v['fit']!=saved['fit'] or v['predictions']!=saved['predictions']:raise ValueError('forecast changed during scoring')
        if set(e['trial'] for e in v['errors'])!=set(validation):raise ValueError('missing retained cases')
        for e in v['errors']:
            predicted=v['predictions'].get(e['trial'])
            if predicted is None:
                if e['deadline_error_pp'] is not None:raise ValueError('refused fit got numeric score')
                continue
            close(e['deadline_error_pp'],abs(predicted['miss_pct']-validation[e['trial']]['miss_pct']))
            errors_checked+=1
        metrics=v['metrics'];errors=[e['deadline_error_pp'] for e in v['errors'] if e['deadline_error_pp'] is not None]
        if errors:
            close(metrics['deadline_mae_pp'],st.mean(errors));close(metrics['deadline_max_error_pp'],max(errors))
        if metrics['deadline_passes']!=sum(x<=3 for x in errors):raise ValueError('accuracy count differs')
    # All original trials, including inventory component sums, reconstruct from recorded clocks.
    for name,v in inventory['trials'].items():
        d=ROOT/v['path'];start=read(d/'started.json');finish=read(d/'complete.json');obs=read(d/'observations.json')
        elapsed=(finish['finished_monotonic_ns']-start['monotonic_ns'])/1e9
        close(v['lifecycle_sec'],elapsed)
        close(v['lifecycle_sec'],v['settling_sec']+v['post_settle_to_measurement_start_sec']+v['accounted_measurement_wall_sec']+v['post_measurement_accounting_sec'])
        if elapsed<0 or not v['technical_cleanup_pass']:raise ValueError('invalid recorded lifecycle')
        for filename,prefix in [('loadgen.json','measurement'),('warmup.json','warmup')]:
            if v['role']=='idle':continue
            client=read(d/filename)
            timely=sum(q['StatusCode']==200 and not q['Error'] and q['EndToEndLatencyNs']<=500000000 for q in client['requests'])
            close(v[prefix+'_not_timely_500'],client['total_scheduled']-timely)
    # Declared offered-rate A/D choices checked directly from covariance minors.
    for n in (3,4):
        scores=[]
        for rates in itertools.combinations(plan['candidate_rates'],n):
            features=[[1,r/120,(r/120)**2] for r in rates]
            matrix=[[sum(x[i]*x[j] for x in features) for j in range(3)] for i in range(3)]
            determinant=det(matrix)
            trace=sum(matrix[(i+1)%3][(i+1)%3]*matrix[(i+2)%3][(i+2)%3]-matrix[(i+1)%3][(i+2)%3]*matrix[(i+2)%3][(i+1)%3] for i in range(3))/determinant
            scores.append((rates,determinant,trace))
        d=min(scores,key=lambda s:(-round(s[1],12),s[0]))[0]
        a=min(scores,key=lambda s:(round(s[2],10),s[0]))[0]
        if list(d)!=plan['designs']['d_opt'+str(n)] or list(a)!=plan['designs']['a_opt'+str(n)]:raise ValueError('design choice differs')
    single=[v for v in r['variants'] if v['family']=='busy' and len(v['trials'])==1]
    if len(single)!=4 or not all(v['metrics']['deadline_passes']==16 for v in single):raise ValueError('stop premise fails')
    if r['decision']!='stop_custom_calibration_cost_route':raise ValueError('wrong verdict')
    result=dict(status='pass',protected_hash_checks=checked,declared_variants=len(r['variants']),
        independent_decimal_quadratic_checks=points_checked,independent_cost_sum_checks=costs_checked,
        scored_case_error_checks=errors_checked,raw_clock_lifecycles_checked=len(inventory['trials']),
        information_design_selection_checked=True,original_full_budget_replay_checks=r['checks'],
        partial_window_fitting=False,scientific_collection=False,novelty_established=False,
        checks='Independent high-precision Cramer/moment equations, covariance minors, raw lifecycle clocks/lateness, exhaustive declared variant coverage and original protected hashes.')
    target=OUT/'verification.json'
    if target.exists():
        if read(target)!=result:raise ValueError('new verification differs; preserve existing record')
    else:
        target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
