#!/usr/bin/env python3
"""Read-only remote source audit; never runs controllers or changes cgroups."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_novelty_discovery_round/20261008'
PINS = {
    'kscaler_latest': ('xlab-uiuc/Kscaler', '1acfe8458c9bcba383975fdb5e3bfeda9d722e35', ['kernel/sched/core.c', 'kernel/sched/fair.c']),
    'kscaler_master': ('xlab-uiuc/Kscaler', '43566d6445c1d1a1d1c22c6e374f808d3582b4c7', ['kernel/sched/core.c', 'kernel/sched/fair.c']),
    'autothrottle': ('microsoft/autothrottle', 'd237d7f3d765ee9ab67bcf4aeb626164a87c6bfa', ['worker-daemon.py']),
    'linux_v6_12': ('torvalds/linux', 'v6.12', ['kernel/sched/core.c', 'kernel/sched/fair.c']),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def prepare():
    if OUT.exists():
        raise RuntimeError('Refusing to overwrite an existing discovery round')
    prior = ROOT / 'analysis/runtime_io_cpu_attribution_novelty_screen/20261008'
    protected = json.loads((ROOT / 'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json').read_text())
    preserved = json.loads((prior / 'design/preserved_sha256.json').read_text())
    for p in prior.rglob('*'):
        if p.is_file():
            preserved[str(p.relative_to(ROOT))] = digest(p)
    for rel in ['docs/runtime_io_cpu_attribution_novelty_screen_20261008.md', 'docs/runtime_io_short_working_draft_v5.md', 'docs/runtime_io_paper_supporting_material_20261008.md']:
        preserved[rel] = digest(ROOT / rel)
    for rel, expected in {**protected, **preserved}.items():
        if digest(ROOT / rel) != expected:
            raise RuntimeError('Prior evidence mismatch: ' + rel)
    save(OUT / 'design/protected_sha256.json', protected)
    save(OUT / 'design/preserved_sha256.json', preserved)
    for rel in ['README.md', 'docs/current_research_plan.md', 'docs/runtime_io_research_status_20261008.md']:
        target = OUT / 'provenance/status_before' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / rel).read_bytes())
    save(OUT / 'design/plan.json', {
        'date': '2026-10-08',
        'question': 'Do dynamic CPU-quota update semantics materially change deadline/cost comparisons under an explicit resource-budget contract?',
        'scope': 'Literature and pinned actuator-source audit only; no controller, kernel, profiler or workload execution.',
        'pins': PINS,
        'ordinary_controls': ['Skip identical limit writes', 'Skip identical period writes', 'Replenishment-boundary application with validated timing', 'Report allocated CPU and consumed CPU separately', 'Known adaptive-reservation consistency rules'],
        'proceed_gate': 'An actual actuator path makes the hypothesis plausible and a resource-matched comparison could establish a nonroutine causal finding or capability.',
        'stop_gate': 'Documented refill alone, a synthetic duplicate-write example alone, or an ordinary control already suffices with no meaningful empirical effect.',
        'collection': 'stopped', 'quota_period_selection': 'on_hold', 'fifo_theorem': 'closed',
        'prior_inventory_caveat': 'Preserve the previously recorded calibration-cost verifier cache; do not reseal old roots.',
    })
    save(OUT / 'design/seal.json', {p.name: digest(p) for p in (OUT / 'design').iterdir() if p.name != 'seal.json'})
    print('Prepared discovery round and preserved prior evidence.')


def fetch():
    inventory = []
    for label, (repo, revision, paths) in PINS.items():
        for rel in paths:
            target = OUT / 'sources' / label / rel
            if target.exists():
                raise RuntimeError('Refusing source overwrite: ' + str(target))
            url = f'https://raw.githubusercontent.com/{repo}/{revision}/{rel}'
            req = urllib.request.Request(url, headers={'User-Agent': 'cpu-quota-source-audit'})
            data = urllib.request.urlopen(req, timeout=30).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            inventory.append({'path': str(target.relative_to(OUT)), 'url': url, 'sha256': digest(target), 'bytes': len(data)})
            print(label, rel, len(data))
    save(OUT / 'source_inventory.json', inventory)


def verify():
    protected = json.loads((OUT / 'design/protected_sha256.json').read_text())
    preserved = json.loads((OUT / 'design/preserved_sha256.json').read_text())
    for rel, expected in {**protected, **preserved}.items():
        if digest(ROOT / rel) != expected:
            raise RuntimeError('Prior evidence changed: ' + rel)
    for record in json.loads((OUT / 'source_inventory.json').read_text()):
        if digest(OUT / record['path']) != record['sha256']:
            raise RuntimeError('Source changed: ' + record['path'])
    result = {'protected_scientific_paths': len(protected), 'additional_preserved_paths': len(preserved), 'sources_hashes_valid': True, 'paper_unchanged': True, 'fresh_workload_runs': 0}
    save(OUT / 'preservation_audit.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    {'prepare': prepare, 'fetch': fetch, 'verify': verify}[sys.argv[1]]()
