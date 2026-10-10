#!/usr/bin/env python3
"""Offline review of the completed traffic but domain-failed one-CPU pilot."""
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import imgproxy_one_cpu_qualify_v2 as one

q = one.q
require = one.require


def main():
    one.verify(check_boot=False)
    pilot = one.BASE / 'pilot'
    sealed = q.read(pilot / 'evidence-seal.json')['files_sha256']
    actual = {str(p.relative_to(pilot)) for p in pilot.rglob('*')
              if p.is_file() and p != pilot / 'evidence-seal.json'}
    require(actual == set(sealed), 'Pilot file set differs')
    for name, digest in sealed.items():
        require(q.prep.sha(pilot / name) == digest, 'Pilot evidence changed: ' + name)
    summary = q.read(pilot / 'summary.json')
    require(summary['status'] == 'qualification_unavailable' and
            summary['error'] == 'Measurement throttling; no replacement allowed', 'Unexpected outcome')
    require(not summary['scientific_collection'] and not summary['ready_for_scientific_collection'] and
            not summary['original_pilot_replaced'], 'Unsupported claim')
    ref = q.read(pilot / 'observer-inventory.json')
    require(q.prep.sha(Path(ref['path'])) == ref['sha256'], 'Inventory changed')
    one.review_inventory(Path(ref['path']))
    require(summary['elapsed_sec'] <= one.PROTOCOL['pilot_total_sec'], 'Total lifetime exceeded')
    require(q.read(pilot / 'lifetime.json')['protocol'] == one.PROTOCOL, 'Run protocol differs')
    cases, complete_rows, endpoint_rows = [], [], []
    expected_cases = {f'p{pair}_{arm}' for pair in range(1, 7) for arm in ('stock', 'observed')}
    require({p.name for p in pilot.glob('p*_*') if p.is_dir()} == expected_cases, 'Trial set differs')
    for pair, order in enumerate(one.PROTOCOL['pair_orders'], 1):
        for arm in order.split(','):
            case = pilot / f'p{pair}_{arm}'
            cleanup = q.read(case / 'cleanup.json')
            require(not cleanup['errors'] and cleanup['elapsed_sec'] <= 120, 'Cleanup/lifetime unavailable')
            require(not (case / 'watchdog-cleanup.json').exists(), 'Watchdog intervention')
            container = q.read(case / 'container.json')['inspect']
            require(container['Image'] == q.read(q.SOFTWARE / 'images.json')[arm], 'Image differs')
            require(container['Config']['Labels'][q.LABEL] == q.read(case / 'ownership.json')['nonce'], 'Ownership differs')
            initial = q.read(case / 'initial.json')
            require(container['HostConfig']['CpusetCpus'] == '2' and initial['limits'] == one.LIMITS,
                    'Single-CPU resource contract differs')
            require(q.read(case / 'executable.json')['sha256'] ==
                    q.read(q.SOFTWARE / 'manifest.json')['binaries'][arm], 'Executable differs')
            require(q.read(case / 'sources-at-start.json') == one.source_hashes(), 'Runner changed')
            for phase in ('before', 'after'):
                snapshot = q.read(case / f'threads-{phase}.json')
                require(snapshot['affinity'] == [2] and snapshot['cgroup'] == initial['cgroup'] and
                        initial['pid'] in snapshot['tids'] and snapshot['before_ns'] <= snapshot['after_ns'],
                        'Actual thread snapshot differs')
            digest = q.prep.sha(case / 'output.jpg')
            require(digest == q.read(q.BASE / 'functional/attempt-03/summary.json')['rows'][0]['body_sha256'],
                    'Image output identity differs')
            client = q.read(case / 'measurement.json')
            warmup = q.read(case / 'warmup.json')
            timing = q.validate_client(client, 'measurement', 200, digest)
            q.validate_client(warmup, 'warmup', 25, digest)
            require(timing['dispatch_p99_ns'] <= 2000000 and timing['dispatch_max_ns'] <= 10000000,
                    'Dispatch gate failed')
            counts = q.read(case / 'measurement-counters.json')
            delta = {k: counts['after'][k] - counts['before'][k] for k in counts['before']}
            require(delta == counts['delta'] and all(v >= 0 for v in delta.values()), 'Counter replay differs')
            require(q.read(case / 'measurement-before.json') == counts['before'], 'Before-counter evidence differs')
            joined = None
            if arm == 'observed':
                events = q.read(case / 'events.json')
                ids = {'image-check'} | {r['ID'] for c in (client, warmup) for r in c['Rows']}
                require(len(events['Records']) == len(ids) == 226 and
                        {r['ID'] for r in events['Records']} == ids and
                        all(r['Success'] for r in events['Records']), 'Raw all-offer server records differ')
                q.join_records(warmup, events)
                joined = q.join_records(client, events)
                require(joined['queue_le_100us_fraction'] >= .99, 'Observed queue gate failed')
            if case.name != 'p6_stock':
                one.check_case_identity(case, arm)
                result = one.classify_case(case, arm, True)
                require(result == q.read(case / 'result.json'), 'Successful trial replay differs')
                complete_rows.append(dict(result, pair=pair))
            else:
                require(q.read(case / 'failure.json')['error'] == summary['error'], 'Failed gate differs')
                require(not (case / 'result.json').exists(), 'Failed case has an accepted result')
                require(delta['nr_throttled'] == 1 and delta['throttled_usec'] == 46064, 'Failed counter differs')
                try:
                    one.classify_case(case, arm, True)
                except ValueError as exc:
                    require(str(exc) == summary['error'], 'Failed trial replay differs')
                else:
                    raise ValueError('Failed trial unexpectedly passed')
            endpoint_rows.append(dict(arm=arm, pair=pair, cpu_per_offer_usec=delta['usage_usec'] / 200,
                                      median_e2e_ns=timing['median_e2e_ns']))
            latency = sorted(r['BodyDoneNs'] - r['ScheduledNs'] for r in client['Rows'])
            cases.append(dict(case=case.name, arm=arm, **timing,
                measurement_counter_delta=delta, prior_throttled_periods=counts['before']['nr_throttled'],
                max_e2e_ns=max(latency), p99_e2e_ns=latency[math.ceil(.99 * len(latency)) - 1],
                raw_join=joined, owned_cleanup_verified=True, single_cpu_snapshots_verified=True))
    require(complete_rows == summary['rows'] and len(complete_rows) == 11, 'Accepted rows differ')
    # All twelve cohorts exist, but one exits the predeclared domain. Report cost
    # summaries only as descriptive; do not turn complete traffic into a pass.
    effects = q.effects_from(endpoint_rows)
    out = ROOT / 'analysis/runtime_io_imgproxy_one_cpu_failure_review/20261009-generation02'
    out.mkdir(parents=True, exist_ok=False)
    value = dict(status='verified_one_cpu_domain_exit', elapsed_sec=summary['elapsed_sec'],
        cases=cases, attempted_services=12, successful_measurement_offers=2400,
        successful_warmup_offers=300, eligible_services=11, complete_eligible_pairs=5,
        failed_case='p6_stock', descriptive_cost_effects_including_domain_exit=effects,
        observer_cost_qualified=False, scientific_collection=False,
        application_transfer_established=False, original_throttle_cause_established=False,
        conclusions=['An uninstrumented service recorded a measurement throttle with only CPU 2 granted.',
                     'Two-CPU execution and the added recorder are not necessary for throttling in this candidate.',
                     'Single-CPU restriction did not satisfy the zero-throttle qualification.'],
        limitation='No time-resolved scheduler/counter trace or stock server-stage timing; the throttle cannot be assigned to a specific request or background task.')
    q.save(out / 'report.json', value)
    (out / 'report.md').write_text('''# One-CPU imgproxy: verified qualification domain exit

The corrected generation-02 runner completed all twelve offered-traffic cohorts
in 675.173 seconds (11.253 minutes). Eleven services passed their individual
gates; the final stock service p6_stock failed the zero-throttle measurement
gate. All 2,400 measurement offers and 300 warmup offers succeeded with the
original complete-response JPEG hash. All twelve owned cleanups verify.
Input/evidence seals, root observer inventory, image/executable identities,
single-CPU resource settings and both actual thread snapshots per service verify.
The six observed cohorts retain all 226 server records each and their raw joins.

In p6_stock, nr_throttled increased from 3 before measurement to 4 afterward;
throttled_usec increased by 46,064 us. This is a measurement increment, not
just startup accounting. The service used 3,244,797 us of CPU in that window,
or 16.224 ms per offer. Its longest offered-to-full-body response was 21.890 ms.
The 46.064 ms is cgroup throttle accounting, not a measured delay of any one
request. No time-resolved trace locates it inside a particular request window.
The stock arm intentionally has no recorder or per-stage timing.

This failure occurs with the uninstrumented binary and one granted logical CPU.
Thus neither the added timing recorder nor simultaneous execution on CPUs 2,4
is necessary for measurement throttling under these tested conditions. This does
not identify the mechanism or prove why the earlier observed-arm throttle
occurred. Periodic memory freeing, other background work, and budget-period
alignment remain unproven explanations.

There are five complete domain-eligible pairs plus one clean observed cohort
and one stock domain exit. The JSON report includes the six-pair cost endpoints
as descriptive calculations including the failed cohort. They cannot override
the joint acceptance rules or establish observer-cost qualification.

Stop this imgproxy candidate at its predeclared gate. Do not repeat the pilot
until a favorable run appears, remove the last trial, or loosen zero throttling
after seeing this outcome. A future changed candidate needs an independently
justified prospective protocol. No imgproxy calibration or held-out forecast
validation occurred; this is an applicability limitation, not a rejection of
V31's forecast within its tested domain, an independent replication, or novelty.
The original pilot and pre-measurement generation-01 code abort remain preserved.
''')
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md',
             one.BASE / 'bundle-seal.json', pilot / 'evidence-seal.json', Path(ref['path'])]
    q.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): q.prep.sha(p) for p in paths}))
    print(out / 'report.md')
    print('Verified: uninstrumented one-CPU domain exit; stop this candidate.')


if __name__ == '__main__':
    main()
