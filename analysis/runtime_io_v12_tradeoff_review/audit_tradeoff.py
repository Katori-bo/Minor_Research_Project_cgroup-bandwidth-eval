#!/usr/bin/env python3
"""Offline, post-hoc audit of sealed V12 trials. Never collects performance data."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RESULT = ROOT / 'results/diagnostic/runtime-io-v12-bursty-parallelism-1'
sys.path.insert(0, str(ROOT / 'diagnostic'))
import parallelism_analysis as pa
import parallelism_study as study

SECOND = 1_000_000_000
END = 60 * SECOND


def read(p):
    return json.loads(p.read_text())


def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(RESULT.rglob('*')) if p.is_file()}


def quantile(values, p):
    a = sorted(values)
    return a[math.ceil(p * len(a)) - 1] if a else None


def describe(values):
    return {'n': len(values), 'mean_ms': st.mean(values) / 1e6 if values else None,
            **{f'p{int(p*100)}_ms': quantile(values, p) / 1e6 if values else None
               for p in (.5, .95, .99)}}


def phase(t):
    # Half-open intervals reflect the pinned arrivalOffset implementation.
    if t >= END:
        return 'drain'
    return 'low' if t % (10 * SECOND) < 5 * SECOND else 'high'


def phase_interval(lo, hi):
    # Do not assign a midpoint when the clock bracket crosses a phase boundary.
    return phase(lo) if lo // (5 * SECOND) == hi // (5 * SECOND) else 'ambiguous'


def summarize(rows):
    good = [r for r in rows if r['outcome'] == 'success']
    jobs = [r for r in rows if r['admitted']]
    value = dict(offered=len(rows), success=len(good),
                 rejected=sum(r['outcome'] == 'rejected' for r in rows),
                 timeout=sum(r['outcome'] == 'timeout' for r in rows),
                 error=sum(r['outcome'] == 'error' for r in rows),
                 admitted=len(jobs), server_completed=len(jobs),
                 missing_entries=sum(not r['entry_observed'] for r in rows),
                 certain_long_entry=sum(r['entry_lower_ns'] >= SECOND for r in rows),
                 possible_long_entry=sum(r['entry_upper_ns'] >= SECOND for r in rows),
                 success_after_window=sum(r['completed_ns'] > END for r in good),
                 terminal_after_window=sum(r['completed_ns'] > END for r in rows),
                 server_context_gone_at_work_completion=sum(r['client_gone'] for r in jobs),
                 server_work_certainly_after_client_terminal=sum(r['work_after_client_certain'] for r in jobs),
                 server_work_possibly_after_client_terminal=sum(r['work_after_client_possible'] for r in jobs),
                 server_work_certainly_after_window=sum(r['work_after_window_certain'] for r in jobs),
                 server_work_possibly_after_window=sum(r['work_after_window_possible'] for r in jobs))
    value['failure_fraction'] = (len(rows) - len(good)) / len(rows) if rows else None
    value['timely_success_fraction'] = {
        str(ms): sum(r['e2e_ns'] <= ms * 1e6 for r in good) / len(rows) if rows else None
        for ms in (100, 500, 1000, 5000)}
    value['success_e2e'] = describe([r['e2e_ns'] for r in good])
    value['terminal_latency_all_outcomes'] = describe([r['e2e_ns'] for r in rows])
    value['entry_lower_all_outcomes'] = describe([r['entry_lower_ns'] for r in rows])
    value['entry_upper_all_outcomes'] = describe([r['entry_upper_ns'] for r in rows])
    value['queue_all_completed'] = describe([r['queue_ns'] for r in jobs])
    for field in ('queue_ns', 'processing_ns', 'pre_ns', 'post_ns', 'dispatch_lag_ns'):
        value[field.removesuffix('_ns') + '_success'] = describe([r[field] for r in good])
    value['entry_transition'] = {p: sum(r['entry_phase'] == p for r in rows)
                                 for p in ('low', 'high', 'drain', 'ambiguous')}
    value['worker_start_transition'] = {p: sum(r['worker_phase'] == p for r in jobs)
                                        for p in ('low', 'high', 'drain', 'ambiguous')}
    return value


def decomposition(rows):
    """Average actual durations for the same cohort; never add stage percentiles."""
    fields = ('e2e_ns', 'entry_lower_ns', 'entry_upper_ns', 'pre_ns', 'queue_ns',
              'processing_ns', 'post_ns', 'response_lower_ns', 'response_upper_ns')
    return {'n': len(rows), **{k.removesuffix('_ns') + '_mean_ms':
                              st.mean(r[k] for r in rows) / 1e6 if rows else None
                              for k in fields}}


def main():
    before = hashes()
    study.verify_completion(RESULT)  # Frozen sources/build, raw evidence and clock validation.
    csv_original = {r['run_id']: r for r in csv.DictReader(
        (RESULT / 'session/analysis/trials.csv').open())}
    trials = []
    failure_rows = []
    phase_rows = []
    cycle_rows = []
    bucket_rows = []
    decompositions = []
    by_run = {}
    completion = read(RESULT / 'completion.json')
    for config in read(RESULT / 'session/matrix.json'):
        rid = config['run_id']
        d = RESULT / 'session/attempts' / rid / completion['attempts'][rid]['attempt']
        client, server, result = [read(d / n) for n in
                                  ('loadgen.json', 'server_metrics.json', 'result.json')]
        entry = pa.entry_analysis(client, server)
        entries = {r['id']: r for r in entry['requests']}
        jobs = {r['id']: r for r in server['events']}
        handlers = {r['id']: r for r in server['handler_events']}
        m = entry['mapping']
        def mapped(t):
            return (t - m['server_minus_client_upper_ns'] - m['client_test_start_ns'],
                    t - m['server_minus_client_lower_ns'] - m['client_test_start_ns'])
        rows = []
        for q in client['requests']:
            e = entries[q['ID']]
            assert e['entry_observed'], 'Audit currently requires complete observed entries.'
            entry_lo, entry_hi = mapped(e['server_entry_ns'])
            row = dict(id=q['ID'], run_id=rid, block=config['rep'], gomaxprocs=config['gomaxprocs'],
                       phase=phase(q['ScheduledOffsetNs']),
                       cycle=q['ScheduledOffsetNs'] // (10 * SECOND),
                       bucket=q['ScheduledOffsetNs'] % (10 * SECOND) // SECOND,
                       scheduled_ns=q['ScheduledOffsetNs'], completed_ns=q['CompletedOffsetNs'],
                       e2e_ns=q['EndToEndLatencyNs'], outcome=e['outcome'], admitted=e['admitted'],
                       entry_observed=e['entry_observed'], entry_phase=phase_interval(entry_lo, entry_hi),
                       entry_lower_ns=e['scheduled_to_entry_lower_ns'],
                       entry_upper_ns=e['scheduled_to_entry_upper_ns'],
                       dispatch_lag_ns=q['DispatchLagNs'], client_gone=False,
                       work_after_client_certain=False, work_after_client_possible=False,
                       work_after_window_certain=False, work_after_window_possible=False,
                       queue_ns=None, processing_ns=None, worker_phase=None)
            j = jobs.get(q['ID'])
            assert (j is not None) == row['admitted']
            if j:
                work_lo, work_hi = mapped(j['completion_ns'])
                worker_lo, worker_hi = mapped(j['worker_start_ns'])
                row.update(queue_ns=j['queue_wait_ns'], processing_ns=j['processing_ns'],
                           worker_phase=phase_interval(worker_lo, worker_hi),
                           client_gone=j['client_gone_at_completion'],
                           work_after_client_certain=work_lo > row['completed_ns'],
                           work_after_client_possible=work_hi > row['completed_ns'],
                           work_after_window_certain=work_lo > END,
                           work_after_window_possible=work_hi > END)
            if row['outcome'] == 'success':
                h = handlers[q['ID']]
                row.update(pre_ns=h['pre_admission_ns'], post_ns=h['post_work_wait_ns'])
                assert row['queue_ns'] == q['QueueWaitNs']
                assert row['processing_ns'] == q['ProcessingNs']
                stages = row['pre_ns'] + row['queue_ns'] + row['processing_ns'] + row['post_ns']
                row['response_lower_ns'] = row['e2e_ns'] - row['entry_upper_ns'] - stages
                row['response_upper_ns'] = row['e2e_ns'] - row['entry_lower_ns'] - stages
                assert row['entry_lower_ns'] + stages + row['response_upper_ns'] == row['e2e_ns']
                assert row['entry_upper_ns'] + stages + row['response_lower_ns'] == row['e2e_ns']
            else:
                failure_rows.append({**row, 'status': q['StatusCode'], 'error_text': q['Error']})
            rows.append(row)
        by_run[rid] = rows
        groups = {ph: [r for r in rows if ph == 'all' or r['phase'] == ph]
                  for ph in ('all', 'low', 'high')}
        metrics = {ph: summarize(rs) for ph, rs in groups.items()}
        assert metrics['all']['success_e2e']['p50_ms'] == float(csv_original[rid]['p50_e2e_ms'])
        assert metrics['all']['success_e2e']['p99_ms'] == float(csv_original[rid]['p99_e2e_ms'])
        assert metrics['low']['offered'] == 1699 and metrics['high']['offered'] == 5094
        assert metrics['all']['server_context_gone_at_work_completion'] == server['client_gone_at_completion']
        assert metrics['all']['server_completed'] == server['completed'] == server['admitted']
        for ph, rs in groups.items():
            z = metrics[ph]
            phase_rows.append(dict(run_id=rid, block=config['rep'], gomaxprocs=config['gomaxprocs'], phase=ph,
                **{k: v for k, v in z.items() if not isinstance(v, dict)},
                **{f'{k}_{a}': b for k, v in z.items() if isinstance(v, dict)
                   for a, b in v.items()}))
            good = sorted((r for r in rs if r['outcome'] == 'success'), key=lambda r: r['e2e_ns'])
            for label, cohort in [('all_success', good),
                                  ('median_rank_45_to_55_percent', good[math.floor(.45*len(good)):math.ceil(.55*len(good))]),
                                  ('slowest_one_percent', good[-math.ceil(.01*len(good)):])]:
                decompositions.append(dict(run_id=rid, phase=ph, cohort=label, **decomposition(cohort)))
        cycles = []
        buckets = []
        for cycle in range(6):
            for ph in ('low', 'high'):
                v = summarize([r for r in rows if r['cycle'] == cycle and r['phase'] == ph])
                cycles.append(dict(cycle=cycle, phase=ph, **v))
                cycle_rows.append(dict(run_id=rid, cycle=cycle, phase=ph, offered=v['offered'],
                    success=v['success'], rejected=v['rejected'], timeout=v['timeout'],
                    p50_ms=v['success_e2e']['p50_ms'], p99_ms=v['success_e2e']['p99_ms']))
        for bucket in range(10):
            v = summarize([r for r in rows if r['bucket'] == bucket])
            buckets.append(dict(second_in_cycle=bucket, **v))
            bucket_rows.append(dict(run_id=rid, gomaxprocs=config['gomaxprocs'], second_in_cycle=bucket,
                offered=v['offered'], success=v['success'],
                p50_ms=v['success_e2e']['p50_ms'], p99_ms=v['success_e2e']['p99_ms'],
                queue_mean_ms=v['queue_all_completed']['mean_ms']))
        monitor = read(d / 'monitor.json')
        temperatures = [s['temps_c']['k10temp:temp1_input'] for s in monitor]
        trials.append(dict(run_id=rid, block=config['rep'], gomaxprocs=config['gomaxprocs'], phases=metrics,
                           cycles=cycles, buckets=buckets,
                           clock_uncertainty_ns=m['uncertainty_ns'],
                           cpu_usec_per_completed_job=result['cgroup_delta']['usage_usec']/server['completed'],
                           cpu_usage_cores=result['cpu_usage_cores'], throttled_period_fraction=result['throttling_fraction'],
                           package_temperature_range_c=[min(temperatures), max(temperatures)],
                           package_temperature_median_c=st.median(temperatures),
                           quality_flags=result['quality_flags']))
    pairs = []
    matched = []
    cells = {(t['block'], t['gomaxprocs']): t for t in trials}
    for b in range(1, 5):
        a = {r['id']: r for r in by_run[f'parallelism_b{b}_g2']}
        z = {r['id']: r for r in by_run[f'parallelism_b{b}_g1']}
        assert set(a) == set(z) and all(a[k]['scheduled_ns'] == z[k]['scheduled_ns'] for k in a)
        for ph in ('all', 'low', 'high'):
            x, y = [cells[b, g]['phases'][ph] for g in (2, 1)]
            pairs.append(dict(block=b, phase=ph,
                p50_g2_ms=x['success_e2e']['p50_ms'], p50_g1_ms=y['success_e2e']['p50_ms'],
                p50_difference_ms=y['success_e2e']['p50_ms']-x['success_e2e']['p50_ms'],
                p99_g2_ms=x['success_e2e']['p99_ms'], p99_g1_ms=y['success_e2e']['p99_ms'],
                mean_queue_g2_ms=x['queue_all_completed']['mean_ms'], mean_queue_g1_ms=y['queue_all_completed']['mean_ms']))
            good_ids = [k for k in a if a[k]['outcome'] == z[k]['outcome'] == 'success'
                        and (ph == 'all' or a[k]['phase'] == ph)]
            deltas = [z[k]['e2e_ns']-a[k]['e2e_ns'] for k in good_ids]
            matched.append(dict(block=b, phase=ph, common_success_ids=len(good_ids),
                g1_faster_fraction=sum(v<0 for v in deltas)/len(deltas),
                e2e_g1_minus_g2=describe(deltas),
                queue_delta_mean_ms=st.mean(z[k]['queue_ns']-a[k]['queue_ns'] for k in good_ids)/1e6,
                e2e_delta_mean_ms=st.mean(deltas)/1e6))
    medians = {}
    for ph in ('all', 'low', 'high'):
        medians[ph] = {}
        for g in (2, 1):
            v = [t['phases'][ph] for t in trials if t['gomaxprocs'] == g]
            medians[ph][str(g)] = {
                'success_p50_ms': st.median(z['success_e2e']['p50_ms'] for z in v),
                'success_p99_ms': st.median(z['success_e2e']['p99_ms'] for z in v),
                'queue_p50_ms': st.median(z['queue_all_completed']['p50_ms'] for z in v),
                'queue_p99_ms': st.median(z['queue_all_completed']['p99_ms'] for z in v),
                'queue_mean_ms': st.median(z['queue_all_completed']['mean_ms'] for z in v),
                'entry_p50_upper_ms': st.median(z['entry_upper_all_outcomes']['p50_ms'] for z in v),
                'timely_success_fraction': {ms: st.median(z['timely_success_fraction'][ms] for z in v)
                                            for ms in ('100', '500', '1000', '5000')}}
    totals = {str(g): {k: sum(t['phases']['all'][k] for t in trials if t['gomaxprocs'] == g)
                       for k in ('offered','success','rejected','timeout','error','certain_long_entry',
                                 'missing_entries','success_after_window','server_completed',
                                 'server_context_gone_at_work_completion',
                                 'server_work_certainly_after_client_terminal',
                                 'server_work_possibly_after_client_terminal',
                                 'server_work_certainly_after_window','server_work_possibly_after_window')}
              for g in (2, 1)}
    after = hashes()
    assert before == after, 'Sealed experiment files changed during audit.'
    summary = dict(method='Post-hoc descriptive audit; scheduled phase; nearest-rank percentiles; four independent trial pairs.',
                   trials=trials, pairs=pairs, matched_arrival_positions=matched,
                   medians_of_trial_statistics=medians, totals=totals,
                   validation=dict(original_completion_verified=True, input_hashes_unchanged=True,
                                   phase_counts_verified=True, original_p50_p99_reproduced=True,
                                   all_entries_and_admitted_work_linked=True, same_request_stage_accounting_verified=True,
                                   identical_paired_arrival_schedules=True),
                   input_sha256=before, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (OUT/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    for name, rows in [('trial_phase.csv',phase_rows), ('trial_cycle_phase.csv',cycle_rows),
                       ('cycle_second.csv',bucket_rows), ('paired_phase.csv',pairs),
                       ('stage_cohorts.csv',decompositions), ('failed_requests.csv',failure_rows)]:
        with (OUT/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(dict(validation=summary['validation'], medians=medians, totals=totals,
                         pairs=pairs, matched=matched),indent=2))


if __name__ == '__main__':
    main()
