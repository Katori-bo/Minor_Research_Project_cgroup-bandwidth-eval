#!/usr/bin/env python3
"""Bounded offline actuation model. No cgroup access or workload collection.

One CPU, one continuously backlogged FIFO worker, integer microsecond events.
Models global/local runtime, five-ms slices, zero burst and active fixed timer.
No claim to reproduce Linux scheduling, multi-core/hierarchy, or published evals.
"""
import ast
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS = ROOT / 'analysis/runtime_io_novelty_discovery_round/20261008'
OUT = ROOT / 'analysis/runtime_io_quota_update_replay/20261008'
PERIOD = 100_000
HORIZON = 4_000_000
WORK = 5_000
DEADLINES = [100_000, 300_000, 500_000]
PHASES = list(range(1_000, 100_001, 1_000))
ARMS = ['original_pair', 'quota_only', 'boundary_setter', 'boundary_native']


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def read(p):
    return json.loads(p.read_text())


def native_class():
    source = PREVIOUS / 'sources/autothrottle/worker-daemon.py'
    node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'CaptainScaler')
    namespace = {'statistics': statistics}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace['CaptainScaler']


def coalesce(limit, previous):
    # Exact predicates in pinned worker run loop, with its minimum limit.
    limit = max(0.01, limit)
    if abs(limit - previous) < 0.00001:
        return previous
    return limit


def sequences():
    return [
        {'id': 'unchanged_limit_control', 'initial': 50_000, 'changes': [[t, 50_000] for t in range(100_000, HORIZON, 100_000)], 'cadence': 'unchanged observation-loop proposals; must be suppressed'},
        {'id': 'regular_alternation', 'initial': 50_000, 'changes': [[1_000_000, 40_000], [2_000_000, 60_000], [3_000_000, 40_000]], 'cadence': 'one-second genuine-change stress sequence, not captured controller decisions'},
        {'id': 'regular_small_changes', 'initial': 50_000, 'changes': [[1_000_000, 49_000], [2_000_000, 51_000], [3_000_000, 49_000]], 'cadence': 'one-second genuine-change stress sequence'},
        {'id': 'rollback_grant', 'initial': 50_000, 'changes': [[1_000_000, 25_000], [1_100_000, 75_000], [2_000_000, 50_000]], 'cadence': 'scale-down then conditional Captain rollback arithmetic; 75ms emergency quota counted in allocation'},
        {'id': 'nonbinding_control', 'initial': 100_000, 'changes': [[1_000_000, 120_000], [2_000_000, 110_000], [3_000_000, 120_000]], 'cadence': 'single-CPU nonbinding genuine changes'},
    ]


