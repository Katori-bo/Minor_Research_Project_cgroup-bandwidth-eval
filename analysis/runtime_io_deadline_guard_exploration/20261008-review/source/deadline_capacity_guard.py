"""Exploratory deadline-specific guard; no collection or validation fitting.

The bound is conditional on a constant true capacity inside the supplied range
and model discrepancy within the supplied margin. Neither premise follows from
an empirical calibration range. All FIFO calculations use rational arithmetic.
"""
from collections import deque
from fractions import Fraction
from functools import lru_cache
import math


def positive(value, name):
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


@lru_cache(maxsize=256)
def _fifo(offsets, capacity, deadline_ns, slots):
    service = Fraction(1_000_000_000) / Fraction(str(capacity))
    pending = deque()
    last = Fraction(0)
    misses = rejections = peak = 0
    for arrival in offsets:
        while pending and pending[0] <= arrival:
            pending.popleft()
        if slots is not None and len(pending) >= slots:
            misses += 1
            rejections += 1
            continue
        last = max(arrival, last) + service
        pending.append(last)
        peak = max(peak, len(pending))
        misses += last - arrival > deadline_ns
    return dict(offers=len(offsets), misses=misses,
                miss_pct=100 * misses / len(offsets), rejections=rejections,
                system_peak=peak)


def fifo(offsets_ns, capacity_rps, deadline_ns=500_000_000, system_slots=129):
    offsets = tuple(offsets_ns)
    if not offsets or any(type(x) is not int or x < 0 for x in offsets):
        raise ValueError("nonempty integer nanosecond offsets required")
    if any(a > b for a, b in zip(offsets, offsets[1:])):
        raise ValueError("offsets must be ordered; simultaneous offers are allowed")
    positive(capacity_rps, "capacity")
    if type(deadline_ns) is not int or deadline_ns <= 0:
        raise ValueError("deadline must be positive integer nanoseconds")
    if system_slots is not None and (type(system_slots) is not int or system_slots < 1):
        raise ValueError("system_slots must be a positive integer or None")
    return dict(_fifo(offsets, capacity_rps, deadline_ns, system_slots))


def diagnose(offsets_ns, estimate_rps, reference_rps, margin_pp,
             tolerance_pp=3.0, deadline_ns=500_000_000, system_slots=129):
    """Compare one fixed finite-FIFO forecast to a reference model family.

If the infinite FIFO at the slow reference endpoint fits in the finite queue,
all reference capacities admit the same offers. Their completion times and
miss counts are monotone, so endpoint forecasts bound the whole family.
Rejecting estimates are allowed: their point forecast is fixed. A rejecting
reference family causes abstention, not an unproved endpoint envelope.
"""
    if system_slots is None:
        raise ValueError("guard requires finite system_slots")
    lo, hi = reference_rps
    positive(lo, "reference lower capacity")
    positive(hi, "reference upper capacity")
    if lo > hi:
        raise ValueError("unordered reference range")
    if not math.isfinite(margin_pp) or margin_pp < 0:
        raise ValueError("margin must be finite and nonnegative")
    positive(tolerance_pp, "tolerance")
    point = fifo(offsets_ns, estimate_rps, deadline_ns, system_slots)
    slow = fifo(offsets_ns, lo, deadline_ns, None)
    result = dict(point_forecast=point, reference_capacity_rps=[lo, hi],
                  discrepancy_margin_pp=margin_pp, tolerance_pp=tolerance_pp,
                  conditional_on="constant capacity in reference range and real/model miss discrepancy <= margin",
                  real_world_guarantee=False)
    if slow['system_peak'] > system_slots:
        result.update(decision='insufficient_model_support',
                      reason='reference family may reject; monotone no-rejection proof unavailable',
                      reference_slow_infinite_system_peak=slow['system_peak'])
        return result
    fast = fifo(offsets_ns, hi, deadline_ns, None)
    a, b = fast['miss_pct'], slow['miss_pct']
    if a > b:
        raise AssertionError("reference no-rejection FIFO monotonicity failed")
    sensitivity = max(abs(point['miss_pct'] - a), abs(point['miss_pct'] - b))
    result.update(reference_model_miss_range_pct=[a, b],
                  forecast_disagreement_pp=sensitivity,
                  conditional_error_bound_pp=min(100.0, sensitivity + margin_pp),
                  reference_family_rejection_free=True)
    result['decision'] = ('accept_conditional' if result['conditional_error_bound_pp'] <= tolerance_pp
                          else 'flag_for_recalibration')
    return result


def fit_reference(anchor_rows, discrepancy_rows, schedules, deadline_ns=500_000_000,
                  system_slots=129):
    """Separate capacity anchors from model-discrepancy calibration.

Each input row is qualified mixed CALIBRATION data. Validation roles, duplicate
IDs, or reused blocks are refused. The maximum held-out error is a descriptive
margin, not a confidence bound or a guarantee for unseen schedules.
"""
    if not anchor_rows or not discrepancy_rows:
        raise ValueError("capacity and discrepancy calibration are both required")
    rows = anchor_rows + discrepancy_rows
    if any(r['role'] != 'mixed' or not r['state_eligible'] or not r['all_successful'] for r in rows):
        raise ValueError("qualified mixed calibration rows only; validation forbidden")
    if len({r['trial'] for r in rows}) != len(rows):
        raise ValueError("duplicate calibration ID")
    if {r['block'] for r in anchor_rows} & {r['block'] for r in discrepancy_rows}:
        raise ValueError("capacity and discrepancy blocks must be separate")
    lo = min(r['busy_capacity_bounds_rps'][0] for r in anchor_rows)
    hi = max(r['busy_capacity_bounds_rps'][1] for r in anchor_rows)
    errors = []
    for row in discrepancy_rows:
        offsets = schedules[row['trial']]
        slow = fifo(offsets, lo, deadline_ns, None)
        fast = fifo(offsets, hi, deadline_ns, None)
        if slow['system_peak'] > system_slots:
            raise ValueError("discrepancy calibration reference family may reject")
        observed = row['miss_pct']
        if observed is None or not math.isfinite(observed) or not 0 <= observed <= 100:
            raise ValueError("invalid calibration miss percentage")
        error = max(abs(observed - x['miss_pct']) for x in (slow, fast))
        errors.append(dict(trial=row['trial'],maximum_endpoint_error_pp=error))
    return dict(reference_capacity_rps=[lo, hi], margin_pp=max(x['maximum_endpoint_error_pp'] for x in errors),
                anchor_trial_ids=[r['trial'] for r in anchor_rows],
                discrepancy_trial_ids=[r['trial'] for r in discrepancy_rows],
                discrepancy_errors=errors, statistical_coverage_established=False,
                validation_outcomes_used=False)
