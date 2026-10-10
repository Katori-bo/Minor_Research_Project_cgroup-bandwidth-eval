#!/usr/bin/env python3
"""Separate V18 observer-cost runner. Preparation never collects pilot trials."""
import argparse
import csv
import datetime
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

import kernel_observer_common as c
import kernel_observer_analysis as analysis
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures
import run
from environment_controls import power_settings


def attempt_directories(session, mode, trial):
    return sorted((session/('rehearsals' if mode=='qualify' else 'trials')/trial).glob('attempt-*'))


def valid_attempt(session, mode, trial):
    valid=[]
    for d in attempt_directories(session,mode,trial):
        if (d/'complete.json').exists():
            c.verify_seal(d)
            if not c.read(d/'complete.json')['valid']: raise ValueError('invalid completion marker')
            valid.append(d)
    if len(valid)>1: raise ValueError('multiple completed attempts for one frozen trial')
    return valid[0] if valid else None


def pending(session, mode):
    configs=([dict(trial='rehearsal_'+a,arm=a,pair=0,order=i+1,**c.WORKLOAD)
              for i,a in enumerate(('off','on'))] if mode=='qualify' else c.matrix())
    return [v for v in configs if valid_attempt(session,mode,v['trial']) is None]


def prepare(session):
    if os.geteuid()==0: raise ValueError('prepare under the original user identity')
    if session.exists(): raise ValueError('preserve existing generation; choose a new directory')
    c.PARENT.mkdir(parents=True,exist_ok=True); c.capacity(c.PARENT)
    c.verify_seal(c.BASE,'verification.json'); c.verify_seal(c.BRIDGE_ASSETS); c.verify_seal(c.BRIDGE)
    summary=c.read(c.BRIDGE/'summary.json')
    if not summary['passed'] or not summary['root_trace_controls_unchanged'] or len(summary['cases'])!=5:
        raise ValueError('five already-passed bridge controls required (never rerun here)')
    sources=c.source_hashes()
    base=c.read(c.BASE/'build.json'); audit=c.read(c.BASE/'binary_audit/audit.json')['records']['legacy']
    retained=c.read(c.BRIDGE_ASSETS/'manifest.json')
    image=base['images']['legacy_a']
    if image!=audit['image'] or image!=retained['image'] or c.digest(c.BASE/'loadgen')!=retained['loadgen_sha256']:
        raise ValueError('retained original identities disagree')
    session.mkdir(); prep=session/'preparation'; prep.mkdir(); (prep/'source').mkdir()
    for name,sha in sources.items():
        target=prep/'source'/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(c.ROOT/name,target)
        if c.digest(target)!=sha: raise ValueError('source copy changed')
    for source,name in ((c.BRIDGE_ASSETS/'gate','gate'),(c.BASE/'loadgen','loadgen'),
                        (c.BASE/'binary_audit/legacy.server','original.server'),
                        (c.ROOT/'diagnostic/kernel_observer.bt','kernel_observer.bt')):
        shutil.copy2(source,prep/name)
    result=subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic',
                           '-p','test_kernel_observer*.py','-v'],cwd=c.ROOT,capture_output=True,text=True,timeout=120)
    (prep/'tests.stdout').write_text(result.stdout); (prep/'tests.stderr').write_text(result.stderr)
    if result.returncode: raise ValueError('observer-cost preparation tests failed')
    # Hash/extract the actual original image outside measurement; no service build.
    inspected=json.loads(bridge.capture(['docker','image','inspect',image]))[0]
    if inspected['Id']!=image: raise ValueError('original image unavailable')
    container=bridge.capture(['docker','create',image])
    try: bridge.capture(['docker','cp',container+':/server',str(prep/'image.server')])
    finally: bridge.capture(['docker','rm',container])
    if c.digest(prep/'image.server')!=audit['binary_sha256']: raise ValueError('packaged executable hash differs')
    c.save(prep/'image.json',inspected)
    c.save(prep/'manifest.json',dict(schema=1,generation=session.name,sources=sources,matrix=c.matrix(),
        workload=c.WORKLOAD,baseline=c.baseline(),image=image,server_sha256=audit['binary_sha256'],
        loadgen_sha256=c.digest(prep/'loadgen'),gate_sha256=c.digest(prep/'gate'),
        collector_sha256=c.digest(prep/'kernel_observer.bt'),raw_limit=c.RAW_LIMIT,capture_sec=c.CAPTURE_SEC,
        watchdog_sec=c.WATCHDOG_SEC,free_min=c.FREE_MIN,tests_passed=True,performance_run=False,
        original_build_seal=c.digest(c.BASE/'verification.json'),bridge_seal=c.digest(c.BRIDGE/'seal.json'),
        bridge_assets_seal=c.digest(c.BRIDGE_ASSETS/'seal.json'),created=time.time()))
    if c.source_hashes()!=sources: raise ValueError('sources changed during preparation')
    c.seal(prep); verify_preparation(session)
    print('Prepared generation: '+str(session)+'; full off/on qualification rehearsals remain required.',flush=True)


