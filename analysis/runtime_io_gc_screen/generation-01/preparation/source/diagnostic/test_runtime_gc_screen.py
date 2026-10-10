import unittest

import runtime_gc_screen as screen
import runtime_gc_probe as full


def rows(interactions=(0,0),gc_saving=.95):
    result=[]
    for spec in screen.matrix():
        value=interactions[screen.BLOCKS.index(spec['block'])]
        costs={'A':3600,'B':3600*gc_saving,'C':3600*1.05,'D':3600*gc_saving*1.05*(1+value)}
        result.append(dict(spec,cpu_usec_per_completed_work=costs[spec['arm']],busy_capacity=140,
            busy_cpu_cores=.5,timely_500_fraction=.8))
    return result


class ShortScreenTests(unittest.TestCase):
    def test_two_opposite_orders_without_mutating_full_matrix(self):
        matrix=screen.matrix()
        self.assertEqual(len(matrix),8)
        self.assertEqual([s['arm'] for s in matrix],list('ABCDDCBA'))
        self.assertEqual(len(full.matrix()),16)
        for s in matrix: self.assertIn(s,full.matrix())

    def test_small_result_never_rules_out_gc(self):
        result=screen.compare(rows())
        self.assertEqual(result['decision'],'short_screen_inconclusive')
        self.assertFalse(result['gc_hypothesis_ruled_out'])
        self.assertFalse(result['automatic_followup_authorized'])

    def test_equal_saving_is_not_interaction(self):
        result=screen.compare(rows(gc_saving=.8))
        self.assertAlmostEqual(result['cpu_interaction']['mean'],0)
        self.assertFalse(result['large_consistent_interaction_seen'])

    def test_consistent_large_signal_in_either_direction(self):
        for changes in [(.04,.05),(-.04,-.05)]:
            result=screen.compare(rows(changes))
            self.assertTrue(result['large_consistent_interaction_seen'])
            self.assertFalse(result['historical_cause_established'])

    def test_opposite_or_single_block_signal_inconclusive(self):
        for changes in [(.06,-.06),(.06,.001)]:
            self.assertEqual(screen.compare(rows(changes))['decision'],'short_screen_inconclusive')

    def test_missing_duplicate_and_invalid_cost_rejected(self):
        data=rows()
        with self.assertRaises(ValueError): screen.compare(data[:-1])
        data[-1]=data[0]
        with self.assertRaises(ValueError): screen.compare(data)
        for value in [0,-1,float('nan')]:
            data=rows(); data[0]['cpu_usec_per_completed_work']=value
            with self.assertRaises(ValueError): screen.compare(data)

    def test_separate_output_parent(self):
        self.assertNotEqual(screen.PARENT,full.PARENT)
        with self.assertRaises(ValueError): screen.owned_directory(full.DEFAULT)


if __name__=='__main__': unittest.main()
