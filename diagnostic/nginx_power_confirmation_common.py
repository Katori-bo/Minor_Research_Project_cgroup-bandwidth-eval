"""Separate fixed power-policy study; original scientific bundles stay sealed."""
import itertools
import random
from pathlib import Path
import nginx_prediction_common as old

ROOT = old.ROOT
BASE = ROOT / 'analysis/runtime_io_nginx_power_confirmation/generation-01'
POLICIES = {'P0': 'balance_performance', 'P1': 'performance'}
CELLS = [('P0', 4), ('P0', 8), ('P1', 4), ('P1', 8)]
FILES = ('diagnostic/nginx_power_confirmation_common.py', 'diagnostic/nginx_power_confirmation_guard.py',
         'diagnostic/nginx_power_confirmation_model.py', 'diagnostic/nginx_power_confirmation_study.py',
         'diagnostic/test_nginx_power_confirmation.py', 'diagnostic/start_nginx_power_confirmation.sh',
         'docs/runtime_io_nginx_power_confirmation_protocol_20261010.md')
PROTOCOL = dict(schema='nginx-power-confirmation-v1', policies=POLICIES, target_cpu=2,
    governor='powersave', quota_us=25000, period_us=100000, rates=[4, 8],
    calibration_rate=5, calibration_cohorts=4, calibration_count=400,
    blocks=6, validation_count=300, qualification_count=20, warmup_count=25,
    primary_deadline_ns=20565395, secondary_deadlines_ns=[10000000, 25000000, 50000000],
    settling_sec=10, campaign_total_sec=2700, cleanup_reserve_sec=120,
    qualification_total_sec=600, service_active_sec=120, policy_lease_sec=150,
    retries=0, improvement_reference_pp=2, accuracy_upper_reference_pp=5,
    t_multiplier=2.571, fixed_frequency=False, new_estimator=False,
    population='all offered requests under the configured quota, including throttling',
    failed_offers='misses beyond every finite deadline in all references and scores',
    observations_allowed=['measurement_throttling', 'warmup_throttling', 'client_response_overlap',
        'client_inflight_cap', 'dispatch_gate', 'unsuccessful_offers'],
    observers='original client/cgroup controls; policy boundary readbacks and CPU3 procstat only')
sha, read, require = old.sha, old.read, old.require


def save(path, value):
    import json
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def sources():
    return {name: sha(ROOT / name) for name in FILES}


def config(role, index, policy, rate, block=None):
    require(role in ('qualification', 'calibration', 'validation'), 'Foreign role')
    require(policy in POLICIES and rate in (4, 5, 8), 'Foreign treatment')
    require(type(index) is int and index > 0, 'Foreign index')
    require((role == 'calibration') == (rate == 5), 'Foreign calibration rate')
    require((role == 'validation') == (block in range(1, 7)), 'Foreign block')
    return dict(role=role, index=index, policy=policy, rate_rps=rate,
        interval_ns=1000000000 // rate, block=block,
        count=PROTOCOL[role + '_count'], warmup_count=25,
        profile='A' if rate == 4 else ('C' if rate == 8 else None))


def schedule(seed):
    rng = random.Random(seed)
    orders = sorted(set(itertools.permutations(['P0', 'P0', 'P1', 'P1'])))
    calibration = [config('calibration', i, p, 5) for i, p in enumerate(rng.choice(orders), 1)]
    validation = []
    for b in range(1, 7):
        cells = rng.sample(CELLS, 4)
        first = len(validation)
        validation.extend(config('validation', first + j, p, r, b)
                          for j, (p, r) in enumerate(cells, 1))
    qualification = [config('qualification', i, p, r) for i, (p, r) in enumerate(CELLS, 1)]
    return dict(seed=seed, qualification=qualification, calibration=calibration, validation=validation)


def verify_prepared(boot=True):
    # Old qualification belongs to its recorded boot. A fresh four-cell smoke
    # qualification is mandatory for this generation's newly captured baseline.
    old.verify(False)
    import nginx_power_common as pilot
    pilot.verify_prepared(False)
    pilot.verify_evidence(pilot.BASE / 'campaign')
    require(sha(pilot.BASE / 'campaign/evidence-seal.json') ==
            read(BASE / 'lineage.json')['stopped_pilot_sha256'], 'Stopped pilot changed')
    seal = read(BASE / 'preparation-seal.json')
    require(read(BASE / 'protocol.json') == PROTOCOL, 'Power protocol changed')
    sched = read(BASE / 'schedule.json')
    require(sched == schedule(sched['seed']), 'Randomized schedule changed')
    for name, digest in seal['files_sha256'].items():
        require(sha(ROOT / name) == digest, 'Power prepared file changed: ' + name)
    if boot:
        import nginx_qualify as q
        require(seal['baseline'] == q.h.common.baseline(), 'Power host boot/topology changed')
        import nginx_power_confirmation_guard as guard
        require(guard.snapshot() == read(BASE / 'policy-baseline.json'), 'Prepared host policy baseline changed')
    return sched


def verify_evidence(directory):
    old.verify_evidence(directory)
