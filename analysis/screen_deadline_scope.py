#!/usr/bin/env python3
"""Retrospective point-versus-CDF transfer experiment; no collection or fitting."""
import argparse
import bisect
from fractions import Fraction
import json
import math
from pathlib import Path
import statistics as st
import sys
import screen_forecast_reliability as e

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/runtime_io_deadline_scope/20261010'
sys.path.insert(0,str(ROOT/'diagnostic'))
import nginx_prediction_model as model


def pool(records):
    e.require(bool(records),'Empty all-offer pool')
    successes=sorted(r['e2e_ns'] for r in records if r['success'])
    e.require(all(isinstance(x,int) and x>=0 for x in successes),'Invalid latency')
    return dict(offers=len(records),successful_ns=successes,failed=len(records)-len(successes))


def miss(p,deadline):
    e.require(isinstance(deadline,int) and deadline>=0,'Finite integer deadline required')
    return Fraction(p['offers']-bisect.bisect_right(p['successful_ns'],deadline),p['offers'])


def panel(p):
    result=[]
    for q in (Fraction(1,10),Fraction(1,4),Fraction(1,2),Fraction(3,4),Fraction(9,10)):
        rank=math.floor(q*(p['offers']-1))
        result.append(dict(quantile=str(q),rank=rank,
            deadline_ns=p['successful_ns'][rank] if rank<len(p['successful_ns']) else None))
    return result


def discrepancy(a,b):
    # Step functions are constant between union support points. At D=0 and
    # after the largest finite point this also checks different failure mass.
    candidates=sorted(set([0]+a['successful_ns']+b['successful_ns']))
    maximum=Fraction(-1); where=None; signed=None
    for d in candidates:
        difference=miss(a,d)-miss(b,d)
        if abs(difference)>maximum:
            maximum=abs(difference);where=d;signed=difference
    return dict(maximum_pp=float(100*maximum),first_attaining_deadline_ns=where,
        signed_forecast_minus_observed_pp=float(100*signed),target_used_for_scoring_only=True)


def forecast(references,common_panel,deadline):
    # This function receives calibration only, never target records.
    return {name:dict(primary_miss_pct=float(100*miss(p,deadline)),
        panel=[dict(**d,miss_pct=float(100*miss(p,d['deadline_ns']))
             if d['deadline_ns'] is not None else None) for d in common_panel])
        for name,p in references.items()}


def summary(rows):
    methods=rows[0]['scores']
    result={}
    for method in methods:
        scores=[r['scores'][method] for r in rows]
        panel_errors=[d['error_pp'] for s in scores for d in s['panel'] if d['error_pp'] is not None]
        result[method]=dict(cohorts=len(rows),primary_mae_pp=st.mean(s['primary_error_pp'] for s in scores),
            primary_max_pp=max(s['primary_error_pp'] for s in scores),
            cdf_maximum_mean_pp=st.mean(s['cdf']['maximum_pp'] for s in scores),
            cdf_maximum_max_pp=max(s['cdf']['maximum_pp'] for s in scores),
            primary_within_5pp=sum(s['primary_error_pp']<=5+1e-10 for s in scores),
            primary_within_5pp_but_cdf_above_5pp=sum(s['primary_error_pp']<=5+1e-10 and
                s['cdf']['maximum_pp']>5+1e-10 for s in scores),
            panel_mae_pp=st.mean(panel_errors) if panel_errors else None,
            panel_max_pp=max(panel_errors) if panel_errors else None)
    return result


