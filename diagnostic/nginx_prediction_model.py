"""All-offer deadline outcomes and sealed calibration-only empirical forecasts."""
from bisect import bisect_right
import math
import statistics as st
import nginx_prediction_common as c


def probability(samples, deadline):
    c.require(samples and all(type(x) is int and x >= 0 for x in samples), 'Invalid CDF samples')
    c.require(type(deadline) is int and deadline >= 0, 'Invalid deadline')
    return (len(samples) - bisect_right(sorted(samples), deadline)) / len(samples)


def outcomes(client, cfg, prefix='measurement'):
    count = cfg['count'] if prefix == 'measurement' else cfg['warmup_count']
    interval = cfg['interval_ns']
    c.require(client['Schema'] == 'nginx-client-v1' and client['Count'] == count and
              client['IntervalNs'] == interval and len(client['Rows']) == count,
              'Study client schedule/count contract differs')
    records = []
    for i, r in enumerate(client['Rows']):
        c.require(r['ID'] == f'{prefix}-{i}' and r['ScheduledNs'] == i * interval,
                  'Missing, duplicate or foreign scheduled offer')
        dropped = r['Error'] == 'client in-flight cap reached'
        if not dropped:
            c.require(r['DispatchNs'] >= r['ScheduledNs'], 'Invalid dispatch timestamp')
        success = (not r['Error'] and not r['DecodeError'] and r['Status'] == 200 and
            r['EchoID'] == r['ID'] and r['ContentEncoding'] == 'gzip' and
            r['ContentType'] == 'application/x-ndjson' and r['DecodedBytes'] == 1048576 and
            r['DecodedSHA256'] == c.n.INPUT_SHA and 0 < r['BodyBytes'] <= 2097152)
        if success:
            c.require(r['ScheduledNs'] <= r['DispatchNs'] <= r['HeadersNs'] <= r['BodyDoneNs'],
                      'Invalid complete-response milestones')
        records.append(dict(id=r['ID'], success=success, dropped=dropped,
            e2e_ns=r['BodyDoneNs'] - r['ScheduledNs'] if success else None,
            dispatch_lag_ns=None if dropped else r['DispatchNs'] - r['ScheduledNs'],
            response_headers_observed=r['Status'] > 0))
    return records


def miss_fraction(records, deadline):
    c.require(records, 'Empty all-offer outcome')
    return sum(not r['success'] or r['e2e_ns'] > deadline for r in records) / len(records)


def fit(cohorts):
    c.require(len(cohorts) == 4 and [x['config'] for x in cohorts] == c.configs('calibration'),
              'Exact fresh calibration cohorts required; no pilot/validation fitting')
    samples, by_cohort = [], []
    for value in cohorts:
        c.require(not value['domain_exits'] and all(r['success'] for r in value['outcomes']),
                  'Calibration unavailable: unsuccessful offer or applicability exit')
        cohort = [r['e2e_ns'] for r in value['outcomes']]
        c.require(len(cohort) == 400, 'Calibration sample count differs')
        samples.extend(cohort); by_cohort.append(cohort)
    samples.sort()
    deadline = samples[(len(samples) - 1) // 2]
    deadlines = sorted(set([deadline, *c.PROTOCOL['secondary_deadlines_ns']]))
    return dict(schema='nginx-forecast-v1', primary_deadline_ns=deadline,
        sample_count=len(samples), sorted_samples_ns=samples,
        predictions={str(d): probability(samples, d) for d in deadlines},
        primary_cohort_miss_fractions=[probability(s, deadline) for s in by_cohort],
        calibration_uncertainty='Per-cohort sensitivity is descriptive; requests are not independent calibration replications.',
        rate_invariant_forecast=True, validation_used=False, queue_subtraction=False)


def compare(rows, forecast):
    c.require([r['config'] for r in rows] == c.configs('validation'), 'Exact balanced validation sequence required')
    deadline = forecast['primary_deadline_ns']
    predicted = forecast['predictions'][str(deadline)]
    errors, blocks = [], []
    for r in rows:
        observed = miss_fraction(r['outcomes'], deadline)
        errors.append(dict(block=r['config']['block'], profile=r['config']['profile'],
            observed_miss_fraction=observed, predicted_miss_fraction=predicted,
            signed_error_pp=100 * (predicted - observed), absolute_error_pp=100 * abs(predicted - observed)))
    for b in range(1, 7):
        blocks.append(st.mean(x['absolute_error_pp'] for x in errors if x['block'] == b))
    mean = st.mean(blocks)
    margin = c.PROTOCOL['block_t_multiplier'] * st.stdev(blocks) / math.sqrt(6)
    upper = mean + margin
    exits = [dict(config=r['config'], exits=r['domain_exits']) for r in rows if r['domain_exits']]
    rate_errors = {p: st.mean(x['absolute_error_pp'] for x in errors if x['profile'] == p) for p in 'ABC'}
    passed = upper <= c.PROTOCOL['primary_accuracy_upper_bound_pp'] and not exits
    sensitivity = [st.mean(100 * abs(x['observed_miss_fraction'] - alt) for x in errors)
                   for alt in forecast['primary_cohort_miss_fractions']]
    return dict(status='full_response_prediction_accuracy_supported' if passed else
        ('scientific_applicability_exit' if exits else 'full_response_prediction_accuracy_not_supported'),
        primary_deadline_ns=deadline, predicted_miss_fraction=predicted, errors=errors,
        mean_block_mae_pp=mean, block_mae_pp=blocks,
        conditional_model_based_95_interval_pp=[mean - margin, upper],
        conditional_accuracy_upper_le_5pp=upper <= 5,
        per_profile_mae_pp=rate_errors, calibration_cohort_sensitivity_mae_pp=sensitivity,
        secondary_deadlines={str(d): dict(predicted=forecast['predictions'][str(d)],
            observed_by_trial=[miss_fraction(r['outcomes'], d) for r in rows])
            for d in c.PROTOCOL['secondary_deadlines_ns']},
        domain_exits=exits, scientific_collection=True, queue_observed=False,
        novelty_established=False, independent_host_replication=False,
        inference_limit='The t interval conditions on the sealed forecast and assumes approximately independent normal block means. It does not propagate calibration uncertainty or prove a population guarantee. Cohort sensitivity and per-rate errors must accompany the primary result.')
