#!/usr/bin/env python3
"""Final bounded minimal-SHA instruction/cycle screen; no automatic extension."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

import minimal_computation_screen as base
import period_cost as pc
import period_cost_perf as hw

c, gc, ROOT = base.c, base.gc, base.ROOT
BASE = base.PARENT/'generation-02'
PARENT = ROOT/'analysis/runtime_io_minimal_counter_closing'
DEFAULT = PARENT/'generation-02'
NEW = ('diagnostic/minimal_counter_closing.py', 'diagnostic/minimal_counter_helper.py',
       'diagnostic/test_minimal_counter_closing.py', 'diagnostic/start_minimal_counter_closing.sh',
       'docs/runtime_io_minimal_counter_closing.md', 'diagnostic/period_cost.py',
       'diagnostic/period_cost_perf.py', 'diagnostic/period_cost_fixture.c')
FACTORS = {'A': (100,False), 'B': (20,False), 'C': (100,True), 'D': (20,True)}
LIMITS = dict(cpu_observer=.01, capacity_observer=.01, delivery_observer=.01,
              period_signal=.02, instructions_stable=.01, decomposition_signal=.02,
              counter_native_alignment=.005, wall_ceiling_sec=2100,
              per_trial_settle_ceiling_sec=180)


def matrix():
    return [dict(trial=f'b{b}_{a}',block=b,arm=a,order=(b-1)*4+i+1,kind='minimal',
                 period_ms=FACTORS[a][0],counters=FACTORS[a][1])
            for b,order in enumerate(('ABCD','DCBA'),1) for i,a in enumerate(order)]


def owned(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use a dedicated direct closing-screen generation')
    return p


def durations(spec,functional=False):
    return dict(MINIMAL_WARMUP_MS='1000' if functional else '20000',
                MINIMAL_MEASURE_MS='2000' if functional else '30000',GOGC='100')


def config_for(spec,functional=False):
    return gc.legacy_config(dict(block=1,period_ms=spec['period_ms']),functional)


def sources():
    return dict(base.source_hashes(),**{n:c.digest(ROOT/n) for n in NEW})


def verify(session,current=True):
    prep=session/'preparation'; c.verify_seal(prep); m=c.read(prep/'manifest.json')
    b=base.verify_preparation(BASE,current=current)
    if (m['matrix']!=matrix() or m['closing_limits']!=LIMITS or not m['tests_passed']
            or not m['functional_passed'] or m['performance_run']
            or m['base_preparation_seal']!=c.digest(BASE/'preparation/seal.json')):
        raise ValueError('closing preparation incomplete or changed')
    for k in ('image','server_sha256','gate_sha256','loadgen_sha256','resource_baseline',
              'minimal_image','minimal_server_sha256'):
        if m[k]!=b[k]: raise ValueError('retained input changed: '+k)
    for name,key in [('gate','gate_sha256'),('minimal.server','minimal_server_sha256'),('fixture','fixture_sha256')]:
        if c.digest(prep/name)!=m[key]: raise ValueError('binary changed: '+name)
    for n,sha in m['sources'].items():
        if c.digest(prep/'source'/n)!=sha or (current and c.digest(ROOT/n)!=sha):
            raise ValueError('source changed: '+n)
    if current and (m['sources']!=sources() or m['baseline']!=c.baseline()
                    or m['perf_sha256']!=c.digest(Path('/usr/bin/perf'))):
        raise ValueError('boot/tool/source environment changed')
    for period in (100,20):
        p=prep/'functional'/str(period)
        if replay(p,session,True)!=c.read(p/'closing_derived.json'):
            raise ValueError('functional replay differs')
    return m


class Helper(pc.Helper):
    def __init__(self,session):
        self.log=(session/'helper.stderr').open('x')
        self.process=subprocess.Popen(['sudo','-n','/usr/bin/python3',
            str(ROOT/'diagnostic/minimal_counter_helper.py'),'--directory',str(session)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log)
        try:
            if json.loads(hw.line(self.process.stdout,15,self.process))!={'ready':True}:
                raise ValueError('counter helper did not initialize')
        except BaseException:
            self.close(); raise


def wait_record(service,event,seconds):
    until=time.monotonic()+seconds+20
    while True:
        service.observe(); rows=service.records()
        if any(r['event']==event for r in rows): return rows
        if time.monotonic()>until: raise TimeoutError('native boundary timeout: '+event)
        time.sleep(1)


def collect(session,directory,spec,helper=None,functional=False):
    directory.mkdir(parents=True); c.save(directory/'closing_config.json',spec)
    config=config_for(spec,functional); c.save(directory/'config.json',config)
    service=base.MinimalService(session,config,directory,spec,functional)
    attached=False; enabled=False; failure=None
    try:
        if not functional:
            gc.run.require_quiet_host(); env=c.read(session/'environment.json')
            c.save(directory/'environment.json',env)
            print(f"{spec['order']}/8 {spec['trial']}: settling (maximum 3 minutes)",flush=True)
            with patch.dict(gc.run.old.POLICY,timeout_sec=120):
                gc.run.old.settle(directory/'settling.json',env['baseline_c'],expected_power=env['power_settings'])
        with patch.object(base,'minimal_environment',durations): service.create()
        observations={'startup':service.observe()}; service.release()
        wait_record(service,'warmup_done',1 if functional else 20)
        if helper:
            helper.request('attach'); attached=True
            helper.request('enable'); enabled=True
        observations['measurement_start']=service.observe()
        base.bridge.release_fifo(directory/'qualification/measure.fifo')
        print(f"{spec['order']}/8 {spec['trial']}: measurement",flush=True)
        rows=wait_record(service,'measurement_done',2 if functional else 30)
        observations['measurement_stop']=service.observe()
        if helper:
            helper.request('disable'); enabled=False
            helper.request('detach'); attached=False
        c.save(directory/'native_records.json',rows)
        c.save(directory/'observations.json',observations)
        c.save(directory/'resource_samples.json',service.resources)
        if not functional and gc.power_settings(include_profile=True)!=env['power_settings']:
            raise ValueError('power settings changed')
        service.close(); c.seal(directory)
        result=replay(directory,session,functional)
        c.save(directory/'closing_derived.json',result)
        c.save(directory/'complete.json',dict(valid=True,performance_run=not functional)); c.seal(directory)
    except BaseException as e:
        failure=str(e); c.save(directory/'failure.json',dict(error=failure,traceback=traceback.format_exc())); raise
    finally:
        if attached:
            try:
                if enabled: helper.request('disable')
                helper.request('detach')
            except Exception as e: c.save(directory/'counter_cleanup_failure.json',dict(error=str(e)))
        try: service.close(failure)
        finally:
            if failure: c.seal(directory)


def counter_metrics(directory,native):
    spec=c.read(directory/'closing_config.json')
    counts,bounds=pc.validate_counter(directory,spec['counters'])
    receipt=c.read(directory/'perf_receipt.json')
    if receipt['cgroup']!=c.read(directory/'initial.json')['cgroup']:
        raise ValueError('counter cgroup differs from actual workload')
    start,stop=receipt['controls'][1:]
    if not start['after_ns']<=native['start_monotonic_ns']<native['stop_monotonic_ns']<=stop['before_ns']:
        raise ValueError('hardware interval does not contain native work')
    cpu=(native['cpu_stop_ns']-native['cpu_start_ns'])/1000
    if bounds['usage_usec']['lower']<=0 or max(abs(bounds['usage_usec'][k]/cpu-1)
            for k in ('lower','upper'))>LIMITS['counter_native_alignment']:
        raise ValueError('counter/native CPU alignment exceeds 0.5%')
    metrics={}
    if counts:
        user=bounds['user_usec']
        if user['lower']<=0: raise ValueError('no measured user CPU')
        metrics=dict(instructions_per_job=counts['instructions']/native['jobs'],
            cycles_per_instruction=counts['cycles_per_instruction'],
            cycles_per_user_cpu_sec=counts['cycles']/(user['midpoint']/1e6),
            cycles_per_user_cpu_sec_lower=counts['cycles']/(user['upper']/1e6),
            cycles_per_user_cpu_sec_upper=counts['cycles']/(user['lower']/1e6))
    return dict(counts=counts,bounds=bounds,metrics=metrics)


def replay(directory,session,functional=False):
    c.verify_seal(directory)
    if any((directory/n).exists() for n in ('failure.json','counter_cleanup_failure.json','watchdog_cleanup.json')):
        raise ValueError('failed or interrupted trial')
    spec=c.read(directory/'closing_config.json'); m=c.read(session/'preparation/manifest.json')
    if not functional and spec not in matrix(): raise ValueError('outside frozen sequence')
    config=config_for(spec,functional); initial=c.read(directory/'initial.json')
    container=c.read(directory/'container.json')['inspect']
    if c.read(directory/'config.json')!=config: raise ValueError('resource config changed')
    c.validate_resources(initial['initial_limits'],container['HostConfig'],m['resource_baseline'],config)
    if (container['Image']!=m['minimal_image'] or initial['container_server_sha256']!=m['minimal_server_sha256']
            or c.digest(directory/'container.server')!=m['minimal_server_sha256']):
        raise ValueError('actual computation executable differs')
    expected=['GOMAXPROCS=1','WORKERS=1','QUEUE_SIZE=128','INSTRUMENT=1','WORKER_YIELD=0',
              'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
    expected += [k+'='+v for k,v in durations(spec,functional).items()]
    if sorted(container['Config']['Env'])!=sorted(expected): raise ValueError('workload environment changed')
    rows=c.read(directory/'native_records.json')
    logged=[json.loads(x) for x in (directory/'container.stdout').read_text().splitlines()]
    if [r for r in logged if r['event']!='ready']!=rows or (directory/'container.stderr').read_text():
        raise ValueError('native output differs')
    if [r['duration_ms'] for r in rows[1:]]!=([1000,2000] if functional else [20000,30000]):
        raise ValueError('measurement duration changed')
    summary=base.minimal_summary(rows,c.read(directory/'observations.json'),base.vector(),functional)
    cleanup=c.read(directory/'cleanup.json')
    if (cleanup['errors'] or not cleanup['container_removed'] or not cleanup['cgroup_removed']
            or cleanup['watchdog_intervened'] or cleanup['tracing_used']): raise ValueError('cleanup failed')
    peak=max(r['memory_peak_bytes'] for r in c.read(directory/'resource_samples.json'))
    if peak>gc.MEMORY_GUARD_BYTES: raise ValueError('memory guard exceeded')
    counter=None
    if not functional:
        gc.verify_environment(session)
        if c.read(directory/'environment.json')!=c.read(session/'environment.json'):
            raise ValueError('environment provenance differs')
        counter=counter_metrics(directory,rows[-1])
    return dict(summary=dict(spec,**summary,memory_peak_bytes=peak,
                **({} if counter is None else counter['metrics'])),counter=counter)


def compare(rows):
    if len(rows)!=8 or {r['trial'] for r in rows}!={s['trial'] for s in matrix()}:
        raise ValueError('all eight unique cells required')
    by={r['trial']:r for r in rows}; observer=[]; contrasts=[]
    for r in rows:
        fields=['cpu_usec_per_completed_work','capacity','cpu_cores']
        if r['counters']: fields+=['instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec']
        if any(not math.isfinite(r[f]) or r[f]<=0 for f in fields):
            raise ValueError('positive finite measurements required')
    for b in (1,2):
        for off,on in [('A','C'),('B','D')]:
            a,z=(by[f'b{b}_{k}'] for k in (off,on))
            changes={f:z[f]/a[f]-1 for f in ('cpu_usec_per_completed_work','capacity','cpu_cores')}
            observer.append(dict(block=b,period_ms=a['period_ms'],changes=changes,
                passed=all(abs(changes[f])<=LIMITS[k] for f,k in
                    [('cpu_usec_per_completed_work','cpu_observer'),('capacity','capacity_observer'),('cpu_cores','delivery_observer')])))
        for enabled,arms in [(False,('A','B')),(True,('C','D'))]:
            a,z=(by[f'b{b}_{k}'] for k in arms)
            fields=['cpu_usec_per_completed_work','capacity','cpu_cores']
            if enabled: fields+=['instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec']
            contrasts.append(dict(block=b,counters=enabled,changes={f:z[f]/a[f]-1 for f in fields}))
    qualified=all(r['passed'] for r in observer)
    off=[r['changes']['cpu_usec_per_completed_work'] for r in contrasts if not r['counters']]
    on=[r['changes']['cpu_usec_per_completed_work'] for r in contrasts if r['counters']]
    large=lambda v: all(x>=LIMITS['period_signal'] for x in v) or all(x<=-LIMITS['period_signal'] for x in v)
    reproduced=large(off)
    matching=large(on) and all(a*b>0 for a,b in zip(off,on))
    hints=[]
    if not qualified: decision='close_unresolved_counter_observer_not_qualified'
    elif not reproduced or not matching: decision='close_unresolved_period_effect_not_consistent'
    else:
        measured=[r['changes'] for r in contrasts if r['counters']]
        stable=all(abs(r['instructions_per_job'])<=LIMITS['instructions_stable'] for r in measured)
        extra=all(r['instructions_per_job']>=LIMITS['decomposition_signal'] for r in measured)
        if extra: hints.append('more_user_instructions_per_job')
        if stable: hints.append('similar_user_instruction_count_with_changed_execution_cost')
        if all(r['cycles_per_instruction']>=LIMITS['decomposition_signal'] for r in measured):
            hints.append('more_cycles_per_instruction')
        if all(r['cycles_per_user_cpu_sec']<=-LIMITS['decomposition_signal'] for r in measured):
            hints.append('lower_effective_user_cycles_per_cpu_second')
        decision='close_with_supported_execution_hint' if hints else 'close_unresolved_mixed_or_small_decomposition'
    return dict(decision=decision,observer_qualified=qualified,observer_checks=observer,
        period_contrasts=contrasts,reproduced_without_counters=reproduced,execution_hints=hints,
        historical_reversal_cause_established=False,novelty_established=False,automatic_followup_authorized=False,
        limitation='Eight short cells are a closing screen, not equivalence or historical causal proof. '
        'User counts cover all Go threads, not just SHA instructions. Similar counts are a 1% practical screen. '
        'Cycles/user CPU second is an effective execution metric, not a direct frequency measurement. '
        'CPI changes do not uniquely identify caches, migration, preemption or interrupts. '
        'No counter-based causal interpretation when observer qualification fails. Close this branch after this attempt.')


def analyze(session):
    verify(session,current=False); rows=[]
    for spec in matrix():
        p=session/'trials'/spec['trial']
        if c.read(p/'complete.json')!={'valid':True,'performance_run':True}: raise ValueError('incomplete cell')
        result=replay(p,session)
        if result!=c.read(p/'closing_derived.json'): raise ValueError('raw replay differs')
        rows.append(result['summary'])
    c.verify_seal(session/'counter_fixtures')
    if pc.validate_fixtures(session/'counter_fixtures')!=c.read(session/'counter_fixtures/result.json'):
        raise ValueError('counter fixture replay differs')
    report=compare(rows); report.update(rows=rows,preparation_seal=c.digest(session/'preparation/seal.json'),
        trial_seals={s['trial']:c.digest(session/'trials'/s['trial']/'seal.json') for s in matrix()})
    out=session/'analysis'/str(time.time_ns()); out.mkdir(parents=True); c.save(out/'report.json',report)
    lines=['# Final minimal counter screen','',report['decision'],'',report['limitation'],'',
           'Observer qualified: '+str(report['observer_qualified']),
           'Execution hints: '+', '.join(report['execution_hints']),'',
           '| Block | Counters | CPU/job change | Instruction/job change | CPI change | Effective cycle-rate change |',
           '|---|---|---:|---:|---:|---:|']
    for r in report['period_contrasts']:
        v=r['changes']; fields=['cpu_usec_per_completed_work','instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec']
        lines.append('| '+str(r['block'])+' | '+str(r['counters'])+' | '+' | '.join(
            f'{100*v[f]:+.2f}%' if f in v else 'unmeasured' for f in fields)+' |')
    (out/'report.md').write_text('\n'.join(lines)+'\n'); c.seal(out)
    print(report['decision']+'; report: '+str(out/'report.md'),flush=True)


def prepare(session):
    if os.geteuid()==0 or session.exists(): raise ValueError('prepare once as normal user into a new generation')
    b=base.verify_preparation(BASE); shas=sources()
    prep=session/'preparation'; prep.mkdir(parents=True)
    for n in shas:
        p=prep/'source'/n; p.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/n,p)
    for n in ('gate','minimal.server'): shutil.copy2(BASE/'preparation'/n,prep/n)
    argv=['/usr/bin/gcc','-O2','-Wall','-Wextra','-Werror',str(prep/'source/diagnostic/period_cost_fixture.c'),'-o',str(prep/'fixture')]
    r=subprocess.run(argv,capture_output=True,text=True,timeout=30)
    c.save(prep/'compile.json',dict(argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
    if r.returncode: raise ValueError('fixture compilation failed')
    r=subprocess.run([str(prep/'fixture'),'selftest'],input='GQ',capture_output=True,text=True,timeout=10)
    c.save(prep/'fixture_selftest.json',dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
    if r.returncode or r.stderr or not r.stdout.startswith('READY\nCHILD ') or '\nDONE ' not in r.stdout:
        raise ValueError('fixture selftest failed')
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic','-p','test_minimal_counter_closing.py','-v'],
        cwd=ROOT,capture_output=True,text=True,timeout=60)
    (prep/'tests.stdout').write_text(r.stdout); (prep/'tests.stderr').write_text(r.stderr)
    if r.returncode: raise ValueError('closing tests failed')
    m=dict(b,matrix=matrix(),sources=shas,baseline=c.baseline(),closing_limits=LIMITS,
           base_preparation_seal=c.digest(BASE/'preparation/seal.json'),fixture_sha256=c.digest(prep/'fixture'),
           perf_sha256=c.digest(Path('/usr/bin/perf')),tests_passed=True,functional_passed=False,
           performance_run=False,prepared=time.time())
    c.save(prep/'manifest.json',m)
    for period in (100,20):
        spec=dict(trial=str(period),block=0,arm='A',order=0,kind='minimal',period_ms=period,counters=False)
        collect(session,prep/'functional'/str(period),spec,functional=True)
    m['functional_passed']=True; c.save(prep/'manifest.json',m)
    if sources()!=shas: raise ValueError('sources changed during preparation')
    c.seal(prep); verify(session)
    print('Prepared and verified: '+str(session)+'; performance and privileged counter fixtures unrun.',flush=True)


def run(session,audit):
    if os.geteuid()==0 or os.environ.get('QUOTA_CLOSING_EXTERNAL')!='1': raise ValueError('use external normal-user launcher')
    os.sched_setaffinity(0,{0,1})
    with gc.run.acquire_experiment_lock():
        verify(session); gc.run.require_quiet_host(); base.verify_audit(audit)
        if (session/'owner.json').exists() or (session/'trials').exists(): raise ValueError('one attempt only; retain prior evidence')
        c.save(session/'owner.json',c.process_identity(os.getpid()))
        shutil.copy2(audit,session/'audit.json')
        review=Path(audit).with_suffix('.review.json')
        if review.exists(): shutil.copy2(review,session/'audit_ownership_review.json')
        helper=monitor=log=None; prior=signal.getsignal(signal.SIGALRM)
        prior_term=signal.getsignal(signal.SIGTERM)
        def deadline(_s,_f): raise TimeoutError('35-minute closing-test ceiling reached; close branch with partial evidence')
        def terminate(_s,_f): raise KeyboardInterrupt('closing test terminated; retain evidence and clean owned resources')
        signal.signal(signal.SIGALRM,deadline); signal.alarm(LIMITS['wall_ceiling_sec'])
        signal.signal(signal.SIGTERM,terminate)
        try:
            helper=Helper(session)
            helper.request('fixtures',timeout=90)
            log=(session/'host_monitor.log').open('x')
            monitor=subprocess.Popen([sys.executable,str(ROOT/'scripts/monitor_host.py'),
                '--output',str(session/'host_monitor.json')],stdout=log,stderr=subprocess.STDOUT,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            gc.run.old.prepare_environment(session)
            c.save(session/'environment_seal.json',dict(files_sha256={n:c.digest(session/n)
                for n in ('environment.json','initial-settling.json')}))
            for spec in matrix():
                if monitor.poll() is not None: raise ValueError('host sampler exited early')
                verify(session)
                collect(session,session/'trials'/spec['trial'],spec,helper)
            helper.request('finish'); helper.close(); helper=None
            analyze(session)
        except BaseException as e:
            c.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc(),
                closing_decision='close_unresolved_incomplete_final_attempt',automatic_followup_authorized=False)); raise
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM,prior); signal.signal(signal.SIGTERM,prior_term)
            try:
                if helper: helper.close()
            finally:
                if monitor:
                    gc.legacy.fixtures.stop(monitor,signal.SIGINT); log.close()
                    if monitor.returncode: c.save(session/'host_monitor_failure.json',dict(returncode=monitor.returncode))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('prepare','verify-preparation','verify-audit','run','analyze'))
    p.add_argument('--directory',type=Path,default=DEFAULT); p.add_argument('--audit',type=Path)
    a=p.parse_args(); session=owned(a.directory)
    if a.command=='prepare':
        with gc.run.acquire_experiment_lock():
            try: prepare(session)
            except BaseException as e:
                prep=session/'preparation'
                if prep.exists() and not (prep/'seal.json').exists():
                    c.save(prep/'preparation_failure.json',dict(error=str(e),traceback=traceback.format_exc()))
                    c.seal(prep)
                raise
    elif a.command=='verify-preparation': verify(session); print('Closing preparation verified.')
    elif a.command=='verify-audit': base.verify_audit(a.audit); print('Observer audit verified.')
    elif a.command=='run': run(session,a.audit)
    else: analyze(session)


if __name__=='__main__': main()
