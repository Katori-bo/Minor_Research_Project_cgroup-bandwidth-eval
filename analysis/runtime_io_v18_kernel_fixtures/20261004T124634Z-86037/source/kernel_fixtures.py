#!/usr/bin/env python3
"""Three bounded root-only kernel fixtures; never launches the service benchmark."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
import uuid

import kernel_fixture_analysis as analysis
import kernel_tools

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
CGROOT=Path('/sys/fs/cgroup')
SOURCE_NAMES=('kernel_fixtures.py','kernel_fixture_analysis.py','kernel_fixture_work.py',
              'kernel_fixture.bt','kernel_tools.py','start_kernel_fixtures.sh',
              'test_kernel_fixtures.py','test_kernel_tools.py')


def save(path,value):
    with path.open('x') as f:f.write(json.dumps(value,indent=2)+'\n')


def stat(cgroup):
    return {k:int(v) for k,v in (s.split() for s in (cgroup/'cpu.stat').read_text().splitlines())}


def root_state():
    base=Path('/sys/kernel/tracing')
    return {n:(base/n).read_text() for n in ('current_tracer','tracing_on','trace_clock',
                'tracing_cpumask','buffer_size_kb','events/enable')}


def program_ids():
    return {int(p['id']) for p in json.loads(kernel_tools.checked(['bpftool','-j','prog','show']))}


def owned_ids(pid):
    result=set()
    for p in Path(f'/proc/{pid}/fdinfo').iterdir():
        try:text=p.read_text()
        except FileNotFoundError:continue
        for line in text.splitlines():
            if line.startswith('prog_id:'):result.add(int(line.split(':',1)[1]))
    if not result:raise ValueError('could not identify owned BPF programs from collector FDs')
    return result


def stop(process, first_signal):
    if process is None or process.poll() is not None:return
    process.send_signal(first_signal)
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=3)


def wait_for(path, marker, process, seconds=30):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if marker in path.read_text():return
        if process.poll() is not None:raise RuntimeError('process exited before '+marker)
        time.sleep(.05)
    raise TimeoutError('waiting for '+marker)


def wait_detached(owned):
    until=time.monotonic()+5
    while owned & program_ids():
        if time.monotonic()>=until:raise ValueError('owned BPF programs still present after detach')
        time.sleep(.05)


def run_case(directory,mode,assets):
    directory.mkdir()
    group=CGROOT/('quota-v18-fixture-'+uuid.uuid4().hex+'-'+mode)
    worker=observer=None;owned=set();created=False;handles=[];failure=None;metadata={}
    try:
        group.mkdir();created=True
        for name,text in {'cpu.max':'50000 100000' if mode=='quota' else 'max 100000',
                          'cpu.max.burst':'0','pids.max':'16','memory.max':str(256*1024**2),
                          'cpuset.cpus':'2'}.items():
            (group/name).write_text(text)
            if (group/name).read_text().strip()!=text:raise ValueError('resource setting failed: '+name)
        cg_id=group.stat().st_ino
        before=stat(group)
        if before.get('nr_throttled',0):raise ValueError('fresh fixture cgroup already throttled')
        worker_log=directory/'worker.jsonl';trace_log=directory/'events.txt';error_log=directory/'observer.stderr'
        wf=worker_log.open('x');tf=trace_log.open('x');ef=error_log.open('x');handles.extend((wf,tf,ef))
        worker=subprocess.Popen(['/usr/bin/python3',str(assets/'kernel_fixture_work.py'),mode],
            stdin=subprocess.PIPE,stdout=wf,stderr=subprocess.STDOUT,text=True,
            preexec_fn=lambda:os.sched_setaffinity(0,{2}))
        wait_for(worker_log,'"ready"',worker,5)
        (group/'cgroup.procs').write_text(str(worker.pid))
        if (group/'cgroup.procs').read_text().split()!=[str(worker.pid)]:raise ValueError('wrong cgroup members')
        if os.sched_getaffinity(worker.pid)!={2}:raise ValueError('wrong initial worker affinity')
        # This fixture deliberately begins with a blocked worker and an unthrottled
        # fresh cgroup. The later service pilot needs its own initial-state rules.
        until=time.monotonic()+2
        while True:
            status=Path(f'/proc/{worker.pid}/stat').read_text().split(') ',1)[1].split()[0]
            if status=='S':break
            if time.monotonic()>until:raise ValueError('worker did not block at start barrier')
            time.sleep(.01)
        argv=['/usr/bin/bpftrace','-q','-k','-B','line',str(assets/'kernel_fixture.bt'),str(worker.pid),str(cg_id)]
        metadata=dict(mode=mode,pid=worker.pid,cgroup=str(group),cgroup_id=cg_id,cpu=2,
            observer_cpus=[0,1],argv=argv,cpu_stat_before=before,
            resource_settings={n:(group/n).read_text() for n in ('cpu.max','cpu.max.burst','pids.max','memory.max','cpuset.cpus.effective')})
        save(directory/'initial.json',metadata)
        observer=subprocess.Popen(argv,stdout=tf,stderr=ef,
            env={k:v for k,v in os.environ.items() if not k.startswith('BPFTRACE_')} | {'LC_ALL':'C'},
            preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        wait_for(trace_log,'BEGIN ',observer,30)
        owned=owned_ids(observer.pid)
        if observer.poll() is not None:raise ValueError('observer ended before workload')
        worker.stdin.write('GO\n');worker.stdin.flush();worker.stdin.close()
        worker.wait(timeout=8)
        if worker.returncode:raise ValueError('worker failed; inspect worker log')
        time.sleep(.2)
        stop(observer,signal.SIGINT)
        if observer.returncode != 0:raise ValueError('observer did not exit cleanly')
        metadata.update(cpu_stat_after=stat(group),observer_returncode=observer.returncode,
                        worker_returncode=worker.returncode,owned_bpf_ids=sorted(owned))
        metadata['cpu_stat_delta']={k:metadata['cpu_stat_after'][k]-before.get(k,0) for k in metadata['cpu_stat_after']}
        wait_detached(owned)
        result=analysis.validate(trace_log.read_text(),worker_log.read_text(),error_log.read_text(),metadata)
        save(directory/'validation.json',result)
        return result
    except BaseException as e:
        failure=str(e)
        raise
    finally:
        cleanup=[]
        for process,sig in ((worker,signal.SIGTERM),(observer,signal.SIGINT)):
            try:stop(process,sig)
            except BaseException as e:cleanup.append(str(e))
        for h in handles:h.close()
        if owned:
            try:
                wait_detached(owned)
            except BaseException as e:cleanup.append(str(e))
        if created:
            try:
                if (group/'cgroup.procs').read_text().strip():raise ValueError('owned cgroup not empty; retained for review')
                group.rmdir()
            except BaseException as e:cleanup.append(str(e))
        save(directory/'attempt.json',dict(metadata=metadata,error=failure,cleanup_errors=cleanup,
             cgroup_removed=not group.exists(),owned_bpf_ids=sorted(owned)))
        if cleanup:raise RuntimeError('cleanup needs review: '+'; '.join(cleanup))


def run(output):
    if os.geteuid()!=0:raise ValueError('run the external launcher to authenticate sudo locally')
    expected_parent=(ROOT/'analysis/runtime_io_v18_kernel_fixtures').resolve()
    if output.parent.resolve()!=expected_parent or output.exists():raise ValueError('new dedicated fixture output required')
    if not {0,1,2} <= os.sched_getaffinity(0):raise ValueError('required fixture/collector CPUs unavailable')
    if 'cpu' not in (CGROOT/'cgroup.subtree_control').read_text().split():raise ValueError('CPU controller is not already enabled; no change attempted')
    output.mkdir()
    initial=None;results=[];failure=None
    try:
        initial=root_state();save(output/'root_trace_state_before.json',initial)
        inv=kernel_tools.inventory();save(output/'inventory.json',inv)
        assess=kernel_tools.assessment(inv);save(output/'inventory_assessment.json',assess)
        if assess['status']!='review_inventory_before_fixture' or assess['scheduler_events_missing']:
            raise ValueError('kernel capability inventory incomplete')
        paths={n:HERE/n for n in SOURCE_NAMES}
        paths['protocol.md']=ROOT/'docs/runtime_io_v18_kernel_fixtures.md'
        sources={n:kernel_tools.digest(p) for n,p in paths.items()}
        save(output/'source_hashes.json',sources)
        assets=output/'source';assets.mkdir()
        for name,path in paths.items():shutil.copy2(path,assets/name)
        if {n:kernel_tools.digest(assets/n) for n in paths}!=sources:
            raise ValueError('source snapshot changed during preparation')
        for mode in ('sleep','cpu','quota'):
            if {n:kernel_tools.digest(p) for n,p in paths.items()}!=sources:
                raise ValueError('fixture implementation changed during collection')
            print('Fixture:',mode,flush=True)
            results.append(run_case(output/mode,mode,assets))
        if {n:kernel_tools.digest(p) for n,p in paths.items()}!=sources:
            raise ValueError('fixture implementation changed during collection')
        print('All three bounded fixtures passed. Service observer overhead remains unqualified.',flush=True)
    except BaseException as e:
        failure=str(e)
        raise
    finally:
        after=root_state();save(output/'root_trace_state_after.json',after)
        unchanged=initial==after
        summary=dict(passed=failure is None and unchanged and len(results)==3,
            error=failure,root_trace_controls_unchanged=unchanged,fixtures=results,
            performance_batch_ready=False,observer_cost_qualified=False,
            kernel=platform.release(),performance_run=False)
        save(output/'summary.json',summary)
        hashes={str(p.relative_to(output)):kernel_tools.digest(p) for p in sorted(output.rglob('*')) if p.is_file()}
        save(output/'fixture_seal.json',dict(files_sha256=hashes))
        uid=int(os.environ.get('SUDO_UID','0'));gid=int(os.environ.get('SUDO_GID','0'))
        if uid:
            for p in [*output.rglob('*'),output]:
                if not p.is_symlink():os.chown(p,uid,gid)
        if not unchanged:raise ValueError('root trace controls changed during fixtures; review before continuing')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    def interrupted(signum,frame):raise InterruptedError('fixture interrupted: '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    signal.signal(signal.SIGALRM,interrupted);signal.alarm(150)
    try:run(args.output.resolve())
    finally:signal.alarm(0)


if __name__=='__main__':main()