def prepare():
    if OUT.exists():
        raise ValueError('Refusing to overwrite an existing replay gate')
    preserved = read(PREVIOUS / 'design/preserved_sha256.json')
    for p in PREVIOUS.rglob('*'):
        if p.is_file():
            preserved[str(p.relative_to(ROOT))] = sha(p)
    preserved['docs/runtime_io_novelty_discovery_round_20261008.md'] = sha(ROOT / 'docs/runtime_io_novelty_discovery_round_20261008.md')
    protected = read(PREVIOUS / 'design/protected_sha256.json')
    for rel, expected in {**protected, **preserved}.items():
        if sha(ROOT / rel) != expected:
            raise ValueError('Prior input changed: ' + rel)
    save(OUT / 'design/protected_sha256.json', protected)
    save(OUT / 'design/preserved_sha256.json', preserved)
    save(OUT / 'design/plan.json', {
        'date': '2026-10-08', 'period_us': PERIOD, 'resource_window_us': HORIZON,
        'work_us': WORK, 'offered_jobs': HORIZON // WORK, 'arrivals': 'one 5ms-CPU job every 5ms; deliberately backlogged synthetic CPU demand, never a live overload',
        'absolute_initial_state': {'global_runtime_us': 'initial quota', 'local_runtime_us': 0, 'timer': 'active throughout', 'burst_us': 0, 'slice_us': 5_000},
        'phases_first_boundary_us': PHASES, 'phase_interpretation': '100 fixed sensitivity points; no probability distribution or all-continuous-phase guarantee',
        'deadlines_us': DEADLINES, 'fixed_sequences': sequences(), 'arms': ARMS,
        'event_order': 'completion before events; pending boundary setter/native recommendation before periodic refill; periodic refill before immediate writes; observation after those events; zero-duration paired writes in primary check',
        'native_policy': {'class': 'CaptainScaler extracted unchanged by AST from pinned source', 'target': 0.1, 'initial_limit': 0.5, 'observation_interval_us': 100_000, 'regular_decision_interval_s': 1, 'stats': 'simulated consumed CPU and count of currently throttled periodic callbacks; not empirical counters'},
        'matching': ['Identical intended allocation across immediate pair/quota-only arms', 'Boundary quota offset calibrated within integer-us precision to original nominal allocation integral', 'Boundary quota offset calibrated to original saturated CPU consumption within 10us, or report inability'],
        'calibration_scope': 'Ordinary bisection; counts and costs reported; retrospective offline comparator, not a deployable low-information policy',
        'interwrite_sensitivity_us': [10, 100, 1_000],
        'materiality': {'resource_relative_pct': 5, 'deadline_miss_absolute_pp': 3},
        'stop_rule': 'Known reset/refill or synthetic phase effects explained by ordinary budget replay/accounting, without a concrete additional capability or established real-controller causal finding.',
        'proceed_rule': 'Material effect plus a nonroutine additional capability/finding survives adequate controls and matched contracts; synthetic materiality alone is insufficient.',
        'limitations': ['Not Linux or full Kscaler execution', 'No ancestor throttling, multi-core, scheduler interference, runtime debt or timer jitter', 'Active timer and persistent demand assumed; no idle timer shutdown/slack returns', 'Boundary setter and native boundary arms distinguish clearing local runtime from retaining it', 'Synthetic regular/rollback sequences are not actual controller traces', 'Fixed-sequence comparisons are actuator-level; native feedback sensitivity is not a published-controller ranking'],
        'collection': 'stopped', 'period_selection': 'on_hold', 'fifo_theorem': 'closed',
    })
    save(OUT / 'design/seal.json', {p.name: sha(p) for p in (OUT / 'design').iterdir() if p.name != 'seal.json'})
    for rel in ['README.md', 'docs/current_research_plan.md', 'docs/runtime_io_research_status_20261008.md']:
        target = OUT / 'provenance/status_before' / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / rel).read_bytes())
    print('Frozen replay design before numerical outcomes.')


