#!/usr/bin/env python3
"""Bounded source/reporting semantics comparison, not a runtime reproduction."""
from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
OUT=ROOT/'analysis/runtime_io_profiler_semantics_gate/20261008'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def replay(work,q,p,reserve=0,horizon=None):
    # Ordinary per-ms periodic supply replay. Reserve is charged controller CPU.
    t=0;j=0;left=work[0];ends=[];application_cpu=0;controller_cpu=0
    while j<len(work) and (horizon is None or t<horizon):
        phase=t%p
        if phase<reserve:controller_cpu+=1
        elif phase<q:
            application_cpu+=1;left-=1
            if left==0:
                ends.append(t+1);j+=1
                if j<len(work):left=work[j]
        t+=1
    return dict(completions_ms=ends,elapsed_ms=t,application_cpu_ms=application_cpu,controller_cpu_ms=controller_cpu)

def profile(elapsed,delta,credit,samples=1):
    # Source C++ record arithmetic: duration=elapsed-global_credit.
    # Include runtime/sample records: inspected pinned viewers ignore these.
    ns=1000000
    return '\n'.join([
      'startup\ttime=0',
      f'experiment\tselected=work.cc:1\tspeedup=0\tduration={elapsed*ns}\tselected-samples={samples}',
      f'throughput-point\tname=done\tdelta={delta}',
      f'experiment\tselected=work.cc:1\tspeedup=0.6\tduration={round((elapsed-credit)*ns)}\tselected-samples={samples}',
      f'throughput-point\tname=done\tdelta={delta}',
      f'runtime\ttime={elapsed*2*ns}',
      f'samples\tlocation=work.cc:1\tcount={samples*2}',
      'shutdown\ttime=0',''])

