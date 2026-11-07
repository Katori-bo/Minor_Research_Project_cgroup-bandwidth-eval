"""Synthetic-only scientific arithmetic and information-boundary oracles."""
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest

import evaluation as e
import freeze_design as design


class DecisionOracles(unittest.TestCase):
    def test_mixed_calibration_warmup_is_steady_low_rate(self):
        mixed=dict(traffic_pattern='bursty',low_rate=7.5,rate=19.15,duration_sec=60,
                   burst_low=7.5,burst_high=42.45,burst_period_sec=15,burst_low_duration_sec=10)
        warm=design.warmup_config(mixed)
        self.assertEqual(warm['traffic_pattern'],'steady')
        self.assertEqual(warm['rate'],7.5)
        vector=design.go_vector(warm)
        self.assertEqual(len(vector),150)
        self.assertEqual(vector[-1],19866666667)
    def test_equality_and_failures_use_all_offers(self):
        self.assertEqual(e.probability([10, 11, None], 10), (2, Fraction(2, 3)))
        self.assertEqual(e.point_decision(Fraction(1, 20)), 'meets')
        self.assertEqual(e.point_decision(Fraction(2, 39)), 'exceeds')

    def test_nearest_rank_ties_and_unavailable_failure_mass(self):
        self.assertEqual(e.cutoff([1] * 38 + [2, 3], '39/40'), 2)
        self.assertEqual(e.cutoff([1] * 40, '39/40'), 1)
        self.assertIsNone(e.cutoff([1] * 38 + [None, None], '39/40'))

    def test_positive_slack_small_error_flip(self):
        f = e.forecast([1] * 39 + [2], 1)
        s = e.score(f, [1] * 93 + [2] * 7, 1)
        self.assertTrue(s['positive_slack_small_error_false_assurance'])
        self.assertEqual(s['forecast_slack'], dict(numerator=1, denominator=40))
        self.assertEqual(s['absolute_error'], dict(numerator=9, denominator=200))

    def test_zero_margin_is_not_positive_margin_evidence(self):
        f = e.forecast([1] * 19 + [2], 1)
        s = e.score(f, [1] * 94 + [2] * 6, 1)
        self.assertTrue(s['false_assurance'])
        self.assertFalse(s['positive_slack_small_error_false_assurance'])
        self.assertEqual(f['dkw_decision'], 'inconclusive')

    def test_error_limit_does_not_mark_large_failure(self):
        f = e.forecast([1] * 99 + [2], 1)
        self.assertFalse(e.score(f, [2] * 100, 1)['positive_slack_small_error_false_assurance'])

    def test_recent_selection_charges_full_acquisition(self):
        reference, warmup = [1] * 100, [2] * 75 + [1] * 25
        cells = e.calibration_predictions(reference, [1])
        updated = e.warmup_predictions(reference, warmup, cells)[-1]['methods']
        self.assertEqual(updated['recent25']['offers'], 25)
        self.assertEqual(updated['recent25']['misses'], 0)
        self.assertEqual(updated['weighted_update']['offers'], 125)

    def test_all_abstention_has_undefined_assurance_risk(self):
        counts = dict(meets=0, exceeds=0, inconclusive=18, unavailable_deadline=0,
                      false_assurance=0, unnecessary_rejection=0, observed_compliant=18)
        rates = e.rates(counts, 36, 18)
        self.assertIsNone(rates['false_assurance_per_meets'])
        self.assertEqual(rates['answer_coverage_all_planned'], 0)
        self.assertEqual(rates['completed_availability'], .5)
        self.assertEqual(rates['unobserved_planned_windows'], 18)

    def test_no_observed_compliant_windows_is_undefined(self):
        counts = dict(meets=0, exceeds=18, inconclusive=0, unavailable_deadline=0,
                      false_assurance=0, unnecessary_rejection=0, observed_compliant=0)
        self.assertIsNone(e.rates(counts, 18, 18)['unnecessary_rejection_per_observed_compliant'])

    def test_invalid_duration_or_short_warmup_fails(self):
        for values in ([], [True], [1.1], [-1]):
            with self.assertRaises(ValueError): e.validate_values(values)
        with self.assertRaises(ValueError):
            e.warmup_predictions([1], [1] * 24, [])


