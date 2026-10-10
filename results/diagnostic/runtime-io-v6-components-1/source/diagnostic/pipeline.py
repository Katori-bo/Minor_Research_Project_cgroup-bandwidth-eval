#!/usr/bin/env python3
"""Run the protected diagnostic pilot; full collection requires explicit --full."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess as sp
import sys
import time
import traceback
import uuid

import run as runner

DEFAULT_DIRECTORY = runner.ROOT / 'results/diagnostic/runtime-io-v6'
ACTIVE_STATES = {'starting', 'running'}


def update_status(directory, state, stage, **details):
    path = directory / 'workflow-status.json'
    status = runner.read(path) if path.exists() else {'created_at': runner.now()}
    status.update(state=state, stage=stage, updated_at=runner.now(), **details)
    runner.put(path, status)
    with (directory / 'workflow-events.jsonl').open('a') as out:
        out.write(json.dumps({'at': status['updated_at'], 'state': state, 'stage': stage, **details}) + '\n')
    return status


def stage_command(directory, stage, command, lock):
    update_status(directory, 'running', stage, command=list(map(str, command)))
    print(f'\n[{runner.now()}] {stage}: {shlex.join(list(map(str, command)))}', flush=True)
    env = dict(os.environ, CPU_QUOTA_EXPERIMENT_LOCK_FD=str(lock.fileno()), PYTHONUNBUFFERED='1')
    process = sp.Popen(list(map(str, command)), cwd=runner.ROOT, env=env,
                       pass_fds=(lock.fileno(),), start_new_session=True)
    try:
        code = process.wait()
        if code:
            raise RuntimeError(f'{stage} exited with code {code}; see this launch log for the reason')
    finally:
        if process.poll() is None:
            # run.py handles SIGTERM and cleans up its own Docker container and children.
            process.terminate()
            try:
                process.wait(timeout=30)
            except sp.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    with (directory / 'workflow-events.jsonl').open('a') as out:
        out.write(json.dumps({'at': runner.now(), 'stage': stage, 'state': 'stage_complete'}) + '\n')


def collection_command(session, pilot=False, pilot_session=None):
    if session.exists() and not (session / 'metadata.json').exists():
        raise RuntimeError(f'{session} exists without session metadata. Inspect it; no files were overwritten.')
    action = 'resume' if (session / 'metadata.json').exists() else 'new'
    command = [sys.executable, '-u', runner.HERE / 'run.py', action, '--session', session]
    if action == 'new':
        if pilot:
            command.append('--pilot')
        else:
            command += ['--pilot-session', pilot_session]
    return command


def write_completion(directory, pilot, full):
    # The analyzer has just verified all raw trials before this file is written.
    estimates = runner.read(full / 'analysis/estimates.json')
    validation = runner.read(full / 'analysis/validation.json')
    if not validation['passed']:
        raise RuntimeError('Full analysis did not validate')
    report = ['# CPU quota timing diagnostic completed', '', f'Completed: {runner.now()}', '',
              f'- Pilot: {len(runner.read(pilot / "matrix.json"))} validated diagnostic trials.',
              f'- Full experiment: {len(runner.read(full / "matrix.json"))} validated trials.',
              '- Research results exclude the pilot.', '',
              f'[All trial results]({full / "analysis/report.md"})', '',
              f'[Trial CSV]({full / "analysis/trials.csv"})', '',
              f'[Estimates and uncertainty]({full / "analysis/estimates.json"})', '',
              f'[Attempt audit]({full / "analysis/attempt_audit.csv"})', '',
              f'[Pilot checks]({pilot / "analysis/pilot_gate.json"})', '',
              '## Timing interaction', '']
    for metric, values in estimates.items():
        if 'interaction_ms' in values:
            lo, hi = values['interaction_ms_ci95']
            report.append(f'- {metric}: {values["interaction_ms"]:.2f} ms '
                          f'(trial-bootstrap 95% interval {lo:.2f} to {hi:.2f} ms).')
    report += ['', 'These are trial-level timing estimates. Review the remaining client/server boundary and all failure rates before asserting a cause.', '']
    (directory / 'COMPLETED.md').write_text('\n'.join(report))
    runner.put(directory / 'completion.json', {'completed_at': runner.now(),
        'pilot_session': str(pilot), 'full_session': str(full),
        'report_sha256': runner.sha(directory / 'COMPLETED.md'),
        'estimates_sha256': runner.sha(full / 'analysis/estimates.json')})


def execute(directory, lock, full_collection=False):
    """Stop on any failed stage. Explicit reruns resume the same saved sessions."""
    pilot, full = directory / 'pilot', directory / 'full'
    existing = [session for session in (pilot, full) if (session / 'metadata.json').exists()]
    if existing:
        update_status(directory, 'running', 'verify-existing-build')
        runner.verify_build()  # Rebuilding would invalidate an existing session's provenance.
        for session in existing:
            runner.verify_session(session)
    else:
        stage_command(directory, 'build-and-go-tests', [runner.HERE / 'build.sh'], lock)
        runner.verify_build()
    stage_command(directory, 'python-regression-tests',
                  [sys.executable, '-m', 'unittest', 'discover', '-s', runner.HERE, '-p', 'test_*.py', '-v'], lock)
    stage_command(directory, 'pilot-collection', collection_command(pilot, pilot=True), lock)
    stage_command(directory, 'pilot-analysis', [sys.executable, runner.HERE / 'analyze.py', pilot], lock)
    runner.require_pilot(pilot)
    if not full_collection:
        report = directory / 'PILOT_COMPLETED.md'
        report.write_text('# Runtime and I/O trace pilot completed\n\n'
            f'Completed: {runner.now()}\n\n'
            f'{len(runner.read(pilot / "matrix.json"))} trials passed validation and the overhead gate.\n\n'
            f'[Timing report]({pilot / "analysis/report.md"})\n\n'
            f'[Pilot gate]({pilot / "analysis/pilot_gate.json"})\n\n'
            'Review matched request timelines and trace scheduler states before choosing any intervention. '
            'A passing overhead gate does not establish a mechanism. Full collection requires an explicit --full launch.\n')
        update_status(directory, 'complete', 'pilot-complete', report=str(report))
        print(f'\nPILOT COMPLETE: {report}', flush=True)
        return
    if (full / 'metadata.json').exists():
        metadata = runner.read(full / 'metadata.json')
        if metadata['pilot_session'] != str(pilot) or metadata['pilot_gate_sha256'] != runner.sha(pilot / 'analysis/pilot_gate.json'):
            raise RuntimeError('The pilot evidence differs from the pilot recorded by the full session')
    stage_command(directory, 'full-collection', collection_command(full, pilot_session=pilot), lock)
    stage_command(directory, 'full-analysis', [sys.executable, runner.HERE / 'analyze.py', full], lock)
    write_completion(directory, pilot, full)
    update_status(directory, 'complete', 'complete', report=str(directory / 'COMPLETED.md'))
    print(f'\nCOMPLETE: {directory / "COMPLETED.md"}', flush=True)


def run_worker(directory, full_collection=False):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.worker.lock').open('a') as worker_lock:
        try:
            fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('This workflow is already running')
        lock = None
        def stop(signum, frame):
            raise KeyboardInterrupt(f'signal {signum}')
        previous_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, stop)
        update_status(directory, 'running', 'acquire-experiment-lock', worker_pid=os.getpid(), error=None)
        try:
            lock = runner.acquire_experiment_lock()
            execute(directory, lock, full_collection=full_collection)
        except BaseException as exc:
            state = 'interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed'
            previous = runner.read(directory / 'workflow-status.json')
            update_status(directory, state, previous['stage'], error=str(exc) or type(exc).__name__)
            print(f'\nSTOPPED ({state}): {exc}\nEvidence preserved in {directory}.', flush=True)
            traceback.print_exc()
            return 130 if state == 'interrupted' else 1
        finally:
            signal.signal(signal.SIGTERM, previous_handler)
            if lock:
                lock.close()
    return 0


def process_signature(pid):
    """Linux PID plus start tick prevents treating an unrelated reused PID as our job."""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rpartition(')')[2].split()
        return None if fields[0] == 'Z' else fields[19]
    except (OSError, IndexError):
        return None


def is_running(directory):
    path = directory / '.worker.lock'
    if path.exists():
        with path.open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
    path = directory / 'launch.json'
    if path.exists():
        launch = runner.read(path)
        signature = process_signature(launch['pid'])
        return signature is not None and signature == launch['start_tick']
    return False


def print_status(directory):
    path = directory / 'workflow-status.json'
    if not path.exists():
        print('Not started. Run ./diagnostic/run_all.sh')
        return
    status = runner.read(path)
    state = status['state']
    if state in ACTIVE_STATES and not is_running(directory):
        state = 'interrupted (process no longer running)'
    print(f'State: {state}\nStage: {status["stage"]}\nOutput: {directory}')
    for phase in ('pilot', 'full'):
        p = directory / phase / 'status.json'
        if p.exists():
            progress = runner.read(p)
            print(f'{phase.capitalize()}: {progress["completed"]}/{progress["total"]} trials, {progress["state"]}')
    if status.get('error'):
        print('Reason:', status['error'])
    if (directory / 'launch.json').exists():
        print('Log:', runner.read(directory / 'launch.json')['log'])
    if state == 'complete':
        print('Report:', status.get('report', str(directory / 'COMPLETED.md')))


def launch(directory, full_collection=False):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.launch.lock').open('a') as launch_lock:
        fcntl.flock(launch_lock, fcntl.LOCK_EX)
        if is_running(directory):
            print_status(directory)
            return 0
        status = directory / 'workflow-status.json'
        completed = (directory / 'COMPLETED.md').exists() or (
            not full_collection and (directory / 'PILOT_COMPLETED.md').exists())
        if status.exists() and runner.read(status)['state'] == 'complete' and completed:
            print_status(directory)
            return 0
        logs = directory / 'logs'
        logs.mkdir(exist_ok=True)
        logfile = logs / f'{time.time_ns()}-{uuid.uuid4().hex[:8]}.log'
        command = [sys.executable, '-u', str(Path(__file__).resolve()), 'foreground', '--directory', str(directory)]
        if full_collection:
            command.append('--full')
        inhibitor = shutil.which('systemd-inhibit')
        if inhibitor:
            command = [inhibitor, '--no-ask-password', '--what=idle:sleep', '--mode=block', '--who=CPU quota experiment',
                       '--why=Unattended controlled measurements', '--'] + command
        update_status(directory, 'starting', 'launch', error=None, sleep_inhibitor=bool(inhibitor))
        try:
            with logfile.open('x') as output:
                process = sp.Popen(command, cwd=runner.ROOT, stdin=sp.DEVNULL, stdout=output,
                                   stderr=sp.STDOUT, start_new_session=True)
            runner.put(directory / 'launch.json', {'pid': process.pid, 'start_tick': process_signature(process.pid),
                'log': str(logfile), 'launched_at': runner.now(), 'command': command})
        except Exception as exc:
            update_status(directory, 'failed', 'launch', error=str(exc))
            raise
        for _ in range(100):
            state = runner.read(status)['state']
            if state != 'starting' or process.poll() is not None:
                break
            time.sleep(.1)
        if process.poll() is not None and runner.read(status)['state'] == 'starting':
            detail = logfile.read_text()[-4000:]
            update_status(directory, 'failed', 'launch', error=detail or f'Launcher exited {process.returncode}')
        print_status(directory)
        state = runner.read(status)['state']
        if state in ('failed', 'interrupted'):
            return 1
        print('Runs in the background; you may close this terminal. Re-run the same command to resume after a stop.')
        if not inhibitor:
            print('Automatic sleep inhibition is unavailable; keep the machine awake with the lid open.')
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['start', 'status', 'foreground'], default='start')
    parser.add_argument('--directory', type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument('--full', action='store_true',
                        help='Continue into full collection after reviewing the focused pilot')
    args = parser.parse_args()
    directory = args.directory.resolve()
    root = runner.ROOT / 'results/diagnostic'
    if not directory.is_relative_to(root) or directory == root:
        parser.error('--directory must be a subdirectory of results/diagnostic')
    if args.action == 'status':
        print_status(directory)
        return 0
    if args.action == 'foreground':
        return run_worker(directory, full_collection=args.full)
    return launch(directory, full_collection=args.full)


if __name__ == '__main__':
    raise SystemExit(main())
