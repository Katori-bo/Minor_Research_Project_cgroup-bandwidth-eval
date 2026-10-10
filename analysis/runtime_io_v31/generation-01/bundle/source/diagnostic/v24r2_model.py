"""Monotonic counter bounds and fixed-phase CPU accounting; no collector."""
import bisect
import math
import statistics
import v23_model as queue
from kernel_bridge_analysis import clock_join


def validate_samples(probe,expected_path):
    if (probe.get('schema')!=2 or probe.get('sampler_revision')!='v24r2-gc-suspended'
            or probe.get('gc_policy')!='suspended_during_bounded_capture'
            or type(probe.get('gc_was_enabled')) is not bool
            or probe.get('gc_enabled_during_capture') is not False
            or probe.get('gc_enabled_after_capture') is not probe['gc_was_enabled']
            or not isinstance(probe.get('gc_collections_before'),list)
            or len(probe['gc_collections_before'])!=3
            or any(type(v) is not int or v<0 for v in probe['gc_collections_before'])
            or not isinstance(probe.get('gc_collections_after'),list)
            or any(type(v) is not int or v<0 for v in probe['gc_collections_after'])
            or probe['gc_collections_after']!=probe['gc_collections_before']):
        raise ValueError('counter sampler GC policy/collection contract failed')
    if (probe['path']!=expected_path or probe['interval_sec']!=.02
            or probe['duration_bound_sec']!=110 or probe['affinity']!=[0,1]
            or probe['failure'] is not None or probe['own_cpu_ns']<0):
        raise ValueError('counter sampler identity/contract failed')
    samples=probe['samples']
    if len(samples)<2:raise ValueError('counter sampler coverage missing')
    for i,r in enumerate(samples):
        if (not probe['started_ns']<=r['before_ns']<=r['after_ns']<=probe['finished_ns']
                or r['after_ns']-r['before_ns']>2_000_000
                or not {'usage_usec','user_usec','system_usec'}<=set(r['cpu_stat'])
                or any(not isinstance(v,int) or v<0 for v in r['cpu_stat'].values())):
            raise ValueError('invalid counter-read bracket/counters')
        if i:
            previous=samples[i-1]
            if (previous['after_ns']>r['before_ns'] or set(previous['cpu_stat'])!=set(r['cpu_stat'])
                    or any(r['cpu_stat'][k]<v for k,v in previous['cpu_stat'].items())):
                raise ValueError('counter samples moved backwards')
    return samples


def counter_bounds(samples,lo,hi):
    """Monotonic values at an uncertain time, without interpolation."""
    if lo>hi:raise ValueError('empty boundary interval')
    before=[r for r in samples if r['after_ns']<=lo]
    after=[r for r in samples if r['before_ns']>=hi]
    if not before or not after:raise ValueError('boundary lacks enclosing counter reads')
    left,right=before[-1],after[0]
    if right['after_ns']-left['before_ns']>60_000_000:
        raise ValueError('counter boundary span exceeds60ms')
    return {k:[left['cpu_stat'][k],right['cpu_stat'][k]] for k in left['cpu_stat']}


def window_usage(samples,origins,windows):
    totals={};details=[]
    for a,b in windows:
        start=counter_bounds(samples,origins[0]+a*1e9,origins[1]+a*1e9)
        stop=counter_bounds(samples,origins[0]+b*1e9,origins[1]+b*1e9)
        delta={k:[max(0,stop[k][0]-start[k][1]),stop[k][1]-start[k][0]] for k in start}
        for k,(lo,hi) in delta.items():
            if hi<lo:raise ValueError('inconsistent counter bounds')
            old=totals.setdefault(k,[0,0]);old[0]+=lo;old[1]+=hi
        details.append(dict(window_sec=[a,b],cpu_delta_bounds=delta))
    return totals,details


def completion_bounds(ends,origins,windows):
    lower=upper=0
    for a,b in windows:
        lower+=max(0,bisect.bisect_left(ends,origins[0]+b*1e9)-bisect.bisect_left(ends,origins[1]+a*1e9))
        upper+=bisect.bisect_left(ends,origins[1]+b*1e9)-bisect.bisect_left(ends,origins[0]+a*1e9)
    return [lower,upper]


