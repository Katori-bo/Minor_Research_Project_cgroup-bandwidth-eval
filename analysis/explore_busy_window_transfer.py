"""Retrospective accounting-range check at matching window durations.

Reads original native-sampler-off event records. No collection, interpolation,
statistical intervals, threshold tuning, or original-artifact modification.
"""
import bisect
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import v28_common as c
import v23_model as queue
import v24r3_model as bounds


def read(p):
    return json.loads(p.read_text())


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out = ROOT/'analysis/runtime_io_deadline_guard_exploration/20261008-window-transfer'
    if out.exists():
        raise ValueError('preserve the existing exploratory result')
    session = c.PARENT/'generation-01'
    original = c.resolve(session, read(session/'latest_analysis.json')['path'])
    c.verify_seal(original)
    report = read(original/'report.json')
    refs = {}; observations = []; envelopes = {}; inputs = {}
    anchors = [r for r in report['trial_accounting'] if r['role']=='mixed' and r['block']==1]
    # Exploratory duration choices explicitly reflect already-seen V28 windows.
    # The grid is fixed for this replay; it is not a prospective specification.
    for row in anchors:
        trial = c.resolve(session, report['trial_refs'][row['trial']]['path'])
        c.verify_seal(trial)
        client = read(trial/'loadgen.json'); server = read(trial/'server_metrics.json')
        for p in (trial/'loadgen.json', trial/'server_metrics.json', trial/'seal.json'):
            inputs[str(p.relative_to(ROOT))] = digest(p)
        origin = (client['client_test_start_ns'] + max(a['server_ns']-a['after_ns'] for a in client['clock_anchors']),
                  client['client_test_start_ns'] + min(a['server_ns']-a['before_ns'] for a in client['clock_anchors']))
        ends = sorted(e['completion_ns'] for e in server['events'])
        q = queue.series([e['admission_ns'] for e in server['events']],
                         [e['worker_start_ns'] for e in server['events']])
        for duration in (1.0, 1.8, 3.0):
            values = refs.setdefault(str(duration), [])
            for cycle in range(4):
                for quarter in range(9):
                    start = 11.5 + cycle*15 + quarter*.25
                    end = start+duration
                    if end > 14.5 + cycle*15:
                        continue
                    eligible = queue.min_window(q, origin[0]+start*1e9, origin[1]+end*1e9)>0
                    if not eligible:
                        raise ValueError('subwindow violates retained backlogged-state qualification')
                    count = bounds.completion_bounds(ends, origin, [[start,end]])
                    # Separate direct bisect implementation verifies bracket endpoints.
                    direct = [bisect.bisect_left(ends, origin[0]+end*1e9)-bisect.bisect_left(ends, origin[1]+start*1e9),
                              bisect.bisect_left(ends, origin[1]+end*1e9)-bisect.bisect_left(ends, origin[0]+start*1e9)]
                    if list(count)!=direct:
                        raise ValueError('independent completion bracket replay differs')
                    value = dict(trial=row['trial'], start_sec=start, end_sec=end,
                                 rate_bounds_rps=[x/duration for x in count])
                    values.append(value)
    for duration, values in refs.items():
        envelopes[duration] = [min(x['rate_bounds_rps'][0] for x in values),
                               max(x['rate_bounds_rps'][1] for x in values)]
    for row in report['trial_accounting']:
        if row['role']!='validation':
            continue
        duration = '1.0' if row['period_sec']==6 else '1.8'
        lo,hi = envelopes[duration];a,b = row['busy_capacity_bounds_rps']
        observations.append(dict(trial=row['trial'], duration_sec=float(duration),
                                 observed_aggregate_bounds_rps=[a,b], envelope_rps=[lo,hi],
                                 covered=lo<=a<=b<=hi))
    result = dict(prospective_validation=False, novelty_established=False,
                  scientific_collection_started=False,
                  durations_chosen_after_V28_outcomes_known=True,
                  anchor_trial_ids=[r['trial'] for r in anchors],
                  duration_envelopes_rps=envelopes,
                  correlated_subwindow_counts={k:len(v) for k,v in refs.items()},
                  validation_aggregate_bounds_covered=sum(x['covered'] for x in observations),
                  validation_trials=16, validation=observations, calibration_subwindows=refs,
                  input_sha256=inputs, source_sha256=digest(Path(__file__)),
                  limits=['Min/max of observed calibration windows has no future statistical coverage.',
                          'Overlapping windows and repeated cycles are correlated, not independent trials.',
                          'Validation target is its aggregate busy bound, not coverage of every validation subwindow.',
                          'Range coverage alone does not validate deadline accuracy or the guard.',
                          'Only an exploratory direction for new calibration; historical V28 unchanged.'])
    out.mkdir(parents=True)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    if any(digest(ROOT/p)!=sha for p,sha in inputs.items()):
        raise ValueError('historical raw inputs changed')
    (out/'seal.json').write_text(json.dumps(dict(files_sha256={'report.json':digest(out/'report.json')}),indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('duration_envelopes_rps','correlated_subwindow_counts','validation_aggregate_bounds_covered','validation_trials')},indent=2))


if __name__=='__main__':
    main()
