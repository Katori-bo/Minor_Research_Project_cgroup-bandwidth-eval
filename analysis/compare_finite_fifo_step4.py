"""Frozen harder-case gate: offline synthetic inputs, no service experiments.

Select using only the existing shortcut and queue replay, never solver timing.
Reuse all Step 3 exact implementations unchanged. Retain every pool candidate,
selection decision, timed refusal and completed result.
"""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys

from finite_fifo_deadline_reference import Problem, replay, solve
from finite_fifo_deadline_shortcut import solve_shortcut
from compare_finite_fifo_step3 import worker, write_new

METHODS = ('candidate', 'reachable', 'compact_smt')
FAMILIES = ('jittered', 'clustered', 'mixed_gaps')
CONFIGS = {
    'small_buffer': dict(system_slots=2, relative_deadline='5/4',
                         service_min='9/20', service_max='23/20'),
    'larger_buffer': dict(system_slots=5, relative_deadline='21/10',
                          service_min='11/20', service_max='27/20'),
}


def generate(family, n, config_index, trial):
    rng = random.Random(810202640 + 100000 * FAMILIES.index(family)
                        + 10000 * config_index + 100 * n + trial)
    t = F(0)
    arrivals = [t]
    for i in range(1, n):
        if family == 'jittered':
            gap = F(rng.randint(3, 13), 20)
        elif family == 'clustered':
            gap = F(rng.randint(18, 46), 20) if i % 4 == 0 else F(rng.randint(0, 4), 20)
        else:
            gap = F(rng.choice([0, 1, 3, 5, 8, 13, 21, 34]), 20)
        t += gap
        arrivals.append(t)
    return arrivals


