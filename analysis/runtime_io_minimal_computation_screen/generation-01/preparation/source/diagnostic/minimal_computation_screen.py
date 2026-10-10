#!/usr/bin/env python3
"""Bounded eight-cell full-service / continuously-busy exact-SHA screen."""
import argparse
import hashlib
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

import runtime_gc_probe as gc
import leftover_observer_audit as audit

c, ROOT, legacy, bridge = gc.c, gc.ROOT, gc.legacy, gc.bridge
PARENT = ROOT/'analysis/runtime_io_minimal_computation_screen'
DEFAULT = PARENT/'generation-01'
BASE = gc.DEFAULT
TOOLCHAIN = ROOT/'analysis/runtime_io_software_audit/audit-01/toolchain'
SOURCE = ROOT/'analysis/runtime_io_v12_parallelism_build/prepared/service/main.go'
NEW_FILES = ('diagnostic/leftover_observer_audit.py', 'diagnostic/minimal_sha.go',
    'diagnostic/minimal_computation_screen.py', 'diagnostic/test_minimal_computation_screen.py',
    'diagnostic/start_minimal_computation_screen.sh', 'docs/runtime_io_minimal_computation_screen.md')
FACTORS = {'A': ('full',100), 'B': ('full',20), 'C': ('minimal',100), 'D': ('minimal',20)}
ORDERS = ('ABCD','DCBA')
MARGIN = .02


def matrix():
    return [dict(trial=f'b{b}_{a}', block=b, arm=a, order=(b-1)*4+i+1,
                 kind=FACTORS[a][0], period_ms=FACTORS[a][1])
            for b,order in zip((1,4),ORDERS) for i,a in enumerate(order)]


def full_spec(spec, functional=False):
    arm = 'A' if spec['period_ms']==100 else 'C'
    if functional:
        return dict(trial=arm,block=0,arm=arm,order=0,period_ms=spec['period_ms'],gogc='100')
    return next(v for v in gc.matrix() if v['block']==spec['block'] and v['arm']==arm)


def minimal_environment(spec, functional=False):
    return dict(MINIMAL_WARMUP_MS='1000' if functional else '20000',
                MINIMAL_MEASURE_MS='2000' if functional else '60000', GOGC='100')


def work_source(text):
    found = re.search(r'func work\(n int\) \[32\]byte \{.*?\n\}',text,re.S)
    if not found: raise ValueError('exact retained work function not found')
    return found.group()


def vector(n=44000):
    state=bytes(range(32))
    for _ in range(n): state=hashlib.sha256(state).digest()
    return state.hex()


