#!/usr/bin/env python3
"""Twelve matched observer qualification trials, with sealed evidence and resume."""
import argparse
import fcntl
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
import uuid

import analyze
import build_completion as build
import completion_analysis as analysis
import parallelism_analysis as stock_analysis
import parallelism_progress as progress
import parallelism_study as stock_study
import pipeline
import run

DEFAULT=run.ROOT/'results/diagnostic/runtime-io-v13-completion-qualification-1'
PROTOCOL=run.ROOT/'docs/runtime_io_v13_completion_protocol.md'
ORDERS=(('legacy','locked','bounded'),('bounded','locked','legacy'),
        ('locked','legacy','bounded'),('bounded','legacy','locked'))


def matrix(value):
    cal=run.read(run.ORIGINAL/'calibration.json')
    if cal['high_rps']!=113.21 or cal['iterations']!=44000: raise ValueError('discovery calibration changed')
    return [dict(study='completion_qualification_v1',run_id=f'completion_b{block}_{arm}',rep=block,
        recorder_arm=arm,parallelism_arm='g1',gomaxprocs=1,workers=4,period_us=100000,quota_us=50000,
        pattern='bursty',rate=cal['high_rps'],burst_low=cal['high_rps']*.5,burst_high=cal['high_rps']*1.5,
        iterations=cal['iterations'],duration_sec=60,warmup_sec=20,timeout_sec=5,instrument=True,
        client_trace=True,runtime_trace=False,custom_recording=False,worker_yield=False,require_quiet=True,
        service_image=value['images'][arm]) for block,order in enumerate(ORDERS,1) for arm in order]


def sources():
    return sorted(set(stock_study.sources()+build.dependencies()+[Path(__file__),PROTOCOL,
        run.HERE/'completion_analysis.py',run.ROOT/'docs/current_research_plan.md']))


