#!/usr/bin/env python3
"""Read-only exploratory V18 reanalysis; preserves the prespecified cost verdict.

Run from any directory. Uses existing frozen verification and clock mapping.
Request observations describe cohorts, not independent experimental replicates.
"""
from pathlib import Path
import argparse
import bisect
import collections
import csv
import hashlib
import json
import math
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'diagnostic'))
from parallelism_analysis import clock_mapping
from verify_kernel_observer_cost import verify_completion
from kernel_fixture_analysis import records

NS = 1_000_000
DEADLINE = 500 * NS


def read(p):
    return json.loads(p.read_text())


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def percentile(values, q):
    """Nearest-rank quantile, explicitly consistent within this new analysis."""
    v = sorted(values)
    return v[max(0, math.ceil(len(v) * q) - 1)] if v else None


def describe(v):
    return dict(n=len(v), mean=st.mean(v) if v else None,
                p50=percentile(v, .5), p90=percentile(v, .9),
                p99=percentile(v, .99), maximum=max(v) if v else None)


class Intervals:
    """Merged half-open intervals; union duration queries in logarithmic time."""
    def __init__(self, intervals):
        self.items = []
        for a, b in sorted(intervals):
            if b < a:
                raise ValueError('reversed interval')
            if b == a:
                continue
            if self.items and a <= self.items[-1][1]:
                self.items[-1] = (self.items[-1][0], max(b, self.items[-1][1]))
            else:
                self.items.append((a, b))
        self.starts = [a for a, b in self.items]
        self.ends = [b for a, b in self.items]
        self.prefix = [0]
        for a, b in self.items:
            self.prefix.append(self.prefix[-1] + b - a)

    def cumulative(self, t):
        i = bisect.bisect_right(self.ends, t)
        return self.prefix[i] + (max(0, t - self.starts[i]) if i < len(self.items) else 0)

    def overlap(self, a, b):
        return max(0, self.cumulative(b) - self.cumulative(a)) if b >= a else 0

    def intersect(self, other):
        rows = []
        i = j = 0
        while i < len(self.items) and j < len(other.items):
            a, b = self.items[i]
            c, d = other.items[j]
            if max(a, c) < min(b, d):
                rows.append((max(a, c), min(b, d)))
            if b <= d:
                i += 1
            else:
                j += 1
        return Intervals(rows)


def backlog(intervals):
    changes = collections.Counter()
    for a, b in intervals:
        if a > b:
            raise ValueError('reversed logical backlog interval')
        changes[a] += 1
        changes[b] -= 1
    total = peak = area = 0
    last = None
    for t, change in sorted(changes.items()):
        if last is not None:
            area += (t - last) * total
        total += change
        if total < 0:
            raise ValueError('negative logical backlog')
        peak = max(peak, total)
        last = t
    if total:
        raise ValueError('unclosed logical backlog')
    if area != sum(b - a for a, b in intervals):
        raise ValueError('backlog area conservation')
    return dict(peak=peak, request_seconds=area / 1e9)


def classification(e2e, comp_lo, comp_hi, resume_lo, resume_hi):
    if e2e <= DEADLINE:
        return 'timely'
    if comp_lo > DEADLINE:
        return 'computation_after_deadline'
    if comp_hi > DEADLINE:
        return 'computation_boundary_ambiguous'
    if resume_lo > DEADLINE:
        return 'computed_before_handler_resumed_after'
    if resume_hi > DEADLINE:
        return 'handler_boundary_ambiguous'
    return 'handler_resumed_before_client_finished_after'


