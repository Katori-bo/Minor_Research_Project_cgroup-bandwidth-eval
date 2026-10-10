#!/usr/bin/env python3
"""Bounded V18 two-CPU/service compatibility gate; not the performance pilot."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import uuid

import build_repeatability
import kernel_bridge_analysis as analysis
import kernel_fixtures as fixtures
import kernel_tools
import repeatability_analysis

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = ROOT / 'analysis/runtime_io_v18_service_bridge_assets'
OUTPUT_PARENT = ROOT / 'analysis/runtime_io_v18_service_bridge'
PROTOCOL = ROOT / 'docs/runtime_io_v18_service_bridge.md'
EXTRAS = ('kernel_service_bridge.py', 'kernel_start_gate.c', 'kernel_bridge.bt',
          'kernel_bridge_analysis.py', 'kernel_fixtures.py', 'kernel_fixture_analysis.py',
          'kernel_tools.py', 'start_kernel_service_bridge.sh', 'test_kernel_bridge.py')


def save(path, value): fixtures.save(path, value)


def capture(argv, timeout=15):
    return subprocess.check_output(argv, text=True, stderr=subprocess.PIPE, timeout=timeout).strip()


def sources():
    paths = set(build_repeatability.dependencies()) | {HERE/n for n in EXTRAS} | {PROTOCOL}
    for module in list(sys.modules.values()):
        location=getattr(module,'__file__',None)
        if location:
            path=Path(location).resolve()
            if ROOT in path.parents and path.suffix=='.py': paths.add(path)
    return {str(p.relative_to(ROOT)): kernel_tools.digest(p) for p in sorted(paths)}


def verify_assets():
    seal = json.loads((ASSETS/'seal.json').read_text())['files_sha256']
    actual = {str(p.relative_to(ASSETS)):kernel_tools.digest(p) for p in ASSETS.rglob('*')
              if p.is_file() and p != ASSETS/'seal.json'}
    if actual != seal: raise ValueError('service bridge assets seal mismatch')
    value = json.loads((ASSETS/'manifest.json').read_text())
    if sources() != value['sources']: raise ValueError('service bridge implementation changed; prepare new assets')
    return value


def prepare():
    if os.geteuid()==0: raise ValueError('prepare as the normal user')
    if ASSETS.exists(): raise ValueError('preserve existing bridge assets; use --verify')
    base = build_repeatability.DEFAULT
    seal = json.loads((base/'verification.json').read_text())
    if not seal['passed']: raise ValueError('retained baseline build not verified')
    for name, expected in seal['files_sha256'].items():
        if kernel_tools.digest(base/name) != expected: raise ValueError('retained build seal mismatch: '+name)
    build = json.loads((base/'build.json').read_text())
    audit = json.loads((base/'binary_audit/audit.json').read_text())['records']['legacy']
    if audit['image'] != build['images']['legacy_a'] or audit['binary_sha256'] != kernel_tools.digest(base/'binary_audit/legacy.server'):
        raise ValueError('retained original image/binary mismatch')
    initial = sources()
    ASSETS.mkdir()
    shutil.copy2(base/'loadgen', ASSETS/'loadgen')
    command = ['/usr/bin/cc','-O2','-static','-Wall','-Wextra','-Werror',str(HERE/'kernel_start_gate.c'),'-o',str(ASSETS/'gate')]
    p = subprocess.run(command, capture_output=True, text=True, timeout=30)
    save(ASSETS/'compile.json',dict(argv=command,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
    if p.returncode or p.stderr.strip(): raise ValueError('static gate compilation failed')
    elf = capture(['readelf','-l',str(ASSETS/'gate')])
    (ASSETS/'gate.elf.txt').write_text(elf+'\n')
    if 'INTERP' in elf: raise ValueError('gate is not static')
    for name in ('legacy.server','loadgen'):
        binary = base/'binary_audit/legacy.server' if name=='legacy.server' else base/'loadgen'
        asm = capture(['objdump','-d','--disassemble=runtime.nanotime1.abi0',str(binary)])
        (ASSETS/(name+'.nanotime.asm')).write_text(asm+'\n')
        if 'runtime.vdsoClockgettimeSym' not in asm or '$0x1,%edi' not in asm or '$0xe4,%rax' not in asm:
            raise ValueError('retained Go monotonic clock implementation requires review')
        now=capture(['objdump','-d','--disassemble=time.now',str(binary)])
        (ASSETS/(name+'.time_now.asm')).write_text(now+'\n')
        if 'runtime.vdsoClockgettimeSym' not in now or '$0x1,%edi' not in now or '$0xe4,%rax' not in now:
            raise ValueError('retained time.Now monotonic implementation requires review')
    # Functional test of the actual static start barrier, fork and fixed CPU work.
    with (ASSETS/'gate_test.jsonl').open('x') as log:
        worker = subprocess.Popen([str(ASSETS/'gate'),'--fixture'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                                  preexec_fn=lambda:os.sched_setaffinity(0,{2,4}))
        try:
            stopped(worker.pid)
            os.kill(worker.pid,signal.SIGCONT)
            worker.wait(timeout=6)
            if worker.returncode: raise ValueError('unquotaed gate fixture failed')
        finally:
            stop_known(worker)
    events = [json.loads(l) for l in (ASSETS/'gate_test.jsonl').read_text().splitlines()]
    if [e['event'] for e in events].count('ready')!=1 or [e['event'] for e in events].count('done')!=1:
        raise ValueError('gate fixture lifecycle failed')
    if {e['cpu'] for e in events if e['event']=='child_end'}!={2,4}:
        raise ValueError('gate CPU pinning failed')
    if sources()!=initial: raise ValueError('source changed during preparation')
    save(ASSETS/'manifest.json',dict(sources=initial,image=audit['image'],server_sha256=audit['binary_sha256'],
        loadgen_sha256=build['loadgen_sha256'],baseline_seal_sha256=kernel_tools.digest(base/'verification.json'),
        gate_sha256=kernel_tools.digest(ASSETS/'gate'),kernel=platform.release(),performance_run=False,
        root_capture_verified=False,clock_id=1,clock='CLOCK_MONOTONIC'))
    save(ASSETS/'seal.json',dict(files_sha256={str(p.relative_to(ASSETS)):kernel_tools.digest(p)
        for p in ASSETS.rglob('*') if p.is_file()}))
    verify_assets()
    print('Bridge assets prepared; root capture and observer cost remain unqualified.',flush=True)


def preflight():
    """Exercise static scratch-image startup and clock joins without attaching probes."""
    if os.geteuid()==0: raise ValueError('preflight as the normal user')
    value=verify_assets()
    output=ROOT/'analysis/runtime_io_v18_service_bridge_preflight'/time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
    output.mkdir(parents=True,exist_ok=False);results=[];failure=None
    try:
        for g,capped in ((1,False),(2,False),(1,True),(2,True)):
            name=f'g{g}_'+('quota' if capped else 'uncapped');d=output/name;d.mkdir()
            container=None
            try:
                qualification=d/'qualification';qualification.mkdir()
                shutil.copy2(ASSETS/'gate',qualification/'gate');os.mkfifo(qualification/'start.fifo',0o600)
                argv=['docker','create','--name','quota-v18-preflight-'+uuid.uuid4().hex,
                    '--cpuset-cpus','2,4','--cpu-period','100000','--cpu-quota','50000' if capped else '-1',
                    '--pids-limit','128','--memory','256m','--mount',f'type=bind,src={qualification},dst=/qualification,readonly',
                    '--entrypoint','/qualification/gate','-e',f'GOMAXPROCS={g}','-e','WORKERS=4','-e','INSTRUMENT=1',
                    '-p','127.0.0.1::8080',value['image'],'--server']
                container=capture(argv);capture(['docker','start',container])
                inspect=json.loads(capture(['docker','inspect',container]))[0];pid=inspect['State']['Pid']
                save(d/'container.json',dict(argv=argv,inspect=inspect))
                stopped(pid, state='S')
                release_fifo(qualification/'start.fifo')
                port=capture(['docker','port',container,'8080/tcp']).rsplit(':',1)[1];base=f'http://127.0.0.1:{port}'
                until=time.monotonic()+8
                while True:
                    try:health=get(base,'health');break
                    except OSError:
                        if time.monotonic()>until: raise ValueError('preflight health timeout')
                        time.sleep(.05)
                if health['gomaxprocs']!=g or health['workers']!=4 or health['queue_cap']!=128 or not health['instrument']:
                    raise ValueError('functional runtime parameters differ')
                clock_samples=anchors(base,'start')
                with (d/'client.log').open('x') as log:
                    subprocess.run([str(ASSETS/'loadgen'),'-url',base+'/work?iterations=44000','-duration','2s',
                        '-rate','113.21','-pattern','steady','-concurrency','64','-timeout','5s','-trace-client=true',
                        '-output',str(d/'loadgen.json')],stdout=log,stderr=subprocess.STDOUT,timeout=15,check=True,
                        preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
                until=time.monotonic()+8
                while True:
                    server=get(base,'metrics')
                    if not server['active_handlers'] and not server['queue_len'] and server['admitted']==server['completed']: break
                    if time.monotonic()>until: raise ValueError('preflight drain timeout')
                    time.sleep(.05)
                save(d/'server_metrics.json',server)
                result=repeatability_analysis.classify(json.loads((d/'loadgen.json').read_text()),server,'legacy_a')
                if result['offered']!=227 or result['missing_entry_count']: raise ValueError('functional request conservation failed')
                clock_samples+=anchors(base,'stop');joined=analysis.clock_join(clock_samples,result['mapping'],server['clock_generation'])
                save(d/'kernel_server_anchors.json',clock_samples);save(d/'clock_mapping.json',joined)
                save(d/'request_classification.json',result)
                results.append(dict(case=name,offered=result['offered'],clock_uncertainty_ns=joined['uncertainty_ns']))
                print('HTTP preflight passed:',name,flush=True)
            finally:
                if container:
                    try:
                        logs=subprocess.run(['docker','logs',container],capture_output=True,text=True,timeout=10)
                        (d/'container.stdout').write_text(logs.stdout);(d/'container.stderr').write_text(logs.stderr)
                    finally: capture(['docker','rm','-f',container])
        verify_assets()
    except BaseException as e:
        failure=str(e);raise
    finally:
        save(output/'summary.json',dict(passed=failure is None and len(results)==4,error=failure,cases=results,
            assets_seal_sha256=kernel_tools.digest(ASSETS/'seal.json'),root_capture_verified=False,
            observer_cost_qualified=False,performance_run=False))
        save(output/'seal.json',dict(files_sha256={str(p.relative_to(output)):kernel_tools.digest(p)
            for p in output.rglob('*') if p.is_file()}))
    print(output/'summary.json',flush=True)


def stopped(pid, state='T'):
    until = time.monotonic()+8
    while time.monotonic()<until:
        tasks = list(Path(f'/proc/{pid}/task').iterdir())
        if len(tasks)==1 and tasks[0].name==str(pid) and Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1][0]==state:
            return
        time.sleep(.02)
    raise ValueError('single-thread startup gate did not stop')


def release_fifo(path):
    # Nonblocking open fails if the frozen gate has not reached its reader.
    fd=os.open(path,os.O_WRONLY|os.O_NONBLOCK)
    try:
        if os.write(fd,b'G')!=1: raise ValueError('startup handshake write failed')
    finally: os.close(fd)


def stop_known(worker):
    if worker is None: return
    # The known worker owns a new session/process group, including its children.
    try: os.killpg(worker.pid,signal.SIGKILL)
    except ProcessLookupError: pass
    worker.wait(timeout=3)


def cgroup(pid):
    lines = Path(f'/proc/{pid}/cgroup').read_text().splitlines()
    if len(lines)!=1 or not lines[0].startswith('0::/'): raise ValueError('unified cgroup identity missing')
    return fixtures.CGROOT/lines[0][4:]


def ancestors(group):
    result = []
    p = group.parent
    while p==fixtures.CGROOT or fixtures.CGROOT in p.parents:
        if (p/'cpu.max').exists():
            limit = (p/'cpu.max').read_text().strip()
            if limit.split()[0]!='max': raise ValueError('capped ancestor: '+str(p))
            result.append(dict(path=str(p),cpu_max=limit))
        elif p!=fixtures.CGROOT: raise ValueError('ancestor CPU limit unavailable')
        if p==fixtures.CGROOT: break
        p = p.parent
    return result


def snapshot(pid, expected_group):
    before = time.monotonic_ns()
    observed=[]; vanished=[]
    tids = sorted(int(p.name) for p in Path(f'/proc/{pid}/task').iterdir())
    for tid in tids:
        try:
            if cgroup(tid)!=expected_group or os.sched_getaffinity(tid)!={2,4}:
                raise ValueError('live service thread changed cgroup/CPU affinity')
            observed.append(tid)
        except (FileNotFoundError,ProcessLookupError): vanished.append(tid)
    return dict(before_ns=before,after_ns=time.monotonic_ns(),tids=observed,
                vanished_during_enumeration=vanished,cgroup=str(expected_group),affinity=[2,4])


def namespaces(pid):
    value = {}
    for label, target in (('host', 'self'),('service',str(pid))):
        rows = Path(f'/proc/{target}/timens_offsets').read_text().splitlines()
        value[label] = {parts[0]:[int(parts[1]),int(parts[2])] for parts in map(str.split,rows)}
        if value[label] != {'monotonic':[0,0],'boottime':[0,0]}:
            raise ValueError('shifted time namespace')
    return value


def get(base, endpoint):
    with urllib.request.urlopen(base+'/'+endpoint,timeout=3) as response: return json.load(response)


def anchors(base, phase):
    values = []
    for i in range(3):
        before=time.monotonic_ns(); value=get(base,'clock'); after=time.monotonic_ns()
        values.append(dict(label=f'{phase}_{i}',before_ns=before,after_ns=after,**value))
    return values


def run_case(directory, assets, known=False, g=1, capped=True):
    directory.mkdir(); group=None; container=None; worker=observer=None; handles=[]; owned=set()
    metadata={}; failure=None; created=False
    try:
        if known:
            group=fixtures.CGROOT/('quota-v18-bridge-'+uuid.uuid4().hex);group.mkdir();created=True
            for name,value in {'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus':'2,4',
                               'pids.max':'32','memory.max':str(256*1024**2)}.items():
                (group/name).write_text(value)
            log=(directory/'worker.jsonl').open('x');handles.append(log)
            worker=subprocess.Popen([str(assets/'gate'),'--fixture'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                preexec_fn=lambda:os.sched_setaffinity(0,{2,4}))
            stopped(worker.pid);pid=worker.pid
            (group/'cgroup.procs').write_text(str(pid))
        else:
            qualification=directory/'qualification';qualification.mkdir()
            shutil.copy2(assets/'gate',qualification/'gate');os.mkfifo(qualification/'start.fifo',0o600)
            argv=['docker','create','--name','quota-v18-bridge-'+uuid.uuid4().hex,
                '--cpuset-cpus','2,4','--cpu-period','100000','--cpu-quota','50000' if capped else '-1',
                '--pids-limit','128','--memory','256m',
                '--mount',f'type=bind,src={qualification},dst=/qualification,readonly',
                '--entrypoint','/qualification/gate','-e',f'GOMAXPROCS={g}','-e','WORKERS=4',
                '-e','INSTRUMENT=1','-p','127.0.0.1::8080',json.loads((assets/'manifest.json').read_text())['image'],'--server']
            container=capture(argv);capture(['docker','start',container])
            inspect=json.loads(capture(['docker','inspect',container]))[0]
            save(directory/'container.json',dict(argv=argv,inspect=inspect))
            pid=inspect['State']['Pid'];stopped(pid,state='S');group=cgroup(pid)
        if cgroup(pid)!=group or os.sched_getaffinity(pid)!={2,4} or (group/'cgroup.procs').read_text().split()!=[str(pid)]:
            raise ValueError('initial cgroup/affinity mismatch')
        limits={n:(group/n).read_text().strip() for n in ('cpu.max','cpu.max.burst','cpuset.cpus.effective','memory.max','pids.max')}
        if limits['cpu.max']!=('50000 100000' if capped else 'max 100000') or limits['cpu.max.burst']!='0' or limits['cpuset.cpus.effective']!='2,4':
            raise ValueError('actual CPU limits differ')
        before=fixtures.stat(group)
        if before.get('nr_throttled',0): raise ValueError('startup cgroup already throttled; initial state unknown')
        metadata=dict(pid=pid,cgroup=str(group),cgroup_id=group.stat().st_ino,capped=capped,
            gomaxprocs=None if known else g,initial_limits=limits,uncapped_ancestors=ancestors(group),
            initial_cpu_stat=before,time_namespaces=namespaces(pid),
            startup='single-thread SIGSTOP' if known else 'single-thread FIFO before original /server exec')
        if kernel_tools.digest(Path(f'/proc/{pid}/exe'))!=json.loads((assets/'manifest.json').read_text())['gate_sha256']:
            raise ValueError('initial process is not the frozen native gate')
        save(directory/'initial.json',metadata)
        tf=(directory/'events.txt').open('x');ef=(directory/'observer.stderr').open('x');handles.extend((tf,ef))
        argv=['/usr/bin/bpftrace','-q','-k','-B','line',str(assets/'kernel_bridge.bt'),str(pid),str(metadata['cgroup_id'])]
        observer=subprocess.Popen(argv,stdout=tf,stderr=ef,
            env={k:v for k,v in os.environ.items() if not k.startswith('BPFTRACE_')}|{'LC_ALL':'C'},
            preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        fixtures.wait_for(directory/'events.txt','BEGIN ',observer,30)
        owned=fixtures.owned_ids(observer.pid)
        metadata['owned_bpf_ids']=sorted(owned)
        if known: os.kill(pid,signal.SIGCONT)
        else: release_fifo(qualification/'start.fifo')
        snapshots=[];clock_samples=[];request_bounds=[];after=None
        if known:
            worker.wait(timeout=8)
            if worker.returncode: raise ValueError('known multi-CPU worker failed')
        else:
            port=capture(['docker','port',container,'8080/tcp']).rsplit(':',1)[1]
            base=f'http://127.0.0.1:{port}'
            until=time.monotonic()+8
            while True:
                try:health=get(base,'health');break
                except OSError:
                    if time.monotonic()>until: raise ValueError('service startup timeout')
                    time.sleep(.05)
            manifest=json.loads((assets/'manifest.json').read_text())
            exe=Path(f'/proc/{pid}/exe')
            if kernel_tools.digest(exe)!=manifest['server_sha256'] or os.readlink(exe)!='/server':
                raise ValueError('running executable is not original packaged server')
            if inspect['Image']!=manifest['image'] or len(inspect['Mounts'])!=1 or any(m['Destination']=='/server' for m in inspect['Mounts']):
                raise ValueError('image or packaged loading differs')
            metadata['executable_sha256']=kernel_tools.digest(exe)
            repeatability_analysis.validate_state(health,'legacy_a')
            if health['gomaxprocs']!=g or health['go_version']!='go1.26.1' or health['workers']!=4 or health['queue_cap']!=128 or not health['instrument']:
                raise ValueError('Go runtime or request configuration differs')
            time.sleep(.3)
            snapshots.append(snapshot(pid,group));clock_samples+=anchors(base,'start')
            args=[str(assets/'loadgen'),'-url',base+'/work?iterations=44000','-duration','2s',
                  '-rate','113.21','-pattern','steady','-concurrency','64','-timeout','5s',
                  '-trace-client=true','-output',str(directory/'loadgen.json')]
            log=(directory/'client.log').open('x');handles.append(log)
            client=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            try:
                while client.poll() is None:
                    snapshots.append(snapshot(pid,group))
                    if len(snapshots)>151: raise TimeoutError('bounded client timeout')
                    time.sleep(.1)
                if client.returncode: raise ValueError('client failed')
            finally: fixtures.stop(client,signal.SIGTERM)
            until=time.monotonic()+8
            while True:
                server=get(base,'metrics')
                if not server['active_handlers'] and not server['queue_len'] and server['completed']==server['admitted']: break
                if time.monotonic()>until: raise ValueError('service drain timeout')
                time.sleep(.05)
            save(directory/'server_metrics.json',server)
            classified=repeatability_analysis.classify(json.loads((directory/'loadgen.json').read_text()),server,'legacy_a')
            if classified['offered']!=227 or classified['missing_entry_count']: raise ValueError('functional offered/entry coverage mismatch')
            save(directory/'request_classification.json',classified)
            snapshots.append(snapshot(pid,group));clock_samples+=anchors(base,'stop')
            joined=analysis.clock_join(clock_samples,classified['mapping'],server['clock_generation'])
            save(directory/'clock_mapping.json',joined);save(directory/'kernel_server_anchors.json',clock_samples)
            requests={q['ID']:q for q in json.loads((directory/'loadgen.json').read_text())['requests']}
            jobs={j['id']:j for j in server['events']};handlers={h['id']:h for h in server['handler_events']}
            for row in classified['requests']:
                if row['deadline_ms']!=500: continue
                # Export existing boundaries in the kernel domain, preserving missing events.
                q=requests[row['id']]
                origin=classified['mapping']['client_test_start_ns']+q['ScheduledOffsetNs']
                entry=dict(id=row['id'],outcome=row['outcome'],deadline_crossing=row['deadline_crossing'])
                entry['scheduled_kernel_lower_ns']=origin+joined['kernel_minus_client_lower_ns']
                entry['scheduled_kernel_upper_ns']=origin+joined['kernel_minus_client_upper_ns']
                for boundary in ('completion','resume'):
                    record=(jobs if boundary=='completion' else handlers).get(row['id'])
                    stamp=None if record is None else record[boundary+'_ns']
                    entry[boundary+'_kernel_lower_ns']=None if stamp is None else stamp+joined['kernel_minus_server_lower_ns']
                    entry[boundary+'_kernel_upper_ns']=None if stamp is None else stamp+joined['kernel_minus_server_upper_ns']
                request_bounds.append(entry)
            save(directory/'request_kernel_bounds.json',request_bounds)
            time.sleep(.3)
            # Docker may remove the runtime cgroup as soon as the process stops.
            # Counters are a cross-check of active work, not the final exit tail.
            after=fixtures.stat(group)
            capture(['docker','stop','--time','2',container])
        time.sleep(.2)
        fixtures.stop(observer,signal.SIGINT)
        if observer.returncode: raise ValueError('observer exit failed')
        fixtures.wait_detached(owned)
        if after is None: after=fixtures.stat(group)
        metadata['cpu_stat_delta']={k:after[k]-before.get(k,0) for k in after}
        metadata['cpu_stat_after']=after
        metadata['cpu_stat_end']='after worker exit' if known else 'after drain, before container stop'
        metadata['observer_returncode']=observer.returncode
        save(directory/'thread_snapshots.json',snapshots)
        result=analysis.coverage((directory/'events.txt').read_text(),(directory/'observer.stderr').read_text(),metadata,snapshots)
        if known: result['known_two_cpu']=analysis.known_two_cpu(result,(directory/'worker.jsonl').read_text())
        else:
            if g==2 and result['observed_cpus']!=[2,4]: raise ValueError('GOMAXPROCS=2 did not exercise both CPUs')
            if not all(result['capture_begin_ns'] < s['before_ns'] <= s['after_ns'] < result['capture_end_ns'] for s in clock_samples):
                raise ValueError('clock anchor outside capture')
            for r in request_bounds:
                for b in ('completion','resume'):
                    lo=r[b+'_kernel_lower_ns'];hi=r[b+'_kernel_upper_ns']
                    if lo is not None and not result['capture_begin_ns']<=lo<=hi<=result['capture_end_ns']:
                        raise ValueError('request boundary not certainly inside capture')
            result.update(offered=classified['offered'],clock_uncertainty_ns=joined['uncertainty_ns'])
        save(directory/'validation.json',result)
        return result
    except BaseException as e:
        failure=str(e);raise
    finally:
        errors=[]
        if worker:
            try: stop_known(worker)
            except BaseException as e: errors.append(str(e))
        for process,sig in ((observer,signal.SIGINT),):
            try: fixtures.stop(process,sig)
            except BaseException as e: errors.append(str(e))
        for handle in handles: handle.close()
        if owned:
            try: fixtures.wait_detached(owned)
            except BaseException as e: errors.append(str(e))
        if container:
            try:
                logs=subprocess.run(['docker','logs',container],capture_output=True,text=True,timeout=10,check=True)
                (directory/'container.stdout').write_text(logs.stdout)
                (directory/'container.stderr').write_text(logs.stderr)
            except BaseException as e: errors.append('container log capture: '+str(e))
            try: capture(['docker','rm','-f',container])
            except BaseException as e: errors.append(str(e))
            if group is not None:
                until=time.monotonic()+5
                while group.exists() and time.monotonic()<until: time.sleep(.05)
                if group.exists(): errors.append('owned container cgroup still present after removal')
        if created:
            try:
                if (group/'cgroup.procs').read_text().strip(): raise ValueError('owned group nonempty')
                group.rmdir()
            except BaseException as e: errors.append(str(e))
        save(directory/'attempt.json',dict(metadata=metadata,error=failure,cleanup_errors=errors,
             owned_bpf_ids=sorted(owned),cgroup_removed=group is not None and not group.exists()))
        if errors: raise RuntimeError('bridge cleanup needs review: '+'; '.join(errors))


def run(output):
    if os.geteuid()!=0: raise ValueError('use the external launcher for local sudo')
    if output.parent.resolve()!=OUTPUT_PARENT.resolve() or output.exists(): raise ValueError('new dedicated output required')
    if not {0,1,2,4} <= os.sched_getaffinity(0): raise ValueError('required CPUs unavailable')
    value=verify_assets()
    if value['kernel']!=platform.release(): raise ValueError('kernel changed; review capabilities first')
    if capture(['docker','image','inspect','--format','{{.Id}}',value['image']])!=value['image']:
        raise ValueError('retained image unavailable; no pull attempted')
    output.mkdir();initial=None;failure=None;results=[]
    try:
        initial=fixtures.root_state();save(output/'root_trace_state_before.json',initial)
        inv=kernel_tools.inventory();save(output/'inventory.json',inv)
        assessed=kernel_tools.assessment(inv);save(output/'inventory_assessment.json',assessed)
        if assessed['status']!='review_inventory_before_fixture' or assessed['scheduler_events_missing']:
            raise ValueError('kernel capability inventory incomplete')
        assets=output/'assets';shutil.copytree(ASSETS,assets)
        shutil.copy2(HERE/'kernel_bridge.bt',assets/'kernel_bridge.bt')
        source=output/'source'
        for name, expected in value['sources'].items():
            p=source/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
            if kernel_tools.digest(p)!=expected: raise ValueError('source snapshot mismatch')
        for known,g,capped in [(True,1,True),(False,1,False),(False,2,False),(False,1,True),(False,2,True)]:
            verify_assets()
            name='two_cpu_quota' if known else f'service_g{g}_'+('quota' if capped else 'uncapped')
            print('Bridge:',name,flush=True)
            results.append(run_case(output/name,assets,known,g,capped))
        verify_assets()
        print('All five compatibility cases passed; observer overhead remains unqualified.',flush=True)
    except BaseException as e:
        failure=str(e);raise
    finally:
        after=fixtures.root_state();save(output/'root_trace_state_after.json',after)
        save(output/'summary.json',dict(passed=failure is None and initial==after and len(results)==5,
            error=failure,root_trace_controls_unchanged=initial==after,cases=results,
            observer_cost_qualified=False,performance_batch_ready=False,performance_run=False))
        save(output/'seal.json',dict(files_sha256={str(p.relative_to(output)):kernel_tools.digest(p)
            for p in output.rglob('*') if p.is_file()}))
        uid=int(os.environ.get('SUDO_UID','0'));gid=int(os.environ.get('SUDO_GID','0'))
        if uid:
            for p in [*output.rglob('*'),output]:
                if not p.is_symlink(): os.chown(p,uid,gid)
        if initial!=after: raise ValueError('root tracing state changed; review before continuing')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare',action='store_true');group.add_argument('--verify',action='store_true')
    group.add_argument('--preflight',action='store_true')
    group.add_argument('--output',type=Path)
    args=parser.parse_args()
    def interrupt(signum,frame): raise InterruptedError('bridge interrupted: '+str(signum))
    signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt)
    signal.signal(signal.SIGALRM,interrupt);signal.alarm(360)
    try:
        if args.prepare: prepare()
        elif args.verify: print(json.dumps(verify_assets(),indent=2))
        elif args.preflight: preflight()
        else: run(args.output.resolve())
    finally: signal.alarm(0)


if __name__=='__main__': main()