class Model:
    def __init__(self, initial, phase, arm, changes=(), offset=0, gap=0, policy=None):
        self.q = initial + offset
        self.g = self.q
        self.l = 0
        self.t = 0
        self.used = 0
        self.initial = self.q
        self.grants = 0
        self.lost = 0
        self.nominal_numerator = 0
        self.next_boundary = phase
        self.arm = arm
        self.offset = offset
        self.gap = gap
        self.queue_changes = list(changes)
        self.pending = None
        self.second_write = None
        self.ends = []
        self.job_left = WORK
        self.offered = HORIZON // WORK
        self.nr_periods = 0
        self.nr_throttled = 0
        self.setter_calls = 0
        self.trace = []
        self.policy = policy
        self.next_observation = 0 if policy else math.inf
        self.limit = initial / PERIOD
        self.requested_changes = []
        self.window = None

    def ledger(self, kind, before, discarded=0):
        self.trace.append({'t_us': self.t, 'kind': kind, 'quota_us': self.q,
                           'global_before_us': before, 'global_after_us': self.g,
                           'global_grant_us': self.g - before, 'discarded_local_us': discarded})

    def refill(self, kind):
        before = self.g
        self.g = min(self.g + self.q, self.q)
        self.grants += self.g - before
        self.ledger(kind, before)

    def setter(self, quota, kind):
        self.q = quota
        before = self.g
        discarded = self.l
        self.g = min(self.g + self.q, self.q)
        self.grants += self.g - before
        self.lost += discarded
        self.l = 0
        self.setter_calls += 1
        self.ledger(kind, before, discarded)

    def request(self, quota):
        current = self.limit
        limit = coalesce(quota / PERIOD, current)
        if limit == current:
            return
        self.limit = limit
        quota = round(limit * PERIOD)
        self.requested_changes.append([self.t, quota])
        quota += self.offset
        assert quota >= 1_000
        if self.arm.startswith('boundary'):
            self.pending = quota
        elif self.arm == 'quota_only':
            self.setter(quota, 'quota_write')
        else:
            self.setter(self.q, 'period_write')
            if self.gap:
                self.second_write = (self.t + self.gap, quota)
            else:
                self.setter(quota, 'quota_write')

    def runnable(self):
        return len(self.ends) < self.offered and self.t >= len(self.ends) * WORK

    def allocate(self):
        if self.runnable() and self.l == 0 and self.g:
            amount = min(5_000, self.g)
            self.g -= amount
            self.l += amount

    def run(self):
        end = HORIZON + max(DEADLINES)
        while self.t < end:
            # Resource accounting uses [0,HORIZON); deadline evaluation drains
            # through the last offered job's possible deadline separately.
            if self.t == HORIZON:
                self.window = self.snapshot()
            if self.t == self.next_boundary:
                self.nr_periods += 1
                self.nr_throttled += int(self.runnable() and self.l == 0 and self.g == 0)
                if self.pending is not None:
                    if self.arm == 'boundary_setter':
                        self.setter(self.pending, 'boundary_quota_write')
                    else:
                        self.q = self.pending
                    self.pending = None
                self.refill('periodic_refill')
                self.next_boundary += PERIOD
            if self.second_write is not None and self.t == self.second_write[0]:
                quota = self.second_write[1]
                self.second_write = None
                self.setter(quota, 'quota_write_delayed')
            while self.queue_changes and self.t == self.queue_changes[0][0]:
                _, quota = self.queue_changes.pop(0)
                self.request(quota)
            if self.policy and self.t == self.next_observation:
                stats = {'cpu_usage': self.used / 1e6, 'cpu_stat.nr_throttled': self.nr_throttled}
                proposed = self.policy(self.t / 1e6, stats)
                self.request(round(max(0.01, proposed) * PERIOD))
                self.next_observation += 100_000
            self.allocate()
            future = [end, self.next_boundary, self.next_observation]
            if self.t < HORIZON:
                future.append(HORIZON)
            if self.queue_changes:
                future.append(self.queue_changes[0][0])
            if self.second_write:
                future.append(self.second_write[0])
            running = self.runnable() and self.l > 0
            if running:
                future += [self.t + self.l, self.t + self.job_left]
            elif len(self.ends) < self.offered and not self.runnable():
                future.append(len(self.ends) * WORK)
            next_t = min(x for x in future if x > self.t)
            dt = next_t - self.t
            if self.t < HORIZON:
                self.nominal_numerator += self.q * dt
            if running:
                self.l -= dt
                self.used += dt
                self.job_left -= dt
            self.t = next_t
            if running and self.job_left == 0:
                self.ends.append(self.t)
                self.job_left = WORK
            assert self.initial + self.grants - self.lost == self.used + self.g + self.l
        result = self.window
        result['miss_pct'] = {str(d): 100 * sum(i >= len(self.ends) or self.ends[i] > i * WORK + d for i in range(self.offered)) / self.offered for d in DEADLINES}
        result['completions_us'] = self.ends
        result['requested_changes'] = self.requested_changes
        result['ledger'] = self.trace
        return result

    def snapshot(self):
        return {'cpu_us': self.used, 'nominal_cpu_us': self.nominal_numerator / PERIOD,
                'nominal_numerator': self.nominal_numerator, 'global_us': self.g, 'local_us': self.l,
                'initial_us': self.initial, 'net_grants_us': self.grants, 'discarded_local_us': self.lost,
                'setter_calls': self.setter_calls, 'periods': self.nr_periods,
                'throttled_callbacks': self.nr_throttled}


