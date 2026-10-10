"""Descriptive repeated controls, independent recording quality and workload states."""
import statistics
import math
import v24r3_model as retained

validate_samples = retained.validate_samples


def trial(derived, server, anchors, probe, config, design, expected_path):
    row = retained.trial(derived, server, anchors, probe, config, design, expected_path)
    row['order'] = config['order']
    row['repeat'] = config['repeat']
    row['recording_quality_pass'] = True
    if probe is not None:
        for name, phase in row['phases'].items():
            phase['legacy_v24_state_margin_pass'] = phase['state_eligible']
            if name == 'busy':
                phase['state_eligible'] = all(v > 0 for v in phase['queue_minima'])
                phase['state_definition'] = 'guaranteed_positive_waiting_queue'
            else:
                throttle = phase['cpu_delta_bounds'].get('nr_throttled')
                phase['state_eligible'] = (all(v <= 1 for v in phase['queue_maxima'])
                                           and throttle is not None and throttle[1] == 0)
                phase['state_definition'] = 'at_most_one_waiting_job_and_no_throttled_periods'
    return row


METRICS = ('busy_capacity_rps', 'whole_cpu_usec_per_job', 'miss_pct')


def differences(on, off):
    return dict(capacity_pct=100*(on['busy_capacity_rps']-off['busy_capacity_rps'])/off['busy_capacity_rps'],
                cost_pct=100*(on['whole_cpu_usec_per_job']-off['whole_cpu_usec_per_job'])/off['whole_cpu_usec_per_job'],
                miss_pp=on['miss_pct']-off['miss_pct'])


def means(rows):
    return {key: statistics.mean(r[key] for r in rows) for key in METRICS}


def report(trials, design):
    expected = {r['id']: r for r in design['trial_order']}
    ids = [r['trial'] for r in trials]
    if len(set(ids)) != len(ids) or not set(ids) <= set(expected):
        raise ValueError('duplicate or foreign control-screen trial')
    for row in trials:
        slot = expected[row['trial']]
        if (any(row[key] != slot[key] for key in ('size', 'block', 'repeat', 'counter_probe'))
                or row['order'] != slot['collection_order'] or row.get('recording_quality_pass') is not True
                or any(not math.isfinite(row[k]) for k in METRICS)
                or row['busy_capacity_rps'] <= 0 or row['whole_cpu_usec_per_job'] <= 0
                or not 0 <= row['miss_pct'] <= 100):
            raise ValueError('control-screen trial identity/quality differs')
        if row['counter_probe']:
            if (not row.get('measurement_quality', {}).get('pass_budget')
                    or set(row.get('phases', {})) != {'busy', 'low'}):
                raise ValueError('control-screen phase recording quality missing')
        elif 'phases' in row:
            raise ValueError('off trial contains phase counter evidence')
    complete = set(ids) == set(expected)
    result = dict(decision='control_design_screen_complete' if complete else 'control_design_screen_incomplete',
                  complete=complete,recording_quality_pass=complete,accepted_trials=len(trials),planned_trials=16,
                  equivalence_established=False,scientific_explanation_established=False,by_size={},
                  limits='Four trials per condition/size are a bounded diagnostic. Observed repeat differences are not a confidence interval or a universal noise bound. Balanced descriptive contrasts do not establish equivalence or causality. Qualification data are not confirmatory scientific data.')
    if not complete:
        return result
    for size in ('small', 'large'):
        selected = sorted((r for r in trials if r['size'] == size),key=lambda r:r['order'])
        groups = []
        for block in range(1, 5):
            rows = sorted((r for r in selected if r['block'] == block),key=lambda r:r['repeat'])
            if len(rows) != 2 or {r['repeat'] for r in rows} != {1, 2} or len({r['counter_probe'] for r in rows}) != 1:
                raise ValueError('repeat group differs from frozen design')
            groups.append(dict(block=block,counter_probe=rows[0]['counter_probe'],trials=[r['trial'] for r in rows],
                               means=means(rows),signed_repeat_difference=differences(rows[1], rows[0])))
        conditions = {}
        for on in (False, True):
            rows = [r for r in selected if r['counter_probe'] == on]
            if len(rows) != 4:
                raise ValueError('four independent trials per condition required')
            conditions['on' if on else 'off'] = {k:dict(n=4,mean=statistics.mean(r[k] for r in rows),
                sample_sd=statistics.stdev(r[k] for r in rows),minimum=min(r[k] for r in rows),maximum=max(r[k] for r in rows)) for k in METRICS}
        contrasts = []
        for a,b in design['control_analysis']['contrasts']:
            pair = [g for g in groups if g['block'] in (a,b)]
            off = next(g for g in pair if not g['counter_probe'])
            on = next(g for g in pair if g['counter_probe'])
            contrasts.append(dict(blocks=[a,b],order='on_then_off' if on['block'] < off['block'] else 'off_then_on',
                                  on_trials=on['trials'],off_trials=off['trials'],signed_difference=differences(on['means'],off['means'])))
        reference = dict(capacity_pct=100*design['rules']['observer_capacity_relative'],
                         cost_pct=100*design['rules']['observer_cost_relative'],miss_pp=design['rules']['observer_miss_pp'])
        overall = differences(means([r for r in selected if r['counter_probe']]),means([r for r in selected if not r['counter_probe']]))
        repeat_max = {k:max(abs(g['signed_repeat_difference'][k]) for g in groups) for k in reference}
        diagnostic = {}
        for k in reference:
            values = [x['signed_difference'][k] for x in contrasts]
            diagnostic[k] = dict(observed_maximum_repeat_difference=repeat_max[k],
                both_order_contrasts_same_sign=values[0]*values[1]>0,
                both_order_contrasts_exceed_observed_repeat_differences=values[0]*values[1]>0 and all(abs(v)>repeat_max[k] for v in values),
                reference_margin=reference[k],overall_mean_difference_within_reference=abs(overall[k])<=reference[k])
        states = [dict(trial=r['trial'],**{name:p['state_eligible'] for name,p in r['phases'].items()}) for r in selected if r['counter_probe']]
        result['by_size'][size] = dict(condition_summaries=conditions,repeat_groups=groups,order_contrasts=contrasts,
            overall_mean_signed_difference=overall,diagnostics=diagnostic,workload_state_checks=states,
            eligible_on_trials=sum(r['busy'] and r['low'] for r in states))
    return result
