#!/usr/bin/env python3
"""Bounded retrospective assessment of existing calibrators; no collection API."""
import argparse
import bisect
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics as st
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'diagnostic'))
import v28_common as c
import v28_model as model
import v23_model as queue

OUT = ROOT/'analysis/runtime_io_calibration_cost_assessment/20261008'
SESSION = c.PARENT/'generation-01'
RATES = (0, 15, 30, 60, 90, 120)


def read(p):
    return json.loads(Path(p).read_text())


def save(p, value):
    c.save(p, value)


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def original():
    latest = read(SESSION/'latest_analysis.json')
    directory = SESSION/latest['path']
    c.verify_seal(directory)
    if digest(directory/'seal.json') != latest['seal']:
        raise ValueError('original analysis reference changed')
    return directory, read(directory/'report.json')


def design_score(rates):
    features = [[1.0, r/120, (r/120)**2] for r in rates]
    matrix = [[sum(f[i]*f[j] for f in features) for j in range(3)] for i in range(3)]
    a,b,d = matrix[0];_,e,f = matrix[1];_,_,g = matrix[2]
    determinant = a*(e*g-f*f)-b*(b*g-f*d)+d*(b*f-e*d)
    inverse = [model.solve(matrix, [float(i==j) for i in range(3)]) for j in range(3)]
    trace = sum(inverse[j][j] for j in range(3))
    return dict(determinant=determinant, inverse_trace=trace)


def declare():
    if OUT.exists():
        raise ValueError('preserve existing assessment; do not overwrite')
    directory, report = original()
    cal = [r for r in report['trial_accounting'] if r['role']!='validation']
    mixed = sorted((r for r in cal if r['role']=='mixed'), key=lambda r:r['order'])
    specs = []
    for n in (1,2,4):
        for selected in itertools.combinations(mixed,n):
            specs.append(dict(id='busy_'+'_'.join(str(r['order']) for r in selected),
                family='busy', trials=[r['trial'] for r in selected], primary=selected==tuple(mixed[:n])))
    designs = {'spaced3':(0,60,120)}
    alternatives = {}
    for n in (3,4):
        candidates = [(rates,design_score(rates)) for rates in itertools.combinations(RATES,n)]
        alternatives[str(n)] = [dict(rates=r,**s) for r,s in candidates]
        # Deterministic lexicographic ties; outcomes, CPU usage and observed X unavailable here.
        designs['d_opt'+str(n)] = min(candidates,key=lambda z:(-round(z[1]['determinant'],12),z[0]))[0]
        designs['a_opt'+str(n)] = min(candidates,key=lambda z:(round(z[1]['inverse_trace'],10),z[0]))[0]
    designs['all6'] = RATES
    for label,rates in designs.items():
        for blocks in ((1,),(2,),(1,2)):
            selected = sorted((r for r in cal if r['role'] in ('idle','steady')
                and r['block'] in blocks and r['low_rate'] in rates),key=lambda r:r['order'])
            specs.append(dict(id='quadratic_'+label+'_b'+''.join(map(str,blocks)),family='quadratic',
                trials=[r['trial'] for r in selected], design_label=label, rates=rates, blocks=blocks,
                primary=label=='spaced3' and blocks==(1,)))
    specs.append(dict(id='historical_whole4',family='whole',trials=[r['trial'] for r in mixed],primary=False))
    original_files = ['docs/runtime_io_short_working_draft_v4.md','docs/runtime_io_short_working_draft_v5.md',
        'docs/runtime_io_paper_supporting_material_20261008.md','docs/runtime_io_v28_protocol.md',
        'docs/runtime_io_next_research_decision_20261008.md','docs/runtime_io_calibration_cost_question_20261008.md',
        'docs/runtime_io_calibration_cost_novelty_screen_20261008.md',
        'analysis/runtime_io_paper_focus_review/20261008/report.json',
        'analysis/runtime_io_calibration_novelty_screen/20261008/report.json']
    plan = dict(date='2026-10-08',status='retrospective_known_validation',variants=specs,
        candidate_rates=RATES,designs=designs,information_design_candidates=alternatives,
        selection_inputs='Declared offered rates, equal nominal trial cost, polynomial features [1,r/120,(r/120)^2]; no validation results or final capacities.',
        fitting='Unchanged V28 constrained quadratic/zero-intercept/linear-fallback candidate selection by calibration SSE only; no compulsory zero intercept.',
        primary_busy='First chronological mixed calibration; every singleton and pair reported for sensitivity, without best-outcome selection.',
        repeats='One/two/four complete mixed trials. Singletons have state/cohort qualification only; repeated range screen requires at least two trials.',
        accuracy_reference_pp=3,capacity_reference_pct=5,
        coverage='All 16 retained validation cases; zero and nonzero miss cases separately; unavailable fits answer none and are not adequate.',
        cost='Selected recorded lifecycle sums plus shared costs, actual chronological availability, warmup/measurement requests, CPU and induced lateness/queueing. No standalone collection speedup claim.',
        window_scope='Complete trial subsets only. Inventory coarse host-monitor CPU samples and clock brackets; no shortened or sub-period windows fitted.',
        verdict_rule='Stop custom calibration-cost method development if the earliest single busy trial and all singleton sensitivities meet the deadline reference, with ordinary repeat confirmation available. Otherwise require a concrete unmet capability before any custom prototype; failures do not establish novelty.',
        original_report=str((directory/'report.json').relative_to(ROOT)),
        original_analysis_seal=digest(directory/'seal.json'),
        historical_prospective_forecast_seal=digest(SESSION/'predictions/seal.json'),
        script_sha256=digest(Path(__file__)),novelty_established=False,fresh_collection_authorized=False)
    save(OUT/'design/plan.json',plan)
    save(OUT/'design/preserved_documents_sha256.json',{n:digest(ROOT/n) for n in original_files})
    c.seal(OUT/'design')
    print(json.dumps(dict(declared_variants=len(specs),designs=designs,plan=str(OUT/'design/plan.json'))))


