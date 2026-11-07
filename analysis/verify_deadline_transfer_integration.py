#!/usr/bin/env python3
"""Verify integrated documents and historical snapshots without new traffic."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import consolidate_transfer_evidence as consolidation
import verify_deadline_extension_revision as revision
import render_deadline_extension_revision as old_renderer
from render_deadline_transfer_integration import render

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_deadline_transfer_integration/20261010'
OLD = ROOT / 'analysis/runtime_io_deadline_extension_revision/20261010-review-corrections'
DOCUMENTS = revision.DOCS


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok: raise ValueError(message)


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2); f.write('\n')


def historical_revision():
    # The prior checker intentionally refers to its then-live manuscript. Supply
    # its sealed snapshots through a temporary read-only logical workspace.
    # Scientific sources/data are symlinked read-only by use, never rewritten.
    with tempfile.TemporaryDirectory(prefix='deadline-history-') as directory:
        shadow = Path(directory)
        for path in ROOT.iterdir():
            if path.name != 'paper': (shadow / path.name).symlink_to(path, target_is_directory=path.is_dir())
        (shadow / 'paper').mkdir()
        for path in (ROOT / 'paper').iterdir():
            if path.name in DOCUMENTS:
                (shadow / 'paper' / path.name).write_bytes((OLD / revision.SNAPSHOTS[path.name]).read_bytes())
            else:
                (shadow / 'paper' / path.name).symlink_to(path, target_is_directory=path.is_dir())
        modules = [revision, revision.prior, revision.historical_renderer, old_renderer]
        saved_paths = [(module, key, value) for module in modules
            for key, value in vars(module).items()
            if isinstance(value, Path) and value.is_relative_to(ROOT)]
        old_argv = sys.argv
        try:
            for module, key, value in saved_paths:
                setattr(module, key, shadow / value.relative_to(ROOT))
            sys.argv = ['analysis/verify_deadline_extension_revision.py']
            output = io.StringIO()
            with contextlib.redirect_stdout(output): revision.main()
        finally:
            for module, key, value in saved_paths: setattr(module, key, value)
            sys.argv = old_argv
    return dict(command='Prior revision checker against its sealed manuscript snapshots', exit_code=0,
        stdout=output.getvalue(), performance_collection=False)


def historical_inventory():
    inventory = dict(read(OLD / 'report.json')['historical_inventory_sha256'])
    inventory.update(read(OLD / 'evidence-seal.json')['files_sha256'])
    for name, digest in inventory.items():
        path = ROOT / name
        if name.startswith('paper/') and Path(name).name in DOCUMENTS:
            path = OLD / revision.SNAPSHOTS[Path(name).name]
        require(sha(path) == digest, 'Historical evidence/snapshot changed: ' + name)
    return inventory


def source_checks():
    receipt = [historical_revision()]
    # Keep the consolidation's sources and snapshot sealed. Its numeric
    # calculation remains valid; only the old live-document invocation needs
    # the historical workspace above after an authorized manuscript revision.
    for rel, digest in read(consolidation.OUT / 'seal.json')['files_sha256'].items():
        require(sha(ROOT / rel) == digest, 'Consolidation input changed: ' + rel)
    require(consolidation.calculate() == read(consolidation.OUT / 'report.json'), 'Consolidation arithmetic changed')
    for script in consolidation.CHECKS[1:]:
        completed = subprocess.run([sys.executable, '-B', script, '--verify'], cwd=ROOT,
            capture_output=True, text=True, timeout=120)
        require(completed.returncode == 0, 'Saved-evidence check failed: ' + script + '\n' + completed.stdout + completed.stderr)
        receipt.append(dict(command=script + ' --verify', exit_code=completed.returncode,
            stdout=completed.stdout, stderr=completed.stderr, performance_collection=False))
    return receipt


def method_table(report, names, limit):
    rows = [['Forecast', 'MAE pp', 'Conditional 95% interval pp', 'Maximum error pp', 'Cohorts >5 pp']]
    for key, label in names:
        value = report[key]; lo, hi = value['conditional_95_interval']
        rows.append([label, f"{value['mean']:.3f}", f'[{lo:.3f}, {hi:.3f}]',
            f"{value['maximum_error_pp']:.3f}", f"{value['errors_above_5pp']}/{limit}"])
    return rows


def audit():
    inventory = historical_inventory()
    text = (ROOT / 'paper/deadline_resolution_extension.md').read_text()
    groups = revision.prior.tables(text)
    original = revision.prior.tables((OLD / 'manuscript_snapshot.md').read_text())
    require(all(group in groups for group in original), 'Original table values changed or disappeared')
    power = read(ROOT / 'analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.json')
    rate = read(ROOT / 'analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.json')
    power_names = [('pooled','Pooled policies'), ('matched','Policy-matched'), ('baseline','P0-only'),
        ('warmup','25-offer warmup'), ('matched_update','Matched + warmup'), ('pooled_update','Pooled + warmup')]
    rate_names = [('matched','Rate-matched'), ('baseline','Fixed 5/s'), ('pooled','Pooled rates'),
        ('warmup','25-offer warmup'), ('matched_update','Matched + warmup'),
        ('baseline_update','5/s + warmup'), ('pooled_update','Pooled + warmup')]
    require(method_table(power['methods'], power_names, 24) in groups, 'Power result table differs')
    require(method_table(rate['primary']['methods'], rate_names, 12) in groups, 'Rate result table differs')
    require(consolidation.calculate()['table_markdown'] in text, 'Five-study ledger differs')
    for phrase in ['matching offered rate repaired', 'Neither superiority nor equivalence',
        '6,600 us', '9,133 us', '0.778 pp', '[-0.375, 1.931]', '9.021 pp', '[1.746, 16.296]',
        '800 calibration offers', '1,600', '2,400', 'pending', 'No novel estimator']:
        require(phrase in text, 'Missing result/claim limit: ' + phrase)
    headings = re.findall(r'^## (\d+)\.', text, re.M)
    require(headings == [str(i) for i in range(1,19)], 'Manuscript section sequence differs')
    latex = (ROOT / 'paper/deadline_resolution_extension.tex').read_text()
    require(latex == render(text), 'Integrated Markdown/LaTeX derivation differs')
    for key in ['tales','retail','mpora','amdpstate']:
        require(r'\bibitem{' + key + '}' in latex and r'\cite{' + key + '}' in latex, 'Missing integrated citation: ' + key)
    links = 0
    for name in DOCUMENTS:
        if name.endswith('.tex'): continue
        path = ROOT / 'paper' / name
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' in link or link.startswith('#'): continue
            require((path.parent / link.split('#')[0]).exists(), f'Broken link in {name}: {link}')
            links += 1
    return dict(status='transfer_integration_verified', date='2026-10-10',
        historical_table_groups_preserved=len(original), new_method_rows_checked=13,
        complete_primary_campaigns=5, summary_rows_checked=5, local_links_checked=links,
        historical_evidence_files_preserved=len(inventory), historical_inventory_sha256=inventory,
        manuscript_sha256={name: sha(ROOT / 'paper' / name) for name in DOCUMENTS},
        independent_host_result_received=False, new_method_novelty_established=False,
        performance_collection=False, full_pdf_layout_inspected=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', action='store_true')
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    require(not (args.stage and args.build), 'Choose one mutation phase')
    if args.stage:
        require(not OUT.exists(), 'Preserve existing integration package')
        for name in DOCUMENTS:
            require(sha(ROOT / 'paper' / name) == sha(OLD / revision.SNAPSHOTS[name]), 'Starting manuscript differs from sealed revision')
        OUT.mkdir(parents=True)
        save(OUT / 'before_sha256.json', {name: sha(ROOT / 'paper' / name) for name in DOCUMENTS})
        for name in DOCUMENTS:
            (OUT / ('before_' + name)).write_bytes((ROOT / 'paper' / name).read_bytes())
        print('Pre-integration manuscript preserved separately.')
        return
    require(OUT.exists(), 'Stage historical documents before editing')
    for name, digest in read(OUT / 'before_sha256.json').items():
        require(sha(OUT / ('before_' + name)) == digest, 'Pre-integration snapshot changed')
    if not args.build:
        for rel, digest in read(OUT / 'evidence-seal.json')['files_sha256'].items():
            require(sha(ROOT / rel) == digest, 'Integrated document/package changed: ' + rel)
    else:
        require(not (OUT / 'evidence-seal.json').exists(), 'Preserve existing integrated revision')
    receipt = source_checks()
    result = audit()
    compiler = read(OUT / 'compiler_status.json')
    require(compiler['kind'] == 'success' and compiler['source_sha256'] ==
        sha(ROOT / 'paper/deadline_resolution_extension.tex'), 'Current native compilation unverified')
    if args.build:
        save(OUT / 'report.json', result)
        save(OUT / 'verification_receipt.json', receipt)
        for name in DOCUMENTS:
            (OUT / ('integrated_' + name)).write_bytes((ROOT / 'paper' / name).read_bytes())
        paths = [*OUT.iterdir(), *(ROOT / 'paper' / name for name in DOCUMENTS),
            Path(__file__), ROOT / 'analysis/render_deadline_transfer_integration.py']
        save(OUT / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths}))
    else:
        require(result == read(OUT / 'report.json'), 'Integrated audit result differs')
    print(json.dumps({key:result[key] for key in ['status','historical_table_groups_preserved',
        'new_method_rows_checked','complete_primary_campaigns','historical_evidence_files_preserved',
        'performance_collection']}, indent=2))


if __name__ == '__main__': main()
