#!/usr/bin/env python3
"""Offline interval decomposition for causal planning; sealed inputs stay read-only."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REVIEW = ROOT / 'analysis/runtime_io_v11_decision_probe_review'
SESSION = ROOT / 'results/diagnostic/runtime-io-v11-decision-probe-1/session'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(values):
    ordered = sorted(values)
    if not ordered:
        return None
    return dict(n=len(ordered), **{
        key: ordered[math.ceil(fraction * len(ordered))-1]
        for key, fraction in [('p50', .5), ('p99', .99), ('maximum', 1)]})


def main():
    if (OUT / 'report.md').exists():
        raise ValueError('Use a fresh output directory; preserve prior derived evidence')
    provenance = read(REVIEW / 'provenance.json')
    inputs = {Path(path): digest for path, digest in provenance['inputs'].items()}
    inputs.update({REVIEW / name: digest for name, digest in provenance['outputs'].items()})
    inputs[REVIEW / 'provenance.json'] = sha(REVIEW / 'provenance.json')
    for path, digest in inputs.items():
        if sha(path) != digest:
            raise ValueError('Reviewed input changed: ' + str(path))
    attribution = read(SESSION / 'analysis/scheduler_attribution.json')
    trial_rows, wait_rows, examples = [], [], []
    for config in read(SESSION / 'matrix.json'):
        if config['probe_mode'] != 'observed':
            continue
        rid = config['run_id']
        candidates = [p for p in inputs if p.name == 'server_metrics.json' and rid in p.parts]
        if len(candidates) != 1:
            raise ValueError('Cannot resolve reviewed raw capture: ' + rid)
        events = read(candidates[0])['scheduler_capture']['events']
        choices = sorted((e for e in events if e['kind'] == 2), key=lambda e: (e['time_ns'], e['sequence']))
        rows = []
        for wait in attribution[rid]['all_matched_waits']:
            selection = wait['final_selection']
            if selection is None:
                raise ValueError('Unmatched final selection')
            before = selection['time_ns'] - wait['wake_ns']
            after = wait['dispatch_ns'] - selection['time_ns']
            marker = wait['handler_mark_ns'] - wait['dispatch_ns']
            if min(before, after, marker) < 0 or before + after != wait['wait_ns']:
                raise ValueError('Invalid causal interval decomposition')
            row = dict(run_id=rid, request_id=wait['request_id'], outcome=wait['outcome'],
                       ready_wait_ns=wait['wait_ns'], wake_to_selection_ns=before,
                       selection_to_dispatch_ns=after, dispatch_to_handler_marker_ns=marker,
                       before_selection_fraction=before/wait['wait_ns'], final_p=selection['p'])
            rows.append(row)
        long = [r for r in rows if r['ready_wait_ns'] >= 1_000_000_000]
        trial_rows.append(dict(run_id=rid, matched=len(rows), long=len(long),
            ready_wait_ns=summary([r['ready_wait_ns'] for r in rows]),
            selection_to_dispatch_ns=summary([r['selection_to_dispatch_ns'] for r in rows]),
            long_selection_to_dispatch_ns=summary([r['selection_to_dispatch_ns'] for r in long]),
            long_dispatch_to_handler_marker_ns=summary([r['dispatch_to_handler_marker_ns'] for r in long]),
            long_min_before_selection_fraction=min(r['before_selection_fraction'] for r in long),
            long_after_selection_over_1ms=sum(r['selection_to_dispatch_ns'] > 1_000_000 for r in long)))
        wait_rows.extend(rows)
        worst = max(attribution[rid]['all_matched_waits'], key=lambda w: w['wait_ns'])
        ahead = [e for e in choices if worst['wake_ns'] < e['time_ns'] < worst['dispatch_ns']
                 and e['sequence'] != worst['final_selection']['sequence']]
        per_p = []
        for pid in sorted({e['p'] for e in ahead}):
            local = [e for e in ahead if e['p'] == pid]
            tick_delta = (local[-1]['schedtick']-local[0]['schedtick']) % (1 << 32)
            if tick_delta > len(local):
                raise ValueError('Unresolved tick progression')
            per_p.append(dict(p=pid, choices=len(local), inherited=sum(e['inherit'] for e in local),
                first_tick=local[0]['schedtick'], last_tick=local[-1]['schedtick'],
                tick_progress_between_first_last=tick_delta,
                periodic_global_choices=sum(e['source'] == 3 and not e['fair'] for e in local),
                forced_choices=sum(e['fair'] for e in local)))
        examples.append(dict(run_id=rid, request_id=worst['request_id'], g=worst['g'],
            ready_wait_ns=worst['wait_ns'], final_source=worst['final_selection_source'],
            other_choices=len(ahead), per_p=per_p))
    result = dict(trials=trial_rows, longest_per_trial=examples,
        matched=sum(t['matched'] for t in trial_rows), long=sum(t['long'] for t in trial_rows),
        long_after_selection_over_1ms=sum(t['long_after_selection_over_1ms'] for t in trial_rows),
        all_selection_to_dispatch_ns=summary([r['selection_to_dispatch_ns'] for r in wait_rows]),
        maximum_long_selection_to_dispatch_ns=max(r['selection_to_dispatch_ns'] for r in wait_rows if r['ready_wait_ns'] >= 1_000_000_000),
        minimum_long_before_selection_fraction=min(r['before_selection_fraction'] for r in wait_rows if r['ready_wait_ns'] >= 1_000_000_000))
    (OUT / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    with (OUT / 'waits.csv').open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(wait_rows[0]))
        writer.writeheader()
        writer.writerows(wait_rows)
    lines = ['# V11 interval decomposition for causal planning', '',
        'Offline analysis of the reviewed, hash-checked raw captures. No workload was launched.', '',
        '## What can be eliminated for the linked long-wait cohort', '',
        f'Of {result["matched"]:,} matched pre-handler network-ready waits, {result["long"]} last at least one second. '
        f'The largest final-selection-to-dispatch interval among these long waits is '
        f'{result["maximum_long_selection_to_dispatch_ns"]/1e6:.6f} ms. '
        f'At least {100*result["minimum_long_before_selection_fraction"]:.6f}% of each long wait occurs '
        'before the final selection observation. This narrows the explanation: seconds spent between '
        'the final selection hook and the dispatch hook do not explain this cohort.', '',
        '| Trial | Matched waits | Waits >=1s | Selection-to-dispatch p99, all (ms) | Selection-to-dispatch maximum, long (ms) | Dispatch-to-handler-marker maximum, long (ms) |',
        '|---|---:|---:|---:|---:|---:|']
    for t in trial_rows:
        lines.append(f'| {t["run_id"]} | {t["matched"]} | {t["long"]} | '
            f'{t["selection_to_dispatch_ns"]["p99"]/1e6:.6f} | '
            f'{t["long_selection_to_dispatch_ns"]["maximum"]/1e6:.6f} | '
            f'{t["long_dispatch_to_handler_marker_ns"]["maximum"]/1e6:.6f} |')
    lines += ['', '## Scheduling opportunities during each trial\'s longest linked wait', '',
        '| Trial / request | P | Other selections | Inherited selections | Tick progress between first/last choice | Periodic global choices | Forced choices |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for e in examples:
        for p in e['per_p']:
            lines.append(f'| {e["run_id"]} / {e["request_id"]} | {p["p"]} | {p["choices"]} | '
                f'{p["inherited"]} | {p["tick_progress_between_first_last"]} | '
                f'{p["periodic_global_choices"]} | {p["forced_choices"]} |')
    lines += ['', '## Limits', '',
        'Wake hooks observe a state transition and can precede queue publication. Final selection hooks '
        'observe a findRunnable return and can follow queue removal. Consequently wake-to-selection '
        'includes scheduling, admission/publication, OS descheduling and quota effects; it is not exact '
        'queue residence. Dispatch is a runtime state observation before machine-code execution. '
        'A small selection-to-dispatch interval does not exclude OS throttling before selection or '
        'after dispatch. The handler marker can follow another CPU pause.', '',
        'Per-P tick progress covers the first through last other selections, not the entire wait; '
        'periodic global counts record successful choices, not unsuccessful checks. Queue location is '
        'still unknown. Cohort members can overlap and are not independent experimental repetitions. '
        'No causal CPU-time partition or source of a preemption signal is inferred.', '']
    (OUT / 'report.md').write_text('\n'.join(lines))
    for path, digest in inputs.items():
        if sha(path) != digest:
            raise ValueError('Input changed during analysis: ' + str(path))
    (OUT / 'provenance.json').write_text(json.dumps(dict(
        inputs={str(p):d for p,d in inputs.items()}, source={str(Path(__file__)):sha(Path(__file__))},
        outputs={name:sha(OUT / name) for name in ('summary.json', 'waits.csv', 'report.md')}), indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
