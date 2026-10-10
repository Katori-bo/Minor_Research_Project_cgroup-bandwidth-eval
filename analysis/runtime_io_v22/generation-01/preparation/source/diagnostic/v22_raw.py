"""V22 retained stock-service request/asset replay; no collector or fitted decisions."""
import bisect
import collections
import json
import math
import statistics as st

import v22_common as c
import parallelism_analysis
import kernel_bridge_analysis
from urllib.parse import urlparse, parse_qs
from environment_controls import comparable_power

MARGINS = dict(timely_500_delta=.01, timely_1000_delta=.01,
               failure_delta=.001, cpu_ratio=.05, p99_ratio=.10)
GAP_REDUCTION_TARGET = .25
T95_DF3 = 3.182446305284263
LIMITATION = ('Four independent blocks are an exploratory factorial probe, not confirmation or equivalence. '
              'Next-job starts bound prior publication only because there is exactly one worker. '
              'Exact publication, handler runnable readiness and CPU availability remain unobserved. '
              'Neither factor identifies an exclusive cause or proves a scheduler defect. '
              'No A/A arm or kernel observation is included; V19 repeatability does not qualify V20.')


def index(rows):
    result = {r['id']: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('duplicate service record')
    return result


def percentile(values, q):
    v = sorted(values)
    return v[max(0, math.ceil(len(v)*q)-1)] if v else None


def distribution(values):
    v = [x for x in values if x is not None]
    return dict(n=len(v), mean=st.mean(v) if v else None,
                p50=percentile(v, .5), p90=percentile(v, .9),
                p99=percentile(v, .99), maximum=max(v) if v else None)


def backlog(intervals):
    changes = collections.Counter()
    for a, b in intervals:
        if a > b:
            raise ValueError('reversed backlog interval')
        changes[a] += 1
        changes[b] -= 1
    count = peak = area = 0
    last = None
    for t, change in sorted(changes.items()):
        if last is not None:
            area += (t-last)*count
        count += change
        if count < 0:
            raise ValueError('negative logical backlog')
        peak = max(peak, count)
        last = t
    if count or area != sum(b-a for a, b in intervals):
        raise ValueError('logical backlog conservation failed')
    return dict(peak=peak, request_seconds=area/1e9)


def validate_service(server, config):
    c.validate_state(server, config, drained=True)


def join(client, server, config):
    vector = c.validate_client(client, config)
    validate_service(server, config)
    mapping = parallelism_analysis.clock_mapping(client, server)
    jobs, handlers, entries = (index(server[key]) for key in ('events', 'handler_events', 'entry_events'))
    ids = set(range(len(vector)))
    if any(not set(record) <= ids for record in (jobs, handlers, entries)):
        raise ValueError('unexpected service request ID')
    admitted = {rid for rid, e in entries.items() if e['admitted']}
    if (set(jobs) != admitted or len(jobs) != server['completed']
            or len(entries)-len(admitted) != server['rejected'] or not set(handlers) <= admitted):
        raise ValueError('service admission/computation/outcome conservation failed')
    for rid, entry in entries.items():
        if type(entry['admitted']) is not bool or not 0 <= entry['entry_ns'] <= entry['exit_ns']:
            raise ValueError('invalid entry interval')
    for rid, job in jobs.items():
        if not entries[rid]['entry_ns'] <= job['admission_ns'] <= job['worker_start_ns'] <= job['completion_ns']:
            raise ValueError('worker timestamps out of order')
        if (job['queue_wait_ns'] != job['worker_start_ns']-job['admission_ns']
                or job['processing_ns'] != job['completion_ns']-job['worker_start_ns']):
            raise ValueError('worker timing identity failed')
    for rid, h in handlers.items():
        j = jobs[rid]
        if (h['entry_ns'] != entries[rid]['entry_ns'] or h['admission_ns'] != j['admission_ns']
                or not h['write_end_ns'] <= entries[rid]['exit_ns'] <= h['handler_exit_ns']
                or not j['completion_ns'] <= h['resume_ns'] <= h['write_start_ns'] <= h['write_end_ns'] <= h['handler_exit_ns']
                or h['post_work_wait_ns'] != h['resume_ns']-j['completion_ns']
                or h['pre_admission_ns'] != j['admission_ns']-h['entry_ns']):
            raise ValueError('handler timing identity/order failed')
    starts = sorted(j['worker_start_ns'] for j in jobs.values())
    finishes = sorted(j['completion_ns'] for j in jobs.values())
    clients = {q['ID']: q for q in client['requests']}
    lo, hi = (mapping['server_minus_client_'+b+'_ns'] for b in ('lower', 'upper'))
    rows = []
    for rid, scheduled in enumerate(vector):
        q, j, h, e = clients.get(rid), jobs.get(rid), handlers.get(rid), entries.get(rid)
        if q is None and e is not None:
            raise ValueError('client-dropped offer has server observations')
        success = q is not None and not q['Error'] and q['StatusCode'] == 200
        outcome = ('client_dropped' if q is None else 'success' if success else
                   'rejected' if not q['Error'] and q['StatusCode'] == 503 else
                   'timeout' if q['TimedOut'] else 'error')
        if success and (e is None or j is None or h is None):
            raise ValueError('successful response lacks required server observations')
        if outcome == 'rejected' and (e is None or e['admitted'] or j is not None or h is not None):
            raise ValueError('rejection conflicts with service records')
        elapsed = q['EndToEndLatencyNs'] if q else None
        origin = mapping['client_test_start_ns']+scheduled
        bounds = lambda stamp: (None, None) if stamp is None else (stamp-hi-origin, stamp-lo-origin)
        entry_lo, entry_hi = bounds(None if e is None else e['entry_ns'])
        comp_lo, comp_hi = bounds(None if j is None else j['completion_ns'])
        resume_lo, resume_hi = bounds(None if h is None else h['resume_ns'])
        if success:
            if entry_hi < q['DispatchLagNs'] or entry_lo > q['DispatchLagNs']+q['HeadersOffsetNs']:
                raise ValueError('clock bounds contradict HTTP entry observation')
            if resume_lo > elapsed:
                raise ValueError('handler certainly resumed after successful client completion')
        gap = None if j is None or h is None else h['resume_ns']-j['completion_ns']
        if not success:
            category = 'unsuccessful'
        elif elapsed <= 500_000_000:
            category = 'timely'
        elif comp_lo > 500_000_000:
            category = 'computation_after_deadline'
        elif comp_hi > 500_000_000:
            category = 'computation_boundary_ambiguous'
        elif resume_lo > 500_000_000:
            category = 'computed_before_handler_resumed_after'
        elif resume_hi > 500_000_000:
            category = 'handler_boundary_ambiguous'
        else:
            category = 'handler_resumed_before_client_finished_after'
        count_inside = lambda v: None if gap is None else bisect.bisect_left(v, h['resume_ns'])-bisect.bisect_right(v, j['completion_ns'])
        row = dict(id=rid, scheduled_offset_ns=scheduled,
            schedule_observation='frozen inferred offset; no dispatch record' if q is None else 'observed',
            outcome=outcome, success=success, timely_500=success and elapsed <= 500_000_000,
            timely_1000=success and elapsed <= 1_000_000_000, e2e_ns=elapsed,
            dispatch_lag_ns=None if q is None else q['DispatchLagNs'],
            entry_observed=e is not None, worker_observed=j is not None, handler_observed=h is not None,
            admitted=None if e is None else e['admitted'],
            drained_response=q is not None and q['CompletedOffsetNs'] > config['duration_sec']*1e9,
            computation_after_arrivals_certain=j is not None and comp_lo+scheduled > config['duration_sec']*1e9,
            computation_after_arrivals_possible=j is not None and comp_hi+scheduled > config['duration_sec']*1e9,
            deadline_class=category, phase=('steady' if config['traffic_pattern'] == 'steady' else 'low' if scheduled % 10_000_000_000 < 5_000_000_000 else 'high'),
            burst_second=scheduled//1_000_000_000 % 10, cycle=scheduled//10_000_000_000,
            scheduled_to_entry_lower_ns=entry_lo, scheduled_to_entry_upper_ns=entry_hi,
            pre_admission_ns=None if j is None else j['admission_ns']-e['entry_ns'],
            queue_ns=None if j is None else j['queue_wait_ns'],
            processing_wall_ns=None if j is None else j['processing_ns'],
            completion_to_resume_ns=gap,
            completion_after_offered_lower_ns=comp_lo, completion_after_offered_upper_ns=comp_hi,
            resume_after_offered_lower_ns=resume_lo, resume_after_offered_upper_ns=resume_hi,
            resume_to_client_lower_ns=None if h is None or q is None else elapsed-resume_hi,
            resume_to_client_upper_ns=None if h is None or q is None else elapsed-resume_lo,
            completion_margin_certain_ns=None if comp_hi is None else 500_000_000-comp_hi,
            work_starts_inside_gap=count_inside(starts), work_completions_inside_gap=count_inside(finishes),
            publication='unobserved', runnable_readiness='unobserved')
        if success:
            for bound, other in (('lower', 'upper'), ('upper', 'lower')):
                budget = (row['scheduled_to_entry_'+bound+'_ns']+row['pre_admission_ns']+
                          row['queue_ns']+row['processing_wall_ns']+gap+row['resume_to_client_'+other+'_ns'])
                if budget != elapsed:
                    raise ValueError('per-request stage budget identity failed')
        rows.append(row)
    logical = dict(admitted_not_started=backlog([(j['admission_ns'], j['worker_start_ns']) for j in jobs.values()]),
                   computed_not_resumed=backlog([(jobs[rid]['completion_ns'], h['resume_ns']) for rid, h in handlers.items()]),
                   computed_missing_handler_count=len(jobs)-len(handlers))
    attach_publication_bounds(rows, jobs, handlers, config)
    return rows, mapping, logical


def attach_publication_bounds(rows, jobs, handlers, config):
    if config['workers'] != 1:
        raise ValueError('publication bound requires exactly one worker')
    ordered = sorted(jobs.values(), key=lambda j: j['worker_start_ns'])
    if any(a['completion_ns'] > b['worker_start_ns'] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('overlapping single-worker computations')
    following = {a['id']: b for a, b in zip(ordered, ordered[1:])}
    for row in rows:
        rid = row['id']
        nxt, job, handler = following.get(rid), jobs.get(rid), handlers.get(rid)
        bound = None if nxt is None else nxt['worker_start_ns']
        lower = upper = wait = None
        if bound is not None:
            delta = bound-job['completion_ns']
            lower = row['completion_after_offered_lower_ns']+delta
            upper = row['completion_after_offered_upper_ns']+delta
            if handler is not None and handler['resume_ns'] > bound:
                wait = handler['resume_ns']-bound
        status = ('no_worker_record' if job is None else 'no_next_job' if nxt is None else
                  'handler_unobserved' if handler is None else 'informative' if wait is not None else
                  'handler_resumed_before_or_at_bound')
        row.update(publication_bound_status=status,
            publication_upper_bound_server_ns=bound,
            next_worker_job_id=None if nxt is None else nxt['id'],
            publication_upper_bound_after_offered_lower_ns=lower,
            publication_upper_bound_after_offered_upper_ns=upper,
            publication_before500_certain=None if upper is None else upper <= 500_000_000,
            post_publication_wait_lower_bound_ns=wait,
            available_result_deadline_crossing=row['deadline_class']=='computed_before_handler_resumed_after'
                and upper is not None and upper <= 500_000_000,
            publication='unobserved' if bound is None else 'bounded by sole-worker next-job program order; exact timestamp unobserved')


def summarize(config, client, server, rows, mapping, logical, observations):
    start, stop = (observations[k] for k in ('measurement_start', 'measurement_stop'))
    if not start['before_ns'] <= start['after_ns'] < stop['before_ns'] <= stop['after_ns']:
        raise ValueError('CPU observation windows out of order')
    delta = {k: stop['cpu_stat'][k]-start['cpu_stat'].get(k, 0) for k in stop['cpu_stat']}
    if any(v < 0 for v in delta.values()):
        raise ValueError('CPU counters went backwards')
    n = len(rows)
    good = [r['e2e_ns'] for r in rows if r['success']]
    completed = server['completed']
    crossing = [r for r in rows if r['deadline_class'] == 'computed_before_handler_resumed_after']
    result = dict(trial=config['trial'], block=config['block'], arm=config['arm'], order=config['order'],
        workers=config['workers'], worker_yield=config['worker_yield'],
        quota_us=config['quota_us'], period_us=config['period_us'], offered=n, completed_computations=completed,
        timely_500_fraction=sum(r['timely_500'] for r in rows)/n,
        timely_1000_fraction=sum(r['timely_1000'] for r in rows)/n,
        failure_fraction=sum(not r['success'] for r in rows)/n,
        cpu_usec_per_completed_work=delta['usage_usec']/completed if completed else None,
        p99_e2e_ms=percentile(good, .99)/1e6 if good else None,
        cohort_successes=len(good), successes_during_arrivals=sum(r['success'] and not r['drained_response'] for r in rows),
        successful_rps_arrival_window=sum(r['success'] and not r['drained_response'] for r in rows)/config['duration_sec'],
        successful_rps_including_drain=len(good)/client['elapsed_including_drain_sec'],
        counter_window=dict(before_ns=start['before_ns'], after_ns=stop['after_ns'], delta=delta),
        missing_worker_count=sum(not r['worker_observed'] for r in rows),
        missing_handler_count=sum(not r['handler_observed'] for r in rows),
        gap_observed_count=sum(r['completion_to_resume_ns'] is not None for r in rows),
        gap_gt50ms_fraction=sum(r['completion_to_resume_ns'] is not None and r['completion_to_resume_ns'] > 50_000_000 for r in rows)/n,
        crossover_fraction=len(crossing)/n, crossover_count=len(crossing),
        crossovers_with50ms_margin=sum(r['completion_margin_certain_ns'] >= 50_000_000 for r in crossing),
        crossovers_with_other_work=sum(r['work_starts_inside_gap'] > 0 for r in crossing),
        deadline_classes=dict(collections.Counter(r['deadline_class'] for r in rows)),
        outcome_counts=dict(collections.Counter(r['outcome'] for r in rows)),
        clock_uncertainty_ns=mapping['uncertainty_ns'], logical_backlogs=logical,
        client_dropped=client['client_dropped'], missed_arrivals=client['missed_arrivals'],
        client_cpu_usec=client['client_cpu_usec'], valid_evidence=True)
    for key in ('e2e_ns', 'queue_ns', 'processing_wall_ns', 'completion_to_resume_ns',
                'scheduled_to_entry_upper_ns', 'resume_to_client_upper_ns'):
        result[key] = distribution([r[key] for r in rows])
    gap = result['completion_to_resume_ns']
    informative = [r['post_publication_wait_lower_bound_ns'] for r in rows
                   if r['post_publication_wait_lower_bound_ns'] is not None]
    result.update(gap_mean_all_offers_ns=gap['mean'] if gap['n']==n else None,
        gap_p99_all_offers_ns=gap['p99'] if gap['n']==n else None,
        gap_coverage_fraction=gap['n']/n, gap_unobserved_count=n-gap['n'],
        gap_fraction_interpretation='observed >50 ms count / all offers; lower bound when gap coverage is incomplete',
        publication_bound_status_counts=dict(collections.Counter(r['publication_bound_status'] for r in rows)),
        post_publication_wait_lower_bound_observed=distribution(informative),
        available_result_crossing_count=sum(r['available_result_deadline_crossing'] for r in rows),
        available_result_crossing_fraction=sum(r['available_result_deadline_crossing'] for r in rows)/n,
        crossover_publication_bound_unknown_count=sum(r['deadline_class']=='computed_before_handler_resumed_after'
            and not r['available_result_deadline_crossing'] for r in rows))
    return result


def groups(config, rows):
    out = []
    for label, key in (('phase', 'phase'), ('second', 'burst_second'), ('cycle', 'cycle')):
        for value in sorted({r[key] for r in rows}):
            subset = [r for r in rows if r[key] == value]
            item = dict(trial=config['trial'], block=config['block'], arm=config['arm'], grouping=label,
                value=value, offered=len(subset), timely_500_fraction=sum(r['timely_500'] for r in subset)/len(subset),
                crossover_fraction=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' for r in subset)/len(subset),
                available_result_crossing_fraction=sum(r['available_result_deadline_crossing'] for r in subset)/len(subset),
                gap_coverage_fraction=sum(r['completion_to_resume_ns'] is not None for r in subset)/len(subset),
                publication_informative_fraction=sum(r['publication_bound_status']=='informative' for r in subset)/len(subset))
            for field in ('e2e_ns', 'queue_ns', 'processing_wall_ns', 'completion_to_resume_ns','post_publication_wait_lower_bound_ns'):
                d = distribution([r[field] for r in subset])
                item[field+'_mean'] = d['mean']
                item[field+'_p99'] = d['p99']
                item[field+'_observed'] = d['n']
            out.append(item)
    return out


def validate_client_argv(directory, name, client, config, seconds):
    argv = c.read(directory/(name+'_argv.json'))
    session = next((p for p in directory.parents if (p/'preparation/manifest.json').exists()), None)
    if session is None or argv[0] != str(session/'preparation/loadgen'):
        raise ValueError('actual loadgen executable path differs')
    expected = ['-url', client['target_url'], '-duration', str(seconds)+'s', '-rate', str(config['rate']),
        '-pattern', config['traffic_pattern'], '-burst-low', str(config['burst_low']), '-burst-high', str(config['burst_high']), '-burst-period', '10s',
        '-concurrency', '512', '-timeout', str(config['timeout_sec'])+'s', '-trace-client=true',
        '-output', str(directory/(name+'.json'))]
    if argv[1:] != expected:
        raise ValueError('actual client command differs')
    url = urlparse(client['target_url'])
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or url.path != '/work' or parse_qs(url.query) != {'iterations': ['44000']}:
        raise ValueError('client endpoint/work differs')


def replay(directory, functional=False):
    c.verify_seal(directory)
    config, cleanup = c.read(directory/'config.json'), c.read(directory/'cleanup.json')
    c.validate_config(config, functional)
    if cleanup['errors'] or not cleanup['container_removed'] or not cleanup['cgroup_removed'] or cleanup['tracing_used'] or cleanup['watchdog_intervened']:
        raise ValueError('owned cleanup/watchdog invalidates trial')
    initial, identity = c.read(directory/'initial.json'), c.read(directory/'identity.json')
    container = c.read(directory/'container.json')['inspect']
    hc = container['HostConfig']
    c.validate_resources(initial['initial_limits'], hc, initial['resource_baseline'], config)
    if container['Image'] != identity['image']:
        raise ValueError('container resource/image inspection differs')
    if len(container['Mounts']) != 1 or container['Mounts'][0]['Destination'] != '/qualification' or container['Mounts'][0]['RW']:
        raise ValueError('startup mount differs')
    if container['Path'] != '/qualification/gate' or container['Args'] != ['--server']:
        raise ValueError('startup command differs')
    expected_env = {'GOMAXPROCS=1', 'WORKERS='+str(config['workers']), 'QUEUE_SIZE=128', 'INSTRUMENT=1',
                    'WORKER_YIELD='+str(int(config['worker_yield']))}
    actual = container['Config']['Env']
    for prefix in ('GOMAXPROCS=', 'WORKERS=', 'QUEUE_SIZE=', 'INSTRUMENT=', 'WORKER_YIELD='):
        if [e for e in actual if e.startswith(prefix)] != [e for e in expected_env if e.startswith(prefix)]:
            raise ValueError('service environment differs')
    if initial['container_server_sha256'] != identity['server_sha256'] or c.digest(directory/'container.server') != identity['server_sha256']:
        raise ValueError('actual packaged executable hash differs')
    if c.digest(directory/'qualification/gate') != identity['gate_sha256']:
        raise ValueError('actual startup gate hash differs')
    before, after = initial['process_identity'], identity['process_identity_after_exec']
    if any(before[k] != after[k] for k in ('pid', 'start_ticks', 'uid')):
        raise ValueError('startup gate and server are different processes')
    for offset in initial['time_namespaces'].values():
        if offset != {'monotonic': [0, 0], 'boottime': [0, 0]}:
            raise ValueError('time namespace shifted')
    if not initial['uncapped_ancestors'] or any(a['cpu_max'].split()[0] != 'max' for a in initial['uncapped_ancestors']):
        raise ValueError('uncapped ancestry not established')
    validate_service(identity['health'], config)
    if identity['health']['queue_cap'] != 128:
        raise ValueError('queue capacity differs')
    client, server = c.read(directory/'loadgen.json'), c.read(directory/'server_metrics.json')
    validate_client_argv(directory, 'loadgen', client, config, config['duration_sec'])
    rows, mapping, logical = join(client, server, config)
    kernel_bridge_analysis.clock_join(c.read(directory/'host_server_anchors.json'), mapping, server['clock_generation'])
    if not functional:
        warm = c.warmup_config(config)
        warm_client = c.read(directory/'warmup.json')
        c.validate_client(warm_client, warm)
        validate_client_argv(directory, 'warmup', warm_client, warm, 20)
        warm_server = c.read(directory/'warmup_server_metrics.json')
        join(warm_client, warm_server, warm)
        reset = c.read(directory/'reset.json')
        validate_service(reset['health'], config)
        if reset['health']['completed'] or reset['health']['admitted'] or reset['health']['clock_generation'] != server['clock_generation']:
            raise ValueError('measurement reset not established')
        if not c.read(directory/'settling.json')['accepted']:
            raise ValueError('thermal settling failed')
        monitor, environment = c.read(directory/'monitor.json'), c.read(directory/'environment.json')
        if len(monitor) < 80 or any(m['chatgpt_present'] or m['power_settings'] != comparable_power(environment['power_settings']) for m in monitor):
            raise ValueError('monitor coverage/quiet/power failure')
    observations = c.read(directory/'observations.json')
    if set(observations) != {'startup','measurement_start','measurement_stop','final'}:
        raise ValueError('CPU/resource observation coverage differs')
    for observed in observations.values():
        if observed['limits'] != initial['initial_limits'] or not observed['before_ns'] <= observed['after_ns']:
            raise ValueError('CPU/resource observation differs')
    sequence = [observations[k] for k in ('startup','measurement_start','measurement_stop','final')]
    for before, after in zip(sequence, sequence[1:]):
        if (before['after_ns'] > after['before_ns'] or set(before['cpu_stat']) != set(after['cpu_stat'])
                or any(after['cpu_stat'][k] < value for k,value in before['cpu_stat'].items())):
            raise ValueError('CPU/resource observations moved backwards')
    snapshots = c.read(directory/'thread_snapshots.json')
    if not snapshots or any(s['affinity'] != [2,4] or s['cgroup'] != initial['cgroup']
            or not s['before_ns'] <= s['after_ns'] or not s['tids'] for s in snapshots):
        raise ValueError('live service thread/cgroup/affinity observations differ')
    summary = summarize(config, client, server, rows, mapping, logical, observations)
    return json.loads(json.dumps(dict(summary=summary, requests=rows, clocks=mapping,
                                     phase_groups=groups(config, rows) if config['traffic_pattern']=='bursty' else []), allow_nan=False))



CONTRASTS = {'yield_100': ('A','B'), 'yield_20': ('C','D'),
             'period_no_yield': ('A','C'), 'period_yield': ('B','D'),
             'combined_vs_baseline': ('A','D')}
EFFECT_FIELDS = ('gap_mean_delta_ns','gap_mean_relative_reduction','gap_p99_delta_ns',
    'gap_gt50ms_delta','available_result_crossing_delta','timely_500_delta',
    'timely_1000_delta','failure_delta','cpu_ratio','p99_ratio')
