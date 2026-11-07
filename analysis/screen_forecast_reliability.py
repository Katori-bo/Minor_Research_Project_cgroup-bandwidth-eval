#!/usr/bin/env python3
"""Bounded retrospective reliability screen; stdlib only, no collection or fitting."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import statistics as st

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_forecast_reliability/20261010'
INPUTS = {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    path = ROOT / path if isinstance(path, str) else path
    INPUTS[str(path.relative_to(ROOT))] = sha(path)
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def close(a, b):
    require(math.isclose(a, b, abs_tol=1e-9, rel_tol=1e-12), f'{a} differs from {b}')


def sealed_read(path, directory, seal_name='seal.json'):
    seal = read(directory / seal_name)['files_sha256']
    name = str(path.relative_to(directory))
    require(name in seal and sha(path) == seal[name], 'Original input seal mismatch: ' + name)
    return read(path)


def probability(values, deadline):
    require(bool(values), 'Empty probability pool')
    ordered = sorted(values)
    by_bisect = 100 * (len(ordered) - bisect.bisect_right(ordered, deadline)) / len(ordered)
    by_count = 100 * sum(x > deadline for x in values) / len(values)
    close(by_bisect, by_count)
    return by_bisect


def calibrations():
    base = ROOT / 'analysis/runtime_io_v31/generation-01'
    fit = sealed_read(base / 'predictions/calibration.json', base / 'predictions')
    saved = read(base / 'analysis/1791544686930410674/report.json')
    design = read('analysis/runtime_io_v31_design/20261009/design.json')
    configs = {x['trial']: x for x in design['calibration_configs'] + design['validation_configs']}
    cohorts = []
    # Cohort starts have monotonic timestamps in retained names; preserve actual chronology.
    names = sorted(fit['timing_cohorts'], key=lambda n: int(saved['trial_refs'][n]['path'].rsplit('-', 1)[1]))
    for name in names:
        directory = base / saved['trial_refs'][name]['path']
        client = sealed_read(directory / 'loadgen.json', directory)
        obs = sealed_read(directory / 'observations.json', directory)
        rows = client['requests']
        require(len(rows) == client['total_scheduled'] and len({r['ID'] for r in rows}) == len(rows), 'Go calibration IDs')
        require(all(not r['Error'] and r['StatusCode'] == 200 for r in rows), 'Unsuccessful Go calibration')
        values = [r['EndToEndLatencyNs'] for r in rows]
        throttle = obs['measurement_stop']['cpu_stat']['nr_throttled'] - obs['measurement_start']['cpu_stat']['nr_throttled']
        cohorts.append(dict(name=name, values_ns=values, rate_rps=client['target_rate'], throttle=throttle))
    go = dict(name='Go V31', deadline_ns=10000000, cohorts=cohorts,
              validation_metadata=(base, saved, configs), endpoint='scheduled offer through client completion after body consumption/close')
    base_n = ROOT / 'analysis/runtime_io_nginx_prediction/generation-01/campaign'
    forecast = sealed_read(base_n / 'forecast/forecast.json', base_n, 'evidence-seal.json')
    cohorts_n = []
    for i in range(1, 5):
        directory = base_n / f'calibration/cohort-{i}'
        rows = sealed_read(directory / 'measurement.json', base_n, 'evidence-seal.json')['Rows']
        result = sealed_read(directory / 'result.json', base_n, 'evidence-seal.json')
        require(len(rows) == 400 and all(not r['Error'] and r['Status'] == 200 and not r['DecodeError'] for r in rows), 'NGINX calibration outcomes')
        cohorts_n.append(dict(name=f'cohort-{i}', values_ns=[r['BodyDoneNs'] - r['ScheduledNs'] for r in rows],
                              rate_rps=5, throttle=result['measurement_counter_delta']['nr_throttled']))
    pooled_n = sorted(x for cohort in cohorts_n for x in cohort['values_ns'])
    require(pooled_n == forecast['sorted_samples_ns'] and pooled_n[(len(pooled_n)-1)//2] == forecast['primary_deadline_ns'], 'NGINX calibration replay differs')
    nginx = dict(name='NGINX', deadline_ns=forecast['primary_deadline_ns'], cohorts=cohorts_n,
                 validation_metadata=base_n, endpoint='scheduled offer through complete encoded-body receipt, correctness checked afterward')
    require(sum(len(c['values_ns']) for c in cohorts) == 676, 'Go complete-response pool differs')
    return go, nginx


def diagnostics(campaign, plan):
    cohorts = campaign['cohorts']
    deadline = campaign['deadline_ns']
    pool = [x for c in cohorts for x in c['values_ns']]
    p = probability(pool, deadline)
    probabilities = [probability(c['values_ns'], deadline) for c in cohorts]
    half = plan['cohort_t_multiplier_df3'] * st.stdev(probabilities) / math.sqrt(len(probabilities))
    stress = []
    for offset in plan['stress_offsets_ns']:
        lower = probability(pool, deadline - offset)
        upper = probability(pool, deadline + offset)
        stress.append(dict(offset_ns=offset, earlier_deadline_probability_pct=lower,
                           later_deadline_probability_pct=upper, maximum_one_sided_change_pp=max(lower-p, p-upper)))
    folds = []
    for j in range(1, len(cohorts)):
        prefix = [x for c in cohorts[:j] for x in c['values_ns']]
        fold_deadline = deadline if campaign['name'] == 'Go V31' else sorted(prefix)[(len(prefix)-1)//2]
        prediction = probability(prefix, fold_deadline)
        observed = probability(cohorts[j]['values_ns'], fold_deadline)
        folds.append(dict(training_cohorts=j, target_cohort=cohorts[j]['name'], deadline_ns=fold_deadline,
                          predicted_pct=prediction, observed_pct=observed, error_pp=abs(prediction-observed)))
    return dict(name=campaign['name'], endpoint=campaign['endpoint'], deadline_ns=deadline,
                samples=len(pool), calibration_cohorts=[dict(name=c['name'], samples=len(c['values_ns']),
                rate_rps=c['rate_rps'], median_ms=st.median(c['values_ns'])/1e6,
                miss_pct=probabilities[i], recorded_throttle_periods=c['throttle']) for i,c in enumerate(cohorts)],
                pooled_forecast_pct=p, equal_cohort_mean_pct=st.mean(probabilities),
                cohort_range_pp=max(probabilities)-min(probabilities),
                max_cohort_deviation_from_pooled_pp=max(abs(x-p) for x in probabilities),
                descriptive_cohort_t_halfwidth_pp=half,
                iid_dkw_halfwidth_pp=100*math.sqrt(math.log(40)/(2*len(pool))),
                timing_rate_support_rps=[min(c['rate_rps'] for c in cohorts), max(c['rate_rps'] for c in cohorts)],
                deadline_stress=stress, chronological_calibration_folds=folds,
                maximum_chronological_calibration_error_pp=max(f['error_pp'] for f in folds),
                calibration_no_recorded_throttle=all(c['throttle']==0 for c in cohorts),
                legitimate_future_risk_certificate=False)


def validation(campaign):
    metadata = campaign['validation_metadata']
    records = []
    if campaign['name'] == 'Go V31':
        base, saved, configs = metadata
        for name, cfg in configs.items():
            if not name.startswith('v31_b'):
                continue
            directory = base / saved['trial_refs'][name]['path']
            client = sealed_read(directory / 'loadgen.json', directory)
            rows = client['requests']
            n = client['total_scheduled']
            require(n == len(rows) and len({r['ID'] for r in rows}) == n, 'Go validation all-offer conservation')
            misses = sum(bool(r['Error']) or r['StatusCode']!=200 or r['EndToEndLatencyNs']>campaign['deadline_ns'] for r in rows)
            records.append(dict(name=name, block=cfg['block'], profile=cfg['profile'], rate_rps=client['target_rate'], offers=n, observed_miss_pct=100*misses/n))
    else:
        base = metadata
        for i in range(1, 19):
            directory = base / f'validation/cohort-{i}'
            rows = sealed_read(directory / 'measurement.json', base, 'evidence-seal.json')['Rows']
            result = sealed_read(directory / 'result.json', base, 'evidence-seal.json')
            cfg = result['config']
            require(len(rows)==300 and len({r['ID'] for r in rows})==300, 'NGINX validation all-offer conservation')
            misses = sum(bool(r['Error']) or bool(r['DecodeError']) or r['Status']!=200 or r['BodyDoneNs']-r['ScheduledNs']>campaign['deadline_ns'] for r in rows)
            records.append(dict(name=f'cohort-{i}', block=cfg['block'], profile=cfg['profile'], rate_rps=1e9/cfg['interval_ns'], offers=len(rows), observed_miss_pct=100*misses/len(rows)))
    require(len(records)==18 and len({r['block'] for r in records})==6, 'Retain all 18 cohorts and six blocks')
    return sorted(records,key=lambda r:(r['block'],r['name']))


def score(records, p, decisions, tolerance):
    accepted = [r for r, accept in zip(records, decisions) if accept]
    errors = [abs(p-r['observed_miss_pct']) for r in accepted]
    return dict(accepted_cohorts=len(accepted), total_cohorts=len(records), answer_coverage_pct=100*len(accepted)/len(records),
                accepted_mae_pp=st.mean(errors) if errors else None, maximum_accepted_error_pp=max(errors) if errors else None,
                accepted_errors_above_tolerance=sum(e>tolerance for e in errors),
                descriptive_bad_accepted_fraction=sum(e>tolerance for e in errors)/len(errors) if errors else None,
                risk_certificate=False)


def assess(campaign, diag, records, plan):
    tau = plan['error_tolerance_pp']
    n = len(records)
    stress = next(s for s in diag['deadline_stress'] if s['offset_ns']==plan['illustrative_stress_rule_offset_ns'])
    lo, hi = diag['timing_rate_support_rps']
    decisions = dict(always_forecast=[True]*n,
        calibration_zero_throttle_only=[diag['calibration_no_recorded_throttle']]*n,
        timing_rate_support=[lo <= r['rate_rps'] <= hi for r in records],
        cohort_agreement=[diag['max_cohort_deviation_from_pooled_pp']<=tau]*n,
        descriptive_cohort_t_precision=[diag['descriptive_cohort_t_halfwidth_pp']<=tau]*n,
        iid_dkw_precision_illustration=[diag['iid_dkw_halfwidth_pp']<=tau]*n,
        bounded_shift_100us_illustration=[stress['maximum_one_sided_change_pp']<=tau]*n,
        chronological_calibration_check=[diag['maximum_chronological_calibration_error_pp']<=tau]*n)
    results = {k:score(records,diag['pooled_forecast_pct'],v,tau) for k,v in decisions.items()}
    prefixes = []
    for j in range(1,5):
        pool = [x for c in campaign['cohorts'][:j] for x in c['values_ns']]
        p = probability(pool,campaign['deadline_ns'])
        prefixes.append(dict(calibration_cohorts=j,samples=len(pool),predicted_miss_pct=p,
                            **score(records,p,[True]*n,tau)))
    errors = [{**r,'error_pp':abs(diag['pooled_forecast_pct']-r['observed_miss_pct'])} for r in records]
    blocks = [dict(block=b,mae_pp=st.mean(r['error_pp'] for r in errors if r['block']==b)) for b in range(1,7)]
    profiles = [dict(profile=p,mae_pp=st.mean(r['error_pp'] for r in errors if r['profile']==p)) for p in 'ABC']
    close(st.mean(b['mae_pp'] for b in blocks),results['always_forecast']['accepted_mae_pp'])
    if campaign['name']=='Go V31':
        retained = read('analysis/runtime_io_deadline_extension_reviewer_assessment/20261010/report.json')['whole_response_cdf_primary']
        close(diag['pooled_forecast_pct'],retained['forecast_miss_pct']);close(results['always_forecast']['accepted_mae_pp'],retained['mae_pp'])
        prior = read('analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
        for r in records:
            match=next(x for x in prior['validation'] if x['trial']==r['name'])
            close(r['observed_miss_pct'],match['observed_miss_pct']['10'])
    else:
        retained = sealed_read(campaign['validation_metadata']/'comparison.json',campaign['validation_metadata'],'evidence-seal.json')
        close(results['always_forecast']['accepted_mae_pp'],retained['mean_block_mae_pp'])
        for r in records:
            match=next(x for x in retained['errors'] if x['block']==r['block'] and x['profile']==r['profile'])
            close(r['observed_miss_pct'],100*match['observed_miss_fraction'])
    return dict(calibration=diag,baselines=results,validation=errors,blocks=blocks,profiles=profiles,calibration_prefixes=prefixes)


def compute():
    INPUTS.clear()
    plan=read(OUT/'design.json')
    for name,h in read(OUT/'design_sha256.json').items():
        require(sha(ROOT/name)==h,'Discovery plan changed after screen declaration')
        INPUTS[name]=h
    campaigns=calibrations()
    # These features depend only on permissible calibration/configuration inputs.
    features=[diagnostics(c,plan) for c in campaigns]
    assessments=[assess(c,d,validation(c),plan) for c,d in zip(campaigns,features)]
    return dict(role='retrospective_discovery_not_fresh_validation',future_risk_established=False,
        new_estimator=False,new_collection=False,campaigns=assessments,
        count_illustrations=dict(iid_cdf_samples_for_5pp_95pct=math.ceil(math.log(40)/(2*.05**2)),
          zero_failure_accepted_episodes_for_one_sided_95_upper_risk_le_5pct=math.ceil(math.log(.05)/math.log(.95)),
          upper_risk_with_two_zero_failure_independent_episodes=1-.05**.5,
          minimum_error_calibration_episodes_for_finite_95_split_conformal_quantile=19,
          actual_exchangeable_history_to_future_error_calibration_episodes_established=0))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    # Strict > deadline includes equality as timely. These are relevant numerical oracles.
    close(probability([9,10,10,11],10),25)
    result=compute()
    if args.verify:
        require(result==json.loads((OUT/'screen.json').read_text()),'Recomputed screen differs')
        for name,h in json.loads((OUT/'inputs_sha256.json').read_text()).items():
            require(sha(ROOT/name)==h,'Consumed input changed: '+name)
        for name,h in json.loads((OUT/'screen_seal.json').read_text()).items():
            require(sha(ROOT/name)==h,'Screen output changed: '+name)
        print('Screen recomputation, original consumed-input seals, CDF counting oracles and saved-result reconciliation pass.')
        return
    require(not (OUT/'screen.json').exists(),'Preserve completed screen; use --verify')
    save(OUT/'screen.json',result)
    save(OUT/'calibration_features.json',[c['calibration'] for c in result['campaigns']])
    save(OUT/'inputs_sha256.json',{**INPUTS,str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))})
    save(OUT/'screen_seal.json',{str(p.relative_to(ROOT)):sha(p) for p in
         [OUT/'screen.json',OUT/'calibration_features.json',OUT/'inputs_sha256.json']})
    for c in result['campaigns']:
        d=c['calibration']
        print(d['name'], 'forecast',round(d['pooled_forecast_pct'],3),'range',round(d['cohort_range_pp'],3),
              'max deviation',round(d['max_cohort_deviation_from_pooled_pp'],3),
              't half',round(d['descriptive_cohort_t_halfwidth_pp'],3),'DKW half',round(d['iid_dkw_halfwidth_pp'],3))
        print('stress',[(s['offset_ns'],round(s['maximum_one_sided_change_pp'],3)) for s in d['deadline_stress']])
        print('chronological',[round(x['error_pp'],3) for x in d['chronological_calibration_folds']])
        print('baselines',[(k,v['accepted_cohorts'],v['accepted_errors_above_tolerance']) for k,v in c['baselines'].items()])


if __name__=='__main__':
    main()
