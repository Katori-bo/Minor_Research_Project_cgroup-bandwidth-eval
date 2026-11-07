#!/usr/bin/env python3
"""One bounded, outcome-known stage signal screen; no scientific collection."""
import argparse
from pathlib import Path
import statistics as st

import screen_forecast_reliability as e
import screen_prevalidation_shift as timing
import screen_continuous_persistence as persistence

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_stage_signal/20261010'
STAGES = {'dispatch': ('ScheduledNs', 'DispatchNs'),
          'headers': ('DispatchNs', 'HeadersNs'),
          'body': ('HeadersNs', 'BodyDoneNs')}


def stages(raw, records):
    e.require(len(raw) == len(records), 'Stage count mismatch')
    data = {j: [] for j in STAGES}
    for r, o in zip(raw, records):
        for j, (a, b) in STAGES.items():
            data[j].append(r[b] - r[a] if o['success'] else None)
        if o['success']:
            e.require(sum(data[j][-1] for j in STAGES) == o['e2e_ns'] and
                      all(data[j][-1] >= 0 for j in STAGES), 'Stage telescoping/order')
    return data


def features(ref, warm, ref_stages, warm_stages, deadline):
    """Future outcomes cannot be supplied to this function."""
    full = timing.features(ref, warm, deadline, 5)
    clean = all(x is not None for x in ref + warm)
    scores = {'full_median_temporal': full.get('candidate_score_pp'),
              'deadline_disagreement': abs(timing.miss(ref, deadline) - timing.miss(warm, deadline)),
              'full_ecdf': full.get('ecdf_distance_pp')}
    component = {}
    if clean:
        p0 = timing.miss(ref, deadline)
        project = lambda shift: timing.miss(ref, deadline - shift)
        for j in STAGES:
            baseline = st.median(ref_stages[j])
            delta = st.median(warm_stages[j]) - baseline
            halves = [project(st.median(v) - baseline)
                      for v in (warm_stages[j][:12], warm_stages[j][-12:])]
            component[j] = dict(median_shift_ns=delta,
                projected_shift_pp=abs(project(delta) - p0),
                projected_temporal_pp=abs(halves[0] - halves[1]),
                ecdf_distance_pp=timing.ks(ref_stages[j], warm_stages[j]))
        scores['stage_projected'] = max(max(x['projected_shift_pp'], x['projected_temporal_pp'])
                                        for x in component.values())
        scores['stage_ecdf'] = max(x['ecdf_distance_pp'] for x in component.values())
    else:
        scores.update(stage_projected=None, stage_ecdf=None)
    return dict(scores_pp=scores, stage_features=component,
                predictions_pct={'reference': timing.miss(ref, deadline)},
                accepts={'always': True, **{j: clean and x is not None and x <= 5
                                           for j, x in scores.items()}},
                future_outcomes_used=False, risk_certificate=False)


