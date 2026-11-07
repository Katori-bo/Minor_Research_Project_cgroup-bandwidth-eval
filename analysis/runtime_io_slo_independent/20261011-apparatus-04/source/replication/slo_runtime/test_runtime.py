"""Offline-only portable imports, ownership, budgets, assembly and qualification gates."""
import copy
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
import common as r
import supervisor as s
import worker
import go_backend
import nginx_backend
import v31_common as go
import v31_verify as verify
import nginx_common as n
import nginx_prediction_common as nc
import nginx_prediction_model as nm
import collectors as adapters
import assemble_returns as returns
import cost
import leftover_observer_audit as audit
import leftover_observer_review as observer_review


class Package(unittest.TestCase):
    def test_standalone_package_and_imports(self):
        package=r.verify_package(ROOT)
        self.assertEqual(package['third_party_python_imports'],[])
        for module in (r,s,worker,go_backend,nginx_backend,go,verify,n,nc,nm,adapters):
            self.assertTrue(Path(module.__file__).resolve().is_relative_to(ROOT))
        self.assertFalse(package['runtime_qualified'])

    def test_go_design_matches_frozen_plan_and_host_relative_placement(self):
        host=r.read(ROOT/'runtime_package.json')['host']
        expected=r.read(ROOT/'scientific/retained_go_design.json')
        for cfg in expected['calibration_configs']+expected['validation_configs']:cfg['cpus']=host['go_service_cpus']
        self.assertEqual(go.design(),expected)
        self.assertEqual(go.SERVER_CPUS,tuple(host['go_service_cpus']))
        self.assertEqual(len(go.calibration_configs()),16)
        self.assertEqual(sum(len(go.schedule(cfg)) for cfg in go.validation_configs()),12600)

    def test_portable_offline_go_bundle_replay(self):
        runs=ROOT/'runs';runs.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=runs) as temp:
            session=Path(temp);shutil.copytree(ROOT/'assets/go_bundle',session/'bundle')
            manifest=verify.verify_bundle(session)
            self.assertEqual(manifest['host_id'],r.read(ROOT/'runtime_package.json')['host']['id'])
            self.assertEqual(manifest['matrix'],go.matrix())

    def test_nginx_exact_schedule_and_identity_constants(self):
        cfgs=nc.configs('validation')
        self.assertEqual(len(cfgs),18)
        self.assertEqual([c['profile'] for c in cfgs],list('ABCB CACABACBCBABAC'.replace(' ','')))
        self.assertEqual(nc.configs('calibration')[0]['count'],400)
        self.assertEqual({c['interval_ns'] for c in cfgs},{250000000,166666667,125000000})
        self.assertEqual(n.INPUT_SHA,r.read(ROOT/'scientific/plan.json')['NGINX']['input_sha256'])

    def test_adapters_have_no_historical_campaign_entry_points(self):
        import ast
        for name in ('go_collector.py','nginx_collector.py'):
            tree=ast.parse((ROOT/'adapted'/name).read_text())
            self.assertFalse({node.name for node in tree.body}&{'campaign','collect_slot','foreground','main'})


