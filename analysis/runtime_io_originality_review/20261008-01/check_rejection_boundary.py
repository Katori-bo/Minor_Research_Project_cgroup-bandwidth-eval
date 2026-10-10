"""Synthetic mathematics check only; no workload runner or evidence refit.

Exact critical-point enumeration is a deliberately small reference calculation,
not a new efficient algorithm or a real-system uncertainty guarantee.
"""
from collections import deque
from fractions import Fraction as F
import json
from pathlib import Path
import sys

ARRIVALS = tuple(map(F, [0, 0, '0.95', '1.95']))
DEADLINE = F('1.1')
SLOTS = 2  # Includes active service.


def replay(service):
    pending = deque()
    last = F(0)
    events = []
    for i, arrival in enumerate(ARRIVALS):
        while pending and pending[0] <= arrival:
            pending.popleft()
        if len(pending) == SLOTS:
            events.append(dict(offer=i, arrival_s=str(arrival),
                               completion_s=None, outcome='rejected'))
            continue
        last = max(arrival, last) + service
        pending.append(last)
        events.append(dict(offer=i, arrival_s=str(arrival),
                           completion_s=str(last),
                           outcome=('timely' if last-arrival <= DEADLINE else 'late')))
    return dict(service_s=str(service), capacity_rps=str(1/service),
                misses=sum(e['outcome'] != 'timely' for e in events),
                rejections=sum(e['outcome'] == 'rejected' for e in events),
                events=events)


def main():
    cases = [replay(s) for s in [F(1), F('0.9'), F('0.5')]]
    # Independent hand-derived completion traces, including rejection and drain.
    expected = [('1', '2', None, '3'),
                ('9/10', '9/5', '27/10', '18/5'),
                ('1/2', '1', '3/2', '49/20')]
    assert [c['misses'] for c in cases] == [2, 3, 0]
    assert [c['rejections'] for c in cases] == [1, 0, 0]
    for c, trace in zip(cases, expected):
        assert tuple(e['completion_s'] for e in c['events']) == trace
    # Cross-check the previous diagnostic's simulator without changing it.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from deadline_capacity_guard import fifo
    for c in cases:
        other = fifo([0, 0, 950_000_000, 1_950_000_000], F(c['capacity_rps']),
                     deadline_ns=1_100_000_000, system_slots=SLOTS)
        assert (other['misses'], other['rejections']) == (c['misses'], c['rejections'])
    # All completions have form arrival_j + k*service, 1 <= k <= N.
    # Admission, idle/busy, and deadline comparisons can change only at these
    # rational values. Evaluate each point AND each intervening open interval.
    low, high = F('0.5'), F(1)
    critical = {low, high}
    for i, ai in enumerate(ARRIVALS):
        for aj in ARRIVALS[:i+1]:
            for k in range(1, len(ARRIVALS)+1):
                for x in [(ai-aj)/k, (ai+DEADLINE-aj)/k]:
                    if low <= x <= high:
                        critical.add(x)
    critical = sorted(critical)
    points = [dict(kind='boundary', left_s=str(s), right_s=str(s),
                   sample=replay(s)) for s in critical]
    cells = [dict(kind='open_interval', left_s=str(a), right_s=str(b),
                  sample=replay((a+b)/2)) for a,b in zip(critical, critical[1:])]
    all_cells = points + cells
    miss_range = [min(c['sample']['misses'] for c in all_cells),
                  max(c['sample']['misses'] for c in all_cells)]
    assert miss_range == [0, 3]
    report = dict(
        scientific_measurements_launched=False,
        role='synthetic mathematical counterexample and tiny exact reference',
        novelty_established=False,
        assumptions=['initially empty single FIFO server',
                     'identical constant service time', '2 positions including active job',
                     'reject new offer only when full', 'late jobs continue to completion',
                     'departures at arrival instant processed first',
                     'completion exactly at relative deadline is timely',
                     'rejections and late completions count as misses over all 4 offers'],
        cases=cases, endpoint_miss_range_pct=[0,50],
        actual_model_family_miss_range_pct=[0,75],
        critical_service_times_s=[str(s) for s in critical],
        cells=all_cells,
        verification=dict(hand_traces_passed=True, existing_fifo_crosscheck_passed=True,
                          boundary_and_open_interval_enumeration_passed=True),
        limitation='Does not estimate true capacity or bound real-system/model discrepancy.')
    out = Path(__file__).with_name('rejection_boundary_report.json')
    if out.exists():
        raise FileExistsError('Preserve previous report; use a fresh review directory.')
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['endpoint_miss_range_pct',
          'actual_model_family_miss_range_pct', 'verification']}))


if __name__ == '__main__':
    main()
