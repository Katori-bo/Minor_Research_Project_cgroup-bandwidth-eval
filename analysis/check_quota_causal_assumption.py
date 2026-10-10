#!/usr/bin/env python3
"""Small offline assumption check, not a Coz/BCOZ or Linux reproduction."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
OUT=ROOT/'analysis/runtime_io_third_avenue_screen/20261008'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def execution(n,work,quota,period):
    # One continuously runnable worker, no overhead or competing work.
    # Whole budget available initially, hard periodic refill, no carry/burst.
    time=0;epoch=0;remaining=quota;ends=[];segments=[]
    for j in range(n):
        need=work
        while need:
            if remaining==0:
                epoch+=1;time=epoch*period;remaining=quota
            used=min(need,remaining)
            segments.append(dict(job=j,start_ms=time,end_ms=time+used,cpu_ms=used,period_index=epoch))
            time+=used;need-=used;remaining-=used
        ends.append(time)
    return ends,segments

def main():
    if OUT.exists():raise ValueError('preserve existing third-avenue screen')
    protected=read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    preserve={};seal_audit={}
    for dirname in ('runtime_io_calibration_cost_assessment','runtime_io_passive_novelty_screen','runtime_io_passive_baseline_assessment'):
        folder=ROOT/'analysis'/dirname/'20261008'
        sealed=read(folder/'seal.json')['files_sha256']
        actual=c.files(folder)
        changed=[name for name,h in sealed.items() if actual.get(name)!=h]
        extras=[name for name in actual if name not in sealed]
        if changed:raise ValueError('sealed content changed: '+str(changed))
        # Preserve, report, and do not silently remove or reseal existing caches.
        if any(not name.startswith('__pycache__/') for name in extras):
            raise ValueError('unexpected unsealed content: '+str(extras))
        seal_audit[dirname]=dict(sealed_contents_intact=True,extra_unsealed_files=extras,
            exact_directory_seal_matches=not extras)
        preserve.update({str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()})
    for name in ('runtime_io_short_working_draft_v5.md','runtime_io_paper_supporting_material_20261008.md',
        'runtime_io_v19_residual_findings.md','runtime_io_v20_findings.md','runtime_io_v20_repeat_findings.md',
        'runtime_io_execution_state_continuation_findings.md','runtime_io_next_research_decision_20261008.md',
        'runtime_io_passive_baseline_assessment_20261008.md'):
        p=ROOT/'docs'/name;preserve[str(p.relative_to(ROOT))]=sha(p)
    for name,h in {**protected,**preserve}.items():
        if sha(ROOT/name)!=h:raise ValueError('protected input changed')
    cases=[
        dict(id='unlimited_control',n=10,work_ms=50,saving_ms=30,quota_ms=1000,period_ms=1000,deadline_ms=500),
        dict(id='quota_nonbinding_control',n=2,work_ms=5,saving_ms=3,quota_ms=50,period_ms=100,deadline_ms=500),
        dict(id='quota_same_final_period_control',n=2,work_ms=50,saving_ms=10,quota_ms=50,period_ms=100,deadline_ms=500),
        dict(id='quota_crossing_witness',n=10,work_ms=50,saving_ms=30,quota_ms=50,period_ms=100,deadline_ms=500)]
    plan=dict(date='2026-10-08',script_sha256=sha(Path(__file__)),cases=cases,
        question='Can optimization-benefit causal profiling retain its timing equivalence under fixed periodic CPU budgets?',
        scope='Synthetic exact integer-ms periodic-server assumption check only. All jobs available at time zero. No admission rejection, uncertainty solver, Linux collector, profiler sampler, or Go scheduler model.',
        rule_under_test='Subtract accumulated CPU savings from original completion times without recomputing budget depletion/refills.',
        comparator='Direct execution with genuinely reduced CPU work under identical quota/period.',
        inference='A failure motivates checking source profiler semantics; it is not evidence of failure of actual Coz/BCOZ output, not a novel theorem, and not empirical deadline evidence.',
        collection=False)
    c.save(OUT/'design/plan.json',plan);c.save(OUT/'design/preserved_sha256.json',preserve)
    c.save(OUT/'design/prior_seal_audit.json',seal_audit);c.seal(OUT/'design')
    results=[]
    for spec in cases:
        n,w,d,q,p,D=[spec[k] for k in ('n','work_ms','saving_ms','quota_ms','period_ms','deadline_ms')]
        baseline,bseg=execution(n,w,q,p);optimized,oseg=execution(n,w-d,q,p)
        normalized=[t-(j+1)*d for j,t in enumerate(baseline)]
        # Independent inverse of cumulative periodic supply, with boundary ties.
        finish=lambda total:((total-1)//q)*p+(total-1)%q+1
        if baseline!=[finish(j*w) for j in range(1,n+1)] or optimized!=[finish(j*(w-d)) for j in range(1,n+1)]:
            raise ValueError('independent supply inversion mismatch')
        for segments in (bseg,oseg):
            for epoch in {x['period_index'] for x in segments}:
                if sum(x['cpu_ms'] for x in segments if x['period_index']==epoch)>q:raise ValueError('budget violated')
        pct=lambda ends:100*sum(t>D for t in ends)/n
        results.append(dict(**spec,original_completions_ms=baseline,subtract_only_completions_ms=normalized,
            real_optimization_completions_ms=optimized,original_miss_pct=pct(baseline),
            subtract_only_miss_pct=pct(normalized),real_optimization_miss_pct=pct(optimized),
            completion_equivalence=normalized==optimized,budget_ledger_original=bseg,budget_ledger_optimized=oseg))
    if not all(r['completion_equivalence'] for r in results[:-1]) or results[-1]['completion_equivalence']:
        raise ValueError('declared controls/witness changed')
    report=dict(date='2026-10-08',status='offline_screen_complete',results=results,
        selected_candidate='optimization_benefit_profiling_under_fixed_periodic_CPU_quota',
        decision='proceed_only_to_bounded_profiler_semantics_and_prior_art_gate',
        empirical_profiler_failure=False,novelty_established=False,new_collection=False,
        witness_scope='Shows noncommutation of CPU-work reduction and wall-time subtraction in a simple periodic server. Not actual profiler reproduction or Linux observational evidence.',
        next_gate='Pin and inspect Coz/BCOZ delay, synchronization, phase correction and progress semantics; check prior quota-aware profiling; compare actual CPU-saving reference and simple periodic-budget replay. Stop if ordinary machinery suffices.')
    c.save(OUT/'assumption_check.json',report)
    for name,h in {**protected,**preserve}.items():
        if sha(ROOT/name)!=h:raise ValueError('protected input changed')
    c.save(OUT/'verification.json',dict(status='pass',synthetic_cases=len(cases),
        independent_supply_inversion_vectors=8,per_period_budget_conservation=True,controls_pass=True,
        protected_scientific_files=len(protected),additional_preserved_files=len(preserve),
        actual_profiler_executed=False,Linux_experiment=False,new_collection=False))
    print(json.dumps(dict(decision=report['decision'],cases=[{k:r[k] for k in ('id','completion_equivalence','original_miss_pct','subtract_only_miss_pct','real_optimization_miss_pct')} for r in results]),indent=2))

if __name__=='__main__':main()
