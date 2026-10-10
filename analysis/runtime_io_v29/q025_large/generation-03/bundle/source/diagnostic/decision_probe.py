#!/usr/bin/env python3
"""Eight paired quiet trials linking scheduler choices to HTTP readiness.

Only the bounded recorder differs; the retained policy and workload stay fixed.
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
import build_decision_probe as build
import fairness_analysis
import decision_analysis
import pipeline
import run

DEFAULT=run.ROOT/'results/diagnostic/runtime-io-v11-decision-probe-1'


def verify_build(require_fixtures=True):
    value=run.read(build.DEFAULT/'build.json')
    if value['base_build']!=run.verify_build():raise ValueError('base build changed')
    if value['producer_sha256']!=run.sha(Path(build.__file__)):raise ValueError('probe producer changed')
    for name,digest in value['prepared']['sources'].items():
        if run.sha(build.DEFAULT/name)!=digest:raise ValueError('probe prepared source changed')
    for mode,image in value['images'].items():
        if run.image_id(image)!=image:raise ValueError('probe image unavailable '+mode)
    if require_fixtures:
        fixture=run.read(build.DEFAULT/'functional_verification.json')
        if (fixture.get('passed') is not True or fixture.get('performance_run') is not False or
            fixture.get('verifier_sha256')!=run.sha(run.HERE/'verify_decision_probe.py') or
            fixture.get('analyzer_sha256')!=run.sha(run.HERE/'decision_analysis.py') or
            {r['mode']:r['image'] for r in fixture['records']}!=value['images']):
            raise ValueError('functional recorder verification missing or changed')
        for record in fixture['records']:
            for name,digest in record['fixture_files_sha256'].items():
                if run.sha(build.DEFAULT/record['fixture_directory']/name)!=digest:
                    raise ValueError('functional fixture changed')
    return value


def matrix(value):
    rows=[]
    for block,order in enumerate((('control','observed'),('observed','control'),
                                  ('observed','control'),('control','observed')),1):
        for mode in order:
            rows.append(dict(run.pilot_matrix()[0],run_id=f'decisions_b{block}_{mode}',rep=block,
                runtime_trace=False,custom_recording=True,worker_yield=False,probe_mode=mode,
                service_image=value['images'][mode],require_quiet=True))
    return rows


def create(session,value):
    run.require_quiet_host()
    session.mkdir(parents=True,exist_ok=False);(session/'attempts').mkdir()
    meta=dict(schema=run.SCHEMA,created=run.now(),pilot=False,decision_probe=True,eligible_for_full=False,
        source_sha256=run.provenance(),build=value['base_build'],probe_build=value,
        topology=run.old.check_topology(),server_cpus=run.old.CPUS,client_cpus=run.old.CLIENT_CPUS,
        kernel=run.capture(['uname','-a']),docker_version=run.capture(['docker','version']),
        python=sys.version,source_session=str(run.ORIGINAL),
        source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json'),
        probe_protocol_sha256=run.sha(run.ROOT/'docs/runtime_io_v11_decision_probe_commands.md'),
        power_settings=run.power_settings(include_profile=True))
    run.put(session/'matrix.json',matrix(value));meta['matrix_sha256']=run.sha(session/'matrix.json')
    for source in run.source_files():
        target=session/'source'/source.relative_to(run.ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    shutil.copy2(run.ROOT/'docs/runtime_io_v11_decision_probe_commands.md',session/'source/docs/runtime_io_v11_decision_probe_commands.md')
    shutil.copy2(run.BUILD,session/'build.json')
    (session/'tools').mkdir()
    shutil.copy2(run.LOADGEN,session/'tools/loadgen')
    shutil.copy2(run.ORIGINAL/'calibration.json',session/'original_calibration.json')
    shutil.copytree(build.DEFAULT,session/'probe_build')
    run.put(session/'metadata.json',meta)


def verify_session(session,check_current=True):
    meta=run.read(session/'metadata.json')
    if not meta.get('decision_probe') or meta['schema']!=run.SCHEMA or meta.get('pilot'):
        raise ValueError('not a standalone scheduler-decision probe')
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
    protocol='docs/runtime_io_v11_decision_probe_commands.md'
    if run.sha(session/'source'/protocol)!=meta['probe_protocol_sha256']:
        raise ValueError('frozen probe protocol changed')
    if check_current and run.sha(run.ROOT/protocol)!=meta['probe_protocol_sha256']:
        raise ValueError('probe protocol changed; use a new session')
    return meta


def validate_capture_attempt(attempt,config):
    server=run.read(attempt/'server_metrics.json')
    status=run.read(attempt/'trace_status.json')
    decision_analysis.validate_capture(server,status,config['probe_mode']=='observed')
    return decision_analysis.analyze_attempt(attempt,config['probe_mode']=='observed')


def collect(directory):
    value=verify_build();session=directory/'session'
    with run.acquire_experiment_lock():
        if not session.exists():create(session,value)
        meta=verify_session(session,check_current=True)
        if not meta.get('decision_probe') or meta['probe_build']!=value:raise ValueError('probe build/session changed')
        if run.old.check_topology()!=meta['topology']:raise ValueError('CPU topology changed')
        if run.capture(['docker','ps','-a','-q','--filter',f'label=quota.diagnostic.session={session}']):
            raise ValueError('prior probe container remains; inspect before resuming')
        plan=run.read(session/'matrix.json');pending=[];completed=0
        for config in plan:
            good=[p for p in run.attempt_dirs(session/'attempts'/config['run_id']) if run.validate(p,config,False)]
            if len(good)>1:raise ValueError('multiple valid attempts')
            if good:validate_capture_attempt(good[0],config);completed+=1
            else:pending.append(config)
        if pending:
            run.require_quiet_host();run.old.prepare_environment(session)
        try:
            for config in pending:
                verify_session(session,check_current=True)
                run.put(session/'status.json',dict(completed=completed,total=8,state='running',current=config['run_id']))
                print('RUN',completed+1,'/8',config['run_id'],flush=True)
                attempt=run.run_attempt(session,config,False,run.next_attempt(session/'attempts'/config['run_id']))
                validate_capture_attempt(attempt,config);completed+=1
            run.put(session/'status.json',dict(completed=completed,total=8,state='complete'))
        except BaseException as exc:
            run.put(session/'status.json',dict(completed=completed,total=8,state='interrupted',error=str(exc)))
            raise


def analyze_results(directory):
    session=directory/'session';verify_session(session,check_current=False)
    rows=[];seals={};attribution={}
    for order,config in enumerate(run.read(session/'matrix.json'),1):
        good=[p for p in run.attempt_dirs(session/'attempts'/config['run_id']) if run.validate(p,config,False)]
        if len(good)!=1:raise ValueError('need exactly one valid attempt '+config['run_id'])
        attempt=good[0];result=validate_capture_attempt(attempt,config)
        attribution[config['run_id']]=result
        row=analyze.trial_row(order,config,attempt)
        lg=run.read(attempt/'loadgen.json');server=run.read(attempt/'server_metrics.json')
        row.update(probe_mode=config['probe_mode'],runtime_mode='patched_off' if config['probe_mode']=='observed' else 'stock_off',
            errors=lg['total_errors'],error_fraction=lg['total_errors']/lg['total_scheduled'],completed_jobs=server['completed'],
            scheduler_events=server['scheduler_capture']['reserved'],
            matched_prehandler_network_waits=result.get('matched_prehandler_network_waits'),
            network_ready_p99_ms=result.get('ready_wait_p99_ms'))
        rows.append(row)
        seals[config['run_id']]=dict(attempt=attempt.name,sha256=run.sha(attempt/'complete.json'))
    if len(rows)!=8:raise ValueError('all eight trials required')
    screen=fairness_analysis.comparison(rows,'patched_off','stock_off')
    screen['treatment']='observed_candidate';screen['reference']='control_candidate'
    out=session/'analysis';out.mkdir(exist_ok=True)
    analyze.writecsv(out/'trials.csv',rows);run.put(out/'observer_screens.json',screen)
    run.put(out/'scheduler_attribution.json',attribution)
    lines=['# Scheduler choices ahead of delayed HTTP handlers','',
        'Eight validated trials with the same candidate policy. Runtime tracing and worker yielding were off. '
        'Only the bounded decision recorder differed. Counts cover capture start through drained stop, including control and drain.', '',
        '| Block | Arm | Events | Matched pre-handler waits | Ready-wait p99 ms | Successful p99 ms | Rejection | Timeout |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        wait=f'{r["network_ready_p99_ms"]:.3f}' if r['network_ready_p99_ms'] is not None else 'unavailable'
        lines.append(f'| {r["rep"]} | {r["probe_mode"]} | {r["scheduler_events"]} | '
            f'{r["matched_prehandler_network_waits"] if r["matched_prehandler_network_waits"] is not None else "unavailable"} | '
            f'{wait} | {r["p99_e2e_ms"]:.3f} | {r["rejection_fraction"]:.3%} | {r["timeout_fraction"]:.3%} |')
    lines += ['',f'Original descriptive observer screens: {"PASS" if screen["original_numeric_screens_passed"] else "FAIL"}. '
        'Inspect observer_screens.json for CPU/job, client CPU/request, successful p99, failure and coverage checks. '
        'Throughput and all failures remain in trials.csv. Four pairs are descriptive.','',
        '| Trial | Request | HTTP G | Ready wait ms | Dispatches ahead | Forced selections ahead | Final source |',
        '|---|---:|---:|---:|---:|---:|---|']
    for rid,result in attribution.items():
        for e in result['examples'][:3]:
            lines.append(f'| {rid} | {e["request_id"]} | {e["g"]} | {e["wait_ns"]/1e6:.3f} | '
                f'{e["dispatches_ahead"]} | {e["forced_selections_ahead"]} | {e["final_selection_source"]} |')
    lines += ['','scheduler_attribution.json preserves selected G identities, sources and pending/fairness flags, '
        'plus per-request dispatch counts by role/source. Only network wakes whose first running segment reaches '
        'a handler marker are associated. Earlier connection cleanup must finish before the wake; ambiguous '
        'reuse is retained separately. Control waits are unavailable, not zero.','',
        'Recorder timestamps describe observation sites, not continuous CPU execution or exact queue residence. '
        'A selection may be diverted before execute; unmatched dispatches have no source claim. '
        'The origin of a preemption signal is unavailable. Equal boundary timestamps are reported as ambiguous. '
        'The longest examples overlap and their counts must not be added.','',
        'If the recorder fails the original perturbation screens, its timings cannot replace the control. '
        'Activation with delays does not establish sufficiency. No new correction, solution claim, '
        'qualification gate or larger collection is created.','']
    (out/'report.md').write_text('\n'.join(lines))
    run.put(out/'validation.json',dict(passed=True,trials=8,eligible_for_full=False))
    names=('trials.csv','observer_screens.json','scheduler_attribution.json','validation.json')
    run.put(directory/'completion.json',dict(at=run.now(),report_sha256=run.sha(out/'report.md'),
        analysis_sha256={name:run.sha(out/name) for name in names},attempts=seals,eligible_for_full=False))
    pipeline.update_status(directory,'complete','complete',report=str(out/'report.md'))
    print('DECISION PROBE COMPLETE:',out/'report.md',flush=True)


def status(directory):
    if not (directory/'workflow-status.json').exists():
        print('Scheduler-decision probe has not started:',directory)
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
            pipeline.update_status(directory,'running','analyze-scheduler-choices');analyze_results(directory)
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
                validate_capture_attempt(attempt,config)
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