def phase(samples,jobs,q,host_origins,server_origins,windows,busy):
    counters,details=window_usage(samples,host_origins,windows)
    ends=sorted(j['completion_ns'] for j in jobs)
    counts=completion_bounds(ends,server_origins,windows)
    if counts[0]<=0:raise ValueError('no guaranteed phase completions')
    expanded=[(server_origins[0]+a*1e9,server_origins[1]+b*1e9) for a,b in windows]
    minima=[queue.min_window(q,a,b) for a,b in expanded]
    maxima=[max([queue.at(q,a)]+q[1][bisect.bisect_right(q[0],a):bisect.bisect_left(q[0],b)]) for a,b in expanded]
    valid=all(v>5 for v in minima) if busy else all(v<=5 for v in maxima)
    duration=sum(b-a for a,b in windows)
    usage=counters['usage_usec']
    wall=sorted(j['processing_ns']/1e6 for j in jobs if 'processing_ns' in j
                and any(server_origins[1]+a*1e9<=j['worker_start_ns']<server_origins[0]+b*1e9 for a,b in windows))
    wall_summary=dict(n=len(wall),mean=statistics.mean(wall) if wall else None,
        p50=statistics.median(wall) if wall else None,
        p99=wall[max(0,math.ceil(.99*len(wall))-1)] if wall else None,
        interpretation='Processing wall time of jobs certainly started in this phase; includes descheduling/throttling, not per-job CPU time.')
    return dict(windows_sec=windows,clock_bounded_completions=counts,
        cpu_delta_bounds=counters,counter_windows=details,queue_minima=minima,queue_maxima=maxima,
        state_eligible=valid,duration_sec=duration,
        worker_processing_wall_ms=wall_summary,
        cpu_usec_per_completion_bounds=[usage[0]/counts[1],usage[1]/counts[0]],
        delivered_cpu_fraction_bounds=[usage[0]/(duration*1e6),usage[1]/(duration*1e6)])


def trial(derived,server,anchors,probe,config,design,expected_path):
    mapping=derived['clocks'];origin=(mapping['client_test_start_ns']+mapping['server_minus_client_lower_ns'],
                                      mapping['client_test_start_ns']+mapping['server_minus_client_upper_ns'])
    jobs=server['events'];q=queue.series([j['admission_ns'] for j in jobs],[j['worker_start_ns'] for j in jobs])
    ends=sorted(j['completion_ns'] for j in jobs)
    windows=design['windows']['busy'];counts=completion_bounds(ends,origin,windows)
    midpoint=(origin[0]+origin[1])/2
    point=sum(bisect.bisect_left(ends,midpoint+b*1e9)-bisect.bisect_left(ends,midpoint+a*1e9) for a,b in windows)
    duration=sum(b-a for a,b in windows);busy_capacity=point/duration
    whole=derived['summary']['cpu_usec_per_completed_work']
    if whole is None or not math.isfinite(whole) or whole<=0:raise ValueError('invalid whole-cohort demand')
    result=dict(trial=config['trial'],size=config['size'],block=config['block'],counter_probe=config['counter_probe'],
        busy_capacity_rps=busy_capacity,busy_capacity_bounds_rps=[x/duration for x in counts],
        whole_cpu_usec_per_job=whole,miss_pct=100*(1-derived['summary']['timely_500_fraction']),
        implied_cpu_fraction_from_mixed_estimates=busy_capacity*whole/1e6)
    if probe is None:
        if config['counter_probe']:raise ValueError('probe-on trial lacks counters')
        return result
    if not config['counter_probe']:raise ValueError('probe-off trial has extra counter evidence')
    samples=validate_samples(probe,expected_path)
    joined=clock_join(anchors,mapping,server['clock_generation'])
    host_origins=(mapping['client_test_start_ns']+joined['kernel_minus_client_lower_ns'],
                  mapping['client_test_start_ns']+joined['kernel_minus_client_upper_ns'])
    relevant=[r for r in samples if r['after_ns']>=host_origins[0] and r['before_ns']<=host_origins[1]+60e9]
    if any(b['before_ns']-a['after_ns']>50_000_000 for a,b in zip(relevant,relevant[1:])):
        raise ValueError('measurement counter gap exceeds50ms')
    phases={label:phase(samples,jobs,q,host_origins,origin,design['windows'][label],label=='busy') for label in ('busy','low')}
    cost=phases['busy']['cpu_usec_per_completion_bounds'];low=phases['low']['cpu_usec_per_completion_bounds']
    result.update(phases=phases,whole_over_busy_cost_bounds=[whole/cost[1],whole/cost[0]] if cost[0]>0 else [whole/cost[1],None],
        low_over_busy_cost_bounds=[low[0]/cost[1],low[1]/cost[0]] if cost[0]>0 else [low[0]/cost[1],None],
        sampler_own_cpu_ms=probe['own_cpu_ns']/1e6)
    return result


