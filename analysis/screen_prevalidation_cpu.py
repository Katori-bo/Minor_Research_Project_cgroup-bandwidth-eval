#!/usr/bin/env python3
"""Isolated warmup CPU shift feasibility; no new workloads or fitted thresholds."""
import argparse
from pathlib import Path
import statistics as st

import screen_forecast_reliability as e
import screen_prevalidation_shift as timing

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'analysis/runtime_io_prevalidation_cpu/20261010'


def counters(base, case, phase):
    record = e.sealed_read(case/f'{phase}-counters.json',base,'evidence-seal.json')
    before = e.sealed_read(case/f'{phase}-before.json',base,'evidence-seal.json')
    e.require(record['before'] == before, 'CPU baseline mismatch')
    e.require(record['delta'] == {k:record['after'][k]-v for k,v in before.items()},
              'CPU counter-delta mismatch')
    e.require(record['delta']['usage_usec'] > 0, 'Nonpositive CPU increment')
    return record['delta']


def cpu_features(reference,warmup,cpu_us,reference_cpu_us,deadline,throttle):
    delta = 1000*(cpu_us-reference_cpu_us)
    p0 = timing.miss(reference,deadline)
    pcpu = timing.miss(reference,deadline-delta)
    pw = timing.miss(warmup,deadline)
    score = abs(pcpu-p0)
    return dict(cpu_per_warmup_offer_us=cpu_us, reference_cpu_per_warmup_offer_us=reference_cpu_us,
                cpu_shift_ns=delta, cpu_change_pct=100*(cpu_us/reference_cpu_us-1),
                cpu_score_pp=score, predictions_pct=dict(reference=p0,recent25=pw,
                  pooled_update=timing.miss(reference+warmup,deadline),cpu_conditioned=pcpu),
                accepts=dict(always=True,cpu_shift=score<=5 and not throttle and
                  all(x is not None for x in reference+warmup),deadline_disagreement=abs(pw-p0)<=5),
                future_outcomes_used=False,risk_certificate=False)


