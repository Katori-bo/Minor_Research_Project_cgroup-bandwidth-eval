"""Prospective complete-response prediction contract; prior evidence stays frozen."""
from pathlib import Path
import nginx_common as n

ROOT = n.ROOT
BASE = ROOT / 'analysis/runtime_io_nginx_prediction/generation-01'
PLAN = ROOT / 'docs/runtime_io_nginx_prediction_protocol_20261009.md'
FILES = ('diagnostic/nginx_prediction_common.py', 'diagnostic/nginx_prediction_model.py',
         'diagnostic/nginx_prediction_study.py', 'diagnostic/nginx_prediction_prepare.py',
         'diagnostic/test_nginx_prediction.py', 'diagnostic/start_nginx_prediction.sh',
         'docs/runtime_io_nginx_prediction_protocol_20261009.md')
PROTOCOL = dict(version='nginx-full-response-prediction-v1',
    calibration_cohorts=4, calibration_interval_ns=200000000, calibration_offers=400,
    validation_intervals_ns=dict(A=250000000, B=166666667, C=125000000),
    validation_offers=300, block_orders=['ABC', 'BCA', 'CAB', 'ACB', 'CBA', 'BAC'],
    preparation_offers=20, pilot_offers=100, warmup_offers=25, settling_sec=10,
    service_active_sec=120, campaign_total_sec=2700, cleanup_reserve_sec=120,
    retries=0, primary_deadline='lower pooled calibration median in integer nanoseconds',
    miss_rule='unsuccessful OR BodyDoneNs - ScheduledNs > deadline_ns',
    predictor='fresh full-response empirical CDF, constant across held-out rates',
    primary_accuracy_upper_bound_pp=5, block_t_multiplier=2.571, block_t_df=5,
    secondary_deadlines_ns=[10000000, 25000000, 50000000],
    queue_observed=False, queue_subtraction=False, comparator=None,
    input_sha256=n.INPUT_SHA, source_sha256=n.SOURCE_SHA, limits=n.LIMITS,
    historical_pilot_is_calibration=False, independent_host_replication=False)
sha, read, save, require = n.sha, n.read, n.save, n.require


def sources():
    return {name: sha(ROOT / name) for name in FILES}


def config(role, index, profile=None, block=None):
    require(role in ('preparation', 'pilot', 'calibration', 'validation'), 'Unknown study role')
    require(isinstance(index, int) and index > 0, 'Invalid cohort index')
    if role == 'calibration':
        require(index <= 4 and profile is None and block is None, 'Foreign calibration configuration')
        interval, count = PROTOCOL['calibration_interval_ns'], PROTOCOL['calibration_offers']
    else:
        require(profile in PROTOCOL['validation_intervals_ns'], 'Foreign rate profile')
        interval = PROTOCOL['validation_intervals_ns'][profile]
        count = PROTOCOL[role + '_offers']
        if role == 'validation':
            require(block in range(1, 7) and index in range(1, 19) and
                PROTOCOL['block_orders'][block - 1][(index - 1) % 3] == profile and
                (index - 1) // 3 + 1 == block, 'Validation order differs')
        else:
            require(index in range(1, 4) and profile == 'ABC'[index - 1] and block is None,
                    'Qualification order differs')
    return dict(role=role, index=index, profile=profile, block=block,
                interval_ns=interval, count=count, warmup_count=25)


def configs(role):
    if role == 'calibration': return [config(role, i) for i in range(1, 5)]
    if role in ('preparation', 'pilot'): return [config(role, i, p) for i, p in enumerate('ABC', 1)]
    return [config(role, (b - 1) * 3 + j, p, b)
            for b, order in enumerate(PROTOCOL['block_orders'], 1) for j, p in enumerate(order, 1)]


def verify_evidence(directory):
    seal = read(directory / 'evidence-seal.json')['files_sha256']
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*')
              if p.is_file() and p != directory / 'evidence-seal.json'}
    require(actual == set(seal), 'Study evidence file set changed')
    for name, digest in seal.items():
        require(sha(directory / name) == digest, 'Study evidence changed: ' + name)


def verify(boot=True):
    n.verify(boot)
    import nginx_qualify as q
    require(q.replay()['passed'], 'Prior NGINX qualification unavailable')
    seal = read(BASE / 'bundle-seal.json')
    require(seal['protocol'] == PROTOCOL and read(BASE / 'protocol.json') == PROTOCOL,
            'Prospective protocol changed')
    if boot:
        require(seal['baseline'] == q.h.common.baseline(), 'Study host boot/topology changed')
    for name, digest in seal['files_sha256'].items():
        require(sha(ROOT / name) == digest, 'Study prepared file changed: ' + name)
