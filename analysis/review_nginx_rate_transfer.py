#!/usr/bin/env python3
"""Read-only replay and separately sealed assessment of rate-transfer generation 01."""
import argparse
import contextlib
import io
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_rate_transfer_common as c
import nginx_rate_transfer_model as m
import nginx_rate_transfer_study as s
import nginx_power_confirmation_guard as g

OUT = ROOT / 'analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01'


def calculate():
    with contextlib.redirect_stdout(io.StringIO()):
        result = s.replay()
    campaign = c.BASE / 'campaign'
    counts = {}
    calibration = {}
    for phase in ('calibration', 'validation'):
        rows = c.read(campaign / phase / 'summary.json')['rows']
        counts[phase] = dict(cohorts=len(rows), measurement_offers=sum(r['offers'] for r in rows),
            warmup_offers=sum(len(r['warmup_outcomes']) for r in rows),
            unsuccessful_measurement=sum(r['offers'] - r['successful'] for r in rows),
            unsuccessful_warmup=sum(not o['success'] for r in rows for o in r['warmup_outcomes']),
            observation_flags=[dict(config=r['config'], observations=r['observations'],
                measurement_counter_delta=r['measurement_counter_delta'],
                warmup_counter_delta=r['warmup_counter_delta']) for r in rows if r['observations']])
        for r in rows:
            case = campaign / phase / f"cohort-{r['config']['index']}"
            final = c.read(case / 'policy-final-check.json')
            c.require(not final['host_policy_writes'] and final['snapshot'] ==
                c.read(c.BASE / 'policy-baseline.json'), 'Final fixed-policy check differs')
            c.require(not c.read(case / 'cleanup.json')['errors'], 'Owned cleanup differs')
        if phase == 'calibration':
            for rate in (4, 5, 8):
                group = [r for r in rows if r['config']['rate_rps'] == rate]
                calibration[str(rate)] = dict(offers=sum(r['offers'] for r in group),
                    cohort_miss_percent=[100 * m.miss_fraction(r['outcomes'], c.PROTOCOL['primary_deadline_ns']) for r in group],
                    prediction_percent=100 * m.miss_fraction([o for r in group for o in r['outcomes']],
                        c.PROTOCOL['primary_deadline_ns']))
    old = c.read(c.previous.BASE / 'campaign/comparison.json')
    return dict(status=result['status'], primary_deadline_ns=c.PROTOCOL['primary_deadline_ns'],
        campaign_summary=c.read(campaign / 'summary.json'), counts=counts, calibration=calibration,
        primary=result['primary'], secondary={d: dict(methods=v['methods'], endpoint_saturated=v['endpoint_saturated'])
            for d, v in result['secondary'].items()},
        calibration_cohort_sensitivity=result['calibration_cohort_sensitivity'],
        accuracy_criterion_met=result['useful_absolute_accuracy'], advantage_criterion_met=result['useful_gain'],
        previous_confirmation=dict(status=old['status'], matched=old['primary']['methods']['matched'],
            evidence_seal_sha256=c.sha(c.previous.BASE / 'campaign/evidence-seal.json')),
        campaign_evidence_seal_sha256=c.sha(campaign / 'evidence-seal.json'),
        preparation_seal_sha256=c.sha(c.BASE / 'preparation-seal.json'),
        qualification_and_campaign_raw_replay_verified=True, forecast_barriers_verified=True,
        owned_cleanup_and_fixed_policy_records_verified=True, novelty_established=False,
        historical_failure_cause_identified=False,
        decision='Close the bounded rate-matching collection branch. Report accurate transfer for both matched and 5/s calibration, without demonstrated incremental advantage. No automatic repeat, tuning or causal attribution across campaigns; independent V31 remains pending.')


