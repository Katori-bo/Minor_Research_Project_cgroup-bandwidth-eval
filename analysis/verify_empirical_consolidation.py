#!/usr/bin/env python3
"""Verify the 11 October consolidation and replay historical versions offline."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import render_deadline_transfer_integration as renderer
import verify_deadline_transfer_integration as previous

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_empirical_consolidation/20261011'
DOCUMENTS = previous.DOCUMENTS
CHECKS = [
    ('analysis/verify_deadline_transfer_integration.py', []),
    ('analysis/review_nginx_deadline_panel.py', ['--verify']),
    ('analysis/screen_prevalidation_shift.py', ['--verify']),
    ('analysis/screen_prevalidation_cpu.py', ['--verify']),
    ('analysis/screen_continuous_persistence.py', ['--verify']),
    ('analysis/screen_stage_transfer_signal.py', ['--verify']),
    ('analysis/screen_deadline_scope.py', ['--verify']),
    ('analysis/screen_deadline_sensitivity.py', ['--verify']),
    ('diagnostic/nginx_worker_wait_study.py', ['replay']),
    ('analysis/worker_wait_precision_cost.py', ['--verify', 'analysis/runtime_io_worker_wait_precision_cost/20261010/planning.json']),
    ('analysis/warmup_precision_cost.py', ['--verify']),
    ('analysis/audit_execution_rate_capability.py', ['--verify']),
    ('analysis/plan_execution_rate_qualification.py', ['--verify']),
]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')


def preserved_inputs():
    for name, digest in read(OUT / 'before_sha256.json').items():
        require(sha(OUT / ('before_' + name)) == digest, 'Snapshot changed: ' + name)
    inventory = read(OUT / 'protected_inputs_sha256.json')
    for name, digest in inventory.items():
        path = ROOT / name
        if name.startswith('paper/') and Path(name).name in DOCUMENTS:
            path = OUT / ('before_' + Path(name).name)
        require(sha(path) == digest, 'Protected evidence changed: ' + name)
    return len(inventory)


def historical_checks():
    # Copy unchanged top-level Python sources so __file__.resolve() identifies
    # the logical workspace. Link large immutable data; substitute only the
    # four captured manuscript versions. Old checkers and seals stay untouched.
    receipts = []
    with tempfile.TemporaryDirectory(prefix='empirical-history-') as directory:
        shadow = Path(directory)
        for path in ROOT.iterdir():
            if path.name not in ['analysis', 'diagnostic', 'paper']:
                (shadow / path.name).symlink_to(path, target_is_directory=path.is_dir())
        for folder in ['analysis', 'diagnostic', 'paper']:
            target = shadow / folder
            target.mkdir()
            for path in (ROOT / folder).iterdir():
                dest = target / path.name
                if folder == 'paper' and path.name in DOCUMENTS:
                    dest.write_bytes((OUT / ('before_' + path.name)).read_bytes())
                elif path.is_file() and path.suffix == '.py' and path.name != 'leftover_observer_review.py':
                    dest.write_bytes(path.read_bytes())
                else:
                    dest.symlink_to(path, target_is_directory=path.is_dir())
        # The capability checker rejects resolved inputs outside its workspace.
        # Materialize its protected closure (about 23 MB), preserving all bytes
        # and directory membership, instead of relaxing that access check.
        def materialize_directory(path):
            if path == shadow:
                return
            materialize_directory(path.parent)
            if path.is_symlink():
                source = path.resolve()
                path.unlink()
                path.mkdir()
                for child in source.iterdir():
                    (path / child.name).symlink_to(child, target_is_directory=child.is_dir())
        for name in read(OUT / 'protected_inputs_sha256.json'):
            dest = shadow / name
            materialize_directory(dest.parent)
            if dest.is_symlink():
                data = dest.read_bytes()
                dest.unlink()
                dest.write_bytes(data)
        for script, args in CHECKS:
            completed = subprocess.run([sys.executable, '-B', str(shadow / script), *args],
                cwd=shadow, capture_output=True, text=True, timeout=180)
            require(completed.returncode == 0,
                'Historical replay failed: ' + script + '\n' + completed.stdout + completed.stderr)
            receipts.append(dict(command=' '.join([script, *args]), exit_code=0,
                stdout=completed.stdout, stderr=completed.stderr,
                manuscript_version='preserved 10 October integration', performance_collection=False))
            print('Verified ' + script, flush=True)
    return receipts


def panel_table():
    review = read(ROOT / 'analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01/review.json')
    rows = ['| Policy | Matched score (pp) | Conditional 97.5% interval (pp) | Pooled score (pp) | Accuracy supported |',
            '|---|---:|---:|---:|---|']
    for policy in ['P0', 'P1']:
        methods = review['policies'][policy]['methods']
        score = methods['matched']['worst_cutoff_block_score']
        lo, hi = score['conditional_interval']
        rows.append(f"| {policy} | {score['mean']:.3f} | [{lo:.3f}, {hi:.3f}] | {methods['pooled']['worst_cutoff_block_score']['mean']:.3f} | No |")
        require(hi > 5, 'Unexpected panel decision')
    require(review['status'] == 'deadline_panel_accuracy_not_supported', 'Panel status changed')
    return '\n'.join(rows)


def audit():
    text = (ROOT / 'paper/deadline_resolution_extension.md').read_text()
    old = (OUT / 'before_deadline_resolution_extension.md').read_text()
    tables = previous.revision.prior.tables
    require(all(group in tables(text) for group in tables(old)), 'Historical result table changed')
    require(panel_table() in text, 'New primary panel table differs from sealed arithmetic')
    require(re.findall(r'^## (\d+)\.', text, re.M) == [str(i) for i in range(1, 21)], 'Section sequence differs')
    for phrase in ['six separately calibrated prospective', '10,530', '4,703 us', '31.5 pp',
                   '525.452 us', '47.708/43.496 us', '268.804/262.564 us', '32/31 pairs',
                   'observer_overhead_qualification_inconclusive', 'unverified',
                   'Independent-host replication remains\npending', 'No novel estimator']:
        require(phrase in text, 'Missing result or scope: ' + phrase)
    require((ROOT / 'paper/deadline_resolution_extension.tex').read_text() == renderer.render(text),
            'Markdown/LaTeX derivation differs')
    links = 0
    for name in DOCUMENTS:
        if name.endswith('.tex'):
            continue
        path = ROOT / 'paper' / name
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
            if '://' in link or link.startswith('#'):
                continue
            require((path.parent / link.split('#')[0]).exists(), 'Broken local link: ' + link)
            links += 1
    compiler = read(OUT / 'compiler_status.json')
    require(compiler['kind'] == 'success' and compiler['source_sha256'] ==
            sha(ROOT / 'paper/deadline_resolution_extension.tex'), 'Current compilation unverified')
    return dict(status='empirical_consolidation_verified', date='2026-10-11',
        protected_inputs_preserved=preserved_inputs(), historical_table_groups_preserved=len(tables(old)),
        complete_primary_campaigns=6, panel_primary_policy_rows_checked=2, local_links_checked=links,
        manuscript_sha256={name: sha(ROOT / 'paper' / name) for name in DOCUMENTS},
        performance_collection=False, independent_host_result_received=False,
        new_observer_measurement_performed=False, new_method_novelty_established=False,
        full_pdf_layout_inspected=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--history-only', action='store_true')
    args = parser.parse_args()
    count = preserved_inputs()
    if not args.build and not args.history_only:
        for rel, digest in read(OUT / 'evidence-seal.json')['files_sha256'].items():
            require(sha(ROOT / rel) == digest, 'New package changed: ' + rel)
    receipt = historical_checks()
    if args.history_only:
        print(f'Historical replay and {count} protected paths verify.')
        return
    result = audit()
    if args.build:
        require(not (OUT / 'evidence-seal.json').exists(), 'Preserve completed revision')
        save(OUT / 'report.json', result)
        save(OUT / 'verification_receipt.json', receipt)
        for name in DOCUMENTS:
            (OUT / ('consolidated_' + name)).write_bytes((ROOT / 'paper' / name).read_bytes())
        paths = [*OUT.iterdir(), Path(__file__), *(ROOT / 'paper' / name for name in DOCUMENTS),
                 ROOT / 'README.md', ROOT / 'docs/current_research_plan.md',
                 ROOT / 'docs/runtime_io_research_checkpoint_20261010.md',
                 ROOT / 'docs/runtime_io_empirical_consolidation_20261011.md']
        save(OUT / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths}))
    else:
        require(result == read(OUT / 'report.json'), 'Consolidation audit differs')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
