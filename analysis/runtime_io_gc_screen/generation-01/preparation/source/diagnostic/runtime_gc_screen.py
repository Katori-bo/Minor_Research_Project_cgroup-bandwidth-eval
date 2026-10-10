#!/usr/bin/env python3
"""Eight-trial GC/period screen; preserve the sealed sixteen-trial probe."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

import runtime_gc_probe as gc

c, ROOT = gc.c, gc.ROOT
BASE = gc.DEFAULT
PARENT = ROOT/'analysis/runtime_io_gc_screen'
DEFAULT = PARENT/'generation-01'
BLOCKS = (1, 4)
NEW_FILES = ('diagnostic/runtime_gc_screen.py', 'diagnostic/test_runtime_gc_screen.py',
    'diagnostic/start_runtime_gc_screen.sh', 'docs/runtime_io_gc_screen.md')


def matrix():
    # Opposite orders ABCD / DCBA, not the first two blocks of the full probe.
    # Keep accepted legacy block labels for the unchanged raw replay machinery.
    return [spec for spec in gc.matrix() if spec['block'] in BLOCKS]


def owned_directory(value):
    path=Path(value).absolute()
    if path.parent != PARENT or path.is_symlink() or path.resolve() != path:
        raise ValueError('use a new direct GC-screen generation')
    return path


def source_hashes():
    retained=gc.source_hashes()
    return dict(retained, **{name:c.digest(ROOT/name) for name in NEW_FILES})


def verify_preparation(session, current=True):
    prep=session/'preparation'; c.verify_seal(prep)
    manifest=c.read(prep/'manifest.json')
    base=gc.verify_preparation(BASE,current=current)
    if (manifest['matrix'] != matrix() or manifest['performance_run'] or not manifest['tests_passed']
            or manifest['workload'] != c.WORKLOAD or manifest['base_gc_preparation_seal'] != c.digest(BASE/'preparation/seal.json')
            or manifest['screen_signal_margin'] != gc.INTERACTION_MARGIN):
        raise ValueError('screen protocol or qualification differs')
    for key in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline','baseline'):
        if manifest[key] != base[key]: raise ValueError('base executable/resources/boot differ')
    for name,key in [('gate','gate_sha256'),('loadgen','loadgen_sha256'),('original.server','server_sha256')]:
        if c.digest(prep/name) != manifest[key]: raise ValueError('screen executable differs')
    for name,sha in manifest['sources'].items():
        if c.digest(prep/'source'/name) != sha or (current and c.digest(ROOT/name) != sha):
            raise ValueError('screen source changed: '+name)
    if current and source_hashes() != manifest['sources']: raise ValueError('screen dependencies changed')
    if c.read(prep/'arrivals.json') != c.arrivals(): raise ValueError('arrival schedule differs')
    return manifest


def prepare(session):
    if os.geteuid()==0 or session.exists(): raise ValueError('prepare as normal user into a new directory')
    base=gc.verify_preparation(BASE)
    PARENT.mkdir(parents=True,exist_ok=True); c.capacity(PARENT)
    prep=session/'preparation'; prep.mkdir(parents=True)
    try:
        sources=source_hashes()
        for name in sources:
            target=prep/'source'/name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/name,target)
        for name in ('gate','loadgen','original.server'): shutil.copy2(BASE/'preparation'/name,prep/name)
        tested=subprocess.run([sys.executable,'-m','unittest','discover','-s','diagnostic',
            '-p','test_runtime_gc_screen.py','-v'],cwd=ROOT,capture_output=True,text=True,timeout=60)
        (prep/'tests.stdout').write_text(tested.stdout); (prep/'tests.stderr').write_text(tested.stderr)
        if tested.returncode: raise ValueError('screen regression tests failed')
        manifest=dict(matrix=matrix(),workload=c.WORKLOAD,sources=sources,prepared=time.time(),
            performance_run=False,tests_passed=True,screen_signal_margin=gc.INTERACTION_MARGIN,
            base_gc_preparation_seal=c.digest(BASE/'preparation/seal.json'),
            qualification='Reuse sealed actual-service GC functional controls; no new service workload in screen preparation.',
            **{k:base[k] for k in ('image','server_sha256','loadgen_sha256','gate_sha256','resource_baseline','baseline')})
        c.save(prep/'manifest.json',manifest); c.save(prep/'arrivals.json',c.arrivals())
        if source_hashes()!=sources: raise ValueError('source changed during preparation')
        c.seal(prep); verify_preparation(session)
        print('Eight-trial screen prepared and verified: '+str(session)+'; performance unrun.',flush=True)
    except BaseException as e:
        c.save(prep/'preparation_failure.json',dict(error=str(e),traceback=traceback.format_exc()))
        c.seal(prep); raise


def progress(session,spec,stage):
    order=next(i for i,v in enumerate(matrix(),1) if v==spec)
    c.save(session/'progress.json',dict(trial=spec['trial'],order=order,total=8,stage=stage,updated=time.time()))
    print(f"{order}/8 {spec['trial']}: {stage}",flush=True)


def interval(values,ratio=True):
    if len(values)!=2 or any(not math.isfinite(v) for v in values): raise ValueError('two finite block values required')
    mean=statistics.mean(values)
    half=12.706204736432095*statistics.stdev(values)/math.sqrt(2)
    transform=math.expm1 if ratio else lambda x:x
    # A two-block interval can be very wide. It is descriptive and not used to
    # claim equivalence or rule out the hypothesis.
    return dict(values=values,mean=transform(mean),lower=transform(mean-half),upper=transform(mean+half))


def compare(rows):
    if len(rows)!=8 or {r['trial'] for r in rows}!={s['trial'] for s in matrix()}:
        raise ValueError('all eight distinct screen trials required')
    table={r['trial']:r for r in rows}
    for row in rows:
        if any(not math.isfinite(row[k]) or row[k]<=0 for k in
                ('cpu_usec_per_completed_work','busy_capacity','busy_cpu_cores')):
            raise ValueError('positive finite cost/capacity/delivery required')
    contrasts={}
    for field in ('cpu_usec_per_completed_work','busy_capacity','busy_cpu_cores','timely_500_fraction'):
        contrasts[field]={}
        for label,a,b in [('period_default_gc','A','C'),('period_gc_off','B','D'),('gc_at_100','A','B'),('gc_at_20','C','D')]:
            ratio=field!='timely_500_fraction'
            values=[]
            for block in BLOCKS:
                x,y=(table[f'b{block}_{arm}'][field] for arm in (a,b))
                values.append(math.log(y/x) if ratio else y-x)
            contrasts[field][label]=interval(values,ratio)
    effects=[]
    for block in BLOCKS:
        a,b,cc,d=(table[f'b{block}_{arm}']['cpu_usec_per_completed_work'] for arm in 'ABCD')
        effects.append(math.log(d/b)-math.log(cc/a))
    changes=[math.expm1(v) for v in effects]
    consistent=all(v>=gc.INTERACTION_MARGIN for v in changes) or all(v<=-gc.INTERACTION_MARGIN for v in changes)
    return dict(decision='consistent_gc_period_signal_in_short_screen' if consistent else 'short_screen_inconclusive',
        cpu_interaction=interval(effects),block_interactions=changes,contrasts=contrasts,
        large_consistent_interaction_seen=consistent,
        original_default_cpu_penalty_seen_in_both_blocks=all(v>=math.log1p(.02) for v in
            contrasts['cpu_usec_per_completed_work']['period_default_gc']['values']),
        gc_hypothesis_ruled_out=False,historical_cause_established=False,language_bug_established=False,
        automatic_followup_authorized=False,
        limitation='Two opposite-order blocks are a prioritization screen. They cannot establish equivalence or exclude GC from the historical reversal. '
        'A signal requires at least 2% interaction in the same direction in both blocks; it is not confirmation. '
        'GC-off changes object lifetime and cache/page behavior as well as collector work.')


def replay(directory):
    result=gc.replay(directory)
    spec=c.read(directory/'runtime_config.json')
    if spec not in matrix(): raise ValueError('trial outside screen matrix')
    session=next(p for p in directory.parents if (p/'preparation/manifest.json').exists())
    metadata=c.read(directory/'screen_execution.json')
    order=next(i for i,v in enumerate(matrix(),1) if v==spec)
    if metadata!=dict(screen_order=order,total=8,base_runtime_spec=spec):
        raise ValueError('actual screen execution order differs')
    if c.read(directory/'initial.json')['resource_baseline']!=c.read(session/'preparation/manifest.json')['resource_baseline']:
        raise ValueError('screen resource provenance differs')
    result['summary']['screen_order']=order
    return result


def analyze(session):
    verify_preparation(session,current=False)
    rows=[]; seals={}
    for spec in matrix():
        directory=session/'trials'/spec['trial']
        complete=c.read(directory/'complete.json')
        if not complete['valid'] or not complete['performance_run']: raise ValueError('screen trial incomplete')
        result=replay(directory)
        if result!=c.read(directory/'screen_derived.json'): raise ValueError('screen raw replay differs')
        rows.append(result['summary']); seals[spec['trial']]=c.digest(directory/'seal.json')
    report=compare(rows)
    report.update(rows=rows,trial_seals=seals,preparation_seal=c.digest(session/'preparation/seal.json'))
    out=session/'analysis'/str(time.time_ns()); out.mkdir(parents=True)
    c.save(out/'report.json',report)
    lines=['# Short GC / quota-period screen','',report['decision'],'',report['limitation'],'',
        '| Cell | Period | GOGC | CPU/job ms | Busy jobs/s | 500 ms success |','|---|---:|---|---:|---:|---:|']
    for arm,(period,gogc) in gc.FACTORS.items():
        group=[r for r in rows if r['arm']==arm]
        lines.append(f"| {arm} | {period} | {gogc} | {statistics.mean(r['cpu_usec_per_completed_work'] for r in group)/1000:.3f} | {statistics.mean(r['busy_capacity'] for r in group):.2f} | {statistics.mean(r['timely_500_fraction'] for r in group)*100:.2f}% |")
    lines+=['','Block CPU interactions: '+', '.join(f'{v*100:.2f}%' for v in report['block_interactions']),
        '', 'GC hypothesis ruled out: **False**. This screen alone cannot explain the earlier session.', '']
    (out/'report.md').write_text('\n'.join(lines)); c.seal(out)
    c.save(session/'latest_analysis.json',dict(path=str(out.relative_to(session)),seal=c.digest(out/'seal.json')))
    print(report['decision']+'; report: '+str(out/'report.md'),flush=True)
    return report


def run_screen(session):
    if os.geteuid()==0 or os.environ.get('QUOTA_GC_SCREEN_EXTERNAL')!='1': raise ValueError('use the normal-user external launcher')
    os.sched_setaffinity(0,{0,1})
    with gc.run.acquire_experiment_lock():
        verify_preparation(session); gc.run.require_quiet_host()
        if (session/'environment.json').exists() or (session/'trials').exists(): raise ValueError('one capped screen only; preserve all attempts')
        try:
            gc.run.old.prepare_environment(session)
            c.save(session/'environment_seal.json',dict(files_sha256={n:c.digest(session/n) for n in ('environment.json','initial-settling.json')}))
            for order,spec in enumerate(matrix(),1):
                directory=session/'trials'/spec['trial']
                with patch.object(gc,'progress',progress): gc.collect(session,directory,spec)
                # Supplement unchanged retained runtime/raw records with actual
                # screen execution order; reseal before independent screen replay.
                c.save(directory/'screen_execution.json',dict(screen_order=order,total=8,base_runtime_spec=spec))
                c.seal(directory)
                result=replay(directory); c.save(directory/'screen_derived.json',result); c.seal(directory)
            analyze(session)
        except BaseException as e:
            c.save(session/'interruption.json',dict(error=str(e),traceback=traceback.format_exc())); raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify-preparation','run','analyze','status'))
    parser.add_argument('--directory',type=Path,default=DEFAULT)
    args=parser.parse_args(); session=owned_directory(args.directory)
    if args.command=='prepare':
        with gc.run.acquire_experiment_lock(): prepare(session)
    elif args.command=='verify-preparation': verify_preparation(session); print('Eight-trial screen preparation verified.')
    elif args.command=='run': run_screen(session)
    elif args.command=='analyze': analyze(session)
    else: print(json.dumps(dict(directory=str(session),complete=sum((session/'trials'/s['trial']/'complete.json').exists() for s in matrix()),total=8,interrupted=(session/'interruption.json').exists()),indent=2))


if __name__=='__main__': main()
