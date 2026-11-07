import copy
from fractions import Fraction
import inspect
import unittest
import screen_deadline_sensitivity as s


class SensitivityTests(unittest.TestCase):
    def test_exact_medians_and_strict_cutoff(self):
        self.assertEqual(s.median([1,2]),Fraction(3,2))
        self.assertEqual(s.median([1,2,9]),2)
        self.assertEqual(s.miss([10,11,None],10),Fraction(2,3))
        self.assertEqual(s.miss([0,1,None],-1),1)
        with self.assertRaises(ValueError):s.median([1,None])

    def fixture(self):
        ref=[i*100000 for i in range(40)];cohorts=[ref[:20],ref[20:]]
        panel=s.scope.panel(s.scope.pool([dict(success=True,e2e_ns=x) for x in ref]))
        return ref,cohorts,[1000000]*25,panel

    def test_features_have_no_target_argument_and_no_mutation(self):
        args=self.fixture();before=copy.deepcopy(args)
        result=s.features(*args)
        self.assertEqual(args,before)
        self.assertEqual(set(inspect.signature(s.features).parameters),{'reference','cohorts','warmup','panel'})
        self.assertFalse(result['target_used'])
        # Scoring arbitrary future outcomes cannot change the feature record.
        for target in ([1000000000]*300,[0]*300):s.miss(target,1000000)
        self.assertEqual(result,s.features(*args))

    def test_complete_failure_mass_refuses_location_but_keeps_cdf(self):
        ref,cohorts,warm,panel=self.fixture();warm[0]=None
        result=s.features(ref,cohorts,warm,panel)
        self.assertFalse(result['location_available'])
        self.assertIsNone(result['scores_pp']['median_shift'])
        self.assertFalse(result['accepts']['median_shift'])
        self.assertTrue(all(x>=4 for x in result['predictions_pct']['warmup']))
        self.assertTrue(result['accepts']['always'])
        self.assertAlmostEqual(result['predictions_pct']['weighted_update'][-1],
            float(100*s.miss(ref+warm,panel[-1]['deadline_ns'])))

    def test_shift_direction_and_half_nanosecond_arithmetic(self):
        ref=[2,3,4,5];warm=[4]*25;panel=[dict(deadline_ns=3)]*5
        f=s.features(ref,[ref],warm,panel)
        self.assertEqual(f['median_delta_ns'],.5)
        self.assertEqual(f['predictions_pct']['reference'],[50]*5)
        self.assertEqual(f['predictions_pct']['location_shift'],[75]*5)
        warm=[3]*25
        self.assertEqual(s.features(ref,[ref],warm,panel)['predictions_pct']['location_shift'],[50]*5)

    def test_sensitivity_direction_includes_deadline_equality(self):
        ref=[100000,200000,300000,400000];panel=[dict(deadline_ns=200000)]*5
        f=s.features(ref,[ref],[200000]*25,panel)
        self.assertEqual(f['scores_pp']['sensitivity_100us'],25)
        self.assertEqual(f['scores_pp']['calibration_agreement'],0)

    def test_budget_and_reference_integrity_rejected(self):
        ref,cohorts,warm,panel=self.fixture()
        for args in ((ref,cohorts,warm[:-1],panel),(ref,cohorts,warm,panel[:-1]),
                     (ref,cohorts[:-1],warm,panel),(ref,cohorts,warm,[dict(deadline_ns=None)]*5)):
            with self.assertRaises(ValueError):s.features(*args)

    def row(self,score,signal,accept):
        return dict(features=dict(scores_pp=dict(x=signal),accepts=dict(x=accept)),
            methods=dict(reference=dict(maximum_error_pp=score,mean_error_pp=score)))

    def test_coverage_missed_warning_false_warning_and_no_answers(self):
        rows=[self.row(5,1,True),self.row(7,2,True),self.row(4,3,False),self.row(9,4,False)]
        score=s.warning_score(rows,'x')
        self.assertEqual(score['accepted'],2)
        self.assertEqual(score['accepted_errors_above_5pp'],1)
        self.assertEqual(score['rejected_errors_within_5pp'],1)
        self.assertEqual(score['coverage_pct'],50)
        for row in rows:row['features']['accepts']['x']=False
        score=s.warning_score(rows,'x')
        self.assertIsNone(score['accepted_maximum_error_pp'])
        self.assertEqual(score['accepted_errors_above_5pp'],0)
        self.assertEqual(score['coverage_pct'],0)

    def test_auc_ties_unavailable_and_one_class(self):
        rows=[self.row(3,0,True),self.row(8,2,True)]
        self.assertEqual(s.auc(rows,'x')['descriptive_auc'],1)
        rows[1]['features']['scores_pp']['x']=0
        self.assertEqual(s.auc(rows,'x')['descriptive_auc'],.5)
        rows[1]['features']['scores_pp']['x']=None
        result=s.auc(rows,'x')
        self.assertIsNone(result['descriptive_auc'])
        self.assertEqual(result['unavailable'],1)
        self.assertFalse(result['independent_pairs_established'])


if __name__=='__main__':unittest.main()
