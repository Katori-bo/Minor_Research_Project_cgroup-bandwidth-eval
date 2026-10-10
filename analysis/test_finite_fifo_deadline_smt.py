"""Cross-method verification; synthetic cases, no scientific collection."""
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

import z3
from finite_fifo_deadline_reference import Problem, replay, solve, BudgetExceeded
from finite_fifo_deadline_smt import Encoding, Queries, SMTLimits, IncompleteAnalysis, real, solve_smt


COUNTS = dict(exhaustive=0, random=0, directed=0, universal_cells=0)


class SMTTests(unittest.TestCase):
    def compare(self, p, *, cells=False):
        reference = solve(p)
        result = solve_smt(p)
        for name in ('minimum', 'maximum'):
            self.assertEqual(reference[name]['failures'], result[name]['failures'])
            self.assertEqual(result[name]['strict_improvement_result'], 'unsat')
            witness = result[name]['witness']
            actual = replay(p, witness['witness_service_time'], include_offers=True)
            self.assertEqual(witness['offers'], actual['offers'])
            for key in ('offered', 'failures', 'rejected', 'late', 'timely', 'failure_fraction'):
                self.assertEqual(witness[key], actual[key])
        if cells:
            # Ask SMT whether ANY real value in a full cell has different counts.
            # This includes irrational values, not just sampled replay witnesses.
            e = Encoding(p)
            q = Queries(e)
            rejected = z3.Sum([z3.If(z3.Not(a), 1, 0) for a in e.admitted])
            late = z3.Sum([z3.If(a, 1, 0) for a in e.late])
            for cell in reference['cells']:
                d = cell['domain']
                low, high = real(F(d['low'])), real(F(d['high']))
                domain = z3.And(e.s >= low if d['left_closed'] else e.s > low,
                                e.s <= high if d['right_closed'] else e.s < high)
                sat, _ = q.check(domain, 'cell nonempty')
                self.assertTrue(sat)
                sat, _ = q.check(z3.And(domain, z3.Or(rejected != cell['rejected'],
                                                      late != cell['late'])), 'cell disagreement')
                self.assertFalse(sat)
                COUNTS['universal_cells'] += 1
        return result

    def test_directed(self):
        problems = [
            Problem([0,0,'0.95','1.95'],2,'1.1','0.5',1),
            Problem([0,0,'1.05','2.10'],2,'1.30',1,'1.20'),
            Problem([0,0],2,1,'0.5','0.75'),
            Problem([0,1,2],1,1,1,1),  # departure before equal-time arrival
            Problem([0,0,0],2,1,1,1),  # ties use input order
            Problem([0,0,0,2],1,3,1,1),  # rejected offers do not advance service
            Problem([0,0,1],2,0,'0.5','1.5'),  # expired jobs persist
            Problem([0,0,0],3,1,2,2),  # all terminal completions counted
            Problem([5,5,7],2,1,'1/3','4/3'),
            Problem([0,'1/1000003','3/1000003'],2,'2/1000003','1/1000003','3/1000003'),
            Problem([0,3,6,9],4,2,1,3),
            Problem([0,0,1,2],2,'1/2','3/4','3/4'),
        ]
        for p in problems:
            self.compare(p, cells=True)
            COUNTS['directed'] += 1
        self.assertEqual(COUNTS['directed'],12)

    def test_exhaustive_small(self):
        for n in range(1,4):
            for arrivals in itertools.combinations_with_replacement(range(3),n):
                for b in range(1,n+1):
                    for d in (F(0),F(1)):
                        self.compare(Problem(arrivals,b,d,'1/4','3/2'))
                        COUNTS['exhaustive'] += 1
        self.assertEqual(COUNTS['exhaustive'],90)

    def test_seeded_rational(self):
        rng = random.Random(810202602)
        for case in range(100):
            n = rng.randint(1,8)
            arrivals = sorted(F(rng.randint(0,30),rng.randint(1,9)) for _ in range(n))
            low = F(rng.randint(1,10),rng.randint(1,9))
            high = low + F(rng.randint(0,10),rng.randint(1,9))
            p = Problem(arrivals,rng.randint(1,n),F(rng.randint(0,15),rng.randint(1,9)),low,high)
            self.compare(p, cells=case<20)
            COUNTS['random'] += 1
        self.assertEqual(COUNTS['random'],100)

    def test_time_scale_and_origin(self):
        p = Problem([0,0,'0.95','1.95'],2,'1.1','0.5',1)
        a = solve_smt(p)
        scaled = Problem([t*1000+123 for t in p.arrivals],2,p.relative_deadline*1000,
                         p.service_min*1000,p.service_max*1000,'ms')
        b = self.compare(scaled)
        for name in ('minimum','maximum'):
            self.assertEqual(a[name]['failures'],b[name]['failures'])

    def test_unknown_and_budget_refuse(self):
        p = Problem([0,0,1,2],2,1,'1/2',2)
        with self.assertRaises(IncompleteAnalysis):
            solve_smt(p,SMTLimits(resource_limit=1))
        with self.assertRaises(BudgetExceeded):
            solve_smt(p,SMTLimits(max_offers=3))
        for args in (dict(max_offers=0),dict(per_check_ms=0),dict(resource_limit=-1),
                     dict(total_check_ms=True)):
            with self.assertRaises(ValueError):
                SMTLimits(**args)

    def test_smt2_roundtrip_and_cli(self):
        p = Problem([0,0],2,1,'1/2','3/4')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path, output_path, smt_path = root/'input.json',root/'result.json',root/'model.smt2'
            input_path.write_text(json.dumps(p.to_json()))
            script = Path(__file__).with_name('finite_fifo_deadline_smt.py')
            args = [sys.executable,str(script),str(input_path),'--output',str(output_path),'--smt2',str(smt_path)]
            completed = subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            result = json.loads(output_path.read_text())
            self.assertEqual(result['minimum']['failures'],0)
            solver = z3.Solver()
            solver.from_string(smt_path.read_text())
            solver.add(z3.Int('failure_count') < result['minimum']['failures'])
            self.assertEqual(solver.check(),z3.unsat)
            original = output_path.read_bytes(),smt_path.read_bytes()
            self.assertEqual(subprocess.run(args,capture_output=True).returncode,2)
            self.assertEqual(original,(output_path.read_bytes(),smt_path.read_bytes()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
