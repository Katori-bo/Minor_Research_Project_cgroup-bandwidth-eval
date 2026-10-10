"""Offline all-offered accounting and descriptive six-pair practical screen."""
import json
import math
import statistics

import kernel_observer_common as c
import kernel_observer_coverage as coverage
import parallelism_analysis
import repeatability_analysis

METRICS = ('timely_500_delta', 'timely_1000_delta', 'failure_delta', 'cpu_ratio', 'p99_ratio')
MARGINS = dict(timely_500_delta=.01, timely_1000_delta=.01, failure_delta=.001, cpu_ratio=.05, p99_ratio=.10)
LIMITATION = ('Six pairs do not establish statistical equivalence. Effects within practical margins require '
              'review. No kernel/request causal attribution or runtime intervention follows automatically. '
              'Publication and runnable readiness remain unobserved.')


def indexed(rows):
    result = {r['id']: r for r in rows}
    if len(result) != len(rows): raise ValueError('duplicate service record')
    return result


def classify(client, server, anchors):
    c.arrival_vector(client)
    repeatability_analysis.validate_state(server, 'legacy_a')
    if server['active_handlers'] or server['queue_len'] or server['completed'] != server['admitted']:
        raise ValueError('service not fully drained')
    mapping = parallelism_analysis.clock_mapping(client, server)
    joined = coverage.clock_join(anchors, mapping, server['clock_generation'])
    jobs = indexed(server['events']); handlers = indexed(server['handler_events']); entries = indexed(server['entry_events'])
    offered = client['total_scheduled']; ids = set(range(offered))
    if any(not set(records) <= ids for records in (jobs, handlers, entries)):
        raise ValueError('unexpected request ID in service records')
    if len(jobs) != server['completed']: raise ValueError('completed computation record count mismatch')
    rows = []
    for q in sorted(client['requests'], key=lambda q:q['ID']):
        rid=q['ID']; job=jobs.get(rid); handler=handlers.get(rid); entry=entries.get(rid)
        success=not q['Error'] and q['StatusCode']==200
        row=dict(id=rid, outcome='success' if success else 'timeout' if q['TimedOut'] else
                 'rejected' if not q['Error'] and q['StatusCode']==503 else 'error',
                 timely_500=success and q['EndToEndLatencyNs']<=500_000_000,
                 timely_1000=success and q['EndToEndLatencyNs']<=1_000_000_000,
                 success=success, e2e_ns=q['EndToEndLatencyNs'], scheduled_offset_ns=q['ScheduledOffsetNs'],
                 entry_observed=entry is not None, worker_observed=job is not None, handler_observed=handler is not None,
                 drained_response=q['CompletedOffsetNs']>60_000_000_000,
                 publication='unobserved', runnable_readiness='unobserved', kernel_request_attribution=False)
        origin=mapping['client_test_start_ns']+q['ScheduledOffsetNs']
        row.update(scheduled_kernel_lower_ns=origin+joined['kernel_minus_client_lower_ns'],
                   scheduled_kernel_upper_ns=origin+joined['kernel_minus_client_upper_ns'])
        stamps = [('entry', entry, 'entry_ns'), ('admission', job, 'admission_ns'),
                  ('worker_start', job, 'worker_start_ns'), ('completion', job, 'completion_ns'),
                  ('resume', handler, 'resume_ns'), ('handler_exit', handler, 'handler_exit_ns')]
        for label, record, key in stamps:
            stamp=None if record is None else record[key]
            row[label+'_kernel_lower_ns']=None if stamp is None else stamp+joined['kernel_minus_server_lower_ns']
            row[label+'_kernel_upper_ns']=None if stamp is None else stamp+joined['kernel_minus_server_upper_ns']
        horizon=mapping['client_test_start_ns']+60_000_000_000
        row['computation_after_arrivals_certain']=job is not None and job['completion_ns']-mapping['server_minus_client_upper_ns']>horizon
        row['computation_after_arrivals_possible']=job is not None and job['completion_ns']-mapping['server_minus_client_lower_ns']>horizon
        row['completion_to_handler_ns']=None if job is None or handler is None else handler['resume_ns']-job['completion_ns']
        if row['completion_to_handler_ns'] is not None and row['completion_to_handler_ns'] < 0:
            raise ValueError('handler precedes computation')
        rows.append(row)
    return rows, joined