def owned_directory(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use a new direct minimal-screen generation')
    return p


def source_hashes():
    retained=gc.source_hashes()
    return dict(retained,**{n:c.digest(ROOT/n) for n in NEW_FILES})


def verify_audit(path, current=True):
    path=Path(path).absolute()
    if path.parent!=ROOT/'analysis/runtime_io_leftover_observer_audit' or path.is_symlink():
        raise ValueError('use a dedicated audit evidence JSON file')
    value=c.read(path)
    if value['uid']!=0 or value['audit_script_sha256']!=c.digest(ROOT/'diagnostic/leftover_observer_audit.py'):
        raise ValueError('complete root audit from this implementation required')
    if audit.assess(value)!=value['assessment'] or not value['assessment']['clear_snapshot']:
        raise ValueError('audit not clear; review findings/missing sections before performance')
    if value['observation_started'] or value['configuration_changed']:
        raise ValueError('audit changed settings or started monitoring')
    if current and value['boot_id']['text']!=c.baseline()['boot_id']:
        raise ValueError('audit boot differs; rerun audit')
    if value['tracefs']['root_controls_before']!=value['tracefs']['root_controls_after']:
        raise ValueError('tracing changed during audit; review before performance')
    return value


def verify_preparation(session,current=True):
    prep=session/'preparation'; c.verify_seal(prep); m=c.read(prep/'manifest.json')
    if (m['matrix']!=matrix() or m['workload']!=c.WORKLOAD or m['signal_margin']!=MARGIN
            or not m['tests_passed'] or not m['functional_passed'] or m['performance_run']):
        raise ValueError('screen preparation/protocol incomplete or changed')
    previous=gc.verify_preparation(BASE,current=current)
    if m['base_preparation_seal']!=c.digest(BASE/'preparation/seal.json'):
        raise ValueError('retained preparation changed')
    for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline'):
        if m[k]!=previous[k]: raise ValueError('retained input differs: '+k)
    for name,key in [('gate','gate_sha256'),('loadgen','loadgen_sha256'),
                     ('original.server','server_sha256'),('minimal.server','minimal_server_sha256')]:
        if c.digest(prep/name)!=m[key]: raise ValueError('prepared executable changed')
    for name,sha in m['sources'].items():
        if c.digest(prep/'source'/name)!=sha or (current and c.digest(ROOT/name)!=sha):
            raise ValueError('source changed: '+name)
    if c.digest(prep/'retained_service_source.go')!=m['retained_service_source_sha256']:
        raise ValueError('retained computation source changed')
    if work_source((prep/'minimal/minimal_sha.go').read_text())!=work_source((prep/'retained_service_source.go').read_text()):
        raise ValueError('control computation differs from retained service')
    if c.read(prep/'arrivals.json')!=c.arrivals() or c.read(prep/'vectors.json')['44000']!=vector():
        raise ValueError('arrivals or independent digest changed')
    for kind in ('full','minimal'):
        for period in (100,20):
            p=prep/'functional'/f'{kind}{period}'
            if replay(p,session,True)!=c.read(p/'screen_derived.json'):
                raise ValueError('functional replay differs')
    if current and (m['sources']!=source_hashes() or m['baseline']!=c.baseline()):
        raise ValueError('source/kernel/boot/topology changed; prepare a new generation')
    return m


class MinimalService(gc.Service):
    def __init__(self,session,config,directory,spec,functional=False):
        super().__init__(session,config,directory)
        m=self.manifest
        self.manifest=dict(m,image=m['minimal_image'],server_sha256=m['minimal_server_sha256'])
        self.spec,self.functional=spec,functional
        self.resources=[]

    def create(self):
        original=c.service_argv
        def argv(*args):
            result=original(*args)
            extra=[]
            for k,v in minimal_environment(self.spec,self.functional).items(): extra+=['-e',k+'='+v]
            result[result.index('-p'):result.index('-p')]=extra
            return result
        with patch.object(c,'service_argv',argv): value=super().create()
        for name in ('measure','exit'): os.mkfifo(self.directory/'qualification'/f'{name}.fifo',0o600)
        env=c.read(self.directory/'container.json')['inspect']['Config']['Env']
        expected=['GOMAXPROCS=1','WORKERS=1','QUEUE_SIZE=128','INSTRUMENT=1','WORKER_YIELD=0',
            'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
        expected += [k+'='+v for k,v in minimal_environment(self.spec,self.functional).items()]
        if sorted(env)!=sorted(expected): raise ValueError('minimal environment differs')
        return value

    def release(self):
        self.guard(); bridge.release_fifo(self.directory/'qualification/start.fifo')

    def records(self):
        self.guard()
        p=subprocess.run(['docker','logs',self.container],capture_output=True,text=True,timeout=10)
        if p.returncode or p.stderr: raise ValueError('minimal program failed: '+p.stderr)
        rows=[]
        for line in p.stdout.splitlines():
            value=json.loads(line)
            # Startup gate prints its own ready record before exec.
            if value['event']!='ready': rows.append(value)
        if any(r['event'] not in ('started','warmup_done','measurement_done') for r in rows):
            raise ValueError('unexpected minimal protocol event')
        return rows

    def observe(self):
        value=super().observe()
        value['memory_peak_bytes']=int((self.group/'memory.peak').read_text())
        if value['memory_peak_bytes']>gc.MEMORY_GUARD_BYTES: raise MemoryError('memory guard crossed')
        self.resources.append(value)
        return value


def progress(session,spec,stage):
    if spec['block']==0: return
    c.save(session/'progress.json',dict(**spec,stage=stage,total=8,updated=time.time()))
    print(f"{spec['order']}/8 {spec['trial']} {spec['kind']} {spec['period_ms']} ms: {stage}",flush=True)


def collect_minimal(session,directory,spec,functional=False):
    directory.mkdir(parents=True)
    c.save(directory/'screen_config.json',spec)
    config=gc.legacy_config(full_spec(spec,functional),functional)
    c.save(directory/'config.json',config)
    service=MinimalService(session,config,directory,spec,functional)
    monitor=log=None; failure=None
    try:
        if not functional:
            gc.run.require_quiet_host(); env=c.read(session/'environment.json')
            c.save(directory/'environment.json',env); progress(session,spec,'settling')
            gc.run.old.settle(directory/'settling.json',env['baseline_c'],expected_power=env['power_settings'])
        service.create()
        if not functional:
            log=(directory/'monitor.log').open('x')
            monitor=subprocess.Popen([sys.executable,str(ROOT/'scripts/monitor_host.py'),
                '--cgroup-path',str(service.group).removeprefix('/sys/fs/cgroup'),
                '--output',str(directory/'monitor.json')],stdout=log,stderr=subprocess.STDOUT,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        observations={'startup':service.observe()}; service.release()
        envs=minimal_environment(spec,functional)
        until=time.monotonic()+int(envs['MINIMAL_WARMUP_MS'])/1000+20
        progress(session,spec,'warmup')
        while True:
            records=service.records(); service.observe()
            if any(r['event']=='warmup_done' for r in records): break
            if time.monotonic()>until: raise TimeoutError('minimal warmup timeout')
            time.sleep(1)
        observations['measurement_start']=service.observe()
        bridge.release_fifo(directory/'qualification/measure.fifo')
        progress(session,spec,'measurement')
        until=time.monotonic()+int(envs['MINIMAL_MEASURE_MS'])/1000+20
        while True:
            service.observe(); records=service.records()
            if any(r['event']=='measurement_done' for r in records): break
            if time.monotonic()>until: raise TimeoutError('minimal measurement timeout')
            time.sleep(1)
        observations['measurement_stop']=service.observe()
        c.save(directory/'native_records.json',records)
        c.save(directory/'observations.json',observations)
        c.save(directory/'resource_samples.json',service.resources)
        if not functional and gc.power_settings(include_profile=True)!=env['power_settings']:
            raise ValueError('power configuration changed')
        if monitor:
            legacy.fixtures.stop(monitor,signal.SIGINT)
            if monitor.returncode: raise ValueError('host monitor failed')
            log.close(); monitor=None
        service.close(); c.seal(directory)
        result=replay(directory,session,functional)
        c.save(directory/'screen_derived.json',result)
        c.save(directory/'complete.json',dict(valid=True,performance_run=not functional))
        c.seal(directory)
    except BaseException as e:
        failure=str(e); c.save(directory/'failure.json',dict(error=failure,traceback=traceback.format_exc())); raise
    finally:
        if monitor: legacy.fixtures.stop(monitor,signal.SIGINT); log.close()
        try: service.close(failure)
        finally:
            if failure: c.seal(directory)


def collect_full(session,directory,spec,functional=False):
    def update(_session,_spec,stage): progress(session,spec,stage)
    with patch.object(gc,'progress',update): gc.collect(session,directory,full_spec(spec,functional),functional)
    c.save(directory/'screen_config.json',spec); c.seal(directory)
    c.save(directory/'screen_derived.json',replay(directory,session,functional)); c.seal(directory)


def minimal_summary(records,observations,expected_digest,functional=False):
    if [r['event'] for r in records]!=['started','warmup_done','measurement_done']:
        raise ValueError('incomplete/duplicate minimal events')
    for row in records:
        if row['go_version']!='go1.26.1' or row['gomaxprocs']!=1: raise ValueError('runtime differs')
    for r in records[1:]:
        if r['iterations']!=44000 or r['digest']!=expected_digest or type(r['jobs'])!=int or r['jobs']<=0:
            raise ValueError('minimal work conservation/digest failed')
        wall=(r['stop_monotonic_ns']-r['start_monotonic_ns'])/1e9
        cpu=(r['cpu_stop_ns']-r['cpu_start_ns'])/1e9
        if not r['duration_ms']/1000<=wall<=r['duration_ms']/1000+.5 or not 0<cpu<=wall*1.05:
            raise ValueError('native time/cost bounds invalid')
    r=records[-1]; a,b=(observations[k] for k in ('measurement_start','measurement_stop'))
    if not a['after_ns']<=r['start_monotonic_ns']<=r['stop_monotonic_ns']<=b['before_ns']:
        raise ValueError('native measurement not contained in cgroup boundary observations')
    cost=b['cpu_stat']['usage_usec']-a['cpu_stat']['usage_usec']
    native=(r['cpu_stop_ns']-r['cpu_start_ns'])/1000
    agreement=cost/native-1
    if cost<=0 or abs(agreement)>(.05 if functional else .01):
        raise ValueError('cgroup/process CPU alignment exceeds declared margin')
    wall=(r['stop_monotonic_ns']-r['start_monotonic_ns'])/1e9
    return dict(cpu_usec_per_completed_work=cost/r['jobs'],native_cpu_usec_per_job=native/r['jobs'],
                capacity=r['jobs']/wall,cpu_cores=cost/1e6/wall,completed=r['jobs'],
                cgroup_native_cpu_relative_difference=agreement,wall_sec=wall)


def replay(directory,session,functional=False):
    c.verify_seal(directory)
    if any((directory/n).exists() for n in ('failure.json','cleanup_failure.json','watchdog_cleanup.json')):
        raise ValueError('failed/interrupted trial rejected')
    spec=c.read(directory/'screen_config.json')
    if not functional and spec not in matrix(): raise ValueError('trial outside frozen matrix')
    m=c.read(session/'preparation/manifest.json')
    if spec['kind']=='full':
        result=gc.replay(directory,functional)
        if c.read(directory/'runtime_config.json')!=full_spec(spec,functional): raise ValueError('full spec mismatch')
        row=result['summary']
        summary=dict(spec, cpu_usec_per_completed_work=row['cpu_usec_per_completed_work'],
            capacity=row.get('busy_capacity'),cpu_cores=row.get('busy_cpu_cores'),
            completed=row['completed_computations'],timely_500_fraction=row['timely_500_fraction'],
            failure_fraction=row['failure_fraction'],memory_peak_bytes=row['memory_peak_bytes'])
        return dict(summary=summary, full=result)
    if spec['kind']!='minimal': raise ValueError('unknown computation mode')
    config=gc.legacy_config(full_spec(spec,functional),functional)
    if c.read(directory/'config.json')!=config: raise ValueError('minimal limits config differs')
    container=c.read(directory/'container.json')['inspect']; initial=c.read(directory/'initial.json')
    c.validate_resources(initial['initial_limits'],container['HostConfig'],m['resource_baseline'],config)
    if (container['Image']!=m['minimal_image'] or
            initial['container_server_sha256']!=m['minimal_server_sha256'] or
            c.digest(directory/'container.server')!=m['minimal_server_sha256']):
        raise ValueError('actual minimal executable differs')
    expected=['GOMAXPROCS=1','WORKERS=1','QUEUE_SIZE=128','INSTRUMENT=1','WORKER_YIELD=0',
              'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
    expected += [k+'='+v for k,v in minimal_environment(spec,functional).items()]
    if sorted(container['Config']['Env'])!=sorted(expected): raise ValueError('minimal environment mismatch')
    rows=c.read(directory/'native_records.json')
    logged=[json.loads(s) for s in (directory/'container.stdout').read_text().splitlines()]
    if [r for r in logged if r['event']!='ready']!=rows or (directory/'container.stderr').read_text():
        raise ValueError('native events differ from actual container output')
    expected_durations=[1000,2000] if functional else [20000,60000]
    if [r['duration_ms'] for r in rows[1:]]!=expected_durations: raise ValueError('duration differs')
    summary=minimal_summary(rows,c.read(directory/'observations.json'),c.read(session/'preparation/vectors.json')['44000'],functional)
    cleanup=c.read(directory/'cleanup.json')
    if (cleanup['errors'] or not cleanup['container_removed'] or not cleanup['cgroup_removed']
            or cleanup['tracing_used'] or cleanup['watchdog_intervened']): raise ValueError('cleanup not verified')
    resources=c.read(directory/'resource_samples.json')
    peak=max(r['memory_peak_bytes'] for r in resources)
    if peak>gc.MEMORY_GUARD_BYTES: raise ValueError('memory guard exceeded')
    if not functional:
        gc.verify_environment(session)
        if c.read(directory/'environment.json')!=c.read(session/'environment.json'):
            raise ValueError('environment provenance differs')
    return dict(summary=dict(spec,**summary,memory_peak_bytes=peak), native_records=rows)


def compare(rows):
    if len(rows)!=8 or {r['trial'] for r in rows}!={r['trial'] for r in matrix()}:
        raise ValueError('all eight unique cells required')
    table={r['trial']:r for r in rows}; costs={}; capacities={}; delivery={}
    for kind,arms in [('full',('A','B')),('minimal',('C','D'))]:
        for field,output in [('cpu_usec_per_completed_work',costs),('capacity',capacities),('cpu_cores',delivery)]:
            effects=[]
            for block in (1,4):
                x,y=(table[f'b{block}_{a}'][field] for a in arms)
                if x is None or y is None or not math.isfinite(x+y) or min(x,y)<=0:
                    raise ValueError('positive finite cost/capacity/delivery required')
                effects.append(y/x-1)
            output[kind]=effects
    def substantial(v): return all(x>=MARGIN for x in v) or all(x<=-MARGIN for x in v)
    signals={k:substantial(v) for k,v in costs.items()}
    same_direction=all(costs['full'][i]*costs['minimal'][i]>0 for i in range(2))
    if signals['full'] and signals['minimal'] and same_direction:
        decision='period_cost_signal_also_present_in_minimal_control'
    elif signals['full']:
        decision='full_service_period_signal_not_matched_by_minimal_control'
    elif signals['minimal']:
        decision='minimal_control_signal_without_matching_full_service_signal'
    else: decision='bounded_screen_did_not_narrow_cause'
    return dict(decision=decision,block_cpu_changes=costs,block_capacity_changes=capacities,
        block_cpu_delivery_changes=delivery,signal_margin=MARGIN,large_consistent_signals=signals,
        original_full_penalty_seen_in_both_blocks=all(x>=MARGIN for x in costs['full']),
        substantial_rejection_work=any(r.get('failure_fraction',0)>0 for r in rows),
        historical_cause_established=False,novelty_established=False,automatic_followup_authorized=False,
        limitation='Two opposite-order blocks are a screen, not equivalence or causal proof. '
            'Minimal work is continuously backlogged; the full service receives the retained burst arrivals. '
            'The control differs in workload shape, runtime/HTTP work and power behavior. '
            'A negative control cannot exclude burst-specific execution effects. '
            'Do not extend automatically. If no useful narrowing, retain both historical outcomes with cause unknown.')


def analyze(session):
    verify_preparation(session,current=False); rows=[]
    for spec in matrix():
        p=session/'trials'/spec['trial']
        complete=c.read(p/'complete.json')
        if complete.get('valid') is not True or complete.get('performance_run') is not True:
            raise ValueError('incomplete cell')
        result=replay(p,session)
        if result!=c.read(p/'screen_derived.json'): raise ValueError('raw replay differs')
        rows.append(result['summary'])
    report=compare(rows)
    report.update(rows=rows,preparation_seal=c.digest(session/'preparation/seal.json'),
        audit_sha256=c.digest(session/'audit.json'),
        trial_seals={s['trial']:c.digest(session/'trials'/s['trial']/'seal.json') for s in matrix()})
    out=session/'analysis'/str(time.time_ns()); out.mkdir(parents=True)
    c.save(out/'report.json',report)
    lines=['# Bounded minimal-computation comparison','',report['decision'],'',report['limitation'],'',
        '| Kind | Period | CPU/job ms | Capacity jobs/s | CPU delivered |','|---|---:|---:|---:|---:|']
    for kind in ('full','minimal'):
        for period in (100,20):
            group=[r for r in rows if r['kind']==kind and r['period_ms']==period]
            lines.append(f"| {kind} | {period} | {statistics.mean(r['cpu_usec_per_completed_work'] for r in group)/1000:.3f} | {statistics.mean(r['capacity'] for r in group):.2f} | {statistics.mean(r['cpu_cores'] for r in group):.4f} |")
    lines+=['','20-versus-100 CPU/job changes by block:']
    for k,v in report['block_cpu_changes'].items(): lines.append(f"- {k}: "+', '.join(f'{x*100:+.2f}%' for x in v))
    lines+=['','If this screen does not narrow the cause, stop this branch and retain both earlier outcomes. '
            'Cite latency-smoothing and throughput-loss prior work as context, not proof of either mechanism.','']
    (out/'report.md').write_text('\n'.join(lines)); c.seal(out)
    c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session))))
    print(report['decision']+'; report: '+str(out/'report.md'),flush=True)


