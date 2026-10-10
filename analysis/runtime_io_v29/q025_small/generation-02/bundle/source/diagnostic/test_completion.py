from copy import deepcopy
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_completion as build
import completion_analysis as analysis
import completion_study as study
import run
from test_parallelism import fixture as entry_fixture


def fixture(arm='locked'):
    client,server=entry_fixture()
    for q in client['requests']: q['EndToEndLatencyNs']=600_000_000
    for e in server['entry_events']: e.update(entry_ns=1500,exit_ns=2500)
    server['events']=[dict(id=rid,admission_ns=1600,worker_start_ns=1800,completion_ns=2000) for rid in (0,2)]
    server['handler_events']=[dict(id=0,entry_ns=1500,resume_ns=2100,write_start_ns=2200,write_end_ns=2300,handler_exit_ns=2400)]
    if arm!='legacy':
        server.update(completion_protocol='publication-brackets-v1',recorder_mode=arm,record_errors=0,record_capacity=32768,
            completion_events=[dict(id=rid,record_start_ns=2001,record_lock_ns=2002,record_end_ns=2010,
                publish_start_ns=2020,publish_end_ns=2120) for rid in (0,2)])
    return client,server


def screen_rows():
    return [dict(rep=b,recorder_arm=a,timely_500_fraction=.7,timely_1000_fraction=.9,failure_fraction=.01,
        cpu_usec_per_completed_work=4000,p99_e2e_ms=1200,post_work_late_fraction=.05)
        for b in range(1,5) for a in ('legacy','locked','bounded')]


