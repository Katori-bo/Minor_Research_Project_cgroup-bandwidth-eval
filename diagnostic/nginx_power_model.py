"""Ordinary forecasts, all-offer errors and six-block contrasts; no tuned model."""
import itertools
import math
import statistics as st
import nginx_power_common as c
import nginx_prediction_model as original

outcomes = original.outcomes
probability = original.probability
miss_fraction = original.miss_fraction


def fit(rows, schedule):
    c.require([r['config'] for r in rows] == schedule['calibration'], 'Fresh calibration sequence required')
    samples = {'P0': [], 'P1': []}
    for r in rows:
        c.require(not r['domain_exits'] and len(r['outcomes']) == 400 and
                  all(o['success'] for o in r['outcomes']), 'Invalid calibration')
        samples[r['config']['policy']].extend(o['e2e_ns'] for o in r['outcomes'])
    c.require(all(len(v) == 800 for v in samples.values()), 'Two cohorts per policy required')
    return dict(schema='nginx-power-forecast-v1', primary_deadline_ns=20565395,
        samples_ns={k: sorted(v) for k, v in samples.items()},
        pooled_samples_ns=sorted(samples['P0'] + samples['P1']), validation_used=False,
        source='only the four fresh calibration cohorts', queue_subtraction=False)


def predictions(forecast, cfg, warmup, deadline):
    c.require(len(warmup) == 25 and all(o['success'] for o in warmup), 'Complete warmup required')
    pooled = forecast['pooled_samples_ns']
    matched = forecast['samples_ns'][cfg['policy']]
    warm = [o['e2e_ns'] for o in warmup]
    return {k: probability(v, deadline) for k, v in dict(pooled=pooled, matched=matched,
        baseline=forecast['samples_ns']['P0'], warmup=warm,
        matched_update=matched + warm, pooled_update=pooled + warm).items()}


def interval(values):
    c.require(len(values) == 6, 'Six block replication units required')
    mean = st.mean(values)
    half = 2.571 * st.stdev(values) / math.sqrt(6)
    return dict(mean=mean, conditional_95_interval=[mean - half, mean + half], blocks=values)


def compare(rows, forecast, schedule):
    c.require([r['config'] for r in rows] == schedule['validation'], 'Exact full validation sequence required')
    c.require(not forecast['validation_used'] and forecast['primary_deadline_ns'] == 20565395,
              'Foreign forecast endpoint')
    panels = {}
    for deadline in [20565395, *c.PROTOCOL['secondary_deadlines_ns']]:
        errors = []
        for r in rows:
            cfg = r['config']; pred = predictions(forecast, cfg, r['warmup_outcomes'], deadline)
            observed = miss_fraction(r['outcomes'], deadline)
            errors.append(dict(config=cfg, observed=observed, predictions=pred,
                signed_error_pp={k: 100 * (v - observed) for k, v in pred.items()},
                absolute_error_pp={k: 100 * abs(v - observed) for k, v in pred.items()}))
        methods = {}
        for method in errors[0]['predictions']:
            blocks = [st.mean(e['absolute_error_pp'][method] for e in errors
                              if e['config']['block'] == b) for b in range(1, 7)]
            methods[method] = dict(**interval(blocks), maximum_error_pp=max(
                e['absolute_error_pp'][method] for e in errors), errors_above_5pp=sum(
                e['absolute_error_pp'][method] > 5 for e in errors),
                per_cell_mae_pp={f'{p}-{r}': st.mean(e['absolute_error_pp'][method] for e in errors
                    if e['config']['policy'] == p and e['config']['rate_rps'] == r) for p, r in c.CELLS})
        gain = interval([methods['pooled']['blocks'][i] - methods['matched']['blocks'][i]
                         for i in range(6)])
        pairs = []; effect = []; interactions = []
        for b in range(1, 7):
            cell = {(e['config']['policy'], e['config']['rate_rps']): e['observed']
                    for e in errors if e['config']['block'] == b}
            d4 = 100 * (cell['P1', 4] - cell['P0', 4])
            d8 = 100 * (cell['P1', 8] - cell['P0', 8])
            pairs.extend([d4, d8]); effect.append((d4 + d8) / 2)
            interactions.append(d8 - d4)
        # Condition on rate positions: each within-rate policy assignment has
        # two equally likely permutations. Exact test of the sharp policy null.
        observed_stat = abs(st.mean(pairs))
        count = sum(abs(st.mean(x * s for x, s in zip(pairs, signs))) >= observed_stat - 1e-12
                    for signs in itertools.product((-1, 1), repeat=12))
        panels[str(deadline)] = dict(errors=errors, methods=methods, matched_gain_pp=gain,
            assigned_policy_miss_difference_pp=interval(effect), rate_interaction_pp=interval(interactions),
            conditional_sharp_null_randomization_p=count / 4096,
            randomization_assumptions='Condition on rate positions; no policy interference/carryover; sharp null. Ten-second settling does not verify these assumptions.')
    primary = panels['20565395']; gain = primary['matched_gain_pp']
    useful_gain = gain['mean'] >= 2 and gain['conditional_95_interval'][0] > 0
    useful_accuracy = primary['methods']['matched']['conditional_95_interval'][1] <= 5
    exits = [dict(config=r['config'], exits=r['domain_exits']) for r in rows if r['domain_exits']]
    return dict(status='policy_matching_forecast_feasibility_supported' if useful_gain and
        useful_accuracy and not exits else ('domain_exit' if exits else 'policy_matching_forecast_feasibility_not_supported'),
        primary=primary, secondary={k: v for k, v in panels.items() if k != '20565395'},
        useful_gain=useful_gain, useful_absolute_accuracy=useful_accuracy, domain_exits=exits,
        novelty_established=False, fixed_frequency=False, independent_host_replication=False,
        causal_mechanism_identified=False, inference_limit='Six consecutive blocks; conditional t intervals assume sufficient block independence. Calibration uncertainty is not propagated; policy readback is not physical frequency evidence; carryover/shared-package/client effects remain possible.')
