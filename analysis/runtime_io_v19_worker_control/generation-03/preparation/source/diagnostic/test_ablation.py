from collections import Counter
from copy import deepcopy
import csv
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import ablation_analysis as analysis
import ablation_study as study
import build_ablation as build
import run
from test_completion import fixture as completion_fixture


def fixture(arm):
    client,server=completion_fixture('legacy' if arm in ('legacy','clocks') else 'locked')
    if arm=='v13':return client,server
    if arm!='legacy':
        server.update(ablation_protocol='worker-buffer-ablation-v1',ablation_mode=arm,
            observer_pending_records=0,observer_dropped_records=0,observer_capacity_per_worker=16384)
        for k in ('completion_protocol','recorder_mode','record_capacity','record_errors'):server.pop(k,None)
    return client,server


def screen_rows():
    return [dict(rep=b,recorder_arm=arm,timely_500_fraction=.7,timely_1000_fraction=.9,
        failure_fraction=.01,cpu_usec_per_completed_work=4000,p99_e2e_ms=1200)
        for b in range(1,9) for arm in analysis.ARMS]


class AblationTests(unittest.TestCase):
    def test_six_arms_keep_all_offered_and_missing_markers_explicit(self):
        for arm in analysis.ARMS:
            result=analysis.classify(*fixture(arm),arm)
            self.assertEqual(result['arm'],arm);self.assertEqual(result['offered'],4)
            self.assertEqual(result['deadlines']['500']['failure'],3)
            self.assertEqual(result['deadlines']['500']['late_success_work_before'],1)
            if arm in ('legacy','clocks'):self.assertTrue(all(r['publish_start_lower_ns'] is None for r in result['requests']))
            else:self.assertEqual(result['requests'][0]['publication_to_resume_lower_ns'],0)

    def test_mode_drift_overflow_pending_duplicate_and_trace_are_rejected(self):
        for change in ('mode','pending','dropped','duplicate','trace'):
            c,s=fixture('passive')
            if change=='mode':s['ablation_mode']='mutex_early'
            elif change=='pending':s['observer_pending_records']=1
            elif change=='dropped':s['observer_dropped_records']=1
            elif change=='duplicate':s['completion_events'].append(deepcopy(s['completion_events'][0]))
            else:s['runtime_capture']=True
            with self.assertRaises(ValueError,msg=change):analysis.classify(c,s,'passive')
        c,s=fixture('clocks');s['completion_events']=[dict(id=0)]
        with self.assertRaises(ValueError):analysis.classify(c,s,'clocks')

    def test_48_trial_matrix_controls_and_order_are_balanced(self):
        plan=study.matrix(dict(images={a:a for a in analysis.ARMS}))
        self.assertEqual(len(plan),48);self.assertEqual(len({r['run_id'] for r in plan}),48)
        excluded={'run_id','rep','recorder_arm','service_image'}
        self.assertEqual(len({tuple((k,v) for k,v in r.items() if k not in excluded) for r in plan}),1)
        for position in range(6):self.assertEqual(Counter(order[position] for order in study.ORDERS[:6]),Counter(analysis.ARMS))
        for a in analysis.ARMS:
            for b in analysis.ARMS:
                if a!=b:self.assertEqual(sum(o.index(a)<o.index(b) for o in study.ORDERS),4)
        transitions=Counter((o[i],o[i+1]) for o in study.ORDERS[:6] for i in range(5))
        self.assertEqual(set(transitions.values()),{1});self.assertEqual(len(transitions),30)

    def test_candidate_qualification_is_separate_from_causal_contrasts(self):
        result=analysis.compare(screen_rows())
        self.assertTrue(result['candidate_within_screen']);self.assertFalse(result['eligible_for_controls'])
        rows=screen_rows();rows[2]['timely_500_fraction']-=.02
        self.assertFalse(analysis.compare(rows)['candidate_within_screen'])
        rows=screen_rows();rows[3]['cpu_usec_per_completed_work']=4500
        result=analysis.compare(rows)
        self.assertTrue(result['candidate_within_screen'])
        self.assertFalse(result['contrasts']['post_publication_mutex']['within_screen'])
        rows=screen_rows();rows[2]['p99_e2e_ms']=None
        self.assertFalse(analysis.compare(rows)['candidate_within_screen'])
        with self.assertRaises(ValueError):analysis.compare(screen_rows()[:-1])

    def test_observer_drain_waits_and_attempt_restores_original(self):
        pending=dict(admitted=1,completed=1,queue_len=0,active_handlers=0,observer_pending_records=1)
        drained=dict(pending,observer_pending_records=0)
        with patch.object(run,'get',side_effect=[pending,drained]),patch.object(study.time,'sleep') as sleep:
            self.assertEqual(study.observer_drain(),drained);sleep.assert_called_once_with(.1)
        original=run.drain
        with patch.object(study.stock_study,'run_checked_attempt',side_effect=ValueError('fixture')):
            with self.assertRaises(ValueError):study.run_observer_attempt(Path('/tmp/fixture'),{},1)
        self.assertIs(run.drain,original)

    def test_extra_observer_invalid_attempt_is_preserved_but_not_reused(self):
        with patch.object(study,'validate_attempt',side_effect=ValueError('observer dropped records')):
            result=study.attempt_check(Path('/tmp/fixture/001'),dict(run_id='fixture'))
            self.assertFalse(result['valid']);self.assertIn('dropped',result['error'])
        with patch.object(study,'validate_attempt',return_value={}):
            self.assertTrue(study.attempt_check(Path('/tmp/fixture/002'),dict(run_id='fixture'))['valid'])

    def test_quiet_guard_refuses_before_background_spawn(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(study.pipeline,'is_running',return_value=False),\
            patch.object(run,'require_quiet_host',side_effect=ValueError('desktop present')),patch.object(study.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'desktop'):study.launch(Path(tmp))
            spawn.assert_not_called()

    def test_prepare_is_isolated_and_anchor_drift_refuses(self):
        original=(run.HERE/'service/main.go').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            build.prepare(Path(tmp)/'prepared')
            source=(Path(tmp)/'prepared/service/main.go').read_text()
            self.assertIn('s.ablationPending()!=0',source)
            self.assertIn('s.resetAblation()',source)
        self.assertEqual((run.HERE/'service/main.go').read_text(),original)
        with self.assertRaises(ValueError):build.service_source(original.replace('func (s *service) worker() {','func altered() {'))

    def test_whole_frozen_bundle_and_source_tampering_are_detected(self):
        for changed in ('source','matrix','race','prepared'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);bundle=root/'build';(bundle/'prepared').mkdir(parents=True)
                (bundle/'prepared/main.go').write_text('fixture');(bundle/'loadgen').write_bytes(b'fixture')
                (bundle/'race_tests.log').write_text('race checks passed')
                value=dict(images={a:a for a in analysis.ARMS},prepared_sha256=build.stock.prepared_hashes(bundle/'prepared'),loadgen_sha256=run.sha(bundle/'loadgen'))
                run.put(bundle/'build.json',value);run.put(bundle/'functional_verification.json',dict(files_sha256={}))
                with patch.object(build,'DEFAULT',bundle),patch.object(run,'require_quiet_host'),\
                    patch.object(study.stock_study,'time_offsets'),patch.object(run.old,'check_topology',return_value={}),\
                    patch.object(run,'capture',return_value='fixture'),patch.object(run,'power_settings',return_value={}):
                    session=root/'session';study.create(session,value)
                    self.assertEqual(study.verify_session(session,current=False)['study'],'observer_ablation_v1')
                    p={'source':session/'source/diagnostic/ablation_study.py','matrix':session/'matrix.json',
                        'race':session/'observer_build/race_tests.log','prepared':session/'observer_build/prepared/main.go'}[changed]
                    p.write_text(p.read_text()+'\n')
                    with self.assertRaises(ValueError):study.verify_session(session,current=False)

    def test_remaining_count_and_not_started_status(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run.old,'temperatures',return_value={}):
            directory=Path(tmp);value=study.snapshot(directory)
            self.assertEqual((value['total'],value['remaining']),(48,48))
            run.put(directory/'session/status.json',dict(completed=17,total=48))
            self.assertEqual(study.snapshot(directory)['remaining'],31)

    def test_real_http_export_and_seal(self):
        if not (build.DEFAULT/'functional_verification.json').exists():self.skipTest('build fixtures not prepared')
        with tempfile.TemporaryDirectory() as tmp,patch.object(study,'verify_session'),\
            patch.object(run,'validate',return_value=True),patch.object(study,'validate_attempt') as valid:
            directory=Path(tmp);session=directory/'session'
            plan=study.matrix(run.read(build.DEFAULT/'build.json'));run.put(session/'matrix.json',plan)
            for c in plan:
                target=session/'attempts'/c['run_id']/'001';target.mkdir(parents=True)
                source=build.DEFAULT/f'fixture_{c["recorder_arm"]}_g1'
                for name in ('loadgen.json','server_metrics.json'):(target/name).write_bytes((source/name).read_bytes())
                run.put(target/'result.json',dict(cpu_usage_cores=.5,throttling_fraction=.5,cgroup_delta={'usage_usec':1000}))
                run.put(target/'complete.json',dict(functional_fixture=True))
            valid.side_effect=lambda path,c:analysis.classify(run.read(path/'loadgen.json'),run.read(path/'server_metrics.json'),c['recorder_arm'])
            study.analyze_results(directory);study.verify_completion(directory)
            with (session/'analysis/requests.csv').open() as stream:self.assertEqual(len(list(csv.DictReader(stream))),576)
            self.assertEqual(run.read(session/'analysis/validation.json')['trials'],48)
            (session/'analysis/report.md').write_text('changed')
            with self.assertRaises(ValueError):study.verify_completion(directory)


if __name__=='__main__':unittest.main()
