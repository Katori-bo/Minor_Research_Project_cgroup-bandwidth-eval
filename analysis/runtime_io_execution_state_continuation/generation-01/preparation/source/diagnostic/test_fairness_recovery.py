from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import recover_fairness_metrics as recovery
import run
import fairness_study as study
from test_fairness_study import BUILD, trial_rows


class RecoveryTests(unittest.TestCase):
    def test_existing_output_and_session_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp)
            for output in (session, session / 'recovery'):
                with self.assertRaisesRegex(ValueError, 'fresh and outside'):
                    recovery.recover(session, output)

    def test_invalid_attempt_refused_without_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            session, output = Path(tmp) / 'session', Path(tmp) / 'recovery'
            session.mkdir()
            run.put(session / 'matrix.json', study.matrix(BUILD))
            with patch.object(study, 'verify_frozen'):
                with self.assertRaisesRegex(ValueError, '0 valid attempts'):
                    recovery.recover(session, output)
            self.assertFalse(output.exists())

    def test_partial_report_keeps_failure_and_raw_files_and_null_scheduler_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            session, output = Path(tmp) / 'session', Path(tmp) / 'recovery'
            session.mkdir()
            plan = study.matrix(BUILD)
            run.put(session / 'matrix.json', plan)
            (session / 'analysis/parsed').mkdir(parents=True)
            run.put(session / 'analysis/validation.json', dict(passed=False, issues=['retained failure']))
            rows = {(r['rep'], r['runtime_mode']): r for r in trial_rows()}
            for config in plan:
                attempt = session / 'attempts' / config['run_id'] / '001'
                attempt.mkdir(parents=True)
                run.put(attempt / 'loadgen.json', dict(total_scheduled=100, total_success=90,
                    total_503=8, total_errors=2, requests=[dict(TimedOut=True)]))
                run.put(attempt / 'server_metrics.json', dict(completed=92))
                run.put(attempt / 'trace_scheduler.json', {})
                run.put(attempt / 'trace_requests.json', dict(clock_mapping=dict(uncertainty_ns=1)))
                (session / 'analysis/parsed' / (config['run_id'] + '.txt')).write_text('')
            before = {p: p.read_bytes() for p in session.rglob('*') if p.is_file()}
            def row(order, config, attempt):
                result = dict(rows[config['rep'], config['runtime_mode']], run_id=config['run_id'])
                if config['runtime_variant'] == 'patched':
                    result['cpu_usec_per_completed_work'] = 1.2
                return result
            with patch.object(study, 'verify_frozen'), \
                 patch.object(run, 'validation_errors', return_value=[]), \
                 patch.object(run, 'provenance', return_value={}), \
                 patch.object(recovery.analyze, 'trial_row', side_effect=row), \
                 patch.object(recovery.trace_analysis, 'parse_lines', return_value={}), \
                 patch.object(recovery.cleanup, 'index_events', return_value={}), \
                 patch.object(recovery.cleanup, 'join', side_effect=ValueError('unresolved trace')):
                result = recovery.recover(session, output)
            self.assertEqual(len(result), 16)
            self.assertTrue(all(r['cleanup_wait_p99_ms'] is None and r['network_ready_p99_ms'] is None for r in result))
            self.assertEqual(before, {p: p.read_bytes() for p in before})
            self.assertFalse(run.read(session / 'analysis/validation.json')['passed'])
            self.assertFalse(run.read(output / 'recovery_status.json')['original_analysis_passed'])
            self.assertFalse(run.read(output / 'screens.json')['patch_trace_off']['original_numeric_screens_passed'])
            self.assertEqual(len(run.read(output / 'scheduler_audit.json')), 8)
            self.assertIn('FAIL', (output / 'report.md').read_text())
            self.assertFalse((session / 'completion.json').exists())


if __name__ == '__main__':
    unittest.main()
