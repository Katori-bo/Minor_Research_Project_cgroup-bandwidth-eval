"""Synthetic-only checks: no Docker, sudo, real sampler, service or benchmark."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import types
import v24r3_common as c
import v24r3_model as model
import v24r3_study as runner
import v24r3_verify as verify
import v23_model as fifo
import v24r3_counter as counter
import v24r3_software as software
import subprocess
import os
import signal
import select
import json


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
    for i,r in enumerate(samples):
        r.update(scheduled_ns=r['before_ns'],thread_cpu_before_ns=i*1000,thread_cpu_after_ns=i*1000+500,read_errno=0)
    return dict(schema=3,sampler_revision='v24r3-native',cadence='absolute_skip_missed',record_capacity=6000,raw_capacity=4096,skipped_deadlines=0,thread_cpu_started_ns=0,thread_cpu_finished_ns=10000000,path='/owned/cpu.stat',interval_sec=.02,duration_bound_sec=110,
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


class V24NativeTests(unittest.TestCase):
    def test_qualification_runs_four_cells_and_stops_before_full_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp)
            def watcher(s,phase,seconds):
                self.assertEqual((phase,seconds),('qualification',1800))
                c.save(s/(phase+'_lifetime.json'),dict(started_monotonic=0,deadline_monotonic=1e12))
                return types.SimpleNamespace(),(s/'watch.log').open('w')
            with (patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),
                  patch.object(runner.run.old,'check_topology'),patch.object(runner,'bind_observer_inventory'),
                  patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'environment'),
                  patch.object(runner,'start_watchdog',side_effect=watcher),patch.object(runner.fixtures,'stop') as stop,
                  patch.object(runner,'collect_slot') as collect,
                  patch.object(runner.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as replay):
                runner.qualify(session,Path('/unused/audit'))
                self.assertEqual(collect.call_count,4)
                self.assertEqual([x.args[1] for x in collect.call_args_list],c.qualification_matrix())
                self.assertEqual(replay.call_args.args[0][2],'analyze-qualification')
                self.assertEqual(c.read(session/'qualification_collection_receipt.json')['completed_slots'],4)
                self.assertTrue((session/'qualification_finished.json').exists());self.assertTrue(stop.called)
                self.assertFalse((session/'measurement_lifetime.json').exists())

    def test_interrupted_qualification_cannot_auto_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);(session/'slots/q_b1_small_off/attempt-1').mkdir(parents=True)
            with (patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),
                  patch.object(runner.run.old,'check_topology'),patch.object(runner.os,'sched_setaffinity'),
                  patch.object(runner,'start_watchdog') as start):
                with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.qualify(session,None)
                start.assert_not_called()

    def test_native_cpu_time_inconsistent_with_wall_time_is_rejected(self):
        p=counter_fixture();p['samples'][1]['thread_cpu_after_ns']=p['samples'][1]['thread_cpu_before_ns']+2000
        with self.assertRaisesRegex(ValueError,'bracket'):model.validate_samples(p,'/owned/cpu.stat')

    def test_scientific_rules_and_fixed_schedules_match_original(self):
        import v24_common as original
        self.assertEqual(c.matrix(),original.matrix())
        self.assertEqual(c.design()['rules'],original.design()['rules'])
        self.assertEqual(c.design()['windows'],original.design()['windows'])
        for cfg in c.matrix():self.assertEqual(c.schedule(cfg),original.schedule(cfg))

    def test_native_decoder_preserves_every_raw_record_and_rejects_duplicates(self):
        record=dict(scheduled_ns=0,before_ns=0,after_ns=1000,
                    thread_cpu_before_ns=0,thread_cpu_after_ns=500,read_errno=0,
                    raw='usage_usec 10\nuser_usec 8\nsystem_usec 2\n')
        raw=dict(schema=3,sampler_revision='v24r3-native',samples=[record,dict(record)])
        decoded=counter.decode(raw)
        self.assertEqual(len(decoded['samples']),2)
        self.assertEqual(decoded['samples'][0]['cpu_stat']['usage_usec'],10)
        for text in ('usage_usec 10\nusage_usec 11\nuser_usec 8\nsystem_usec 2\n',
                     'usage_usec -1\nuser_usec 0\nsystem_usec 0\n','usage_usec 1\n'):
            bad=copy.deepcopy(raw);bad['samples'][0]['raw']=text
            with self.assertRaises(ValueError):counter.decode(bad)

    def test_native_executable_retains_raw_cpu_wall_times_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'synthetic.cpu.stat';out=Path(tmp)/'counter.raw.json'
            path.write_text('usage_usec 10\nuser_usec 8\nsystem_usec 2\n')
            with subprocess.Popen([str(c.BUILD/'counter'),'--path',str(path),'--output',str(out)],
                  stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                  preexec_fn=lambda:os.sched_setaffinity(0,{0,1})) as process:
                try:
                    self.assertTrue(select.select([process.stdout],[],[],2)[0])
                    self.assertEqual(os.read(process.stdout.fileno(),6),b'READY\n')
                    # Let real acquisitions run briefly; this is a regular-file software check.
                    process.wait(timeout=.12)
                except subprocess.TimeoutExpired:
                    process.send_signal(signal.SIGINT)
                finally:
                    stdout,stderr=process.communicate(timeout=5)
                    self.assertEqual(process.returncode,0,stderr)
            raw=c.read(out);probe=counter.decode(raw)
            model.validate_samples(probe,str(path));self.assertGreaterEqual(len(probe['samples']),2)
            self.assertEqual(probe['own_cpu_ns'],probe['thread_cpu_finished_ns']-probe['thread_cpu_started_ns'])
            saved=out.read_bytes()
            result=subprocess.run([str(c.BUILD/'counter'),'--path',str(path),'--output',str(out)],capture_output=True,timeout=3)
            self.assertNotEqual(result.returncode,0);self.assertEqual(saved,out.read_bytes())

    def test_native_error_preserved_and_long_input_not_silently_truncated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'large.cpu.stat';out=Path(tmp)/'counter.raw.json'
            path.write_text('usage_usec 1\nuser_usec 1\nsystem_usec 0\n'+'extra 0\n'*600)
            result=subprocess.run([str(c.BUILD/'counter'),'--path',str(path),'--output',str(out)],capture_output=True,timeout=3)
            self.assertNotEqual(result.returncode,0)
            raw=c.read(out);self.assertIsNotNone(raw['failure'])
            with self.assertRaisesRegex(ValueError,'acquisition'):counter.decode(raw)

    def test_window_quality_rejects_uncertainty_without_testing_hypothesis(self):
        phases={n:dict(cpu_usec_per_completion_bounds=[100,102],delivered_cpu_fraction_bounds=[.49,.50]) for n in ('busy','low')}
        self.assertTrue(model.window_quality(phases,c.design())['pass_budget'])
        phases['low']['cpu_usec_per_completion_bounds']=[100,105]
        with self.assertRaisesRegex(ValueError,'uncertainty'):model.window_quality(phases,c.design())
        phases['low']['cpu_usec_per_completion_bounds']=[100,102]
        phases['busy']['delivered_cpu_fraction_bounds']=[.48,.51]
        with self.assertRaisesRegex(ValueError,'uncertainty'):model.window_quality(phases,c.design())

    def test_qualification_checks_both_sizes_without_selecting_cost_shift(self):
        rows=[]
        for cfg in c.qualification_matrix():
            r=evaluate(cfg['size'],1,cfg['counter_probe']);r['trial']=cfg['trial']
            if cfg['counter_probe']:
                r['whole_over_busy_cost_bounds']=[1.0,1.02]
                r['phases']['busy']['delivered_cpu_fraction_bounds']=[.54,.55]
            rows.append(r)
        self.assertTrue(model.qualification_report(rows,c.design())['passed'])
        with self.assertRaisesRegex(ValueError,'four'):model.qualification_report(rows[:-1],c.design())
        next(r for r in rows if r['size']=='large' and r['counter_probe'])['busy_capacity_rps']*=1.1
        self.assertFalse(model.qualification_report(rows,c.design())['passed'])

    def test_full_study_is_blocked_before_trials_when_qualification_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp)
            with (patch.object(verify,'verify_preparation'),patch.object(verify,'verify_qualification',side_effect=ValueError('qualification missing')),
                 patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'collect_slot') as collect):
                with self.assertRaisesRegex(ValueError,'qualification missing'):runner.foreground(session)
                collect.assert_not_called()
                self.assertFalse((session/'measurement_lifetime.json').exists())

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
        model.validate_samples(q,'/owned/cpu.stat')
        q=copy.deepcopy(p);q['samples'][1]['after_ns']=q['samples'][1]['before_ns']-1
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
            with patch.object(verify,'verify_preparation'),patch.object(verify,'verify_qualification'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),\
                 patch.object(runner,'bind_observer_inventory'),patch.object(runner,'start_watchdog',side_effect=watcher),\
                 patch.object(runner,'environment'),patch.object(runner,'collect_slot'),patch.object(runner.os,'sched_setaffinity'),\
                 patch.object(runner.fixtures,'stop') as stop,patch.object(runner.subprocess,'run',side_effect=replay):
                runner.foreground(session,Path('/unused/audit'))

    def test_no_auto_resume_after_any_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);(session/'slots/first/attempt-1').mkdir(parents=True)
            with patch.object(verify,'verify_preparation'),patch.object(verify,'verify_qualification'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),\
                 patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'start_watchdog') as start:
                with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.foreground(session)
                start.assert_not_called()


if __name__=='__main__':unittest.main()
