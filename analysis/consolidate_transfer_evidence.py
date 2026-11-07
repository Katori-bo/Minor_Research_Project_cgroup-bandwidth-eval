#!/usr/bin/env python3
"""Consolidate saved transfer results without fitting a predictor or collecting traffic."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_transfer_consolidation/20261010'
DOC = ROOT / 'docs/runtime_io_transfer_consolidation_20261010.md'
PAPER = ROOT / 'paper/deadline_transfer_contribution_note.md'
SOURCES = ROOT / 'docs/runtime_io_transfer_consolidation_sources_20261010.json'
CHECKS = ['analysis/verify_deadline_extension_revision.py',
    'analysis/screen_forecast_reliability.py', 'analysis/screen_recent_timing_observable.py',
    'analysis/review_nginx_power_stopped.py', 'analysis/review_nginx_power_confirmation.py',
    'analysis/review_nginx_rate_transfer.py']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def calculate():
    inputs = {}
    def consume(rel):
        path = ROOT / rel
        inputs[rel] = sha(path)
        return json.loads(path.read_text())
    v30 = consume('analysis/runtime_io_v30_result_review/20261009-generation01/report.json')
    v31 = consume('analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
    revision = consume('analysis/runtime_io_deadline_extension_revision/20261010-review-corrections/report.json')
    nginx = consume('analysis/runtime_io_nginx_prediction_result_review/20261009-generation01/report.json')
    power = consume('analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.json')
    rate = consume('analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.json')
    consume('analysis/runtime_io_nginx_power_policy_review/20261010-generation01/report.json')
    require(all(v30['primary_gates'].values()) and all(v31['gates'].values()), 'Go primary gates changed')
    require(nginx['status'] == 'verified_complete_accuracy_not_supported', 'Original NGINX outcome changed')
    require(not power['accuracy_criterion_met'] and power['gain_criterion_met'], 'Power outcome changed')
    require(rate['accuracy_criterion_met'] and not rate['advantage_criterion_met'], 'Rate outcome changed')
    rows = [
        dict(study='Go V30', deadline_ms=25, reference='Periodic + delay', mae_pp=v30['primary_equal_profile_mae_pp'],
            comparator='Fluid busy FIFO', comparator_mae_pp=v30['secondary_deadline_mae_pp']['25']['fluid_busy'],
            status='Prospective gates passed', cohorts=18),
        dict(study='Go V31', deadline_ms=10, reference='Queue-adjusted CDF',
            mae_pp=v31['deadline_grid']['joint_calibration_cdf']['10']['mae_pp'],
            comparator='Periodic + delay', comparator_mae_pp=v31['deadline_grid']['periodic_uniform_phase_calibrated_delay']['10']['mae_pp'],
            status='Prospective gates passed in observed domain', cohorts=18),
        dict(study='NGINX original', deadline_ms=nginx['primary_deadline_ns']/1e6, reference='Complete-response CDF',
            mae_pp=nginx['mean_block_mae_pp'], accuracy_interval_pp=nginx['conditional_model_based_95_interval_pp'],
            status='Prospective accuracy gate not supported', cohorts=18),
        dict(study='NGINX power confirmation', deadline_ms=power['primary_deadline_ns']/1e6, reference='Policy-matched CDF',
            mae_pp=power['methods']['matched']['mean'], accuracy_interval_pp=power['methods']['matched']['conditional_95_interval'],
            comparator='Pooled policies', comparator_mae_pp=power['methods']['pooled']['mean'],
            gain_pp=power['matched_gain_pp'], status='Improvement passed; accuracy failed', cohorts=24),
        dict(study='NGINX rate transfer', deadline_ms=rate['primary_deadline_ns']/1e6, reference='Rate-matched CDF',
            mae_pp=rate['primary']['methods']['matched']['mean'], accuracy_interval_pp=rate['primary']['methods']['matched']['conditional_95_interval'],
            comparator='Fixed 5/s CDF', comparator_mae_pp=rate['primary']['methods']['baseline']['mean'],
            comparator_accuracy_interval_pp=rate['primary']['methods']['baseline']['conditional_95_interval'],
            gain_pp=rate['primary']['matched_gain_pp'], status='Accuracy passed; advantage not supported', cohorts=12)]
    table = ['| Study | Deadline (ms) | Reference MAE (pp) | Comparator MAE (pp) | Frozen result |',
             '|---|---:|---:|---:|---|']
    for row in rows:
        comparator = f"{row['comparator']}: {row['comparator_mae_pp']:.3f}" if 'comparator' in row else 'No head-to-head comparator'
        table.append(f"| {row['study']} | {row['deadline_ms']:.6f}".rstrip('0').rstrip('.') +
            f" | {row['reference']}: {row['mae_pp']:.3f} | {comparator} | {row['status']} |")
    control = revision['retrospective_control']
    flags = rate['counts']['validation']['observation_flags']
    return dict(date='2026-10-10', rows=rows, table_markdown='\n'.join(table),
        go_complete_response_control=dict(mae_pp=control['mae_pp'], maximum_error_pp=control['maximum_trial_error_pp'],
            samples=control['samples'], provenance='retrospective_method_selection; not prospective observer removal'),
        rate_reference_budgets=dict(per_known_rate_offers=800, both_target_rates_offers=1600,
            shared_5_rps_offers=800, pooled_offers=2400, scientific_campaign_total_offers=6450),
        retained_rate_throttling=[dict(cohort=x['config']['index'], block=x['config']['block'],
            rate_rps=x['config']['rate_rps'], nr_throttled=x['measurement_counter_delta']['nr_throttled'],
            throttled_usec=x['measurement_counter_delta']['throttled_usec']) for x in flags],
        source_record_sha256=inputs, independent_host_result_received=False,
        new_method_gap_established=False, new_estimator_novelty_established=False,
        historical_failure_cause_identified=False, state_of_the_art_superiority_tested=False,
        decision='Consolidate the scoped empirical paper. Hold new collection and custom diagnostics until a concrete capability, fair compatible comparator and independent evaluation contract exist.')


def checks():
    results = []
    for script in CHECKS:
        args = [sys.executable, '-B', script]
        if script != CHECKS[0]:
            args.append('--verify')
        completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=120)
        require(completed.returncode == 0, f'Saved-evidence verification failed: {script}\n{completed.stderr}\n{completed.stdout}')
        results.append(dict(command=args[1:], exit_code=completed.returncode,
            stdout=completed.stdout, stderr=completed.stderr, performance_collection=False))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        for rel, digest in json.loads((OUT / 'seal.json').read_text())['files_sha256'].items():
            require(sha(ROOT / rel) == digest, 'Consolidation/input file changed: ' + rel)
    receipt = checks()
    report = calculate()
    require(report['table_markdown'] in DOC.read_text(), 'Consolidation evidence table differs from source records')
    if args.verify:
        require(report == json.loads((OUT / 'report.json').read_text()), 'Consolidated results differ')
        require(DOC.read_bytes() == (OUT / 'assessment_snapshot.md').read_bytes(), 'Assessment snapshot differs')
        require(PAPER.read_bytes() == (OUT / 'contribution_snapshot.md').read_bytes(), 'Contribution snapshot differs')
        print('Consolidation inputs, numerical table, preservation checks and six saved-evidence verifiers pass. No performance collection.')
    else:
        OUT.mkdir(parents=True, exist_ok=False)
        for name, value in [('report.json', report), ('verification_receipt.json', receipt)]:
            with (OUT / name).open('x') as f:
                json.dump(value, f, indent=2); f.write('\n')
        for name, source in [('assessment_snapshot.md', DOC), ('contribution_snapshot.md', PAPER), ('sources.json', SOURCES)]:
            with (OUT / name).open('xb') as f: f.write(source.read_bytes())
        paths = [Path(__file__), DOC, PAPER, SOURCES, *OUT.iterdir(),
                 *(ROOT / p for p in report['source_record_sha256']), *(ROOT / p for p in CHECKS)]
        with (OUT / 'seal.json').open('x') as f:
            json.dump(dict(files_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths}), f, indent=2); f.write('\n')
        print('Transfer consolidation preserved: ' + str(DOC))


if __name__ == '__main__': main()
