"""Independent bounded SMT baseline for the Step 1 finite FIFO contract.

Uses all-prior-offer occupancy constraints, not the reference's breakpoint
generator or simulator. Z3 is a generic solver, not a reproduced research tool.
"""
from dataclasses import dataclass
from fractions import Fraction
import argparse
import json
from pathlib import Path
import time

import z3
from finite_fifo_deadline_reference import Problem, BudgetExceeded


class IncompleteAnalysis(BudgetExceeded):
    """No certified extrema: a solver query returned unknown or exhausted time."""


@dataclass(frozen=True)
class SMTLimits:
    max_offers: int = 128
    per_check_ms: int = 2000
    total_check_ms: int = 10000
    resource_limit: int = 0

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in
               (self.max_offers, self.per_check_ms, self.total_check_ms)):
            raise ValueError('offer and time limits must be positive integers')
        if type(self.resource_limit) is not int or self.resource_limit < 0:
            raise ValueError('resource_limit must be a nonnegative integer')


def real(value):
    value = Fraction(value)
    return z3.RealVal(f'{value.numerator}/{value.denominator}')


def fraction(value):
    if not z3.is_rational_value(value):
        raise IncompleteAnalysis('solver witness is not an exact rational')
    return Fraction(value.numerator_as_long(), value.denominator_as_long())


class Encoding:
    """A quantifier-free Boolean/linear real and integer encoding, O(N²)."""

    def __init__(self, problem, limits=None):
        if not isinstance(problem, Problem):
            raise ValueError('Encoding requires a validated Problem')
        self.problem = problem
        self.limits = limits or SMTLimits()
        n = len(problem.arrivals)
        if n > self.limits.max_offers:
            raise BudgetExceeded(f'{n} offers exceed limit {self.limits.max_offers}')
        self.s = z3.Real('service_time')
        self.admitted = [z3.Bool(f'admitted_{i}') for i in range(n)]
        self.completion = [z3.Real(f'completion_{i}') for i in range(n)]
        self.last = [z3.Real(f'last_completion_{i}') for i in range(n)]
        self.late = [z3.Bool(f'late_{i}') for i in range(n)]
        self.count = z3.Int('failure_count')
        self.solver = z3.Solver()
        self.solver.set(random_seed=0)
        self.solver.add(self.s >= real(problem.service_min),
                        self.s <= real(problem.service_max))
        for i, arrival in enumerate(problem.arrivals):
            a = real(arrival)
            # Completion at arrival has already departed. Rejections never occupy.
            occupied = z3.Sum([z3.If(z3.And(self.admitted[j], self.completion[j] > a),
                                     1, 0) for j in range(i)]) if i else z3.IntVal(0)
            previous = self.last[i-1] if i else real(0)
            start = z3.If(previous > a, previous, a)
            self.solver.add(self.admitted[i] == (occupied < problem.system_slots),
                            self.completion[i] == z3.If(self.admitted[i], start+self.s, real(0)),
                            self.last[i] == z3.If(self.admitted[i], self.completion[i], previous),
                            self.late[i] == z3.And(self.admitted[i],
                                self.completion[i] > real(arrival+problem.relative_deadline)))
        self.solver.add(self.count == z3.Sum([
            z3.If(z3.Or(z3.Not(self.admitted[i]), self.late[i]), 1, 0) for i in range(n)]))
        self.occupancy_terms = n*(n-1)//2

    def witness(self, model):
        s = fraction(model.eval(self.s))
        offers = []
        rejected = late = 0
        for i, a in enumerate(self.problem.arrivals):
            accepted = z3.is_true(model.eval(self.admitted[i]))
            missed = z3.is_true(model.eval(self.late[i]))
            c = fraction(model.eval(self.completion[i])) if accepted else None
            rejected += not accepted
            late += missed
            offers.append(dict(index=i, arrival=str(a), completion=str(c) if accepted else None,
                latency=str(c-a) if accepted else None,
                outcome='rejected' if not accepted else 'late' if missed else 'timely'))
        count = model.eval(self.count).as_long()
        if rejected+late != count or not self.problem.service_min <= s <= self.problem.service_max:
            raise IncompleteAnalysis('inconsistent SMT witness')
        return dict(witness_service_time=str(s), offered=len(offers), failures=count,
                    rejected=rejected, late=late, timely=len(offers)-count,
                    failure_fraction=str(Fraction(count, len(offers))), offers=offers)


