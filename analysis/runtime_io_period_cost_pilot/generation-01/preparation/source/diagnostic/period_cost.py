#!/usr/bin/env python3
"""Prepare, run and replay one bounded original-binary CPU-period cost pilot."""
import argparse
import bisect
import csv
import fcntl
import json
import math
import os
from pathlib import Path
import platform
import shutil
import signal
import statistics as st
import subprocess
import sys
import time
import traceback

import execution_delay_common as old
import execution_delay_analysis as legacy_analysis
import execution_delay_study as legacy
from execution_delay_service import Service
import kernel_bridge_analysis
import kernel_service_bridge as bridge
import period_cost_perf as hardware
import run
from environment_controls import power_settings

ROOT = old.ROOT
BASE = ROOT/'analysis/runtime_io_v20_execution_delay/generation-03'
PARENT = ROOT/'analysis/runtime_io_period_cost_pilot'
DEFAULT = PARENT/'generation-01'
NEW_FILES = ('diagnostic/period_cost.py', 'diagnostic/period_cost_perf.py',
             'diagnostic/period_cost_fixture.c', 'diagnostic/test_period_cost.py',
             'diagnostic/start_period_cost.sh', 'docs/runtime_io_period_cost_pilot.md',
             'docs/runtime_io_paper_scope.md')
ORDERS = (('100_off','100_on','20_off','20_on'),
          ('100_on','100_off','20_on','20_off'),
          ('20_off','20_on','100_off','100_on'),
          ('20_on','20_off','100_on','100_off'))
MARGINS = dict(cpu=.01, busy_capacity=.01, timely_500=.01, timely_1000=.01,
               failure=.001, p99=.10, counter_coverage=.995, alignment=.005,
               fixture_instruction_span=.01, signal=.02, precision=.02)
LIMITATION = ('Four blocks are a capped feasibility pilot, not a powered equivalence study. '
              'Aggregate user counters cover the whole service, not individual SHA calculations. '
              'Rejected-offer and runtime work remain included. Cycles/user-CPU is an effective '
              'aggregate clock proxy, not a verified worker frequency. No kernel scheduler trace, '
              'causal mechanism, generalization or novelty is established by a passing screen.')


def owned_directory(value):
    path = Path(value).absolute()
    if path.parent != PARENT or path.resolve() != path or path.is_symlink():
        raise ValueError('use a direct dedicated period-cost generation directory')
    return path


def matrix():
    return [dict(trial=f'b{b}_{arm}', block=b, order=(b-1)*4+i+1,
                 period_ms=int(arm.split('_')[0]), counters=arm.endswith('_on'))
            for b, order in enumerate(ORDERS, 1) for i, arm in enumerate(order)]


def legacy_config(spec):
    arm = 'A' if spec['period_ms'] == 100 else 'C'
    # Preserve the exact V20 baseline configuration and use a separate pilot ID.
    return next(v for v in old.matrix() if v['block'] == spec['block'] and v['arm'] == arm)


def source_hashes():
    retained = old.read(BASE/'preparation/manifest.json')['sources']
    for name, sha in retained.items():
        if old.digest(ROOT/name) != sha:
            raise ValueError('retained V20 dependency changed: '+name)
    return {name: old.digest(ROOT/name) for name in sorted(set(retained)|set(NEW_FILES))}


def verify_preparation(session, current=True):
    old.verify_seal(session/'preparation')
    manifest = old.read(session/'preparation/manifest.json')
    if manifest['matrix'] != matrix() or manifest['margins'] != MARGINS or manifest['workload'] != old.WORKLOAD:
        raise ValueError('frozen protocol differs')
    for name, sha in manifest['sources'].items():
        if old.digest(session/'preparation/source'/name) != sha:
            raise ValueError('frozen source differs: '+name)
        if current and old.digest(ROOT/name) != sha:
            raise ValueError('current source differs: '+name)
    for name, key in [('loadgen','loadgen_sha256'),('gate','gate_sha256'),
                      ('original.server','server_sha256'),('fixture','fixture_sha256')]:
        if old.digest(session/'preparation'/name) != manifest[key]:
            raise ValueError('prepared executable differs: '+name)
    if current and old.baseline() != manifest['baseline']:
        raise ValueError('kernel, boot or CPU topology changed; prepare a new generation')
    return manifest


