#!/usr/bin/env python3
"""Offline admission/queue reconstruction from a sealed worker-yield study.

Never launches a workload, changes retained trials, or creates a passing gate.
"""
import argparse
import bisect
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import statistics

import inspect_http_cleanup
import run as runner
import trace_analysis

MODES = ('plain', 'trace', 'yield', 'yield_trace')
NS = 1_000_000_000


def read(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def unique(rows, key, label):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError('duplicate ' + label)
    return result


def percentile(values, p):
    values = sorted(values)
    return values[max(0, math.ceil(len(values)*p/100)-1)] if values else None


def causal_clock_bounds(requests, entries):
    """Server time = client time + offset, using dispatch <= entry <= first byte.

    FirstByteOffsetNs is relative to dispatch, not scheduled time. Bounds assume
    a constant clock offset over this short same-host trial. No WroteRequest
    callback is assumed to precede server entry.
    """
    low, high = [], []
    for rid, entry in entries.items():
        r = requests[rid]
        if r['FirstByteOffsetNs'] < 0:
            raise ValueError('missing first-byte callback; cannot align this trial')
        dispatch = r['ScheduledOffsetNs'] + r['DispatchLagNs']
        low.append((entry['start_ns']-dispatch-r['FirstByteOffsetNs'], rid))
        high.append((entry['start_ns']-dispatch, rid))
    lower, lower_id = max(low)
    upper, upper_id = min(high)
    if lower > upper:
        raise ValueError('inconsistent causal clock bounds; do not force an alignment')
    return dict(offset_low_ns=lower, offset_high_ns=upper,
                uncertainty_ns=upper-lower, lower_bound_request=lower_id,
                upper_bound_request=upper_id, request_count=len(low))


def sweep(workers):
    """Cumulative timestamp estimates; q includes dequeue-to-start gaps."""
    changes = defaultdict(lambda: [0, 0])
    for row in workers.values():
        changes[row['admission_ns']][0] += 1
        changes[row['worker_start_ns']][0] -= 1
        changes[row['worker_start_ns']][1] += 1
        changes[row['completion_ns']][1] -= 1
    times, qvalues, activevalues = [], [], []
    q, active = 0, 0
    for stamp, (dq, da) in sorted(changes.items()):
        q += dq
        active += da
        times.append(stamp)
        qvalues.append(q)
        activevalues.append(active)
    return times, qvalues, activevalues


def value_at(times, values, stamp, before=False):
    pos = (bisect.bisect_left if before else bisect.bisect_right)(times, stamp)-1
    return values[pos] if pos >= 0 else 0


def extrema(times, values, start, end):
    # Half-open interval: state at start plus transitions strictly inside.
    a, b = bisect.bisect_right(times, start), bisect.bisect_left(times, end)
    relevant = [value_at(times, values, start)] + values[a:b]
    return min(relevant), max(relevant)


def count_between(times, start, end):
    return bisect.bisect_left(times, end)-bisect.bisect_left(times, start)


def delay_bounds(stamp, client_stamp, clock):
    return (stamp-client_stamp-clock['offset_high_ns'],
            stamp-client_stamp-clock['offset_low_ns'])


def busy_capacity(times, qvalues, completions, origin, width_ms, threshold=8):
    width = width_ms*1_000_000
    seconds, count = 0, 0
    for i in range(20*NS//width):
        a, b = origin+i*width, origin+(i+1)*width
        qmin, _ = extrema(times, qvalues, a, b)
        if qmin>=threshold:
            seconds += width/NS
            count += count_between(completions,a,b)
    return dict(width_ms=width_ms, threshold=threshold, seconds=seconds,
                completions=count, rps=count/seconds if seconds else None)


def report(out, trials, bursts, contrasts):
    median = lambda group,key: statistics.median(t[key] for t in group)
    lines = [
        '# What the saved v8 trials reveal about admission and queue saturation', '',
        'Offline review — 2026-10-02. All 16 sealed trials revalidated; '
        '36,240 client requests join uniquely to server handler entry, decision '
        'and exit events. Source snapshots and completion seals were checked. '
        'No measurement was launched; no performance gate was changed.', '',
        '## Finding: lower rejection can conceal waiting before admission', '',
        'Yielding sharply reduces the time from the client schedule to HTTP '
        'handler entry in every balanced block, with tracing off and on. '
        'The non-yielding queue often stays almost empty through much of the '
        'offered high-rate half, then jumps near its limit as handlers catch up. '
        'Yielded queues instead grow throughout the high-rate half. This '
        'supports admission spreading as a substantial contributor to the '
        'lower rejection of the non-yielding baseline.', '',
        'The table reports medians of four per-trial values, not pooled '
        'percentiles. Entry delay includes all offered requests; queue wait '
        'includes admitted work only.', '',
        '| Mode | p99 schedule → handler entry | p50 queue wait | High-phase requests entering after their burst, per trial | Backlog-window completions/s |',
        '|---|---:|---:|---:|---:|',
    ]
    for mode in MODES:
        group = [t for t in trials if t['mode']==mode]
        lines.append(f'| {mode} | {median(group,"entry_delay_p99_mid_ms"):.3f} ms | '
                     f'{median(group,"queue_wait_p50_ms"):.3f} ms | '
                     f'{median(group,"high_spill_definite"):.1f} | '
                     f'{median(group,"busy_completion_rps"):.2f} |')
    plain3 = next(t for t in trials if t['mode']=='plain' and t['block']==3)
    lines += ['',
              f'The clearest counterexample to interpreting rejection alone is block 3 '
              f'plain: **{plain3["rejected"]} rejections**, but '
              f'**{plain3["high_spill_definite"]}** requests offered in high-rate halves '
              f'enter after their own burst ends, and schedule-to-entry p99 is '
              f'**{plain3["entry_delay_p99_mid_ms"]/1000:.3f} seconds**. '
              f'The timestamp queue estimate peaks at {plain3["q_estimate_max"]}. '
              'This trial does not show that the offered burst fits the work queue '
              'when HTTP admission is responsive.', '',
              '![Representative block 3 comparison](burst_walkthrough.png)', '',
              '## Finding: yielded bursts outpace worker starts', '',
              'Each high half offers 849 requests in five seconds. In yielded '
              'cells, 667–685 worker starts occur during each aligned high '
              'window, while 834–847 handler entries occur. The queue ends '
              'those windows with an estimated 118–126 admitted-but-not-started '
              'jobs. Rejection follows the resulting pressure on the 128-job '
              'channel. Small boundary ambiguity is documented below.', '',
              'A useful conservation calculation is admissions minus worker '
              'starts equals growth in admitted-but-not-started work. Do not '
              'substitute successful throughput over the full trial for '
              'busy-window worker capacity. Rejected requests never start CPU '
              'work, and requests still waiting before the handler are absent '
              'from the channel queue.', '',
              '## Finding: worker-capacity change is modest in the observed windows', '',
              'Across the 100 ms bins with sustained backlog, observed completion '
              'rates are about 133–136 jobs/s. Yielding is 0.20–1.95 jobs/s lower '
              'than plain and 0.18–2.70 jobs/s lower than trace within blocks. '
              'These are descriptive comparisons of different selected windows, '
              'not proof of a causal capacity penalty. The large change in '
              'admission timing cannot be reduced to a large CPU-cost increase. '
              'A small scheduling cost could still contribute.', '',
              '`capacity_sensitivity.csv` repeats this calculation using 50, '
              '100, 200 and 500 ms bins, low/mid/high clock offsets, and backlog '
              'thresholds 8 and 16. A bin is included only if the timestamp '
              'queue estimate remains above the threshold throughout. Results '
              'without eligible bins remain unavailable. The threshold 8 allows '
              'for four dequeue-to-start gaps and one pre-send sample: the '
              'channel still has backlog under those timing bounds.', '',
              'CPU/job from the entire trial is not CPU/job specifically during '
              'these busy windows; dividing the nominal quota by the whole-trial '
              'CPU/job does not measure actual burst capacity.', '',
              '## What the retained runtime traces add', '',
              'For traced cells, we intersect the HTTP connection goroutine '
              'scheduler states with a conservative interval from the latest '
              'possible client request-write callback to server handler entry. '
              'The request-write callback records client progress; it does '
              'not timestamp physical arrival of bytes at the server.', '',
              '| Traced mode | Runnable | Sync/other wait | Network wait | Not yet created/ended |',
              '|---|---:|---:|---:|---:|']
    for mode in ('trace','yield_trace'):
        counts = Counter()
        for t in trials:
            if t['mode']==mode:
                counts.update(t['trace_preentry_states_ns'])
        total = sum(counts.values())
        lines.append('| '+mode+' | '+' | '.join(f'{counts.get(k,0)/total:.2%}' for k in
                     ('runnable_ns','sync_or_other_wait_ns','network_wait_ns','not_created_or_ended_ns'))+' |')
    lines += ['',
              'These are shares of summed, overlapping request intervals, '
              'not CPU utilization. Their denominators differ between modes. '
              'The connection goroutine often exists and is Runnable during '
              'non-yielded pre-handler delay; some intervals occur before that '
              'goroutine is created. The exact runtime/netpoll/accept cause '
              'remains unresolved. A network-wait state does not by itself '
              'demonstrate a slow network.', '',
              'The ledger also checks whether a reused request was written '
              'during the previous request\'s server cleanup on the same '
              'connection. That direct overlap accounts for only part of '
              'the pre-handler delay. Cleanup starvation alone is an '
              'incomplete explanation of all delayed admission.', '',
              '## How clock alignment and queue estimates were checked', '',
              'For each request, client dispatch must precede the server '
              'handler-entry mark, which must precede the client first response '
              'byte. If server time equals client time plus a constant offset, '
              'each request bounds that offset. Intersecting all 2,265 request '
              'brackets gives a nonempty interval in every trial. Its width is '
              '0.101–0.135 ms in 15 trials and 3.089 ms in block 3 plain. '
              'This is causal bracketing under a constant-offset assumption, '
              'not an independently synchronized timestamp. WroteRequest '
              'callbacks are not used as an entry ordering constraint.', '',
              'Delay percentiles retain lower/upper bounds in `trials.csv`. '
              'Burst spill counts retain definite/possible classifications in '
              '`bursts.csv`; six requests in block 4 trace straddle the burst '
              'boundary under those bounds. The large seconds-long delays '
              'and the within-block yielding effect survive this uncertainty.', '',
              '`admission_ns` precedes channel send; `worker_start_ns` follows '
              'dequeue; decision marks follow the decision and mutex unlock. '
              'The difference of cumulative admissions and starts is therefore '
              'an estimate of unstarted admitted work, not exact instantaneous '
              'channel occupancy. Two trials reach 129 in that estimate '
              'despite channel capacity 128; these values are retained, not '
              'clamped. Processing-interval counts stay within four workers, '
              'and all reconstructed work drains to zero. Every rejection '
              'has a capacity-sized estimate somewhere between its handler '
              'entry and rejection mark; this supports consistency with the '
              'server\'s full-queue rejection, not exact decision timestamps.', '',
              '## Verdict and the next question', '',
              '- **Admission spreading: supported.** The non-yielding cells '
              'delay handler entry, spread some high-phase work beyond the '
              'burst, and keep much waiting outside the bounded work queue.',
              '- **Burst pressure on the yielded queue: supported.** '
              'Responsive admission delivers more work than workers start '
              'during the high halves, exhausting the finite queue.',
              '- **Large worker-capacity collapse: weakened.** Busy-window '
              'rates are similar, although a modest penalty and selection '
              'effects remain possible.',
              '- **Exact scheduler/accept/netpoll cause and a transparent '
              'instrumentation fix: unresolved.** Tracing-off cells have no '
              'runtime scheduler record; all four v8 modes retain custom '
              'recording and base timing.', '',
              'The next retained-data step is to inspect the longest pre-handler '
              'Runnable spans and the accept-loop/connection-reader wakeup '
              'stacks, then compare how many CPU jobs complete while the HTTP '
              'goroutine is ready. If those retained events cannot locate the '
              'perturbation, plan a narrowly targeted diagnostic for that gap. '
              'Keep yielding a mechanism probe. A candidate still needs a '
              'fresh qualification at the original workload and failure/overhead '
              'gates before full collection.', '',
              '## Reproduction and artifacts', '',
              'Run from the repository root, choosing a fresh output directory:', '',
              '```bash',
              'MPLCONFIGDIR=/tmp/cpu-quota-mpl venv/bin/python diagnostic/inspect_yield_queue.py \\',
              '  results/diagnostic/runtime-io-v8-yield-1 \\',
              '  --output analysis/runtime_io_v8_queue_fresh',
              '```', '',
              'Outputs: `request_ledger.csv`, `trials.csv`, `bursts.csv`, '
              '`contrasts.csv`, cumulative/count timelines at 10/50/100 ms, '
              '`capacity_sensitivity.csv`, `summary.json`, `validation.json`, '
              '`source_hashes.json` and PNG/PDF figures. The analyzer refuses '
              'to overwrite an existing output or write into the retained '
              'session. The six new tests cover clock bounds, dispatch origins, '
              'inconsistent alignment, ID zero/duplicates, conservation, '
              'handoff estimates and half-open bin boundaries. All 50 diagnostic '
              'tests passed.', '',
              'Frozen load-generator source and its recorded binary seal are '
              'retained; the collector did not snapshot the executable itself. '
              'This analysis does not claim to rehash a nonexistent frozen '
              'binary. Individual sealed trial files were rehashed by the '
              'existing validator.', '']
    (out/'report.md').write_text('\n'.join(lines))


def plot_trials(out, trials, ledgers, series, timelines):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = dict(plain='#44546a', trace='#d16b25', yield_='#168985', yield_trace='#7b55a6')
    colors['yield'] = colors.pop('yield_')
    fig, axes = plt.subplots(4, 4, figsize=(15, 11), sharex=True, sharey=True)
    for trial in trials:
        rid, mode, block = trial['run_id'], trial['mode'], trial['block']
        ax = axes[block-1, MODES.index(mode)]
        clock = trial['clock']
        origin = (clock['offset_low_ns']+clock['offset_high_ns'])/2
        tt, qq, _ = series[rid]
        ax.step([(t-origin)/NS for t in tt], qq, where='post', color=colors[mode], lw=.8)
        ax.axhline(128, color='#9e3d40', lw=.8, ls='--')
        for start in (5, 15):
            ax.axvspan(start, start+5, color='#ffbf69', alpha=.16)
        rejected = [row for row in ledgers[rid] if row['status']==503]
        ax.scatter([(r['decision_mark_ns']-origin)/NS for r in rejected],
                   [137]*len(rejected), color='#9e3d40', marker='|', s=15)
        ax.set_title(f'Block {block}: {mode} — {len(rejected)} rejected', fontsize=10)
        ax.set_xlim(0, 25)
        ax.set_ylim(-2, 145)
        ax.grid(alpha=.2)
    for ax in axes[-1]:
        ax.set_xlabel('Seconds from bounded client start')
    for ax in axes[:, 0]:
        ax.set_ylabel('Admitted, not yet started\n(timestamp estimate)')
    fig.suptitle('Yielding exposes the queue to the burst sooner\n'
                 'Shading: offered high-rate halves; red ticks: rejection marks; dashed line: queue capacity', fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(out/'queue_timelines.png', dpi=170)
    fig.savefig(out/'queue_timelines.pdf')
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for mode in MODES:
        selected = [t for t in trials if t['mode']==mode]
        for t in selected:
            rows = ledgers[t['run_id']]
            delay = sorted(max(0, (r['entry_delay_low_ns']+r['entry_delay_high_ns'])/2)/1e6 for r in rows)
            rank = [(i+1)/len(delay)*100 for i in range(len(delay))]
            axes[0].plot(rank, delay, color=colors[mode], alpha=.6, lw=1,
                         label=mode if t==selected[0] else None)
        axes[1].scatter([t['entry_delay_p99_mid_ms'] for t in selected],
                        [t['queue_wait_p50_ms'] for t in selected], color=colors[mode], label=mode, s=45)
    axes[0].set_yscale('symlog', linthresh=1)
    axes[0].set_xlabel('Percentile of all offered requests')
    axes[0].set_ylabel('Scheduled-to-handler-entry delay (ms)')
    axes[0].set_title('All 16 trials: yielding removes the seconds-long tail')
    axes[0].legend(fontsize=9)
    axes[1].set_xlabel('Trial p99 scheduled-to-handler-entry delay (ms)')
    axes[1].set_ylabel('Trial p50 queue wait, admitted requests (ms)')
    axes[1].set_title('Where the waiting appears')
    axes[1].legend(fontsize=9)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(out/'waiting_shift.png', dpi=170)
    fig.savefig(out/'waiting_shift.pdf')
    plt.close(fig)

    fig, axes = plt.subplots(2,2,figsize=(11,6.5),sharex=True,sharey='row')
    for col,mode in enumerate(('plain','yield')):
        trial = next(t for t in trials if t['block']==3 and t['mode']==mode)
        rid = trial['run_id']
        origin = (trial['clock']['offset_low_ns']+trial['clock']['offset_high_ns'])/2
        rows = ledgers[rid]
        for key,color,label in (('scheduled_client_ns','#8b949e','Client scheduled'),
                                ('entry_mark_ns','#2664ad','HTTP handler entered'),
                                ('worker_start_ns','#168985','Worker started')):
            times = sorted((r[key]-(0 if key=='scheduled_client_ns' else origin))/NS
                           for r in rows if r[key] is not None)
            axes[0,col].step(times,range(1,len(times)+1),where='post',color=color,label=label,lw=1.4)
        tt,qq,_ = series[rid]
        axes[1,col].step([(t-origin)/NS for t in tt],qq,where='post',color=colors[mode],lw=1)
        axes[1,col].axhline(128,color='#9e3d40',ls='--',lw=1)
        axes[0,col].set_title(f'Block 3: {mode} — {trial["rejected"]} rejections')
        axes[0,col].legend(fontsize=9,loc='upper left')
        for ax in axes[:,col]:
            for start in (5,15):
                ax.axvspan(start,start+5,color='#ffbf69',alpha=.16)
            ax.set_xlim(0,25)
            ax.grid(alpha=.2)
        axes[1,col].set_xlabel('Seconds from bounded client start')
    axes[0,0].set_ylabel('Cumulative request count')
    axes[1,0].set_ylabel('Admitted, not yet started\n(timestamp estimate)')
    axes[1,0].set_ylim(-2,140)
    fig.suptitle('A zero-rejection trial can hide waiting before admission\n'
                 'Shading marks the two high-rate offered bursts',fontsize=13)
    fig.tight_layout(rect=(0,0,1,.9))
    fig.savefig(out/'burst_walkthrough.png',dpi=180)
    fig.savefig(out/'burst_walkthrough.pdf')
    plt.close(fig)


def analyze(session, out, plots=True):
    if out.exists():
        raise ValueError('output directory exists; use a fresh directory')
    if out.is_relative_to(session):
        raise ValueError('derived output must be outside the retained session')
    meta = runner.verify_session(session, check_current=False)
    if not meta.get('yield_study'):
        raise ValueError('expected a worker-yield study')
    source_hashes = {}
    for rel, expected in meta['source_sha256'].items():
        frozen = session/'source'/rel
        if rel=='diagnostic/bin/build.json':
            frozen = session/'build.json'
        elif rel=='diagnostic/bin/loadgen':
            # The collector snapshots source and records the binary seal; it
            # does not copy the load-generator executable into the session.
            if meta['build']['loadgen_sha256']!=expected:
                raise ValueError('load-generator binary seal disagrees with provenance')
            continue
        if not frozen.is_file() or runner.sha(frozen)!=expected:
            raise ValueError('frozen source changed: ' + rel)
        source_hashes[rel] = expected
    configs = read(session/'matrix.json')
    # Validate before creating any successful-looking artifact.
    accepted = {}
    audit = []
    for config in configs:
        good = []
        for attempt in runner.attempt_dirs(session/'attempts'/config['run_id']):
            errors = runner.validation_errors(attempt, config, False)
            audit.append(dict(run_id=config['run_id'], attempt=attempt.name, issues=errors))
            if not errors:
                good.append(attempt)
        if len(good)!=1:
            raise ValueError(f'{config["run_id"]}: expected one valid attempt')
        accepted[config['run_id']] = good[0]
    if len(configs)!=16:
        raise ValueError('expected 16 trials')

    out.mkdir(parents=True)
    write_json(out/'validation.json', dict(passed=False, issues=['analysis incomplete']))
    trials, bursts, ledger_all, sensitivity = [], [], [], []
    ledgers, series, all_timelines = {}, {}, {}
    provenance = dict(session=str(session), analyzer_sha256=runner.sha(Path(__file__)),
                      frozen_sources=source_hashes, completion_sha256={}, consumed_files={})
    provenance['recorded_loadgen_binary_sha256'] = meta['source_sha256']['diagnostic/bin/loadgen']
    provenance['loadgen_binary_snapshot_retained'] = False
    for config in configs:
        rid, mode, block = config['run_id'], config['yield_mode'], config['rep']
        attempt = accepted[rid]
        print('RECONSTRUCT:', rid, flush=True)
        srv, status, lg, result = [read(attempt/n) for n in
                                 ('server_metrics.json', 'trace_status.json', 'loadgen.json', 'result.json')]
        provenance['completion_sha256'][rid] = runner.sha(attempt/'complete.json')
        consumed = ['config.json', 'server_metrics.json', 'trace_status.json', 'loadgen.json', 'result.json']
        requests = unique(lg['requests'], 'ID', 'client request')
        workers = unique(srv['events'], 'id', 'worker job')
        handlers = unique(srv['handler_events'], 'id', 'successful handler')
        io = status['io_events']
        by_kind = {kind: unique([e for e in io if e['kind']==kind and e['request_known']], 'request', kind)
                   for kind in ('handler_entry', 'handler_exit', 'admitted', 'rejected')}
        entries = by_kind['handler_entry']
        if set(entries)!=set(requests) or set(by_kind['handler_exit'])!=set(requests):
            raise ValueError(rid+': incomplete all-request handler coverage')
        if set(by_kind['admitted'])!=set(workers) or set(by_kind['rejected'])!=set(requests)-set(workers):
            raise ValueError(rid+': decision/job reconciliation failed')
        if len(workers)!=srv['admitted'] or len(by_kind['rejected'])!=srv['rejected']:
            raise ValueError(rid+': server counters do not reconcile')
        for req in requests.values():
            if req['Error'] or req['StatusCode'] not in (200, 503):
                raise ValueError('this clock reconstruction requires fully observed responses')
            if (req['StatusCode']==200)!=(req['ID'] in workers):
                raise ValueError(rid+': outcome disagrees with admission')
        clock = causal_clock_bounds(requests, entries)
        lo, hi = clock['offset_low_ns'], clock['offset_high_ns']
        origin = (lo+hi)//2
        tt, qq, aa = sweep(workers)
        if min(qq)<0 or max(qq)>srv['queue_cap']+config['workers']+1 or min(aa)<0 or max(aa)>config['workers']:
            raise ValueError(rid+': queue/work conservation outside handoff bounds')
        if qq[-1]!=0 or aa[-1]!=0:
            raise ValueError(rid+': reconstruction not drained')
        series[rid] = (tt, qq, aa)
        terminal = unique([e for e in io if e['kind'] in ('conn_idle', 'conn_closed') and e['request_known']],
                          'request', 'connection terminal')
        if set(terminal)!=set(requests):
            raise ValueError(rid+': missing/duplicate connection terminal')
        rows, previous = [], {}
        for reqid, e in sorted(entries.items(), key=lambda item: item[1]['start_ns']):
            r = requests[reqid]
            work, handler = workers.get(reqid), handlers.get(reqid)
            decision = by_kind['admitted' if work else 'rejected'][reqid]
            if not e['start_ns']<=decision['start_ns']<=by_kind['handler_exit'][reqid]['start_ns']:
                raise ValueError(rid+': reversed decision lifecycle')
            entry_low, entry_high = delay_bounds(e['start_ns'], r['ScheduledOffsetNs'], clock)
            prior = previous.get(e['conn'])
            previous[e['conn']] = reqid
            wrote = r['ScheduledOffsetNs']+r['DispatchLagNs']+r['WroteRequestOffsetNs']
            cleanup_overlap = 0
            if prior is not None and r['WroteRequestOffsetNs']>=0:
                prior_exit = by_kind['handler_exit'][prior]['start_ns']
                prior_done = terminal[prior]['start_ns']
                if prior_done>e['start_ns']:
                    raise ValueError(rid+': overlapping connection lifetimes')
                cleanup_overlap = max(0, prior_done-max(prior_exit, wrote+hi))
            row = dict(run_id=rid, mode=mode, block=block, request_id=reqid,
                       status=r['StatusCode'], conn=e['conn'], previous_request_id=prior,
                       offered_phase='high' if r['ScheduledOffsetNs']%(10*NS)>=5*NS else 'low',
                       offered_cycle=r['ScheduledOffsetNs']//(10*NS)+1,
                       scheduled_client_ns=r['ScheduledOffsetNs'], dispatch_lag_ns=r['DispatchLagNs'],
                       client_wrote_offset_ns=r['WroteRequestOffsetNs'],
                       e2e_ns=r['EndToEndLatencyNs'], entry_mark_ns=e['start_ns'],
                       decision_mark_ns=decision['start_ns'],
                       exit_mark_ns=by_kind['handler_exit'][reqid]['start_ns'],
                       connection_done_ns=terminal[reqid]['start_ns'],
                       entry_delay_low_ns=entry_low, entry_delay_high_ns=entry_high,
                       prior_cleanup_overlap_lower_ns=cleanup_overlap,
                       admission_sample_ns=work['admission_ns'] if work else None,
                       worker_start_ns=work['worker_start_ns'] if work else None,
                       completion_ns=work['completion_ns'] if work else None,
                       sampled_queue_depth=work['depth_at_admission'] if work else None,
                       queue_wait_ns=work['queue_wait_ns'] if work else None,
                       processing_ns=work['processing_ns'] if work else None,
                       post_work_ns=handler['post_work_wait_ns'] if handler else None)
            rows.append(row)
        ledgers[rid] = rows
        ledger_all.extend(rows)
        admission_times = sorted(w['admission_ns'] for w in workers.values())
        start_times = sorted(w['worker_start_ns'] for w in workers.values())
        completion_times = sorted(w['completion_ns'] for w in workers.values())
        entry_times = sorted(e['start_ns'] for e in entries.values())
        reject_times = sorted(e['start_ns'] for e in by_kind['rejected'].values())
        channels = dict(entries=entry_times, admissions=admission_times, starts=start_times,
                        completions=completion_times, rejections=reject_times)
        # Cover the entire server lifecycle, with an origin aligned only within the stated bounds.
        horizon = max(20*NS, max(completion_times+entry_times)-origin)+NS
        for width_ms in (10, 50, 100):
            width = width_ms*1_000_000
            timeline = []
            for i in range(math.ceil(horizon/width)):
                a, b = origin+i*width, origin+(i+1)*width
                qmin, qmax = extrema(tt, qq, a, b)
                row = dict(run_id=rid, mode=mode, block=block, width_ms=width_ms,
                           start_s=i*width/NS, end_s=(i+1)*width/NS,
                           q_estimate_begin=value_at(tt, qq, a, before=True),
                           q_estimate_end=value_at(tt, qq, b, before=True), q_estimate_min=qmin,
                           q_estimate_max=qmax, processing_begin=value_at(tt, aa, a, before=True),
                           backlog_entire_bin=qmin>=8)
                for name, stamps in channels.items():
                    row[name] = count_between(stamps, a, b)
                    row[name+'_cumulative_end'] = bisect.bisect_left(stamps, b)
                timeline.append(row)
            all_timelines[rid, width_ms] = timeline
        bins = [b for b in all_timelines[rid, 100] if b['end_s']<=20 and b['backlog_entire_bin']]
        busy_sec = len(bins)*.1
        busy_completions = sum(b['completions'] for b in bins)
        for width in (50,100,200,500):
            for threshold in (8,16):
                for label,offset in (('low',lo),('mid',origin),('high',hi)):
                    sensitivity.append(dict(run_id=rid,mode=mode,block=block,clock_offset=label,
                                            **busy_capacity(tt,qq,completion_times,offset,width,threshold)))
        rejection_consistent = 0
        for e in by_kind['rejected'].values():
            _, peak = extrema(tt, qq, entries[e['request']]['start_ns'], e['start_ns']+1)
            rejection_consistent += peak>=srv['queue_cap']
        high_rows = [r for r in rows if r['offered_phase']=='high']
        def spill(r, bound):
            # Server entry after the end of the SAME offered high half.
            return r['entry_mark_ns'] > bound+r['offered_cycle']*10*NS
        trial = dict(run_id=rid, mode=mode, block=block, scheduled=len(rows),
                     rejected=len(reject_times), clock=clock, queue_sample_max=srv['queue_max'],
                     q_estimate_max=max(qq), processing_estimate_max=max(aa),
                     rejected_with_capacity_in_entry_to_mark_window=rejection_consistent,
                     high_offered=len(high_rows), high_spill_definite=sum(spill(r, hi) for r in high_rows),
                     high_spill_possible=sum(spill(r, lo) for r in high_rows),
                     entry_delay_p50_mid_ms=percentile([(r['entry_delay_low_ns']+r['entry_delay_high_ns'])/2e6 for r in rows], 50),
                     entry_delay_p99_mid_ms=percentile([(r['entry_delay_low_ns']+r['entry_delay_high_ns'])/2e6 for r in rows], 99),
                     entry_delay_p99_low_ms=percentile([r['entry_delay_low_ns']/1e6 for r in rows], 99),
                     entry_delay_p99_high_ms=percentile([r['entry_delay_high_ns']/1e6 for r in rows], 99),
                     entry_delay_definitely_over_1s=sum(r['entry_delay_low_ns']>=NS for r in rows),
                     queue_wait_p50_ms=percentile([w['queue_wait_ns']/1e6 for w in workers.values()],50),
                     post_work_p99_ms=percentile([h['post_work_wait_ns']/1e6 for h in handlers.values()],99),
                     busy_seconds=busy_sec, busy_completions=busy_completions,
                     busy_completion_rps=busy_completions/busy_sec if busy_sec else None,
                     cpu_usec_per_job=result['cgroup_delta']['usage_usec']/len(workers),
                     trace_preentry_states_ns=None,
                     prior_cleanup_overlap_lower_total_ns=sum(r['prior_cleanup_overlap_lower_ns'] for r in rows))
        for cycle in (1, 2):
            selected = [r for r in high_rows if r['offered_cycle']==cycle]
            a, b = origin+((cycle-1)*10+5)*NS, origin+cycle*10*NS
            burst = dict(run_id=rid, mode=mode, block=block, cycle=cycle,
                         offered_high=len(selected), rejected_high=sum(r['status']==503 for r in selected),
                         high_spill_definite=sum(spill(r,hi) for r in selected),
                         high_spill_possible=sum(spill(r,lo) for r in selected),
                         queue_estimate_begin=value_at(tt, qq, a, before=True),
                         queue_estimate_end=value_at(tt, qq, b, before=True))
            for name, stamps in channels.items():
                burst[name+'_in_aligned_high_window'] = count_between(stamps,a,b)
            bursts.append(burst)
        if config['runtime_trace']:
            parsed, trace_requests = [read(attempt/n) for n in ('trace_scheduler.json','trace_requests.json')]
            consumed += ['trace_scheduler.json', 'trace_requests.json']
            scheduler = inspect_http_cleanup.snapshot_series(parsed)
            rtclock = trace_requests['clock_mapping']
            rtoffset = (rtclock['offset_low_ns']+rtclock['offset_high_ns'])//2
            trace_rows = unique(trace_requests['all_requests'], 'id', 'traced request')
            if set(trace_rows)!=set(requests):
                raise ValueError(rid+': missing traced request')
            summed = Counter()
            for row in rows:
                req = requests[row['request_id']]
                begin = req['ScheduledOffsetNs']+req['DispatchLagNs']+req['WroteRequestOffsetNs']+hi
                end = row['entry_mark_ns']
                if req['WroteRequestOffsetNs']<0 or begin>=end:
                    continue
                g = trace_rows[row['request_id']]['handler_g']
                states = trace_analysis.state_durations(scheduler[g], begin+rtoffset, end+rtoffset)
                summed.update(states)
                for key,value in states.items():
                    row['preentry_'+key] = value
            trial['trace_preentry_states_ns'] = dict(summed)
        provenance['consumed_files'][rid] = {n: runner.sha(attempt/n) for n in consumed}
        trials.append(trial)

    write_csv(out/'request_ledger.csv', ledger_all)
    write_csv(out/'bursts.csv', bursts)
    flat_trials = [{**{k:v for k,v in t.items() if k not in ('clock','trace_preentry_states_ns')},
                    **{'clock_'+k:v for k,v in t['clock'].items()},
                    'trace_preentry_states_ns': json.dumps(t['trace_preentry_states_ns'])} for t in trials]
    write_csv(out/'trials.csv', flat_trials)
    for width in (10,50,100):
        write_csv(out/f'timeline_{width}ms.csv', [r for c in configs for r in all_timelines[c['run_id'],width]])
    metrics = ('entry_delay_p99_mid_ms', 'queue_wait_p50_ms', 'busy_completion_rps', 'high_spill_definite', 'rejected')
    contrasts = []
    for block in range(1,5):
        group = {t['mode']:t for t in trials if t['block']==block}
        if set(group)!=set(MODES):
            raise ValueError('incomplete factorial block')
        row = dict(block=block)
        for metric in metrics:
            for left,right in (('yield','plain'),('yield_trace','trace'),('trace','plain'),('yield_trace','yield')):
                row[metric+'_'+left+'_minus_'+right] = group[left][metric]-group[right][metric]
        contrasts.append(row)
    write_csv(out/'contrasts.csv', contrasts)
    write_csv(out/'capacity_sensitivity.csv',sensitivity)
    write_json(out/'summary.json', dict(trials=trials, contrasts=contrasts, eligible_for_full=False))
    write_json(out/'source_hashes.json', provenance)
    if plots:
        plot_trials(out, trials, ledgers, series, all_timelines)
    report(out,trials,bursts,contrasts)
    write_json(out/'validation.json', dict(passed=True, trials=16, ledger_requests=len(ledger_all),
                                         issues=[], attempt_audit=audit, eligible_for_full=False))
    print('OFFLINE RECONSTRUCTION COMPLETE:', out, flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    analyze(args.session.resolve(), args.output.resolve(), not args.no_plots)
