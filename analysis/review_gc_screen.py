#!/usr/bin/env python3
"""Read-only raw review of the completed eight-trial GC screen."""
import collections
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import runtime_gc_screen as screen
from review_period_cost_pilot import host_summary, fixed_busy_rate


def main():
    c=screen.c; session=screen.DEFAULT
    manifest=screen.verify_preparation(session,current=False)
    assert screen.source_hashes()==manifest['sources']
    latest=c.read(session/'latest_analysis.json')
    report_path=session/latest['path']; c.verify_seal(report_path)
    assert c.digest(report_path/'seal.json')==latest['seal']
    original=c.read(report_path/'report.json')
    assert original['preparation_seal']==c.digest(session/'preparation/seal.json')
    paths=[]; rows=[]; raw=[]; per_trial_host={}
    for spec in screen.matrix():
        path=session/'trials'/spec['trial']; result=screen.replay(path)
        assert result==c.read(path/'screen_derived.json')
        assert original['trial_seals'][spec['trial']]==c.digest(path/'seal.json')
        assert c.read(path/'complete.json')['valid'] is True
        observations=c.read(path/'observations.json')
        cpu=observations['measurement_stop']['cpu_stat']['usage_usec']-observations['measurement_start']['cpu_stat']['usage_usec']
        server=c.read(path/'server_metrics.json'); client=c.read(path/'loadgen.json')
        n=server['completed']; requests=client['requests']
        assert n==server['admitted']==len(server['events'])==len(requests)==6793
        assert len({r['ID'] for r in requests})==len(requests)
        cpu_per_job=cpu/n
        timely=sum(r['StatusCode']==200 and not r['Error'] and r['EndToEndLatencyNs']<=500_000_000 for r in requests)/len(requests)
        timely1000=sum(r['StatusCode']==200 and not r['Error'] and r['EndToEndLatencyNs']<=1_000_000_000 for r in requests)/len(requests)
        failures=sum(r['StatusCode']!=200 or bool(r['Error']) for r in requests)
        row=result['summary']; rows.append(row); paths.append(path)
        assert math.isclose(cpu_per_job,row['cpu_usec_per_completed_work'],rel_tol=1e-12)
        assert timely==row['timely_500_fraction'] and timely1000==row['timely_1000_fraction']
        assert failures/len(requests)==row['failure_fraction']
        warm=c.read(path/'warmup_server_metrics.json')
        assert warm['completed']==warm['admitted']==2265 and warm['rejected']==0
        peak=max(r['memory_peak_bytes'] for r in c.read(path/'resource_samples.json'))
        assert peak==row['memory_peak_bytes']
        raw.append(dict(trial=spec['trial'],completed=n,offered=len(requests),failures=failures,
            timely_1000=timely1000,raw_cpu_usec=cpu,raw_cpu_usec_per_job=cpu_per_job,
            raw_timely_500_fraction=timely,memory_peak_bytes=peak,warmup_completed=warm['completed']))
        per_trial_host[spec['trial']]=host_summary([path])
    recomputed=screen.compare(rows)
    assert all(original[k]==v for k,v in recomputed.items())
    assert original['rows']==rows
    table={r['trial']:r for r in raw}
    independent_interactions=[]
    for block in screen.BLOCKS:
        a,b,cc,d=(table[f'b{block}_{arm}']['raw_cpu_usec_per_job'] for arm in 'ABCD')
        independent_interactions.append((d/b)/(cc/a)-1)
    assert all(math.isclose(x,y,abs_tol=1e-12) for x,y in zip(independent_interactions,original['block_interactions']))
    cells={}
    fields=('cpu_usec_per_completed_work','busy_capacity','busy_cpu_cores','timely_500_fraction',
        'failure_fraction','memory_peak_bytes','p99_e2e_ms')
    for arm in screen.gc.FACTORS:
        group=[r for r in rows if r['arm']==arm]
        cells[arm]={k:st.mean(r[k] for r in group) for k in fields}
        cells[arm]['queue_mean_ms']=st.mean(r['queue_ns']['mean'] for r in group)/1e6
        cells[arm]['fixed_busy_capacity']=st.mean(fixed_busy_rate(p) for p,r in zip(paths,rows) if r['arm']==arm)
    result=dict(review='2026-10-06',decision_recomputed=recomputed['decision'],raw_trials_verified=8,
        completed=sum(r['completed'] for r in raw),offered=sum(r['offered'] for r in raw),
        failures=sum(r['failures'] for r in raw),all_1000ms_met=all(r['timely_1000']==1 for r in raw),
        independent_cpu_interactions=independent_interactions,contrasts=recomputed['contrasts'],
        cells=cells,raw_checks=raw,host=host_summary(paths),per_trial_host=per_trial_host,
        idle_baseline_c=c.read(session/'environment.json')['baseline_c'],
        memory_manipulation='Functional GC cycling was qualified; performance GC cycle counts were not collected. Memory peaks differ descriptively by policy.',
        causal_cause_established=False,gc_hypothesis_ruled_out=False,
        recommendation='No large consistent GC/period CPU signal appeared. Do not automatically extend this GC screen; test a measured persistent-state intervention before a full mechanism study.',
        source_report=str(report_path.relative_to(ROOT)),report_seal=c.digest(report_path/'seal.json'),
        preparation_seal=c.digest(session/'preparation/seal.json'),reviewer_sha256=c.digest(Path(__file__)))
    out=ROOT/'analysis/runtime_io_gc_screen_review/20261006'; out.mkdir(parents=True,exist_ok=True)
    c.save(out/'report.json',result)
    print(json.dumps({k:result[k] for k in ('decision_recomputed','raw_trials_verified','completed','failures',
        'all_1000ms_met','independent_cpu_interactions','cells','host')},indent=2))
    print('Review: '+str(out/'report.json'))


if __name__=='__main__': main()
