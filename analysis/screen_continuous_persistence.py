#!/usr/bin/env python3
"""Frozen first100/next200 NGINX persistence replay; no new collection."""
import argparse
from fractions import Fraction
from pathlib import Path
import statistics as st
import sys

import screen_forecast_reliability as e

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis/runtime_io_continuous_persistence/20261010'
sys.path.insert(0,str(ROOT/'diagnostic'))
import nginx_prediction_model as model


def count(records, deadline):
    e.require(bool(records), 'Empty all-offer pool')
    return sum(not r['success'] or r['e2e_ns'] > deadline for r in records)


def forecast(reference, probe, deadline, available):
    """Only reference and first100 outcomes; no suffix argument."""
    e.require(len(probe)==100, 'Frozen100-offer probe required')
    nr,np=count(reference,deadline),count(probe,deadline)
    probabilities={
        'original':Fraction(nr,len(reference)),
        'recent100':Fraction(np,100),
        'sample_weighted_update':Fraction(nr+np,len(reference)+100)}
    half_score=100*abs(Fraction(count(probe[:50],deadline),50)-
                       Fraction(count(probe[50:],deadline),50))
    return dict(predictions={k:dict(misses=p.numerator,offers=p.denominator,
                                   miss_pct=float(100*p)) for k,p in probabilities.items()},
                probe_misses=np,probe_offers=100,
                probe_half_miss_pct=[2*count(probe[:50],deadline),2*count(probe[50:],deadline)],
                half_disagreement_pp=float(half_score),accept_recent100=bool(available and half_score<=5),
                body_timing_available_before_target=available,
                suffix_used=False,future_risk_certificate=False)


def errors(row):
    observed=Fraction(row['target_misses'],200)
    return {k:100*abs(Fraction(p['misses'],p['offers'])-observed)
            for k,p in row['forecast']['predictions'].items()}


def method_summary(rows,method):
    vals=[errors(r)[method] for r in rows]
    return dict(cohorts=len(rows),mae_pp=float(st.mean(vals)) if vals else None,
                maximum_error_pp=float(max(vals)) if vals else None,
                errors_above_5pp=sum(v>5 for v in vals),
                fraction_with_error_above_5pp=sum(v>5 for v in vals)/len(vals) if vals else None)


def summarize(rows):
    e.require(bool(rows),'Empty summary population')
    methods={k:method_summary(rows,k) for k in rows[0]['forecast']['predictions']}
    blocks=[]
    for b in sorted({r['block'] for r in rows}):
        group=[r for r in rows if r['block']==b]
        blocks.append(dict(block=b,methods={k:method_summary(group,k) for k in methods}))
    accepted=[r for r in rows if r['forecast']['accept_recent100']]
    rejected=[r for r in rows if not r['forecast']['accept_recent100']]
    transition=[r for r in rows if 10<=r['observed_target_miss_pct']<=90]
    transition_accepted=[r for r in transition if r['forecast']['accept_recent100']]
    accepted_methods={k:method_summary(accepted,k) for k in methods}
    bad=lambda r:errors(r)['recent100']>5
    coverage=100*len(accepted)/len(rows)
    transition_coverage=100*len(transition_accepted)/len(transition) if transition else None
    useful=bool(accepted) and coverage>=50 and not any(bad(r) for r in accepted) and (
        not transition or transition_coverage>=50)
    return dict(methods=methods,transition_methods={k:method_summary(transition,k) for k in methods},
                blocks=blocks,
                paired_block_gains_pp={k:[b['methods']['original']['mae_pp']-b['methods'][k]['mae_pp']
                                         for b in blocks] for k in methods if k!='original'},
                chronological_domain_flags=sum(not r['forecast']['body_timing_available_before_target'] for r in rows),
                guard=dict(accepted=len(accepted),total=len(rows),coverage_pct=coverage,
                  transition_cohorts=len(transition),transition_accepted=len(transition_accepted),
                  transition_coverage_pct=transition_coverage,bad_accepted=sum(bad(r) for r in accepted),
                  caught_bad=sum(bad(r) for r in rejected),false_warnings=sum(not bad(r) for r in rejected),
                  accepted_methods=accepted_methods,useful_screen=useful,independent_validation=False),
                all_answer_recent100_within_5pp=all(not bad(r) for r in rows))


def read_client(base,case,cfg,phase):
    raw=e.sealed_read(case/f'{phase}.json',base,'evidence-seal.json')
    records=model.outcomes(raw,cfg,phase)
    e.require(len(records)==cfg['count' if phase=='measurement' else 'warmup_count'],
              'All-offer count mismatch')
    return raw['Rows'],records


