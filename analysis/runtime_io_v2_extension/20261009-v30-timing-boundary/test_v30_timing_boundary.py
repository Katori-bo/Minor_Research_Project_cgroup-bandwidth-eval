import unittest
from investigate_v30_timing_boundary import empirical_misses,independent_misses,select_calibration,categories


class BoundaryTests(unittest.TestCase):
    def test_exact_boundary_and_ties_are_timely(self):
        self.assertEqual(empirical_misses([9000000,10000000,10000000,11000000],10),25)
        with self.assertRaises(ValueError):empirical_misses([],10)
        with self.assertRaises(ValueError):empirical_misses([-1],10)

    def test_convolution_against_brute_force_with_correlated_pairs(self):
        workers=[4,8];residuals=[8,4]
        self.assertEqual(independent_misses(workers,residuals,.000012),25)
        self.assertEqual(empirical_misses([a+b for a,b in zip(workers,residuals)],.000012),0)

    def test_validation_and_duplicate_calibration_inputs_rejected(self):
        with self.assertRaises(ValueError):select_calibration([(dict(trial='v',role='validation'),dict(requests=[]))])
        entry=(dict(trial='a',role='idle'),dict(requests=[]))
        with self.assertRaises(ValueError):select_calibration([entry,entry])

    def test_no_queue_filter_and_negative_stage_rejection(self):
        entries=[]
        for i in range(4):
            cfg=dict(trial=str(i),role='steady',reference_low_rate=15 if i%2 else 30)
            rows=[dict(success=True,queue_ns=100000,e2e_ns=10100000,processing_wall_ns=8000000),dict(success=True,queue_ns=100001,e2e_ns=10100000,processing_wall_ns=8000000)]
            entries.append((cfg,dict(requests=rows)))
        samples,by_trial=select_calibration(entries);self.assertEqual(len(samples),4)
        entries[0][1]['requests'][0]['e2e_ns']=1
        with self.assertRaises(ValueError):select_calibration(entries)

    def test_stage_categories_conserve_failed_and_ambiguous_offers(self):
        requests=[dict(success=False),dict(success=True,e2e_ns=11000000,completion_after_offered_lower_ns=10500000,completion_after_offered_upper_ns=11500000),
                  dict(success=True,e2e_ns=11000000,completion_after_offered_lower_ns=9000000,completion_after_offered_upper_ns=10000000),
                  dict(success=True,e2e_ns=11000000,completion_after_offered_lower_ns=9900000,completion_after_offered_upper_ns=10100000),
                  dict(success=True,e2e_ns=10000000)]
        result=categories(requests,10)
        self.assertEqual(result,dict(misses=4,unsuccessful=1,computation_certainly_after=1,computation_certainly_within_but_client_missed=1,boundary_ambiguous=1))


if __name__=='__main__':unittest.main()
