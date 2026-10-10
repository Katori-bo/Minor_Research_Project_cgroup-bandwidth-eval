"""Read-only verification of the final empirical paper and saved-data figures.

Default prints the report. --write-report writes only the new finalization
report before its seal exists. Never collects data or fits a scientific model.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_paper_finalization/20261008'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def close(a, b):
    if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-8):
        raise ValueError(f'arithmetic disagreement: {a} vs {b}')


def seal(directory):
    d = read(directory / 'seal.json')
    files = d.get('files_sha256', d.get('files'))
    if files is None:
        raise ValueError('unknown seal schema: ' + str(directory))
    for name, expected in files.items():
        if digest(ROOT / directory / name) != expected:
            raise ValueError('saved seal mismatch: ' + str(directory / name))
    return len(files)


def verify():
    preservation = read(OUT.relative_to(ROOT) / 'preserved_evidence_sha256.json')
    for inventory in preservation.values():
        for name, expected in inventory.items():
            if digest(ROOT / name) != expected:
                raise ValueError('preserved evidence changed: ' + name)
    sealed = []
    for directory in ['runtime_io_v22_result_review/20261007', 'runtime_io_v23_result_review/20261007',
                      'runtime_io_v25_result_review/20261007', 'runtime_io_v26_result_review/20261007',
                      'runtime_io_v27r3_result_review/20261008', 'runtime_io_v28_result_review/20261008',
                      'runtime_io_v28/generation-01/analysis/1791438579821212637',
                      'runtime_io_v28/generation-01/predictions', 'runtime_io_v28/generation-01/calibration_review']:
        relative = Path('analysis') / directory
        sealed.append(dict(path=str(relative), files_checked=seal(relative)))
    figures = read(OUT.relative_to(ROOT) / 'figure_data.json')
    original_path = ROOT / figures['source_report']
    if digest(original_path) != figures['source_report_sha256']:
        raise ValueError('figure source report changed')
    original = json.loads(original_path.read_text())
    review = read('analysis/runtime_io_v28_result_review/20261008/report.json')
    doc = (ROOT / 'paper/capacity_calibration_empirical.md').read_text()
    tex = (ROOT / 'paper/capacity_calibration_empirical.tex').read_text()
    compilation = read(OUT.relative_to(ROOT) / 'compiler_status.json')
    if compilation['result']['kind'] != 'success' or compilation['source_sha256'] != digest(ROOT / compilation['source']):
        raise ValueError('successful compiler result is not tied to the final source')
    session = ROOT / 'analysis/runtime_io_v28/generation-01'
    preparation = json.loads((session / 'preparation/manifest.json').read_text())
    if preparation['baseline']['kernel'] != '7.2.8-arch1-2':
        raise ValueError('manuscript kernel differs from recorded preparation')
    identities = list((session / 'slots').glob('*/attempt-*/identity.json'))
    if len(identities) != 32 or any(json.loads(p.read_text())['health']['go_version'] != 'go1.26.1' for p in identities):
        raise ValueError('recorded runtime differs from manuscript')
    environment = json.loads((session / 'environment.json').read_text())
    for policy in environment['power_settings']['policies'].values():
        if policy['scaling_driver'] != 'amd-pstate-epp' or policy['scaling_governor'] != 'powersave' or policy['energy_performance_preference'] != 'balance_performance':
            raise ValueError('recorded frequency policy differs from manuscript')
    actual_cal = [dict(trial=r['trial'], throughput_rps=r['throughput_rps'], utilization=r['utilization'])
                  for r in original['trial_accounting'] if r['role'] in ('idle', 'steady')]
    if figures['calibration_points'] != actual_cal or len(actual_cal) != 12:
        raise ValueError('calibration figure observations differ')
    if figures['calibration_models'] != original['calibration']['methods']:
        raise ValueError('calibration figure uses changed fits')
    if figures['summary'] != review['methods'] or figures['advantages'] != review['advantages']:
        raise ValueError('figure summary differs from reviewed results')
    for method, metrics in review['methods'].items():
        errors = original['result']['methods'][method]['errors']
        if len(errors) != 16:
            raise ValueError('validation cohort changed')
        observed_by_trial = {r['trial']: r for r in errors}
        absolute_errors = []
        for trial in figures['validation_trials']:
            r = observed_by_trial[trial['trial']]
            close(trial['observed_miss_pct'], r['observed_miss_pct'])
            close(trial['forecasts'][method], r['predicted_miss_pct'])
            absolute_errors.append(abs(r['observed_miss_pct'] - r['predicted_miss_pct']))
        close(statistics.mean(absolute_errors), metrics['deadline_mae_pp'])
        close(max(absolute_errors), metrics['maximum_deadline_error_pp'])
        if sum(e <= 3 for e in absolute_errors) != metrics['deadline_pass_count']:
            raise ValueError('deadline pass count changed')
        for value in [metrics['capacity_rps'], metrics['deadline_mae_pp'], metrics['maximum_deadline_error_pp'],
                      metrics['maximum_capacity_error_pct']]:
            if f'{value:.3f}' not in doc or f'{value:.3f}' not in tex:
                raise ValueError('paper numeric table value absent: ' + str(value))
        if method == 'busy':
            continue
        busy = {r['trial']: r for r in original['result']['methods']['busy']['errors']}
        block_improvements = [statistics.mean(abs(r['observed_miss_pct']-r['predicted_miss_pct']) -
                    abs(busy[r['trial']]['observed_miss_pct']-busy[r['trial']]['predicted_miss_pct'])
                    for r in errors if r['block'] == b) for b in range(1, 5)]
        a = review['advantages'][method]
        for x, y in zip(block_improvements, a['block_improvements_pp']): close(x, y)
        mean = statistics.mean(block_improvements)
        half = 3.182446305284263 * statistics.stdev(block_improvements) / 2
        for x, y in zip([mean-half, mean+half], a['model_based_95_interval']): close(x, y)
    a = review['advantages']['quadratic']
    if a['frozen_advantage_pass'] or 'predictive_advantage_inconclusive' not in doc:
        raise ValueError('inconclusive decision changed')
    for key in ['regression', 'quadratic']:
        m = figures['calibration_models'][key]; x = m['capacity_rps']
        close(m['intercept'] + m['demand_sec']*x + m['quadratic_sec2']*x*x, .5)
    linear = figures['calibration_models']['regression']; quadratic = figures['calibration_models']['quadratic']
    for phrase in [f"{linear['intercept']:.7f}", f"{linear['demand_sec']:.8f}",
                   f"{quadratic['demand_sec']:.9f}", f"{abs(quadratic['quadratic_sec2']):.12f}",
                   f"{quadratic['calibration_max_throughput_rps']:.3f}", f"{quadratic['extrapolation_ratio']:.3f}"]:
        if phrase not in doc: raise ValueError('reported fit value differs from retained coefficient: ' + phrase)
    required = ['The calibration budgets differ', 'one host', '500 ms', 'unidentified',
                'Neither algorithm is reproduced here', 'sixteen fresh', 'approximately normal']
    for phrase in required:
        if phrase not in doc: raise ValueError('required limitation absent: ' + phrase)
    local_links = 0
    for filename in ['capacity_calibration_empirical.md', 'capacity_calibration_supporting_material.md',
                     'capacity_calibration_reproducibility.md', 'README.md']:
        path = ROOT / 'paper' / filename
        for destination in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if destination.startswith(('http://', 'https://')): continue
            target = (path.parent / destination.split('#')[0]).resolve()
            if target == OUT / 'report.json': continue
            if not target.exists(): raise ValueError('broken local link: ' + destination)
            local_links += 1
    if tex.count(r'\begin{figure}') != 2 or tex.count(r'\bibitem{') != 6:
        raise ValueError('figure/reference inventory changed')
    paper_files = sorted((ROOT / 'paper').glob('capacity_calibration*')) + [ROOT / 'paper/README.md']
    return dict(date='2026-10-08', decision='empirical_manuscript_finalized_existing_evidence',
        verification_scope='Saved-result statistics, figure coordinates, manuscript numbers/limitations, local links and retained hashes/seals. Prior independent raw-data audits are preserved; no new raw replay or fit.',
        protected_files_unchanged=len(preservation['protected']), additional_files_unchanged=len(preservation['additional']),
        seals_checked=sealed, calibration_points_checked=12, validation_trials_checked=16,
        method_trial_forecasts_checked=80, block_intervals_checked=4, local_links_checked=local_links,
        recorded_runtime_identities_checked=32,
        standalone_latex_compilation='success', compiled_pdf_page_layout_independently_inspected=False,
        png_figures_visually_inspected=True, external_pdf_exported=False,
        software_sha256={str(p.relative_to(ROOT)):digest(p) for p in
                         [ROOT/'analysis/finalize_empirical_paper.py', ROOT/'analysis/verify_empirical_paper.py']},
        manuscript_and_guide_sha256={str(p.relative_to(ROOT)):digest(p) for p in paper_files},
        scientific_collection_launched=False, new_models_fitted=False, thresholds_changed=False,
        mechanism_identified=False, superiority_over_published_algorithms_established=False,
        advantage_decision='predictive_advantage_inconclusive',
        composition_decision='composition_inconclusive', quota_period_selection='on_hold',
        submission_status='Scientific manuscript and local artifact guide complete; author/affiliation, venue formatting, external artifact URL and submission remain unset.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-report', action='store_true')
    args = parser.parse_args(); report = verify()
    if args.write_report:
        if (OUT / 'seal.json').exists(): raise ValueError('preserve finalized report; omit --write-report')
        (OUT / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
