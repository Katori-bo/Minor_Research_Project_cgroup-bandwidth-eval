from fractions import Fraction
import inspect
import math
import unittest
import warmup_precision_cost as s


class WarmupPrecision(unittest.TestCase):
    def test_exact_rank_coverage_and_maximality(self):
        for n in (5,8,25,40,800):
            for alpha in (Fraction(1,20),Fraction(1,40)):
                value=s.median_ranks(n,alpha);k=value['k']
                if not k:
                    self.assertGreater(Fraction(2,2**n),alpha);continue
                tail=Fraction(sum(math.comb(n,i) for i in range(k)),2**n)
                self.assertLessEqual(2*tail,alpha)
                self.assertAlmostEqual(value['continuous_iid_coverage'],float(1-2*tail))
                next_tail=tail+Fraction(math.comb(n,k),2**n)
                self.assertGreater(2*next_tail,alpha)
        self.assertEqual((s.median_ranks(25)['k'],s.median_ranks(25)['upper_rank']),(8,18))
        self.assertEqual(s.median_ranks(25,Fraction(1,40))['k'],7)

    def test_exact_coverage_against_enumerated_small_binomial(self):
        import itertools
        n=8;rank=s.median_ranks(n,Fraction(1,5));k=rank['k']
        count=sum(k<=sum(bits)<=n-k for bits in itertools.product((0,1),repeat=n))
        self.assertAlmostEqual(rank['continuous_iid_coverage'],count/2**n)

    def test_sorted_endpoints_ties_and_failed_mass_unavailability(self):
        v=list(reversed(range(25)));r=s.median_interval(v)
        self.assertEqual((r['lower_ns'],r['upper_ns']),(7,17))
        self.assertEqual(s.median_interval([10]*25)['width_us'],0)
        v[0]=None
        self.assertFalse(s.median_interval(v)['available'])
        self.assertFalse(s.median_interval([1,2])['available'])

    def test_difference_and_probability_transform_direction(self):
        reference=list(range(100));warm=list(range(40,65))
        panel=[dict(quantile=str(i),deadline_ns=49) for i in range(5)]
        result=s.precision(reference,warm,panel)
        lo,hi=result['median_difference_interval_ns']
        r=result['mapped_probability_range_pp'][0]
        self.assertEqual(r['lower_pct'],float(100*s.s.miss(reference,49-lo)))
        self.assertEqual(r['upper_pct'],float(100*s.s.miss(reference,49-hi)))
        self.assertLessEqual(r['lower_pct'],r['upper_pct'])
        self.assertFalse(result['future_forecast_confidence_interval'])
        self.assertFalse(result['reference_cdf_uncertainty_propagated'])
        self.assertEqual(set(inspect.signature(s.precision).parameters),{'reference','warmup','panel'})

    def test_failure_does_not_drop_cohort_or_create_location_interval(self):
        reference=list(range(100));warm=[30]*25;warm[0]=None
        panel=[dict(quantile='1/2',deadline_ns=49)]*5
        result=s.precision(reference,warm,panel)
        self.assertFalse(result['difference_available'])
        self.assertEqual(s.summarize([dict(precision=result)])['unavailable'],1)

    def test_empirical_radius_checks_integer_boundary_and_ties(self):
        reference=list(range(100));panel=[dict(deadline_ns=49)]*5
        radius=s.location_radius(reference,panel)
        self.assertEqual(radius['symmetric_radius_ns'],5)
        for sign in (-1,1):
            self.assertLessEqual(abs(s.s.miss(reference,49+sign*5)-s.s.miss(reference,49)),Fraction(1,20))
            self.assertGreater(abs(s.s.miss(reference,49+sign*6)-s.s.miss(reference,49)),Fraction(1,20))
        self.assertEqual(s.location_radius([10]*100,[dict(deadline_ns=10)]*5)['symmetric_radius_ns'],0)

    def test_sufficient_iid_count_and_paired_floor(self):
        n=s.sufficient_n();self.assertEqual(n,738)
        self.assertLessEqual(s.dkw(n),.05);self.assertGreater(s.dkw(n-1),.05)
        self.assertIsNone(s.pair_n(800)['sufficient_warmup_n'])
        x=s.pair_n(1600);n=x['sufficient_warmup_n']
        self.assertLessEqual(s.dkw(1600,.025)+s.dkw(n,.025),.05)
        self.assertGreater(s.dkw(1600,.025)+s.dkw(n-1,.025),.05)

    def test_strict_lifetime_ceilings(self):
        self.assertEqual(s.maximum_warmup(4),149)
        self.assertEqual(s.maximum_warmup(8),597)
        self.assertFalse(s.nominal_service(150,4)['passes_necessary_120sec'])
        self.assertFalse(s.nominal_service(598,8)['passes_necessary_120sec'])
        for rate in (4,8):self.assertFalse(s.nominal_service(738,rate)['passes_necessary_120sec'])

    def test_cost_all_offers_and_nominal_time(self):
        x=s.cost(738,2140.3849313460014)
        self.assertEqual(x['extra_offers'],17112)
        self.assertEqual(x['scientific_offers'],26612)
        self.assertEqual(x['including_fixed_qualification_offers'],27642)
        self.assertEqual(x['extra_nominal_sec'],3208.5)
        self.assertFalse(x['within_45min_total_projection'])
        self.assertFalse(x['selected_protocol'])


if __name__=='__main__':unittest.main()