def main():
    if (OUT/'design').exists():raise ValueError('preserve previous gate')
    c.verify_seal(ROOT/'analysis/runtime_io_third_avenue_screen/20261008')
    manifest=c.read(OUT/'sources/manifest.json')
    for row in manifest['files']:
        p=ROOT/row['saved_path'];raw=p.read_bytes()
        if sha(p)!=row['sha256'] or hashlib.sha1(f'blob {len(raw)}\0'.encode()+raw).hexdigest()!=row['git_blob_sha1']:
            raise ValueError('pinned source changed')
    protected=c.read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    preserved=c.read(ROOT/'analysis/runtime_io_third_avenue_screen/20261008/design/preserved_sha256.json')
    folder=ROOT/'analysis/runtime_io_third_avenue_screen/20261008'
    preserved.update({str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()})
    preserved['docs/runtime_io_third_avenue_novelty_screen_20261008.md']=sha(ROOT/'docs/runtime_io_third_avenue_novelty_screen_20261008.md')
    for rel,h in {**protected,**preserved}.items():
        if sha(ROOT/rel)!=h:raise ValueError('protected input changed')
    cases=[dict(id='full_cpu_control',q=100,p=100,reserve=0),
           dict(id='half_cpu',q=50,p=100,reserve=0),
           dict(id='fifth_cpu',q=20,p=100,reserve=0),
           dict(id='half_cpu_controller_1ms',q=50,p=100,reserve=1),
           dict(id='half_cpu_controller_5ms',q=50,p=100,reserve=5)]
    plan=dict(date='2026-10-08',cases=cases,horizon_ms=10000,work_ms=50,saving_ms=30,
      assumption='One indefinitely backlogged application worker; known full initial periodic budget; same reserved controller CPU in baseline and genuine modeled optimization. Perfect aligned 1-ms task-clock sample census and flushed batches. No locks, I/O or wakeup dependency. No real sampling or Linux execution.',
      source_paths='Coz CPU-only credits; BCOZ on-CPU subclass credits; BCOZ line credits with all non-lock blocked samples attributed to target (conditional, not established for Linux quota stack traces).',
      limitations=['source-model counter credit only, not execution of profiler C++/kernel sampler','no measured overhead or neutral observer claim','BCOZ blocked attribution unresolved','deadline miss fractions are not native profiler output'],
      scripts_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'analysis/run_pinned_profiler_reporting.js']},
      novelty_gate='Stop unless a distinct capability survives adequate ordinary replay with matched information/cost.',new_collection=False)
    c.save(OUT/'design/plan.json',plan);c.save(OUT/'design/preserved_sha256.json',preserved);c.seal(OUT/'design')
    records=[];cases_out=[]
    for spec in cases:
        q,p,h=spec['q'],spec['p'],spec['reserve'];W=plan['horizon_ms']
        baseline=replay([50]*1000,q,p,h,W);optimized=replay([20]*1000,q,p,h,W)
        N=len(baseline['completions_ms']);M=len(optimized['completions_ms'])
        C=baseline['application_cpu_ms'];H=baseline['controller_cpu_ms'];B=W-C
        # One application's local counter never lags global: no injected sleep.
        # Perfect 1ms samples; processing in 10ms batches leaves no partial batch.
        if C%10:raise ValueError('Coz batch-boundary assumption violated')
        credits={'cpu_only':.6*C,'line_all_blocked':.6*(C+B)}
        for mode,credit in credits.items():
            records.append(dict(id=spec['id']+'_'+mode,profile_text=profile(W,N,credit,C+B)))
        cases_out.append(dict(**spec,application_cpu_ms=C,charged_controller_cpu_ms=H,
          original_completions=N,genuine_optimized_completions=M,
          actual_period_reduction=1-N/M,source_credit_cpu_only_ms=credits['cpu_only'],
          source_credit_all_blocked_ms=credits['line_all_blocked'],
          ordinary_replay_exact=True,conditional_all_blocked_attribution=True))
    # Same profile metadata with changed phase/sample totals: reporting invariance.
    text=records[2]['profile_text']
    records.append(dict(id='phase_metadata_control',profile_text=text.replace('count=10000','count=100000000').replace('time=20000000000','time=90000000000')))
    c.save(OUT/'reporting_inputs.json',dict(records=records))
    subprocess.run(['node',str(ROOT/'analysis/run_pinned_profiler_reporting.js')],check=True,cwd=ROOT)
    native=c.read(OUT/'native_reporting_results.json')['results']
    lookup={}
    for r in native:
        if len(r['results'])!=1:raise ValueError('missing native curve')
        measures=r['results'][0]['progress_points'][0]['measurements']
        value=next(m['progress_speedup'] for m in measures if m['speedup']==.6)
        lookup[(r['profiler'],r['id'])]=value
    for r in cases_out:
        for name in ('coz','bcoz'):
            cpu=lookup[(name,r['id']+'_cpu_only')];blocked=lookup[(name,r['id']+'_line_all_blocked')]
            if abs(cpu-r['source_credit_cpu_only_ms']/10000)>1e-12 or abs(blocked-.6)>1e-12:
                raise ValueError('native reporting vs source arithmetic mismatch')
            r[name+'_cpu_only_reported_period_reduction']=cpu
            r[name+'_conditional_all_blocked_reported_period_reduction']=blocked
        if abs(r['actual_period_reduction']-.6)>1e-12:raise ValueError('known optimization reference')
    for name in ('coz','bcoz'):
        if lookup[(name,'phase_metadata_control')]!=lookup[(name,'half_cpu_cpu_only')]:raise ValueError('phase metadata invariance')
    A=[20]*5+[50]*5;B=[50]*5+[20]*5
    ranking=[]
    for label,work in [('save_first_five',A),('save_last_five',B)]:
        result=replay(work,50,100)
        result.update(id=label,total_cpu_ms=sum(work),miss_pct=100*sum(t>500 for t in result['completions_ms'])/10)
        ranking.append(result)
    if [x['miss_pct'] for x in ranking]!=[20,50] or ranking[0]['elapsed_ms']!=ranking[1]['elapsed_ms']:
        raise ValueError('declared aggregate-tie deadline witness')
    report=dict(status='bounded_offline_gate_complete',cases=cases_out,deadline_ranking_example=ranking,
      native_reporting_checks=len(native),phase_metadata_controls=2,
      decision='stop_custom_profiler_and_new_collection',novelty_established=False,
      conclusion='CPU-only source-model mismatch survives, conditional BCOZ line credits can recover aggregate benefit, native outputs do not identify deadline ranking, ordinary periodic replay solves every declared reference with the same toy inputs. No fewer-measurement capability established.',
      actual_runtime_profiler_failure_established=False,new_collection=False,
      protected_scientific_files=len(protected),additional_preserved_files=len(preserved))
    c.save(OUT/'assessment.json',report)
    for rel,h in {**protected,**preserved}.items():
        if sha(ROOT/rel)!=h:raise ValueError('protected input changed')
    print(json.dumps(dict(decision=report['decision'],native_reporting_checks=len(native),cases=cases_out,ranking=ranking),indent=2))

if __name__=='__main__':main()