def verify_preparation(session, current=True):
    prep=session/'preparation'; c.verify_seal(prep); value=c.read(prep/'manifest.json')
    if value['matrix']!=c.matrix() or value['workload']!=c.WORKLOAD or not value['tests_passed']:
        raise ValueError('frozen protocol/test receipt differs')
    expected={'loadgen':'loadgen_sha256','gate':'gate_sha256','kernel_observer.bt':'collector_sha256','original.server':'server_sha256','image.server':'server_sha256'}
    for name,key in expected.items():
        if c.digest(prep/name)!=value[key]: raise ValueError('frozen input hash changed: '+name)
    for name,sha in value['sources'].items():
        if c.digest(prep/'source'/name)!=sha: raise ValueError('frozen source hash differs')
    if current:
        if c.source_hashes()!=value['sources']: raise ValueError('sources changed: new preparation generation required')
        if c.baseline()!=value['baseline']: raise ValueError('kernel/boot/topology baseline changed')
        for directory,name,key in ((c.BASE,'verification.json','original_build_seal'),(c.BRIDGE,'seal.json','bridge_seal'),
                                   (c.BRIDGE_ASSETS,'seal.json','bridge_assets_seal')):
            c.verify_seal(directory,name)
            if c.digest(directory/name)!=value[key]: raise ValueError('retained baseline identity changed')
    return value


def verify_qualification(session, current=True):
    manifest=verify_preparation(session,current)
    c.verify_seal(session/'qualification'); q=c.read(session/'qualification/result.json')
    if not q['passed'] or (session/'qualification/capacity_failure.json').exists() or q['preparation_seal']!=c.digest(session/'preparation/seal.json'):
        raise ValueError('qualification does not cover this preparation generation')
    if q['environment_sha256']!=c.digest(session/'environment.json'): raise ValueError('qualified thermal/power baseline changed')
    for arm in ('off','on'):
        d=session/q['rehearsals'][arm]['path']; result=analysis.replay(d)
        if c.digest(d/'seal.json')!=q['rehearsals'][arm]['seal'] or result!=c.read(d/'derived.json'):
            raise ValueError('qualification raw replay changed')
        client=c.read(d/'loadgen.json')
        if c.read(d/'environment.json')!=c.read(session/'environment.json'): raise ValueError('rehearsal environment baseline changed')
        if client.get('client_dropped',0) or client.get('missed_arrivals',0) or client['dispatch_lag_summary']['p99_ms']>2:
            raise ValueError('rehearsal client capacity failed')
    if manifest['collector_sha256']!=q['collector_sha256']: raise ValueError('collector changed since qualification')
    return q


class RPC:
    def __init__(self,sock): self.sock=sock; sock.settimeout(45)
    def call(self,op):
        c.send(self.sock,dict(op=op)); response=c.receive(self.sock)
        if not response.get('ok'): raise ValueError(response.get('error','supervisor failed'))
        return response['result']