def compute():
    e.INPUTS.clear();design=e.read(OUT/'design.json')
    for path,digest in e.read(OUT/'design_sha256.json').items():
        e.require(e.sha(ROOT/path)==digest,'Analysis specification/source changed: '+path)
        e.INPUTS[path]=digest
    campaigns=[]
    for spec in design['campaigns']:
        base=ROOT/'analysis'/spec['folder']/'generation-01/campaign'
        read=lambda rel:e.sealed_read(base/rel,base,'evidence-seal.json')
        saved=read('forecast/forecast.json');historical=read('comparison.json')
        e.require(saved['primary_deadline_ns']==design['deadline_ns'] and not saved['validation_used'],
            'Foreign original forecast')
        groups={};calibration_offers=0;calibration_warmup=0
        for i in range(1,spec['calibration_cohorts']+1):
            rel=f'calibration/cohort-{i}';cfg=read(rel+'/study-config.json')
            measurement=model.outcomes(read(rel+'/measurement.json'),cfg,'measurement')
            warm=model.outcomes(read(rel+'/warmup.json'),cfg,'warmup')
            e.require(len(measurement)==400 and len(warm)==25,'Calibration conservation differs')
            key=cfg.get('policy','original') if spec['name']!='NGINX rate' else str(cfg['rate_rps'])
            groups.setdefault(key,[]).extend(measurement)
            calibration_offers+=len(measurement);calibration_warmup+=len(warm)
        pools={k:pool(v) for k,v in groups.items()};pooled=pool([r for v in groups.values() for r in v])
        if spec['name']=='NGINX original':
            e.require(pooled['successful_ns']==saved['sorted_samples_ns'] and pooled['offers']==saved['sample_count'],
                'Original calibration CDF differs')
        else:
            for k,p in pools.items():
                s=saved['references'][k]
                e.require(p['offers']==s['offers'] and p['failed']==s['failed_offers'] and
                    p['successful_ns']==s['successful_samples_ns'],'Calibration reference differs')
        rows=[]
        for i in range(1,spec['validation_cohorts']+1):
            rel=f'validation/cohort-{i}';cfg=read(rel+'/study-config.json')
            if spec['name']=='NGINX original':
                refs={'original':pooled};basis=pooled
            elif spec['name']=='NGINX power':
                refs={'pooled':pooled,'matched':pools[cfg['policy']],'baseline':pools['P0']}
                basis=pools[cfg['policy']]
            else:
                refs={'pooled':pooled,'matched':pools[str(cfg['rate_rps'])],'baseline':pools['5']}
                basis=pools['5']
            cutoffs=panel(basis);predictions=forecast(refs,cutoffs,design['deadline_ns'])
            target_records=model.outcomes(read(rel+'/measurement.json'),cfg,'measurement')
            warm=model.outcomes(read(rel+'/warmup.json'),cfg,'warmup')
            e.require(len(target_records)==300 and len(warm)==25,'Validation conservation differs')
            target=pool(target_records);result=read(rel+'/result.json')
            observed=float(100*miss(target,design['deadline_ns']));scores={}
            for name,reference in refs.items():
                p=predictions[name];curve=discrepancy(reference,target)
                errors=[]
                for d in p['panel']:
                    observed_panel=float(100*miss(target,d['deadline_ns'])) if d['deadline_ns'] is not None else None
                    errors.append(dict(**d,observed_pct=observed_panel,
                        error_pp=abs(d['miss_pct']-observed_panel) if observed_panel is not None else None))
                primary_error=abs(p['primary_miss_pct']-observed)
                e.require(curve['maximum_pp']+1e-10>=primary_error,'Primary exceeds full CDF supremum')
                scores[name]=dict(primary_prediction_pct=p['primary_miss_pct'],primary_error_pp=primary_error,
                    cdf=curve,panel=errors,reference_offers=reference['offers'])
                if spec['name']=='NGINX original':
                    e.close(p['primary_miss_pct'],100*historical['predicted_miss_fraction'])
                else:
                    prior=next(x for x in historical['primary']['errors'] if x['config']==cfg)
                    e.close(observed,100*prior['observed'])
                    e.close(p['primary_miss_pct'],100*prior['predictions'][name])
                    e.close(primary_error,prior['absolute_error_pp'][name])
            rows.append(dict(cohort=i,config=cfg,observed_primary_pct=observed,common_panel=cutoffs,
                target_offers=target['offers'],target_failures=target['failed'],scores=scores,
                observations=result.get('observations',result.get('domain_exits',[])),
                measurement_counter_delta=result.get('measurement_counter_delta')))
        e.require(len(rows)==spec['validation_cohorts'] and {r['config']['block'] for r in rows}==set(range(1,7)),
            'Incomplete chronological blocks')
        summed=summary(rows)
        if spec['name']=='NGINX original':e.close(summed['original']['primary_mae_pp'],historical['mean_block_mae_pp'])
        blocks=[dict(block=b,methods=summary([r for r in rows if r['config']['block']==b])) for b in range(1,7)]
        subgroups={}
        if spec['name']=='NGINX power':
            subgroups={p:summary([r for r in rows if r['config']['policy']==p]) for p in ('P0','P1')}
        elif spec['name']=='NGINX rate':
            subgroups={str(p):summary([r for r in rows if r['config']['rate_rps']==p]) for p in (4,8)}
        gains=[]
        if 'matched' in summed:
            comparator='pooled' if spec['name']=='NGINX power' else 'baseline'
            gains=[dict(block=b['block'],comparator=comparator,
                primary_gain_pp=b['methods'][comparator]['primary_mae_pp']-b['methods']['matched']['primary_mae_pp'],
                cdf_gain_pp=b['methods'][comparator]['cdf_maximum_mean_pp']-b['methods']['matched']['cdf_maximum_mean_pp'],
                panel_gain_pp=b['methods'][comparator]['panel_mae_pp']-b['methods']['matched']['panel_mae_pp']) for b in blocks]
        campaigns.append(dict(name=spec['name'],rows=rows,methods=summed,blocks=blocks,subgroups=subgroups,
            descriptive_paired_gains=gains,calibration_offers=calibration_offers,calibration_warmup_offers=calibration_warmup,
            validation_offers=300*len(rows),validation_warmup_offers=25*len(rows)))
    return dict(role=design['role'],all54_cohorts_retained=True,manuscript_changed=False,new_collection=False,
        independent_confirmation=False,novelty_established=False,causal_mechanism_identified=False,
        full_cdf_metrics='Finite empirical sub-CDF differences, not a population confidence statement or a forecast at an outcome-selected deadline',
        primary_deadline_ns=design['deadline_ns'],campaigns=campaigns)