def summary(config, client, server, rows, observations):
    n=len(rows); good=sorted(r['e2e_ns'] for r in rows if r['success'])
    start=observations['measurement_start']; stop=observations['measurement_stop']
    delta={k:stop['cpu_stat'][k]-start['cpu_stat'].get(k,0) for k in stop['cpu_stat']}
    if any(v<0 for v in delta.values()): raise ValueError('cgroup counters went backwards')
    completed=server['completed']
    return dict(trial=config['trial'], pair=config['pair'], arm=config['arm'], order=config['order'],
                offered=n, completed_computations=completed,
                timely_500_fraction=sum(r['timely_500'] for r in rows)/n,
                timely_1000_fraction=sum(r['timely_1000'] for r in rows)/n,
                failure_fraction=sum(not r['success'] for r in rows)/n,
                cpu_usec_per_completed_work=delta['usage_usec']/completed if completed else None,
                p99_e2e_ms=good[max(0, math.ceil(.99*len(good))-1)]/1e6 if good else None,
                counter_window=dict(before_ns=start['before_ns'], after_ns=stop['after_ns'], delta=delta),
                missing_worker_count=sum(not r['worker_observed'] for r in rows),
                missing_handler_count=sum(not r['handler_observed'] for r in rows), valid_evidence=True)


def capture_result(directory, arm, observations, snapshots):
    metadata=c.read(directory/'initial.json')
    for ns in metadata['time_namespaces'].values():
        if ns != {'monotonic':[0,0], 'boottime':[0,0]}: raise ValueError('nonzero time namespace')
    if arm=='off':
        if (directory/'events.txt').exists() or (directory/'observer.stderr').exists():
            raise ValueError('off arm contains observer output')
        return dict(kernel_events='unobserved', quota_intervals=None, throttle_attempts=None)
    if (directory/'events.txt').stat().st_size+(directory/'observer.stderr').stat().st_size > c.RAW_LIMIT:
        raise ValueError('raw observer output exceeds 1 GiB')
    stderr=(directory/'observer.stderr').read_text()
    if stderr.strip(): raise ValueError('observer diagnostics present')
    raw=(directory/'events.txt').read_text()
    rows, begin, end=coverage.primitive.records(raw, stderr)
    if not 0 < end-begin <= (c.CAPTURE_SEC+1)*1e9: raise ValueError('capture ceiling violated')
    for row in rows:
        # Wakeups can originate on IRQ/network CPUs outside the service cpuset;
        # the verified bridge semantics constrain their target CPU and TID.
        cpu=row[4] if row[0]=='W' else row[3] if row[0] in ('T','U') else row[2]
        if cpu not in (2,4): raise ValueError('event on unexpected CPU')
        if row[0] in ('T','U') and not begin <= row[1] <= row[2] <= end:
            raise ValueError('quota bracket outside capture')
    result=coverage.coverage(raw, stderr, metadata, snapshots)
    counters=[]
    for label, bounds in observations.items():
        if not begin < bounds['before_ns'] <= bounds['after_ns'] < end:
            raise ValueError('counter observation outside capture')
        counters.append(dict(label=label, **bounds))
    result.update(counter_observation_windows=counters,
                  counter_comparison='nr_throttled counts bandwidth periods; event transitions are per CPU. '
                  'Startup-to-exit event counts and bracketed counter windows have different coverage.',
                  whole_service_pause='unobserved')
    comparisons=[]
    for start_label,stop_label in (('startup','final'),('measurement_start','measurement_stop')):
        start,stop=observations[start_label],observations[stop_label]
        certain=[r for r in rows if r[0]=='T' and start['after_ns']<=r[1]<=r[2]<=stop['before_ns']]
        possible=[r for r in rows if r[0]=='T' and r[2]>=start['before_ns'] and r[1]<=stop['after_ns']]
        nr=stop['cpu_stat'].get('nr_throttled',0)-start['cpu_stat'].get('nr_throttled',0)
        successful=sum(r[6:]==[1,1] for r in certain)
        comparisons.append(dict(start_label=start_label,stop_label=stop_label,
            window_lower_ns=start['before_ns'],window_upper_ns=stop['after_ns'],counter_nr_throttled=nr,
            certain_throttle_attempts=len(certain),possible_throttle_attempts=len(possible),
            certain_successful_per_cpu_transitions=successful,
            per_cpu_transition_minus_bandwidth_period_count=successful-nr,
            interpretation='Descriptive discrepancy for bracketed windows; counter periods and per-CPU transitions differ.'))
    result['counter_event_comparisons']=comparisons
    result['wakeup_origin_cpus']=sorted({r[2] for r in rows if r[0]=='W'})
    return result


