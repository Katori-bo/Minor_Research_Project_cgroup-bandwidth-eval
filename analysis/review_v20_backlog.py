#!/usr/bin/env python3
"""Offline V20 backlog reconstruction and block-held-out queue predictions.

Never invokes the collector, Docker, or a new performance workload.
Run with the repository venv Python; original evidence is read only.
"""
import argparse
import bisect
import collections
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'diagnostic'), str(ROOT / 'scripts')]
import execution_delay_analysis as original


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dist(v):
    values = list(v)
    result = original.distribution(values)
    result['p10'] = original.percentile(values, .1)
    return result


def write_csv(p, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, keys)
        w.writeheader()
        w.writerows(rows)


def series(admissions, starts):
    changes = collections.Counter(admissions)
    changes.subtract(starts)
    count = 0
    times, values = [], []
    for t, step in sorted(changes.items()):
        count += step
        assert count >= 0
        times.append(t)
        values.append(count)
    assert count == 0
    return times, values


def at(trace, t):
    i = bisect.bisect_right(trace[0], t) - 1
    return trace[1][i] if i >= 0 else 0


def peak(trace, a, b):
    return max([at(trace, a)] + trace[1][bisect.bisect_right(trace[0], a):bisect.bisect_left(trace[0], b)])


def recovery(trace, boundary):
    # All observed cycles fall below five queued jobs well before boundary+5.
    # Includes final drain. Five jobs avoids counting ordinary sub-ms enqueue noise.
    lo = bisect.bisect_left(trace[0], boundary)
    hi = bisect.bisect_left(trace[0], boundary + 5)
    above = [i for i in range(max(0, lo - 1), hi)
             if trace[1][i] > 5 and trace[0][i] < boundary + 5]
    if not above:
        return 0.0
    last = above[-1]
    assert last + 1 < len(trace[0])
    return max(0.0, trace[0][last + 1] - boundary)


def simulate(offsets, mu, limit=128):
    """D/D/1/K FIFO, initially empty; constant effective wall-time service.

    One active job plus 128 queued jobs. Offers only; no held-out admission,
    queue, response, frequency or throttle records enter the prediction.
    Completion is used as the approximate response time, an explicit omission.
    """
    end = 0.0
    pending = collections.deque()
    rows = []
    for rid, t in enumerate(offsets):
        while pending and pending[0] <= t:
            pending.popleft()
        if len(pending) >= limit + 1:
            rows.append(dict(id=rid, rejected=True, start=None, completion=None,
                             latency=None, timely=False))
            continue
        start = max(t, end)
        end = start + 1 / mu
        pending.append(end)
        rows.append(dict(id=rid, rejected=False, start=start, completion=end,
                         latency=end-t, timely=end-t <= .5))
    q = series([offsets[r['id']] for r in rows if not r['rejected']],
               [r['start'] for r in rows if not r['rejected']])
    return rows, q


