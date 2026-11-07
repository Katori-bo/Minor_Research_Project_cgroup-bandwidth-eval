#!/usr/bin/env python3
"""Read-only replay and sealed assessment of the completed fresh confirmation."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_power_confirmation_common as c
import nginx_power_confirmation_guard as g
import nginx_power_confirmation_model as m
import nginx_power_confirmation_study as s

OUT = ROOT / 'analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01'


def calculate():
    with contextlib.redirect_stdout(io.StringIO()):
        result = s.replay()
    campaign = c.BASE / 'campaign'
    groups = {phase: c.read(campaign / phase / 'summary.json')['rows']
              for phase in ('calibration', 'validation')}
    policies = {}
    counts = {}
    deadline = result['primary']['errors'][0]['predictions']
    c.require(len(deadline) == 6, 'Ordinary comparison inventory differs')
    deadline = c.PROTOCOL['primary_deadline_ns']
    for phase, rows in groups.items():
        counts[phase] = dict(cohorts=len(rows), measurement_offers=sum(r['offers'] for r in rows),
            warmup_offers=sum(len(r['warmup_outcomes']) for r in rows),
            unsuccessful_measurement=sum(r['offers'] - r['successful'] for r in rows),
            unsuccessful_warmup=sum(not o['success'] for r in rows for o in r['warmup_outcomes']),
            throttled_measurement_cohorts=sum(bool(r['measurement_counter_delta']['nr_throttled'] or
                r['measurement_counter_delta']['throttled_usec']) for r in rows),
            throttled_warmup_cohorts=sum(bool(r['warmup_counter_delta']['nr_throttled'] or
                r['warmup_counter_delta']['throttled_usec']) for r in rows),
            observation_flags=[dict(config=r['config'], observations=r['observations']) for r in rows if r['observations']])
        policies[phase] = {}
        for policy in ('P0', 'P1'):
            group = [r for r in rows if r['config']['policy'] == policy]
            outcomes = [o for r in group for o in r['outcomes']]
            timing = [o['e2e_ns'] for o in outcomes if o['success']]
            policies[phase][policy] = dict(offers=len(outcomes),
                observed_miss_percent=100 * m.miss_fraction(outcomes, deadline),
                cohort_miss_percent=[100 * m.miss_fraction(r['outcomes'], deadline) for r in group],
                mean_successful_response_ms=st.mean(timing) / 1e6 if timing else None,
                successful_response_fraction_within_0_5ms_of_deadline=sum(abs(x-deadline) <= 500000 for x in timing) / len(timing) if timing else None,
                mean_stages_ms={k: st.mean(r['mean_stages_ns'][k] for r in group) / 1e6
                    for k in ('dispatch_ns', 'headers_ns', 'body_ns')})
    cases = [campaign / phase / f"cohort-{r['config']['index']}" for phase, rows in groups.items() for r in rows]
    c.require(all(c.read(case / 'policy-journal.json')['status'] == 'restored' and
        not c.read(case / 'cleanup.json')['errors'] for case in cases), 'Cleanup/restoration differs')
    return dict(status=result['status'], primary_deadline_ns=deadline,
        campaign_summary=c.read(campaign / 'summary.json'), counts=counts, policies=policies,
        methods=result['primary']['methods'], matched_gain_pp=result['primary']['matched_gain_pp'],
        gain_criterion_met=result['useful_gain'], accuracy_criterion_met=result['useful_absolute_accuracy'],
        primary_cohort_errors=result['primary']['errors'],
        calibration_cohort_sensitivity=result['calibration_cohort_sensitivity'],
        assigned_policy_contrast_pp=result['primary']['assigned_policy_miss_difference_pp'],
        conditional_policy_randomization_p=result['primary']['conditional_sharp_null_randomization_p'],
        secondary_methods={d: panel['methods'] for d, panel in result['secondary'].items()},
        qualification_raw_replay_verified=True, complete_campaign_raw_replay_verified=True,
        forecast_barriers_verified=True, cleanup_restoration_records_verified=True,
        campaign_evidence_seal_sha256=c.sha(campaign / 'evidence-seal.json'),
        preparation_seal_sha256=c.sha(c.BASE / 'preparation-seal.json'),
        novelty_established=False, historical_excursion_cause_identified=False,
        decision='Close this bounded collection branch. Report improvement without sufficient absolute accuracy; do not retune, retry, pool with the stopped pilot, or develop an outcome-fitted diagnostic from confirmation labels.')


def markdown(r):
    lines = ['# Completed NGINX policy-matching confirmation', '',
        '10 October 2026. The original pilot and fresh confirmation remain sealed and unchanged.', '',
        '**Policy matching improved the pooled comparison but failed the frozen absolute-accuracy criterion.**', '',
        'The new qualification passed, and all four calibration and twenty-four validation cohorts',
        'completed: 8,800 measurement offers and 700 warmup offers. The scientific campaign',
        f"lasted {r['campaign_summary']['elapsed_sec'] / 60:.2f} minutes. Full raw replay, source/evidence seals,",
        'global and pre-measurement warmup forecast barriers, owned cleanup and policy restoration verify.',
        'A separate current-host readback matched the prepared policy baseline when this review was created.', '',
        'The repeated “Selection seal verifies; service implementation/qualification remain pending”',
        'line is an inherited selection-validator message in `gzip_candidate_prepare.py`.',
        'It is not the fresh confirmation’s status: the fresh qualification and complete campaign verify.', '',
        '## Frozen primary result', '',
        'Primary deadline: 20.565395 ms. Errors concern all-offer deadline-miss probabilities,',
        'in percentage points (pp), rather than response-time error or percent relative improvement.', '',
        '| Forecast | Mean absolute error (pp) | Conditional 95% interval (pp) | Maximum error (pp) | Cohorts >5 pp |',
        '|---|---:|---:|---:|---:|']
    labels = dict(pooled='Pooled calibration', matched='Policy-matched calibration', baseline='P0-only calibration',
        warmup='25-offer target-rate warmup', matched_update='Matched + warmup samples', pooled_update='Pooled + warmup samples')
    for name, v in r['methods'].items():
        lo, hi = v['conditional_95_interval']
        lines.append(f"| {labels[name]} | {v['mean']:.3f} | [{lo:.3f}, {hi:.3f}] | {v['maximum_error_pp']:.3f} | {v['errors_above_5pp']}/24 |")
    gain = r['matched_gain_pp']; lo, hi = gain['conditional_95_interval']
    lines += ['', f"Matched improvement over pooled calibration is {gain['mean']:.3f} pp, with conditional",
        f"95% interval [{lo:.3f}, {hi:.3f}] pp. This meets the frozen mean improvement >=2 pp",
        'and positive interval-lower-bound conditions. It does not establish a >=2 pp lower confidence bound.', '',
        'Matched mean error is 15.708 pp and its conditional upper bound is 18.721 pp,',
        'above the required <=5 pp. Therefore the combined acceptance result is negative.',
        'Warmup is more accurate on average in this campaign, but its upper bound is 8.974 pp',
        'and its maximum error is 25 pp. It has a later decision time and additional acquisition',
        'budget; it does not rescue the primary matched-calibration claim or establish a reliable rule.', '',
        'Intervals condition on the frozen calibration and assume adequate independence among',
        'six consecutive block means. They do not propagate calibration uncertainty or provide',
        'a guarantee for each future cohort. All blocks and both policies remain included.', '',
        '## What failed to transfer', '',
        'P0 (powersave / balance_performance) calibration predicted 79.5% misses. Its two',
        'calibration cohorts gave 81% and 78%; agreement between them did not ensure transfer.',
        'P0 validation averaged 48.889% misses, ranging from 36.333% to 84.333% across its',
        'twelve cohorts. Its policy-specific MAE was about 31 pp. P1 (powersave / performance)',
        'had zero recorded deadline misses in calibration and all twelve validation cohorts;',
        'this finite sample does not certify a zero future miss probability.', '',
        'Neither calibration nor validation recorded throttling, unsuccessful offers, overlap',
        'or dispatch-gate observations. Allowing throttling enabled a complete prospective',
        'contract, but no recorded throttle event explains this confirmation’s prediction failure.', '',
        'The successful P0 mean response changed from 20.507 ms in calibration to 20.190 ms',
        'in validation, a decrease of about 0.317 ms. A large share of validation responses',
        '(61.94%) lay within 0.5 ms of the fixed deadline. This is descriptive evidence that',
        'small timing-distribution changes can produce large miss-probability changes at this',
        'deadline; it does not identify the physical cause. Calibration was at 5/s and validation',
        'at 4/s or 8/s, in later fresh instances. Rate, chronology, distribution shape and',
        'unmeasured physical state remain possible explanations. Matching EPP does not measure',
        'fixed frequency, thermals, idle state or exclusive access to shared CPU resources.', '',
        'The assigned-policy contrast in validation is strong, but an effect of policy and',
        'accurate within-policy forecast transfer are different questions. The randomized',
        'contrast still requires no interference/carryover assumptions; it cannot explain',
        'the historical unobserved NGINX excursion. Pooled calibration deliberately combines',
        'different assigned policies, so its defeat does not establish superiority over an',
        'established state-aware prediction method.', '',
        'At the fixed secondary 10 ms deadline every measured response missed; at 25 and',
        '50 ms every measured response met the deadline. Zero global-CDF errors there are',
        'trivial endpoint saturation in this sample, not grounds to replace the failed primary deadline.', '',
        '## Paper contribution and next decision', '',
        'A defensible empirical statement is: **under this single-host NGINX workload,',
        'matching the assigned EPP policy reduced mean deadline-probability error relative',
        'to pooled calibration, but did not suffice for the frozen accuracy target.**', '',
        'This strengthens the empirical account of where inexpensive calibration transfers',
        'and where it fails. It does not establish a novel estimator, a general reliability',
        'diagnostic, physical frequency causation or conference-level novelty by itself.',
        'Keep the independent V31 replication separate. Treat the stopped pilot as exploratory',
        'and this fresh confirmation as the complete prospective outcome; do not combine',
        'them into a favorable acceptance test. Close this bounded collection branch and',
        'integrate the result into the empirical paper without further automatic runs,',
        'deadline changes or a diagnostic fitted to these validation outcomes.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    report = calculate()
    if args.verify:
        seal = c.read(OUT / 'seal.json')
        for path, digest in seal['files_sha256'].items():
            c.require(c.sha(ROOT / path) == digest, 'Review changed: ' + path)
        c.require(report == c.read(OUT / 'report.json') and markdown(report) == (OUT / 'report.md').read_text(),
                  'Confirmation assessment replay differs')
        print('Complete confirmation, forecast barriers, restoration records and sealed assessment verify.')
    else:
        OUT.mkdir(parents=True, exist_ok=False)
        c.save(OUT / 'report.json', report)
        with (OUT / 'report.md').open('x') as f: f.write(markdown(report))
        c.save(OUT / 'host-restoration-check.json', dict(snapshot=g.snapshot(),
            prepared_baseline=c.read(c.BASE / 'policy-baseline.json'),
            restored_now=g.snapshot() == c.read(c.BASE / 'policy-baseline.json'),
            performance_measurement=False))
        paths = [Path(__file__), OUT / 'report.json', OUT / 'report.md', OUT / 'host-restoration-check.json']
        c.save(OUT / 'seal.json', dict(files_sha256={str(p.relative_to(ROOT)): c.sha(p) for p in paths}))
        print('Complete negative confirmation assessed and preserved: ' + str(OUT / 'report.md'))


if __name__ == '__main__': main()
