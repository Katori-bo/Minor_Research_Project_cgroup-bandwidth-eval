"""Prospective V29 schedules and immutable scientific configuration."""
import math
import os
from pathlib import Path
import v27r3_common as retained

ROOT = retained.ROOT
CONTEXTS = {'q050_small': {'quota_us': 50000, 'iterations': 44000, 'size': 'small'}, 'q025_small': {'quota_us': 25000, 'iterations': 44000, 'size': 'small'}, 'q050_large': {'quota_us': 50000, 'iterations': 88000, 'size': 'large'}, 'q025_large': {'quota_us': 25000, 'iterations': 88000, 'size': 'large'}}
ACTIVE=os.environ.get('RESEARCH_V29_CONTEXT','q050_small')
if ACTIVE not in CONTEXTS:raise ValueError('Unknown V29 context')
CONTEXT=CONTEXTS[ACTIVE]
SCALE=CONTEXT['quota_us']/50000*44000/CONTEXT['iterations']
DEADLINES_MS=(25,50,100,200,500,1000)
PARENT = ROOT/'analysis/runtime_io_v29'/ACTIVE
DESIGN = ROOT/'analysis/runtime_io_v29_design/20261009'/ACTIVE
ORIGINAL, CLIENT_BUILD = retained.ORIGINAL, retained.CLIENT_BUILD
HISTORY = ROOT/'analysis/runtime_io_v28/generation-01'
for _name in ('read','save','digest','seal','verify_seal','files','baseline','capacity',
              'resolve','process_identity','same_process','validate_resources','validate_state',
              'service_argv','require_desktop_absent','verify_client_build','technical_client'):
    globals()[_name] = getattr(retained, _name)


def design():
    value = read(DESIGN/'seal.json')
    for name, expected in value['files_sha256'].items():
        if digest(ROOT/name)!=expected:raise ValueError('frozen V29 design changed: '+name)
    return read(DESIGN/'design.json')


def config(slot):
    kind, rate = slot['kind'], slot['low_rate']
    period = slot.get('period_sec',15)
    low_duration = slot.get('low_duration_sec',10)
    high = slot.get('high_rate',169.8)
    duration = 60 if kind in ('mixed','validation') else 30
    pattern = 'idle' if kind=='idle' else ('steady' if kind=='steady' else 'bursty')
    return dict(retained.legacy.WORKLOAD,duration_sec=duration,warmup_sec=20,
        quota_us=CONTEXT['quota_us'],period_us=100000,worker_yield=False,trial=slot['id'],arm='M',
        block=slot['block'],order=slot['collection_order'],role=kind,repeat=slot['block'],
        context=ACTIVE,reference_low_rate=rate/SCALE,size=CONTEXT['size'],iterations=CONTEXT['iterations'],low_rate=rate,traffic_pattern=pattern,
        rate=rate if pattern!='bursty' else (low_duration*rate+(period-low_duration)*high)/period,
        burst_low=rate,burst_high=rate if pattern!='bursty' else high,
        burst_period_sec=period,burst_low_duration_sec=low_duration,counter_probe=False)


def matrix():return [config(s) for s in design()['trial_order']]
def calibration_configs():return [x for x in matrix() if x['role']!='validation']
def validation_configs():return [x for x in matrix() if x['role']=='validation']


def warmup_config(cfg):
    idle = cfg['traffic_pattern']=='idle'
    return dict(cfg,duration_sec=20,traffic_pattern='idle' if idle else 'steady',
                rate=cfg['low_rate'],burst_low=cfg['low_rate'],burst_high=cfg['low_rate'])


