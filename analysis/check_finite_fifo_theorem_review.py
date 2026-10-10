"""Small exact structural checks for the originality-review theorem.

This is offline mathematical verification, not a performance campaign or a
novelty test. Earlier solvers and sealed evidence are read without editing.
"""
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
from itertools import combinations_with_replacement
import json
from pathlib import Path

from finite_fifo_deadline_reference import Problem, replay, solve
from finite_fifo_deadline_admission import solve_admission


def admission_vector(p, s):
    return tuple(row['outcome'] != 'rejected'
                 for row in replay(p, s, include_offers=True)['offers'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    counters = Counter()
    alphabet = tuple(F(k, 2) for k in range(5))
    for n in range(1, 6):
        for arrivals in combinations_with_replacement(alphabet, n):
            for b in range(1, n+2):
                roots = {(arrivals[i]-arrivals[p])/k
                         for i in range(n) for p in range(i)
                         for k in range(1, i-p-b+2)}
                root_count = sum(max(0, i-p-b+1)
                                 for i in range(n) for p in range(i))
                m = max(n-b, 0)
                assert root_count == m*(m+1)*(m+2)//6
                for deadline in (F(0), F(3, 4), F(3, 2)):
                    for lo, hi in ((F(1, 4), F(5, 4)), (F(1, 2), F(1, 2))):
                        p = Problem(arrivals, b, deadline, lo, hi)
                        candidate = solve_admission(p)
                        reference = solve(p)
                        regions = candidate['regions']
                        assert len(regions) <= 1 + len({x for x in roots if lo <= x < hi})
                        assert len(regions) <= 1 + root_count
                        assert F(regions[0]['domain']['low']) == lo
                        assert F(regions[-1]['domain']['high']) == hi
                        for index, region in enumerate(regions):
                            d = region['domain']
                            l, h = F(d['low']), F(d['high'])
                            assert d['right_closed']
                            assert d['left_closed'] == (index == 0)
                            if l == h:
                                assert l == lo and d['left_closed']
                                counters['singleton_regions_at_L'] += 1
                            if index:
                                assert l == F(regions[index-1]['domain']['high'])
                                assert l in roots
                            samples = {F(region['minimum_witness_service_time']),
                                       F(region['maximum_witness_service_time']), h}
                            if l < h:
                                samples.add((l+h)/2)
                            vectors = {admission_vector(p, s) for s in samples}
                            assert len(vectors) == 1
                            counters['regions_checked'] += 1
                        for kind in ('minimum', 'maximum'):
                            assert candidate[kind]['failures'] == reference[kind]['failures']
                        cells = reference['cells']
                        for i in range(1, len(cells), 2):
                            # Every interior interval is followed by its right endpoint.
                            left, point = cells[i], cells[i+1]
                            assert left['failures'] == point['failures']
                            assert admission_vector(p, F(left['witness_service_time'])) == admission_vector(
                                p, F(point['witness_service_time']))
                            counters['left_continuity_boundaries_checked'] += 1
                        counters['problems_checked'] += 1
    repo = Path(__file__).resolve().parent.parent
    sources = ['analysis/check_finite_fifo_theorem_review.py',
               'analysis/finite_fifo_deadline_admission.py',
               'analysis/finite_fifo_deadline_reference.py',
               'analysis/finite_fifo_deadline_symbolic_check.py']
    result = dict(schema=1, status='passed', scope=dict(max_offers=5,
                  arrival_alphabet=[str(x) for x in alphabet],
                  capacities='1 through N+1', deadlines=['0', '3/4', '3/2'],
                  service_intervals=[['1/4', '5/4'], ['1/2', '1/2']]),
                  **counters, source_sha256={name: hashlib.sha256((repo/name).read_bytes()).hexdigest()
                                            for name in sources},
                  checks_are_proof=False, independent_expert_review=False,
                  novelty_established=False, scientific_collection_launched=False)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'problems_checked',
                     'regions_checked', 'left_continuity_boundaries_checked')}))


if __name__ == '__main__':
    main()