def replay(spec, phase, arm, offset=0, gap=0):
    return Model(spec['initial'], phase, arm, spec['changes'], offset, gap).run()


def match(spec, phase, arm, target, field):
    # Ordinary scalar bisection; small quantization mismatch is explicit.
    low = 1_000 - min([spec['initial']] + [q for _, q in spec['changes']])
    high = PERIOD
    count = 0
    candidates = []
    while low <= high:
        mid = (low + high) // 2
        result = replay(spec, phase, arm, mid)
        count += 1
        candidates.append((abs(result[field] - target), mid, result))
        if result[field] < target:
            low = mid + 1
        else:
            high = mid - 1
    _, offset, result = min(candidates, key=lambda x: (x[0], abs(x[1])))
    result['matching'] = {'field': field, 'target': target, 'error': result[field] - target,
                          'offset_us': offset, 'replay_evaluations': count,
                          'within_10_cpu_us': abs(result[field] - target) <= 10}
    return result


def compact(result):
    return {k: v for k, v in result.items() if k not in ['ledger', 'completions_us']}


def assess():
    if (OUT / 'results.json').exists():
        raise ValueError('Refusing to overwrite assessed results')
    fixed = []
    ledgers = []
    for spec in sequences():
        for phase in PHASES:
            runs = {arm: replay(spec, phase, arm) for arm in ARMS}
            original = runs['original_pair']
            # Same intended allocation, exact zero-interwrite-gap equivalence.
            assert original['cpu_us'] == runs['quota_only']['cpu_us']
            assert original['miss_pct'] == runs['quota_only']['miss_pct']
            assert original['completions_us'] == runs['quota_only']['completions_us']
            for arm in ['boundary_setter', 'boundary_native']:
                runs[arm + '_match_nominal'] = match(spec, phase, arm, original['nominal_cpu_us'], 'nominal_cpu_us')
                runs[arm + '_match_cpu'] = match(spec, phase, arm, original['cpu_us'], 'cpu_us')
            fixed.append({'id': spec['id'], 'phase_us': phase, 'runs': {arm: compact(r) for arm, r in runs.items()}})
            if phase in [1_000, 50_000, 100_000]:
                ledgers.append({'id': spec['id'], 'phase_us': phase, 'runs': runs})
    feedback = []
    Captain = native_class()
    for phase in PHASES:
        runs = {arm: Model(50_000, phase, arm, policy=Captain(target=0.1, initial_limit=0.5)).run() for arm in ARMS}
        assert runs['original_pair']['requested_changes'] == runs['quota_only']['requested_changes']
        assert runs['original_pair']['completions_us'] == runs['quota_only']['completions_us']
        feedback.append({'phase_us': phase, 'runs': {arm: compact(r) for arm, r in runs.items()}})
    gaps = []
    for spec in sequences()[1:4]:
        for phase in PHASES:
            quota_only = replay(spec, phase, 'quota_only')
            for gap in [10, 100, 1_000]:
                pair = replay(spec, phase, 'original_pair', gap=gap)
                gaps.append({'id': spec['id'], 'phase_us': phase, 'gap_us': gap,
                             'pair': compact(pair), 'quota_only': compact(quota_only)})
    save(OUT / 'results.json', {'fixed': fixed, 'native_scalar_feedback': feedback, 'interwrite_sensitivity': gaps})
    save(OUT / 'reference_ledgers.json', ledgers)
    print(json.dumps({'fixed_phase_cases': len(fixed), 'native_feedback_phase_cases': len(feedback), 'interwrite_cases': len(gaps)}))


if __name__ == '__main__':
    {'prepare': prepare, 'assess': assess}[sys.argv[1]]()