def prepare(session):
    if os.geteuid() == 0 or session.exists():
        raise ValueError('prepare as the normal user into a new generation')
    old.verify_seal(BASE/'preparation')
    sources = source_hashes()
    PARENT.mkdir(parents=True, exist_ok=True)
    old.capacity(PARENT)
    prep = session/'preparation'; prep.mkdir(parents=True)
    try:
        for name in sources:
            target = prep/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)
        for name in ('gate','loadgen','original.server'):
            shutil.copy2(BASE/'preparation'/name, prep/name)
        previous = old.read(BASE/'preparation/manifest.json')
        argv = ['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror',
                str(prep/'source/diagnostic/period_cost_fixture.c'),'-o',str(prep/'fixture')]
        compiled = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        old.save(prep/'compile.json', dict(argv=argv, returncode=compiled.returncode,
                                         stdout=compiled.stdout, stderr=compiled.stderr))
        if compiled.returncode:
            raise ValueError('known-work fixture compilation failed')
        smoke = subprocess.run([str(prep/'fixture'),'selftest'], input='GQ',
                               capture_output=True, text=True, timeout=5)
        old.save(prep/'fixture_smoke.json', dict(returncode=smoke.returncode,
                  stdout=smoke.stdout, stderr=smoke.stderr, hardware_counters_used=False))
        if smoke.returncode or not smoke.stdout.startswith('READY\nCHILD ') or '\nDONE ' not in smoke.stdout or smoke.stderr:
            raise ValueError('native fixture functional check failed')
        manifest = dict(schema=1, matrix=matrix(), margins=MARGINS, workload=old.WORKLOAD,
            sources=sources, baseline=old.baseline(), prepared=time.time(), performance_run=False,
            v20_preparation_seal=old.digest(BASE/'preparation/seal.json'),
            fixture_sha256=old.digest(prep/'fixture'),
            **{k: previous[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline')})
        old.save(prep/'manifest.json', manifest)
        old.save(prep/'arrivals.json', old.arrivals())
        tested = subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic',
            '-p','test_period_cost.py','-v'], cwd=ROOT, capture_output=True, text=True, timeout=60)
        (prep/'tests.stdout').write_text(tested.stdout); (prep/'tests.stderr').write_text(tested.stderr)
        if tested.returncode:
            raise ValueError('pilot regression checks failed')
        if source_hashes() != sources:
            raise ValueError('sources changed during preparation')
        old.seal(prep); verify_preparation(session)
        print('Prepared: '+str(session)+'; privileged counter fixtures and service trials remain unrun.')
    except BaseException as e:
        old.save(prep/'preparation_failure.json', dict(error=str(e), traceback=traceback.format_exc()))
        old.seal(prep)
        raise


def parse_perf(path, enabled=True):
    text = path.read_text()
    records = [json.loads(s) for s in text.splitlines() if s.strip() and not s.lstrip().startswith('#')]
    if not enabled:
        if records:
            raise ValueError('counter-off trial contains events')
        return None
    counts = {}
    coverage = []
    for row in records:
        event = row['event']
        cpu = int(str(row['cpu']).removeprefix('CPU'))
        if event not in ('cycles:u','instructions:u') or cpu not in (2,4) or (cpu,event) in counts:
            raise ValueError('unexpected/duplicate event or CPU')
        value = float(row['counter-value'])
        pcnt = float(row['pcnt-running'])/100
        if not math.isfinite(value) or value < 0 or not math.isfinite(pcnt) or not MARGINS['counter_coverage'] <= pcnt <= 1.000001:
            raise ValueError('unsupported, missing or multiplexed counter')
        if float(row['event-runtime']) <= 0:
            raise ValueError('counter has no runtime')
        counts[cpu,event] = value; coverage.append(pcnt)
    if set(counts) != {(cpu,event) for cpu in (2,4) for event in ('cycles:u','instructions:u')}:
        raise ValueError('both counters on both service CPUs required')
    instructions = sum(counts[cpu,'instructions:u'] for cpu in (2,4))
    cycles = sum(counts[cpu,'cycles:u'] for cpu in (2,4))
    if instructions <= 0 or cycles <= 0:
        raise ValueError('empty hardware capture')
    return dict(instructions=instructions, cycles=cycles, cycles_per_instruction=cycles/instructions,
                minimum_coverage=min(coverage), by_cpu={str(cpu):{event:counts[cpu,event]
                    for event in ('cycles:u','instructions:u')} for cpu in (2,4)})


def counter_bounds(receipt):
    controls = receipt['controls']
    if [r['op'] for r in controls] != ['disable','enable','disable'] or receipt['returncode'] != 0:
        raise ValueError('collector lifecycle/exit failed')
    start, stop = controls[1:]
    if not start['before_ns'] <= start['after_ns'] < stop['before_ns'] <= stop['after_ns']:
        raise ValueError('counter control timestamps out of order')
    result = {}
    for key in ('usage_usec','user_usec','system_usec'):
        lower = stop['cpu_before'][key]-start['cpu_after'][key]
        upper = stop['cpu_after'][key]-start['cpu_before'][key]
        if lower < 0 or upper < lower:
            raise ValueError('counter-aligned CPU accounting went backwards')
        result[key] = dict(lower=lower, upper=upper, midpoint=(lower+upper)/2)
    if result['usage_usec']['upper'] <= 0:
        raise ValueError('no measured CPU work')
    width = (result['usage_usec']['upper']-result['usage_usec']['lower'])/result['usage_usec']['upper']
    if width > MARGINS['alignment']:
        raise ValueError('counter/CPU alignment uncertainty exceeds 0.5%')
    result['relative_alignment_width'] = width
    result['wall_sec'] = (stop['before_ns']-start['after_ns'])/1e9
    return result


def validate_counter(directory, enabled):
    receipt = old.read(directory/'perf_receipt.json')
    if receipt['enabled'] != enabled or old.read(directory/'perf_argv.json') != receipt['argv']:
        raise ValueError('collector identity/arguments differ')
    argv = receipt['argv']
    expected = ['/usr/bin/perf','stat','-a','-C','2,4','-A','-j','-D','-1',
                '--timeout','300000','--control',argv[12],'-o',str(directory/'perf.jsonl')]
    # File descriptors are ephemeral integers; all remaining arguments are fixed.
    if not argv[12].startswith('fd:') or not all(x.isdigit() for x in argv[12][3:].split(',')) or len(argv[12][3:].split(',')) != 2:
        raise ValueError('invalid collector control descriptors')
    expected += ['-e','{cycles:u,instructions:u}',
                 '-G',str(Path(receipt['cgroup']).relative_to('/sys/fs/cgroup'))] if enabled else ['-n']
    expected += ['--','/usr/bin/cat']
    if argv != expected:
        raise ValueError('collector command differs from fixed protocol')
    messages = [s.strip() for s in (directory/'perf.stderr').read_text().splitlines() if s.strip()]
    if any(s not in ('Events disabled','Events enabled') for s in messages):
        raise ValueError('unexpected collector diagnostic')
    return parse_perf(directory/'perf.jsonl', enabled), counter_bounds(receipt)


def validate_fixtures(directory):
    values = []
    for name in ('compute_1','compute_2','compute_3','compute_sleep'):
        d = directory/name
        cleanup = old.read(d/'cleanup.json')
        if cleanup['errors'] or cleanup['error'] or not cleanup['cgroup_removed']:
            raise ValueError('fixture cleanup failed')
        counters, bounds = validate_counter(d, True)
        if any(v['instructions:u'] <= 0 for v in counters['by_cpu'].values()):
            raise ValueError('fixture did not exercise both CPUs')
        values.append(dict(name=name, **counters, cpu_bounds=bounds))
    instructions = [v['instructions'] for v in values]
    if max(instructions)/min(instructions)-1 > MARGINS['fixture_instruction_span']:
        raise ValueError('fixed-work instruction counts vary by more than 1%')
    sleep, compute = values[-1], values[:-1]
    wall_extra = sleep['cpu_bounds']['wall_sec']-st.mean(v['cpu_bounds']['wall_sec'] for v in compute)
    cpu_extra = sleep['cpu_bounds']['usage_usec']['midpoint']/1e6-st.mean(v['cpu_bounds']['usage_usec']['midpoint']/1e6 for v in compute)
    if wall_extra < .75 or wall_extra-cpu_extra < .75:
        raise ValueError('known sleep was not separated from running CPU time')
    return dict(passed=True, fixtures=values, wall_extra_sec=wall_extra,
                cpu_extra_sec=cpu_extra, service_observer_qualified=False)


class Helper:
    def __init__(self, session):
        self.log = (session/'helper.stderr').open('x')
        self.process = subprocess.Popen(['sudo','-n','/usr/bin/python3',
            str(ROOT/'diagnostic/period_cost_perf.py'),'--directory',str(session)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log)
        try:
            if json.loads(hardware.line(self.process.stdout, 10, self.process)) != {'ready':True}:
                raise ValueError('privileged helper did not initialize')
        except BaseException:
            self.close()
            raise

    def request(self, op, timeout=15):
        self.process.stdin.write((json.dumps(dict(op=op))+'\n').encode()); self.process.stdin.flush()
        return json.loads(hardware.line(self.process.stdout, timeout, self.process))

    def close(self):
        self.process.stdin.close()  # EOF makes helper detach and clean owned resources.
        self.process.wait(timeout=20)
        self.process.stdout.close(); self.log.close()


def collect(session, spec, helper):
    directory = session/'trials'/spec['trial']; directory.mkdir(parents=True, exist_ok=False)
    config = legacy_config(spec)
    old.save(directory/'pilot_config.json', spec); old.save(directory/'config.json', config)
    service = Service(session, config, directory)
    monitor = monitor_log = None
    attached = False
    failure = None
    resources = []
    def observe():
        value = service.observe(); resources.append(value); return value
    def load(seconds, name):
        argv = [str(session/'preparation/loadgen'),'-url',service.base+'/work?iterations=44000',
            '-duration',str(seconds)+'s','-rate','113.21','-pattern','bursty',
            '-burst-low','56.605','-burst-high','169.815','-burst-period','10s',
            '-concurrency','512','-timeout','5s','-trace-client=true','-output',str(directory/(name+'.json'))]
        old.save(directory/(name+'_argv.json'), argv)
        with (directory/(name+'.log')).open('x') as log:
            p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
                                 preexec_fn=lambda: os.sched_setaffinity(0,{0,1}))
            try:
                until = time.monotonic()+seconds+30
                while p.poll() is None:
                    observe()
                    if time.monotonic() > until: raise TimeoutError('bounded client timeout')
                    time.sleep(1)
                if p.returncode: raise ValueError('retained loadgen failed')
            finally:
                legacy.fixtures.stop(p, signal.SIGTERM)
    try:
        run.require_quiet_host()
        env = old.read(session/'environment.json'); old.save(directory/'environment.json', env)
        progress(session,spec,'settling')
        run.old.settle(directory/'settling.json',env['baseline_c'],expected_power=env['power_settings'])
        old.capacity(session); verify_preparation(session)
        service.create()
        monitor_log = (directory/'monitor.log').open('x')
        monitor = subprocess.Popen([sys.executable,str(ROOT/'scripts/monitor_host.py'),
            '--cgroup-path',str(service.group).removeprefix('/sys/fs/cgroup'),
            '--output',str(directory/'monitor.json')],stdout=monitor_log,stderr=subprocess.STDOUT,
            preexec_fn=lambda: os.sched_setaffinity(0,{0,1}))
        service.release(); observations = dict(startup=observe())
        progress(session,spec,'warmup'); load(20,'warmup')
        old.save(directory/'warmup_server_metrics.json',legacy.drain(service))
        old.save(directory/'reset.json',legacy.reset(service))
        helper.request('attach'); attached = True
        anchors = bridge.anchors(service.base,'start')
        observations['measurement_start'] = observe()
        helper.request('enable')
        progress(session,spec,'measurement'); load(60,'loadgen')
        progress(session,spec,'drain'); server = legacy.drain(service)
        helper.request('disable'); observations['measurement_stop'] = observe()
        helper.request('detach'); attached = False
        anchors += bridge.anchors(service.base,'stop'); observations['final'] = observe()
        old.save(directory/'host_server_anchors.json',anchors)
        old.save(directory/'server_metrics.json',server); old.save(directory/'observations.json',observations)
        old.save(directory/'resource_samples.json',resources)
        if power_settings(include_profile=True) != env['power_settings']:
            raise ValueError('power settings changed')
        legacy.fixtures.stop(monitor,signal.SIGINT)
        if monitor.returncode: raise ValueError('host monitor failed')
        monitor_log.close(); monitor = None
        service.close(); old.seal(directory)
        result = replay_trial(directory)
        old.save(directory/'derived.json',result)
        old.save(directory/'complete.json',dict(valid=True,finished=time.time()))
        old.seal(directory)
    except BaseException as e:
        failure = str(e)
        old.save(directory/'failure.json',dict(error=failure,traceback=traceback.format_exc()))
        raise
    finally:
        if attached:
            try: helper.request('disable'); helper.request('detach')
            except Exception as e: old.save(directory/'counter_cleanup_failure.json',dict(error=str(e)))
        if monitor:
            legacy.fixtures.stop(monitor,signal.SIGINT); monitor_log.close()
        service.close(failure)
        if failure: old.seal(directory)


def busy_summary(directory, server, mapping):
    anchors = kernel_bridge_analysis.clock_join(old.read(directory/'host_server_anchors.json'),
                                               mapping,server['clock_generation'])
    lo, hi = anchors['kernel_minus_server_lower_ns'], anchors['kernel_minus_server_upper_ns']
    samples = old.read(directory/'resource_samples.json')
    start, stop = (old.read(directory/'observations.json')[k] for k in ('measurement_start','measurement_stop'))
    selected = [s for s in samples if start['before_ns'] <= s['before_ns'] and s['after_ns'] <= stop['after_ns']]
    jobs = server['events']
    completions = sorted(j['completion_ns'] for j in jobs)
    changes = {}
    for j in jobs:
        for timestamp, delta in [(j['admission_ns'],1),(j['worker_start_ns'],-1)]:
            changes[timestamp] = changes.get(timestamp,0)+delta
    times = sorted(changes); depths = []; depth = 0
    for timestamp in times:
        depth += changes[timestamp]; depths.append(depth)
    intervals = []
    for a,b in zip(selected,selected[1:]):
        if a['after_ns'] >= b['before_ns']: raise ValueError('resource samples overlap')
        wall = ((b['before_ns']+b['after_ns'])-(a['before_ns']+a['after_ns']))/2e9
        if not .5 <= wall <= 2: continue
        left, right = a['before_ns']-hi, b['after_ns']-lo
        i,j = bisect.bisect_right(times,left)-1,bisect.bisect_right(times,right)
        if i < 0 or min(depths[i:j] or [0]) < 1: continue
        cpu = b['cpu_stat']['usage_usec']-a['cpu_stat']['usage_usec']
        lower = bisect.bisect_right(completions,b['before_ns']-hi)-bisect.bisect_right(completions,a['after_ns']-lo)
        upper = bisect.bisect_right(completions,b['after_ns']-lo)-bisect.bisect_right(completions,a['before_ns']-hi)
        if cpu < 0 or lower < 0 or upper < lower: raise ValueError('busy-window accounting inconsistent')
        intervals.append(dict(wall_sec=wall,
            wall_lower_sec=(b['before_ns']-a['after_ns'])/1e9,
            wall_upper_sec=(b['after_ns']-a['before_ns'])/1e9,
            cpu_usec=cpu,completed_lower=lower,completed_upper=upper,
            host_before_ns=a['before_ns'],host_after_ns=b['after_ns']))
    seconds = sum(v['wall_sec'] for v in intervals)
    if seconds < 6: raise ValueError('fewer than six seconds of certainly backlogged counter windows')
    lower,upper = (sum(v['completed_'+bound] for v in intervals) for bound in ('lower','upper'))
    wall_lower = sum(v['wall_lower_sec'] for v in intervals)
    wall_upper = sum(v['wall_upper_sec'] for v in intervals)
    cpu_sec = sum(v['cpu_usec'] for v in intervals)/1e6
    return dict(intervals=intervals,seconds=seconds,capacity_lower=lower/wall_upper,
                capacity_upper=upper/wall_lower,capacity=(lower+upper)/2/seconds,
                cpu_cores=cpu_sec/seconds,cpu_cores_lower=cpu_sec/wall_upper,
                cpu_cores_upper=cpu_sec/wall_lower)


def replay_trial(directory):
    old.verify_seal(directory)
    if any((directory/name).exists() for name in ('failure.json','interruption.json','counter_cleanup_failure.json')):
        raise ValueError('failed/interrupted trial cannot be accepted')
    spec = old.read(directory/'pilot_config.json')
    if spec not in matrix() or old.read(directory/'config.json') != legacy_config(spec):
        raise ValueError('pilot configuration differs')
    result = legacy_analysis.replay(directory)
    counters, bounds = validate_counter(directory,spec['counters'])
    if old.read(directory/'perf_receipt.json')['cgroup'] != old.read(directory/'initial.json')['cgroup']:
        raise ValueError('counter target differs from actual service')
    row = dict(result['summary'], **spec)
    completed = row['completed_computations']
    row['legacy_cpu_usec_per_completed_work'] = row['cpu_usec_per_completed_work']
    row['cpu_usec_per_completed_work'] = bounds['usage_usec']['midpoint']/completed
    for bound in ('lower','upper'):
        row['cpu_usec_per_completed_work_'+bound] = bounds['usage_usec'][bound]/completed
    row['user_usec_per_completed_work'] = bounds['user_usec']['midpoint']/completed
    row['cpu_alignment_width'] = bounds['relative_alignment_width']
    row['rejected_fraction'] = row['outcome_counts'].get('rejected',0)/row['offered']
    busy = busy_summary(directory,old.read(directory/'server_metrics.json'),result['clocks'])
    row['busy_capacity'] = busy['capacity']; row['busy_cpu_cores'] = busy['cpu_cores']
    for bound in ('lower','upper'):
        row['busy_capacity_'+bound] = busy['capacity_'+bound]
        row['busy_cpu_cores_'+bound] = busy['cpu_cores_'+bound]
    if counters:
        row.update(instructions_per_job=counters['instructions']/completed,
            cycles_per_instruction=counters['cycles_per_instruction'],
            effective_cycles_per_user_sec=counters['cycles']/(bounds['user_usec']['midpoint']/1e6))
        if bounds['user_usec']['lower'] <= 0:
            raise ValueError('no bounded user CPU time for effective clock proxy')
        for bound,opposite in (('lower','upper'),('upper','lower')):
            row['effective_cycles_per_user_sec_'+bound] = counters['cycles']/(bounds['user_usec'][opposite]/1e6)
    return dict(summary=row,busy=busy,counters=counters,cpu_bounds=bounds)


def estimate(values, logarithmic=False):
    if len(values) != 4 or any(not math.isfinite(v) for v in values):
        raise ValueError('four finite block effects required')
    mean = st.mean(values); half = 3.182446305284263*st.stdev(values)/2
    transform = (lambda v: math.expm1(v)) if logarithmic else (lambda v:v)
    return dict(values=values,mean=transform(mean),lower=transform(mean-half),
                upper=transform(mean+half),halfwidth=(transform(mean+half)-transform(mean-half))/2,
                scale='relative change' if logarithmic else 'fraction-point change')


def compare(rows):
    if len(rows) != 16 or {r['trial'] for r in rows} != {s['trial'] for s in matrix()}:
        raise ValueError('all sixteen distinct pilot trials required')
    table = {r['trial']:r for r in rows}
    def effects(base,treatment,field,ratio=True):
        values = []
        lowers,uppers = [],[]
        for block in range(1,5):
            ar,br = (table[f'b{block}_{label}'] for label in (base,treatment))
            a,b = ar[field],br[field]
            if ratio and (a <= 0 or b <= 0): raise ValueError('positive ratio inputs required')
            values.append(math.log(b/a) if ratio else b-a)
            if ratio:
                alo,ahi = ar.get(field+'_lower',a),ar.get(field+'_upper',a)
                blo,bhi = br.get(field+'_lower',b),br.get(field+'_upper',b)
                if min(alo,blo) <= 0 or not alo <= a <= ahi or not blo <= b <= bhi:
                    raise ValueError('invalid measurement bounds')
                lowers.append(math.log(blo/ahi)); uppers.append(math.log(bhi/alo))
        result = estimate(values,ratio)
        if ratio:
            half = 3.182446305284263*st.stdev(values)/2
            result['lower'] = math.expm1(st.mean(lowers)-half)
            result['upper'] = math.expm1(st.mean(uppers)+half)
            result['halfwidth'] = (result['upper']-result['lower'])/2
            result['measurement_bounds_included'] = True
        return result
    observer = {}
    fields = {'cpu':'cpu_usec_per_completed_work','busy_capacity':'busy_capacity',
              'timely_500':'timely_500_fraction','timely_1000':'timely_1000_fraction',
              'failure':'failure_fraction','p99':'p99_e2e_ms'}
    for period in (100,20):
        tests = {name:effects(f'{period}_off',f'{period}_on',field,
                 name not in ('timely_500','timely_1000','failure')) for name,field in fields.items()}
        for name,value in tests.items():
            value['margin'] = MARGINS[name]
            value['passed'] = value['lower'] >= -MARGINS[name] and value['upper'] <= MARGINS[name]
        observer[str(period)] = tests
    cpu = effects('100_off','20_off','cpu_usec_per_completed_work')
    capacity = effects('100_off','20_off','busy_capacity')
    reproduced = cpu['mean'] >= MARGINS['signal'] and cpu['lower'] > 0 and capacity['upper'] < 0
    decomposition = {field:effects('100_on','20_on',field) for field in
        ('instructions_per_job','cycles_per_instruction','effective_cycles_per_user_sec','busy_cpu_cores')}
    precise = all(v['halfwidth'] <= MARGINS['precision'] for v in decomposition.values())
    qualified = all(v['passed'] for tests in observer.values() for v in tests.values())
    signals = [field for field,value in decomposition.items() if abs(value['mean']) >= MARGINS['signal']
               and (value['lower'] > 0 or value['upper'] < 0)]
    decision = ('effect_not_reproduced' if not reproduced else
                'observer_or_precision_inconclusive' if not qualified or not precise else
                'measurement_feasible_targeted_control_needed' if signals else
                'aggregate_measurements_inconclusive')
    return dict(decision=decision,effect_reproduced=reproduced,observer_screen_passed=qualified,
        decomposition_precision_passed=precise,observer=observer,
        unobserved_period_effect=dict(cpu=cpu,busy_capacity=capacity),decomposition=decomposition,
        detectable_aggregate_signals=signals,rejection_work_present=any(r['rejected_fraction']>0 for r in rows),
        causal_mechanism_established=False,novelty_established=False,limitation=LIMITATION)


def analyze(session):
    verify_preparation(session,current=False)
    old.verify_seal(session/'counter_fixtures')
    if validate_fixtures(session/'counter_fixtures') != old.read(session/'counter_fixtures/result.json'):
        raise ValueError('fixture replay differs')
    rows = []; refs = {}
    for spec in matrix():
        d = session/'trials'/spec['trial']
        if not (d/'complete.json').exists() or old.read(d/'complete.json') != dict(valid=True,finished=old.read(d/'complete.json')['finished']):
            raise ValueError('complete trial missing; no rerun or imputation')
        result = replay_trial(d)
        if result != old.read(d/'derived.json'): raise ValueError('saved trial derivation differs')
        rows.append(result['summary']); refs[spec['trial']] = old.digest(d/'seal.json')
    report = compare(rows)
    report.update(trial_seals=refs,preparation_seal=old.digest(session/'preparation/seal.json'),
                  fixture_seal=old.digest(session/'counter_fixtures/seal.json'))
    out = session/'analysis'/str(time.time_ns()); out.mkdir(parents=True)
    legacy.export_csv(out/'trials.csv',rows); old.save(out/'report.json',report)
    lines = ['# CPU-period cost feasibility pilot','', '**Decision: '+report['decision']+'**','',LIMITATION,'',
        '| Period | Observer CPU change, 95% interval | Busy capacity change, 95% interval | All observer checks pass |',
        '|---|---:|---:|---|']
    for period,tests in report['observer'].items():
        fmt = lambda v:f"{v['mean']*100:.2f}% [{v['lower']*100:.2f}, {v['upper']*100:.2f}]"
        lines.append(f"| {period} ms | {fmt(tests['cpu'])} | {fmt(tests['busy_capacity'])} | {all(v['passed'] for v in tests.values())} |")
    lines += ['', '## Aggregate period contrasts with counters on','',
              '| Quantity | Relative change, 95% interval |','|---|---:|']
    for field,value in report['decomposition'].items(): lines.append(f"| {field} | {fmt(value)} |")
    lines += ['', 'A passing result permits designing one targeted causal control; it does not approve a full sweep.',
              'Rejected-work composition must be resolved before attributing aggregate instructions to the calculation.',
              'An inconclusive observer screen is not proof of a profiler effect or technical impossibility.', '']
    (out/'report.md').write_text('\n'.join(lines)); old.seal(out)
    old.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=old.digest(out/'seal.json')))
    print(report['decision']+'; report: '+str(out/'report.md'))
    return report


