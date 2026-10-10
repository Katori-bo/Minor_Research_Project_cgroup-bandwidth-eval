"""Read-only terminal progress display; no sampling thread in the experiment."""
import datetime as dt
import os
import sys
import time

import pipeline
import run


def read_live(path):
    try:return run.read(path)
    except (OSError,ValueError):return {}


def elapsed(start,end=None):
    try:
        begin=dt.datetime.fromisoformat(start)
        finish=dt.datetime.fromisoformat(end) if end else dt.datetime.now().astimezone()
        return max(0,(finish-begin).total_seconds())
    except (TypeError,ValueError):return None


def duration(seconds):
    if seconds is None:return 'unavailable'
    value=int(seconds);return f'{value//3600:02d}:{value//60%60:02d}:{value%60:02d}'


def snapshot(directory):
    workflow=read_live(directory/'workflow-status.json');session=directory/'session'
    progress=read_live(session/'status.json');launch=read_live(directory/'launch.json')
    state=workflow.get('state','not_started')
    if state in ('starting','running') and not pipeline.is_running(directory):state='interrupted'
    completed=progress.get('completed',0);total=progress.get('total',8)
    result=dict(state=state,stage=workflow.get('stage','not started'),completed=completed,total=total,
        percent=100*completed/total if total else 0,current=progress.get('current'),
        overall_elapsed_sec=elapsed(launch.get('at') or workflow.get('created_at'),
            workflow.get('updated_at') if state in ('complete','failed','interrupted') else None),
        temperatures=run.old.temperatures(),phase='not started',trial_elapsed_sec=None,
        baseline=read_live(session/'environment.json').get('baseline_c',{}),log=launch.get('log'))
    if state in ('complete','failed','interrupted'):
        result['phase']=state;return result
    if result['current']:
        attempts=run.attempt_dirs(session/'attempts'/result['current'])
        if attempts:
            attempt=attempts[-1];result['attempt']=attempt.name
            result['trial_elapsed_sec']=elapsed(read_live(attempt/'started.json').get('at'))
            settling=read_live(attempt/'settling.json')
            if (attempt/'complete.json').exists():result['phase']='validating trial'
            elif (attempt/'loadgen.json').exists():result['phase']='draining / exporting / validating'
            elif (attempt/'monitor.log').exists():result['phase']='measurement (60 s) / client drain'
            elif settling.get('accepted'):result['phase']='service startup / warmup (20 s)'
            else:result['phase']='trial cooling / settling'
            if result['phase']=='trial cooling / settling' and settling.get('samples'):
                result['settling_elapsed_sec']=settling['samples'][-1]['elapsed_sec']
                result['settling_minimum_sec']=settling['policy']['window_sec']
            return result
        result['phase']='preparing trial';return result
    if progress.get('state')=='complete' or workflow.get('stage')=='analyze-remedy-sufficiency':
        result['phase']='analysis';return result
    settles=sorted(session.glob('*settling*.json'),key=lambda p:p.stat().st_mtime)
    settling=read_live(settles[-1]) if settles else {}
    if settling and not settling.get('accepted'):
        result['phase']='initial / resume idle and cooling'
        if settling.get('samples'):
            result['settling_elapsed_sec']=settling['samples'][-1]['elapsed_sec']
            result['settling_minimum_sec']=settling['policy']['initial_idle_sec']
    elif state in ('starting','running'):result['phase']='preflight / between trials'
    return result


def print_progress(value):
    print(f'Trials: {value["completed"]}/{value["total"]} complete ({value["percent"]:.1f}%)')
    if value['current']:
        print(f'Current: {min(value["completed"]+1,value["total"])}/{value["total"]} '
              f'{value["current"]} (attempt {value.get("attempt","pending")})')
    print(f'Phase: {value["phase"]} | Elapsed: {duration(value["overall_elapsed_sec"])}')
    if value['trial_elapsed_sec'] is not None:print('Current trial elapsed:',duration(value['trial_elapsed_sec']))
    if 'settling_elapsed_sec' in value:
        print(f'Settling: {value["settling_elapsed_sec"]:.0f}s / minimum {value["settling_minimum_sec"]}s; '
              'waiting for the stable temperature window')
    temps=value['temperatures']
    print('Temperatures now: '+(', '.join(f'{k}={v:.1f}°C' for k,v in sorted(temps.items())) if temps else 'unavailable'))
    baseline=value['baseline']
    if baseline:
        print('Baseline: '+', '.join(f'{k}={v:.1f}°C' for k,v in sorted(baseline.items())))


def watch(directory,interval=5):
    if interval<2:raise ValueError('watch interval must be at least two seconds')
    # Keep the display off the service CPUs, like the retained client/monitor.
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{int(c) for c in run.old.CLIENT_CPUS.split(',')})
    try:
        while True:
            value=snapshot(directory)
            if sys.stdout.isatty():print('\033[2J\033[H',end='')
            print('Bursty parallelism study | '+run.now())
            print(f'State: {value["state"]} | Stage: {value["stage"]}')
            print_progress(value)
            if value['log']:print('Log:',value['log'])
            print('Ctrl+C closes this display; the background experiment continues.',flush=True)
            if value['state'] in ('complete','failed','interrupted'):return
            time.sleep(interval)
    except KeyboardInterrupt:return
