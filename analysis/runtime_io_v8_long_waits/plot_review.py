"""Render a saved-window illustration; no experiment is run."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
REVIEW = BASE / 'review_final'
rid = 'yield_b2_trace'
summary = json.loads((REVIEW / 'summary.json').read_text())
t = next(t for t in summary['trials'] if t['run_id'] == rid)
attempt = ROOT / 'results/diagnostic/runtime-io-v8-yield-1/attempts' / rid / '001'
trace = json.loads((attempt / 'trace_requests.json').read_text())
metrics = json.loads((attempt / 'server_metrics.json').read_text())
clock = trace['clock_mapping']
offset = (clock['offset_low_ns'] + clock['offset_high_ns']) // 2
begin, end = t['ready_trace_ns'], t['run_trace_ns']
times = sorted(e['completion_ns'] + offset for e in metrics['events']
               if begin <= e['completion_ns'] + offset < end)
assert len(times) == t['worker_completion_certain'] == t['worker_completion_possible'] == 384
seconds = [(x - begin) / 1e9 for x in times]
duration = (end - begin) / 1e9
fig, axes = plt.subplots(2, 1, figsize=(9, 4.4), sharex=True,
                         gridspec_kw={'height_ratios': [1, 2]})
fig.patch.set_facecolor('white')
fig.suptitle('HTTP waits for its turn while workers complete 384 jobs',
             x=.12, y=.98, ha='left', fontsize=15, weight='bold')
ax = axes[0]
ax.barh([0], [duration], height=.38, color='#e39a38', left=0)
ax.text(duration/2, 0, 'Ready, but not running: 2.900648 seconds',
        va='center', ha='center', fontsize=11, color='#312415')
ax.scatter([0, duration], [0, 0], s=65, c=['#e39a38', '#258573'], zorder=3)
ax.text(0, .38, 'Network read wakes HTTP', ha='left', fontsize=10)
ax.text(duration, -.48, 'HTTP runs; handler entry follows in ~25 µs',
        ha='right', fontsize=10, color='#206b5e')
ax.set_ylim(-.7, .7)
ax.set_yticks([])
ax.spines[['left', 'top', 'right', 'bottom']].set_visible(False)
ax.tick_params(bottom=False, labelbottom=False)
ax = axes[1]
ax.step([0, *seconds, duration], [0, *range(1, len(times)+1), len(times)],
        where='post', color='#347da2', linewidth=2)
ax.set_ylabel('Completed worker jobs')
ax.set_xlabel('Seconds since this HTTP goroutine became ready')
ax.set_yticks([0, 100, 200, 300, 384])
ax.set_xlim(-.02, duration+.03)
ax.set_ylim(0, 405)
ax.grid(axis='y', color='#e5e9eb')
ax.spines[['top', 'right']].set_visible(False)
fig.text(.12, .015, 'Saved v8 block 2, tracing on, worker yielding off • G2103 / request 1695 • Selected extreme window',
         fontsize=8, color='#59656a')
fig.tight_layout(rect=[0, .055, 1, .95])
fig.savefig(REVIEW / 'http_wait_worker_progress.png', dpi=180)
fig.savefig(REVIEW / 'http_wait_worker_progress.pdf')
provenance = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [Path(__file__), REVIEW/'summary.json', attempt/'trace_requests.json',
                        attempt/'server_metrics.json', BASE/'go_runtime_sources.tar',
                        *(BASE/'go_source/runtime').glob('*.go')]}
(REVIEW/'illustration_source_hashes.json').write_text(json.dumps(provenance, indent=2)+'\n')
print(REVIEW/'http_wait_worker_progress.png')
