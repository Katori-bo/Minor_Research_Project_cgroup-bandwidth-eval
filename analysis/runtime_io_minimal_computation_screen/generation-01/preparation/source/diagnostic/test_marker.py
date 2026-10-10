from collections import Counter
from copy import deepcopy
import tempfile
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch

import marker_analysis as analysis
import marker_study as study
import build_marker as build
import run
from test_completion import fixture as completion_fixture


def fixture(arm):
    c,s=completion_fixture('legacy')
    if arm=='v14_clocks':
        s.update(ablation_protocol='worker-buffer-ablation-v1',ablation_mode='clocks',
            observer_pending_records=0,observer_dropped_records=0,observer_capacity_per_worker=16384)
    elif arm!='legacy':
        s.update(marker_protocol='inline-clock-screen-v1',marker_arm=arm,marker_clock_calls=build.COUNTS[arm])
    return c,s


def screen_rows():
    return [dict(rep=b,recorder_arm=a,timely_500_fraction=.7,timely_1000_fraction=.9,
        failure_fraction=.01,cpu_usec_per_completed_work=4000,p99_e2e_ms=1200)
        for b in range(1,5) for a in analysis.ARMS]


class MarkerTests(unittest.TestCase):
    def test_all_offered_outcomes_and_unobserved_publication(self):
        for a in analysis.ARMS:
            result=analysis.classify(*fixture(a),a)
            self.assertEqual(result['offered'],4)
            self.assertEqual(result['deadlines']['500']['failure'],3)
            self.assertEqual(result['deadlines']['500']['late_success_work_before'],1)
            self.assertTrue(all(r['publish_start_lower_ns'] is None for r in result['requests']))

    def test_schema_drift_and_unexpected_records_fail(self):
        for kind in ('count','mode','records','trace','yield'):
            c,s=fixture('before_one')
            if kind=='count':s['marker_clock_calls']=5
            elif kind=='mode':s['marker_arm']='rebuilt_zero'
            elif kind=='records':s['completion_events']=[dict(id=0)]
            elif kind=='trace':s['runtime_capture']=True
            else:s['worker_yield']=True
            with self.assertRaises(ValueError):analysis.classify(c,s,'before_one')
        c,s=fixture('v14_clocks');s['observer_pending_records']=1
        with self.assertRaises(ValueError):analysis.classify(c,s,'v14_clocks')

    def test_fixed_24_trial_matrix_and_pair_order_balance(self):
        plan=study.matrix(dict(images={a:a for a in analysis.ARMS}))
        self.assertEqual(len(plan),24);self.assertEqual(len({r['run_id'] for r in plan}),24)
        self.assertEqual(len(set(study.ORDERS)),4)
        excluded={'run_id','rep','recorder_arm','service_image'}
        self.assertEqual(len({tuple((k,v) for k,v in r.items() if k not in excluded) for r in plan}),1)
        for a in analysis.ARMS:
            for b in analysis.ARMS:
                if a!=b:self.assertEqual(sum(o.index(a)<o.index(b) for o in study.ORDERS),2)

    def test_screen_cannot_promote_full_recorder_or_controls(self):
        result=analysis.compare(screen_rows())
        self.assertTrue(result['candidate_within_screen']);self.assertFalse(result['eligible_for_controls'])
        self.assertIn('recording_qualification',result['decision'])
        rows=screen_rows();rows[4]['timely_500_fraction']-=.02
        self.assertFalse(analysis.compare(rows)['candidate_within_screen'])
        rows=screen_rows();rows[4]['p99_e2e_ms']=None
        self.assertFalse(analysis.compare(rows)['candidate_within_screen'])
        with self.assertRaises(ValueError):analysis.compare(screen_rows()[:-1])

    def test_original_worker_and_sha_source_retained_no_runtime_dispatch(self):
        original=(run.HERE/'service/main.go').read_text()
        stock=build.stock.service_source(original)
        worker=stock[stock.index('func (s *service) worker()'):stock.index('func (s *service) runJob(')]
        for arm,n in build.COUNTS.items():
            source=build.service_source(original,arm)
            self.assertEqual(source.count('_ = time.Since(markerOrigin)'),n)
            self.assertEqual(source[source.index('func (s *service) worker()'):source.index('func (s *service) runJob(')],worker)
            self.assertNotIn('ablationWorker',source);self.assertNotIn('configureAblation',source)
            if n>=2:
                self.assertIn('markerOrigin := s.origin',source)
                self.assertIn('j.reply <- answer // Buffered: timed-out clients never strand a worker.\n\t_ = time.Since(markerOrigin)',source)
            self.assertLess(source.index('s.completed++'),source.index('j.reply <- answer'))
        self.assertEqual((run.HERE/'service/main.go').read_text(),original)
        with self.assertRaises(ValueError):build.service_source(original.replace('j.reply <- answer','j.reply <- changed'),'before_one')

    def test_actual_assembly_normalization_keeps_instruction_immediates(self):
        raw='TEXT main.work(SB)\n main.go:12 0x123456 4883ec20 SUBQ $0x20, SP\n main.go:13 0x123459 e9000000 JMP 0x124567\n'
        self.assertEqual(build.normalized_assembly(raw),'SUBQ $0x20, SP\nJMP ADDR')

    def test_quiet_host_refuses_before_spawn_and_stop_refuses_pid_reuse(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(study.pipeline,'is_running',return_value=False),\
            patch.object(run,'require_quiet_host',side_effect=ValueError('desktop present')),patch.object(study.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'desktop'):study.launch(Path(tmp))
            spawn.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);run.put(p/'launch.json',dict(pid=10,start_tick='old'));run.put(p/'workflow-status.json',dict(worker_pid=11))
            with patch.object(study.pipeline,'is_running',return_value=True),patch.object(study.pipeline,'process_signature',return_value='new'),patch.object(study.os,'kill') as kill:
                with self.assertRaisesRegex(ValueError,'PID changed'):study.stop(p)
                kill.assert_not_called()

    def test_new_environment_is_measured_then_retained_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp)
            power=dict(policies={},platform_profile='balanced',external_power={'AC':'1'},desktop_profile='balanced')
            summary=dict(sensors={'test':dict(mean_c=44.0)})
            with patch.object(run.old,'power_settings',return_value=power),patch.object(run.old,'settle',return_value=summary) as settle:
                run.old.prepare_environment(session)
                self.assertEqual(run.read(session/'environment.json')['baseline_c'],{'test':44.0})
                self.assertNotIn('baseline',settle.call_args.kwargs)
                run.old.prepare_environment(session)
                self.assertEqual(settle.call_args.args[1],{'test':44.0})
                self.assertEqual(run.read(session/'environment.json')['baseline_c'],{'test':44.0})

    def test_progress_total_remaining_and_failed_attempt_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            value=study.snapshot(Path(tmp));self.assertEqual((value['total'],value['remaining']),(24,24))
            run.put(Path(tmp)/'session/status.json',dict(completed=17,total=24,current=None))
            value=study.snapshot(Path(tmp));self.assertEqual(value['remaining'],7)
        with patch.object(study,'validate_attempt',side_effect=ValueError('marker count changed')):
            self.assertFalse(study.attempt_check(Path('/tmp/001'),dict(run_id='test'))['valid'])

    def test_frozen_environment_tamper_refuses_before_resume_cooling(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);run.put(p/'environment.json',dict(baseline_c={'test':44.0}))
            run.put(p/'initial-settling.json',dict(accepted=True))
            run.put(p/'environment_seal.json',dict(files_sha256={n:run.sha(p/n) for n in ('environment.json','initial-settling.json')}))
            study.verify_environment(p,required=True)
            run.put(p/'environment.json',dict(baseline_c={'test':59.0}))
            with patch.object(run.old,'prepare_environment') as prepare:
                with self.assertRaisesRegex(ValueError,'environment changed'):study.prepare_environment(p)
                prepare.assert_not_called()

    def test_accepted_new_idle_baseline_is_sealed_before_first_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'attempts').mkdir()
            power=dict(policies={},platform_profile='balanced',external_power={'AC':'1'},desktop_profile='balanced')
            samples=[dict(elapsed_sec=t,temperatures={'test':44.0},power_settings=run.comparable_power(power)) for t in range(0,661,5)]
            def prepare(session):
                run.put(session/'environment.json',dict(policy=run.POLICY,power_settings=power,baseline_c={'test':44.0}))
                run.put(session/'initial-settling.json',dict(policy=run.POLICY,accepted=True,samples=samples))
            with patch.object(run.old,'prepare_environment',side_effect=prepare):study.prepare_environment(p)
            study.verify_environment(p,required=True)
            self.assertEqual(set(run.read(p/'environment_seal.json')['files_sha256']),{'environment.json','initial-settling.json'})
            (p/'initial-settling.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'environment changed'):study.verify_environment(p,required=True)

    def test_verified_build_and_fixtures_seal_export_and_tamper(self):
        if not (build.DEFAULT/'verification.json').exists():
            self.skipTest('functional fixtures not built yet')
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);session=directory/'session';session.mkdir()
            run.put(session/'environment_seal.json',dict(fixture=True))
            value=run.read(build.DEFAULT/'build.json');run.put(session/'matrix.json',study.matrix(value))
            fixtures={a:Path(build.DEFAULT/f'fixture_{a}_g1') for a in analysis.ARMS}
            def validated(p,c):return analysis.classify(run.read(fixtures[c['recorder_arm']]/'loadgen.json'),run.read(fixtures[c['recorder_arm']]/'server_metrics.json'),c['recorder_arm'])
            def trial_row(order,c,p):
                row=screen_rows()[0].copy();row.update(order=order,run_id=c['run_id'],rep=c['rep'],recorder_arm=c['recorder_arm'])
                return row,{}
            for c in study.matrix(value):
                p=session/'attempts'/c['run_id']/'001';p.mkdir(parents=True)
                for name in ('loadgen.json','server_metrics.json'):(p/name).write_bytes((fixtures[c['recorder_arm']]/name).read_bytes())
                run.put(p/'complete.json',dict(fixture=True))
            with patch.object(study,'verify_session',return_value={}),patch.object(study,'validate_attempt',side_effect=validated),patch.object(study.stock_analysis,'trial_row',side_effect=trial_row):
                study.analyze_results(directory);study.verify_completion(directory)
                self.assertEqual(run.read(session/'analysis/validation.json')['trials'],24)
                self.assertFalse(run.read(session/'analysis/observer_screen.json')['eligible_for_controls'])
                (session/'analysis/report.md').write_text('changed')
                with self.assertRaisesRegex(ValueError,'analysis changed'):study.verify_completion(directory)

    def test_real_build_bundle_and_frozen_session_reject_compiler_audit_tamper(self):
        if not (build.DEFAULT/'verification.json').exists():self.skipTest('verified build not ready')
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/'bundle';shutil.copytree(build.DEFAULT,bundle)
            with patch.object(run,'image_id',side_effect=lambda image:image),patch.object(run,'capture',return_value='{"research.runtime.variant":"stock"}'):
                self.assertEqual(build.verify(bundle),run.read(bundle/'build.json'))
                (bundle/'compiler_audit/legacy.work.txt').write_text('changed')
                with self.assertRaisesRegex(ValueError,'verification files changed'):build.verify(bundle)
            session=Path(tmp)/'session'
            with patch.object(run,'require_quiet_host'),patch.object(study.stock_study,'time_offsets'),\
                patch.object(run.old,'check_topology',return_value={'fixture':True}),patch.object(run,'capture',return_value='fixture'),\
                patch.object(run,'power_settings',return_value={'fixture':True}):
                study.create(session,run.read(build.DEFAULT/'build.json'))
            study.verify_session(session,current=False)
            (session/'marker_build/compiler_audit/legacy.work.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError,'bundle changed'):study.verify_session(session,current=False)


if __name__=='__main__':unittest.main()