def prepare(root):
    root.mkdir(parents=True, exist_ok=True)
    source_files = ['compare_finite_fifo_step4.py', 'compare_finite_fifo_step3.py',
                    'finite_fifo_deadline_reference.py', 'finite_fifo_deadline_symbolic_check.py',
                    'finite_fifo_deadline_admission.py', 'finite_fifo_deadline_compact_smt.py',
                    'finite_fifo_deadline_smt.py', 'finite_fifo_deadline_shortcut.py']
    source_hashes = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                     for name in source_files}
    protocol = dict(schema=1, synthetic_only=True, sizes=[8, 16, 32, 64],
        families=list(FAMILIES), configurations=CONFIGS, pool_trials_per_stratum=50,
        seed_formula='810202640 + 100000*family_index + 10000*config_index + 100*N + trial',
        selection='first trial per stratum with shortcut undetermined and at least one rejection at its five probe values; all 50 candidates logged',
        prohibited_selection_information='no exact solver, region count, runtime or true extremum used for selection',
        methods=list(METHODS), repeats=3, order_seed=810202641,
        fresh_process=True, serial=True, hard_worker_timeout_seconds=6,
        admission_limits=dict(max_offers=512, max_states=10000, max_terms=50000000),
        reachable_limits=dict(max_states=10000, max_transitions=10000000),
        smt_limits=dict(max_offers=512, per_check_ms=750, total_check_ms=2000, resource_limit=0),
        timing='method call including output and witnesses; excludes imports/startup/JSON and independent replay',
        outputs_differ='candidate admission-region extrema; reachable constant-outcome cells; compact SMT extrema with witnesses',
        practical_gate='candidate completes no fewer runs than reachable, at least 2x faster on >=2/3 of paired all-three-exact cases, and >=1/2 in each family; requires >=12 paired cases',
        gate_interpretation='exploratory engineering threshold only; passing does not establish originality or publication readiness',
        reference_check='all selected 8-offer cases independently compared with complete breakpoint reference outside timing',
        shortcuts='selection status and five-probe extrema retained; undetermined is never an exact result',
        limitations=['selected unresolved subset, not workload prevalence', 'small synthetic cases',
                     'three repeats', 'desktop host not controlled', 'generic baselines written here, no published tool reproduction',
                     'timeouts reflect these limits', 'common constant service parameter only'],
        source_sha256=source_hashes)
    # Freeze the protocol before even running the selection screen.
    write_new(root / 'protocol.json', protocol)
    pool, cases = [], []
    for family in FAMILIES:
        for n in protocol['sizes']:
            for ci, (config, params) in enumerate(CONFIGS.items()):
                chosen = False
                for trial in range(protocol['pool_trials_per_stratum']):
                    p = Problem(generate(family, n, ci, trial), **params)
                    shortcut = solve_shortcut(p)
                    probes = sorted({p.service_min + (p.service_max - p.service_min) * F(k, 4)
                                     for k in range(5)})
                    rejected = [replay(p, s)['rejected'] for s in probes]
                    eligible = shortcut['status'] == 'undetermined' and max(rejected) > 0
                    selected = eligible and not chosen
                    case_id = f'{family}_{n}_{config}'
                    row = dict(stratum=case_id, trial=trial, problem=p.to_json(),
                        shortcut_status=shortcut['status'],
                        proved_lower_count=shortcut['proved_lower_count'],
                        proved_upper_count=shortcut['proved_upper_count'],
                        sampled_minimum_count=shortcut['sampled_minimum_count'],
                        sampled_maximum_count=shortcut['sampled_maximum_count'],
                        probe_service_times=[str(s) for s in probes], probe_rejected_counts=rejected,
                        eligible=eligible, selected=selected)
                    pool.append(row)
                    if selected:
                        cases.append(dict(id=case_id, family=family, offered=n, configuration=config,
                                          trial=trial, problem=p.to_json(), selection=row))
                        chosen = True
    write_new(root / 'selection.json', dict(pool=pool, selected_cases=len(cases),
        eligible_candidates=sum(r['eligible'] for r in pool), pool_candidates=len(pool),
        missing_strata=24-len(cases)))
    jobs = [(c['id'], method, repeat) for c in cases for method in METHODS for repeat in range(3)]
    random.Random(protocol['order_seed']).shuffle(jobs)
    design = dict(protocol, cases=cases, order=[list(j) for j in jobs],
                  protocol_sha256=hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest(),
                  selection_sha256=hashlib.sha256((root/'selection.json').read_bytes()).hexdigest())
    write_new(root / 'design.json', design)
    print(json.dumps(dict(selected=len(cases), pool=len(pool), eligible=sum(r['eligible'] for r in pool),
                          timed_runs=len(jobs))))


