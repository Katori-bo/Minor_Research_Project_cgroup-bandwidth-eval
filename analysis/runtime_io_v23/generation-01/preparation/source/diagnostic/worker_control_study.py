#!/usr/bin/env python3
"""V19 original-binary worker control. Prepare now; quiet measurements externally."""
import argparse
import csv
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

import worker_control_common as c
import worker_control_analysis as analysis
from worker_control_service import Service, command, owned_inspect
from verify_worker_control import verify_preparation, verify_qualification, verify_environment, verify_completion
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures
import run
from environment_controls import power_settings


def attempts(session, mode, trial):
    return sorted((session/('rehearsals' if mode == 'qualify' else 'trials')/trial).glob('attempt-*'))


def valid_attempt(session, mode, trial):
    accepted = []
    for d in attempts(session, mode, trial):
        c.verify_seal(d)
        if (d/'complete.json').exists():
            if not c.read(d/'complete.json')['valid']:
                raise ValueError('invalid completion marker')
            accepted.append(d)
    if len(accepted) > 1:
        raise ValueError('multiple accepted attempts for one frozen trial')
    return accepted[0] if accepted else None


def pending(session, mode):
    configs = c.rehearsals() if mode == 'qualify' else c.matrix()
    return [config for config in configs if valid_attempt(session, mode, config['trial']) is None]


def update(session, config, stage):
    if config.get('functional'):
        return
    c.save(session/'progress.json', dict(trial=config['trial'], order=config['order'], block=config['block'],
        stage=stage, temperatures=run.old.temperatures(), baseline=c.read(session/'environment.json')['baseline_c'],
        timestamp=time.time(), log=str(session)))
    print(f"{config['order']}/{'2 rehearsals' if config['block'] == 0 else '18 trials'} {config['trial']}: {stage}", flush=True)


def load(directory, service, seconds, name, session, config):
    argv = [str(session/'preparation/loadgen'), '-url', service.base+'/work?iterations=44000',
        '-duration', str(seconds)+'s', '-rate', str(config['rate']), '-pattern', 'bursty', '-burst-low', str(config['burst_low']),
        '-burst-high', str(config['burst_high']), '-burst-period', '10s', '-concurrency', '512',
        '-timeout', str(config['timeout_sec'])+'s', '-trace-client=true', '-output', str(directory/(name+'.json'))]
    c.save(directory/(name+'_argv.json'), argv)
    with (directory/(name+'.log')).open('x') as log:
        process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT,
            preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
        try:
            until = time.monotonic()+seconds+30
            next_report = 0
            while process.poll() is None:
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
    service = Service(session, config, directory)
    monitor = None
    monitor_log = None
    failure = None
    try:
        if not functional:
            environment = c.read(session/'environment.json')
            c.save(directory/'environment.json', environment)
            run.require_quiet_host()
            update(session, config, 'settling')
            run.old.settle(directory/'settling.json', environment['baseline_c'], expected_power=environment['power_settings'])
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
        service.release()
        observations = dict(startup=service.observe())
        if not functional:
            load(directory, service, 20, 'warmup', session, config)
            c.save(directory/'warmup_server_metrics.json', drain(service))
            c.validate_client(c.read(directory/'warmup.json'), dict(config, duration_sec=20))
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
        c.save(directory/'complete.json', dict(valid=True, performance_run=mode == 'start',
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
    if os.geteuid() == 0:
        raise ValueError('prepare as the original normal user')
    if session.exists():
        raise ValueError('preserve existing generation; choose a new directory')
    c.PARENT.mkdir(parents=True, exist_ok=True)
    c.capacity(c.PARENT)
    c.verify_seal(c.V18/'preparation')
    previous = c.read(c.V18/'preparation/manifest.json')
    sources = c.source_hashes()
    session.mkdir()
    prep = session/'preparation'
    prep.mkdir()
    try:
        for name, sha in sources.items():
            target = prep/'source'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(c.ROOT/name, target)
            if c.digest(target) != sha:
                raise ValueError('source copy changed')
        for name in ('gate', 'loadgen', 'original.server'):
            shutil.copy2(c.V18/'preparation'/name, prep/name)
        tests = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'diagnostic',
            '-p', 'test_worker_control.py', '-v'], cwd=c.ROOT, capture_output=True, text=True, timeout=120)
        (prep/'tests.stdout').write_text(tests.stdout)
        (prep/'tests.stderr').write_text(tests.stderr)
        if tests.returncode:
            raise ValueError('V19 preparation tests failed')
        image = json.loads(command(['docker', 'image', 'inspect', previous['image']]))[0]
        if image['Id'] != previous['image']:
            raise ValueError('retained original image unavailable')
        c.save(prep/'image.json', image)
        name = 'quota-v19-extract-'+str(time.time_ns())
        try:
            command(['docker', 'create', '--name', name, previous['image']])
            command(['docker', 'cp', name+':/server', str(prep/'image.server')])
        finally:
            command(['docker', 'rm', '-f', name])
        if c.digest(prep/'image.server') != previous['server_sha256']:
            raise ValueError('original packaged executable differs')
        manifest = dict(schema=1, generation=session.name, sources=sources, matrix=c.matrix(),
            workload=c.WORKLOAD, baseline=c.baseline(), tests_passed=True, functional_passed=False,
            performance_run=False, v18_preparation_seal=c.digest(c.V18/'preparation/seal.json'),
            **{k: previous[k] for k in ('image', 'server_sha256', 'loadgen_sha256', 'gate_sha256', 'resource_baseline')})
        c.save(prep/'manifest.json', manifest)
        c.save(prep/'arrivals.json', c.arrivals())
        directory = prep/'resource_preflight'
        directory.mkdir()
        resource = Service(session, c.fixture('four_a'), directory)
        try:
            resource.create()
            observed = c.read(directory/'initial.json')['resource_baseline']
            c.save(directory/'observed.json', dict(baseline=observed, gate_released=False, performance_run=False))
        finally:
            resource.close()
        functional = {}
        for config in [c.fixture('four_a'), c.fixture('one'), c.fixture('one', True)]:
            label = config['arm']+('_cancel' if config['timeout_sec'] < 1 else '')
            d = collect(session, prep/'functional'/label, config, 'functional', functional=True)
            result = c.read(d/'derived.json')['summary']
            functional[label] = dict(path=str(d.relative_to(prep)), seal=c.digest(d/'seal.json'))
            print('Functional '+label+': '+str(result['offered'])+' offers; outcomes='+str(result['outcome_counts']), flush=True)
        manifest.update(functional=functional, functional_passed=True, created=time.time())
        c.save(prep/'manifest.json', manifest)
        if c.source_hashes() != sources:
            raise ValueError('sources changed during preparation')
        c.seal(prep)
        verify_preparation(session)
        print('Prepared V19 '+str(session)+'. Functional checks passed; full quiet-host qualification remains required.', flush=True)
    except BaseException as e:
        c.save(prep/'preparation_failure.json', dict(error=str(e), traceback=traceback.format_exc(), time=time.time()))
        c.seal(prep)
        raise


