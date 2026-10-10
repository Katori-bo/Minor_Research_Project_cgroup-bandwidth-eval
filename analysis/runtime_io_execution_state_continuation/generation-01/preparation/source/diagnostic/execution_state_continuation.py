#!/usr/bin/env python3
"""Four automatic-speed missing cells under a fresh, separately identified baseline."""
import argparse
from contextlib import contextmanager
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

import execution_state_pilot as pilot

c,gc,ROOT=pilot.c,pilot.gc,pilot.ROOT
SOURCE=pilot.PARENT/'generation-02'
PARENT=ROOT/'analysis/runtime_io_execution_state_continuation'
DEFAULT=PARENT/'generation-01'
ORIGINAL_MATRIX=tuple(pilot.matrix())
LIMITS=dict(pilot.LIMITS,wall_ceiling_sec=4500)
NEW=('diagnostic/execution_state_continuation.py','diagnostic/execution_state_continuation_helper.py',
     'diagnostic/execution_state_stream_monitor.py','diagnostic/test_execution_state_continuation.py',
     'diagnostic/start_execution_state_continuation.sh','docs/runtime_io_execution_state_continuation.md')


def matrix():return [dict(r) for r in ORIGINAL_MATRIX[12:]]


def owned(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:raise ValueError('use a new direct continuation generation')
    return p


@contextmanager
def collector_context():
    # Adapt only accepted matrix and bounded runtime. Original source and raw
    # records are never modified, and patches are restored on every exit.
    with patch.object(pilot,'matrix',matrix),patch.dict(pilot.LIMITS,LIMITS):yield


def sources():return dict(pilot.sources(),**{n:c.digest(ROOT/n) for n in NEW})


def parent_receipts():
    names=['preparation/seal.json','speed_control/seal.json','counter_fixtures/seal.json',
           'feasibility.json','interruption.json','host_monitor_failure.json',
           'conditions/automatic/environment_seal.json','conditions/constrained/environment_seal.json']
    names += ['trials/'+r['trial']+'/seal.json' for r in ORIGINAL_MATRIX[:13]]
    return {n:c.digest(SOURCE/n) for n in names}


def parent_rows():
    pilot.verify(SOURCE,current=False)
    return pilot.replay_rows(SOURCE,ORIGINAL_MATRIX[:12])


def replay(directory,session,functional=False):
    with collector_context():return pilot.replay(directory,session,functional)


def verified_environment(session):
    with collector_context():
        with patch.dict(gc.run.old.POLICY,pilot.thermal_policy(True)):
            return gc.verify_environment(session/'conditions/automatic')


def verify(session,current=True):
    prep=session/'preparation';c.verify_seal(prep);m=c.read(prep/'manifest.json')
    b=pilot.verify(SOURCE,current=current)
    if (m['matrix']!=matrix() or m['continuation_limits']!=LIMITS or
        m['parent_receipts']!=parent_receipts() or not m['tests_passed'] or
        not m['functional_passed'] or m['performance_run']):raise ValueError('continuation preparation changed or incomplete')
    for key in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline','minimal_image','minimal_server_sha256','fixture_sha256'):
        if m[key]!=b[key]:raise ValueError('retained computation contract differs: '+key)
    if m['controls_before']!=b['controls_before'] or m['control_plan']!=b['control_plan']:
        raise ValueError('automatic settings differ from source experiment')
    for name,key in [('gate','gate_sha256'),('minimal.server','minimal_server_sha256'),('fixture','fixture_sha256')]:
        if c.digest(prep/name)!=m[key]:raise ValueError('prepared executable changed')
    for name,sha in m['sources'].items():
        if c.digest(prep/'source'/name)!=sha or (current and c.digest(ROOT/name)!=sha):raise ValueError('source changed: '+name)
    if current and (m['sources']!=sources() or m['baseline']!=c.baseline() or m['perf_sha256']!=c.digest(Path('/usr/bin/perf'))):
        raise ValueError('boot, tool or source changed')
    for period in (100,20):
        d=prep/'functional'/str(period)
        if replay(d,session,True)!=c.read(d/'pilot_derived.json'):raise ValueError('functional replay differs')
    return m


class Helper(pilot.pc.Helper):
    def __init__(self,session):
        self.log=(session/'helper.stderr').open('x')
        self.process=subprocess.Popen(['sudo','-n','/usr/bin/python3',str(ROOT/'diagnostic/execution_state_continuation_helper.py'),
            '--directory',str(session)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log)
        try:
            if json.loads(pilot.hw.line(self.process.stdout,15,self.process))!={'ready':True}:raise ValueError('helper startup failed')
        except BaseException:self.close();raise


def compare(rows,old_rows):
    if len(rows)!=4 or {r['trial'] for r in rows}!={r['trial'] for r in matrix()}:raise ValueError('four unique continuation cells required')
    if len(old_rows)!=12 or {r['trial'] for r in old_rows}!={r['trial'] for r in ORIGINAL_MATRIX[:12]}:raise ValueError('twelve source cells required')
    for r in rows:
        fs=['cpu_usec_per_completed_work','capacity','cpu_cores']+(['instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec'] if r['counters'] else [])
        if any(not math.isfinite(r[f]) or r[f]<=0 for f in fs):raise ValueError('invalid measured values')
    by={r['arm']:r for r in rows};observer=[];contrasts=[]
    for off,on in [('A','B'),('C','D')]:
        a,z=by[off],by[on];changes={f:z[f]/a[f]-1 for f in ('cpu_usec_per_completed_work','capacity','cpu_cores')}
        observer.append(dict(period_ms=a['period_ms'],changes=changes,passed=all(abs(v)<=.01 for v in changes.values())))
    for counted,arms in [(False,('A','C')),(True,('B','D'))]:
        a,z=[by[k] for k in arms]
        fs=['cpu_usec_per_completed_work','capacity','cpu_cores']+(['instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec'] if counted else [])
        contrasts.append(dict(counters=counted,changes={f:z[f]/a[f]-1 for f in fs}))
    qualified=all(r['passed'] for r in observer)
    cpu=[r['changes']['cpu_usec_per_completed_work'] for r in contrasts]
    if not qualified:decision='continuation_observer_not_qualified'
    elif all(v>=.02 for v in cpu):decision='shorter_period_penalty_observed_in_new_baseline_continuation'
    elif all(v<=-.02 for v in cpu):decision='shorter_period_improvement_observed_in_new_baseline_continuation'
    else:decision='continuation_no_consistent_large_period_signal'
    # Original compare is only a descriptive calculation across changed sessions.
    combined=pilot.compare(list(old_rows)+list(rows),True)
    return dict(decision=decision,observer_qualified=qualified,observer_checks=observer,
        automatic_period_contrasts=contrasts,descriptive_combined=combined,
        all_planned_cell_labels_available=True,original_uninterrupted_protocol_complete=False,
        cross_session_interaction_causal=False,historical_cause_established=False,novelty_established=False,
        automatic_followup_authorized=False,
        limitation='Four automatic-speed trials share a fresh baseline and constitute a separate continuation. '
        'Their within-session period contrast is interpretable subject to qualification; combinations with the '
        'older constrained cells are descriptive and confounded by session/baseline and host-logging changes. '
        'No historical causal proof, statistical equivalence, or replicated controlled speed-interaction claim.')


def analyze(session):
    m=verify(session,current=False)
    if (session/'interruption.json').exists() or (session/'host_monitor_failure.json').exists():raise ValueError('interrupted or unfinalized continuation')
    rows=[]
    for spec in matrix():
        d=session/'trials'/spec['trial']
        if c.read(d/'complete.json')!={'valid':True,'performance_run':True}:raise ValueError('incomplete continuation trial')
        result=replay(d,session)
        if result!=c.read(d/'pilot_derived.json'):raise ValueError('continuation raw replay differs')
        rows.append(result['summary'])
    controls=session/'speed_control';c.verify_seal(controls)
    final=c.read(controls/'restoration.json')
    if not final['restored'] or final['observed']!=m['controls_before'] or final['changes_applied']:
        raise ValueError('automatic controls changed')
    for i,spec in enumerate(matrix()):
        receipt=c.read(controls/f'condition_{i}.json')
        if receipt['trial']!=spec['trial'] or receipt['observed']!=m['controls_before']:raise ValueError('control receipt differs')
    fixtures=session/'counter_fixtures';c.verify_seal(fixtures)
    if pilot.pc.validate_fixtures(fixtures)!=c.read(fixtures/'result.json'):raise ValueError('counter fixtures differ')
    # JSONL-like incremental array writing still produces standard JSON on clean exit.
    host=json.loads((session/'host_monitor.json').read_text())
    if not host:raise ValueError('missing finalized host samples')
    old=parent_rows();report=compare(rows,old)
    env=verified_environment(session)
    if any(r['chatgpt_present'] or any(p['comm'] in ('ChatGPT','Codex','codex') for p in r['process_cpu_deltas'])
           for r in host):raise ValueError('research app present during continuation host sampling')
    if any(r['power_settings']!=gc.run.old.comparable_power(env['power_settings']) for r in host):
        raise ValueError('power settings changed during continuation host sampling')
    prior=c.read(SOURCE/'conditions/automatic/environment.json')
    report.update(rows=rows,parent_rows=old,new_baseline=env['baseline_c'],prior_baseline=prior['baseline_c'],
        host_samples=len(host),host_monitor_sha256=c.digest(session/'host_monitor.json'),
        continuation_preparation_seal=c.digest(session/'preparation/seal.json'),parent_receipts=parent_receipts(),
        trial_seals={r['trial']:c.digest(session/'trials'/r['trial']/'seal.json') for r in matrix()},controls=final)
    split=[]
    for spec in matrix():
        if spec['counters']:
            b=c.read(session/'trials'/spec['trial']/'pilot_derived.json')['counter']['bounds']
            split.append(dict(trial=spec['trial'],system_fraction=b['system_usec']['midpoint']/b['usage_usec']['midpoint']))
    report['user_system_cpu_split']=split
    out=session/'analysis'/str(time.time_ns());out.mkdir(parents=True);c.save(out/'report.json',report)
    lines=['# Four-cell execution-state continuation','',report['decision'],'',report['limitation'],'',
        'Fresh baseline: '+json.dumps(env['baseline_c'])+'. Prior automatic baseline: '+json.dumps(prior['baseline_c'])+'.','',
        '| Counters | CPU/job, 20 vs 100 ms | Instructions/job | CPI | Effective cycle-rate |',
        '|---|---:|---:|---:|---:|']
    for r in report['automatic_period_contrasts']:
        v=r['changes'];fs=['cpu_usec_per_completed_work','instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec']
        lines.append('| '+str(r['counters'])+' | '+' | '.join(f'{100*v[f]:+.4f}%' if f in v else 'unmeasured' for f in fs)+' |')
    lines+=['','## Descriptive combined interactions across sessions','',
        'These do not constitute the original uninterrupted two-block result.']
    for r in report['descriptive_combined']['interactions']:
        lines.append(f"Block-label {r['block']}, counters {r['counters']}: {100*r['cpu_job_ratio_interaction']:+.4f}%")
    (out/'report.md').write_text('\n'.join(lines)+'\n');shutil.copy2(ROOT/'diagnostic/execution_state_continuation.py',out/'reviewer.py');c.seal(out)
    print(report['decision']+'; report: '+str(out/'report.md'),flush=True)


def prepare(session):
    if os.geteuid()==0 or session.exists():raise ValueError('prepare once as normal user in a new generation')
    b=pilot.verify(SOURCE);parent_rows();receipts=parent_receipts();shas=sources()
    prep=session/'preparation';prep.mkdir(parents=True)
    for name in shas:
        p=prep/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
    for name in ('gate','minimal.server','fixture'):shutil.copy2(SOURCE/'preparation'/name,prep/name)
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic','-p','test_execution_state_continuation.py','-v'],
        cwd=ROOT,capture_output=True,text=True,timeout=60)
    (prep/'tests.stdout').write_text(r.stdout);(prep/'tests.stderr').write_text(r.stderr)
    if r.returncode:raise ValueError('continuation tests failed')
    if pilot.controls.snapshot()!=b['controls_before']:raise ValueError('automatic CPU settings differ')
    m=dict(b,matrix=matrix(),sources=shas,baseline=c.baseline(),continuation_limits=LIMITS,parent_receipts=receipts,
        tests_passed=True,functional_passed=False,performance_run=False,prepared=time.time())
    c.save(prep/'manifest.json',m)
    for period in (100,20):
        spec=dict(trial=str(period),block=0,arm='A',order=0,kind='minimal',period_ms=period,counters=False,condition='automatic')
        with collector_context():pilot.collect(session,prep/'functional'/str(period),spec,functional=True)
    m['functional_passed']=True;c.save(prep/'manifest.json',m)
    if sources()!=shas or parent_receipts()!=receipts:raise ValueError('inputs changed during preparation')
    c.seal(prep);verify(session)
    print('Continuation prepared; four performance trials and fresh baseline unrun: '+str(session),flush=True)


def run(session,audit):
    if os.geteuid()==0 or os.environ.get('QUOTA_CONTINUATION_EXTERNAL')!='1':raise ValueError('use external normal-user launcher')
    os.sched_setaffinity(0,{0,1})
    with gc.run.acquire_experiment_lock():
        m=verify(session);gc.run.require_quiet_host();pilot.base.verify_audit(audit);parent_rows()
        if pilot.controls.snapshot()!=m['controls_before']:raise ValueError('automatic settings changed')
        if (session/'owner.json').exists() or (session/'trials').exists():raise ValueError('one attempt only')
        c.save(session/'owner.json',c.process_identity(os.getpid()));shutil.copy2(audit,session/'audit.json')
        review=Path(audit).with_suffix('.review.json')
        if review.exists():shutil.copy2(review,session/'audit_ownership_review.json')
        helper=monitor=log=None;prior=signal.getsignal(signal.SIGALRM);prior_term=signal.getsignal(signal.SIGTERM)
        def deadline(_s,_f):raise TimeoutError('75-minute continuation ceiling reached; retain partial evidence')
        def terminate(_s,_f):raise KeyboardInterrupt('continuation interrupted; clean owned resources')
        signal.signal(signal.SIGALRM,deadline);signal.alarm(LIMITS['wall_ceiling_sec']);signal.signal(signal.SIGTERM,terminate)
        try:
            helper=Helper(session);helper.request('fixtures',timeout=90)
            log=(session/'host_monitor.log').open('x')
            monitor=subprocess.Popen([sys.executable,str(ROOT/'diagnostic/execution_state_stream_monitor.py'),
                '--output',str(session/'host_monitor.json')],stdout=log,stderr=subprocess.STDOUT,
                preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            envdir=session/'conditions/automatic';envdir.mkdir(parents=True)
            with collector_context():
                with patch.dict(gc.run.old.POLICY,pilot.thermal_policy(True)):gc.run.old.prepare_environment(envdir)
            c.save(envdir/'environment_seal.json',dict(files_sha256={n:c.digest(envdir/n) for n in ('environment.json','initial-settling.json')}))
            for i,spec in enumerate(matrix(),1):
                if monitor.poll() is not None:raise ValueError('streaming host sampler exited early')
                verify(session);gc.run.require_quiet_host();helper.request('condition')
                print(f"Continuation {i}/4: {spec['trial']}, automatic {spec['period_ms']} ms, counters {spec['counters']}",flush=True)
                with collector_context():pilot.collect(session,session/'trials'/spec['trial'],spec,helper)
            helper.request('finish');helper.close();helper=None
        except BaseException as e:
            c.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc()));raise
        finally:
            signal.alarm(0);signal.signal(signal.SIGALRM,prior);signal.signal(signal.SIGTERM,prior_term)
            try:
                if helper:helper.close()
            finally:
                if monitor:
                    gc.legacy.fixtures.stop(monitor,signal.SIGINT);log.close()
                    if monitor.returncode:c.save(session/'host_monitor_failure.json',dict(returncode=monitor.returncode))
        analyze(session)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','verify-preparation','verify-audit','run','analyze'))
    p.add_argument('--directory',type=Path,default=DEFAULT);p.add_argument('--audit',type=Path)
    a=p.parse_args();session=owned(a.directory)
    if a.command=='prepare':
        with gc.run.acquire_experiment_lock():
            try:prepare(session)
            except BaseException as e:
                prep=session/'preparation'
                if prep.exists() and not (prep/'seal.json').exists():
                    c.save(prep/'preparation_failure.json',dict(error=str(e),traceback=traceback.format_exc()));c.seal(prep)
                raise
    elif a.command=='verify-preparation':verify(session);print('Continuation preparation verified.')
    elif a.command=='verify-audit':pilot.base.verify_audit(a.audit);print('Observer audit verified.')
    elif a.command=='run':run(session,a.audit)
    else:analyze(session)

if __name__=='__main__':main()
