"""Post-pilot shortcut diagnostic; all frozen cases and one unresolved control."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

from finite_fifo_deadline_reference import Problem,replay
from finite_fifo_deadline_admission import solve_admission
from finite_fifo_deadline_shortcut import solve_shortcut


def write_new(path,obj):
    with Path(path).open('x') as f:json.dump(obj,f,indent=2)


def worker(path):
    p=Problem.from_json(json.loads(Path(path).read_text()))
    start=time.perf_counter()
    result=solve_shortcut(p)
    seconds=time.perf_counter()-start
    if result['status']=='exact':
        for name in ('minimum','maximum'):
            assert result[name]['witness_replay']['offers']==replay(
                p,result[name]['witness_service_time'],include_offers=True)['offers']
    print(json.dumps(dict(seconds=seconds,result=result)))


def run(root):
    design=json.loads((root/'design.json').read_text())
    control=Problem([0,0,'1/5','2/5'],3,1,'1/2','4/5')
    write_new(root/'unresolved_control_input.json',control.to_json())
    cases=[dict(id=c['id'],input=str(root/'inputs'/(c['id']+'.json'))) for c in design['cases']]
    cases.append(dict(id='unresolved_control',input=str(root/'unresolved_control_input.json')))
    plan=dict(purpose='post-pilot diagnostic, separate from original timing comparison',
              selection='all 20 predeclared cases plus one small unresolved control',cases=cases,
              repeats=3,serial=True,fresh_process=True,hard_worker_timeout_seconds=5,
              novelty_established=False)
    write_new(root/'shortcut_design.json',plan)
    rows=[]
    with (root/'shortcut_runs.jsonl').open('x') as raw:
        for c in cases:
            for repeat in range(3):
                proc=subprocess.run([sys.executable,__file__,'--worker',c['input']],
                                    capture_output=True,text=True,timeout=5)
                if proc.returncode:raise RuntimeError(proc.stderr)
                row=json.loads(proc.stdout)
                row.update(case=c['id'],repeat=repeat)
                rows.append(row)
                raw.write(json.dumps(row)+'\n')
    original=json.loads((root/'comparison.json').read_text())
    summaries=[]
    for c in cases:
        selected=[r for r in rows if r['case']==c['id']]
        result=selected[0]['result']
        certified=result['status']=='exact'
        prior=[r for r in original['summaries'] if r['case']==c['id'] and r['exact_runs']]
        if certified:
            for r in prior:
                assert (result['minimum']['failures'],result['maximum']['failures'])==(
                    r['minimum_failures'],r['maximum_failures'])
        summaries.append(dict(case=c['id'],status=result['status'],median_seconds=statistics.median(
            r['seconds'] for r in selected),mode=result['mode'],proved_lower_count=result['proved_lower_count'],
            proved_upper_count=result['proved_upper_count'],sampled_minimum_count=result['sampled_minimum_count'],
            sampled_maximum_count=result['sampled_maximum_count'],cross_method_results_available=bool(prior)))
    assert all(r['status']=='exact' for r in summaries if r['case']!='unresolved_control')
    assert summaries[-1]['status']=='undetermined'
    write_new(root/'unresolved_control_exact.json',solve_admission(control))
    write_new(root/'shortcut_comparison.json',dict(post_pilot=True,
        design_sha256=hashlib.sha256((root/'shortcut_design.json').read_bytes()).hexdigest(),
        certified_original_cases=20,original_cases=20,control_status='undetermined',
        cross_method_agreement_when_available=True,summaries=summaries,
        inference='Original benchmark families do not establish a need for full symbolic analysis of extrema.'))
    print(json.dumps(dict(certified_original_cases=20,control='undetermined',runs=len(rows))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path)
    p.add_argument('--worker',type=Path)
    args=p.parse_args()
    if (args.run is None)==(args.worker is None):p.error('choose --run or --worker')
    if args.run:run(args.run)
    else:worker(args.worker)