def environment(session):
    if (session/'environment.json').exists():
        verify_environment(session)
    run.old.prepare_environment(session)
    if not (session/'environment_seal.json').exists():
        c.save(session/'environment_seal.json', dict(files_sha256={
            n: c.digest(session/n) for n in ('environment.json', 'initial-settling.json')}))
    verify_environment(session)


def qualify_receipt(session):
    out = session/'qualification'
    if out.exists():
        return verify_qualification(session)
    refs = {}
    for config in c.rehearsals():
        d = valid_attempt(session, 'qualify', config['trial'])
        if d is None:
            raise ValueError('full-duration rehearsal incomplete')
        refs[config['arm']] = dict(path=str(d.relative_to(session)), seal=c.digest(d/'seal.json'))
    out.mkdir()
    c.save(out/'result.json', dict(passed=True, performance_run=False, rehearsals=refs,
        preparation_seal=c.digest(session/'preparation/seal.json'), environment_seal=c.digest(session/'environment_seal.json')))
    c.seal(out)
    try:
        result = verify_qualification(session)
    except Exception as e:
        c.save(out/'capacity_failure.json', dict(error=str(e)))
        c.seal(out)
        raise
    print('Both full-duration rehearsals passed; V19 performance stage is ready.', flush=True)
    return result