class Queries:
    """Unknown never means unsatisfiable. Only successful checks yield results."""

    def __init__(self, encoding):
        self.encoding = encoding
        self.elapsed = 0.0
        self.log = []

    def check(self, constraint, label):
        e = self.encoding
        remaining = e.limits.total_check_ms - self.elapsed*1000
        if remaining < 1:
            raise IncompleteAnalysis('total solver-check time budget exhausted')
        e.solver.set(timeout=max(1, min(e.limits.per_check_ms, int(remaining))),
                     rlimit=e.limits.resource_limit)
        e.solver.push()
        try:
            e.solver.add(constraint)
            start = time.perf_counter()
            result = e.solver.check()
            seconds = time.perf_counter()-start
            self.elapsed += seconds
            self.log.append(dict(label=label, constraint=str(constraint),
                                 result=str(result), seconds=seconds))
            if result == z3.unknown:
                raise IncompleteAnalysis(f'{label}: unknown ({e.solver.reason_unknown()})')
            return (result == z3.sat, e.solver.model() if result == z3.sat else None)
        finally:
            e.solver.pop()


def solve_smt(problem, limits=None, *, smt2_path=None):
    e = Encoding(problem, limits)
    if smt2_path:
        with Path(smt2_path).open('x') as stream:
            stream.write(e.solver.to_smt2())
    q = Queries(e)
    extrema = {}
    n = len(problem.arrivals)
    for name in ('minimum', 'maximum'):
        low, high = 0, n
        while low < high:
            mid = (low+high)//2 if name == 'minimum' else (low+high+1)//2
            constraint = e.count <= mid if name == 'minimum' else e.count >= mid
            sat, _ = q.check(constraint, f'{name} threshold {mid}')
            if name == 'minimum':
                if sat:
                    high = mid
                else:
                    low = mid+1
            else:
                if sat:
                    low = mid
                else:
                    high = mid-1
        optimum = low
        sat, model = q.check(e.count == optimum, f'{name} attainment')
        if not sat:
            raise IncompleteAnalysis(f'{name} optimum has no witness')
        witness = e.witness(model)
        outside = e.count < optimum if name == 'minimum' else e.count > optimum
        better, _ = q.check(outside, f'{name} strict improvement excluded')
        if better:
            raise IncompleteAnalysis(f'{name} bound failed its exclusion check')
        extrema[name] = dict(failures=optimum, failure_fraction=str(Fraction(optimum,n)),
                             witness_service_time=witness['witness_service_time'],
                             witness=witness, strict_improvement_query=str(outside),
                             strict_improvement_result='unsat')
    return dict(schema=1, method='generic Z3 finite-trace SMT baseline',
                status='exact', problem=problem.to_json(), z3_version=z3.get_version_string(),
                scope='one shared constant service time; finite tail-drop FIFO; late jobs finish',
                novelty_established=False, real_system_coverage_established=False,
                limits=vars(e.limits), stats=dict(occupancy_terms=e.occupancy_terms,
                    solver_checks=len(q.log), solver_check_seconds=q.elapsed), queries=q.log, **extrema)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--smt2', type=Path, help='new path for the base constraint encoding')
    args = parser.parse_args()
    try:
        if args.output and args.output.exists():
            raise FileExistsError(f'output exists: {args.output}')
        result = solve_smt(Problem.from_json(json.loads(args.input.read_text())), smt2_path=args.smt2)
        content = json.dumps(result, indent=2)+'\n'
        if args.output:
            with args.output.open('x') as stream:
                stream.write(content)
        else:
            print(content, end='')
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Exact SMT analysis not completed: {exc}\n')


if __name__ == '__main__':
    main()