def drain(base,rpc,seconds=100):
    until=time.monotonic()+seconds
    while True:
        rpc.call('observe'); server=bridge.get(base,'metrics')
        if not server['active_handlers'] and not server['queue_len'] and server['completed']==server['admitted']: return server
        if time.monotonic()>until: raise TimeoutError('full service drain timeout')
        time.sleep(1)


def load(directory,base,seconds,name,rpc,session,config):
    args=[str(session/'preparation/loadgen'),'-url',base+'/work?iterations=44000',
          '-duration',f'{seconds}s','-rate','113.21','-pattern','bursty','-burst-low','56.605',
          '-burst-high','169.815','-burst-period','10s','-concurrency','512','-timeout','5s',
          '-trace-client=true','-output',str(directory/(name+'.json'))]
    c.save(directory/(name+'_argv.json'),args)
    with (directory/(name+'.log')).open('x') as log:
        process=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        try:
            until=time.monotonic()+seconds+30
            while process.poll() is None:
                rpc.call('observe')
                update(session,config,name)
                if time.monotonic()>until: raise TimeoutError('bounded loadgen timeout')
                time.sleep(1)
            if process.returncode: raise ValueError('retained client failed')
        finally: fixtures.stop(process,signal.SIGTERM)


def update(session,config,stage):
    environment=c.read(session/'environment.json') if (session/'environment.json').exists() else None
    c.save(session/'progress.json',dict(trial=config['trial'],order=config['order'],stage=stage,
        temperatures=run.old.temperatures(),baseline=None if environment is None else environment['baseline_c'],
        log=str(session),timestamp=time.time()))
    print(f"{config['order']}/{'2 rehearsals' if config['pair']==0 else '12 trials'} {config['trial']}: {stage}; "
          f"temperature={run.old.temperatures()}; log={session}",flush=True)


