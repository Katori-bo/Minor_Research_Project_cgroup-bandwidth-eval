import importlib.util
from pathlib import Path
import unittest
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('experiment', Path(__file__).resolve().parents[1] / 'scripts/experiment.py')
exp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exp)


class MatrixTests(unittest.TestCase):
    def test_design_and_matched_rates(self):
        cal = {'iterations': 45000, 'moderate_rps': 52, 'high_rps': 88.4}
        rows = exp.matrix(cal)
        self.assertEqual(len(rows), 300)
        self.assertEqual(len({r['run_id'] for r in rows}), 300)
        self.assertEqual(sum(r['period_us'] == 0 for r in rows), 60)
        self.assertEqual(rows, exp.matrix(cal))
        self.assertNotEqual(rows, exp.matrix(cal, seed=43))
        for r in rows:
            self.assertEqual(r['iterations'], 45000)
            self.assertAlmostEqual((r['burst_low'] + r['burst_high']) / 2, r['rate'])
            if r['period_us']:
                self.assertEqual(r['quota_us'] / r['period_us'], .5)

    def test_instrumentation_flags_not_scientific_outcome(self):
        report = {'loadgen_metrics': {'client_dropped': 0, 'missed_arrivals': 0,
            'dispatch_lag_summary': {'p99_ms': 1}}, 'monitor_samples': 59, 'config': {'duration_sec': 60}}
        self.assertEqual(exp.assess(report), [])
        report['monitor_samples'] = 0
        self.assertIn('insufficient_monitor_samples', exp.assess(report))

    def test_calibration_brackets_capacity_and_derives_rates(self):
        calls = []
        def fake_trial(session, phase, name, cfg, **kwargs):
            calls.append(cfg)
            return {'config': cfg, 'quality_flags': [], 'loadgen_metrics': {'total_success': 100},
                    'cgroup_metrics': {'delta': {'usage_usec': 500000}}}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(exp, 'trial', side_effect=fake_trial), patch.object(exp, 'stable_capacity', side_effect=lambda r: r['config']['rate'] <= 95):
                cal = exp.calibrate(Path(tmp))
            self.assertLessEqual(cal['capacity_stable_rps'], 95)
            self.assertGreater(cal['capacity_unstable_rps'], 95)
            self.assertLess(cal['capacity_unstable_rps'] - cal['capacity_stable_rps'], 3)
            self.assertAlmostEqual(cal['high_rps'], round(cal['capacity_stable_rps'] * .85, 2))

    def test_no_capacity_fallback_without_bracket(self):
        def fake_trial(session, phase, name, cfg, **kwargs):
            return {'config': cfg, 'quality_flags': [], 'loadgen_metrics': {'total_success': 100},
                    'cgroup_metrics': {'delta': {'usage_usec': 500000}}}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(exp, 'trial', side_effect=fake_trial), patch.object(exp, 'stable_capacity', return_value=True):
                with self.assertRaisesRegex(RuntimeError, 'bracket'):
                    exp.calibrate(Path(tmp))
