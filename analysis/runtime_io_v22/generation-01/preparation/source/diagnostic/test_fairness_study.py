import collections
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import fairness_analysis as analysis
import fairness_study as study
import run
import trace_analysis


BUILD=dict(images=dict(stock='sha256:stock',patched='sha256:patched'),
           decoder='/tmp/decoder',decoder_sha256='abc')


def trial_rows():
    rows=[]
    for config in study.matrix(BUILD):
        row={field:1. for field in analysis.FIELDS}
        row.update(rep=config['rep'],runtime_mode=config['runtime_mode'],trace_coverage=1.,
                   rejection_fraction=0.,timeout_fraction=0.,runtime_trace=config['runtime_trace'],
                   runtime_trace_complete=True)
        row.update({f:1. for f in ('p99_pre_admission_ms','p99_resume_to_write_ms','p99_write_call_ms',
                                  'p99_write_to_exit_ms','p99_request_to_first_byte_ms','p99_first_byte_to_body_done_ms')})
        rows.append(row)
    return rows


class FairnessStudyTests(unittest.TestCase):
    def test_balanced_runtime_and_trace_with_original_workload(self):
        rows=study.matrix(BUILD)
        self.assertEqual(len(rows),16)
        self.assertEqual(len({r['run_id'] for r in rows}),16)
        for position in range(4):self.assertEqual({r['runtime_mode'] for r in rows[position::4]},set(study.MODES))
        pairs=collections.Counter((rows[b+i]['runtime_mode'],rows[b+i+1]['runtime_mode'])
                                  for b in range(0,16,4) for i in range(3))
        self.assertEqual(len(pairs),12);self.assertEqual(set(pairs.values()),{1})
        base=run.pilot_matrix()[0]
        changes={'run_id','rep','runtime_trace'}
        for row in rows:
            self.assertTrue(all(row[k]==v for k,v in base.items() if k not in changes))
            self.assertFalse(row['worker_yield']);self.assertTrue(row['custom_recording'])
            self.assertEqual(row['service_image'],BUILD['images'][row['runtime_variant']])

    def test_failures_are_maximum_not_median_and_latency_alone_cannot_pass(self):
        rows=trial_rows()
        result=analysis.screens(rows)
        self.assertTrue(result['patch_trace_off']['original_numeric_screens_passed'])
        bad=next(r for r in rows if r['runtime_mode']=='patched_off')
        bad['rejection_fraction']=.004
        for r in rows:
            if r['runtime_mode']=='patched_off':r['p99_e2e_ms']=.1
        result=analysis.screens(rows)['patch_trace_off']
        self.assertFalse(result['original_numeric_screens_passed'])
        self.assertEqual(result['max_rejection_plus_timeout']['patched_off'],.004)
        self.assertFalse(result['eligible_for_full'])
        self.assertTrue(result['throughput_review_required'])

    def test_each_cpu_latency_coverage_and_timing_screen(self):
        for field,value in [('cpu_usec_per_completed_work',1.2),('client_cpu_usec_per_scheduled',1.2),
                            ('p99_e2e_ms',1.2),('trace_coverage',.98),('p99_pre_admission_ms',None)]:
            rows=trial_rows()
            for row in rows:
                if row['runtime_mode']=='patched_off':row[field]=value
            self.assertFalse(analysis.screens(rows)['patch_trace_off']['original_numeric_screens_passed'])
        rows=trial_rows();rows[0]['p99_e2e_ms']=None
        self.assertIsNone(analysis.screens(rows)['patch_trace_off']['ratios']['p99_e2e_ms'])

    def test_contrasts_keep_null_traceoff_and_reject_missing_or_duplicates(self):
        rows=trial_rows()
        for row in rows:
            row['rejection_fraction']={'stock_off':.01,'stock_on':.05,'patched_off':.005,'patched_on':.015}[row['runtime_mode']]
            if not row['runtime_trace']:row['network_ready_p99_ms']=None
        result=analysis.contrasts(rows)
        self.assertAlmostEqual(result[0]['rejection_fraction_interaction'],-.03)
        self.assertIsNone(result[0]['network_ready_p99_ms_interaction'])
        for incomplete in (rows[1:],rows+[rows[0]]):
            with self.assertRaises(ValueError):analysis.contrasts(incomplete)
            with self.assertRaises(ValueError):analysis.screens(incomplete)

    def test_study_cannot_qualify_full(self):
        with patch.object(run,'verify_session',return_value=dict(fairness_study=True,pilot=False)):
            with self.assertRaisesRegex(RuntimeError,'cannot qualify'):run.require_pilot(Path('/tmp/study'))

    def test_native_decoder_refuses_unsealed_tool(self):
        with tempfile.TemporaryDirectory() as tmp:
            decoder=Path(tmp)/'decoder';decoder.write_text('changed')
            with self.assertRaisesRegex(ValueError,'decoder'):
                trace_analysis.parse_trace(Path(tmp)/'runtime.trace',decoder,'wrong-sha')

    def test_launcher_refuses_no_sleep_inhibitor_before_spawning(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(run,'require_quiet_host'),patch.object(study.build_fairness,'verify_manifest'), \
             patch.object(study.pipeline,'is_running',return_value=False), \
             patch.object(study.shutil,'which',return_value=None),patch.object(run.sp,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'systemd-inhibit'):study.launch(Path(tmp))
            spawn.assert_not_called()

    def test_launcher_checks_desktop_guard_before_spawning(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(run,'require_quiet_host',side_effect=RuntimeError('desktop open')), \
             patch.object(study.pipeline,'is_running',return_value=False),patch.object(run.sp,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'desktop open'):study.launch(Path(tmp))
            spawn.assert_not_called()

    def test_complete_valid_session_resumes_without_new_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);run.put(session/'metadata.json',{})
            run.put(session/'matrix.json',study.matrix(BUILD))
            lock=(session/'lock').open('a')
            with patch.object(study.build_fairness,'verify_manifest',return_value=BUILD), \
                 patch.object(run,'acquire_experiment_lock',return_value=lock), \
                 patch.object(study,'verify_frozen',return_value=dict(fairness_build=BUILD,topology='fixed')), \
                 patch.object(run.old,'check_topology',return_value='fixed'),patch.object(run,'capture',return_value=''), \
                 patch.object(run,'attempt_dirs',return_value=[Path('/tmp/valid')]),patch.object(run,'validate',return_value=True), \
                 patch.object(run,'run_attempt') as attempt,patch.object(run.old,'prepare_environment') as settle:
                study.collect(session)
            attempt.assert_not_called();settle.assert_not_called()

    def test_changed_build_refuses_resume_before_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);run.put(session/'metadata.json',{})
            lock=(session/'lock').open('a')
            with patch.object(study.build_fairness,'verify_manifest',return_value=BUILD), \
                 patch.object(run,'acquire_experiment_lock',return_value=lock), \
                 patch.object(study,'verify_frozen',return_value=dict(fairness_build={},topology='fixed')), \
                 patch.object(run,'run_attempt') as attempt:
                with self.assertRaisesRegex(RuntimeError,'changed'):study.collect(session)
            attempt.assert_not_called()

    def test_report_preserves_failed_performance_screen_and_all_outcomes(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);plan=study.matrix(BUILD);run.put(session/'matrix.json',plan)
            by_mode={(r['rep'],r['runtime_mode']):r for r in trial_rows()}
            for config in plan:
                directory=session/'attempts'/config['run_id']/'001';directory.mkdir(parents=True)
                run.put(directory/'complete.json',{})
                run.put(directory/'loadgen.json',dict(total_scheduled=100,total_success=90,total_503=8,
                    total_errors=2,requests=[dict(TimedOut=True),dict(TimedOut=False)]))
                run.put(directory/'server_metrics.json',dict(completed=92))
                run.put(directory/'trace_scheduler.json',{})
                run.put(directory/'trace_requests.json',{})
            def row(order,config,directory):
                value=dict(by_mode[(config['rep'],config['runtime_mode'])],run_id=config['run_id'])
                value.update(rejection_fraction=.08,timeout_fraction=.01)
                if config['runtime_variant']=='patched':value['cpu_usec_per_completed_work']=1.2
                return value
            waits=dict(network_ready_count=1,network_ready_unresolved_count=1,
                       network_ready_p50_ms=1.,network_ready_p99_ms=1.,network_ready_max_ms=1.)
            with patch.object(study,'verify_frozen'),patch.object(run,'validation_errors',return_value=[]), \
                 patch.object(analysis.analyze,'trial_row',side_effect=row),patch.object(run.sp,'run'), \
                 patch.object(trace_analysis,'parse_lines',return_value={}), \
                 patch.object(analysis.inspect_http_cleanup,'inspect',return_value=dict(wait_ms=dict(p99=1.),max_wait_ms=1.,requests_matched=1)), \
                 patch.object(analysis,'network_waits',return_value=waits) as network:
                analysis.analyze_session(session)
            self.assertEqual(network.call_count,8)
            self.assertTrue(run.read(session/'analysis/validation.json')['passed'])
            self.assertFalse(run.read(session/'analysis/screens.json')['patch_trace_off']['original_numeric_screens_passed'])
            self.assertFalse((session/'analysis/pilot_gate.json').exists())
            import csv
            with (session/'analysis/trials.csv').open() as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),16)
            self.assertEqual(float(rows[0]['all_failure_fraction']),.10)
            self.assertEqual(float(rows[0]['error_fraction']),.02)
            self.assertIn('FAIL',(session/'analysis/report.md').read_text())

    def test_missing_valid_attempt_stops_analysis_and_preserves_validation_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);run.put(session/'matrix.json',study.matrix(BUILD))
            with patch.object(study,'verify_frozen'):
                with self.assertRaisesRegex(RuntimeError,'0 of 16'):analysis.analyze_session(session)
            self.assertFalse(run.read(session/'analysis/validation.json')['passed'])
            self.assertFalse((session/'analysis/report.md').exists())


if __name__=='__main__':unittest.main()