def compute():
    e.INPUTS.clear()
    design=e.read(OUT/'design.json')
    for path,digest in e.read(OUT/'design_sha256.json').items():
        e.require(e.sha(ROOT/path)==digest,'Frozen persistence design changed')
        e.INPUTS[path]=digest
    prior=e.read('analysis/runtime_io_prevalidation_shift/20261010/screen.json')
    all_campaigns=[]
    for spec in design['campaigns']:
        base=ROOT/'analysis'/spec['folder']/'generation-01/campaign'
        saved=e.sealed_read(base/'forecast/forecast.json',base,'evidence-seal.json')
        e.require(saved['primary_deadline_ns']==design['deadline_ns'] and not saved['validation_used'],
                  'Foreign primary endpoint/forecast')
        refs={};calibration_warmup=0
        for i in range(1,spec['calibration_cohorts']+1):
            case=base/f'calibration/cohort-{i}'
            cfg=e.sealed_read(case/'study-config.json',base,'evidence-seal.json')
            _,records=read_client(base,case,cfg,'measurement')
            _,warmup=read_client(base,case,cfg,'warmup')
            calibration_warmup+=len(warmup)
            key=cfg['policy'] if spec['name']=='NGINX power' else (
                str(cfg['rate_rps']) if spec['name']=='NGINX rate' else 'original')
            refs.setdefault(key,[]).extend(records)
        if spec['name']=='NGINX original':
            e.require(sorted(r['e2e_ns'] for r in refs['original'] if r['success'])==saved['sorted_samples_ns'],
                      'Original calibration-CDF mismatch')
        else:
            for key,records in refs.items():
                r=saved['references'][key]
                e.require(sorted(x['e2e_ns'] for x in records if x['success'])==r['successful_samples_ns'] and
                          sum(not x['success'] for x in records)==r['failed_offers'],
                          'Policy/rate reference mismatch')
        rows=[]
        prior_name='NGINX' if spec['name']=='NGINX original' else spec['name']
        historical=next(c for c in prior['campaigns'] if c['name']==prior_name)
        for i in range(1,spec['validation_cohorts']+1):
            case=base/f'validation/cohort-{i}'
            cfg=e.sealed_read(case/'study-config.json',base,'evidence-seal.json')
            raw,records=read_client(base,case,cfg,'measurement')
            _,warmup=read_client(base,case,cfg,'warmup')
            e.require(len(records)==300 and len(warmup)==25,'Frozen300/25 cohort contract')
            reference=refs[cfg['policy'] if spec['name']=='NGINX power' else (
                '5' if spec['name']=='NGINX rate' else 'original')]
            # Only prefix records are supplied to the forecast function.
            probe=records[:100]
            probe_complete=max(r['BodyDoneNs'] for r in raw[:100])
            target_start=raw[100]['ScheduledNs']
            known_completion=all(r['BodyDoneNs']>=r['ScheduledNs'] for r in raw[:100])
            available=known_completion and probe_complete<target_start
            predicted=forecast(reference,probe,design['deadline_ns'],available)
            # Suffix scoring occurs after the predictions and flags are finalized.
            target=records[100:]
            target_misses=count(target,design['deadline_ns'])
            observed=100*Fraction(target_misses,200)
            complete_misses=count(records,design['deadline_ns'])
            e.require(complete_misses==count(probe,design['deadline_ns'])+target_misses,
                      'Probe/suffix all-offer conservation')
            previous=next(r for r in historical['rows'] if r['name']==f'cohort-{i}')
            e.close(float(100*Fraction(complete_misses,300)),previous['observed_miss_pct'])
            e.close(predicted['predictions']['original']['miss_pct'],
                    previous['features']['predictions_pct']['reference'])
            result=e.sealed_read(case/'result.json',base,'evidence-seal.json')
            rows.append(dict(name=f'cohort-{i}',block=cfg['block'],profile=cfg['profile'],
                policy=cfg.get('policy'),rate_rps=1e9/cfg['interval_ns'],forecast=predicted,
                target_misses=target_misses,target_offers=200,observed_target_miss_pct=float(observed),
                whole_cohort_misses=complete_misses,whole_cohort_observed_miss_pct=previous['observed_miss_pct'],
                unsuccessful_probe=sum(not r['success'] for r in probe),
                unsuccessful_target=sum(not r['success'] for r in target),
                historical_measurement_counter_delta=result.get('measurement_counter_delta'),
                historical_observations=result.get('observations',result.get('domain_exits',[])),
                cost=dict(selected_reference_offers=len(reference),initial_warmup_offers=len(warmup),
                  continuous_probe_offers=100,scheduled100_offer_window_sec=100*cfg['interval_ns']/1e9,
                  probe_body_completion_span_sec=probe_complete/1e9,
                  target_boundary_slack_sec=(target_start-probe_complete)/1e9,
                  online_correctness_and_inference_overhead_qualified=False)))
        e.require(len(rows)==spec['validation_cohorts'] and {r['block'] for r in rows}==set(range(1,7)),
                  'Retain entire54-cohort/6-block design')
        score=summarize(rows)
        subgroups={}
        for p in sorted({r['policy'] for r in rows if r['policy'] is not None}):
            subgroups[p]=summarize([r for r in rows if r['policy']==p])
        all_campaigns.append(dict(name=spec['name'],deadline_ns=design['deadline_ns'],rows=rows,**score,
            policy_subgroups=subgroups,cost=dict(acquired_calibration_measurement_offers=sum(len(v) for v in refs.values()),
              acquired_calibration_warmup_offers=calibration_warmup,
              acquired_validation_initial_warmup_offers=sum(r['cost']['initial_warmup_offers'] for r in rows),
              consumed_continuous_probe_offers=100*len(rows),target_offers=200*len(rows),
              qualification_startup_settling_cost_additional=True)))
    survives=all(c['guard']['useful_screen'] for c in all_campaigns) and all_campaigns[1]['policy_subgroups']['P0']['guard']['useful_screen']
    return dict(role=design['role'],new_collection=False,independent_confirmation=False,novelty_established=False,
                live_observer_qualified=False,all54_cohorts_retained=True,
                candidate_survives_frozen_usefulness_screen=survives,campaigns=all_campaigns)