def render(result):
    lines=['# Deadline scope: retrospective distribution-transfer experiment','','10 October 2026. Complete saved records; known development outcomes, no new traffic or independent confirmation.','',
        '| Campaign / method | Cohorts | Primary MAE (pp) | Mean empirical CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for campaign in result['campaigns']:
        for name,m in campaign['methods'].items():
            lines.append(f"| {campaign['name']} / {name} | {m['cohorts']} | {m['primary_mae_pp']:.3f} | {m['cdf_maximum_mean_pp']:.3f} | {m['cdf_maximum_max_pp']:.3f} | {m['primary_within_5pp_but_cdf_above_5pp']}/{m['primary_within_5pp']} | {m['panel_mae_pp']:.3f} |")
    lines+=['','Primary is the unchanged 20.565395 ms cutoff. The count denominator is the number of cohorts with primary error <=5 pp, not all cohorts. This is a scope diagnostic; the historical primary acceptance decisions remain unchanged.','',
        'Panel deadlines are calibration-only 10/25/50/75/90% lower order statistics, with one common panel per cohort/method comparison. Power panels use the assigned-policy reference, rate panels the ordinary5/s reference. CDF maxima inspect all finite cutoffs; attaining locations are retrospective diagnostics, never newly selected operational deadlines. Failure mass is retained.','',
        '## Policy and rate subgroups','']
    for campaign in result['campaigns']:
        for group,methods in campaign['subgroups'].items():
            lines.append(f"### {campaign['name']} / {group}")
            lines+=['','| Method | Primary MAE (pp) | Mean CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |','|---|---:|---:|---:|---:|---:|']
            for name,m in methods.items():
                lines.append(f"| {name} | {m['primary_mae_pp']:.3f} | {m['cdf_maximum_mean_pp']:.3f} | {m['cdf_maximum_max_pp']:.3f} | {m['primary_within_5pp_but_cdf_above_5pp']}/{m['primary_within_5pp']} | {m['panel_mae_pp']:.3f} |")
            lines.append('')
    lines+=['## Descriptive block gains','','Positive means smaller error for matching. No new significance or advantage decision is made; these six blocks share one host and calibration references.','']
    for campaign in result['campaigns']:
        if campaign['descriptive_paired_gains']:
            gains=campaign['descriptive_paired_gains']
            lines.append(f"{campaign['name']}, matched versus {gains[0]['comparator']}: mean primary gain {st.mean(x['primary_gain_pp'] for x in gains):.3f} pp; mean CDF-maximum gain {st.mean(x['cdf_gain_pp'] for x in gains):.3f} pp; mean panel gain {st.mean(x['panel_gain_pp'] for x in gains):.3f} pp.")
            lines.append('')
    lines+=['## Limits and disposition','','These are discrepancies between two finite empirical distributions, including sampling noise. They do not identify latent-distribution error, causality or future reliability. Calibration quantiles are exploratory questions selected after historical outcomes were known. Every cohort and throttling observation is retained; no new deadline, threshold or model was tuned. Full original acquisition, warmup, qualification, settling and startup costs remain charged.','',
        'The scientific result is a more precise assessment of deadline-specific versus distribution-wide empirical agreement. Any stronger all-deadline prediction claim requires a separately declared fresh evaluation. No live experiment or manuscript update is selected by this screen; worker-wait collection remains held and the friend-owned V31 remains pending.','',
        'Complete per-cohort cutoffs, forecasts, empirical suprema, observations and six-block summaries are in screen.json. The frozen specification and verification receipts preserve the analysis.']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=compute();report=render(result)
    if args.verify:
        e.require(e.read(OUT/'screen.json')==result,'Saved scope metrics differ')
        e.require((OUT/'report.md').read_text()==report,'Saved scope report differs')
        for name,digest in e.read(OUT/'inputs_sha256.json').items():
            e.require(e.sha(ROOT/name)==digest,'Saved input changed: '+name)
        if (OUT/'seal.json').exists():
            for name,digest in e.read(OUT/'seal.json')['files_sha256'].items():
                e.require(e.sha(OUT/name)==digest,'Saved artifact changed: '+name)
        print('All 54 cohorts, original primary forecasts and deadline-scope analysis verify; no collection.')
    else:
        e.require(not (OUT/'screen.json').exists(),'No overwrite or favorable rerun')
        e.save(OUT/'screen.json',result);e.save(OUT/'inputs_sha256.json',dict(e.INPUTS))
        (OUT/'report.md').write_text(report)
        print(report)


if __name__=='__main__':main()
