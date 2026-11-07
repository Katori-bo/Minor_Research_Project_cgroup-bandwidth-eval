#!/usr/bin/env python3
"""Offline prospective planning scenarios; never qualify or collect a workload."""
import argparse
import functools
import hashlib
import json
import math
from pathlib import Path
import statistics as st

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'analysis/runtime_io_nginx_worker_wait_qualification/generation-01'
TARGET_JOINT_PASS = .80  # Planning illustration, not an acceptance rule.
FAIL_PER_GATE = (1 - TARGET_JOINT_PASS) / 6


def beta_fraction(a, b, x):
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c = 1.; d = 1 - qab * x / qap
    d = 1 / max(d, tiny); h = d
    for m in range(1, 10001):
        for aa in (m * (b - m) * x / ((qam + 2*m) * (a + 2*m)),
                   -(a + m) * (qab + m) * x / ((a + 2*m) * (qap + 2*m))):
            d = 1 + aa*d; c = 1 + aa/c
            if abs(d) < tiny: d = tiny
            if abs(c) < tiny: c = tiny
            d = 1/d; delta = d*c; h *= delta
        if abs(delta - 1) < 1e-13: return h
    raise ArithmeticError('Incomplete beta did not converge')


def beta_cdf(a, b, x):
    if x <= 0: return 0.
    if x >= 1: return 1.
    factor = math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)
                      +a*math.log(x)+b*math.log1p(-x))
    if x < (a+1)/(a+b+2): return factor*beta_fraction(a,b,x)/a
    return 1-factor*beta_fraction(b,a,1-x)/b


def t_cdf(x, df):
    if x == 0: return .5
    tail = .5 * beta_cdf(df/2, .5, df/(df+x*x))
    return 1-tail if x > 0 else tail


def gamma_cdf(a, x):
    if x <= 0: return 0.
    factor = math.exp(a*math.log(x)-x-math.lgamma(a))
    if x < a+1:
        term = total = 1/a
        for k in range(1,10001):
            term *= x/(a+k); total += term
            if abs(term) < abs(total)*1e-13: return factor*total
    else:
        tiny=1e-300; b=x+1-a; c=1/tiny; d=1/b; h=d
        for k in range(1,10001):
            an=-k*(k-a); b+=2; d=an*d+b; c=b+an/c
            if abs(d)<tiny: d=tiny
            if abs(c)<tiny: c=tiny
            d=1/d; delta=d*c; h*=delta
            if abs(delta-1)<1e-13: return 1-factor*h
    raise ArithmeticError('Incomplete gamma did not converge')


def quantile(cdf, p):
    lo,hi=0.,1.
    while cdf(hi)<p: hi*=2
    for _ in range(70):
        mid=(lo+hi)/2
        if cdf(mid)<p: lo=mid
        else: hi=mid
    return hi


@functools.lru_cache(None)
def t_critical(n):
    # Round up, so numerical rounding cannot make the prospective CI narrower.
    return math.ceil(quantile(lambda x:t_cdf(x,n-1),.9975)*1e6)/1e6


@functools.lru_cache(None)
def sd_upper_factor(n):
    v=quantile(lambda x:gamma_cdf((n-1)/2,x/2),1-FAIL_PER_GATE/2)
    return math.sqrt(v/(n-1))


def required_n(mean, sigma, margin, powered=False):
    if abs(mean)>=margin: return None
    z=st.NormalDist().inv_cdf(1-FAIL_PER_GATE/4)
    def contains(n):
        factor=t_critical(n)
        if powered: factor=factor*sd_upper_factor(n)+z
        return abs(mean)+factor*sigma/math.sqrt(n)<=margin
    lo,hi=5,6
    while not contains(hi):
        lo,hi=hi,hi*2
        if hi>100000: raise ValueError('Planning exceeds supported search range')
    while hi-lo>1:
        mid=(lo+hi)//2
        if contains(mid): hi=mid
        else: lo=mid
    return hi