def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def self_test():
    x = Intervals([(10, 20), (15, 25), (30, 40), (40, 40)])
    assert x.overlap(0, 50) == 25
    assert x.overlap(17, 33) == 11
    assert x.overlap(25, 30) == 0
    assert x.intersect(Intervals([(18, 32)])).items == [(18, 25), (30, 32)]
    assert backlog([(0, 10), (5, 15)]) == dict(peak=2, request_seconds=20 / 1e9)
    assert classification(501 * NS, 490 * NS, 490 * NS, 501 * NS, 502 * NS) == 'computed_before_handler_resumed_after'
    assert classification(501 * NS, 499 * NS, 501 * NS, 501 * NS, 502 * NS) == 'computation_boundary_ambiguous'
    # Test interval queries against a discrete independent representation.
    x = Intervals([(1, 6), (3, 9), (11, 14)])
    for a in range(16):
        for b in range(a, 16):
            assert x.overlap(a, b) == sum(any(l <= t < r for l, r in x.items) for t in range(a, b))


def analyze(session, output):
    self_test()
    report = verify_completion(session)
    print('Frozen completion, raw replay, and original cost verdict verified.', flush=True)
    sources = {str(session / 'latest_analysis.json'): digest(session / 'latest_analysis.json')}
    trials = []
    requests = []
    phases = []
    seconds = []
    cycles = []
    cdf = []
    kernel_summaries = []
    kernel_rows = []
    completion_waves = []
    on_releases = []
    examples = []
    for name, ref in report['attempts'].items():
        trial = session / ref['path']
        sources[str(trial / 'seal.json')] = digest(trial / 'seal.json')
        client = read(trial / 'loadgen.json')
        server = read(trial / 'server_metrics.json')
        derived = read(trial / 'derived.json')
        mapping = clock_mapping(client, server)
        lo = mapping['server_minus_client_lower_ns']
        hi = mapping['server_minus_client_upper_ns']
        origin = mapping['client_test_start_ns']
        events = {r['id']: r for r in server['events']}
        handlers = {r['id']: r for r in server['handler_events']}
        old = {r['id']: r for r in derived['requests']}
        n = client['total_scheduled']
        assert len(events) == len(handlers) == n == len(client['requests'])
        starts = sorted(r['worker_start_ns'] for r in events.values())
        completions = sorted(r['completion_ns'] for r in events.values())
        rows = []
        k_lo = derived['clocks']['kernel_minus_server_lower_ns']
        k_hi = derived['clocks']['kernel_minus_server_upper_ns']
        residence = None
        quota = {}
        if derived['summary']['arm'] == 'on':
            raw, begin, end = records((trial / 'events.txt').read_text(), (trial / 'observer.stderr').read_text())
            active = {}
            segments = []
            for r in sorted((r for r in raw if r[0] == 'S'), key=lambda r: r[1]):
                _, t, cpu, prev, nxt, state, pt, nt = r
                if pt:
                    assert active[cpu][0] == prev
                    segments.append((active.pop(cpu)[1], t))
                if nt:
                    assert cpu not in active
                    active[cpu] = (nxt, t)
            assert not active
            residence = Intervals(segments)
            qi = derived['capture']['quota_intervals']
            for bound in ('certain', 'possible'):
                by_cpu = {}
                for cpu in (2, 4):
                    by_cpu[cpu] = Intervals([
                        (q['start_upper_ns'], q['end_lower_ns']) if bound == 'certain'
                        else (q['start_lower_ns'], q['end_upper_ns'])
                        for q in qi if q['cpu'] == cpu])
                quota['both_' + bound] = by_cpu[2].intersect(by_cpu[4])
                quota['either_' + bound] = Intervals(by_cpu[2].items + by_cpu[4].items)
            # Empirical successful-unthrottle timing, not a bandwidth-period origin.
            client_k_mid = (derived['clocks']['kernel_minus_client_lower_ns'] +
                            derived['clocks']['kernel_minus_client_upper_ns']) / 2
            release_origin = origin + client_k_mid
            times = []
            for q in qi:
                a, b = q['end_lower_ns'], q['end_upper_ns']
                t = ((a + b) / 2 - release_origin) / 1e9
                if 0 <= t < 60:
                    times.append(t)
                    on_releases.append(dict(trial=name, cpu=q['cpu'], offered_relative_mid_sec=t,
                        phase_100ms_mid_ms=(t % .1) * 1000,
                        transition_bracket_us=(b - a) / 1000))
            angles = [2 * math.pi * (t % .1) / .1 for t in times]
            z = complex(st.mean([math.cos(a) for a in angles]), st.mean([math.sin(a) for a in angles]))
            kernel_summaries.append(dict(trial=name, successful_unthrottles_measurement=len(times),
                empirical_100ms_phase_ms=(math.atan2(z.imag, z.real) % (2 * math.pi)) * 100 / (2 * math.pi),
                circular_concentration=abs(z), scheduled_union_sec=residence.overlap(begin, end) / 1e9))
        for q in sorted(client['requests'], key=lambda r: r['ID']):
            e, h = events[q['ID']], handlers[q['ID']]
            assert not q['Error'] and q['StatusCode'] == 200
            assert h['entry_ns'] <= e['admission_ns'] <= e['worker_start_ns'] <= e['completion_ns'] <= h['resume_ns'] <= h['write_start_ns'] <= h['write_end_ns'] <= h['handler_exit_ns']
            assert e['queue_wait_ns'] == e['worker_start_ns'] - e['admission_ns']
            assert e['processing_ns'] == e['completion_ns'] - e['worker_start_ns']
            assert h['post_work_wait_ns'] == h['resume_ns'] - e['completion_ns']
            assert h['pre_admission_ns'] == e['admission_ns'] - h['entry_ns']
            scheduled = origin + q['ScheduledOffsetNs']
            stamp_bounds = lambda stamp: (stamp - hi - scheduled, stamp - lo - scheduled)
            entry_lo, entry_hi = stamp_bounds(h['entry_ns'])
            comp_lo, comp_hi = stamp_bounds(e['completion_ns'])
            resume_lo, resume_hi = stamp_bounds(h['resume_ns'])
            gap = h['resume_ns'] - e['completion_ns']
            # Strict interior timestamps; own completion at left boundary is excluded.
            progress = bisect.bisect_left(starts, h['resume_ns']) - bisect.bisect_right(starts, e['completion_ns'])
            finished = bisect.bisect_left(completions, h['resume_ns']) - bisect.bisect_right(completions, e['completion_ns'])
            row = dict(trial=name, pair=derived['summary']['pair'], arm=derived['summary']['arm'], id=q['ID'],
                offered_second=q['ScheduledOffsetNs'] // 1_000_000_000,
                burst_second=q['ScheduledOffsetNs'] // 1_000_000_000 % 10,
                cycle=q['ScheduledOffsetNs'] // 10_000_000_000,
                phase='low' if q['ScheduledOffsetNs'] % 10_000_000_000 < 5_000_000_000 else 'high',
                e2e_ms=q['EndToEndLatencyNs'] / NS,
                dispatch_lag_ms=q['DispatchLagNs'] / NS,
                scheduled_to_entry_lower_ms=entry_lo / NS, scheduled_to_entry_upper_ms=entry_hi / NS,
                pre_admission_ms=h['pre_admission_ns'] / NS,
                queue_ms=e['queue_wait_ns'] / NS, processing_wall_ms=e['processing_ns'] / NS,
                completion_to_resume_ms=gap / NS,
                resume_to_client_lower_ms=(q['EndToEndLatencyNs'] - resume_hi) / NS,
                resume_to_client_upper_ms=(q['EndToEndLatencyNs'] - resume_lo) / NS,
                resume_to_write_end_ms=(h['write_end_ns'] - h['resume_ns']) / NS,
                completion_after_offered_lower_ms=comp_lo / NS,
                completion_after_offered_upper_ms=comp_hi / NS,
                resume_after_offered_lower_ms=resume_lo / NS,
                resume_after_offered_upper_ms=resume_hi / NS,
                deadline_class=classification(q['EndToEndLatencyNs'], comp_lo, comp_hi, resume_lo, resume_hi),
                work_starts_inside_gap=progress, work_completions_inside_gap=finished,
                previous_clock_crossover=(old[q['ID']]['completion_kernel_upper_ns'] <= old[q['ID']]['scheduled_kernel_lower_ns'] + DEADLINE and
                    old[q['ID']]['resume_kernel_lower_ns'] > old[q['ID']]['scheduled_kernel_upper_ns'] + DEADLINE),
                completion_margin_certain_ms=(DEADLINE - comp_hi) / NS)
            # Interval budget identity checked for both shared clock endpoints.
            for bound in ('lower', 'upper'):
                rest = 'upper' if bound == 'lower' else 'lower'
                stage_sum = row[f'scheduled_to_entry_{bound}_ms'] + row['pre_admission_ms'] + row['queue_ms'] + row['processing_wall_ms'] + row['completion_to_resume_ms'] + row[f'resume_to_client_{rest}_ms']
                assert abs(stage_sum - row['e2e_ms']) < 1e-8
            rows.append(row)
            if residence is not None and (gap > 50 * NS or row['deadline_class'] == 'computed_before_handler_resumed_after'):
                a_c, b_c = e['completion_ns'] + k_hi, h['resume_ns'] + k_lo
                a_p, b_p = e['completion_ns'] + k_lo, h['resume_ns'] + k_hi
                kr = dict(trial=name, id=q['ID'], gap_ms=gap / NS, deadline_class=row['deadline_class'],
                          work_starts_inside_gap=progress, work_completions_inside_gap=finished)
                for label, intervals in [('scheduled_union', residence),
                    ('both_rq_throttled', quota['both_certain']), ('either_rq_throttled', quota['either_certain'])]:
                    possible = residence if label == 'scheduled_union' else quota[('both' if label.startswith('both') else 'either') + '_possible']
                    low = intervals.overlap(a_c, b_c)
                    high = min(gap, possible.overlap(a_p, b_p))
                    assert 0 <= low <= high <= gap
                    kr[label + '_lower_ms'] = low / NS
                    kr[label + '_upper_ms'] = high / NS
                kernel_rows.append(kr)
        requests.extend(rows)
        trial_row = dict(derived['summary'])
        trial_row.pop('counter_window')
        trial_row.update(clock_mapping_uncertainty_us=mapping['uncertainty_ns'] / 1000,
            late_500=sum(r['e2e_ms'] > 500 for r in rows),
            deadline_classes=dict(collections.Counter(r['deadline_class'] for r in rows)),
            previous_clock_crossover_count=sum(r['previous_clock_crossover'] for r in rows),
            crossover_with_50ms_margin=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' and r['completion_margin_certain_ms'] >= 50 for r in rows),
            long_gaps_gt50ms=sum(r['completion_to_resume_ms'] > 50 for r in rows),
            long_gaps_with_other_work=sum(r['completion_to_resume_ms'] > 50 and r['work_starts_inside_gap'] > 0 for r in rows),
            crossover_with_other_work=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' and r['work_starts_inside_gap'] > 0 for r in rows),
            logical_admitted_not_started=backlog([(e['admission_ns'], e['worker_start_ns']) for e in events.values()]),
            logical_computed_not_resumed=backlog([(events[h['id']]['completion_ns'], h['resume_ns']) for h in handlers.values()]))
        for key in ('e2e_ms', 'scheduled_to_entry_upper_ms', 'queue_ms', 'processing_wall_ms', 'completion_to_resume_ms',
                    'resume_to_client_upper_ms', 'dispatch_lag_ms', 'resume_to_write_end_ms'):
            trial_row[key] = describe([r[key] for r in rows])
        obs = read(trial / 'observations.json')
        before, after = (obs[k]['cpu_stat']['usage_usec'] for k in ('measurement_start', 'measurement_stop'))
        samples = [s for s in read(trial / 'monitor.json') if before <= s['cgroup_cpu_stat']['usage_usec'] <= after]
        trial_row['host_samples_counter_selected'] = len(samples)
        trial_row['temperature_c'] = describe([s['temps_c']['k10temp:temp1_input'] for s in samples])
        for cpu in (2, 3, 4, 5):
            trial_row[f'cpu{cpu}_util_pct'] = describe([s['cpu_util_pct'][f'cpu{cpu}'] for s in samples])
            trial_row[f'cpu{cpu}_frequency_mhz'] = describe([s['freqs_mhz'][f'cpu{cpu}'] for s in samples])
        trial_row['client_cpu_ms'] = client['client_cpu_usec'] / 1000
        collector = [p['cpu_delta_sec'] for s in read(trial / 'monitor.json') for p in s['process_cpu_deltas'] if p['comm'] == 'bpftrace']
        trial_row['collector_sampled_cpu_sec_full_capture'] = sum(collector)
        trials.append(trial_row)
        for kind, field, values in [('phase', 'phase', ['low', 'high']), ('second', 'burst_second', range(10)), ('cycle', 'cycle', range(6))]:
            for value in values:
                subset = [r for r in rows if r[field] == value]
                item = dict(trial=name, pair=trial_row['pair'], arm=trial_row['arm'], grouping=kind, value=value,
                            offered=len(subset), timely_500_pct=100 * sum(r['e2e_ms'] <= 500 for r in subset) / len(subset),
                            crossover_count=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' for r in subset))
                for key in ('e2e_ms', 'queue_ms', 'processing_wall_ms', 'completion_to_resume_ms'):
                    item[key + '_mean'] = st.mean(r[key] for r in subset)
                    item[key + '_p99'] = percentile([r[key] for r in subset], .99)
                (phases if kind == 'phase' else seconds if kind == 'second' else cycles).append(item)
        for threshold in range(250, 1001, 5):
            cdf.append(dict(trial=name, pair=trial_row['pair'], arm=trial_row['arm'], threshold_ms=threshold,
                timely_pct=100 * sum(r['e2e_ms'] <= threshold for r in rows) / n))
        for r in sorted((r for r in rows if r['deadline_class'] == 'computed_before_handler_resumed_after'),
                        key=lambda r: r['completion_margin_certain_ms'], reverse=True)[:5]:
            examples.append(r)
        # Service completion markers modulo 100 ms, relative to offers (midpoint only).
        completion_origin = origin + (lo + hi) / 2
        counts = collections.Counter(int(((e['completion_ns'] - completion_origin) % (100 * NS)) // (5 * NS)) for e in events.values())
        for bin_id in range(20):
            completion_waves.append(dict(trial=name, arm=trial_row['arm'], phase_bin_start_ms=bin_id * 5,
                                         count=counts[bin_id], mapping_uncertainty_us=mapping['uncertainty_ns'] / 1000))
        print(name + ': joined and interval accounting verified', flush=True)
    paired = []
    for pair in range(1, 7):
        a = [r for r in requests if r['trial'] == f'p{pair}_off']
        b = [r for r in requests if r['trial'] == f'p{pair}_on']
        assert [r['id'] for r in a] == [r['id'] for r in b]
        row = dict(pair=pair,
            lost_timely=sum(x['e2e_ms'] <= 500 < y['e2e_ms'] for x, y in zip(a, b)),
            gained_timely=sum(y['e2e_ms'] <= 500 < x['e2e_ms'] for x, y in zip(a, b)),
            both_late=sum(x['e2e_ms'] > 500 and y['e2e_ms'] > 500 for x, y in zip(a, b)))
        assert (row['gained_timely'] - row['lost_timely']) / len(a) == report['pairs'][pair - 1]['timely_500_delta'] or abs((row['gained_timely'] - row['lost_timely']) / len(a) - report['pairs'][pair - 1]['timely_500_delta']) < 1e-12
        for field in ('e2e_ms', 'queue_ms', 'processing_wall_ms', 'completion_to_resume_ms', 'scheduled_to_entry_upper_ms'):
            row[field + '_on_minus_off_mean'] = st.mean(y[field] - x[field] for x, y in zip(a, b))
        for window in (5, 10, 25, 50, 100):
            row[f'off_within_{window}ms_of_deadline'] = sum(abs(r['e2e_ms'] - 500) <= window for r in a)
        paired.append(row)
    result = dict(purpose='Exploratory retained-data analysis; no new measurement or threshold qualification',
        original_decision=report['decision'], observer_cost_qualified=report['observer_cost_qualified'],
        input_seals=sources, original_pairs=report['pairs'], trials=trials, paired_stage_changes=paired,
        pooled_by_arm={}, kernel_on_only=kernel_summaries,
        limitations=[
            'Six paired trials are the experimental units; requests and cycles are dependent descriptive cohorts.',
            'Publication and runnable readiness are unobserved. Completion-to-resume includes bookkeeping and publication.',
            'Kernel overlap describes the unqualified on arm only, never counterfactual off-arm attribution.',
            'Both-runqueue flags are not a global quota-availability oracle; no overlap does not exclude quota.',
            'Residency includes kernel/interrupt time and union duration must not be summed over CPUs.',
            'Empirical unthrottle phase is not necessarily a bandwidth-period origin or refill.',
            'Counter-selected monitor samples are approximate; last CPU does not identify all contention.',
            'Near-500ms sensitivity is exploratory and does not replace the failed prespecified 1pp screen.'])
    for arm in ('off', 'on'):
        rr = [r for r in requests if r['arm'] == arm]
        result['pooled_by_arm'][arm] = dict(offered=len(rr), timely_500_pct=100 * sum(r['e2e_ms'] <= 500 for r in rr) / len(rr),
            deadline_classes=dict(collections.Counter(r['deadline_class'] for r in rr)),
            previous_clock_crossover_count=sum(r['previous_clock_crossover'] for r in rr),
            crossovers_margin_at_least50ms=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' and r['completion_margin_certain_ms'] >= 50 for r in rr),
            crossovers_with_other_work=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' and r['work_starts_inside_gap'] > 0 for r in rr),
            long_gaps_gt50ms=sum(r['completion_to_resume_ms'] > 50 for r in rr),
            long_gaps_with_other_work=sum(r['completion_to_resume_ms'] > 50 and r['work_starts_inside_gap'] > 0 for r in rr),
            stages={key: describe([r[key] for r in rr]) for key in ('e2e_ms', 'scheduled_to_entry_upper_ms', 'queue_ms', 'processing_wall_ms', 'completion_to_resume_ms', 'resume_to_client_upper_ms')})
    result['kernel_gap_summary'] = {}
    for category in ('all_selected', 'computed_before_handler_resumed_after'):
        rr = [r for r in kernel_rows if category == 'all_selected' or r['deadline_class'] == category]
        result['kernel_gap_summary'][category] = dict(n=len(rr),
            scheduled_union_lower_fraction=describe([r['scheduled_union_lower_ms'] / r['gap_ms'] for r in rr]),
            both_rq_throttled_lower_fraction=describe([r['both_rq_throttled_lower_ms'] / r['gap_ms'] for r in rr]),
            both_rq_throttled_upper_fraction=describe([r['both_rq_throttled_upper_ms'] / r['gap_ms'] for r in rr]),
            count_scheduled_union_certainly_gt10ms=sum(r['scheduled_union_lower_ms'] > 10 for r in rr))
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in [('requests', requests), ('phases', phases), ('burst_seconds', seconds), ('cycles', cycles),
                       ('deadline_cdf', cdf), ('paired_changes', paired), ('kernel_gap_overlap', kernel_rows),
                       ('completion_waveforms', completion_waves), ('unthrottle_phase', on_releases), ('examples', examples)]:
        write_csv(output / (name + '.csv'), rows)
    (output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    assert all(digest(Path(p)) == h for p, h in sources.items())
    print('Input seal files unchanged; output: ' + str(output), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, default=ROOT / 'analysis/runtime_io_v18_observer_cost/generation-04')
    parser.add_argument('--output', type=Path, default=ROOT / 'analysis/runtime_io_v19_planning/offline-20261004')
    args = parser.parse_args()
    analyze(args.session.resolve(), args.output.resolve())
