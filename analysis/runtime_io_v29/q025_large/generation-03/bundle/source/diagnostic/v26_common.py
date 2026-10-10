"""Frozen V26 low-load qualification configuration, provenance and exact all-offer accounting."""
import math
import subprocess
import sys
from pathlib import Path

import execution_delay_common as legacy

ROOT = legacy.ROOT
PARENT = ROOT / 'analysis/runtime_io_v26'
DESIGN = ROOT / 'analysis/runtime_io_v26_design/20261007'
PREVIOUS = ROOT / 'analysis/runtime_io_v25/generation-01'
REPAIR = ROOT / 'analysis/runtime_io_v24_native_software/20261007'
BUILD = ROOT / 'analysis/runtime_io_v24_native_build/revision-01'
ORIGINAL = ROOT / 'analysis/runtime_io_v20_execution_delay/generation-03/preparation'
V23 = ROOT / 'analysis/runtime_io_v23/generation-01'
read, save, digest = legacy.read, legacy.save, legacy.digest
seal, verify_seal, files = legacy.seal, legacy.verify_seal, legacy.files
baseline, capacity = legacy.baseline, legacy.capacity
resolve, process_identity, same_process = legacy.resolve, legacy.process_identity, legacy.same_process
validate_resources, validate_state, service_argv = legacy.validate_resources, legacy.validate_state, legacy.service_argv
ARMS = ('A', 'B')


def require_desktop_absent():
    result = subprocess.run(['pgrep', '-x', 'ChatGPT|Codex'], capture_output=True, text=True, timeout=3)
    if result.returncode not in (0, 1) or result.returncode == 0:
        raise ValueError('fully quit Codex/ChatGPT before external measurement')


def design():
    value = read(DESIGN / 'seal.json')
    for name, expected in value['files_sha256'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('frozen Step 3 design changed: ' + name)
    return read(DESIGN / 'design.json')


def config(slot):
    rate=slot['rate']
    return dict(legacy.WORKLOAD,duration_sec=30,warmup_sec=20,
        quota_us=50000,period_us=100000,worker_yield=False,
        trial=slot['id'],arm='L',block=slot['block'],order=slot['collection_order'],
        role='low_load_qualification',repeat=slot['repeat'],size='small',iterations=44000,
        traffic_pattern='steady',rate=rate,burst_low=rate,burst_high=rate,
        burst_period_sec=10,counter_probe=True)


def matrix():
    return [config(slot) for slot in design()['trial_order']]


def warmup_config(cfg):
    return dict(cfg,duration_sec=20)


def functional_configs():
    result=[]
    for rate in (15,30):
        slot=dict(id='functional_rate'+str(rate),rate=rate,block=0,collection_order=0,repeat=0)
        cfg=dict(config(slot),functional=True,duration_sec=2,warmup_sec=0)
        result.append(cfg)
        result.append(dict(cfg,trial=cfg['trial']+'_cancel',timeout_sec=.001,
                           rate=226.4,burst_low=226.4,burst_high=226.4))
    return result


def validate_config(cfg, functional=False):
    if cfg not in (functional_configs() if functional else matrix()):
        raise ValueError('configuration outside frozen V26 low-load qualification design')
    if any(type(cfg[k]) is not int for k in ('workers','block','order','repeat','quota_us','period_us','iterations','burst_period_sec')):
        raise ValueError('configuration integer types differ')
    if type(cfg['worker_yield']) is not bool or type(cfg['counter_probe']) is not bool:
        raise ValueError('configuration boolean type differs')


def generated_schedule(rate, seconds):
    if type(rate) not in (int,float) or not math.isfinite(rate) or rate<=0 or seconds<=0:
        raise ValueError('invalid steady schedule')
    result=[]
    i=0
    while True:
        stamp=math.floor((i/rate)*1e9+.5)
        if stamp>=seconds*1e9:return result
        result.append(stamp);i+=1


def schedule(cfg):
    if cfg.get('functional'):
        return generated_schedule(cfg['rate'],cfg['duration_sec'])
    label='warmup' if cfg['duration_sec']==20 else 'measurement'
    return read(DESIGN/('rate'+str(cfg['rate'])+'_'+label+'_offsets_ns.json'))


def validate_client(client, cfg):
    expected = schedule(cfg)
    offered, rows = client['total_scheduled'], client['requests']
    if offered != len(expected):
        raise ValueError('offered cohort differs from frozen schedule')
    ids = [r['ID'] for r in rows]
    if len(set(ids))!=len(ids) or any(type(i) is not int or not 0<=i<offered for i in ids):
        raise ValueError('duplicate/unexpected client IDs')
    if any(r['ScheduledOffsetNs']!=expected[r['ID']] for r in rows):
        raise ValueError('exact scheduled offsets differ')
    if type(client['client_dropped']) is not int or client['client_dropped']<0 or offered-len(rows)!=client['client_dropped']:
        raise ValueError('dropped-offer conservation failed')
    good = sum(not r['Error'] and r['StatusCode']==200 for r in rows)
    rejected = sum(not r['Error'] and r['StatusCode']==503 for r in rows)
    counts = dict(total_completed=len(rows), total_dispatched=len(rows), total_success=good,
                  total_503=rejected, total_errors=len(rows)-good-rejected)
    if any(client[k]!=v for k,v in counts.items()):
        raise ValueError('client outcome conservation failed')
    if not 0<=client['missed_arrivals']<=offered:
        raise ValueError('invalid missed-arrival count')
    for r in rows:
        if r['EndToEndLatencyNs']<0 or r['CompletedOffsetNs']!=r['ScheduledOffsetNs']+r['EndToEndLatencyNs']:
            raise ValueError('client timing identity failed')
    fields = dict(pattern=cfg['traffic_pattern'], duration_sec=cfg['duration_sec'],
        target_rate=(cfg['burst_low']+cfg['burst_high'])/2 if cfg['traffic_pattern']=='bursty' else cfg['rate'],
        burst_low_rate=cfg['burst_low'], burst_high_rate=cfg['burst_high'],
        burst_period_sec=cfg['burst_period_sec'], client_trace_enabled=True)
    if any(client.get(k)!=v for k,v in fields.items()):
        raise ValueError('client traffic/settings differ')
    return expected


def technical_client(client):
    lag = client['dispatch_lag_summary']['p99_ms']
    if client['client_dropped'] or client['missed_arrivals'] or not math.isfinite(lag) or lag>2:
        raise ValueError('technical client dispatch/capacity failure')
    if client['total_503'] or client['total_errors']:
        raise ValueError('low-load cohort has unsuccessful offers or admission rejections')


def owned_directory(value):
    p = Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use a direct dedicated V26 low-load qualification generation directory')
    return p


def source_hashes():
    names=set(read(PREVIOUS/'bundle/manifest.json')['sources'])
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v26_*.py'))
    names.update(('diagnostic/test_v26.py','diagnostic/start_v26.sh',
                  'docs/runtime_io_v26_protocol.md','docs/runtime_io_v26_execution.md'))
    return {name:digest(ROOT/name) for name in sorted(names)}
