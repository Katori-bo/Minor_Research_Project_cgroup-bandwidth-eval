"""V19 frozen configuration and read-only reused V18 evidence primitives."""
import math
import os
from pathlib import Path

import kernel_observer_common as old

ROOT = old.ROOT
PARENT = ROOT / 'analysis/runtime_io_v19_worker_control'
V18 = ROOT / 'analysis/runtime_io_v18_observer_cost/generation-04'
WORKLOAD = {k: v for k, v in old.WORKLOAD.items() if k != 'workers'}
ARMS = ('four_a', 'four_b', 'one')
ORDERS = (('four_a', 'four_b', 'one'), ('four_b', 'one', 'four_a'),
          ('one', 'four_a', 'four_b'), ('four_a', 'one', 'four_b'),
          ('one', 'four_b', 'four_a'), ('four_b', 'four_a', 'one'))
NEW_FILES = ('diagnostic/worker_control_common.py', 'diagnostic/worker_control_service.py',
             'diagnostic/worker_control_study.py', 'diagnostic/worker_control_analysis.py',
             'diagnostic/verify_worker_control.py', 'diagnostic/test_worker_control.py',
             'diagnostic/start_worker_control.sh', 'diagnostic/plot_worker_control.py',
             'docs/runtime_io_v19_worker_control.md', 'docs/runtime_io_v19_plan.md')
digest, read, save = old.digest, old.read, old.save
seal, verify_seal, files = old.seal, old.verify_seal, old.files
capacity, baseline = old.capacity, old.baseline
validate_resources = old.validate_resources


def matrix():
    return [dict(trial=f'b{b}_{a}', block=b, arm=a, order=(b-1)*3+i+1,
                 workers=1 if a == 'one' else 4, **WORKLOAD)
            for b, order in enumerate(ORDERS, 1) for i, a in enumerate(order)]


def rehearsals():
    return [dict(trial='rehearsal_'+a, block=0, arm=a, order=i+1,
                 workers=1 if a == 'one' else 4, **WORKLOAD)
            for i, a in enumerate(('four_a', 'one'))]


def fixture(arm, cancel=False):
    return dict(trial='functional_'+arm+('_cancel' if cancel else ''), block=0,
                arm=arm, order=0, workers=1 if arm == 'one' else 4,
                **dict(WORKLOAD, warmup_sec=0, duration_sec=2,
                       timeout_sec=.001 if cancel else 5,
                       rate=226.42 if cancel else 113.21,
                       burst_low=226.42 if cancel else 56.605,
                       burst_high=226.42 if cancel else 169.815), functional=True)


def validate_config(config, functional=False):
    permitted = [fixture(a) for a in ('four_a', 'one')] + [fixture('one', True)] if functional else matrix()+rehearsals()
    if any(type(config.get(k)) is not int for k in ('workers', 'block', 'order')) or config not in permitted:
        raise ValueError('configuration is outside the frozen V19 matrix')


def source_hashes():
    # Preserve V18's fixed source set; adding a V19 module is not a V18 mutation.
    retained = read(V18/'preparation/manifest.json')['sources']
    for name, sha in retained.items():
        if digest(ROOT/name) != sha:
            raise ValueError('V18 frozen source changed: '+name)
    return {name: digest(ROOT/name) for name in sorted(set(retained) | set(NEW_FILES))}


def owned_directory(value):
    p = Path(value).absolute()
    if p.parent != PARENT or p.is_symlink() or p.resolve() != p:
        raise ValueError('use a direct dedicated V19 generation directory')
    return p


def resolve(session, reference):
    p = Path(reference)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('unsafe evidence reference')
    result = (session/p).resolve()
    if session.resolve() not in result.parents:
        raise ValueError('evidence reference escapes session')
    return result


def arrivals(seconds=60):
    return old.arrivals(seconds)


def schedule(config):
    if config['burst_low'] == 56.605 and config['burst_high'] == 169.815:
        return arrivals(config['duration_sec'])
    if not config.get('functional'):
        raise ValueError('discovery arrival rates changed')
    low, high = config['burst_low'], config['burst_high']
    offsets = []
    i = 0
    while True:
        cycle = math.floor(i/(5*(low+high)))
        within = i-cycle*(5*(low+high))
        sec = cycle*10+(within/low if within < 5*low else 5+(within-5*low)/high)
        stamp = math.floor(sec*1e9+.5)
        if stamp >= config['duration_sec']*1e9:
            return offsets
        offsets.append(stamp)
        i += 1


def validate_client(client, config):
    expected = schedule(config)
    offered = client['total_scheduled']
    if offered != len(expected):
        raise ValueError('wrong offered count')
    rows = client['requests']
    ids = [r['ID'] for r in rows]
    if len(set(ids)) != len(ids) or any(type(i) is not int or not 0 <= i < offered for i in ids):
        raise ValueError('duplicate or unexpected client request identity')
    if any(r['ScheduledOffsetNs'] != expected[r['ID']] for r in rows):
        raise ValueError('relative arrival vector differs from frozen schedule')
    dropped = client['client_dropped']
    if type(dropped) is not int or dropped < 0 or offered-len(rows) != dropped:
        raise ValueError('missing client rows do not match dropped offers')
    good = sum(not r['Error'] and r['StatusCode'] == 200 for r in rows)
    rejected = sum(not r['Error'] and r['StatusCode'] == 503 for r in rows)
    errors = len(rows)-good-rejected
    if (client['total_completed'] != len(rows) or client['total_dispatched'] != len(rows)
            or client['total_success'] != good or client['total_503'] != rejected or client['total_errors'] != errors):
        raise ValueError('client total/outcome conservation failed')
    if not 0 <= client['missed_arrivals'] <= offered:
        raise ValueError('invalid missed-arrival count')
    for r in rows:
        if r['EndToEndLatencyNs'] < 0 or r['CompletedOffsetNs'] != r['ScheduledOffsetNs']+r['EndToEndLatencyNs']:
            raise ValueError('client completion timing identity failed')
    for key, expected_value in dict(pattern='bursty', duration_sec=config['duration_sec'],
            target_rate=config['rate'], burst_low_rate=config['burst_low'], burst_high_rate=config['burst_high'],
            burst_period_sec=10, client_trace_enabled=True).items():
        if client.get(key) != expected_value:
            raise ValueError('client workload differs: '+key)
    return expected


def service_argv(image, qualification, name, config):
    argv = old.service_argv(image, qualification, name)
    argv[argv.index('WORKERS=4')] = 'WORKERS='+str(config['workers'])
    return argv


def process_identity(pid):
    stat = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
    return dict(pid=pid, start_ticks=stat[19], state=stat[0], uid=Path(f'/proc/{pid}').stat().st_uid)


def same_process(identity):
    try:
        current = process_identity(identity['pid'])
        return current['start_ticks'] == identity['start_ticks'] and current['uid'] == identity['uid'] and current['state'] not in ('Z', 'X')
    except (FileNotFoundError, ProcessLookupError):
        return False
