"""Additional ordinary baseline: isolated processing speed plus busy throughput.

Both parameters come from V29 calibration; all results remain retrospective.
"""
import argparse
import math
from pathlib import Path
import statistics as st
from compare_v29_timing_models import ROOT,c,calibration_delays,DEADLINES,PHASES
from periodic_budget_model import replay,misses,delayed_misses


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.absolute()
    if out.parent!=ROOT/'analysis/runtime_io_v2_extension' or out.exists():raise ValueError('new extension directory required')
    first=ROOT/'analysis/runtime_io_v2_extension/20261009-v29-ordinary-models';c.verify_seal(first)
    previous=c.read(first/'report.json');combined=c.read(ROOT/'analysis/runtime_io_v29_result_review/20261009-complete-matrix/report.json')
    inputs={str(first.relative_to(ROOT))+'/seal.json':c.digest(first/'seal.json')}
    def read(path):inputs[str(path.relative_to(ROOT))]=c.digest(path);return c.read(path)
    for name in ('compare_v29_two_rate_models.py','compare_v29_timing_models.py','periodic_budget_model.py'):
        path=ROOT/'analysis'/name;inputs[str(path.relative_to(ROOT))]=c.digest(path)
    out.mkdir();contexts={};forecasts={}
    c.save(out/'contract.json',dict(status='retrospective_discovery_only',worker_time='median low-rate calibration processing-wall interval, queue <=100us; not isolated CPU demand',
        capacity='unchanged independently calibrated busy throughput',budget='effective worker wall-service budget B=P*capacity*worker_time; reject B>configured Q',
        assumptions='periodic worker availability, instantaneous on-speed inferred from lightly loaded processing; no verified phase or guarantee',
        models=['zero_phase_full_budget','uniform_phase','uniform_phase_with_independent_calibrated_delay'],phases_sec=PHASES,validation_residual_fitting=False))
    for key,selected in combined['contexts'].items():
        session=ROOT/'analysis/runtime_io_v29'/key/selected['generation'];report=read(Path(selected['report_path']))
        manifest=read(session/'bundle/manifest.json');configs={x['trial']:x for x in manifest['matrix']}
        entries=[];workers=[]
        for trial,ref in report['trial_refs'].items():
            cfg=configs[trial]
            if cfg['role']=='validation':continue
            directory=session/ref['path'];c.verify_seal(directory);derived=read(directory/'derived.json');entries.append((cfg,derived))
            if cfg['role']=='steady' and cfg['reference_low_rate'] in (15,30):
                workers.extend(r['processing_wall_ns']/1e9 for r in derived['requests'] if r['success'] and r['queue_ns']<=100000)
        delays,cal_trials=calibration_delays(entries);processing=st.median(workers)
        capacity=report['calibration']['methods']['busy']['capacity_rps'];cfg=next(iter(configs.values()))
        period=cfg['period_us']/1e6;quota=cfg['quota_us']/1e6;budget=period*capacity*processing
        if not 0<budget<=quota:raise ValueError('effective worker supply exceeds configured CPU ceiling; baseline unavailable')
        predictions={};observed={}
        for cfg in manifest['matrix']:
            if cfg['role']!='validation':continue
            trial=cfg['trial'];print(key+' '+trial+': two-rate discovery replay',flush=True)
            offers=read(session/'bundle/compiled_vectors'/(trial+'_measurement.json'));raw=[];delayed=[]
            for phase in PHASES:
                lat=replay(offers,capacity,budget,period,phase,1.)
                raw.append(misses(lat,DEADLINES));delayed.append(delayed_misses(lat,delays,DEADLINES))
            predictions[trial]=dict(zero_phase_full_budget=raw[0],uniform_phase={str(ms):st.mean(g[str(ms)] for g in raw) for ms in DEADLINES},
                uniform_phase_with_calibrated_delay={str(ms):st.mean(g[str(ms)] for g in delayed) for ms in DEADLINES})
            directory=session/report['trial_refs'][trial]['path'];c.verify_seal(directory);derived=read(directory/'derived.json')
            observed[trial]={str(ms):100*sum(not r['success'] or r['e2e_ns']>ms*1000000 for r in derived['requests'])/len(offers) for ms in DEADLINES}
        methods={name:{str(ms):dict(mae_pp=st.mean(abs(p[name][str(ms)]-observed[trial][str(ms)]) for trial,p in predictions.items()),
            maximum_error_pp=max(abs(p[name][str(ms)]-observed[trial][str(ms)]) for trial,p in predictions.items())) for ms in DEADLINES} for name in next(iter(predictions.values()))}
        contexts[key]=dict(worker_time_ms=processing*1000,worker_samples=len(workers),effective_worker_budget_ms=budget*1000,
            configured_quota_ms=quota*1000,busy_capacity_rps=capacity,calibration_delay_trials=cal_trials,methods=methods,
            previous_models=previous['contexts'][key]['methods'])
        forecasts[key]=dict(predictions=predictions,observed=observed)
    if any(c.digest(ROOT/name)!=h for name,h in inputs.items()):raise ValueError('consumed input changed')
    c.save(out/'report.json',dict(status='two_rate_ordinary_model_discovery_complete',contexts=contexts,prospective_validation=False,
        phase_measured=False,novelty_established=False,interpretation='Two calibrated worker-service parameters tested; effective budget is not a measured kernel budget or lower CPU-service guarantee.'))
    c.save(out/'forecasts.json',forecasts);c.save(out/'input_hashes.json',inputs)
    for name in ('compare_v29_two_rate_models.py','compare_v29_timing_models.py','periodic_budget_model.py'):(out/name).write_bytes((ROOT/'analysis'/name).read_bytes())
    lines=['# Two-rate periodic worker baseline','','All results are retrospective discovery. Median low-rate worker processing wall time and independent busy throughput define effective worker availability. This is a calibrated wall-service approximation, not isolated CPU-demand measurement or a kernel supply guarantee. No validation residual or phase is fitted.','','| Context | Worker time ms | Effective budget ms | Model | 25 ms MAE pp | 50 ms MAE pp | 100 ms MAE pp | 500 ms MAE pp |','|---|---:|---:|---|---:|---:|---:|---:|']
    for key,v in contexts.items():
        for name,g in v['methods'].items():lines.append(f"| {key} | {v['worker_time_ms']:.3f} | {v['effective_worker_budget_ms']:.3f} | {name} | "+' | '.join(f"{g[str(ms)]['mae_pp']:.3f}" for ms in (25,50,100,500))+' |')
    lines+=['','The effective budget B=P*busy_capacity*worker_time preserves the calibrated long-run capacity and must not exceed the configured quota. It represents worker wall-service availability; runtime and other service CPU demands are not separately measured. Unknown phase is averaged uniformly, not observed or selected as an oracle. Independent response delay is appended from the same four low-rate calibration trials. These choices were examined after V29 outcomes and require fresh confirmation.']
    (out/'report.md').write_text('\n'.join(lines)+'\n');c.seal(out);print('Two-rate discovery complete: '+str(out/'report.md'),flush=True)


if __name__=='__main__':main()
