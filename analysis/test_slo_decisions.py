"""Numerical/accounting oracles for the fixed offline decision audit."""
from fractions import Fraction
import math
import unittest

import audit_slo_decisions as a


class DecisionContractTests(unittest.TestCase):
    def test_deadline_equality_and_failure_mass(self):
        self.assertEqual(a.miss([9, 10, 11, None], 10), Fraction(1, 2))

    def test_budget_equality_meets(self):
        self.assertEqual(a.decide(Fraction(15, 300)), 'meets')
        self.assertEqual(a.decide(Fraction(16, 300)), 'exceeds')

    def test_small_error_can_reverse_decision(self):
        value = a.classify(Fraction(4, 100), Fraction(6, 100))
        self.assertTrue(value['false_assurance'])
        self.assertTrue(value['within_5pp_false_assurance'])
        self.assertEqual(value['error_pp'], 2)
        self.assertEqual(value['forecast_budget_slack_pp'], 1)

    def test_unnecessary_rejection_and_direction(self):
        value = a.classify(Fraction(7, 100), Fraction(3, 100))
        self.assertTrue(value['unnecessary_rejection'])
        self.assertFalse(value['false_assurance'])
        self.assertLess(value['signed_underprediction_pp'], 0)

    def test_nearest_rank_and_failed_quantile(self):
        values = list(range(800))
        self.assertEqual(a.quantile_cutoff(values, '19/20')['rank'], 759)
        self.assertEqual(a.miss(values, 759), Fraction(1, 20))
        self.assertIsNone(a.quantile_cutoff([1, 2, None, None], '19/20')['deadline_ns'])

    def test_ties_lower_miss_fraction(self):
        self.assertEqual(a.quantile_cutoff([10]*20, '19/20')['deadline_ns'], 10)
        self.assertEqual(a.miss([10]*20, 10), 0)

    def test_band_boundary_and_no_assurance_coverage(self):
        self.assertEqual(a.band_decide(0, .05), 'meets')
        self.assertEqual(a.band_decide(.05, .1), 'inconclusive')
        self.assertEqual(a.band_decide(.051, .1), 'exceeds')
        forecast = a.forecast([10]*800, [10]*25, {}, 10)
        self.assertEqual(forecast['recent25']['point_decision'], 'meets')
        self.assertEqual(forecast['recent25']['iid_dkw_decision'], 'inconclusive')
        self.assertFalse(forecast['recent25']['transfer_guarantee'])

    def test_exact_binomial_closed_form_and_nist_example(self):
        low, high = a.binomial_interval(0, 100)
        self.assertEqual(low, 0)
        self.assertAlmostEqual(high, 1-math.pow(.025, 1/100), places=12)
        low, high = a.binomial_interval(4, 20, .10)
        self.assertAlmostEqual(low, .0713538843, places=8)
        self.assertAlmostEqual(high, .4010281173, places=8)

    def test_family_correction_widens_target_interval(self):
        plain = a.binomial_interval(20, 300)
        family = a.binomial_interval(20, 300, .05/100)
        self.assertLess(family[0], plain[0])
        self.assertGreater(family[1], plain[1])

    def test_invalid_input_rejected(self):
        for args in [(-1, 100), (101, 100), (0, 0)]:
            with self.assertRaises(ValueError):
                a.binomial_interval(*args)
        with self.assertRaises(ValueError):
            a.miss([], 10)
        with self.assertRaises(ValueError):
            a.miss([10], -1)


if __name__ == '__main__':
    unittest.main()
