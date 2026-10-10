#!/usr/bin/env python3
"""V28 controlled composition comparison: offline preparation and bounded external collection."""
import argparse
import select
import v24r3_counter as native
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

import v28_common as c
import v28_raw as analysis
import v28_model as model
from v28_monitor_control import HostMonitor
import v28_verify as verify
from v28_service import Service, command, owned_inspect, remove_owned, LABEL
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures
import run
from environment_controls import POLICY, comparable_power, power_settings, window_summary


def require_quiet_host():
    run.require_quiet_host()
    c.require_desktop_absent()


def bounded_settle(path, baseline=None, initial_idle=False, expected_power=None):
    start=time.monotonic();samples=[];minimum=600 if initial_idle else 60
    while True:
        require_quiet_host()
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
    print(f"{config['order']}/{len(c.matrix())} {config['trial']}: {stage}",flush=True)


def load(directory, service, seconds, name, session, config):
    config = c.warmup_config(config) if name=='warmup' else config
    if config['traffic_pattern']=='idle':
        return capture_idle(directory,service,seconds,'warmup_idle' if name=='warmup' else 'idle',session,config)
    argv = [str(session/'preparation/loadgen'), '-url', service.base+'/work?iterations='+str(config['iterations']),
        '-duration', str(seconds)+'s', '-rate', str(config['rate']), '-pattern', config['traffic_pattern'], '-burst-low', str(config['burst_low']),
        '-burst-high', str(config['burst_high']), '-burst-period', str(config['burst_period_sec'])+'s', '-burst-low-duration', str(config['burst_low_duration_sec'])+'s', '-concurrency', '512',
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
    directory.mkdir(parents=True, exist_ok=False)
    c.save(directory/'config.json', config)
    c.save(directory/'started.json', dict(monotonic_ns=time.monotonic_ns(),wall_time=time.time()))
    service = Service(session, config, directory)
    monitor = None
    counter = None
    counter_log = None
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
            monitor = HostMonitor(directory, lambda: (service.guard(), require_quiet_host()))
            monitor.start(service.group)
        service.release()
        if config['counter_probe']:
            counter_log=(directory/'counter.log').open('x')
            argv=[str(session/'preparation/counter'),'--path',str(service.group/'cpu.stat'),
                  '--output',str(directory/'counter.raw.json')]
            c.save(directory/'counter_argv.json',argv)
            counter=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=counter_log,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            c.save(directory/'counter_process.json',c.process_identity(counter.pid))
            service.counter_process=counter
            until=time.monotonic()+2
            while True:
                service.guard()
                if time.monotonic()>=until:raise TimeoutError('native counter readiness deadline')
                if select.select([counter.stdout],[],[],.005)[0]:
                    token=os.read(counter.stdout.fileno(),6)
                    if token!=b'READY\n':raise ValueError('native readiness handshake failed')
                    c.save(directory/'counter_readiness.json',dict(token='READY',received_monotonic_ns=time.monotonic_ns()))
                    break
        observations = dict(startup=service.observe())
        if not functional:
            load(directory, service, 20, 'warmup', session, config)
            c.save(directory/'warmup_server_metrics.json', drain(service))
            if config['traffic_pattern']!='idle':c.validate_client(c.read(directory/'warmup.json'), c.warmup_config(config))
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
        if counter:
            service.counter_process=None
            fixtures.stop(counter,signal.SIGINT)
            if counter.returncode:raise ValueError('counter sampler failed')
            counter.stdout.close()
            native.decode_file(directory/'counter.raw.json',directory/'counter.json',c.save)
            c.save(directory/'counter.ready.json',c.read(directory/'counter.json')['samples'][0])
            counter_log.close();counter=None
        if monitor:
            monitor.finish(observations['final']['after_ns'])
            monitor = None
        service.close()
        c.seal(directory)
        derived = analysis.replay(directory, functional)
        c.save(directory/'derived.json', derived)
        if config['counter_probe']:
            verify.counter_input(session,directory,config)
        if not functional:
            phase=model.trial(derived,server,anchors,c.read(directory/'counter.json') if config['counter_probe'] else None,
                              config,c.design(),str(service.group/'cpu.stat'))
            c.save(directory/'phase_accounting.json',phase)
        if not functional and config['traffic_pattern']!='idle':
            for name in ('warmup','loadgen'):c.technical_client(c.read(directory/(name+'.json')))
        c.save(directory/'complete.json', dict(valid=True, performance_run=not functional,
            functional=functional,finished=time.time(),finished_monotonic_ns=time.monotonic_ns()))
        c.seal(directory)
        return directory
    except BaseException as e:
        failure = str(e)
        c.save(directory/'interruption.json', dict(error=failure, time=time.time(), traceback=traceback.format_exc()))
        raise
    finally:
        if counter:
            service.counter_process=None
            fixtures.stop(counter,signal.SIGINT);counter.stdout.close();counter_log.close()
        monitor_cleanup_error = None
        if monitor:
            try:monitor.stop()
            except Exception as e:
                monitor_cleanup_error = e
                c.save(directory/'monitor_cleanup_failure.json', dict(error=str(e)))
        try:
            service.close(failure)
        except Exception as e:
            c.save(directory/'cleanup_failure.json', dict(error=str(e)))
            if failure is None:
                raise
        finally:
            if failure:
                c.seal(directory)
        if monitor_cleanup_error is not None:
            raise monitor_cleanup_error


def prepare_offline(session):
    if session.exists():raise ValueError('preserve existing generation; choose a new directory')
    import v27r3_verify as historical
    previous=historical.verify_bundle(c.HISTORY)
    historical.verify_completion(c.HISTORY)
    c.design();client=c.verify_client_build();sources=c.source_hashes()
    session.mkdir(parents=True);out=session/'bundle';out.mkdir()
    for name,h in sources.items():
        target=out/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(c.ROOT/name,target)
        if c.digest(target)!=h:raise ValueError('source changed during snapshot')
    for name in ('gate','loadgen','image.server','publication_source.go','publication_build.json','counter'):
        shutil.copy2(c.HISTORY/'bundle'/name,out/name)
    shutil.copytree(c.CLIENT_BUILD,out/'client_build')
    for name in c.read(c.DESIGN/'seal.json')['files_sha256']:
        target=out/'scientific_design'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(c.ROOT/name,target)
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','diagnostic','-p','test_v28.py','-v'],cwd=c.ROOT,capture_output=True,text=True,timeout=180)
    (out/'tests.stdout').write_text(tests.stdout);(out/'tests.stderr').write_text(tests.stderr)
    if tests.returncode:raise ValueError('V28 software checks failed; scientific collection remains unrun')
    exports={}
    for cfg in c.matrix()+[c.warmup_config(x) for x in c.matrix() if x['traffic_pattern']!='idle']+c.functional_configs():
        if cfg['traffic_pattern']=='idle':continue
        key=cfg['trial']+('_warmup' if cfg['duration_sec']==20 else '_measurement')
        target=out/'compiled_vectors'/(key+'.json');target.parent.mkdir(exist_ok=True)
        argv=[str(out/'loadgen'),'-duration',str(cfg['duration_sec'])+'s','-rate',str(cfg['rate']),'-pattern',cfg['traffic_pattern'],
            '-burst-low',str(cfg['burst_low']),'-burst-high',str(cfg['burst_high']),'-burst-period',str(cfg['burst_period_sec'])+'s',
            '-burst-low-duration',str(cfg['burst_low_duration_sec'])+'s','-schedule-output',str(target)]
        result=subprocess.run(argv,capture_output=True,text=True,timeout=10)
        if result.returncode:raise ValueError('compiled schedule export failed: '+result.stderr)
        exported=c.read(target)
        if exported!=c.schedule(cfg):raise ValueError('compiled binary schedule differs')
        exports[key]=dict(argv=argv,sha256=c.digest(target),count=len(exported))
    c.save(out/'manifest.json',dict(previous,schema=28,generation=session.name,matrix=c.matrix(),sources=sources,
        design_seal=c.digest(c.DESIGN/'seal.json'),historical_bundle_seal=c.digest(c.HISTORY/'bundle/seal.json'),
        historical_analysis_seal=c.design()['historical_analysis_seal'],compiled_exports=exports,
        software_checks_passed=True,runtime_qualified=False,performance_run=False,created=time.time()))
    if c.source_hashes()!=sources:raise ValueError('sources changed during preparation')
    c.seal(out);verify.verify_bundle(session)
    print('V28 offline bundle verified; 16 calibration and 16 validation trials remain unrun.',flush=True)


def start_watchdog(session,phase,seconds):
    now=time.monotonic();owner=c.process_identity(os.getpid())
    c.save(session/(phase+'_owner.json'),dict(owner=owner))
    c.save(session/(phase+'_lifetime.json'),dict(started_monotonic=now,deadline_monotonic=now+seconds,boot=c.baseline()['boot_id']))
    log=(session/(phase+'_watchdog-'+str(time.time_ns())+'.log')).open('x')
    watcher=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'_watchdog','--phase',phase,'--directory',str(session)],
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    return watcher,log


