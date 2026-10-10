"""Post-pilot time-limit sensitivity, separate from the frozen comparison."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from compare_finite_fifo_solvers import write_new
from finite_fifo_deadline_smt import SMTLimits


def main(root):
    root = Path(root)
    jobs = [(name, vars(limits)) for name in ('regular_32','irregular_32') for limits in
            (SMTLimits(), SMTLimits(per_check_ms=5000,total_check_ms=30000))]
    plan = dict(purpose='post-pilot sensitivity; not part of frozen comparison',
                selection='the two cases incomplete under 500 ms per query',
                jobs=[dict(case=name,limits=limits) for name,limits in jobs],
                repeats=1,hard_worker_timeout_seconds=35,conclusions='budget sensitivity only')
    write_new(root/'sensitivity_design.json',plan)
    rows = []
    runner = Path(__file__).with_name('compare_finite_fifo_solvers.py')
    for name, limits in jobs:
        args = [sys.executable,str(runner),'--worker',str(root/'inputs'/(name+'.json')),
                '--method','smt','--limits',json.dumps(limits)]
        try:
            completed = subprocess.run(args,capture_output=True,text=True,timeout=35)
            if completed.returncode:
                raise RuntimeError(completed.stderr)
            row = json.loads(completed.stdout)
        except subprocess.TimeoutExpired:
            row = dict(status='hard_timeout',reason='35-second worker limit')
        row.update(case=name,limits=limits)
        rows.append(row)
        print(json.dumps(row),flush=True)
    write_new(root/'sensitivity.json',dict(design_sha256=hashlib.sha256(
        (root/'sensitivity_design.json').read_bytes()).hexdigest(),rows=rows))


if __name__ == '__main__':
    main(sys.argv[1])
