#!/usr/bin/env python3
"""Verify and compare original V20, cost pilot and original-runner V20 repeat."""
import collections
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import period_cost as pc
from verify_execution_delay import verify_completion
from review_period_cost_pilot import host_summary, fixed_busy_rate


def load_v20(session):
    report = verify_completion(session)
    paths = sorted((session/'trials').glob('*/attempt-*'))
    assert len(paths) == 16
    rows = []
    for path in paths:
        pc.old.verify_seal(path)
        row = pc.old.read(path/'derived.json')['summary'].copy()
        row['fixed_busy_rate'] = fixed_busy_rate(path)
        row['warmup_completed'] = pc.old.read(path/'warmup_server_metrics.json')['completed']
        row['warmup_failures'] = sum(pc.old.read(path/'warmup.json')[k] for k in ('total_503','total_errors'))
        rows.append(row)
    return report, paths, rows


def cells(rows, pilot=False):
    groups = collections.defaultdict(list)
    for row in rows:
        key = f"{row['period_ms']}_{'on' if row['counters'] else 'off'}" if pilot else row['arm']
        groups[key].append(row)
    out = {}
    for key, group in groups.items():
        out[key] = {field:st.mean(r[field] for r in group) for field in
            ('cpu_usec_per_completed_work','timely_500_fraction','timely_1000_fraction',
             'failure_fraction','p99_e2e_ms','fixed_busy_rate','warmup_completed','warmup_failures')}
        out[key]['gap_mean_all_offers_ns'] = (st.mean(r['gap_mean_all_offers_ns'] for r in group)
            if all(r['gap_mean_all_offers_ns'] is not None for r in group) else None)
        out[key]['queue_mean_ms'] = st.mean(r['queue_ns']['mean'] for r in group)/1e6
    return out


def main():
    original, pilot, repeat = pc.BASE, pc.DEFAULT, pc.old.PARENT/'generation-04'
    repeat_protocol = repeat/'repeat_protocol'
    pc.old.verify_seal(repeat_protocol)
    protocol = pc.old.read(repeat_protocol/'manifest.json')
    assert protocol['original_preparation_seal'] == pc.old.digest(original/'preparation/seal.json')
    assert protocol['repeat_preparation_seal'] == pc.old.digest(repeat/'preparation/seal.json')
    before, old_paths, old_rows = load_v20(original)
    after, repeat_paths, repeat_rows = load_v20(repeat)
    pm = pc.verify_preparation(pilot,current=False)
    pc.old.verify_seal(pilot/'counter_fixtures')
    assert pc.validate_fixtures(pilot/'counter_fixtures') == pc.old.read(pilot/'counter_fixtures/result.json')
    pilot_paths=[];pilot_rows=[]
    for spec in pc.matrix():
        path=pilot/'trials'/spec['trial'];result=pc.replay_trial(path)
        assert result == pc.old.read(path/'derived.json')
        row=result['summary'].copy();row['fixed_busy_rate']=fixed_busy_rate(path)
        row['warmup_completed']=pc.old.read(path/'warmup_server_metrics.json')['completed']
        row['warmup_failures']=sum(pc.old.read(path/'warmup.json')[k] for k in ('total_503','total_errors'))
        pilot_paths.append(path);pilot_rows.append(row)
    om,rm=(pc.old.read(s/'preparation/manifest.json') for s in (original,repeat))
    matches={k:om[k]==rm[k] for k in ('sources','matrix','workload','image','server_sha256',
        'loadgen_sha256','gate_sha256','resource_baseline','baseline')}
    assert all(matches.values())
    assert om['baseline']==pm['baseline']
    assert all(pc.old.read(s/'preparation/arrivals.json') == pc.old.read(original/'preparation/arrivals.json')
               for s in (pilot,repeat))
    power={name:pc.old.read(s/'environment.json')['power_settings']
           for name,s in [('original',original),('pilot',pilot),('repeat',repeat)]}
    assert power['original']==power['pilot']==power['repeat']
    table={name:cells(rows,is_pilot) for name,rows,is_pilot in
           [('original',old_rows,False),('pilot',pilot_rows,True),('repeat',repeat_rows,False)]}
    hosts={name:host_summary(paths) for name,paths in
           [('original',old_paths),('pilot',pilot_paths),('repeat',repeat_paths)]}
    supplemental={}
    import math
    for name,rows in [('original',old_rows),('repeat',repeat_rows)]:
        by_id={r['trial']:r for r in rows}
        vals=[math.log(by_id[f'b{b}_C']['fixed_busy_rate']/by_id[f'b{b}_A']['fixed_busy_rate']) for b in range(1,5)]
        supplemental[name]=dict(period_capacity_change=pc.estimate(vals,logarithmic=True),
            interpretation='Exploratory fixed-window comparison, supplementary to frozen V20 outcomes.')
    result=dict(review='2026-10-06',raw_trials_verified=48,original_decision=before['decision'],
        repeat_decision=after['decision'],repeat_interpretation_eligible=after['interpretation_eligible'],
        repeat_guardrails_pass=after['guardrails_pass'],repeatability_claim=after['repeatability_established'],
        repeat_offers=sum(r['offered'] for r in repeat_rows),
        repeat_completed=sum(r['completed_computations'] for r in repeat_rows),
        original_repeat_contract_matches=matches,power_settings_match=True,cells=table,host=hosts,
        baseline_c={name:pc.old.read(s/'environment.json')['baseline_c']
                    for name,s in [('original',original),('pilot',pilot),('repeat',repeat)]},
        repeat_contrasts=after['contrasts'],supplemental_capacity=supplemental,
        conclusions=['The original shorter-period CPU penalty did not return under the original runner.',
            'The pilot-only perf helper and its measurement window are not necessary for the improved direction.',
            'The repeat omitted an explicit profile setter, but a persistent effect of a previous setting is not excluded.',
            'All three sessions support a strong yield response of the completion-to-handler interval.',
            'Deadline benefit from yielding depends on session and period; no universal net benefit is established.',
            'Higher desktop activity coincides with the two sessions showing a 20 ms improvement; causation is unresolved.'],
        causal_mechanism_established=False,novelty_established=False,
        reviewer_sha256=pc.old.digest(Path(__file__)),
        source_seals={str(p.relative_to(ROOT)/'seal.json'):pc.old.digest(p/'seal.json')
                      for p in old_paths+pilot_paths+repeat_paths+[repeat_protocol]})
    output=ROOT/'analysis/runtime_io_v20_repeat_review/20261006';output.mkdir(parents=True,exist_ok=True)
    pc.old.save(output/'report.json',result)
    print(json.dumps({k:result[k] for k in ('raw_trials_verified','original_decision','repeat_decision',
        'repeat_guardrails_pass','repeat_offers','repeat_completed','original_repeat_contract_matches')},indent=2))
    print('Review: '+str(output/'report.json'))


if __name__=='__main__':main()
