#!/usr/bin/env python3
"""Verify complete NGINX campaign and describe its retained accuracy limitation."""
from pathlib import Path
import math
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_prediction_common as c
import nginx_prediction_model as model
import nginx_prediction_study as s


def describe(case):
    result = c.read(case / 'result.json')
    raw = c.read(case / 'measurement.json')['Rows']
    values = sorted(r['e2e_ns'] for r in result['outcomes'])
    return dict(config=result['config'], offers=result['offers'], successful=result['successful'],
        median_e2e_ms=st.median(values) / 1e6,
        p05_e2e_ms=values[math.ceil(.05 * len(values)) - 1] / 1e6,
        p95_e2e_ms=values[math.ceil(.95 * len(values)) - 1] / 1e6,
        median_dispatch_ms=st.median(r['DispatchNs'] - r['ScheduledNs'] for r in raw) / 1e6,
        median_dispatch_to_full_body_ms=st.median(r['BodyDoneNs'] - r['DispatchNs'] for r in raw) / 1e6,
        cpu_ms_per_offer=result['measurement_counter_delta']['usage_usec'] / len(values) / 1000,
        measurement_throttled_periods=result['measurement_counter_delta']['nr_throttled'],
        measurement_throttled_usec=result['measurement_counter_delta']['throttled_usec'],
        domain_exits=result['domain_exits'],
        stock_request_accounting_exact=result['stock_request_accounting']['exact'])