def render(report):
    lines=['# Continuous probe persistence: offline assessment','','10 October 2026. First100 scheduled offers forecast the next200 in every completed NGINX cohort. Historical outcomes were known; this is development evidence.','',
           '| Campaign | Cohorts | Original MAE | Recent100 MAE | Update MAE | Recent100 max | Recent100 errors >5 pp |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for c in report['campaigns']:
        m=c['methods']
        lines.append(f"| {c['name']} | {len(c['rows'])} | {m['original']['mae_pp']:.3f} | {m['recent100']['mae_pp']:.3f} | {m['sample_weighted_update']['mae_pp']:.3f} | {m['recent100']['maximum_error_pp']:.3f} | {m['recent100']['errors_above_5pp']} |")
    lines+=['','All errors are percentage points of all-offer deadline-miss probability at20.565395ms, scored on the same200-offer suffix. The original method is original calibration for the first campaign, matched-policy calibration for power, and fixed5/s calibration for rate. The sample-weighted update pools that reference with the same100 probe offers. No window, threshold or blend was fitted.','',
            '## Difficult power-policy cases','','| Population | Original MAE | Recent100 MAE | Update MAE | Recent100 max | Errors >5 pp |','|---|---:|---:|---:|---:|---:|']
    for p,c in report['campaigns'][1]['policy_subgroups'].items():
        m=c['methods'];lines.append(f"| {p} | {m['original']['mae_pp']:.3f} | {m['recent100']['mae_pp']:.3f} | {m['sample_weighted_update']['mae_pp']:.3f} | {m['recent100']['maximum_error_pp']:.3f} | {m['recent100']['errors_above_5pp']} |")
    lines+=['','Keep P1 zero-miss endpoints separate; they cannot establish useful performance for P0 transition cases.','',
            '## Predeclared probe agreement guard','','Accept recent100 only if the first50 and second50 probe miss fractions differ by<=5pp and all first100 bodies finish before offer101 is scheduled. It is an ordinary stability check, not a future-risk bound.','',
            '| Campaign | Accepted / total | Coverage | Transition coverage | Bad accepted | Caught errors | False warnings | Accepted recent100 max |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    for c in report['campaigns']:
        g=c['guard'];tc='—' if g['transition_coverage_pct'] is None else f"{g['transition_coverage_pct']:.1f}%"
        mx=g['accepted_methods']['recent100']['maximum_error_pp'];mx='—' if mx is None else f'{mx:.3f}'
        lines.append(f"| {c['name']} | {g['accepted']}/{g['total']} | {g['coverage_pct']:.1f}% | {tc} | {g['bad_accepted']} | {g['caught_bad']} | {g['false_warnings']} | {mx} |")
    g=report['campaigns'][1]['policy_subgroups']['P0']['guard']
    lines+=['',f"P0 power guard: {g['accepted']}/{g['total']} answers, {g['coverage_pct']:.1f}% coverage, {g['bad_accepted']} bad accepted forecasts. Transition cases have observed suffix misses between10% and90%; that outcome-side label never enters the guard.",'',
            'The frozen usefulness screen requires>=50% overall and transition coverage and no accepted error>5pp in every campaign and separately P0 power. Candidate survives: **'+str(report['candidate_survives_frozen_usefulness_screen'])+'**. Accepted-subset errors for all three methods and six-block paired descriptive gains are in screen.json. Cohorts share references and chronology; no pooled significance or independent-risk claim is made.','',
            '## Boundary and costs','']
    for c in report['campaigns']:
        costs=c['cost'];slack=[r['cost']['target_boundary_slack_sec'] for r in c['rows']]
        spans=[r['cost']['probe_body_completion_span_sec'] for r in c['rows']]
        lines.append(f"- {c['name']}: {c['chronological_domain_flags']} body-timing domain flags; probe body completion span {min(spans):.3f}–{max(spans):.3f}s; minimum boundary slack {min(slack):.3f}s. Acquisition: {costs['acquired_calibration_measurement_offers']} calibration measurement +{costs['acquired_calibration_warmup_offers']} calibration warmup offers, +{costs['acquired_validation_initial_warmup_offers']} initial validation warmup offers, +{costs['consumed_continuous_probe_offers']} probe offers, with {costs['target_offers']} suffix offers evaluated.")
    lines+=['','100 scheduled offers occupy a12.5–25s window at8–4/s. The actual completion span is99 intervals plus completion, reported above. Qualification, settling, setup and inference/observer overhead add cost. Offline computing a forecast is not evidence of a deployed cost reduction.','',
            'The saved client emits its JSON after the whole300-offer cohort. BodyDoneNs precedes decompression/correctness checking, whose completion timestamp is not retained. The timestamp test therefore establishes body-timing availability for a hypothetical online observer, not a qualified live integrity/inference barrier. No service reset or traffic pause is inserted at the100/200 split. A future live design must qualify observation/correctness/inference without silently adding a pause that changes the population.','',
            '## Outcome interpretation','','A close first100/next200 match is evidence of within-cohort persistence for this cost and endpoint. It cannot certify a later unrelated deployment, a future state jump, production SLO compliance or a novel estimator. These are ordinary recent empirical forecasts. Cases with errors above tolerance remain retained; the probe guard cannot be declared reliable from its mean alone.','',
            '## Reproduction','','```bash','python3 -B analysis/screen_continuous_persistence.py --verify','python3 -B -m unittest discover -s analysis -p test_continuous_persistence.py -v','```','',
            'The verifier reconstructs permitted calibration from sealed raw files, checks the fixed100/200 all-offer split and timestamp boundary, reconciles unchanged300-offer results with previous reviews, and recomputes every score and hash. Tests exercise strict deadlines/failures, translation-free empirical forecasting, exact5pp boundaries, suffix-outcome isolation and insufficient probe coverage. Original experiments and manuscript gates remain intact.','']
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=compute();markdown=render(result)
    if args.verify:
        e.require(result==e.read(OUT/'screen.json'),'Persistence screen recomputation differs')
        e.require(markdown==(OUT/'report.md').read_text(),'Persistence report differs')
        for path,digest in e.read(OUT/'inputs_sha256.json').items():
            e.require(e.sha(ROOT/path)==digest,'Persistence consumed input changed: '+path)
        for path,digest in e.read(OUT/'seal.json').items():
            e.require(e.sha(ROOT/path)==digest,'Persistence output changed: '+path)
        print('Frozen100/200 design, raw seals, body-timing barriers, all54 cohorts, full300 reconciliation, exact scores and report recomputation verify.')
        return
    e.require(not (OUT/'screen.json').exists(),'Preserve completed persistence screen; use --verify')
    e.save(OUT/'screen.json',result);(OUT/'report.md').write_text(markdown)
    source_paths=[Path(__file__),Path(e.__file__),Path(model.__file__),ROOT/'analysis/test_continuous_persistence.py']
    e.save(OUT/'inputs_sha256.json',{**e.INPUTS,**{str(p.relative_to(ROOT)):e.sha(p) for p in source_paths}})
    e.save(OUT/'seal.json',{str(p.relative_to(ROOT)):e.sha(p) for p in
                          [OUT/'screen.json',OUT/'report.md',OUT/'inputs_sha256.json']})
    print(markdown)


if __name__=='__main__':main()