def replay(directory):
    c.verify_seal(directory)
    config=c.read(directory/'config.json'); cleanup=c.read(directory/'cleanup.json')
    if any(config.get(k)!=v for k,v in c.WORKLOAD.items()) or config['arm'] not in ('off','on'):
        raise ValueError('trial configuration differs from frozen workload')
    if config['pair'] and config not in c.matrix(): raise ValueError('trial outside frozen matrix')
    if cleanup['errors'] or not all(cleanup[k] for k in ('detached','container_removed','cgroup_removed','root_controls_unchanged')):
        raise ValueError('cleanup incomplete')
    initial=c.read(directory/'initial.json')
    expected={'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2,4','memory.max':'max','pids.max':'max'}
    if initial['initial_limits'] != expected: raise ValueError('historical resource settings differ')
    identity=c.read(directory/'identity.json')
    container=c.read(directory/'container.json')['inspect']
    hc=container['HostConfig']
    if container['Image']!=identity['image'] or hc['CpuPeriod']!=100000 or hc['CpuQuota']!=50000 or hc['CpusetCpus']!='2,4':
        raise ValueError('container inspection differs from protocol')
    if hc['Memory']!=0 or hc['MemorySwap']!=0 or hc.get('PidsLimit') not in (None,0): raise ValueError('extra container limits')
    if len(container['Mounts'])!=1 or container['Mounts'][0]['Destination']!='/qualification': raise ValueError('qualification mount differs')
    if identity['server_sha256'] != identity['expected_server_sha256'] or identity['image'] != identity['expected_image']:
        raise ValueError('image/executable identity differs')
    if identity['loadgen_sha256'] != identity['expected_loadgen_sha256']:
        raise ValueError('client identity differs')
    if identity['health']['gomaxprocs']!=1 or identity['health']['workers']!=4 or identity['health']['queue_cap']!=128:
        raise ValueError('service workload differs')
    repeatability_analysis.validate_state(identity['health'],'legacy_a')
    if identity['health']['go_version']!='go1.26.1' or not identity['health']['instrument']:
        raise ValueError('original runtime/instrumentation differs')
    client=c.read(directory/'loadgen.json'); server=c.read(directory/'server_metrics.json')
    c.arrival_vector(c.read(directory/'warmup.json'), 20)
    observations=c.read(directory/'observations.json'); anchors=c.read(directory/'kernel_server_anchors.json')
    requests, clocks=classify(client, server, anchors)
    capture=capture_result(directory, config['arm'], observations, c.read(directory/'thread_snapshots.json'))
    if config['arm']=='on':
        begin,end=capture['capture_begin_ns'],capture['capture_end_ns']
        if not all(begin<s['before_ns']<=s['after_ns']<end for s in anchors):
            raise ValueError('clock anchors outside capture')
        for r in requests:
            for key in ('entry','admission','worker_start','completion','resume','handler_exit'):
                lo,hi=r[key+'_kernel_lower_ns'],r[key+'_kernel_upper_ns']
                if lo is not None and not begin<=lo<=hi<=end: raise ValueError('request boundary outside capture')
    monitor=c.read(directory/'monitor.json'); environment=c.read(directory/'environment.json')
    from environment_controls import comparable_power
    if len(monitor)<80 or any(m['chatgpt_present'] or m['power_settings']!=comparable_power(environment['power_settings']) for m in monitor):
        raise ValueError('host monitor coverage/quiet/power failure')
    if not c.read(directory/'settling.json')['accepted']: raise ValueError('thermal settling not accepted')
    return json.loads(json.dumps(dict(summary=summary(config,client,server,requests,observations),
                                     requests=requests, clocks=clocks, capture=capture),allow_nan=False))


def compare(rows):
    cells={(r['pair'],r['arm']):r for r in rows}
    if len(cells)!=len(rows): raise ValueError('duplicate trial cell')
    pairs=[]
    for p in range(1,7):
        a,z=cells.get((p,'off')),cells.get((p,'on'))
        effects=dict(pair=p, complete=a is not None and z is not None)
        if effects['complete']:
            for key in ('timely_500','timely_1000','failure'):
                effects[key+'_delta']=z[key+'_fraction']-a[key+'_fraction']
            for label,key in (('cpu','cpu_usec_per_completed_work'),('p99','p99_e2e_ms')):
                x,y=a[key],z[key]
                effects[label+'_ratio']=y/x if x is not None and y is not None and math.isfinite(x) and math.isfinite(y) and x>0 and y>0 else None
            effects['finite']=all(effects[k] is not None and math.isfinite(effects[k]) for k in METRICS)
            effects['within_screen']=effects['finite'] and all(abs(effects[k]-(1 if k.endswith('ratio') else 0)) <= MARGINS[k]+1e-12 for k in METRICS)
        else: effects.update(finite=False,within_screen=False)
        pairs.append(effects)
    statistics_by_metric={}
    for key in METRICS:
        vals=[p[key] for p in pairs if p['finite']]
        statistics_by_metric[key]=dict(n=len(vals), median=statistics.median(vals), minimum=min(vals), maximum=max(vals),
                                      sample_sd=statistics.stdev(vals) if len(vals)>1 else None) if vals else None
    incomplete=not all(p['complete'] and p['finite'] for p in pairs)
    decision='incomplete_evidence' if incomplete else 'effects_outside_margins' if not all(p['within_screen'] for p in pairs) else 'within_margins_requires_review'
    return dict(decision=decision,pairs=pairs,paired_statistics=statistics_by_metric,margins=MARGINS,
                observer_cost_qualified=False, service_request_attribution=False, limitation=LIMITATION)