def compute():
    e.INPUTS.clear()
    for p, digest in e.read(OUT / 'design_sha256.json').items():
        e.require(e.sha(ROOT / p) == digest, 'Stage protocol changed')
        e.INPUTS[p] = digest
    specs = e.read(persistence.OUT / 'design.json')['campaigns']
    prior = e.read(timing.OUT / 'screen.json')['campaigns']
    inputs = []
    for spec in specs:
        base = ROOT / 'analysis' / spec['folder'] / 'generation-01/campaign'
        forecast = e.sealed_read(base / 'forecast/forecast.json', base, 'evidence-seal.json')
        provenance = e.sealed_read(base / 'forecast/provenance.json', base, 'evidence-seal.json')
        e.require(not forecast['validation_used'] and not provenance['validation_used'], 'Forecast used validation')
        e.require(forecast['primary_deadline_ns'] == 20565395, 'Deadline changed')
        ref_records, ref_stages = {}, {}
        for i in range(1, spec['calibration_cohorts'] + 1):
            case = base / f'calibration/cohort-{i}'
            cfg = e.sealed_read(case / 'study-config.json', base, 'evidence-seal.json')
            raw, records = persistence.read_client(base, case, cfg, 'measurement')
            key = cfg['policy'] if spec['name'] == 'NGINX power' else (
                str(cfg['rate_rps']) if spec['name'] == 'NGINX rate' else 'original')
            ref_records.setdefault(key, []).extend(records)
            sj = stages(raw, records)
            for j in STAGES:
                ref_stages.setdefault(key, {}).setdefault(j, []).extend(sj[j])
        for key, records in ref_records.items():
            ordered = sorted(x['e2e_ns'] for x in records if x['success'])
            if spec['name'] == 'NGINX original':
                e.require(ordered == forecast['sorted_samples_ns'], 'Original calibration changed')
            else:
                saved = forecast['references'][key]
                e.require(ordered == saved['successful_samples_ns'] and
                          sum(not x['success'] for x in records) == saved['failed_offers'], 'Reference changed')
        rows = []
        for i in range(1, spec['validation_cohorts'] + 1):
            case = base / f'validation/cohort-{i}'
            cfg = e.sealed_read(case / 'study-config.json', base, 'evidence-seal.json')
            raw, records = persistence.read_client(base, case, cfg, 'warmup')
            e.require(len(records) == 25, 'Warmup count changed')
            key = cfg['policy'] if spec['name'] == 'NGINX power' else (
                '5' if spec['name'] == 'NGINX rate' else 'original')
            ref = [x['e2e_ns'] if x['success'] else None for x in ref_records[key]]
            warm = [x['e2e_ns'] if x['success'] else None for x in records]
            start = e.sealed_read(case / 'trial-start.json', base, 'evidence-seal.json')
            e.require(start['forecast_ref']['sealed_monotonic'] == provenance['sealed_monotonic'] <=
                      start['monotonic'], 'Initial forecast barrier')
            barrier = 'synchronous source acquisition order; no separate warmup boundary stamp'
            elapsed = None
            if spec['name'] != 'NGINX original':
                times = e.sealed_read(case / 'warmup-timing.json', base, 'evidence-seal.json')
                ws = e.sealed_read(case / 'warmup-forecast.json', base, 'evidence-seal.json')
                ms = e.sealed_read(case / 'measurement-start.json', base, 'evidence-seal.json')
                e.require(start['monotonic'] <= times['started_monotonic'] <=
                          times['finished_monotonic'] <= ws['sealed_monotonic'] <= ms['monotonic'],
                          'Warmup forecast boundary differs')
                elapsed = times['finished_monotonic'] - times['started_monotonic']
                barrier = 'saved warmup acquisition/forecast/measurement monotonic stamps'
            rows.append(dict(name=f'cohort-{i}', block=cfg['block'],
                policy=cfg.get('policy', 'uncontrolled-original'),
                rate_rps=1e9 / cfg['interval_ns'],
                features=features(ref, warm, ref_stages[key], stages(raw, records), 20565395),
                availability=dict(barrier=barrier, new_guard_executed_historically=False),
                cost=dict(reference_offers=len(ref), warmup_offers=25,
                    warmup_elapsed_sec=elapsed, scheduled_span_sec=24 * cfg['interval_ns'] / 1e9,
                    acquired_calibration_measurement_offers=400 * spec['calibration_cohorts']),
                case=case, config=cfg))
        inputs.append(dict(name=spec['name'], base=base, rows=rows))
    # Scores for every campaign are fixed before any validation measurement read.
    output = []
    for c in inputs:
        base = c.pop('base')
        historical = next(x for x in prior if x['name'] == (
            'NGINX' if c['name'] == 'NGINX original' else c['name']))
        for row in c['rows']:
            case, cfg = row.pop('case'), row.pop('config')
            _, records = persistence.read_client(base, case, cfg, 'measurement')
            e.require(len(records) == 300, 'Target count changed')
            row['observed_miss_pct'] = 100 * persistence.count(records, 20565395) / 300
            old = next(x for x in historical['rows'] if x['name'] == row['name'])
            e.close(row['observed_miss_pct'], old['observed_miss_pct'])
            e.close(row['features']['predictions_pct']['reference'],
                    old['features']['predictions_pct']['reference'])
            e.require(row['features']['accepts']['full_median_temporal'] ==
                      old['features']['accepts']['shift_and_temporal'], 'Full comparator reconciliation')
        output.append({**c, **timing.summarize(c['rows']),
            'policy_subgroups': {p: timing.summarize([x for x in c['rows'] if x['policy'] == p])
                                for p in sorted({x['policy'] for x in c['rows']})}})
    return dict(role='historical outcome-known development screen', new_collection=False,
                all_scores_before_future_measurement_reads=True, independent_validation=False,
                deadline_ns=20565395, campaigns=output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = compute()
    if args.verify:
        e.require(result == e.read(OUT / 'screen.json'), 'Stage screen recomputation differs')
        for p, digest in e.read(OUT / 'inputs_sha256.json').items():
            e.require(e.sha(ROOT / p) == digest, 'Consumed stage input changed: ' + p)
        for p, digest in e.read(OUT / 'seal.json').items():
            e.require(e.sha(ROOT / p) == digest, 'Stage output changed: ' + p)
        print('Stage protocol, sealed raw inputs, calibration, chronology, historical comparators and recomputation verify.')
        return
    e.require(not (OUT / 'screen.json').exists(), 'Preserve screen; use --verify')
    e.save(OUT / 'screen.json', result)
    sources = [Path(__file__), Path(e.__file__), Path(timing.__file__), Path(persistence.__file__),
               Path(persistence.model.__file__), ROOT / 'diagnostic/nginx_prediction_study.py',
               ROOT / 'diagnostic/nginx_power_confirmation_study.py',
               ROOT / 'diagnostic/nginx_rate_transfer_study.py']
    e.save(OUT / 'inputs_sha256.json', {**e.INPUTS, **{str(p.relative_to(ROOT)): e.sha(p) for p in sources}})
    e.save(OUT / 'seal.json', {str(p.relative_to(ROOT)): e.sha(p) for p in
                             [OUT / 'screen.json', OUT / 'inputs_sha256.json', OUT / 'design_sha256.json']})
    for c in result['campaigns']:
        print(c['name'], c['guards'])


if __name__ == '__main__':
    main()
