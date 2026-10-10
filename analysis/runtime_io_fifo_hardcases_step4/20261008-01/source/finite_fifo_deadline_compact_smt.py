"""Improved generic SMT baseline: scalar deterministic FIFO workload guard.

Linear-size encoding, using the same FIFO lemma as the candidate; not a
reproduction of a published analyzer. Keeps all deadline Boolean indicators.
"""
from fractions import Fraction
import z3
from finite_fifo_deadline_reference import Problem, BudgetExceeded
from finite_fifo_deadline_smt import SMTLimits, Encoding, Queries, real, IncompleteAnalysis


class CompactEncoding(Encoding):
    def __init__(self, problem, limits=None):
        if not isinstance(problem,Problem):
            raise ValueError('CompactEncoding requires a validated Problem')
        self.problem = problem
        self.limits = limits or SMTLimits()
        n = len(problem.arrivals)
        if n > self.limits.max_offers:
            raise BudgetExceeded('compact SMT offer budget exceeded')
        self.s = z3.Real('service_time')
        self.admitted = [z3.Bool(f'admitted_{i}') for i in range(n)]
        self.completion = [z3.Real(f'completion_{i}') for i in range(n)]
        self.last = [z3.Real(f'last_completion_{i}') for i in range(n)]
        self.late = [z3.Bool(f'late_{i}') for i in range(n)]
        self.count = z3.Int('failure_count')
        self.solver = z3.Solver()
        self.solver.set(random_seed=0)
        self.solver.add(self.s >= real(problem.service_min),self.s <= real(problem.service_max))
        for i,arrival in enumerate(problem.arrivals):
            previous = self.last[i-1] if i else real(0)
            a = real(arrival)
            self.solver.add(self.admitted[i] == (previous-(problem.system_slots-1)*self.s <= a),
                self.completion[i] == z3.If(self.admitted[i],z3.If(previous>a,previous,a)+self.s,real(0)),
                self.last[i] == z3.If(self.admitted[i],self.completion[i],previous),
                self.late[i] == z3.And(self.admitted[i],self.completion[i]>real(arrival+problem.relative_deadline)))
        self.solver.add(self.count == z3.Sum([
            z3.If(z3.Or(z3.Not(self.admitted[i]),self.late[i]),1,0) for i in range(n)]))


def solve_compact_smt(problem,limits=None):
    e = CompactEncoding(problem,limits)
    q = Queries(e)
    extrema = {}
    n = len(problem.arrivals)
    for name in ('minimum','maximum'):
        low,high = 0,n
        while low<high:
            mid = (low+high)//2 if name=='minimum' else (low+high+1)//2
            sat,_ = q.check(e.count<=mid if name=='minimum' else e.count>=mid,f'{name} threshold {mid}')
            if name=='minimum':
                if sat: high=mid
                else: low=mid+1
            else:
                if sat: low=mid
                else: high=mid-1
        sat,model = q.check(e.count==low,f'{name} attainment')
        if not sat:
            raise IncompleteAnalysis('compact SMT optimum has no witness')
        witness = e.witness(model)
        outside = e.count<low if name=='minimum' else e.count>low
        better,_ = q.check(outside,f'{name} strict improvement excluded')
        if better:
            raise IncompleteAnalysis('compact SMT strict improvement feasible')
        extrema[name] = dict(failures=low,failure_fraction=str(Fraction(low,n)),
            witness_service_time=witness['witness_service_time'],witness=witness,
            strict_improvement_query=str(outside),strict_improvement_result='unsat')
    return dict(method='generic compact scalar-workload SMT',status='exact',problem=problem.to_json(),
        novelty_established=False,real_system_coverage_established=False,limits=vars(e.limits),
        stats=dict(occupancy_terms=0,workload_guards=n,solver_checks=len(q.log),solver_check_seconds=q.elapsed),
        queries=q.log,**extrema)
