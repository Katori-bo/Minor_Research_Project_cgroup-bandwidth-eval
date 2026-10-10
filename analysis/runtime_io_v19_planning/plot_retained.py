#!/usr/bin/env python3
"""Static exploratory figures; trial lines expose variation rather than hide it."""
from pathlib import Path
import csv
import json
import statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / 'offline-20261004'
DATA = json.loads((OUT / 'analysis.json').read_text())
COLORS = {'off': '#246c9c', 'on': '#c86428'}
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 130, 'savefig.dpi': 180})


def rows(name):
    with (OUT / (name + '.csv')).open() as f:
        return list(csv.DictReader(f))


def save(fig, name):
    fig.savefig(OUT / (name + '.png'), bbox_inches='tight')
    fig.savefig(OUT / (name + '.svg'), bbox_inches='tight')
    plt.close(fig)


def main():
    cdf = rows('deadline_cdf')
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout='constrained')
    for pair in range(1, 7):
        subsets = {a: sorted([r for r in cdf if int(r['pair']) == pair and r['arm'] == a],
                            key=lambda r: float(r['threshold_ms'])) for a in ('off', 'on')}
        for arm, rr in subsets.items():
            axes[0].plot([float(r['threshold_ms']) for r in rr], [float(r['timely_pct']) for r in rr],
                         color=COLORS[arm], alpha=.38, label=arm if pair == 1 else None)
        axes[1].plot([float(r['threshold_ms']) for r in subsets['off']],
            [float(b['timely_pct']) - float(a['timely_pct']) for a, b in zip(subsets['off'], subsets['on'])], label=f'Pair {pair}')
    for ax in axes:
        ax.axvline(500, color='black', ls=':', lw=1)
        ax.set_xlabel('Scheduled-arrival deadline (ms)')
        ax.set_xlim(250, 1000)
    axes[0].set_ylabel('Timely successful responses / all offers (%)')
    axes[0].set_title('All twelve trials; no failures')
    axes[0].legend()
    axes[1].axhspan(-1, 1, color='#777777', alpha=.12)
    axes[1].axhline(0, color='black', lw=.7)
    axes[1].set_ylabel('On minus off (percentage points)')
    axes[1].set_title('Original 500 ms screen remains failed')
    axes[1].legend(ncol=2, fontsize=8)
    fig.suptitle('V18: deadline sensitivity is exploratory, not a replacement endpoint')
    save(fig, 'deadline_sensitivity')

    seconds = rows('burst_seconds')
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for ax, field, title, ylabel in zip(axes.flat,
        ('timely_500_pct', 'queue_ms_mean', 'processing_wall_ms_mean', 'completion_to_resume_ms_mean'),
        ('500 ms success', 'Queue before computation', 'Computation wall time', 'Computation completion to handler resume'),
        ('Timely success (%)', 'Mean per request (ms)', 'Mean per request (ms)', 'Mean per request (ms)')):
        ax.axvspan(-.5, 4.5, color='#bed9e2', alpha=.25)
        ax.axvspan(4.5, 9.5, color='#eac9a9', alpha=.25)
        for arm in ('off', 'on'):
            for pair in range(1, 7):
                rr = sorted([r for r in seconds if r['arm'] == arm and int(r['pair']) == pair], key=lambda r: int(r['value']))
                ax.plot([int(r['value']) for r in rr], [float(r[field]) for r in rr], color=COLORS[arm], alpha=.3)
            medians = [st.median(float(r[field]) for r in seconds if r['arm'] == arm and int(r['value']) == s) for s in range(10)]
            ax.plot(range(10), medians, color=COLORS[arm], lw=2.5, label=arm + ' trial median')
        ax.set(xlim=(-.5, 9.5), xticks=range(10), xlabel='Offered-arrival second within 10 s burst cycle', ylabel=ylabel, title=title)
        ax.legend(fontsize=8)
    fig.suptitle('V18: blue background = low offers; tan = high offers. Requests remain dependent.')
    save(fig, 'burst_stage_profiles')

    classes = ['computation_after_deadline', 'computation_boundary_ambiguous',
               'computed_before_handler_resumed_after', 'handler_boundary_ambiguous',
               'handler_resumed_before_client_finished_after']
    labels = ['Computation after deadline', 'Computation boundary ambiguous',
              'Computation before; handler after', 'Handler boundary ambiguous',
              'Handler before; client after']
    colors = ['#60758a', '#afbecb', '#c86428', '#edbd92', '#5e9e76']
    fig, ax = plt.subplots(figsize=(10, 4.5), layout='constrained')
    bottom = [0, 0]
    for key, label, color in zip(classes, labels, colors):
        values = [100 * DATA['pooled_by_arm'][a]['deadline_classes'].get(key, 0) / DATA['pooled_by_arm'][a]['offered'] for a in ('off', 'on')]
        ax.bar(['off', 'on'], values, bottom=bottom, color=color, label=label)
        bottom = [a + b for a, b in zip(bottom, values)]
    ax.set(ylabel='500 ms misses / all offers (%)', title='Pooled description; direct bounded clocks')
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=8)
    fig.suptitle('V18 deadline accounting: main computation completion is before publication')
    save(fig, 'deadline_classes')

    wave = rows('completion_waveforms')
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), layout='constrained')
    for arm, ax in zip(('off', 'on'), axes):
        for pair in range(1, 7):
            rr = sorted([r for r in wave if r['arm'] == arm and r['trial'] == f'p{pair}_{arm}'], key=lambda r: int(r['phase_bin_start_ms']))
            ax.plot([int(r['phase_bin_start_ms']) + 2.5 for r in rr], [int(r['count']) for r in rr], label=f'Pair {pair}')
        ax.set(xlabel='Completion-marker time modulo 100 ms relative to offers (ms)',
               ylabel='Completions per 5 ms bin', title=arm + ': descriptive midpoint mapping, not quota origin', xlim=(0, 100))
        ax.legend(ncol=3, fontsize=8)
    fig.suptitle('Periodic completion waveforms vary between trials')
    save(fig, 'completion_waveforms')

    root = Path(__file__).resolve().parents[2]
    historical = [('V16 same image', root / 'results/diagnostic/runtime-io-v16-repeatability-1/session/analysis/repeatability_screen.json', 'same_image'),
                  ('V17 packaged image', root / 'results/diagnostic/runtime-io-v17-shared-loading-1/session/analysis/loading_screen.json', 'packaged_image_gap'),
                  ('V17 shared image', root / 'results/diagnostic/runtime-io-v17-shared-loading-1/session/analysis/loading_screen.json', 'shared_image_gap')]
    fig, ax = plt.subplots(figsize=(9, 4.5), layout='constrained')
    for i, (label, path, contrast) in enumerate(historical):
        rr = json.loads(path.read_text())['contrasts'][contrast]['pairs']
        vals = [r['timely_fraction_delta'] * 100 for r in rr]
        ax.scatter(vals, [i] * len(vals), label=label, s=40)
    ax.scatter([r['timely_500_delta'] * 100 for r in DATA['original_pairs']], [3] * 6, s=40, color=COLORS['on'])
    ax.axvspan(-1, 1, color='#777777', alpha=.12)
    ax.axvline(0, color='black', lw=.7)
    ax.set(yticks=range(4), yticklabels=[r[0] for r in historical] + ['V18 observer on − off'],
           xlabel='Paired 500 ms success difference (percentage points)',
           title='Separate studies and procedures; these points are not pooled replicates')
    save(fig, 'historical_effect_sizes')


if __name__ == '__main__':
    main()
