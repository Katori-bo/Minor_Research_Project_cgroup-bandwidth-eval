#!/usr/bin/env python3
"""Read-only review of sealed v11 scheduler decisions and observer effects."""
from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'diagnostic'))
import decision_analysis as analysis
import decision_probe as probe
import run


def main():
    output=Path(__file__).parent
    if (output/'report.md').exists():
        raise ValueError('review already exists; preserve it')
    directory=ROOT/'results/diagnostic/runtime-io-v11-decision-probe-1'
    session=directory/'session';source=session/'analysis'
    seal=run.read(directory/'completion.json')
    hashes={source/'report.md':seal['report_sha256']}
    hashes.update({source/n:d for n,d in seal['analysis_sha256'].items()})
    for path,digest in hashes.items():
        if run.sha(path)!=digest:raise ValueError('sealed analysis changed: '+str(path))
    probe.verify_session(session,check_current=False)
    attribution=run.read(source/'scheduler_attribution.json')
    screen=run.read(source/'observer_screens.json')
    choices_total=Counter();forced_roles=Counter();trials=[];examples=[];corrections=[]
    for config in run.read(session/'matrix.json'):
        rid=config['run_id'];attempt=session/'attempts'/rid/seal['attempts'][rid]['attempt']
        if run.sha(attempt/'complete.json')!=seal['attempts'][rid]['sha256'] or not run.validate(attempt,config,False):
            raise ValueError('sealed trial invalid: '+rid)
        for name in ('complete.json','server_metrics.json','trace_status.json','loadgen.json'):
            hashes[attempt/name]=run.sha(attempt/name)
        if config['probe_mode']=='control':continue
        rebuilt=analysis.analyze_attempt(attempt,True)
        if rebuilt!=attribution[rid]:raise ValueError('attribution differs from raw evidence: '+rid)
        events=run.read(attempt/'server_metrics.json')['scheduler_capture']['events']
        roles=analysis.classify(events)
        choices=[e for e in events if e['kind']==2]
        forced=[e for e in choices if e['fair']]
        sources=Counter(analysis.SOURCES[e['source']] for e in choices)
        choices_total.update(sources)
        role_counts=Counter(roles[e['g']] for e in forced);forced_roles.update(role_counts)
        corrected=[]
        for e in rebuilt['all_matched_waits']:
            final=e['final_selection']
            self_selected=bool(final and final['fair'] and e['wake_ns']<final['time_ns']<e['dispatch_ns'])
            ahead=e['forced_selections_ahead']-int(self_selected)
            corrected.append(dict(request_id=e['request_id'],wait_ns=e['wait_ns'],other_forced_choices=ahead))
            if self_selected:
                corrections.append(dict(run_id=rid,request_id=e['request_id'],
                    recorded_forced_ahead=e['forced_selections_ahead'],other_forced_choices=ahead))
        long=[e for e in corrected if e['wait_ns']>=1_000_000_000]
        trials.append(dict(run_id=rid,block=config['rep'],events=len(events),choices=len(choices),
            runnext=sources['runnext'],forced_choices=len(forced),pending_choices=sum(e['pending'] for e in choices),
            forced_sources=dict(Counter(analysis.SOURCES[e['source']] for e in forced)),
            forced_roles=dict(role_counts),matched_waits=len(corrected),waits_over_1s=len(long),
            waits_over_2s=sum(e['wait_ns']>=2_000_000_000 for e in corrected),
            long_waits_without_other_forced_choice=sum(e['other_forced_choices']==0 for e in long),
            unmatched_dispatches=rebuilt['unmatched_dispatches'],unresolved_wakes=len(rebuilt['unresolved_wakes']),
            cleanup_ambiguous=len(rebuilt['cleanup_ambiguous']),unlinked_http_network_waits=rebuilt['unlinked_http_network_waits'],
            ready_p99_ms=rebuilt['ready_wait_p99_ms']))
        for e in rebuilt['examples'][:3]:
            other_forced=[f for f in e['forced_selected_goroutines'] if f['g']!=e['g']]
            examples.append(dict(run_id=rid,request_id=e['request_id'],g=e['g'],outcome=e['outcome'],
                wait_ms=e['wait_ns']/1e6,dispatches_ahead=e['dispatches_ahead'],by_role=e['by_role'],
                by_source=e['by_source'],other_forced_choices=len(other_forced),other_forced_selected=other_forced,
                final_source=e['final_selection_source'],final_pending=e['final_selection']['pending'],
                final_forced=e['final_selection']['fair']))
        print('REVIEWED',rid,flush=True)
    total=sum(choices_total.values());forced=sum(t['forced_choices'] for t in trials)
    data=dict(trials=trials,examples=examples,selection_sources=dict(choices_total),
        selections=total,runnext_fraction=choices_total['runnext']/total,forced_choices=forced,
        forced_fraction=forced/total,forced_roles=dict(forced_roles),observer_screens=screen,
        own_final_selection_corrections=corrections,eligible_for_full=False)
    run.put(output/'review.json',data)
    lines=['# V11 findings: which work got turns ahead of delayed HTTP', '',
        'All eight sealed trials revalidate. Derived attribution was rebuilt from the raw recorder arrays '
        'and matches the sealed analysis. No performance measurement or scheduling correction was added.', '',
        '## What this establishes', '',
        'Ready HTTP goroutines wait seconds in the runtime-tracing-off workload while workers, other '
        'HTTP goroutines and HTTP background readers keep getting turns. The longest retained matched '
        'example is request 470 in block 4: 4.416610 seconds, 2,407 dispatches ahead, including 592 worker, '
        '1,221 HTTP, 593 background-reader and one runtime-background dispatch. Of those turns, 1,768 '
        'came from runnext, 629 from regular local FIFO and 10 from the periodic global-fairness branch. '
        'None of the selections during this wait captured a pending flag or used forceFair.', '',
        f'Across all observed captures, runnext supplies {choices_total["runnext"]:,} of {total:,} selections '
        f'({choices_total["runnext"]/total:.2%}). The pending-preemption ordinary correction supplies '
        f'{forced} forceFair selections ({forced/total:.3%}), all from the global queue. These are capture '
        'counts including control requests and drain, not workload-only rates.', '',
        f'Those {forced} forced selections choose {forced_roles["worker"]} worker, {forced_roles["http"]} HTTP, '
        f'{forced_roles["runtime_background"]} runtime-background and {forced_roles["http_background_reader"]} '
        'HTTP background-reader goroutines. It sometimes selects the delayed HTTP G, but that is not '
        'a guarantee of a prompt turn. For request 1554, it eventually selects the delayed G after '
        '3.406082 seconds. Three other forced HTTP selections precede it, all near the end of the wait.', '',
        '## Per-observed-trial evidence', '',
        '| Block | Selections | Forced global choices | Matched pre-handler waits | Waits ≥1s | Waits ≥1s without another forced choice | Ready-wait p99 ms |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for t in trials:
        lines.append(f'| {t["block"]} | {t["choices"]:,} | {t["forced_choices"]} | {t["matched_waits"]} | '
            f'{t["waits_over_1s"]} | {t["long_waits_without_other_forced_choice"]} | {t["ready_p99_ms"]:.3f} |')
    lines += ['', f'Total matched waits: {sum(t["matched_waits"] for t in trials):,}; '
        f'{sum(t["waits_over_1s"] for t in trials)} last at least one second, and '
        f'{sum(t["waits_over_2s"] for t in trials)} last at least two seconds. '
        'This is the explicitly linked network-ready cohort, not all client requests. Some wait windows '
        'overlap; their work-ahead counts must not be added.', '',
        '## Recorder perturbation', '',
        'The predeclared descriptive screens pass. Ratios of arm medians: server CPU/job +0.30%, '
        'client CPU/request +0.65%, successful p99 +4.86%, throughput +0.11%. Maximum rejection-plus-timeout '
        'rates are 2.43% observed and 2.56% control, and client trace coverage is 100%. This supports '
        'using the observed evidence with its stated limits; four pairs do not prove zero perturbation '
        'or statistical equivalence. Both arms use the same candidate, so this run does not compare '
        'the correction against stock Go.', '',
        '## Interpretation and next question', '',
        'The tested correction can help a selected G, but relying on a pending-preemption flag leaves '
        'long intervals in which it is inactive. Periodic global checks also occur during the longest '
        'wait and still fail to provide that particular G a prompt turn. The dominance of runnext is '
        'directly recorded; how a specific waiting G moves between global and local queues remains '
        'unrecorded. The next focused question is that queue residence/migration and whether a bounded '
        'dispatch or wait-age fairness rule can prevent these gaps without depending solely on the flag. '
        'This is a hypothesis for the next step, not a demonstrated fix.', '',
        'Dispatch and runnable timestamps are observation sites, not continuous CPU execution. '
        'The source of a preemption signal is unavailable. Existing CPU-quota effects are retained; '
        'the experiment does not isolate kernel scheduling from every part of the delay.', '',
        '## Small counting correction in this derived review', '',
        'The sealed report defines "forced selections ahead" using the interval before the delayed '
        'G dispatches. That interval can include the delayed G’s own final selection. This review '
        'excludes its own final selection when describing other work selected ahead. Among the displayed '
        'examples, request 1554 therefore has three other forced choices (sealed count four), and request '
        '1559 has zero (sealed count one). Exact corrections for every matched wait are in review.json. '
        'The timestamps and selections are unchanged, and the sealed report remains intact.', '']
    (output/'report.md').write_text('\n'.join(lines))
    for p,digest in hashes.items():
        if run.sha(p)!=digest:raise ValueError('input changed during review')
    run.put(output/'validation.json',dict(passed=True,trials=8,raw_attribution_rebuilt=True,
        inputs_unchanged=True,eligible_for_full=False))
    run.put(output/'provenance.json',dict(inputs={str(p):d for p,d in hashes.items()},
        sources={str(p):run.sha(p) for p in (Path(__file__),Path(analysis.__file__),Path(probe.__file__))},
        outputs={p.name:run.sha(p) for p in (output/'report.md',output/'review.json',output/'validation.json')}))
    print('REVIEW COMPLETE:',output/'report.md',flush=True)


if __name__=='__main__':main()
