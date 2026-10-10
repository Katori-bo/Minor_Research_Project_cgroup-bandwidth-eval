"""Observer ablation validation and matched-block comparisons, never automatic policy selection."""
from copy import deepcopy
import statistics

import completion_analysis as boundaries

from build_marker import ARMS, COUNTS
BLOCKS=4
CONTRASTS=(('legacy','rebuilt_zero','rebuild_control'),
    ('rebuilt_zero','before_one','one_pre_publication_clock'),
    ('before_one','bracket_two','one_post_publication_clock'),
    ('bracket_two','boundary_five','three_event_boundary_clocks'),
    ('boundary_five','v14_clocks','v14_worker_path_and_order_check_bundle'),
    ('legacy','boundary_five','candidate_marker_screen'))


def validate_state(server,arm):
    if arm not in ARMS:raise ValueError('unknown inline marker arm')
    if server['runtime_variant']!='stock' or server['runtime_capture'] or server['custom_recording'] or server['worker_yield']:
        raise ValueError('runtime observer/patch/yield enabled')
    if server.get('completion_protocol') or server.get('completion_events'):
        raise ValueError('this screen has no persistent publication records')
    if arm=='v14_clocks':
        if server.get('ablation_protocol')!='worker-buffer-ablation-v1' or server.get('ablation_mode')!='clocks' or server.get('observer_pending_records') or server.get('observer_dropped_records'):
            raise ValueError('V14 clocks reference changed')
        if server.get('observer_capacity_per_worker')!=16384 or server.get('marker_protocol'):
            raise ValueError('V14 clocks state changed')
    elif arm=='legacy':
        if server.get('marker_protocol') or server.get('ablation_protocol'):
            raise ValueError('legacy marker state changed')
    elif server.get('marker_protocol')!='inline-clock-screen-v1' or server.get('marker_arm')!=arm or server.get('marker_clock_calls')!=COUNTS[arm] or server.get('ablation_protocol'):
        raise ValueError('inline marker mode/count mismatch')


def classify(client,server,arm):
    validate_state(server,arm)
    result=boundaries.classify(client,server,'legacy')
    result['arm']=arm
    return result


def compare(rows):
    cells={(r['rep'],r['recorder_arm']):r for r in rows}
    if len(rows)!=BLOCKS*len(ARMS) or len(cells)!=len(rows) or set(cells)!={(b,a) for b in range(1,BLOCKS+1) for a in ARMS}:
        raise ValueError('four complete six-arm blocks required')
    contrasts={};margins=boundaries.MARGINS
    for base,arm,label in CONTRASTS:
        pairs=[]
        for b in range(1,BLOCKS+1):
            a,z=cells[b,base],cells[b,arm]
            def ratio(k):return z[k]/a[k] if z[k] is not None and a[k] not in (None,0) else None
            p=dict(block=b,timely_fraction_delta=z['timely_500_fraction']-a['timely_500_fraction'],
                timely_1000_fraction_delta=z['timely_1000_fraction']-a['timely_1000_fraction'],
                failure_fraction_delta=z['failure_fraction']-a['failure_fraction'],cpu_ratio=ratio('cpu_usec_per_completed_work'),
                p99_ratio=ratio('p99_e2e_ms'))
            p['within_screen']=abs(p['timely_fraction_delta'])<=margins['timely_fraction'] and \
                abs(p['timely_1000_fraction_delta'])<=margins['timely_fraction'] and \
                abs(p['failure_fraction_delta'])<=margins['failure_fraction'] and \
                p['cpu_ratio'] is not None and abs(p['cpu_ratio']-1)<=margins['cpu_ratio'] and \
                p['p99_ratio'] is not None and abs(p['p99_ratio']-1)<=margins['p99_ratio']
            pairs.append(p)
        metrics={}
        for k in ('timely_fraction_delta','timely_1000_fraction_delta','failure_fraction_delta','cpu_ratio','p99_ratio'):
            values=[p[k] for p in pairs]
            metrics[k]=dict(median=statistics.median(values),minimum=min(values),maximum=max(values)) if all(v is not None for v in values) else None
        contrasts[label]=dict(base=base,arm=arm,pairs=pairs,block_summary=metrics,within_screen=all(p['within_screen'] for p in pairs))
    ok=contrasts['candidate_marker_screen']['within_screen']
    return dict(margins=margins,contrasts=contrasts,decision='inline_markers_require_recording_qualification' if ok else 'inline_marker_effect_requires_review',
        candidate_within_screen=ok,eligible_for_controls=False,
        limitation='Four discovery blocks; no persistent publication records and no full-recorder qualification. Clock placement, cached origin and compilation are part of the treatments. The V14 contrast is a worker-path/order-check bundle. No automatic controls.')
