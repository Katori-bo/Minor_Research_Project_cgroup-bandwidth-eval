"""Four-cell image/loading discovery screen; no automatic qualification."""
import math
import statistics
import completion_analysis as boundaries
import repeatability_analysis as baseline

ARMS = ('legacy_packaged', 'rebuilt_packaged', 'legacy_shared', 'rebuilt_shared')
MODES = dict(zip(ARMS, ('packaged', 'packaged', 'shared', 'shared')))
BLOCKS = 4
CONTRASTS = (('legacy_packaged', 'rebuilt_packaged', 'packaged_image_gap'),
    ('legacy_shared', 'rebuilt_shared', 'shared_image_gap'),
    ('legacy_packaged', 'legacy_shared', 'mount_in_legacy'),
    ('rebuilt_packaged', 'rebuilt_shared', 'mount_in_rebuilt'))


def validate_state(server, arm):
    if arm not in ARMS: raise ValueError('unknown loading arm')
    baseline.validate_state(server, 'legacy_a')


def classify(client, server, arm):
    validate_state(server, arm)
    result = boundaries.classify(client, server, 'legacy')
    result['arm'] = arm
    return result


def summarize(pairs):
    result = {}
    for key in baseline.METRICS:
        values = [p[key] for p in pairs]
        result[key] = dict(median=statistics.median(values), minimum=min(values), maximum=max(values),
            sample_sd=statistics.stdev(values)) if all(x is not None and math.isfinite(x) for x in values) else None
    return result


def compare(rows):
    cells = {(r['rep'], r['recorder_arm']): r for r in rows}
    if len(rows) != 16 or len(cells) != 16 or set(cells) != {(b, a) for b in range(1, 5) for a in ARMS}:
        raise ValueError('four complete four-arm blocks required')
    margins = boundaries.MARGINS.copy()
    contrasts = {}
    for base, arm, label in CONTRASTS:
        pairs = []
        for b in range(1, 5):
            a, z = cells[b, base], cells[b, arm]
            def ratio(key):
                x, y = a[key], z[key]
                return y / x if x is not None and y is not None and x > 0 and y > 0 else None
            p = dict(block=b, timely_fraction_delta=z['timely_500_fraction'] - a['timely_500_fraction'],
                timely_1000_fraction_delta=z['timely_1000_fraction'] - a['timely_1000_fraction'],
                failure_fraction_delta=z['failure_fraction'] - a['failure_fraction'],
                cpu_ratio=ratio('cpu_usec_per_completed_work'), p99_ratio=ratio('p99_e2e_ms'))
            p['within_screen'] = all(p[k] is not None and math.isfinite(p[k]) for k in baseline.METRICS) and (
                abs(p['timely_fraction_delta']) <= margins['timely_fraction'] and
                abs(p['timely_1000_fraction_delta']) <= margins['timely_fraction'] and
                abs(p['failure_fraction_delta']) <= margins['failure_fraction'] and
                abs(p['cpu_ratio'] - 1) <= margins['cpu_ratio'] and abs(p['p99_ratio'] - 1) <= margins['p99_ratio'])
            pairs.append(p)
        contrasts[label] = dict(base=base, arm=arm, pairs=pairs, block_summary=summarize(pairs),
            within_screen=all(p['within_screen'] for p in pairs))
    interactions = []
    for a, z in zip(contrasts['packaged_image_gap']['pairs'], contrasts['shared_image_gap']['pairs']):
        p = dict(block=a['block'])
        for k in baseline.METRICS:
            if a[k] is None or z[k] is None:
                p[k] = None
            else:
                p[k] = z[k] / a[k] if k.endswith('_ratio') else z[k] - a[k]
        interactions.append(p)
    packaged = contrasts['packaged_image_gap']['pairs']
    # Reproduction of V16's predicted direction, not a selected post-result sign.
    reproduced = all(math.isfinite(p['timely_fraction_delta']) and
        p['timely_fraction_delta'] > margins['timely_fraction'] and
        all(p[k] is not None and math.isfinite(p[k]) for k in baseline.METRICS) for p in packaged)
    shared = contrasts['shared_image_gap']['within_screen']
    decision = ('packaged_gap_not_reproduced_requires_review' if not reproduced else
        'shared_file_gap_within_margins_requires_review' if shared else
        'shared_file_did_not_establish_neutrality')
    return dict(margins=margins, contrasts=contrasts,
        loading_interaction=dict(pairs=interactions, block_summary=summarize(interactions),
            definition='shared image contrast minus packaged image contrast; ratios are ratios of ratios'),
        packaged_v16_direction_reproduced=reproduced, shared_image_within_screen=shared,
        decision=decision, eligible_for_controls=False, eligible_for_persistent_recording=False,
        limitation='Four discovery blocks cannot establish equivalence or a filesystem/cache/scheduler cause. '
        'Shared loading changes the backing file and mount setup together. Startup qualification is common '
        'to all arms. A missing packaged gap prevents claiming the common file removed it. No automatic next study.')
