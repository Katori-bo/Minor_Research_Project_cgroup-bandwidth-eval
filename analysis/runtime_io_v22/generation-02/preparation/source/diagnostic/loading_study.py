#!/usr/bin/env python3
"""Sixteen matched packaged/shared executable trials, with sealed evidence and resume."""
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
import build_loading as build
import loading_analysis as analysis
import loading_identity
import parallelism_analysis as stock_analysis
import parallelism_progress as progress
import parallelism_study as stock_study
import pipeline
import run

DEFAULT=run.ROOT/'results/diagnostic/runtime-io-v17-shared-loading-1'
PROTOCOL=run.ROOT/'docs/runtime_io_v17_loading_protocol.md'
# Deterministic Williams orders balance position and within-block carryover.
ORDERS=(('legacy_packaged','rebuilt_packaged','rebuilt_shared','legacy_shared'),
        ('rebuilt_packaged','legacy_shared','legacy_packaged','rebuilt_shared'),
        ('legacy_shared','rebuilt_shared','rebuilt_packaged','legacy_packaged'),
        ('rebuilt_shared','legacy_packaged','legacy_shared','rebuilt_packaged'))
TOTAL=16


def matrix(value,assets=None):
    images=value['images']
    if set(images)!=set(analysis.ARMS) or images['legacy_packaged']!=images['legacy_shared'] or images['rebuilt_packaged']!=images['rebuilt_shared']:
        raise ValueError('each image must remain identical across loading modes')
    assets=assets or DEFAULT/'session/loading_build/runtime_assets'
    cal=run.read(run.ORIGINAL/'calibration.json')
    if cal['high_rps']!=113.21 or cal['iterations']!=44000: raise ValueError('discovery calibration changed')
    return [dict(study='shared_executable_loading_v1',run_id=f'loading_b{block}_{arm}',rep=block,
        recorder_arm=arm,parallelism_arm='g1',gomaxprocs=1,workers=4,period_us=100000,quota_us=50000,
        pattern='bursty',rate=cal['high_rps'],burst_low=cal['high_rps']*.5,burst_high=cal['high_rps']*1.5,
        iterations=cal['iterations'],duration_sec=60,warmup_sec=20,timeout_sec=5,instrument=True,
        client_trace=True,runtime_trace=False,custom_recording=False,worker_yield=False,require_quiet=True,
        service_image=images[arm],loading_mode=analysis.MODES[arm],loading_assets=str(assets),
        shared_executable_sha256=value['server_sha256'],probe_sha256=value['probe_sha256'])
        for block,order in enumerate(ORDERS,1) for arm in order]


def sources():
    return sorted(set(stock_study.sources()+build.dependencies()+[Path(__file__),PROTOCOL,
        run.HERE/'loading_analysis.py',run.HERE/'test_loading.py',run.HERE/'start_loading_batch.sh',run.ROOT/'docs/current_research_plan.md']))