def compute():
    e.INPUTS.clear()
    design=e.read(OUT/'design.json')
    for path,digest in e.read(OUT/'design_sha256.json').items():
        e.require(e.sha(ROOT/path)==digest,'CPU design changed')
        e.INPUTS[path]=digest
    campaigns=[]
    for folder,name,n in [('runtime_io_nginx_power_confirmation','NGINX power',24),
                          ('runtime_io_nginx_rate_transfer','NGINX rate',12)]:
        base=ROOT/'analysis'/folder/'generation-01/campaign'
        forecast=e.sealed_read(base/'forecast/forecast.json',base,'evidence-seal.json')
        cal=e.sealed_read(base/'calibration/summary.json',base,'evidence-seal.json')['rows']
        refs={};cpu_refs={}
        for row in cal:
            cfg=row['config']; key=cfg['policy'] if name=='NGINX power' else str(cfg['rate_rps'])
            case=base/f"calibration/cohort-{cfg['index']}"
            values,_=timing.nginx_values(case/'measurement.json',base,'measurement')
            warm,_=timing.nginx_values(case/'warmup.json',base,'warmup')
            cpu=counters(base,case,'warmup')
            e.require(cpu==row['warmup_counter_delta'],'Calibration warmup CPU mismatch')
            refs.setdefault(key,[]).extend(values)
            cpu_refs.setdefault(key,[]).append((cpu['usage_usec'],len(warm)))
        for key,ref in refs.items():
            saved=forecast['references'][key]
            e.require(sorted(x for x in ref if x is not None)==saved['successful_samples_ns'] and
                      sum(x is None for x in ref)==saved['failed_offers'],'CPU forecast reference mismatch')
        rows=[]
        for i in range(1,n+1):
            case=base/f'validation/cohort-{i}'
            cfg=e.sealed_read(case/'study-config.json',base,'evidence-seal.json')
            key=cfg['policy'] if name=='NGINX power' else '5'
            warm,span=timing.nginx_values(case/'warmup.json',base,'warmup')
            cpu=counters(base,case,'warmup')
            reference_cpu=sum(x[0] for x in cpu_refs[key])/sum(x[1] for x in cpu_refs[key])
            acquisition=e.sealed_read(case/'warmup-timing.json',base,'evidence-seal.json')
            start=e.sealed_read(case/'measurement-start.json',base,'evidence-seal.json')
            e.require(acquisition['finished_monotonic']<=start['monotonic'],'CPU warmup barrier')
            rows.append(dict(name=f'cohort-{i}',block=cfg['block'],profile=cfg['profile'],policy=cfg['policy'],
                             rate_rps=cfg['rate_rps'],features=cpu_features(refs[key],warm,
                               cpu['usage_usec']/len(warm),reference_cpu,forecast['primary_deadline_ns'],cpu['nr_throttled']),
                             cost=dict(reference_offers=len(refs[key]),reference_cpu_warmup_offers=sum(x[1] for x in cpu_refs[key]),
                               warmup_offers=len(warm),warmup_span_sec=span),case=case))
        campaigns.append(dict(name=name,base=base,deadline_ns=forecast['primary_deadline_ns'],rows=rows))
    # All CPU-based forecasts/flags exist before reading future measurement records or CPU increments.
    output=[]
    for campaign in campaigns:
        base=campaign.pop('base')
        for row in campaign['rows']:
            case=row.pop('case')
            values,_=timing.nginx_values(case/'measurement.json',base,'measurement')
            row['observed_miss_pct']=timing.miss(values,campaign['deadline_ns'])
            future=counters(base,case,'measurement')['usage_usec']/len(values)
            row['future_cpu_per_offer_us']=future
            row['future_minus_warmup_cpu_us']=future-row['features']['cpu_per_warmup_offer_us']
        scores=timing.summarize(campaign['rows'])
        output.append({**campaign,**scores,'policy_subgroups':{
          p:timing.summarize([r for r in campaign['rows'] if r['policy']==p])
          for p in sorted({r['policy'] for r in campaign['rows']})},
          'cpu_change_pct_range':[min(r['features']['cpu_change_pct'] for r in campaign['rows']),
                                  max(r['features']['cpu_change_pct'] for r in campaign['rows'])],
          'mean_future_minus_warmup_cpu_us':st.mean(r['future_minus_warmup_cpu_us'] for r in campaign['rows'])})
    prior=e.read(timing.OUT/'screen.json')['campaigns'][2:]
    for c,p in zip(output,prior):
        e.close(c['predictors']['reference']['mae_pp'],p['predictors']['reference']['mae_pp'])
    return dict(role=design['role'],features_computed_before_future_measurement_reads=True,
                new_collection=False,independent_validation=False,campaigns=output)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    ref=list(range(1,26));f=cpu_features(ref,[x+3 for x in ref],.013,.010,15,0)
    e.close(f['predictions_pct']['cpu_conditioned'],timing.miss([x+3 for x in ref],15))
    e.require(not cpu_features(ref,ref,.010,.010,15,1)['accepts']['cpu_shift'],'Throttle must abstain')
    result=compute()
    if args.verify:
        e.require(result==e.read(OUT/'screen.json'),'CPU screen recomputation differs')
        for path,digest in e.read(OUT/'inputs_sha256.json').items():
            e.require(e.sha(ROOT/path)==digest,'CPU consumed input changed: '+path)
        for path,digest in e.read(OUT/'screen_seal.json').items():
            e.require(e.sha(ROOT/path)==digest,'CPU output changed: '+path)
        print('CPU design, original seals/counter deltas, forecast barrier, shift/throttle oracles and recomputation verify.')
        return
    e.require(not (OUT/'screen.json').exists(),'Preserve CPU screen; use --verify')
    e.save(OUT/'screen.json',result)
    paths=[Path(__file__),Path(e.__file__),Path(timing.__file__)]
    e.save(OUT/'inputs_sha256.json',{**e.INPUTS,**{str(p.relative_to(ROOT)):e.sha(p) for p in paths}})
    e.save(OUT/'screen_seal.json',{str(p.relative_to(ROOT)):e.sha(p) for p in [OUT/'screen.json',OUT/'inputs_sha256.json']})
    for c in result['campaigns']:
        print(c['name'],'guards',c['guards'],'predictors',c['predictors'],'CPU change%',c['cpu_change_pct_range'])


if __name__=='__main__':main()
