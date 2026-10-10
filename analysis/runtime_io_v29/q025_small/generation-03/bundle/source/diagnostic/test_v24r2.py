"""Synthetic-only checks: no Docker, sudo, real sampler, service or benchmark."""
import copy
import gc
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import types
import v24r2_common as c
import v24r2_model as model
import v24r2_study as runner
import v24r2_verify as verify
import v23_model as fifo
import v24r2_counter as counter
import v24r2_software as software


def counter_fixture():
    samples=[]
    def usage(sec):
        if sec<0:return sec*.27
        cycle=int(sec//10);within=sec-cycle*10
        return cycle*3.85+.27*min(within,5)+.5*max(0,within-5)
    for i in range(3201):
        host=8e9+i*20e6;us=int(10e6+1e6*usage(host/1e9-10))
        samples.append(dict(before_ns=int(host-500),after_ns=int(host+500),
                            cpu_stat=dict(usage_usec=us,user_usec=us-100000,system_usec=100000)))
    return dict(schema=2,sampler_revision='v24r2-gc-suspended',
        gc_policy='suspended_during_bounded_capture',gc_was_enabled=True,
        gc_enabled_during_capture=False,gc_enabled_after_capture=True,
        gc_collections_before=[1,2,3],gc_collections_after=[1,2,3],
        path='/owned/cpu.stat',interval_sec=.02,duration_bound_sec=110,
        affinity=[0,1],failure=None,own_cpu_ns=10000000,started_ns=samples[0]['before_ns'],
        finished_ns=samples[-1]['after_ns'],samples=samples)


def phase_fixture(size='small',block=1,on=True):
    cfg=next(r for r in c.matrix() if r['size']==size and r['block']==block and r['counter_probe']==on)
    vec=c.schedule(cfg);mu=152 if size=='small' else 76
    points,_=fifo.simulate(vec,mu)
    jobs=[dict(id=r['id'],admission_ns=vec[r['id']],worker_start_ns=r['start_ns'],completion_ns=r['completion_sec']*1e9)
          for r in points if not r['rejected']]
    mapping=dict(client_test_start_ns=0,server_minus_client_lower_ns=0,server_minus_client_upper_ns=10000)
    derived=dict(clocks=mapping,summary=dict(cpu_usec_per_completed_work=3600 if size=='small' else 7200,timely_500_fraction=.9))
    server=dict(events=jobs,clock_generation=1)
    anchors=[dict(label=f'{phase}_{i}',before_ns=10_000_000_000-1000+stamp,after_ns=10_000_000_000+1000+stamp,
                  server_ns=stamp,generation=1) for phase,stamp in [('start',0),('stop',61_000_000_000)] for i in range(3)]
    probe=counter_fixture() if on else None
    return cfg,derived,server,anchors,probe


def evaluate(size='small',block=1,on=True):
    cfg,d,s,a,p=phase_fixture(size,block,on)
    return model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')


class V24Revision2Tests(unittest.TestCase):
    def test_full_recording_software_screen_requires_duration_and_coverage(self):
        p=counter_fixture()
        p['started_ns']=0;p['finished_ns']=110_000_000_000
        p['samples']=[dict(before_ns=i*20_000_000,after_ns=i*20_000_000+1000,
            cpu_stat=dict(usage_usec=i,user_usec=i,system_usec=0)) for i in range(5500)]
        summary=software.summarize(p,'/owned/cpu.stat')
        self.assertEqual(summary['samples'],5500)
        self.assertEqual(summary['gc_collections_during_capture'],[0,0,0])
        q=copy.deepcopy(p);q['finished_ns']=111_000_000_000
        with self.assertRaisesRegex(ValueError,'full110'):software.summarize(q,'/owned/cpu.stat')
        q=copy.deepcopy(p);del q['samples'][100:110]
        with self.assertRaisesRegex(ValueError,'gap'):software.summarize(q,'/owned/cpu.stat')
        q=copy.deepcopy(p);del q['samples'][-10:]
        with self.assertRaisesRegex(ValueError,'endpoints'):software.summarize(q,'/owned/cpu.stat')

    def test_original_scientific_design_and_schedules_are_retained(self):
        import v24_common as original
        self.assertEqual(c.DESIGN,original.DESIGN)
        self.assertEqual(c.matrix(),original.matrix())
        self.assertEqual(c.functional_configs(),original.functional_configs())
        for cfg in c.matrix():
            self.assertEqual(c.schedule(cfg),original.schedule(cfg))
            self.assertEqual(c.schedule(c.warmup_config(cfg)),original.schedule(original.warmup_config(cfg)))

    def test_original_failed_counter_records_still_fail_original_verifier(self):
        import v24_model as original
        paths=list((c.PREVIOUS/'slots/b1_small_on').glob('*/counter.json'))
        self.assertEqual(len(paths),2)
        for path in paths:
            probe=c.read(path)
            with self.assertRaisesRegex(ValueError,'bracket'):original.validate_samples(probe,probe['path'])

    def test_gc_state_restored_after_success_and_exception(self):
        original = gc.isenabled()
        try:
            for enabled in (True, False):
                (gc.enable if enabled else gc.disable)()
                with counter.suspend_cyclic_gc() as was_enabled:
                    self.assertIs(was_enabled, enabled)
                    self.assertFalse(gc.isenabled())
                self.assertIs(gc.isenabled(), enabled)
                with self.assertRaisesRegex(RuntimeError, 'synthetic'):
                    with counter.suspend_cyclic_gc():
                        self.assertFalse(gc.isenabled())
                        raise RuntimeError('synthetic')
                self.assertIs(gc.isenabled(), enabled)
        finally:
            (gc.enable if original else gc.disable)()

    def test_retained_full_length_record_count_has_no_gc_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.cpu.stat'
            p.write_text('usage_usec 10\nuser_usec 8\nsystem_usec 2\n')
            with counter.suspend_cyclic_gc():
                before=[r['collections'] for r in gc.get_stats()]
                samples=[counter.read_counter(p) for _ in range(6000)]
                self.assertEqual(len(samples),6000)
                self.assertEqual(before,[r['collections'] for r in gc.get_stats()])
                self.assertTrue(all(r['cpu_stat']['usage_usec']==10 for r in samples))

    def test_capture_records_gc_policy_and_preserves_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.cpu.stat';out=Path(tmp)/'counter.json'
            p.write_text('usage_usec 10\nuser_usec 8\nsystem_usec 2\n')
            remaining=iter([True,True,False])
            with patch.object(counter.time,'sleep'),patch.object(counter.os,'sched_getaffinity',return_value={0,1}):
                value=counter.capture(p,out,lambda:next(remaining))
            model.validate_samples(value,str(p))
            self.assertEqual(value['gc_collections_before'],value['gc_collections_after'])
            self.assertEqual(c.read(out.with_suffix('.ready.json')),value['samples'][0])
            self.assertEqual(c.read(out),value)
            saved=out.read_bytes()
            with self.assertRaisesRegex(ValueError,'overwrite'):counter.capture(p,out,lambda:False)
            self.assertEqual(saved,out.read_bytes())

    def test_capture_error_records_failure_and_restores_gc(self):
        original=gc.isenabled()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'missing.cpu.stat';out=Path(tmp)/'counter.json'
            with self.assertRaises(FileNotFoundError):counter.capture(p,out,lambda:True)
            self.assertIs(gc.isenabled(),original)
            value=c.read(out)
            self.assertIsNotNone(value['failure'])
            self.assertEqual(value['samples'],[])

    def test_gc_collection_or_policy_mismatch_rejected(self):
        for changes in (dict(schema=1),dict(gc_enabled_during_capture=True),
                        dict(gc_collections_after=[2,2,3]),dict(gc_enabled_after_capture=False),
                        dict(gc_collections_after=[True,2,3])):
            p=counter_fixture();p.update(changes)
            with self.assertRaisesRegex(ValueError,'GC policy'):model.validate_samples(p,'/owned/cpu.stat')

    def test_original_failure_width_remains_rejected(self):
        p=counter_fixture()
        p['samples'][3015]['after_ns']=p['samples'][3015]['before_ns']+3_408_707
        with self.assertRaisesRegex(ValueError,'bracket'):model.validate_samples(p,'/owned/cpu.stat')

    def test_missing_software_receipt_blocks_runtime_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(verify,'verify_software_receipt',side_effect=ValueError('missing repair check')),patch.object(runner,'command') as docker:
                with self.assertRaisesRegex(ValueError,'missing repair check'):runner.prepare_runtime(Path(tmp))
                docker.assert_not_called()

    def test_exact_schedules_and_matched_pairs(self):
        self.assertEqual(len(c.matrix()),12)
        for size,n in [('small',6792),('large',3396)]:
            selected=[r for r in c.matrix() if r['size']==size]
            self.assertEqual(len(selected),6)
            for b in range(1,4):
                pair=[r for r in selected if r['block']==b]
                self.assertEqual({r['counter_probe'] for r in pair},{False,True})
                self.assertEqual(c.schedule(pair[0]),c.schedule(pair[1]))
                self.assertEqual(len(c.schedule(pair[0])),n)
                self.assertEqual(n*pair[0]['iterations'],298848000)

    def test_treatment_requires_boolean_not_equal_integer(self):
        cfg=c.matrix()[0];c.validate_config(cfg)
        with self.assertRaisesRegex(ValueError,'boolean'):c.validate_config(dict(cfg,counter_probe=0))

    def test_counter_boundary_uses_enclosure_not_interpolation(self):
        samples=counter_fixture()['samples']
        result=model.counter_bounds(samples,10_001_000_000,10_002_000_000)
        self.assertEqual(result['usage_usec'],[10000000,10005400])

    def test_missing_and_wide_counter_boundary_rejected(self):
        samples=counter_fixture()['samples']
        with self.assertRaisesRegex(ValueError,'enclosing'):model.counter_bounds(samples,1,2)
        with self.assertRaisesRegex(ValueError,'60ms'):model.counter_bounds(samples[::5],10_001_000_000,10_002_000_000)

    def test_counter_monotonicity_and_read_width(self):
        p=counter_fixture();model.validate_samples(p,'/owned/cpu.stat')
        q=copy.deepcopy(p);q['samples'][1]['cpu_stat']['usage_usec']=0
        with self.assertRaisesRegex(ValueError,'backwards'):model.validate_samples(q,'/owned/cpu.stat')
        q=copy.deepcopy(p);q['samples'][1]['after_ns']+=3000000
        with self.assertRaisesRegex(ValueError,'bracket'):model.validate_samples(q,'/owned/cpu.stat')

    def test_phase_accounting_encloses_known_demand(self):
        for size,mu in [('small',152),('large',76)]:
            value=evaluate(size);p=value['phases']['busy'];bounds=p['cpu_usec_per_completion_bounds']
            self.assertLessEqual(bounds[0],.5e6/mu);self.assertGreaterEqual(bounds[1],.5e6/mu)
            self.assertTrue(p['state_eligible']);self.assertTrue(value['phases']['low']['state_eligible'])
            self.assertGreater(value['whole_over_busy_cost_bounds'][0],1.05)
            self.assertGreater(value['low_over_busy_cost_bounds'][0],1.05)

    def test_probe_off_has_no_inferred_phase_cpu(self):
        value=evaluate(on=False);self.assertNotIn('phases',value)
        cfg,d,s,a,p=phase_fixture(on=False)
        with self.assertRaisesRegex(ValueError,'off trial'):model.trial(d,s,a,counter_fixture(),cfg,c.design(),'/owned/cpu.stat')

    def test_missing_probe_and_measurement_gap_rejected(self):
        cfg,d,s,a,p=phase_fixture()
        with self.assertRaisesRegex(ValueError,'lacks counters'):model.trial(d,s,a,None,cfg,c.design(),'/owned/cpu.stat')
        p['samples']=[r for r in p['samples'] if not 12e9<r['before_ns']<12.15e9]
        with self.assertRaisesRegex(ValueError,'gap'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')

    def test_completion_counts_bound_shared_origin(self):
        counts=model.completion_bounds([0,10,20,30],(0,1),[(0,20e-9)])
        self.assertEqual(counts,[1,3])

    def test_all_pairs_and_both_sizes_required(self):
        rows=[evaluate(r['size'],r['block'],r['counter_probe']) for r in c.matrix()]
        result=model.report(rows,c.design());self.assertTrue(result['explanation_supported'])
        partial=model.report(rows[:-1],c.design());self.assertFalse(partial['complete']);self.assertFalse(partial['explanation_supported'])
        bad=copy.deepcopy(rows);next(r for r in bad if r['counter_probe'])['busy_capacity_rps']*=1.1
        result=model.report(bad,c.design());self.assertEqual(result['decision'],'observer_effect_unresolved')
        bad=copy.deepcopy(rows);next(r for r in bad if r['counter_probe'])['whole_over_busy_cost_bounds'][0]=1.01
        result=model.report(bad,c.design());self.assertFalse(result['explanation_supported']);self.assertTrue(result['observer_screen_pass'])
        with self.assertRaisesRegex(ValueError,'duplicate'):model.report(rows+[rows[0]],c.design())

    def test_phase_state_failure_is_retained(self):
        cfg,d,s,a,p=phase_fixture();s['events']=[dict(j,admission_ns=j['worker_start_ns']) for j in s['events']]
        value=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertFalse(value['phases']['busy']['state_eligible'])

    def test_delivery_difference_does_not_count_as_cost_explanation(self):
        rows=[evaluate(r['size'],r['block'],r['counter_probe']) for r in c.matrix()]
        next(r for r in rows if r['counter_probe'])['phases']['busy']['delivered_cpu_fraction_bounds']=[.55,.56]
        result=model.report(rows,c.design());self.assertFalse(result['explanation_supported'])

    def test_model_rejects_foreign_sampler_path(self):
        with self.assertRaisesRegex(ValueError,'identity'):model.validate_samples(counter_fixture(),'/another/cpu.stat')

    def test_counter_parser_brackets_only_the_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'cpu.stat';p.write_text('usage_usec 10\nuser_usec 8\nsystem_usec 2\n')
            with patch.object(counter.time,'monotonic_ns',side_effect=[100,200]):
                r=counter.read_counter(p)
            self.assertEqual((r['before_ns'],r['after_ns']),(100,200));self.assertEqual(r['cpu_stat']['usage_usec'],10)

    def test_unqualified_bundle_blocks_docker_before_any_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(verify,'verify_bundle',side_effect=ValueError('unqualified bundle')),patch.object(runner,'command') as docker:
                with self.assertRaisesRegex(ValueError,'unqualified'):runner.prepare_runtime(Path(tmp))
                docker.assert_not_called()

    def test_watchdog_cleans_only_its_owned_preparation_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);owner=dict(pid=11,uid=1000,start_ticks=1)
            c.save(s/'preparation_owner.json',dict(owner=owner));c.save(s/'preparation_lifetime.json',dict(deadline_monotonic=1e12))
            d=s/'preparation/functional/ours';d.mkdir(parents=True)
            c.save(d/'ownership.json',dict(owner=owner,container='ours',nonce='owned'))
            c.save(d/'counter_process.json',dict(pid=22,uid=1000,start_ticks=2))
            other=s/'preparation/foreign';other.mkdir();c.save(other/'ownership.json',dict(owner=dict(pid=99),container='foreign',nonce='foreign'))
            with patch.object(c,'same_process',side_effect=lambda p:p['pid']==22),patch.object(runner.os,'kill') as kill,patch.object(runner,'remove_owned') as remove:
                runner.session_watchdog(s,'preparation')
                remove.assert_called_once_with('ours','owned');kill.assert_called_once_with(22,runner.signal.SIGTERM)

    def test_saved_phase_accounting_tamper_fails_independent_replay(self):
        cfg,d,s,a,p=phase_fixture();expected=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);trial=session/'trial';trial.mkdir()
            manifest={key:key for key in ('image','server_sha256','loadgen_sha256','gate_sha256')}
            manifest['resource_baseline']={}
            c.save(trial/'config.json',cfg);c.save(trial/'complete.json',dict(valid=True,functional=False))
            c.save(trial/'derived.json',d);c.save(trial/'identity.json',manifest)
            c.save(trial/'initial.json',dict(resource_baseline={},cgroup='/owned'))
            c.save(trial/'server_metrics.json',s);c.save(trial/'host_server_anchors.json',a)
            c.save(trial/'environment.json',{});c.save(session/'environment.json',{})
            for name in ('warmup','loadgen'):c.save(trial/(name+'.json'),{})
            c.save(trial/'phase_accounting.json',expected);c.seal(trial)
            with patch.object(verify.raw,'replay',return_value=d),patch.object(verify,'counter_input',return_value=p),patch.object(c,'technical_client'):
                verify.verify_trial(session,trial,manifest)
                altered=copy.deepcopy(expected);altered['whole_over_busy_cost_bounds'][0]=100
                c.save(trial/'phase_accounting.json',altered);c.seal(trial)
                with self.assertRaisesRegex(ValueError,'independent replay'):verify.verify_trial(session,trial,manifest)

    def test_report_replay_occurs_after_watchdog_disarmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp)
            def watcher(s,phase,seconds):
                c.save(s/(phase+'_lifetime.json'),dict(started_monotonic=0,deadline_monotonic=1e12))
                return types.SimpleNamespace(),(s/'watch.log').open('w')
            def replay(argv,timeout):
                self.assertTrue((session/'measurement_finished.json').exists())
                self.assertTrue((session/'collection_receipt.json').exists())
                self.assertTrue(stop.called);self.assertEqual(timeout,600)
                return types.SimpleNamespace(returncode=0)
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),\
                 patch.object(runner,'bind_observer_inventory'),patch.object(runner,'start_watchdog',side_effect=watcher),\
                 patch.object(runner,'environment'),patch.object(runner,'collect_slot'),patch.object(runner.os,'sched_setaffinity'),\
                 patch.object(runner.fixtures,'stop') as stop,patch.object(runner.subprocess,'run',side_effect=replay):
                runner.foreground(session,Path('/unused/audit'))

    def test_no_auto_resume_after_any_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);(session/'slots/first/attempt-1').mkdir(parents=True)
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),\
                 patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'start_watchdog') as start:
                with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.foreground(session)
                start.assert_not_called()


if __name__=='__main__':unittest.main()
