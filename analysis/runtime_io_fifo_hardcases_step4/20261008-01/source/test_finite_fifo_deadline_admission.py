"""Verify admission reduction, envelope pruning and stronger compact SMT."""
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

from finite_fifo_deadline_reference import Problem, replay, solve, BudgetExceeded
from finite_fifo_deadline_symbolic_check import Domain, symbolic_solve
from finite_fifo_deadline_admission import AdmissionLimits, Hull, solve_admission
from finite_fifo_deadline_smt import SMTLimits, IncompleteAnalysis, Encoding, Queries, real
from finite_fifo_deadline_compact_smt import CompactEncoding, solve_compact_smt
import z3


COUNTS = dict(exhaustive=0,random=0,directed=0,whole_region_smt=0)


def domain(obj):
    return Domain(F(obj['low']),F(obj['high']),obj['left_closed'],obj['right_closed'])


def intersection(a,b):
    low,high = max(a.low,b.low),min(a.high,b.high)
    d = Domain(low,high,a.contains(low) and b.contains(low),a.contains(high) and b.contains(high))
    return d if d.valid() else None


class AdmissionTests(unittest.TestCase):
    def compare(self,p,*,smt=False):
        reference = solve(p)
        reachable = symbolic_solve(p)
        candidate = solve_admission(p)
        raw = solve_admission(p,use_hull=False)
        self.assertEqual(candidate['regions'],raw['regions'])
        for name in ('minimum','maximum'):
            count = reference[name]['failures']
            self.assertEqual(candidate[name]['failures'],count)
            self.assertEqual(reachable[name+'_failures'],count)
            value = candidate[name]
            witness = replay(p,value['witness_service_time'],include_offers=True)
            self.assertEqual(witness['offers'],value['witness_replay']['offers'])
        # Every reference cell belongs to exactly one admission region; intersect
        # rather than assume the candidate's regions have constant deadline counts.
        for cell in reference['cells']:
            cd = domain(cell['domain'])
            matches = [r for r in candidate['regions'] if intersection(cd,domain(r['domain']))]
            self.assertEqual(len(matches),1)
        for region in candidate['regions']:
            d = domain(region['domain'])
            parts = [(c,intersection(d,domain(c['domain']))) for c in reference['cells']]
            parts = [(c,inter) for c,inter in parts if inter]
            self.assertEqual(region['minimum_failures'],min(c['failures'] for c,_ in parts))
            self.assertEqual(region['maximum_failures'],max(c['failures'] for c,_ in parts))
            self.assertTrue(all(c['rejected']==region['rejected'] for c,_ in parts))
            patterns = set()
            for _,inter in parts:
                s = (inter.low+inter.high)/2
                offers = replay(p,s,include_offers=True)['offers']
                patterns.add(tuple(o['outcome']!='rejected' for o in offers))
            self.assertEqual(len(patterns),1)
        if smt:
            compact = solve_compact_smt(p)
            for name in ('minimum','maximum'):
                self.assertEqual(compact[name]['failures'],candidate[name]['failures'])
                self.assertEqual(compact[name]['witness']['offers'],
                    replay(p,compact[name]['witness_service_time'],include_offers=True)['offers'])
            # Whole-region bound exclusion in the old all-prior-occupancy encoding.
            # Thus no capacity-reduction lemma is shared by this SMT check.
            e = Encoding(p)
            q = Queries(e)
            for region in candidate['regions']:
                d = domain(region['domain'])
                interval = z3.And(e.s>=real(d.low) if d.left_closed else e.s>real(d.low),
                                  e.s<=real(d.high) if d.right_closed else e.s<real(d.high))
                outside = z3.Or(e.count<region['minimum_failures'],e.count>region['maximum_failures'])
                sat,_ = q.check(z3.And(interval,outside),'candidate region bound violation')
                self.assertFalse(sat)
                COUNTS['whole_region_smt'] += 1
        return candidate

    def test_directed_boundaries(self):
        cases=[Problem([0,0,'0.95','1.95'],2,'1.1','0.5',1),
               Problem([0,0,'1.05','2.10'],2,'1.3',1,'1.2'),
               Problem([0,0],2,1,'1/2','3/4'),
               Problem([0,1,2],1,1,1,1),
               Problem([0,0,0,2],1,3,1,1),
               Problem([0,0,1],2,0,'1/2','3/2'),
               Problem([0,0,0],3,1,2,2),
               Problem([0,1,100,100],3,2,'1/2',2),
               Problem([0,'1/1000003','3/1000003'],2,'2/1000003','1/1000003','3/1000003'),
               Problem([0,0,1,2],2,'1/2','3/4','3/4')]
        for p in cases:
            self.compare(p,smt=True)
            COUNTS['directed'] += 1
        self.assertEqual(COUNTS['directed'],10)

    def test_exhaustive(self):
        for n in range(1,5):
            for a in itertools.combinations_with_replacement(range(4),n):
                for b in range(1,n+1):
                    for d in (F(0),F(1,2),F(1)):
                        self.compare(Problem(a,b,d,'1/4','3/2'))
                        COUNTS['exhaustive'] += 1
        self.assertEqual(COUNTS['exhaustive'],672)

    def test_rational_random(self):
        rng = random.Random(810202604)
        for case in range(150):
            n = rng.randint(1,9)
            a = sorted(F(rng.randint(0,40),rng.randint(1,11)) for _ in range(n))
            low = F(rng.randint(1,10),rng.randint(1,11))
            high = low+F(rng.randint(0,10),rng.randint(1,11))
            self.compare(Problem(a,rng.randint(1,n),F(rng.randint(0,20),rng.randint(1,11)),low,high),smt=case<30)
            COUNTS['random'] += 1
        self.assertEqual(COUNTS['random'],150)

    def test_deadline_does_not_change_admission_regions(self):
        regions=[]
        for d in (0,'1/2','11/10',100):
            result=self.compare(Problem([0,0,'0.95','1.95',4,4,'4.95','5.95'],2,d,'1/2',1))
            regions.append([(r['domain'],r['admitted'],r['rejected']) for r in result['regions']])
        self.assertTrue(all(r==regions[0] for r in regions))

    def test_hull_preserves_envelope(self):
        rng=random.Random(810202605)
        for _ in range(50):
            arrivals=sorted(F(rng.randint(0,100),rng.randint(1,7)) for _ in range(20))
            hull=Hull()
            for m,a in enumerate(arrivals):
                hull=hull.append(a,m)
                probes={F(0),F(1,10),F(1),F(10),F(100)}
                for i in range(m+1):
                    for j in range(i+1,m+1):
                        probes.add((arrivals[j]-arrivals[i])/(j-i))
                for s in probes:
                    self.assertEqual(max(t-j*s for t,j in hull.lines),
                                     max(arrivals[j]-j*s for j in range(m+1)))
                self.assertTrue(all(x>y for x,y in zip(hull.crossings,hull.crossings[1:])))

    def test_scale_and_origin(self):
        p=Problem([0,0,'0.95','1.95'],2,'1.1','1/2',1)
        base=solve_admission(p)
        shifted=Problem([a*1000+123 for a in p.arrivals],2,p.relative_deadline*1000,
                        p.service_min*1000,p.service_max*1000,'ms')
        result=self.compare(shifted,smt=True)
        for name in ('minimum','maximum'):
            self.assertEqual(result[name]['failures'],base[name]['failures'])

    def test_refusal(self):
        p=Problem([0,0,'0.95','1.95'],2,'1.1','1/2',1)
        for limits in (AdmissionLimits(max_offers=3),AdmissionLimits(max_states=1),AdmissionLimits(max_terms=1)):
            with self.assertRaises(BudgetExceeded): solve_admission(p,limits)
        with self.assertRaises(IncompleteAnalysis): solve_compact_smt(p,SMTLimits(resource_limit=1))
        for args in (dict(max_offers=False),dict(max_terms=0),dict(max_states=-1)):
            with self.assertRaises(ValueError): AdmissionLimits(**args)

    def test_cli_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Problem([0,0],2,1,'1/2','3/4')
            input_path,output_path=Path(temp)/'in.json',Path(temp)/'out.json'
            input_path.write_text(json.dumps(p.to_json()))
            args=[sys.executable,str(Path(__file__).with_name('finite_fifo_deadline_admission.py')),
                  str(input_path),'--output',str(output_path)]
            run=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            original=output_path.read_bytes()
            self.assertEqual(subprocess.run(args,capture_output=True).returncode,2)
            self.assertEqual(original,output_path.read_bytes())

    @classmethod
    def tearDownClass(cls):
        print('CASE_COUNTS '+json.dumps(COUNTS,sort_keys=True),flush=True)


if __name__=='__main__':
    unittest.main(verbosity=2)
