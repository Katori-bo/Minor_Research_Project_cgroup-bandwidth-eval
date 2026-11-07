#!/usr/bin/env python3
"""External single-attempt supervisor, independent watchdog and owned cleanup."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import shutil

import common as c


def terminate(record, group=True, grace_sec=5, inspect=c.identity, send=os.kill,
              send_group=os.killpg, clock=time.monotonic, sleep=time.sleep):
    if not c.same(record,inspect):return
    pid=record['pid']
    # Only session leaders whose PID is also the saved PGID can be group-killed.
    if group:c.require(os.getpgid(pid)==pid,'owned process is not its own process-group leader')
    action=send_group if group else send
    action(pid,signal.SIGTERM);until=clock()+grace_sec
    while c.same(record,inspect) and clock()<until:sleep(.05)
    if c.same(record,inspect):action(pid,signal.SIGKILL)


def cleanup(directory, package, worker, remove=None):
    """Clean only evidence owned by this worker, with container nonce checks."""
    errors=[];directory=Path(directory)
    def remove_default(name,nonce,label):
        p=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=15)
        if p.returncode:
            c.require('no such' in p.stderr.lower(),'container inspect failed');return
        value=json.loads(p.stdout)[0]
        c.require(value['Config'].get('Labels',{}).get(label)==nonce,'owned container label/nonce changed')
        c.command(['docker','rm','-f',value['Id']],timeout=20)
    remove=remove or remove_default
    for path in directory.rglob('ownership.json'):
        try:
            c.require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()),'foreign ownership path')
            record=c.read(path);owner=record['owner']
            if owner.get('pid')!=worker.get('pid') or str(owner.get('start_ticks'))!=str(worker.get('start_ticks')):continue
            done=path.parent/'cleanup.json'
            if done.exists():
                receipt=c.read(done)
                if not receipt.get('errors') and (receipt.get('container_removed') or
                    package['application']=='NGINX'):continue
            # Clients with independent sessions need separate cleanup. Go's
            # clients/monitors share the worker group and were already signalled.
            for child_path in list(path.parent.glob('*ownership.json'))+list(path.parent.glob('*process.json')):
                if child_path.name=='ownership.json':continue
                child=c.read(child_path)
                if 'pid' not in child:continue
                if c.same(child):
                    terminate(child,group=os.getpgid(child['pid'])==child['pid'],
                              inspect=c.identity)
            label='research.slo.'+package['host']['id']+'.'+package['application']+'.owner'
            remove(record['container'],record['nonce'],label)
        except Exception as exc:errors.append(dict(path=str(path.relative_to(directory)),error=str(exc)))
    return errors


def watchdog(directory):
    directory=Path(directory);life=c.read(directory/'lifetime.json')
    package=c.read(directory/'allocation.json');owner=c.read(directory/'supervisor.json')
    while not (directory/'supervisor_finished.json').exists():
        expired=time.monotonic_ns()>=life['active_deadline_ns']
        if expired or not c.same(owner):
            errors=[];active=directory/'active_worker.json'
            if active.exists():
                worker=c.read(active)
                new_session=worker.pop('new_session',True)
                try:terminate(worker,group=new_session)
                except Exception as exc:errors.append(dict(error=str(exc)))
            for path in (directory/'workers').glob('*.json'):
                errors+=cleanup(directory,package,c.read(path))
            c.write(directory/'watchdog_cleanup.json',dict(errors=errors,expired=expired,
                finished_ns=time.monotonic_ns(),hard_deadline_ns=life['hard_deadline_ns']))
            if c.same(owner):os.kill(owner['pid'],signal.SIGTERM)
            else:
                finished=time.monotonic_ns()
                c.write(directory/'supervisor_finished.json',dict(failure='supervisor exited; independent cleanup',
                    cleanup_errors=errors,elapsed_sec=(finished-life['started_ns'])/1e9,
                    within_hard_cap=finished<=life['hard_deadline_ns'],allocation_closed=True,no_retry=True))
                root=directory.parents[2]
                c.write(directory/'return_seal.json',dict(files_sha256={str(p.relative_to(directory)):c.sha(p)
                    for p in sorted(directory.rglob('*')) if p.is_file()},
                    package_seal_sha256=c.sha(root/'runtime_seal.json'),planned_campaign_id=package['campaign']['id'],allocation_closed=True))
            return
        time.sleep(.2)


def allocation(plan,host_id,application):
    host=next(h for h in plan['hosts'] if h['id']==host_id)
    campaign=next(x for x in plan['campaigns'] if x['host']==host_id and x['application']==application)
    return dict(host=host,application=application,campaign=campaign,
                cap_sec=12600 if application=='Go' else 2700,cleanup_reserve_sec=120)


def admit(root, app, allocation_confirmed):
    package=c.verify_package(root);plan=c.read(Path(root)/'scientific/plan.json');host=package['host']['id']
    c.require(allocation_confirmed,'host allocation is unconfirmed; external collection requires --allocation-confirmed')
    c.require(app not in package.get('consumed_allocations',{}),'allocation already consumed in preserved source package; no retry')
    value=allocation(plan,host,app)
    c.require(app in ('Go','NGINX'),'foreign application')
    parent=Path(root)/'runs'/host;parent.mkdir(parents=True,exist_ok=True)
    directory=parent/app
    c.require(not directory.exists(),'campaign allocation consumed; no resume, retry or overwrite')
    preceding=value['host']['order'][:value['host']['order'].index(app)]
    for prior in preceding:
        origin=c.campaign_origin(root,prior)
        c.require((origin/'runs'/host/prior/'supervisor_finished.json').exists(),'frozen host campaign order requires closing '+prior+' first')
    directory.mkdir();return directory,value


def close_unavailable(root,app,reason,allocation_confirmed=False):
    c.require(reason and reason.strip(),'explicit unavailability reason required')
    root=Path(root);directory,alloc=admit(root,app,allocation_confirmed)
    c.write(directory/'allocation.json',alloc)
    c.write(directory/'supervisor_finished.json',dict(failure='allocation unavailable: '+reason,
        cleanup_errors=[],elapsed_sec=0,within_hard_cap=True,allocation_closed=True,
        no_retry=True,traffic_started=False))
    c.write(directory/'return_seal.json',dict(files_sha256={str(p.relative_to(directory)):c.sha(p)
        for p in sorted(directory.rglob('*')) if p.is_file()},package_seal_sha256=c.sha(root/'runtime_seal.json'),
        planned_campaign_id=alloc['campaign']['id'],allocation_closed=True))


def invoke(directory,argv,phase,hard,active_bound_sec=None,new_session=True,log_output=True,watcher=None):
    c.require(time.monotonic_ns()+120*10**9<hard,'cleanup reserve reached')
    stop_at=hard-120*10**9
    if active_bound_sec is not None:stop_at=min(stop_at,time.monotonic_ns()+int(active_bound_sec*10**9))
    started=time.monotonic_ns()
    c.write(directory/'supervisor_ledger'/(phase+'_start.json'),dict(started_ns=started,stop_at_ns=stop_at,
        bound_sec=active_bound_sec,argv=argv,new_session=new_session))
    log=(directory/(phase+'.log')).open('x') if log_output else None
    child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT if log else None,start_new_session=new_session)
    record=c.identity(child.pid)
    c.write(directory/'workers'/(phase+'.json'),record)
    c.replace(directory/'active_worker.json',dict(record,new_session=new_session))
    failure=None
    try:
        while child.poll() is None:
            if watcher is not None:c.require(watcher.poll() is None,'independent campaign watchdog exited')
            if time.monotonic_ns()>=stop_at:raise TimeoutError(phase+' bounded lifetime exhausted')
            time.sleep(.2)
        c.require(child.returncode==0,phase+' stopped; preserve partial evidence')
    except BaseException as exc:
        failure=str(exc);raise
    finally:
        try:
            if child.poll() is None:terminate(record,group=new_session)
            child.wait(timeout=3)
        finally:
            if log:log.close()
            c.write(directory/'supervisor_ledger'/(phase+'_end.json'),dict(finished_ns=time.monotonic_ns(),
                elapsed_sec=(time.monotonic_ns()-started)/1e9,error=failure,returncode=child.returncode))


def inventory(root,directory,alloc,hard,watcher=None):
    c.require(sys.stdin.isatty(),'read-only inventory authentication requires the external interactive terminal')
    audit=root/'runs'/alloc['host']['id']/'audits'/(alloc['application']+'.json')
    audit.parent.mkdir(parents=True,exist_ok=True)
    # This child stays in the terminal session and is signalled by PID, never
    # by the terminal process group. User input goes directly to sudo.
    invoke(directory,['sudo',sys.executable,'-B',str(root/'diagnostic/leftover_observer_audit.py'),
        '--output',str(audit)],'read_only_inventory',hard,300,new_session=False,log_output=False,watcher=watcher)
    import leftover_observer_review as review
    result=review.review(audit);c.require(result['performance_eligible'],'observer inventory ineligible')
    shutil.copy2(audit,directory/'observer_audit.json')
    c.write(directory/'observer.json',dict(path=str(audit),sha256=c.sha(audit),review=result))


def run(root,app,allocation_confirmed=False):
    root=Path(root);package=c.verify_package(root)
    from v31_common import require_desktop_absent
    require_desktop_absent()
    host=package['host']['id'];lockpath=root/'runs'/host/'campaign.lock'
    lockpath.parent.mkdir(parents=True,exist_ok=True)
    with lockpath.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        directory,alloc=admit(root,app,allocation_confirmed)
        started=time.monotonic_ns();hard=started+alloc['cap_sec']*10**9
        c.write(directory/'allocation.json',alloc)
        c.write(directory/'lifetime.json',dict(started_ns=started,hard_deadline_ns=hard,
            active_deadline_ns=hard-120*10**9,cap_sec=alloc['cap_sec'],boot_id=c.identity(os.getpid())['boot_id']))
        c.write(directory/'supervisor.json',c.identity(os.getpid()))
        watchlog=(directory/'watchdog.log').open('x')
        watch=subprocess.Popen([sys.executable,'-B',str(root/'runtime/supervisor.py'),'watchdog',
            '--directory',str(directory)],stdout=watchlog,stderr=subprocess.STDOUT,start_new_session=True)
        failure=None;errors=[]
        def stop(signum,frame):raise InterruptedError('campaign interrupted; preserving attempt')
        handlers={sig:signal.signal(sig,stop) for sig in (signal.SIGTERM,signal.SIGINT)}
        try:
            c.require(watch.poll() is None,'independent campaign watchdog exited')
            for phase in ('prepare','collect'):
                if phase=='collect':inventory(root,directory,alloc,hard,watch)
                invoke(directory,[sys.executable,'-B',str(root/'runtime/worker.py'),
                    '--directory',str(directory),'--phase',phase],phase,hard,
                    600 if phase=='prepare' and app=='Go' else (300 if phase=='prepare' else None),watcher=watch)
                for path in (directory/'workers').glob('*.json'):
                    errors+=cleanup(directory,alloc,c.read(path))
                c.require(not errors,'owned phase cleanup failed')
                c.require(watch.poll() is None,'independent campaign watchdog exited')
        except BaseException as exc:failure=str(exc)
        finally:
            active=directory/'active_worker.json'
            if active.exists():
                worker=c.read(active);new_session=worker.pop('new_session',True)
                if c.same(worker):
                    try:terminate(worker,group=new_session)
                    except Exception as exc:errors.append(dict(error=str(exc)))
            for path in (directory/'workers').glob('*.json'):
                errors+=cleanup(directory,alloc,c.read(path))
            finished=time.monotonic_ns()
            c.write(directory/'supervisor_finished.json',dict(failure=failure,cleanup_errors=errors,
                elapsed_sec=(finished-started)/1e9,within_hard_cap=finished<=hard,
                acquired_campaign_cap_sec=alloc['cap_sec'],allocation_closed=True,no_retry=True))
            if watch.poll() is None:watch.terminate()
            try:watch.wait(timeout=3)
            except subprocess.TimeoutExpired:watch.kill();watch.wait(timeout=3)
            watchlog.close()
            for sig,handler in handlers.items():signal.signal(sig,handler)
            c.write(directory/'return_seal.json',dict(files_sha256={str(p.relative_to(directory)):c.sha(p)
                for p in sorted(directory.rglob('*')) if p.is_file()},
                package_seal_sha256=c.sha(root/'runtime_seal.json'),
                planned_campaign_id=alloc['campaign']['id'],allocation_closed=True))
        c.require(failure is None and not errors and finished<=hard,'campaign closed with unavailable/partial evidence: '+str(failure))


def main():
    root=Path(__file__).resolve().parents[1]
    sys.path[:0]=[str(root/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['run','watchdog','close-unavailable'])
    p.add_argument('--application',choices=['Go','NGINX']);p.add_argument('--directory',type=Path)
    p.add_argument('--reason')
    p.add_argument('--allocation-confirmed',action='store_true');args=p.parse_args()
    if args.command=='watchdog':watchdog(args.directory)
    elif args.command=='close-unavailable':close_unavailable(root,args.application,args.reason,args.allocation_confirmed)
    else:run(root,args.application,args.allocation_confirmed)


if __name__=='__main__':main()
