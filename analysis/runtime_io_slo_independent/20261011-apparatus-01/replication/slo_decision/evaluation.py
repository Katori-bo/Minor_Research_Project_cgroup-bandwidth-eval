"""Ordinary CDF decision evaluation and a fail-closed pre-target barrier.

No HTTP, Docker, hardware measurement, fitting, or historical-data imports.
The one-second bound starts after full warmup readback and drain, not at the
unobserved absolute timestamp of its final HTTP completion.
Collectors must call the barrier before creating the target client process.
"""
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import time

BUDGET = Fraction(1, 20)
QUANTILES = ('9/10', '19/20', '39/40', '99/100', '199/200')
ERROR_LABEL = Fraction(1, 20)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_values(values):
    require(isinstance(values, list) and values, 'nonempty all-offer pool required')
    require(all(x is None or type(x) is int and x >= 0 for x in values),
            'offer duration must be nonnegative integer ns or None for failure')


def fraction_json(value):
    return dict(numerator=value.numerator, denominator=value.denominator)


def probability(values, deadline_ns):
    validate_values(values)
    require(type(deadline_ns) is int and deadline_ns >= 0, 'integer deadline required')
    misses = sum(x is None or x > deadline_ns for x in values)
    return misses, Fraction(misses, len(values))


def cutoff(values, quantile):
    validate_values(values)
    require(quantile in QUANTILES, 'undeclared quantile')
    rank = math.ceil(Fraction(quantile) * len(values)) - 1
    finite = sorted(x for x in values if x is not None)
    return finite[rank] if rank < len(finite) else None


def point_decision(p):
    return 'meets' if p <= BUDGET else 'exceeds'


def forecast(values, deadline_ns):
    misses, p = probability(values, deadline_ns)
    radius = math.sqrt(math.log(40) / (2 * len(values)))
    lo, hi = max(0., float(p) - radius), min(1., float(p) + radius)
    interval_decision = ('meets' if hi <= float(BUDGET) else
                         'exceeds' if lo > float(BUDGET) else 'inconclusive')
    return dict(offers=len(values), misses=misses, probability=fraction_json(p),
                point_decision=point_decision(p), dkw95=[lo, hi],
                dkw_decision=interval_decision, sampling_assumptions_verified=False,
                future_transfer_guarantee=False)


def calibration_predictions(reference, historical_deadlines):
    validate_values(reference)
    require(all(type(x) is int and x >= 0 for x in historical_deadlines),
            'invalid historical deadline')
    cells = [dict(label='q/' + q, deadline_ns=cutoff(reference, q)) for q in QUANTILES]
    cells += [dict(label='fixed/' + str(x), deadline_ns=x) for x in historical_deadlines]
    for cell in cells:
        cell['reference'] = (None if cell['deadline_ns'] is None else
                             forecast(reference, cell['deadline_ns']))
    return cells


def warmup_predictions(reference, warmup, cells):
    validate_values(reference)
    validate_values(warmup)
    require(len(warmup) >= 25, 'at least 25 acquired warmup offers required')
    recent = warmup[-25:]
    output = []
    for cell in cells:
        deadline = cell['deadline_ns']
        output.append(dict(label=cell['label'], deadline_ns=deadline,
            methods={} if deadline is None else dict(
                reference=forecast(reference, deadline),
                recent25=forecast(recent, deadline),
                weighted_update=forecast(reference + recent, deadline))))
    return output


def score(forecast_record, target, deadline_ns):
    misses, p = probability(target, deadline_ns)
    predicted = Fraction(**forecast_record['probability'])
    observed = point_decision(p)
    slack = BUDGET - predicted
    underprediction = p - predicted
    point = forecast_record['point_decision']
    interval = forecast_record['dkw_decision']
    false = point == 'meets' and observed == 'exceeds'
    return dict(target_offers=len(target), target_misses=misses,
        observed_probability=fraction_json(p), observed_decision=observed,
        signed_underprediction=fraction_json(underprediction),
        absolute_error=fraction_json(abs(underprediction)),
        forecast_slack=fraction_json(slack), budget_excess=fraction_json(p - BUDGET),
        false_assurance=false,
        positive_slack_small_error_false_assurance=(false and slack > 0 and
                                                   abs(underprediction) <= ERROR_LABEL),
        unnecessary_rejection=point == 'exceeds' and observed == 'meets',
        interval_false_assurance=interval == 'meets' and observed == 'exceeds',
        interval_unnecessary_rejection=interval == 'exceeds' and observed == 'meets',
        interval_inconclusive=interval == 'inconclusive')


def rates(counts, all_planned, completed):
    """Keep undefined assurance/error denominators distinct from zero errors."""
    require(0 <= completed <= all_planned and all_planned > 0, 'invalid availability')
    require(counts['meets'] + counts['exceeds'] + counts['inconclusive'] +
            counts['unavailable_deadline'] == completed, 'decision conservation failed')
    divide = lambda a, b: None if b == 0 else a / b
    return dict(false_assurance_per_meets=divide(counts['false_assurance'], counts['meets']),
        false_assurance_per_completed=divide(counts['false_assurance'], completed),
        unnecessary_rejection_per_observed_compliant=divide(
            counts['unnecessary_rejection'], counts['observed_compliant']),
        answer_coverage_completed=divide(counts['meets'] + counts['exceeds'], completed),
        assurance_coverage_completed=divide(counts['meets'], completed),
        answer_coverage_all_planned=(counts['meets'] + counts['exceeds']) / all_planned,
        assurance_coverage_all_planned=counts['meets'] / all_planned,
        completed_availability=completed / all_planned,
        unobserved_planned_windows=all_planned - completed,
        missing_windows_assumed_safe=False)