def create(session,value):
    run.require_quiet_host();stock_study.time_offsets()
    session.mkdir(parents=True,exist_ok=False);(session/'attempts').mkdir()
    meta=dict(schema=run.SCHEMA,study='shared_executable_loading_v1',created=run.now(),
        source_sha256=run.hashes(sources()),build=value,build_manifest_sha256=run.sha(build.DEFAULT/'build.json'),
        fixture_manifest_sha256=run.sha(build.DEFAULT/'functional_verification.json'),
        build_bundle_sha256=build.stock.prepared_hashes(build.DEFAULT),
        topology=run.old.check_topology(),server_cpus=run.old.CPUS,client_cpus=run.old.CLIENT_CPUS,
        kernel=run.capture(['uname','-a']),python=sys.version,power_settings=run.power_settings(include_profile=True),
        source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json'),eligible_for_full=False)
    run.put(session/'matrix.json',matrix(value,session/'loading_build/runtime_assets'));meta['matrix_sha256']=run.sha(session/'matrix.json')
    for p in sources():
        target=session/'source'/p.relative_to(run.ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    shutil.copytree(build.DEFAULT,session/'loading_build')
    shutil.copy2(run.ORIGINAL/'calibration.json',session/'original_calibration.json')
    assets=session/'loading_build/runtime_assets'
    run.put(session/'loading_assets_seal.json',{n:loading_identity.identity(assets/n) for n in ('shared.server','probe')})
    meta['loading_assets_seal_sha256']=run.sha(session/'loading_assets_seal.json')
    run.put(session/'metadata.json',meta)


def verify_environment(session,required=False):
    seal_path=session/'environment_seal.json'
    if not seal_path.exists():
        if required:raise ValueError('missing frozen environment seal')
        return
    value=run.read(seal_path)
    for name,digest in value['files_sha256'].items():
        if run.sha(session/name)!=digest:raise ValueError('frozen environment changed: '+name)


def prepare_environment(session):
    # Establish once from quiet idle, then verify rather than silently rebaseline.
    verify_environment(session,required=any((session/'attempts').glob('*/*/complete.json')))
    run.old.prepare_environment(session)
    seal_path=session/'environment_seal.json'
    if seal_path.exists():return
    env=run.read(session/'environment.json');thermal=run.read(session/'initial-settling.json')
    samples=thermal['samples'];elapsed=samples[-1]['elapsed_sec'];index=0
    while index+1<len(samples) and samples[index+1]['elapsed_sec']<=elapsed-run.POLICY['window_sec']:index+=1
    summary=run.window_summary(samples[index:])
    if env['policy']!=run.POLICY or thermal['policy']!=run.POLICY or not thermal['accepted'] or elapsed<run.POLICY['initial_idle_sec'] or not summary or not summary['stable']:
        raise ValueError('initial environment window not valid')
    if env['baseline_c']!={k:v['mean_c'] for k,v in summary['sensors'].items()} or any(s['power_settings']!=run.comparable_power(env['power_settings']) for s in samples):
        raise ValueError('baseline differs from accepted idle evidence')
    run.put(seal_path,dict(at=run.now(),files_sha256={n:run.sha(session/n) for n in ('environment.json','initial-settling.json')}))


def verify_session(session,current=True):
    meta=run.read(session/'metadata.json')
    if meta['study']!='shared_executable_loading_v1' or meta['schema']!=run.SCHEMA: raise ValueError('wrong session')
    if run.sha(session/'matrix.json')!=meta['matrix_sha256'] or run.read(session/'matrix.json')!=matrix(meta['build'],session/'loading_build/runtime_assets'):
        raise ValueError('frozen matrix changed')
    if current and run.hashes(sources())!=meta['source_sha256']: raise ValueError('source/protocol changed')
    for name,digest in meta['source_sha256'].items():
        if run.sha(session/'source'/name)!=digest: raise ValueError('frozen source changed: '+name)
    frozen=session/'loading_build'
    if build.stock.prepared_hashes(frozen)!=meta['build_bundle_sha256']: raise ValueError('frozen build bundle changed')
    if run.sha(frozen/'build.json')!=meta['build_manifest_sha256'] or run.read(frozen/'build.json')!=meta['build']:
        raise ValueError('frozen build changed')
    if build.stock.prepared_hashes(frozen/'prepared')!=meta['build']['prepared_sha256'] or run.sha(frozen/'loadgen')!=meta['build']['loadgen_sha256']:
        raise ValueError('frozen source/binary changed')
    if run.sha(frozen/'functional_verification.json')!=meta['fixture_manifest_sha256']: raise ValueError('fixture seal changed')
    # The complete bundle seal above covers each fixture, probe and binary.
    if not run.read(frozen/'functional_verification.json')['passed']:
        raise ValueError('functional loading qualification failed')
    if run.sha(session/'original_calibration.json')!=meta['source_calibration_sha256']: raise ValueError('calibration changed')
    if current and (build.verify()!=meta['build'] or run.sha(run.ORIGINAL/'calibration.json')!=meta['source_calibration_sha256']):
        raise ValueError('current build/calibration changed')
    verify_environment(session,required=any((session/'attempts').glob('*/*/complete.json')))
    verify_assets(session,meta,current)
    return meta


def verify_assets(session,meta,current=True):
    if run.sha(session/'loading_assets_seal.json')!=meta['loading_assets_seal_sha256']:
        raise ValueError('loading asset identity seal changed')
    seal=run.read(session/'loading_assets_seal.json')
    if current:
        for name,value in seal.items():
            if loading_identity.identity(session/'loading_build/runtime_assets'/name)!=value:
                raise ValueError('same-file asset identity changed: '+name)


def validate_attempt(attempt,config):
    errors=run.validation_errors(attempt,config,False)
    if errors: raise ValueError('invalid raw attempt: '+'; '.join(errors))
    namespaces=run.read(attempt/'time_namespaces.json');expected={'monotonic':[0,0],'boottime':[0,0]}
    if namespaces['host']!=expected or namespaces['container']!=expected: raise ValueError('shifted time namespace')
    evidence=run.read(attempt/'file_loading.json')
    loading_identity.validate(evidence,config['loading_mode'],Path(config['loading_assets']),config['shared_executable_sha256'],config['probe_sha256'])
    if evidence['collection']!='startup_before_warmup' or evidence['expected_image_id']!=config['service_image']:
        raise ValueError('loading startup provenance differs')
    seal=run.read(attempt.parents[2]/'loading_assets_seal.json')
    if evidence['host_shared_identity']!=seal['shared.server'] or evidence['host_probe_identity']!=seal['probe']:
        raise ValueError('trial backing files differ from session identity seal')
    report=run.read(attempt/'result.json');server=run.read(attempt/'server_metrics.json')
    for state in (report['runtime'],report['runtime_end'],server):
        analysis.validate_state(state,config['recorder_arm'])
    return analysis.classify(run.read(attempt/'loadgen.json'),server,config['recorder_arm'])


def attempt_check(attempt,config):
    try:
        validate_attempt(attempt,config)
        return dict(run_id=config['run_id'],attempt=attempt.name,valid=True,error=None)
    except (ValueError,KeyError,TypeError,OSError) as exc:
        return dict(run_id=config['run_id'],attempt=attempt.name,valid=False,error=str(exc))


def baseline_drain(timeout=30):
    end=time.monotonic()+timeout
    while True:
        state=run.get('health')
        if state['admitted']==state['completed'] and state['queue_len']==state['active_handlers']==0 and not state.get('trace_pending_responses',0) and not state.get('observer_pending_records',0):
            return state
        if time.monotonic()>=end: raise RuntimeError('work/handler/observer drain timed out')
        time.sleep(.1)


def run_loading_attempt(session,config,number):
    # Extend only this study; leave historical runners and service binaries intact.
    assets=Path(config['loading_assets'])
    original_capture,original_cgroup,original_drain=run.capture,run.old.cgroup_path,run.drain
    container_id=None
    def capture(args):
        nonlocal container_id
        if args[:2]==['docker','create']:
            if args[-1]!=config['service_image'] or '--label' not in args or args[args.index('--label')+1]!=f'quota.diagnostic.session={session}':
                raise ValueError('unexpected container creation in loading attempt')
            args[-1:-1]=loading_identity.mount_arguments(assets,config['loading_mode'])
            container_id=original_capture(args)
            return container_id
        return original_capture(args)
    def checked_cgroup(pid):
        if not container_id:raise ValueError('missing owned container')
        evidence=loading_identity.collect(container_id,assets,config['loading_mode'],config['service_image'],config['shared_executable_sha256'],config['probe_sha256'])
        path=session/'attempts'/config['run_id']/f'{number:03d}'/'file_loading.json'
        run.put(path,evidence)
        return original_cgroup(pid)
    run.capture=capture;run.old.cgroup_path=checked_cgroup;run.drain=baseline_drain
    try:return stock_study.run_checked_attempt(session,config,number)
    finally:run.capture=original_capture;run.old.cgroup_path=original_cgroup;run.drain=original_drain


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
            good=[p for p in run.attempt_dirs(session/'attempts'/c['run_id']) if attempt_check(p,c)['valid']]
            if len(good)>1: raise ValueError('multiple valid attempts')
            if good: validate_attempt(good[0],c);completed+=1
            else: pending.append(c)
        run.put(session/'status.json',dict(completed=completed,total=len(plan),state='running',current=None))
        previous=run.LOADGEN;run.LOADGEN=session/'loading_build/loadgen'
        try:
            if pending: run.require_quiet_host();prepare_environment(session)
            for c in pending:
                verify_session(session)
                run.put(session/'status.json',dict(completed=completed,total=len(plan),state='running',current=c['run_id']))
                print('RUN',completed+1,'/16',c['run_id'],flush=True)
                attempt=run_loading_attempt(session,c,run.next_attempt(session/'attempts'/c['run_id']))
                validate_attempt(attempt,c);completed+=1
                run.put(session/'status.json',dict(completed=completed,total=len(plan),state='running',current=None,last_completed=c['run_id']))
                temps=run.old.temperatures()
                print(f'DONE {completed}/16 ({100*completed/16:.1f}%) {c["run_id"]} | '+
                    ', '.join(f'{k}={v:.1f}°C' for k,v in sorted(temps.items())),flush=True)
            run.put(session/'status.json',dict(completed=completed,total=len(plan),state='complete'))
        except BaseException as exc:
            run.put(session/'status.json',dict(completed=completed,total=len(plan),state='interrupted',error=str(exc)));raise
        finally: run.LOADGEN=previous


def analyze_results(directory):
    session=directory/'session';verify_session(session,current=False)
    if (directory/'completion.json').exists(): verify_completion(directory);return
    rows=[];request_rows=[];seals={};schedules={};attempt_audit=[]
    for order,c in enumerate(run.read(session/'matrix.json'),1):
        attempts=run.attempt_dirs(session/'attempts'/c['run_id'])
        checks=[attempt_check(p,c) for p in attempts];attempt_audit.extend(checks)
        good=[p for p,check in zip(attempts,checks) if check['valid']]
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
            record_errors=run.read(attempt/'server_metrics.json').get('record_errors',0),
            observer_dropped_records=run.read(attempt/'server_metrics.json').get('observer_dropped_records',0))
        row['failure_fraction']=entry['deadlines']['500']['failure_fraction'];rows.append(row)
        for r in entry['requests']: request_rows.append(dict(run_id=c['run_id'],rep=c['rep'],recorder_arm=c['recorder_arm'],**r))
        seals[c['run_id']]=dict(attempt=attempt.name,sha256=run.sha(attempt/'complete.json'))
    screen=analysis.compare(rows)
    screen['shared_executable_sha256']=run.read(session/'metadata.json')['build']['server_sha256']
    screen['startup_loading_verified']=True
    out=session/'analysis';out.mkdir(exist_ok=True)
    analyze.writecsv(out/'trials.csv',rows);analyze.writecsv(out/'requests.csv',request_rows)
    run.put(out/'attempt_audit.json',attempt_audit)
    run.put(out/'loading_screen.json',screen)
    run.put(out/'validation.json',dict(passed=True,trials=16,matched_schedules=True,performance_trial_validation=True))
    lines=['# Packaged versus common-file executable loading','',
        'Four matched four-arm blocks at GOMAXPROCS=1, four workers, 50 ms / 100 ms quota, zero burst credits. '
        'All offered requests remain in the 500 ms primary and 1,000 ms guardrail denominators.','',
        '| Block | Arm | Timely 500 ms | Timely 1,000 ms | Failures | Late successes: work before 500 ms | CPU/job us | Queue p99 ms | Post-work p99 ms |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        cpu='unavailable' if r['cpu_usec_per_completed_work'] is None else f'{r["cpu_usec_per_completed_work"]:.2f}'
        def stage(k):return 'unavailable' if r.get(k) is None else f'{r[k]:.2f}'
        lines.append(f'| {r["rep"]} | {r["recorder_arm"]} | {r["timely_500_fraction"]:.3%} | '
            f'{r["timely_1000_fraction"]:.3%} | {r["failure_fraction"]:.3%} | {r["late_success_work_before"]} | {cpu} | '
            f'{stage("p99_queue_ms")} | {stage("p99_post_work_ms")} |')
    lines+=['','## Declared paired contrasts','',
        '| Contrast | Block | Timely 500 ms delta, pp | Timely 1,000 ms delta, pp | CPU/job change | Successful p99 change | Within practical margins |',
        '|---|---:|---:|---:|---:|---:|---|']
    for contrast in screen['contrasts'].values():
        for pair in contrast['pairs']:
            def change(k):return 'unavailable' if pair[k] is None else f'{100*(pair[k]-1):+.2f}%'
            lines.append(f'| {contrast["base"]} → {contrast["arm"]} | {pair["block"]} | '
                f'{100*pair["timely_fraction_delta"]:+.2f} | {100*pair["timely_1000_fraction_delta"]:+.2f} | '
                f'{change("cpu_ratio")} | {change("p99_ratio")} | {pair["within_screen"]} |')
    lines+=['','## Loading interaction','',
        'Shared-image contrast minus packaged-image contrast; CPU and p99 are ratios of ratios.','',
        '| Block | 500 ms interaction, pp | 1,000 ms interaction, pp | CPU ratio-of-ratios change | p99 ratio-of-ratios change |',
        '|---|---:|---:|---:|---:|']
    for pair in screen['loading_interaction']['pairs']:
        def change(k):return 'unavailable' if pair[k] is None else f'{100*(pair[k]-1):+.2f}%'
        lines.append(f'| {pair["block"]} | {100*pair["timely_fraction_delta"]:+.2f} | '
            f'{100*pair["timely_1000_fraction_delta"]:+.2f} | {change("cpu_ratio")} | {change("p99_ratio")} |')
    lines+=['',f'Loading discovery decision: **{screen["decision"]}**.','',
        'loading_screen.json retains paired deltas, block median/range and standard deviation, and the loading interaction. '
        'Four discovery blocks cannot establish statistical equivalence. Both retained images use their packaged executable '
        'and the exact common read-only file. Every arm has the same startup executable-provenance check before warmup. '
        'Actual mounts and process executable hashes are verified; shared arms also match the common device/inode identity. '
        'A missing packaged gap prevents claiming shared loading removed it. No publication timestamps are added. '
        'No filesystem/cache/scheduler cause or next-stage qualification follows automatically.','',
        'requests.csv retains failed, cancelled, late and drained outcomes, missing worker/handler events, clock bounds, '
        'and existing computation/handler deadline-crossing classes. Publication and mutex-boundary fields remain explicitly unobserved. '
        'Handler execution is not a runnable-readiness timestamp. Wall intervals include scheduling and off-CPU delays. '
        'Host/cgroup samples and CPU counters remain sealed, but do not identify instantaneous remaining quota or request-level throttle intervals. '
        'Further runtime/kernel observation requires a separate qualification.','',
        '[Frozen protocol](../source/docs/runtime_io_v17_loading_protocol.md)','']
    (out/'report.md').write_text('\n'.join(lines))
    names=('trials.csv','requests.csv','loading_screen.json','validation.json','attempt_audit.json','report.md')
    run.put(directory/'completion.json',dict(at=run.now(),analysis_sha256={n:run.sha(out/n) for n in names},attempts=seals,eligible_for_full=False,
        environment_seal_sha256=run.sha(session/'environment_seal.json'),
        loading_assets_seal_sha256=run.sha(session/'loading_assets_seal.json')))
    pipeline.update_status(directory,'complete','complete',report=str(out/'report.md'))
    print('SHARED LOADING SCREEN COMPLETE:',out/'report.md',flush=True)


def verify_completion(directory):
    session=directory/'session';verify_session(session,current=False);value=run.read(directory/'completion.json')
    if run.sha(session/'environment_seal.json')!=value['environment_seal_sha256']:raise ValueError('environment seal changed')
    if run.sha(session/'loading_assets_seal.json')!=value['loading_assets_seal_sha256']:raise ValueError('loading asset identity seal changed')
    for name,digest in value['analysis_sha256'].items():
        if run.sha(session/'analysis'/name)!=digest: raise ValueError('completed analysis changed')
    for c in run.read(session/'matrix.json'):
        seal=value['attempts'][c['run_id']];attempt=session/'attempts'/c['run_id']/seal['attempt']
        if run.sha(attempt/'complete.json')!=seal['sha256']: raise ValueError('attempt seal changed')
        validate_attempt(attempt,c)


def status(directory):
    if (directory/'workflow-status.json').exists(): pipeline.print_status(directory)
    value=snapshot(directory);progress.print_progress(value);print('Trials remaining:',value['remaining'])


def snapshot(directory):
    value=progress.snapshot(directory)
    if not (directory/'session/status.json').exists(): value.update(total=16)
    if value['stage']=='analyze-loading' and value['state']=='running': value['phase']='analysis'
    value['remaining']=max(0,value['total']-value['completed'])
    return value


def watch(directory,interval=5):
    if interval<2: raise ValueError('watch interval must be at least two seconds')
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{int(c) for c in run.old.CLIENT_CPUS.split(',')})
    try:
        while True:
            value=snapshot(directory)
            if sys.stdout.isatty(): print('\033[2J\033[H',end='')
            print('Shared executable loading pilot | '+run.now())
            print(f'State: {value["state"]} | Stage: {value["stage"]}')
            progress.print_progress(value)
            print('Trials remaining:',value['remaining'])
            if value['log']: print('Log:',value['log'])
            print('Ctrl+C closes this display.',flush=True)
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
            run.require_quiet_host();pipeline.update_status(directory,'running','collect-16-trials');collect(directory)
            pipeline.update_status(directory,'running','analyze-loading');analyze_results(directory)
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
        command=[inhibitor,'--no-ask-password','--what=idle:sleep','--mode=block','--who=Shared executable loading pilot',
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


def stop(directory):
    if not pipeline.is_running(directory):
        status(directory);return
    launch_state=run.read(directory/'launch.json')
    worker=run.read(directory/'workflow-status.json')['worker_pid']
    if pipeline.process_signature(launch_state['pid'])!=launch_state['start_tick']:
        raise ValueError('launch PID changed; refusing signal')
    args=(Path('/proc')/str(worker)/'cmdline').read_bytes().split(b'\0')
    if os.fsencode(str(Path(__file__).resolve())) not in args or b'foreground' not in args or os.getpgid(worker)!=launch_state['pid']:
        raise ValueError('worker identity changed; refusing signal')
    os.kill(worker,signal.SIGTERM)
    for _ in range(50):
        if not pipeline.is_running(directory):break
        time.sleep(.1)
    status(directory)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('start','stop','foreground','status','watch','analyze','verify-build','verify-completion','plan'))
    p.add_argument('--directory',type=Path,default=DEFAULT);a=p.parse_args();directory=a.directory.resolve()
    if a.command=='start': sys.exit(launch(directory))
    elif a.command=='stop': stop(directory)
    elif a.command=='foreground': sys.exit(foreground(directory))
    elif a.command=='status': status(directory)
    elif a.command=='watch': watch(directory)
    elif a.command=='analyze': analyze_results(directory)
    elif a.command=='verify-completion': verify_completion(directory);print('Completed evidence verified.')
    elif a.command=='verify-build': build.verify();print('Build verified; no performance measurements launched.')
    else: print(__import__('json').dumps(matrix(dict(images=dict(legacy_packaged='unbuilt:legacy',legacy_shared='unbuilt:legacy',rebuilt_packaged='unbuilt:rebuilt',rebuilt_shared='unbuilt:rebuilt'),server_sha256='unbuilt',probe_sha256='unbuilt')),indent=2))
