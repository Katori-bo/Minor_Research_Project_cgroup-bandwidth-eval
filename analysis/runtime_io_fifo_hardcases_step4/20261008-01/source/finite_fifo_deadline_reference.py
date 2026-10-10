"""Exact finite-trace FIFO reference; shared constant service time only.

No workload launch, fitted calibration, real-system guarantee, or novelty claim.
All time inputs must be integers, rational strings, or Fractions in one unit.
See docs/runtime_io_fifo_reference_step1_20261008.md for the proof and scope.
"""
from collections import deque
from dataclasses import dataclass
from fractions import Fraction
import argparse
import json
from pathlib import Path


class BudgetExceeded(ValueError):
    """The exact analysis was refused; no approximate extrema are returned."""


def rational(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, str, Fraction)):
        raise ValueError(f'{name}: use integer or exact rational/decimal string, not float')
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(f'{name}: invalid rational value') from exc


@dataclass(frozen=True)
class Problem:
    arrivals: tuple
    system_slots: int
    relative_deadline: Fraction
    service_min: Fraction
    service_max: Fraction
    time_unit: str = 'seconds'

    def __post_init__(self):
        if not isinstance(self.arrivals, (list, tuple)) or not self.arrivals:
            raise ValueError('arrivals must be a nonempty list or tuple')
        arrivals = tuple(rational(a, 'arrival') for a in self.arrivals)
        if any(a < 0 for a in arrivals) or any(a > b for a,b in zip(arrivals, arrivals[1:])):
            raise ValueError('arrivals must be nonnegative and ordered; ties use input order')
        if type(self.system_slots) is not int or self.system_slots < 1:
            raise ValueError('system_slots must be a positive integer, including active service')
        deadline = rational(self.relative_deadline, 'relative_deadline')
        lo = rational(self.service_min, 'service_min')
        hi = rational(self.service_max, 'service_max')
        if deadline < 0 or lo <= 0 or hi < lo:
            raise ValueError('require deadline >= 0 and 0 < service_min <= service_max')
        if not isinstance(self.time_unit, str) or not self.time_unit.strip():
            raise ValueError('time_unit must be a nonempty label')
        object.__setattr__(self, 'arrivals', arrivals)
        object.__setattr__(self, 'relative_deadline', deadline)
        object.__setattr__(self, 'service_min', lo)
        object.__setattr__(self, 'service_max', hi)

    @classmethod
    def from_json(cls, obj):
        if not isinstance(obj, dict):
            raise ValueError('input must be a JSON object')
        required = {'arrivals', 'system_slots', 'relative_deadline', 'service_interval'}
        if set(obj) - (required | {'time_unit'}) or required - set(obj):
            raise ValueError('require arrivals, system_slots, relative_deadline, service_interval; optional time_unit')
        interval = obj['service_interval']
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            raise ValueError('service_interval must contain exactly two endpoints')
        return cls(obj['arrivals'], obj['system_slots'], obj['relative_deadline'],
                   interval[0], interval[1], obj.get('time_unit', 'seconds'))

    def to_json(self):
        return dict(arrivals=[str(a) for a in self.arrivals],
                    system_slots=self.system_slots, relative_deadline=str(self.relative_deadline),
                    service_interval=[str(self.service_min), str(self.service_max)],
                    time_unit=self.time_unit)


@dataclass(frozen=True)
class Limits:
    max_root_expressions: int = 100_000
    max_replays: int = 20_000
    max_replay_offers: int = 200_000

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in vars(self).values()):
            raise ValueError('every resource limit must be a positive integer')


def replay(problem, service_time, *, include_offers=False):
    """Exact fixed-parameter replay. Expired jobs are never removed early."""
    s = rational(service_time, 'service_time')
    if not problem.service_min <= s <= problem.service_max:
        raise ValueError('service_time outside the declared interval')
    pending = deque()
    last = Fraction(0)
    rejected = late = peak = 0
    offers = []
    for index, arrival in enumerate(problem.arrivals):
        while pending and pending[0] <= arrival:
            pending.popleft()
        if len(pending) >= problem.system_slots:
            rejected += 1
            if include_offers:
                offers.append(dict(index=index, arrival=str(arrival), completion=None,
                                   latency=None, outcome='rejected'))
            continue
        last = max(arrival, last) + s
        pending.append(last)
        peak = max(peak, len(pending))
        missed = last - arrival > problem.relative_deadline
        late += missed
        if include_offers:
            offers.append(dict(index=index, arrival=str(arrival), completion=str(last),
                               latency=str(last-arrival), outcome='late' if missed else 'timely'))
    n = len(problem.arrivals)
    result = dict(offered=n, rejected=rejected, late=late, timely=n-rejected-late,
                  failures=rejected+late, failure_fraction=str(Fraction(rejected+late, n)),
                  failure_percentage=str(Fraction(100*(rejected+late), n)), system_peak=peak)
    if include_offers:
        result['offers'] = offers
    return result


