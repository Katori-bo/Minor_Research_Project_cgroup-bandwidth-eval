"""Exact model verification against hand traces and a separate symbolic engine."""
from fractions import Fraction as F
from itertools import combinations_with_replacement
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from finite_fifo_deadline_reference import Problem, Limits, BudgetExceeded, replay, solve
from finite_fifo_deadline_symbolic_check import symbolic_solve

CHECK_COUNTS = dict(exhaustive_problems=0, randomized_problems=0,
                    parameter_membership_checks=0, reference_cells_checked=0)


def contains(domain,s):
    lo,hi=F(domain['low']),F(domain['high'])
    return ((s > lo or (s == lo and domain['left_closed'])) and
            (s < hi or (s == hi and domain['right_closed'])))


class ReferenceTests(unittest.TestCase):
    def compare(self,problem):
        reference=solve(problem)
        symbolic=symbolic_solve(problem)
        self.assertEqual(reference['minimum']['failures'],symbolic['minimum_failures'])
        self.assertEqual(reference['maximum']['failures'],symbolic['maximum_failures'])
        # Inspect the union of BOTH partitions. This catches a checker boundary
        # missing from the reference, not just disagreement at chosen midpoints.
        cuts={problem.service_min,problem.service_max}
        for result in (reference,symbolic):
            for cell in result['cells']:
                cuts.update([F(cell['domain']['low']),F(cell['domain']['high'])])
        cuts=sorted(cuts)
        samples=list(cuts)
        for a,b in zip(cuts,cuts[1:]):
            samples.extend(a+(b-a)*q for q in (F(1,7),F(1,2),F(6,7)))
        for s in samples:
            refs=[c for c in reference['cells'] if contains(c['domain'],s)]
            syms=[c for c in symbolic['cells'] if contains(c['domain'],s)]
            self.assertEqual(len(refs),1,(problem,s,'reference partition'))
            self.assertEqual(len(syms),1,(problem,s,'symbolic partition'))
            actual=replay(problem,s)
            for key in ('rejected','late','failures'):
                self.assertEqual(refs[0][key],syms[0][key],(problem,s,key))
                self.assertEqual(actual[key],syms[0][key],(problem,s,key))
            CHECK_COUNTS['parameter_membership_checks']+=1
        for key in ('minimum','maximum'):
            ext=reference[key]
            self.assertEqual(replay(problem,ext['witness_service_time'])['failures'],ext['failures'])
            self.assertEqual(F(ext['failure_fraction']),F(ext['failures'],len(problem.arrivals)))
        CHECK_COUNTS['reference_cells_checked']+=len(reference['cells'])
        return reference

    def test_hand_traces_and_interior_maximum(self):
        problem=Problem([0,0,'0.95','1.95'],2,'1.1','0.5',1)
        expected=[('1',['1','2',None,'3'],2,1),
                  ('0.9',['9/10','9/5','27/10','18/5'],3,0),
                  ('0.5',['1/2','1','3/2','49/20'],0,0)]
        for s,completions,failures,rejections in expected:
            value=replay(problem,s,include_offers=True)
            self.assertEqual([x['completion'] for x in value['offers']],completions)
            self.assertEqual((value['failures'],value['rejected']),(failures,rejections))
        result=self.compare(problem)
        self.assertEqual((result['minimum']['failures'],result['maximum']['failures']),(0,3))
        endpoint_max=max(replay(problem,s)['failures'] for s in ('0.5','1'))
        self.assertLess(endpoint_max,result['maximum']['failures'])

    def test_user_review_interior_minimum(self):
        problem=Problem([0,0,'1.05','2.10'],2,'1.30',1,'1.20')
        result=self.compare(problem)
        self.assertEqual((result['minimum']['failures'],result['maximum']['failures']),(2,3))
        self.assertEqual(replay(problem,1)['failures'],3)
        self.assertEqual(replay(problem,'1.2')['failures'],3)

    def test_departure_arrival_and_deadline_equalities(self):
        problem=Problem([0,1,2],1,1,1,1)
        result=self.compare(problem)
        self.assertEqual(result['minimum']['failures'],0)
        self.assertEqual(len(result['cells']),1)
        self.assertEqual(result['cells'][0]['domain'],dict(low='1',high='1',left_closed=True,right_closed=True))

    def test_timely_only_at_boundary(self):
        problem=Problem([0,0],2,1,'0.5','0.75')
        result=self.compare(problem)
        self.assertEqual(result['minimum']['failures'],0)
        for i in result['minimum']['attaining_cell_indices']:
            self.assertEqual(result['cells'][i]['domain']['low'],'1/2')
            self.assertEqual(result['cells'][i]['domain']['high'],'1/2')
        self.assertEqual(result['maximum']['failures'],1)

    def test_tail_drop_denominator_and_no_abandonment(self):
        problem=Problem([0,0,'0.9'],1,'0.1',1,1)
        value=replay(problem,1,include_offers=True)
        self.assertEqual([o['outcome'] for o in value['offers']],['late','rejected','rejected'])
        self.assertEqual(value['failure_fraction'],'1')
        self.assertEqual((value['late'],value['rejected']),(1,2))
        self.compare(problem)

    def test_first_arrival_after_zero_and_terminal_drain(self):
        problem=Problem([10,10,'10.25'],3,2,1,1)
        value=replay(problem,1,include_offers=True)
        self.assertEqual([o['completion'] for o in value['offers']],['11','12','13'])
        self.assertEqual(value['late'],1)
        self.compare(problem)

    def test_zero_deadline_all_offers_fail(self):
        result=self.compare(Problem([0,0,1,5],2,0,'0.1',2))
        self.assertEqual(result['minimum']['failures'],4)
        self.assertEqual(result['maximum']['failures'],4)

    def test_exact_scale_and_time_origin_invariance(self):
        problem=Problem([0,0,'0.95','1.95'],2,'1.1','0.5',1)
        original=solve(problem)
        scale=1000
        transformed=Problem([a*scale+100 for a in problem.arrivals],2,
                            problem.relative_deadline*scale,
                            problem.service_min*scale,problem.service_max*scale,'milliseconds')
        changed=self.compare(transformed)
        self.assertEqual([(c['rejected'],c['late']) for c in original['cells']],
                         [(c['rejected'],c['late']) for c in changed['cells']])
        for a,b in zip(original['cells'],changed['cells']):
            self.assertEqual(F(a['witness_service_time'])*scale,F(b['witness_service_time']))

    def test_rejection_free_family_is_monotone(self):
        problem=Problem([0,0,'0.4','1.1',3],5,'1.5','0.1',2)
        result=self.compare(problem)
        failures=[c['failures'] for c in result['cells']]
        self.assertEqual(failures,sorted(failures))
        self.assertTrue(all(c['rejected']==0 for c in result['cells']))

    def test_exhaustive_small_trace_family(self):
        for n in range(1,5):
            for arrivals in combinations_with_replacement(range(4),n):
                for slots in range(1,n+1):
                    for deadline in (0,F(1,2),1):
                        self.compare(Problem(arrivals,slots,deadline,F(1,4),F(3,2)))
                        CHECK_COUNTS['exhaustive_problems']+=1
        self.assertEqual(CHECK_COUNTS['exhaustive_problems'],672)

    def test_seeded_rational_traces(self):
        rng=random.Random(8102026)
        for _ in range(200):
            n=rng.randrange(1,9)
            arrivals=sorted(F(rng.randrange(0,25),rng.choice([2,3,5,7])) for _ in range(n))
            lo=F(rng.randrange(1,8),rng.choice([3,5,7]))
            hi=lo+F(rng.randrange(0,9),rng.choice([2,3,7]))
            problem=Problem(arrivals,rng.randrange(1,n+2),F(rng.randrange(0,12),5),lo,hi)
            self.compare(problem)
            CHECK_COUNTS['randomized_problems']+=1
        self.assertEqual(CHECK_COUNTS['randomized_problems'],200)

    def test_invalid_contracts_and_inexact_inputs(self):
        good=dict(arrivals=[0,1],system_slots=1,relative_deadline=1,service_min=1,service_max=2)
        bad=[dict(arrivals=[]),dict(arrivals=[1,0]),dict(arrivals=[-1]),dict(arrivals=[False]),
             dict(arrivals=[0.1]),dict(system_slots=True),dict(system_slots=0),
             dict(relative_deadline=-1),dict(service_min=0),dict(service_min='nan'),
             dict(service_min='1/0'),dict(service_max='0.5'),dict(time_unit='')]
        for change in bad:
            with self.subTest(change=change),self.assertRaises(ValueError):
                Problem(**(good|change))
        with self.assertRaises(ValueError):
            Problem.from_json(dict(arrivals=[0],system_slots=1,relative_deadline=1,service_interval=[1]))
        with self.assertRaises(ValueError):
            replay(Problem(**good),0)
        with self.assertRaises(ValueError):
            Limits(max_replays=True)

    def test_budget_failures_return_no_extrema(self):
        problem=Problem([0,0,'0.95','1.95'],2,'1.1','0.5',1)
        for limits in (Limits(max_root_expressions=1),Limits(max_replays=1),Limits(max_replay_offers=1)):
            with self.assertRaises(BudgetExceeded):
                solve(problem,limits)
        for limits in (dict(max_states=1),dict(max_transitions=1)):
            with self.assertRaises(BudgetExceeded):
                symbolic_solve(problem,**limits)

    def test_cli_output_and_refusal_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            source=directory/'input.json'
            output=directory/'result.json'
            source.write_text(json.dumps(Problem([0,0],2,1,'0.5','0.75').to_json()))
            cmd=[sys.executable,str(Path(__file__).with_name('finite_fifo_deadline_reference.py')),
                 str(source),'--output',str(output)]
            first=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            before=output.read_bytes()
            self.assertEqual(json.loads(before)['minimum']['failures'],0)
            second=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(second.returncode,2)
            self.assertEqual(output.read_bytes(),before)
            source.write_text(json.dumps(dict(arrivals=[0.1],system_slots=1,
                relative_deadline=1,service_interval=[1,2])))
            refused=subprocess.run(cmd[:-2],capture_output=True,text=True)
            self.assertEqual(refused.returncode,2)
            self.assertIn('not float',refused.stderr)


if __name__ == '__main__':
    unittest.main()
