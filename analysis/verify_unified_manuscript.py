"""Read-only saved-evidence verification of the unified empirical manuscript."""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import render_unified_manuscript as renderer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_unified_closeout/20261011'
DOCUMENTS = ['RESEARCH_FINAL.md', 'paper/unified_manuscript.md',
             'paper/unified_manuscript.tex', 'paper/unified_supporting_material.md',
             'paper/unified_reproducibility.md', 'docs/unified_claim_novelty_comparison_20261011.md',
             'docs/unified_independent_evidence_status_20261011.md']
STUDIES = [
    ('Go', 'handoff/slo-host01-20261011-local-supplement-03',
     'analysis/runtime_io_slo_independent/local-supplement01-return.json'),
    ('NGINX', 'handoff/slo-host01-20261011-nginx-completion-04',
     'analysis/runtime_io_slo_independent/20261011-nginx-completion01-observed-review-01/final_report.json')]
PRIMARY = 'q/39/40'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def probability(value):
    return Fraction(value['numerator'], value['denominator'])


def history():
    result = subprocess.run([sys.executable, '-B', 'analysis/verify_empirical_consolidation.py'],
                            cwd=ROOT, capture_output=True, text=True, timeout=360)
    require(result.returncode == 0, result.stdout + result.stderr)
    spec = importlib.util.spec_from_file_location('capacity_history', ROOT / 'analysis/verify_empirical_paper.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    snapshot = ROOT / 'analysis/runtime_io_quota_update_replay/20261008/provenance/status_after/docs/current_research_plan.md'
    require(sha(snapshot) == 'cc909de7dcf38834386b60c8dcb2ea28b7c17066ecd824357b40d16b1f702e51',
            'Historical capacity planning version differs')
    with tempfile.TemporaryDirectory(prefix='unified-capacity-history-') as directory:
        shadow = Path(directory)
        for path in ROOT.iterdir():
            if path.name != 'docs':
                (shadow / path.name).symlink_to(path, target_is_directory=path.is_dir())
        (shadow / 'docs').mkdir()
        for path in (ROOT / 'docs').iterdir():
            source = snapshot if path.name == 'current_research_plan.md' else path
            (shadow / 'docs' / path.name).symlink_to(source, target_is_directory=source.is_dir())
        module.ROOT = shadow
        module.OUT = shadow / 'analysis/runtime_io_paper_finalization/20261008'
        capacity = module.verify()
    return dict(deadline_consolidation=dict(exit_code=0, stdout=result.stdout, stderr=result.stderr),
                capacity_recorded_version=capacity, old_checker_or_seals_modified=False,
                current_live_planning_file_modified=False, performance_collection=False)


def replay_studies():
    receipts = []
    for app, package, report in STUDIES:
        package_path = ROOT / package
        # Pass absolute paths: the original assembler compares source and resolved
        # campaign paths lexically when recording carried_closed_attempt.
        with tempfile.TemporaryDirectory(prefix='unified-decision-return-') as directory:
            target = Path(directory) / 'report.json'
            completed = subprocess.run([sys.executable, '-B', str(package_path / 'runtime/assemble_returns.py'),
                '--host-package', str(package_path), '--output', str(target)], cwd=ROOT,
                capture_output=True, text=True, timeout=240)
            require(completed.returncode == 0, app + ' retained assembly failed: ' + completed.stdout + completed.stderr)
            require(read(target) == read(ROOT / report), app + ' exact assembled report differs')
        receipts.append(dict(application=app, source_package=package, exact_report_equal=True,
                             return_inventory_raw_schedules_decisions_and_barriers_replayed=True,
                             full_calibration_resource_replay_newly_performed=False,
                             package_assembler_sha256=sha(package_path / 'runtime/assemble_returns.py')))
    return receipts


def decisions():
    output = ['# Complete retained decision tables', '',
              'Generated directly from the two saved fresh reports. Same-host descriptive counts;',
              'no pooled primary endpoint. Null means an undefined denominator.', '']
    costs = []
    primary_rows = []
    events = []
    cells_checked = 0
    for app, package, report in STUDIES:
        data = read(ROOT / report)
        require(data['primary_available_windows'] == 18 and not data['independent_hardware_event_observed'],
                app + ' availability or host claim differs')
        output.extend(['## ' + app, '',
            '| Campaign | View | Deadline label | Method | Procedure | Meets | Exceeds | Abstain | Wrong assurance | Unnecessary rejection | Observed compliant | Unobserved / planned | Answer coverage (planned) | Assurance coverage (planned) | Wrong / assurances | Rejection / compliant |',
            '|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'])
        for table in data['tables']:
            c, rates = table['counts'], table['rates']
            require(c['meets'] + c['exceeds'] + c['inconclusive'] + rates['unobserved_planned_windows'] +
                    c['unavailable_deadline'] == 18, 'Decision table denominator differs')
            def value(v):
                return 'null' if v is None else f'{v:.6f}'
            row = [table['campaign_id'], table['view'], table['label'], table['method'], table['procedure'],
                   *[str(c[k]) for k in ['meets', 'exceeds', 'inconclusive', 'false_assurance',
                                         'unnecessary_rejection', 'observed_compliant']],
                   str(rates['unobserved_planned_windows']),
                   *[value(rates[k]) for k in ['answer_coverage_all_planned', 'assurance_coverage_all_planned',
                                              'false_assurance_per_meets', 'unnecessary_rejection_per_observed_compliant']]]
            output.append('| ' + ' | '.join(row) + ' |')
            if table['label'] == PRIMARY and table['view'] == 'primary_domain' and c['observed_compliant'] > 0:
                if table['procedure'] == 'point':
                    names = {'reference': 'reference', 'recent25': 'recent 25', 'weighted_update': 'weighted update'}
                    primary_rows.append(f"| {app} / {names[table['method']]} | {c['meets']} | {c['false_assurance']} | {c['unnecessary_rejection']} | {c['observed_compliant']} |")
                else:
                    require(c['meets'] == 0 and rates['false_assurance_per_meets'] is None,
                            'Zero-coverage uncertainty interpretation differs')
        for window in data['windows']:
            if window['status'] == 'unavailable':
                continue
            require(window['status'] == 'primary_domain', 'Unexpected adverse window requires explicit review')
            for cell in window['cells']:
                if cell['deadline_ns'] is None:
                    continue
                cells_checked += 1
                for method, values in cell['methods'].items():
                    forecast, score = values['forecast'], values['score']
                    predicted = probability(forecast['probability'])
                    observed = Fraction(score['target_misses'], score['target_offers'])
                    error = abs(predicted-observed)
                    wrong = predicted <= Fraction(1,20) < observed
                    event = predicted < Fraction(1,20) < observed and error <= Fraction(1,20)
                    require(probability(score['absolute_error']) == error and score['false_assurance'] == wrong and
                            score['positive_slack_small_error_false_assurance'] == event,
                            'Independent rational decision arithmetic differs')
                    if cell['label'] == PRIMARY and method == 'reference' and event:
                        events.append(dict(application=app, window_id=window['window_id'], deadline_ns=cell['deadline_ns'],
                            reference_misses=forecast['misses'], reference_offers=forecast['offers'],
                            target_misses=score['target_misses'], target_offers=score['target_offers'],
                            error_pp=100*float(error)))
        costs.append(dict(application=app, observed_campaign_elapsed_sec=data['observed_campaign_elapsed_sec'],
                          allocated_cap_sec=data['allocated_cap_sec'], acquisition=data['acquisition_cost'],
                          preserved_original_attempt_ledger=data['preserved_original_attempt_ledger']))
    require(len(events) == 1 and events[0]['application'] == 'Go' and events[0]['window_id'] == 'v31_b3_A',
            'Narrow primary-event result differs')
    ledger = costs[1]['preserved_original_attempt_ledger']
    require(ledger['combined_attempt_ledger_slots'] == 126 and not ledger['replaces_prior_slots'] and
            not ledger['primary_results_pooled'], 'Attempt lineage differs')
    return '\n'.join(output) + '\n', costs, primary_rows, events, cells_checked


def audit(allow_pending_report=False):
    text = (ROOT / 'paper/unified_manuscript.md').read_text()
    require((ROOT / 'paper/unified_manuscript.tex').read_text() == renderer.render(text), 'Markdown/LaTeX mismatch')
    report = read(ROOT / 'analysis/runtime_io_v28_result_review/20261008/report.json')
    names = [('whole', 'Whole-run CPU/job'), ('idle_corrected', 'Idle-corrected CPU/job'),
             ('busy', 'Busy throughput'), ('regression', 'Linear CPU fit'), ('quadratic', 'Quadratic CPU fit')]
    for key, label in names:
        m = report['methods'][key]
        row = f"| {label} | {m['capacity_rps']:.3f} | {m['deadline_mae_pp']:.3f} | {m['deadline_pass_count']} | {m['capacity_pass_count']} |"
        require(row in text, 'Capacity table differs: ' + key)
    require(not report['advantages']['quadratic']['frozen_advantage_pass'], 'Capacity minimum-effect verdict differs')
    figures = read(ROOT / 'analysis/runtime_io_deadline_extension_finalization/20261010/figure_data.json')
    require(f"Periodic + delay: {figures['v30']['periodic_delay_mae_pp']:.3f}" in text and
            f"Queue-adjusted CDF: {figures['v31']['paired_cdf_mae_pp']:.3f}" in text and
            f"| Original response-CDF transfer | {figures['nginx']['mean_block_mae_pp']:.3f}" in text,
            'Deadline campaign table differs')
    power = read(ROOT / 'analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.json')
    require(f"| Assigned-policy matching | {power['methods']['matched']['mean']:.3f} | Pooled policies: {power['methods']['pooled']['mean']:.3f}" in text,
            'Policy control table differs')
    require(power['gain_criterion_met'] and not power['accuracy_criterion_met'], 'Policy verdict differs')
    rate = read(ROOT / 'analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.json')
    methods = rate['primary']['methods']
    require(f"| Fixed-policy rate matching | {methods['matched']['mean']:.3f} | Shared 5/s reference: {methods['baseline']['mean']:.3f}" in text,
            'Rate control table differs')
    require(rate['accuracy_criterion_met'] and not rate['advantage_criterion_met'], 'Rate verdict differs')
    panel = read(ROOT / 'analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01/review.json')
    for policy in ['P0', 'P1']:
        m = panel['policies'][policy]['methods']
        require(f"| Fresh panel, policy {policy} | {m['matched']['worst_cutoff_block_score']['mean']:.3f} | Pooled panel: {m['pooled']['worst_cutoff_block_score']['mean']:.3f}" in text,
                'Panel table differs: ' + policy)
        require(m['matched']['worst_cutoff_block_score']['conditional_interval'][1] > 5, 'Panel upper-bound verdict differs')
    tables, costs, primary_rows, events, count = decisions()
    require(all(row in text for row in primary_rows), 'Main primary-deadline decision table differs')
    for phrase in ['one physical host', 'zero assurance', 'not_reproduced_in_available_windows',
                   'No independent-host result has been received', '126-slot', '54 closed unavailable',
                   '36\npending independent Intel slots', 'not population rates', 'inconclusive',
                   'not externally supplied production SLOs', 'No first-result claim']:
        require(phrase.lower() in text.lower(), 'Missing central claim limit: ' + phrase)
    links = 0
    for name in DOCUMENTS:
        if name.endswith('.tex'):
            continue
        path = ROOT / name
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' in link or link.startswith('#'):
                continue
            target = (path.parent / link.split('#')[0]).resolve()
            require(target.exists() or allow_pending_report and target == OUT / 'report.json',
                    'Broken local link: ' + name + ': ' + link)
            links += 1
    compiler = read(OUT / 'compiler_status.json')
    require(compiler['kind'] == 'success' and compiler['source_sha256'] == sha(ROOT / 'paper/unified_manuscript.tex'),
            'Current standalone compilation unverified')
    return dict(status='unified_manuscript_verified', evidence_cutoff='2026-10-11',
                capacity_primary_rows_checked=5, decision_primary_rows_checked=len(primary_rows),
                decision_labelled_cells_checked=count, primary_events=events,
                local_links_checked=links, standalone_compilation='success',
                independent_host_result_received=False, scientific_novelty_established=False,
                full_pdf_layout_inspected=False, new_performance_collection=False,
                local_research_closed=True, independent_confirmation='outstanding'), tables, costs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--history', action='store_true')
    args = parser.parse_args()
    if not args.build:
        seal = read(OUT / 'seal.json')
        for name, expected in seal['files_sha256'].items():
            require(sha(ROOT / name) == expected, 'Unified package changed: ' + name)
        for name, expected in read(OUT / 'preserved_current_inputs_sha256.json').items():
            require(sha(ROOT / name) == expected, 'Retained input changed: ' + name)
    history_receipt = history() if args.history else None
    receipts = replay_studies()
    tables, costs, _, _, _ = decisions()
    if args.build:
        require(not (OUT / 'seal.json').exists(), 'Preserve completed closeout')
        if (OUT / 'decision_tables.md').exists():
            require((OUT / 'decision_tables.md').read_text() == tables, 'Preserve differing unsealed table preparation')
        else:
            (OUT / 'decision_tables.md').write_text(tables)
        if (OUT / 'decision_costs.json').exists():
            require(read(OUT / 'decision_costs.json') == costs, 'Preserve differing unsealed cost preparation')
        else:
            save(OUT / 'decision_costs.json', costs)
    result, regenerated_tables, regenerated_costs = audit(allow_pending_report=args.build)
    require((OUT / 'decision_tables.md').read_text() == regenerated_tables and
            read(OUT / 'decision_costs.json') == regenerated_costs, 'Complete tables or acquisition ledger differ')
    if args.build:
        # Preserve current live identity alongside the older version-sensitive
        # snapshots. Never update or relax an earlier seal.
        inventory = read(ROOT / 'analysis/runtime_io_empirical_consolidation/20261011/protected_inputs_sha256.json')
        paths = set(inventory) | set(DOCUMENTS[:-1])
        paths -= set(DOCUMENTS)
        paths.update(['README.md', 'docs/current_research_plan.md', 'paper/README.md',
                      'paper/capacity_calibration_empirical.md', 'paper/capacity_calibration_empirical.tex',
                      'paper/paper_draft.md', 'analysis/runtime_io_empirical_consolidation/20261011/evidence-seal.json',
                      'analysis/runtime_io_slo_independent/20261011-local-supplement01-raw-replay.json',
                      'analysis/runtime_io_slo_independent/20261011-nginx-completion01-raw-replay.json',
                      'analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.json',
                      'analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.json',
                      'analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01/review.json'])
        for _, package, report in STUDIES:
            paths.update([report, package + '/runtime_seal.json'])
        save(OUT / 'preserved_current_inputs_sha256.json', {name: sha(ROOT / name) for name in sorted(paths)})
        result['current_retained_inputs_preserved'] = len(paths)
        save(OUT / 'decision_replay_receipts.json', receipts)
        if history_receipt is not None:
            save(OUT / 'historical_replay_receipt.json', history_receipt)
        save(OUT / 'report.json', result)
        closure = [ROOT / name for name in DOCUMENTS] + [Path(__file__), ROOT / 'analysis/render_unified_manuscript.py'] + list(OUT.iterdir())
        save(OUT / 'seal.json', dict(role='local closeout identity record; not independent attestation',
            files_sha256={str(path.relative_to(ROOT)): sha(path) for path in closure if path.is_file()}))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