def load_trials(base):
    trials, source_hashes = [], {}
    for path in sorted(base.glob('trials/*/attempt-*/config.json')):
        p = path.parent
        # Verify every sealed trial input, including the derived records we compare.
        seal = read(p / 'seal.json')['files_sha256']
        for name, expected in seal.items():
            actual = sha(p / name)
            if actual != expected:
                raise ValueError(f'sealed evidence changed: {p / name}')
        source_hashes[str(p.relative_to(ROOT) / 'seal.json')] = sha(p / 'seal.json')
        config, client, server, obs, derived = (read(p / name) for name in
            ('config.json', 'loadgen.json', 'server_metrics.json', 'observations.json', 'derived.json'))
        rows, mapping, logical = original.join(client, server, config)
        assert rows == derived['requests'] and mapping == derived['clocks']
        assert logical == derived['summary']['logical_backlogs']
        clock_mid = (mapping['server_minus_client_lower_ns'] + mapping['server_minus_client_upper_ns']) / 2
        origin = mapping['client_test_start_ns'] + clock_mid
        stamps = lambda key, records: sorted((r[key] - origin) / 1e9 for r in records)
        jobs, entries = server['events'], server['entry_events']
        admissions = stamps('admission_ns', jobs)
        starts, completions = stamps('worker_start_ns', jobs), stamps('completion_ns', jobs)
        queue = series(admissions, starts)
        # Counting is done on the server clock; origin midpoint only labels burst time.
        assert max(queue[1]) == logical['admitted_not_started']['peak']
        area = sum(v*(b-a) for a,b,v in zip(queue[0],queue[0][1:],queue[1]))
        assert math.isclose(area,logical['admitted_not_started']['request_seconds'],abs_tol=1e-7)
        assert [j['id'] for j in sorted(jobs,key=lambda j:j['admission_ns'])] == [
            j['id'] for j in sorted(jobs,key=lambda j:j['worker_start_ns'])]
        delta = {k: obs['measurement_stop']['cpu_stat'][k] - obs['measurement_start']['cpu_stat'][k]
                 for k in obs['measurement_stop']['cpu_stat']}
        tr = dict(config=config, path=p, rows=rows, server=server, client=client,
                  mapping=mapping, origin=origin, summary=derived['summary'], delta=delta,
                  offers=[r['scheduled_offset_ns']/1e9 for r in rows], queue=queue,
                  entries=stamps('entry_ns', entries), admissions=admissions,
                  starts=starts, completions=completions)
        # Predefined clock-relative busy window, fixed without looking at miss totals.
        tr['busy_completions'] = sum(0 <= t < 60 and 6.5 <= t % 10 < 9.5 for t in completions)
        tr['busy_rate'] = tr['busy_completions'] / 18
        trials.append(tr)
    assert len(trials) == 16
    assert {(t['config']['block'], t['config']['arm']) for t in trials} == {
        (b, a) for b in range(1, 5) for a in 'ABCD'}
    return trials, source_hashes


def audit_host(tr):
    p = tr['path']
    obs, mon, initial = read(p/'observations.json'), read(p/'monitor.json'), read(p/'initial.json')
    lo, hi = (obs[k]['cpu_stat']['usage_usec'] for k in ('measurement_start', 'measurement_stop'))
    # Sample selection by cumulative usage avoids fabricating an unsaved real/monotonic clock bridge.
    samples = [r for r in mon if lo <= r['cgroup_cpu_stat']['usage_usec'] <= hi]
    assert samples
    pid = initial['pid']
    last_core_freq = []
    last_cores = collections.Counter()
    for r in samples:
        proc = next((q for q in r['process_cpu_deltas'] if q['pid'] == pid), None)
        if proc and proc['cpu_delta_ticks'] > 0:
            core = f"cpu{proc['last_cpu']}"
            last_cores[core] += 1
            if core in r['freqs_mhz']:
                last_core_freq.append(r['freqs_mhz'][core])
    return dict(samples=len(samples),
        frequency_cpu2_mhz=dist(r['freqs_mhz']['cpu2'] for r in samples),
        frequency_cpu4_mhz=dist(r['freqs_mhz']['cpu4'] for r in samples),
        frequency_last_server_core_mhz=dist(last_core_freq), last_core_samples=dict(last_cores),
        temperature_k10_c=dist(r['temps_c']['k10temp:temp1_input'] for r in samples),
        power_settings_constant=all(r['power_settings'] == samples[0]['power_settings'] for r in samples),
        power_settings=samples[0]['power_settings'],
        limitation='~1 s snapshots, two allowed cores, process last-CPU is a location sample; '
                   'not active-worker frequency or CPU cycles. Measurement membership is by usage counter range.')