def run(root):
    data = (root/'design.json').read_bytes()
    design = json.loads(data)
    for name, digest in design['source_sha256'].items():
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'frozen source changed: {name}')
    inputs = root/'inputs'
    inputs.mkdir()
    for case in design['cases']:
        write_new(inputs/(case['id']+'.json'), case['problem'])
    rows = []
    with (root/'runs.jsonl').open('x') as raw:
        for case, method, repeat in design['order']:
            cmd = [sys.executable, __file__, '--worker', str(inputs/(case+'.json')),
                   '--method', method, '--design', str(root/'design.json')]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=design['hard_worker_timeout_seconds'])
                if proc.returncode:
                    row = dict(status='worker_error', reason=proc.stderr)
                else:
                    row = json.loads(proc.stdout)
            except subprocess.TimeoutExpired:
                row = dict(status='hard_timeout', reason='6-second worker budget')
            row.update(case=case, method=method, repeat=repeat)
            rows.append(row)
            raw.write(json.dumps(row)+'\n')
            raw.flush()
            print(json.dumps(dict(completed=len(rows), total=len(design['order']), case=case,
                                  method=method, status=row['status'])), flush=True)
    summaries, paired, checks, grid_misses = [], [], [], []
    for case in design['cases']:
        exact = [r for r in rows if r['case']==case['id'] and r['status']=='exact']
        counts = {(r['minimum_failures'],r['maximum_failures']) for r in exact}
        if len(counts)>1:
            raise AssertionError(f'cross-method mismatch: {case["id"]}')
        methods = {}
        for method in METHODS:
            selected = [r for r in rows if r['case']==case['id'] and r['method']==method]
            completed = [r for r in selected if r['status']=='exact']
            summary = dict(case=case['id'], family=case['family'], offered=case['offered'],
                configuration=case['configuration'], method=method, exact_runs=len(completed),
                incomplete_runs=len(selected)-len(completed),
                median_seconds=statistics.median(r['seconds'] for r in completed) if completed else None,
                regions=completed[0]['regions'] if completed else None,
                minimum_failures=completed[0]['minimum_failures'] if completed else None,
                maximum_failures=completed[0]['maximum_failures'] if completed else None,
                reasons=sorted({r.get('reason','') for r in selected if r['status']!='exact'}))
            summaries.append(summary)
            methods[method]=summary
        c,r = methods['candidate'],methods['reachable']
        if c['exact_runs']==3 and r['exact_runs']==3:
            paired.append(dict(case=case['id'],family=case['family'],offered=case['offered'],
                reachable_over_candidate=r['median_seconds']/c['median_seconds'],
                candidate_faster=c['median_seconds']<r['median_seconds'],
                candidate_at_least_2x=r['median_seconds']>=2*c['median_seconds']))
        if counts:
            low,high=next(iter(counts))
            selection=case['selection']
            grid_misses.append(dict(case=case['id'],minimum=low,maximum=high,
                sampled_minimum=selection['sampled_minimum_count'],
                sampled_maximum=selection['sampled_maximum_count'],
                misses_minimum=selection['sampled_minimum_count']!=low,
                misses_maximum=selection['sampled_maximum_count']!=high))
            if case['offered']==8:
                ref=solve(Problem.from_json(case['problem']))
                assert (ref['minimum']['failures'],ref['maximum']['failures'])==(low,high)
                checks.append(dict(case=case['id'],minimum=low,maximum=high,
                                   reference_cells=len(ref['cells']),agreement=True))
    completions={m:sum(r['status']=='exact' and r['method']==m for r in rows) for m in METHODS}
    family_gate={f:dict(pairs=sum(p['family']==f for p in paired),
        at_least_2x=sum(p['family']==f and p['candidate_at_least_2x'] for p in paired)) for f in FAMILIES}
    overall_2x=sum(p['candidate_at_least_2x'] for p in paired)
    passed=(len(paired)>=12 and completions['candidate']>=completions['reachable']
            and 3*overall_2x>=2*len(paired)
            and all(v['pairs']>0 and 2*v['at_least_2x']>=v['pairs'] for v in family_gate.values()))
    write_new(root/'comparison.json',dict(schema=1,design_sha256=hashlib.sha256(data).hexdigest(),
        cases=len(design['cases']),runs=len(rows),completions=completions,
        incomplete_runs=sum(r['status']!='exact' for r in rows),
        all_completed_extrema_agree=True,all_completed_witnesses_verified=all(
            r['witnesses_verified'] for r in rows if r['status']=='exact'),
        summaries=summaries,paired_cases=paired,family_gate=family_gate,
        candidate_faster_cases=sum(p['candidate_faster'] for p in paired),
        candidate_at_least_2x_cases=overall_2x,practical_gate_passed=passed,
        reference_checks=checks,probe_accuracy=grid_misses,
        novelty_established=False,limitations=design['limitations']))
    print(json.dumps(dict(completions=completions,paired=len(paired),at_least_2x=overall_2x,
                          practical_gate_passed=passed)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',type=Path)
    parser.add_argument('--run',type=Path)
    parser.add_argument('--worker',type=Path)
    parser.add_argument('--method',choices=METHODS)
    parser.add_argument('--design',type=Path)
    args=parser.parse_args()
    if sum(x is not None for x in (args.prepare,args.run,args.worker))!=1:
        parser.error('choose prepare, run or worker')
    if args.prepare: prepare(args.prepare)
    elif args.run: run(args.run)
    else:
        if args.method is None or args.design is None: parser.error('worker requires method and design')
        worker(args.worker,args.method,args.design)