def prepare(session):
    if os.geteuid()==0 or session.exists(): raise ValueError('prepare as normal user into a new generation')
    base=gc.verify_preparation(BASE); sources=source_hashes()
    if work_source((ROOT/'diagnostic/minimal_sha.go').read_text())!=work_source(SOURCE.read_text()):
        raise ValueError('SHA function differs')
    PARENT.mkdir(parents=True,exist_ok=True); c.capacity(PARENT)
    prep=session/'preparation'; prep.mkdir(parents=True)
    try:
        for name in sources:
            p=prep/'source'/name; p.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/name,p)
        for name in ('gate','loadgen','original.server'): shutil.copy2(BASE/'preparation'/name,prep/name)
        shutil.copy2(SOURCE,prep/'retained_service_source.go')
        build=prep/'minimal'; build.mkdir(); shutil.copy2(ROOT/'diagnostic/minimal_sha.go',build/'minimal_sha.go')
        (build/'go.mod').write_text('module minimal-sha-control\n\ngo 1.24\n')
        vectors={str(n):vector(n) for n in (1,10,44000)}; c.save(prep/'vectors.json',vectors)
        (build/'minimal_sha_test.go').write_text('package main\nimport("encoding/hex";"testing")\nfunc TestIndependentDigests(t *testing.T){\n'+
            ''.join(f'{{v:=work({n});if hex.EncodeToString(v[:])!="{v}"{{t.Fatal("digest {n}")}}}}\n' for n,v in vectors.items())+'}\n')
        env=dict(os.environ,GOROOT=str(TOOLCHAIN),GOCACHE=str(prep/'gocache'),GOPATH=str(prep/'gopath'),
            GOPROXY='off',GOSUMDB='off',GOTOOLCHAIN='local',GOENV='off',CGO_ENABLED='0',GOOS='linux',
            GOARCH='amd64',GOAMD64='v1',GOMAXPROCS='2',GOFLAGS='')
        receipts=[]
        for label,argv in [('version',[str(TOOLCHAIN/'bin/go'),'version']),
            ('go_tests',[str(TOOLCHAIN/'bin/go'),'test','-count=1','-v','./...']),
            ('go_build',[str(TOOLCHAIN/'bin/go'),'build','-trimpath','-o',str(prep/'minimal.server'),'.']),
            ('python_tests',[sys.executable,'-m','unittest','discover','-s',str(ROOT/'diagnostic'),'-p','test_minimal_computation_screen.py','-v'])]:
            r=subprocess.run(argv,cwd=build,env=env,capture_output=True,text=True,timeout=240,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            (prep/(label+'.stdout')).write_text(r.stdout); (prep/(label+'.stderr')).write_text(r.stderr)
            receipts.append(dict(label=label,argv=argv,returncode=r.returncode))
            if r.returncode or (label=='version' and r.stdout.strip()!='go version go1.26.1 linux/amd64'):
                raise ValueError('build/qualification failed: '+label)
        context=prep/'image_context'; context.mkdir(); shutil.copy2(prep/'minimal.server',context/'server')
        (context/'Dockerfile').write_text(f"FROM {base['image']}\nCOPY server /server\n")
        iid=prep/'minimal_image_id'
        argv=['docker','build','--network=none','--pull=false','--iidfile',str(iid),str(context)]
        r=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (prep/'docker_build.stdout').write_text(r.stdout); (prep/'docker_build.stderr').write_text(r.stderr)
        if r.returncode: raise ValueError('offline derived image build failed')
        image=iid.read_text().strip()
        m=dict(matrix=matrix(),workload=c.WORKLOAD,sources=sources,baseline=c.baseline(),prepared=time.time(),
            signal_margin=MARGIN,tests_passed=True,functional_passed=False,performance_run=False,
            base_preparation_seal=c.digest(BASE/'preparation/seal.json'),
            compiler_go_sha256=c.digest(TOOLCHAIN/'bin/go'),build_receipts=receipts,
            minimal_image=image,minimal_server_sha256=c.digest(prep/'minimal.server'),
            minimal_work_sha256=hashlib.sha256(work_source(SOURCE.read_text()).encode()).hexdigest(),
            retained_service_source_sha256=c.digest(SOURCE),
            **{k:base[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline')})
        c.save(prep/'manifest.json',m); c.save(prep/'arrivals.json',c.arrivals())
        for kind in ('full','minimal'):
            for period in (100,20):
                spec=dict(trial=f'{kind}{period}',block=0,arm='A' if kind=='full' else 'C',order=0,kind=kind,period_ms=period)
                p=prep/'functional'/spec['trial']
                (collect_full if kind=='full' else collect_minimal)(session,p,spec,True)
        m['functional_passed']=True; c.save(prep/'manifest.json',m)
        if source_hashes()!=sources: raise ValueError('sources changed during preparation')
        c.seal(prep); verify_preparation(session)
        print('Prepared and verified: '+str(session)+'; eight performance cells unrun.',flush=True)
    except BaseException as e:
        c.save(prep/'preparation_failure.json',dict(error=str(e),traceback=traceback.format_exc())); c.seal(prep); raise


def run_screen(session,audit_path):
    if os.geteuid()==0 or os.environ.get('QUOTA_MINIMAL_EXTERNAL')!='1': raise ValueError('use normal-user external launcher')
    os.sched_setaffinity(0,{0,1})
    with gc.run.acquire_experiment_lock():
        verify_preparation(session); gc.run.require_quiet_host(); verify_audit(audit_path)
        if (session/'environment.json').exists() or (session/'trials').exists(): raise ValueError('one run only; preserve every attempt')
        shutil.copy2(audit_path,session/'audit.json')
        previous=signal.getsignal(signal.SIGALRM)
        def deadline(_signum,_frame): raise TimeoutError('45-minute whole-screen ceiling reached; retain partial evidence')
        signal.signal(signal.SIGALRM,deadline); signal.alarm(2700)
        try:
            gc.run.old.prepare_environment(session)
            c.save(session/'environment_seal.json',dict(files_sha256={n:c.digest(session/n) for n in ('environment.json','initial-settling.json')}))
            for spec in matrix():
                verify_preparation(session)
                (collect_full if spec['kind']=='full' else collect_minimal)(session,session/'trials'/spec['trial'],spec)
            analyze(session)
        except BaseException as e:
            c.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc())); raise
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM,previous)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('prepare','verify-preparation','verify-audit','run','analyze'))
    p.add_argument('--directory',type=Path,default=DEFAULT)
    p.add_argument('--audit',type=Path)
    a=p.parse_args(); session=owned_directory(a.directory)
    if a.command=='prepare':
        with gc.run.acquire_experiment_lock(): prepare(session)
    elif a.command=='verify-preparation': verify_preparation(session); print('Preparation verified.')
    elif a.command=='verify-audit': verify_audit(a.audit); print('Observer audit clear.')
    elif a.command=='run': run_screen(session,a.audit)
    else: analyze(session)


if __name__=='__main__': main()
