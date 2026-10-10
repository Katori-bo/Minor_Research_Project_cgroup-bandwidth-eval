#!/usr/bin/env python3
"""Eight stock-Go bursty trials testing an existing parallelism remedy."""
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
import build_parallelism as build
import parallelism_analysis as analysis
import parallelism_progress as progress_display
import pipeline
import run

DEFAULT=run.ROOT/'results/diagnostic/runtime-io-v12-bursty-parallelism-1'
PROTOCOL=run.ROOT/'docs/runtime_io_v12_parallelism_commands.md'
RESEARCH=run.ROOT/'docs/runtime_io_prior_art_review.md'


def time_offsets(pid='self'):
    text=Path(f'/proc/{pid}/timens_offsets').read_text()
    values={line.split()[0]:list(map(int,line.split()[1:])) for line in text.splitlines()}
    if set(values)!={'monotonic','boottime'} or any(v!=[0,0] for v in values.values()):
        raise ValueError('unshifted host/container time namespace required')
    return values


def run_checked_attempt(session,config,number):
    # The existing runner exposes the container PID when finding its cgroup.
    # Check the clock namespace at that boundary and seal the evidence with it.
    original=run.old.cgroup_path
    def checked(pid):
        evidence=dict(host=time_offsets(),container=time_offsets(pid),container_pid=pid)
        run.put(session/'attempts'/config['run_id']/f'{number:03d}'/'time_namespaces.json',evidence)
        return original(pid)
    run.old.cgroup_path=checked
    try:return run.run_attempt(session,config,False,number)
    finally:run.old.cgroup_path=original


def matrix(value):
    cal=run.read(run.ORIGINAL/'calibration.json');rows=[]
    if cal['high_rps']!=113.21 or cal['iterations']!=44000:raise ValueError('original calibration changed')
    for block,order in enumerate(((2,1),(1,2),(1,2),(2,1)),1):
        for g in order:
            rows.append(dict(study='bursty_parallelism_v1',run_id=f'parallelism_b{block}_g{g}',rep=block,
                parallelism_arm=f'g{g}',period_us=100000,quota_us=50000,workers=4,gomaxprocs=g,
                pattern='bursty',rate=cal['high_rps'],burst_low=cal['high_rps']*.5,
                burst_high=cal['high_rps']*1.5,iterations=cal['iterations'],duration_sec=60,warmup_sec=20,
                timeout_sec=5,instrument=True,client_trace=True,runtime_trace=False,custom_recording=False,
                worker_yield=False,require_quiet=True,service_image=value['images']['service']))
    return rows


def sources():
    names=('run.py','trace_analysis.py','analyze.py','pipeline.py','parallelism_study.py',
           'parallelism_analysis.py','parallelism_progress.py','build_parallelism.py')
    return sorted(set([run.HERE/n for n in names]+build.dependencies()+
        [run.ROOT/'scripts'/n for n in ('experiment.py','environment_controls.py','monitor_host.py')]+
        [PROTOCOL,RESEARCH,run.ROOT/'analysis/runtime_io_prior_art_review/existing_followup_summary.json']))


