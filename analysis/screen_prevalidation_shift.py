#!/usr/bin/env python3
"""Frozen saved-data development screen. No collector, fitting, or host writes."""
import argparse
import bisect
import json
import math
from pathlib import Path
import statistics as st

import screen_forecast_reliability as evidence
import screen_recent_timing_observable as recent

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_prevalidation_shift/20261010'


def miss(values, deadline):
    evidence.require(bool(values), 'Empty all-offer pool')
    return 100 * sum(x is None or x > deadline for x in values) / len(values)


def ks(a, b):
    """Descriptive ECDF sup distance; no iid test or fitted-parameter p-value."""
    a, b = sorted(a), sorted(b)
    evidence.require(bool(a) and bool(b), 'Empty ECDF')
    return 100 * max(abs(bisect.bisect_right(a, x) / len(a) -
                         bisect.bisect_right(b, x) / len(b)) for x in set(a + b))


def quantile(values, q):
    v = sorted(values)
    index = (len(v) - 1) * q
    lo, hi = math.floor(index), math.ceil(index)
    return v[lo] + (index - lo) * (v[hi] - v[lo])


def features(reference, warmup, deadline, tolerance):
    """Only permitted reference and warmup inputs, no future outcomes."""
    w = warmup[-25:]
    evidence.require(len(w) == 25, 'Exact 25-offer candidate budget')
    p0, pw = miss(reference, deadline), miss(w, deadline)
    clean = all(x is not None for x in reference + w)
    predictions = dict(reference=p0, recent25=pw,
                       pooled_update=miss(reference + w, deadline))
    ordinary_drift = abs(miss(w[:12], deadline) - miss(w[-12:], deadline))
    flags = dict(always=True, deadline_disagreement=abs(pw-p0) <= tolerance,
                 ordinary_temporal_disagreement=ordinary_drift <= tolerance)
    if not clean:
        flags.update(shift_and_temporal=False, shift_only=False, temporal_only=False,
                     ecdf_distance=False)
        predictions['location_shift'] = None
        return dict(predictions_pct=predictions, accepts=flags,
                    signal_unavailable_due_to_failure=True)
    delta = st.median(w) - st.median(reference)
    shifted = miss(reference, deadline - delta)
    halves = [miss(reference, deadline - (st.median(v) - st.median(reference)))
              for v in (w[:12], w[-12:])]
    shift_score = abs(shifted - p0)
    temporal_score = abs(halves[0] - halves[1])
    score = max(shift_score, temporal_score)
    raw_ks = ks(reference, w)
    residual_ks = ks(reference, [x - delta for x in w])
    predictions['location_shift'] = shifted
    flags.update(shift_and_temporal=score <= tolerance,
                 shift_only=shift_score <= tolerance,
                 temporal_only=temporal_score <= tolerance,
                 ecdf_distance=raw_ks <= tolerance)
    return dict(predictions_pct=predictions, accepts=flags, median_shift_ns=delta,
                shift_score_pp=shift_score, temporal_score_pp=temporal_score,
                candidate_score_pp=score, ordinary_temporal_score_pp=ordinary_drift,
                ecdf_distance_pp=raw_ks, translated_shape_distance_pp=residual_ks,
                quartile_shift_ns={str(q):quantile(w, q)-quantile(reference, q)
                                   for q in (.25, .5, .75)},
                future_outcomes_used=False, risk_certificate=False)


def nginx_values(path, base, prefix):
    client = evidence.sealed_read(path, base, 'evidence-seal.json')
    rows = client['Rows']
    evidence.require(len(rows) == client['Count'] and
                     [r['ID'] for r in rows] == [f'{prefix}-{i}' for i in range(len(rows))],
                     'NGINX raw all-offer order/count')
    values = [None if r['Error'] or r['DecodeError'] or r['Status'] != 200
              else r['BodyDoneNs'] - r['ScheduledNs'] for r in rows]
    evidence.require(all(x is None or x >= 0 for x in values), 'Negative response time')
    return values, max(r['BodyDoneNs'] for r in rows)/1e9


