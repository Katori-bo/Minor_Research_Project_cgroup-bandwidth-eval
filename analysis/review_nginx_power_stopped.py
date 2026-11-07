#!/usr/bin/env python3
"""Read-only replay and descriptive review of the stopped power-policy generation."""
import argparse
import json
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import nginx_power_common as c
import nginx_power_model as m
import nginx_power_study as s

OUT = ROOT / 'analysis/runtime_io_nginx_power_policy_review/20261010-generation01'


def calculate():
    schedule = c.verify_prepared(False)
    s.verify_qualification(schedule)
    qualified = c.read(c.BASE / 'qualified-seal.json')
    c.require(qualified['passed'] and qualified['preparation_sha256'] == c.sha(c.BASE / 'preparation-seal.json')
        and qualified['qualification_sha256'] == c.sha(c.BASE / 'qualification/evidence-seal.json'),
        'Qualified lineage changed')
    campaign = c.BASE / 'campaign'
    c.verify_evidence(campaign); s.verify_inventory(campaign)
    summary = c.read(campaign / 'summary.json')
    c.require(not summary['complete'] and summary['phase'] == 'validation' and summary['no_replacement'],
              'Expected a preserved stopped validation campaign')
    forecast, ref = s.verify_forecast(campaign / 'forecast', schedule)
    validation = campaign / 'validation'; c.verify_evidence(validation)
    partial = c.read(validation / 'summary.json')
    c.require(not partial['complete'] and partial['no_replacement'], 'Partial validation status differs')
    count = len(partial['rows']); configs = schedule['validation'][:count]
    c.require(count == 12 and {p.name for p in validation.glob('cohort-*')} ==
              {f"cohort-{cfg['index']}" for cfg in configs}, 'Foreign stopped-case inventory')
    rows = [s.replay_case(validation / f"cohort-{cfg['index']}", cfg, forecast, ref) for cfg in configs]
    c.require(rows == partial['rows'], 'Partial summary/raw replay differs')
    c.require(all(not r['domain_exits'] for r in rows[:-1]) and
              rows[-1]['domain_exits'] == ['measurement_throttling'], 'Foreign stopping pattern')
    errors = []
    for row in rows:
        obs = m.miss_fraction(row['outcomes'], 20565395)
        pred = m.predictions(forecast, row['config'], row['warmup_outcomes'], 20565395)
        errors.append(dict(config=row['config'], observed_miss_fraction=obs, predictions=pred,
            absolute_error_pp={k: 100 * abs(v - obs) for k, v in pred.items()},
            domain_exits=row['domain_exits'], successful=row['successful'],
            counter_delta=row['measurement_counter_delta']))
    methods = {}
    for name in errors[0]['predictions']:
        vals = [e['absolute_error_pp'][name] for e in errors]
        methods[name] = dict(descriptive_mae_pp=st.mean(vals), maximum_error_pp=max(vals),
            errors_above_5pp=sum(v > 5 for v in vals),
            block_mae_pp=[st.mean(e['absolute_error_pp'][name] for e in errors
                                 if e['config']['block'] == b) for b in (1, 2, 3)])
    policies = {p: dict(cohorts=sum(r['config']['policy'] == p for r in rows),
        observed_miss_percent=100 * st.mean(e['observed_miss_fraction'] for e in errors
                                          if e['config']['policy'] == p),
        mean_response_ms=st.mean(r['response_ns']['mean'] for r in rows if r['config']['policy'] == p) / 1e6,
        calibration_prediction_percent=100 * m.probability(forecast['samples_ns'][p], 20565395))
        for p in ('P0', 'P1')}
    cases = [validation / f"cohort-{cfg['index']}" for cfg in configs]
    c.require(all(c.read(p / 'policy-journal.json')['status'] == 'restored' and
                  not c.read(p / 'cleanup.json')['errors'] for p in cases), 'Cleanup/restoration failed')
    return dict(status='stopped_domain_exit_partial_descriptive_result', elapsed_sec=summary['elapsed_sec'],
        original_stop=summary, completed_calibration_cohorts=4, calibration_offers=1600,
        completed_validation_cohorts=count, planned_validation_cohorts=24,
        validation_offers=sum(r['offers'] for r in rows),
        validation_successful=sum(r['successful'] for r in rows), complete_balanced_blocks=3,
        within_domain_complete_blocks=2, primary_deadline_ns=20565395,
        stopped_cohort=rows[-1]['config'], throttle_delta=rows[-1]['measurement_counter_delta'],
        methods=methods, policy_summary=policies, cohort_errors=errors,
        qualification_replay_verified=True, evidence_seals_verified=True,
        fresh_global_and_warmup_prediction_barriers_verified=True,
        cleanup_and_restoration_records_verified=True, six_block_acceptance_test_available=False,
        novelty_established=False, historical_excursion_cause_identified=False,
        interpretation='All twelve collected cohorts, including the domain exit, are retained. These are outcome-stopped partial descriptive results, not the planned six-block acceptance test, a clean in-domain experiment or a new estimator.')


