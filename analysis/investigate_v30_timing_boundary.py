"""Post-V30 discovery: calibrated queue-free timing, stages and scope limits.

V30 validation outcomes have already been seen. No output here is a new
prospective result, a causal intervention or a CPU-demand measurement.
"""
import argparse
from bisect import bisect_right
import math
from pathlib import Path
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v30_common as c

DEADLINES=(9,9.5,10,10.5,11,12,20,25,50,100,500)


def empirical_misses(samples_ns,deadline_ms):
    if not samples_ns or any(x<0 for x in samples_ns):raise ValueError('nonnegative nonempty timing cohort required')
    ordered=sorted(samples_ns)
    return 100*(len(ordered)-bisect_right(ordered,deadline_ms*1000000))/len(ordered)


def distribution(values):
    if not values:raise ValueError('empty descriptive distribution')
    v=sorted(values)
    return dict(n=len(v),mean=st.mean(v),p50=st.median(v),
                p95=v[math.ceil(.95*len(v))-1],p99=v[math.ceil(.99*len(v))-1],maximum=v[-1])


def select_calibration(entries):
    samples=[];ids=[];by_trial={}
    if len({cfg['trial'] for cfg,derived in entries})!=len(entries):raise ValueError('duplicate calibration trial')
    for cfg,derived in entries:
        if cfg['role']=='validation':raise ValueError('validation cannot supply timing parameters')
        if cfg['role']!='steady' or cfg['reference_low_rate'] not in (15,30):continue
        ids.append(cfg['trial']);selected=[]
        for r in derived['requests']:
            if not r['success'] or r['queue_ns']>100000:continue
            worker=r['processing_wall_ns'];total=r['e2e_ns']-r['queue_ns'];residual=total-worker
            if min(worker,total,residual)<0:raise ValueError('negative calibrated stage interval; no clipping')
            selected.append(dict(worker_ns=worker,residual_ns=residual,total_ns=total))
        if not selected:raise ValueError('empty low-rate calibration cohort')
        by_trial[cfg['trial']]=selected;samples.extend(selected)
    if len(ids)!=4 or not samples:raise ValueError('exact four retained low-rate calibration trials required')
    return samples,by_trial


def independent_misses(workers_ns,residuals_ns,deadline_ms):
    # Exact empirical convolution, preserving marginals but breaking pairing.
    r=sorted(residuals_ns);threshold=deadline_ms*1000000
    return 100*sum(len(r)-bisect_right(r,threshold-w) for w in workers_ns)/(len(workers_ns)*len(r))


