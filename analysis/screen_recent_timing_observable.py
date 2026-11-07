#!/usr/bin/env python3
"""Explore pre-measurement warmup timing; no experiments or guard training."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics as st

import screen_forecast_reliability as original

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/runtime_io_recent_timing_observable/20261010'


def save(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def warmup(campaign,record):
    if campaign['name']=='Go V31':
        base,saved,_=campaign['validation_metadata']
        directory=base/saved['trial_refs'][record['name']]['path']
        value=original.sealed_read(directory/'warmup.json',directory)
        rows=value['requests']
        original.require(len(rows)==value['total_scheduled'] and len({r['ID'] for r in rows})==len(rows),'Go warmup all-offer conservation')
        values=[None if r['Error'] or r['StatusCode']!=200 else r['EndToEndLatencyNs'] for r in sorted(rows,key=lambda r:r['ID'])]
        duration=value['duration_sec']
        span=max(r['CompletedOffsetNs'] for r in rows)/1e9
    else:
        base=campaign['validation_metadata']
        directory=base/'validation'/record['name']
        value=original.sealed_read(directory/'warmup.json',base,'evidence-seal.json')
        rows=value['Rows']
        original.require(len(rows)==value['Count']==25 and len({r['ID'] for r in rows})==25,'NGINX warmup all-offer conservation')
        original.require([r['ID'] for r in rows]==[f'warmup-{i}' for i in range(25)],'NGINX warmup order')
        values=[None if r['Error'] or r['DecodeError'] or r['Status']!=200 else r['BodyDoneNs']-r['ScheduledNs'] for r in rows]
        duration=None
        span=max(r['BodyDoneNs'] for r in rows)/1e9
    original.require(len(values)>=25,'Recent pool unavailable')
    return values,dict(full_offers=len(values),last_25_offers=25,configured_warmup_sec=duration,
                      full_observed_client_span_sec=span,unsuccessful=sum(v is None for v in values),
                      same_service_target_rate_rps=record['rate_rps'])


def misspct(values,deadline):
    return 100*sum(v is None or v>deadline for v in values)/len(values)


def aggregates(rows,method,tolerance):
    errors=[abs(r['predictions_pct'][method]-r['observed_miss_pct']) for r in rows]
    blocks=[dict(block=b,mae_pp=st.mean(abs(r['predictions_pct'][method]-r['observed_miss_pct']) for r in rows if r['block']==b)) for b in range(1,7)]
    profiles=[dict(profile=p,mae_pp=st.mean(abs(r['predictions_pct'][method]-r['observed_miss_pct']) for r in rows if r['profile']==p)) for p in 'ABC']
    original.close(st.mean(b['mae_pp'] for b in blocks),st.mean(errors))
    return dict(mae_pp=st.mean(errors),maximum_error_pp=max(errors),errors_above_5pp=sum(e>tolerance for e in errors),blocks=blocks,profiles=profiles)


def compute():
    original.INPUTS.clear()
    plan=original.read(OUT/'design.json')
    for name,h in original.read(OUT/'design_sha256.json').items():
        original.require(original.sha(ROOT/name)==h,'Recent observable design changed')
        original.INPUTS[name]=h
    original.INPUTS[str(Path(original.__file__).relative_to(ROOT))]=original.sha(Path(original.__file__))
    for path in ['diagnostic/nginx_prediction_study.py','diagnostic/v31_study.py']:
        original.INPUTS[path]=original.sha(ROOT/path)
    old=original.read('analysis/runtime_io_forecast_reliability/20261010/screen.json')
    campaigns=original.calibrations()
    output=[]
    for campaign in campaigns:
        baseline=next(c['calibration'] for c in old['campaigns'] if c['calibration']['name']==campaign['name'])
        pool=[x for cohort in campaign['cohorts'] for x in cohort['values_ns']]
        p0=original.probability(pool,campaign['deadline_ns'])
        original.close(p0,baseline['pooled_forecast_pct'])
        records=original.validation(campaign)
        rows=[]
        for record in records:
            values,cost=warmup(campaign,record)
            p25=misspct(values[-25:],campaign['deadline_ns'])
            pfull=misspct(values,campaign['deadline_ns'])
            predictions=dict(original_reference=p0,recent_last_25=p25,recent_full=pfull,
                sample_weighted_update=(len(pool)*p0+len(values)*pfull)/(len(pool)+len(values)),
                equal_weight_update=plan['equal_blend_weight']*pfull+(1-plan['equal_blend_weight'])*p0)
            # Future observed outcomes play no part in these predictions or flags.
            warnings={k:abs(predictions[k]-p0)>plan['error_tolerance_pp'] for k in ('recent_last_25','recent_full')}
            rows.append({**record,'cost':cost,'predictions_pct':predictions,'warnings':warnings,
                         'future_error_used_to_fit_predictor_or_warning':False})
        methods={m:aggregates(rows,m,plan['error_tolerance_pp']) for m in rows[0]['predictions_pct']}
        old_methods=next(c['baselines']['always_forecast'] for c in old['campaigns'] if c['calibration']['name']==campaign['name'])
        original.close(methods['original_reference']['mae_pp'],old_methods['accepted_mae_pp'])
        warnings={}
        for name in ('recent_last_25','recent_full'):
            accepted=[r for r in rows if not r['warnings'][name]]
            rejected=[r for r in rows if r['warnings'][name]]
            err=lambda r:abs(p0-r['observed_miss_pct'])
            warnings[name]=dict(warnings=len(rejected),accepted_cohorts=len(accepted),
                coverage_pct=100*len(accepted)/len(rows),accepted_mae_pp=st.mean(err(r) for r in accepted) if accepted else None,
                accepted_errors_above_5pp=sum(err(r)>5 for r in accepted),
                false_warnings=sum(err(r)<=5 for r in rejected),
                caught_original_errors_above_5pp=sum(err(r)>5 for r in rejected),
                risk_certificate=False)
        contrasts={m:[methods['original_reference']['blocks'][i]['mae_pp']-methods[m]['blocks'][i]['mae_pp'] for i in range(6)] for m in methods if m!='original_reference'}
        halfwidths={str(n):100*math.sqrt(math.log(40)/(2*n)) for n in sorted({25}|{r['cost']['full_offers'] for r in rows})}
        output.append(dict(name=campaign['name'],deadline_ns=campaign['deadline_ns'],methods=methods,
          warnings=warnings,validation=rows,descriptive_block_improvements_pp=contrasts,
          iid_sampling_halfwidth_illustrations_pp=halfwidths,
          distinct_warmup_forecasts=len({r['predictions_pct']['recent_full'] for r in rows}),
          independent_guard_validation=False))
    return dict(role='retrospective_observable_baseline_gate',decision_time=plan['decision_time'],
                contract_differs_from_original_global_forecast=True,new_collection=False,novelty_established=False,
                hardware_or_scheduler_cause_established=False,campaigns=output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    original.close(misspct([9,10,11,None],10),50)
    result=compute()
    if args.verify:
        original.require(result==json.loads((OUT/'screen.json').read_text()),'Recent-timing screen differs')
        for name,h in json.loads((OUT/'inputs_sha256.json').read_text()).items():
            original.require(original.sha(ROOT/name)==h,'Recent timing input changed: '+name)
        for name,h in json.loads((OUT/'screen_seal.json').read_text()).items():
            original.require(original.sha(ROOT/name)==h,'Recent timing output changed: '+name)
        print('Recent-timing recomputation, consumed original seals, prior-result reconciliation and boundary/failure accounting verify.')
        return
    original.require(not (OUT/'screen.json').exists(),'Preserve screen; use --verify')
    save(OUT/'screen.json',result)
    save(OUT/'inputs_sha256.json',{**original.INPUTS,str(Path(__file__).relative_to(ROOT)):original.sha(Path(__file__))})
    save(OUT/'screen_seal.json',{str(p.relative_to(ROOT)):original.sha(p) for p in [OUT/'screen.json',OUT/'inputs_sha256.json']})
    for c in result['campaigns']:
        print(c['name'],{m:(round(v['mae_pp'],3),round(v['maximum_error_pp'],3),v['errors_above_5pp']) for m,v in c['methods'].items()})
        print('warnings',c['warnings'])
        print('block gains',{m:[round(x,3) for x in vals] for m,vals in c['descriptive_block_improvements_pp'].items()})
        if c['name']=='NGINX':
            print('known excursion',next(r for r in c['validation'] if r['name']=='cohort-4'))


if __name__=='__main__':
    main()
