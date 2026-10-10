#!/usr/bin/env python3
"""Freeze unchanged science and verify bounded monitor lifecycle without workload."""
import shutil
import subprocess
import sys
import time
from pathlib import Path
import v27r3_common as c
import v27r3_monitor_control as control


def freeze_design():
    c.verify_seal(c.MONITOR_FAILED/'bundle');c.verify_seal(c.MONITOR_FAILED/'preparation')
    c.verify_client_build()
    design=c.read(c.ROOT/'analysis/runtime_io_v27r2_design/20261007/design.json')
    design.update(software_revision=3,
        monitor_failed_generation_bundle_seal=c.digest(c.MONITOR_FAILED/'bundle/seal.json'),
        monitor_failed_generation_preparation_seal=c.digest(c.MONITOR_FAILED/'preparation/seal.json'),
        monitor_lifecycle=dict(readiness_bound_sec=5,completion_bound_sec=30,
            first_sample_before_service_release=True,last_sample_after_full_drain=True,
            native_stopped_before_monitor_completion_wait=True,interval_sec=1))
    if c.DESIGN.exists():
        c.design()
        if c.read(c.DESIGN/'design.json')!=design:raise ValueError('existing frozen design differs')
        return
    c.DESIGN.mkdir(parents=True);c.save(c.DESIGN/'design.json',design)
    old=c.ROOT/'analysis/runtime_io_v27r2_design/20261007'
    for path in old.glob('*_offsets_ns.json'):shutil.copy2(path,c.DESIGN/path.name)
    hashes={str((c.DESIGN/name).relative_to(c.ROOT)):h for name,h in c.files(c.DESIGN).items()}
    hashes['docs/runtime_io_v27r3_protocol.md']=c.digest(c.ROOT/'docs/runtime_io_v27r3_protocol.md')
    c.save(c.DESIGN/'seal.json',dict(files_sha256=hashes));c.design()


def main():
    if c.MONITOR_CHECK.exists():raise ValueError('preserve existing software check; no overwrite')
    freeze_design()
    out=c.MONITOR_CHECK;out.mkdir(parents=True)
    sources={str(p.relative_to(c.ROOT)):c.digest(p) for p in (c.ROOT/'diagnostic').glob('v27r3_*.py')}
    sources['diagnostic/test_v27r3.py']=c.digest(c.ROOT/'diagnostic/test_v27r3.py')
    sources['diagnostic/test_v27r3_monitor.py']=c.digest(c.ROOT/'diagnostic/test_v27r3_monitor.py')
    for name in sources:
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(c.ROOT/name,target)
    # A real child runs the production monitor loop with synthetic read functions.
    # One-second sleeps plus 31ms per-read cost recreate the failed cadence.
    trial=out/'real_cadence';trial.mkdir()
    argv=[sys.executable,'-B',str(c.ROOT/'diagnostic/v27r3_monitor_fixture.py'),'1','.031',
          '--output',str(trial/'monitor.json'),'--progress',str(trial/'monitor_progress.json')]
    monitor=control.HostMonitor(trial,lambda:None)
    started=time.monotonic()
    try:
        monitor.start('/software-fixture-no-cgroup',argv)
        before_traffic=time.monotonic_ns()
        print('Software monitor fixture: 80-second simulated traffic; synthetic host reads only.',flush=True)
        for part in range(4):
            time.sleep(20)
            print(f'Software monitor fixture: {(part+1)*20}/80 seconds.',flush=True)
        after_drain=time.monotonic_ns()
        count_at_drain=c.read(trial/'monitor_progress.json')['count']
        monitor.finish(after_drain)
    finally:
        monitor.stop()
    records=c.read(trial/'monitor.json')
    observations=dict(startup=dict(before_ns=before_traffic),final=dict(after_ns=after_drain))
    control.validate(trial,records,dict(power_settings={}),observations)
    if count_at_drain>=80 or len(records)<80:
        raise ValueError('fixture did not exercise additional count wait')
    c.save(trial/'report.json',dict(count_at_drain=count_at_drain,accepted_count=len(records),
        nominal_interval_sec=1,synthetic_read_overhead_sec=.031,traffic_lifetime_sec=80,
        elapsed_sec=time.monotonic()-started,observations=observations,
        mean_record_interval_sec=sum(x['process_interval_sec'] for x in records)/len(records),
        monitor_endpoint_and_count_replay_passed=True,host_reads_synthetic=True,
        scientific_workload=False,native_sampler=False))
    c.seal(trial)
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','diagnostic',
                          '-p','test_v27r3*.py','-v'],cwd=c.ROOT,capture_output=True,text=True,timeout=180)
    (out/'tests.stdout').write_text(tests.stdout);(out/'tests.stderr').write_text(tests.stderr)
    if tests.returncode:raise ValueError('revision-3 software checks failed; preserve diagnostic output')
    if any(c.digest(c.ROOT/name)!=h for name,h in sources.items()):raise ValueError('repair source changed during checks')
    c.save(out/'report.json',dict(schema=1,decision='bounded_monitor_lifecycle_software_pass',
        sources=sources,real_cadence_fixture_seal=c.digest(trial/'seal.json'),
        tests_passed=True,client_reused_seal=c.digest(c.CLIENT_BUILD/'seal.json'),
        failed_generation_bundle_seal=c.digest(c.MONITOR_FAILED/'bundle/seal.json'),
        failed_generation_preparation_seal=c.digest(c.MONITOR_FAILED/'preparation/seal.json'),
        design_seal=c.digest(c.DESIGN/'seal.json'),thresholds_relaxed=False,
        runtime_qualified=False,performance_run=False,docker_used=False,sudo_used=False))
    c.seal(out)
    print('Revision-3 design and monitor lifecycle checks sealed; runtime remains unrun.',flush=True)


if __name__=='__main__':main()
