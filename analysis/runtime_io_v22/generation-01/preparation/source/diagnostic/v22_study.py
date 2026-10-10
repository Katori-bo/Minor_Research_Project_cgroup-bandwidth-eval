#!/usr/bin/env python3
"""V22 preparation and bounded external collection; no new service/client binary."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
import urllib.request
import statistics

import v22_common as c
import v22_raw as analysis
import v22_model as model
import v22_verify as verify
from v22_service import Service, command, owned_inspect, remove_owned, LABEL
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures
import run
from environment_controls import POLICY, comparable_power, power_settings, window_summary


def require_quiet_host():
    run.require_quiet_host()
    result=subprocess.run(['pgrep','-x','ChatGPT|Codex'],capture_output=True,text=True)
    if result.returncode not in (0,1) or result.returncode==0:
        raise ValueError('fully quit Codex/ChatGPT before external measurement')


def bounded_settle(path, baseline=None, initial_idle=False, expected_power=None):
    start=time.monotonic();samples=[];minimum=600 if initial_idle else 60
    while True:
        elapsed=time.monotonic()-start
        settings=power_settings()
        if expected_power is not None and settings!=comparable_power(expected_power):
            raise ValueError('power settings changed during settling')
        samples.append(dict(elapsed_sec=elapsed,timestamp=time.time(),temperatures=run.old.temperatures(),power_settings=settings))
        c.save(path,dict(policy=POLICY,samples=samples,accepted=False))
        i=0
        while i+1<len(samples) and samples[i+1]['elapsed_sec']<=elapsed-60:i+=1
        summary=window_summary(samples[i:],baseline)
        if elapsed>=minimum and summary and summary['stable']:
            c.save(path,dict(policy=POLICY,samples=samples,accepted=True,summary=summary));return summary
        if elapsed>=1200:raise TimeoutError('frozen settling timeout1200s')
        if len(samples)%12==1:print(f'Settling {path.parent.name}: {elapsed:.0f}s',flush=True)
        time.sleep(5)


def update(session, config, stage):
    if config.get('functional'):return
    c.save(session/'progress.json',dict(trial=config['trial'],role=config['role'],order=config['order'],stage=stage,timestamp=time.time(),log=str(session)))
    print(f"{config['order']}/12 {config['trial']}: {stage}",flush=True)


def prediction_gate(session,directory):
    verify.verify_predictions(session)
    pm=c.read(session/'predictions/manifest.json')
    now=time.monotonic_ns()
    if now<pm['sealed_before_validation_monotonic_ns']:raise ValueError('prediction clock order failed')
    c.save(directory/'validation_authorization.json',dict(prediction_seal=c.digest(session/'predictions/seal.json'),monotonic_ns=now))

def load(directory, service, seconds, name, session, config):
    config = c.warmup_config(config) if name=='warmup' else config
    argv = [str(session/'preparation/loadgen'), '-url', service.base+'/work?iterations=44000',
        '-duration', str(seconds)+'s', '-rate', str(config['rate']), '-pattern', config['traffic_pattern'], '-burst-low', str(config['burst_low']),
        '-burst-high', str(config['burst_high']), '-burst-period', '10s', '-concurrency', '512',
        '-timeout', str(config['timeout_sec'])+'s', '-trace-client=true', '-output', str(directory/(name+'.json'))]
    c.save(directory/(name+'_argv.json'), argv)
    with (directory/(name+'.log')).open('x') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
            preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
        c.save(directory/(name+'_process.json'),c.process_identity(process.pid))
        try:
            until = time.monotonic()+seconds+30
            next_report = 0
            while process.poll() is None:
                if not config.get('functional'):require_quiet_host()
                service.observe()
                if time.monotonic() >= next_report:
                    update(session, config, name)
                    next_report = time.monotonic()+10
                if time.monotonic() > until:
                    raise TimeoutError('bounded retained-client timeout')
                time.sleep(1)
            if process.returncode:
                raise ValueError('retained loadgen failed')
        finally:
            fixtures.stop(process, signal.SIGTERM)


def drain(service, seconds=100):
    until = time.monotonic()+seconds
    while True:
        service.observe()
        server = bridge.get(service.base, 'metrics')
        if not server['active_handlers'] and not server['queue_len'] and server['completed'] == server['admitted']:
            return server
        if time.monotonic() > until:
            raise TimeoutError('full service drain timeout')
        time.sleep(1)


def reset(service):
    with urllib.request.urlopen(urllib.request.Request(service.base+'/reset', data=b'', method='POST'), timeout=3) as response:
        if response.status != 204:
            raise ValueError('metrics reset failed')
    return dict(monotonic_ns=time.monotonic_ns(), health=bridge.get(service.base, 'health'))


def collect(session, directory, config, mode, functional=False):
    if config['role']=='validation':
        verify.verify_predictions(session)
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'config.json', config)
    if config['role']=='validation':
        prediction_gate(session,directory)
    c.save(directory/'started.json', dict(monotonic_ns=time.monotonic_ns(),wall_time=time.time()))
    service = Service(session, config, directory)
    monitor = None
    monitor_log = None
    failure = None
    try:
        if not functional:
            environment = c.read(session/'environment.json')
            c.save(directory/'environment.json', environment)
            require_quiet_host()
            update(session, config, 'settling')
            bounded_settle(directory/'settling.json', environment['baseline_c'], expected_power=environment['power_settings'])
            c.capacity(session)
            if power_settings(include_profile=True) != environment['power_settings']:
                raise ValueError('power baseline changed')
        service.create()
        if not functional:
            monitor_log = (directory/'monitor.log').open('x')
            monitor = subprocess.Popen([sys.executable, str(c.ROOT/'scripts/monitor_host.py'),
                '--cgroup-path', str(service.group).removeprefix('/sys/fs/cgroup'),
                '--output', str(directory/'monitor.json')], stdout=monitor_log, stderr=subprocess.STDOUT,
                preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
            c.save(directory/'monitor_process.json',c.process_identity(monitor.pid))
        service.release()
        observations = dict(startup=service.observe())
        if not functional:
            load(directory, service, 20, 'warmup', session, config)
            c.save(directory/'warmup_server_metrics.json', drain(service))
            c.validate_client(c.read(directory/'warmup.json'), c.warmup_config(config))
        update(session, config, 'reset')
        c.save(directory/'reset.json', reset(service))
        anchors = bridge.anchors(service.base, 'start')
        observations['measurement_start'] = service.observe()
        load(directory, service, config['duration_sec'], 'loadgen', session, config)
        update(session, config, 'drain')
        server = drain(service)
        observations['measurement_stop'] = service.observe()
        anchors += bridge.anchors(service.base, 'stop')
        observations['final'] = service.observe()
        c.save(directory/'host_server_anchors.json', anchors)
        c.save(directory/'server_metrics.json', server)
        c.save(directory/'observations.json', observations)
        if not functional and power_settings(include_profile=True) != environment['power_settings']:
            raise ValueError('power changed during trial')
        if monitor:
            fixtures.stop(monitor, signal.SIGINT)
            if monitor.returncode:
                raise ValueError('host monitor failed')
            monitor_log.close()
            monitor = None
        service.close()
        c.seal(directory)
        derived = analysis.replay(directory, functional)
        c.save(directory/'derived.json', derived)
        if not functional:
            for name in ('warmup','loadgen'):c.technical_client(c.read(directory/(name+'.json')))
        c.save(directory/'complete.json', dict(valid=True, performance_run=not functional,
            functional=functional, finished=time.time()))
        c.seal(directory)
        return directory
    except BaseException as e:
        failure = str(e)
        c.save(directory/'interruption.json', dict(error=failure, time=time.time(), traceback=traceback.format_exc()))
        raise
    finally:
        if monitor:
            fixtures.stop(monitor, signal.SIGINT)
            monitor_log.close()
        try:
            service.close(failure)
        except Exception as e:
            c.save(directory/'cleanup_failure.json', dict(error=str(e)))
            if failure is None:
                raise
        finally:
            if failure:
                c.seal(directory)


def prepare(session):
    if os.geteuid()==0:raise ValueError('prepare as the normal user')
    if session.exists():raise ValueError('preserve existing generation; choose a new directory')
    c.design();c.PARENT.mkdir(parents=True,exist_ok=True);c.capacity(c.PARENT)
    c.verify_seal(c.ORIGINAL);previous=c.read(c.ORIGINAL/'manifest.json')
    sources=c.source_hashes();session.mkdir();prep=session/'preparation';prep.mkdir()
    try:
        for name,h in sources.items():
            target=prep/'source'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(c.ROOT/name,target)
            if c.digest(target)!=h:raise ValueError('source snapshot changed')
        for name in ('gate','loadgen','image.server','publication_source.go','publication_build.json'):
            shutil.copy2(c.ORIGINAL/name,prep/name)
        for name in c.read(c.DESIGN/'seal.json')['files_sha256']:
            target=prep/'scientific_design'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(c.ROOT/name,target)
        tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic','-p','test_v22.py','-v'],cwd=c.ROOT,capture_output=True,text=True,timeout=180)
        (prep/'tests.stdout').write_text(tests.stdout);(prep/'tests.stderr').write_text(tests.stderr)
        if tests.returncode:raise ValueError('V22 software verification failed')
        image=json.loads(command(['docker','image','inspect',previous['image']]))[0]
        c.save(prep/'image.json',image)
        manifest=dict(schema=1,generation=session.name,matrix=c.matrix(),sources=sources,
            baseline=c.baseline(),design_seal=c.digest(c.DESIGN/'seal.json'),
            original_preparation_seal=c.digest(c.ORIGINAL/'seal.json'),tests_passed=True,
            functional_passed=False,performance_run=False,
            **{k:previous[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline')})
        c.save(prep/'manifest.json',manifest)
        d=prep/'resource_preflight';d.mkdir();resource=Service(session,c.functional_configs()[0],d)
        try:
            resource.create()
            c.save(d/'observed.json',dict(gate_released=False,performance_run=False,limits=resource.expected_limits))
        finally:resource.close()
        functional={}
        for cfg in c.functional_configs():
            d=collect(session,prep/'functional'/cfg['trial'],cfg,'functional',True)
            functional[cfg['trial']]=dict(path=str(d.relative_to(prep)),seal=c.digest(d/'seal.json'))
            print('Functional '+cfg['trial']+': '+str(c.read(d/'derived.json')['summary']['outcome_counts']),flush=True)
        manifest.update(functional=functional,functional_passed=True,created=time.time())
        c.save(prep/'manifest.json',manifest)
        if c.source_hashes()!=sources:raise ValueError('sources changed during preparation')
        c.seal(prep);verify.verify_preparation(session)
        print('V22 prepared: '+str(session)+'; qualification/calibration/validation remain unrun.',flush=True)
    except BaseException as e:
        c.save(prep/'preparation_failure.json',dict(error=str(e),traceback=traceback.format_exc(),time=time.time()))
        c.seal(prep);raise


def freeze_predictions(session):
    m=verify.verify_qualification(session)
    if any(verify.attempts(session,cfg) for cfg in c.matrix() if cfg['role']=='validation'):
        raise ValueError('cannot create/recreate predictions after validation attempts')
    if (session/'predictions').exists():return verify.verify_predictions(session,recompute=True)
    cal,summary,per_id,refs=verify.make_forecast(session,m)
    out=session/'calibration_review';out.mkdir(exist_ok=False)
    c.save(out/'result.json',cal);c.seal(out)
    if not cal['passed']:
        c.save(session/'progress.json',dict(stage='calibration_stopped',decision=cal['decision'],timestamp=time.time()))
        return None
    p=session/'predictions';p.mkdir()
    c.save(p/'calibration.json',cal);c.save(p/'summary.json',summary);c.save(p/'per_id.json',per_id)
    c.save(p/'manifest.json',dict(schema=1,calibration_refs=refs,
        preparation_seal=c.digest(session/'preparation/seal.json'),environment_seal=c.digest(session/'environment_seal.json'),
        design_seal=c.digest(c.DESIGN/'seal.json'),sealed_before_validation_monotonic_ns=time.monotonic_ns(),wall_time=time.time()))
    c.seal(p);verify.verify_predictions(session,recompute=True)
    print('Calibration-only predictions sealed before validation.',flush=True)
    return summary


def environment(session):
    if (session/'environment.json').exists():
        env=verify.verify_environment(session)
        bounded_settle(session/('resume-settling-'+str(time.time_ns())+'.json'),env['baseline_c'],True,env['power_settings'])
        return
    settings=power_settings(include_profile=True)
    if settings['external_power'] and not any(v=='1' for v in settings['external_power'].values()):
        raise ValueError('external power required')
    if settings.get('desktop_profile') not in (None,'balanced'):raise ValueError('retained balanced profile required; no setting changed')
    summary=bounded_settle(session/'initial-settling.json',initial_idle=True,expected_power=settings)
    c.save(session/'environment.json',dict(policy=POLICY,power_settings=settings,baseline_c={k:v['mean_c'] for k,v in summary['sensors'].items()}))
    c.save(session/'environment_seal.json',dict(files_sha256={n:c.digest(session/n) for n in ('environment.json','initial-settling.json')}))
    verify.verify_environment(session)


def failures(session):
    return [p for cfg in c.matrix() for p in verify.attempts(session,cfg) if not (p/'complete.json').exists()]


def collect_slot(session,cfg):
    if verify.accepted(session,cfg) is not None:return
    while True:
        verify.verify_preparation(session)
        verify.verify_environment(session)
        if len(failures(session))>1:raise ValueError('one total technical retry exhausted')
        d=session/'slots'/cfg['trial']/('attempt-'+str(time.time_ns()))
        try:
            collect(session,d,cfg,'run')
            verify.verify_trial(session,d,c.read(session/'preparation/manifest.json'))
            return
        except (ValueError,RuntimeError,OSError,TimeoutError) as exc:
            if (d/'complete.json').exists():raise
            if not d.exists():raise
            cleanup=c.read(d/'cleanup.json') if (d/'cleanup.json').exists() else None
            if not cleanup or cleanup['errors'] or cleanup['watchdog_intervened']:
                raise ValueError('cleanup/watchdog failure stops generation') from exc
            verify.verify_preparation(session);verify.verify_environment(session)
            if len(failures(session))>1:raise
            print('One technical retry, same slot and fixed inputs: '+str(exc),flush=True)


def analyze(session):
    prediction=verify.verify_predictions(session,recompute=True,current=False)
    m=verify.verify_preparation(session,current=False)
    rows,refs=verify.validation_rows(session,m,prediction)
    report=model.report(rows,prediction)
    out=session/'analysis'/str(time.time_ns());out.mkdir(parents=True)
    c.save(out/'report.json',dict(result=report,validation_refs=refs,prediction_seal=c.digest(session/'predictions/seal.json'),
        technical_failures=[str(p.relative_to(session)) for p in failures(session)]))
    lines=['# V22 prospective prediction validation','', '**Decision: '+report['decision']+'**','',report['limits'],'',
        '| Trial | Observed misses % | Predicted misses % | Error pp | Primary pass |','|---|---:|---:|---:|---|']
    for t in rows:
        e=t['models']['M_busy'];forecast=prediction['point']['M_busy'][t['arm']]
        lines.append(f"| {t['trial']} | {t['observed']['miss_pct']:.3f} | {forecast['miss_pct']:.3f} | {e['errors']['miss_error_pp']:.3f} | {e['checks']['primary']} |")
    lines+=['','Queue/rejection/recovery support: '+str(report['supporting_queue_pass']),
            'Even-arrival screen: '+str(report['even_screen_pass']), 'Baseline advantage: '+str(report['baseline_advantage']),
            '','Per-trial stage, rare-tail, queue trajectory and clock-uncertainty diagnostics are retained in report.json.','']
    (out/'report.md').write_text('\n'.join(lines));c.seal(out)
    c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=c.digest(out/'seal.json')))
    verify.verify_completion(session)
    print('V22 analysis: '+report['decision']+'; '+str(out),flush=True)
    return out


def session_watchdog(session):
    state=c.read(session/'active_owner.json');deadline=c.read(session/'session_lifetime.json')['deadline_monotonic']
    while c.same_process(state['owner']) and not (session/'worker_finished.json').exists():
        if time.monotonic()>=deadline:
            os.kill(state['owner']['pid'],signal.SIGTERM)
            until=time.monotonic()+120
            while c.same_process(state['owner']) and time.monotonic()<until:time.sleep(.5)
            if c.same_process(state['owner']):os.kill(state['owner']['pid'],signal.SIGKILL)
            break
        time.sleep(.5)
    # Child identities are recorded before monitoring/loading, and scoped to this worker.
    for ownership in (session/'slots').glob('*/attempt-*/ownership.json'):
        d=ownership.parent;o=c.read(ownership)
        if o['owner']!=state['owner'] or (d/'cleanup.json').exists():continue
        for p in d.glob('*_process.json'):
            identity=c.read(p)
            if c.same_process(identity):os.kill(identity['pid'],signal.SIGTERM)
        remove_owned(o['container'],o['nonce'])


def foreground(session,mode):
    if os.geteuid()==0:raise ValueError('normal user orchestration required')
    os.sched_setaffinity(0,{0,1})
    def interrupted(signum,frame):raise InterruptedError('bounded session interrupted')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    with (session/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify.verify_preparation(session);require_quiet_host();run.old.check_topology()
        if mode=='run' and any((session/'slots').glob('*/attempt-*')):raise ValueError('existing slots; use explicit resume')
        if not (session/'session_lifetime.json').exists():
            now=time.monotonic();c.save(session/'session_lifetime.json',dict(started_monotonic=now,deadline_monotonic=now+5400,boot=c.baseline()['boot_id']))
        lifetime=c.read(session/'session_lifetime.json')
        if lifetime['boot']!=c.baseline()['boot_id'] or time.monotonic()>=lifetime['deadline_monotonic']:
            raise ValueError('session boot/time bound exhausted')
        if (session/'worker_finished.json').exists():
            raise ValueError('finished/stopped generation is retained; do not restart it')
        c.save(session/'active_owner.json',dict(owner=c.process_identity(os.getpid())))
        log=(session/('session_watchdog-'+str(time.time_ns())+'.log')).open('x')
        watcher=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'_watchdog','--directory',str(session)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            environment(session)
            for cfg in c.matrix():
                if cfg['role']=='validation':
                    if not (session/'predictions').exists():
                        if freeze_predictions(session) is None:return
                    verify.verify_predictions(session)
                collect_slot(session,cfg)
            analyze(session)
            c.save(session/'progress.json',dict(stage='complete',timestamp=time.time(),log=str(session)))
        except BaseException as exc:
            c.save(session/'worker_interruption.json',dict(error=str(exc),time=time.time(),traceback=traceback.format_exc()))
            raise
        finally:
            c.save(session/'worker_finished.json',dict(time=time.time(),status=c.read(session/'progress.json').get('stage') if (session/'progress.json').exists() else 'interrupted'))
            fixtures.stop(watcher,signal.SIGTERM);log.close()


def status(session):
    slots={role:0 for role in ('qualification','calibration','validation')}
    for cfg in c.matrix():
        if verify.accepted(session,cfg) is not None:slots[cfg['role']]+=1
    return dict(generation=str(session),completed=slots,predictions_sealed=(session/'predictions/seal.json').exists(),
        progress=c.read(session/'progress.json') if (session/'progress.json').exists() else {'stage':'prepared'},
        counts_are_markers_full_verification_separate=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare','verify-preparation','verify-predictions','verify-completion','analyze','status','stop','_foreground','_watchdog'])
    p.add_argument('--directory',required=True);p.add_argument('--mode',choices=['run','resume'],default='run');args=p.parse_args()
    session=c.owned_directory(args.directory)
    if args.command=='prepare':prepare(session)
    elif args.command=='verify-preparation':verify.verify_preparation(session);print('V22 preparation verified; performance stage unqualified unless separately recorded.')
    elif args.command=='verify-predictions':verify.verify_predictions(session,recompute=True);print('V22 forecasts verified from calibration only.')
    elif args.command=='verify-completion':print(json.dumps(verify.verify_completion(session),indent=2))
    elif args.command=='analyze':analyze(session)
    elif args.command=='status':print(json.dumps(status(session),indent=2))
    elif args.command=='_foreground':foreground(session,args.mode)
    elif args.command=='_watchdog':session_watchdog(session)
    elif args.command=='stop':
        owner=c.read(session/'active_owner.json')['owner']
        if owner['uid']!=os.getuid():raise ValueError('only original user may stop')
        if c.same_process(owner):os.kill(owner['pid'],signal.SIGTERM)


if __name__=='__main__':main()
