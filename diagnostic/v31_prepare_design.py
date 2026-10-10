"""Seal the V31 protocol and exact schedules without starting any service."""
import copy
from pathlib import Path
import subprocess
import v30_common as prior
import v31_common as c


def prepare():
    if c.DESIGN.exists():raise ValueError('preserve existing V31 design; overwrite prohibited')
    prior.design()
    original=prior.read(prior.DESIGN/'design.json')
    calibration=copy.deepcopy(original['calibration_configs'])
    # New namespace and trial identities; the original calibration contract is retained.
    for cfg in calibration:cfg['trial']='v31_'+cfg['trial']
    validation=[]
    for cfg in original['validation_configs']:
        rate={'A':5,'B':11,'C':19}[cfg['profile']]
        validation.append(dict(cfg,trial=cfg['trial'].replace('v30','v31'),
            traffic_pattern='steady',rate=rate,low_rate=rate,burst_low=rate,burst_high=rate,
            burst_period_sec=15,burst_low_duration_sec=10))
    d={k:copy.deepcopy(v) for k,v in original.items() if k not in (
        'compiled_exports','model_switch_ratio','delay_calibration')}
    d.update(schema=31,status='sealed_execution_specification_runtime_qualification_pending',
        calibration_configs=calibration,validation_configs=validation,primary_deadline_ms=10,
        secondary_deadlines_ms=[ms for ms in c.DEADLINES_MS if ms!=10],decision_deadlines_ms=[10,12],
        validation_offers=12600,primary_models=['joint_calibration_cdf','periodic_uniform_phase_calibrated_delay'],
        secondary_models=['fluid_busy','fluid_quadratic','independent_worker_response_convolution',
                          'median_worker_plus_response','periodic_zero_phase_full_budget'],
        phase_prior=dict(phases_sec=[i*.001 for i in range(100)],initial_credit_fraction=1),
        timing_calibration=dict(reference_low_rates=[15,30],maximum_queue_ns=100000,
            cohort_count=4,require_nonempty_each_cohort=True,negative_stage_policy='unavailable_no_clipping',
            pooling='equal request weights; preserve worker/residual pairing; report cohort sensitivity'),
        scientific_domain=dict(maximum_measurement_throttled_periods=0,
            maximum_queue_ns=100000,minimum_observed_low_queue_fraction=.99,
            denominator='all scheduled measurement offers',unobserved_worker='domain failure'),
        decisions=dict(miss_budget_pct=5,all_trials_match_at_ms=[10,12],
            every_block_some_observed_profile_pass_at_ms=12),
        container_bounds=dict(released=41,created=42,functional=6,scientific=34,
                              technical_retry=1,unreleased_preflight=1),
        lifetime_sec=dict(original['lifetime_sec'],active_service=360),
        discovery_status='V30 outcomes inform the predeclared method, never V31 fitted parameters or outcomes',
        input_hashes={str(p.relative_to(c.ROOT)):c.digest(p) for p in (
            c.ROOT/'docs/runtime_io_v31_candidate_protocol_20261009.md',
            prior.DESIGN/'seal.json',prior.DESIGN/'design.json')})
    c.DESIGN.mkdir(parents=True)
    client=c.HISTORY/'bundle/loadgen';exports={}
    configs=calibration+validation
    for cfg in configs+[c.warmup_config(x) for x in configs if x['traffic_pattern']!='idle']:
        if cfg['traffic_pattern']=='idle':continue
        suffix='_warmup' if cfg['duration_sec']==20 else '_measurement'
        name='schedules/'+cfg['trial']+suffix+'.json';target=c.DESIGN/name;target.parent.mkdir(exist_ok=True)
        argv=[str(client),'-duration',str(cfg['duration_sec'])+'s','-rate',str(cfg['rate']),
            '-pattern',cfg['traffic_pattern'],'-burst-low',str(cfg['burst_low']),
            '-burst-high',str(cfg['burst_high']),'-burst-period',str(cfg['burst_period_sec'])+'s',
            '-burst-low-duration',str(cfg['burst_low_duration_sec'])+'s','-schedule-output',str(target)]
        subprocess.run(argv,check=True,capture_output=True,text=True,timeout=10)
        if c.read(target)!=c.generated_schedule(cfg):raise ValueError('compiled schedule differs from rational oracle')
        exports[name]=dict(count=len(c.read(target)),sha256=c.digest(target))
    d['compiled_exports']=exports
    c.save(c.DESIGN/'design.json',d)
    c.seal(c.DESIGN)
    c.design()
    print('V31 specification sealed: 16 calibration trials, 18 new-rate validation trials, 12600 offers. No measurements started.')


if __name__=='__main__':prepare()