def trial(session,mode,config,rpc):
    trial_root=session/('rehearsals' if mode=='qualify' else 'trials')/config['trial']
    trial_root.mkdir(parents=True,exist_ok=True)
    directory=trial_root/f'attempt-{time.time_ns()}'; directory.mkdir()
    c.save(directory/'config.json',config)
    environment=c.read(session/'environment.json'); c.save(directory/'environment.json',environment)
    monitor=None; created=False; ended=False; failure=None
    try:
        run.require_quiet_host(); update(session,config,'settling')
        run.old.settle(directory/'settling.json',environment['baseline_c'],expected_power=environment['power_settings'])
        c.capacity(session)
        if power_settings(include_profile=True)!=environment['power_settings']: raise ValueError('power baseline changed')
        created=True; service=rpc.call('create'); base=service['base']
        # Identical monitor covers startup, warmup, reset, measurement, and drain.
        monitor_log=(directory/'monitor.log').open('x')
        monitor=subprocess.Popen([sys.executable,str(c.ROOT/'scripts/monitor_host.py'),
            '--cgroup-path',service['cgroup'].removeprefix('/sys/fs/cgroup'),
            '--output',str(directory/'monitor.json')],stdout=monitor_log,stderr=subprocess.STDOUT,
            preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        rpc.call('release')
        observations={'startup':rpc.call('observe')}
        load(directory,base,20,'warmup',rpc,session,config)
        c.save(directory/'warmup_server_metrics.json',drain(base,rpc))
        c.arrival_vector(c.read(directory/'warmup.json'),20)
        update(session,config,'reset')
        with urllib.request.urlopen(urllib.request.Request(base+'/reset',data=b'',method='POST'),timeout=3) as response:
            if response.status!=204: raise ValueError('reset failed')
        c.save(directory/'reset.json',dict(monotonic_ns=time.monotonic_ns(),health=bridge.get(base,'health')))
        clocks=bridge.anchors(base,'start')
        observations['measurement_start']=rpc.call('observe')
        load(directory,base,60,'loadgen',rpc,session,config)
        update(session,config,'drain')
        server=drain(base,rpc); observations['measurement_stop']=rpc.call('observe')
        clocks+=bridge.anchors(base,'stop')
        observations['final']=rpc.call('observe')
        c.save(directory/'server_metrics.json',server); c.save(directory/'kernel_server_anchors.json',clocks)
        c.save(directory/'observations.json',observations)
        if power_settings(include_profile=True)!=environment['power_settings']: raise ValueError('power changed during trial')
        fixtures.stop(monitor,signal.SIGINT)
        if monitor.returncode: raise ValueError('host monitor failed')
        monitor_log.close(); monitor=None
        update(session,config,'service exit and detach'); rpc.call('end'); ended=True
        c.seal(directory); result=analysis.replay(directory)
        c.save(directory/'derived.json',result)
        c.save(directory/'complete.json',dict(valid=True,performance_run=mode!='qualify',finished=time.time()))
        c.seal(directory)
        return directory
    except BaseException as e:
        failure=str(e); c.save(directory/'interruption.json',dict(error=failure,time=time.time()))
        raise
    finally:
        if monitor:
            fixtures.stop(monitor,signal.SIGINT); monitor_log.close()
        if created and not ended:
            try: rpc.call('end')
            except Exception as e: c.save(directory/'cleanup_rpc_failure.json',dict(error=str(e)))
        if failure: c.seal(directory)


def worker(session,mode,configs,sock):
    os.sched_setaffinity(0,{0,1})
    def interrupted(signum,frame): raise InterruptedError('benchmark interrupted')
    signal.signal(signal.SIGINT,interrupted); signal.signal(signal.SIGTERM,interrupted)
    rpc=RPC(sock)
    run.require_quiet_host()
    run.old.check_topology(); run.old.prepare_environment(session)
    if mode!='qualify': verify_qualification(session)
    for config in configs:
        # Hashing and full replay happen only before/after an active trial.
        verify_preparation(session)
        if mode!='qualify': verify_qualification(session)
        trial(session,mode,config,rpc)
    rpc.call('finish')
    if mode=='qualify':
        out=session/'qualification'
        if out.exists(): raise ValueError('qualification already sealed')
        out.mkdir(); rehearsals={}
        for arm in ('off','on'):
            d=valid_attempt(session,'qualify','rehearsal_'+arm)
            result=analysis.replay(d)
            if result!=c.read(d/'derived.json'): raise ValueError('rehearsal replay differs')
            rehearsals[arm]=dict(path=str(d.relative_to(session)),seal=c.digest(d/'seal.json'))
        c.save(out/'result.json',dict(passed=True,performance_run=False,rehearsals=rehearsals,
            preparation_seal=c.digest(session/'preparation/seal.json'),
            environment_sha256=c.digest(session/'environment.json'),
            collector_sha256=c.read(session/'preparation/manifest.json')['collector_sha256']))
        c.seal(out)
        try: verify_qualification(session)
        except Exception:
            # Retain failed qualification, but never expose readiness.
            c.save(out/'capacity_failure.json',dict(error='rehearsal capacity verification failed'))
            c.seal(out); raise
        print('Both full-duration rehearsals passed; performance launcher is ready.',flush=True)
    else: analyze(session)


def export_csv(path,rows):
    if not rows: path.write_text(''); return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def analyze(session):
    verify_preparation(session,current=False)
    rows=[]; requests=[]; references={}; gaps=[]; interruptions=[]
    for config in c.matrix():
        for attempt in attempt_directories(session,'start',config['trial']):
            if (attempt/'interruption.json').exists():
                interruptions.append(dict(trial=config['trial'],path=str(attempt.relative_to(session)),
                                          **c.read(attempt/'interruption.json')))
        d=valid_attempt(session,'start',config['trial'])
        if d is None:
            gaps.append(dict(trial=config['trial'],attempts=[str(a.relative_to(session)) for a in attempt_directories(session,'start',config['trial'])])); continue
        result=analysis.replay(d)
        if result!=c.read(d/'derived.json'): raise ValueError('raw replay differs from saved derivation')
        rows.append(result['summary'])
        requests.extend(dict(trial=config['trial'],pair=config['pair'],arm=config['arm'],**r) for r in result['requests'])
        references[config['trial']]=dict(path=str(d.relative_to(session)),seal=c.digest(d/'seal.json'))
    for pair in range(1,7):
        if all(f'p{pair}_{arm}' in references for arm in ('off','on')):
            vectors=[c.arrival_vector(c.read(session/references[f'p{pair}_{arm}']['path']/'loadgen.json')) for arm in ('off','on')]
            if vectors[0]!=vectors[1]: raise ValueError('pair arrival vectors differ')
    split_pairs=[]
    for pair in range(1,7):
        if any(v['trial'].startswith(f'p{pair}_') for v in interruptions): split_pairs.append(pair)
    report=analysis.compare(rows); report.update(pair_gaps=gaps,attempts=references,interruptions=interruptions,
                    interrupted_pairs=split_pairs,
                    preparation_seal=c.digest(session/'preparation/seal.json'))
    parent=session/'analysis'; parent.mkdir(exist_ok=True)
    out=parent/str(time.time_ns()); out.mkdir()
    export_csv(out/'requests.csv',requests); export_csv(out/'trials.csv',rows); export_csv(out/'pairs.csv',report['pairs'])
    c.save(out/'report.json',report)
    (out/'report.md').write_text('# V18 kernel observer cost practical screen\n\n'+report['decision']+'\n\n'+analysis.LIMITATION+
        '\n\nAll offered requests are retained in requests.csv. CPU per computation uses the counter window after reset through full drain. '
        'Successful p99 includes late successes and drained responses. Per-CPU quota intervals remain separate. '
        'After reviewing observer cost, a separate analysis can examine quota/service execution overlap with computation-to-handler delays.\n')
    c.seal(out); c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=c.digest(out/'seal.json')))
    print('Practical screen: '+report['decision']+'; '+str(out),flush=True)
    return out