def create(session,value):
    run.require_quiet_host();stock_study.time_offsets()
    session.mkdir(parents=True,exist_ok=False);(session/'attempts').mkdir()
    meta=dict(schema=run.SCHEMA,study='completion_qualification_v1',created=run.now(),
        source_sha256=run.hashes(sources()),build=value,build_manifest_sha256=run.sha(build.DEFAULT/'build.json'),
        fixture_manifest_sha256=run.sha(build.DEFAULT/'functional_verification.json'),
        topology=run.old.check_topology(),server_cpus=run.old.CPUS,client_cpus=run.old.CLIENT_CPUS,
        kernel=run.capture(['uname','-a']),python=sys.version,power_settings=run.power_settings(include_profile=True),
        source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json'),eligible_for_full=False)
    run.put(session/'matrix.json',matrix(value));meta['matrix_sha256']=run.sha(session/'matrix.json')
    for p in sources():
        target=session/'source'/p.relative_to(run.ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    shutil.copytree(build.DEFAULT,session/'observer_build')
    shutil.copy2(run.ORIGINAL/'calibration.json',session/'original_calibration.json')
    run.put(session/'metadata.json',meta)


def verify_session(session,current=True):
    meta=run.read(session/'metadata.json')
    if meta['study']!='completion_qualification_v1' or meta['schema']!=run.SCHEMA: raise ValueError('wrong session')
    if run.sha(session/'matrix.json')!=meta['matrix_sha256'] or run.read(session/'matrix.json')!=matrix(meta['build']):
        raise ValueError('frozen matrix changed')
    if current and run.hashes(sources())!=meta['source_sha256']: raise ValueError('source/protocol changed')
    for name,digest in meta['source_sha256'].items():
        if run.sha(session/'source'/name)!=digest: raise ValueError('frozen source changed: '+name)
    frozen=session/'observer_build'
    if run.sha(frozen/'build.json')!=meta['build_manifest_sha256'] or run.read(frozen/'build.json')!=meta['build']:
        raise ValueError('frozen build changed')
    if build.stock.prepared_hashes(frozen/'prepared')!=meta['build']['prepared_sha256'] or run.sha(frozen/'loadgen')!=meta['build']['loadgen_sha256']:
        raise ValueError('frozen source/binary changed')
    if run.sha(frozen/'functional_verification.json')!=meta['fixture_manifest_sha256']: raise ValueError('fixture seal changed')
    for name,digest in run.read(frozen/'functional_verification.json')['files_sha256'].items():
        if run.sha(frozen/name)!=digest: raise ValueError('frozen fixture changed')
    if run.sha(session/'original_calibration.json')!=meta['source_calibration_sha256']: raise ValueError('calibration changed')
    if current and (build.verify()!=meta['build'] or run.sha(run.ORIGINAL/'calibration.json')!=meta['source_calibration_sha256']):
        raise ValueError('current build/calibration changed')
    return meta


def validate_attempt(attempt,config):
    errors=run.validation_errors(attempt,config,False)
    if errors: raise ValueError('invalid raw attempt: '+'; '.join(errors))
    namespaces=run.read(attempt/'time_namespaces.json');expected={'monotonic':[0,0],'boottime':[0,0]}
    if namespaces['host']!=expected or namespaces['container']!=expected: raise ValueError('shifted time namespace')
    report=run.read(attempt/'result.json');server=run.read(attempt/'server_metrics.json')
    for state in (report['runtime'],report['runtime_end'],server):
        if state['runtime_capture'] or state['custom_recording'] or state['runtime_variant']!='stock':
            raise ValueError('runtime observer/patch enabled')
        if config['recorder_arm']=='legacy':
            if state.get('completion_protocol'): raise ValueError('legacy runtime has new observer')
        elif state.get('recorder_mode')!=config['recorder_arm'] or state.get('record_errors'):
            raise ValueError('recorder runtime mismatch/errors')
    return analysis.classify(run.read(attempt/'loadgen.json'),server,config['recorder_arm'])


def collect(directory):
    value=build.verify();session=directory/'session'
    with run.acquire_experiment_lock():
        if not session.exists(): create(session,value)
        meta=verify_session(session)
        if run.old.check_topology()!=meta['topology']: raise ValueError('CPU topology changed')
        if run.capture(['docker','ps','-a','-q','--filter',f'label=quota.diagnostic.session={session}']):
            raise ValueError('owned container remains; inspect before resume')
        plan=run.read(session/'matrix.json');pending=[];completed=0
        for c in plan:
            good=[p for p in run.attempt_dirs(session/'attempts'/c['run_id']) if run.validate(p,c,False)]
            if len(good)>1: raise ValueError('multiple valid attempts')
            if good: validate_attempt(good[0],c);completed+=1
            else: pending.append(c)
        run.put(session/'status.json',dict(completed=completed,total=len(plan),state='running',current=None))
        if pending: run.require_quiet_host();run.old.prepare_environment(session)
        previous=run.LOADGEN;run.LOADGEN=session/'observer_build/loadgen'
        try:
            for c in pending:
                verify_session(session)
                run.put(session/'status.json',dict(completed=completed,total=len(plan),state='running',current=c['run_id']))
                print('RUN',completed+1,'/12',c['run_id'],flush=True)
                attempt=stock_study.run_checked_attempt(session,c,run.next_attempt(session/'attempts'/c['run_id']))
                validate_attempt(attempt,c);completed+=1
                run.put(session/'status.json',dict(completed=completed,total=len(plan),state='running',current=None,last_completed=c['run_id']))
                temps=run.old.temperatures()
                print(f'DONE {completed}/12 ({100*completed/12:.1f}%) {c["run_id"]} | '+
                    ', '.join(f'{k}={v:.1f}°C' for k,v in sorted(temps.items())),flush=True)
            run.put(session/'status.json',dict(completed=completed,total=len(plan),state='complete'))
        except BaseException as exc:
            run.put(session/'status.json',dict(completed=completed,total=len(plan),state='interrupted',error=str(exc)));raise
        finally: run.LOADGEN=previous


def analyze_results(directory):
    session=directory/'session';verify_session(session,current=False)
    if (directory/'completion.json').exists(): verify_completion(directory);return
    rows=[];request_rows=[];seals={};schedules={}
    for order,c in enumerate(run.read(session/'matrix.json'),1):
        good=[p for p in run.attempt_dirs(session/'attempts'/c['run_id']) if run.validate(p,c,False)]
        if len(good)!=1: raise ValueError('one valid attempt required: '+c['run_id'])
        attempt=good[0];entry=validate_attempt(attempt,c)
        client=run.read(attempt/'loadgen.json')
        schedule=[(q['ID'],q['ScheduledOffsetNs']) for q in sorted(client['requests'],key=lambda q:q['ID'])]
        if c['rep'] in schedules and schedules[c['rep']]!=schedule: raise ValueError('matched offered schedule changed')
        schedules[c['rep']]=schedule
        row,_=stock_analysis.trial_row(order,c,attempt)
        row.update(recorder_arm=c['recorder_arm'],timely_500_fraction=entry['deadlines']['500']['timely_fraction'],
            timely_1000_fraction=entry['deadlines']['1000']['timely_fraction'],
            post_work_late_fraction=entry['deadlines']['500'].get('late_success_work_before',0)/entry['offered'],
            late_success_work_before=entry['deadlines']['500'].get('late_success_work_before',0),
            record_errors=0 if c['recorder_arm']=='legacy' else run.read(attempt/'server_metrics.json')['record_errors'])
        row['failure_fraction']=entry['deadlines']['500']['failure_fraction'];rows.append(row)
        for r in entry['requests']: request_rows.append(dict(run_id=c['run_id'],rep=c['rep'],recorder_arm=c['recorder_arm'],**r))
        seals[c['run_id']]=dict(attempt=attempt.name,sha256=run.sha(attempt/'complete.json'))
    screen=analysis.compare(rows);out=session/'analysis';out.mkdir(exist_ok=True)
    analyze.writecsv(out/'trials.csv',rows);analyze.writecsv(out/'requests.csv',request_rows)
    run.put(out/'observer_screen.json',screen)
    run.put(out/'validation.json',dict(passed=True,trials=12,matched_schedules=True,performance_trial_validation=True))
    lines=['# Completion-boundary observer qualification','',
        'Four matched three-arm blocks at GOMAXPROCS=1, four workers, 50 ms / 100 ms quota, zero burst credits. '
        'All offered requests remain in the 500 ms primary and 1,000 ms guardrail denominators.','',
        '| Block | Recorder | Timely 500 ms | Timely 1,000 ms | Failures | Late successes: work before 500 ms | CPU/job us |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        cpu='unavailable' if r['cpu_usec_per_completed_work'] is None else f'{r["cpu_usec_per_completed_work"]:.2f}'
        lines.append(f'| {r["rep"]} | {r["recorder_arm"]} | {r["timely_500_fraction"]:.3%} | '
            f'{r["timely_1000_fraction"]:.3%} | {r["failure_fraction"]:.3%} | {r["late_success_work_before"]} | {cpu} |')
    lines+=['',f'Practical observer decision: **{screen["decision"]}**.','',
        'observer_screen.json retains paired deltas and their block median/range; four blocks cannot establish statistical equivalence. '
        'Legacy-to-locked checks the combined marker/bookkeeping observer. Locked-to-bounded checks dynamic shared event storage. '
        'No intervention or larger batch is launched by passing this screen.','',
        'requests.csv retains failed, cancelled, late and drained outcomes, missing worker/handler events, clock bounds, '
        'publication/deadline overlap and publication-to-resume bounds. Sender completion can follow handler resume. '
        'Handler execution is not a runnable-readiness timestamp. Recorded mutex intervals include scheduling and off-CPU delays. '
        'Host/cgroup samples and CPU counters remain sealed, but do not identify instantaneous remaining quota or request-level throttle intervals. '
        'Further runtime/kernel observation requires a separate qualification.','',
        '[Frozen protocol](../source/docs/runtime_io_v13_completion_protocol.md)','']
    (out/'report.md').write_text('\n'.join(lines))
    names=('trials.csv','requests.csv','observer_screen.json','validation.json','report.md')
    run.put(directory/'completion.json',dict(at=run.now(),analysis_sha256={n:run.sha(out/n) for n in names},attempts=seals,eligible_for_full=False))
    pipeline.update_status(directory,'complete','complete',report=str(out/'report.md'))
    print('COMPLETION QUALIFICATION COMPLETE:',out/'report.md',flush=True)


def verify_completion(directory):
    session=directory/'session';verify_session(session,current=False);value=run.read(directory/'completion.json')
    for name,digest in value['analysis_sha256'].items():
        if run.sha(session/'analysis'/name)!=digest: raise ValueError('completed analysis changed')
    for c in run.read(session/'matrix.json'):
        seal=value['attempts'][c['run_id']];attempt=session/'attempts'/c['run_id']/seal['attempt']
        if run.sha(attempt/'complete.json')!=seal['sha256']: raise ValueError('attempt seal changed')
        validate_attempt(attempt,c)


def status(directory):
    if (directory/'workflow-status.json').exists(): pipeline.print_status(directory)
    progress.print_progress(snapshot(directory))


def snapshot(directory):
    value=progress.snapshot(directory)
    if not (directory/'session/status.json').exists(): value.update(total=12)
    if value['stage']=='analyze-observer' and value['state']=='running': value['phase']='analysis'
    return value


def watch(directory,interval=5):
    if interval<2: raise ValueError('watch interval must be at least two seconds')
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{int(c) for c in run.old.CLIENT_CPUS.split(',')})
    try:
        while True:
            value=snapshot(directory)
            if sys.stdout.isatty(): print('\033[2J\033[H',end='')
            print('Completion observer qualification | '+run.now())
            print(f'State: {value["state"]} | Stage: {value["stage"]}')
            progress.print_progress(value)
            if value['log']: print('Log:',value['log'])
            print('Ctrl+C closes this display; the background experiment continues.',flush=True)
            if value['state'] in ('complete','failed','interrupted'): return
            time.sleep(interval)
    except KeyboardInterrupt: return


def foreground(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,lambda *a: (_ for _ in ()).throw(KeyboardInterrupt('signal TERM')))
        pipeline.update_status(directory,'running','preflight',worker_pid=os.getpid(),error=None)
        try:
            run.require_quiet_host();pipeline.update_status(directory,'running','collect-12-trials');collect(directory)
            pipeline.update_status(directory,'running','analyze-observer');analyze_results(directory)
        except BaseException as exc:
            pipeline.update_status(directory,'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
                run.read(directory/'workflow-status.json')['stage'],error=str(exc));traceback.print_exc();return 1
    return 0


def launch(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if pipeline.is_running(directory): status(directory);return 0
        if (directory/'completion.json').exists(): verify_completion(directory);status(directory);return 0
        run.require_quiet_host();build.verify()
        if (directory/'session').exists(): verify_session(directory/'session')
        inhibitor=shutil.which('systemd-inhibit')
        if not inhibitor: raise ValueError('systemd-inhibit is required')
        (directory/'logs').mkdir(exist_ok=True);logfile=directory/'logs'/f'{time.time_ns()}-{uuid.uuid4().hex[:8]}.log'
        command=[inhibitor,'--no-ask-password','--what=idle:sleep','--mode=block','--who=Completion observer study',
            '--why=Quiet controlled measurements','--',sys.executable,'-u',str(Path(__file__).resolve()),
            'foreground','--directory',str(directory)]
        pipeline.update_status(directory,'starting','launch',error=None,sleep_inhibitor=True)
        with logfile.open('x') as stream:
            process=subprocess.Popen(command,cwd=run.ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        run.put(directory/'launch.json',dict(pid=process.pid,start_tick=pipeline.process_signature(process.pid),
            at=run.now(),log=str(logfile),command=command))
        for _ in range(100):
            if run.read(directory/'workflow-status.json')['state']!='starting' or process.poll() is not None: break
            time.sleep(.1)
        if process.poll() is not None and run.read(directory/'workflow-status.json')['state']=='starting':
            pipeline.update_status(directory,'failed','launch',error=logfile.read_text()[-3000:])
        status(directory)
        if pipeline.is_running(directory):
            print('Started in background with sleep inhibition.',flush=True);return 0
        return 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('start','foreground','status','watch','analyze','verify-build','verify-completion','plan'))
    p.add_argument('--directory',type=Path,default=DEFAULT);a=p.parse_args();directory=a.directory.resolve()
    if a.command=='start': sys.exit(launch(directory))
    elif a.command=='foreground': sys.exit(foreground(directory))
    elif a.command=='status': status(directory)
    elif a.command=='watch': watch(directory)
    elif a.command=='analyze': analyze_results(directory)
    elif a.command=='verify-completion': verify_completion(directory);print('Completed evidence verified.')
    elif a.command=='verify-build': build.verify();print('Build verified; no performance measurements launched.')
    else: print(__import__('json').dumps(matrix(dict(images={a:'unbuilt:'+a for a in ORDERS[0]})),indent=2))
