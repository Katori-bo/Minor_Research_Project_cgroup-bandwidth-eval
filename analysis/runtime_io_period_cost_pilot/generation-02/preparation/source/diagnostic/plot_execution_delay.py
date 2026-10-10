#!/usr/bin/env python3
"""V20 block factorial effects and offered burst profiles, not request inference."""
import csv
import json
from pathlib import Path
import statistics as st
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(out):
    report = json.loads((out/'report.json').read_text())
    with (out/'phases.csv').open() as f:
        phases = list(csv.DictReader(f))
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig, axes = plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
    labels = [('yield_100','Yield at 100 ms','#246c9c'),('yield_20','Yield at 20 ms','#77aeca'),
              ('period_no_yield','Period, yield off','#c86428'),('period_yield','Period, yield on','#d9a266')]
    for ax, key, scale, ylabel in zip(axes,('gap_mean_relative_reduction','timely_500_delta'),
                                    (100,100),('Whole-cohort mean gap reduction (%)','500 ms success change (pp)')):
        ax.axhline(0,color='black',lw=.7)
        if key=='gap_mean_relative_reduction':
            ax.axhline(25,color='grey',ls=':',label='25% exploratory target')
        for contrast, label, color in labels:
            pairs=report['contrasts'][contrast]['pairs']
            rr=[p for p in pairs if p[key] is not None]
            ax.plot([p['block'] for p in rr],[scale*p[key] for p in rr],'o-',color=color,label=label)
        ax.set(xticks=range(1,5),xlabel='Independent block',ylabel=ylabel)
        ax.legend(fontsize=8)
    fig.suptitle('V20: '+report['decision'].replace('_',' '),fontsize=11)
    for ext in ('png','svg'):
        fig.savefig(out/('factorial_effects.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for ax, field, scale, ylabel in zip(axes.flat,
            ('timely_500_fraction','queue_ns_mean','processing_wall_ns_mean','completion_to_resume_ns_mean'),
            (100,1e-6,1e-6,1e-6),('Timely by 500 ms (%)','Mean queue (ms)',
             'Mean computation wall time (ms)','Mean observed completion-to-resume (ms)')):
        ax.axvspan(-.5,4.5,color='#bed9e2',alpha=.25)
        ax.axvspan(4.5,9.5,color='#eac9a9',alpha=.25)
        for arm, color in [('A','#246c9c'),('B','#77aeca'),('C','#c86428'),('D','#d9a266')]:
            for block in range(1,5):
                rr=sorted([r for r in phases if r['grouping']=='second' and r['arm']==arm and int(r['block'])==block],key=lambda r:int(r['value']))
                ax.plot([int(r['value']) for r in rr if r[field]],
                        [float(r[field])*scale for r in rr if r[field]],color=color,alpha=.3)
            medians=[]
            for second in range(10):
                values=[float(r[field])*scale for r in phases if r['grouping']=='second'
                    and r['arm']==arm and int(r['value'])==second and r[field]]
                medians.append(st.median(values) if values else float('nan'))
            ax.plot(range(10),medians,color=color,lw=2.5,label=arm+' trial median')
        ax.set(xlim=(-.5,9.5),xticks=range(10),xlabel='Offered second in burst cycle',ylabel=ylabel)
        ax.legend(fontsize=8)
    fig.suptitle('V20 offered cohorts. A/B: 100 ms; C/D: 20 ms. B/D yield. Unknown stage timings excluded and counted in exports.',fontsize=10)
    for ext in ('png','svg'):
        fig.savefig(out/('burst_stages.'+ext),dpi=180,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':
    main(Path(sys.argv[1]))
