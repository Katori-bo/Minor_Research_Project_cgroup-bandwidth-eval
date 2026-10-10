#!/usr/bin/env python3
"""Same-binary, counter-free quota-period x automatic-GC diagnostic."""
import argparse
import contextlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

import execution_delay_common as c
import execution_delay_analysis as analysis
import execution_delay_study as legacy
from execution_delay_service import Service
import kernel_service_bridge as bridge
import run
from environment_controls import power_settings
from verify_execution_delay import verify_environment

ROOT = c.ROOT
BASE = c.PARENT/'generation-04'
PARENT = ROOT/'analysis/runtime_io_gc_probe'
DEFAULT = PARENT/'generation-01'
AUDIT = ROOT/'analysis/runtime_io_software_audit/audit-01/container_followup'
ORDERS = (('A','B','C','D'), ('B','A','D','C'), ('C','D','A','B'), ('D','C','B','A'))
FACTORS = {'A': (100, '100'), 'B': (100, 'off'), 'C': (20, '100'), 'D': (20, 'off')}
NEW_FILES = ('diagnostic/runtime_gc_probe.py', 'diagnostic/test_runtime_gc_probe.py',
    'diagnostic/start_runtime_gc_probe.sh', 'docs/runtime_io_gc_probe.md',
    'diagnostic/runtime_software_audit.py', 'diagnostic/runtime_software_audit_test.go')
MEMORY_GUARD_BYTES = 768*1024*1024
INTERACTION_MARGIN = .02


def owned_directory(value):
    path = Path(value).absolute()
    if path.parent != PARENT or path.is_symlink() or path.resolve() != path:
        raise ValueError('use a dedicated direct GC-probe generation')
    return path


def matrix():
    return [dict(trial=f'b{b}_{arm}', block=b, arm=arm, order=(b-1)*4+i+1,
                 period_ms=FACTORS[arm][0], gogc=FACTORS[arm][1])
            for b, order in enumerate(ORDERS, 1) for i,arm in enumerate(order)]


def legacy_config(spec, functional=False):
    arm = 'A' if spec['period_ms'] == 100 else 'C'
    if functional: return c.fixture(arm)
    return next(v for v in c.matrix() if v['block'] == spec['block'] and v['arm'] == arm)


def runtime_argv(stock, spec, functional=False):
    # Literal extra environment only. No change to the image, CPU contract,
    # original GOMAXPROCS/workers/instrumentation or worker-yield flags.
    values = ['-e', 'GOGC='+spec['gogc']]
    if functional: values += ['-e', 'GODEBUG=gctrace=1']
    result = list(stock)
    result[result.index('-p'):result.index('-p')] = values
    return result


class RuntimeService(Service):
    def __init__(self, session, config, directory, spec, functional=False):
        super().__init__(session, config, directory)
        self.spec, self.functional = spec, functional
        self.resources = []

    def create(self):
        original = c.service_argv
        def argv(*args): return runtime_argv(original(*args), self.spec, self.functional)
        # The runner is single-threaded. Scope this adapter strictly to startup;
        # all inherited ownership, hash, cgroup and cleanup checks remain active.
        with patch.object(c, 'service_argv', argv):
            value = super().create()
        validate_runtime_environment(self.directory, self.spec, self.functional)
        return value

    def guard(self):
        super().guard()
        if int((self.group/'memory.current').read_text()) > MEMORY_GUARD_BYTES:
            raise MemoryError('service crossed the declared 768 MiB memory safety guard')

    def observe(self):
        value = super().observe()
        value['memory_current_bytes'] = int((self.group/'memory.current').read_text())
        value['memory_peak_bytes'] = int((self.group/'memory.peak').read_text())
        self.resources.append(value)
        return value