def run_foreground(session, mode):
    if os.geteuid() == 0:
        raise ValueError('normal-user orchestration required; no root tracing is used')
    os.sched_setaffinity(0, {0, 1})
    def interrupted(signum, frame):
        raise InterruptedError('benchmark interrupted')
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    with (session/'.worker.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('another V19 worker owns this session')
        c.save(session/'owner.json', c.process_identity(os.getpid()))
        verify_preparation(session)
        if mode in ('start', 'resume'):
            verify_qualification(session)
        if mode in ('run', 'start') and any((session/'trials').glob('*/attempt-*')):
            raise ValueError('existing measurement attempts; use explicit resume')
        run.require_quiet_host()
        run.old.check_topology()
        environment(session)
        if mode in ('run', 'qualify'):
            if (session/'qualification').exists():
                verify_qualification(session)
            else:
                for config in pending(session, 'qualify'):
                    verify_preparation(session)
                    collect(session, session/'rehearsals'/config['trial']/f'attempt-{time.time_ns()}', config, 'qualify')
                qualify_receipt(session)
            if mode == 'qualify':
                c.save(session/'progress.json', dict(stage='qualified', timestamp=time.time(), log=str(session)))
                return
        verify_qualification(session)
        for config in pending(session, 'start'):
            verify_preparation(session)
            verify_environment(session)
            collect(session, session/'trials'/config['trial']/f'attempt-{time.time_ns()}', config, 'start')
        analyze(session)
        report = verify_completion(session)
        c.save(session/'progress.json', dict(stage='complete', decision=report['decision'], timestamp=time.time(), log=str(session)))
        print('All 18 trials and independent raw replay verified. Decision: '+report['decision'], flush=True)


def export_csv(path, rows):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', newline='') as f:
        if fields:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)


def analyze(session):
    verify_preparation(session, current=False)
    rows, requests, phase_groups, interruptions, gaps = [], [], [], [], []
    refs = {}
    for config in c.matrix():
        for d in attempts(session, 'start', config['trial']):
            c.verify_seal(d)
            if (d/'interruption.json').exists():
                interruptions.append(dict(trial=config['trial'], block=config['block'],
                    path=str(d.relative_to(session)), **c.read(d/'interruption.json')))
        d = valid_attempt(session, 'start', config['trial'])
        if d is None:
            gaps.append(config['trial'])
            continue
        result = analysis.replay(d)
        if result != c.read(d/'derived.json'):
            raise ValueError('saved derivation differs from raw replay')
        rows.append(result['summary'])
        requests.extend(dict(trial=config['trial'], block=config['block'], arm=config['arm'], **r) for r in result['requests'])
        phase_groups.extend(result['phase_groups'])
        refs[config['trial']] = dict(path=str(d.relative_to(session)), seal=c.digest(d/'seal.json'))
    interrupted_blocks = sorted({r['block'] for r in interruptions})
    report = analysis.compare(rows, interrupted_blocks)
    report.update(attempts=refs, interruptions=interruptions, interrupted_blocks=interrupted_blocks,
                  trial_gaps=gaps, preparation_seal=c.digest(session/'preparation/seal.json'))
    out = session/'analysis'/str(time.time_ns())
    out.mkdir(parents=True)
    for name, values in [('requests', requests), ('trials', rows), ('blocks', report['blocks']), ('phases', phase_groups)]:
        export_csv(out/(name+'.csv'), values)
    c.save(out/'report.json', report)
    lines = ['# V19 worker-control discovery', '', '**Decision: '+report['decision']+'**', '', analysis.LIMITATION, '',
        'Primary: timely successful responses by 500 ms / all offers. Failed and dropped offers remain in requests.csv.', '',
        '| Block | A/B delta (pp) | One minus mean(A,B) (pp) | A/B screen | Guardrails |', '|---|---:|---:|---|---|']
    for b in report['blocks']:
        if b['complete']:
            lines.append(f"| {b['block']} | {b['aa']['timely_500_delta']*100:.3f} | {b['one_vs_mean']['timely_500_delta']*100:.3f} | {b['aa']['within_screen']} | {b['one_vs_mean']['guardrails_pass']} |")
        else:
            lines.append(f"| {b['block']} | — | — | incomplete | incomplete |")
    lines += ['', 'The independent verifier checks raw joins, exports, decision rules and all sealed attempt references.', '',
              'Interrupted blocks: '+str(interrupted_blocks), '', '![Block effects](block_effects.png)', '', '![Burst stages](burst_stages.png)', '']
    (out/'report.md').write_text('\n'.join(lines))
    python = c.ROOT/'venv/bin/python'
    plotted = subprocess.run([str(python), str(c.ROOT/'diagnostic/plot_worker_control.py'), str(out)],
        capture_output=True, text=True, timeout=60, env=dict(os.environ, MPLCONFIGDIR='/tmp/v19-matplotlib'))
    c.save(out/'plot_receipt.json', dict(returncode=plotted.returncode, stdout=plotted.stdout, stderr=plotted.stderr))
    if plotted.returncode:
        raise ValueError('V19 plot generation failed; retained analysis available at '+str(out))
    c.seal(out)
    c.save(session/'latest_analysis.json', dict(path=str(out.relative_to(session)), seal=c.digest(out/'seal.json')))
    print('V19 analysis: '+report['decision']+'; '+str(out), flush=True)
    return out


