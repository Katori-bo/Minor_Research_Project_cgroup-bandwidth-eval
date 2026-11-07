import math
import unittest
import plan_execution_rate_qualification as p


class QualificationDesignTests(unittest.TestCase):
    def test_exact_ratio(self):
        self.assertEqual(p.ratio_interval(300, 200), [1.5, 1.5])

    def test_count_uncertainty_extrema(self):
        self.assertEqual(p.ratio_interval(300, 200, 10, 20), [290/220, 310/180])

    def test_unavailable_counts_are_not_zero_frequency(self):
        for values in [(0, 10), (10, 0), (10, 10, 0, 10), (10, 10, -1, 0), (math.inf, 10)]:
            with self.assertRaises(ValueError):
                p.ratio_interval(*values)

    def test_two_window_log_allocation(self):
        cpu, radius = 20_000_000, 43_496
        a = p.single_window_log_tolerance(cpu, radius)
        self.assertAlmostEqual(cpu * math.expm1(2 * a), radius/2)
        self.assertAlmostEqual(2 * radius/4, radius/2)

    def test_critical_against_analytic_cauchy(self):
        probability = 1 - p.FAMILY_ALPHA/(2*p.GATES)
        expected = math.tan(math.pi*(probability-.5))
        self.assertGreaterEqual(p.critical(2), expected)
        self.assertLess(p.critical(2)-expected, 1.01e-6)

    def test_more_gates_require_wider_intervals(self):
        self.assertGreater(p.critical(8, 14), p.critical(8, 6))

    def test_width_geometry_contains_and_predecessor_fails(self):
        n = p.width_only_n(176_857.21512351072, 20_000)
        self.assertLessEqual(p.critical(n)*176_857.21512351072/math.sqrt(n), 20_000)
        self.assertGreater(p.critical(n-1)*176_857.21512351072/math.sqrt(n-1), 20_000)
        self.assertIsNone(p.width_only_n(100, 20, center=20))

    def test_reserved_budget_is_preserved(self):
        cost = 292.1309516783337
        n = p.balanced_budget_n(cost)
        self.assertEqual(n, 8)
        self.assertLessEqual(n*cost+p.OVERHEAD_RESERVE_SEC, p.OVERHEAD_BUDGET_SEC)
        self.assertGreater((n+1)*cost+p.OVERHEAD_RESERVE_SEC, p.OVERHEAD_BUDGET_SEC)


if __name__ == '__main__':
    unittest.main()
