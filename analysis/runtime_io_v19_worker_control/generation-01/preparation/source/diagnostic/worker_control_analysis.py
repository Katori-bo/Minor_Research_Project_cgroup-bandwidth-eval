"""All-offer V19 outcomes and block-level prospective decisions; no collector."""
import bisect
import collections
import json
import math
import statistics as st

import worker_control_common as c
import parallelism_analysis
import repeatability_analysis
import kernel_bridge_analysis
from urllib.parse import urlparse, parse_qs
from environment_controls import comparable_power

MARGINS = dict(timely_500_delta=.01, timely_1000_delta=.01,
               failure_delta=.001, cpu_ratio=.05, p99_ratio=.10)
PRIMARY_TARGET = .03
T95_DF5 = 2.570581835636305
LIMITATION = ('Six independent blocks are a discovery study, not confirmation or equivalence. '
              'Completion precedes bookkeeping/publication; handler runnable readiness remains unobserved. '
              'No kernel observation or scheduler-only causal attribution is made.')


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
    repeatability_analysis.validate_state(server, 'legacy_a')
    if (server['workers'] != config['workers'] or server['gomaxprocs'] != 1
            or server['go_version'] != 'go1.26.1' or not server['instrument']):
        raise ValueError('service/runtime configuration differs')
    if server['active_handlers'] or server['queue_len'] or server['completed'] != server['admitted']:
        raise ValueError('service not fully drained')


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
            deadline_class=category, phase='low' if scheduled % 10_000_000_000 < 5_000_000_000 else 'high',
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
    return rows, mapping, logical


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
        workers=config['workers'], offered=n, completed_computations=completed,
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
    return result


