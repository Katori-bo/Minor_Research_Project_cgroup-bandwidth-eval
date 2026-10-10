#!/usr/bin/env python3
"""Eight quiet trials asking whether the tested fairness path executes.

The candidate scheduling policy is identical in both arms. Only observational
counters are enabled/disabled. Runtime tracing and worker yielding stay off.
"""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import signal
import statistics as stats
import subprocess
import sys
import time
import traceback
import uuid

import analyze
import build_pending_probe as build
import fairness_analysis
import pipeline
import run

DEFAULT=run.ROOT/'results/diagnostic/runtime-io-v10-pending-probe-1'


def verify_build():
    value=run.read(build.DEFAULT/'build.json')
    if value['base_build']!=run.verify_build():raise ValueError('base build changed')
    if value['producer_sha256']!=run.sha(Path(build.__file__)):raise ValueError('probe producer changed')
    for name,digest in value['prepared']['sources'].items():
        if run.sha(build.DEFAULT/name)!=digest:raise ValueError('probe prepared source changed')
    for mode,image in value['images'].items():
        if run.image_id(image)!=image:raise ValueError('probe image unavailable '+mode)
    return value


def matrix(value):
    rows=[]
    for block,order in enumerate((('control','observed'),('observed','control'),
                                  ('observed','control'),('control','observed')),1):
        for mode in order:
            rows.append(dict(run.pilot_matrix()[0],run_id=f'pending_b{block}_{mode}',rep=block,
                runtime_trace=False,custom_recording=True,worker_yield=False,probe_mode=mode,
                service_image=value['images'][mode],require_quiet=True))
    return rows


