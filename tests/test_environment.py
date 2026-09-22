import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import experiment as exp
from environment_controls import window_summary


def trace(start=60, slope=0, spike=False):
    return [{'elapsed_sec': i * 5, 'temperatures': {'k10temp:Tctl': start + slope * i / 12 + (4 if spike and i == 6 else 0)}} for i in range(13)]


class EnvironmentTests(unittest.TestCase):
    def test_stable_warmer_baseline_allowed(self):
        self.assertTrue(window_summary(trace(70), {'k10temp:Tctl': 70})['stable'])

    def test_drift_spike_and_baseline_departure(self):
        self.assertFalse(window_summary(trace(slope=1.5))['stable'])
        self.assertFalse(window_summary(trace(spike=True))['stable'])
        self.assertFalse(window_summary(trace(64), {'k10temp:Tctl': 60})['stable'])
        self.assertIsNone(window_summary(trace()[:12]))

    def test_missing_sensor_rejected(self):
        samples = trace()
        samples[-1]['temperatures'] = {}
        with self.assertRaisesRegex(RuntimeError, 'sensors'):
            window_summary(samples)

    def test_initial_idle_is_full_ten_minutes_and_logged(self):
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'settling.json'
            with patch.object(exp.time, 'monotonic', side_effect=lambda: clock[0]), \
                 patch.object(exp.time, 'sleep', side_effect=sleep), \
                 patch.object(exp, 'temperatures', return_value={'k10temp:Tctl': 60}), \
                 patch.object(exp, 'power_settings', return_value={'policies': {}}):
                summary = exp.settle(out, initial_idle=True, expected_power={'policies': {}})
            self.assertEqual(clock[0], 600)
            self.assertTrue(summary['stable'])
            record = json.loads(out.read_text())
            self.assertTrue(record['accepted'])
            self.assertEqual(len(record['samples']), 121)

    def test_power_change_fails_and_preserves_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'settling.json'
            with patch.object(exp, 'temperatures', return_value={'k10temp:Tctl': 60}), \
                 patch.object(exp, 'power_settings', return_value={'policies': {'mode': 'changed'}}):
                with self.assertRaisesRegex(RuntimeError, 'Power settings changed'):
                    exp.settle(out, expected_power={'policies': {}})
            self.assertFalse(json.loads(out.read_text())['accepted'])

    def test_stable_but_wrong_baseline_times_out_without_relaxation(self):
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        policy = dict(exp.POLICY, timeout_sec=15)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'settling.json'
            with patch.object(exp, 'POLICY', policy), \
                 patch.object(exp.time, 'monotonic', side_effect=lambda: clock[0]), \
                 patch.object(exp.time, 'sleep', side_effect=sleep), \
                 patch.object(exp, 'temperatures', return_value={'k10temp:Tctl': 70}), \
                 patch.object(exp, 'power_settings', return_value={'policies': {}}):
                with self.assertRaisesRegex(RuntimeError, 'did not stabilize'):
                    exp.settle(out, baseline={'k10temp:Tctl': 60})
            self.assertEqual(clock[0], 75)
            self.assertFalse(json.loads(out.read_text())['accepted'])
