"""Offline audit of review corrections, preserving every historical evidence seal.

Default: verify the sealed revision. --build: record one new revision package
after successful native compilation. No scientific collector is invoked.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics as st
import verify_deadline_extension as prior
import finalize_deadline_extension as historical_renderer
from render_deadline_extension_revision import render

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT/'analysis/runtime_io_deadline_extension_finalization/20261010'
REVIEW = ROOT/'analysis/runtime_io_deadline_extension_reviewer_assessment/20261010'
OUT = ROOT/'analysis/runtime_io_deadline_extension_revision/20261010-review-corrections'
DOCS = ['deadline_resolution_extension.md', 'deadline_resolution_extension.tex',
        'deadline_resolution_supporting_material.md', 'deadline_resolution_reproducibility.md']
SNAPSHOTS = dict(zip(DOCS, ['manuscript_snapshot.md', 'manuscript_snapshot.tex',
                           'supporting_material_snapshot.md', 'reproducibility_snapshot.md']))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected):
    require(math.isclose(actual, expected, abs_tol=1e-10, rel_tol=1e-12),
            f'Arithmetic changed: {actual} != {expected}')


def historical_path(name):
    # The old seals continue to identify the old manuscript, not the live revision.
    if name.startswith('paper/') and Path(name).name in SNAPSHOTS:
        return FINAL/SNAPSHOTS[Path(name).name]
    return ROOT/name


def preserve_history():
    inventory = read(FINAL/'protected_evidence_sha256.json')
    for directory in [FINAL, REVIEW]:
        for name, digest in read(directory/'evidence-seal.json')['files_sha256'].items():
            require(sha(historical_path(name)) == digest, 'Historical seal changed: '+name)
        # Protect every original package file, including the seals themselves.
        for path in directory.rglob('*'):
            if path.is_file():
                inventory[str(path.relative_to(ROOT))] = sha(path)
    for name, digest in read(REVIEW/'inputs_sha256.json').items():
        require(sha(historical_path(name)) == digest, 'Historical review input changed: '+name)
    for name, digest in inventory.items():
        require(sha(ROOT/name) == digest, 'Protected scientific/historical evidence changed: '+name)
    return inventory


def response_control():
    base = ROOT/'analysis/runtime_io_v31/generation-01'
    saved = read(base/'analysis/1791544686930410674/report.json')
    fit = read(base/'predictions/calibration.json')
    result_review = read(ROOT/'analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
    fitted = {(r['trial'], r['id']): r for r in fit['paired_samples']}
    full, queues = [], []
    for name in fit['timing_cohorts']:
        directory = base/saved['trial_refs'][name]['path']
        jobs = {r['id']: r for r in read(directory/'server_metrics.json')['events']}
        clients = read(directory/'loadgen.json')['requests']
        for row in clients:
            require(not row['Error'] and row['StatusCode'] == 200, 'Failed calibration offer')
            queue = jobs[row['ID']]['queue_wait_ns']
            sample = fitted[(name, row['ID'])]
            require(queue <= 100000, 'Calibration pool membership differs')
            require(row['EndToEndLatencyNs']-queue == sample['total_ns'] ==
                    sample['worker_ns']+sample['residual_ns'], 'Pairing/sum identity changed')
            full.append(row['EndToEndLatencyNs']); queues.append(queue)
    require(len(full) == len(fitted) == 676, 'Expected original 676-offer pool')
    forecast = 100*sum(v > 10000000 for v in full)/len(full)
    errors = []
    for trial in result_review['validation']:
        directory = base/saved['trial_refs'][trial['trial']]['path']
        clients = read(directory/'loadgen.json')['requests']
        require(len(clients) == {'A':300, 'B':660, 'C':1140}[trial['profile']],
                'Validation offer count changed')
        observed = 100*sum(bool(r['Error']) or r['StatusCode'] != 200 or
                           r['EndToEndLatencyNs'] > 10000000 for r in clients)/len(clients)
        close(observed, trial['observed_miss_pct']['10'])
        errors.append(dict(trial=trial['trial'], block=trial['block'],
                           observed_miss_pct=observed, forecast_miss_pct=forecast,
                           absolute_error_pp=abs(forecast-observed)))
    require(len(errors) == 18, 'Expected all original validation trials')
    blocks = [st.mean(r['absolute_error_pp'] for r in errors if r['block'] == b)
              for b in range(1,7)]
    control = dict(forecast_miss_pct=forecast, mae_pp=st.mean(blocks),
                   maximum_trial_error_pp=max(r['absolute_error_pp'] for r in errors),
                   queue_wait_mean_ns=st.mean(queues), queue_wait_maximum_ns=max(queues),
                   samples=676, validation_offers=12600, trial_errors=errors, block_mae_pp=blocks,
                   role='retrospective_method_selection_calibration_values_only',
                   superiority_or_equivalence_established=False,
                   observer_removal_qualified=False)
    reviewed = read(REVIEW/'report.json')
    for key in ['forecast_miss_pct', 'mae_pp', 'maximum_trial_error_pp']:
        close(control[key], reviewed['whole_response_cdf_primary'][key])
    close(control['queue_wait_mean_ns'], reviewed['queue_wait_mean_ns'])
    close(control['queue_wait_maximum_ns'], reviewed['queue_wait_maximum_ns'])
    return control


def methods_provenance():
    hashes = {}
    def consume(path):
        hashes[str(path.relative_to(ROOT))] = sha(path)
        return read(path)
    for label in ['v30', 'v31']:
        base = ROOT/f'analysis/runtime_io_{label}/generation-01'
        require(consume(base/'observer_review/audit.json')['kernel'] == '7.2.8-arch1-2',
                'Kernel identity differs')
        design = consume(base/'bundle/scientific_design/design.json')
        configs = design['calibration_configs']
        require(len(configs) == 16, 'Calibration count differs')
        require(all(c['warmup_sec'] == 20 and c['quota_us'] == 25000 and
                    c['period_us'] == 100000 and c['iterations'] == 88000 for c in configs),
                'Calibration resource/work contract differs')
        steady = sorted(c['rate'] for c in configs if c['role'] == 'steady')
        require(steady == sorted([3.75,7.5,15,22.5,30]*2), 'Steady schedule differs')
        mixed = [c for c in configs if c['role'] == 'mixed']
        require(len(mixed) == 4 and sorted(c['burst_low'] for c in mixed) == [3.75,3.75,7.5,7.5]
                and all(c['burst_high'] == 42.45 and c['burst_period_sec'] == 15 and
                        c['burst_low_duration_sec'] == 10 and c['duration_sec'] == 60 for c in mixed),
                'Mixed calibration schedules differ')
        require(sum(c['role'] == 'idle' and c['duration_sec'] == 30 for c in configs) == 2
                and all(c['duration_sec'] == 30 for c in configs if c['role'] == 'steady'),
                'Idle/steady duration differs')
        require(consume(base/'bundle/client_build/manifest.json')['compiler_version'] ==
                'go version go1.26.1 linux/amd64', 'Client compiler differs')
        runtime = consume(sorted(base.glob('slots/*/*/server_metrics.json'))[0])
        require(runtime['go_version'] == 'go1.26.1' and runtime['runtime_variant'] == 'stock'
                and runtime['instrument'] and not runtime['runtime_capture'], 'Runtime contract differs')
        environment = consume(base/'environment.json')
        for policy in environment['power_settings']['policies'].values():
            require(policy['scaling_driver'] == 'amd-pstate-epp' and policy['scaling_governor'] ==
                    'powersave' and policy['energy_performance_preference'] == 'balance_performance',
                    'Power policy differs')
    inherited = consume(ROOT/'analysis/runtime_io_v29_design/20261009/q025_large/design.json')
    require(inherited['busy_windows_sec']['calibration'] == [[11.5,14.5],[26.5,29.5],[41.5,44.5],[56.5,59.5]]
            and inherited['steady_windows_sec'] == [[3,10],[10,17],[17,24]]
            and inherited['rules']['calibration_capacity_range_pct'] == 5, 'Fixed windows/rules differ')
    for name in ['paper/paper_draft.md','diagnostic/service/main.go','diagnostic/build_completion.py',
                 'diagnostic/v29_model.py','diagnostic/v30_common.py','diagnostic/v31_common.py',
                 'tools/loadgen/main.go','diagnostic/nginx_client/main.go']:
        hashes[name] = sha(ROOT/name)
    require('AMD Ryzen 5 5600H' in (ROOT/'paper/paper_draft.md').read_text(), 'Earlier host record differs')
    return hashes


def audit():
    inventory = preserve_history()
    control = response_control()
    methods = methods_provenance()
    manuscript = (ROOT/'paper/deadline_resolution_extension.md').read_text()
    groups = prior.tables(manuscript)
    new_tables = [g for g in groups if g[0][0] == 'Calibration reference at 10 ms']
    require(len(new_tables) == 1, 'Missing retrospective control table')
    require(new_tables[0][1:] == [
        ['Frozen queue-adjusted CDF, prospective','67.160','1.844','5.055'],
        ['Complete-response CDF, retrospective',f"{control['forecast_miss_pct']:.3f}",
         f"{control['mae_pp']:.3f}",f"{control['maximum_trial_error_pp']:.3f}"]], 'Control table differs')
    # Reuse the existing numerical audit against the live revised document.
    # Only filter the separately checked new table and use the revised renderer.
    old_tables, old_latex = prior.tables, historical_renderer.latex
    try:
        prior.tables = lambda text: [g for g in old_tables(text) if g[0][0] != 'Calibration reference at 10 ms']
        historical_renderer.latex = render
        result = prior.audit()
    finally:
        prior.tables, historical_renderer.latex = old_tables, old_latex
    source = (ROOT/'paper/deadline_resolution_extension.tex').read_text()
    require('**' not in source and 'p\\_hat' not in source and 'sqrt(6)' not in source,
            'Literal Markdown or plain mathematics remains')
    for phrase in [r'\hat p_{b,k}(D)', r'\sqrt{6}', 'Retrospective complete-response CDF control',
                   'including waiting', 'Client-only deployment', r'\cite{capacityprecursor}']:
        require(phrase in source, 'Missing corrected statement/math: '+phrase)
    require('internal-queue estimand' not in source, 'Old endpoint misdescription remains')
    return dict(result, status='review_corrections_verified', date='2026-10-10',
                original_scientific_table_rows=31, retrospective_table_rows=2,
                protected_evidence_files=len(inventory), retrospective_control=control,
                methods_sources_sha256=methods, historical_inventory_sha256=inventory,
                compiler_success_verified_separately=True, full_pdf_layout_inspected=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    if not args.build:
        require((OUT/'evidence-seal.json').exists(), 'Revision has not been sealed')
        for name, digest in read(OUT/'evidence-seal.json')['files_sha256'].items():
            require(sha(ROOT/name) == digest, 'Revised document/package changed: '+name)
        recorded = read(OUT/'report.json')
        for name, digest in recorded['historical_inventory_sha256'].items():
            require(sha(ROOT/name) == digest, 'Preserved history changed: '+name)
        for name, digest in recorded['methods_sources_sha256'].items():
            require(sha(ROOT/name) == digest, 'Methods source changed: '+name)
    else:
        require(not (OUT/'evidence-seal.json').exists(), 'Preserve existing revision; run without --build')
        # Resolve new manuscript links during the audit; replace only after it passes.
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT/'report.json').write_text('{"status":"revision_audit_pending"}\n')
    result = audit()
    compiler = read(OUT/'compiler_status.json')
    require(compiler['kind'] == 'success' and compiler['source_sha256'] ==
            sha(ROOT/'paper/deadline_resolution_extension.tex'), 'Current source compilation unverified')
    if args.build:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        for name in DOCS:
            (OUT/SNAPSHOTS[name]).write_bytes((ROOT/'paper'/name).read_bytes())
        for name in ['verify_deadline_extension_revision.py','render_deadline_extension_revision.py']:
            (OUT/name).write_bytes((ROOT/'analysis'/name).read_bytes())
        outputs = {str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file()}
        for name in DOCS:
            outputs['paper/'+name] = sha(ROOT/'paper'/name)
        for name in ['verify_deadline_extension_revision.py','render_deadline_extension_revision.py']:
            outputs['analysis/'+name] = sha(ROOT/'analysis'/name)
        (OUT/'evidence-seal.json').write_text(json.dumps(dict(files_sha256=outputs), indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','original_scientific_table_rows',
                     'retrospective_table_rows','protected_evidence_files','primary_intervals_recomputed']}, indent=2))
    print('Response-CDF control: forecast %.6f%%, MAE %.6f pp, maximum %.6f pp.' %
          tuple(result['retrospective_control'][k] for k in ['forecast_miss_pct','mae_pp','maximum_trial_error_pp']))


if __name__ == '__main__':
    main()