def prepare_runtime(session):
    if os.geteuid()==0:raise ValueError('runtime preparation requires normal user')
    verify.verify_bundle(session);require_quiet_host();run.old.check_topology()
    if (session/'preparation').exists():
        verify.verify_preparation(session);print('Existing runtime preparation verified.',flush=True);return
    watcher,log=start_watchdog(session,'preparation',c.design()['runtime_preparation_bound_sec'])
    def interrupted(signum,frame):raise InterruptedError('bounded runtime preparation interrupted')
    old={sig:signal.signal(sig,interrupted) for sig in (signal.SIGTERM,signal.SIGINT)}
    out=session/'preparation';out.mkdir()
    try:
        previous=verify.verify_bundle(session)
        for name in ('gate','loadgen','image.server','publication_source.go','publication_build.json','counter'):
            shutil.copy2(session/'bundle'/name,out/name)
        c.capacity(session)
        image=json.loads(command(['docker','image','inspect',previous['image']]))[0];c.save(out/'image.json',image)
        manifest=dict(previous,bundle_seal=c.digest(session/'bundle/seal.json'),baseline=c.baseline(),
            functional_passed=False,performance_run=False,runtime_qualified=True)
        c.save(out/'manifest.json',manifest)
        d=out/'resource_preflight';d.mkdir();service=Service(session,c.functional_configs()[0],d)
        try:
            service.create();c.save(d/'observed.json',dict(gate_released=False,performance_run=False,limits=service.expected_limits))
        finally:service.close()
        functional={}
        for cfg in c.functional_configs():
            require_quiet_host()
            d=collect(session,out/'functional'/cfg['trial'],cfg,'functional',True)
            functional[cfg['trial']]=dict(path=str(d.relative_to(out)),seal=c.digest(d/'seal.json'))
        manifest.update(functional=functional,functional_passed=True,created=time.time())
        c.save(out/'manifest.json',manifest);c.seal(out);verify.verify_preparation(session)
        print('V28 composition runtime resources and six functional cases verified; scientific trials remain unrun.',flush=True)
    except BaseException as exc:
        c.save(out/'preparation_failure.json',dict(error=str(exc),traceback=traceback.format_exc(),time=time.time()));c.seal(out);raise
    finally:
        c.save(session/'preparation_finished.json',dict(time=time.time()))
        fixtures.stop(watcher,signal.SIGTERM);log.close()
        for sig,handler in old.items():signal.signal(sig,handler)


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
            if (not cleanup or cleanup['errors'] or cleanup['watchdog_intervened']
                    or (d/'monitor_cleanup_failure.json').exists()):
                raise ValueError('cleanup/watchdog failure stops generation') from exc
            verify.verify_preparation(session);verify.verify_environment(session)
            if len(failures(session))>1:raise
            print('One technical retry, same slot and fixed inputs: '+str(exc),flush=True)


