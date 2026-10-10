"""Bounded steady low-state qualification; no busy phase or deadline hypothesis."""
import math
import statistics

import v23_model as queue
import v24r3_model as retained
from kernel_bridge_analysis import clock_join

validate_samples = retained.validate_samples


def trial(derived, server, anchors, probe, config, design, expected_path):
    if not config['counter_probe'] or probe is None:
        raise ValueError('all low-load pilot trials require native counter records')
    samples = validate_samples(probe, expected_path)
    mapping = derived['clocks']
    origin = tuple(mapping['client_test_start_ns'] + mapping['server_minus_client_' + k + '_ns']
                   for k in ('lower', 'upper'))
    joined = clock_join(anchors, mapping, server['clock_generation'])
    host_origin = tuple(mapping['client_test_start_ns'] + joined['kernel_minus_client_' + k + '_ns']
                        for k in ('lower', 'upper'))
    # Establish both endpoints of the whole measurement, then inspect all its gaps.
    for offset in (0, config['duration_sec']):
        retained.counter_bounds(samples, host_origin[0] + offset*1e9, host_origin[1] + offset*1e9)
    relevant = [r for r in samples if r['after_ns'] >= host_origin[0]
                and r['before_ns'] <= host_origin[1] + config['duration_sec']*1e9]
    if any(b['before_ns']-a['after_ns'] > design['sampler']['max_gap_ms']*1e6
           for a, b in zip(relevant, relevant[1:])):
        raise ValueError('measurement counter gap exceeds50ms')
    jobs = server['events']
    q = queue.series([j['admission_ns'] for j in jobs], [j['worker_start_ns'] for j in jobs])
    low = retained.phase(samples, jobs, q, host_origin, origin, design['windows']['low'], False)
    throttle = low['cpu_delta_bounds'].get('nr_throttled')
    low['state_definition'] = 'at_most_one_waiting_job_and_no_throttled_periods'
    low['state_eligible'] = all(v <= 1 for v in low['queue_maxima']) and throttle is not None and throttle[1] == 0
    bounds = low['cpu_usec_per_completion_bounds']
    width = (bounds[1]-bounds[0])/bounds[0] if bounds[0] > 0 else float('inf')
    if width > design['measurement_quality']['max_cost_relative_bound_width']:
        raise ValueError('fixed-window measurement uncertainty exceeds frozen budget')
    whole = derived['summary']['cpu_usec_per_completed_work']
    misses = 100*(1-derived['summary']['timely_500_fraction'])
    if not math.isfinite(whole) or whole <= 0 or not math.isfinite(misses) or not 0 <= misses <= 100:
        raise ValueError('invalid whole-cohort cost or descriptive deadline value')
    return dict(trial=config['trial'], size=config['size'], block=config['block'],
                order=config['order'], repeat=config['repeat'], rate=config['rate'],
                counter_probe=True, recording_quality_pass=True,
                whole_cpu_usec_per_job=whole, miss_pct=misses,
                measurement_quality=dict(cost_relative_bound_width=width, pass_budget=True,
                                         busy_delivery_check='inapplicable_no_busy_phase'),
                acquisition_diagnostics=retained.acquisition_diagnostics(probe),
                phases={'low': low}, sampler_own_cpu_ms=probe['own_cpu_ns']/1e6)


def report(trials, design, collection_complete=True):
    expected = {r['id']: r for r in design['trial_order']}
    ids = [r['trial'] for r in trials]
    if len(set(ids)) != len(ids) or not set(ids) <= set(expected):
        raise ValueError('duplicate or foreign low-load pilot trial')
    for row in trials:
        slot = expected[row['trial']]
        if (row['size'] != 'small' or row['counter_probe'] is not True
                or row['recording_quality_pass'] is not True
                or row['order'] != slot['collection_order']
                or any(row[k] != slot[k] for k in ('rate', 'block', 'repeat'))
                or set(row.get('phases', {})) != {'low'}
                or row.get('measurement_quality', {}).get('pass_budget') is not True
                or not math.isfinite(row['whole_cpu_usec_per_job']) or row['whole_cpu_usec_per_job'] <= 0
                or not math.isfinite(row['miss_pct']) or not 0 <= row['miss_pct'] <= 100):
            raise ValueError('pilot trial identity or recording quality differs')
    recordings_complete = set(ids) == set(expected)
    complete = recordings_complete and collection_complete
    qualified = complete and all(r['phases']['low']['state_eligible'] for r in trials)
    result = dict(decision=('pilot_incomplete' if not complete else
                            'both_low_rates_qualified' if qualified else 'low_state_qualification_failed'),
                  complete=complete, both_low_rates_qualified=qualified,
                  recording_quality_pass=recordings_complete, accepted_trials=len(trials), planned_trials=4,
                  busy_delivery_check='inapplicable_no_busy_phase',
                  scientific_explanation_established=False, equivalence_established=False,
                  novelty_established=False, by_rate={},
                  limits='Two on recordings per rate qualify only fixed steady windows. '
                         'They do not establish future mixed-state eligibility, deadline equivalence, '
                         'causality or statistical uncertainty. No follow-on collection is launched.')
    for rate in design['rates']:
        selected = sorted((r for r in trials if r['rate'] == rate), key=lambda r: r['order'])
        result['by_rate'][str(rate)] = dict(
            planned=2, recorded=len(selected), qualified=sum(r['phases']['low']['state_eligible'] for r in selected),
            trials=[r['trial'] for r in selected],
            whole_cpu_usec_per_job_mean=(statistics.mean(r['whole_cpu_usec_per_job'] for r in selected)
                                        if selected else None),
            descriptive_miss_pct_mean=statistics.mean(r['miss_pct'] for r in selected) if selected else None)
    return result
