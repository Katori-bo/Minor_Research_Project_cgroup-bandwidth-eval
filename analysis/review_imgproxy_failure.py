#!/usr/bin/env python3
"""Offline, separate review of the stopped imgproxy engineering pilot."""
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import imgproxy_qualify as q
import leftover_observer_review as observer


def main():
    base=q.BASE; pilot=base/'pilot'
    out=ROOT/'analysis/runtime_io_imgproxy_feasibility_review/20261009-generation01'
    out.mkdir(parents=True,exist_ok=True)
    if (out/'report.json').exists(): raise ValueError('preserve an existing completed review')
    seal=q.read(base/'bundle-seal.json')
    for name,digest in seal['files_sha256'].items():
        assert q.prep.sha(ROOT/name)==digest, name
    summary=q.read(pilot/'summary.json')
    assert summary['status']=='qualification_unavailable'
    assert summary['error']=='measurement throttling; no replacement allowed'
    ref=q.read(pilot/'observer-inventory.json'); assert q.prep.sha(Path(ref['path']))==ref['sha256']
    inventory=observer.review(Path(ref['path'])); assert inventory['performance_eligible']
    cases=[]
    for case in sorted(pilot.glob('p*_*')):
        arm=case.name.split('_')[1]
        client=q.read(case/'measurement.json'); warm=q.read(case/'warmup.json')
        digest=q.prep.sha(case/'output.jpg')
        stats=q.validate_client(client,'measurement',200,digest)
        q.validate_client(warm,'warmup',25,digest)
        counts=q.read(case/'measurement-counters.json')
        delta={k:counts['after'][k]-counts['before'][k] for k in counts['before']}
        assert delta==counts['delta'] and all(v>=0 for v in delta.values())
        assert not q.read(case/'cleanup.json')['errors']
        assert not (case/'watchdog-cleanup.json').exists()
        container=q.read(case/'container.json')['inspect']; owned=q.read(case/'ownership.json')
        assert container['Config']['Labels'][q.LABEL]==owned['nonce']
        assert container['Image']==q.read(q.SOFTWARE/'images.json')[arm]
        assert q.read(case/'initial.json')['limits']==q.LIMITS
        assert q.read(case/'executable.json')['sha256']==q.read(q.SOFTWARE/'manifest.json')['binaries'][arm]
        for name,sha in q.read(case/'sources-at-start.json').items(): assert q.prep.sha(ROOT/name)==sha
        rows=client['Rows']; latency=sorted(r['BodyDoneNs']-r['ScheduledNs'] for r in rows)
        queue=[r['QueueNs'] for r in rows] if arm=='observed' else None
        if queue is not None: assert all(not r['TimingError'] for r in rows)
        result=dict(case=case.name,arm=arm,successful=200,**stats,
            cpu_per_offer_usec=delta['usage_usec']/200,measurement_counters=delta,
            recorded_startup_warmup_throttled=counts['before']['nr_throttled'],
            p99_e2e_ns=latency[math.ceil(.99*200)-1],max_e2e_ns=max(latency),
            queue_le_100us_fraction=sum(v<=100000 for v in queue)/200 if queue is not None else None,
            max_queue_ns=max(queue) if queue is not None else None,
            server_events_retained=(case/'events.json').exists(),owned_cleanup_verified=True)
        if (case/'events.json').exists():
            server=q.read(case/'events.json'); q.join_records(warm,server)
            result['raw_join']=q.join_records(client,server)
        result['slowest_request']=max(rows,key=lambda r:r['BodyDoneNs']-r['ScheduledNs'])
        cases.append(result)
    assert {r['case'] for r in cases}=={'p1_stock','p1_observed','p2_observed'}
    failed=next(r for r in cases if r['case']=='p2_observed')
    assert failed['measurement_counters']['nr_throttled']==1
    assert failed['measurement_counters']['throttled_usec']==38456
    value=dict(status='verified_domain_exit',cases=cases,elapsed_sec=summary['elapsed_sec'],
        completed_pairs=1,attempted_services=3,measurement_offers=600,
        scientific_collection=False,observer_cost_qualification_established=False,
        causal_mechanism_established=False,root_observer_inventory_eligible=True,
        limitation='Failed trial server buffer was not exported before cleanup; no time-resolved counter trace or client clock anchor was recorded.')
    q.save(out/'report.json',value)
    (out/'report.md').write_text('''# Stopped imgproxy qualification: verified domain exit

The engineering pilot stopped after 168.719 seconds: one complete stock/observed
pair followed by p2_observed. All 600 measurement offers succeeded with matching
full-response image hashes. Cleanup is verified for all three owned services.
The preparation seal, runtime/image/resource identities, original sources,
actual measurement-counter differences and observer inventory all verify.

The failed trial's nr_throttled increased from 2 to 3 during measurement. Thus
the increase is not just its two pre-measurement startup/warmup throttles.
throttled_usec increased by 38,456 us. All 200 observed queue waits were <=100 us
(maximum 38.632 us). Its median end-to-end latency was 18.297 ms, with maximum
58.177 ms at measurement-125; that request reported 56.091 ms processing and
1.453 us queue wait. A slow request and a throttle increment are consistent with
a quota stall, but without a time-resolved trace their association is not proven.

Average measured CPU use was approximately 0.086 CPU, below the configured
0.25-CPU average allowance. An average allowance does not guarantee every
100-ms budget interval stays unthrottled. Application background work, native
thread behavior, and budget allocation remain candidate explanations. The
upstream default performs memory freeing every 10 s, including Go FreeOSMemory
and glibc malloc_trim; no recorded event establishes that it caused this stall.

There is only one complete pair. No six-pair confidence interval or observer-cost
qualification can be claimed. There is no calibration/held-out transfer result
and no new causal or novelty claim. The V31 result remains separate.

Reporting limitation: the frozen runner checked the domain before exporting
the failed trial's bounded server buffer. Client timing headers and CPU counters
remain, but that buffer cannot be recovered after owned cleanup. Keep this
limitation; do not rewrite the frozen collector or replace the failed trial.

Next: one separately declared forensic diagnostic with idle and fixed-load
windows, monotonic client anchors, a bounded CPU-counter timeline, and server
event export before classification. Keep the application, rate, worker setting
and quota unchanged. Its aim is localization, not passing the original pilot.
''')
    paths=[*pilot.rglob('*'),base/'bundle-seal.json',Path(ref['path']),Path(__file__).resolve()]
    q.save(out/'evidence-seal.json',dict(files_sha256={str(p.relative_to(ROOT)):q.prep.sha(p) for p in sorted(paths) if p.is_file()}))
    print(out/'report.md')


if __name__=='__main__': main()