def analyze(session):
    m=verify.verify_preparation(session,current=False);verify.verify_environment(session);verify.verify_observer(session,current=False)
    values,refs=verify.rows(session,m)
    cal=[r for r in values if r['role']!='validation'];validation=[r for r in values if r['role']=='validation']
    calibration=model.calibrate(cal,c.design()) if len(cal)==len(c.calibration_configs()) else dict(usable=False,decision='calibration_incomplete')
    predictions=verify.verify_predictions(session)['summary'] if (session/'predictions').exists() else {}
    complete=(session/'collection_receipt.json').exists() and len(validation)==len(c.validation_configs())
    report=model.report(validation,calibration,predictions,c.design(),complete)
    if len(cal)!=len(c.calibration_configs()):report['decision']='comparison_incomplete'
    out=session/'analysis'/str(time.time_ns());out.mkdir(parents=True)
    c.save(out/'report.json',dict(result=report,calibration=calibration,trial_refs=refs,trial_accounting=values,
        preparation_seal=c.digest(session/'preparation/seal.json'),
        prediction_seal=c.digest(session/'predictions/seal.json') if (session/'predictions/seal.json').exists() else None,
        collection_receipt_sha256=c.digest(session/'collection_receipt.json') if (session/'collection_receipt.json').exists() else None,
        measurement_lifetime_sha256=c.digest(session/'measurement_lifetime.json'),technical_failures=[str(p.relative_to(session)) for p in failures(session)]))
    lines=['# V28 prospective estimator comparison','','**Decision: '+report['decision']+'**','',report['limits'],'',
        '| Method | Capacity rps | Deadline MAE pp | Accuracy screen |','|---|---:|---:|---|']
    for name,value in calibration.get('methods',{}).items():
        z=report['methods'].get(name,{})
        lines.append('| '+name+' | '+str(value.get('capacity_rps','unavailable'))+' | '+str(z.get('deadline_mae_pp','unavailable'))+' | '+str(z.get('accuracy_pass',False))+' |')
    lines+=['','All failures, state qualifications, block intervals, calibration inputs and per-offer forecasts remain in sealed JSON.',
        'No further experiment starts automatically. A positive decision does not establish novelty or workload/quota transfer.']
    (out/'report.md').write_text('\n'.join(lines)+'\n');c.seal(out)
    c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=c.digest(out/'seal.json')))
    verify.verify_completion(session)
    print('V28 prospective comparison: '+report['decision']+'; '+str(out),flush=True)
    return out


