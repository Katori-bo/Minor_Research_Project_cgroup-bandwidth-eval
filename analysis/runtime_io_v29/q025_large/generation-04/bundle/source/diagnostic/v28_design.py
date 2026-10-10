"""Write a new immutable V28 protocol and exact schedules; no runtime work."""
import random
import v28_common as c


def create():
    if c.DESIGN.exists():raise ValueError('preserve existing frozen design')
    slots=[];conditions=[('idle',0)]+[('steady',r) for r in (15,30,60,90,120)]+[('mixed',r) for r in (15,30)]
    rng=random.Random(2808102026);rng.shuffle(conditions)
    for block in (1,2):
        for kind,rate in (conditions if block==1 else list(reversed(conditions))):
            slots.append(dict(id=f'cal_b{block}_{kind}{rate}',kind=kind,low_rate=rate,block=block,collection_order=len(slots)+1))
    labels=[(15,6),(15,12),(30,6),(30,12)];rng.shuffle(labels)
    for block,order in enumerate(((0,1,3,2),(1,2,0,3),(2,3,1,0),(3,0,2,1)),1):
        for index in order:
            rate,p=labels[index]
            slots.append(dict(id=f'val_b{block}_low{rate}_p{p}',kind='validation',low_rate=rate,block=block,
                collection_order=len(slots)+1,period_sec=p,low_duration_sec=2*p//3,high_rate=180))
    prior=c.resolve(c.HISTORY,c.read(c.HISTORY/'latest_analysis.json')['path']);c.verify_seal(prior)
    design=dict(schema=28,date='2026-10-08',purpose='prospective_estimator_comparison',seed=2808102026,
        trial_order=slots,planned_calibration_trials=16,planned_validation_trials=16,quota_cpu=.5,
        steady_windows_sec=[[3,10],[10,17],[17,24]],
        busy_windows_sec=dict(calibration=[[11.5+15*k,14.5+15*k] for k in range(4)],
            **{'6':[[4.8+6*k,5.8+6*k] for k in range(10)],'12':[[10+12*k,11.8+12*k] for k in range(5)]}),
        rules=dict(calibration_capacity_range_pct=5,capacity_error_pct=5,deadline_error_pp=3,advantage_pp=1),
        analysis=dict(t_critical_95_df3=3.182446305284263,unit='four_validation_blocks'),
        measurement_bound_sec=7200,runtime_preparation_bound_sec=600,analysis_bound_sec=600,technical_retries=1,
        monitor_lifecycle=dict(readiness_bound_sec=5,completion_bound_sec=30),
        historical_analysis_seal=c.digest(prior/'seal.json'),native_sampler=False,novelty_established=False)
    c.DESIGN.mkdir(parents=True);c.save(c.DESIGN/'design.json',design)
    for slot in slots:
        cfg=c.config(slot)
        for suffix,x in (('measurement',cfg),('warmup',c.warmup_config(cfg))):
            c.save(c.DESIGN/'schedules'/(cfg['trial']+'_'+suffix+'_offsets_ns.json'),c.generated_schedule(x))
    names=[str(p.relative_to(c.ROOT)) for p in c.DESIGN.rglob('*') if p.is_file()]
    names+=['docs/runtime_io_v28_protocol.md','docs/runtime_io_v28_execution.md']
    c.save(c.DESIGN/'seal.json',dict(files_sha256={n:c.digest(c.ROOT/n) for n in sorted(names)}))
    c.design()


if __name__=='__main__':create()
