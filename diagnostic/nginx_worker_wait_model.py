"""Operational boundary checks and paired equivalence screen, not prediction."""
import math
import statistics as st
from pathlib import Path
import sys
import nginx_worker_wait_common as c
sys.path.insert(0, str(c.ROOT / 'analysis'))
import worker_wait_features as w


def parse_task_stat(text):
    close = text.rfind(')')
    c.require(close > 0 and '(' in text[:close], 'Malformed task stat')
    pid = int(text[:text.index('(')].strip())
    fields = text[close + 1:].split()
    c.require(len(fields) >= 37, 'Short task stat')
    return dict(pid=pid, parent=int(fields[1]), start_ticks=int(fields[19]),
                state=fields[0], processor=int(fields[36]))


def check_snapshot(s, expected):
    before, after = parse_task_stat(s['stat_before']), parse_task_stat(s['stat_after'])
    for value in (before, after):
        c.require(all(value[k] == expected[k] for k in ('pid', 'parent', 'start_ticks')) and
                  value['processor'] == 2 and value['state'] == 'S', 'Worker identity/state boundary differs')
    c.require(s['read_started_ns'] <= s['read_finished_ns'] and
              0 <= s['read_finished_ns'] - s['read_started_ns'] <= c.PROTOCOL['max_read_bracket_ns'],
              'Worker counter read bracket exceeded')
    parsed = w.parse_schedstat(s['schedstat_raw'])
    c.require(parsed == s['counters'], 'Counter text differs')
    return parsed


def provisional(before, after, expected, count):
    a, b = check_snapshot(before, expected), check_snapshot(after, expected)
    c.require(before['read_finished_ns'] <= after['read_started_ns'], 'Counter acquisition reversed')
    delta = {k: b[k] - a[k] for k in a}
    c.require(all(v >= 0 for v in delta.values()) and delta['running_ns'] > 0 and
              delta['timeslices'] > 0, 'Worker accounting unavailable or reversed')
    return dict(delta=delta, offered=count, running_ns_per_offer=delta['running_ns'] / count,
                runnable_wait_ns_per_offer=delta['runnable_wait_ns'] / count,
                qualification_oracle_only=True, hardware_qualified=False)


def check_boundary(evidence, expected, cpu_delta_us):
    p = c.PROTOCOL
    b, a = evidence['before'], evidence['after']
    feature = provisional(b, a, expected, 25)
    events = evidence['events']
    operations = evidence['operations']
    c.require(len(operations) == 2 and
              operations[0]['started_ns'] <= b['read_started_ns'] <= b['read_finished_ns'] <=
              operations[0]['finished_ns'] <= events['warmup_call_started_ns'] and
              events['warmup_call_finished_ns'] <= operations[1]['started_ns'] <=
              a['read_started_ns'] <= a['read_finished_ns'] <= operations[1]['finished_ns'] <=
              events['feature_saved_ns'] and
              evidence['observer_wall_ns'] == sum(x['finished_ns'] - x['started_ns'] for x in operations),
              'Observer operation timing/cost differs')
    c.require(b['read_finished_ns'] <= events['warmup_call_started_ns'] <=
              events['warmup_call_finished_ns'] <= a['read_started_ns'] <=
              a['read_finished_ns'] <= events['feature_saved_ns'] <=
              events['status_started_ns'] <= events['status_finished_ns'] <=
              events['decision_sealed_ns'] <= events['measurement_started_ns'], 'Observer/control boundary differs')
    c.require(0 <= evidence['observer_wall_ns'] <= p['max_observer_wall_ns'], 'Observer wall budget exceeded')
    residual = abs(feature['delta']['running_ns'] - 1000 * cpu_delta_us) / 25
    c.require(residual <= p['cpu_agreement_ns_per_offer'], 'Worker/cgroup CPU discrepancy exceeds allowance')
    carryover = None
    if 'idle_after' in evidence:
        idle = evidence['idle_after']
        z = check_snapshot(idle, expected)
        c.require(a['read_finished_ns'] + int(p['quiet_sec'] * 1e9) <= idle['read_started_ns'] <=
                  idle['read_finished_ns'] <= events['status_started_ns'], 'Idle/control boundary differs')
        carryover = {k: z[k] - a['counters'][k] for k in z}
        c.require(all(x >= 0 for x in carryover.values()) and
                  all(carryover[k] / 25 <= p['idle_carryover_ns_per_offer']
                      for k in ('running_ns', 'runnable_wait_ns')), 'Idle carryover exceeds allowance')
    return dict(feature=feature, worker_cgroup_residual_ns_per_offer=residual,
                idle_carryover=carryover, operational_boundary_checks=True,
                absolute_wait_accuracy_verified=False)


def interval(values, margin):
    c.require(len(values) == 6, 'Six paired blocks required')
    mean = st.mean(values)
    half = c.PROTOCOL['paired_t_multiplier'] * st.stdev(values) / math.sqrt(6)
    bounds = [mean - half, mean + half]
    return dict(differences=values, mean=mean, conditional_interval=bounds, margin=margin,
                equivalence_supported=bounds[0] >= -margin and bounds[1] <= margin)


def compare(rows, sched):
    c.require([r['config'] for r in rows] == sched['overhead'], 'Full paired schedule required')
    panels = {}
    for rate in (4, 8):
        pairs = []
        for block in range(1, 7):
            cell = {r['config']['arm']: r for r in rows
                    if r['config']['rate_rps'] == rate and r['config']['block'] == block}
            c.require(set(cell) == {'off', 'on'}, 'Paired cell missing')
            pairs.append({k: cell['on'][k] - cell['off'][k] for k in
                          ('measurement_miss_pct', 'measurement_mean_ns', 'warmup_mean_ns')})
        tests = {k: interval([x[k] for x in pairs], c.PROTOCOL['miss_equivalence_margin_pp']
                             if k.endswith('pct') else c.PROTOCOL['mean_equivalence_margin_ns'])
                 for k in pairs[0]}
        miss = [r['measurement_miss_pct'] for r in rows if r['config']['rate_rps'] == rate]
        transition = c.PROTOCOL['transition_min_pct'] <= st.mean(miss) <= c.PROTOCOL['transition_max_pct']
        panels[str(rate)] = dict(tests=tests, endpoint_transition_informative=transition,
                                mean_miss_pct=st.mean(miss), qualifies=transition and
                                all(v['equivalence_supported'] for v in tests.values()))
    qualified = all(x['qualifies'] for x in panels.values())
    return dict(status='observer_overhead_qualification_supported' if qualified else 'observer_overhead_qualification_inconclusive',
                qualified=qualified, rates=panels, all_offers_retained=True, predictive_usefulness_tested=False,
                inference=c.PROTOCOL['inference'], simultaneous_model_intervals='Six 99.5% conditional intervals; Bonferroni family coverage >=97% under the stated assumptions')