def validate_runtime_environment(directory, spec, functional=False):
    container = c.read(directory/'container.json')['inspect']
    expected = ['GOMAXPROCS=1', 'WORKERS=1', 'QUEUE_SIZE=128', 'INSTRUMENT=1',
        'WORKER_YIELD=0', 'GOGC='+spec['gogc'],
        'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
    if functional: expected.append('GODEBUG=gctrace=1')
    if sorted(container['Config']['Env']) != sorted(expected):
        raise ValueError('complete runtime environment differs')


def source_hashes():
    retained = c.read(BASE/'preparation/manifest.json')['sources']
    for name, sha in retained.items():
        if c.digest(ROOT/name) != sha: raise ValueError('frozen dependency changed: '+name)
    return {name:c.digest(ROOT/name) for name in sorted(set(retained)|set(NEW_FILES))}


def verify_preparation(session, current=True):
    prep = session/'preparation'; c.verify_seal(prep)
    manifest = c.read(prep/'manifest.json')
    if (manifest['matrix'] != matrix() or manifest['workload'] != c.WORKLOAD
            or manifest['interaction_margin'] != INTERACTION_MARGIN
            or manifest['memory_guard_bytes'] != MEMORY_GUARD_BYTES
            or not manifest['tests_passed'] or not manifest['functional_passed']):
        raise ValueError('prepared GC protocol differs or qualification failed')
    for name,key in [('loadgen','loadgen_sha256'),('gate','gate_sha256'),('original.server','server_sha256')]:
        if c.digest(prep/name) != manifest[key]: raise ValueError('prepared binary changed')
    for name,sha in manifest['sources'].items():
        if c.digest(prep/'source'/name) != sha or (current and c.digest(ROOT/name) != sha):
            raise ValueError('prepared or loaded source changed: '+name)
    if c.read(prep/'arrivals.json') != c.arrivals(): raise ValueError('arrival vector changed')
    previous = c.read(BASE/'preparation/manifest.json')
    if manifest['base_preparation_seal'] != c.digest(BASE/'preparation/seal.json') or any(
            manifest[k] != previous[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline')):
        raise ValueError('retained binary/resource provenance changed')
    c.verify_seal(AUDIT)
    audit = c.read(AUDIT/'report.json')
    if (not audit['passed'] or audit['performance_run']
            or manifest['software_audit_seal'] != c.digest(AUDIT/'seal.json')
            or audit['source_sha256']['runtime_software_audit_test.go'] != manifest['sources']['diagnostic/runtime_software_audit_test.go']):
        raise ValueError('qualified software audit differs')
    for arm in FACTORS:
        path = prep/'functional'/arm
        c.verify_seal(path)
        result = replay(path, functional=True)
        if result != c.read(path/'derived.json'): raise ValueError('functional raw replay differs')
        cycles = len(re.findall(r'^gc \d+ @', (path/'container.stderr').read_text(), re.M))
        if (FACTORS[arm][1] == 'off' and cycles != 0) or (FACTORS[arm][1] == '100' and cycles == 0):
            raise ValueError('functional GC manipulation not demonstrated')
    if current:
        if source_hashes() != manifest['sources'] or c.baseline() != manifest['baseline']:
            raise ValueError('host/kernel/source changed; prepare a new generation')
    return manifest


def prepare(session):
    if os.geteuid() == 0 or session.exists(): raise ValueError('prepare as normal user into a new generation')
    c.verify_seal(BASE/'preparation')
    c.verify_seal(AUDIT)
    if not c.read(AUDIT/'report.json')['passed']: raise ValueError('software audit must pass before preparation')
    sources = source_hashes()
    PARENT.mkdir(parents=True, exist_ok=True); c.capacity(PARENT)
    prep = session/'preparation'; prep.mkdir(parents=True)
    try:
        for name in sources:
            target = prep/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/name, target)
        for name in ('gate','loadgen','original.server'): shutil.copy2(BASE/'preparation'/name, prep/name)
        previous = c.read(BASE/'preparation/manifest.json')
        manifest = dict(matrix=matrix(), workload=c.WORKLOAD, sources=sources, baseline=c.baseline(),
            prepared=time.time(), performance_run=False, interaction_margin=INTERACTION_MARGIN,
            memory_guard_bytes=MEMORY_GUARD_BYTES, tests_passed=False, functional_passed=False,
            software_audit_seal=c.digest(AUDIT/'seal.json'),
            base_preparation_seal=c.digest(BASE/'preparation/seal.json'),
            **{k:previous[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline')})
        c.save(prep/'manifest.json', manifest); c.save(prep/'arrivals.json', c.arrivals())
        tested = subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic',
            '-p','test_runtime_gc_probe.py','-v'], cwd=ROOT, capture_output=True, text=True, timeout=60)
        (prep/'tests.stdout').write_text(tested.stdout); (prep/'tests.stderr').write_text(tested.stderr)
        if tested.returncode: raise ValueError('GC-probe tests failed')
        manifest['tests_passed'] = True
        for arm,(period,gogc) in FACTORS.items():
            spec = dict(trial=arm, block=0, arm=arm, order=0, period_ms=period, gogc=gogc)
            collect(session, prep/'functional'/arm, spec, functional=True)
        manifest['functional_passed'] = True
        if source_hashes() != sources: raise ValueError('source changed during preparation')
        c.save(prep/'manifest.json', manifest); c.seal(prep); verify_preparation(session)
        print('Prepared and verified: '+str(session)+'; 16 performance trials remain unrun.', flush=True)
    except BaseException as e:
        c.save(prep/'preparation_failure.json', dict(error=str(e), traceback=traceback.format_exc()))
        c.seal(prep); raise


def progress(session, spec, stage):
    if spec['block'] == 0: return
    c.save(session/'progress.json', dict(trial=spec['trial'], order=spec['order'], total=16, stage=stage, updated=time.time()))
    print(f"{spec['order']}/16 {spec['trial']}: {stage}", flush=True)


def load(session, directory, service, spec, config, seconds, name):
    argv = [str(session/'preparation/loadgen'), '-url', service.base+'/work?iterations=44000',
        '-duration', str(seconds)+'s', '-rate', str(config['rate']), '-pattern','bursty',
        '-burst-low',str(config['burst_low']),'-burst-high',str(config['burst_high']),
        '-burst-period','10s','-concurrency','512','-timeout',str(config['timeout_sec'])+'s',
        '-trace-client=true','-output',str(directory/(name+'.json'))]
    c.save(directory/(name+'_argv.json'), argv)
    with (directory/(name+'.log')).open('x') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
            preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        try:
            until, next_report = time.monotonic()+seconds+30, 0
            while process.poll() is None:
                service.observe()
                if time.monotonic() >= next_report:
                    progress(session,spec,name); next_report = time.monotonic()+10
                if time.monotonic() > until: raise TimeoutError('bounded client timeout')
                time.sleep(1)
            if process.returncode: raise ValueError('retained client failed')
        finally: legacy.fixtures.stop(process,signal.SIGTERM)


def collect(session, directory, spec, functional=False):
    directory.mkdir(parents=True, exist_ok=False)
    config = legacy_config(spec,functional)
    c.save(directory/'config.json',config); c.save(directory/'runtime_config.json',spec)
    service = RuntimeService(session,config,directory,spec,functional)
    monitor = monitor_log = None
    failure = None
    try:
        if not functional:
            run.require_quiet_host()
            env = c.read(session/'environment.json'); c.save(directory/'environment.json',env)
            progress(session,spec,'settling')
            run.old.settle(directory/'settling.json',env['baseline_c'],expected_power=env['power_settings'])
            c.capacity(session)
            if power_settings(include_profile=True) != env['power_settings']: raise ValueError('power changed')
        service.create()
        if not functional:
            monitor_log = (directory/'monitor.log').open('x')
            monitor = subprocess.Popen([sys.executable,str(ROOT/'scripts/monitor_host.py'),
                '--cgroup-path',str(service.group).removeprefix('/sys/fs/cgroup'),
                '--output',str(directory/'monitor.json')],stdout=monitor_log,stderr=subprocess.STDOUT,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        service.release(); observations = dict(startup=service.observe())
        if not functional:
            load(session,directory,service,spec,config,20,'warmup')
            c.save(directory/'warmup_server_metrics.json',legacy.drain(service))
        c.save(directory/'reset.json',legacy.reset(service))
        anchors = bridge.anchors(service.base,'start')
        observations['measurement_start'] = service.observe()
        load(session,directory,service,spec,config,config['duration_sec'],'loadgen')
        progress(session,spec,'drain'); server = legacy.drain(service)
        if functional:
            # Boundary-only functional stress: demonstrate GC control using the
            # actual retained service. Never performed in a performance trial.
            for _ in range(128):
                service.guard(); bridge.get(service.base,'metrics')
        observations['measurement_stop'] = service.observe()
        anchors += bridge.anchors(service.base,'stop'); observations['final'] = service.observe()
        c.save(directory/'server_metrics.json',server)
        c.save(directory/'host_server_anchors.json',anchors)
        c.save(directory/'observations.json',observations)
        c.save(directory/'resource_samples.json',service.resources)
        if not functional and power_settings(include_profile=True) != env['power_settings']: raise ValueError('power changed')
        if monitor:
            legacy.fixtures.stop(monitor,signal.SIGINT)
            if monitor.returncode: raise ValueError('host monitor failed')
            monitor_log.close(); monitor = None
        service.close(); c.seal(directory)
        result = replay(directory,functional)
        c.save(directory/'derived.json',result)
        c.save(directory/'complete.json',dict(valid=True,performance_run=not functional,finished=time.time()))
        c.seal(directory)
    except BaseException as e:
        failure = str(e)
        c.save(directory/'failure.json',dict(error=failure,traceback=traceback.format_exc())); raise
    finally:
        if monitor:
            legacy.fixtures.stop(monitor,signal.SIGINT); monitor_log.close()
        try: service.close(failure)
        except Exception as e:
            c.save(directory/'cleanup_failure.json',dict(error=str(e)))
            if failure is None: raise
        finally:
            if failure: c.seal(directory)


def replay(directory, functional=False):
    c.verify_seal(directory)
    if any((directory/n).exists() for n in ('failure.json','interruption.json','cleanup_failure.json')):
        raise ValueError('failed trial cannot be accepted')
    spec = c.read(directory/'runtime_config.json')
    if functional:
        expected = dict(trial=spec['arm'], block=0, arm=spec['arm'], order=0,
            period_ms=FACTORS[spec['arm']][0], gogc=FACTORS[spec['arm']][1])
        if spec != expected: raise ValueError('functional factor mismatch')
    elif spec not in matrix(): raise ValueError('runtime configuration outside matrix')
    if c.read(directory/'config.json') != legacy_config(spec,functional): raise ValueError('legacy workload differs')
    validate_runtime_environment(directory,spec,functional)
    session = next(p for p in directory.parents if (p/'preparation/manifest.json').exists())
    manifest = c.read(session/'preparation/manifest.json')
    identity = c.read(directory/'identity.json')
    if any(identity[k] != manifest[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256')):
        raise ValueError('trial executable provenance differs from preparation')
    if c.read(directory/'initial.json')['resource_baseline'] != manifest['resource_baseline']:
        raise ValueError('trial resource baseline differs from preparation')
    result = analysis.replay(directory,functional)
    row = dict(result['summary'], **spec)
    samples = c.read(directory/'resource_samples.json')
    if not samples or max(v['memory_peak_bytes'] for v in samples) > MEMORY_GUARD_BYTES:
        raise ValueError('memory guard violated')
    row['memory_peak_bytes'] = max(v['memory_peak_bytes'] for v in samples)
    if not functional:
        verify_environment(session)
        if c.read(directory/'environment.json') != c.read(session/'environment.json'):
            raise ValueError('trial environment baseline differs from session')
        # Same capacity and CPU-delivery estimator as the earlier cost pilot.
        import period_cost
        busy = period_cost.busy_summary(directory,c.read(directory/'server_metrics.json'),result['clocks'])
        row['busy_capacity'] = busy['capacity']; row['busy_cpu_cores'] = busy['cpu_cores']
        result['busy'] = busy
    result['summary'] = row
    return result


def estimate(values, ratio=True):
    if len(values) != 4 or any(not math.isfinite(v) for v in values): raise ValueError('four finite block effects required')
    mean = statistics.mean(values); half = 3.182446305284263*statistics.stdev(values)/2
    transform = math.expm1 if ratio else lambda x:x
    return dict(values=values,mean=transform(mean),lower=transform(mean-half),upper=transform(mean+half))


def compare(rows):
    if len(rows) != 16 or {r['trial'] for r in rows} != {s['trial'] for s in matrix()}:
        raise ValueError('sixteen unique trials required')
    table = {r['trial']:r for r in rows}
    def effect(a,b,field,ratio=True):
        values=[]
        for block in range(1,5):
            left,right = (table[f'b{block}_{arm}'][field] for arm in (a,b))
            if ratio and min(left,right) <= 0: raise ValueError('positive ratio inputs required')
            values.append(math.log(right/left) if ratio else right-left)
        return estimate(values,ratio)
    contrasts={}
    for field in ('cpu_usec_per_completed_work','busy_capacity','busy_cpu_cores','timely_500_fraction'):
        ratio = field != 'timely_500_fraction'
        contrasts[field] = {label:effect(a,b,field,ratio) for label,a,b in
            [('period_default_gc','A','C'),('period_gc_off','B','D'),('gc_at_100','A','B'),('gc_at_20','C','D')]}
    values=[]
    for block in range(1,5):
        a,b,cc,d = (table[f'b{block}_{arm}']['cpu_usec_per_completed_work'] for arm in ('A','B','C','D'))
        values.append(math.log(d/b)-math.log(cc/a))
    interaction = estimate(values)
    signal = abs(interaction['mean']) >= INTERACTION_MARGIN and (interaction['lower'] > 0 or interaction['upper'] < 0)
    equivalent = interaction['lower'] >= -INTERACTION_MARGIN and interaction['upper'] <= INTERACTION_MARGIN
    default = contrasts['cpu_usec_per_completed_work']['period_default_gc']
    original_penalty_reproduced = default['mean'] >= .02 and default['lower'] > 0
    return dict(decision='gc_period_interaction_detected' if signal else
            'no_large_gc_period_interaction_in_tested_conditions' if equivalent else 'gc_period_interaction_inconclusive',
        cpu_interaction=interaction, contrasts=contrasts, interaction_margin=INTERACTION_MARGIN,
        original_cpu_penalty_reproduced=original_penalty_reproduced,
        rejection_work_present=any(r['failure_fraction'] > 0 for r in rows),
        historical_cause_established=False, language_bug_established=False,
        limitation='A GC-policy intervention can identify a conditional contribution to the period contrast. '
        'GC-off also changes memory lifetime and cache/page behavior. A general CPU reduction is not a period explanation. '
        'Four-block intervals are exploratory. Without reproduction of the original penalty this cannot establish its historical cause.')


def analyze(session):
    verify_preparation(session,current=False)
    rows=[]; seals={}
    for spec in matrix():
        path = session/'trials'/spec['trial']
        complete = c.read(path/'complete.json')
        if not complete['valid'] or not complete['performance_run']: raise ValueError('performance trial not complete')
        result = replay(path)
        if result != c.read(path/'derived.json'): raise ValueError('independent raw replay differs')
        rows.append(result['summary']); seals[spec['trial']] = c.digest(path/'seal.json')
    report = compare(rows)
    report.update(rows=rows,trial_seals=seals,preparation_seal=c.digest(session/'preparation/seal.json'))
    out = session/'analysis'/str(time.time_ns()); out.mkdir(parents=True)
    c.save(out/'report.json',report)
    lines=['# Same-binary GC / CPU-period diagnostic','',report['decision'],'',report['limitation'],'',
        '| Cell | Period | GOGC | CPU/job ms | Busy jobs/s | 500 ms success |','|---|---:|---|---:|---:|---:|']
    for arm,(period,gogc) in FACTORS.items():
        group=[r for r in rows if r['arm']==arm]
        lines.append(f"| {arm} | {period} | {gogc} | {statistics.mean(r['cpu_usec_per_completed_work'] for r in group)/1000:.3f} | {statistics.mean(r['busy_capacity'] for r in group):.2f} | {statistics.mean(r['timely_500_fraction'] for r in group)*100:.2f}% |")
    v=report['cpu_interaction']
    lines+=['',f"CPU period-ratio interaction: {v['mean']*100:.2f}% [{v['lower']*100:.2f}, {v['upper']*100:.2f}].",
        '',f"Original CPU penalty reproduced: {report['original_cpu_penalty_reproduced']}",
        '', 'Read JSON for every block, contrasts, memory peak and CPU-delivery results. No historical root cause or Go defect is established.','']
    (out/'report.md').write_text('\n'.join(lines)); c.seal(out)
    c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=c.digest(out/'seal.json')))
    print(report['decision']+'; report: '+str(out/'report.md'),flush=True)
    return report


def run_probe(session):
    if os.geteuid() == 0: raise ValueError('run as normal user')
    if os.environ.get('QUOTA_GC_EXTERNAL') != '1': raise ValueError('use the external launcher')
    os.sched_setaffinity(0,{0,1})
    with run.acquire_experiment_lock():
        verify_preparation(session); run.require_quiet_host()
        if (session/'environment.json').exists() or (session/'trials').exists():
            raise ValueError('one capped run only; preserve every attempt; no automatic retry')
        try:
            run.old.prepare_environment(session)
            c.save(session/'environment_seal.json',dict(files_sha256={n:c.digest(session/n) for n in ('environment.json','initial-settling.json')}))
            for spec in matrix(): collect(session,session/'trials'/spec['trial'],spec)
            analyze(session)
        except BaseException as e:
            c.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc())); raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify-preparation','run','analyze','status'))
    parser.add_argument('--directory',type=Path,default=DEFAULT)
    args=parser.parse_args(); session=owned_directory(args.directory)
    if args.command=='prepare':
        with run.acquire_experiment_lock(): prepare(session)
    elif args.command=='verify-preparation': verify_preparation(session); print('Preparation verified.')
    elif args.command=='run': run_probe(session)
    elif args.command=='analyze': analyze(session)
    else:
        print(json.dumps(dict(directory=str(session),complete=sum((session/'trials'/s['trial']/'complete.json').exists() for s in matrix()),total=16,interrupted=(session/'interruption.json').exists()),indent=2))


if __name__=='__main__': main()
