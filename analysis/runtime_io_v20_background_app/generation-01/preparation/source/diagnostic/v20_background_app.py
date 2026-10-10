#!/usr/bin/env python3
"""Retained V20 workload with an explicit idle-app-present intervention."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

import execution_delay_common as c
import execution_delay_study as legacy
import execution_delay_analysis as analysis
from verify_execution_delay import verify_preparation as verify_base, verify_environment
import minimal_computation_screen as audit_gate
sys.path.insert(0,str(c.ROOT/'analysis'))
from review_period_cost_pilot import fixed_busy_rate

ROOT=c.ROOT
BASE=c.PARENT/'generation-04'
PARENT=ROOT/'analysis/runtime_io_v20_background_app'
DEFAULT=PARENT/'generation-01'
NEW=('diagnostic/v20_background_app.py','diagnostic/test_v20_background_app.py',
     'diagnostic/start_v20_background_app.sh','docs/runtime_io_v20_background_app.md',
     'analysis/review_period_cost_pilot.py','diagnostic/period_cost.py',
     'diagnostic/period_cost_perf.py','diagnostic/period_cost_fixture.c')
APP_NAMES={'ChatGPT','Codex','codex'}
LAUNCHER=Path('/usr/bin/chatgpt')
EXECUTABLE=LAUNCHER.resolve().parent/'ChatGPT'
FLAGS=Path.home()/'.config/chatgpt-flags.conf'
FACTORS={'A':(False,100),'B':(False,20),'C':(True,100),'D':(True,20)}
LIMITS=dict(initial_idle_sec=1200,initial_ceiling_sec=1800,settle_ceiling_sec=600,
            wall_ceiling_sec=10800,interaction_margin=.02)
ORIGINAL_POLICY=dict(legacy.run.old.POLICY)
RAW_REPLAY=analysis.replay


def matrix():
    return [dict(trial=f'b{b}_{a}',block=b,arm=a,order=offset*4+i+1,
                 app_open=FACTORS[a][0],period_ms=FACTORS[a][1])
            for offset,(b,order) in enumerate([(1,'ABCD'),(4,'DCBA')]) for i,a in enumerate(order)]


def original_config(spec,functional=False):
    arm='A' if spec['period_ms']==100 else 'C'
    return c.fixture(arm) if functional else next(r for r in c.matrix()
        if r['block']==spec['block'] and r['arm']==arm)


def policy(initial=False):
    p=dict(ORIGINAL_POLICY,initial_idle_sec=LIMITS['initial_idle_sec'])
    minimum=p['initial_idle_sec'] if initial else p['window_sec']
    p['timeout_sec']=(LIMITS['initial_ceiling_sec'] if initial else LIMITS['settle_ceiling_sec'])-minimum
    return p


def owned(value):
    p=Path(value).absolute()
    if p.parent!=PARENT or p.is_symlink() or p.resolve()!=p:
        raise ValueError('use a direct dedicated background-app generation')
    return p


def app_hashes():
    return dict(launcher=c.digest(LAUNCHER),executable=c.digest(EXECUTABLE),
                flags=None if not FLAGS.exists() else c.digest(FLAGS))


def source_hashes():
    return dict(audit_gate.source_hashes(),**{n:c.digest(ROOT/n) for n in NEW})


def app_processes():
    out=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if p.stat().st_uid!=os.getuid() or (p/'comm').read_text().strip() not in APP_NAMES: continue
            identity=c.process_identity(int(p.name))
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]=='Z': continue
            out.append(dict(identity,pgrp=int(fields[2])))
        except (OSError,ValueError,IndexError): continue
    return out


def require_app_state(expected):
    processes=app_processes()
    if bool(processes)!=expected:
        raise ValueError('intended app-open/app-closed condition not present')
    return processes


def group_members(group):
    members=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            if fields[0]!='Z' and p.stat().st_uid==os.getuid() and int(fields[2])==group:
                members.append(c.process_identity(int(p.name)))
        except (OSError,ValueError,IndexError): continue
    return members


class App:
    def __init__(self,affinity): self.process=None; self.affinity=set(affinity)

    def check(self,expected):
        rows=require_app_state(expected)
        if expected and (self.process is None or any(r['pgrp']!=self.process.pid for r in rows)):
            raise ValueError('unowned app process; do not close unrelated applications')
        return rows

    def switch(self,expected):
        if expected:
            if self.process is not None: return self.check(True)
            require_app_state(False)
            self.process=subprocess.Popen([str(LAUNCHER)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                start_new_session=True,preexec_fn=lambda:os.sched_setaffinity(0,self.affinity))
            until=time.monotonic()+30
            while not app_processes():
                if self.process.poll() is not None: raise ValueError('app launch failed')
                if time.monotonic()>until: raise TimeoutError('app startup did not establish named processes')
                time.sleep(.5)
            return self.check(True)
        self.close(); return self.check(False)

    def close(self):
        if self.process is None: return
        group=self.process.pid
        try: os.killpg(self.process.pid,signal.SIGTERM)
        except ProcessLookupError: pass
        until=time.monotonic()+20
        while group_members(group) and time.monotonic()<until:
            self.process.poll()  # Reap the main app while waiting for helper exit.
            time.sleep(.5)
        if group_members(group): raise ValueError('owned idle app/helper group did not quit; cleanup needs review')
        self.process.wait(timeout=5); self.process=None


def monitor_condition(rows,expected):
    if len(rows)<80: raise ValueError('original monitor coverage incomplete')
    elapsed=sum(r['process_interval_sec'] for r in rows)
    if elapsed<=0: raise ValueError('invalid host intervals')
    app_cpu=desktop_cpu=0
    for r in rows:
        if 'process_cpu_deltas' not in r: raise ValueError('complete process snapshots required')
        names={v['comm'] for v in r['process_cpu_deltas']}
        actual=bool(names & APP_NAMES)
        if actual!=expected or bool(r['chatgpt_present'])!=('ChatGPT' in names):
            raise ValueError('recorded app condition does not match intended intervention')
        app_cpu+=sum(v['cpu_delta_sec'] for v in r['process_cpu_deltas'] if v['comm'] in APP_NAMES)
        desktop_cpu+=sum(v['cpu_delta_sec'] for v in r['process_cpu_deltas']
                         if v['comm'] in ('plasmashell','kwin_wayland'))
    return dict(samples=len(rows),coverage_sec=elapsed,app_open=expected,
                named_app_cpu_pct_one_core=100*app_cpu/elapsed,
                plasma_kwin_cpu_pct_one_core=100*desktop_cpu/elapsed,
                limitation='Named app-process CPU can omit differently named helpers. Idle is a user instruction, not an observed agent-state guarantee.')


def replay(directory,functional=False):
    if functional: return RAW_REPLAY(directory,True)
    spec=c.read(directory/'background_config.json')
    if spec not in matrix() or c.read(directory/'config.json')!=original_config(spec):
        raise ValueError('outside frozen background matrix')
    rows=c.read(directory/'monitor.json'); state=monitor_condition(rows,spec['app_open'])
    actual_read=c.read
    def read(path):
        value=actual_read(path)
        if spec['app_open'] and Path(path)==directory/'monitor.json':
            # Raw flags stay intact on disk and are independently validated above.
            # Only the original replay's quiet-app assumption is replaced by the
            # declared app-present intervention. All power/coverage/work checks remain.
            return [dict(r,chatgpt_present=False) for r in value]
        return value
    with patch.object(c,'read',read): result=RAW_REPLAY(directory)
    result['background_state']=state
    return result


def verify(session,current=True):
    prep=session/'preparation'; c.verify_seal(prep); m=c.read(prep/'manifest.json')
    b=verify_base(BASE,current=current)
    if (m['background_matrix']!=matrix() or m['background_limits']!=LIMITS or
            not m['background_tests_passed'] or not m['background_functional_passed'] or
            m['base_preparation_seal']!=c.digest(BASE/'preparation/seal.json')):
        raise ValueError('background preparation incomplete/changed')
    for k in ('image','server_sha256','gate_sha256','loadgen_sha256','resource_baseline'):
        if m[k]!=b[k]: raise ValueError('original V20 input changed')
    for n,k in [('gate','gate_sha256'),('original.server','server_sha256'),('loadgen','loadgen_sha256')]:
        if c.digest(prep/n)!=m[k]: raise ValueError('retained executable changed')
    for n,sha in m['sources'].items():
        if c.digest(prep/'source'/n)!=sha or (current and c.digest(ROOT/n)!=sha):
            raise ValueError('source changed: '+n)
    if current and (source_hashes()!=m['sources'] or c.baseline()!=m['baseline'] or app_hashes()!=m['app_hashes']):
        raise ValueError('source, boot, app build or flags changed')
    for period in (100,20):
        p=prep/'functional'/str(period)
        if RAW_REPLAY(p,True)!=c.read(p/'derived.json'): raise ValueError('functional replay differs')
    return m


def environment(session,expected):
    folder=session/'conditions'/('open' if expected else 'closed')
    if not (folder/'environment.json').exists():
        folder.mkdir(parents=True)
        with patch.dict(legacy.run.old.POLICY,policy(initial=True)):
            legacy.run.old.prepare_environment(folder)
        c.save(folder/'environment_seal.json',dict(files_sha256={n:c.digest(folder/n)
            for n in ('environment.json','initial-settling.json')})); c.seal(folder)
    c.verify_seal(folder)
    with patch.dict(legacy.run.old.POLICY,policy(initial=True)): verify_environment(folder)
    return c.read(folder/'environment.json')


def collect(session,directory,spec,env):
    directory.mkdir(parents=True); c.save(directory/'background_config.json',spec)
    actual_read=c.read
    def read(path):
        return env if Path(path)==session/'environment.json' else actual_read(path)
    def update(_session,_config,stage):
        print(f"{spec['order']}/8 {spec['trial']} app={'open' if spec['app_open'] else 'closed'} {spec['period_ms']} ms: {stage}",flush=True)
        c.save(session/'progress.json',dict(spec,stage=stage,updated=time.time()))
    with patch.object(c,'read',read),patch.object(analysis,'replay',replay),\
            patch.object(legacy.run,'require_quiet_host',lambda:require_app_state(spec['app_open'])),\
            patch.object(legacy,'update',update),patch.dict(legacy.run.old.POLICY,policy()):
        legacy.collect(session,directory,original_config(spec),'start')
    result=replay(directory)
    if result!=c.read(directory/'derived.json'): raise ValueError('saved background replay differs')


def compare(rows):
    if len(rows)!=8 or {r['trial'] for r in rows}!={r['trial'] for r in matrix()}:
        raise ValueError('all eight unique background cells required')
    by={r['trial']:r for r in rows}; blocks=[]
    for b in (1,4):
        a,z,x,y=(by[f'b{b}_{arm}'] for arm in 'ABCD')
        fields=('cpu_usec_per_completed_work','capacity','timely_500_fraction')
        if any(not math.isfinite(r[f]) or r[f]<0 for r in (a,z,x,y) for f in fields):
            raise ValueError('invalid comparison inputs')
        if any(r['cpu_usec_per_completed_work']<=0 for r in (a,z,x,y)):
            raise ValueError('positive CPU/job required')
        closed=z['cpu_usec_per_completed_work']/a['cpu_usec_per_completed_work']
        opened=y['cpu_usec_per_completed_work']/x['cpu_usec_per_completed_work']
        blocks.append(dict(block=b,closed_period_cpu_change=closed-1,open_period_cpu_change=opened-1,
            relative_interaction=opened/closed-1,
            closed_deadline_change=z['timely_500_fraction']-a['timely_500_fraction'],
            open_deadline_change=y['timely_500_fraction']-x['timely_500_fraction']))
    v=[r['relative_interaction'] for r in blocks]; margin=LIMITS['interaction_margin']
    substantial=all(x>=margin for x in v) or all(x<=-margin for x in v)
    return dict(decision='app_presence_changes_period_contrast_in_this_screen' if substantial else
        'app_presence_did_not_show_a_consistent_large_period_interaction',blocks=blocks,
        historical_cause_established=False,novelty_established=False,automatic_followup_authorized=False,
        limitation='Two opposite-order blocks are exploratory, not equivalence or proof of the historical cause. '
        'Opening the app changes a bundle of CPU, GPU, desktop and thermal conditions. '
        'Condition-specific thermal references allow that bundle to change temperature; this is not a pure CPU-contention test. '
        'The original benchmark workload/collector is retained, but the quiet-app check is deliberately replaced by verified app presence. '
        'No physical CPU-frequency control or instruction/cycle measurement is added.')


def analyze(session):
    verify(session,current=False); rows=[]
    for spec in matrix():
        p=session/'trials'/spec['trial']; result=replay(p)
        if result!=c.read(p/'derived.json') or not c.read(p/'complete.json')['valid']:
            raise ValueError('incomplete/different raw replay')
        env=c.read(p/'environment.json'); cond=session/'conditions'/('open' if spec['app_open'] else 'closed')
        c.verify_seal(cond)
        with patch.dict(legacy.run.old.POLICY,policy(initial=True)): verify_environment(cond)
        if env!=c.read(cond/'environment.json'): raise ValueError('wrong condition thermal reference')
        r=result['summary']; rows.append(dict(spec,cpu_usec_per_completed_work=r['cpu_usec_per_completed_work'],
            capacity=fixed_busy_rate(p),timely_500_fraction=r['timely_500_fraction'],
            failure_fraction=r['failure_fraction'],background_state=result['background_state']))
    report=compare(rows); report.update(rows=rows,preparation_seal=c.digest(session/'preparation/seal.json'))
    out=session/'analysis'/str(time.time_ns()); out.mkdir(parents=True);c.save(out/'report.json',report)
    lines=['# Retained V20 idle-app comparison','',report['decision'],'',report['limitation'],'',
           '| Block | Closed: period CPU/job change | Open: period CPU/job change | Relative interaction |',
           '|---|---:|---:|---:|']
    for b in report['blocks']:
        lines.append(f"| {b['block']} | {100*b['closed_period_cpu_change']:+.2f}% | {100*b['open_period_cpu_change']:+.2f}% | {100*b['relative_interaction']:+.2f}% |")
    (out/'report.md').write_text('\n'.join(lines)+'\n');c.seal(out)
    print(report['decision']+'; report: '+str(out/'report.md'),flush=True)


def prepare(session):
    if os.geteuid()==0 or session.exists(): raise ValueError('new generation, normal user only')
    b=verify_base(BASE); sources=source_hashes();prep=session/'preparation';prep.mkdir(parents=True)
    for n in sources:
        p=prep/'source'/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/n,p)
    for n in ('gate','loadgen','original.server'): shutil.copy2(BASE/'preparation'/n,prep/n)
    m=dict(b,sources=sources,background_matrix=matrix(),background_limits=LIMITS,
           base_preparation_seal=c.digest(BASE/'preparation/seal.json'),app_hashes=app_hashes(),
           app_affinity=sorted(os.sched_getaffinity(0)),background_tests_passed=False,
           background_functional_passed=False,prepared=time.time())
    c.save(prep/'manifest.json',m)
    r=subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic','-p','test_v20_background_app.py','-v'],
        cwd=ROOT,capture_output=True,text=True,timeout=60)
    (prep/'tests.stdout').write_text(r.stdout);(prep/'tests.stderr').write_text(r.stderr)
    if r.returncode: raise ValueError('background decision tests failed')
    m['background_tests_passed']=True;c.save(prep/'manifest.json',m)
    for period in (100,20):
        spec=dict(period_ms=period)
        legacy.collect(session,prep/'functional'/str(period),original_config(spec,True),'functional',functional=True)
    m['background_functional_passed']=True;c.save(prep/'manifest.json',m)
    if sources!=source_hashes(): raise ValueError('sources changed during preparation')
    c.seal(prep);verify(session)
    print('Background-app preparation verified; no app was launched and performance remains unrun.',flush=True)


def run(session,audit):
    if os.geteuid()==0 or os.environ.get('QUOTA_BACKGROUND_EXTERNAL')!='1':
        raise ValueError('external normal-user launcher required')
    m=verify(session);require_app_state(False);audit_gate.verify_audit(audit)
    if sorted(os.sched_getaffinity(0))!=m['app_affinity']: raise ValueError('original app CPU affinity changed')
    app=App(m['app_affinity']);os.sched_setaffinity(0,{0,1})
    with legacy.run.acquire_experiment_lock():
        if (session/'owner.json').exists() or (session/'trials').exists(): raise ValueError('one fresh attempt only')
        c.save(session/'owner.json',c.process_identity(os.getpid()));shutil.copy2(audit,session/'audit.json')
        review=Path(audit).with_suffix('.review.json')
        if review.exists(): shutil.copy2(review,session/'audit_ownership_review.json')
        prior={sig:signal.getsignal(sig) for sig in (signal.SIGALRM,signal.SIGTERM,signal.SIGINT)}
        def stop(_sig,_frame): raise InterruptedError('background test interrupted or three-hour ceiling reached')
        for sig in prior: signal.signal(sig,stop)
        signal.alarm(LIMITS['wall_ceiling_sec'])
        try:
            for spec in matrix():
                verify(session);processes=app.switch(spec['app_open'])
                env=environment(session,spec['app_open']);app.check(spec['app_open'])
                other=session/'conditions'/('closed' if spec['app_open'] else 'open')/'environment.json'
                if other.exists() and c.read(other)['power_settings']!=env['power_settings']:
                    raise ValueError('power settings differ between background conditions')
                p=session/'trials'/spec['trial'];collect(session,p,spec,env)
                app.check(spec['app_open']);c.save(p/'app_transition.json',dict(processes=processes,
                    app_affinity=m['app_affinity'],instructed_idle=True));c.seal(p)
            app.close();analyze(session)
        except BaseException as e:
            c.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc()));raise
        finally:
            signal.alarm(0)
            for sig,value in prior.items(): signal.signal(sig,value)
            app.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','verify-preparation','verify-audit','run','analyze'))
    p.add_argument('--directory',type=Path,default=DEFAULT);p.add_argument('--audit',type=Path)
    a=p.parse_args();session=owned(a.directory)
    if a.command=='prepare':
        try:
            with legacy.run.acquire_experiment_lock(): prepare(session)
        except BaseException as e:
            prep=session/'preparation'
            if prep.exists() and not (prep/'seal.json').exists():
                c.save(prep/'preparation_failure.json',dict(error=str(e),traceback=traceback.format_exc()));c.seal(prep)
            raise
    elif a.command=='verify-preparation': verify(session);print('Background-app preparation verified.')
    elif a.command=='verify-audit':audit_gate.verify_audit(a.audit);print('Observer audit verified.')
    elif a.command=='run':run(session,a.audit)
    else:analyze(session)


if __name__=='__main__':main()