def main():
    replay = s.replay()
    c.require(replay['status'] == 'full_response_prediction_accuracy_not_supported', 'Unexpected campaign status')
    base = c.BASE / 'campaign'
    summary = c.read(base / 'summary.json')
    comparison = c.read(base / 'comparison.json')
    forecast = c.read(base / 'forecast/forecast.json')
    calibration = [describe(base / 'calibration' / f"cohort-{cfg['index']}") for cfg in c.configs('calibration')]
    validation = [describe(base / 'validation' / f"cohort-{cfg['index']}") for cfg in c.configs('validation')]
    pilot = [describe(base / 'pilot' / f"cohort-{cfg['index']}") for cfg in c.configs('pilot')]
    all_rows = pilot + calibration + validation
    c.require(all(r['offers'] == r['successful'] and not r['domain_exits'] and
        r['measurement_throttled_periods'] == r['measurement_throttled_usec'] == 0 and
        r['stock_request_accounting_exact'] for r in all_rows), 'Campaign eligibility differs')
    profiles = []
    for p in 'ABC':
        errors = [e for e in comparison['errors'] if e['profile'] == p]
        profiles.append(dict(profile=p, exact_rate_rps=1e9 / c.PROTOCOL['validation_intervals_ns'][p],
            observed_mean_miss_pct=100 * st.mean(e['observed_miss_fraction'] for e in errors),
            observed_range_miss_pct=[100 * min(e['observed_miss_fraction'] for e in errors),
                                     100 * max(e['observed_miss_fraction'] for e in errors)],
            forecast_miss_pct=50, mae_pp=st.mean(e['absolute_error_pp'] for e in errors)))
    largest = max(comparison['errors'], key=lambda e: e['absolute_error_pp'])
    anomaly = next(r for r in validation if r['config']['block'] == largest['block'] and
                   r['config']['profile'] == largest['profile'])
    # Secondary endpoints are retained exactly; they never replace the primary.
    for deadline, expected in [('10000000', 1), ('25000000', 0), ('50000000', 0)]:
        value = comparison['secondary_deadlines'][deadline]
        c.require(value['predicted'] == expected and all(x == expected for x in value['observed_by_trial']),
                  'Secondary result differs')
    c.require(comparison['mean_block_mae_pp'] > 5 and
              comparison['conditional_model_based_95_interval_pp'][1] > 5, 'Primary gate replay differs')
    out = ROOT / 'analysis/runtime_io_nginx_prediction_result_review/20261009-generation01'
    if out.exists():
        for name, digest in c.read(out / 'evidence-seal.json')['files_sha256'].items():
            c.require(c.sha(ROOT / name) == digest, 'Result review changed')
        print('Campaign and result review verify:', out / 'report.md'); return
    out.mkdir(parents=True)
    c.save(out / 'report.json', dict(status='verified_complete_accuracy_not_supported', replay=replay,
        elapsed_sec=summary['elapsed_sec'], fresh_calibration_offers=1600, held_out_validation_offers=5400,
        new_rate_qualification_offers=300, services=25, warmup_offers=625,
        all_complete_correct=True, all_measurement_throttle_deltas_zero=True,
        all_runtime_identity_accounting_cleanup_verified=True,
        primary_deadline_ns=comparison['primary_deadline_ns'], predicted_miss_fraction=.5,
        mean_block_mae_pp=comparison['mean_block_mae_pp'],
        conditional_model_based_95_interval_pp=comparison['conditional_model_based_95_interval_pp'],
        profiles=profiles, calibration=calibration, validation=validation,
        calibration_cohort_miss_fractions=forecast['primary_cohort_miss_fractions'],
        largest_error=largest, largest_error_cohort=anomaly,
        calibration_sensitivity_mae_pp=comparison['calibration_cohort_sensitivity_mae_pp'],
        primary_result_unchanged=True, scheduler_or_internal_queue_cause_established=False,
        original_v31_claim_refuted=False, novelty_established=False,
        interpretation='Zero recorded measurement throttling and stable runtime/measurement checks did not ensure the declared accuracy of a rate-invariant full-response empirical forecast in this campaign.',
        next_step='Retain the negative boundary result in the extension; inspect saved timing/state records before any separately justified prospective study. Do not rerun, trim the large excursion, relax the gate or substitute secondary deadlines.'))
    lines = ['# NGINX prospective prediction: complete, accuracy not supported', '',
        'All sealed raw records and the prospective comparison replay verify. The',
        'campaign completed in 1,742.660 seconds (29 minutes 2.660 seconds): three',
        'new-rate qualification services, four fresh calibration services and',
        'eighteen held-out validation services. All 7,300 measured offers and 625',
        'warmup offers returned correct complete compressed bodies. All measurement',
        'throttle increments were zero; dispatch, source/runtime identity, process',
        'stability, exact request accounting, observer inventory and owned cleanup',
        'verify. There were no technical or applicability exits.', '',
        'The calibration-only lower-median deadline was 20,565,395 ns (20.565395 ms).',
        'The sealed forecast was 50% misses at all three validation rates. The',
        'primary equal-profile/block mean absolute error was 5.981481 percentage',
        'points. Its declared conditional model-based 95% interval was',
        '[1.320988, 10.641975] points; the required upper endpoint was <=5.',
        'The accuracy criterion failed. This interval does not establish that the',
        'unknown population mean error exceeds five points, and does not propagate',
        'calibration uncertainty.', '',
        '| Rate requests/s | Mean observed miss % | Frozen forecast % | Mean absolute error pp |',
        '|---:|---:|---:|---:|']
    for p in profiles:
        lines.append(f"| {p['exact_rate_rps']:.6g} | {p['observed_mean_miss_pct']:.3f} | 50.000 | {p['mae_pp']:.3f} |")
    lines += ['',
        'At 8 requests/s, all six trials had fewer misses than forecast (41.000–',
        '46.667%), giving 6.389-point mean absolute error. At approximately 6',
        'requests/s, block 2 had 88.333% misses and 38.333-point error; the other',
        'five trials had 40.333–48.333% misses. Retain that excursion in every',
        'primary calculation. Block 2 mean error was 14.778 points.', '',
        'The excursion cohort median full-response latency was 21.438653 ms.',
        'Median scheduled-to-dispatch time was 0.541647 ms and median dispatch-to-',
        'full-body time was 20.857623 ms. The latter includes server waiting,',
        'compression and delivery; it is not an observed processing stage. These',
        'records locate a longer response interval without diagnosing its cause.', '',
        'The fresh reference-rate calibration itself varied: miss fractions at',
        'the pooled deadline were 44.500%, 56.250%, 48.500% and 50.750%. Its cohort',
        'medians ranged from 20.510439 to 20.621183 ms. A steep deadline region can',
        'turn small duration shifts into substantial miss-fraction differences;',
        'the observed calibration variation limits a stationarity claim. The',
        'predeclared cohort-probability sensitivity MAEs were 5.296, 11.463, 5.111',
        'and 6.574 points. These are descriptive and do not change the pooled fit.', '',
        'At the secondary 10 ms deadline, forecast and observation were all misses;',
        'at 25 and 50 ms, both were zero observed misses. These broad secondary',
        'matches do not rescue the failed primary transition-region prediction or',
        'guarantee zero future misses.', '',
        'This is a scientific accuracy limitation for the newly scoped full-response',
        'NGINX forecast, rather than another unavailable qualification. It adds',
        'negative application-transfer evidence to the manuscript extension: zero',
        'measurement throttling and successful apparatus checks were insufficient',
        'to ensure the declared rate-invariant forecast accuracy in this campaign.',
        'The original queue-adjusted V31 confirmation remains valid in its own',
        'tested domain; NGINX did not observe that queue or test its paired-stage',
        'comparator. No new algorithm, universal counterexample, identified scheduler',
        'mechanism, novelty or independent-host replication has been established.', '',
        'Preserve this completed generation. Do not rerun it, remove block 2,',
        'select another deadline, relax the gate or replace calibration with pilot',
        'data. The next step is consolidation and saved-evidence diagnosis before',
        'any separately justified prospective follow-up.', '']
    (out / 'report.md').write_text('\n'.join(lines))
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md',
             c.BASE / 'bundle-seal.json', base / 'evidence-seal.json']
    c.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): c.sha(p) for p in paths}))
    print(out / 'report.md')


if __name__ == '__main__': main()
