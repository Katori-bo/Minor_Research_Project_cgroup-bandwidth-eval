#!/usr/bin/env python3
"""Independently step through the synthetic cases and audit preserved inputs."""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import v28_common as c
OUT=ROOT/'analysis/runtime_io_third_avenue_screen/20261008'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def ticks(n,work,quota,period):
    # Independent millisecond stepping; do not call the generation simulator.
    time=0;done=0;need=work;ends=[]
    while done<n:
        supply=time%period<quota
        time+=1
        if supply:
            need-=1
            if need==0:
                ends.append(time);done+=1;need=work
    return ends

def main():
    c.verify_seal(OUT/'design')
    plan=c.read(OUT/'design/plan.json')
    if digest(ROOT/'analysis/check_quota_causal_assumption.py')!=plan['script_sha256']:
        raise ValueError('generation source changed')
    protected=c.read(ROOT/'analysis/runtime_io_paper_consolidation_review/20261008/protected_evidence_sha256.json')
    extra=c.read(OUT/'design/preserved_sha256.json')
    for name,h in {**protected,**extra}.items():
        if digest(ROOT/name)!=h:raise ValueError('preserved input changed: '+name)
    results=c.read(OUT/'assumption_check.json')['results']
    if len(results)!=len(plan['cases']):raise ValueError('case count')
    for spec,r in zip(plan['cases'],results):
        if any(r[k]!=v for k,v in spec.items()):raise ValueError('case changed')
        n,w,d,q,p,D=[r[k] for k in ('n','work_ms','saving_ms','quota_ms','period_ms','deadline_ms')]
        baseline=ticks(n,w,q,p);optimized=ticks(n,w-d,q,p)
        if baseline!=r['original_completions_ms'] or optimized!=r['real_optimization_completions_ms']:
            raise ValueError('tick reference mismatch')
        subtract=[t-(i+1)*d for i,t in enumerate(baseline)]
        if subtract!=r['subtract_only_completions_ms']:raise ValueError('subtraction mismatch')
        for ends,label in [(baseline,'original'),(optimized,'real_optimization'),(subtract,'subtract_only')]:
            if 100*sum(t>D for t in ends)/n!=r[label+'_miss_pct']:raise ValueError('deadline endpoint mismatch')
        if (subtract==optimized)!=r['completion_equivalence']:raise ValueError('equivalence mismatch')
    if [r['completion_equivalence'] for r in results]!=[True,True,True,False]:raise ValueError('controls/witness')
    report=dict(status='pass',independent_tick_vectors=8,deadline_endpoint_checks=12,
        protected_scientific_files=len(protected),additional_preserved_files=len(extra),
        generator_sha256=plan['script_sha256'],verifier_sha256=digest(Path(__file__)),
        original_sealed_contents_intact=True,exact_prior_directory_inventory_exception=
            c.read(OUT/'design/prior_seal_audit.json')['runtime_io_calibration_cost_assessment']['extra_unsealed_files'],
        actual_profiler_reproduced=False,new_collection=False)
    c.save(OUT/'independent_verification.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
