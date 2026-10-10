"""Retrospective Stage A: calibration-only ordinary timing model comparison.

No kernel phase measurement, fresh validation, or service experiment is implied.
"""
import argparse
import math
from pathlib import Path
import statistics as st
import sys
from periodic_budget_model import replay,misses,delayed_misses

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v29_common as c

DEADLINES=(25,50,100,200,500,1000)
PHASES=tuple(i*.001 for i in range(100))
BALANCES=(0.,1.)


def calibration_delays(entries):
    delays=[];trials=[]
    for cfg,derived in entries:
        if cfg['role']=='validation':raise ValueError('validation cannot supply delay parameters')
        if cfg['role']!='steady' or cfg['reference_low_rate'] not in (15,30):continue
        trials.append(cfg['trial'])
        for r in derived['requests']:
            if not r['success'] or r['queue_ns']>100000:continue
            value=r['e2e_ns']-r['queue_ns']-r['processing_wall_ns']
            if value<0:raise ValueError('calibrated non-queue delay is negative')
            delays.append(value/1e9)
    if len(trials)!=4 or not delays:raise ValueError('four independent low-rate calibration trials required')
    return sorted(delays),trials


def percentile(values,q):return sorted(values)[max(0,math.ceil(len(values)*q)-1)]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();out=args.output.absolute()
    if out.parent!=ROOT/'analysis/runtime_io_v2_extension' or out.exists() or out.is_symlink():
        raise ValueError('Use a new direct extension report directory')
    source=ROOT/'analysis/runtime_io_v29_result_review/20261009-complete-matrix'
    c.verify_seal(source);combined=c.read(source/'report.json');inputs={}
    def track(path):
        inputs[str(path.relative_to(ROOT))]=c.digest(path)
    def checked(path):track(path);return c.read(path)
    track(source/'seal.json');track(source/'report.json')
    for path in (Path(__file__),ROOT/'analysis/periodic_budget_model.py',ROOT/'analysis/test_periodic_budget_model.py'):
        track(path)
    out.mkdir()
    c.save(out/'contract.json',dict(status='retrospective_discovery_only',deadlines_ms=DEADLINES,
        phase_grid_sec=PHASES,initial_balances=BALANCES,capacity_range='min/max of four calibration busy-throughput bounds',
        periodic_demand='(quota/period)/busy_capacity, an effective whole-service CPU demand',
        delay='Empirical e2e-minus-queue-minus-processing distribution from four low-rate calibration trials; queue<=100us',
        unknown_phase_prediction='Uniform average over the 100 sampled shared phases, full initial balance; assumed prior, not measured phase',
        envelope='Sampled model-scenario range over phases, full/empty initial balances and calibration capacity extremes; neither continuous bound nor Linux guarantee',
        queue='One job in service plus 128 waiting; failures/rejections count in all-offer denominator',
        budget='Work-conserving consumption; replenish to Q at boundaries; unused global budget discarded, no local slice carry or multi-thread competition',
        validation_residual_fitting=False,phase_oracle_selection=False,novel_algorithm=False))
    contexts={};all_rows=[];forecasts={}
    for key,selected in combined['contexts'].items():
        session=ROOT/'analysis/runtime_io_v29'/key/selected['generation']
        report_path=Path(selected['report_path']);c.verify_seal(report_path.parent);report=checked(report_path)
        c.verify_seal(session/'bundle');manifest=checked(session/'bundle/manifest.json')
        c.verify_seal(session/'predictions');frozen=checked(session/'predictions/per_offer.json')
        track(session/'predictions/seal.json')
        configs={cfg['trial']:cfg for cfg in manifest['matrix']}
        cal_entries=[]
        for trial,ref in report['trial_refs'].items():
            if configs[trial]['role']=='validation':continue
            d=session/ref['path'];c.verify_seal(d)
            if c.digest(d/'seal.json')!=ref['seal']:raise ValueError('calibration trial seal differs')
            track(d/'seal.json');cal_entries.append((configs[trial],checked(d/'derived.json')))
        delays,delay_trials=calibration_delays(cal_entries)
        busy=report['calibration']['methods']['busy']['capacity_rps']
        quadratic=report['calibration']['methods']['quadratic']['capacity_rps']
        cal_mixed=[r for r in report['trial_accounting'] if r['role']=='mixed']
        lower=min(r['busy_capacity_bounds_rps'][0] for r in cal_mixed)
        upper=max(r['busy_capacity_bounds_rps'][1] for r in cal_mixed)
        capacities=sorted(set((lower,busy,upper)))
        first=next(iter(configs.values()));quota=first['quota_us']/1e6;period=first['period_us']/1e6
        parameters=dict(busy_capacity_rps=busy,quadratic_capacity_rps=quadratic,
            capacity_sensitivity_rps=[lower,upper],effective_demand_ms=1000*(quota/period)/busy,
            calibration_delay_trials=delay_trials,delay_samples=len(delays),
            delay_mean_ms=st.mean(delays)*1000,delay_p50_ms=percentile(delays,.5)*1000,
            delay_p95_ms=percentile(delays,.95)*1000,quota_ms=quota*1000,period_ms=period*1000)
        context_rows=[];predictions={}
        for cfg in manifest['matrix']:
            if cfg['role']!='validation':continue
            trial=cfg['trial'];print(key+' '+trial+': periodic phase/budget/capacity scenarios',flush=True)
            path=session/'bundle/compiled_vectors'/(trial+'_measurement.json');offers=checked(path)
            base={method:[None if r['rejected'] else r['latency_sec'] for r in frozen[method][trial]]
                  for method in ('busy','quadratic')}
            pred=dict(fluid_busy=misses(base['busy'],DEADLINES),fluid_quadratic=misses(base['quadratic'],DEADLINES),
                      fluid_busy_calibrated_delay=delayed_misses(base['busy'],delays,DEADLINES))
            envelope={str(ms):[100.,0.] for ms in DEADLINES};phase_values=[];phase_delay_values=[]
            for capacity in capacities:
                for initial in BALANCES:
                    for phase in PHASES:
                        lat=replay(offers,capacity,quota,period,phase,initial)
                        grid=misses(lat,DEADLINES)
                        for ms,g in grid.items():envelope[ms]=[min(envelope[ms][0],g),max(envelope[ms][1],g)]
                        if capacity==busy and initial==1.:
                            phase_values.append(grid);phase_delay_values.append(delayed_misses(lat,delays,DEADLINES))
                            if phase==0.:pred['periodic_zero_phase_full_budget']=grid
            pred['periodic_uniform_phase']={str(ms):st.mean(g[str(ms)] for g in phase_values) for ms in DEADLINES}
            pred['periodic_uniform_phase_calibrated_delay']={str(ms):st.mean(g[str(ms)] for g in phase_delay_values) for ms in DEADLINES}
            predictions[trial]=dict(methods=pred,sampled_envelope=envelope,central_full_budget_phase_predictions=phase_values)
            ref=report['trial_refs'][trial];directory=session/ref['path'];c.verify_seal(directory)
            if c.digest(directory/'seal.json')!=ref['seal']:raise ValueError('validation seal differs')
            track(directory/'seal.json');derived=checked(directory/'derived.json');requests=derived['requests']
            if len(requests)!=len(offers):raise ValueError('offered denominator differs')
            observed={str(ms):100*sum(not r['success'] or r['e2e_ns']>ms*1000000 for r in requests)/len(offers) for ms in DEADLINES}
            for method,grid in pred.items():
                for ms,value in grid.items():
                    row=dict(context=key,trial=trial,block=cfg['block'],deadline_ms=int(ms),method=method,
                             observed_miss_pct=observed[ms],predicted_miss_pct=value,error_pp=abs(value-observed[ms]))
                    context_rows.append(row);all_rows.append(row)
            failed25=[r for r in requests if not r['success'] or r['e2e_ns']>25000000]
            predictions[trial]['outcome_diagnostics']=dict(observed_miss_pct=observed,
                sampled_envelope_covers={ms:a<=observed[ms]<=b for ms,(a,b) in envelope.items()},
                misses25=len(failed25),completion_certainly_within25_but_client_missed=sum(r['success'] and r['completion_after_offered_upper_ns']<=25000000 for r in failed25),
                completion_certainly_after25=sum(r['success'] and r['completion_after_offered_lower_ns']>25000000 for r in failed25),
                worker_processing_p50_ms=percentile([r['processing_wall_ns']/1e6 for r in requests if r['worker_observed']],.5))
        summary={}
        for method in next(iter(predictions.values()))['methods']:
            summary[method]={str(ms):dict(mae_pp=st.mean(r['error_pp'] for r in context_rows if r['method']==method and r['deadline_ms']==ms),
                maximum_error_pp=max(r['error_pp'] for r in context_rows if r['method']==method and r['deadline_ms']==ms)) for ms in DEADLINES}
        for ms in DEADLINES:
            expected=report['result']['deadline_grid']['busy'][str(ms)]['mae_pp']
            if not math.isclose(summary['fluid_busy'][str(ms)]['mae_pp'],expected,abs_tol=1e-8):raise ValueError('original model result did not reproduce')
        envelope_summary={str(ms):dict(covered_trials=sum(p['outcome_diagnostics']['sampled_envelope_covers'][str(ms)] for p in predictions.values()),
            mean_width_pp=st.mean(p['sampled_envelope'][str(ms)][1]-p['sampled_envelope'][str(ms)][0] for p in predictions.values())) for ms in DEADLINES}
        contexts[key]=dict(parameters=parameters,methods=summary,sampled_envelope=envelope_summary,source_report_path=str(report_path))
        forecasts[key]=predictions
        c.save(out/'progress.json',dict(completed_contexts=list(contexts),last_context=key))
    if any(c.digest(ROOT/name)!=h for name,h in inputs.items()):raise ValueError('consumed source changed')
    result=dict(status='ordinary_model_discovery_complete',contexts=contexts,
        scope='All V29 outcomes are discovery data. Calibration-only parameter fitting does not make this retrospective comparison prospective.',
        phase_measured=False,hard_bound_established=False,novelty_established=False,
        sources=['https://docs.kernel.org/scheduler/sched-bwc.html','https://retis.santannapisa.it/people/nino/publication/TCC23.pdf'])
    c.save(out/'report.json',result);c.save(out/'forecasts_and_diagnostics.json',forecasts);c.save(out/'comparison_rows.json',all_rows)
    c.save(out/'input_hashes.json',inputs)
    for name in ('compare_v29_timing_models.py','periodic_budget_model.py','test_periodic_budget_model.py'):
        (out/name).write_bytes((ROOT/'analysis'/name).read_bytes())
    lines=['# Ordinary timing models: V29 discovery comparison','','Retrospective model development, with parameters restricted to calibration records. No new service experiment or measured replenishment phase.','','| Context | Model | 25 ms MAE pp | 50 ms MAE pp | 100 ms MAE pp | 500 ms MAE pp |','|---|---|---:|---:|---:|---:|']
    for key,value in contexts.items():
        for method,grids in value['methods'].items():lines.append('| '+key+' | '+method+' | '+' | '.join(f"{grids[str(ms)]['mae_pp']:.3f}" for ms in (25,50,100,500))+' |')
    lines+=['','Unknown phase is averaged uniformly over a sampled 1 ms grid, with full initial budget. This is an assumed prior, not an observed kernel phase. The separately reported scenario range includes full/empty starting balances and independently calibrated capacity extremes; it is neither a continuous envelope nor a guaranteed Linux bound. The ideal work-conserving budget server omits CPU-local retained slices, competing cgroup threads, CPU migrations and OS/runtime interference. Effective demand covers the whole busy service, not isolated SHA work.','','The empirical non-queue delay distribution comes only from the four low-rate calibration trials, with queue wait <=100 us. It is appended independently of worker latency and does not consume additional modeled budget. That independence/transfer assumption may fail under load. No negative delay or validation residual is fitted.','','Original busy-model errors reproduce at all six deadlines. V1 and all frozen V29 inputs remain untouched. Numerical tests independently compare the budget replay with discrete CPU-slot simulation, continuous service, spillover, idle-budget retention, queue rejection and delay CDF counting.','','These are ordinary baselines informed by [Linux bandwidth control](https://docs.kernel.org/scheduler/sched-bwc.html) and established [reservation timing models](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf). The latter uses guaranteed hierarchical real-time reservations and small-period assumptions; it is not a hard-bound algorithm reproduced here. Bandwidth ceilings do not justify a finite worst-case response-time guarantee without a lower service assumption.','','Further conclusions and a prospective protocol must be written from these discovery results before a new experiment. Selecting the best phase from validation would be an oracle and was not used.']
    (out/'report.md').write_text('\n'.join(lines)+'\n');c.seal(out)
    print('Discovery complete: '+str(out/'report.md'),flush=True)


if __name__=='__main__':main()
