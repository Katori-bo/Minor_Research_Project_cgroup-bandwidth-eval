"""Exact extrema by admission intervals; deadline and idle events never branch.

One common deterministic service time, Step 1 contract. Standard max-plus and
upper-envelope tools; originality of this specialization remains unverified.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
import argparse
import json
from pathlib import Path

from finite_fifo_deadline_reference import Problem, BudgetExceeded
from finite_fifo_deadline_symbolic_check import Domain


@dataclass(frozen=True)
class AdmissionLimits:
    max_offers: int = 2048
    max_states: int = 10000
    max_terms: int = 10_000_000

    def __post_init__(self):
        if any(type(x) is not int or x < 1 for x in vars(self).values()):
            raise ValueError('all admission solver limits must be positive integers')


@dataclass(frozen=True)
class Hull:
    # H_m(s) = max(t_j - j*s), j zero-based admitted ordinal.
    # Lines are in increasing j; adjacent intersections strictly decrease.
    lines: tuple = ()
    crossings: tuple = ()

    def append(self, arrival, ordinal):
        lines, crossings = list(self.lines), list(self.crossings)
        while lines:
            old_t, old_j = lines[-1]
            cut = (arrival-old_t)/(ordinal-old_j)
            if len(lines) == 1 or cut < crossings[-1]:
                crossings.append(cut)
                break
            lines.pop()
            crossings.pop()
        lines.append((arrival, ordinal))
        return Hull(tuple(lines),tuple(crossings))


@dataclass(frozen=True)
class DeadlineNode:
    cut: F
    previous: object = None


@dataclass(frozen=True)
class State:
    domain: Domain
    hull: Hull = Hull()
    admitted: int = 0
    rejected: int = 0
    deadlines: object = None


def workload_replay(problem, s):
    """Witness construction with scalar workload, independently queue-checked in tests."""
    last = F(0)
    rejected = late = 0
    offers = []
    for index,a in enumerate(problem.arrivals):
        if last-(problem.system_slots-1)*s > a:
            rejected += 1
            offers.append(dict(index=index,arrival=str(a),completion=None,latency=None,outcome='rejected'))
        else:
            last = max(last,a)+s
            missed = last > a+problem.relative_deadline
            late += missed
            offers.append(dict(index=index,arrival=str(a),completion=str(last),latency=str(last-a),
                               outcome='late' if missed else 'timely'))
    return dict(offered=len(offers),rejected=rejected,late=late,failures=rejected+late,
                timely=len(offers)-rejected-late,offers=offers)


def solve_admission(problem, limits=None, *, use_hull=True):
    if not isinstance(problem, Problem):
        raise ValueError('solve_admission requires a validated Problem')
    if type(use_hull) is not bool:
        raise ValueError('use_hull must be Boolean')
    limits = limits or AdmissionLimits()
    n = len(problem.arrivals)
    if n > limits.max_offers:
        raise BudgetExceeded('admission offer budget exceeded')
    states = [State(Domain(problem.service_min,problem.service_max))]
    terms = splits = visits = 0
    peak_states = 1
    peak_hull = 0

    def charge(count):
        nonlocal terms
        terms += count
        if terms > limits.max_terms:
            raise BudgetExceeded('admission arithmetic-term budget exceeded')

    for a in problem.arrivals:
        next_states = []
        for state in states:
            visits += 1
            m = state.admitted
            if m < problem.system_slots:
                admitted_domain, rejected_domain = state.domain, None
            else:
                charge(len(state.hull.lines))
                capacity_cut = min((a-t)/(m-j-problem.system_slots+1)
                    for t,j in state.hull.lines if m-j-problem.system_slots+1 > 0)
                admitted_domain,rejected_domain = state.domain.split_le(capacity_cut)
                splits += admitted_domain is not None and rejected_domain is not None
            if rejected_domain is not None:
                next_states.append(replace(state,domain=rejected_domain,rejected=state.rejected+1))
            if admitted_domain is not None:
                if use_hull:
                    charge(len(state.hull.lines)+1)  # Covers copying/pruning as well.
                    hull = state.hull.append(a,m)
                else:
                    charge(len(state.hull.lines)+1)
                    hull = Hull(state.hull.lines+((a,m),))
                peak_hull = max(peak_hull,len(hull.lines))
                charge(len(hull.lines))
                deadline_cut = min((a+problem.relative_deadline-t)/(m+1-j) for t,j in hull.lines)
                next_states.append(State(admitted_domain,hull,m+1,state.rejected,
                                         DeadlineNode(deadline_cut,state.deadlines)))
            if len(next_states) > limits.max_states:
                raise BudgetExceeded('admission state budget exceeded')
        states = next_states
        peak_states = max(peak_states,len(states))

    states.sort(key=lambda x:(x.domain.low,not x.domain.left_closed,x.domain.high))
    regions = []
    for state in states:
        d = state.domain
        min_late = max_late = 0
        first_cut, last_cut = d.high, d.low
        node = state.deadlines
        charge(state.admitted)
        while node is not None:
            cut = node.cut
            min_late += cut < d.low or (cut == d.low and not d.left_closed)
            max_late += cut < d.high
            if d.low < cut < first_cut:
                first_cut = cut
            if last_cut < cut < d.high:
                last_cut = cut
            node = node.previous
        witness_min = d.low if d.left_closed else (d.low+first_cut)/2
        witness_max = d.high if d.right_closed else (last_cut+d.high)/2
        regions.append(dict(domain=d.to_json(),admitted=state.admitted,rejected=state.rejected,
            minimum_late=min_late,maximum_late=max_late,
            minimum_failures=state.rejected+min_late,maximum_failures=state.rejected+max_late,
            minimum_witness_service_time=str(witness_min),maximum_witness_service_time=str(witness_max)))
    extrema = {}
    for name,select in (('minimum',min),('maximum',max)):
        count = select(r[name+'_failures'] for r in regions)
        indices = [i for i,r in enumerate(regions) if r[name+'_failures']==count]
        s = regions[indices[0]][name+'_witness_service_time']
        witness = workload_replay(problem,F(s))
        if witness['failures'] != count:
            raise AssertionError('admission extrema and workload witness disagree')
        extrema[name] = dict(failures=count,failure_fraction=str(F(count,n)),
            attaining_region_indices=indices,witness_service_time=s,witness_replay=witness)
    return dict(schema=1,status='exact',method='admission intervals with deferred deadline counts',
        problem=problem.to_json(),scope='one common constant service time; finite FIFO tail-drop; late jobs finish',
        novelty_established=False,real_system_coverage_established=False,limits=vars(limits),
        stats=dict(terms=terms,admission_splits=splits,state_visits=visits,peak_states=peak_states,
                   peak_hull_lines=peak_hull,regions=len(regions),deadline_splits=0,idle_splits=0,
                   hull_enabled=use_hull),regions=regions,**extrema)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--without-hull',action='store_true',help='ablation retains all max-plus lines')
    args = parser.parse_args()
    try:
        if args.output and args.output.exists():
            raise FileExistsError('output path already exists')
        result = solve_admission(Problem.from_json(json.loads(args.input.read_text())),use_hull=not args.without_hull)
        if args.output:
            with args.output.open('x') as stream:
                json.dump(result,stream,indent=2)
                stream.write('\n')
        else:
            print(json.dumps(result,indent=2))
    except (ValueError,OSError) as exc:
        parser.exit(2,f'Exact admission analysis not completed: {exc}\n')


if __name__ == '__main__':
    main()
