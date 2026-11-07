#!/usr/bin/env python3
"""Fixed saved-data SLO decision audit; no collection, fitting or manuscript edit."""
import argparse
from fractions import Fraction
import functools
import hashlib
import json
import math
from pathlib import Path
import statistics as st
import sys

import screen_forecast_reliability as e
import screen_deadline_sensitivity as sensitivity
import screen_recent_timing_observable as recent
from worker_wait_precision_cost import beta_cdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/runtime_io_slo_decision/20261011'
PROTOCOL = ROOT / 'docs/runtime_io_slo_decision_protocol_20261011.md'
BUDGET = Fraction(1, 20)
TOLERANCE = Fraction(1, 20)
QUANTILES = ['9/10', '19/20', '39/40', '99/100', '199/200']
EXPECTED = {'Go V31': 18, 'NGINX original': 18, 'NGINX power': 24,
            'NGINX rate': 12, 'NGINX panel': 24}


def dump(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write('\n')


def values_valid(values):
    e.require(values and all(x is None or type(x) is int and x >= 0 for x in values),
              'Missing pool or invalid response duration')


def miss_count(values, deadline):
    values_valid(values)
    e.require(type(deadline) is int and deadline >= 0, 'Finite integer deadline required')
    return sum(x is None or x > deadline for x in values)


def miss(values, deadline):
    return Fraction(miss_count(values, deadline), len(values))


def quantile_cutoff(values, q):
    values_valid(values)
    q = Fraction(q)
    e.require(0 < q <= 1, 'Invalid calibration quantile')
    rank = math.ceil(q * len(values)) - 1
    finite = sorted(x for x in values if x is not None)
    return dict(quantile=str(q), rank=rank,
                deadline_ns=finite[rank] if rank < len(finite) else None)


def decide(p):
    return 'meets' if p <= BUDGET else 'exceeds'


def band_decide(lo, hi):
    e.require(0 <= lo <= hi <= 1, 'Invalid probability band')
    return 'meets' if hi <= float(BUDGET) else 'exceeds' if lo > float(BUDGET) else 'inconclusive'


def beta_quantile(a, b, probability):
    lo, hi = 0., 1.
    for _ in range(65):
        middle = (lo + hi) / 2
        if beta_cdf(a, b, middle) < probability:
            lo = middle
        else:
            hi = middle
    return (lo + hi) / 2


@functools.lru_cache(None)
def binomial_interval(k, n, alpha=.05):
    e.require(type(k) is int and type(n) is int and 0 <= k <= n and n > 0
              and 0 < alpha < 1, 'Invalid binomial input')
    lo = 0. if k == 0 else beta_quantile(k, n-k+1, alpha/2)
    hi = 1. if k == n else beta_quantile(k+1, n-k, 1-alpha/2)
    return [lo, hi]


def forecast(reference, warmup, alternatives, deadline):
    """Target outcomes cannot be supplied to the forecast builder."""
    e.require(len(warmup) == 25, 'Exact consumed warmup budget')
    pools = dict(reference=reference, recent25=warmup,
                 weighted_update=reference + warmup, **alternatives)
    result = {}
    for name, values in pools.items():
        p = miss(values, deadline)
        epsilon = math.sqrt(math.log(40) / (2*len(values)))
        lo, hi = max(0., float(p)-epsilon), min(1., float(p)+epsilon)
        result[name] = dict(misses=p.numerator, denominator=p.denominator,
            actual_reference_misses=miss_count(values, deadline), reference_offers=len(values),
            predicted_pct=float(100*p), point_decision=decide(p),
            iid_dkw95_band_pct=[100*lo, 100*hi], iid_dkw_decision=band_decide(lo, hi),
            decision_time='after last 25 warmup offers' if name in ['recent25', 'weighted_update']
                          else 'after calibration, before target warmup',
            transfer_guarantee=False, target_outcomes_used=False)
    return result


def load_specs():
    specs = []
    # The helper reconstructs all 78 NGINX references/warmups and saved barriers.
    for spec in sensitivity.load_specs():
        name = spec['campaign']
        alternatives = {}
        if spec['extra_reference'] is not None:
            alternatives['rate_matched'] = spec['extra_reference']
        if name in ['NGINX power', 'NGINX panel']:
            saved = e.sealed_read(spec['base'] / 'forecast/forecast.json', spec['base'], 'evidence-seal.json')
            pools = [saved['references'][p] for p in ['P0', 'P1']]
            alternatives['pooled_policy'] = [x for pool in pools for x in
                [*pool['successful_samples_ns'], *([None]*pool['failed_offers'])]]
        cfg = spec['config']
        cutoffs = [dict(label='historical', deadline_ns=20565395, selection='historical fixed endpoint')]
        if name == 'NGINX panel':
            cutoffs += [dict(**p, label='original_panel/' + p['quantile'],
                             selection='original frozen lower-order rank') for p in spec['panel']]
        cutoffs += [dict(**quantile_cutoff(spec['reference'], q), label='slo_grid/' + q,
                         selection='new calibration-only nearest rank; development') for q in QUANTILES]
        specs.append(dict(campaign=name, name=spec['case'].split('/')[-1], config=cfg,
            reference=spec['reference'], warmup=spec['warmup'], alternatives=alternatives,
            cutoffs=cutoffs, acquired_calibration_offers=spec['acquired_calibration_offers'],
            acquired_validation_warmup_offers=25,
            calibration_warmup_offers=100 if name != 'NGINX rate' else 150,
            base=spec['base'], case=spec['case'], go=False))
    go, _ = e.calibrations()
    reference = [x for group in go['cohorts'] for x in group['values_ns']]
    base, saved, configs = go['validation_metadata']
    for name, cfg in configs.items():
        if not name.startswith('v31_b'):
            continue
        case = base / saved['trial_refs'][name]['path']
        record = dict(name=name, rate_rps=cfg['rate'] if 'rate' in cfg else cfg['rate_rps'])
        # Preserve ID chronology; no target rows are loaded by this helper.
        warmup, cost = recent.warmup(go, record)
        cutoffs = [dict(label='historical/' + str(d), deadline_ns=d*1000000,
                       selection='original primary' if d == 10 else 'original secondary') for d in [10, 11, 12]]
        cutoffs += [dict(**quantile_cutoff(reference, q), label='slo_grid/' + q,
                         selection='new calibration-only nearest rank; development') for q in QUANTILES]
        specs.append(dict(campaign='Go V31', name=name, config=cfg, reference=reference,
            warmup=warmup[-25:], alternatives={}, cutoffs=cutoffs,
            acquired_calibration_offers=9022, calibration_warmup_offers=3600,
            acquired_validation_warmup_offers=cost['full_offers'], base=base, case=case,
            saved=saved, go=True))
    e.require({name: sum(s['campaign'] == name for s in specs) for name in EXPECTED} == EXPECTED,
              'Complete retained cohort set differs')
    return specs


def target_values(spec):
    if spec['go']:
        client = e.sealed_read(spec['case'] / 'loadgen.json', spec['case'])
        rows = client['requests']
        e.require(len(rows) == client['total_scheduled'] and len({r['ID'] for r in rows}) == len(rows),
                  'Go all-offer count/identity mismatch')
        values = [None if r['Error'] or r['StatusCode'] != 200 else r['EndToEndLatencyNs'] for r in rows]
        observations = e.sealed_read(spec['case'] / 'observations.json', spec['case'])
        return values, dict(observations=observations,
                            endpoint='scheduled offer through client completion')
    raw = e.sealed_read(spec['base'] / (spec['case'] + '/measurement.json'), spec['base'], 'evidence-seal.json')
    records = sensitivity.model.outcomes(raw, spec['config'])
    result = e.sealed_read(spec['base'] / (spec['case'] + '/result.json'), spec['base'], 'evidence-seal.json')
    e.require(len(records) == 300, 'NGINX all-offer target mismatch')
    return [o['e2e_ns'] if o['success'] else None for o in records], dict(
        observations=result.get('observations', result.get('domain_exits', [])),
        measurement_counter_delta=result.get('measurement_counter_delta'),
        endpoint='scheduled offer through encoded-body completion, correctness checked afterward')


def classify(p, observed):
    error = abs(p-observed)
    safe = p <= BUDGET
    actual_safe = observed <= BUDGET
    return dict(point_decision=decide(p), observed_decision=decide(observed),
        false_assurance=safe and not actual_safe, unnecessary_rejection=not safe and actual_safe,
        decision_correct=safe == actual_safe, error_pp=float(100*error),
        signed_underprediction_pp=float(100*(observed-p)), forecast_budget_slack_pp=float(100*(BUDGET-p)),
        error_within_5pp=error <= TOLERANCE,
        within_5pp_false_assurance=error <= TOLERANCE and safe and not actual_safe,
        observed_budget_excess_pp=float(100*max(Fraction(0), observed-BUDGET)))


def summarize(cells, method, interval=False):
    available = [c for c in cells if method in c['methods']]
    scored = [c['methods'][method] for c in available]
    decisions = [r['iid_dkw_decision'] if interval else r['point_decision'] for r in scored]
    safe = [(c, r) for c, r, d in zip(available, scored, decisions) if d == 'meets']
    unsafe = [(c, r) for c, r, d in zip(available, scored, decisions) if d == 'exceeds']
    false = [(c, r) for c, r in safe if c['observed_decision'] == 'exceeds']
    actual_safe = sum(c['observed_decision'] == 'meets' for c in available)
    reject = [(c, r) for c, r in unsafe if c['observed_decision'] == 'meets']
    unknown = len(available)-len(safe)-len(unsafe)
    return dict(cells=len(available), meets_decisions=len(safe), exceeds_decisions=len(unsafe),
        inconclusive=unknown, correct_meets=len(safe)-len(false), false_assurances=len(false),
        correct_exceeds=len(unsafe)-len(reject), unnecessary_rejections=len(reject),
        answer_coverage_pct=100*(len(available)-unknown)/len(available) if available else None,
        meets_coverage_pct=100*len(safe)/len(available) if available else None,
        false_assurance_fraction_of_meets=len(false)/len(safe) if safe else None,
        unnecessary_rejection_fraction_of_observed_meets=len(reject)/actual_safe if actual_safe else None,
        false_assurances_with_error_within_5pp=sum(r['error_within_5pp'] for _, r in false),
        false_assurances_with_iid_family_lower_above_budget=sum(
            c['iid_family_target_band_pct'][0] > 5 for c, _ in false),
        mae_pp=st.mean(r['error_pp'] for r in scored) if scored else None,
        maximum_error_pp=max(r['error_pp'] for r in scored) if scored else None,
        maximum_false_assurance_observed_pct=max((c['observed_pct'] for c, _ in false), default=None),
        independent_risk_estimate=False)


def reconciliation(spec, values, cells):
    primary = next(c for c in cells if c['label'] in ['historical', 'historical/10'])
    if spec['go']:
        review = e.read(ROOT / 'analysis/runtime_io_v31_result_review/20261009-generation01/report.json')
        prior = next(r for r in review['validation'] if r['trial'] == spec['name'])
        for cell in cells:
            if cell['label'].startswith('historical/'):
                e.close(cell['observed_pct'], prior['observed_miss_pct'][cell['label'].split('/')[1]])
        old = e.read(ROOT / 'analysis/runtime_io_forecast_reliability/20261010/screen.json')
        calibration = next(c['calibration'] for c in old['campaigns'] if c['calibration']['name'] == 'Go V31')
        e.close(primary['methods']['reference']['predicted_pct'], calibration['pooled_forecast_pct'])
        # The ordinary complete-response CDF is retrospective; only its saved
        # observed endpoint is reconciled here, without borrowing primary status.
        return
    saved = e.sealed_read(spec['base'] / 'comparison.json', spec['base'], 'evidence-seal.json')
    if spec['campaign'] == 'NGINX original':
        prior = next(r for r in saved['errors'] if r['block'] == spec['config']['block'] and r['profile'] == spec['config']['profile'])
        e.close(primary['observed_pct'], 100*prior['observed_miss_fraction'])
        e.close(primary['methods']['reference']['predicted_pct'], 100*prior['predicted_miss_fraction'])
    elif spec['campaign'] == 'NGINX panel':
        prior = next(r for r in saved['errors'] if r['config'] == spec['config'])
        e.close(primary['observed_pct'], 100*prior['historical']['observed'])
        e.close(primary['methods']['reference']['predicted_pct'], 100*prior['historical']['predictions']['matched'])
        for cell in cells:
            if cell['label'].startswith('original_panel/'):
                original = next(r for r in prior['panel'] if r['quantile'] == cell['quantile'])
                e.close(cell['observed_pct'], 100*original['observed'])
                e.close(cell['methods']['reference']['predicted_pct'], 100*original['predictions']['matched'])
    else:
        prior = next(r for r in saved['primary']['errors'] if r['config'] == spec['config'])
        key = 'matched' if spec['campaign'] == 'NGINX power' else 'baseline'
        e.close(primary['observed_pct'], 100*prior['observed'])
        e.close(primary['methods']['reference']['predicted_pct'], 100*prior['predictions'][key])


def compute():
    e.INPUTS.clear()
    for rel, digest in json.loads((OUT / 'design_sha256.json').read_text()).items():
        e.require(e.sha(ROOT/rel) == digest, 'Frozen audit design changed: ' + rel)
        e.INPUTS[rel] = digest
    specs = load_specs()
    # Seal in-memory predictions for EVERY cohort before target raw loading.
    prepared = [[dict(**d, methods=forecast(s['reference'], s['warmup'], s['alternatives'], d['deadline_ns']))
                 if d['deadline_ns'] is not None else dict(**d, methods=None) for d in s['cutoffs']] for s in specs]
    family_size = sum(d['deadline_ns'] is not None for row in prepared for d in row)
    rows = []
    for spec, points in zip(specs, prepared):
        values, annotations = target_values(spec)
        cells = []
        for point in points:
            if point['deadline_ns'] is None:
                continue
            k, n = miss_count(values, point['deadline_ns']), len(values)
            obs = Fraction(k, n)
            methods = {name: {**f, **classify(Fraction(f['misses'], f['denominator']), obs)}
                       for name, f in point['methods'].items()}
            cells.append(dict(**{key: v for key, v in point.items() if key != 'methods'},
                observed_misses=k, target_offers=n, observed_pct=float(100*obs), observed_decision=decide(obs),
                target_failures=sum(x is None for x in values), methods=methods,
                iid_target95_band_pct=[100*x for x in binomial_interval(k, n)],
                iid_family_target_band_pct=[100*x for x in binomial_interval(k, n, .05/family_size)]))
        reconciliation(spec, values, cells)
        rows.append(dict(campaign=spec['campaign'], name=spec['name'], config=spec['config'],
            reference_offers=len(spec['reference']), acquired_calibration_offers=spec['acquired_calibration_offers'],
            acquired_calibration_warmup_offers=spec['calibration_warmup_offers'],
            acquired_validation_warmup_offers=spec['acquired_validation_warmup_offers'],
            target_offers=len(values), cells=cells, unavailable_cutoffs=[d for d in points if d['deadline_ns'] is None],
            retained_annotations=annotations))
    summaries = []
    for campaign in EXPECTED:
        cohorts = [r for r in rows if r['campaign'] == campaign]
        labels = list(dict.fromkeys(c['label'] for r in cohorts for c in r['cells']))
        method_names = list(cohorts[0]['cells'][0]['methods'])
        by_deadline = {}
        for label in labels:
            cells = [c for r in cohorts for c in r['cells'] if c['label'] == label]
            by_deadline[label] = {m: dict(point=summarize(cells, m), iid_band=summarize(cells, m, True))
                                  for m in method_names}
        subgroups = {}
        for policy in sorted({r['config'].get('policy', 'Go') for r in cohorts}):
            q95 = [c for r in cohorts if r['config'].get('policy', 'Go') == policy for c in r['cells']
                   if c['label'] == 'slo_grid/19/20']
            subgroups[policy] = {m: summarize(q95, m) for m in method_names}
        summaries.append(dict(campaign=campaign, cohorts=len(cohorts), by_deadline=by_deadline,
            q95_policy_subgroups=subgroups,
            q95_blocks=[dict(block=b, **summarize([c for r in cohorts if r['config']['block'] == b
                for c in r['cells'] if c['label'] == 'slo_grid/19/20'], 'reference')) for b in range(1, 7)],
            acquired_calibration_offers=cohorts[0]['acquired_calibration_offers'],
            acquired_calibration_warmup_offers=cohorts[0]['acquired_calibration_warmup_offers'],
            acquired_validation_warmup_offers=sum(r['acquired_validation_warmup_offers'] for r in cohorts),
            acquired_target_offers=sum(r['target_offers'] for r in cohorts)))
    return dict(role='known-outcome offline development', cohorts=len(rows), target_family_cells=family_size,
        target_family_alpha=.05, slo_miss_budget_pct=5, tolerance_pp=5, campaigns=summaries, rows=rows,
        all_predictions_built_before_target_raw_reads=True, target_calibration_independence_established=False,
        offer_iid_established=False, future_population_slo_guarantee=False, independent_confirmation=False,
        causal_mechanism_identified=False, new_method_novelty_established=False, new_collection=False,
        manuscript_changed=False, friend_v31_received=False)


def render(result):
    lines = ['# SLO decisions: fixed offline audit', '',
        '11 October 2026. Known-outcome development; no new collection, manuscript change or independent confirmation.', '',
        'The illustrative SLO is <=5% failed/late offers in a complete target window. Finite observed compliance is not a population certificate.', '',
        '## Calibration 95th-percentile deadline: ordinary reference', '',
        '| Campaign | Cohorts | Meets decisions | False assurances | False assurances with error <=5 pp | False assurances with conditional family lower >5% | MAE (pp) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for campaign in result['campaigns']:
        r = campaign['by_deadline']['slo_grid/19/20']['reference']['point']
        lines.append(f"| {campaign['campaign']} | {campaign['cohorts']} | {r['meets_decisions']} | {r['false_assurances']} | {r['false_assurances_with_error_within_5pp']} | {r['false_assurances_with_iid_family_lower_above_budget']} | {r['mae_pp']:.3f} |")
    lines += ['', 'The 95th-percentile reference meets its own empirical 5% budget by construction. This is self-fit, not proof of accurate transfer. Nearest ranks, strict deadline exceedance and failure mass are fixed before scoring.', '',
        '## All fixed deadline labels and information-matched controls', '',
        '| Campaign | Deadline label | Method | Point false assurance / meets | Point unnecessary rejection | IID-band false assurance / meets | IID-band inconclusive / cells |',
        '|---|---|---|---:|---:|---:|---:|']
    for campaign in result['campaigns']:
        for label, methods in campaign['by_deadline'].items():
            for name, values in methods.items():
                a, b = values['point'], values['iid_band']
                lines.append(f"| {campaign['campaign']} | {label} | {name} | {a['false_assurances']}/{a['meets_decisions']} | {a['unnecessary_rejections']} | {b['false_assurances']}/{b['meets_decisions']} | {b['inconclusive']}/{b['cells']} |")
    lines += ['', 'Zero meets decisions means no assurance coverage, not demonstrated safety. DKW bands are conditional common-population sampling illustrations; they do not cover future drift. Warmup controls decide later and consume the same last 25 offers. The acquired pools and full warmups remain charged.', '',
        '## Target uncertainty and scope', '',
        f"All {result['cohorts']} cohorts and {result['target_family_cells']} finite labelled deadline cells are retained. Exact Clopper-Pearson target intervals are provided per cell and at Bonferroni family alpha .05. Within-target IID Bernoulli behavior and independence from calibration are unverified. Family correction needs no independence between labelled cells. These calculations do not identify physical drift or the historical cause.", '',
        'Rows include all point/band confusion counts, signed error and budget slack, 95% and family target intervals, complete acquired-cost counts, policy subgroups, six-block 95th-percentile counts and retained observations. Deadline-specific counts share cohorts and calibration; no pooled independent-risk estimate or method ranking is made.', '',
        'Historic Go 10/11/12 ms, NGINX historical and fresh original-panel forecasts reconcile with saved outcomes. New calibration-only deadline questions and decisions remain development despite the information boundary. V30 is outside this ordinary-CDF audit, and friend-owned V31 remains pending. The manuscript and prior scientific decisions are unchanged.', '',
        'Read-only replay: `python3 -B analysis/audit_slo_decisions.py --verify`.', '']
    return '\n'.join(lines)


def verify_protected():
    for name, digest in json.loads((OUT / 'protected_current_sha256.json').read_text()).items():
        e.require(e.sha(ROOT / name) == digest, 'Prior consolidated artifact changed: ' + name)


def freeze():
    e.require(not OUT.exists(), 'Preserve existing audit; use --verify')
    OUT.mkdir(parents=True)
    # Hash loaded implementation modules before any result calculation.
    paths = {Path(__file__), ROOT / 'analysis/test_slo_decisions.py', PROTOCOL,
             ROOT / 'docs/runtime_io_slo_decision_sources_20261011.json'}
    paths.update(Path(module.__file__).resolve() for module in list(sys.modules.values())
                 if getattr(module, '__file__', None) and Path(module.__file__).resolve().is_relative_to(ROOT)
                 and str(module.__file__).endswith('.py'))
    dump(OUT / 'design_sha256.json', {str(p.relative_to(ROOT)): e.sha(p) for p in sorted(paths)})
    seal = ROOT / 'analysis/runtime_io_empirical_consolidation/20261011/evidence-seal.json'
    manifest = json.loads(seal.read_text())['files_sha256']
    manifest[str(seal.relative_to(ROOT))] = e.sha(seal)
    dump(OUT / 'protected_current_sha256.json', manifest)
    dump(OUT / 'design.json', dict(question='When does apparently accurate calibration lead to a wrong SLO decision?',
        quantiles=QUANTILES, slo_budget_pct=5, error_label_pp=5, expected_cohorts=EXPECTED,
        role='known-outcome development', target_uncertainty='exact per-cell and Bonferroni family IID illustration'))
    verify_protected()
    print('Audit contract and current manuscript/evidence hashes frozen; no calculation or collection.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--freeze', action='store_true')
    group.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return
    verify_protected()
    if args.verify:
        for name, digest in json.loads((OUT / 'seal.json').read_text())['files_sha256'].items():
            e.require(e.sha(OUT / name) == digest, 'Audit artifact changed: ' + name)
    else:
        e.require(not (OUT / 'screen.json').exists(), 'No overwrite or favorable rerun')
    result = compute()
    report = render(result)
    if args.verify:
        e.require(result == json.loads((OUT / 'screen.json').read_text()), 'Saved decision audit differs')
        e.require(report == (OUT / 'report.md').read_text(), 'Saved decision report differs')
        for name, digest in json.loads((OUT / 'inputs_sha256.json').read_text()).items():
            e.require(e.sha(ROOT/name) == digest, 'Consumed input changed: ' + name)
        print('All 96 cohorts, calibration-only decisions, uncertainty arithmetic and protected manuscript verify.')
    else:
        dump(OUT / 'screen.json', result)
        dump(OUT / 'inputs_sha256.json', dict(e.INPUTS))
        (OUT / 'report.md').write_text(report)
        dump(OUT / 'seal.json', dict(files_sha256={p.name: e.sha(p) for p in OUT.iterdir()}))
        print('\n'.join(report.splitlines()[:18]))


if __name__ == '__main__':
    main()
