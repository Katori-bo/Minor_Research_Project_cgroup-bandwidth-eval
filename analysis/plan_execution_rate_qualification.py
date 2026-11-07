#!/usr/bin/env python3
"""Offline design arithmetic. No counter access, service, or qualification."""
import argparse
import functools
import hashlib
import json
import math
from pathlib import Path

from worker_wait_precision_cost import quantile, t_cdf

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'analysis/runtime_io_execution_rate_qualification_design/20261011'
INPUTS = [
    'analysis/runtime_io_worker_wait_precision_cost/20261010/planning.json',
    'analysis/runtime_io_warmup_precision_cost/20261011/planning.json',
    'analysis/runtime_io_nginx_deadline_panel/generation-01/campaign/forecast/forecast.json',
    'analysis/worker_wait_precision_cost.py',
]
GATES = 14  # 5 cutoff differences + target/warmup means, at each of two rates.
FAMILY_ALPHA = .05
MEAN_MARGIN_NS = 20_000
MISS_MARGIN_PP = 2
SCOPE_BUDGET_SEC = 600
OVERHEAD_BUDGET_SEC = 2700
OVERHEAD_RESERVE_SEC = 120


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ratio_interval(a, m, error_a=0, error_m=0):
    """Deterministic count-error propagation, not a sampling confidence interval."""
    require(all(math.isfinite(x) for x in (a, m, error_a, error_m)), 'Nonfinite count/error')
    require(0 <= error_a < a and 0 <= error_m < m, 'Undefined or nonpositive count interval')
    return [(a - error_a) / (m + error_m), (a + error_a) / (m - error_m)]


def single_window_log_tolerance(cpu_ns, radius_ns):
    require(cpu_ns > 0 and radius_ns > 0, 'Positive CPU scale/radius required')
    # Half the radius is allocated to clock measurement. Two independently
    # bounded windows contribute up to 2a log error; no stochastic independence.
    return .5 * math.log1p(radius_ns / (2 * cpu_ns))


@functools.lru_cache(None)
def critical(n, gates=GATES):
    require(n >= 2 and gates >= 1, 'Invalid interval family')
    p = 1 - FAMILY_ALPHA / (2 * gates)
    return math.ceil(quantile(lambda x: t_cdf(x, n - 1), p) * 1e6) / 1e6


def width_only_n(sd, margin, center=0, gates=GATES):
    require(sd >= 0 and margin > 0, 'Invalid planning moments')
    if abs(center) >= margin:
        return None
    def contains(n):
        return abs(center) + critical(n, gates) * sd / math.sqrt(n) <= margin
    lo, hi = 1, 2
    while not contains(hi):
        lo, hi = hi, 2 * hi
        require(hi <= 2**20, 'Planning range exceeded')
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if contains(mid):
            hi = mid
        else:
            lo = mid
    return hi


def balanced_budget_n(pair_seconds):
    require(pair_seconds > 0, 'Positive pair cost required')
    return math.floor((OVERHEAD_BUDGET_SEC - OVERHEAD_RESERVE_SEC) / pair_seconds)


