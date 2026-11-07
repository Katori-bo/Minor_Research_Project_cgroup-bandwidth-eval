"""Contract and outcome-isolation checks for the100/200 replay."""
from fractions import Fraction
import unittest

import screen_continuous_persistence as p


def outcomes(n,misses,deadline=10):
    return [dict(success=True,e2e_ns=deadline+1 if i<misses else deadline) for i in range(n)]


class PersistenceTests(unittest.TestCase):
    def test_strict_deadline_and_failed_offers(self):
        rows=[dict(success=True,e2e_ns=9),dict(success=True,e2e_ns=10),
              dict(success=True,e2e_ns=11),dict(success=False,e2e_ns=None)]
        self.assertEqual(p.count(rows,10),2)

    def test_actual_offer_weighted_update(self):
        r=p.forecast(outcomes(800,640),outcomes(100,40),10,True)
        v=r['predictions']['sample_weighted_update']
        self.assertEqual(Fraction(v['misses'],v['offers']),Fraction(680,900))
        self.assertEqual(r['predictions']['original']['miss_pct'],80)
        self.assertEqual(r['predictions']['recent100']['miss_pct'],40)

    def test_half_agreement_discrete_boundary(self):
        probe=outcomes(50,20)+outcomes(50,22)
        self.assertTrue(p.forecast(outcomes(100,40),probe,10,True)['accept_recent100'])
        probe=outcomes(50,20)+outcomes(50,23)
        self.assertFalse(p.forecast(outcomes(100,40),probe,10,True)['accept_recent100'])

    def test_timing_violation_abstains(self):
        self.assertFalse(p.forecast(outcomes(100,50),outcomes(100,0),10,False)['accept_recent100'])

    def test_no_suffix_can_enter_forecast(self):
        reference=outcomes(100,50);probe=outcomes(100,50)
        before=p.forecast(reference,probe,10,True)
        cohort=probe+outcomes(200,0)
        cohort[100:]=outcomes(200,200)
        self.assertEqual(before,p.forecast(reference,cohort[:100],10,True))
        self.assertEqual(p.count(cohort[100:],10),200)

    def test_error_at_five_pp_is_retained_as_within_tolerance(self):
        f=p.forecast(outcomes(100,50),outcomes(100,50),10,True)
        row=dict(block=1,forecast=f,target_misses=110,observed_target_miss_pct=55)
        self.assertEqual(p.errors(row)['recent100'],5)
        self.assertEqual(p.method_summary([row],'recent100')['errors_above_5pp'],0)
        row['target_misses']=111
        self.assertEqual(p.method_summary([row],'recent100')['errors_above_5pp'],1)

    def test_guard_cannot_hide_bad_accepted_forecast(self):
        # Both halves agree yet future outcomes can shift completely.
        f=p.forecast(outcomes(100,50),outcomes(50,25)+outcomes(50,25),10,True)
        row=dict(block=1,forecast=f,target_misses=200,observed_target_miss_pct=100)
        result=p.summarize([row])
        self.assertEqual(result['guard']['bad_accepted'],1)
        self.assertFalse(result['guard']['useful_screen'])


if __name__=='__main__':unittest.main()