class DecisionBarrier:
    """Append-only receipts; the collector passes the same boot/monotonic clock.

    A hash and local timestamp alone do not prove honest external collection.
    Final raw replay must reconcile the collector's target child-creation event, receipt,
    source identity, inputs and boot identity. This class cannot authorize traffic.
    """
    def __init__(self, directory, plan_hash, campaign_id, boot_id, clock=time.monotonic_ns):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.plan_hash, self.campaign_id, self.boot_id = plan_hash, campaign_id, boot_id
        self.clock = clock
        require(all(isinstance(x, str) and x for x in (plan_hash, campaign_id, boot_id)),
                'barrier identity required')

    def write(self, filename, value):
        with (self.directory / filename).open('x') as handle:
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())

    def freeze_calibration(self, reference, historical_deadlines, acquired_cost):
        require(not list(self.directory.iterdir()), 'calibration freeze must be first')
        cells = calibration_predictions(reference, historical_deadlines)
        self.reference, self.cells = list(reference), cells
        self.write('calibration.json', dict(plan_hash=self.plan_hash,
            campaign_id=self.campaign_id, boot_id=self.boot_id,
            input_sha256=digest(reference), acquired_cost=acquired_cost,
            reference=reference, cells=cells, sealed_monotonic_ns=self.clock()))
        self.calibration_hash = hashlib.sha256(
            (self.directory / 'calibration.json').read_bytes()).hexdigest()

    def freeze_warmup(self, window_id, warmup, warmup_available_ns):
        require(hasattr(self, 'reference'), 'calibration must already be frozen')
        require(hashlib.sha256((self.directory / 'calibration.json').read_bytes()).hexdigest()
                == self.calibration_hash, 'frozen calibration changed')
        require(window_id.replace('_', '').isalnum(), 'safe unique window id required')
        start = self.clock()
        require(type(warmup_available_ns) is int and
                0 <= warmup_available_ns <= start, 'warmup availability clock invalid')
        predictions = warmup_predictions(self.reference, warmup, self.cells)
        finish = self.clock()
        require(finish - warmup_available_ns <= 1_000_000_000,
                'one-second post-warmup barrier exhausted; do not release target')
        record = dict(plan_hash=self.plan_hash, campaign_id=self.campaign_id,
            boot_id=self.boot_id, window_id=window_id, warmup_sha256=digest(warmup),
            acquired_warmup_offers=len(warmup), selected_warmup_offers=25,
            warmup_available_ns=warmup_available_ns,
            sealed_monotonic_ns=finish, cells=predictions)
        self.write(window_id + '_forecast.json', record)
        # Return the file-byte hash after the exclusive write closes. The target
        # release records this digest; changing any receipt invalidates replay.
        return hashlib.sha256((self.directory / (window_id + '_forecast.json')).read_bytes()).hexdigest()

    def prepare_target_start(self, window_id, forecast_hash):
        """Must finish successfully before the collector schedules any target."""
        require(window_id.replace('_', '').isalnum(), 'safe unique window id required')
        path = self.directory / (window_id + '_forecast.json')
        require(path.exists(), 'target requires frozen warmup decisions')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == forecast_hash, 'forecast receipt changed')
        record = json.loads(data)
        require(record['plan_hash'] == self.plan_hash and
                record['campaign_id'] == self.campaign_id and record['window_id'] == window_id,
                'receipt belongs to another contract or window')
        now = self.clock()
        require(record['sealed_monotonic_ns'] <= now and
                now - record['warmup_available_ns'] <= 1_000_000_000,
                'target-start barrier expired; do not schedule target')
        self.write(window_id + '_permit.json', dict(forecast_sha256=forecast_hash,
            permit_monotonic_ns=now, boot_id=self.boot_id, window_id=window_id))

    def record_target_release(self, window_id, forecast_hash, target_spawn_before_ns, boot_id):
        require(window_id.replace('_', '').isalnum(), 'safe unique window id required')
        path = self.directory / (window_id + '_forecast.json')
        permit_path = self.directory / (window_id + '_permit.json')
        require(path.exists() and permit_path.exists(), 'target-start permit required')
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == forecast_hash, 'forecast receipt changed')
        record, permit = json.loads(data), json.loads(permit_path.read_bytes())
        require(permit['forecast_sha256'] == forecast_hash, 'target-start permit differs')
        require(boot_id == self.boot_id == record['boot_id'], 'clock boot changed')
        require(type(target_spawn_before_ns) is int and
                permit['permit_monotonic_ns'] < target_spawn_before_ns <= self.clock(),
                'target child creation must follow the sealed forecast')
        require(target_spawn_before_ns - record['warmup_available_ns'] <= 1_000_000_000,
                'warmup-availability to child-creation gap exceeded one second')
        self.write(window_id + '_release.json', dict(forecast_sha256=forecast_hash,
            target_spawn_before_ns=target_spawn_before_ns, boot_id=boot_id, window_id=window_id))