def read(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze():
    comp=read(BASE/'qualification/comparison.json')
    overhead=read(BASE/'qualification/overhead/summary.json')
    rows=overhead['rows']; metrics={}; costs={}
    # Charge the whole observed group, including gaps/verification between services.
    cohort_seconds={}
    for row in rows:
        case=BASE/'qualification/overhead'/f"cohort-{row['config']['index']}"
        cohort_seconds[row['config']['index']]=(read(case/'fixed-final.json')['monotonic_ns']-
            read(case/'trial-start.json')['monotonic_ns'])/1e9
    overhead_per_pair=(overhead['elapsed_sec']-sum(cohort_seconds.values()))/12
    assert overhead_per_pair>=0
    for rate in ('4','8'):
        cells=[r for r in rows if r['config']['rate_rps']==int(rate)]
        costs[rate]=2*st.mean(cohort_seconds[r['config']['index']] for r in cells)+overhead_per_pair
        metrics[rate]={}
        for metric,item in comp['rates'][rate]['tests'].items():
            values=item['differences']; sigma=st.stdev(values)
            assert len(values)==6 and math.isclose(st.mean(values),item['mean'],abs_tol=1e-8)
            sd95=[math.sqrt(5/quantile(lambda x:gamma_cdf(2.5,x/2),p)) for p in (.975,.025)]
            metrics[rate][metric]=dict(mean=item['mean'],sd=sigma,margin=item['margin'],
                pilot_sd95_factor=sd95,pilot_sd95=[sigma*x for x in sd95],differences=values)
    boundary_seconds=read(BASE/'qualification/boundary/summary.json')['elapsed_sec']
    scenarios=[]
    for mean_case in ('zero_effect','pilot_mean'):
        for scale in (.75,1.,1.5,2.):
            for mode in ('width_only','conservative_joint80'):
                needs={rate:{metric:required_n(0 if mean_case=='zero_effect' else x['mean'],
                    x['sd']*scale,x['margin'],mode!='width_only') for metric,x in panel.items()}
                    for rate,panel in metrics.items()}
                n={rate:max(panel.values()) for rate,panel in needs.items()}
                balanced=max(n.values())
                scenarios.append(dict(mean_case=mean_case,sd_scale=scale,mode=mode,
                    minimum_per_metric=needs,pairs_per_rate=n,
                    bottleneck={rate:max(panel,key=panel.get) for rate,panel in needs.items()},
                    balanced_pairs_each_rate=balanced,
                    balanced_offers=1300*balanced+90,
                    balanced_projected_hours=(balanced*sum(costs.values())+boundary_seconds)/3600,
                    unequal_offers=650*sum(n.values())+90,
                    unequal_projected_hours=(sum(n[r]*costs[r] for r in n)+boundary_seconds)/3600))
    grid=[]
    for n in (6,9,12,24,48,96,192,384):
        grid.append(dict(pairs_each_rate=n,offers=1300*n+90,
            projected_hours=(n*sum(costs.values())+boundary_seconds)/3600,
            projections={rate:{metric:dict(halfwidth=t_critical(n)*x['sd']/math.sqrt(n),
                zero_center_contains=t_critical(n)*x['sd']/math.sqrt(n)<=x['margin'],
                pilot_center_contains=abs(x['mean'])+t_critical(n)*x['sd']/math.sqrt(n)<=x['margin'])
                for metric,x in panel.items()} for rate,panel in metrics.items()}))
    return dict(schema='worker-wait-precision-cost-development-v1',
        status='hold_unchanged_observer_collection',collection_performed=False,
        original_qualification=comp['status'],original_qualified=comp['qualified'],
        target_joint_pass_probability=TARGET_JOINT_PASS,
        pass_probability_scope='Six interval-containment gates only; excludes technical failures, endpoint informativeness, boundary checks and phase/lifetime limits. No overall hardware qualification probability is calculated.',
        metrics=metrics,pair_seconds=costs,boundary_seconds=boundary_seconds,
        scenarios=scenarios,budget_grid=grid,
        conditional_assumptions='Fresh independent identically normal paired differences within each metric; stated mean/SD scenarios, fixed 99.5% prospective intervals, all six gates. No confidence that pilot moments or wall-time scale transfer; no independence across gates required for the union bound.',
        powered_bound='Each gate: failure <=1/30, split equally between two-sided mean deviation and upper sample-SD tail. Require abs(delta)+(z_(1-epsilon/4)+t_(.9975,n-1)*sqrt(chi2_(1-epsilon/2,n-1)/(n-1)))*sigma/sqrt(n)<=margin. Six-gate union bound gives >=.80 conditional pass probability. Sufficient, not minimal or an actual power estimate.',
        width_only='Substitute scenario SD for future sample SD and scenario mean for future sample mean. This is interval geometry, not expected width, power or qualification.',
        cost_scope='Fresh boundary probes + fresh overhead services; includes warmup/target offers, observed full service lifetimes, gaps and verification. Excludes preflight, observer inventory, new source preparation, rest between sessions, predictive discovery and independent confirmation. Hours are projections, not certified bounds; unequal rate allocation is an illustration, not a selected protocol.',
        predictive_usefulness_tested=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--output',type=Path)
    mode.add_argument('--verify',type=Path)
    args=parser.parse_args(); result=analyze()
    if args.verify:
        manifest=read(args.verify.parent/'inputs_sha256.json')
        for name,digest in manifest.items():
            if sha(ROOT/name)!=digest: raise ValueError('Planning input changed: '+name)
        seal_path=args.verify.parent/'assessment_seal.json'
        if seal_path.exists():
            for name,digest in read(seal_path)['files_sha256'].items():
                if sha(args.verify.parent/name)!=digest:
                    raise ValueError('Planning artifact changed: '+name)
        if result!=read(args.verify): raise ValueError('Saved offline planning does not replay')
        print('Offline precision/cost inputs and arithmetic verify; no collection or qualification performed.')
    elif args.output:
        with args.output.open('x') as f: json.dump(result,f,indent=2); f.write('\n')
    else: print(json.dumps(result,indent=2))


if __name__=='__main__': main()
