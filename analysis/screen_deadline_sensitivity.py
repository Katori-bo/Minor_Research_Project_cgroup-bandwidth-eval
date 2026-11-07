#!/usr/bin/env python3
"""Fixed calibration/warmup diagnostics at declared panels; no fit or collection."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import statistics as st
import sys
import screen_forecast_reliability as e
import screen_deadline_scope as scope

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/runtime_io_deadline_sensitivity/20261010'
sys.path.insert(0,str(ROOT/'diagnostic'))
import nginx_power_confirmation_model as model

SOURCES=('analysis/screen_deadline_sensitivity.py','analysis/test_deadline_sensitivity.py',
 'docs/runtime_io_deadline_sensitivity_protocol_20261010.md','analysis/screen_forecast_reliability.py',
 'analysis/screen_deadline_scope.py','diagnostic/nginx_power_confirmation_model.py',
 'diagnostic/nginx_prediction_model.py')
SPECS=(('NGINX original','runtime_io_nginx_prediction',4,18),
 ('NGINX power','runtime_io_nginx_power_confirmation',4,24),
 ('NGINX rate','runtime_io_nginx_rate_transfer',6,12),
 ('NGINX panel','runtime_io_nginx_deadline_panel',4,24))


def median(values):
    e.require(values and all(x is not None for x in values),'Location median needs complete outcomes')
    v=sorted(values);n=len(v)
    return Fraction(v[n//2]) if n%2 else Fraction(v[n//2-1]+v[n//2],2)


def miss(values,deadline):
    e.require(bool(values),'Empty all-offer reference')
    return Fraction(sum(x is None or x>deadline for x in values),len(values))


def maxdiff(a,b):return float(100*max(abs(x-y) for x,y in zip(a,b)))


def features(reference,cohorts,warmup,panel):
    e.require(len(warmup)==25 and len(panel)==5,'Fixed warmup/panel budget required')
    e.require(sorted(x for group in cohorts for x in group if x is not None)==
              sorted(x for x in reference if x is not None) and
              sum(x is None for group in cohorts for x in group)==sum(x is None for x in reference),
              'Calibration cohort/reference accounting differs')
    deadlines=[p['deadline_ns'] for p in panel]
    e.require(all(type(d) is int and d>=0 for d in deadlines),'Finite calibration cutoffs required')
    pred=[miss(reference,d) for d in deadlines];warm=[miss(warmup,d) for d in deadlines]
    agreement=max(maxdiff(pred,[miss(v,d) for d in deadlines]) for v in cohorts)
    stress=max(maxdiff(pred,[miss(reference,max(0,d+offset)) for d in deadlines])
               for offset in (-100000,100000))
    delta=median(warmup)-median(reference) if all(x is not None for x in reference+warmup) else None
    shifted=[miss(reference,Fraction(d)-delta) for d in deadlines] if delta is not None else None
    signal=maxdiff(pred,shifted) if shifted is not None else None
    scores=dict(calibration_agreement=agreement,sensitivity_100us=stress,
                warmup_cdf=maxdiff(pred,warm),median_shift=signal)
    accepts={k:v is not None and v<=5+1e-10 for k,v in scores.items()}
    accepts.update(always=True,agreement_and_shift=accepts['calibration_agreement'] and accepts['median_shift'])
    predictions=dict(reference=pred,warmup=warm,weighted_update=[miss(reference+warmup,d) for d in deadlines],
                     location_shift=shifted)
    return dict(scores_pp=scores,accepts=accepts,median_delta_ns=float(delta) if delta is not None else None,
                location_available=delta is not None,
                predictions_pct={k:[float(100*x) for x in v] if v is not None else None for k,v in predictions.items()},
                target_used=False)


def warning_score(rows,key):
    accepted=[r for r in rows if r['features']['accepts'][key]]
    rejected=[r for r in rows if not r['features']['accepts'][key]]
    errs=[r['methods']['reference']['maximum_error_pp'] for r in accepted]
    return dict(cohorts=len(rows),accepted=len(accepted),coverage_pct=100*len(accepted)/len(rows),
        accepted_errors_above_5pp=sum(x>5+1e-10 for x in errs),
        rejected_errors_within_5pp=sum(r['methods']['reference']['maximum_error_pp']<=5+1e-10 for r in rejected),
        accepted_mean_maximum_error_pp=st.mean(errs) if errs else None,
        accepted_maximum_error_pp=max(errs) if errs else None,confirmed=False)


def auc(rows,key):
    available=[r for r in rows if r['features']['scores_pp'][key] is not None]
    bad=[r['features']['scores_pp'][key] for r in available if r['methods']['reference']['maximum_error_pp']>5+1e-10]
    good=[r['features']['scores_pp'][key] for r in available if r['methods']['reference']['maximum_error_pp']<=5+1e-10]
    pairs=len(bad)*len(good)
    value=sum((x>y)+.5*(x==y) for x in bad for y in good)/pairs if pairs else None
    return dict(descriptive_auc=value,bad=len(bad),good=len(good),unavailable=len(rows)-len(available),
                independent_pairs_established=False)


def summary(rows):
    methods={}
    for name in rows[0]['methods']:
        available=[r['methods'][name] for r in rows if r['methods'][name] is not None]
        methods[name]=dict(available=len(available),unavailable=len(rows)-len(available),
            panel_mae_pp=st.mean(x['mean_error_pp'] for x in available) if available else None,
            mean_cohort_maximum_pp=st.mean(x['maximum_error_pp'] for x in available) if available else None,
            worst_error_pp=max(x['maximum_error_pp'] for x in available) if available else None,
            cohorts_above_5pp=sum(x['maximum_error_pp']>5+1e-10 for x in available),
            per_quantile=[dict(quantile=q,mean_error_pp=st.mean(x['errors_pp'][i] for x in available),
                mean_signed_forecast_minus_target_pp=st.mean(x['signed_forecast_minus_target_pp'][i] for x in available))
                for i,q in enumerate(('1/10','1/4','1/2','3/4','9/10'))] if available else [])
    return dict(cohorts=len(rows),methods=methods,
        warnings={k:warning_score(rows,k) for k in rows[0]['features']['accepts']},
        rankings={k:auc(rows,k) for k in rows[0]['features']['scores_pp']})


def load_specs():
    specs=[]
    for name,folder,ncal,nval in SPECS:
        base=ROOT/'analysis'/folder/'generation-01/campaign'
        read=lambda rel:e.sealed_read(base/rel,base,'evidence-seal.json')
        forecast=read('forecast/forecast.json');e.require(not forecast['validation_used'],'Foreign forecast')
        groups={}
        for i in range(1,ncal+1):
            case=f'calibration/cohort-{i}';cfg=read(case+'/study-config.json')
            records=model.outcomes(read(case+'/measurement.json'),cfg)
            e.require(len(records)==400,'Complete calibration required')
            key='all' if name=='NGINX original' else str(cfg['rate_rps']) if name=='NGINX rate' else cfg['policy']
            groups.setdefault(key,[]).append([o['e2e_ns'] if o['success'] else None for o in records])
        refs={k:[x for cohort in cohorts for x in cohort] for k,cohorts in groups.items()}
        if name=='NGINX original':e.require(sorted(refs['all'])==forecast['sorted_samples_ns'],'Original reference mismatch')
        else:
            for k,v in refs.items():e.require(model.reference([dict(success=x is not None,e2e_ns=x) for x in v])==forecast['references'][k],'Reference mismatch')
        for i in range(1,nval+1):
            case=f'validation/cohort-{i}';cfg=read(case+'/study-config.json')
            key='all' if name=='NGINX original' else '5' if name=='NGINX rate' else cfg['policy']
            reference=refs[key];panel=scope.panel(scope.pool([dict(success=x is not None,e2e_ns=x) for x in reference]))
            if name=='NGINX panel':e.require(panel==forecast['panels'][key],'Frozen fresh panel mismatch')
            warm=model.outcomes(read(case+'/warmup.json'),cfg,'warmup')
            if name!='NGINX original':
                timing=read(case+'/warmup-timing.json');start=read(case+'/measurement-start.json')
                e.require(timing['finished_monotonic']<=start['monotonic'],'Warmup barrier differs')
            extra=refs[str(cfg['rate_rps'])] if name=='NGINX rate' else None
            specs.append(dict(campaign=name,base=base,case=case,config=cfg,panel=panel,reference=reference,
                cohorts=groups[key],warmup=[o['e2e_ns'] if o['success'] else None for o in warm],
                extra_reference=extra,acquired_calibration_offers=ncal*400))
    return specs


def compute():
    e.INPUTS.clear();design=e.read(OUT/'design.json')
    e.require(design['specs']==[list(v) for v in SPECS] and design['tolerance_pp']==5 and
              design['stress_ns']==100000,'Fixed screen design differs')
    for name,digest in e.read(OUT/'design_sha256.json').items():
        e.require(e.sha(ROOT/name)==digest,'Screen source/design changed: '+name);e.INPUTS[name]=digest
    # Every feature is computed before any measurement target is loaded here.
    specs=load_specs();pre=[features(x['reference'],x['cohorts'],x['warmup'],x['panel']) for x in specs]
    rows=[]
    for spec,feature in zip(specs,pre):
        base=spec['base'];read=lambda rel:e.sealed_read(base/rel,base,'evidence-seal.json')
        targets=model.outcomes(read(spec['case']+'/measurement.json'),spec['config'])
        e.require(len(targets)==300,'Complete validation required')
        values=[o['e2e_ns'] if o['success'] else None for o in targets]
        observed=[float(100*miss(values,p['deadline_ns'])) for p in spec['panel']]
        predictions=dict(feature['predictions_pct'])
        if spec['extra_reference'] is not None:
            predictions['rate_matched']=[float(100*miss(spec['extra_reference'],p['deadline_ns'])) for p in spec['panel']]
        methods={}
        for name,pred in predictions.items():
            errors=[abs(a-b) for a,b in zip(pred,observed)] if pred is not None else None
            methods[name]=dict(mean_error_pp=st.mean(errors),maximum_error_pp=max(errors),
                errors_pp=errors,signed_forecast_minus_target_pp=[a-b for a,b in zip(pred,observed)]) if errors is not None else None
        raw_result=read(spec['case']+'/result.json')
        rows.append(dict(campaign=spec['campaign'],config=spec['config'],panel=spec['panel'],features=feature,
            methods=methods,observed_pct=observed,target_failures=sum(x is None for x in values),
            observations=raw_result.get('observations',raw_result.get('domain_exits',[])),
            cost=dict(acquired_calibration_offers=spec['acquired_calibration_offers'],warmup_offers=25,
                      additional_offers=0,live_observer_qualified=False)))
    old=e.read(ROOT/'analysis/runtime_io_deadline_scope/20261010/screen.json')
    fresh=e.read(ROOT/'analysis/runtime_io_nginx_deadline_panel/generation-01/campaign/comparison.json')
    campaigns=[]
    for name,_,_,count in SPECS:
        subset=[r for r in rows if r['campaign']==name];e.require(len(subset)==count,'All cohorts retained')
        total=summary(subset)
        if name!='NGINX panel':
            previous=next(x for x in old['campaigns'] if x['name']==name)
            prior='original' if name=='NGINX original' else 'matched' if name=='NGINX power' else 'baseline'
            e.close(total['methods']['reference']['panel_mae_pp'],previous['methods'][prior]['panel_mae_pp'])
        else:
            for policy in ('P0','P1'):
                sub=[r for r in subset if r['config']['policy']==policy]
                e.close(summary(sub)['methods']['reference']['panel_mae_pp'],fresh['policies'][policy]['methods']['matched']['panel_average']['mean'])
                for row in sub:
                    prior=next(x for x in fresh['errors'] if x['config']==row['config'])
                    for i,d in enumerate(prior['panel']):
                        e.close(row['methods']['reference']['errors_pp'][i],d['absolute_error_pp']['matched'])
        policies=sorted({r['config'].get('policy','original') for r in subset})
        campaigns.append(dict(name=name,summary=total,
            policies={p:summary([r for r in subset if r['config'].get('policy','original')==p]) for p in policies},
            rates_rps={str(1e9/rate):summary([r for r in subset if r['config']['interval_ns']==rate])
                   for rate in sorted({r['config']['interval_ns'] for r in subset})},
            blocks={str(b):summary([r for r in subset if r['config']['block']==b]) for b in range(1,7)}))
    return dict(role='Known-outcome retrospective development, not independent confirmation',
        cohorts=len(rows),all78_retained=len(rows)==78,new_collection=False,manuscript_changed=False,
        novelty_established=False,future_reliability_established=False,primary_decisions_changed=False,
        calibration_only_panels_and_prevalidation_features=True,no_parameter_search=True,
        rows=rows,campaigns=campaigns,inference='All ranks/coverage are descriptive; shared references and correlated chronology. No IID tests, population drift claim or future certificate.')


def render(result):
    lines=['# Deadline sensitivity and advance-warning screen','','10 October 2026. Known-outcome development; all 78 cohorts retained, no new traffic or paper edit.','',
        '| Campaign | Flag | Accepted | Accepted errors >5 pp | Rejected errors <=5 pp | Max accepted error (pp) |',
        '|---|---|---:|---:|---:|---:|']
    for campaign in result['campaigns']:
        for name,x in campaign['summary']['warnings'].items():
            value=f"{x['accepted_maximum_error_pp']:.3f}" if x['accepted_maximum_error_pp'] is not None else 'unavailable'
            lines.append(f"| {campaign['name']} | {name} | {x['accepted']}/{x['cohorts']} | {x['accepted_errors_above_5pp']} | {x['rejected_errors_within_5pp']} | {value} |")
    lines+=['','Errors above 5 pp here are cohort maxima over the panel, an exploratory label, not a new primary acceptance test.','',
        '| Campaign | Forecast | Panel MAE (pp) | Mean cohort maximum (pp) | Cohorts >5 pp |','|---|---|---:|---:|---:|']
    for campaign in result['campaigns']:
        for name,x in campaign['summary']['methods'].items():
            mean=f"{x['panel_mae_pp']:.3f}" if x['panel_mae_pp'] is not None else 'unavailable'
            maximum=f"{x['mean_cohort_maximum_pp']:.3f}" if x['mean_cohort_maximum_pp'] is not None else 'unavailable'
            lines.append(f"| {campaign['name']} | {name} | {mean} | {maximum} | {x['cohorts_above_5pp']}/{x['available']} |")
    lines+=['','All methods receive the full acquired calibration and existing 25-offer warmup. Location correction is an ordinary median-shift model, not a new measured state signal.','',
        '## Descriptive rankings by campaign','','| Campaign | Feature | AUC | Larger/smaller errors |','|---|---|---:|---:|']
    for campaign in result['campaigns']:
        for name,x in campaign['summary']['rankings'].items():
            value=f"{x['descriptive_auc']:.3f}" if x['descriptive_auc'] is not None else 'unavailable'
            lines.append(f"| {campaign['name']} | {name} | {value} | {x['bad']}/{x['good']} |")
    lines+=['','No significance or predictive guarantee follows from AUC. Policy/rate/block breakdowns and every cohort are in screen.json; no favorable pooled campaign is selected.','',
        '## Calibration and fixed sensitivity','','| Campaign / reference | Max cohort disagreement (pp) | Max 100 us sensitivity (pp) |','|---|---:|---:|']
    seen=set()
    for r in result['rows']:
        key=(r['campaign'],r['config'].get('policy','original'))
        if key in seen:continue
        seen.add(key);s=r['features']['scores_pp']
        lines.append(f"| {' / '.join(key)} | {s['calibration_agreement']:.3f} | {s['sensitivity_100us']:.3f} |")
    lines+=['','Fixed sensitivity is not a justified bound on future drift. Calibration agreement is constant within a reference group; neither can select later time windows within that group.',
        'Failures retain their mass at infinity. Location quantities refuse if inputs contain failures. Duplicate cutoff labels and all chronological blocks remain included.',
        'This screen changes no scientific acceptance decision, establishes no causal shift mechanism, and qualifies no live observer. Any fitted rule or changed threshold would be development requiring fresh evaluation.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=compute();report=render(result)
    if args.verify:
        for name,digest in e.read(OUT/'inputs_sha256.json').items():e.require(e.sha(ROOT/name)==digest,'Screen input changed: '+name)
        for name,digest in e.read(OUT/'seal.json')['files_sha256'].items():e.require(e.sha(OUT/name)==digest,'Screen artifact changed: '+name)
        e.require(result==e.read(OUT/'screen.json') and report==(OUT/'report.md').read_text(),'Screen replay differs')
        print('All 78 cohorts, fixed features, forecast reconciliation and sealed screen verify.')
    else:
        e.require(not (OUT/'screen.json').exists(),'No overwrite or rescreen')
        e.save(OUT/'screen.json',result);(OUT/'report.md').write_text(report)
        e.save(OUT/'inputs_sha256.json',e.INPUTS)
        print('Saved fixed screen: '+str(OUT/'report.md'))


if __name__=='__main__':main()
