"""Frozen V24 revision 2 configuration, provenance and exact all-offer accounting."""
import math
import subprocess
import sys
from pathlib import Path

import execution_delay_common as legacy

ROOT = legacy.ROOT
PARENT = ROOT / 'analysis/runtime_io_v24'
DESIGN = ROOT / 'analysis/runtime_io_v24_design/20261007'
PREVIOUS = PARENT / 'generation-01'
REPAIR = ROOT / 'analysis/runtime_io_v24_sampler_repair/20261007'
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
    info=design()['sizes'][slot['size']]
    return dict(legacy.WORKLOAD,quota_us=50000,period_us=100000,worker_yield=False,
        trial=slot['id'],arm='C',block=slot['block'],order=slot['collection_order'],role='mechanism',
        size=slot['size'],iterations=info['iterations'],traffic_pattern='bursty',
        burst_low=info['low'],burst_high=info['high'],rate=(info['low']+info['high'])/2,
        burst_period_sec=10,counter_probe=slot['counter_probe'])


def matrix():
    return [config(slot) for slot in design()['trial_order']]


def warmup_config(cfg):
    return dict(cfg,duration_sec=20)


def functional_configs():
    result=[]
    for size in ('small','large'):
        slot=dict(id='functional_'+size,size=size,block=0,collection_order=0,counter_probe=True)
        cfg=dict(config(slot),functional=True,duration_sec=2,warmup_sec=0)
        result.append(cfg)
        rate=226.4/design()['sizes'][size]['scale']
        result.append(dict(cfg,trial=cfg['trial']+'_cancel',timeout_sec=.001,
                           rate=rate,burst_low=rate,burst_high=rate))
    return result


def validate_config(cfg, functional=False):
    if cfg not in (functional_configs() if functional else matrix()):
        raise ValueError('configuration outside frozen V24 revision 2 design')
    if any(type(cfg[k]) is not int for k in ('workers','block','order','quota_us','period_us','iterations','burst_period_sec')):
        raise ValueError('configuration integer types differ')
    if type(cfg['worker_yield']) is not bool or type(cfg['counter_probe']) is not bool:
        raise ValueError('configuration boolean type differs')


def schedule(cfg):
    if not cfg.get('functional'):
        label='warmup' if cfg['duration_sec']==20 else cfg['arm']
        return read(DESIGN/(cfg['size']+'_'+label+'_offsets_ns.json'))
    result = []
    i = 0
    while True:
        if cfg['traffic_pattern']=='steady':
            sec = i/cfg['rate']
        else:
            low, high = cfg['burst_low'], cfg['burst_high']
            half=cfg['burst_period_sec']/2
            cyc = math.floor(i/(half*(low+high)))
            within = i-cyc*(half*(low+high))
            sec = cyc*cfg['burst_period_sec']+(within/low if within<half*low else half+(within-half*low)/high)
        stamp = math.floor(sec*1e9+.5)
        if stamp >= cfg['duration_sec']*1e9:
            return result
        result.append(stamp)
        i += 1


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


def owned_directory(value):
    p = Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use a direct dedicated V24 revision 2 generation directory')
    return p


def source_hashes():
    # Retain revision-1 sources verbatim, alongside separately named repairs.
    names=set(read(PREVIOUS/'bundle/manifest.json')['sources'])
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v24r2_*.py'))
    names.update(('diagnostic/test_v24r2.py','diagnostic/start_v24r2.sh',
                  'docs/runtime_io_v24r2_execution.md','docs/runtime_io_v24r2_sampler_revision.md',
                  'analysis/check_v24r2_sampler.py'))
    return {name:digest(ROOT/name) for name in sorted(names)}
