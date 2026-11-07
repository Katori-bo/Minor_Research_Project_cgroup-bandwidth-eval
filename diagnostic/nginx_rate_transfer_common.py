"""Fresh rate-matching contract; historical scientific evidence stays sealed."""
import itertools
import random
from pathlib import Path
import nginx_power_confirmation_common as previous

old = previous.old
ROOT = previous.ROOT
BASE = ROOT / 'analysis/runtime_io_nginx_rate_transfer/generation-01'
CELLS = [('P0', 4), ('P0', 8)]
POLICIES = {'P0': 'balance_performance'}
FILES = ('diagnostic/nginx_rate_transfer_common.py', 'diagnostic/nginx_rate_transfer_model.py',
    'diagnostic/nginx_rate_transfer_study.py', 'diagnostic/test_nginx_rate_transfer.py',
    'diagnostic/start_nginx_rate_transfer.sh', 'docs/runtime_io_nginx_rate_transfer_protocol_20261010.md')
PROTOCOL = dict(schema='nginx-rate-transfer-v1', fixed_policy='P0', governor='powersave',
    epp='balance_performance', target_cpu=2, quota_us=25000, period_us=100000,
    calibration_rates=[4, 5, 8], validation_rates=[4, 8], calibration_cohorts=6,
    calibration_count=400, blocks=6, validation_cohorts=12, validation_count=300,
    qualification_count=20, qualification_lifetime_count=400, warmup_count=25,
    primary_deadline_ns=20565395, secondary_deadlines_ns=[10000000, 25000000, 50000000],
    settling_sec=10, campaign_total_sec=2700, qualification_total_sec=600,
    cleanup_reserve_sec=120, service_active_sec=120, cohort_reserve_sec=150,
    within_service_reserve_sec=8, retries=0, improvement_reference_pp=2,
    accuracy_upper_reference_pp=5, t_multiplier=2.571, fixed_frequency=False,
    host_policy_writes=False, new_estimator=False, calibration_offers=2400,
    validation_offers=3600, scientific_total_offers=6450, qualification_total_offers=560,
    population='all offered requests under the configured quota, including throttling',
    failed_offers='misses beyond every finite deadline in all references and scores',
    observers='original client/cgroup controls; policy boundary readbacks and CPU3 procstat only')
sha, read, require, save = previous.sha, previous.read, previous.require, previous.save
verify_evidence = previous.verify_evidence


def sources():
    return {name: sha(ROOT / name) for name in FILES}


def config(role, index, policy, rate, block=None):
    require(role in ('qualification', 'qualification_lifetime', 'calibration', 'validation'), 'Foreign role')
    require(policy == 'P0' and type(rate) is int and rate in (4, 5, 8), 'Foreign policy/rate')
    require(type(index) is int and index > 0, 'Foreign index')
    require(role != 'validation' or rate in (4, 8), 'Foreign validation rate')
    require(role != 'qualification_lifetime' or rate == 4, 'Foreign lifetime rate')
    require((role == 'validation' and type(block) is int and block in range(1, 7)) or
            (role != 'validation' and block is None), 'Foreign block')
    return dict(role=role, index=index, policy=policy, rate_rps=rate,
        interval_ns=1000000000 // rate, block=block, count=PROTOCOL[role + '_count'],
        warmup_count=25, profile={4: 'A', 5: 'B', 8: 'C'}[rate])


def schedule(seed):
    rng = random.Random(seed)
    orders = sorted(set(itertools.permutations([4, 4, 5, 5, 8, 8])))
    calibration = [config('calibration', i, 'P0', rate) for i, rate in enumerate(rng.choice(orders), 1)]
    validation = []
    for block in range(1, 7):
        first = len(validation)
        validation.extend(config('validation', first + j, 'P0', rate, block)
                          for j, rate in enumerate(rng.sample([4, 8], 2), 1))
    qualification = [config('qualification', i, 'P0', rate) for i, rate in enumerate([4, 5, 8], 1)]
    qualification.append(config('qualification_lifetime', 4, 'P0', 4))
    return dict(seed=seed, qualification=qualification, calibration=calibration, validation=validation)


def verify_prior():
    previous.verify_prepared(False)
    previous.verify_evidence(previous.BASE / 'campaign')
    require(read(previous.BASE / 'campaign/summary.json')['complete'], 'Completed prior confirmation required')


def verify_prepared(boot=True):
    verify_prior()
    seal = read(BASE / 'preparation-seal.json')
    require(sha(previous.BASE / 'campaign/evidence-seal.json') ==
        read(BASE / 'lineage.json')['power_confirmation_sha256'], 'Prior confirmation changed')
    require(read(BASE / 'protocol.json') == PROTOCOL, 'Rate-transfer protocol changed')
    sched = read(BASE / 'schedule.json')
    require(sched == schedule(sched['seed']), 'Randomized rate schedule changed')
    for name, digest in seal['files_sha256'].items():
        require(sha(ROOT / name) == digest, 'Rate-transfer prepared file changed: ' + name)
    if boot:
        import nginx_qualify as q
        import nginx_power_confirmation_guard as guard
        require(seal['baseline'] == q.h.common.baseline(), 'Host boot/topology changed')
        guard.check_baseline(guard.snapshot())
        require(guard.snapshot() == read(BASE / 'policy-baseline.json'), 'Prepared P0 baseline changed')
    return sched