class Ownership(unittest.TestCase):
    def test_reused_pid_is_never_signalled(self):
        record=dict(pid=991,start_ticks=10,uid=1000,boot_id='boot');sent=[]
        s.terminate(record,inspect=lambda pid:dict(record,start_ticks=11),send=lambda *x:sent.append(x),send_group=lambda *x:sent.append(x))
        self.assertEqual(sent,[])

    def test_boot_and_uid_change_are_not_owned(self):
        record=dict(pid=1,start_ticks=10,uid=1000,boot_id='boot')
        self.assertFalse(r.same(record,lambda _:dict(record,uid=0)))
        self.assertFalse(r.same(record,lambda _:dict(record,boot_id='new')))

    def test_retained_string_ticks_and_transient_state_normalize(self):
        record=dict(pid=7,start_ticks='10',uid=1000,state='R')
        self.assertTrue(r.same(record,lambda _:dict(pid=7,start_ticks=10,uid=1000,boot_id='boot')))

    def test_owned_dummy_child_is_terminated(self):
        child=subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(15)'],start_new_session=True)
        try:
            record=r.identity(child.pid);s.terminate(record,grace_sec=.1);child.wait(timeout=3)
            self.assertIsNotNone(child.returncode)
        finally:
            if child.poll() is None:child.kill();child.wait()

    def test_only_registered_worker_container_is_cleaned(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);own=base/'own';foreign=base/'foreign';own.mkdir();foreign.mkdir()
            r.write(own/'ownership.json',dict(owner=dict(pid=7,start_ticks='10'),container='owned',nonce='right'))
            r.write(foreign/'ownership.json',dict(owner=dict(pid=8,start_ticks=10),container='foreign',nonce='other'))
            removed=[]
            errors=s.cleanup(base,dict(host=dict(id='host02'),application='Go'),dict(pid=7,start_ticks=10),
                remove=lambda *args:removed.append(args))
            self.assertEqual(errors,[])
            self.assertEqual(removed,[('owned','right','research.slo.host02.Go.owner')])

    def test_cleanup_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            r.write(base/'ownership.json',dict(owner=dict(pid=7,start_ticks=10),container='owned',nonce='right'))
            def fail(*_):raise ValueError('nonce changed')
            errors=s.cleanup(base,dict(host=dict(id='host01'),application='NGINX'),dict(pid=7,start_ticks=10),fail)
            self.assertEqual(len(errors),1);self.assertIn('nonce changed',errors[0]['error'])

    def test_terminal_inventory_process_never_group_signalled(self):
        record=dict(pid=7,start_ticks=10,uid=1000);sent=[];clock=[0]
        def now():clock[0]+=1;return clock[0]
        s.terminate(record,group=False,grace_sec=.1,inspect=lambda _:record,
            send=lambda *args:sent.append(args),send_group=lambda *_:self.fail('terminal process group signalled'),
            clock=now,sleep=lambda _:None)
        self.assertEqual([x[1] for x in sent],[signal.SIGTERM,signal.SIGKILL])


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.plan=r.read(ROOT/'scientific/plan.json')
        self.package=r.read(ROOT/'runtime_package.json')
        self.package.pop('consumed_allocations',None)  # Fresh synthetic allocation fixtures.

    def test_actual_audit_writer_and_reader_accept_supervisor_route(self):
        host=self.package['host'];value=dict(uid=0,boot_id=dict(text='synthetic'),assessment=dict(synthetic=True))
        script=self.root/'diagnostic/leftover_observer_audit.py';script.parent.mkdir()
        shutil.copy2(audit.__file__,script);value['audit_script_sha256']=r.sha(script)
        def invoke(directory,argv,*args,**kwargs):
            directory.mkdir(parents=True,exist_ok=True)
            with patch.object(sys,'argv',argv[3:]):audit.main()
        with patch.object(audit,'ROOT',self.root),patch.object(observer_review,'ROOT',self.root),\
             patch.object(s.sys.stdin,'isatty',return_value=True),patch.object(s,'invoke',side_effect=invoke),\
             patch.object(audit,'inventory',return_value=value),patch.object(audit,'assess',return_value=value['assessment']),\
             patch.object(observer_review,'classify',return_value=dict(performance_eligible=True)),\
             patch.dict(os.environ,{},clear=True):
            s.inventory(self.root,self.root/'campaign',dict(host=host,application='Go'),10**20)
        self.assertTrue((self.root/'runs'/host['id']/'audits/Go.json').exists())
        self.assertTrue(r.read(self.root/'campaign/observer.json')['review']['performance_eligible'])

    def test_audit_writer_still_rejects_foreign_directory_before_inventory(self):
        with patch.object(audit,'ROOT',self.root),patch.object(sys,'argv',['audit','--output',str(self.root/'foreign.json')]),\
             patch.object(audit,'inventory') as collect:
            with self.assertRaisesRegex(ValueError,'dedicated audit directory'):audit.main()
            collect.assert_not_called()

    def test_consumed_prior_allocation_cannot_be_retried_and_next_uses_original(self):
        host=next(x for x in self.plan['hosts'] if x['id']=='host01')
        new=self.root/'new';old=self.root/'old'
        r.write(new/'scientific/plan.json',self.plan);r.write(old/'runtime_seal.json',dict(synthetic=True))
        directory=old/'runs/host01/Go'
        r.write(directory/'supervisor_finished.json',dict(allocation_closed=True))
        r.write(directory/'return_seal.json',dict(package_seal_sha256=r.sha(old/'runtime_seal.json'),
            files_sha256={'supervisor_finished.json':r.sha(directory/'supervisor_finished.json')}))
        previous=dict(host=host,scientific_plan_sha256='same')
        replacement=dict(previous,consumed_allocations=dict(Go=dict(relative_package='../old',
            package_seal_sha256=r.sha(old/'runtime_seal.json'),return_seal_sha256=r.sha(directory/'return_seal.json'),
            supervisor_finished_sha256=r.sha(directory/'supervisor_finished.json'))))
        with patch.object(r,'verify_package',side_effect=lambda p:replacement if Path(p)==new else previous):
            with self.assertRaisesRegex(ValueError,'already consumed'):s.admit(new,'Go',True)
            self.assertEqual(r.campaign_origin(new,'Go'),old)
            s.admit(new,'NGINX',True)
            (directory/'supervisor_finished.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'receipts changed'):r.campaign_origin(new,'Go')

    def test_unconfirmed_allocation_cannot_create_attempt(self):
        with patch.object(r,'verify_package',return_value=self.package),patch.object(r,'read',return_value=self.plan):
            with self.assertRaises(ValueError):s.admit(self.root,'Go',False)
        self.assertFalse((self.root/'runs').exists())

    def test_frozen_host_order_no_resume_or_overwrite(self):
        host=self.package['host'];first,second=host['order']
        (self.root/'scientific').mkdir();r.write(self.root/'scientific/plan.json',self.plan)
        with patch.object(r,'verify_package',return_value=self.package):
            with self.assertRaises(ValueError):s.admit(self.root,second,True)
            directory,_=s.admit(self.root,first,True)
            with self.assertRaises(ValueError):s.admit(self.root,first,True)
            r.write(directory/'supervisor_finished.json',dict(allocation_closed=True))
            s.admit(self.root,second,True)

    def test_campaign_caps_sum_to_frozen_aggregate(self):
        values=[s.allocation(self.plan,x['host'],x['application']) for x in self.plan['campaigns']]
        self.assertEqual(sum(x['cap_sec'] for x in values),30600)
        self.assertTrue(all(x['cleanup_reserve_sec']==120 for x in values))

    def test_failed_setup_cannot_be_reused_even_with_success_receipt(self):
        r.write(self.root/'setup/failure.json',dict(error='image platform verification failed'))
        r.write(self.root/'setup/setup.json',dict(package_seal_sha256='earlier receipt'))
        with patch.object(r,'command') as command:
            with self.assertRaisesRegex(ValueError,'setup attempt failed'):
                r.verify_setup(self.root,self.root/'setup')
            command.assert_not_called()

    def test_timeout_terminates_owned_child_and_preserves_registration(self):
        process=type('Process',(),dict(pid=991,returncode=None,poll=lambda self:None,wait=lambda self,timeout:None))()
        record=dict(pid=991,start_ticks=10,uid=1000,boot_id='boot')
        ticks=iter([0,0,0,0,2*10**9,2*10**9,2*10**9,2*10**9])
        with patch.object(s.subprocess,'Popen',return_value=process),patch.object(r,'identity',return_value=record),\
             patch.object(s.time,'monotonic_ns',side_effect=lambda:next(ticks)),patch.object(s,'terminate') as terminate:
            with self.assertRaises(TimeoutError):s.invoke(self.root,['synthetic'],'prepare',1000*10**9,.5)
            terminate.assert_called_once_with(record,group=True)
        self.assertTrue((self.root/'workers/prepare.json').exists())

    def test_lost_independent_watchdog_stops_current_worker(self):
        process=type('Process',(),dict(pid=991,returncode=None,poll=lambda self:None,wait=lambda self,timeout:None))()
        watch=type('Watch',(),dict(poll=lambda self:1))()
        record=dict(pid=991,start_ticks=10,uid=1000,boot_id='boot')
        with patch.object(s.subprocess,'Popen',return_value=process),patch.object(r,'identity',return_value=record),patch.object(s,'terminate') as terminate:
            with self.assertRaises(ValueError):s.invoke(self.root,['synthetic'],'prepare',time.monotonic_ns()+1000*10**9,watcher=watch)
            terminate.assert_called_once_with(record,group=True)

    def test_cost_excludes_retained_software_receipts_and_preserves_corrupt_raw(self):
        r.write(self.root/'session/bundle/client_build/compiled_report/loadgen.json',dict(total_scheduled=999,requests=[]))
        r.write(self.root/'session/preparation/functional/loadgen.json',dict(total_scheduled=2,requests=[{},{}],client_dropped=0))
        bad=self.root/'session/slots/partial/warmup.json';bad.parent.mkdir(parents=True);bad.write_text('{')
        rows=cost.acquired(self.root)
        self.assertEqual(len(rows),2);self.assertEqual(sum(x.get('declared_offers',0) for x in rows),2)
        self.assertTrue(any(not x['parseable'] for x in rows))

    def test_existing_control_request_is_counted_without_extra_probe(self):
        import kernel_service_bridge as bridge
        before=bridge.HTTP_CALLS.get('GET synthetic',0)
        with patch.object(bridge,'_retained_get',return_value={'ok':True}) as original:
            self.assertEqual(bridge.get('unused','synthetic'),{'ok':True})
            original.assert_called_once_with('unused','synthetic')
        self.assertEqual(bridge.HTTP_CALLS['GET synthetic'],before+1)

    def test_client_boundaries_are_parent_observations(self):
        child=type('Child',(),dict(pid=991,poll=lambda self:0))()
        process=worker.TimedProcess(child,self.root,'warmup',100,101)
        self.assertEqual(process.poll(),0);self.assertEqual(process.poll(),0)
        self.assertTrue(r.read(self.root/'warmup_supervisor_spawn.json')['absolute_http_completion_not_observed'])
        self.assertTrue(r.read(self.root/'warmup_supervisor_exit.json')['timestamp_is_parent_observation'])

    def test_independent_watchdog_handles_dead_parent(self):
        directory=self.root/'runs/host01/Go'
        r.write(directory/'lifetime.json',dict(started_ns=0,active_deadline_ns=100,hard_deadline_ns=200))
        r.write(directory/'allocation.json',dict(host=dict(id='host01'),application='Go',campaign=dict(id='cid')))
        r.write(directory/'supervisor.json',dict(pid=1,start_ticks=1))
        record=dict(pid=2,start_ticks=2,uid=1000,boot_id='b')
        r.write(directory/'active_worker.json',dict(record,new_session=True))
        r.write(directory/'workers/collect.json',record)
        with patch.object(r,'same',return_value=False),patch.object(s,'terminate') as terminate,\
             patch.object(s,'cleanup',return_value=[]),patch.object(s.time,'monotonic_ns',return_value=101),patch.object(r,'sha',return_value='hash'):
            s.watchdog(directory);terminate.assert_called_once_with(record,group=True)
        self.assertTrue(r.read(directory/'watchdog_cleanup.json')['expired'])
        self.assertTrue(r.read(directory/'supervisor_finished.json')['allocation_closed'])
        self.assertTrue((directory/'return_seal.json').exists())

    def test_four_unavailable_allocations_close_with_72_unavailable_slots(self):
        roots=[]
        for host in self.plan['hosts']:
            base=self.root/host['id'];base.mkdir();roots.append(base)
            r.write(base/'runtime_package.json',dict(host=host))
            r.write(base/'scientific/plan.json',self.plan);r.write(base/'runtime_seal.json',dict(synthetic=True))
        with patch.object(r,'verify_package',side_effect=lambda root:r.read(Path(root)/'runtime_package.json')):
            for base in roots:
                host=r.read(base/'runtime_package.json')['host']
                for app in host['order']:s.close_unavailable(base,app,'synthetic host unavailable',True)
            result=returns.assemble(roots)
        self.assertEqual(len(result['windows']),72);self.assertEqual(result['primary_verdict'],'unavailable')
        self.assertTrue(result['study_closed']);self.assertFalse(result['independent_hardware_event_observed'])

    def test_return_mutation_is_rejected(self):
        directory=self.root/'return';directory.mkdir();package=self.root/'package';package.mkdir()
        r.write(package/'runtime_seal.json',dict(synthetic=True));r.write(directory/'raw.json',dict(x=1))
        r.write(directory/'return_seal.json',dict(files_sha256={'raw.json':r.sha(directory/'raw.json')},
            package_seal_sha256=r.sha(package/'runtime_seal.json')))
        returns.verify_return(directory,package)
        (directory/'raw.json').write_text('{}')
        with self.assertRaises(ValueError):returns.verify_return(directory,package)

    def test_stage_failure_records_time_and_offers(self):
        with self.assertRaises(ValueError):
            with worker.Stage(self.root,'warmup',300,100):raise ValueError('partial')
        self.assertEqual(r.read(self.root/'ledger/warmup_start.json')['planned_warmup_offers'],100)
        self.assertEqual(r.read(self.root/'ledger/warmup_end.json')['error'],'partial')

    def test_worker_requires_supervisor_registration_before_any_backend(self):
        r.write(self.root/'workers/prepare.json',dict(pid=-1,start_ticks=0))
        with self.assertRaises(ValueError):worker.wait_for_registration(self.root,'prepare')


class Qualification(unittest.TestCase):
    def test_frozen_amd_control_siblings_are_valid(self):
        host=next(x for x in r.read(ROOT/'scientific/plan.json')['hosts'] if x['id']=='host01')
        topo={str(i):dict(core=str(i//2),package='0',siblings=str(i//2*2)+'-'+str(i//2*2+1)) for i in range(12)}
        r.placement(host,topo,set(range(12)))
        topo['4']['core']='0'
        with self.assertRaises(ValueError):r.placement(host,topo,set(range(12)))

    def test_retained_intel_control_core_separation_is_preserved(self):
        host=next(x for x in r.read(ROOT/'scientific/plan.json')['hosts'] if x['id']=='host02')
        topo={str(i):dict(core=str(i%4),package='0',siblings=str(i%4)+','+str(i%4+4)) for i in range(8)}
        r.placement(host,topo,set(range(8)))
        topo['1']['core']='0'
        with self.assertRaises(ValueError):r.placement(host,topo,set(range(8)))

    def test_incomplete_go_calibration_cannot_freeze(self):
        backend=go_backend.Backend(ROOT,ROOT/'runs/synthetic')
        with self.assertRaises(ValueError):backend.reference([],r.read(ROOT/'scientific/plan.json'))

    def test_incomplete_or_adverse_nginx_calibration_cannot_freeze(self):
        backend=nginx_backend.Backend(ROOT,ROOT/'runs/synthetic')
        with self.assertRaises(ValueError):backend.reference([],r.read(ROOT/'scientific/plan.json'))
        values=[dict(config=cfg,domain_exits=['throttling']) for cfg in nc.configs('calibration')]
        with self.assertRaises(ValueError):backend.reference(values,r.read(ROOT/'scientific/plan.json'))

    def test_nginx_reference_is_all_1600_offers_and_not_pilots(self):
        backend=nginx_backend.Backend(ROOT,ROOT/'runs/synthetic')
        values=[dict(config=cfg,domain_exits=[],outcomes=[dict(success=True,e2e_ns=i) for i in range(400)]) for cfg in nc.configs('calibration')]
        ref=backend.reference(values,r.read(ROOT/'scientific/plan.json'))
        self.assertEqual(len(ref),1600)
        values[0]['config']=nc.configs('pilot')[0]
        with self.assertRaises(ValueError):backend.reference(values,r.read(ROOT/'scientific/plan.json'))

    def test_physical_core_overlap_and_disallowed_affinity_rejected(self):
        host=r.read(ROOT/'runtime_package.json')['host']
        topo={str(i):dict(core=str(i),package='0',siblings=str(i)) for i in range(12)}
        r.placement(host,topo,set(range(12)))
        topo[str(host['go_service_cpus'][1])]['core']=topo[str(host['go_service_cpus'][0])]['core']
        with self.assertRaises(ValueError):r.placement(host,topo,set(range(12)))
        with self.assertRaises(ValueError):r.placement(host,topo,{0,1})


def synthetic_go_client(cfg):
    offsets=go.schedule(cfg)
    rows=[dict(ID=i,ScheduledOffsetNs=ns,EndToEndLatencyNs=50,CompletedOffsetNs=ns+50,Error='',StatusCode=200)
          for i,ns in enumerate(offsets)]
    return dict(total_scheduled=len(rows),requests=rows,client_dropped=0,total_completed=len(rows),
        total_dispatched=len(rows),total_success=len(rows),total_503=0,total_errors=0,missed_arrivals=0,
        dispatch_lag_summary=dict(p99_ms=0),pattern=cfg['traffic_pattern'],duration_sec=cfg['duration_sec'],target_rate=cfg['rate'],
        burst_low_rate=cfg['burst_low'],burst_high_rate=cfg['burst_high'],burst_period_sec=cfg['burst_period_sec'],
        burst_low_duration_sec=cfg['burst_low_duration_sec'],client_trace_enabled=True)


class RunnerIntegration(unittest.TestCase):
    def run_synthetic(self,mode):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);package=r.read(ROOT/'runtime_package.json');host=package['host']['id']
            r.write(root/'scientific/plan.json',r.read(ROOT/'scientific/plan.json'))
            r.write(root/'runtime_seal.json',dict(synthetic=True))
            directory=root/'runs'/host/'Go';directory.mkdir(parents=True)
            alloc=s.allocation(r.read(ROOT/'scientific/plan.json'),host,'Go')
            started=time.monotonic_ns();boot=r.identity(os.getpid())['boot_id']
            r.write(directory/'allocation.json',alloc)
            r.write(directory/'lifetime.json',dict(started_ns=started,boot_id=boot))
            r.write(directory/'workers/collect.json',r.identity(os.getpid()))
            events=[];test=self
            class Backend:
                def __init__(self,root,directory):
                    self.directory=directory
                    self.reader=adapters.OfferReader('Go',dict(c=go))
                def configs(self,role):return go.calibration_configs() if role=='calibration' else go.validation_configs()
                def begin(self,hook):self.hook=hook
                def case(self,cfg):return self.directory/'cases'/cfg['trial']
                def collect(self,cfg):
                    case=self.case(cfg);case.mkdir(parents=True)
                    events.append(cfg['role'])
                    if cfg['traffic_pattern']!='idle' and cfg['role']!='validation':r.write(case/'loadgen.json',synthetic_go_client(cfg))
                    if cfg['role']=='validation':
                        self.hook.before_trial(case,cfg)
                        r.write(case/'warmup.json',synthetic_go_client(go.warmup_config(cfg)))
                        self.hook.warmup_ready(case,cfg)
                        # No process, network or service is created here.
                        def create():
                            test.assertFalse((case/'loadgen.json').exists())
                            r.write(case/'loadgen.json',synthetic_go_client(cfg))
                            return type('Child',(),dict(pid=991))()
                        self.hook.spawn(case,cfg,'loadgen',create)
                    return dict(config=cfg,dispatch_exit=False,domain_exits=['synthetic_domain_exit']
                        if mode=='adverse' and cfg['role']=='validation' and cfg['profile']=='B' else [])
                def reference(self,cohorts,plan):
                    test.assertEqual(len(cohorts),16)
                    if mode=='failed_calibration':raise ValueError('synthetic calibration unqualified')
                    return [50]*676
                def target_values(self,case,cfg):return self.reader
            with patch.object(worker,'ROOT',root),patch.object(r,'verify_package',return_value=package),\
                 patch.object(r,'check_host',return_value=dict(synthetic=True)),patch.object(os,'sched_setaffinity'),\
                 patch.object(signal,'signal'),patch.object(go_backend,'Backend',Backend):
                if mode=='complete':worker.run(directory,'collect')
                else:
                    with self.assertRaises(ValueError):worker.run(directory,'collect')
            report=r.read(directory/'campaign_report.json')
            rows=[row for row in report['windows'] if row['campaign_id']==alloc['campaign']['id']]
            return rows,events,r.read(directory/'acquisition_cost.json')

    def test_complete_runner_keeps_all_18_slots_and_full_warmup_cost(self):
        rows,events,cost=self.run_synthetic('complete')
        self.assertEqual(events.count('calibration'),0)  # Go retains idle/steady/mixed role labels.
        self.assertEqual(events.count('validation'),18)
        self.assertTrue(all(row['status']=='primary_domain' for row in rows))
        warmups=[x for x in cost['raw_acquisitions'] if x['path'].endswith('warmup.json')]
        self.assertEqual(sum(x['declared_offers'] for x in warmups),4200)

    def test_failed_calibration_never_releases_a_target(self):
        rows,events,cost=self.run_synthetic('failed_calibration')
        self.assertNotIn('validation',events)
        self.assertTrue(all(row['status']=='unavailable' for row in rows))
        self.assertIn('unqualified',cost['error'])

    def test_first_adverse_target_is_retained_and_stops_remaining_slots(self):
        rows,events,cost=self.run_synthetic('adverse')
        self.assertEqual(events.count('validation'),2)
        self.assertEqual([x['status'] for x in rows[:3]],['primary_domain','applicability_exit','unavailable'])
        self.assertEqual(cost['stopped_stage'],'v31_b1_B')


if __name__=='__main__':unittest.main()
