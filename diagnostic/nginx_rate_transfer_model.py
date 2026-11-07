"""Ordinary rate CDFs and frozen six-block error comparisons; no fitted guard."""
import statistics as st
import nginx_rate_transfer_common as c
from nginx_power_confirmation_model import outcomes, reference, merge, reference_probability, miss_fraction, interval


def fit(rows, schedule):
    c.require([r['config'] for r in rows] == schedule['calibration'], 'Exact fresh calibration sequence required')
    cohorts = {str(rate): [] for rate in (4, 5, 8)}
    for r in rows:
        c.require(not r['domain_exits'] and len(r['outcomes']) == 400 and
                  r['config']['policy'] == 'P0', 'Invalid calibration')
        cohorts[str(r['config']['rate_rps'])].append(reference(r['outcomes']))
    c.require(all(len(v) == 2 for v in cohorts.values()), 'Two fresh cohorts per rate required')
    refs = {rate: merge(*v) for rate, v in cohorts.items()}
    c.require(all(v['offers'] == 800 for v in refs.values()), 'Reference offer count differs')
    return dict(schema='nginx-rate-transfer-forecast-v1', primary_deadline_ns=20565395,
        references=dict(**refs, pooled=merge(*refs.values())), calibration_cohorts=cohorts,
        validation_used=False, source='only the six fresh calibration cohorts',
        queue_subtraction=False, fixed_policy='P0')


def predictions(forecast, cfg, warmup, deadline):
    c.require(forecast['schema'] == 'nginx-rate-transfer-forecast-v1' and
        forecast['fixed_policy'] == cfg['policy'] == 'P0' and cfg['rate_rps'] in (4, 8) and
        not forecast['validation_used'], 'Foreign forecasting contract')
    c.require(len(warmup) == 25, 'Complete all-offer warmup required')
    refs = forecast['references']; warm = reference(warmup)
    matched, baseline, pooled = refs[str(cfg['rate_rps'])], refs['5'], refs['pooled']
    return {k: reference_probability(v, deadline) for k, v in dict(matched=matched,
        baseline=baseline, pooled=pooled, warmup=warm, matched_update=merge(matched, warm),
        baseline_update=merge(baseline, warm), pooled_update=merge(pooled, warm)).items()}


def compare(rows, forecast, schedule):
    c.require([r['config'] for r in rows] == schedule['validation'], 'Exact full validation sequence required')
    c.require(len(rows) == 12 and all(len(r['outcomes']) == 300 for r in rows),
              'All twelve complete validation cohorts required')
    c.require(not forecast['validation_used'] and forecast['primary_deadline_ns'] == 20565395,
              'Foreign forecast endpoint')
    panels = {}
    for deadline in [20565395, *c.PROTOCOL['secondary_deadlines_ns']]:
        errors = []
        for row in rows:
            cfg = row['config']; predicted = predictions(forecast, cfg, row['warmup_outcomes'], deadline)
            observed = miss_fraction(row['outcomes'], deadline)
            errors.append(dict(config=cfg, observed=observed, predictions=predicted,
                signed_error_pp={k: 100 * (v - observed) for k, v in predicted.items()},
                absolute_error_pp={k: 100 * abs(v - observed) for k, v in predicted.items()}))
        methods = {}
        for method in errors[0]['predictions']:
            blocks = [st.mean(e['absolute_error_pp'][method] for e in errors if e['config']['block'] == b)
                      for b in range(1, 7)]
            methods[method] = dict(**interval(blocks), maximum_error_pp=max(e['absolute_error_pp'][method] for e in errors),
                errors_above_5pp=sum(e['absolute_error_pp'][method] > 5 for e in errors),
                per_rate_mae_pp={str(rate): st.mean(e['absolute_error_pp'][method] for e in errors
                    if e['config']['rate_rps'] == rate) for rate in (4, 8)})
        gain = interval([methods['baseline']['blocks'][i] - methods['matched']['blocks'][i] for i in range(6)])
        contrasts = []
        for block in range(1, 7):
            cell = {e['config']['rate_rps']: e['observed'] for e in errors if e['config']['block'] == block}
            contrasts.append(100 * (cell[8] - cell[4]))
        panels[str(deadline)] = dict(errors=errors, methods=methods, matched_gain_pp=gain,
            observed_8_minus_4_miss_difference_pp=interval(contrasts),
            endpoint_saturated=all(e['observed'] == 0 for e in errors) or all(e['observed'] == 1 for e in errors))
    primary = panels['20565395']; gain = primary['matched_gain_pp']
    accuracy = primary['methods']['matched']['conditional_95_interval'][1] <= 5
    advantage = gain['mean'] >= 2 and gain['conditional_95_interval'][0] > 0
    exits = [dict(config=r['config'], exits=r['domain_exits']) for r in rows if r['domain_exits']]
    status = ('technical_invalid' if exits else 'rate_matching_transfer_supported' if accuracy and advantage
        else 'rate_matched_accuracy_supported_advantage_not_supported' if accuracy
        else 'rate_matching_transfer_not_supported')
    sensitivity = {rate: [dict(predicted=reference_probability(ref, 20565395),
        target_rate_mae_pp=st.mean(100 * abs(reference_probability(ref, 20565395) - e['observed'])
            for e in primary['errors'] if e['config']['rate_rps'] == int(rate))) for ref in refs]
        for rate, refs in forecast['calibration_cohorts'].items() if rate != '5'}
    sensitivity['baseline_5'] = [dict(predicted=reference_probability(ref, 20565395),
        all_target_rate_mae_pp=st.mean(100 * abs(reference_probability(ref, 20565395) - e['observed'])
            for e in primary['errors'])) for ref in forecast['calibration_cohorts']['5']]
    return dict(status=status, primary=primary, secondary={k: v for k, v in panels.items() if k != '20565395'},
        useful_absolute_accuracy=accuracy and not exits, useful_gain=advantage and not exits,
        combined_claim_supported=accuracy and advantage and not exits, domain_exits=exits,
        calibration_cohort_sensitivity=sensitivity,
        calibration_reference_counts={k: dict(offers=v['offers'], failed_offers=v['failed_offers'])
            for k, v in forecast['references'].items()},
        cohort_observations=[{k: r[k] for k in ('config', 'offers', 'successful', 'observations',
            'warmup_counter_delta', 'measurement_counter_delta', 'cpu_per_offer_us',
            'maximum_client_response_overlap', 'mean_stages_ns', 'response_ns',
            'unsuccessful_counts', 'failure_categories') if k in r} for r in rows],
        population=c.PROTOCOL['population'], failure_mass_retained=True, novelty_established=False,
        fixed_frequency=False, independent_host_replication=False, causal_mechanism_identified=False,
        inference_limit='Conditional on fresh calibration; six consecutive block means assume adequate independence. Calibration uncertainty is not propagated. Assigned rate and policy do not measure all physical state; no universal transfer or causal mechanism claim.')