def collect_inputs():
    campaigns = []
    for campaign in evidence.calibrations():
        reference = [x for c in campaign['cohorts'] for x in c['values_ns']]
        specs = []
        if campaign['name'] == 'Go V31':
            base, saved, cfgs = campaign['validation_metadata']
            for name, cfg in cfgs.items():
                if not name.startswith('v31_b'):
                    continue
                directory = base / saved['trial_refs'][name]['path']
                client = evidence.sealed_read(directory/'warmup.json', directory)
                record = dict(name=name, block=cfg['block'], profile=cfg['profile'],
                              rate_rps=client['target_rate'])
                warmup, cost = recent.warmup(campaign, record)
                specs.append(dict(**record, reference=reference, warmup=warmup, cost=cost,
                                  measurement_path=directory/'loadgen.json', seal_base=directory,
                                  seal_name='seal.json', is_go=True))
        else:
            base = campaign['validation_metadata']
            for i in range(1,19):
                directory = base/f'validation/cohort-{i}'
                cfg = evidence.sealed_read(directory/'study-config.json', base, 'evidence-seal.json')
                record = dict(name=f'cohort-{i}', block=cfg['block'], profile=cfg['profile'],
                              rate_rps=1e9/cfg['interval_ns'])
                warmup, cost = recent.warmup(campaign, record)
                specs.append(dict(**record, reference=reference, warmup=warmup, cost=cost,
                                  measurement_path=directory/'measurement.json', seal_base=base,
                                  seal_name='evidence-seal.json', is_go=False))
        campaigns.append(dict(name=campaign['name'], deadline_ns=campaign['deadline_ns'],
                              calibration_total_offers=len(reference), rows=specs))
    for folder, name, count in [('runtime_io_nginx_power_confirmation', 'NGINX power', 24),
                               ('runtime_io_nginx_rate_transfer', 'NGINX rate', 12)]:
        base = ROOT/'analysis'/folder/'generation-01/campaign'
        forecast = evidence.sealed_read(base/'forecast/forecast.json', base, 'evidence-seal.json')
        evidence.require(not forecast['validation_used'], 'Foreign forecast inputs')
        calibration = evidence.sealed_read(base/'calibration/summary.json', base, 'evidence-seal.json')['rows']
        reconstructed = {}
        for row in calibration:
            cfg = row['config']
            key = cfg['policy'] if name == 'NGINX power' else str(cfg['rate_rps'])
            values, _ = nginx_values(base/f"calibration/cohort-{cfg['index']}/measurement.json", base, 'measurement')
            evidence.require(values == [o['e2e_ns'] if o['success'] else None for o in row['outcomes']],
                             'Calibration raw/summary mismatch')
            reconstructed.setdefault(key, []).extend(values)
        for key, v in reconstructed.items():
            ref = forecast['references'][key]
            evidence.require(sorted(x for x in v if x is not None) == ref['successful_samples_ns'] and
                             sum(x is None for x in v) == ref['failed_offers'], 'Original reference mismatch')
        specs = []
        for i in range(1,count+1):
            directory = base/f'validation/cohort-{i}'
            cfg = evidence.sealed_read(directory/'study-config.json', base, 'evidence-seal.json')
            key = cfg['policy'] if name == 'NGINX power' else '5'
            warmup, span = nginx_values(directory/'warmup.json', base, 'warmup')
            timing = evidence.sealed_read(directory/'warmup-timing.json', base, 'evidence-seal.json')
            start = evidence.sealed_read(directory/'measurement-start.json', base, 'evidence-seal.json')
            evidence.require(timing['started_monotonic'] <= timing['finished_monotonic'] <= start['monotonic'],
                             'Warmup-before-measurement barrier')
            specs.append(dict(name=f'cohort-{i}', block=cfg['block'], profile=cfg['profile'],
                              policy=cfg['policy'], rate_rps=cfg['rate_rps'], reference=reconstructed[key],
                              warmup=warmup, cost=dict(full_offers=len(warmup), last_25_offers=25,
                                full_observed_client_span_sec=span, reference_offers=len(reconstructed[key])),
                              measurement_path=directory/'measurement.json', seal_base=base,
                              seal_name='evidence-seal.json', is_go=False))
        campaigns.append(dict(name=name, deadline_ns=forecast['primary_deadline_ns'],
                              calibration_total_offers=sum(len(v) for v in reconstructed.values()), rows=specs))
    return campaigns


