#!/usr/bin/env python3
"""Read-only review of sealed V13; derived outputs are outside the session."""
import csv
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'diagnostic'))
import completion_study as study
import run

OUT=ROOT/'analysis/runtime_io_v13_observer_review'


def summary(values):
    v=sorted(values)
    if not v: return None
    return dict(count=len(v),p50_ms=v[math.ceil(.5*len(v))-1]/1e6,
        p99_ms=v[math.ceil(.99*len(v))-1]/1e6,max_ms=max(v)/1e6,
        over_1ms=sum(x>1e6 for x in v),over_50ms=sum(x>50e6 for x in v))


def review():
    study.verify_completion(study.DEFAULT)
    session=study.DEFAULT/'session';seal=run.read(study.DEFAULT/'completion.json')
    rows=list(csv.DictReader((session/'analysis/trials.csv').open()))
    primary={c['run_id']:[] for c in run.read(session/'matrix.json')}
    with (session/'analysis/requests.csv').open() as stream:
        for r in csv.DictReader(stream):
            if r['deadline_ms']=='500': primary[r['run_id']].append(r)
    trials=[]
    for c in run.read(session/'matrix.json'):
        attempt=session/'attempts'/c['run_id']/seal['attempts'][c['run_id']]['attempt']
        srv=run.read(attempt/'server_metrics.json');client=run.read(attempt/'loadgen.json')
        settling=run.read(attempt/'settling.json');monitor=run.read(attempt/'monitor.json')
        trial=next(r for r in rows if r['run_id']==c['run_id'])
        detail=dict(run_id=c['run_id'],rep=c['rep'],arm=c['recorder_arm'],offered=client['total_scheduled'],
            timely_500=sum(not q['Error'] and q['StatusCode']==200 and q['EndToEndLatencyNs']<=500_000_000 for q in client['requests']),
            failures=client['total_errors']+client['total_503'],
            late_success_work_before=int(trial['late_success_work_before']),
            cpu_usec_per_completed_work=float(trial['cpu_usec_per_completed_work']),
            p99_e2e_ms=float(trial['p99_e2e_ms']),p99_post_work_ms=float(trial['p99_post_work_ms']),
            clock_uncertainty_ns=int(trial['clock_uncertainty_ns']),
            accepted_settling_means_c={k:v['mean_c'] for k,v in settling['summary']['sensors'].items()},
            monitor_temperature_ranges_c={k:dict(minimum=min(s['temps_c'][k] for s in monitor),
                maximum=max(s['temps_c'][k] for s in monitor)) for k in monitor[0]['temps_c']},
            publication_deadline_classes_for_late_work_before={})
        for r in primary[c['run_id']]:
            if r['outcome']=='success' and r['timely']=='False' and r['deadline_crossing'].startswith('work_before_'):
                key=r['publication_class'];counts=detail['publication_deadline_classes_for_late_work_before']
                counts[key]=counts.get(key,0)+1
        jobs={e['id']:e for e in srv['events']};handlers={h['id']:h for h in srv['handler_events']}
        bs=srv.get('completion_events',[])
        if bs:
            detail['intervals']={k:summary(v) for k,v in dict(
                completion_to_publish_start=[b['publish_start_ns']-jobs[b['id']]['completion_ns'] for b in bs],
                record_lock_wait=[b['record_lock_ns']-b['record_start_ns'] for b in bs],
                record_held=[b['record_end_ns']-b['record_lock_ns'] for b in bs],
                publication_bracket=[b['publish_end_ns']-b['publish_start_ns'] for b in bs],
                publication_to_resume_lower=[max(0,handlers[b['id']]['resume_ns']-b['publish_end_ns']) for b in bs if b['id'] in handlers]
                ).items()}
        trials.append(detail)
    arms={}
    for arm in ('legacy','locked','bounded'):
        group=[r for r in trials if r['arm']==arm]
        arms[arm]={k:sum(r[k] for r in group) for k in ('offered','timely_500','failures','late_success_work_before')}
        arms[arm]['timely_500_fraction']=arms[arm]['timely_500']/arms[arm]['offered']
        arms[arm]['late_work_before_share_of_misses']=arms[arm]['late_success_work_before']/(arms[arm]['offered']-arms[arm]['timely_500'])
    screen=run.read(session/'analysis/observer_screen.json')
    value=dict(completion_seal_sha256=run.sha(study.DEFAULT/'completion.json'),review_script_sha256=run.sha(Path(__file__)),
        sealed_evidence_verified=True,arms=arms,trials=trials,screen=screen)
    OUT.mkdir(exist_ok=True);run.put(OUT/'review.json',value)
    pairs=screen['comparisons']['legacy_to_locked']['pairs']
    loss=[-100*p['timely_fraction_delta'] for p in pairs]
    cpu=[100*(p['cpu_ratio']-1) for p in pairs];tail=[100*(p['p99_ratio']-1) for p in pairs]
    lines=['# V13 observer qualification review — 2026-10-03','',
        '**Technical completion verified; observer qualification failed.** Original session, sources and reports remain sealed. '
        'These derived files live outside the result session.','',
        '| Four-trial arm totals | Offered | Timely at 500 ms | Failures | Late successful response, work certainly before 500 ms |',
        '|---|---:|---:|---:|---:|']
    for arm,g in arms.items():
        lines.append(f'| {arm} | {g["offered"]:,} | {g["timely_500"]:,} ({g["timely_500_fraction"]:.3%}) | {g["failures"]} | {g["late_success_work_before"]:,} |')
    lines+=['',f'Legacy→locked loses {min(loss):.2f}–{max(loss):.2f} percentage points of primary timely success in every block '
        f'(median loss {statistics.median(loss):.2f} points). CPU/job rises {min(cpu):.2f}–{max(cpu):.2f}%; '
        f'successful p99 rises {min(tail):.2f}–{max(tail):.2f}%. CPU alone passes its 5% margin, '
        'but deadline success fails the 1-point margin and p99 fails the 10% margin in every pair. '
        'Zero rejection/timeout/error outcomes does not mean zero deadline misses.','',
        'Locked→bounded passes all declared practical screens in these four pairs. Its 500 ms timely-success change ranges '
        'from −0.90 to +0.65 percentage points, without a consistent benefit. This does not prove equivalence or show '
        'that all application locks are harmless: both arms retain locks and the same new observer.','',
        '## What the new boundaries show, within the affected observer','',
        'In all eight marked trials, completion→publication-start p99 is about 1.1–1.3 microseconds; '
        'publication-bracket p99 is about 1.6–2.3 microseconds. Recorded pre-publication lock-wait p99 is 0.11 microseconds. '
        'Publication→handler-execution lower-bound p99 remains about 161–164 ms. '
        'One bounded request has a roughly 91 ms pre-publication interval; three marked requests have publication brackets '
        'over 50 ms. Those exceptions remain explicit rather than silently treating publication as instantaneous.','',
        'This weakens dynamic event append as the dominant delay explanation in the marked service and localizes most '
        'measured post-computation delay after publication. Because the observer changes external outcomes, '
        'these timings cannot establish the exact mechanism of the legacy service. Wall intervals do not separate '
        'quota pauses from runnable competition. Fewer marked work-before misses also does not mean a remedy: '
        'overall deadline success worsened, so misses can migrate to earlier stages.','',
        '## Implementation ambiguity to isolate next','',
        'The new worker path adds timestamp calls, large fixed slot allocation, ID checks/slot bookkeeping and a second '
        'mutex acquisition after the result send; it moves completion/abandonment counters from before publication '
        'to after marker storage. Legacy→locked tests this combined change. The second lock and changed bookkeeping '
        'are concrete causal candidates, not established causes. I added these to make drain/export conservation explicit; '
        'the qualification experiment now shows their combined measurement cost is too large for the declared objective.','',
        'Next prepare an isolated observer ablation: keep legacy counters/send order and HTTP behavior, then distinguish '
        'timestamp cost from record commit/second-lock cost and slot layout. Design safe record finalization/export/reset '
        'without changing result handoff; retain cancellation and race/conservation checks. Freeze a new protocol/build '
        'and requalify against legacy before using fine-grained marked timings or launching the independent-control matrix. '
        'Do not rebuild or rewrite this completed V13 session, rerun valid trials to obtain a pass, '
        'or attribute the effect solely to clock calls.','',
        '## Temperature and technical validity','',
        'Every accepted trial passed the frozen settling/power/quiet-host and resource checks; accepted settling-window '
        'temperature means span roughly 56.94–60.13°C. The recorded k10temp collection samples span 66.125–75.875°C; '
        'review.json retains all actual monitor temperature ranges separately. '
        'The terminal’s 88.9°C reading was a live host reading after completion; it does not describe all collection samples '
        'or by itself invalidate the sealed trials. The protocol does not measure hardware thermal throttling directly, '
        'so passing its checks is not proof of thermal equivalence or absence of all host effects.','',
        '[Sealed report](../../results/diagnostic/runtime-io-v13-completion-qualification-1/session/analysis/report.md)',
        '[Detailed derived evidence](review.json)','']
    (OUT/'report.md').write_text('\n'.join(lines))
    print(json.dumps(dict(arms=arms,marker_loss_points_median=statistics.median(loss),report=str(OUT/'report.md')),indent=2))


if __name__=='__main__': review()
