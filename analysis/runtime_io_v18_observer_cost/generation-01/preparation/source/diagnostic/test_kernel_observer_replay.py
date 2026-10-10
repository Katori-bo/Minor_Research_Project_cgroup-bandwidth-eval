"""Synthetic raw-evidence integration; never performs a pilot observation."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import kernel_observer_common as c
import kernel_observer_analysis as a
import kernel_observer_cost as runner
import verify_kernel_observer_cost as verifier

KERNEL_ORIGIN=10**12


def fixture(directory,config):
    directory.mkdir(parents=True)
    c.save(directory/'config.json',config)
    c.save(directory/'cleanup.json',dict(errors=[],detached=True,container_removed=True,cgroup_removed=True,root_controls_unchanged=True))
    limits={'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2,4','memory.max':'max','pids.max':'max'}
    c.save(directory/'initial.json',dict(pid=100,cgroup_id=50,initial_limits=limits,capped=True,
        time_namespaces=dict(host={'monotonic':[0,0],'boottime':[0,0]},service={'monotonic':[0,0],'boottime':[0,0]})))
    health=dict(gomaxprocs=1,workers=4,queue_cap=128,go_version='go1.26.1',instrument=True,
                runtime_variant='stock',runtime_capture=False,custom_recording=False,worker_yield=False,entry_protocol='all-outcomes-v1')
    identity=dict(health=health,image='image',expected_image='image',server_sha256='server',expected_server_sha256='server',
                  loadgen_sha256='client',expected_loadgen_sha256='client')
    c.save(directory/'identity.json',identity)
    c.save(directory/'container.json',dict(inspect=dict(Image='image',Mounts=[dict(Destination='/qualification')],
        HostConfig=dict(CpuPeriod=100000,CpuQuota=50000,CpusetCpus='2,4',Memory=0,MemorySwap=0,PidsLimit=None))))
    requests=[dict(ID=i,ScheduledOffsetNs=stamp,Error='',TimedOut=False,StatusCode=200,
                   EndToEndLatencyNs=100_000_000,CompletedOffsetNs=stamp+100_000_000) for i,stamp in enumerate(c.arrivals())]
    # Keep a timeout with no service records and a drained late success.
    requests[-2].update(Error='timeout',TimedOut=True,StatusCode=0,EndToEndLatencyNs=5_000_000_000)
    requests[-1].update(EndToEndLatencyNs=2_000_000_000,CompletedOffsetNs=requests[-1]['ScheduledOffsetNs']+2_000_000_000)
    client=dict(total_scheduled=len(requests),requests=requests,client_test_start_ns=10**9,elapsed_including_drain_sec=65,
                client_dropped=0,missed_arrivals=0,dispatch_lag_summary=dict(p99_ms=.2))
    client['clock_anchors']=[dict(label=f'{phase}_{i}',before_ns=base+i,after_ns=base+i+10,server_ns=base+i+5,generation=7)
                             for phase,base in (('start',900_000_000),('stop',67_000_000_000)) for i in range(3)]
    c.save(directory/'loadgen.json',client)
    warmup=dict(total_scheduled=len(c.arrivals(20)),requests=[dict(ID=i,ScheduledOffsetNs=s) for i,s in enumerate(c.arrivals(20))])
    c.save(directory/'warmup.json',warmup)
    jobs=[]; handlers=[]; entries=[]
    for q in requests:
        if q['Error']: continue
        t=10**9+q['ScheduledOffsetNs']; rid=q['ID']
        jobs.append(dict(id=rid,admission_ns=t+1_000_000,worker_start_ns=t+2_000_000,completion_ns=t+3_000_000))
        handlers.append(dict(id=rid,resume_ns=t+4_000_000,handler_exit_ns=t+5_000_000))
        entries.append(dict(id=rid,entry_ns=t+500_000))
    server=dict(health,active_handlers=0,queue_len=0,completed=len(jobs),admitted=len(jobs),clock_generation=7,
                events=jobs,handler_events=handlers,entry_events=entries)
    c.save(directory/'server_metrics.json',server)
    c.save(directory/'kernel_server_anchors.json',[
        dict(label=f'{phase}_{i}',before_ns=KERNEL_ORIGIN+base+i,after_ns=KERNEL_ORIGIN+base+i+10,
             server_ns=base+i+5,generation=7) for phase,base in (('start',800_000_000),('stop',68_000_000_000)) for i in range(3)])
    observations={label:dict(before_ns=KERNEL_ORIGIN+stamp,after_ns=KERNEL_ORIGIN+stamp+100,
                             cpu_stat=dict(usage_usec=usage,nr_throttled=0)) for label,stamp,usage in
                  (('startup',100_000_000,10),('measurement_start',900_000_000,100),
                   ('measurement_stop',67_500_000_000,100+len(jobs)*2000),('final',69_000_000_000,100+len(jobs)*2000))}
    c.save(directory/'observations.json',observations)
    c.save(directory/'thread_snapshots.json',[dict(before_ns=KERNEL_ORIGIN+100_000_000,after_ns=KERNEL_ORIGIN+100_000_100,tids=[100])])
    if config['arm']=='on':
        (directory/'events.txt').write_text(f'BEGIN {KERNEL_ORIGIN} 50\nS {KERNEL_ORIGIN+1} 2 0 100 0 0 1\n'
            f'X {KERNEL_ORIGIN+81_000_000_000} 2 100\nS {KERNEL_ORIGIN+81_000_000_001} 2 100 0 0 1 0\nEND {KERNEL_ORIGIN+90_000_000_000} 3\n')
        (directory/'observer.stderr').write_text('')
    environment=dict(power_settings=dict(policies={},platform_profile='balanced',external_power={'AC':'1'},desktop_profile='balanced'),baseline_c={'package':40})
    c.save(directory/'environment.json',environment); c.save(directory/'settling.json',dict(accepted=True))
    c.save(directory/'monitor.json',[dict(chatgpt_present=False,power_settings={k:v for k,v in environment['power_settings'].items() if k!='desktop_profile'}) for _ in range(80)])
    c.seal(directory); result=a.replay(directory)
    c.save(directory/'derived.json',result); c.save(directory/'complete.json',dict(valid=True)); c.seal(directory)
    return result


class RawReplayTests(unittest.TestCase):
    def test_all_offered_failures_missing_and_late_records_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=fixture(Path(tmp)/'off',c.matrix()[0])
            self.assertEqual(len(result['requests']),6793)
            self.assertFalse(result['requests'][-2]['worker_observed'])
            self.assertEqual(result['requests'][-2]['outcome'],'timeout')
            self.assertFalse(result['requests'][-1]['timely_1000'])
            self.assertTrue(result['requests'][-1]['drained_response'])
            self.assertEqual(result['capture']['kernel_events'],'unobserved')
            self.assertEqual(result['summary']['cpu_usec_per_completed_work'],2000)

    def test_zero_throttle_capture_replay_and_counter_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=fixture(Path(tmp)/'on',c.matrix()[1])
            self.assertEqual(result['capture']['quota_intervals'],[])
            self.assertEqual(result['capture']['counter_event_comparisons'][1]['counter_nr_throttled'],0)

    def test_namespace_diagnostics_wrong_cpu_or_generation_invalidates(self):
        for kind in ('namespace','diagnostics','cpu','generation'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp)/'on'; fixture(d,c.matrix()[1])
                if kind=='namespace':
                    m=c.read(d/'initial.json'); m['time_namespaces']['host']['monotonic']=[1,0]; c.save(d/'initial.json',m)
                elif kind=='diagnostics': (d/'observer.stderr').write_text('map exhausted')
                elif kind=='cpu': (d/'events.txt').write_text((d/'events.txt').read_text().replace(' 2 ',' 3 '))
                else:
                    anchors=c.read(d/'kernel_server_anchors.json'); anchors[-1]['generation']=8; c.save(d/'kernel_server_anchors.json',anchors)
                c.seal(d)
                with self.assertRaises(ValueError): a.replay(d)

    def test_complete_offline_screen_and_export_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); prep=session/'preparation'; prep.mkdir()
            for name in ('loadgen','gate','kernel_observer.bt','original.server','image.server'): (prep/name).write_text(name if name not in ('original.server','image.server') else 'server')
            manifest=dict(matrix=c.matrix(),workload=c.WORKLOAD,sources={},image='image',server_sha256='server',loadgen_sha256='client',
                          gate_sha256=c.digest(prep/'gate'),collector_sha256=c.digest(prep/'kernel_observer.bt'))
            # Trial fixture identity values match these sealed input digests below.
            manifest['server_sha256']=c.digest(prep/'original.server'); manifest['loadgen_sha256']=c.digest(prep/'loadgen')
            c.save(prep/'manifest.json',manifest); c.seal(prep)
            q=session/'qualification'; q.mkdir(); refs={}
            for i,arm in enumerate(('off','on')):
                config=dict(trial='rehearsal_'+arm,pair=0,order=i+1,arm=arm,**c.WORKLOAD)
                d=session/'rehearsals'/config['trial']/'attempt-1'; fixture(d,config); self.fix_identity(d,manifest)
                refs[arm]=dict(path=str(d.relative_to(session)),seal=c.digest(d/'seal.json'))
            c.save(session/'environment.json',c.read(session/refs['off']['path']/'environment.json'))
            c.save(q/'result.json',dict(passed=True,rehearsals=refs,preparation_seal=c.digest(prep/'seal.json'),
                                      environment_sha256=c.digest(session/'environment.json'))); c.seal(q)
            for config in c.matrix():
                d=session/'trials'/config['trial']/'attempt-1'; fixture(d,config); self.fix_identity(d,manifest)
            with patch.object(runner,'verify_preparation'):
                out=runner.analyze(session)
            result=verifier.verify_completion(session)
            self.assertEqual(result['decision'],'within_margins_requires_review')
            text=(out/'requests.csv').read_text(); (out/'requests.csv').write_text(text.replace('unobserved','invented',1))
            c.seal(out); c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=c.digest(out/'seal.json')))
            with self.assertRaisesRegex(ValueError,'requests.csv'): verifier.verify_completion(session)

    def fix_identity(self,d,manifest):
        identity=c.read(d/'identity.json')
        for key in ('image','server_sha256','loadgen_sha256'):
            identity[key]=manifest[key]; identity['expected_'+key]=manifest[key]
        c.save(d/'identity.json',identity)
        container=c.read(d/'container.json'); container['inspect']['Image']=manifest['image']; c.save(d/'container.json',container)
        c.seal(d); c.save(d/'derived.json',a.replay(d)); c.seal(d)


if __name__=='__main__': unittest.main()