class BarrierOracles(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 100
        self.barrier = e.DecisionBarrier(Path(self.temp.name) / 'attempt', 'plan', 'campaign',
                                         'boot', clock=lambda: self.now)

    def freeze(self):
        self.barrier.freeze_calibration([1] * 40, [1], dict(all_acquired_offers=40))
        digest = self.barrier.freeze_warmup('b1_A', [1] * 100, 100)
        self.barrier.prepare_target_start('b1_A', digest)
        return digest

    def test_target_cannot_precede_calibration_or_warmup(self):
        with self.assertRaises(ValueError):
            self.barrier.freeze_warmup('b1_A', [1] * 25, 100)
        with self.assertRaises(ValueError):
            self.barrier.record_target_release('b1_A', 'fake', 101, 'boot')

    def test_sealed_barrier_precedes_target_and_preserves_cost(self):
        digest = self.freeze()
        self.now = 102
        self.barrier.record_target_release('b1_A', digest, 101, 'boot')
        f = json.loads((self.barrier.directory / 'b1_A_forecast.json').read_text())
        self.assertEqual(f['acquired_warmup_offers'], 100)
        self.assertEqual(f['selected_warmup_offers'], 25)
        self.assertNotIn('target_outcomes', f)

    def test_late_seal_and_release_fail(self):
        self.barrier.freeze_calibration([1] * 40, [1], {})
        self.now = 1_000_000_101
        with self.assertRaises(ValueError):
            self.barrier.freeze_warmup('b1_A', [1] * 25, 100)
        self.now = 100
        digest = self.barrier.freeze_warmup('b1_A', [1] * 25, 100)
        self.barrier.prepare_target_start('b1_A', digest)
        self.now = 1_000_000_102
        with self.assertRaises(ValueError):
            self.barrier.record_target_release('b1_A', digest, self.now, 'boot')

    def test_boot_change_and_same_time_release_fail(self):
        digest = self.freeze()
        self.now = 102
        with self.assertRaises(ValueError):
            self.barrier.record_target_release('b1_A', digest, 101, 'other_boot')
        with self.assertRaises(ValueError):
            self.barrier.record_target_release('b1_A', digest, 100, 'boot')

    def test_mutated_receipt_fails(self):
        digest = self.freeze()
        path = self.barrier.directory / 'b1_A_forecast.json'
        path.write_text(path.read_text() + ' ')
        self.now = 102
        with self.assertRaises(ValueError):
            self.barrier.record_target_release('b1_A', digest, 101, 'boot')

    def test_no_permit_cannot_record_release(self):
        self.barrier.freeze_calibration([1] * 40, [1], {})
        digest = self.barrier.freeze_warmup('b1_A', [1] * 25, 100)
        self.now = 102
        with self.assertRaises(ValueError):
            self.barrier.record_target_release('b1_A', digest, 101, 'boot')

    def test_expired_start_permit_is_rejected_before_target(self):
        self.barrier.freeze_calibration([1] * 40, [1], {})
        digest = self.barrier.freeze_warmup('b1_A', [1] * 25, 100)
        self.now = 1_000_000_101
        with self.assertRaises(ValueError):
            self.barrier.prepare_target_start('b1_A', digest)
        self.assertFalse((self.barrier.directory / 'b1_A_permit.json').exists())

    def test_mutated_calibration_prevents_future_forecasts(self):
        self.barrier.freeze_calibration([1] * 40, [1], {})
        path = self.barrier.directory / 'calibration.json'
        path.write_text(path.read_text() + ' ')
        with self.assertRaises(ValueError):
            self.barrier.freeze_warmup('b1_A', [1] * 25, 100)

    def test_attempt_and_window_cannot_overwrite_or_resume(self):
        with self.assertRaises(FileExistsError):
            e.DecisionBarrier(self.barrier.directory, 'plan', 'campaign', 'boot')
        self.freeze()
        with self.assertRaises(FileExistsError):
            self.barrier.freeze_warmup('b1_A', [1] * 25, 100)


if __name__ == '__main__':
    unittest.main()