def create(session,value):
    run.require_quiet_host();time_offsets();session.mkdir(parents=True,exist_ok=False);(session/'attempts').mkdir()
    meta=dict(schema=run.SCHEMA,study='bursty_parallelism_v1',created=run.now(),pilot=False,eligible_for_full=False,
        source_sha256=run.hashes(sources()),build=value,build_manifest_sha256=run.sha(build.DEFAULT/'build.json'),
        fixture_manifest_sha256=run.sha(build.DEFAULT/'functional_verification.json'),
        topology=run.old.check_topology(),server_cpus=run.old.CPUS,client_cpus=run.old.CLIENT_CPUS,
        kernel=run.capture(['uname','-a']),python=sys.version,power_settings=run.power_settings(include_profile=True),
        source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json'))
    run.put(session/'matrix.json',matrix(value));meta['matrix_sha256']=run.sha(session/'matrix.json')
    for p in sources():
        target=session/'source'/p.relative_to(run.ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    shutil.copytree(build.DEFAULT,session/'stock_build')
    shutil.copy2(run.ORIGINAL/'calibration.json',session/'original_calibration.json')
    run.put(session/'metadata.json',meta)


def verify_session(session,current=True):
    meta=run.read(session/'metadata.json')
    if meta['study']!='bursty_parallelism_v1' or meta['schema']!=run.SCHEMA or meta['pilot']:
        raise ValueError('not a standalone bursty parallelism session')
    if run.sha(session/'matrix.json')!=meta['matrix_sha256'] or run.read(session/'matrix.json')!=matrix(meta['build']):
        raise ValueError('frozen matrix changed')
    if current and run.hashes(sources())!=meta['source_sha256']:raise ValueError('source/protocol/research context changed')
    for name,digest in meta['source_sha256'].items():
        if run.sha(session/'source'/name)!=digest:raise ValueError('frozen source changed: '+name)
    frozen=session/'stock_build'
    if run.sha(frozen/'build.json')!=meta['build_manifest_sha256'] or run.read(frozen/'build.json')!=meta['build']:
        raise ValueError('frozen stock build changed')
    if build.prepared_hashes(frozen/'prepared')!=meta['build']['prepared_sha256'] or run.sha(frozen/'loadgen')!=meta['build']['loadgen_sha256']:
        raise ValueError('frozen prepared source/client changed')
    checks=run.read(frozen/'functional_verification.json')
    if run.sha(frozen/'functional_verification.json')!=meta['fixture_manifest_sha256']:
        raise ValueError('frozen functional verification changed')
    for name,digest in checks['files_sha256'].items():
        if run.sha(frozen/name)!=digest:raise ValueError('frozen functional fixture changed')
    if run.sha(session/'original_calibration.json')!=meta['source_calibration_sha256']:
        raise ValueError('frozen calibration changed')
    if current and (build.verify()!=meta['build'] or run.sha(run.ORIGINAL/'calibration.json')!=meta['source_calibration_sha256']):
        raise ValueError('current build/calibration differs from session')
    return meta


def validate_attempt(attempt,config):
    errors=run.validation_errors(attempt,config,False)
    if errors:raise ValueError('invalid raw attempt: '+'; '.join(errors))
    client=run.read(attempt/'loadgen.json');server=run.read(attempt/'server_metrics.json')
    report=run.read(attempt/'result.json')
    namespaces=run.read(attempt/'time_namespaces.json')
    expected={'monotonic':[0,0],'boottime':[0,0]}
    if namespaces['host']!=expected or namespaces['container']!=expected:
        raise ValueError('shifted or missing clock namespace evidence')
    for state in (report['runtime'],report['runtime_end'],server):
        if state['runtime_capture'] or state['custom_recording'] or state['runtime_variant']!='stock':
            raise ValueError('runtime patch or observer enabled')
    return analysis.entry_analysis(client,server)


def collect(directory):
    value=build.verify();session=directory/'session'
    with run.acquire_experiment_lock():
        if not session.exists():create(session,value)
        meta=verify_session(session)
        if run.old.check_topology()!=meta['topology']:raise ValueError('CPU topology changed')
        if run.capture(['docker','ps','-a','-q','--filter',f'label=quota.diagnostic.session={session}']):
            raise ValueError('previous owned container remains; inspect before resuming')
        plan=run.read(session/'matrix.json');pending=[];completed=0
        for c in plan:
            good=[p for p in run.attempt_dirs(session/'attempts'/c['run_id']) if run.validate(p,c,False)]
            if len(good)>1:raise ValueError('multiple valid attempts')
            if good:validate_attempt(good[0],c);completed+=1
            else:pending.append(c)
        run.put(session/'status.json',dict(completed=completed,total=8,state='running' if pending else 'complete',current=None))
        if pending:run.require_quiet_host();run.old.prepare_environment(session)
        previous_client=run.LOADGEN;run.LOADGEN=session/'stock_build/loadgen'
        try:
            for c in pending:
                verify_session(session)
                run.put(session/'status.json',dict(completed=completed,total=8,state='running',current=c['run_id']))
                print('RUN',completed+1,'/8',c['run_id'],flush=True)
                attempt=run_checked_attempt(session,c,run.next_attempt(session/'attempts'/c['run_id']))
                validate_attempt(attempt,c);completed+=1
                run.put(session/'status.json',dict(completed=completed,total=8,state='running',current=None,last_completed=c['run_id']))
                temps=run.old.temperatures()
                print(f'DONE {completed}/8 ({100*completed/8:.1f}%) {c["run_id"]} | '+
                    ', '.join(f'{k}={v:.1f}°C' for k,v in sorted(temps.items())),flush=True)
            run.put(session/'status.json',dict(completed=completed,total=8,state='complete'))
        except BaseException as exc:
            run.put(session/'status.json',dict(completed=completed,total=8,state='interrupted',error=str(exc)));raise
        finally:run.LOADGEN=previous_client


def analyze_results(directory):
    session=directory/'session';verify_session(session,current=False);rows=[];entries={};seals={}
    for order,c in enumerate(run.read(session/'matrix.json'),1):
        good=[p for p in run.attempt_dirs(session/'attempts'/c['run_id']) if run.validate(p,c,False)]
        if len(good)!=1:raise ValueError('one validated attempt required: '+c['run_id'])
        attempt=good[0];validate_attempt(attempt,c);row,entry=analysis.trial_row(order,c,attempt)
        rows.append(row);entries[c['run_id']]=entry;seals[c['run_id']]=dict(attempt=attempt.name,sha256=run.sha(attempt/'complete.json'))
    screen=analysis.comparison(rows);out=session/'analysis';out.mkdir(exist_ok=True)
    analyze.writecsv(out/'trials.csv',rows);run.put(out/'entry_delays.json',entries);run.put(out/'remedy_screen.json',screen)
    lines=['# Existing parallelism remedy under bursty half-CPU load','',
        'Eight stock-Go trials; four paired GOMAXPROCS=1/2 contrasts. Four application workers and nominal CPU budget remain fixed. '
        'No runtime tracing, queue observer, scheduler patch or worker yielding.','',
        '| Block | GOMAXPROCS | Long entry fraction lower–upper | Missing entries | Success p99 ms | Success/s in window | Failure fraction | CPU/job us |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        p99=f'{r["p99_e2e_ms"]:.3f}' if r['p99_e2e_ms'] is not None else 'unavailable'
        cpu=f'{r["cpu_usec_per_completed_work"]:.3f}' if r['cpu_usec_per_completed_work'] is not None else 'unavailable'
        lines.append(f'| {r["rep"]} | {r["gomaxprocs"]} | {r["certainly_long_entry_rate"]:.3%}–{r["possibly_long_entry_rate"]:.3%} | '
            f'{r["missing_entry_count"]} | {p99} | {r["successful_rps"]:.3f} | '
            f'{r["failure_fraction"]:.3%} | {cpu} |')
    lines+=['',f'Diagnostic interpretation: **{screen["interpretation"]}**.','',
        'remedy_screen.json retains every predeclared criterion, four pair results and ratios of trial medians. '
        'Passing is a practical diagnostic screen, not a significance test, production SLO or novelty claim.','',
        'Entry delays retain successes, rejections and cancellations. Missing entries are unknown and widen the upper bound; '
        'they are never assigned zero delay. entry_delays.json contains every offered ID, interval bounds and one/five-second horizons. '
        'Clock round trips occur before arrivals and after client drain; monotonic offset brackets are intersected, never replaced by a midpoint.','',
        'Successful E2E percentiles remain conditional on success. The throughput column counts successes completed within the measurement window; '
        'cohort and drain throughput are separate in trials.csv. Server CPU accounting includes workload/drain and clock-control requests, '
        'but excludes final metrics export. Different CPU/job costs can change capacity and cannot be attributed entirely to fairness.','',
        'Scheduled-to-entry includes client dispatch lag. Dispatch-to-entry begins at the client request worker, not an exact wire-send or network-ready event. '
        'This stock comparison cannot identify ready-queue residence, runnext starvation or continuous CPU execution.','',
        'If the existing remedy suffices, report a known remedy validated in this case. If delay migrates into queueing/failures, inspect that tradeoff. '
        'If long entry delays remain, localize the residual with a separately controlled queue-history observer. '
        'If baseline symptom or coverage checks fail, repair the named measurement problem. No further experiment is automatically launched.','',
        '[Frozen research comparison](../source/docs/runtime_io_prior_art_review.md)',
        '[Frozen protocol](../source/docs/runtime_io_v12_parallelism_commands.md)','']
    (out/'report.md').write_text('\n'.join(lines));run.put(out/'validation.json',dict(passed=True,trials=8,performance_trial_validation=True))
    names=('trials.csv','entry_delays.json','remedy_screen.json','validation.json')
    run.put(directory/'completion.json',dict(at=run.now(),report_sha256=run.sha(out/'report.md'),
        analysis_sha256={n:run.sha(out/n) for n in names},attempts=seals,eligible_for_full=False))
    pipeline.update_status(directory,'complete','complete',report=str(out/'report.md'))
    print('BURSTY PARALLELISM COMPLETE:',out/'report.md',flush=True)


def verify_completion(directory):
    verify_session(directory/'session',current=False);value=run.read(directory/'completion.json')
    out=directory/'session/analysis'
    if run.sha(out/'report.md')!=value['report_sha256']:raise ValueError('completed report changed')
    for name,digest in value['analysis_sha256'].items():
        if run.sha(out/name)!=digest:raise ValueError('completed analysis changed')
    plan=run.read(directory/'session/matrix.json')
    for c in plan:
        seal=value['attempts'][c['run_id']];attempt=directory/'session/attempts'/c['run_id']/seal['attempt']
        if run.sha(attempt/'complete.json')!=seal['sha256']:raise ValueError('completed attempt changed')
        validate_attempt(attempt,c)


def status(directory):
    if not (directory/'workflow-status.json').exists():
        print('Bursty parallelism study has not started:',directory)
        progress_display.print_progress(progress_display.snapshot(directory));return
    pipeline.print_status(directory)
    progress_display.print_progress(progress_display.snapshot(directory))


def foreground(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM,lambda *a: (_ for _ in ()).throw(KeyboardInterrupt('signal TERM')))
        pipeline.update_status(directory,'running','preflight',worker_pid=os.getpid(),error=None)
        try:
            run.require_quiet_host();pipeline.update_status(directory,'running','collect-8-trials');collect(directory)
            pipeline.update_status(directory,'running','analyze-remedy-sufficiency');analyze_results(directory)
        except BaseException as exc:
            pipeline.update_status(directory,'interrupted' if isinstance(exc,KeyboardInterrupt) else 'failed',
                run.read(directory/'workflow-status.json')['stage'],error=str(exc));traceback.print_exc();return 1
    return 0


def launch(directory):
    directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.launch.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if pipeline.is_running(directory):status(directory);return 0
        if (directory/'completion.json').exists():verify_completion(directory);status(directory);return 0
        run.require_quiet_host();build.verify()
        if (directory/'session').exists():verify_session(directory/'session')
        inhibitor=shutil.which('systemd-inhibit')
        if not inhibitor:raise ValueError('systemd-inhibit is required')
        (directory/'logs').mkdir(exist_ok=True);logfile=directory/'logs'/f'{time.time_ns()}-{uuid.uuid4().hex[:8]}.log'
        command=[inhibitor,'--no-ask-password','--what=idle:sleep','--mode=block','--who=Bursty parallelism study',
            '--why=Quiet controlled measurements','--',sys.executable,'-u',str(Path(__file__).resolve()),
            'foreground','--directory',str(directory)]
        pipeline.update_status(directory,'starting','launch',error=None,sleep_inhibitor=True)
        with logfile.open('x') as stream:
            process=subprocess.Popen(command,cwd=run.ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        run.put(directory/'launch.json',dict(pid=process.pid,start_tick=pipeline.process_signature(process.pid),
            log=str(logfile),command=command,at=run.now()))
        for _ in range(100):
            if run.read(directory/'workflow-status.json')['state']!='starting' or process.poll() is not None:break
            time.sleep(.1)
        if process.poll() is not None and run.read(directory/'workflow-status.json')['state']=='starting':
            pipeline.update_status(directory,'failed','launch',error=logfile.read_text()[-3000:])
        status(directory)
        if pipeline.is_running(directory):print('Started in background with sleep inhibition.',flush=True);return 0
        return 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('start','status','watch','foreground','analyze','verify-build'))
    p.add_argument('--interval',type=float,default=5,help='watch refresh seconds (minimum two)')
    p.add_argument('--directory',type=Path,default=DEFAULT);a=p.parse_args();directory=a.directory.resolve()
    if a.command=='start':raise SystemExit(launch(directory))
    elif a.command=='status':status(directory)
    elif a.command=='watch':progress_display.watch(directory,a.interval)
    elif a.command=='foreground':raise SystemExit(foreground(directory))
    elif a.command=='analyze':
        if (directory/'completion.json').exists():verify_completion(directory);status(directory)
        else:analyze_results(directory)
    else:build.verify();print('Stock build verified; no performance trials launched.')
