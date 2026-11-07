import random
import unittest
from fractions import Fraction
import screen_deadline_scope as s


def records(values):return [dict(success=x is not None,e2e_ns=x) for x in values]


class DeadlineScope(unittest.TestCase):
    def test_equal_on_time_and_failed_mass(self):
        p=s.pool(records([10,20,None]));self.assertEqual(s.miss(p,20),Fraction(1,3))
        self.assertEqual(s.miss(p,19),Fraction(2,3));self.assertEqual(s.miss(p,10000),Fraction(1,3))

    def test_tied_values_and_tail_discrepancy(self):
        a=s.pool(records([10,10,None]));b=s.pool(records([10,10,10]))
        self.assertAlmostEqual(s.discrepancy(a,b)['maximum_pp'],100/3)
        self.assertEqual(s.discrepancy(a,b)['first_attaining_deadline_ns'],10)

    def test_zero_primary_error_can_hide_large_curve_error(self):
        a=s.pool(records([10,10,100,100]));b=s.pool(records([40,40,60,60]))
        self.assertEqual(s.miss(a,50),s.miss(b,50))
        self.assertEqual(s.discrepancy(a,b)['maximum_pp'],50)

    def test_union_support_against_exhaustive_deadlines(self):
        rng=random.Random(365)
        for _ in range(100):
            a=s.pool(records([rng.choice([None]+list(range(21))) for _ in range(8)]))
            b=s.pool(records([rng.choice([None]+list(range(21))) for _ in range(7)]))
            brute=max(abs(s.miss(a,d)-s.miss(b,d)) for d in range(31))
            self.assertAlmostEqual(s.discrepancy(a,b)['maximum_pp'],float(100*brute))

    def test_panel_has_no_target_input_and_preserves_missing_quantiles(self):
        p=s.pool(records([10,20,None,None]));panel=s.panel(p)
        self.assertEqual([d['deadline_ns'] for d in panel],[10,10,20,None,None])
        predicted=s.forecast({'reference':p},panel,15)
        s.discrepancy(p,s.pool(records([900]*100)))
        self.assertEqual(predicted,s.forecast({'reference':p},s.panel(p),15))

    def test_identical_and_all_failed_pools(self):
        p=s.pool(records([None,None]));q=s.pool(records([None]))
        self.assertEqual(s.discrepancy(p,q)['maximum_pp'],0)
        self.assertEqual(s.discrepancy(p,s.pool(records([0])))['maximum_pp'],100)


if __name__=='__main__':unittest.main()
