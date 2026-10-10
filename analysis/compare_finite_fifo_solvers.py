"""Frozen synthetic Step 2 comparison; fresh serial processes, bounded runs.

Run --prepare once before --run. Outputs are never overwritten. These are
algorithm probes, not workload experiments or a publication-scale benchmark.
"""
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

from finite_fifo_deadline_reference import Problem, replay, solve, BudgetExceeded
from finite_fifo_deadline_symbolic_check import symbolic_solve
from finite_fifo_deadline_smt import SMTLimits, IncompleteAnalysis, solve_smt
import z3


METHODS = ('reference', 'reachable', 'smt')


def write_new(path, obj):
    with Path(path).open('x') as stream:
        json.dump(obj, stream, indent=2)
        stream.write('\n')


def prepare(root):
    root.mkdir(parents=True, exist_ok=True)
    cases = []
    for n in (4,8,16,32):
        rng = random.Random(810202600+n)
        irregular = []
        t = F(0)
        for _ in range(n):
            t += F(rng.randint(0,15),10)
            irregular.append(t)
        families = {
            'regular': Problem([F(3*i,4) for i in range(n)],3,'3/2','1/4',2),
            'bursts': Problem([4*(i//4) for i in range(n)],3,'3/2','1/4',2),
            'irregular': Problem(irregular,3,'5/4','1/4',2),
            'repeated_interior': Problem([4*(i//4)+[F(0),F(0),F(19,20),F(39,20)][i%4]
                                         for i in range(n)],2,'11/10','1/2',1),
        }
        for family, p in families.items():
            cases.append(dict(id=f'{family}_{n}', family=family, offered=n, problem=p.to_json()))
    jobs = [(case['id'], method, repeat) for case in cases for method in METHODS for repeat in range(3)]
    random.Random(810202603).shuffle(jobs)
    write_new(root/'design.json',dict(schema=1, purpose='bounded offline method comparison',
        synthetic_only=True, cases=cases, order=[list(job) for job in jobs], repeats=3,
        fresh_process=True, serial=True, random_seed=810202603,
        hard_worker_timeout_seconds=6, smt_limits=vars(SMTLimits(per_check_ms=500,total_check_ms=2000)),
        timing='method call including encoding and witness extraction; excludes imports, JSON, verification',
        memory='fresh worker absolute peak RSS, including imports and verification; not solver-only memory',
        outputs_differ='reference: full conservative partition+witnesses; reachable: reachable partition; SMT: extrema+witnesses',
        novelty_established=False, real_system_coverage_established=False))


def worker(input_path, method, limits):
    p = Problem.from_json(json.loads(Path(input_path).read_text()))
    start_wall, start_cpu = time.perf_counter(), time.process_time()
    try:
        if method == 'reference':
            result = solve(p)
            counts = [result[k]['failures'] for k in ('minimum','maximum')]
            witnesses = [result[k]['witness_service_time'] for k in ('minimum','maximum')]
        elif method == 'reachable':
            result = symbolic_solve(p)
            counts = [result[k+'_failures'] for k in ('minimum','maximum')]
            witnesses = []
            for count in counts:
                d = next(c['domain'] for c in result['cells'] if c['failures']==count)
                witnesses.append(str((F(d['low'])+F(d['high']))/2))
        else:
            result = solve_smt(p, SMTLimits(**limits))
            counts = [result[k]['failures'] for k in ('minimum','maximum')]
            witnesses = [result[k]['witness_service_time'] for k in ('minimum','maximum')]
        seconds, cpu_seconds = time.perf_counter()-start_wall, time.process_time()-start_cpu
        # Outside timed method. No claim based on an unverified witness.
        for count,s in zip(counts,witnesses):
            actual = replay(p,s,include_offers=True)
            if actual['failures'] != count:
                raise AssertionError('extremum witness disagrees with exact replay')
        if method == 'smt':
            for name in ('minimum','maximum'):
                actual = replay(p,result[name]['witness_service_time'],include_offers=True)
                if actual['offers'] != result[name]['witness']['offers']:
                    raise AssertionError('SMT per-offer witness disagrees with replay')
        output = dict(status='exact', minimum_failures=counts[0],maximum_failures=counts[1],
                      witness_service_times=witnesses,witnesses_verified=True,
                      seconds=seconds,cpu_seconds=cpu_seconds,stats=result['stats'],
                      cells=len(result['cells']) if 'cells' in result else None)
    except (BudgetExceeded, IncompleteAnalysis) as exc:
        output = dict(status='incomplete', reason=str(exc),seconds=time.perf_counter()-start_wall,
                      cpu_seconds=time.process_time()-start_cpu)
    output['worker_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(json.dumps(output))


def run(root):
    design_bytes = (root/'design.json').read_bytes()
    design = json.loads(design_bytes)
    inputs = root/'inputs'
    inputs.mkdir()
    for case in design['cases']:
        write_new(inputs/(case['id']+'.json'),case['problem'])
    rows = []
    raw_path = root/'runs.jsonl'
    with raw_path.open('x') as raw:
        for case_id, method, repeat in design['order']:
            args = [sys.executable,__file__,'--worker',str(inputs/(case_id+'.json')),
                    '--method',method,'--limits',json.dumps(design['smt_limits'])]
            try:
                completed = subprocess.run(args,text=True,capture_output=True,
                                           timeout=design['hard_worker_timeout_seconds'])
                if completed.returncode:
                    raise RuntimeError(f'worker failed: {completed.stderr}')
                row = json.loads(completed.stdout)
            except subprocess.TimeoutExpired:
                row = dict(status='hard_timeout', reason='6-second worker limit')
            row.update(case=case_id,method=method,repeat=repeat)
            rows.append(row)
            raw.write(json.dumps(row)+'\n')
            raw.flush()
            print(json.dumps(dict(completed=len(rows),total=len(design['order']),
                                  case=case_id,method=method,status=row['status'])),flush=True)
    summaries = []
    for case in design['cases']:
        exact = [r for r in rows if r['case']==case['id'] and r['status']=='exact']
        pairs = {(r['minimum_failures'],r['maximum_failures']) for r in exact}
        if len(pairs)>1:
            raise AssertionError(f'cross-method extrema disagreement: {case["id"]}')
        for method in METHODS:
            selected = [r for r in rows if r['case']==case['id'] and r['method']==method]
            done = [r for r in selected if r['status']=='exact']
            summaries.append(dict(case=case['id'],family=case['family'],offered=case['offered'],method=method,
                exact_runs=len(done),incomplete_runs=len(selected)-len(done),
                median_seconds=statistics.median(r['seconds'] for r in done) if done else None,
                median_cpu_seconds=statistics.median(r['cpu_seconds'] for r in done) if done else None,
                peak_worker_rss_kib=max((r['worker_peak_rss_kib'] for r in done), default=None),
                cells=done[0]['cells'] if done else None,
                minimum_failures=done[0]['minimum_failures'] if done else None,
                maximum_failures=done[0]['maximum_failures'] if done else None))
    write_new(root/'comparison.json',dict(schema=1,design_sha256=hashlib.sha256(design_bytes).hexdigest(),
        cases=len(design['cases']),runs=len(rows),exact_runs=sum(r['status']=='exact' for r in rows),
        incomplete_runs=sum(r['status']!='exact' for r in rows),all_exact_extrema_agree=True,
        runtime_environment=dict(python=sys.version,executable=sys.executable,z3=z3.get_version_string(),
                                 platform=platform.platform(),machine=platform.machine()),
        limitations=['small synthetic traces','three repeats','uncontrolled desktop host',
                     'outputs differ','one unoptimized generic SMT encoding',
                     'peak RSS includes runtime/imports/verification','not a published algorithm reproduction'],
        summaries=summaries))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',type=Path)
    parser.add_argument('--run',type=Path)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--method',choices=METHODS)
    parser.add_argument('--limits',default='{}')
    args = parser.parse_args()
    if sum(x is not None for x in (args.prepare,args.run,args.worker)) != 1:
        parser.error('choose exactly one of --prepare, --run, --worker')
    if args.prepare:
        prepare(args.prepare)
    elif args.run:
        run(args.run)
    else:
        if args.method is None:
            parser.error('--worker requires --method')
        worker(args.worker,args.method,json.loads(args.limits))


if __name__ == '__main__':
    main()