def report(trials,design):
    ids=[r['trial'] for r in trials]
    if len(set(ids))!=len(ids):raise ValueError('duplicate accepted trial')
    expected={r['id'] for r in design['trial_order']}
    if not set(ids)<=expected:raise ValueError('unexpected trial')
    complete=set(ids)==expected;by_size={};pairs=[]
    for size in ('small','large'):
        selected=[r for r in trials if r['size']==size];on=[r for r in selected if r['counter_probe']]
        for block in range(1,4):
            a=next((r for r in selected if r['block']==block and not r['counter_probe']),None)
            b=next((r for r in selected if r['block']==block and r['counter_probe']),None)
            pair=dict(size=size,block=block,complete=a is not None and b is not None)
            if pair['complete']:
                rate=abs(b['busy_capacity_rps']-a['busy_capacity_rps'])/a['busy_capacity_rps'] if a['busy_capacity_rps']>0 else None
                cpu=abs(b['whole_cpu_usec_per_job']-a['whole_cpu_usec_per_job'])/a['whole_cpu_usec_per_job']
                miss=abs(b['miss_pct']-a['miss_pct'])
                pair.update(capacity_relative_difference=rate,cpu_job_relative_difference=cpu,miss_abs_difference_pp=miss,
                    observer_screen_pass=rate is not None and rate<=.02 and cpu<=.02 and miss<=1)
            pairs.append(pair)
        eligible=len(on)==3 and all(all(p['state_eligible'] for p in r['phases'].values()) for r in on)
        shift=eligible and all(r['whole_over_busy_cost_bounds'][0]>=1.05 and r['low_over_busy_cost_bounds'][0]>=1.05 for r in on)
        delivery=eligible and all(.48<=r['phases']['busy']['delivered_cpu_fraction_bounds'][0]
                                 and r['phases']['busy']['delivered_cpu_fraction_bounds'][1]<=.52 for r in on)
        by_size[size]=dict(complete=len(selected)==6,phase_state_eligible=eligible,
            phase_cost_shift_supported=shift,busy_delivery_near_nominal=delivery)
    observer=complete and all(p['observer_screen_pass'] for p in pairs)
    supported=observer and all(r['phase_cost_shift_supported'] and r['busy_delivery_near_nominal'] for r in by_size.values())
    diagnostics=[]
    for r in trials:
        if not r['counter_probe']:continue
        p=r['phases']
        eligible=all(v['state_eligible'] for v in p.values())
        shift=eligible and r['whole_over_busy_cost_bounds'][0]>=1.05
        diagnostics.append(dict(trial=r['trial'],state_eligible=eligible,
            verdict='whole_cohort_cost_not_transferable_to_busy_state' if observer and shift else 'not_established',
            lower_whole_over_busy_ratio=r['whole_over_busy_cost_bounds'][0],
            interpretation='A measurement-based check of state-invariant demand; no new queueing model or independent predictor.'))
    decision=('incomplete' if not complete else 'observer_effect_unresolved' if not observer else
              'phase_cost_explanation_supported' if supported else 'phase_cost_explanation_not_fully_demonstrated')
    return dict(decision=decision,complete=complete,observer_screen_pass=observer,explanation_supported=supported,
        by_size=by_size,pairs=pairs,trials=trials,diagnostics=diagnostics,novelty_established=False,
        limits='Same host/service/hash; aggregate CPU per phase completion, not per-job CPU or attribution to spinning/GC/HTTP. Observer screens are engineering checks, not equivalence tests. Matching CPU and throughput windows is accounting, not a new independent predictor.')
