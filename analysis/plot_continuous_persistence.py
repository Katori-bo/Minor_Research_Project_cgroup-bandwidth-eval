#!/usr/bin/env python3
"""Diagnostic figure for the frozen persistence replay; no prediction fitting."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import screen_continuous_persistence as screen
import screen_forecast_reliability as e

ROOT=Path(__file__).resolve().parents[1]
OUT=screen.OUT


def main():
    report=e.read(OUT/'screen.json')
    seal=e.read(OUT/'seal.json')
    for path,digest in seal.items():
        e.require(e.sha(ROOT/path)==digest,'Persistence package changed: '+path)
    base=ROOT/'analysis/runtime_io_nginx_power_confirmation/generation-01/campaign'
    case=base/'validation/cohort-23'
    cfg=e.sealed_read(case/'study-config.json',base,'evidence-seal.json')
    _,records=screen.read_client(base,case,cfg,'measurement')
    bins=[100*screen.count(records[i:i+50],report['campaigns'][1]['deadline_ns'])/50
          for i in range(0,300,50)]
    row=next(r for r in report['campaigns'][1]['rows'] if r['name']=='cohort-23')
    e.close(sum(bins[:2])/2,row['forecast']['predictions']['recent100']['miss_pct'])
    e.close(sum(bins[2:])/4,row['observed_target_miss_pct'])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'white'})
    fig,axes=plt.subplots(1,2,figsize=(12,4.7),gridspec_kw={'width_ratios':[1,1.1]})
    colors=['#506278','#217a70','#d58a29']
    labels=['Original calibration','Recent 100','Weighted update']
    for i,(method,label,color) in enumerate(zip(['original','recent100','sample_weighted_update'],labels,colors)):
        axes[0].bar([j+(i-1)*.24 for j in range(3)],
                    [c['methods'][method]['mae_pp'] for c in report['campaigns']],width=.22,label=label,color=color)
    axes[0].set_xticks(range(3),['Original study','Power study','Rate study'])
    axes[0].set_ylabel('Mean absolute error (percentage points)')
    axes[0].set_title('Better average accuracy is uneven',loc='left',fontweight='bold',pad=13)
    axes[0].legend(frameon=False,fontsize=9)
    axes[0].grid(axis='y',alpha=.18);axes[0].set_axisbelow(True)
    x=[25,75,125,175,225,275]
    axes[1].axvspan(0,100,color='#217a70',alpha=.09)
    axes[1].axvline(100,color='#526170',linestyle=':',linewidth=1.3)
    axes[1].plot(x,bins,'o-',color='#217a70',linewidth=2,markersize=6,label='Observed in each 50-offer bin')
    axes[1].hlines(row['forecast']['predictions']['recent100']['miss_pct'],100,300,
                   color='#d58a29',linestyle='--',linewidth=2,label='Probe forecast: 48%')
    axes[1].hlines(row['observed_target_miss_pct'],100,300,color='#506278',linewidth=1.6,
                   label='Next 200 observed: 79.5%')
    axes[1].set_title('An agreeing probe misses a later excursion',loc='left',fontweight='bold',pad=13)
    axes[1].set_xlabel('Scheduled offer number')
    axes[1].set_ylabel('Deadline misses (%)')
    axes[1].set_xlim(0,300);axes[1].set_ylim(0,100)
    axes[1].text(50,94,'Probe: 100',ha='center',fontsize=9)
    axes[1].text(200,94,'Target: 200',ha='center',fontsize=9)
    axes[1].legend(frameon=False,fontsize=8.5,loc='lower left')
    axes[1].grid(axis='y',alpha=.18)
    fig.suptitle('Continuous NGINX profiling at a fixed 20.565395 ms deadline',fontsize=14,fontweight='bold',x=.07,ha='left')
    fig.text(.07,.025,'Known development data. Right: power cohort 23, P0, 8/s; selected after scoring for diagnosis. No causal inference.',fontsize=9,color='#526170')
    fig.tight_layout(rect=[0,.055,1,.93])
    fig.savefig(OUT/'persistence.png',dpi=180)
    plt.close(fig)
    diagnostic=dict(role='postscore diagnostic only',selected_case='NGINX power cohort-23',
                    fixed_50offer_bin_miss_pct=bins,inputs_sha256=e.INPUTS,
                    figure_sha256=e.sha(OUT/'persistence.png'),script_sha256=e.sha(Path(__file__)))
    e.save(OUT/'figure_audit.json',diagnostic)
    print('Figure and selected-case bin reconciliation saved:',OUT/'persistence.png')


if __name__=='__main__':main()
