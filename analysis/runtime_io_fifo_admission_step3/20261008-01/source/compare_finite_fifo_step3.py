"""Predeclared, bounded Step 3 synthetic comparison. No workload launches."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import platform
import random
import resource
import statistics
import subprocess
import sys
import time

from finite_fifo_deadline_reference import Problem,replay,BudgetExceeded
from finite_fifo_deadline_symbolic_check import symbolic_solve
from finite_fifo_deadline_admission import solve_admission,AdmissionLimits
from finite_fifo_deadline_compact_smt import solve_compact_smt
from finite_fifo_deadline_smt import SMTLimits
import z3


METHODS=('candidate','without_hull','reachable','compact_smt','safe_endpoints')


def write_new(path,obj):
    with Path(path).open('x') as stream:
        json.dump(obj,stream,indent=2)
        stream.write('\n')


def prepare(root):
    root.mkdir(parents=True,exist_ok=True)
    cases=[]
    for n in (16,64,128,256):
        rng=random.Random(810202610+n)
        irregular=[]
        t=F(0)
        for _ in range(n):
            t+=F(rng.randint(0,15),10)
            irregular.append(t)
        families={
            'regular':Problem([F(3*i,4) for i in range(n)],3,'3/2','1/4',2),
            'bursts':Problem([4*(i//4) for i in range(n)],3,'3/2','1/4',2),
            'irregular':Problem(irregular,3,'5/4','1/4',2),
            'repeated_interior':Problem([4*(i//4)+[F(0),F(0),F(19,20),F(39,20)][i%4]
                                        for i in range(n)],2,'11/10','1/2',1),
            'no_loss':Problem([F(3*i,4) for i in range(n)],n,'3/2','1/4',2),
        }
        for family,p in families.items():
            cases.append(dict(id=f'{family}_{n}',family=family,offered=n,problem=p.to_json()))
    jobs=[(case['id'],method,repeat) for case in cases for method in METHODS
          if method!='safe_endpoints' or case['family']=='no_loss' for repeat in range(3)]
    random.Random(810202611).shuffle(jobs)
    design=dict(schema=1,synthetic_only=True,cases=cases,order=[list(j) for j in jobs],repeats=3,
        fresh_process=True,serial=True,hard_worker_timeout_seconds=10,
        smt_limits=vars(SMTLimits(max_offers=512,per_check_ms=2000,total_check_ms=5000)),
        admission_limits=vars(AdmissionLimits(max_offers=512,max_states=10000,max_terms=50000000)),
        reachable_limits=dict(max_states=10000,max_transitions=10000000),
        timing='method call including encoding/output/witness construction; excludes imports, process startup, JSON, independent replay',
        memory='absolute fresh worker peak RSS includes imports and post-timing verification; not solver-only',
        outputs_differ='candidate and ablation: admission regions+extrema+witnesses; reachable: constant-outcome cells; compact SMT and endpoints: extrema+witnesses',
        comparison_scope='generic baselines implemented here; no published algorithm reproduction',
        novelty_established=False,real_system_coverage_established=False)
    write_new(root/'design.json',design)


def worker(path,method,design_path):
    p=Problem.from_json(json.loads(Path(path).read_text()))
    design=json.loads(Path(design_path).read_text())
    start,cpu_start=time.perf_counter(),time.process_time()
    try:
        if method in ('candidate','without_hull'):
            result=solve_admission(p,AdmissionLimits(**design['admission_limits']),use_hull=method=='candidate')
            counts=[result[k]['failures'] for k in ('minimum','maximum')]
            witnesses=[result[k]['witness_service_time'] for k in ('minimum','maximum')]
            regions=len(result['regions'])
        elif method=='reachable':
            result=symbolic_solve(p,**design['reachable_limits'])
            counts=[result[k+'_failures'] for k in ('minimum','maximum')]
            witnesses=[]
            for count in counts:
                d=next(c['domain'] for c in result['cells'] if c['failures']==count)
                witnesses.append(str((F(d['low'])+F(d['high']))/2))
            regions=len(result['cells'])
        elif method=='compact_smt':
            result=solve_compact_smt(p,SMTLimits(**design['smt_limits']))
            counts=[result[k]['failures'] for k in ('minimum','maximum')]
            witnesses=[result[k]['witness_service_time'] for k in ('minimum','maximum')]
            regions=None
        else:
            if p.system_slots<len(p.arrivals):
                raise ValueError('endpoint baseline requires an unconditional no-rejection capacity')
            witnesses=[str(p.service_min),str(p.service_max)]
            details=[replay(p,s,include_offers=True) for s in witnesses]
            counts=[d['failures'] for d in details]
            result=dict(stats=dict(fixed_parameter_replays=2))
            regions=None
        elapsed,cpu_elapsed=time.perf_counter()-start,time.process_time()-cpu_start
        for count,s in zip(counts,witnesses):
            actual=replay(p,s,include_offers=True)
            if actual['failures']!=count:
                raise AssertionError('extremum witness mismatch')
        for name in ('minimum','maximum'):
            if method in ('candidate','without_hull'):
                assert result[name]['witness_replay']['offers']==replay(p,result[name]['witness_service_time'],include_offers=True)['offers']
            elif method=='compact_smt':
                assert result[name]['witness']['offers']==replay(p,result[name]['witness_service_time'],include_offers=True)['offers']
        output=dict(status='exact',seconds=elapsed,cpu_seconds=cpu_elapsed,
            minimum_failures=counts[0],maximum_failures=counts[1],witness_service_times=witnesses,
            witnesses_verified=True,regions=regions,stats=result['stats'])
    except BudgetExceeded as exc:
        output=dict(status='incomplete',reason=str(exc),seconds=time.perf_counter()-start,
                    cpu_seconds=time.process_time()-cpu_start)
    output['worker_peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(output))


def run(root):
    data=(root/'design.json').read_bytes()
    design=json.loads(data)
    inputs=root/'inputs'
    inputs.mkdir()
    for case in design['cases']:
        write_new(inputs/(case['id']+'.json'),case['problem'])
    rows=[]
    with (root/'runs.jsonl').open('x') as raw:
        for case,method,repeat in design['order']:
            args=[sys.executable,__file__,'--worker',str(inputs/(case+'.json')),
                  '--method',method,'--design',str(root/'design.json')]
            try:
                proc=subprocess.run(args,text=True,capture_output=True,timeout=design['hard_worker_timeout_seconds'])
                if proc.returncode:
                    raise RuntimeError(proc.stderr)
                row=json.loads(proc.stdout)
            except subprocess.TimeoutExpired:
                row=dict(status='hard_timeout',reason='10-second worker budget')
            row.update(case=case,method=method,repeat=repeat)
            rows.append(row)
            raw.write(json.dumps(row)+'\n')
            raw.flush()
            print(json.dumps(dict(completed=len(rows),total=len(design['order']),case=case,
                                  method=method,status=row['status'])),flush=True)
    summaries=[]
    for case in design['cases']:
        exact=[r for r in rows if r['case']==case['id'] and r['status']=='exact']
        pairs={(r['minimum_failures'],r['maximum_failures']) for r in exact}
        if len(pairs)>1:
            raise AssertionError(f'cross-method mismatch: {case["id"]}')
        for method in METHODS:
            chosen=[r for r in rows if r['case']==case['id'] and r['method']==method]
            if not chosen: continue
            completed=[r for r in chosen if r['status']=='exact']
            summaries.append(dict(case=case['id'],family=case['family'],offered=case['offered'],method=method,
                exact_runs=len(completed),incomplete_runs=len(chosen)-len(completed),
                median_seconds=statistics.median(r['seconds'] for r in completed) if completed else None,
                median_cpu_seconds=statistics.median(r['cpu_seconds'] for r in completed) if completed else None,
                regions=completed[0]['regions'] if completed else None,
                minimum_failures=completed[0]['minimum_failures'] if completed else None,
                maximum_failures=completed[0]['maximum_failures'] if completed else None,
                reasons=sorted({r.get('reason','') for r in chosen if r['status']!='exact'})))
    write_new(root/'comparison.json',dict(schema=1,design_sha256=hashlib.sha256(data).hexdigest(),
        cases=len(design['cases']),runs=len(rows),exact_runs=sum(r['status']=='exact' for r in rows),
        incomplete_runs=sum(r['status']!='exact' for r in rows),all_completed_extrema_agree=True,
        summaries=summaries,environment=dict(python=sys.version,z3=z3.get_version_string(),
        platform=platform.platform(),executable=sys.executable),limitations=['small synthetic families',
        'three repeats','uncontrolled desktop host','output differences','solver-only memory not isolated',
        'timeouts are budget effects','no published tool reproduction','no real-system coverage']))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',type=Path)
    parser.add_argument('--run',type=Path)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--method',choices=METHODS)
    parser.add_argument('--design',type=Path)
    args=parser.parse_args()
    if sum(x is not None for x in (args.prepare,args.run,args.worker))!=1:
        parser.error('choose --prepare, --run or --worker')
    if args.prepare: prepare(args.prepare)
    elif args.run: run(args.run)
    else:
        if args.method is None or args.design is None: parser.error('worker needs method and design')
        worker(args.worker,args.method,args.design)