def create(session,value):
    run.require_quiet_host()
    session.mkdir(parents=True,exist_ok=False);(session/'attempts').mkdir()
    meta=dict(schema=run.SCHEMA,created=run.now(),pilot=False,pending_probe=True,eligible_for_full=False,
        source_sha256=run.provenance(),build=value['base_build'],probe_build=value,
        topology=run.old.check_topology(),server_cpus=run.old.CPUS,client_cpus=run.old.CLIENT_CPUS,
        kernel=run.capture(['uname','-a']),docker_version=run.capture(['docker','version']),
        python=sys.version,source_session=str(run.ORIGINAL),
        source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json'),
        probe_protocol_sha256=run.sha(run.ROOT/'docs/runtime_io_v10_pending_probe_commands.md'),
        power_settings=run.power_settings(include_profile=True))
    run.put(session/'matrix.json',matrix(value));meta['matrix_sha256']=run.sha(session/'matrix.json')
    for source in run.source_files():
        target=session/'source'/source.relative_to(run.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    shutil.copy2(run.ROOT/'docs/runtime_io_v10_pending_probe_commands.md',session/'source/docs/runtime_io_v10_pending_probe_commands.md')
    shutil.copy2(run.BUILD,session/'build.json')
    (session/'tools').mkdir()
    shutil.copy2(run.LOADGEN,session/'tools/loadgen')
    shutil.copy2(run.ORIGINAL/'calibration.json',session/'original_calibration.json')
    shutil.copytree(build.DEFAULT,session/'probe_build')
    run.put(session/'metadata.json',meta)


def verify_session(session,check_current=True):
    meta=run.read(session/'metadata.json')
    if not meta.get('pending_probe') or meta['schema']!=run.SCHEMA or meta.get('pilot'):
        raise ValueError('not a standalone pending-preemption probe')
    if (run.sha(session/'matrix.json')!=meta['matrix_sha256'] or
        run.read(session/'matrix.json')!=matrix(meta['probe_build'])):
        raise ValueError('probe matrix changed')
    if check_current and meta['source_sha256']!=run.provenance():
        raise ValueError('source, binary or protocol changed; use a new session')
    for name,digest in meta['source_sha256'].items():
        if name==str(run.LOADGEN.relative_to(run.ROOT)):source=session/'tools/loadgen'
        elif name==str(run.BUILD.relative_to(run.ROOT)):source=session/'build.json'
        else:source=session/'source'/name
        if run.sha(source)!=digest:raise ValueError('frozen source changed '+name)
    frozen=run.read(session/'probe_build/build.json')
    if frozen!=meta['probe_build']:raise ValueError('frozen probe build changed')
    for name,digest in frozen['prepared']['sources'].items():
        if run.sha(session/'probe_build'/name)!=digest:raise ValueError('frozen probe source changed')
    if run.sha(run.ORIGINAL/'calibration.json')!=meta['source_calibration_sha256']:
        raise ValueError('original calibration changed')
    protocol='docs/runtime_io_v10_pending_probe_commands.md'
    if run.sha(session/'source'/protocol)!=meta['probe_protocol_sha256']:
        raise ValueError('frozen probe protocol changed')
    if check_current and run.sha(run.ROOT/protocol)!=meta['probe_protocol_sha256']:
        raise ValueError('probe protocol changed; use a new session')
    return meta


def validate_counters(attempt,config):
    server=run.read(attempt/'server_metrics.json')
    enabled=config['probe_mode']=='observed'
    if server.get('scheduler_observation_enabled') is not enabled:
        raise ValueError('counter observation mode differs from planned image')
    counters=server.get('scheduler_counters',{})
    if set(counters)!=set(build.NAMES) or any(type(v) is not int or v<0 for v in counters.values()):
        raise ValueError('counter schema/monotonicity invalid')
    if not enabled and any(counters.values()):raise ValueError('disabled control counted events')
    if server.get('scheduler_counter_window')!='reset_to_snapshot_including_control_and_drain':
        raise ValueError('unknown counter capture window')
    return counters


def collect(directory):
    value=verify_build();session=directory/'session'
    with run.acquire_experiment_lock():
        if not session.exists():create(session,value)
        meta=verify_session(session,check_current=True)
        if not meta.get('pending_probe') or meta['probe_build']!=value:raise ValueError('probe build/session changed')
        if run.old.check_topology()!=meta['topology']:raise ValueError('CPU topology changed')
        if run.capture(['docker','ps','-a','-q','--filter',f'label=quota.diagnostic.session={session}']):
            raise ValueError('prior probe container remains; inspect before resuming')
        plan=run.read(session/'matrix.json');pending=[];completed=0
        for config in plan:
            good=[p for p in run.attempt_dirs(session/'attempts'/config['run_id']) if run.validate(p,config,False)]
            if len(good)>1:raise ValueError('multiple valid attempts')
            if good:validate_counters(good[0],config);completed+=1
            else:pending.append(config)
        if pending:
            run.require_quiet_host();run.old.prepare_environment(session)
        try:
            for config in pending:
                verify_session(session,check_current=True)
                run.put(session/'status.json',dict(completed=completed,total=8,state='running',current=config['run_id']))
                print('RUN',completed+1,'/8',config['run_id'],flush=True)
                attempt=run.run_attempt(session,config,False,run.next_attempt(session/'attempts'/config['run_id']))
                validate_counters(attempt,config);completed+=1
            run.put(session/'status.json',dict(completed=completed,total=8,state='complete'))
        except BaseException as exc:
            run.put(session/'status.json',dict(completed=completed,total=8,state='interrupted',error=str(exc)))
            raise


def analyze_results(directory):
    session=directory/'session';verify_session(session,check_current=False)
    rows=[];seals={}
    for order,config in enumerate(run.read(session/'matrix.json'),1):
        good=[p for p in run.attempt_dirs(session/'attempts'/config['run_id']) if run.validate(p,config,False)]
        if len(good)!=1:raise ValueError('need exactly one valid attempt '+config['run_id'])
        attempt=good[0];counters=validate_counters(attempt,config)
        row=analyze.trial_row(order,config,attempt)
        lg=run.read(attempt/'loadgen.json');server=run.read(attempt/'server_metrics.json')
        row.update(probe_mode=config['probe_mode'],runtime_mode='patched_off' if config['probe_mode']=='observed' else 'stock_off',
            errors=lg['total_errors'],error_fraction=lg['total_errors']/lg['total_scheduled'],completed_jobs=server['completed'],
            **counters)
        rows.append(row)
        seals[config['run_id']]=dict(attempt=attempt.name,sha256=run.sha(attempt/'complete.json'))
    if len(rows)!=8:raise ValueError('all eight trials required')
    screen=fairness_analysis.comparison(rows,'patched_off','stock_off')
    screen['treatment']='observed_candidate';screen['reference']='control_candidate'
    out=session/'analysis';out.mkdir(exist_ok=True)
    analyze.writecsv(out/'trials.csv',rows);run.put(out/'observer_screens.json',screen)
    lines=['# Pending-preemption observation probe','',
        'Eight validated trials of the same candidate runtime, with observation disabled/enabled. '
        'Runtime tracing and worker yielding were off. The original workload and limits were fixed.', '',
        '| Block | Arm | Pending flags seen | Ordinary fairness reached | Global work selected | Regular local selected | Sole runnext selected | Successful p99 ms | Rejection | Timeout |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["rep"]} | {r["probe_mode"]} | {r["pending_seen"]} | {r["ordinary_fairness_reached"]} | '
            f'{r["global_selected"]} | {r["regular_local_selected"]} | {r["sole_runnext_selected"]} | '
            f'{r["p99_e2e_ms"]:.3f} | {r["rejection_fraction"]:.3%} | {r["timeout_fraction"]:.3%} |')
    lines += ['', '## Observer perturbation screen', '',
        f'Original descriptive numeric screens: {"PASS" if screen["original_numeric_screens_passed"] else "FAIL"}. '
        f'Median throughput ratio: {screen["ratios"]["successful_rps"]:.4f}. '
        'See observer_screens.json for CPU, client cost, p99, failures and coverage checks.', '',
        'The purpose is to measure whether the previously tested policy executes, not test a new correction. '
        'Counters cover reset through the final snapshot, including control requests and drain. '
        'They are aggregate atomic samples, not a per-request queue history or proof of which ready HTTP request was selected.', '',
        'Nonzero ordinary/global/local counts establish that those paths execute in the observer arm. '
        'Zero or rare pending signals would show that this workload hardly exercises the proposed correction. '
        'A path executing while delays remain would weaken its sufficiency, not exonerate the runtime. '
        'If the observer changes outcomes beyond the original screens, its timing cannot be substituted for the unobserved control.', '',
        'No solution claim, qualification gate or larger collection is created.','']
    (out/'report.md').write_text('\n'.join(lines))
    run.put(out/'validation.json',dict(passed=True,trials=8,eligible_for_full=False))
    run.put(directory/'completion.json',dict(at=run.now(),report_sha256=run.sha(out/'report.md'),
        analysis_sha256={name:run.sha(out/name) for name in ('trials.csv','observer_screens.json','validation.json')},
        attempts=seals,eligible_for_full=False))
    pipeline.update_status(directory,'complete','complete',report=str(out/'report.md'))
    print('PROBE COMPLETE:',out/'report.md',flush=True)


def status(directory):
    if not (directory/'workflow-status.json').exists():
        print('Pending-preemption probe has not started:',directory)
        return
    pipeline.print_status(directory)
    path=directory/'session/status.json'
    if path.exists():
        value=run.read(path);print(f'Trials: {value["completed"]}/{value["total"]}; {value["state"]}')


def foreground(directory):
    with (directory/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,lambda *args: (_ for _ in ()).throw(KeyboardInterrupt('signal TERM')))
        pipeline.update_status(directory,'running','preflight',worker_pid=os.getpid(),error=None)
        try:
            run.require_quiet_host();pipeline.update_status(directory,'running','collect-8-trials')
            collect(directory)
            pipeline.update_status(directory,'running','analyze-counters');analyze_results(directory)
        except BaseException as exc:
            pipeline.update_status(directory,'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
                run.read(directory/'workflow-status.json')['stage'],error=str(exc))
            traceback.print_exc();return 1
    return 0


def launch(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if pipeline.is_running(directory):status(directory);return
        if (directory/'completion.json').exists():
            value=run.read(directory/'completion.json')
            session=directory/'session';verify_session(session,check_current=False)
            if value['report_sha256']!=run.sha(directory/'session/analysis/report.md'):raise ValueError('completion report changed')
            for name,digest in value['analysis_sha256'].items():
                if run.sha(session/'analysis'/name)!=digest:raise ValueError('completed analysis changed')
            for config in run.read(session/'matrix.json'):
                seal=value['attempts'][config['run_id']]
                attempt=session/'attempts'/config['run_id']/seal['attempt']
                if run.sha(attempt/'complete.json')!=seal['sha256'] or not run.validate(attempt,config,False):
                    raise ValueError('completed raw evidence changed')
                validate_counters(attempt,config)
            status(directory);return
        run.require_quiet_host();verify_build()
        inhibitor=shutil.which('systemd-inhibit')
        if not inhibitor:raise ValueError('systemd-inhibit is required')
        (directory/'logs').mkdir(exist_ok=True)
        logfile=directory/'logs'/(str(time.time_ns())+'-'+uuid.uuid4().hex[:8]+'.log')
        command=[inhibitor,'--no-ask-password','--what=idle:sleep','--mode=block','--who=Pending fairness probe',
                 '--why=Quiet controlled observation','--',sys.executable,'-u',str(Path(__file__).resolve()),
                 'foreground','--directory',str(directory)]
        pipeline.update_status(directory,'starting','launch',error=None,sleep_inhibitor=True)
        with logfile.open('x') as stream:
            process=subprocess.Popen(command,cwd=run.ROOT,stdin=subprocess.DEVNULL,stdout=stream,
                                     stderr=subprocess.STDOUT,start_new_session=True)
        run.put(directory/'launch.json',dict(pid=process.pid,start_tick=pipeline.process_signature(process.pid),
            log=str(logfile),command=command,at=run.now()))
        for _ in range(100):
            if run.read(directory/'workflow-status.json')['state']!='starting' or process.poll() is not None:break
            time.sleep(.1)
        if process.poll() is not None and run.read(directory/'workflow-status.json')['state']=='starting':
            pipeline.update_status(directory,'failed','launch',error=logfile.read_text()[-3000:])
        status(directory)
        if pipeline.is_running(directory):print('Started in background with sleep inhibition.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('start','status','foreground','analyze','verify-build'))
    parser.add_argument('--directory',type=Path,default=DEFAULT)
    args=parser.parse_args();directory=args.directory.resolve()
    if args.command=='start':launch(directory)
    elif args.command=='status':status(directory)
    elif args.command=='foreground':raise SystemExit(foreground(directory))
    elif args.command=='analyze':analyze_results(directory)
    else:verify_build();print('Probe build verified; no measurements launched.')
