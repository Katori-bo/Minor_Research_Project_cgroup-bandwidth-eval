"""V30 fresh deadline confirmation; retained binaries, separate evidence namespace."""
from fractions import Fraction
from pathlib import Path
import v29_common as retained

ROOT=retained.ROOT
ACTIVE='q025_large'
CONTEXTS=retained.CONTEXTS
CONTEXT=CONTEXTS[ACTIVE]
PARENT=ROOT/'analysis/runtime_io_v30'
DESIGN=ROOT/'analysis/runtime_io_v30_design/20261009'
HISTORY=retained.HISTORY
CLIENT_BUILD=retained.CLIENT_BUILD
ORIGINAL=retained.ORIGINAL
DEADLINES_MS=(10,20,25,35,50,75,100,150,500)
for name in ('read','save','digest','seal','verify_seal','files','baseline','capacity',
             'resolve','process_identity','same_process','validate_resources','validate_state',
             'service_argv','require_desktop_absent','verify_client_build','technical_client'):
    globals()[name]=getattr(retained,name)


def design():
    verify_seal(DESIGN)
    directory=ROOT/'analysis/runtime_io_v29_design/20261009/q025_large'
    for name,expected in read(directory/'seal.json')['files_sha256'].items():
        if digest(ROOT/name)!=expected:raise ValueError('frozen scientific input changed: '+name)
    fresh=read(DESIGN/'design.json')
    prior=read(ROOT/'analysis/runtime_io_v29_design/20261009/q025_large/design.json')
    configs=fresh['calibration_configs']+fresh['validation_configs']
    return dict(prior,**fresh,trial_order=[dict(id=x['trial'],kind=x['role']) for x in configs],
                measurement_bound_sec=fresh['lifetime_sec']['measurement'],
                runtime_preparation_bound_sec=fresh['lifetime_sec']['preparation'],
                analysis_bound_sec=fresh['lifetime_sec']['analysis'])


def matrix():
    d=design();return d['calibration_configs']+d['validation_configs']
def calibration_configs():return design()['calibration_configs']
def validation_configs():return design()['validation_configs']
warmup_config=retained.warmup_config
monitor_minimum=retained.monitor_minimum


def functional_configs():
    cal=calibration_configs();val=validation_configs()
    selected=[next(x for x in cal if x['role']=='idle'),
              next(x for x in cal if x['role']=='steady' and x['reference_low_rate']==120),
              next(x for x in cal if x['role']=='mixed' and x['reference_low_rate']==30),
              next(x for x in val if x['profile']=='A'),next(x for x in val if x['profile']=='C')]
    result=[dict(x,trial='functional_'+str(i),functional=True,
                 duration_sec=x['burst_period_sec'] if x['traffic_pattern']=='bursty' else 2,
                 warmup_sec=0) for i,x in enumerate(selected)]
    result.append(dict(result[1],trial='functional_cancel',timeout_sec=.001,duration_sec=2,
                       traffic_pattern='steady',rate=56.6,burst_low=56.6,burst_high=56.6))
    return result


def validate_config(cfg,functional=False):
    if cfg not in (functional_configs() if functional else matrix()):
        raise ValueError('configuration outside frozen V30 design')
    if cfg['counter_probe'] is not False:raise ValueError('V30 requires sampler off')


def generated_schedule(cfg):
    # Rational oracle independently reproduces the compiled Go client's rounding.
    if cfg['traffic_pattern']=='idle':return []
    duration=Fraction(str(cfg['duration_sec']));out=[];i=0
    while True:
        if cfg['traffic_pattern']=='steady':sec=Fraction(i)/Fraction(str(cfg['rate']))
        else:
            a=Fraction(str(cfg['burst_low_duration_sec']));p=Fraction(str(cfg['burst_period_sec']))
            low=Fraction(str(cfg['burst_low']));high=Fraction(str(cfg['burst_high']))
            count=a*low+(p-a)*high;cycle=int(Fraction(i)//count);within=Fraction(i)-cycle*count
            sec=cycle*p+(within/low if within<a*low else a+(within-a*low)/high)
        stamp=sec*10**9;rounded=(2*stamp.numerator+stamp.denominator)//(2*stamp.denominator)
        if rounded>=duration*10**9:return out
        out.append(rounded);i+=1


def schedule(cfg):
    vector=generated_schedule(cfg)
    if not cfg.get('functional'):
        suffix='_warmup' if cfg['duration_sec']==20 else '_measurement'
        if cfg['role']=='validation':path=DESIGN/'schedules'/(cfg['trial']+suffix+'.json')
        else:path=ROOT/'analysis/runtime_io_v29_design/20261009/q025_large/schedules'/(cfg['trial']+suffix+'_offsets_ns.json')
        if vector!=read(path):raise ValueError('frozen offered schedule differs from rational oracle')
    return vector


def validate_client(client,cfg):
    # Local retained checks resolve this module's exact V30 schedule.
    expected=schedule(cfg);offered=client['total_scheduled'];rows=client['requests']
    if offered!=len(expected):raise ValueError('offered cohort differs')
    ids=[r['ID'] for r in rows]
    if len(set(ids))!=len(ids) or any(type(i) is not int or not 0<=i<offered for i in ids):raise ValueError('client IDs differ')
    if any(r['ScheduledOffsetNs']!=expected[r['ID']] for r in rows):raise ValueError('exact offsets differ')
    if type(client['client_dropped']) is not int or client['client_dropped']<0 or offered-len(rows)!=client['client_dropped']:raise ValueError('dropped conservation failed')
    good=sum(not r['Error'] and r['StatusCode']==200 for r in rows)
    rejected=sum(not r['Error'] and r['StatusCode']==503 for r in rows)
    counts=dict(total_completed=len(rows),total_dispatched=len(rows),total_success=good,total_503=rejected,total_errors=len(rows)-good-rejected)
    if any(client[k]!=v for k,v in counts.items()):raise ValueError('outcome conservation failed')
    if not 0<=client['missed_arrivals']<=offered:raise ValueError('invalid missed arrivals')
    if any(r['EndToEndLatencyNs']<0 or r['CompletedOffsetNs']!=r['ScheduledOffsetNs']+r['EndToEndLatencyNs'] for r in rows):raise ValueError('timing identity failed')
    fields=dict(pattern=cfg['traffic_pattern'],duration_sec=cfg['duration_sec'],target_rate=cfg['rate'],burst_low_rate=cfg['burst_low'],burst_high_rate=cfg['burst_high'],burst_period_sec=cfg['burst_period_sec'],burst_low_duration_sec=cfg['burst_low_duration_sec'],client_trace_enabled=True)
    if any(client.get(k)!=v for k,v in fields.items()):raise ValueError('client settings differ')
    return expected


def owned_directory(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.name!='generation-01' or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use fresh V30 generation-01; preserve all previous evidence')
    return p


def source_hashes():
    names=set(retained.source_hashes())
    names.update(str(p.relative_to(ROOT)) for p in (ROOT/'diagnostic').glob('v30_*.py'))
    names.update(('diagnostic/test_v30.py','diagnostic/start_v30.sh','analysis/periodic_budget_model.py',
                  'analysis/test_periodic_budget_model.py','docs/runtime_io_v30_execution.md'))
    return {name:digest(ROOT/name) for name in sorted(names)}
