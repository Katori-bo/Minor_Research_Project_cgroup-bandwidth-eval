import math
import random
import unittest
from periodic_budget_model import replay,misses,delayed_misses


def slot_oracle(arrivals,demand,quota,period,phase,initial):
    """Independent discrete CPU-slot simulation on exactly aligned inputs."""
    pending=[];results=[None]*len(arrivals);next_offer=0;credit=initial*quota
    tick=0;finished=0
    while finished<len(arrivals):
        if tick and (tick-phase)%period==0 or tick==phase and phase>0:credit=quota
        while next_offer<len(arrivals) and arrivals[next_offer]==tick:
            if len(pending)<129:pending.append([next_offer,demand])
            else:finished+=1
            next_offer+=1
        if pending and credit>0:
            credit-=1;pending[0][1]-=1
            if pending[0][1]==0:
                rid,_=pending.pop(0);results[rid]=tick+1-arrivals[rid];finished+=1
        tick+=1
        if tick>100000:raise AssertionError('oracle did not terminate')
    return results


class BudgetTests(unittest.TestCase):
    def test_closed_form_spill_and_idle_credit(self):
        # 10 ms demand; third queued job spends the remaining 5 ms before reset.
        self.assertEqual([round(x*1000) for x in replay([0,1000000,2000000],25,.025,.1)], [10,19,103])
        # An idle gap does not force service to the first Q ms of each period.
        self.assertEqual([round(x*1000) for x in replay([0,10000000,60000000],25,.025,.1)], [10,10,45])

    def test_empty_budget_and_multi_period_job(self):
        self.assertAlmostEqual(replay([0],25,.025,.1,0.,0.)[0],.11)
        self.assertAlmostEqual(replay([0],5,.025,.1)[0],.125)

    def test_unlimited_quota_matches_continuous_service(self):
        arrivals=[0,1000000,20000000,20000000,300000000]
        end=0.;expected=[]
        for ns in arrivals:
            a=ns/1e9;end=max(a,end)+1/37;expected.append(end-a)
        for phase in (0.,.027,.099):
            actual=replay(arrivals,37,.1,.1,phase)
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=10)

    def test_against_independent_discrete_time_oracle(self):
        rng=random.Random(301009)
        for _ in range(40):
            period=rng.choice((20,30));quota=rng.choice((5,10));demand=rng.choice((2,4,7,12))
            phase=rng.randrange(period);initial=rng.choice((0,1))
            arrivals=sorted(rng.randrange(300) for _ in range(30))
            expected=slot_oracle(arrivals,demand,quota,period,phase,initial)
            actual=replay([x*1000000 for x in arrivals],quota/period/(demand/1000),quota/1000,period/1000,phase/1000,initial)
            for a,b in zip(actual,expected):self.assertAlmostEqual(a,b/1000,places=10)

    def test_fifo_limit_and_all_offer_denominator(self):
        x=replay([0]*131,25,.025,.1)
        self.assertEqual(sum(v is None for v in x),2)
        self.assertAlmostEqual(misses(x,[100000])['100000'],200/131)

    def test_delay_distribution_is_nonnegative_and_exact(self):
        self.assertEqual(delayed_misses([.01,.02,None],[0.,.01],[20])['20'],50.)
        with self.assertRaises(ValueError):delayed_misses([.01],[-.001],[25])

    def test_invalid_resource_contract_rejected(self):
        for args in ((0,.025,.1),(-1,.025,.1),(10,.2,.1)):
            with self.assertRaises(ValueError):replay([0],*args)


if __name__=='__main__':unittest.main()
