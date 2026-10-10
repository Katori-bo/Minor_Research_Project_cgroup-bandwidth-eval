#!/usr/bin/env python3
"""Read-only raw replay of an incomplete execution-state pilot; writes a sidecar."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import execution_state_pilot as s


def available_period_contrast(by,block,condition,counters):
    a=next((r for r in by.values() if r['block']==block and r['condition']==condition and
            r['counters']==counters and r['period_ms']==100),None)
    z=next((r for r in by.values() if r['block']==block and r['condition']==condition and
            r['counters']==counters and r['period_ms']==20),None)
    if a is None or z is None:return None
    fields=['cpu_usec_per_completed_work','capacity','cpu_cores']
    if counters:fields+=['instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec']
    return dict(block=block,condition=condition,counters=counters,
                changes={f:z[f]/a[f]-1 for f in fields})


def review(session):
    m=s.verify(session,current=False)
    for name,sha in m['sources'].items():
        if name.endswith('.py') and s.c.digest(ROOT/name)!=sha:
            raise ValueError('loaded replay source differs: '+name)
    rows=[]; states=[]; receipts={}
    for spec in s.matrix():
        d=session/'trials'/spec['trial']
        if (d/'complete.json').exists():
            if s.c.read(d/'complete.json')!={'valid':True,'performance_run':True}:
                raise ValueError('wrong trial completion kind')
            result=s.replay(d,session)
            if result!=s.c.read(d/'pilot_derived.json'):raise ValueError('raw replay differs')
            rows.append(result['summary']); states.append(dict(spec,status='raw_replay_verified'))
            receipts[spec['trial']]=s.c.digest(d/'seal.json')
        elif d.exists():
            s.c.verify_seal(d); states.append(dict(spec,status='failed_before_measurement' if not (d/'native_records.json').exists() else 'failed_with_raw_work'))
            receipts[spec['trial']]=s.c.digest(d/'seal.json')
        else:states.append(dict(spec,status='unrun'))
    if {r['trial'] for r in rows}!={r['trial'] for r in s.matrix()[:12]}:
        raise ValueError('this reviewer is for the retained twelve-cell prefix')
    first=s.compare(rows[:8],False)
    if first!=s.c.read(session/'feasibility.json'):raise ValueError('first-block gate differs')
    by={r['trial']:r for r in rows}
    contrasts=[r for b in (1,2) for condition in ('automatic','constrained') for counted in (False,True)
               if (r:=available_period_contrast(by,b,condition,counted)) is not None]
    observer=list(first['observer_checks'])
    for off,on in [('G','H'),('E','F')]:
        a,z=[by['b2_'+k] for k in (off,on)]
        changes={f:z[f]/a[f]-1 for f in ('cpu_usec_per_completed_work','capacity','cpu_cores')}
        observer.append(dict(block=2,condition='constrained',period_ms=a['period_ms'],changes=changes,
            passed=all(abs(v)<=.01 for v in changes.values())))
    s.c.verify_seal(session/'speed_control')
    restoration=s.c.read(session/'speed_control/restoration.json')
    if not restoration['restored'] or restoration['observed']!=m['controls_before']:
        raise ValueError('restoration failed')
    if s.c.read(session/'speed_control/original.json')!=m['controls_before']:
        raise ValueError('original control snapshot differs')
    selftest=s.c.read(session/'speed_control/selftest.json')
    if selftest['constrained_readback']!=m['control_plan']['constrained'] or not selftest['restoration']['restored']:
        raise ValueError('control selftest differs')
    for i,spec in enumerate(s.matrix()[:13]):
        receipt=s.c.read(session/'speed_control'/f'condition_{i}.json')
        if receipt['condition']!=spec['condition'] or receipt['trial']!=spec['trial'] or receipt['observed']!=m['control_plan'][spec['condition']]:
            raise ValueError('condition application differs')
    fixtures=session/'counter_fixtures'; s.c.verify_seal(fixtures)
    if s.pc.validate_fixtures(fixtures)!=s.c.read(fixtures/'result.json'):raise ValueError('hardware fixtures differ')
    failure_dir=session/'trials/b2_D'; settling=s.c.read(failure_dir/'settling.json')
    env=s.c.read(failure_dir/'environment.json'); samples=settling['samples']; end=samples[-1]['elapsed_sec']; i=0
    while i+1<len(samples) and samples[i+1]['elapsed_sec']<=end-settling['policy']['window_sec']:i+=1
    window=s.gc.run.old.window_summary(samples[i:],env['baseline_c'])
    failure_cleanup=s.c.read(failure_dir/'cleanup.json')
    if failure_cleanup['container_id'] is not None or failure_cleanup['cgroup'] is not None:
        raise ValueError('failed cell unexpectedly created workload resources')
    user_split=[]
    for spec in s.matrix()[:12]:
        if not spec['counters']:continue
        counter=s.c.read(session/'trials'/spec['trial']/'pilot_derived.json')['counter']; bounds=counter['bounds']
        user_split.append(dict(trial=spec['trial'],system_cpu_fraction=bounds['system_usec']['midpoint']/bounds['usage_usec']['midpoint'],
                              user_cpu_usec=bounds['user_usec']['midpoint'],system_cpu_usec=bounds['system_usec']['midpoint']))
    out=session/'partial_analysis'/str(time.time_ns());out.mkdir(parents=True)
    report=dict(decision='incomplete_pilot_feasibility_demonstrated_no_large_interaction_in_complete_block',
        completed_trials=len(rows),states=states,rows=rows,first_block=first,available_period_contrasts=contrasts,
        available_observer_checks=observer,restoration=restoration,
        controls_match_original_now=s.controls.snapshot()==m['controls_before'],
        failed_settling=dict(baseline=env['baseline_c'],final_window=window,elapsed_sec=end,policy=settling['policy']),
        counter_user_system_split=user_split,host_monitor_failure=s.c.read(session/'host_monitor_failure.json'),
        host_monitor_sha256=s.c.digest(session/'host_monitor.json'),
        evidence_sha256=dict(preparation_seal=s.c.digest(session/'preparation/seal.json'),trial_seals=receipts,
            speed_control_seal=s.c.digest(session/'speed_control/seal.json'),fixtures_seal=s.c.digest(fixtures/'seal.json'),
            interruption=s.c.digest(session/'interruption.json'),feasibility=s.c.digest(session/'feasibility.json')),
        reviewer_sha256=s.c.digest(Path(__file__)),historical_cause_established=False,novelty_established=False,
        full_predeclared_comparison_complete=False,automatic_followup_authorized=False,
        limitation='One complete interaction block; reverse block has only constrained cells. '
        'The historical large penalty was not reproduced. No equivalence, exclusion of all execution-state mechanisms, '
        'or historical causal attribution. Whole-session host JSON was truncated after monitor SIGKILL; trial-local '
        'sealed control/power coverage remains verified. Cycles/user CPU second is not direct clock measurement; '
        'one counted reverse cell has a materially changed user/system CPU split.')
    s.c.save(out/'report.json',report)
    lines=['# Partial execution-state pilot review','',report['decision'],'',
           'Twelve completed measurements pass independent raw replay. The thirteenth failed before workload startup; three were unrun.',
           '',report['limitation'],'',
           '| Block | Condition | Counters | CPU/job, 20 vs 100 ms | Capacity | Instructions/job | CPI | Effective user cycle rate |',
           '|---|---|---|---:|---:|---:|---:|---:|']
    for r in contrasts:
        v=r['changes']; fs=['cpu_usec_per_completed_work','capacity','instructions_per_job','cycles_per_instruction','cycles_per_user_cpu_sec']
        lines.append('| '+str(r['block'])+' | '+r['condition']+' | '+str(r['counters'])+' | '+' | '.join(
            f'{100*v[f]:+.4f}%' if f in v else 'unmeasured' for f in fs)+' |')
    lines+=['','The first-block speed intervention reduced the effective user cycle-rate proxy by 23.63% at 100 ms and 24.14% at 20 ms. '
            'All four first-block observer checks and the two available reverse-block checks passed the 1% practical margins.',
            '', 'First-block CPU/job interaction: -0.8161% counters off, +0.1576% counters on. Neither meets the predeclared 2% practical signal.',
            '', 'The final thermal window was steady: mean 56.933 C, range 0.125 C, slope -0.0987 C/min. '
            'It was 5.788 C below the automatic-mode baseline 62.721 C, outside the +/-3 C band. '
            'Increasing the timeout alone does not guarantee returning to that band.',
            '', 'Original controls were restored. The failed cell created no container or cgroup.',
            '', 'Caution: b2_F recorded 5.463% system CPU, versus approximately 0.23–0.46% in other counted cells. '
            'Its +7.188% cycles/user CPU-second period contrast is sensitive to this changed denominator; '
            'it must not be labeled a direct frequency increase under fixed clocks. Instructions and CPI remain nearly unchanged.',
            '', 'The whole-session sampler exited -9 and its JSON ends inside a record. '
            'The parsed prefix has 4,931 complete records ending just after the final settling began, '
            'so it cannot establish background activity during the subsequent temperature drop.',
            '', 'Recommendation: retain this as an informative incomplete pilot. Measurement feasibility is supported '
            'in the completed block, but the tested speed intervention did not reproduce the old period penalty. '
            'No automatic rerun or filling missing cells across sessions. A formal two-block interaction claim '
            'would require a new complete controlled comparison after addressing baseline drift; this is not '
            'necessary just to decide that the current pilot provides no promising large interaction signal.']
    (out/'report.md').write_text('\n'.join(lines)+'\n'); s.c.seal(out)
    print(out/'report.md')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=s.DEFAULT)
    a=p.parse_args();review(s.owned(a.directory))
