"""Plot saved post-hoc audit statistics; no performance collection."""
import csv
import hashlib
import json
from pathlib import Path
import statistics as st

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
summary = json.loads((OUT/'summary.json').read_text())
stages = list(csv.DictReader((OUT/'stage_cohorts.csv').open()))
colors = {2: '#be6333', 1: '#187d76'}
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(2, 2, figsize=(11.6, 8.0), layout='constrained')
fig.suptitle('Lower parallelism improves the tail, with a burst-dependent median cost', fontsize=15)
for ax, ph, title in [(axes[0,0], 'all', 'A. Overall successful-request median'),
                      (axes[0,1], 'high', 'B. High-phase median: one pair improves')]:
    for b in range(1,5):
        p = next(p for p in summary['pairs'] if p['block']==b and p['phase']==ph)
        y = [p['p50_g2_ms'], p['p50_g1_ms']]
        ax.plot([2,1], y, color='#9aa4ae', linewidth=1.2)
        for g, v in zip((2,1), y):
            ax.scatter(g, v, color=colors[g], s=45, zorder=3)
        ax.annotate(f'Pair {b}', (2,y[0]), xytext=(7,[-9,12,-13,3][b-1]), textcoords='offset points', fontsize=8)
    ax.set(title=title, ylabel='Latency (ms)', xlim=(2.5,.65), ylim=(0,650))
    ax.set_xticks([2,1], ['GOMAXPROCS=2','GOMAXPROCS=1'])
    ax.grid(axis='y', alpha=.2)
ax = axes[1,0]
ax.axvspan(0,5,color='#e3ebf1',alpha=.6)
ax.axvspan(5,10,color='#f5e7d6',alpha=.6)
for g in (2,1):
    ts=[t for t in summary['trials'] if t['gomaxprocs']==g]
    ys=[st.median(t['buckets'][k]['success_e2e']['p50_ms'] for t in ts) for k in range(10)]
    lo=[min(t['buckets'][k]['success_e2e']['p50_ms'] for t in ts) for k in range(10)]
    hi=[max(t['buckets'][k]['success_e2e']['p50_ms'] for t in ts) for k in range(10)]
    ax.plot([k+.5 for k in range(10)],ys,color=colors[g],label=f'GOMAXPROCS={g}',marker='o',markersize=4)
    ax.fill_between([k+.5 for k in range(10)],lo,hi,color=colors[g],alpha=.12)
ax.text(2.5,780,'LOW',ha='center',color='#526474')
ax.text(7.5,880,'HIGH',ha='center',color='#8b673d')
ax.set(title='C. Median by scheduled second in the burst cycle',xlabel='Scheduled time within 10-second cycle (s)',
       ylabel='Successful-request median (ms)',xlim=(0,10),ylim=(0,950))
ax.legend(loc='upper left',fontsize=8)
ax.grid(axis='y',alpha=.2)
ax = axes[1,1]
components=[('entry_upper_mean_ms','Before handler entry','#688fa8'),
            ('queue_mean_ms','Application queue','#cf9952'),
            ('processing_mean_ms','Worker span (wall time)','#908db8'),
            ('post_mean_ms','Work done → handler resume','#55a394')]
for i,g in enumerate((2,1)):
    rs=[r for r in stages if r['phase']=='all' and r['cohort']=='median_rank_45_to_55_percent'
        and r['run_id'].endswith(f'_g{g}')]
    left=0
    for key,label,color in components:
        v=st.mean(float(r[key]) for r in rs)
        ax.barh(i,v,left=left,color=color,label=label if i==0 else None)
        if v>30:ax.text(left+v/2,i,f'{v:.0f}',ha='center',va='center',color='white',fontsize=9)
        left+=v
    other=st.mean(float(r['pre_mean_ms'])+float(r['response_lower_mean_ms']) for r in rs)
    ax.barh(i,other,left=left,color='#777777')
    ax.text(left+other+5,i,f'{left+other:.0f} ms',va='center',fontsize=9)
ax.set(title='D. Same-request stages near each trial’s median',xlabel='Mean duration (ms); trial means weighted equally',xlim=(0,420))
ax.set_yticks([0,1],['GOMAXPROCS=2','GOMAXPROCS=1'])
ax.set_ylim(2.1,-.5)
ax.legend(loc='lower left',fontsize=7.5)
fig.supxlabel('Post-hoc description of four trial pairs. Phases use scheduled arrivals. C: band = trial min–max.\n'
               'D: success ranks 45–55%; sums are cohort means, not sums of percentiles. Clock bounds retained in audit.',fontsize=9)
fig.savefig(OUT/'tradeoff.png',dpi=180)
fig.savefig(OUT/'tradeoff.pdf')
plt.close(fig)
(OUT/'figure_provenance.json').write_text(json.dumps({str(p.name):hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (Path(__file__),OUT/'summary.json',OUT/'stage_cohorts.csv',OUT/'tradeoff.png',OUT/'tradeoff.pdf')},indent=2)+'\n')
print(OUT/'tradeoff.png')