def close(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8):
        raise ValueError(f'arithmetic differs: {a} != {b}')


def inventory_trial(row,ref):
    d = SESSION/ref['path'];c.verify_seal(d)
    if digest(d/'seal.json')!=ref['seal']:raise ValueError('trial ref mismatch')
    cfg=read(d/'config.json');obs=read(d/'observations.json');derived=read(d/'derived.json')
    start=read(d/'started.json');finish=read(d/'complete.json');server=read(d/'server_metrics.json')
    cpu=(obs['measurement_stop']['cpu_stat']['usage_usec']-obs['measurement_start']['cpu_stat']['usage_usec'])/1e6
    wall=(obs['measurement_stop']['after_ns']-obs['measurement_start']['before_ns'])/1e9
    close(cpu,row['cpu_sec']);close(wall,row['accounted_wall_sec'])
    close(row['throughput_rps'],server['completed']/wall);close(row['utilization'],cpu/wall)
    counters=read(d/'monitor.json')
    samples=[x for x in counters if 'cgroup_cpu_stat' in x and 'usage_usec' in x['cgroup_cpu_stat']]
    spans=[(x['record_after_ns']-x['record_before_ns'])/1e9 for x in samples]
    before=[x['record_before_ns'] for x in samples]
    after=[x['record_after_ns'] for x in samples]
    if cfg['role']=='idle':
        warm_offers=0;warm_late=0;warm_fail=0;measure_late=0;measure_fail=0
    else:
        client=read(d/'loadgen.json');warm=read(d/'warmup.json')
        def outcomes(x):
            timely=sum(not r['Error'] and r['StatusCode']==200 and r['EndToEndLatencyNs']<=500_000_000 for r in x['requests'])
            return x['total_scheduled']-timely,x['total_scheduled']-x['total_success']
        measure_late,measure_fail=outcomes(client);warm_late,warm_fail=outcomes(warm);warm_offers=warm['total_scheduled']
        close(row['miss_pct'],100*measure_late/row['offers'])
        if cfg['role'] in ('mixed','validation'):
            anchors=client['clock_anchors'];lo=max(a['server_ns']-a['after_ns'] for a in anchors)+client['client_test_start_ns']
            hi=min(a['server_ns']-a['before_ns'] for a in anchors)+client['client_test_start_ns']
            windows=c.design()['busy_windows_sec']['calibration' if cfg['role']=='mixed' else str(cfg['burst_period_sec'])]
            ends=sorted(e['completion_ns'] for e in server['events']);duration=sum(b-a for a,b in windows)
            def count(a,b):return sum(bisect.bisect_left(ends,b+y*1e9)-bisect.bisect_left(ends,a+x*1e9) for x,y in windows)/duration
            close(count((lo+hi)/2,(lo+hi)/2),row['busy_capacity_rps'])
            close(count(hi,lo),row['busy_capacity_bounds_rps'][0]);close(count(lo,hi),row['busy_capacity_bounds_rps'][1])
    lifecycle=(finish['finished_monotonic_ns']-start['monotonic_ns'])/1e9
    settle=read(d/'settling.json')['samples'][-1]['elapsed_sec']
    accounted_to_finish=(finish['finished_monotonic_ns']-obs['measurement_stop']['after_ns'])/1e9
    settle_to_start=(obs['measurement_start']['before_ns']-start['monotonic_ns'])/1e9-settle
    return dict(trial=row['trial'],role=row['role'],block=row['block'],order=row['order'],low_rate=row['low_rate'],
        path=str(d.relative_to(ROOT)),started_ns=start['monotonic_ns'],finished_ns=finish['finished_monotonic_ns'],
        lifecycle_sec=lifecycle,settling_sec=settle,post_settle_to_measurement_start_sec=settle_to_start,
        accounted_measurement_wall_sec=wall,post_measurement_accounting_sec=accounted_to_finish,
        scheduled_warmup_sec=20,scheduled_measurement_sec=cfg['duration_sec'],
        measurement_offers=row['offers'],warmup_offers=warm_offers,measurement_cpu_sec=cpu,
        cpu_startup_to_final_sec=(obs['final']['cpu_stat']['usage_usec']-obs['startup']['cpu_stat']['usage_usec'])/1e6,
        measurement_not_timely_500=measure_late,warmup_not_timely_500=warm_late,
        measurement_failures=measure_fail,warmup_failures=warm_fail,queue_peak=row['queue_peak'],
        queued_request_seconds=sum(e['queue_wait_ns'] for e in server['events'])/1e9,
        state_eligible=row['state_eligible'],all_successful=row['all_successful'],
        monitor_cpu_sample_count=len(samples),monitor_cpu_bracket_max_sec=max(spans,default=0),
        monitor_cpu_interval_max_sec=max(((y-x)/1e9 for x,y in zip(before,before[1:])),default=0),
        monitor_covers_measurement_endpoints=bool(samples and before[0]<=obs['measurement_start']['before_ns'] and after[-1]>=obs['measurement_stop']['after_ns']),
        native_counter_samples_available=(d/'counter.json').exists(),
        technical_cleanup_pass=not read(d/'cleanup.json')['errors'])


