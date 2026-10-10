#!/usr/bin/env python3
"""Offline replay of the preserved gzip queue-domain qualification exit."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import gzip_qualify as q


def main():
    q.verify(False)
    pilot = q.BASE / 'pilot'
    sealed = q.read(pilot / 'evidence-seal.json')['files_sha256']
    actual = {str(p.relative_to(pilot)) for p in pilot.rglob('*')
              if p.is_file() and p != pilot / 'evidence-seal.json'}
    q.require(actual == set(sealed), 'Pilot file set differs')
    for name, digest in sealed.items():
        q.require(q.sha(pilot / name) == digest, 'Pilot evidence changed: ' + name)
    summary = q.read(pilot / 'summary.json')
    error = 'Gzip qualification gate failed: queue_domain; no replacement allowed'
    q.require(summary['status'] == 'qualification_unavailable' and summary['error'] == error,
              'Unexpected stopped outcome')
    q.require(not summary['scientific_collection'] and not summary['ready_for_scientific_collection'],
              'Unsupported scientific claim')
    q.require(q.read(pilot / 'lifetime.json')['protocol'] == q.PROTOCOL and
              summary['elapsed_sec'] <= 1200, 'Protocol/lifetime differs')
    inventory = q.read(pilot / 'observer-inventory.json')
    inventory_path = Path(inventory['path'])
    q.require(q.sha(inventory_path) == inventory['sha256'] and
              q.observer.review(inventory_path)['performance_eligible'], 'Observer inventory differs')
    expected = []
    for pair, order in enumerate(q.PROTOCOL['pair_orders'], 1):
        for arm in order.split(','):
            expected.append((pair, arm, f'p{pair}_{arm}'))
            if expected[-1][2] == 'p4_observed': break
        if expected[-1][2] == 'p4_observed': break
    q.require({p.name for p in pilot.glob('p*_*') if p.is_dir()} == {r[2] for r in expected},
              'Attempted trial prefix differs')
    cases, accepted = [], []
    manifest = q.read(q.SOFTWARE / 'manifest.json')
    images = q.read(q.SOFTWARE / 'images.json')
    for pair, arm, name in expected:
        case = pilot / name
        cleanup = q.read(case / 'cleanup.json')
        q.require(not cleanup['errors'] and cleanup['elapsed_sec'] <= 120 and
                  not (case / 'watchdog-cleanup.json').exists(), 'Cleanup/invalidation differs')
        container = q.read(case / 'container.json')['inspect']
        host = container['HostConfig']; initial = q.read(case / 'initial.json')
        q.require(container['Image'] == images[arm] and
                  container['Config']['Labels'][q.LABEL] == q.read(case / 'ownership.json')['nonce'] and
                  container['Config']['User'] == q.PROTOCOL['application_user'], 'Runtime ownership differs')
        q.require(initial['limits'] == q.LIMITS and host['CpuQuota'] == 25000 and
                  host['CpuPeriod'] == 100000 and host['CpusetCpus'] == '2', 'Resources differ')
        q.require(q.read(case / 'executables.json') ==
                  dict(server=manifest['binaries'][arm], gzip=manifest['gzip_sha256']) and
                  q.read(case / 'sources-at-start.json') == q.sources(), 'Source/executable differs')
        for phase in ('before', 'after'):
            snapshot = q.read(case / f'threads-{phase}.json')
            q.require(snapshot['affinity'] == [2] and snapshot['cgroup'] == initial['cgroup'] and
                      snapshot['main_pid'] == initial['pid'] and
                      any(p['pid'] == initial['pid'] for p in snapshot['processes']), 'Snapshot differs')
        q.require(q.sha(case / 'output.gz') ==
                  q.read(q.selection.BASE / 'correctness/result.json')['output_sha256'], 'Correctness body differs')
        counts = q.read(case / 'measurement-counters.json')
        q.require(q.read(case / 'measurement-before.json') == counts['before'], 'Before counters differ')
        result = q.analyze(case, arm, 200, False)
        q.require(result['recorded_throttled_periods'] == 0 and
                  counts['delta']['throttled_usec'] == 0, 'Unexpected measurement throttle')
        if name != 'p4_observed':
            q.identity(case, arm)
            q.require(q.analyze(case, arm, 200, True) == q.read(case / 'result.json'), 'Accepted replay differs')
            accepted.append(dict(result, pair=pair))
        else:
            q.require(q.read(case / 'failure.json')['error'] == error and not (case / 'result.json').exists(),
                      'Failed classification differs')
            try: q.analyze(case, arm, 200, True)
            except ValueError as exc: q.require(str(exc) == error, 'Failed gate replay differs')
            else: raise ValueError('Failed trial unexpectedly passed')
        cases.append(dict(case=name, pair=pair, **result, measurement_counter_delta=counts['delta'],
                          prior_throttled_periods=counts['before']['nr_throttled'], cleanup_verified=True))
    q.require(accepted == summary['rows'] and len(accepted) == 6, 'Accepted rows differ')
    case = pilot / 'p4_observed'
    events = q.read(case / 'events.json')['Records']
    index = {r['ID']: i for i, r in enumerate(events)}
    exceedances = []
    for row in q.read(case / 'measurement.json')['Rows']:
        if row['QueueNs'] <= 100000: continue
        i = index[row['ID']]; event = events[i]; previous = events[i - 1]
        exceedances.append(dict(id=row['ID'], queue_ns=row['QueueNs'],
            previous_release_to_enqueue_ns=event['EnqueuedNs'] - previous['ReleasedNs'],
            process_ns=row['ProcessNs'], e2e_ns=row['BodyDoneNs'] - row['ScheduledNs']))
    q.require(len(exceedances) == 3 and all(r['previous_release_to_enqueue_ns'] > 0 for r in exceedances),
              'Queue exceedance/no-overlap finding differs')
    out = ROOT / 'analysis/runtime_io_gzip_failure_review/20261009-generation01'
    out.mkdir(parents=True, exist_ok=False)
    q.save(out / 'report.json', dict(status='verified_queue_domain_exit', failed_case='p4_observed',
        elapsed_sec=summary['elapsed_sec'], attempted_services=7, eligible_services=6,
        complete_eligible_pairs=3, successful_measurement_offers=1400, successful_warmup_offers=175,
        native_jobs_verified=1582, cases=cases, failed_case_queue_exceedances=exceedances,
        failed_case_queue_le_100us_fraction=.985, required_queue_le_100us_fraction=.99,
        all_measurement_throttle_deltas_zero=True, all_cleanup_verified=True,
        observer_cost_qualified=False, scientific_collection=False,
        application_transfer_established=False, scheduler_cause_established=False,
        inference='The three exceeded intervals contain worker handoff/acquisition delay with no prior job overlap; exact cause is unobserved.',
        next_step='Review timestamp boundaries and model applicability from retained evidence before proposing any fresh experiment. Preserve the fixed failure and thresholds.'))
    (out / 'report.md').write_text('''# Gzip qualification: verified queue-domain exit

Generation 01 stopped after seven services and 391.693 seconds (6.53 minutes).
Three complete pairs passed. The first service of pair 4, p4_observed, failed
the predeclared queue-domain gate: 197/200 offers (98.5%) had enqueue-to-worker
acquisition time <=100 us, while the requirement was >=99% (198/200).
The three exceedances were 132.037, 100.468 and 113.252 us. No observations are
rounded to change their classification. The failed trial remains failed.

All 1,400 measurement offers and 175 warmup offers returned matching full gzip
bodies and request IDs. All 1,582 native jobs, including seven correctness
requests, verify identity/affinity/cgroup/pidfd/exec/reap and body size. Each
measurement window has zero increments of both nr_throttled and throttled_usec;
startup/warmup counter values are separate. Dispatch gates, raw timing joins,
owned cleanup, source/runtime identities, actual one-CPU snapshots, root
observer inventory, evidence file sets and hashes verify for all seven services.
The original failure replays exactly, and all failed-trial raw records survived.

For the three longer queue intervals, the preceding worker release occurred
180.852317, 180.181956 and 180.822303 ms before the new request's enqueue.
The new request therefore did not wait behind the preceding compression job.
The recorded queue interval includes dispatcher critical-section work, worker
wakeup/scheduling, mutex reacquisition, dequeue and work before the acquisition
timestamp. This is the declared implementation boundary, not proof of backlog
or an identified operating-system fault. No scheduler trace resolves these
components. The failed trial's median offered-to-full-body latency was 20.426 ms;
its queue exceedances were 0.100468–0.132037 ms.

Seven completed traffic cohorts cannot establish the required six-pair observer
cost result. Qualification is unavailable and no scientific calibration or
held-out forecast validation began. This applicability limit neither confirms
nor refutes V31's prediction in its original tested domain and establishes no
novelty or independent replication.

Do not rerun this fixed pilot, discard the failed cohort, or relax 100 us/99%
after seeing the outcome. The useful next step is a timing-boundary and model
applicability review using these saved records, before choosing another service
or proposing a separately justified prospective revision. Any later changed
candidate must retain this result and explicitly declare its changed scope.
''')
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md',
             q.BASE / 'bundle-seal.json', pilot / 'evidence-seal.json', inventory_path]
    q.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): q.sha(p) for p in paths}))
    print(out / 'report.md')
    print('Verified: queue-domain exit, no prior compression overlap, qualification unavailable.')


if __name__ == '__main__': main()
