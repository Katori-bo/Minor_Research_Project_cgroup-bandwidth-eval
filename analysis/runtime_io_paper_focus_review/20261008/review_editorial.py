"""Check the focused manuscript against saved results; no collection or fits."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'diagnostic'))
import v28_common as c


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    preserved = json.loads((OUT / 'preserved_documents_sha256.json').read_text())
    protected = json.loads((ROOT / 'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json').read_text())
    for name, expected in {**protected, **preserved}.items():
        if digest(ROOT / name) != expected:
            raise ValueError('Preserved file changed: ' + name)

    documents = [ROOT / name for name in (
        'docs/runtime_io_short_working_draft_v5.md',
        'docs/runtime_io_paper_supporting_material_20261008.md',
        'docs/current_research_plan.md',
        'docs/runtime_io_research_status_20261008.md',
        'README.md')]
    main_text, support = (documents[0].read_text(), documents[1].read_text())
    combined = main_text + '\n' + support
    old = (ROOT / 'docs/runtime_io_short_working_draft_v4.md').read_text()

    data = {}
    sealed = []
    for key, folder in (
        ('v22', 'runtime_io_v22_result_review/20261007'),
        ('v23', 'runtime_io_v23_result_review/20261007'),
        ('v25', 'runtime_io_v25_result_review/20261007'),
        ('v26', 'runtime_io_v26_result_review/20261007'),
        ('v27', 'runtime_io_v27r3_result_review/20261008'),
        ('v28', 'runtime_io_v28_result_review/20261008')):
        directory = ROOT / 'analysis' / folder
        c.verify_seal(directory)
        data[key] = c.read(directory / 'report.json')
        sealed.append(str(directory.relative_to(ROOT)))

    rows = []
    for size, label in [('small', 'Small'), ('large', 'Large')]:
        for arm, period in [('A', 3), ('B', 12)]:
            v = data['v23']['metrics'][size][arm]
            rows.append(f"| {label} | {period} s | {v['observed_mean_miss_pct']:.2f}% | "
                        f"{v['busy_predicted_miss_pct']:.2f}% | {v['cpu_predicted_miss_pct']:.2f}% |")
        v = data['v25']['by_size'][size]
        rows.append(f"| {label} | {v['whole_cost_nominal_cpu_capacity_rps']:.2f} jobs/s | "
                    f"{v['measured_busy_capacity_on_mean_rps']:.2f} jobs/s | {v['capacity_underprediction_pct']:.2f}% |")
    for arm, label in [('off', 'Off'), ('on', 'On')]:
        v = data['v27']['contrasts'][arm]['whole_cpu_usec_per_job']
        lo, hi = v['model_based_95_interval']
        rows.append(f"| {label} | {v['mean']:.3f}% | [{lo:.3f}%, {hi:.3f}%] |")
    for key, label in (
        ('whole', 'Whole-run CPU/job'), ('idle_corrected', 'Idle-corrected CPU/job'),
        ('busy', 'Busy capacity'), ('regression', 'Linear utilization–throughput regression'),
        ('quadratic', 'Quadratic utilization–throughput benchmark')):
        v = data['v28']['methods'][key]
        rows.append(f"| {label} | {v['capacity_rps']:.3f} | {v['deadline_mae_pp']:.3f} | "
                    f"{v['maximum_deadline_error_pp']:.3f} | {v['maximum_capacity_error_pct']:.3f} | "
                    f"{v['deadline_pass_count']} | {v['capacity_pass_count']} |")
    for row in rows:
        if row not in combined:
            raise ValueError('Result row differs from saved evidence: ' + row)
    for row in old.splitlines():
        if row.startswith('| ') and row not in combined:
            raise ValueError('Original table row lost: ' + row)

    retained_sections = [
        ('### 3.2 Accounting evidence and sampler limitations', '### 3.3 Qualified low load and composition sensitivity'),
        ('### 3.3 Qualified low load and composition sensitivity', '### 3.4 Fresh comparison with idle and regression controls'),
        ('The two live-idle captures consume', '## 4. Closest prior methods and contribution boundary'),
        ('Earlier V24 generations stopped', 'Saved artifacts retain')]
    for start, end in retained_sections:
        body = old.split(start, 1)[1].split(end, 1)[0].strip()
        if body not in support:
            raise ValueError('Supporting evidence paragraph changed: ' + start)

    advantage = data['v28']['advantages']['quadratic']
    lo, hi = advantage['model_based_95_interval']
    for phrase in (
        f"{advantage['mean_improvement_pp']:.3f} percentage points",
        f"[{lo:.3f}, {hi:.3f}]",
        f"{data['v28']['prediction_seal_precedes_first_validation_sec']:.3f} s",
        'predictive_advantage_inconclusive', 'composition_inconclusive'):
        if phrase not in main_text:
            raise ValueError('Main paper lost numerical or decision statement: ' + phrase)
    if data['v27']['cost_screen_pass'] or advantage['frozen_advantage_pass']:
        raise ValueError('Frozen inconclusive outcomes changed')

    links = 0
    for path in documents:
        for destination in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if destination.startswith(('http://', 'https://', 'app://')):
                continue
            target = (path.parent / destination.split('#')[0]).resolve()
            if target != OUT / 'report.json' and not target.exists():
                raise ValueError('Broken document link: ' + str(target))
            links += 1

    report = dict(
        date='2026-10-08', decision='editorial_focus_on_prospective_capacity_comparison',
        documents_sha256={str(p.relative_to(ROOT)): digest(p) for p in documents},
        preserved_documents_sha256=preserved,
        protected_files_unchanged=len(protected), result_rows_checked=len(rows),
        result_review_seals_verified=sealed, moved_sections_retained=len(retained_sections),
        local_links_checked=links, collection_launched=False, new_models_fitted=False,
        thresholds_changed=False, novelty_established=False,
        v27_decision='composition_inconclusive', v28_decision='predictive_advantage_inconclusive',
        quota_period_candidate='on_hold',
        verification_scope='Saved result tables, moved paragraphs, document links and retained hashes/seals; no new raw-data replay or scientific experiment.',
        claim_review='Editorial review keeps nonlinear agreement, unequal calibration budgets, sampler limitations and both failed minimum-effect screens central or explicitly linked; no new estimator, mechanism or superiority claim.')
    c.save(OUT / 'report.json', report)
    c.seal(OUT)
    c.verify_seal(OUT)
    print(f'Editorial verification passed: {len(rows)} result rows, {len(retained_sections)} moved sections, {links} links; {len(protected)} protected files unchanged.')


if __name__ == '__main__':
    main()
