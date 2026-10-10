"""Independent checks of timing-envelope containment and deadline accounting."""
import random
import unittest
from fractions import Fraction
from deadline_capacity_guard import fifo
from explore_deadline_timing_envelope import latencies


class TimingTests(unittest.TestCase):
    def test_exact_no_rejection_trace_agrees_with_offered_deadline_accounting(self):
        offsets = [i*100_000_000 for i in range(80)]
        for mu in (8,10,12,16):
            trace = latencies(offsets,mu)
            count = sum(x>500_000_000 for x in trace)
            self.assertEqual(count,fifo(offsets,mu)['misses'])
            self.assertEqual(fifo(offsets,mu)['rejections'],0)
        self.assertEqual(latencies([0],2),[Fraction(500_000_000)])

    def test_intermediate_capacity_and_per_offer_shifts_stay_inside_miss_envelope(self):
        rng=random.Random(2918102026)
        for _ in range(120):
            offsets=sorted(rng.randrange(0,2_000_000_000) for _ in range(60))
            lo,hi=25,45
            fast,slow=latencies(offsets,hi),latencies(offsets,lo)
            actual=latencies(offsets,rng.uniform(lo,hi))
            early,late=50_000_000,80_000_000
            deadline=rng.randrange(100_000_000,800_000_001)
            perturbed=[max(0,x+rng.randrange(-early,late+1)) for x in actual]
            lower=sum(max(0,x-early)>deadline for x in fast)
            upper=sum(x+late>deadline for x in slow)
            misses=sum(x>deadline for x in perturbed)
            self.assertLessEqual(lower,misses)
            self.assertLessEqual(misses,upper)


if __name__=='__main__':
    unittest.main()