def groups(config, rows):
    out = []
    for label, key in (('phase', 'phase'), ('second', 'burst_second'), ('cycle', 'cycle')):
        for value in sorted({r[key] for r in rows}):
            subset = [r for r in rows if r[key] == value]
            item = dict(trial=config['trial'], block=config['block'], arm=config['arm'], grouping=label,
                value=value, offered=len(subset), timely_500_fraction=sum(r['timely_500'] for r in subset)/len(subset),
                crossover_fraction=sum(r['deadline_class'] == 'computed_before_handler_resumed_after' for r in subset)/len(subset))
            for field in ('e2e_ns', 'queue_ns', 'processing_wall_ns', 'completion_to_resume_ns'):
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
    expected = ['-url', client['target_url'], '-duration', str(seconds)+'s', '-rate', '113.21',
        '-pattern', 'bursty', '-burst-low', '56.605', '-burst-high', '169.815', '-burst-period', '10s',
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
    c.validate_resources(initial['initial_limits'], hc, initial['resource_baseline'])
    if container['Image'] != identity['image'] or hc['CpuQuota'] != 50000 or hc['CpuPeriod'] != 100000 or hc['CpusetCpus'] != '2,4':
        raise ValueError('container resource/image inspection differs')
    if len(container['Mounts']) != 1 or container['Mounts'][0]['Destination'] != '/qualification' or container['Mounts'][0]['RW']:
        raise ValueError('startup mount differs')
    if container['Path'] != '/qualification/gate' or container['Args'] != ['--server']:
        raise ValueError('startup command differs')
    expected_env = {'GOMAXPROCS=1', 'WORKERS='+str(config['workers']), 'QUEUE_SIZE=128', 'INSTRUMENT=1'}
    actual = container['Config']['Env']
    for prefix in ('GOMAXPROCS=', 'WORKERS=', 'QUEUE_SIZE=', 'INSTRUMENT='):
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
        warm = dict(config, duration_sec=20)
        warm_client = c.read(directory/'warmup.json')
        c.validate_client(warm_client, warm)
        validate_client_argv(directory, 'warmup', warm_client, config, 20)
        validate_service(c.read(directory/'warmup_server_metrics.json'), config)
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
    summary = summarize(config, client, server, rows, mapping, logical, observations)
    return json.loads(json.dumps(dict(summary=summary, requests=rows, clocks=mapping,
                                     phase_groups=groups(config, rows)), allow_nan=False))


def ratio(y, x):
    return y/x if all(v is not None and math.isfinite(v) and v > 0 for v in (x, y)) else None


def contrast(base, treatment):
    result = {key+'_delta': treatment[key+'_fraction']-base[key+'_fraction']
              for key in ('timely_500', 'timely_1000', 'failure')}
    for label, field in (('cpu', 'cpu_usec_per_completed_work'), ('p99', 'p99_e2e_ms')):
        result[label+'_ratio'] = ratio(treatment[field], base[field])
    for field in ('gap_gt50ms_fraction', 'crossover_fraction'):
        a, z = base[field], treatment[field]
        result[field+'_relative_reduction'] = (a-z)/a if a > 0 else None
    return result


def finite(effect):
    return all(effect[k] is not None and math.isfinite(effect[k]) for k in MARGINS)


def statistical_summary(values):
    v = [x for x in values if x is not None and math.isfinite(x)]
    return dict(n=len(v), median=st.median(v) if v else None, mean=st.mean(v) if v else None,
        minimum=min(v) if v else None, maximum=max(v) if v else None,
        sample_sd=st.stdev(v) if len(v) > 1 else None)


def compare(rows, interrupted_blocks=()):
    cells = {(r['block'], r['arm']): r for r in rows}
    if len(cells) != len(rows) or not set(cells) <= {(b, a) for b in range(1, 7) for a in c.ARMS}:
        raise ValueError('duplicate or unexpected V19 trial cell')
    blocks = []
    for b in range(1, 7):
        complete = all((b, a) in cells for a in c.ARMS)
        row = dict(block=b, complete=complete, interrupted=b in interrupted_blocks)
        if complete:
            a, z, one = (cells[b, arm] for arm in c.ARMS)
            baseline = {k: (a[k]+z[k])/2 if a[k] is not None and z[k] is not None else None
                        for k in ('timely_500_fraction', 'timely_1000_fraction', 'failure_fraction',
                                  'cpu_usec_per_completed_work', 'p99_e2e_ms', 'gap_gt50ms_fraction', 'crossover_fraction')}
            aa, effect = contrast(a, z), contrast(baseline, one)
            aa['within_screen'] = finite(aa) and all(abs(aa[k]-(1 if k.endswith('ratio') else 0)) <= margin+1e-12 for k, margin in MARGINS.items())
            effect['guardrails_pass'] = (finite(effect) and effect['timely_1000_delta'] >= -.01-1e-12
                and effect['failure_delta'] <= .001+1e-12 and effect['cpu_ratio'] <= 1.05+1e-12 and effect['p99_ratio'] <= 1.10+1e-12)
            row.update(aa=aa, one_vs_mean=effect, one_vs_a=contrast(a, one), one_vs_b=contrast(z, one))
        blocks.append(row)
    complete = all(b['complete'] for b in blocks)
    effects = [b['one_vs_mean'] for b in blocks if b['complete']]
    stats = {key: statistical_summary([e[key] for e in effects]) for key in
             list(MARGINS)+['gap_gt50ms_fraction_relative_reduction', 'crossover_fraction_relative_reduction']}
    primary = stats['timely_500_delta']
    ci = None
    if complete:
        half = T95_DF5*primary['sample_sd']/math.sqrt(6)
        ci = dict(mean=primary['mean'], lower=primary['mean']-half, upper=primary['mean']+half,
                  degrees_of_freedom=5, experimental_unit='block', method='Student t small-sample discovery summary')
    repeatable = complete and all(b['aa']['within_screen'] for b in blocks)
    primary_pass = (complete and primary['median'] >= PRIMARY_TARGET-1e-12
        and sum(e['timely_500_delta'] > 0 for e in effects) >= 5 and ci['lower'] > 0
        and all(sum(b['one_vs_'+ref]['timely_500_delta'] > 0 for b in blocks) >= 5 for ref in ('a', 'b')))
    guards = complete and all(e['guardrails_pass'] for e in effects)
    mechanism = complete and all(stats[key]['n'] == 6 and stats[key]['median'] >= .5-1e-12
        and sum(e[key] > 0 for e in effects) >= 5 for key in
        ('gap_gt50ms_fraction_relative_reduction', 'crossover_fraction_relative_reduction'))
    if not complete:
        decision = 'incomplete_evidence'
    elif interrupted_blocks:
        decision = 'inconclusive_interrupted_blocks'
    elif not repeatable:
        decision = 'inconclusive_repeatability'
    elif not guards:
        decision = 'guardrail_failure'
    elif primary_pass:
        decision = 'useful_worker_control_with_gap_signal' if mechanism else 'useful_worker_control_without_gap_signal'
    elif mechanism:
        decision = 'gap_reduction_without_useful_deadline_gain'
    else:
        decision = 'worker_control_not_demonstrated'
    return dict(decision=decision, complete_evidence=complete, blocks=blocks, block_statistics=stats,
        primary_mean_ci95=ci, margins=MARGINS, primary_target=PRIMARY_TARGET,
        repeatability_pass=repeatable, guardrails_pass=guards, primary_signal_pass=primary_pass,
        post_computation_signal_pass=mechanism,
        eligible_for_independent_confirmation=complete and repeatable and primary_pass and guards and not interrupted_blocks,
        publication_observed=False, runnable_readiness_observed=False, kernel_observation=False, limitation=LIMITATION)