def markdown(r):
    lines = ['# Completed NGINX rate-transfer assessment', '',
        '10 October 2026. All frozen studies and their evidence remain unchanged.', '',
        '**Rate-matched calibration met the accuracy target; its required advantage over ordinary 5/s calibration was not supported. Both references were accurate in this campaign.**', '',
        'Qualification, six fresh calibration cohorts and all twelve validation cohorts replay successfully.',
        f"The scientific campaign took {r['campaign_summary']['elapsed_sec'] / 60:.2f} minutes and retained",
        '6,000 measured offers plus 450 warmup offers. All scientific responses succeeded.',
        'Source/evidence seals, advance forecast barriers, owned cleanup and read-only fixed-P0 checks verify.',
        'A separate current-host policy readback matched the prepared baseline when this assessment was saved.', '',
        '## Frozen primary comparison', '',
        'Deadline: 20.565395 ms. Errors are absolute deadline-miss probability errors in percentage points (pp).', '',
        '| Reference | Mean error (pp) | Conditional 95% interval (pp) | Maximum error (pp) | Cohorts >5 pp |',
        '|---|---:|---:|---:|---:|']
    labels = dict(matched='Rate-matched calibration', baseline='Ordinary 5/s calibration',
        pooled='Pooled 4/5/8 calibration', warmup='25-offer target-rate warmup',
        matched_update='Matched + warmup', baseline_update='5/s + warmup', pooled_update='Pooled + warmup')
    for name, v in r['primary']['methods'].items():
        lo, hi = v['conditional_95_interval']
        lines.append(f"| {labels[name]} | {v['mean']:.3f} | [{lo:.3f}, {hi:.3f}] | {v['maximum_error_pp']:.3f} | {v['errors_above_5pp']}/12 |")
    gain = r['primary']['matched_gain_pp']; lo, hi = gain['conditional_95_interval']
    lines += ['', f"Matched improvement over 5/s calibration is {gain['mean']:.3f} pp, conditional 95% interval [{lo:.3f}, {hi:.3f}] pp.",
        'It fails both the frozen >=2 pp mean-improvement condition and the positive interval-lower-bound condition.',
        'This does not prove equivalence or absence of any rate-matching benefit. The rate-matched, 5/s and pooled',
        'references each have an accuracy upper bound <=5 pp; all their individual cohort errors are <=5 pp.', '',
        'Intervals use six consecutive block means and condition on frozen calibration. Adequate block independence',
        'is assumed; calibration uncertainty and between-campaign variation are not propagated. These are not',
        'per-cohort guarantees. Warmup and updated references have later decision times and different acquisition budgets.', '',
        '## Population and applicability', '',
        'Observed primary miss probabilities ranged from 78.667% to 84.000%. Accurate forecasts here mean',
        'accurately predicting that most offers miss the deadline; they do not mean the service meets the deadline.',
        'The primary endpoint was not saturated. Rate-specific calibration predicted 81.000% at 4/s,',
        '79.500% at 5/s and 81.875% at 8/s.', '',
        'Validation cohort 5 (8/s, block 3) recorded one throttled period and 6,600 us aggregate throttling;',
        'cohort 9 (8/s, block 5) recorded one throttled period and 9,133 us. Both were retained as prescribed',
        'by the all-offer contract. These aggregate counters do not assign a throttle event to a specific response.',
        'No other scientific observation flags or unsuccessful offers were recorded.', '',
        'At the predeclared secondary 10 ms endpoint all measured offers missed; at 50 ms all met the deadline.',
        'Those zero-error endpoints are saturated. At 25 ms matched and 5/s MAE were 0.027778 pp;',
        'this secondary endpoint does not replace the primary comparison.', '',
        '## What this changes in the research argument', '',
        'The preceding power-policy confirmation failed its absolute-accuracy target. In this fresh campaign,',
        'the ordinary 5/s fixed-P0 reference also transferred accurately, so the earlier failure cannot be',
        'attributed to rate mismatch or declared repaired by rate matching. Chronology, fresh instances and',
        'unmeasured physical state differ across campaigns. Matching an EPP setting does not fix physical frequency.',
        'The campaigns are separate empirical episodes, not randomized trials of why the historical failure occurred.', '',
        'The defensible claim is accurate empirical-CDF transfer in this episode, without demonstrated incremental',
        'advantage from matching the offered rate. This result establishes neither a novel estimator nor a general',
        'reliability diagnostic. Preserve the preceding failure alongside this success in the empirical paper.',
        'Close this bounded collection branch; do not automatically repeat, change deadlines or fit a rule to',
        'these validation outcomes. The friend-owned independent V31 replication remains pending.', '',
        'Reproduce this assessment with `python3 -B analysis/review_nginx_rate_transfer.py --verify`.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    report = calculate()
    if args.verify:
        for path, digest in c.read(OUT / 'seal.json')['files_sha256'].items():
            c.require(c.sha(ROOT / path) == digest, 'Assessment changed: ' + path)
        c.require(report == c.read(OUT / 'report.json') and markdown(report) == (OUT / 'report.md').read_text(),
            'Rate-transfer assessment replay differs')
        print('Complete rate-transfer evidence, forecast barriers, cleanup and sealed assessment verify.')
    else:
        snapshot = g.snapshot(); baseline = c.read(c.BASE / 'policy-baseline.json')
        c.require(snapshot == baseline, 'Current host policy differs from prepared baseline')
        OUT.mkdir(parents=True, exist_ok=False)
        c.save(OUT / 'report.json', report)
        with (OUT / 'report.md').open('x') as f: f.write(markdown(report))
        c.save(OUT / 'host-policy-check.json', dict(snapshot=snapshot, prepared_baseline=baseline,
            matched_now=True, host_policy_writes=False, performance_measurement=False))
        paths = [Path(__file__), OUT / 'report.json', OUT / 'report.md', OUT / 'host-policy-check.json']
        c.save(OUT / 'seal.json', dict(files_sha256={str(p.relative_to(ROOT)): c.sha(p) for p in paths}))
        print('Completed rate-transfer assessment preserved: ' + str(OUT / 'report.md'))


if __name__ == '__main__': main()
