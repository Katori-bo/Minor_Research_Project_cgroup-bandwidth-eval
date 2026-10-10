"""V16 discovery comparisons; identical-image variability gates rebuild attribution."""
import math
import statistics

import completion_analysis as boundaries

ARMS = ('legacy_a', 'legacy_b', 'exact_rebuild')
BLOCKS = 4
CONTRASTS = (('legacy_a', 'legacy_b', 'same_image'),
             ('legacy_a', 'exact_rebuild', 'rebuild_vs_a'),
             ('legacy_b', 'exact_rebuild', 'rebuild_vs_b'))
METRICS = ('timely_fraction_delta', 'timely_1000_fraction_delta',
           'failure_fraction_delta', 'cpu_ratio', 'p99_ratio')


def validate_state(server, arm):
    if arm not in ARMS:
        raise ValueError('unknown repeatability arm')
    if server['runtime_variant'] != 'stock' or any(server[k] for k in
            ('runtime_capture', 'custom_recording', 'worker_yield')):
        raise ValueError('runtime tracing, patch or yielding enabled')
    if server.get('entry_protocol') != 'all-outcomes-v1':
        raise ValueError('original entry accounting absent')
    if any(server.get(k) for k in ('marker_protocol', 'ablation_protocol',
            'completion_protocol', 'completion_events')):
        raise ValueError('baseline contains added observer metadata/records')


def classify(client, server, arm):
    validate_state(server, arm)
    result = boundaries.classify(client, server, 'legacy')
    result['arm'] = arm
    return result


def compare(rows):
    cells = {(r['rep'], r['recorder_arm']): r for r in rows}
    if len(rows) != BLOCKS * len(ARMS) or len(cells) != len(rows) or set(cells) != {
            (b, a) for b in range(1, BLOCKS + 1) for a in ARMS}:
        raise ValueError('four complete three-arm blocks required')
    margins = boundaries.MARGINS.copy()
    contrasts = {}
    for base, arm, label in CONTRASTS:
        pairs = []
        for block in range(1, BLOCKS + 1):
            a, z = cells[block, base], cells[block, arm]
            def ratio(key):
                x, y = a[key], z[key]
                return y / x if x is not None and y is not None and x > 0 and y > 0 else None
            pair = dict(block=block,
                timely_fraction_delta=z['timely_500_fraction'] - a['timely_500_fraction'],
                timely_1000_fraction_delta=z['timely_1000_fraction'] - a['timely_1000_fraction'],
                failure_fraction_delta=z['failure_fraction'] - a['failure_fraction'],
                cpu_ratio=ratio('cpu_usec_per_completed_work'), p99_ratio=ratio('p99_e2e_ms'))
            pair['within_screen'] = all(pair[k] is not None and math.isfinite(pair[k]) for k in METRICS) and (
                abs(pair['timely_fraction_delta']) <= margins['timely_fraction'] and
                abs(pair['timely_1000_fraction_delta']) <= margins['timely_fraction'] and
                abs(pair['failure_fraction_delta']) <= margins['failure_fraction'] and
                abs(pair['cpu_ratio'] - 1) <= margins['cpu_ratio'] and
                abs(pair['p99_ratio'] - 1) <= margins['p99_ratio'])
            pairs.append(pair)
        summary = {}
        for key in METRICS:
            values = [p[key] for p in pairs]
            summary[key] = dict(median=statistics.median(values), minimum=min(values), maximum=max(values),
                sample_sd=statistics.stdev(values)) if all(v is not None and math.isfinite(v) for v in values) else None
        contrasts[label] = dict(base=base, arm=arm, pairs=pairs, block_summary=summary,
            within_screen=all(p['within_screen'] for p in pairs))
    aa = contrasts['same_image']['within_screen']
    rebuild = all(contrasts[k]['within_screen'] for k in ('rebuild_vs_a', 'rebuild_vs_b'))
    decision = ('same_image_variability_requires_review' if not aa else
        'exact_source_rebuild_difference_requires_review' if not rebuild else
        'baseline_discovery_screen_within_margins_requires_review')
    return dict(margins=margins, contrasts=contrasts, decision=decision,
        same_image_within_screen=aa, rebuild_within_screen=rebuild,
        rebuild_attribution_resolved=False, rebuild_comparison_interpretable=aa,
        eligible_for_controls=False, eligible_for_persistent_recording=False,
        limitation='Four discovery blocks describe repeatability; passing practical margins does not '
        'prove equivalence. A/A failure prevents rebuild attribution. Full binary identity does not '
        'prove identical host/runtime state. Manual review and separate recorder qualification remain required.')
