"""Meaningful soundness and leakage tests for the new conditional guard."""
import math
import random
import unittest
from deadline_capacity_guard import diagnose, fifo, fit_reference


class GuardTests(unittest.TestCase):
    def test_exact_deadline_and_completion_arrival_ties(self):
        # Equality is timely; a completion exactly at an arrival frees its slot.
        self.assertEqual(fifo([0, 500_000_000], 2, system_slots=1)['misses'], 0)
        self.assertEqual(fifo([0], 1.999999)['misses'], 1)

    def test_rejections_count_in_offered_cohort(self):
        out = fifo([0] * 130, 1000)
        self.assertEqual(out['rejections'], 1)
        self.assertEqual(out['misses'], 1)
        self.assertEqual(out['offers'], 130)

    def test_reference_overflow_abstains(self):
        out = diagnose([0] * 130, 1000, [900, 1100], 0)
        self.assertEqual(out['decision'], 'insufficient_model_support')
        self.assertNotIn('conditional_error_bound_pp', out)

    def test_rejecting_point_does_not_break_reference_certificate(self):
        arrivals = list(range(0, 1_000_000_000, 1_000_000))
        out = diagnose(arrivals, 50, [999, 1001], 0, system_slots=2)
        self.assertGreater(out['point_forecast']['rejections'], 0)
        self.assertTrue(out['reference_family_rejection_free'])

    def test_randomized_bound_against_interior_capacities(self):
        rng = random.Random(2908102026)
        count = 0
        for _ in range(250):
            offsets = sorted(rng.randrange(0, 3_000_000_000) for _ in range(rng.randrange(2, 90)))
            lo = rng.uniform(10, 120)
            hi = lo + rng.uniform(0, 60)
            estimate = rng.uniform(5, 200)
            slots = rng.randrange(1, 100)
            deadline = rng.randrange(1, 900_000_001)
            out = diagnose(offsets, estimate, [lo, hi], 1.25,
                           deadline_ns=deadline, system_slots=slots)
            if out['decision'] == 'insufficient_model_support':
                continue
            count += 1
            for j in range(11):
                mu = lo + (hi-lo) * j/10
                target = fifo(offsets, mu, deadline, slots)['miss_pct']
                self.assertGreaterEqual(target + 1e-12, out['reference_model_miss_range_pct'][0])
                self.assertLessEqual(target, out['reference_model_miss_range_pct'][1] + 1e-12)
                for bias in (-1.25, 0, 1.25):
                    actual = min(100, max(0, target + bias))
                    error = abs(actual - out['point_forecast']['miss_pct'])
                    self.assertLessEqual(error, out['conditional_error_bound_pp'] + 1e-12)
        self.assertGreater(count, 100)

    def test_calibration_separation(self):
        row = dict(trial='a', role='mixed', block=1, state_eligible=True,
                   all_successful=True, busy_capacity_bounds_rps=[2, 2], miss_pct=0)
        other = dict(row, trial='b', block=2)
        fit = fit_reference([row], [other], {'b': [0, 1_000_000_000]})
        self.assertEqual(fit['margin_pp'], 0)
        for bad in (dict(other, role='validation'), dict(other, block=1), dict(other, trial='a')):
            with self.assertRaises(ValueError):
                fit_reference([row], [bad], {'b': [0]})

    def test_bad_inputs_refused(self):
        for offsets, capacity in (([], 1), ([True], 1), ([2, 1], 1), ([0], math.nan), ([0], -1)):
            with self.assertRaises(ValueError):
                fifo(offsets, capacity)
        with self.assertRaises(ValueError):
            diagnose([0], 1, [2, 1], 0)
        with self.assertRaises(ValueError):
            diagnose([0], 1, [1, 2], -1)


if __name__ == '__main__':
    unittest.main()
