"""Frozen V27 load-composition configuration, provenance and exact schedules."""
import math
import subprocess
from pathlib import Path
import execution_delay_common as legacy

ROOT = legacy.ROOT
PARENT = ROOT / 'analysis/runtime_io_v27'
DESIGN = ROOT / 'analysis/runtime_io_v27_design/20261007'
PREVIOUS = ROOT / 'analysis/runtime_io_v26/generation-01'
CLIENT_BUILD = ROOT / 'analysis/runtime_io_v27_client_build/revision-01'
REPAIR = ROOT / 'analysis/runtime_io_v24_native_software/20261007'
BUILD = ROOT / 'analysis/runtime_io_v24_native_build/revision-01'
ORIGINAL = ROOT / 'analysis/runtime_io_v20_execution_delay/generation-03/preparation'
V23 = ROOT / 'analysis/runtime_io_v23/generation-01'
read, save, digest = legacy.read, legacy.save, legacy.digest
seal, verify_seal, files = legacy.seal, legacy.verify_seal, legacy.files
baseline, capacity = legacy.baseline, legacy.capacity
resolve, process_identity, same_process = legacy.resolve, legacy.process_identity, legacy.same_process
validate_resources, validate_state, service_argv = legacy.validate_resources, legacy.validate_state, legacy.service_argv


def require_desktop_absent():
    result = subprocess.run(['pgrep', '-x', 'ChatGPT|Codex'], capture_output=True, text=True, timeout=3)
    if result.returncode not in (0, 1) or result.returncode == 0:
        raise ValueError('fully quit Codex/ChatGPT before external measurement')