def capture_idle(directory,service,seconds,name,session,cfg):
    start=time.monotonic_ns();deadline=start+int(seconds*1e9);samples=[]
    while True:
        if not cfg.get('functional'):require_quiet_host()
        service.observe();before=time.monotonic_ns();health=bridge.get(service.base,'health');after=time.monotonic_ns()
        samples.append(dict(before_ns=before,after_ns=after,health=health))
        update(session,cfg,name)
        remaining=(deadline-time.monotonic_ns())/1e9
        if remaining<=0:break
        time.sleep(min(1,remaining))
    c.save(directory/(name+'.json'),dict(kind='zero_request_live_service',offers=0,requested_duration_sec=seconds,
        started_ns=start,finished_ns=time.monotonic_ns(),samples=samples))


def freeze_predictions(session):
    if any(verify.attempts(session,cfg) for cfg in c.validation_configs()):raise ValueError('validation started before forecast freeze')
    if (session/'predictions').exists() or (session/'calibration_review').exists():raise ValueError('forecast recreation prohibited')
    manifest=verify.verify_preparation(session);values,refs=verify.rows(session,manifest)
    if any(r['role']=='validation' for r in values):raise ValueError('validation outcomes in calibration prohibited')
    result=model.calibrate(values,c.design());review=session/'calibration_review';review.mkdir()
    c.save(review/'report.json',dict(calibration=result,trial_refs=refs));c.seal(review)
    if not result['usable']:return None
    summary,per_id=model.forecast(result,c.validation_configs());out=session/'predictions';out.mkdir()
    c.save(out/'summary.json',summary);c.save(out/'per_offer.json',per_id);c.save(out/'calibration.json',result)
    c.save(out/'manifest.json',dict(calibration_refs=refs,calibration_review_seal=c.digest(review/'seal.json'),
        preparation_seal=c.digest(session/'preparation/seal.json'),environment_seal=c.digest(session/'environment_seal.json'),
        design_seal=c.digest(c.DESIGN/'seal.json'),frozen_monotonic_ns=time.monotonic_ns(),validation_outcomes_used=False))
    c.seal(out);verify.verify_predictions(session)
    print('Calibration qualified; every method and per-offer forecast is sealed before validation.',flush=True)
    return out


def session_watchdog(session,phase):
    state=c.read(session/(phase+'_owner.json'));deadline=c.read(session/(phase+'_lifetime.json'))['deadline_monotonic']
    finished=session/(phase+'_finished.json')
    while c.same_process(state['owner']) and not finished.exists():
        if time.monotonic()>=deadline:
            os.kill(state['owner']['pid'],signal.SIGTERM);until=time.monotonic()+120
            while c.same_process(state['owner']) and time.monotonic()<until:time.sleep(.5)
            if c.same_process(state['owner']):os.kill(state['owner']['pid'],signal.SIGKILL)
            break
        time.sleep(.5)
    for ownership in session.rglob('ownership.json'):
        d=ownership.parent;o=c.read(ownership)
        if o['owner']!=state['owner'] or (d/'cleanup.json').exists():continue
        for p in d.glob('*_process.json'):
            identity=c.read(p)
            if c.same_process(identity):os.kill(identity['pid'],signal.SIGTERM)
        remove_owned(o['container'],o['nonce'])


def bind_observer_inventory(session, path):
    if path is None:raise ValueError('fresh root observer inventory and ownership review required')
    reviewed=verify.observer.review(path)
    if reviewed['boot_id'].strip()!=c.baseline()['boot_id']:
        raise ValueError('observer inventory belongs to another boot')
    audit=c.read(path);manifest=c.read(session/'preparation/manifest.json')
    if (verify.datetime.datetime.fromisoformat(audit['at']).timestamp()<manifest['created']
            or audit['configuration_changed'] or audit['observation_started']
            or audit['tracefs']['root_controls_before']!=audit['tracefs']['root_controls_after']):
        raise ValueError('fresh post-preparation read-only inventory required')
    directory=session/'observer_review'
    if directory.exists():
        verify.verify_observer(session)
        directory=session/'observer_refresh'/str(time.time_ns())
    directory.mkdir(parents=True)
    shutil.copy2(path,directory/'audit.json')
    c.save(directory/'review.json',reviewed)
    c.save(directory/'receipt.json',dict(audit_path=str(Path(path).absolute()),bound_monotonic_ns=time.monotonic_ns()))
    c.seal(directory)
    verify.verify_observer(session)


