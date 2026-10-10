#!/usr/bin/env python3
"""Four separate prospective contexts under one seven-hour external supervisor."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

import v29_common as c
from v29_service import remove_owned

PARENT=c.ROOT/'analysis/runtime_io_v29_campaign'
ORDER=('q050_small','q025_small','q050_large','q025_large')
TOTAL_SEC=7*60*60


def session_for(key):return c.ROOT/'analysis/runtime_io_v29'/key/'generation-03'


def observer_audit_path(directory):
    # The retained reviewer deliberately accepts only its dedicated evidence
    # directory. Keep the audit there, and store a reference in the campaign.
    return c.ROOT/'analysis/runtime_io_leftover_observer_audit'/('v29-'+directory.name+'-'+str(time.time_ns())+'.json')


def validate_directory(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('Use a dedicated direct V29 campaign directory')
    return p


def terminate(identity,new_session=True):
    if not c.same_process(identity):return
    send=os.killpg if new_session else os.kill
    send(identity['pid'],signal.SIGTERM)
    deadline=time.monotonic()+120
    while c.same_process(identity) and time.monotonic()<deadline:time.sleep(.2)
    if c.same_process(identity):send(identity['pid'],signal.SIGKILL)


def cleanup_context(session,owner):
    errors=[]
    for p in session.rglob('ownership.json'):
        value=c.read(p)
        if value['owner']!=owner:continue
        try:remove_owned(value['container'],value['nonce'])
        except Exception as exc:errors.append(str(exc))
    return errors


def watchdog(directory):
    owner=c.read(directory/'owner.json')['owner']
    deadline=c.read(directory/'lifetime.json')['deadline_monotonic']
    while c.same_process(owner) and not (directory/'finished.json').exists():
        if time.monotonic()>=deadline:
            os.kill(owner['pid'],signal.SIGTERM)
            break
        time.sleep(.5)
    if (directory/'finished.json').exists():return
    active=c.read(directory/'active.json') if (directory/'active.json').exists() else None
    errors=[]
    if active:
        try:terminate(active['process'],active.get('new_session',True))
        except Exception as exc:errors.append(str(exc))
        if active.get('session'):
            errors+=cleanup_context(Path(active['session']),active['process'])
    c.save(directory/'watchdog_cleanup.json',dict(errors=errors,at=time.time(),invalidated=True))


def invoke(directory,argv,deadline,key=None,stage=None,new_session=True,timeout_sec=None):
    env=dict(os.environ)
    if key:env['RESEARCH_V29_CONTEXT']=key
    remaining=deadline-time.monotonic()
    if remaining<=120:raise TimeoutError('Campaign time bound reached; preserve partial results')
    stop_at=deadline-120
    if timeout_sec is not None:stop_at=min(stop_at,time.monotonic()+timeout_sec)
    process=subprocess.Popen(argv,env=env,start_new_session=new_session)
    identity=c.process_identity(process.pid)
    active=dict(process=identity,context=key,stage=stage,new_session=new_session,session=None if key is None else str(session_for(key)),started=time.time())
    c.save(directory/'active.json',active)
    c.save(directory/'progress.json',active)
    try:
        while process.poll() is None:
            if time.monotonic()>=stop_at:
                raise TimeoutError(f'{stage} time bound reached; stopping with campaign cleanup reserve')
            time.sleep(.5)
        if process.returncode:raise RuntimeError(f'{stage} failed for {key}: exit {process.returncode}')
    finally:
        if process.poll() is None:terminate(identity,new_session)
        errors=[] if key is None else cleanup_context(session_for(key),identity)
        if errors:raise RuntimeError('Owned cleanup failed: '+'; '.join(errors))


def collect_observer_inventory(directory,audit,deadline):
    if not sys.stdin.isatty():
        raise ValueError('Observer authentication requires the external interactive terminal')
    print('Runtime checks passed. Authenticate now for the read-only observer inventory; '
          'wait for the first scientific context before leaving the terminal.',flush=True)
    # sudo's credential cache may be scoped to the controlling terminal. Keep
    # this single read-only invocation in that session and allow a fresh prompt.
    # Shared-session cleanup signals this child only, never the terminal group.
    invoke(directory,['sudo',sys.executable,'-B',str(c.ROOT/'diagnostic/leftover_observer_audit.py'),
                      '--output',str(audit)],deadline,stage='read_only_observer_inventory',
           new_session=False,timeout_sec=300)


def run(directory):
    if os.geteuid()==0:raise ValueError('Use normal-user external orchestration')
    if directory.exists():raise ValueError('Preserve attempted campaign; do not resume or overwrite it')
    c.require_desktop_absent()
    directory.mkdir(parents=True)
    started=time.monotonic();deadline=started+TOTAL_SEC
    c.save(directory/'owner.json',dict(owner=c.process_identity(os.getpid())))
    c.save(directory/'lifetime.json',dict(started_monotonic=started,deadline_monotonic=deadline,bound_sec=TOTAL_SEC,boot=c.baseline()['boot_id']))
    c.save(directory/'plan.json',dict(context_order=ORDER,contexts=c.CONTEXTS,contexts_sequential=True,primary_deadline_ms=500,secondary_deadlines_ms=c.DEADLINES_MS,planned_calibration_trials=64,planned_validation_trials=64,independent_applications=1,independent_hosts=1))
    log=(directory/'watchdog.log').open('x')
    watcher=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'_watchdog','--directory',str(directory)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    def interrupted(signum,frame):raise InterruptedError('Campaign interrupted; preserving data and cleaning owned work')
    handlers={sig:signal.signal(sig,interrupted) for sig in (signal.SIGINT,signal.SIGTERM)}
    failure=None
    try:
        with (c.ROOT/'.experiment.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            # Prepare every context before the single fresh root observer audit.
            for key in ORDER:
                invoke(directory,[sys.executable,'-B',str(c.ROOT/'diagnostic/v29_study.py'),'prepare-runtime','--directory',str(session_for(key))],deadline,key,'runtime_preparation')
            audit=observer_audit_path(directory)
            c.save(directory/'observer_inventory_reference.json',dict(audit_path=str(audit)))
            collect_observer_inventory(directory,audit,deadline)
            invoke(directory,[sys.executable,'-B',str(c.ROOT/'diagnostic/leftover_observer_review.py'),'write','--audit',str(audit)],deadline,stage='observer_review')
            for key in ORDER:
                print('\nStarting independent context '+key,flush=True)
                invoke(directory,[sys.executable,'-B',str(c.ROOT/'diagnostic/v29_study.py'),'_foreground','--directory',str(session_for(key)),'--observer-audit',str(audit)],deadline,key,'calibration_then_validation')
            reviews={}
            for key in ORDER:
                session=session_for(key)
                latest=c.read(session/'latest_analysis.json')
                report=c.read(c.resolve(session,latest['path'])/'report.json')
                reviews[key]=dict(decision=report['result']['decision'],report_path=str(c.resolve(session,latest['path'])/'report.json'),calibration_usable=report['calibration'].get('usable',False),accepted_validation_trials=report['result']['accepted_validation_trials'])
            c.save(directory/'summary.json',dict(status='collection_complete',contexts=reviews,elapsed_sec=time.monotonic()-started,generality='Within one application and one host only. Sequential context order is confounded with time.',novelty_established=False))
            print('Campaign complete. Read '+str(directory/'summary.json'),flush=True)
    except BaseException as exc:
        failure=str(exc)
        c.save(directory/'interruption.json',dict(error=failure,traceback=traceback.format_exc(),at=time.time()))
        raise
    finally:
        c.save(directory/'finished.json',dict(failure=failure,at=time.time(),elapsed_sec=time.monotonic()-started))
        if watcher.poll() is None:
            watcher.terminate()
            try:watcher.wait(timeout=5)
            except subprocess.TimeoutExpired:watcher.kill();watcher.wait(timeout=5)
        log.close()
        for sig,handler in handlers.items():signal.signal(sig,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('run','status','_watchdog'))
    parser.add_argument('--directory',required=True)
    args=parser.parse_args();directory=validate_directory(args.directory)
    if args.command=='run':run(directory)
    elif args.command=='_watchdog':watchdog(directory)
    else:
        result={name:c.read(directory/name) for name in ('progress.json','summary.json','interruption.json','finished.json') if (directory/name).exists()}
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