def design():
    value = read(DESIGN / 'seal.json')
    for name, expected in value['files_sha256'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('frozen V27 design changed: ' + name)
    return read(DESIGN / 'design.json')


def config(slot):
    low = slot['low_rate']
    return dict(legacy.WORKLOAD, duration_sec=60, warmup_sec=20,
        quota_us=50000, period_us=100000, worker_yield=False,
        trial=slot['id'], arm='M', block=slot['block'], order=slot['collection_order'],
        role='load_composition_comparison', repeat=slot['block'], size='small', iterations=44000,
        low_rate=low, traffic_pattern='bursty', rate=(10*low+5*169.8)/15,
        burst_low=low, burst_high=169.8, burst_period_sec=15, burst_low_duration_sec=10,
        counter_probe=slot['counter_probe'])


def matrix():
    return [config(slot) for slot in design()['trial_order']]


def warmup_config(cfg):
    low = cfg['low_rate']
    return dict(cfg, duration_sec=20, traffic_pattern='steady', rate=low, burst_low=low, burst_high=low)


def functional_configs():
    result=[]
    for low in (15, 30):
        slot=dict(id='functional_rate'+str(low),low_rate=low,block=0,collection_order=0,counter_probe=True)
        cfg=dict(config(slot),functional=True,duration_sec=15,warmup_sec=0)
        result.append(cfg)
        result.append(dict(cfg,trial=cfg['trial']+'_cancel',timeout_sec=.001,duration_sec=2,traffic_pattern='steady',
                           rate=226.4,burst_low=226.4,burst_high=226.4))
    return result


def validate_config(cfg, functional=False):
    if cfg not in (functional_configs() if functional else matrix()):
        raise ValueError('configuration outside frozen V27 composition design')
    if any(type(cfg[k]) is not int for k in ('workers','block','order','repeat','quota_us','period_us','iterations','burst_period_sec','burst_low_duration_sec','low_rate')):
        raise ValueError('configuration integer types differ')
    if type(cfg['worker_yield']) is not bool or type(cfg['counter_probe']) is not bool:
        raise ValueError('configuration boolean type differs')


def generated_schedule(cfg):
    result=[]
    i=0
    while True:
        if cfg['traffic_pattern']=='steady':
            sec=i/cfg['rate']
        else:
            low, high = cfg['burst_low'], cfg['burst_high']
            a, period = cfg['burst_low_duration_sec'], cfg['burst_period_sec']
            n=a*low+(period-a)*high
            cycle=math.floor(i/n);within=i-cycle*n
            sec=cycle*period+(within/low if within<a*low else a+(within-a*low)/high)
        stamp=math.floor(sec*1e9+.5)
        if stamp>=cfg['duration_sec']*1e9:return result
        result.append(stamp);i+=1


def schedule(cfg):
    if cfg.get('functional'):return generated_schedule(cfg)
    label='warmup' if cfg['traffic_pattern']=='steady' else 'measurement'
    return read(DESIGN/('rate'+str(cfg['low_rate'])+'_'+label+'_offsets_ns.json'))


def validate_client(client, cfg):
    expected=schedule(cfg)
    offered,rows=client['total_scheduled'],client['requests']
    if offered!=len(expected):raise ValueError('offered cohort differs from frozen schedule')
    ids=[r['ID'] for r in rows]
    if len(set(ids))!=len(ids) or any(type(i) is not int or not 0<=i<offered for i in ids):
        raise ValueError('duplicate/unexpected client IDs')
    if any(r['ScheduledOffsetNs']!=expected[r['ID']] for r in rows):raise ValueError('exact scheduled offsets differ')
    if type(client['client_dropped']) is not int or client['client_dropped']<0 or offered-len(rows)!=client['client_dropped']:
        raise ValueError('dropped-offer conservation failed')
    good=sum(not r['Error'] and r['StatusCode']==200 for r in rows)
    rejected=sum(not r['Error'] and r['StatusCode']==503 for r in rows)
    counts=dict(total_completed=len(rows),total_dispatched=len(rows),total_success=good,total_503=rejected,total_errors=len(rows)-good-rejected)
    if any(client[k]!=v for k,v in counts.items()):raise ValueError('client outcome conservation failed')
    if not 0<=client['missed_arrivals']<=offered:raise ValueError('invalid missed-arrival count')
    for r in rows:
        if r['EndToEndLatencyNs']<0 or r['CompletedOffsetNs']!=r['ScheduledOffsetNs']+r['EndToEndLatencyNs']:
            raise ValueError('client timing identity failed')
    fields=dict(pattern=cfg['traffic_pattern'],duration_sec=cfg['duration_sec'],target_rate=cfg['rate'],
        burst_low_rate=cfg['burst_low'],burst_high_rate=cfg['burst_high'],burst_period_sec=cfg['burst_period_sec'],
        burst_low_duration_sec=cfg['burst_low_duration_sec'],client_trace_enabled=True)
    if any(client.get(k)!=v for k,v in fields.items()):raise ValueError('client traffic/settings differ')
    return expected


def technical_client(client):
    lag=client['dispatch_lag_summary']['p99_ms']
    if client['client_dropped'] or client['missed_arrivals'] or not math.isfinite(lag) or lag>2:
        raise ValueError('technical client dispatch/capacity failure')
    # Drops, timeout/errors and admission rejections are retained outcomes, not
    # grounds to replace a technically valid performance trial.


def owned_directory(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use a direct dedicated V27 composition generation directory')
    return p


def source_hashes():
    names=set(read(PREVIOUS/'bundle/manifest.json')['sources'])
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v27_*.py'))
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic/v27_loadgen').iterdir() if p.suffix in ('.go','.mod'))
    names.update(('diagnostic/test_v27.py','diagnostic/start_v27.sh',
                  'docs/runtime_io_v27_protocol.md','docs/runtime_io_v27_execution.md'))
    return {name:digest(ROOT/name) for name in sorted(names)}


def verify_client_build():
    verify_seal(CLIENT_BUILD)
    m=read(CLIENT_BUILD/'manifest.json')
    names=('main.go','main_test.go','go.mod')
    expected={name:digest(ROOT/'diagnostic/v27_loadgen'/name) for name in names}
    if (m['sources']!=expected or m['binary_sha256']!=digest(CLIENT_BUILD/'loadgen')
            or not m['test_passed'] or not m['vet_passed'] or not m['race_passed']
            or not m['all_frozen_vectors_match_binary']):
        raise ValueError('asymmetric client build/verification differs')
    for name,h in expected.items():
        if digest(CLIENT_BUILD/'source'/name)!=h:raise ValueError('client build source snapshot differs')
    return m