def status(session):
    progress=c.read(session/'progress.json') if (session/'progress.json').exists() else dict(stage='prepared')
    progress['completed_trials']=sum(valid_attempt(session,'start',v['trial']) is not None for v in c.matrix())
    progress['completed_rehearsals']=sum(valid_attempt(session,'qualify','rehearsal_'+a) is not None for a in ('off','on'))
    progress['log']=str(session)
    print(json.dumps(progress,indent=2),flush=True)


def stop(session):
    owner=c.read(session/'owner.json'); pid=owner['worker_pid']
    if owner['uid']!=os.getuid(): raise ValueError('only the original user can stop the benchmark')
    try: current=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
    except FileNotFoundError: return
    if current!=owner['worker_starttime']: raise ValueError('worker PID reused; refusing signal')
    os.kill(pid,signal.SIGTERM)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify-preparation','qualify','start','resume','status','watch','stop','analyze','verify-completion','_supervise'))
    parser.add_argument('--directory',required=True,type=c.owned_directory)
    parser.add_argument('--mode',choices=('qualify','start','resume'))
    args=parser.parse_args(); session=args.directory
    try:
        if args.command=='prepare': prepare(session)
        elif args.command=='verify-preparation': verify_preparation(session); print('Preparation verified; qualification status is separate.')
        elif args.command=='analyze': analyze(session)
        elif args.command=='verify-completion':
            from verify_kernel_observer_cost import verify_completion
            verify_completion(session); print('Complete evidence and practical-screen replay verified.')
        elif args.command=='status': status(session)
        elif args.command=='watch':
            while True: status(session); time.sleep(5)
        elif args.command=='stop': stop(session)
        elif args.command=='_supervise':
            if args.mode is None: parser.error('_supervise requires --mode')
            from kernel_observer_supervisor import supervise
            supervise(session,args.mode)
        else:
            verify_preparation(session)
            if args.command!='qualify': verify_qualification(session)
            if args.command=='start' and any((session/'trials').glob('*/attempt-*')):
                raise ValueError('existing attempts: use explicit resume')
            print('Launch from an external terminal after fully quitting Codex:')
            print(f'{c.ROOT}/diagnostic/start_kernel_observer_cost.sh {args.command} {session}')
    except (Exception,KeyboardInterrupt) as e:
        print('Observer-cost pilot: '+str(e),file=sys.stderr); return 1
    return 0


if __name__=='__main__': sys.exit(main())