def summarize_trial(tr):
    c, rr = tr['config'], tr['rows']
    categories = collections.Counter()
    miss_stages = collections.defaultdict(list)
    for r in rr:
        if not r['success']:
            categories['unsuccessful_' + r['outcome']] += 1
            continue
        if r['timely_500']:
            categories['timely'] += 1
            continue
        intervals = [
            ('entry', r['scheduled_to_entry_lower_ns'], r['scheduled_to_entry_upper_ns']),
            ('admission', r['scheduled_to_entry_lower_ns']+r['pre_admission_ns'],
             r['scheduled_to_entry_upper_ns']+r['pre_admission_ns']),
            ('worker_start', r['completion_after_offered_lower_ns']-r['processing_wall_ns'],
             r['completion_after_offered_upper_ns']-r['processing_wall_ns']),
            ('completion', r['completion_after_offered_lower_ns'], r['completion_after_offered_upper_ns']),
            ('handler_resume', r['resume_after_offered_lower_ns'], r['resume_after_offered_upper_ns'])]
        prev_upper = 0
        category = 'after_handler_resume'
        for stage, lower, upper in intervals:
            if lower > 500_000_000:
                category = 'crossed_during_' + stage if prev_upper <= 500_000_000 else 'boundary_ambiguous_' + stage
                break
            if upper > 500_000_000:
                category = 'boundary_ambiguous_' + stage
                break
            prev_upper = upper
        categories[category] += 1
        for k in ('scheduled_to_entry_lower_ns', 'scheduled_to_entry_upper_ns', 'pre_admission_ns',
                  'queue_ns', 'processing_wall_ns', 'completion_to_resume_ns'):
            miss_stages[k].append(r[k]/1e6)
    stages = {k: dist(r[k]/1e6 for r in rr if r[k] is not None) for k in (
        'scheduled_to_entry_lower_ns', 'scheduled_to_entry_upper_ns', 'pre_admission_ns',
        'queue_ns', 'processing_wall_ns', 'completion_to_resume_ns')}
    low = [r['processing_wall_ns']/1e6 for r in rr if r['worker_observed'] and r['burst_second'] in (2,3,4)]
    high = [r['processing_wall_ns']/1e6 for r in rr if r['worker_observed'] and r['burst_second'] in (6,7,8,9)]
    n = tr['server']['completed']
    return dict(trial=c['trial'], block=c['block'], arm=c['arm'], period_us=c['period_us'],
        offers=len(rr), rejections=tr['server']['rejected'],
        misses=sum(not r['timely_500'] for r in rr),
        successful_misses=sum(r['success'] and not r['timely_500'] for r in rr),
        deadline_stage_counts=dict(categories), stages_ms=stages,
        successful_miss_stages_ms={k:dist(v) for k,v in miss_stages.items()},
        busy_service_rps=tr['busy_rate'], peak_logical_queue=max(tr['queue'][1]),
        cpu_usec_per_job={k: tr['delta'][k]/n for k in ('usage_usec','user_usec','system_usec')},
        aggregate_cpu_counters=tr['delta'], low_phase_processing_wall_ms=dist(low),
        high_phase_processing_wall_ms=dist(high),
        high_phase_sub5ms_processing_wall_ms=dist(x for x in high if x < 5), host=audit_host(tr))