def breakpoints(problem, limits):
    n = len(problem.arrivals)
    # Sum_{i=0}^{N-1} Sum_{j=0}^{i} 2*(i-j+1).
    expressions = n*(n+1)*(n+2)//3
    if expressions > limits.max_root_expressions:
        raise BudgetExceeded(f'{expressions} root expressions exceed limit {limits.max_root_expressions}')
    roots = {problem.service_min, problem.service_max}
    for i, ai in enumerate(problem.arrivals):
        for j in range(i+1):
            delta = ai-problem.arrivals[j]
            for k in range(1, i-j+2):
                for root in (delta/k, (delta+problem.relative_deadline)/k):
                    if problem.service_min <= root <= problem.service_max:
                        roots.add(root)
    return sorted(roots), expressions


def solve(problem, limits=None):
    """Partition the entire closed service interval, with exact point cells."""
    if not isinstance(problem, Problem):
        raise ValueError('solve requires a validated Problem')
    limits = limits or Limits()
    roots, expressions = breakpoints(problem, limits)
    calls = 2*len(roots)-1
    # Two additional complete replays produce explicit extremum witnesses.
    if calls+2 > limits.max_replays:
        raise BudgetExceeded(f'{calls+2} replays exceed limit {limits.max_replays}')
    offer_evaluations = (calls+2)*len(problem.arrivals)
    if offer_evaluations > limits.max_replay_offers:
        raise BudgetExceeded(f'{offer_evaluations} offer evaluations exceed limit {limits.max_replay_offers}')
    cells = []
    for i, root in enumerate(roots):
        domains = [(root, root, True, True, root)]
        if i+1 < len(roots):
            next_root = roots[i+1]
            domains.append((root, next_root, False, False, (root+next_root)/2))
        for lo,hi,lc,hc,sample in domains:
            value = replay(problem, sample)
            cells.append(dict(domain=dict(low=str(lo), high=str(hi),
                                          left_closed=lc, right_closed=hc),
                              witness_service_time=str(sample),
                              **{k:value[k] for k in ['rejected','late','timely','failures',
                                                     'failure_fraction','failure_percentage']}))
    extrema = {}
    for name, select in [('minimum',min),('maximum',max)]:
        count = select(c['failures'] for c in cells)
        indices = [i for i,c in enumerate(cells) if c['failures']==count]
        witness = cells[indices[0]]['witness_service_time']
        extrema[name] = dict(failures=count, failure_fraction=str(Fraction(count,len(problem.arrivals))),
                             failure_percentage=str(Fraction(100*count,len(problem.arrivals))),
                             attaining_cell_indices=indices, witness_service_time=witness,
                             witness_replay=replay(problem,witness,include_offers=True))
    return dict(schema=1, method='exact critical-point reference', problem=problem.to_json(),
                scope='shared constant service time; finite known trace; tail-drop FIFO; late jobs finish',
                real_system_coverage_established=False, novelty_established=False,
                limits=vars(limits), stats=dict(root_expressions=expressions,
                distinct_breakpoints=len(roots), cells=len(cells), fixed_parameter_replays=calls+2,
                offer_evaluations=offer_evaluations), cells=cells, **extrema)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='JSON trace with exact rational time inputs')
    parser.add_argument('--output', type=Path, help='new output path; existing files are refused')
    args = parser.parse_args()
    try:
        result = solve(Problem.from_json(json.loads(args.input.read_text())))
        content = json.dumps(result, indent=2)+'\n'
        if args.output:
            with args.output.open('x') as stream:
                stream.write(content)
        else:
            print(content, end='')
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Exact analysis not completed: {exc}\n')


if __name__ == '__main__':
    main()