def costs(rows,inventory,collection_start,common):
    values=[inventory[r['trial']] for r in rows]
    fields=('lifecycle_sec','settling_sec','scheduled_warmup_sec','scheduled_measurement_sec','accounted_measurement_wall_sec',
        'measurement_offers','warmup_offers','measurement_cpu_sec','cpu_startup_to_final_sec',
        'measurement_not_timely_500','warmup_not_timely_500','measurement_failures','warmup_failures','queued_request_seconds')
    result={k:sum(v[k] for v in values) for k in fields}
    result.update(trials=len(values),queue_peak=max(v['queue_peak'] for v in values),
        actual_original_collection_elapsed_until_available_sec=max(v['finished_ns'] for v in values)/1e9-collection_start,
        initial_shared_collection_overhead_sec=common,
        lifecycle_sum_plus_shared_initial_overhead_sec=result['lifecycle_sec']+common,
        interpretation='Sum of recorded selected trial lifecycles, not measured standalone acquisition time. Original chronological elapsed includes other trials. Shared functional preparation and offline tuning are reported separately; earlier research acquisition is not free.')
    return result


def independent_fifo(offsets,capacity):
    ends=[];head=0;last=0.0;misses=0
    for ns in offsets:
        arrival=ns/1e9
        while head<len(ends) and ends[head]<=arrival:head+=1
        if len(ends)-head>=129:misses+=1;continue
        last=max(arrival,last)+1/capacity;ends.append(last);misses+=last-arrival>.5
    return 100*misses/len(offsets)


