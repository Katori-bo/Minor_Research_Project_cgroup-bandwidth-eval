"""Prospective V28 schedules and immutable scientific configuration."""
import math
from pathlib import Path
import v27r3_common as retained

ROOT = retained.ROOT
PARENT = ROOT/'analysis/runtime_io_v28'
DESIGN = ROOT/'analysis/runtime_io_v28_design/20261008'
ORIGINAL, CLIENT_BUILD = retained.ORIGINAL, retained.CLIENT_BUILD
HISTORY = ROOT/'analysis/runtime_io_v27/generation-03'
for _name in ('read','save','digest','seal','verify_seal','files','baseline','capacity',
              'resolve','process_identity','same_process','validate_resources','validate_state',
              'service_argv','require_desktop_absent','verify_client_build','technical_client'):
    globals()[_name] = getattr(retained, _name)


def design():
    value = read(DESIGN/'seal.json')
    for name, expected in value['files_sha256'].items():
        if digest(ROOT/name)!=expected:raise ValueError('frozen V28 design changed: '+name)
    return read(DESIGN/'design.json')


def config(slot):
    kind, rate = slot['kind'], slot['low_rate']
    period = slot.get('period_sec',15)
    low_duration = slot.get('low_duration_sec',10)
    high = slot.get('high_rate',169.8)
    duration = 60 if kind in ('mixed','validation') else 30
    pattern = 'idle' if kind=='idle' else ('steady' if kind=='steady' else 'bursty')
    return dict(retained.legacy.WORKLOAD,duration_sec=duration,warmup_sec=20,
        quota_us=50000,period_us=100000,worker_yield=False,trial=slot['id'],arm='M',
        block=slot['block'],order=slot['collection_order'],role=kind,repeat=slot['block'],
        size='small',iterations=44000,low_rate=rate,traffic_pattern=pattern,
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
    templates=[config(dict(id='functional_idle',kind='idle',low_rate=0,block=0,collection_order=0)),
               config(dict(id='functional_steady',kind='steady',low_rate=120,block=0,collection_order=0)),
               config(dict(id='functional_mixed',kind='mixed',low_rate=30,block=0,collection_order=0))]
    for p in (6,12):
        templates.append(config(dict(id='functional_period'+str(p),kind='validation',low_rate=15,
            block=0,collection_order=0,period_sec=p,low_duration_sec=2*p//3,high_rate=180)))
    result=[dict(x,functional=True,duration_sec=2 if x['traffic_pattern']!='bursty' else x['burst_period_sec'],warmup_sec=0) for x in templates]
    result.append(dict(result[1],trial='functional_cancel',timeout_sec=.001,rate=226.4,burst_low=226.4,burst_high=226.4))
    return result


def validate_config(cfg,functional=False):
    if cfg not in (functional_configs() if functional else matrix()):
        raise ValueError('configuration outside frozen V28 design')
    if cfg['counter_probe'] is not False:raise ValueError('V28 requires sampler off')


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
    # exact V28 vector through a local copy of those checks, with no monkeypatch.
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
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:raise ValueError('use a dedicated direct V28 generation directory')
    return p


def source_hashes():
    names=set(read(HISTORY/'bundle/manifest.json')['sources'])
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v28_*.py'))
    names.update(('diagnostic/test_v28.py','diagnostic/start_v28.sh','docs/runtime_io_v28_protocol.md','docs/runtime_io_v28_execution.md'))
    return {n:digest(ROOT/n) for n in sorted(names)}