def functional_configs():
    scientific=matrix()
    selected=[next(x for x in scientific if x['role']=='idle'),
              next(x for x in scientific if x['role']=='steady' and x['reference_low_rate']==120),
              next(x for x in scientific if x['role']=='mixed' and x['reference_low_rate']==30)]
    selected += [next(x for x in scientific if x['role']=='validation' and x['burst_period_sec']==p) for p in (6,12)]
    result=[dict(x,trial='functional_'+str(i),functional=True,duration_sec=2 if x['traffic_pattern']!='bursty' else x['burst_period_sec'],warmup_sec=0) for i,x in enumerate(selected)]
    result.append(dict(result[1],trial='functional_cancel',timeout_sec=.001,duration_sec=2,traffic_pattern='steady',rate=226.4*SCALE,burst_low=226.4*SCALE,burst_high=226.4*SCALE))
    return result


def validate_config(cfg,functional=False):
    if cfg not in (functional_configs() if functional else matrix()):
        raise ValueError('configuration outside frozen V29 design')
    if cfg['counter_probe'] is not False:raise ValueError('V29 requires sampler off')


def generated_schedule(cfg):
    if cfg['traffic_pattern']=='idle':return []
    return retained.generated_schedule(cfg)


def schedule(cfg):
    if cfg.get('functional'):return generated_schedule(cfg)
    name=cfg['trial']+('_warmup' if cfg['duration_sec']==20 else '_measurement')+'_offsets_ns.json'
    result=read(DESIGN/'schedules'/name)
    if result!=generated_schedule(cfg):raise ValueError('frozen schedule differs from declared generator')
    return result


def validate_client(client,cfg):
    # Retained conservation checks use their own schedule function; supply the
    # exact V29 vector through a local copy of those checks, with no monkeypatch.
    expected=schedule(cfg)
    offered,rows=client['total_scheduled'],client['requests']
    if offered!=len(expected):raise ValueError('offered cohort differs from frozen schedule')
    ids=[r['ID'] for r in rows]
    if len(set(ids))!=len(ids) or any(type(i) is not int or not 0<=i<offered for i in ids):raise ValueError('client IDs differ')
    if any(r['ScheduledOffsetNs']!=expected[r['ID']] for r in rows):raise ValueError('exact offsets differ')
    if type(client['client_dropped']) is not int or client['client_dropped']<0 or offered-len(rows)!=client['client_dropped']:raise ValueError('dropped-offer conservation failed')
    good=sum(not r['Error'] and r['StatusCode']==200 for r in rows)
    rejected=sum(not r['Error'] and r['StatusCode']==503 for r in rows)
    counts=dict(total_completed=len(rows),total_dispatched=len(rows),total_success=good,total_503=rejected,total_errors=len(rows)-good-rejected)
    if any(client[k]!=v for k,v in counts.items()):raise ValueError('outcome conservation failed')
    if not 0<=client['missed_arrivals']<=offered:raise ValueError('invalid missed arrivals')
    if any(r['EndToEndLatencyNs']<0 or r['CompletedOffsetNs']!=r['ScheduledOffsetNs']+r['EndToEndLatencyNs'] for r in rows):raise ValueError('timing identity failed')
    fields=dict(pattern=cfg['traffic_pattern'],duration_sec=cfg['duration_sec'],target_rate=cfg['rate'],burst_low_rate=cfg['burst_low'],burst_high_rate=cfg['burst_high'],burst_period_sec=cfg['burst_period_sec'],burst_low_duration_sec=cfg['burst_low_duration_sec'],client_trace_enabled=True)
    if any(client.get(k)!=v for k,v in fields.items()):raise ValueError('client settings differ')
    return expected


def monitor_minimum(cfg):return 80 if cfg['duration_sec']==60 else 45


def owned_directory(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:raise ValueError('use a dedicated direct V29 generation directory')
    return p


def source_hashes():
    names=set(read(HISTORY/'bundle/manifest.json')['sources'])
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v29_*.py'))
    names.update(('diagnostic/test_v29.py','diagnostic/start_v29.sh','docs/runtime_io_v29_protocol.md','docs/runtime_io_v29_execution.md','diagnostic/v29_campaign.py'))
    return {n:digest(ROOT/n) for n in sorted(names)}