class CompletionTests(unittest.TestCase):
    def test_every_offered_outcome_and_publication_overlap_survive(self):
        result=analysis.classify(*fixture(),'locked')
        self.assertEqual(result['offered'],4);self.assertEqual(result['missing_entry_count'],1)
        self.assertEqual(result['deadlines']['500']['late_success_work_before'],1)
        self.assertEqual(result['deadlines']['500']['failure'],3)
        self.assertEqual(result['deadlines']['1000']['timely'],1)
        rows=result['requests'][:4]
        self.assertEqual(rows[0]['publication_to_resume_lower_ns'],0)
        self.assertEqual(rows[0]['publication_to_resume_upper_ns'],80)
        self.assertEqual(rows[2]['deadline_crossing'],'work_before_resume_unobserved')
        self.assertEqual(rows[3]['deadline_crossing'],'work_unobserved')
        self.assertEqual([r['outcome'] for r in rows],['success','rejected','timeout','error'])

    def test_legacy_has_no_invented_publication_marker(self):
        result=analysis.classify(*fixture('legacy'),'legacy')
        self.assertTrue(all(r['publish_start_lower_ns'] is None for r in result['requests']))
        self.assertTrue(all(r['publication_class']=='unobserved' for r in result['requests']))

    def test_clock_bound_deadline_crossing_remains_ambiguous(self):
        client,server=fixture()
        server['events'][0]['completion_ns']=500_001_200
        for key in ('record_start_ns','record_lock_ns','record_end_ns','publish_start_ns','publish_end_ns'):
            server['completion_events'][0][key]+=500_000_000
        for key in ('resume_ns','write_start_ns','write_end_ns','handler_exit_ns'):
            server['handler_events'][0][key]+=500_000_000
        row=analysis.classify(client,server,'locked')['requests'][0]
        self.assertEqual(row['deadline_crossing'],'work_ambiguous')
        self.assertLess(row['completion_lower_ns'],500_000_000)
        self.assertGreater(row['completion_upper_ns'],500_000_000)

    def test_bad_boundaries_missing_records_overflow_and_runtime_fail(self):
        for change in ('missing','duplicate','ordering','resume','overflow','mode','runtime'):
            client,server=fixture()
            if change=='missing': server['completion_events'].pop()
            elif change=='duplicate': server['completion_events'].append(deepcopy(server['completion_events'][0]))
            elif change=='ordering': server['completion_events'][0]['record_end_ns']=0
            elif change=='resume': server['completion_events'][0].update(publish_start_ns=2150,publish_end_ns=2160)
            elif change=='overflow': server['record_errors']=1
            elif change=='mode': server['recorder_mode']='bounded'
            else: server['runtime_capture']=True
            with self.assertRaises(ValueError,msg=change): analysis.classify(client,server,'locked')

    def test_csv_fields_are_stable_across_missing_evidence_and_arms(self):
        rows=[]
        for arm in ('legacy','locked','bounded'): rows+=analysis.classify(*fixture(arm),arm)['requests']
        stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(stream.getvalue())))),24)

    def test_observer_and_recorder_screens_are_separate_and_block_based(self):
        rows=screen_rows()
        self.assertEqual(analysis.compare(rows)['decision'],'qualified_for_scoped_control_preparation')
        rows[1]['timely_500_fraction']-=.02
        self.assertEqual(analysis.compare(rows)['decision'],'marker_effect_requires_review')
        rows=screen_rows();rows[2]['cpu_usec_per_completed_work']=4500
        self.assertEqual(analysis.compare(rows)['decision'],'recorder_effect_requires_review')
        rows=screen_rows();rows[1]['p99_e2e_ms']=None
        self.assertEqual(analysis.compare(rows)['decision'],'marker_effect_requires_review')
        with self.assertRaises(ValueError): analysis.compare(screen_rows()[:-1])

    def test_matrix_changes_only_recorder_and_image_and_balances_marker_order(self):
        plan=study.matrix(dict(images={a:a for a in ('legacy','locked','bounded')}))
        self.assertEqual(len(plan),12);self.assertEqual(len({c['run_id'] for c in plan}),12)
        excluded={'run_id','rep','recorder_arm','service_image'}
        self.assertEqual(len({tuple((k,v) for k,v in c.items() if k not in excluded) for c in plan}),1)
        self.assertEqual(sum(order.index('legacy')<order.index('locked') for order in study.ORDERS),2)
        self.assertTrue(all(c['require_quiet'] and c['gomaxprocs']==1 and c['workers']==4 for c in plan))

    def test_prepare_is_isolated_and_source_anchor_drift_fails(self):
        original=(run.HERE/'service/main.go').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            build.prepare(Path(tmp)/'prepared')
            source=(Path(tmp)/'prepared/service/main.go').read_text()
            self.assertIn('s.completionRunJob',source)
            self.assertIn('s.completionSnapshot',source)
            self.assertIn('clear(s.completionSlots)',source)
        self.assertEqual((run.HERE/'service/main.go').read_text(),original)
        with self.assertRaises(ValueError): build.service_source(original.replace('\ts.active++','\ts.active += 1'))

    def test_quiet_guard_prevents_benchmark_spawn(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(study.pipeline,'is_running',return_value=False),\
            patch.object(run,'require_quiet_host',side_effect=ValueError('desktop present')),\
            patch.object(study.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'desktop'): study.launch(Path(tmp))
            spawn.assert_not_called()

    def test_frozen_session_and_fixture_tampering_fail(self):
        for changed in ('source','matrix','prepared','fixture'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);bundle=root/'build';(bundle/'prepared').mkdir(parents=True)
                (bundle/'prepared/main.go').write_text('fixture');(bundle/'loadgen').write_bytes(b'fixture')
                value=dict(images={a:a for a in ('legacy','locked','bounded')},
                    prepared_sha256=build.stock.prepared_hashes(bundle/'prepared'),loadgen_sha256=run.sha(bundle/'loadgen'))
                run.put(bundle/'build.json',value);run.put(bundle/'functional_verification.json',dict(files_sha256={}))
                with patch.object(build,'DEFAULT',bundle),patch.object(run,'require_quiet_host'),\
                    patch.object(study.stock_study,'time_offsets'),patch.object(run.old,'check_topology',return_value={}),\
                    patch.object(run,'capture',return_value='fixture'),patch.object(run,'power_settings',return_value={}):
                    session=root/'session';study.create(session,value)
                    self.assertEqual(study.verify_session(session,current=False)['study'],'completion_qualification_v1')
                    target={'source':session/'source/diagnostic/completion_study.py','matrix':session/'matrix.json',
                        'prepared':session/'observer_build/prepared/main.go','fixture':session/'observer_build/functional_verification.json'}[changed]
                    target.write_text(target.read_text()+'\n')
                    with self.assertRaises(ValueError,msg=changed): study.verify_session(session,current=False)

    def test_progress_reports_twelve_and_analysis_without_starting_work(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run.old,'temperatures',return_value={}),\
            patch.object(study.pipeline,'is_running',return_value=True):
            directory=Path(tmp)
            self.assertEqual(study.snapshot(directory)['total'],12)
            run.put(directory/'workflow-status.json',dict(state='running',stage='analyze-observer'))
            self.assertEqual(study.snapshot(directory)['phase'],'analysis')

    def test_real_http_fixture_export_and_completion_seal(self):
        # Exercise report/CSV/sealing with unquotaed functional data. Fake CPU
        # counters are for serialization only, never performance evidence.
        if not (build.DEFAULT/'functional_verification.json').exists(): self.skipTest('build fixtures not prepared')
        with tempfile.TemporaryDirectory() as tmp,patch.object(study,'verify_session'),\
            patch.object(run,'validate',return_value=True),patch.object(study,'validate_attempt') as valid:
            directory=Path(tmp);session=directory/'session'
            plan=study.matrix(run.read(build.DEFAULT/'build.json'));run.put(session/'matrix.json',plan)
            for c in plan:
                target=session/'attempts'/c['run_id']/'001';target.mkdir(parents=True)
                arm=c['recorder_arm'];source=build.DEFAULT/f'fixture_{arm}_g1'
                for name in ('loadgen.json','server_metrics.json'): (target/name).write_bytes((source/name).read_bytes())
                run.put(target/'result.json',dict(cpu_usage_cores=.5,throttling_fraction=.5,cgroup_delta={'usage_usec':1000}))
                run.put(target/'complete.json',dict(functional_fixture=True))
            valid.side_effect=lambda path,c: analysis.classify(run.read(path/'loadgen.json'),run.read(path/'server_metrics.json'),c['recorder_arm'])
            study.analyze_results(directory)
            self.assertTrue((directory/'completion.json').exists())
            with (session/'analysis/requests.csv').open() as stream:
                self.assertEqual(len(list(csv.DictReader(stream))),144)
            study.verify_completion(directory)
            (session/'analysis/report.md').write_text('changed')
            with self.assertRaises(ValueError): study.verify_completion(directory)


if __name__=='__main__': unittest.main()