def summarize(rows):
    method_scores = {}
    for name in rows[0]['features']['predictions_pct']:
        errors = [abs(r['features']['predictions_pct'][name]-r['observed_miss_pct'])
                  for r in rows if r['features']['predictions_pct'][name] is not None]
        method_scores[name] = dict(answered=len(errors), mae_pp=st.mean(errors) if errors else None,
                                  maximum_error_pp=max(errors) if errors else None,
                                  errors_above_5pp=sum(e > 5 for e in errors))
    guards = {}
    for name in rows[0]['features']['accepts']:
        accepted = [r for r in rows if r['features']['accepts'][name]]
        rejected = [r for r in rows if not r['features']['accepts'][name]]
        err = lambda r: abs(r['features']['predictions_pct']['reference']-r['observed_miss_pct'])
        errors = [err(r) for r in accepted]
        transition = [r for r in rows if 10 <= r['observed_miss_pct'] <= 90]
        guards[name] = dict(accepted=len(accepted), total=len(rows), coverage_pct=100*len(accepted)/len(rows),
                           accepted_mae_pp=st.mean(errors) if errors else None,
                           maximum_accepted_error_pp=max(errors) if errors else None,
                           bad_accepted=sum(e > 5 for e in errors),
                           bad_accepted_fraction=sum(e > 5 for e in errors)/len(errors) if errors else None,
                           caught_bad=sum(err(r) > 5 for r in rejected),
                           false_warnings=sum(err(r) <= 5 for r in rejected),
                           transition_total=len(transition),
                           transition_coverage_pct=100*sum(r['features']['accepts'][name] for r in transition)/len(transition) if transition else None,
                           useful_screen=bool(errors) and len(accepted)/len(rows) >= .5 and max(errors) <= 5 and
                             (not transition or sum(r['features']['accepts'][name] for r in transition)/len(transition) >= .5),
                           independent_risk_validation=False)
    return dict(predictors=method_scores, guards=guards)


