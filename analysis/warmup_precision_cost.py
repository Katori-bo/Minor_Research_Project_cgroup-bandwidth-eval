#!/usr/bin/env python3
"""Exact median interval geometry and conditional IID CDF/cost planning; offline."""
import argparse
from fractions import Fraction
from functools import lru_cache
import json
import math
from pathlib import Path
import statistics as st
import screen_deadline_sensitivity as s
import screen_forecast_reliability as e

ROOT=s.ROOT
OUT=ROOT/'analysis/runtime_io_warmup_precision_cost/20261011'
SOURCES=('analysis/warmup_precision_cost.py','analysis/test_warmup_precision_cost.py',
 'docs/runtime_io_warmup_precision_cost_protocol_20261011.md',
 'analysis/screen_deadline_sensitivity.py','analysis/screen_forecast_reliability.py',
 'analysis/screen_deadline_scope.py','diagnostic/nginx_power_confirmation_model.py',
 'diagnostic/nginx_prediction_model.py')
GRID=(25,50,100,149,200,400,597,738,800,1600)


@lru_cache(None)
def median_ranks(n,alpha=Fraction(1,20)):
    e.require(type(n) is int and n>0 and 0<alpha<1,'Invalid rank inputs')
    alpha=Fraction(alpha);den=1<<n;comb=1;total=0;k=0
    for i in range(n//2+1):
        if i:comb=comb*(n-i+1)//i
        candidate=total+comb
        if 2*candidate*alpha.denominator>alpha.numerator*den:break
        total=candidate;k=i+1
    return dict(n=n,k=k,upper_rank=n-k+1 if k else None,
        continuous_iid_coverage=float(1-Fraction(2*total,den)) if k else None)


def median_interval(values,alpha=Fraction(1,20)):
    ranks=median_ranks(len(values),alpha)
    if any(x is None for x in values) or not ranks['k']:
        return dict(**ranks,available=False,lower_ns=None,upper_ns=None,width_us=None)
    v=sorted(values);lo=v[ranks['k']-1];hi=v[ranks['upper_rank']-1]
    return dict(**ranks,available=True,lower_ns=lo,upper_ns=hi,width_us=(hi-lo)/1000)


def precision(reference,warmup,panel):
    e.require(len(warmup)==25 and len(panel)==5,'Original warmup/panel required')
    warm95=median_interval(warmup);w=median_interval(warmup,Fraction(1,40))
    r=median_interval(reference,Fraction(1,40))
    if not w['available'] or not r['available']:
        return dict(warmup95=warm95,warmup97_5=w,reference97_5=r,
                    difference_available=False,median_difference_interval_ns=None,
                    mapped_probability_range_pp=None,largest_mapped_width_pp=None)
    lo=w['lower_ns']-r['upper_ns'];hi=w['upper_ns']-r['lower_ns']
    ranges=[]
    for point in panel:
        d=point['deadline_ns'];e.require(type(d) is int and d>=0,'Finite panel required')
        lower=float(100*s.miss(reference,d-lo));upper=float(100*s.miss(reference,d-hi))
        e.require(lower<=upper,'Median transform direction reversed')
        ranges.append(dict(quantile=point['quantile'],lower_pct=lower,upper_pct=upper,width_pp=upper-lower))
    return dict(warmup95=warm95,warmup97_5=w,reference97_5=r,difference_available=True,
        median_difference_interval_ns=[lo,hi],difference_width_us=(hi-lo)/1000,
        difference_contains_zero=lo<=0<=hi,mapped_probability_range_pp=ranges,
        largest_mapped_width_pp=max(x['width_pp'] for x in ranges),
        future_forecast_confidence_interval=False,reference_cdf_uncertainty_propagated=False)


def location_radius(reference,panel):
    e.require(reference and all(x is not None for x in reference),'Finite reference required')
    deadlines=[p['deadline_ns'] for p in panel]
    base=[s.miss(reference,d) for d in deadlines]
    def safe(offset,direction):
        return all(abs(s.miss(reference,d+direction*offset)-p)<=Fraction(1,20)
                   for d,p in zip(deadlines,base))
    limits=[]
    for direction in (-1,1):
        lo=0;hi=max(max(deadlines),max(reference))+1
        if safe(hi,direction):
            limits.append(None);continue
        while hi-lo>1:
            mid=(lo+hi)//2
            if safe(mid,direction):lo=mid
            else:hi=mid
        limits.append(lo)
    return dict(earlier_cutoff_radius_ns=limits[0],later_cutoff_radius_ns=limits[1],
                symmetric_radius_ns=min(x for x in limits if x is not None) if any(x is not None for x in limits) else None,
                unbounded_sides=[direction for direction,limit in zip(('earlier','later'),limits) if limit is None],
                future_shift_bound=False)


def dkw(n,alpha=.05):
    e.require(n>0 and 0<alpha<1,'Invalid IID bound inputs')
    return math.sqrt(math.log(2/alpha)/(2*n))


def sufficient_n(epsilon=.05,alpha=.05):
    e.require(0<epsilon<1 and 0<alpha<1,'Invalid required precision')
    return math.ceil(math.log(2/alpha)/(2*epsilon**2))


def pair_n(ncal):
    floor=dkw(ncal,.025);remaining=.05-floor
    return dict(calibration_n=ncal,asymptotic_halfwidth_floor_pp=100*floor,
                sufficient_warmup_n=sufficient_n(remaining,.025) if remaining>0 else None,
                equal_alpha_allocation=True,necessary_sample_size=False)


def nominal_service(nwarm,rate):
    total=Fraction(nwarm-1,rate)+Fraction(299,rate)+8
    return dict(optimistic_seconds=float(total),passes_necessary_120sec=total<120,
                startup_drain_cleanup_included=False)


def maximum_warmup(rate):
    n=1
    while nominal_service(n+1,rate)['passes_necessary_120sec']:n+=1
    return n


def cost(nwarm,elapsed):
    extra=(nwarm-25)*24
    sec=float((nwarm-25)*(Fraction(12,4)+Fraction(12,8)))
    return dict(warmup_offers_per_target=nwarm,extra_offers=extra,
        scientific_offers=9500+extra,including_fixed_qualification_offers=10530+extra,
        extra_nominal_sec=sec,conditional_projected_science_minutes=(elapsed+sec)/60,
        within_45min_total_projection=elapsed+sec<=2700,
        services={str(r):nominal_service(nwarm,r) for r in (4,8)},
        selected_protocol=False,qualification_preflight_extra_overhead_excluded=True)


def summarize(rows):
    available=[r['precision'] for r in rows if r['precision']['difference_available']]
    widths=[x['warmup95']['width_us'] for x in available]
    mapped=[x['largest_mapped_width_pp'] for x in available]
    return dict(cohorts=len(rows),available=len(available),unavailable=len(rows)-len(available),
        warmup95_width_us=dict(minimum=min(widths),median=st.median(widths),maximum=max(widths)) if widths else None,
        mapped_width_pp=dict(minimum=min(mapped),median=st.median(mapped),maximum=max(mapped)) if mapped else None,
        mapped_width_above_5pp=sum(x>5+1e-10 for x in mapped),
        difference_intervals_containing_zero=sum(x['difference_contains_zero'] for x in available))


def analyze():
    e.INPUTS.clear();design=e.read(OUT/'design.json')
    e.require(design['warmup_grid']==list(GRID) and design['cohorts']==78,'Planning specification differs')
    for name,digest in e.read(OUT/'design_sha256.json').items():
        e.require(e.sha(ROOT/name)==digest,'Planning source/design changed: '+name);e.INPUTS[name]=digest
    # Reuse the sealed screen's calibration/warmup-only loader. No measurement
    # targets or historical error labels are needed for this precision audit.
    specs=s.load_specs();rows=[];groups={}
    for x in specs:
        key=x['campaign']+'/'+x['config'].get('policy','original')
        if key not in groups:
            groups[key]=dict(reference_offers=len(x['reference']),radius=location_radius(x['reference'],x['panel']))
        rows.append(dict(campaign=x['campaign'],config=x['config'],precision=precision(x['reference'],x['warmup'],x['panel']),
                         reference_group=key,target_used=False))
    e.require(len(rows)==78,'All original cohorts required')
    elapsed=e.read(ROOT/'analysis/runtime_io_nginx_deadline_panel/generation-01/campaign/summary.json')['elapsed_sec']
    return dict(schema='warmup-precision-cost-offline-v1',cohorts=78,rows=rows,groups=groups,
        campaigns={name:summarize([r for r in rows if r['campaign']==name]) for name,_,_,_ in s.SPECS},
        policies={key:summarize([r for r in rows if r['reference_group']==key]) for key in groups},
        iid_cdf=dict(warmup25_halfwidth_pp=100*dkw(25),sufficient_5pp_n=sufficient_n(),
            paired_comparison=[pair_n(n) for n in (800,1600)],
            sufficient_only=True,independence_stationarity_established=False,future_transfer_bound=False),
        cost_grid=[cost(n,elapsed) for n in GRID],
        optimistic_maximum_service_warmup={str(r):maximum_warmup(r) for r in (4,8)},
        original_campaign_elapsed_sec=elapsed,new_collection=False,manuscript_changed=False,
        predictive_usefulness_established=False,
        inference='Conditional IID within-window median/CDF illustrations, no 78-window joint inference. Precision does not establish post-warmup stability; transformed intervals hold empirical shape fixed and omit CDF uncertainty.',
        decision='Hold longer-warmup hardware collection. Twenty-five offers give coarse conditional precision, but the sufficient IID CDF count violates current service limits and does not address later drift. A new measurement/protocol and demonstrated window-to-future relation are required before fresh evaluation.')


def render(r):
    lines=['# Warmup precision and collection cost','','11 October 2026. Offline audit of all 78 NGINX warmup/reference pairs; no target outcomes used for precision.','',
        '| Campaign | Median warmup 95% interval width (us) | Median transformed probability-range width (pp) | Width >5 pp |',
        '|---|---:|---:|---:|']
    for name,x in r['campaigns'].items():
        lines.append(f"| {name} | {x['warmup95_width_us']['median']:.3f} | {x['mapped_width_pp']['median']:.3f} | {x['mapped_width_above_5pp']}/{x['cohorts']} |")
    lines+=['','These are conditional IID order-statistic illustrations. The transformed range is median-correction interval geometry, not a future miss-probability or error confidence interval.','',
        '| Reference group | Largest symmetric empirical location radius for <=5 pp (us) |','|---|---:|']
    for name,x in r['groups'].items():lines.append(f"| {name} | {x['radius']['symmetric_radius_ns']/1000:.3f} |")
    lines+=['','Radii are calibration sensitivity quantities, not justified bounds on future shifts.','',
        f"The one-window IID DKWM CDF halfwidth at n=25 is {r['iid_cdf']['warmup25_halfwidth_pp']:.3f} pp.",
        f"A sufficient 95% uniform-CDF halfwidth <=5 pp uses {r['iid_cdf']['sufficient_5pp_n']} offers, not a minimum necessary sample size or a power estimate.",'',
        '| Fixed calibration offers | Equal-alpha paired-bound floor (pp) | Sufficient warmup offers for paired <=5 pp |','|---|---:|---:|']
    for x in r['iid_cdf']['paired_comparison']:
        lines.append(f"| {x['calibration_n']} | {x['asymptotic_halfwidth_floor_pp']:.3f} | {x['sufficient_warmup_n'] if x['sufficient_warmup_n'] is not None else 'Unavailable under this bound'} |")
    lines+=['','The paired illustration applies one-sample DKWM bounds with alpha=.025 each and the triangle/union bound. It permits different window distributions, estimates contemporaneous distributions only, and gives no future transfer certificate.',
        'A floor above the margin is a limitation of this conservative allocation, not proof that every estimator or interval needs more calibration.','',
        '| Warmup offers per target | Extra offered requests | Extra nominal minutes | Projected science minutes | Fits optimistic service at 4/s / 8/s |','|---|---:|---:|---:|---|']
    for x in r['cost_grid']:
        passed=' / '.join('yes' if x['services'][str(rate)]['passes_necessary_120sec'] else 'no' for rate in (4,8))
        lines.append(f"| {x['warmup_offers_per_target']} | {x['extra_offers']} | {x['extra_nominal_sec']/60:.3f} | {x['conditional_projected_science_minutes']:.3f} | {passed} |")
    lines+=['','Projections add nominal warmup schedules to the observed science lifetime, assuming all other behavior is unchanged. They exclude new design/qualification/preflight and do not certify campaign reserve or cleanup checks.',
        f"Ignoring startup and drain, the strict 120-second service ceiling plus 8-second reserve permits at most {r['optimistic_maximum_service_warmup']['4']} warmup offers at 4/s and {r['optimistic_maximum_service_warmup']['8']} at 8/s with 300 target offers. Those are optimistic maxima, not approved counts.",'',
        '**Decision: hold longer-warmup hardware collection.** More precise warmup measurements would still need a demonstrated relation to the later window. Existing failed forecasts, protocol limits and no-retry rules remain unchanged.',
        'Worker-wait remains held, friend-owned V31 pending, manuscript unchanged.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    r=analyze();report=render(r)
    if args.verify:
        for name,digest in e.read(OUT/'inputs_sha256.json').items():e.require(e.sha(ROOT/name)==digest,'Planning input changed: '+name)
        for name,digest in e.read(OUT/'seal.json')['files_sha256'].items():e.require(e.sha(OUT/name)==digest,'Planning artifact changed: '+name)
        e.require(r==e.read(OUT/'planning.json') and report==(OUT/'report.md').read_text(),'Planning arithmetic replay differs')
        print('All 78 warmups, exact ranks, precision/cost arithmetic and sealed audit verify.')
    else:
        e.require(not (OUT/'planning.json').exists(),'Preserve existing audit; no overwrite')
        e.save(OUT/'planning.json',r);(OUT/'report.md').write_text(report);e.save(OUT/'inputs_sha256.json',e.INPUTS)
        print('Saved offline audit: '+str(OUT/'report.md'))


if __name__=='__main__':main()