def markdown(r):
    lines = ['# Stopped NGINX power-policy study: verified partial results', '',
        '10 October 2026. Original generation and all sealed evidence remain unchanged.', '',
        '## Stop and restoration', '',
        'The campaign intentionally stopped at validation cohort 12: P0 at 8 requests/s,',
        'block 3. It recorded one throttled period and 11,793 us (11.793 ms) of',
        'aggregate throttle time during the measurement counter window. This violates',
        'the declared zero-throttling domain. All 300 responses in that cohort',
        'succeeded; success and deadline compliance are different endpoints.', '',
        'Hardware qualification, source/evidence seals, four fresh calibration cohorts,',
        'global forecast and pre-measurement warmup forecast barriers, and all twelve',
        'validation raw replays verify. All collected validation cases record verified',
        'policy restoration and no owned-cleanup errors. The last policy journal',
        'restored the original full policy snapshot. Current-host readback was also',
        'checked separately during review; it is not a new performance measurement.', '',
        'The scientific campaign lasted about 20.94 minutes before stopping. It',
        'contains 1,600 calibration and 3,600 validation measurement offers, plus',
        'their original warmup records. Twelve of the twenty-four planned validation',
        'cohorts were collected: three balanced blocks, with the third containing',
        'the domain exit. Only two complete blocks satisfy the intended domain.', '',
        '## What the partial evidence shows', '',
        'At the unchanged 20.565395 ms deadline, the fresh P0 calibration prediction',
        'was 80.875% misses and P1 was 0%. Across the twelve collected validation',
        'cohorts, P0 averaged 80.167% misses and P1 0%; mean full responses were',
        '20.543 and 16.695 ms respectively. These are descriptive policy contrasts',
        'on this interrupted, single-host study. A preference readback does not',
        'measure fixed frequency or isolate the physical mechanism.', '',
        '| Forecast | Partial MAE (pp) | Maximum error (pp) | Errors >5 pp |',
        '|---|---:|---:|---:|']
    labels = {'pooled':'Pooled CDF', 'matched':'Policy-matched CDF', 'baseline':'P0-only CDF',
              'warmup':'25-offer warmup CDF', 'matched_update':'Matched + warmup samples',
              'pooled_update':'Pooled + warmup samples'}
    for name, v in r['methods'].items():
        lines.append(f"| {labels[name]} | {v['descriptive_mae_pp']:.3f} | {v['maximum_error_pp']:.3f} | {v['errors_above_5pp']}/12 |")
    lines += ['', 'All twelve cohorts are retained in these numbers, including cohort 12.',
        'Pooling responses from two different assigned policies produced a poor',
        'forecast here; ordinary policy-matched calibration transferred much better',
        'over the observed prefix. Warmup-only profiling was less accurate than',
        'the larger matched reference. This does not establish a new estimator.', '',
        '## Interpretation and research decision', '',
        '**The planned six-block acceptance test is unavailable.** Do not run the',
        'complete-campaign comparator on an invented twenty-four-row dataset, apply',
        'the six-block criterion to three blocks, drop the throttled cohort, or',
        'call the stopped prefix a successful non-throttled experiment. Stopping',
        'depends on an observed outcome, so confidence statements cannot ignore it.', '',
        'The observed benefit is strong exploratory evidence for the value of',
        'matching an explicitly controlled policy in this configuration. It does',
        'not establish that policy explains the original unobserved NGINX excursion,',
        'a general transfer guarantee, or a novel reliability diagnostic. The pooled',
        'comparator deliberately combines both policies; the finding supports an',
        'ordinary calibration condition rather than superiority over an existing',
        'state-aware method.', '',
        'Preserve generation-01 and do not resume, replace, relax its gate or rerun',
        'until it passes. There is no collector bug demonstrated by this traceback.',
        'A subsequent scientific run would need a separately justified and frozen',
        'contract, such as predicting all-offer outcomes while explicitly allowing',
        'quota throttling. That would answer a broader question than the original',
        'zero-throttling pilot; changing the population after seeing this outcome',
        'must be disclosed. No new campaign is launched by this review.', '',
        '## Reproduction', '', '```bash',
        'python3 -B analysis/review_nginx_power_stopped.py --verify', '```', '',
        '`report.json` contains every collected cohort and comparator. The original',
        'runner sources and original campaign records are not edited by this review.']
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(); report = calculate(); md = markdown(report)
    if args.verify:
        seal = c.read(OUT / 'seal.json')
        for path, digest in seal['files_sha256'].items():
            c.require(c.sha(ROOT / path) == digest, 'Review package changed: ' + path)
        c.require(report == c.read(OUT / 'report.json') and md == (OUT / 'report.md').read_text(),
                  'Stopped review replay differs')
        print('Stopped campaign seals, all twelve raw cohorts, forecasts and review package verify.')
    else:
        OUT.mkdir(parents=True, exist_ok=False)
        import nginx_power_guard as guard
        current = guard.snapshot()
        c.save(OUT / 'host-restoration-check.json', dict(current_snapshot=current,
            matches_prepared_baseline=current == c.read(c.BASE / 'policy-baseline.json'),
            purpose='read-only review-time policy check, not performance evidence'))
        c.require(current == c.read(c.BASE / 'policy-baseline.json'), 'Current host policy baseline differs')
        c.save(OUT / 'report.json', report); (OUT / 'report.md').write_text(md)
        paths = [Path(__file__).resolve(), OUT / 'report.json', OUT / 'report.md', OUT / 'host-restoration-check.json',
            c.BASE / 'preparation-seal.json', c.BASE / 'qualified-seal.json',
            c.BASE / 'campaign/evidence-seal.json']
        c.save(OUT / 'seal.json', dict(files_sha256={str(p.relative_to(ROOT)): c.sha(p) for p in paths},
            scope='additive saved-data review; preserves source experiment'))
        print(str(OUT / 'report.md'))


if __name__ == '__main__': main()