def categories(requests,deadline_ms):
    threshold=deadline_ms*1000000
    failed=[r for r in requests if not r['success'] or r['e2e_ns']>threshold]
    result=dict(misses=len(failed),unsuccessful=sum(not r['success'] for r in failed),
                computation_certainly_after=sum(r['success'] and r['completion_after_offered_lower_ns']>threshold for r in failed),
                computation_certainly_within_but_client_missed=sum(r['success'] and r['completion_after_offered_upper_ns']<=threshold for r in failed),
                boundary_ambiguous=sum(r['success'] and r['completion_after_offered_lower_ns']<=threshold<r['completion_after_offered_upper_ns'] for r in failed))
    if sum(v for k,v in result.items() if k!='misses')!=result['misses']:raise ValueError('deadline decomposition does not conserve misses')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.absolute()
    if out.parent!=ROOT/'analysis/runtime_io_v2_extension' or out.exists() or out.is_symlink():raise ValueError('use a new direct extension discovery directory')
    session=c.PARENT/'generation-01';latest=c.read(session/'latest_analysis.json');directory=c.resolve(session,latest['path'])
    c.verify_seal(directory);report=c.read(directory/'report.json');c.verify_seal(session/'predictions')
    if report['result']['decision']!='short_deadline_prediction_confirmed':raise ValueError('unexpected V30 source decision')
    inputs={}
    def read(path):inputs[str(path.relative_to(ROOT))]=c.digest(path);return c.read(path)
    for path in (Path(__file__),ROOT/'analysis/test_v30_timing_boundary.py',directory/'report.json',directory/'seal.json',session/'predictions/seal.json',session/'predictions/summary.json',c.DESIGN/'design.json',c.DESIGN/'seal.json'):
        inputs[str(path.relative_to(ROOT))]=c.digest(path)
    configs={cfg['trial']:cfg for cfg in c.matrix()};entries=[];validation=[]
    for trial,ref in report['trial_refs'].items():
        d=c.resolve(session,ref['path']);c.verify_seal(d)
        if c.digest(d/'seal.json')!=ref['seal']:raise ValueError('V30 trial reference differs')
        derived=read(d/'derived.json');read(d/'seal.json')
        cfg=configs[trial]
        if cfg['role']=='validation':validation.append((cfg,derived))
        else:entries.append((cfg,derived))
    samples,by_trial=select_calibration(entries)
    totals=[x['total_ns'] for x in samples];workers=[x['worker_ns'] for x in samples];residuals=[x['residual_ns'] for x in samples]
    capacity=report['calibration']['methods']['busy']['capacity_rps'];demand_ns=.25/capacity*10**9
    parameters=dict(busy_capacity_rps=capacity,effective_demand_ms=demand_ns/1e6,
                    worker_wall_ms=distribution([x/1e6 for x in workers]),response_residual_ms=distribution([x/1e6 for x in residuals]),
                    queue_free_latency_ms=distribution([x/1e6 for x in totals]),
                    implied_worker_wall_budget_ms=.1*capacity*st.median(workers)/1e6,configured_cpu_budget_ms=25,
                    pooled_samples=len(samples),sample_scope='four low-rate calibration trials, successful requests with queue <=100us',
                    stage_correlation_descriptive=st.correlation(workers,residuals))
    predictions={str(ms):dict(joint_calibration_cdf=empirical_misses(totals,ms),
        independent_worker_response_convolution=independent_misses(workers,residuals,ms),
        median_worker_plus_response=empirical_misses([st.median(workers)+x for x in residuals],ms),
        effective_cpu_demand_plus_response=empirical_misses([demand_ns+x for x in residuals],ms)) for ms in DEADLINES}
    cal_rows={}
    for trial,values in by_trial.items():
        accounting=next(x for x in report['trial_accounting'] if x['trial']==trial)
        cal_rows[trial]=dict(samples=len(values),worker_wall_ms=distribution([x['worker_ns']/1e6 for x in values]),
            queue_free_latency_ms=distribution([x['total_ns']/1e6 for x in values]),miss_10ms_pct=empirical_misses([x['total_ns'] for x in values],10),
            aggregate_cpu_per_job_ms=1000*accounting['cpu_sec']/accounting['completed'],
            idle_corrected_aggregate_cpu_per_job_ms=1000*(accounting['cpu_sec']-report['calibration']['idle_cpu_rate']*accounting['accounted_wall_sec'])/accounting['completed'])
    records=[];profiles={}
    for cfg,derived in validation:
        req=derived['requests'];observed={str(ms):100*sum(not x['success'] or x['e2e_ns']>ms*1000000 for x in req)/len(req) for ms in DEADLINES}
        row=next(x for x in report['trial_accounting'] if x['trial']==cfg['trial'])
        records.append(dict(trial=cfg['trial'],block=cfg['block'],profile=cfg['profile'],offers=len(req),
            observed_miss_pct=observed,throttled_periods=row['throttled_periods'],
            queue_ms=distribution([x['queue_ns']/1e6 for x in req if x['worker_observed']]),
            worker_wall_ms=distribution([x['processing_wall_ns']/1e6 for x in req if x['worker_observed']]),
            stage_counts={str(ms):categories(req,ms) for ms in (10,25)},
            arithmetic_replacing_worker_with_effective_demand_10ms_pct=100*sum(not x['success'] or x['e2e_ns']-x['processing_wall_ns']+demand_ns>10000000 for x in req)/len(req)))
    for profile in 'ABC':
        selected=[x for x in records if x['profile']==profile]
        profiles[profile]=dict(scope='applicable steady queue-free discovery comparison' if profile!='C' else 'outside scope; negative control only',
            trials=6,throttled_periods=[x['throttled_periods'] for x in selected],
            stages={str(ms):{key:sum(x['stage_counts'][str(ms)][key] for x in selected) for key in selected[0]['stage_counts'][str(ms)]} for ms in (10,25)},
            joint_cdf_mae_pp={str(ms):st.mean(abs(predictions[str(ms)]['joint_calibration_cdf']-x['observed_miss_pct'][str(ms)]) for x in selected) for ms in DEADLINES})
    steady=[x for x in records if x['profile'] in ('A','B')]
    comparison={name:{str(ms):st.mean(abs(predictions[str(ms)][name]-x['observed_miss_pct'][str(ms)]) for x in steady) for ms in DEADLINES} for name in next(iter(predictions.values()))}
    frozen=read(session/'predictions/summary.json')
    comparison['V30_frozen_periodic_plus_delay']={str(ms):st.mean(abs(frozen['methods']['periodic_uniform_phase_calibrated_delay'][x['trial']]['deadline_miss_pct'][str(ms)]-x['observed_miss_pct'][str(ms)]) for x in steady) for ms in (10,20,25,50,100,500)}
    out.mkdir();contract=dict(status='retrospective_model_development_after_V30_outcomes',calibration_inputs_only=True,prospective_confirmation=False,
        no_new_measurements=True,deadlines_ms=DEADLINES,original_frozen_deadlines_ms=list(c.DEADLINES_MS),
        empirical_baseline='paired empirical distribution of e2e minus queue from four original low-rate calibration trials',
        empirical_scope='steady requests with negligible queue and no observed throttling; no overload/burst capability asserted',
        validation_filters='none; all scheduled validation offers retained; profile C is an explicit outside-scope negative control',
        convolution='all worker/residual cross-pairs preserve marginals but break pairing; ordinary comparator, no fitting to outcomes',
        arithmetic_sensitivity='replacing recorded processing-wall stage is arithmetic only, not a physical intervention or prospective model',
        CPU_boundary='worker wall time is not CPU demand; implied budget above configured Q is an incompatibility diagnostic, not a new periodic model',
        no_oracle_phase_selection=True,novelty_established=False,causal_mechanism_established=False)
    c.save(out/'contract.json',contract);c.save(out/'calibration_samples.json',samples)
    result=dict(status='timing_boundary_discovery_complete',parameters=parameters,calibration_trials=cal_rows,
                predictions=predictions,steady_comparison_mae_pp=comparison,profiles=profiles,trial_diagnostics=records,
                prospective_confirmation=False,novelty_established=False)
    c.save(out/'report.json',result);c.save(out/'input_hashes.json',inputs)
    lines=['# V30 timing-boundary investigation','','**Retrospective discovery after V30 outcomes; no fresh collection or new confirmation.** All fitted timing values come from the original four low-rate calibration trials. This does not make the new comparison prospective, because its method was chosen after validation results.','','## The 10 ms discrepancy','','The four calibration cohorts already show the steady-response timing that the CPU-derived demand misses:','','| Quantity | Value ms |','|---|---:|',f"| Effective CPU demand from busy capacity | {parameters['effective_demand_ms']:.3f} |",f"| Recorded calibration worker-wall median | {parameters['worker_wall_ms']['p50']:.3f} |",f"| Calibration non-queue response residual mean | {parameters['response_residual_ms']['mean']:.3f} |",f"| Paired queue-free calibration latency median | {parameters['queue_free_latency_ms']['p50']:.3f} |",f"| Paired queue-free latency 95th percentile | {parameters['queue_free_latency_ms']['p95']:.3f} |",'',
        f"The paired calibration CDF predicts **{predictions['10']['joint_calibration_cdf']:.3f}%** misses at 10 ms; the frozen periodic model predicts **0.296%** for either steady profile. Observed steady misses are about 67%. Over all 12 steady trials, the empirical CDF has **{comparison['joint_calibration_cdf']['10']:.3f} pp** mean absolute error. This ordinary baseline explains much of the discrepancy without a new CPU-budget parameter.",'',
        '| Steady comparator | 10 ms MAE pp | 11 ms MAE pp (exploratory) | 25 ms MAE pp |','|---|---:|---:|---:|']
    for name,grid in comparison.items():lines.append('| '+name+' | '+f"{grid['10']:.3f}"+' | '+(f"{grid['11']:.3f}" if '11' in grid else 'not frozen')+' | '+f"{grid['25']:.3f}"+' |')
    lines+=['','Retaining paired worker/response samples matters at this threshold: independent convolution predicts '+f"{predictions['10']['independent_worker_response_convolution']:.3f}%"+' misses instead of '+f"{predictions['10']['joint_calibration_cdf']:.3f}%"+'. This is an empirical dependence/shape observation, not a proof of a causal interaction or a new distributional method. Calibration requests are not independent experiment replicates; there are four calibration trials and six validation blocks.','','## Stage and resource evidence','','| Profile | 10 ms misses | Computation certainly after | Computation certainly within, client missed | Clock ambiguous | Recorded throttled-period range |','|---|---:|---:|---:|---:|---:|']
    for p,value in profiles.items():
        s=value['stages']['10'];t=value['throttled_periods']
        lines.append(f"| {p} | {s['misses']} | {s['computation_certainly_after']} | {s['computation_certainly_within_but_client_missed']} | {s['boundary_ambiguous']} | {min(t)}–{max(t)} |")
    lines+=['','All A/B trials have zero recorded throttled periods. Their queue-wait medians are about 0.009 ms. Therefore quota throttling is not needed to observe the 10 ms failure. CPU wall time, CPU accounting and HTTP/dispatch/runtime delay must remain distinct. Clock ambiguity is material at 10 ms and is retained rather than assigned to a cause.','','Median calibration worker-wall time combined with busy capacity would require '+f"{parameters['implied_worker_wall_budget_ms']:.3f}"+' ms of worker availability per 100 ms, above the configured 25 ms CPU quota. The previously rejected identification of worker wall time as transferable CPU on-time remains inadmissible. We do not fix it by clipping the budget or selecting faster samples.','','## Scope and next test','','The empirical CDF predicts zero 25 ms misses for bursts too, while profile C actually misses about 79%; its burst error is '+f"{profiles['C']['joint_cdf_mae_pp']['25']:.3f}"+' pp. It is a low-queue timing reference, not a replacement for queue/budget modeling. The surviving lead is a boundary involving both traffic state and deadline resolution.','','A suitable next confirmation would predeclare this ordinary paired calibration-CDF baseline and test fresh steady rates near the 10–11 ms response transition, with the original frozen models retained. At 11 ms its discovery forecast is '+f"{predictions['11']['joint_calibration_cdf']:.3f}%"+' misses, near the declared 5% operating target. New calibration, rates, primary endpoint, blocks, decisions and technical qualification must be frozen before collection. No runnable next-generation collector is implied by this report.']
    (out/'report.md').write_text('\n'.join(lines)+'\n')
    for name in ('investigate_v30_timing_boundary.py','test_v30_timing_boundary.py'):(out/name).write_bytes((ROOT/'analysis'/name).read_bytes())
    for name,h in inputs.items():
        if c.digest(ROOT/name)!=h:raise ValueError('consumed source changed')
    c.seal(out);print(str(out/'report.md'),flush=True)


if __name__=='__main__':main()