def compute():
    evidence.INPUTS.clear()
    design = evidence.read(OUT/'design.json')
    for path, digest in evidence.read(OUT/'design_sha256.json').items():
        evidence.require(evidence.sha(ROOT/path) == digest, 'Frozen design changed')
        evidence.INPUTS[path] = digest
    inputs = collect_inputs()
    # Complete all feature computations before reading any future measurement windows.
    for campaign in inputs:
        for row in campaign['rows']:
            row['features'] = features(row['reference'], row['warmup'], campaign['deadline_ns'],
                                       design['error_tolerance_pp'])
    output = []
    for campaign in inputs:
        rows = []
        for row in campaign['rows']:
            client = evidence.sealed_read(row['measurement_path'], row['seal_base'], row['seal_name'])
            if row['is_go']:
                raw = client['requests']
                evidence.require(len(raw) == client['total_scheduled'] and len({r['ID'] for r in raw}) == len(raw),
                                 'Go future all-offer conservation')
                values = [None if r['Error'] or r['StatusCode'] != 200 else r['EndToEndLatencyNs'] for r in raw]
            else:
                values, _ = nginx_values(row['measurement_path'], row['seal_base'], 'measurement')
            rows.append({k:row[k] for k in ('name','block','profile','rate_rps','cost','features')} |
                        dict(policy=row.get('policy'), observed_miss_pct=miss(values, campaign['deadline_ns']),
                             measurement_offers=len(values)))
        scored = summarize(rows)
        subgroups = {p:summarize([r for r in rows if r['policy']==p])
                     for p in sorted({r['policy'] for r in rows if r['policy'] is not None})}
        output.append(dict(name=campaign['name'], deadline_ns=campaign['deadline_ns'], rows=rows,
                           calibration_total_offers=campaign['calibration_total_offers'],
                           apparatus_warmup_offers=sum(r['cost']['full_offers'] for r in rows),
                           candidate_consumed_warmup_offers=25*len(rows), **scored, policy_subgroups=subgroups))
    # Reconcile unchanged ordinary references against previous reviewed results.
    old = evidence.read('analysis/runtime_io_recent_timing_observable/20261010/screen.json')
    for campaign, prior in zip(output[:2], old['campaigns']):
        evidence.close(campaign['predictors']['reference']['mae_pp'], prior['methods']['original_reference']['mae_pp'])
    for campaign, folder, method in [(output[2], 'runtime_io_nginx_power_confirmation_review', 'matched'),
                                     (output[3], 'runtime_io_nginx_rate_transfer_review', 'baseline')]:
        prior = evidence.read(f'analysis/{folder}/20261010-generation01/report.json')
        methods = prior['methods'] if 'methods' in prior else prior['primary']['methods']
        evidence.close(campaign['predictors']['reference']['mae_pp'], methods[method]['mean'])
    return dict(role=design['role'], features_computed_before_future_measurement_reads=True,
                new_collection=False, new_estimator=False, independent_validation=False, campaigns=output)


def oracles():
    evidence.close(miss([9,10,11,None],10),50)
    evidence.close(ks([1,2,3],[1,2,3]),0)
    evidence.close(ks([1,1],[2,2]),100)
    ref = list(range(1,26)); warm = [x+3 for x in ref]
    f = features(ref, warm, 15, 5)
    evidence.close(f['median_shift_ns'],3)
    evidence.close(f['predictions_pct']['location_shift'],miss(warm,15))
    evidence.close(f['translated_shape_distance_pp'],0)
    failed = features(ref, [None]+warm[1:],15,5)
    evidence.require(not failed['accepts']['shift_and_temporal'], 'Failed offer must abstain')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true')
    args = parser.parse_args()
    oracles()
    result = compute()
    if args.verify:
        evidence.require(result == evidence.read(OUT/'screen.json'), 'Screen recomputation differs')
        for name, digest in evidence.read(OUT/'inputs_sha256.json').items():
            evidence.require(evidence.sha(ROOT/name) == digest, 'Consumed input changed: '+name)
        for name, digest in evidence.read(OUT/'screen_seal.json').items():
            evidence.require(evidence.sha(ROOT/name) == digest, 'Output changed: '+name)
        print('Frozen design, raw seals, all-offer and shift oracles, prior-result reconciliation and screen recomputation verify.')
        return
    evidence.require(not (OUT/'screen.json').exists(), 'Preserve completed screen; use --verify')
    evidence.save(OUT/'screen.json',result)
    paths = [Path(__file__),Path(evidence.__file__),Path(recent.__file__)]
    evidence.save(OUT/'inputs_sha256.json',{**evidence.INPUTS,**{str(p.relative_to(ROOT)):evidence.sha(p) for p in paths}})
    evidence.save(OUT/'screen_seal.json',{str(p.relative_to(ROOT)):evidence.sha(p) for p in
                                       [OUT/'screen.json',OUT/'inputs_sha256.json']})
    for c in result['campaigns']:
        print(c['name'],json.dumps(dict(predictors=c['predictors'],guards=c['guards']),sort_keys=True))


if __name__ == '__main__':
    main()
