#!/usr/bin/env python3
"""Offline evidence replay of the separately declared imgproxy forensic probe."""
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import imgproxy_throttle_probe as probe
import leftover_observer_review as observer

q = probe.q


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_seal(path, root):
    files = q.read(path)['files_sha256']
    for name, digest in files.items():
        require(q.prep.sha(root / name) == digest, 'Changed sealed evidence: ' + name)
    return files


def main():
    base = probe.BASE
    run = base / 'run'
    service = run / 'service'
    out = ROOT / 'analysis/runtime_io_imgproxy_throttle_probe_review/20261009-generation01'
    require(not out.exists(), 'Preserve the existing review')
    check_seal(q.BASE / 'bundle-seal.json', ROOT)
    check_seal(base / 'bundle-seal.json', ROOT)
    files = check_seal(run / 'evidence-seal.json', run)
    actual = {str(p.relative_to(run)) for p in run.rglob('*')
              if p.is_file() and p != run / 'evidence-seal.json'}
    require(actual == set(files), 'Run evidence file set differs')
    require(q.read(base / 'protocol.json') == probe.PROTOCOL, 'Protocol differs')
    ref = q.read(run / 'observer-inventory.json')
    require(q.prep.sha(Path(ref['path'])) == ref['sha256'], 'Observer inventory changed')
    require(observer.review(Path(ref['path']))['performance_eligible'], 'Observer inventory ineligible')
    container = q.read(service / 'container.json')['inspect']
    owned = q.read(service / 'ownership.json')
    require(container['Config']['Labels'][q.LABEL] == owned['nonce'], 'Ownership label differs')
    require(container['Image'] == q.read(q.SOFTWARE / 'images.json')['observed'], 'Image differs')
    require(q.read(service / 'initial.json')['limits'] == q.LIMITS, 'Resource limits differ')
    require(q.read(service / 'executable.json')['sha256'] ==
            q.read(q.SOFTWARE / 'manifest.json')['binaries']['observed'], 'Executable differs')
    cleanup = q.read(service / 'cleanup.json')
    require(not cleanup['errors'] and cleanup['elapsed_sec'] <= 120, 'Cleanup/lifetime unavailable')
    require(not (service / 'watchdog-cleanup.json').exists(), 'Watchdog intervention')
    lifetime = q.read(run / 'lifetime.json')
    require(lifetime['protocol'] == probe.PROTOCOL and lifetime['elapsed_sec'] <= 300, 'Total lifetime differs')

    summary = q.read(run / 'summary.json')
    clients = {phase: q.read(service / (phase + '.json')) for phase in ('warmup', 'measurement')}
    events = q.read(run / 'events.json')
    ids = {r['ID'] for c in clients.values() for r in c['Rows']}
    require(len(events['Records']) == len(ids) == 225 and
            {r['ID'] for r in events['Records']} == ids, 'All-offer event identities differ')
    for phase, client in clients.items():
        bounds = q.read(service / (phase + '-bounds.json'))
        probe.validate_anchor(client, bounds['launch_before_ns'], bounds['exit_after_ns'])
        timing = q.validate_client(client, phase, 25 if phase == 'warmup' else 200, probe.output_hash())
        require(timing == summary['client_timings'][phase], 'Client timing replay differs')
        require(q.join_records(client, events) == summary['paired_timings'][phase], 'Server join replay differs')

    windows = q.read(run / 'windows.json')
    deltas = {phase: {k: w['after'][k] - w['before'][k] for k in w['before']}
              for phase, w in windows.items()}
    require(deltas == summary['window_counter_deltas'], 'Counter window replay differs')
    require(all(v >= 0 for d in deltas.values() for v in d.values()), 'Counter window regression')
    require(windows['idle']['end_ns'] - windows['idle']['start_ns'] >= 40_000_000_000,
            'Idle window too short')
    trace = q.read(run / 'counter-timeline.json')
    require(trace['error'] is None and trace['interval_sec'] == .004, 'Sampler unavailable')
    rows = trace['rows']
    require(1 < len(rows) <= probe.PROTOCOL['counter_sample_cap'], 'Sample count outside bounds')
    for row in rows:
        require(row['before_ns'] <= row['after_ns'], 'Counter read bracket reversed')
    for a, b in zip(rows, rows[1:]):
        require(a['after_ns'] <= b['before_ns'], 'Sample clock order reversed')
        require(set(a['cpu_stat']) == set(b['cpu_stat']) and
                all(b['cpu_stat'][k] >= v for k, v in a['cpu_stat'].items()), 'Sample counter regression')
    gap = max(b['after_ns'] - a['before_ns'] for a, b in zip(rows, rows[1:]))
    changes = probe.counter_changes(rows, clients)
    require(changes == summary['counter_changes'] and len(rows) == summary['counter_samples'] and
            gap == summary['maximum_sample_gap_ns'], 'Timeline replay differs')
    observed = any(d['nr_throttled'] for d in deltas.values()) or bool(changes)
    status = 'throttling_observed' if observed else 'throttling_not_observed_in_this_probe'
    require(status == summary['status'], 'Classification replay differs')
    require(all(summary[k] is False for k in
                ('scientific_collection', 'qualification_pass', 'causal_mechanism_established')),
            'Unsupported inference flag')
    # The preserved original failure remains part of the interpretation.
    check_seal(ROOT / 'analysis/runtime_io_imgproxy_feasibility_review/20261009-generation01/evidence-seal.json', ROOT)
    original = q.read(q.BASE / 'pilot/p2_observed/measurement-counters.json')
    require(original['after']['nr_throttled'] - original['before']['nr_throttled'] == 1,
            'Original failed trial differs')
    measured = clients['measurement']['Rows']
    latency = sorted(r['BodyDoneNs'] - r['ScheduledNs'] for r in measured)
    value = dict(status='verified_' + status, elapsed_sec=lifetime['elapsed_sec'],
                 successful_offers=225, measurement_offers=200, window_counter_deltas=deltas,
                 throttle_counter_at_first_sample=rows[0]['cpu_stat']['nr_throttled'],
                 throttled_usec_at_first_sample=rows[0]['cpu_stat']['throttled_usec'],
                 counter_samples=len(rows), maximum_sample_gap_ns=gap,
                 median_e2e_ns=summary['client_timings']['measurement']['median_e2e_ns'],
                 p99_e2e_ns=latency[math.ceil(.99 * len(latency)) - 1], max_e2e_ns=max(latency),
                 max_queue_ns=max(r['QueueNs'] for r in measured),
                 cpu_usec_per_measurement_offer=deltas['measurement']['usage_usec'] / 200,
                 original_qualification='unavailable', causal_mechanism_established=False,
                 scientific_replication_established=False, owned_cleanup_verified=True)
    out.mkdir(parents=True)
    q.save(out / 'report.json', value)
    (out / 'report.md').write_text(f'''# Imgproxy forensic probe: verified, cause unresolved

The separate probe completed in {value['elapsed_sec']:.3f} seconds. Both input
seals and the complete run evidence seal verify. Runtime, image, executable,
resource and ownership identities verify. All 225 offers (25 warmup, 200
measurement) have successful matching image bodies, valid clock brackets and
paired raw server events. Owned cleanup completed without errors.

The 40-second idle window and original 5 req/s measurement window each recorded
zero new throttled periods and zero additional throttled time. All 20,418
counter samples retain nr_throttled=1 and throttled_usec=24,125 from before the
idle window. Thus the service had a pre-idle throttle; this probe did not observe
a new throttle during monitoring. The largest counter sample gap was 7.714 ms.
The cumulative counters also cover gaps between samples.

Measurement median end-to-end latency was 17.392 ms. All 200 measurement queue
waits were <=100 us. Whole-cgroup measured CPU consumption was 16.786 ms per
offer. These are descriptive forensic observations, not a new cost qualification.

The original p2_observed measurement throttle and stopped pilot remain verified
and unchanged. The probe has a different service-age schedule (40 seconds idle)
and an added sampler whose overhead is not qualified. It is not a replacement
trial. The absence of a new throttle does not identify the old throttle's cause,
demonstrate that it was fixed, or establish which background/native work caused it.

There is still no complete six-pair observer-cost qualification, effective native
concurrency qualification, or fresh calibration/held-out imgproxy forecast test.
The current 25 ms/100 ms candidate remains unqualified. Stop this candidate's
scientific collection at this gate; do not rerun the pilot until it passes or
weaken the zero-throttle rule after observing the failure. Any revised candidate
requires a separately justified, prospective engineering protocol before its
new measurements. V31's confirmed result remains unchanged. This probe supports
no new mechanism, application-transfer, or novelty claim.
''')
    paths = [Path(__file__).resolve(), out / 'report.json', out / 'report.md', run / 'evidence-seal.json',
             base / 'bundle-seal.json', Path(ref['path'])]
    q.save(out / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(ROOT)): q.prep.sha(p) for p in paths}))
    print(out / 'report.md')
    print('Verified raw replay; original qualification remains unavailable.')


if __name__ == '__main__':
    main()
