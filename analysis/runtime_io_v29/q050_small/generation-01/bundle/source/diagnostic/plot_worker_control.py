#!/usr/bin/env python3
"""Static V19 block and offered-burst summaries. No request independence implied."""
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
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(9, 4.5), layout='constrained')
    blocks = [b for b in report['blocks'] if b['complete']]
    ax.axhspan(-1, 1, color='grey', alpha=.12, label='A/B ±1 pp tolerance')
    ax.axhline(3, color='#5b8367', ls=':', label='3 pp discovery target')
    ax.axhline(0, color='black', lw=.7)
    for field, color, label in [('aa', '#777777', 'Identical four_b − four_a'),
                              ('one_vs_mean', '#246c9c', 'One − mean(four_a, four_b)')]:
        ax.plot([b['block'] for b in blocks], [100*b[field]['timely_500_delta'] for b in blocks],
                'o-', color=color, label=label)
    ax.set(xticks=range(1, 7), xlabel='Independent block', ylabel='500 ms timely-success change (percentage points)',
           title='V19: '+report['decision'].replace('_', ' '))
    ax.legend(fontsize=9)
    for ext in ('png', 'svg'):
        fig.savefig(out/('block_effects.'+ext), dpi=180, bbox_inches='tight')
    plt.close(fig)
    colors = {'four_a': '#246c9c', 'four_b': '#77aeca', 'one': '#c86428'}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for ax, field, scale, label in zip(axes.flat,
            ('timely_500_fraction', 'queue_ns_mean', 'processing_wall_ns_mean', 'completion_to_resume_ns_mean'),
            (100, 1e-6, 1e-6, 1e-6),
            ('Timely by 500 ms (%)', 'Mean queue (ms)', 'Mean computation wall time (ms)', 'Mean completion-to-resume (ms)')):
        ax.axvspan(-.5, 4.5, color='#bed9e2', alpha=.25)
        ax.axvspan(4.5, 9.5, color='#eac9a9', alpha=.25)
        for arm, color in colors.items():
            for block in range(1, 7):
                rr = sorted([r for r in phases if r['grouping'] == 'second' and r['arm'] == arm and int(r['block']) == block],
                            key=lambda r: int(r['value']))
                ax.plot([int(r['value']) for r in rr if r[field]], [float(r[field])*scale for r in rr if r[field]], color=color, alpha=.3)
            medians = []
            for second in range(10):
                v = [float(r[field])*scale for r in phases if r['grouping'] == 'second' and r['arm'] == arm and int(r['value']) == second and r[field]]
                medians.append(st.median(v) if v else float('nan'))
            ax.plot(range(10), medians, color=color, lw=2.5, label=arm+' trial median')
        ax.set(xlim=(-.5, 9.5), xticks=range(10), xlabel='Offered second within burst cycle', ylabel=label)
        ax.legend(fontsize=8)
    fig.suptitle('V19 offered-arrival cohorts; requests are dependent. Low offers blue, high offers tan.')
    for ext in ('png', 'svg'):
        fig.savefig(out/('burst_stages.'+ext), dpi=180, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    main(Path(sys.argv[1]))