def evaluate(tr, model, mu, fold):
    pred, q = simulate(tr['offers'], mu)
    rr, c = tr['rows'], tr['config']
    n = len(rr)
    observed_miss = sum(not r['timely_500'] for r in rr)/n
    predicted_miss = sum(not r['timely'] for r in pred)/n
    residuals = {}
    for name in ('worker_start','completion','e2e'):
        errors = []
        for r, sim in zip(rr, pred):
            if not r['success'] or sim['rejected']:
                continue
            if name == 'worker_start':
                actual = (r['completion_after_offered_lower_ns'] + r['completion_after_offered_upper_ns'])/2-r['processing_wall_ns']
                estimate = (sim['start']-tr['offers'][r['id']])*1e9
            elif name == 'completion':
                actual = (r['completion_after_offered_lower_ns']+r['completion_after_offered_upper_ns'])/2
                estimate = sim['latency']*1e9
            else:
                actual, estimate = r['e2e_ns'], sim['latency']*1e9
            errors.append((estimate-actual)/1e6)
        residuals[name] = dict(n=len(errors), bias_ms=st.mean(errors),
                              mae_ms=st.mean(abs(x) for x in errors),
                              p90_absolute_error_ms=original.percentile([abs(x) for x in errors],.9))
    rec_actual = [recovery(tr['queue'], k*10) for k in range(1,7)]
    rec_pred = [recovery(q, k*10) for k in range(1,7)]
    grid = [i/10 for i in range(601)]
    qe = [at(q,t)-at(tr['queue'],t) for t in grid]
    actual_p99 = original.percentile([r['e2e_ns']/1e6 for r in rr if r['success']],.99)
    predicted_p99 = original.percentile([r['latency']*1000 for r in pred if not r['rejected']],.99)
    rejection_fraction = sum(r['rejected'] for r in pred)/n
    row = dict(trial=c['trial'], block=c['block'], arm=c['arm'], model=model, fold=fold,
        capacity_rps=mu, observed_miss_pct=observed_miss*100, predicted_miss_pct=predicted_miss*100,
        miss_error_pp=(predicted_miss-observed_miss)*100,
        observed_1000ms_miss_pct=100*sum(not r['timely_1000'] for r in rr)/n,
        predicted_1000ms_miss_pct=100*sum(r['rejected'] or r['latency']>1 for r in pred)/n,
        observed_successes_after1000ms=sum(r['success'] and not r['timely_1000'] for r in rr),
        predicted_successes_after1000ms=sum(not r['rejected'] and r['latency']>1 for r in pred),
        observed_rejections=tr['server']['rejected'], predicted_rejections=sum(r['rejected'] for r in pred),
        rejection_error_pp=(rejection_fraction-tr['server']['rejected']/n)*100,
        observed_peak=max(tr['queue'][1]), predicted_peak=max(q[1]),
        queue_grid_mae_jobs=st.mean(abs(x) for x in qe),
        queue_peak_error_jobs=max(q[1])-max(tr['queue'][1]),
        observed_recovery_mean_sec=st.mean(rec_actual), predicted_recovery_mean_sec=st.mean(rec_pred),
        recovery_error_sec=st.mean(rec_pred)-st.mean(rec_actual),
        recovery_cycle_mae_sec=st.mean(abs(x-y) for x,y in zip(rec_actual,rec_pred)),
        observed_p99_ms=actual_p99, predicted_p99_ms=predicted_p99,
        p99_error_ms=predicted_p99-actual_p99, residuals=residuals,
        false_predicted_misses=sum(not p['timely'] and r['timely_500'] for r,p in zip(rr,pred)),
        unpredicted_misses=sum(p['timely'] and not r['timely_500'] for r,p in zip(rr,pred)),
        prediction_overlap_fraction=sum(not p['timely'] and not r['timely_500'] for r,p in zip(rr,pred)) /
            max(1,sum(not r['timely_500'] for r in rr)))
    # Post-hoc diagnostic tolerances, never a frozen V20 decision rule.
    row['descriptive_macro_checks'] = dict(miss_within_3pp=abs(row['miss_error_pp'])<=3,
        peak_within_10jobs=abs(row['queue_peak_error_jobs'])<=10,
        recovery_within_250ms=abs(row['recovery_error_sec'])<=.25,
        p99_within_75ms=abs(row['p99_error_ms'])<=75,
        rejection_within_half_pp=abs(row['rejection_error_pp'])<=.5)
    return row, pred, q


