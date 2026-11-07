import math
import random
import unittest
import worker_wait_precision_cost as p


class PlanningNumerics(unittest.TestCase):
    def test_cauchy_and_exponential_oracles(self):
        for x in (.01,.5,1,3,10):
            self.assertAlmostEqual(p.t_cdf(x,1),.5+math.atan(x)/math.pi,places=11)
            self.assertAlmostEqual(p.gamma_cdf(1,x),1-math.exp(-x),places=11)

    def test_df5_closed_form(self):
        for x in (.1,1,4.774,8):
            theta=math.atan(x/math.sqrt(5))
            exact=.5+theta/math.pi+2*math.sin(2*theta)/(3*math.pi)+math.sin(4*theta)/(12*math.pi)
            self.assertAlmostEqual(p.t_cdf(x,5),exact,places=11)

    def test_nist_quantile_tables(self):
        self.assertAlmostEqual(p.quantile(lambda x:p.t_cdf(x,5),.975),2.570582,places=5)
        self.assertAlmostEqual(p.quantile(lambda x:p.gamma_cdf(2.5,x/2),.975),12.832502,places=5)
        self.assertAlmostEqual(p.quantile(lambda x:p.gamma_cdf(2.5,x/2),.025),.831212,places=5)

    def test_large_df_normal_limit_and_round_trip(self):
        for n in (6,24,192,2000):
            self.assertAlmostEqual(p.t_cdf(p.t_critical(n),n-1),.9975,places=6)
            tail=p.gamma_cdf((n-1)/2,p.sd_upper_factor(n)**2*(n-1)/2)
            self.assertAlmostEqual(tail,1-p.FAIL_PER_GATE/2,places=10)
        self.assertLess(p.t_critical(2000),2.82)
        self.assertGreater(p.t_critical(2000),2.80)

    def test_model_bound_in_normal_draws(self):
        # Independent simulation checks a mathematical model, never a service.
        rng=random.Random(726541)
        delta,sigma,margin=30,175,100
        n=p.required_n(delta,sigma,margin,True)
        successes=0
        for _ in range(20000):
            mean=rng.gauss(delta,sigma/math.sqrt(n))
            sample_sd=sigma*math.sqrt(rng.gammavariate((n-1)/2,2)/(n-1))
            successes+=abs(mean)+p.t_critical(n)*sample_sd/math.sqrt(n)<=margin
        self.assertGreater(successes/20000,1-p.FAIL_PER_GATE)

    def test_width_is_not_power_and_outside_margin(self):
        self.assertGreater(p.required_n(0,175,100,True),p.required_n(0,175,100,False))
        self.assertIsNone(p.required_n(100,175,100,True))
        self.assertGreater(p.required_n(60,175,100,True),p.required_n(0,175,100,True))


if __name__=='__main__': unittest.main()
