"""Offline table/link and retained-evidence audit for the V4 working draft.

Reads saved results only; never collects data or fits a new scientific model.
The initial hash snapshot must have been captured before consolidation edits.
"""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import v28_common as c
import v28_verify as verifier


def main():
    out = ROOT / 'analysis/runtime_io_paper_consolidation_review/20261008'
    before = Path('/tmp/runtime_io_consolidation_before_20261008.json')
    if not before.exists():
        before = out / 'protected_evidence_sha256.json'
    protected = json.loads(before.read_text())
    for name, expected in protected.items():
        if c.digest(ROOT / name) != expected:
            raise ValueError('protected evidence changed: ' + name)
    reviews = {
        'v22': 'runtime_io_v22_result_review/20261007',
        'v23': 'runtime_io_v23_result_review/20261007',
        'v25': 'runtime_io_v25_result_review/20261007',
        'v26': 'runtime_io_v26_result_review/20261007',
        'v27': 'runtime_io_v27r3_result_review/20261008',
        'v28': 'runtime_io_v28_result_review/20261008',
    }
    data = {}; evidence = {}; sealed = []
    for key, relative in reviews.items():
        directory = ROOT / 'analysis' / relative
        c.verify_seal(directory)
        data[key] = c.read(directory / 'report.json')
        evidence[str((directory / 'report.json').relative_to(ROOT))] = c.digest(directory / 'report.json')
        sealed.append(str(directory.relative_to(ROOT)))
    generations = [('v22', 'runtime_io_v22/generation-02'),
                   ('v23', 'runtime_io_v23/generation-01'),
                   ('v25', 'runtime_io_v25/generation-01'),
                   ('v26', 'runtime_io_v26/generation-01'),
                   ('v27', 'runtime_io_v27/generation-03'),
                   ('v28', 'runtime_io_v28/generation-01')]
    for key, relative in generations:
        session = ROOT / 'analysis' / relative
        latest = c.read(session / 'latest_analysis.json')
        original = c.resolve(session, latest['path'])
        c.verify_seal(original)
        if c.digest(original / 'seal.json') != latest['seal']:
            raise ValueError('original result seal differs: ' + key)
        expected = next((data[key][field] for field in
                        ('analysis_seal', 'analysis_seal_sha256', 'original_analysis_seal')
                        if field in data[key]), None)
        if expected is not None and expected != latest['seal']:
            raise ValueError('result review references different analysis: ' + key)
        evidence[str((original / 'report.json').relative_to(ROOT))] = c.digest(original / 'report.json')
        sealed.append(str(original.relative_to(ROOT)))
    verifier.verify_bundle(ROOT / 'analysis/runtime_io_v28/generation-01')

    draft_path = ROOT / 'docs/runtime_io_short_working_draft_v4.md'
    draft = draft_path.read_text()
    rows = []
    for size, label in [('small', 'Small'), ('large', 'Large')]:
        for arm, period in [('A', 3), ('B', 12)]:
            v = data['v23']['metrics'][size][arm]
            rows.append(f"| {label} | {period} s | {v['observed_mean_miss_pct']:.2f}% | "
                        f"{v['busy_predicted_miss_pct']:.2f}% | {v['cpu_predicted_miss_pct']:.2f}% |")
    for size, label in [('small', 'Small'), ('large', 'Large')]:
        v = data['v25']['by_size'][size]
        rows.append(f"| {label} | {v['whole_cost_nominal_cpu_capacity_rps']:.2f} jobs/s | "
                    f"{v['measured_busy_capacity_on_mean_rps']:.2f} jobs/s | {v['capacity_underprediction_pct']:.2f}% |")
    for arm, label in [('off', 'Off'), ('on', 'On')]:
        v = data['v27']['contrasts'][arm]['whole_cpu_usec_per_job']
        lo, hi = v['model_based_95_interval']
        rows.append(f"| {label} | {v['mean']:.3f}% | [{lo:.3f}%, {hi:.3f}%] |")
    labels = [('whole', 'Whole-run CPU/job'), ('idle_corrected', 'Idle-corrected CPU/job'),
              ('busy', 'Busy capacity'), ('regression', 'Linear utilization–throughput regression'),
              ('quadratic', 'Quadratic utilization–throughput benchmark')]
    for key, label in labels:
        v = data['v28']['methods'][key]
        rows.append(f"| {label} | {v['capacity_rps']:.3f} | {v['deadline_mae_pp']:.3f} | "
                    f"{v['maximum_deadline_error_pp']:.3f} | {v['maximum_capacity_error_pct']:.3f} | "
                    f"{v['deadline_pass_count']} | {v['capacity_pass_count']} |")
    for row in rows:
        if row not in draft:
            raise ValueError('table differs from verified evidence: ' + row)
    advantage = data['v28']['advantages']['quadratic']
    lo, hi = advantage['model_based_95_interval']
    phrases = [f"{data['v22']['calibration']['mu_busy']:.2f} jobs/s",
               f"{data['v22']['metrics']['max_primary_abs_error_pp']:.2f} percentage points",
               f"{data['v23']['max_primary_abs_error_pp']:.2f} percentage points",
               f"{data['v23']['validation_offers']:,} validation offers",
               f"{data['v25']['native_capture']['total_samples']:,} readings",
               f"{data['v26']['total_measurement_offers']:,} measurement offers",
               f"{data['v26']['native_capture']['total_samples']:,} native readings",
               f"{data['v27']['measurement_offers']:,}",
               f"{data['v28']['measurement_offers']:,} measurement offers",
               f"{data['v28']['warmup_offers']:,} warmup offers",
               f"{data['v28']['prediction_seal_precedes_first_validation_sec']:.3f} s",
               f"{advantage['mean_improvement_pp']:.3f} percentage points",
               f"[{lo:.3f}, {hi:.3f}]",
               f"{data['v28']['idle_cpu_rate']:.9f} CPU",
               'composition_inconclusive', 'predictive_advantage_inconclusive']
    for phrase in phrases:
        if phrase not in draft:
            raise ValueError('expected numerical/decision statement absent: ' + phrase)
    if data['v27']['cost_screen_pass'] or advantage['frozen_advantage_pass']:
        raise ValueError('inconclusive outcomes changed')

    documents = [draft_path, ROOT / 'docs/runtime_io_load_dependent_baseline_assessment_20261008.md',
                 ROOT / 'docs/current_research_plan.md', ROOT / 'docs/runtime_io_research_status_20261008.md']
    # Create the audit target before checking the new documents' forward links.
    out.mkdir(parents=True, exist_ok=True)
    target = out / 'report.json'
    local_links = 0
    for path in documents:
        for destination in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if destination.startswith(('http://', 'https://', 'app://')):
                continue
            linked = (path.parent / destination.split('#')[0]).resolve()
            if linked != target and not linked.exists():
                raise ValueError(f'broken local link in {path.name}: {destination}')
            local_links += 1

    registry = [
        dict(key='kumar2009', title='Enhanced Inferencing: Estimation of a Workload Dependent Performance Model',
             url='https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799', doi='10.4108/ICST.VALUETOOLS2009.7799',
             reviewed='Primary conference PDF text, sections 2–3, equations 10–20; 2009 conference, publisher posting 2010.',
             limitation='No implementation or equation-image reproduction audit performed.'),
        dict(key='zhang2013', title='Estimate Load-dependent Service Demand for Modern CPU',
             url='https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639', doi='10.3923/itj.2013.632.639',
             reviewed='Primary full HTML, load-dependent estimation section and experimental discussion.',
             limitation='Equation images not fully verified; PDF retrieval failed. Exact constraints not ready for faithful implementation.'),
        dict(key='spinner2015', title='Evaluating Approaches to Resource Demand Estimation',
             url='https://se.informatik.uni-wuerzburg.de/en/tools/librede/', doi='10.1016/j.peva.2015.07.005',
             reviewed='Author-hosted 2015 publication entry and abstract.',
             limitation='Publisher full text unavailable this review; abstract supports overview only.'),
        dict(key='mi2010', title='Sizing multi-tier systems with temporal dependence: benchmarks and analytic models',
             url='https://link.springer.com/article/10.1007/s13174-010-0012-9',
             reviewed='Publisher bibliographic page and abstract; retained version-3 prior-work context.',
             limitation='No implementation comparison.'),
        dict(key='casale2009', title='Automatic Stress Testing of Multi-Tier Systems by Dynamic Bottleneck Switch Generation',
             url='https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf',
             reviewed='Primary PDF available; aggregate-accounting context retained from version 3.',
             limitation='No implementation comparison.'),
        dict(key='cucinotta2023', title='Strong Temporal Isolation Among Containers in OpenStack for NFV Services',
             url='https://retis.santannapisa.it/people/nino/publication/TCC23.pdf',
             reviewed='Author PDF available; reservation-scope context retained from version 3.',
             limitation='Not an executed baseline.'),
        dict(key='sampat2025', title='CPU Autoscaling With a Kernel of Truth',
             url='https://tianyin.github.io/pub/kscaler.pdf',
             reviewed='Author PDF, Linux bandwidth and application-periodicity discussion, sections 2–3.',
             limitation='Not an executed baseline.'),
    ]
    c.save(out / 'sources.json', dict(date='2026-10-08', scope='targeted primary-source assessment, not exhaustive', sources=registry))
    c.save(out / 'protected_evidence_sha256.json', protected)
    c.save(target, dict(
        schema=1, date='2026-10-08', decision='consolidated_scoped_paper_and_targeted_baseline_assessment',
        documents_sha256={str(p.relative_to(ROOT)): c.digest(p) for p in documents},
        review_script_sha256=c.digest(Path(__file__)), evidence_sha256=evidence,
        verified_result_and_review_seals=sealed, v28_current_bundle_verified=True,
        protected_files_unchanged=len(protected), historical_v3_unchanged=True,
        draft_table_rows_checked=len(rows), additional_number_and_decision_phrases_checked=len(phrases),
        local_document_links_checked=local_links,
        v27_decision='composition_inconclusive', v28_decision='predictive_advantage_inconclusive',
        collection_launched=False, new_models_fitted=False, thresholds_changed=False,
        novelty_established=False,
        assessment='Published load-dependent methods are conceptually relevant; V28 is a restricted benchmark, not their reproduction. Full applicability and performance here are unestablished.',
        claim_review='Editorial review retains narrow substitution failure, nonlinear benchmark agreement, sampler limitations and both inconclusive minimum-effect screens; not automated proof of novelty.',
        verification_scope='Saved table arithmetic and seals only; historical full completion replays are referenced, not repeated.',
        next_step='Review scoped empirical draft; collection remains stopped. Stronger comparisons require separately justified implementation and design.'
    ))
    c.seal(out); c.verify_seal(out)
    print(f'Consolidation verified: {len(rows)} table rows, {len(phrases)} statements, '
          f'{local_links} local links, {len(protected)} protected files unchanged; {out}')


if __name__ == '__main__':
    main()
