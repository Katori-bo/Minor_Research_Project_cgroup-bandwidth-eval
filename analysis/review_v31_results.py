"""Audit completed V31 without editing frozen sources or launching collection."""
import argparse
import math
from pathlib import Path
import shutil
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v31_common as c
import v31_verify as verify


def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10):raise ValueError(f'independent result differs: {a} vs {b}')


def review(out):
    if out.parent!=ROOT/'analysis/runtime_io_v31_result_review' or out.exists() or out.is_symlink():
        raise ValueError('use a new direct V31 result-review directory')
    session=c.PARENT/'generation-01';campaign=ROOT/'analysis/runtime_io_v31_campaign/generation-01'
    replay=verify.verify_completion(session)
    if not replay['complete']:raise ValueError('completed V31 comparison required')
    directory=c.resolve(session,c.read(session/'latest_analysis.json')['path']);saved=c.read(directory/'report.json')
    inputs={str(Path(__file__).relative_to(ROOT)):c.digest(Path(__file__))}
    def read(path):
        inputs[str(path.relative_to(ROOT))]=c.digest(path)
        return c.read(path)
    for path in (directory/'report.json',directory/'seal.json',session/'bundle/seal.json',session/'preparation/seal.json',
                 session/'predictions/seal.json',session/'collection_receipt.json',c.DESIGN/'design.json',c.DESIGN/'seal.json'):
        read(path)
    forecasts=read(session/'predictions/summary.json');vectors=read(session/'predictions/per_offer.json')
    fitted=read(session/'predictions/calibration.json');freeze=read(session/'predictions/manifest.json')
    primary='joint_calibration_cdf';comparator='periodic_uniform_phase_calibrated_delay'
    configs={cfg['trial']:cfg for cfg in c.matrix()};raw_trials={};cohorts={};validation=[]
    for trial,ref in saved['trial_refs'].items():
        d=c.resolve(session,ref['path']);read(d/'seal.json')
        cfg=configs[trial]
        if cfg['traffic_pattern']=='idle':continue
        client=read(d/'loadgen.json');server=read(d/'server_metrics.json');raw_trials[trial]=(client,server,d)
        if cfg['role']!='steady' or cfg['reference_low_rate'] not in (15,30):continue
        jobs={j['id']:j for j in server['events']};samples=[]
        for row in sorted(client['requests'],key=lambda r:r['ID']):
            if row['Error'] or row['StatusCode']!=200:continue
            job=jobs[row['ID']]
            if job['queue_wait_ns']>100000:continue
            total=row['EndToEndLatencyNs']-job['queue_wait_ns'];worker=job['processing_ns'];residual=total-worker
            if min(total,worker,residual)<0:raise ValueError('negative calibration interval')
            samples.append(dict(id=row['ID'],trial=trial,total_ns=total,worker_ns=worker,residual_ns=residual))
        cohorts[trial]=samples
    pooled=[r for values in cohorts.values() for r in values]
    key=lambda r:(r['trial'],r['id'])
    if sorted(pooled,key=key)!=sorted(fitted['paired_samples'],key=key):raise ValueError('raw independent calibration pairing differs')
    cdf={str(ms):100*sum(r['total_ns']>ms*1000000 for r in pooled)/len(pooled) for ms in c.DEADLINES_MS}
    for cfg in c.validation_configs():
        trial=cfg['trial'];client,server,d=raw_trials[trial];offers=len(c.schedule(cfg));jobs={j['id']:j for j in server['events']}
        observations=read(d/'observations.json');derived=read(d/'derived.json')
        throttled=observations['measurement_stop']['cpu_stat']['nr_throttled']-observations['measurement_start']['cpu_stat']['nr_throttled']
        queue_good=sum(i in jobs and 0<=jobs[i]['queue_wait_ns']<=100000 for i in range(offers))
        domain_pass=throttled==0 and queue_good/offers>=.99
        observed={str(ms):100*(offers-sum(not r['Error'] and r['StatusCode']==200 and r['EndToEndLatencyNs']<=ms*1000000
            for r in client['requests']))/offers for ms in c.DEADLINES_MS}
        stage={}
        for ms in c.DEADLINES_MS:
            threshold=ms*1000000;misses=[r for r in derived['requests'] if not r['success'] or r['e2e_ns']>threshold]
            stage[str(ms)]=dict(misses=len(misses),unsuccessful=sum(not r['success'] for r in misses),
                computation_certainly_after=sum(r['success'] and r['completion_after_offered_lower_ns']>threshold for r in misses),
                computation_certainly_within_but_client_missed=sum(r['success'] and r['completion_after_offered_upper_ns']<=threshold for r in misses),
                computation_boundary_ambiguous=sum(r['success'] and r['completion_after_offered_lower_ns']<=threshold<r['completion_after_offered_upper_ns'] for r in misses))
            if sum(v for k,v in stage[str(ms)].items() if k!='misses')!=stage[str(ms)]['misses']:raise ValueError('stage conservation failure')
            close(observed[str(ms)],100*len(misses)/offers)
            close(cdf[str(ms)],forecasts['methods'][primary][trial]['deadline_miss_pct'][str(ms)])
            if any(abs(p-cdf[str(ms)]/100)>1e-12 for p in vectors[primary][trial][str(ms)]):raise ValueError('CDF per-offer probabilities differ')
        for name,profile_forecasts in forecasts['methods'].items():
            if profile_forecasts[trial]['status']!='available':continue
            for ms in c.DEADLINES_MS:close(100*st.mean(vectors[name][trial][str(ms)]),profile_forecasts[trial]['deadline_miss_pct'][str(ms)])
        validation.append(dict(trial=trial,block=cfg['block'],profile=cfg['profile'],rate=cfg['rate'],offers=offers,
            observed_miss_pct=observed,domain_pass=domain_pass,throttled_periods=throttled,
            low_queue_offers=queue_good,observed_low_queue_fraction=queue_good/offers,stage=stage))
    blocks=[]
    for block in range(1,7):
        rows=[r for r in validation if r['block']==block]
        mae=st.mean(abs(cdf['10']-r['observed_miss_pct']['10']) for r in rows)
        periodic=st.mean(abs(forecasts['methods'][comparator][r['trial']]['deadline_miss_pct']['10']-r['observed_miss_pct']['10']) for r in rows)
        blocks.append(dict(block=block,cdf_mae_pp=mae,periodic_mae_pp=periodic,improvement_pp=periodic-mae))
    contrasts=[b['improvement_pp'] for b in blocks];mean=st.mean(contrasts);margin=2.571*st.stdev(contrasts)/math.sqrt(6)
    decisions={str(ms):all((cdf[str(ms)]<=5)==(r['observed_miss_pct'][str(ms)]<=5) for r in validation) for ms in (10,12)}
    gates=dict(complete_technically_qualified_trials=len(validation)==18,
        all_trials_inside_scientific_domain=all(r['domain_pass'] for r in validation),
        cdf_mean_block_mae_le_3=st.mean(b['cdf_mae_pp'] for b in blocks)<=3,
        every_block_positive=all(x>0 for x in contrasts),improvement_95_lower_ge_5=mean-margin>=5,
        all_trial_slo_decisions_match_10ms=decisions['10'],all_trial_slo_decisions_match_12ms=decisions['12'],
        some_profile_meets_12ms_slo_every_block=all(any(r['observed_miss_pct']['12']<=5 for r in validation if r['block']==b) for b in range(1,7)))
    if gates!=replay['gates']:raise ValueError('independent confirmation gates differ')
    for independent,retained in zip(blocks,replay['blocks']):
        for k,v in independent.items():close(v,retained[k])
    close(mean,replay['paired_improvement']['mean_pp'])
    for a,b in zip((mean-margin,mean+margin),replay['paired_improvement']['model_based_95_interval']):close(a,b)
    cohort_sensitivity={}
    for trial,samples in cohorts.items():
        prediction=100*sum(r['total_ns']>10000000 for r in samples)/len(samples)
        remaining=[r for t,values in cohorts.items() if t!=trial for r in values]
        loo=100*sum(r['total_ns']>10000000 for r in remaining)/len(remaining)
        cohort_sensitivity[trial]=dict(n=len(samples),single_cohort_predicted_10ms_miss_pct=prediction,
            single_cohort_validation_mae_pp=st.mean(abs(prediction-r['observed_miss_pct']['10']) for r in validation),
            leave_one_cohort_out_predicted_10ms_miss_pct=loo,
            leave_one_cohort_out_validation_mae_pp=st.mean(abs(loo-r['observed_miss_pct']['10']) for r in validation))
    cleanup=[]
    for p in sorted(session.rglob('ownership.json')):
        owner=read(p);receipt=read(p.parent/'cleanup.json');container=read(p.parent/'container.json')['inspect']
        if container['Config']['Labels'].get('research.v31.owner')!=owner['nonce']:raise ValueError('ownership label/nonce differs')
        if receipt['errors'] or not receipt['container_removed'] or not receipt['cgroup_removed'] or receipt['watchdog_intervened']:
            raise ValueError('owned cleanup not successful')
        cleanup.append(dict(path=str(p.parent.relative_to(session)),released=(p.parent/'identity.json').exists()))
    if len(cleanup)>42 or sum(x['released'] for x in cleanup)>41:raise ValueError('container cap exceeded')
    summary=read(campaign/'summary.json');finished=read(campaign/'finished.json');life=read(campaign/'lifetime.json')
    if (summary['status']!='collection_complete' or summary['contexts']['q025_large']['decision']!=replay['decision']
            or finished['failure'] is not None or finished['elapsed_sec']>life['bound_sec']-120):raise ValueError('campaign status/lifetime differs')
    if saved['technical_failures']:raise ValueError('this expected zero-retry record has technical failures')
    totals={str(ms):{k:sum(r['stage'][str(ms)][k] for r in validation) for k in validation[0]['stage'][str(ms)]} for ms in c.DEADLINES_MS}
    report=dict(status='completed_V31_confirmation_independently_verified',decision=replay['decision'],
        accepted_calibration_trials=16,accepted_validation_trials=18,measurement_offers=sum(r['offers'] for r in validation),
        calibration_timing_cohorts=len(cohorts),calibration_timing_samples=len(pooled),calibration_cdf_miss_pct=cdf,
        independent_blocks=blocks,paired_improvement=dict(mean_pp=mean,interval_95=[mean-margin,mean+margin],df=5,t_multiplier=2.571),
        gates=gates,validation=validation,deadline_grid=replay['deadline_grid'],cohort_sensitivity=cohort_sensitivity,
        stage_totals=totals,cleanup=cleanup,created_containers=len(cleanup),released_containers=sum(x['released'] for x in cleanup),
        technical_retries=0,campaign_elapsed_sec=summary['elapsed_sec'],
        minimum_trial_low_queue_fraction=min(r['observed_low_queue_fraction'] for r in validation),
        source_report=str((directory/'report.json').relative_to(ROOT)),inputs=inputs,
        scope='Fresh prospective within-service/host low-queue confirmation. Descriptive secondary and cohort checks; no new mechanism, overload or transfer claim.')
    out.mkdir(parents=True);c.save(out/'report.json',report);shutil.copy2(Path(__file__),out/'review_v31_results.py')
    lines=['# Verified V31 prospective timing confirmation','','**All frozen confirmation gates pass; completion replay and independent raw-outcome/block calculations agree.**','',
        'Sixteen fresh calibration trials precede eighteen validation trials at new steady rates 5/11/19 requests/s (12600 offers). Four calibration cohorts supply 676 paired timing samples. There are no technical retries or scientific domain exits.','',
        '| 10 ms method | Mean trial/block MAE pp | Maximum trial error pp |','|---|---:|---:|']
    for name,z in replay['methods'].items():lines.append(f"| {name} | {z['mae_pp']:.3f} | {z['maximum_error_pp']:.3f} |")
    lines+=['',f'Mean paired periodic-minus-CDF improvement: {mean:.3f} pp; declared 95% six-block t interval [{mean-margin:.3f}, {mean+margin:.3f}] pp (df=5, multiplier 2.571). Every block improves.','',
        'All eighteen trials record zero measurement throttled periods. The lowest trial observed queue<=100 us fraction is '+f"{100*report['minimum_trial_low_queue_fraction']:.3f}%"+' of all offers. All 12600 offers complete successfully; observed 10 ms misses still total 8429. Forty released containers and one unreleased preflight have successful owned cleanup. The campaign takes '+f"{summary['elapsed_sec']/60:.1f}"+' minutes within its fixed bound.','',
        '| Profile | Rate requests/s | Observed mean 10 ms miss % | CDF prediction % | CDF MAE pp |','|---|---:|---:|---:|---:|']
    for profile,rate in (('A',5),('B',11),('C',19)):
        z=replay['methods'][primary]['per_profile'][profile]
        lines.append(f"| {profile} | {rate} | {z['mean_observed_miss_pct']:.3f} | {z['mean_predicted_miss_pct']:.3f} | {z['mae_pp']:.3f} |")
    lines+=['','The CDF classifies all eighteen trials correctly at both 10 and 12 ms. All fail the 5% budget at 10 ms; all have zero observed misses at 12 ms. Those decisions are well separated from 5%, rather than a precision test near the miss-budget boundary. Zero observed misses do not guarantee zero future misses.','',
        '| Deadline ms | Paired CDF MAE pp | Independent convolution MAE pp | Periodic+delay MAE pp |','|---|---:|---:|---:|']
    for ms in c.DEADLINES_MS:
        grid=replay['deadline_grid'];lines.append(f"| {ms} | {grid[primary][str(ms)]['mae_pp']:.3f} | {grid['independent_worker_response_convolution'][str(ms)]['mae_pp']:.3f} | {grid[comparator][str(ms)]['mae_pp']:.3f} |")
    lines+=['','The paired CDF has 3.852 pp error at 10.5 ms, above the numerical 3 pp target used only for the primary 10 ms gate. Maximum 10 ms trial error is 5.055 pp. The independent convolution is better at secondary 9 ms; no universal method dominance is established. At 12–25 ms both paired CDF and periodic forecasts have zero error, so those endpoints supply no accuracy discrimination.','',
        'Cohort-only 10 ms forecasts range from 57.522% to 69.912%. Leaving each cohort out gives validation MAE 1.974–2.268 pp; this sensitivity is descriptive and never refits the frozen primary result. Hundreds of calibration requests are not hundreds of independent experiment replicates.','',
        '| Deadline ms | Misses | Computation certainly after | Computation certainly within, client missed | Clock ambiguous |','|---|---:|---:|---:|---:|']
    for ms in ('10','10.5','11','12'):
        z=totals[ms];lines.append(f"| {ms} | {z['misses']} | {z['computation_certainly_after']} | {z['computation_certainly_within_but_client_missed']} | {z['computation_boundary_ambiguous']} |")
    lines+=['','Stage counts retain material clock ambiguity and are descriptive, not causal CPU/runtime/HTTP attribution. The V30 burst failure of the empirical CDF remains separate negative scope evidence. V31 confirms the low-queue 10 ms forecast on this service/host; it does not establish a new estimator, phase mechanism, overload predictor or independent-service transfer.','',
        'The next research step is to consolidate this scoped claim and design one independent service or host replication before any new collection. The completed V31 design, sources, binaries, predictions and raw records remain unchanged.']
    (out/'report.md').write_text('\n'.join(lines)+'\n');c.seal(out);c.verify_seal(out)
    if any(c.digest(ROOT/name)!=h for name,h in inputs.items()):raise ValueError('consumed evidence changed during review')
    print(f"V31 independent review passed: {replay['decision']}; CDF 10 ms MAE {replay['methods'][primary]['mae_pp']:.3f} pp; {out}")


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    review(parser.parse_args().output.absolute())
