#!/usr/bin/env python3
"""Preserve and verify the pre-measurement abort caused by the old affinity check."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import imgproxy_one_cpu_qualify as one

q = one.q


def main():
    one.verify(check_boot=False)
    pilot = one.BASE / 'pilot'
    case = pilot / 'p1_stock'
    seal = q.read(pilot / 'evidence-seal.json')['files_sha256']
    actual = {str(p.relative_to(pilot)) for p in pilot.rglob('*')
              if p.is_file() and p != pilot / 'evidence-seal.json'}
    one.require(actual == set(seal), 'Evidence file set differs')
    for name, digest in seal.items():
        one.require(q.prep.sha(pilot / name) == digest, 'Evidence changed: ' + name)
    summary = q.read(pilot / 'summary.json')
    failure = q.read(case / 'failure.json')
    one.require(summary['status'] == 'qualification_unavailable' and summary['rows'] == [], 'Unexpected summary')
    one.require(failure['error'] == summary['error'] == 'live service thread changed cgroup/CPU affinity',
                'Unexpected failure')
    one.require('q.bridge.snapshot(service.pid, service.group)' in failure['traceback'], 'Unexpected call site')
    helper = (ROOT / 'diagnostic/kernel_service_bridge.py').read_text()
    one.require('os.sched_getaffinity(tid)!={2,4}' in helper, 'Original affinity check differs')
    container = q.read(case / 'container.json')['inspect']
    one.require(container['Image'] == q.read(q.SOFTWARE / 'images.json')['stock'], 'Image differs')
    one.require(container['Config']['Labels'][q.LABEL] == q.read(case / 'ownership.json')['nonce'], 'Ownership differs')
    one.require(container['HostConfig']['CpusetCpus'] == '2' and
                q.read(case / 'initial.json')['limits'] == one.LIMITS, 'Resource contract differs')
    one.require(q.read(case / 'executable.json')['sha256'] ==
                q.read(q.SOFTWARE / 'manifest.json')['binaries']['stock'], 'Executable differs')
    one.require(q.read(case / 'sources-at-start.json') == one.source_hashes(), 'New source changed')
    one.require(not q.read(case / 'cleanup.json')['errors'] and not (case / 'watchdog-cleanup.json').exists(),
                'Owned cleanup unverified')
    body_hash = q.prep.sha(case / 'output.jpg')
    one.require(body_hash == q.read(q.BASE / 'functional/attempt-03/summary.json')['rows'][0]['body_sha256'],
                'Image identity differs')
    warmup = q.validate_client(q.read(case / 'warmup.json'), 'warmup', 25, body_hash)
    one.require(not list(pilot.rglob('measurement*.json')), 'Measurement unexpectedly started')
    ref = q.read(pilot / 'observer-inventory.json')
    one.require(q.prep.sha(Path(ref['path'])) == ref['sha256'], 'Inventory changed')
    one.review_inventory(Path(ref['path']))
    out = ROOT / 'analysis/runtime_io_imgproxy_one_cpu_abort_review/20261009-generation01'
    out.mkdir(parents=True, exist_ok=False)
    q.save(out / 'report.json', dict(status='verified_pre_measurement_runner_abort',
        created_services=1, warmup_offers=25, measurement_offers=0,
        warmup=warmup, elapsed_sec=summary['elapsed_sec'], owned_cleanup_verified=True,
        cause='New one-CPU runner called a frozen thread snapshot requiring exactly CPUs 2,4.',
        limitation='The rejected thread ID and its affinity were not persisted; no post-cleanup recovery is possible.',
        scientific_collection=False, observer_cost_qualified=False, original_throttle_cause_established=False))
    (out / 'report.md').write_text('''# One-CPU generation 01: pre-measurement technical abort

The sealed bundle and exact pilot evidence file set verify. The first stock
service had the declared one-CPU resource configuration and pinned image/binary.
Its 25 warmup offers succeeded with the original complete-response JPEG hash.
Owned cleanup completed without errors. No measurement collection started, and
there are no paired cost endpoints or scientific outcomes.

The frozen helper kernel_service_bridge.snapshot requires affinity exactly
{2,4}. The new runner called it despite requiring cpuset.cpus.effective=2.
This is an implementation inconsistency: that helper rejects the intended valid
single-CPU affinity. The failure was before the first measurement counter bracket.
The rejected thread identity/affinity were not saved, so those individual values
cannot be retrospectively inspected. This result establishes no new throttle,
performance difference, or cause of the original imgproxy throttle.

Preserve the attempted pilot and all generation-01 sources/seals. The original
preparation did not exercise the snapshot path used after warmup. Correct that
gap in generation 02 using a local strict {2} snapshot checker with equivalent
cgroup identity and disappearing-thread handling. Exercise the actual checker
before and after both real stock/observed functional cohorts, add regression
tests for single-CPU success and wrong-affinity/cgroup failure, and seal before
a new bounded qualification. Rates, operation, binaries, quota, statistical
acceptance rules and no-replacement policy remain unchanged. This repair is
justified by a verified pre-measurement code defect, not a favorable outcome.
''')
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md',
             one.BASE / 'bundle-seal.json', pilot / 'evidence-seal.json', Path(ref['path'])]
    q.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): q.prep.sha(p) for p in paths}))
    print(out / 'report.md')


if __name__ == '__main__':
    main()
