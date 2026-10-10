#!/usr/bin/env python3
"""Resumable stock/patched Go comparison; no automatic full collection."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import signal
import sys
import time
import traceback
import uuid

import build_fairness
import pipeline
import run

DEFAULT = run.ROOT/'results/diagnostic/runtime-io-v9-fairness-1'
MODES = ('stock_off','stock_on','patched_off','patched_on')


def matrix(build):
    base=run.pilot_matrix()[0]
    order=[('stock_off','stock_on','patched_on','patched_off'),
           ('stock_on','patched_off','stock_off','patched_on'),
           ('patched_off','patched_on','stock_on','stock_off'),
           ('patched_on','stock_off','patched_off','stock_on')]
    rows=[]
    for block,cells in enumerate(order,1):
        for mode in cells:
            variant,trace=mode.split('_')
            rows.append(dict(base,run_id=f'fairness_b{block}_{mode}',rep=block,
                    runtime_mode=mode,runtime_variant=variant,worker_yield=False,
                    runtime_trace=trace=='on',custom_recording=True,require_quiet=True,
                    service_image=build['images'][variant],trace_decoder=build['decoder'],
                    trace_decoder_sha256=build['decoder_sha256']))
    return rows


def create(session,build):
    run.require_quiet_host()
    if shutil.disk_usage(run.ROOT).free<3*1024**3:
        raise RuntimeError('At least 3 GiB free disk space is required for raw traces and analysis')
    meta=dict(schema=run.SCHEMA,created=run.now(),pilot=False,components=False,
              yield_study=False,fairness_study=True,eligible_for_full=False,
              source_sha256=run.provenance(),build=build['base_build'],fairness_build=build,
              topology=run.old.check_topology(),server_cpus=run.old.CPUS,client_cpus=run.old.CLIENT_CPUS,
              kernel=run.capture(['uname','-a']),docker_version=run.capture(['docker','version']),
              python=sys.version,source_session=str(run.ORIGINAL),
              source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json'),
              power_settings=run.power_settings(include_profile=True))
    session.mkdir(parents=True,exist_ok=False)
    (session/'attempts').mkdir()
    run.put(session/'matrix.json',matrix(build))
    meta['matrix_sha256']=run.sha(session/'matrix.json')
    for path in run.source_files()+build_fairness.dependencies():
        target=session/'source'/path.relative_to(run.ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,target)
    shutil.copy2(run.BUILD,session/'build.json')
    shutil.copy2(build_fairness.MANIFEST,session/'fairness_build.json')
    shutil.copy2(run.ORIGINAL/'calibration.json',session/'original_calibration.json')
    (session/'tools').mkdir()
    shutil.copy2(build_fairness.DECODER,session/'tools/go-trace')
    meta['frozen_build_sha256']=run.sha(session/'fairness_build.json')
    run.put(session/'metadata.json',meta)


def verify_frozen(session,check_current=False):
    meta=run.verify_session(session,check_current=check_current)
    if not meta.get('fairness_study') or meta.get('pilot') or meta.get('yield_study') or meta.get('components'):
        raise RuntimeError('Not a standalone runtime fairness study')
    if (run.sha(session/'fairness_build.json')!=meta['frozen_build_sha256'] or
        run.read(session/'fairness_build.json')!=meta['fairness_build'] or
        run.sha(session/'tools/go-trace')!=meta['fairness_build']['decoder_sha256']):
        raise RuntimeError('Frozen runtime build or decoder changed')
    return meta


def collect(session):
    build=build_fairness.verify_manifest()
    with run.acquire_experiment_lock():
        if not session.exists():
            create(session,build)
        elif not (session/'metadata.json').exists():
            raise RuntimeError('Session exists without metadata; inspect it before restarting')
        meta=verify_frozen(session,check_current=True)
        if meta['fairness_build']!=build or run.old.check_topology()!=meta['topology']:
            raise RuntimeError('Runtime build or CPU topology changed; cannot resume')
        orphan=run.capture(['docker','ps','-a','-q','--filter',f'label=quota.diagnostic.session={session}'])
        if orphan:
            raise RuntimeError('Prior study container remains; inspect before resuming: '+orphan)
        rows=run.read(session/'matrix.json');pending=[]
        for config in rows:
            good=[d for d in run.attempt_dirs(session/'attempts'/config['run_id'])
                  if run.validate(d,config,False)]
            if len(good)>1:
                raise RuntimeError('Multiple valid attempts: '+config['run_id'])
            if not good:pending.append(config)
        completed=len(rows)-len(pending)
        if not pending:
            print('All 16 trials validate; proceeding to analysis without new workload.',flush=True)
            return
        run.put(session/'status.json',dict(completed=completed,total=len(rows),state='initial-settling'))
        try:
            run.require_quiet_host()
            run.old.prepare_environment(session)
            for config in pending:
                verify_frozen(session,check_current=True)
                print(f'RUN {completed+1}/{len(rows)} {config["run_id"]}',flush=True)
                run.put(session/'status.json',dict(completed=completed,total=len(rows),state='running',current=config['run_id']))
                directory=run.run_attempt(session,config,False,run.next_attempt(session/'attempts'/config['run_id']))
                completed+=1
                run.put(session/'status.json',dict(completed=completed,total=len(rows),state='running',last=str(directory)))
            run.put(session/'status.json',dict(completed=completed,total=len(rows),state='complete'))
        except BaseException as exc:
            run.put(session/'status.json',dict(completed=completed,total=len(rows),state='interrupted',
                                              error=str(exc) or type(exc).__name__))
            raise


def execute(directory,lock):
    session=directory/'session'
    pipeline.stage_command(directory,'verify-build',
        [sys.executable,Path(__file__),'verify-build'],lock)
    pipeline.stage_command(directory,'collect-16-trials',
        [sys.executable,Path(__file__),'collect','--directory',directory],lock)
    pipeline.stage_command(directory,'analyze-results',
        [sys.executable,run.HERE/'fairness_analysis.py',session],lock)
    validation=run.read(session/'analysis/validation.json')
    if not validation['passed']:
        raise RuntimeError('Result analysis failed validation')
    report=directory/'COMPLETED.md'
    report.write_text('# Runtime fairness comparison completed\n\n'
        f'Completed: {run.now()}\n\n16 trials validated.\n\n'
        f'[Results and unchanged performance screens]({session / "analysis/report.md"})\n\n'
        f'[Raw counts and all trial metrics]({session / "analysis/trials.csv"})\n\n'
        'Completion does not mean the candidate passed its performance screens. '
        'No larger collection is started.\n')
    run.put(directory/'completion.json',dict(at=run.now(),eligible_for_full=False,
        report_sha256=run.sha(report),validation_sha256=run.sha(session/'analysis/validation.json'),
        screens_sha256=run.sha(session/'analysis/screens.json'),
        analysis_report_sha256=run.sha(session/'analysis/report.md'),
        summary_sha256=run.sha(session/'analysis/summary.json')))
    pipeline.update_status(directory,'complete','complete',report=str(report))
    print('STUDY COMPLETE:',report,flush=True)


def foreground(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.worker.lock').open('a') as worker:
        fcntl.flock(worker,fcntl.LOCK_EX|fcntl.LOCK_NB)
        lock=None
        def stop(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
        signal.signal(signal.SIGTERM,stop)
        pipeline.update_status(directory,'running','preflight',worker_pid=os.getpid(),error=None)
        try:
            run.require_quiet_host()
            lock=run.acquire_experiment_lock()
            execute(directory,lock)
        except BaseException as exc:
            state='interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed'
            prior=run.read(directory/'workflow-status.json')
            pipeline.update_status(directory,state,prior['stage'],error=str(exc) or type(exc).__name__)
            print(f'STOPPED: {exc}. Saved evidence remains in {directory}.',flush=True)
            traceback.print_exc()
            return 130 if state=='interrupted' else 1
        finally:
            if lock:lock.close()
    return 0


def status(directory):
    if not (directory/'workflow-status.json').exists():
        print('Fairness comparison has not started:',directory)
        return
    pipeline.print_status(directory)
    path=directory/'session/status.json'
    if path.exists():
        value=run.read(path)
        print(f'Trials: {value["completed"]}/{value["total"]}; {value["state"]}')
        if value.get('current'):print('Current:',value['current'])


def launch(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if pipeline.is_running(directory):
            status(directory);return 0
        if (directory/'completion.json').exists():
            session=directory/'session'
            verify_frozen(session)
            completion=run.read(directory/'completion.json')
            if (completion['report_sha256']!=run.sha(directory/'COMPLETED.md') or
                completion['validation_sha256']!=run.sha(session/'analysis/validation.json') or
                completion['screens_sha256']!=run.sha(session/'analysis/screens.json') or
                completion['analysis_report_sha256']!=run.sha(session/'analysis/report.md') or
                completion['summary_sha256']!=run.sha(session/'analysis/summary.json')):
                raise RuntimeError('Completion evidence changed; inspect before restarting')
            seals=run.read(session/'analysis/summary.json')['completion_sha256']
            for config in run.read(session/'matrix.json'):
                good=[d for d in run.attempt_dirs(session/'attempts'/config['run_id'])
                      if run.validate(d,config,False)]
                if len(good)!=1 or seals.get(config['run_id'])!=run.sha(good[0]/'complete.json'):
                    raise RuntimeError('Completed raw trial evidence changed: '+config['run_id'])
            status(directory);return 0
        run.require_quiet_host()
        build_fairness.verify_manifest()
        inhibitor=shutil.which('systemd-inhibit')
        if not inhibitor:
            raise RuntimeError('systemd-inhibit is required for the unattended launcher')
        logs=directory/'logs';logs.mkdir(exist_ok=True)
        logfile=logs/(str(time.time_ns())+'-'+uuid.uuid4().hex[:8]+'.log')
        command=[inhibitor,'--no-ask-password','--what=idle:sleep','--mode=block',
                 '--who=CPU quota fairness comparison','--why=Unattended controlled measurements','--',
                 sys.executable,'-u',str(Path(__file__).resolve()),'foreground','--directory',str(directory)]
        pipeline.update_status(directory,'starting','launch',error=None,sleep_inhibitor=True)
        with logfile.open('x') as output:
            process=run.sp.Popen(command,cwd=run.ROOT,stdin=run.sp.DEVNULL,stdout=output,
                                 stderr=run.sp.STDOUT,start_new_session=True)
        run.put(directory/'launch.json',dict(pid=process.pid,start_tick=pipeline.process_signature(process.pid),
                                           log=str(logfile),command=command,at=run.now()))
        for _ in range(100):
            state=run.read(directory/'workflow-status.json')['state']
            if state!='starting' or process.poll() is not None:break
            time.sleep(.1)
        if process.poll() is not None and run.read(directory/'workflow-status.json')['state']=='starting':
            pipeline.update_status(directory,'failed','launch',error=logfile.read_text()[-3000:])
        status(directory)
        if run.read(directory/'workflow-status.json')['state'] in ('failed','interrupted'):return 1
        print('Started in background with sleep inhibition. You may close this terminal. '
              'Keep AC connected and the lid open. Re-run the same command to resume.',flush=True)
        return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['start','status','foreground','collect','verify-build'],nargs='?',default='start')
    parser.add_argument('--directory',type=Path,default=DEFAULT)
    args=parser.parse_args();directory=args.directory.resolve()
    def stop(signum,frame):raise KeyboardInterrupt(f'signal {signum}')
    signal.signal(signal.SIGTERM,stop)
    if not directory.is_relative_to(run.ROOT/'results/diagnostic') or directory==run.ROOT/'results/diagnostic':
        parser.error('directory must be a subdirectory of results/diagnostic')
    if args.action=='verify-build':
        build_fairness.verify_manifest();print('Stock/patched images, decoder and sources verified.');return 0
    if args.action=='status':status(directory);return 0
    if args.action=='collect':collect(directory/'session');return 0
    if args.action=='foreground':return foreground(directory)
    return launch(directory)


if __name__=='__main__':
    raise SystemExit(main())
