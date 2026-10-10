"""Observer ablation validation and matched-block comparisons, never automatic policy selection."""
from copy import deepcopy
import statistics

import completion_analysis as boundaries

ARMS=('legacy','clocks','passive','mutex_early','mutex_late','v13')
BLOCKS=8
CONTRASTS=(('legacy','clocks','clock_calls_and_worker_path'),
    ('clocks','passive','buffer_allocation_and_record_commit'),
    ('passive','mutex_early','post_publication_mutex'),
    ('mutex_early','mutex_late','counter_placement'),
    ('mutex_late','v13','v13_layout_validation_and_path_bundle'),
    ('legacy','passive','candidate_observer_qualification'),
    ('legacy','v13','observer_effect_replication'))


def validate_state(server,arm):
    if arm not in ARMS:raise ValueError('unknown ablation arm')
    if server['runtime_variant']!='stock' or server['runtime_capture'] or server['custom_recording'] or server['worker_yield']:
        raise ValueError('runtime observer/patch/yield enabled')
    if arm=='legacy':
        if server.get('completion_protocol') or server.get('ablation_protocol'):raise ValueError('legacy observer changed')
    elif arm=='v13':
        if server.get('completion_protocol')!='publication-brackets-v1' or server.get('recorder_mode')!='locked' or server['record_errors']:
            raise ValueError('V13 reference differs')
    else:
        if server.get('ablation_protocol')!='worker-buffer-ablation-v1' or server.get('ablation_mode')!=arm:
            raise ValueError('ablation mode/protocol mismatch')
        if server.get('observer_dropped_records') or server.get('observer_pending_records'):
            raise ValueError('observer dropped/pending records')
        if server.get('observer_capacity_per_worker')!=16384:raise ValueError('observer capacity changed')


def classify(client,server,arm):
    validate_state(server,arm)
    # Reuse the qualified all-offered/bounded-clock join without modifying the
    # stored raw schema. Missing markers in clocks-only are never invented.
    normalized=deepcopy(server)
    if arm in ('legacy','clocks'):
        if arm=='clocks' and normalized.get('completion_events'):raise ValueError('clocks-only unexpectedly stores records')
        base='legacy'
    elif arm=='v13':base='locked'
    else:
        normalized.update(completion_protocol='publication-brackets-v1',recorder_mode='locked',record_errors=0,
            record_capacity=client['total_scheduled'])
        base='locked'
    result=boundaries.classify(client,normalized,base);result['arm']=arm
    return result


def compare(rows):
    cells={(r['rep'],r['recorder_arm']):r for r in rows}
    if len(rows)!=BLOCKS*len(ARMS) or len(cells)!=len(rows) or set(cells)!={(b,a) for b in range(1,BLOCKS+1) for a in ARMS}:
        raise ValueError('eight complete six-arm blocks required')
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
    ok=contrasts['candidate_observer_qualification']['within_screen']
    return dict(margins=margins,contrasts=contrasts,decision='passive_candidate_requires_manual_review' if ok else 'observer_requires_further_repair',
        candidate_within_screen=ok,eligible_for_controls=False,
        limitation='Eight discovery blocks; practical screens do not prove equivalence. No automatic next study. Adjacent contrasts isolate stated changes within this path; V13 bundle includes multiple remaining differences.')