def progress(session,spec,stage):
    old.save(session/'progress.json',dict(stage=stage,trial=spec['trial'],order=spec['order'],total=16,
                                         updated=time.time()))
    print(f"{spec['order']}/16 {spec['trial']}: {stage}",flush=True)


def run_pilot(session):
    if os.geteuid() == 0:
        raise ValueError('run orchestration as the normal user through the launcher')
    verify_preparation(session)
    if (session/'trials').exists() or (session/'counter_fixtures').exists():
        raise ValueError('existing attempt: preserve it; no automatic resume/rerun for this capped pilot')
    run.require_quiet_host(); run.old.check_topology()
    os.sched_setaffinity(0,{0,1})
    def interrupted(signum,frame): raise InterruptedError('pilot interrupted')
    signal.signal(signal.SIGINT,interrupted); signal.signal(signal.SIGTERM,interrupted)
    with (session/'.worker.lock').open('a') as lock, (ROOT/'results/.period-cost.lock').open('a') as global_lock:
        for handle in (lock,global_lock): fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        old.save(session/'owner.json',old.process_identity(os.getpid()))
        helper = None
        try:
            helper = Helper(session)
            print('Checking hardware counters on four bounded known-work fixtures.',flush=True)
            helper.request('fixtures',timeout=90)
            run.old.prepare_environment(session)
            old.save(session/'environment_seal.json',dict(files_sha256={name:old.digest(session/name)
                     for name in ('environment.json','initial-settling.json')}))
            for spec in matrix():
                if old.read(session/'environment_seal.json')['files_sha256'] != {
                        name:old.digest(session/name) for name in ('environment.json','initial-settling.json')}:
                    raise ValueError('environment receipt changed')
                collect(session,spec,helper)
            helper.request('finish'); helper.close(); helper = None
            report = analyze(session)
            old.save(session/'progress.json',dict(stage='complete',decision=report['decision'],total=16))
        except BaseException as e:
            old.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc(),time=time.time()))
            old.save(session/'progress.json',dict(stage='stopped',error=str(e),evidence_preserved=True))
            raise
        finally:
            if helper:
                helper.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('prepare','verify-preparation','run','analyze','status'))
    p.add_argument('--directory',type=owned_directory,default=DEFAULT)
    args = p.parse_args()
    if args.command == 'prepare': prepare(args.directory)
    elif args.command == 'verify-preparation':
        verify_preparation(args.directory); print('Frozen pilot preparation verified; collection status is separate.')
    elif args.command == 'run': run_pilot(args.directory)
    elif args.command == 'analyze': analyze(args.directory)
    else:
        print(json.dumps(old.read(args.directory/'progress.json') if (args.directory/'progress.json').exists()
                         else dict(stage='prepared',trials_completed=0),indent=2))


if __name__ == '__main__':
    try: main()
    except (Exception,KeyboardInterrupt) as e:
        print(str(e),file=sys.stderr); raise SystemExit(1)
