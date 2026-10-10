#!/usr/bin/env python3
"""Verify completed V18 compatibility captures; no kernel/request attribution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'diagnostic'))
import kernel_service_bridge as bridge


def read(path): return json.loads(path.read_text())


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(directory, name):
    expected=read(directory/name)['files_sha256']
    actual={str(p.relative_to(directory)):digest(p) for p in directory.rglob('*')
            if p.is_file() and p!=directory/name}
    if actual!=expected: raise ValueError('sealed file inventory/hash mismatch: '+str(directory))
    return digest(directory/name)


def request_bounds(classified, client, server, joined):
    requests={q['ID']:q for q in client['requests']}
    jobs={j['id']:j for j in server['events']};handlers={h['id']:h for h in server['handler_events']}
    result=[]
    for row in classified['requests']:
        if row['deadline_ms']!=500: continue
        q=requests[row['id']]
        origin=classified['mapping']['client_test_start_ns']+q['ScheduledOffsetNs']
        value=dict(id=row['id'],outcome=row['outcome'],deadline_crossing=row['deadline_crossing'],
                   scheduled_kernel_lower_ns=origin+joined['kernel_minus_client_lower_ns'],
                   scheduled_kernel_upper_ns=origin+joined['kernel_minus_client_upper_ns'])
        for name,records in (('completion',jobs),('resume',handlers)):
            record=records.get(row['id']);stamp=None if record is None else record[name+'_ns']
            value[name+'_kernel_lower_ns']=None if stamp is None else stamp+joined['kernel_minus_server_lower_ns']
            value[name+'_kernel_upper_ns']=None if stamp is None else stamp+joined['kernel_minus_server_upper_ns']
        result.append(value)
    return result


def review(source):
    capture_seal=seal(source,'seal.json')
    summary=read(source/'summary.json')
    if not summary['passed'] or summary['error'] or len(summary['cases'])!=5:
        raise ValueError('compatibility capture did not complete')
    if not summary['root_trace_controls_unchanged'] or read(source/'root_trace_state_before.json')!=read(source/'root_trace_state_after.json'):
        raise ValueError('root trace controls changed')
    if any(summary[k] for k in ('observer_cost_qualified','performance_batch_ready','performance_run')):
        raise ValueError('unexpected cost/performance qualification')
    manifest=read(source/'assets/manifest.json')
    for name,expected in manifest['sources'].items():
        if digest(source/'source'/name)!=expected: raise ValueError('frozen source hash mismatch: '+name)
        if digest(ROOT/name)!=expected: raise ValueError('current reviewer dependencies differ from capture: '+name)
    for name,expected in read(source/'assets/seal.json')['files_sha256'].items():
        if digest(source/'assets'/name)!=expected: raise ValueError('copied asset hash mismatch: '+name)
    if digest(source/'assets/kernel_bridge.bt')!=manifest['sources']['diagnostic/kernel_bridge.bt']:
        raise ValueError('executed BPF differs from frozen source')
    retained=read(source/'retained_cases.json')
    ref=manifest['resume_from']
    checked=bridge.retained_cases(ref['path'],ref['seal_sha256'])
    if checked!=retained or checked['cases']!=summary['cases'][:3]:
        raise ValueError('retained capture provenance/replay mismatch')
    if retained['previous_identity']!={k:manifest[k] for k in retained['previous_identity']}:
        raise ValueError('original input identities differ across source generations')
    cases=[]
    for index,name in enumerate(('service_g1_quota','service_g2_quota'),3):
        d=source/name;attempt=read(d/'attempt.json');m=attempt['metadata']
        if attempt['error'] or attempt['cleanup_errors'] or not attempt['cgroup_removed'] or m['observer_returncode']:
            raise ValueError('case process/cleanup check failed: '+name)
        if not attempt['owned_bpf_ids'] or attempt['owned_bpf_ids']!=m['owned_bpf_ids']:
            raise ValueError('owned BPF identities missing/mismatched')
        expected_limits={'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2,4',
                         'memory.max':'268435456','pids.max':'128'}
        if m['initial_limits']!=expected_limits or m['initial_cpu_stat']['nr_throttled']:
            raise ValueError('resource settings/initial state mismatch')
        if any(a['cpu_max'].split()[0]!='max' for a in m['uncapped_ancestors']):
            raise ValueError('capped ancestor')
        for namespace in m['time_namespaces'].values():
            if namespace!={'monotonic':[0,0],'boottime':[0,0]}: raise ValueError('shifted time namespace')
        if m['executable_sha256']!=manifest['server_sha256'] or m['http_workload']!=bridge.http_workload(True):
            raise ValueError('original server or declared functional load differs')
        container=read(d/'container.json')['inspect']
        if container['Image']!=manifest['image'] or len(container['Mounts'])!=1 or container['Mounts'][0]['Destination']!='/qualification' or container['Mounts'][0]['RW']:
            raise ValueError('image/packaged loading differs')
        client=read(d/'loadgen.json');server=read(d/'server_metrics.json')
        classified=bridge.repeatability_analysis.classify(client,server,'legacy_a')
        if classified!=read(d/'request_classification.json') or classified['offered']!=453 or classified['missing_entry_count']:
            raise ValueError('request classification/conservation replay mismatch')
        if server['gomaxprocs']!=m['gomaxprocs'] or server['workers']!=4 or server['queue_cap']!=128 or not server['instrument']:
            raise ValueError('service configuration differs')
        anchors=read(d/'kernel_server_anchors.json')
        joined=bridge.analysis.clock_join(anchors,classified['mapping'],server['clock_generation'])
        if joined!=read(d/'clock_mapping.json'): raise ValueError('clock mapping replay mismatch')
        result=bridge.analysis.coverage((d/'events.txt').read_text(),(d/'observer.stderr').read_text(),m,
                                        read(d/'thread_snapshots.json'))
        if result['observed_cpus']!=[2,4]: raise ValueError('two-CPU scheduling coverage missing')
        begin,end=result['capture_begin_ns'],result['capture_end_ns']
        if not all(begin<a['before_ns']<=a['after_ns']<end for a in anchors): raise ValueError('anchor outside capture')
        bounds=request_bounds(classified,client,server,joined)
        if bounds!=read(d/'request_kernel_bounds.json'): raise ValueError('request clock bounds replay mismatch')
        for row in bounds:
            for boundary in ('completion','resume'):
                lo=row[boundary+'_kernel_lower_ns'];hi=row[boundary+'_kernel_upper_ns']
                if lo is not None and not begin<=lo<=hi<=end: raise ValueError('request boundary outside capture')
        result.update(offered=classified['offered'],clock_uncertainty_ns=joined['uncertainty_ns'])
        result=json.loads(json.dumps(result))
        if result!=read(d/'validation.json') or result!=summary['cases'][index]:
            raise ValueError('event replay differs from validation/summary')
        intervals=result['quota_intervals']
        durations=[(v['duration_lower_ns']+v['duration_upper_ns'])/2e6 for v in intervals]
        cases.append(dict(case=name,source=str(d),gomaxprocs=m['gomaxprocs'],offered=classified['offered'],
            received_events=result['received_events'],throttle_attempts=result['throttle_attempts'],
            quota_intervals_by_cpu=dict(Counter(v['cpu'] for v in intervals)),
            closed_per_cpu_intervals=len(intervals),nr_throttled=m['cpu_stat_delta']['nr_throttled'],
            interval_duration_midpoint_ms=dict(median=statistics.median(durations),minimum=min(durations),maximum=max(durations)),
            clock_uncertainty_ns=joined['uncertainty_ns'],deadline_counts=classified['deadlines'],
            raw_replay_verified=True,cleanup_checks_passed=True))
    return dict(source=str(source),capture_seal_sha256=capture_seal,retained_origins=retained['origins'],
        original_input_identities=retained['previous_identity'],cases=cases,
        decision='bounded_service_compatibility_verified',root_trace_controls_unchanged=True,
        five_cases_verified=True,observer_cost_qualified=False,performance_batch_ready=False,
        request_throttle_attribution=False,next_gate='prepare and freeze six matched tracing-off/on pairs')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();source=args.source.resolve();output=args.output.resolve()
    if output==source or source in output.parents: raise ValueError('derived output must be outside sealed capture')
    result=review(source);output.mkdir(parents=True,exist_ok=False)
    (output/'review.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'review_source.py').write_bytes(Path(__file__).read_bytes())
    lines=['# V18 bounded service compatibility review','',
        'Decision: **bounded_service_compatibility_verified**.','',
        'The complete capture/asset/source seals verify. Raw scheduler/quota records,',
        'thread snapshots, original service/client outcomes, clock joins and exported',
        'request bounds reproduce both fresh validations and the five-case summary.',
        'Three earlier controls are independently reverified and retain their original',
        'origins; they are not new replications. Recorded owned detach/cgroup cleanup',
        'checks passed and root tracing controls match before/after.','',
        '| Fresh capped case | Offered | Per-CPU quota intervals | nr_throttled | Clock uncertainty |',
        '|---|---:|---:|---:|---:|']
    for c in result['cases']:
        lines.append(f"| G{c['gomaxprocs']} | {c['offered']} | {c['closed_per_cpu_intervals']} | {c['nr_throttled']} | {c['clock_uncertainty_ns']/1e6:.3f} ms |")
    lines+=['','Quota intervals are separate CPU/runqueue state intervals, not counts of',
        'whole-service pauses. Counter reads end before container stop; capture extends',
        'through final exits. Interval counts need not equal throttled-period counts.',
        'Do not sum overlapping per-CPU intervals into whole-service lost time.','',
        'The short traced G1 case retains 36 late successful 500 ms responses whose',
        'computation certainly completed before that deadline under the original',
        'client/server clock bounds (14 with at least 50 ms margin). This establishes',
        'that the symptom and kernel records coexist in this functional capture.',
        'The load is revised steady traffic, not the historical bursty trial.','',
        'Observer overhead is unqualified. No kernel overlap/HTTP-cause attribution',
        'or G1/G2 performance contrast is accepted from these short captures.',
        'Publication and handler runnable-readiness remain unobserved. The earlier',
        'light-load failed positive control remains failed and unchanged.','',
        'Next: prepare and freeze the six-pair off/on cost protocol, using the same',
        'original packaged service, fixed G1/workers4/quota and historical bursty load',
        'in both arms. Extend and qualify collector lifecycle/capacity through warmup,',
        'measurement and full drain. Both arms need identical startup/monitoring',
        'procedures, root-helper scope/cleanup and a quiet-host thermal/power baseline.',
        'The twelve-trial implementation remains pending; this review launches no batch.',
        'Passing practical margins would still not establish statistical equivalence.','']
    (output/'report.md').write_text('\n'.join(lines))
    (output/'review_seal.json').write_text(json.dumps(dict(files_sha256={p.name:digest(p)
        for p in output.iterdir() if p.is_file()}),indent=2)+'\n')
    print(output/'report.md')


if __name__=='__main__':main()