def status(session):
    result = c.read(session/'progress.json') if (session/'progress.json').exists() else dict(stage='prepared')
    def marked(mode, trial):
        return any((d/'complete.json').exists() and c.read(d/'complete.json').get('valid') for d in attempts(session, mode, trial))
    result.update(completed_trials=sum(marked('start', v['trial']) for v in c.matrix()),
        completed_rehearsals=sum(marked('qualify', v['trial']) for v in c.rehearsals()),
        completion_counts='markers only; full verification is offline', log=str(session))
    print(json.dumps(result, indent=2), flush=True)


def stop(session):
    owner = c.read(session/'owner.json')
    if owner['uid'] != os.getuid():
        raise ValueError('only the original user can stop this study')
    try:
        current = c.process_identity(owner['pid'])
    except FileNotFoundError:
        return
    if current['start_ticks'] != owner['start_ticks'] or current['uid'] != owner['uid']:
        raise ValueError('worker PID reused; refusing signal')
    if current['state'] not in ('Z', 'X'):
        os.kill(owner['pid'], signal.SIGTERM)


def audit_cleanup(session):
    prep = session/'preparation'
    c.verify_seal(prep)
    records = []
    for path in sorted(prep.rglob('ownership.json')):
        ownership = c.read(path)
        if c.same_process(ownership['owner']):
            raise ValueError('preparation owner still active; no cleanup audit during work')
        inspect = owned_inspect(ownership['container'], ownership['nonce'])
        initial = path.parent/'initial.json'
        group = Path(c.read(initial)['cgroup']) if initial.exists() else None
        records.append(dict(attempt=str(path.parent.relative_to(session)),
            container=ownership['container'], actual_container_absent=inspect is None,
            cgroup=None if group is None else str(group), actual_cgroup_absent=group is not None and not group.exists()))
    out = session/'cleanup_audits'/str(time.time_ns())
    out.mkdir(parents=True)
    c.save(out/'audit.json', dict(original_preparation_seal=c.digest(prep/'seal.json'),
        records=records, all_absent=bool(records) and all(r['actual_container_absent'] and r['actual_cgroup_absent'] for r in records),
        historical_failure_preserved=True))
    c.seal(out)
    if not records or not all(r['actual_container_absent'] and r['actual_cgroup_absent'] for r in records):
        raise ValueError('owned residue remains or cgroup identity unobserved: '+str(out))
    print('Owned container/cgroup absence verified; original failed receipt preserved: '+str(out))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare', 'verify-preparation', 'qualify', 'start', 'resume', 'run',
        'status', 'watch', 'stop', 'analyze', 'verify-completion', 'audit-cleanup', '_foreground'))
    p.add_argument('--directory', type=c.owned_directory, required=True)
    p.add_argument('--mode', choices=('qualify', 'start', 'resume', 'run'))
    args = p.parse_args()
    session = args.directory
    try:
        if args.command == 'prepare':
            prepare(session)
        elif args.command == 'verify-preparation':
            verify_preparation(session)
            print('V19 preparation verified. Full quiet-host qualification status is separate.')
        elif args.command == 'analyze':
            analyze(session)
        elif args.command == 'verify-completion':
            report = verify_completion(session)
            print('Complete evidence and block-level decision replay verified: '+report['decision'])
        elif args.command in ('status', 'watch'):
            os.sched_setaffinity(0, {0, 1})
            while True:
                status(session)
                if args.command == 'status':
                    break
                time.sleep(5)
        elif args.command == 'stop':
            stop(session)
        elif args.command == 'audit-cleanup':
            audit_cleanup(session)
        elif args.command == '_foreground':
            if args.mode is None:
                p.error('_foreground requires --mode')
            run_foreground(session, args.mode)
        else:
            verify_preparation(session)
            if args.command in ('start', 'resume'):
                verify_qualification(session)
            print('Fully quit Codex/ChatGPT, then launch in an external terminal:')
            print(f'{c.ROOT}/diagnostic/start_worker_control.sh {args.command} {session}')
    except (Exception, KeyboardInterrupt) as e:
        print('V19 worker control: '+str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