def fit(trials, blocks, model, arm):
    train = [t for t in trials if t['config']['block'] in blocks]
    period = 100000 if arm in 'AB' else 20000
    if model == 'nominal_cpu':
        costs = [t['delta']['usage_usec']/t['server']['completed'] for t in train if t['config']['arm']==arm]
        return 500000/st.mean(costs)
    if model == 'common_period_capacity':
        train = [t for t in train if t['config']['period_us']==period]
    elif model == 'arm_capacity_sensitivity':
        train = [t for t in train if t['config']['arm']==arm]
    return sum(t['busy_completions'] for t in train)/(18*len(train))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=ROOT/'analysis/runtime_io_v20_execution_delay/generation-03')
    parser.add_argument('--output', type=Path, default=ROOT/'analysis/runtime_io_v20_backlog_review/20261005')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    trials, hashes = load_trials(args.input.resolve())
    summaries = [summarize_trial(t) for t in trials]
    evaluations, predictions, traces = [], [], {}
    cycles, timeline, stages = [], [], []
    for tr in trials:
        c, rr = tr['config'], tr['rows']
        for cyc in range(6):
            cycle_rows = [r for r in rr if r['cycle']==cyc]
            cycles.append(dict(trial=c['trial'], block=c['block'], arm=c['arm'], cycle=cyc,
                offered=len(cycle_rows), misses=sum(not r['timely_500'] for r in cycle_rows),
                rejected=sum(r['outcome']=='rejected' for r in cycle_rows),
                queue_before_high=at(tr['queue'],cyc*10+5),
                high_phase_peak=peak(tr['queue'],cyc*10+5,cyc*10+10),
                queue_at_switch=at(tr['queue'],cyc*10+10),
                recovery_below6_jobs_sec=recovery(tr['queue'],cyc*10+10)))
        for i in range(651):
            t = i/10
            row = dict(trial=c['trial'], block=c['block'], arm=c['arm'], t_sec=t,
                       logical_queue=at(tr['queue'],t))
            for k in ('offers','entries','admissions','starts','completions'):
                row[k+'_cumulative'] = bisect.bisect_right(tr[k],t)
            row['offered_not_entered_midpoint'] = row['offers_cumulative']-row['entries_cumulative']
            timeline.append(row)
        for second in range(10):
            rrs = [r for r in rr if r['burst_second']==second]
            stagerow = dict(trial=c['trial'], block=c['block'], arm=c['arm'], second=second,
                offers=len(rrs), misses=sum(not r['timely_500'] for r in rrs),
                rejected=sum(r['outcome']=='rejected' for r in rrs),
                miss_pct=100*sum(not r['timely_500'] for r in rrs)/len(rrs),
                completions_before60=sum(0<=t<60 and second<=t%10<second+1 for t in tr['completions']))
            for k in ('scheduled_to_entry_lower_ns','scheduled_to_entry_upper_ns','pre_admission_ns',
                      'queue_ns','processing_wall_ns','completion_to_resume_ns'):
                vv=[r[k]/1e6 for r in rrs if r[k] is not None]
                stagerow[k+'_mean_ms']=st.mean(vv) if vv else None
            stages.append(stagerow)
        if c['block'] in (3,4):
            for model in ('nominal_cpu','common_period_capacity','arm_capacity_sensitivity'):
                mu = fit(trials,(1,2),model,c['arm'])
                result, pred, q = evaluate(tr,model,mu,'train_1_2_test_3_4')
                evaluations.append(result)
                if model == 'common_period_capacity':
                    traces[c['trial']] = (tr,q)
                    for r,p in zip(rr,pred):
                        predictions.append(dict(trial=c['trial'],id=r['id'],scheduled_sec=tr['offers'][r['id']],
                            observed_outcome=r['outcome'],observed_timely=r['timely_500'],
                            predicted_rejected=p['rejected'],predicted_timely=p['timely'],
                            predicted_start_sec=p['start'],predicted_completion_sec=p['completion'],
                            observed_entry_lower_sec=r['scheduled_offset_ns']/1e9+r['scheduled_to_entry_lower_ns']/1e9,
                            observed_entry_upper_sec=r['scheduled_offset_ns']/1e9+r['scheduled_to_entry_upper_ns']/1e9,
                            observed_admission_lower_sec=None if not r['worker_observed'] else
                                (r['scheduled_offset_ns']+r['scheduled_to_entry_lower_ns']+r['pre_admission_ns'])/1e9,
                            observed_admission_upper_sec=None if not r['worker_observed'] else
                                (r['scheduled_offset_ns']+r['scheduled_to_entry_upper_ns']+r['pre_admission_ns'])/1e9,
                            observed_start_lower_sec=None if not r['worker_observed'] else
                                (r['scheduled_offset_ns']+r['completion_after_offered_lower_ns']-r['processing_wall_ns'])/1e9,
                            observed_start_upper_sec=None if not r['worker_observed'] else
                                (r['scheduled_offset_ns']+r['completion_after_offered_upper_ns']-r['processing_wall_ns'])/1e9,
                            observed_completion_lower_sec=None if not r['worker_observed'] else
                                (r['scheduled_offset_ns']+r['completion_after_offered_lower_ns'])/1e9,
                            observed_completion_upper_sec=None if not r['worker_observed'] else
                                (r['scheduled_offset_ns']+r['completion_after_offered_upper_ns'])/1e9,
                            observed_resume_lower_sec=None if not r['handler_observed'] else
                                (r['scheduled_offset_ns']+r['resume_after_offered_lower_ns'])/1e9,
                            observed_resume_upper_sec=None if not r['handler_observed'] else
                                (r['scheduled_offset_ns']+r['resume_after_offered_upper_ns'])/1e9,
                            observed_deadline_stage=r['deadline_class'],
                            observed_queue_ms=None if not r['worker_observed'] else r['queue_ns']/1e6,
                            observed_processing_wall_ms=None if not r['worker_observed'] else r['processing_wall_ns']/1e6,
                            observed_e2e_ms=None if r['e2e_ns'] is None else r['e2e_ns']/1e6))
        # Leave-one-block-out sensitivity: every target block excluded from its fit.
        mu = fit(trials,tuple(b for b in range(1,5) if b!=c['block']),'common_period_capacity',c['arm'])
        result,_,_ = evaluate(tr,'common_period_capacity',mu,'leave_one_block_out')
        evaluations.append(result)
    pooled = {}
    for arm in 'ABCD':
        ss = [r for r in summaries if r['arm']==arm]
        cats = collections.Counter()
        for s in ss:
            cats.update(s['deadline_stage_counts'])
        pooled[arm] = dict(offers=sum(r['offers'] for r in ss), misses=sum(r['misses'] for r in ss),
            successful_misses=sum(r['successful_misses'] for r in ss),deadline_stage_counts=dict(cats),
            cpu_usec_per_job={k:st.mean(r['cpu_usec_per_job'][k] for r in ss)
                             for k in ('usage_usec','user_usec','system_usec')},
            stage_mean_ms={k:st.mean(r['stages_ms'][k]['mean'] for r in ss) for k in ss[0]['stages_ms']},
            busy_rate_rps=dist(r['busy_service_rps'] for r in ss))
    primary=[r for r in evaluations if r['fold']=='train_1_2_test_3_4' and r['model']=='common_period_capacity']
    n_offers = len(trials[0]['offers'])
    even_offsets = [i * 60/n_offers for i in range(n_offers)]
    future = {}
    for period,arm in ((100000,'A'),(20000,'C')):
        mu = fit(trials,(1,2),'common_period_capacity',arm)
        even,queue = simulate(even_offsets,mu)
        future[str(period)] = dict(capacity_rps=mu,even_offers=n_offers,even_rate=n_offers/60,
            even_predicted_misses=sum(not r['timely'] for r in even),
            even_predicted_rejections=sum(r['rejected'] for r in even),even_predicted_peak=max(queue[1]),
            idealized_high_phase_deadline_onset_sec=(.5*mu-1)/(169.815-mu),
            idealized_queue_fill_sec=128/(169.815-mu),
            maximum_steady_cpu_ms_per_job_before_mean_overload=500/(n_offers/60),
            transfer_assumption='Effective capacity measured during bursts continues under evenly spaced arrivals. '
                'This is untested; no extrapolated p99 is promised.')
    report=dict(input=str(args.input.resolve()),source_seals_verified=hashes,
        methodology=dict(training_blocks=[1,2],held_out_blocks=[3,4],busy_windows='6.5–9.5 s in each 10 s cycle; 18 s/trial',
            primary='One common effective capacity per quota period; trained on completion counts, not deadlines.',
            nominal='0.5 CPU / whole-measurement cgroup CPU per completed job, trained by arm.',
            queue='Initially empty FIFO; one in service, up to 128 waiting; offers at the frozen offsets.',
            response='Predicted completion approximates response; entry, publication/handler/HTTP delay and supply pulses omitted.',
            exploratory=True,macro_tolerances='Post-hoc descriptive: 3 pp misses, 10 jobs peak, 250 ms mean recovery, '
                '75 ms p99, 0.5 pp rejection. Not frozen V20 decision rules or independent confirmatory validation.',
            no_request_replication=True,clock='Server-clock queue intervals exact; labels/absolute stages retain shared bracket uncertainty.',
            absence='No per-job CPU time, cycles/instructions, GC events, worker frequency or runnable/throttle timeline.'),
        pooled_descriptive=pooled,trials=summaries,evaluations=evaluations,candidate_even_arrival_predictions=future,
        primary_macro_all_pass=all(all(r['descriptive_macro_checks'].values()) for r in primary))
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    write_csv(out/'cycles.csv',cycles)
    write_csv(out/'timeline_100ms.csv',timeline)
    write_csv(out/'burst_stages.csv',stages)
    write_csv(out/'held_out_requests.csv',predictions)
    write_csv(out/'model_predictions.csv',[{k:v for k,v in r.items() if not isinstance(v,dict)} for r in evaluations])
    # Standalone scientific plot, using the existing local venv dependency.
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/v20-backlog-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    colors={'A':'#276da5','B':'#d77824','C':'#276da5','D':'#d77824'}
    for ax,arms,label in ((axes[0,0],'AB','100 ms period'),(axes[0,1],'CD','20 ms period')):
        for arm in arms:
            grid=np.arange(0,15.01,.1)
            obs_values=[]
            pred_values=[]
            for name,(tr,q) in traces.items():
                if tr['config']['arm']!=arm: continue
                # High starts at zero; then five seconds recovery; next high at 10.
                for cyc in range(5):
                    obs_values.append([at(tr['queue'],cyc*10+5+t) for t in grid])
                    pred_values.append([at(q,cyc*10+5+t) for t in grid])
            ax.plot(grid,np.mean(obs_values,axis=0),label=f'{arm}: observed',color=colors[arm])
            ax.fill_between(grid,np.min(obs_values,axis=0),np.max(obs_values,axis=0),color=colors[arm],alpha=.1)
        ax.plot(grid,np.mean(pred_values,axis=0),'--',color='#242424',label='Common capacity prediction')
        ax.axvspan(0,5,color='#ececec',zorder=-1)
        ax.axvspan(10,15,color='#ececec',zorder=-1)
        ax.set(title=f'{label}: held-out blocks 3–4',xlabel='Seconds from high-phase start',ylabel='Admitted jobs awaiting worker')
        ax.legend(fontsize=8)
        ax.set_ylim(0,140)
    ax=axes[1,0]
    labs=[r['trial'] for r in primary]
    xx=np.arange(len(primary))
    ax.bar(xx-.18,[r['observed_miss_pct'] for r in primary],.36,label='Observed')
    ax.bar(xx+.18,[r['predicted_miss_pct'] for r in primary],.36,label='Predicted')
    ax.set_xticks(xx,labs,rotation=30)
    ax.set(title='500 ms misses, including rejections',ylabel='Percent of all offers')
    ax.legend()
    ax=axes[1,1]
    xx=np.arange(4)
    user=[pooled[a]['cpu_usec_per_job']['user_usec']/1000 for a in 'ABCD']
    system=[pooled[a]['cpu_usec_per_job']['system_usec']/1000 for a in 'ABCD']
    ax.bar(xx,user,label='User CPU',color='#276da5')
    ax.bar(xx,system,bottom=user,label='System CPU',color='#d77824')
    ax.set_xticks(xx,list('ABCD'))
    ax.set(title='Measured cgroup CPU per completed job',ylabel='CPU ms/job (whole trial and drain)')
    ax.legend()
    fig.suptitle('V20 offline resource / queueing account — no new performance run',fontsize=14)
    fig.savefig(out/'backlog_predictions.png',dpi=170)
    fig.savefig(out/'backlog_predictions.svg')
    plt.close(fig)
    seal={'analysis_script':str(Path(__file__).relative_to(ROOT)), 'analysis_script_sha256':sha(Path(__file__)),
          'files_sha256':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='seal.json'}}
    interpretation = ROOT/'docs/runtime_io_v20_backlog_findings.md'
    if interpretation.exists():
        seal.update(interpretation_document=str(interpretation.relative_to(ROOT)),
                    interpretation_document_sha256=sha(interpretation))
    (out/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    print(json.dumps({'output':str(out),'all_primary_macro_checks_pass':report['primary_macro_all_pass'],
                      'held_out_predictions':[{k:r[k] for k in ('trial','capacity_rps','observed_miss_pct',
                          'predicted_miss_pct','queue_peak_error_jobs','recovery_error_sec','p99_error_ms')}
                          for r in primary]},indent=2))


if __name__=='__main__':
    main()
