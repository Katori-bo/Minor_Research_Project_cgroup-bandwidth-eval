import collections
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run
import yield_analysis


class YieldStudyTests(unittest.TestCase):
    def test_balanced_factorial_and_fixed_workload(self):
        rows = run.yield_matrix()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({r['run_id'] for r in rows}), 16)
        for position in range(4):
            self.assertEqual({r['yield_mode'] for r in rows[position::4]}, set(yield_analysis.MODES))
        pairs = collections.Counter((rows[b+i]['yield_mode'], rows[b+i+1]['yield_mode'])
                                    for b in range(0, 16, 4) for i in range(3))
        self.assertEqual(len(pairs), 12)
        self.assertEqual(set(pairs.values()), {1})
        for block in range(1, 5):
            self.assertEqual({(r['runtime_trace'], r['worker_yield']) for r in rows if r['rep'] == block},
                             {(False, False), (True, False), (False, True), (True, True)})
        fixed = ('workers', 'gomaxprocs', 'period_us', 'quota_us', 'rate', 'burst_low', 'burst_high',
                 'iterations', 'duration_sec', 'warmup_sec', 'timeout_sec', 'instrument',
                 'client_trace', 'trace_storage', 'custom_recording', 'require_quiet')
        self.assertEqual(len({tuple(r[k] for k in fixed) for r in rows}), 1)
        self.assertTrue(all(r['custom_recording'] and r['require_quiet'] for r in rows))
        self.assertTrue(all(not r['worker_yield'] for r in run.pilot_matrix()))

    def test_yield_evidence_must_match_strictly(self):
        config = dict(worker_yield=True)
        run.validate_worker_yield(dict(worker_yield=True), config)
        for state in ({}, dict(worker_yield=False), dict(worker_yield=1), dict(worker_yield='1')):
            with self.assertRaises(ValueError):
                run.validate_worker_yield(state, config)
        run.validate_worker_yield({}, {})  # Historical snapshots predate the field.

    def test_factorial_interaction_and_missing_values(self):
        rows = []
        values = {'plain': .01, 'trace': .05, 'yield': .005, 'yield_trace': .015}
        for block in range(1, 5):
            for mode, value in values.items():
                row = {field: value for field in yield_analysis.FIELDS}
                row.update(rep=block, yield_mode=mode)
                rows.append(row)
        result = yield_analysis.contrasts(rows)
        self.assertAlmostEqual(result[0]['rejection_fraction_trace_penalty_without_yield'], .04)
        self.assertAlmostEqual(result[0]['rejection_fraction_trace_penalty_with_yield'], .01)
        self.assertAlmostEqual(result[0]['rejection_fraction_interaction'], -.03)
        rows[0]['p99_e2e_ms'] = None
        self.assertIsNone(yield_analysis.contrasts(rows)[0]['p99_e2e_ms_interaction'])
        with self.assertRaises(ValueError):
            yield_analysis.contrasts(rows[1:])
        with self.assertRaises(ValueError):
            yield_analysis.contrasts(rows+[rows[0]])

    def test_yield_study_cannot_unlock_full(self):
        with patch.object(run, 'verify_session', return_value=dict(yield_study=True, pilot=False)):
            with self.assertRaisesRegex(RuntimeError, 'cannot qualify'):
                run.require_pilot(Path('/tmp/yield-study'))

    def test_schema8_retained_pilot_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            run.put(directory/'matrix.json', [{k: v for k, v in c.items() if k != 'worker_yield'}
                                              for c in run.pilot_matrix()])
            run.put(directory/'metadata.json', dict(schema=8, pilot=True,
                matrix_sha256=run.sha(directory/'matrix.json'),
                source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json')))
            run.verify_session(directory, check_current=False)
            with self.assertRaises(RuntimeError):
                run.verify_session(directory)

    def test_analysis_produces_study_summary_without_pilot_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp)
            plan = run.yield_matrix()
            run.put(session/'matrix.json', plan)
            for config in plan:
                directory = session/'attempts'/config['run_id']/'001'
                directory.mkdir(parents=True)
                run.put(directory/'loadgen.json', dict(total_errors=1, total_scheduled=100))
                run.put(directory/'trace_status.json', dict(io_events=[], io_events_dropped=0))
                run.put(directory/'complete.json', dict(schema=run.SCHEMA))
            def row(order, config, directory):
                result = {field: .01 for field in yield_analysis.FIELDS}
                return dict(result, rep=config['rep'], run_id=config['run_id'], order=order)
            cleanup = dict(requests_matched=100, wait_ms=dict(p99=1), max_wait_ms=2,
                           waits_at_least_1ms=1, reader_runnable_share=.99,
                           long_waits_reader_never_ran_before_cleanup=1)
            with patch.object(run, 'verify_session', return_value=dict(yield_study=True)), \
                 patch.object(run, 'validation_errors', return_value=[]), \
                 patch.object(yield_analysis.analyze, 'trial_row', side_effect=row), \
                 patch.object(yield_analysis.inspect_http_cleanup, 'inspect', return_value=cleanup) as call:
                yield_analysis.analyze_yield(session)
            self.assertEqual(call.call_count, 8)
            self.assertTrue(run.read(session/'analysis/validation.json')['passed'])
            self.assertFalse(run.read(session/'analysis/yield_summary.json')['eligible_for_full'])
            self.assertFalse((session/'analysis/pilot_gate.json').exists())


if __name__ == '__main__':
    unittest.main()