def foreground(session,observer_audit=None):
    if os.geteuid()==0:raise ValueError('normal user orchestration required')
    os.sched_setaffinity(0,{0,1})
    with (session/'.worker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        verify.verify_preparation(session);require_quiet_host();run.old.check_topology()
        if any((session/'slots').glob('*/attempt-*')) or (session/'measurement_lifetime.json').exists():
            raise ValueError('preserve attempted generation; automatic resume prohibited')
        bind_observer_inventory(session,observer_audit)
        def interrupted(signum,frame):raise InterruptedError('bounded measurement interrupted')
        old={sig:signal.signal(sig,interrupted) for sig in (signal.SIGTERM,signal.SIGINT)}
        watcher,log=start_watchdog(session,'measurement',c.design()['measurement_bound_sec'])
        try:
            environment(session)
            for cfg in c.calibration_configs():collect_slot(session,cfg)
            if freeze_predictions(session) is None:
                c.save(session/'calibration_stopped.json',dict(decision='calibration_qualification_failed',monotonic_ns=time.monotonic_ns()))
            else:
                for cfg in c.validation_configs():
                    verify.verify_predictions(session)
                    collect_slot(session,cfg)
            lifetime=c.read(session/'measurement_lifetime.json');now=time.monotonic()
            if now>lifetime['deadline_monotonic']:raise TimeoutError('measurement time bound exhausted')
            c.save(session/'collection_receipt.json',dict(lifetime,collection_finished_monotonic=now,completed_slots=sum(verify.accepted(session,cfg) is not None for cfg in c.matrix()),validation_launched=(session/'predictions/seal.json').exists()))
            c.save(session/'progress.json',dict(stage='collection_complete',timestamp=time.time(),log=str(session)))
        except BaseException as exc:
            c.save(session/'worker_interruption.json',dict(error=str(exc),time=time.time(),traceback=traceback.format_exc()));raise
        finally:
            c.save(session/'measurement_finished.json',dict(time=time.time()))
            fixtures.stop(watcher,signal.SIGTERM);log.close()
            for sig,handler in old.items():signal.signal(sig,handler)
    # The measurement watchdog is disarmed before this separately bounded replay.
    completed=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'analyze','--directory',str(session)],timeout=600)
    if completed.returncode:raise ValueError('offline analysis failed; collected data remain preserved')
    c.save(session/'progress.json',dict(stage='complete',timestamp=time.time(),log=str(session)))


def status(session):
    counts=sum(verify.accepted(session,cfg) is not None for cfg in c.matrix())
    return dict(generation=str(session),completed_composition_markers=counts,planned=len(c.matrix()),
        offline_bundle_present=(session/'bundle/seal.json').exists(),
        runtime_preparation_present=(session/'preparation/seal.json').exists(),
        progress=c.read(session/'progress.json') if (session/'progress.json').exists() else {'stage':'offline_prepared'},
        counts_are_markers_full_verification_separate=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['prepare-offline','verify-bundle','prepare-runtime','verify-preparation',
        'verify-completion','analyze','status','_foreground','_watchdog'])
    p.add_argument('--directory',required=True);p.add_argument('--observer-audit',type=Path)
    p.add_argument('--phase',choices=['preparation','measurement'],default='measurement');args=p.parse_args()
    session=c.owned_directory(args.directory)
    if args.command=='prepare-offline':prepare_offline(session)
    elif args.command=='verify-bundle':verify.verify_bundle(session);print('V28 offline bundle verified; external calibration, forecast freeze and validation remain unrun.')
    elif args.command=='prepare-runtime':prepare_runtime(session)
    elif args.command=='verify-preparation':verify.verify_preparation(session);print('V28 composition runtime preparation verified.')
    elif args.command=='verify-completion':print(json.dumps(verify.verify_completion(session),indent=2))
    elif args.command=='analyze':analyze(session)
    elif args.command=='status':print(json.dumps(status(session),indent=2))
    elif args.command=='_foreground':foreground(session,args.observer_audit)
    elif args.command=='_watchdog':session_watchdog(session,args.phase)


if __name__=='__main__':main()
