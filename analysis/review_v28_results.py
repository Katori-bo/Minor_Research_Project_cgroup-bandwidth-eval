"""Read-only V28 result audit with separate raw arithmetic and FIFO recurrence."""
import bisect
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
import v28_verify as verifier


def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9):
        raise ValueError(f'independent arithmetic differs: {a} vs {b}')


def fifo_misses(offsets,capacity):
    completions=[];head=0;last=0.0;misses=0
    for stamp in offsets:
        arrival=stamp/1e9
        while head<len(completions) and completions[head]<=arrival:head+=1
        if len(completions)-head>=129:misses+=1;continue
        last=max(arrival,last)+1/capacity;completions.append(last)
        misses+=last-arrival>.5
    return 100*misses/len(offsets)


def main():
    session=c.PARENT/'generation-01';verified=verifier.verify_completion(session)
    latest=c.read(session/'latest_analysis.json');original=c.resolve(session,latest['path'])
    report=c.read(original/'report.json');design=c.design();records={};checks=[]
    measurement=warmup=0;monitor_counts=[];all_groups_absent=True
    for cfg in c.matrix():
        ref=report['trial_refs'][cfg['trial']];d=c.resolve(session,ref['path'])
        obs=c.read(d/'observations.json');start,stop=obs['measurement_start'],obs['measurement_stop']
        cpu=(stop['cpu_stat']['usage_usec']-start['cpu_stat']['usage_usec'])/1e6
        wall=(stop['after_ns']-start['before_ns'])/1e9
        server=c.read(d/'server_metrics.json');row=next(x for x in report['trial_accounting'] if x['trial']==cfg['trial'])
        close(cpu,row['cpu_sec']);close(wall,row['accounted_wall_sec'])
        cleanup=c.read(d/'cleanup.json')
        if cleanup['errors'] or cleanup['watchdog_intervened'] or not cleanup['container_removed'] or not cleanup['cgroup_removed']:
            raise ValueError('cleanup failure')
        all_groups_absent &= not Path(c.read(d/'initial.json')['cgroup']).exists()
        if any((d/name).exists() for name in ('counter.json','counter.raw.json','counter_process.json')):
            raise ValueError('native data in sampler-off study')
        monitor_counts.append(len(c.read(d/'monitor.json')))
        records[cfg['trial']]=dict(config=cfg,cpu=cpu,wall=wall,completed=server['completed'],utilization=cpu/wall,throughput=server['completed']/wall)
        if cfg['role']=='idle':continue
        client=c.read(d/'loadgen.json');warm=c.read(d/'warmup.json');n=client['total_scheduled']
        good=sum(not x['Error'] and x['StatusCode']==200 for x in client['requests'])
        timely=sum(not x['Error'] and x['StatusCode']==200 and x['EndToEndLatencyNs']<=500_000_000 for x in client['requests'])
        if good!=n or warm['total_success']!=warm['total_scheduled']:raise ValueError('unsuccessful scientific offer')
        measurement+=n;warmup+=warm['total_scheduled'];close(100*(n-timely)/n,row['miss_pct'])
        records[cfg['trial']]['miss_pct']=100*(n-timely)/n
        if cfg['role'] not in ('mixed','validation'):continue
        anchors=client['clock_anchors'];lo=max(a['server_ns']-a['after_ns'] for a in anchors)+client['client_test_start_ns']
        hi=min(a['server_ns']-a['before_ns'] for a in anchors)+client['client_test_start_ns']
        windows=design['busy_windows_sec']['calibration' if cfg['role']=='mixed' else str(cfg['burst_period_sec'])]
        ends=sorted(e['completion_ns'] for e in server['events']);duration=sum(b-a for a,b in windows)
        def count(origin_a,origin_b):
            return sum(bisect.bisect_left(ends,origin_b+b*1e9)-bisect.bisect_left(ends,origin_a+a*1e9) for a,b in windows)/duration
        point=count((lo+hi)/2,(lo+hi)/2);lower=count(hi,lo);upper=count(lo,hi)
        close(point,row['busy_capacity_rps']);close(lower,row['busy_capacity_bounds_rps'][0]);close(upper,row['busy_capacity_bounds_rps'][1])
        records[cfg['trial']].update(capacity=point,capacity_bounds=[lower,upper])
    checks+=['all32 raw CPU endpoints and denominators','all offered500ms outcomes','fixed-window completion counts with raw client clock intersections',
             'owned cleanup receipts and sampler-off absence']
    calibration=report['calibration'];mixed=[r for r in records.values() if r['config']['role']=='mixed']
    idle=[r for r in records.values() if r['config']['role']=='idle'];background=st.mean(r['utilization'] for r in idle)
    capacities=dict(whole=.5/st.mean(r['cpu']/r['completed'] for r in mixed),busy=st.mean(r['capacity'] for r in mixed),
        idle_corrected=(.5-background)/st.mean((r['cpu']-background*r['wall'])/r['completed'] for r in mixed))
    fit=[r for r in records.values() if r['config']['role'] in ('idle','steady')]
    x=[r['throughput'] for r in fit];y=[r['utilization'] for r in fit];mx,my=st.mean(x),st.mean(y)
    demand=sum((a-mx)*(b-my) for a,b in zip(x,y))/sum((a-mx)**2 for a in x)
    intercept=my-demand*mx;close(demand,calibration['methods']['regression']['demand_sec']);close(intercept,calibration['methods']['regression']['intercept'])
    capacities['regression']=(.5-intercept)/demand
    # The sealed quadratic selected the zero-intercept candidate. Recompute its
    # two normal equations directly from raw U and X, without the fit code.
    s2,s3,s4=(sum(a**k for a in x) for k in (2,3,4));xy=sum(a*b for a,b in zip(x,y));x2y=sum(a*a*b for a,b in zip(x,y))
    determinant=s2*s4-s3*s3;demand_q=(xy*s4-x2y*s3)/determinant;curvature=(s2*x2y-s3*xy)/determinant
    close(calibration['methods']['quadratic']['intercept'],0);close(demand_q,calibration['methods']['quadratic']['demand_sec']);close(curvature,calibration['methods']['quadratic']['quadratic_sec2'])
    capacities['quadratic']=(-demand_q+math.sqrt(demand_q*demand_q+2*curvature))/(2*curvature)
    for name,value in capacities.items():close(value,calibration['methods'][name]['capacity_rps'])
    close(background,calibration['idle_cpu_rate']);checks.append('all five calibration estimates from raw CPU/counts, analytic linear fit and selected quadratic equations')
    errors={};summary={}
    for name,capacity in capacities.items():
        errors[name]=[]
        for cfg in c.validation_configs():
            observed=records[cfg['trial']];predicted=fifo_misses(c.schedule(cfg),capacity)
            saved=next(e for e in verified['methods'][name]['errors'] if e['trial']==cfg['trial'])
            close(predicted,saved['predicted_miss_pct']);error=abs(predicted-observed['miss_pct']);close(error,saved['deadline_error_pp'])
            capacity_error=max(abs(capacity/a-1)*100 for a in observed['capacity_bounds']);close(capacity_error,saved['capacity_error_pct'])
            errors[name].append(dict(trial=cfg['trial'],block=cfg['block'],deadline_error_pp=error,capacity_error_pct=capacity_error))
        summary[name]=dict(capacity_rps=capacity,deadline_mae_pp=st.mean(e['deadline_error_pp'] for e in errors[name]),
            maximum_deadline_error_pp=max(e['deadline_error_pp'] for e in errors[name]),
            maximum_capacity_error_pct=max(e['capacity_error_pct'] for e in errors[name]),
            deadline_pass_count=sum(e['deadline_error_pp']<=3 for e in errors[name]),
            capacity_pass_count=sum(e['capacity_error_pct']<=5 for e in errors[name]))
        close(summary[name]['deadline_mae_pp'],verified['methods'][name]['deadline_mae_pp'])
    advantages={};busy={e['trial']:e for e in errors['busy']}
    for name in ('whole','idle_corrected','regression','quadratic'):
        blocks=[st.mean(e['deadline_error_pp']-busy[e['trial']]['deadline_error_pp'] for e in errors[name] if e['block']==block) for block in range(1,5)]
        mean=st.mean(blocks);half=design['analysis']['t_critical_95_df3']*st.stdev(blocks)/2;interval=[mean-half,mean+half]
        saved=verified['advantages'][name];close(mean,saved['midpoint_mean'])
        for a,b in zip(interval,saved['model_based_95_interval']):close(a,b)
        advantages[name]=dict(block_improvements_pp=blocks,mean_improvement_pp=mean,model_based_95_interval=interval,
            frozen_advantage_pass=all(b>0 for b in blocks) and interval[0]>=1)
    checks+=['separate FIFO recurrence for every method/schedule','all capacity and deadline errors','four block paired t intervals and frozen1pp screen']
    receipt=c.read(session/'collection_receipt.json');freeze=c.read(session/'predictions/manifest.json')['frozen_monotonic_ns']
    starts=[c.read(c.resolve(session,ref['path'])/'started.json')['monotonic_ns'] for key,ref in report['trial_refs'].items() if key.startswith('val_')]
    if min(starts)<=freeze:raise ValueError('forecast freeze ordering failed')
    out=ROOT/'analysis/runtime_io_v28_result_review/20261008'
    if out.exists():raise ValueError('preserve existing result audit')
    c.save(out/'report.json',dict(decision='verified_predictive_advantage_inconclusive',original_report=str(original/'report.json'),
        original_analysis_seal=c.digest(original/'seal.json'),full_completion_replay_passed=True,independent_checks=checks,
        methods=summary,advantages=advantages,idle_cpu_rate=background,measurement_offers=measurement,warmup_offers=warmup,
        accepted_calibration_trials=16,accepted_validation_trials=16,technical_failures=report['technical_failures'],
        collection_minutes=(receipt['collection_finished_monotonic']-receipt['started_monotonic'])/60,
        prediction_seal_precedes_first_validation_sec=(min(starts)-freeze)/1e9,host_monitor_record_counts=monitor_counts,
        all_recorded_cgroups_absent=all_groups_absent,novelty_established=False))
    c.seal(out);c.verify_seal(out)
    print(json.dumps(c.read(out/'report.json'),indent=2))


if __name__=='__main__':main()