def analyze():
    pilot = json.loads((ROOT / INPUTS[0]).read_text())
    sensitivity = json.loads((ROOT / INPUTS[1]).read_text())
    forecast = json.loads((ROOT / INPUTS[2]).read_text())
    ref = forecast['references']['P0']
    require(ref['failed_offers'] == 0 and ref['offers'] == 800, 'Unexpected panel calibration')
    samples = sorted(ref['successful_samples_ns'])
    require(len(samples) == 800, 'Incomplete calibration panel')
    panel = [samples[math.floor(q * (800 - 1))] for q in (.1, .25, .5, .75, .9)]
    radii = {p: sensitivity['groups']['NGINX panel/' + p]['radius']['symmetric_radius_ns']
             for p in ('P0', 'P1')}
    radius = min(radii.values())  # Conservative inherited sensitivity scale; P0-only qualification.
    cpu_scale = 20_000_000  # Declared scale, not a measured CPU-service mapping.
    tolerance = single_window_log_tolerance(cpu_scale, radius)
    cost = sum(pilot['pair_seconds'].values())
    n_cap = balanced_budget_n(cost)
    t = critical(n_cap)
    warmup = {}
    for rate in ('4', '8'):
        item = pilot['metrics'][rate]['warmup_mean_ns']
        sd = item['sd']
        n = width_only_n(sd, MEAN_MARGIN_NS)
        looser_n = width_only_n(sd, 100_000)
        sd_needed = MEAN_MARGIN_NS * math.sqrt(n_cap) / t
        warmup[rate] = {
            'historical_paired_sd_ns': sd,
            'zero_center_halfwidth_at_cap_ns': t * sd / math.sqrt(n_cap),
            'maximum_sd_at_cap_for_zero_center_width_ns': sd_needed,
            'needed_sd_fraction_of_historical': sd_needed / sd,
            'required_sd_reduction_pct': 100 * (1 - sd_needed / sd),
            'zero_center_width_only_pairs': n,
            'zero_center_looser_100us_width_only_pairs': looser_n,
            'single_95pct_zero_center_halfwidth_at_cap_ns': critical(n_cap, 1) * sd / math.sqrt(n_cap),
            'pilot_mean_geometry_has_no_solution': abs(item['mean']) >= MEAN_MARGIN_NS,
        }
    balanced_n = max(x['zero_center_width_only_pairs'] for x in warmup.values())
    grid = [{
        'historical_sd_fraction': scale,
        'warmup_zero_center_widths_ns': {
            r: t * warmup[r]['historical_paired_sd_ns'] * scale / math.sqrt(n_cap)
            for r in warmup},
        'both_warmup_geometries_inside_margin': all(
            t * x['historical_paired_sd_ns'] * scale / math.sqrt(n_cap) <= MEAN_MARGIN_NS
            for x in warmup.values()),
    } for scale in (1, .5, .25, .1, .05)]
    return {
        'schema': 'execution-rate-qualification-offline-design-v1',
        'decision': 'no_go_implementation_or_collection_with_current_precision_cost_evidence',
        'collection_performed': False, 'measurement_qualified': False,
        'predictive_usefulness_tested': False, 'scope': 'P0 only, rates 4/s and 8/s',
        'proposed_gates': GATES, 'family_alpha': FAMILY_ALPHA,
        'mean_equivalence_margin_ns': MEAN_MARGIN_NS, 'miss_equivalence_margin_pp': MISS_MARGIN_PP,
        'fixed_calibration_only_cutoffs_ns': panel,
        'prior_calibration_cost': {'source_campaign_measured_offers': 1600,
                                   'source_campaign_warmup_offers': 100,
                                   'P0_cutoff_pool_offers': 800, 'new_calibration_acquired': False},
        'precision': {
            'empirical_symmetric_radii_ns': radii, 'planning_radius_ns': radius,
            'assumed_cpu_service_scale_ns': cpu_scale,
            'clock_time_budget_ns': radius / 2,
            'single_window_clock_log_error_limit': tolerance,
            'single_window_relative_upper_clock_error_pct': 100 * math.expm1(tolerance),
            'single_window_cpu_accounting_error_ns_per_offer': radius / 4,
            'cpu_time_to_response_mapping_verified': False,
            'limits_are_sampling_confidence_intervals': False,
        },
        'cost': {
            'scope_phase_cap_sec': SCOPE_BUDGET_SEC,
            'overhead_phase_cap_sec': OVERHEAD_BUDGET_SEC,
            'overhead_reserve_sec': OVERHEAD_RESERVE_SEC,
            'historical_pair_seconds': pilot['pair_seconds'],
            'optimistic_balanced_pairs_per_rate_cap': n_cap,
            'cap_incremental_offers': 1300 * n_cap + 90,
            'cap_overhead_projected_sec': n_cap * cost,
            'cap_overhead_spare_after_reserve_sec': OVERHEAD_BUDGET_SEC - OVERHEAD_RESERVE_SEC - n_cap * cost,
            'scope_plus_cap_projected_minutes': (SCOPE_BUDGET_SEC + n_cap * cost) / 60,
            'warmup_only_width_balanced_pairs_per_rate': balanced_n,
            'warmup_only_width_incremental_offers': 1300 * balanced_n + 90,
            'scope_plus_warmup_only_width_projected_hours': (SCOPE_BUDGET_SEC + balanced_n * cost) / 3600,
            'new_counter_cost_included': False,
            'scope_cap_is_observed_time': False,
        },
        'warmup_gate_planning': warmup, 'sd_sensitivity_grid': grid,
        'interpretation': 'Width-only geometry substitutes old-observer SD and a zero center for future statistics; not power, actual new-observer moments, a sample-size minimum, or qualification. Only two of fourteen gates have moments used here; their modeled precision is already insufficient. Future chronological paired normality and cost transfer are unverified. No variance-reduction method or larger budget is justified by this computation.',
    }


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    seal = json.loads((PACKAGE / 'seal.json').read_text())['files_sha256']
    for name, value in seal.items():
        require(sha(PACKAGE / name) == value, 'Package changed: ' + name)
    for name, value in json.loads((PACKAGE / 'inputs_sha256.json').read_text()).items():
        require(sha(ROOT / name) == value, 'Input changed: ' + name)
    require(analyze() == json.loads((PACKAGE / 'planning.json').read_text()), 'Arithmetic differs')
    print('Execution-rate qualification design and inputs verify; no measurement or qualification performed.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify', action='store_true')
    args = p.parse_args()
    verify() if args.verify else print(json.dumps(analyze(), indent=2))