def assess():
    c.verify_seal(OUT/'design');plan=read(OUT/'design/plan.json')
    if digest(Path(__file__))!=plan['script_sha256']:raise ValueError('declared script changed')
    if (OUT/'report.json').exists():raise ValueError('preserve existing result')
    directory,original_report=original();rows=original_report['trial_accounting']
    cal={r['trial']:r for r in rows if r['role']!='validation'}
    validation=sorted((r for r in rows if r['role']=='validation'),key=lambda r:r['order'])
    receipt=read(SESSION/'collection_receipt.json');collection_start=receipt['started_monotonic']
    inventory={r['trial']:inventory_trial(r,original_report['trial_refs'][r['trial']]) for r in rows}
    common=min(inventory[t]['started_ns'] for t in cal)/1e9-collection_start
    save(OUT/'inventory.json',dict(trials=inventory,initial_shared_collection_overhead_sec=common,
        shared_initial_settling_sec=read(SESSION/'initial-settling.json')['samples'][-1]['elapsed_sec'],
        shared_functional_trial_lifecycle_sec=sum((read(p/'complete.json')['finished_monotonic_ns']-read(p/'started.json')['monotonic_ns'])/1e9 for p in (SESSION/'preparation/functional').iterdir() if (p/'started.json').exists()),
        technical_failures=original_report['technical_failures'],
        cost_limits='Common initial collection overhead covers original host qualification, not full prior research/asset acquisition. Functional-trial sum excludes unmeasured preparation overhead. Reordered smaller procedures were not run.'))
    variants=[]
    configs=c.validation_configs();vectors={x['trial']:c.schedule(x) for x in configs}
    for spec in plan['variants']:
        selected=[cal[t] for t in spec['trials']]
        qualified=all(r['state_eligible'] and r['all_successful'] for r in selected)
        started=time.perf_counter()
        if not qualified:fit=dict(status='unavailable',reason='state or cohort qualification failed')
        elif spec['family']=='busy':
            capacities=[r['busy_capacity_rps'] for r in selected]
            fit=dict(status='available',capacity_rps=st.mean(capacities),
                capacity_bounds_rps=[st.mean(r['busy_capacity_bounds_rps'][i] for r in selected) for i in (0,1)])
        elif spec['family']=='whole':fit=dict(status='available',capacity_rps=.5/st.mean(r['whole_cpu_sec_per_job'] for r in selected))
        else:
            try:fit=model.regression([(r['throughput_rps'],r['utilization']) for r in selected],.5,True)
            except ValueError as e:fit=dict(status='unavailable',reason=str(e))
        fitting_sec=time.perf_counter()-started
        repeat_range=((max(r['busy_capacity_rps'] for r in selected)/min(r['busy_capacity_rps'] for r in selected)-1)*100 if spec['family']=='busy' else None)
        result=dict(spec,fit=fit,calibration_state_cohort_pass=qualified,
            busy_repeatability_status=('not_tested_single_trial' if len(selected)==1 else 'pass' if repeat_range<=5 else 'fail') if spec['family']=='busy' else 'not_applicable',
            busy_repeatability_range_pct=repeat_range,estimator_fitting_wall_sec=fitting_sec,
            costs=costs(selected,inventory,collection_start,common),predictions={})
        if fit['status']=='available':
            for cfg in configs:
                _,summary=queue.simulate(vectors[cfg['trial']],fit['capacity_rps'],cfg['burst_period_sec'])
                close(summary['miss_pct'],independent_fifo(vectors[cfg['trial']],fit['capacity_rps']))
                result['predictions'][cfg['trial']]={k:summary[k] for k in ('offers','capacity_rps','miss_pct','rejections','queue_peak')}
        variants.append(result)
    # Separate sealed subset forecasts precede scoring here, but the retained outcomes were already known.
    save(OUT/'subset_forecasts/predictions.json',variants);c.seal(OUT/'subset_forecasts')
    for result in variants:
        errors=[]
        for r in validation:
            predicted=result['predictions'].get(r['trial'])
            errors.append(dict(trial=r['trial'],block=r['block'],period_sec=r['period_sec'],observed_miss_pct=r['miss_pct'],
                predicted_miss_pct=None if predicted is None else predicted['miss_pct'],
                deadline_error_pp=None if predicted is None else abs(predicted['miss_pct']-r['miss_pct']),
                capacity_error_pct=None if predicted is None else max(abs(result['fit']['capacity_rps']/v-1)*100 for v in r['busy_capacity_bounds_rps'])))
        answered=[e for e in errors if e['deadline_error_pp'] is not None]
        nonzero=[e for e in answered if e['observed_miss_pct']>0]
        zero=[e for e in answered if e['observed_miss_pct']==0]
        result['errors']=errors
        result['metrics']=dict(answered_cases=len(answered),declared_cases=len(errors),coverage=len(answered)/len(errors),
            refused_cases=len(errors)-len(answered),deadline_passes=sum(e['deadline_error_pp']<=3 for e in answered),
            capacity_passes=sum(e['capacity_error_pct']<=5 for e in answered),
            deadline_mae_pp=st.mean(e['deadline_error_pp'] for e in answered) if answered else None,
            deadline_max_error_pp=max((e['deadline_error_pp'] for e in answered),default=None),
            capacity_max_error_pct=max((e['capacity_error_pct'] for e in answered),default=None),
            nonzero_cases=len(nonzero),nonzero_mae_pp=st.mean(e['deadline_error_pp'] for e in nonzero) if nonzero else None,
            zero_cases=len(zero),zero_mae_pp=st.mean(e['deadline_error_pp'] for e in zero) if zero else None,
            per_block_mae_pp={str(b):st.mean(e['deadline_error_pp'] for e in answered if e['block']==b) for b in range(1,5)} if answered else {},
            retrospective_deadline_adequate=len(answered)==len(errors) and all(e['deadline_error_pp']<=3 for e in answered))
    # Reproduce sealed full-budget values and forecasts before interpreting subsets.
    checks=[]
    for identifier,method in [('busy_5_6_11_12','busy'),('quadratic_all6_b12','quadratic'),('historical_whole4','whole')]:
        value=next(v for v in variants if v['id']==identifier)
        close(value['fit']['capacity_rps'],original_report['calibration']['methods'][method]['capacity_rps'])
        close(value['metrics']['deadline_mae_pp'],original_report['result']['methods'][method]['deadline_mae_pp'])
        checks.append('reproduced full '+method+' capacity and deadline MAE')
    singleton=[v for v in variants if v['family']=='busy' and len(v['trials'])==1]
    stop=all(v['metrics']['retrospective_deadline_adequate'] for v in singleton)
    report=dict(date='2026-10-08',analysis_type='retrospective_known_validation',original_analysis_seal=plan['original_analysis_seal'],
        plan_seal=digest(OUT/'design/seal.json'),subset_forecast_seal=digest(OUT/'subset_forecasts/seal.json'),
        variants=variants,checks=checks,decision='stop_custom_calibration_cost_route' if stop else 'gap_unestablished_requires_specific_capability',
        decision_reason='All four single busy-trial estimates meet every retained deadline accuracy reference; ordinary direct calibration already supplies the proposed forecasting capability in this case.' if stop else 'Simple-baseline failures alone do not establish a novel capability.',
        novelty_established=False,prospective_status=False,fresh_collection=False,
        limits=['One host/service/quota; retained outcomes already known.','Single-trial state qualification does not establish repeatability or future coverage.',
            'Selected lifecycle sums are observed component costs, not measured standalone speedups.','No validated uncertainty/stopping guarantee or published-algorithm reproduction.',
            'Coarse host-monitor CPU samples exist; shortening trials and quota-period timing require separate clock/state assessment.',
            'Busy calibration deliberately induces queueing and missed deadlines; accuracy is not adequacy for a no-disruption requirement.'])
    save(OUT/'report.json',report)
    print(json.dumps(dict(decision=report['decision'],variants=len(variants),single_busy=[dict(id=v['id'],capacity=v['fit']['capacity_rps'],**v['metrics'],lifecycle_sec=v['costs']['lifecycle_sec']) for v in singleton]),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('declare','assess'))
    args=parser.parse_args();declare() if args.mode=='declare' else assess()
