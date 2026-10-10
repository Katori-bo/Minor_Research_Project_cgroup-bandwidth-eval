"""Certifications must agree with whole-interval analysis; incompleteness is explicit."""
from fractions import Fraction as F
import itertools
import unittest
from finite_fifo_deadline_reference import Problem,solve
from finite_fifo_deadline_shortcut import solve_shortcut


class ShortcutTests(unittest.TestCase):
    def test_certificates_and_enclosures(self):
        for n in range(1,5):
            for arrivals in itertools.combinations_with_replacement(range(3),n):
                for b in range(1,n+1):
                    for deadline in (0,F(1,2),1,2):
                        p=Problem(arrivals,b,deadline,'1/4','3/2')
                        actual,shortcut=solve(p),solve_shortcut(p)
                        self.assertLessEqual(shortcut['proved_lower_count'],actual['minimum']['failures'])
                        self.assertGreaterEqual(shortcut['proved_upper_count'],actual['maximum']['failures'])
                        if shortcut['status']=='exact':
                            for name in ('minimum','maximum'):
                                self.assertEqual(shortcut[name]['failures'],actual[name]['failures'])
                        else:
                            self.assertNotIn('minimum',shortcut)
                            self.assertNotIn('maximum',shortcut)

    def test_unresolved_case_is_not_certified(self):
        p=Problem([0,0,'1/5','2/5'],3,1,'1/2','4/5')
        shortcut=solve_shortcut(p)
        self.assertEqual(shortcut['status'],'undetermined')
        self.assertEqual(solve(p)['minimum']['failures'],2)
        self.assertEqual(shortcut['proved_lower_count'],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
