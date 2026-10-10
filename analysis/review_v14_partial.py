#!/usr/bin/env python3
"""Exploratory review of sealed completed V14 attempts; never resumes collection."""
from collections import Counter
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'diagnostic'))
import ablation_analysis as analysis
import ablation_study as study
import run
from environment_controls import window_summary

OUT = ROOT / 'analysis/runtime_io_v14_partial_review_17'


def distribution(values, scale=1):
    values = sorted(v / scale for v in values if v is not None)
    if not values:
        return None
    return dict(n=len(values), minimum=values[0], median=statistics.median(values),
                p99=values[math.ceil(.99 * len(values)) - 1], maximum=values[-1])


def review():
    session = study.DEFAULT / 'session'
    study.verify_session(session, current=False)
    rows, audit, schedules, seals, failed_cooling = [], [], {}, {}, []
    for order, c in enumerate(run.read(session / 'matrix.json'), 1):
        attempts = run.attempt_dirs(session / 'attempts' / c['run_id'])
        checks = [study.attempt_check(p, c) for p in attempts]
        audit.extend(checks)
        for p, check in zip(attempts, checks):
            if not check['valid'] and (p / 'settling.json').exists():
                thermal = run.read(p / 'settling.json')
                samples = thermal['samples']
                elapsed = samples[-1]['elapsed_sec']
                index = 0
                while index + 1 < len(samples) and samples[index + 1]['elapsed_sec'] <= elapsed - 60:
                    index += 1
                failed_cooling.append(dict(run_id=c['run_id'], attempt=p.name,
                    error=run.read(p / 'failure.json') if (p / 'failure.json').exists() else None,
                    elapsed_sec=elapsed, last_temperatures_c=samples[-1]['temperatures'],
                    last_window=window_summary(samples[index:], run.read(session / 'environment.json')['baseline_c']),
                    performance_measurement_started=(p / 'loadgen.json').exists(),
                    settling_sha256=run.sha(p / 'settling.json')))
        good = [p for p, check in zip(attempts, checks) if check['valid']]
        if len(good) > 1:
            raise ValueError('Multiple valid attempts: ' + c['run_id'])
        if not good:
            continue
        p = good[0]
        classified = study.validate_attempt(p, c)
        client = run.read(p / 'loadgen.json')
        server = run.read(p / 'server_metrics.json')
        schedule = [(q['ID'], q['ScheduledOffsetNs']) for q in sorted(client['requests'], key=lambda q: q['ID'])]
        if c['rep'] in schedules and schedules[c['rep']] != schedule:
            raise ValueError('Matched offered schedule differs')
        schedules[c['rep']] = schedule
        row, _ = study.stock_analysis.trial_row(order, c, p)
        settling, monitor = run.read(p / 'settling.json'), run.read(p / 'monitor.json')
        primary = [q for q in classified['requests'] if q['deadline_ms'] == 500]
        late_before = [q for q in primary if q['outcome'] == 'success' and not q['timely']
                       and q['completion_upper_ns'] is not None and q['completion_upper_ns'] <= 500_000_000]
        row.update(recorder_arm=c['recorder_arm'],
            offered=classified['offered'], timely_500=classified['deadlines']['500']['timely'],
            timely_500_fraction=classified['deadlines']['500']['timely_fraction'],
            timely_1000_fraction=classified['deadlines']['1000']['timely_fraction'],
            failure_count=classified['deadlines']['500']['failure'],
            failure_fraction=classified['deadlines']['500']['failure_fraction'],
            deadline_counts=classified['deadlines'],
            late_success_work_before=len(late_before),
            late_before_publication_classes=dict(Counter(q['publication_class'] for q in late_before)),
            late_before_resume_classes=dict(Counter(q['deadline_crossing'] for q in late_before)),
            accepted_settling_means_c={k: v['mean_c'] for k, v in settling['summary']['sensors'].items()},
            collection_temps_c={k: distribution([s['temps_c'][k] for s in monitor]) for k in monitor[0]['temps_c']},
            measurement_started_at=run.read(p / 'result.json')['measurement_started_at'],
            intervals_ms={key: distribution([q[key] for q in primary], 1e6) for key in (
                'completion_to_resume_ns', 'completion_to_publish_start_ns', 'publication_bracket_ns',
                'record_lock_wait_ns', 'record_held_interval_ns', 'publication_to_resume_lower_ns')},
        observer_dropped=server.get('observer_dropped_records', 0),
            observer_pending=server.get('observer_pending_records', 0))
        rows.append(row)
        seals[c['run_id']] = dict(attempt=p.name, complete_sha256=run.sha(p / 'complete.json'))
    cells = {(r['rep'], r['recorder_arm']): r for r in rows}
    blocks = sorted({r['rep'] for r in rows})
    complete_blocks = [b for b in blocks if all((b, a) in cells for a in analysis.ARMS)]
    if len(rows) != 17 or complete_blocks != [1, 2]:
        raise ValueError('This review describes the 17-trial snapshot; create a separate review for later data.')
    contrasts = {}
    for base, arm, label in analysis.CONTRASTS:
        pairs = []
        for b in blocks:
            if (b, base) not in cells or (b, arm) not in cells:
                continue
            a, z = cells[b, base], cells[b, arm]
            def ratio(k):
                return z[k] / a[k] if z[k] is not None and a[k] not in (None, 0) else None
            pair = dict(block=b, complete_block=b in complete_blocks,
                timely_500_delta_pp=100 * (z['timely_500_fraction'] - a['timely_500_fraction']),
                timely_1000_delta_pp=100 * (z['timely_1000_fraction'] - a['timely_1000_fraction']),
                failure_delta_pp=100 * (z['failure_fraction'] - a['failure_fraction']),
                cpu_ratio=ratio('cpu_usec_per_completed_work'), p99_ratio=ratio('p99_e2e_ms'))
            m = analysis.boundaries.MARGINS
            pair['within_original_screen'] = (abs(pair['timely_500_delta_pp']) <= 100 * m['timely_fraction']
                and abs(pair['timely_1000_delta_pp']) <= 100 * m['timely_fraction']
                and abs(pair['failure_delta_pp']) <= 100 * m['failure_fraction']
                and pair['cpu_ratio'] is not None and abs(pair['cpu_ratio'] - 1) <= m['cpu_ratio']
                and pair['p99_ratio'] is not None and abs(pair['p99_ratio'] - 1) <= m['p99_ratio'])
            pairs.append(pair)
        contrasts[label] = dict(base=base, arm=arm, pairs=pairs,
            complete_block_pairs=[p for p in pairs if p['complete_block']],
            summary={k: distribution([p[k] for p in pairs]) for k in (
                'timely_500_delta_pp', 'timely_1000_delta_pp', 'cpu_ratio', 'p99_ratio')})
    value = dict(created_at=run.now(), partial=True, final_qualification=None, eligible_for_controls=False,
        limitation='Two complete blocks and one incomplete block. Exploratory interim review; no equivalence or causal qualification. All valid attempts retained; no protocol changes.',
        completed=len(rows), complete_blocks=complete_blocks,
        incomplete_blocks={str(b): [a for a in analysis.ARMS if (b, a) not in cells] for b in blocks if b not in complete_blocks},
        frozen_session_verified=True, matched_schedules_verified=True,
        failed_cooling=failed_cooling, baseline_c=run.read(session / 'environment.json')['baseline_c'],
        candidate_already_outside_frozen_all_pairs_rule=any(not p['within_original_screen']
            for p in contrasts['candidate_observer_qualification']['pairs']),
        metadata_sha256=run.sha(session / 'metadata.json'), matrix_sha256=run.sha(session / 'matrix.json'),
        review_script_sha256=run.sha(Path(__file__)), attempt_seals=seals,
        attempt_audit=audit, trials=rows, contrasts=contrasts)
    OUT.mkdir(exist_ok=True)
    run.put(OUT / 'review.json', value)
    lines = ['# V14 exploratory review of 17 completed trials', '',
        'Frozen session and individual attempt seals checked. This is a partial review, not the final eight-block qualification. '
        'Blocks 1–2 are complete; block 3 lacks V13. All available within-block offered schedules match. '
        'No collection is started and no sealed session files are changed.', '',
        '| Block | Arm | Timely 500 ms | Timely 1,000 ms | CPU/job µs | Successful p99 ms | Late successes: work before 500 ms |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f'| {r["rep"]} | {r["recorder_arm"]} | {r["timely_500_fraction"]:.2%} | '
            f'{r["timely_1000_fraction"]:.2%} | {r["cpu_usec_per_completed_work"]:.2f} | '
            f'{r["p99_e2e_ms"]:.2f} | {r["late_success_work_before"]} |')
    lines += ['', '## Declared contrasts, available matched pairs', '',
        'Values are change from the first arm to the second. Percentage points differ from percent change. '
        'Block 3 pairs are additional exploratory context; primary interim comparisons use the two complete blocks.', '',
        '| Contrast | Block | Complete block | Timely 500 ms change, pp | CPU/job change | p99 change | Within original practical margins |',
        '|---|---:|---|---:|---:|---:|---|']
    for contrast in contrasts.values():
        for p in contrast['pairs']:
            lines.append(f'| {contrast["base"]} → {contrast["arm"]} | {p["block"]} | {p["complete_block"]} | '
                f'{p["timely_500_delta_pp"]:+.2f} | {100*(p["cpu_ratio"]-1):+.2f}% | '
                f'{100*(p["p99_ratio"]-1):+.2f}% | {p["within_original_screen"]} |')
    lines += ['', '## Interpretation and next exploration', '',
        'The dominant interim separation is already present in legacy → clocks: in the two complete blocks, '
        'primary timely success loses 12.63 and 13.43 percentage points, CPU/job increases 3.35% and 3.19%, '
        'and successful p99 increases 27.09% and 28.07%. The corresponding pair from incomplete block 3 '
        'has the same direction. This implicates the combined clock-call/new-worker-path change, '
        'not clock calls in isolation.', '',
        'Adding persistent per-worker recording changes timely success by +0.31 and +0.60 points in the complete blocks. '
        'Adding the post-send mutex changes it by +0.46 and −0.97 points. Those much smaller, mixed lock differences '
        'do not support the extra mutex as the dominant source of the roughly 13-point regression. '
        'Counter placement has a smaller adverse trend (−1.37 and −0.15 points in complete blocks; '
        '−1.28 in partial block 3), which deserves continued checking. None proves equivalence.', '',
        'V13 versus legacy reproduces the earlier observer penalty: −8.69 and −9.57 points. '
        'The new passive recorder is worse than legacy by −12.32 and −12.82 points in complete blocks. '
        'The original all-pairs qualification rule already cannot pass with these retained pairs, '
        'regardless of the remaining trials. Finishing the declared batch would estimate consistency and '
        'the component contrasts; it must not be treated as a chance to obtain a passing observer.', '',
        'Queue-delay p99 increases from 601/596 ms in legacy to 826/824 ms in clocks and 824/818 ms in passive. '
        'Post-computation p99 remains about 162–163 ms. The larger end-to-end penalty is therefore accompanied '
        'primarily by a larger queued backlog. These marginal percentiles cannot be added as per-request accounting. '
        'The modest CPU/job increase and larger backlog are consistent with small service-demand differences '
        'being amplified by a quota-limited burst; they do not establish its exact cause.', '',
        'The original late-after-work phenomenon persists: legacy has 512 and 503 successful deadline misses '
        'whose main computation is certainly before 500 ms, plus 520 in partial block 3. '
        'All 393/389/374 corresponding passive successes have publication certainly before the deadline; '
        'their publication-to-handler lower-bound p99 is roughly 163 ms. This localizes delay in the affected '
        'observer, but does not distinguish runnable scheduling from quota unavailability. '
        'The lower late-after-work count in passive is not improvement: many more requests finish work after the deadline.', '',
        'Next explore the common worker-path change with a static source/compiler audit and a separately frozen '
        'minimal ablation that keeps the legacy path and introduces marker calls incrementally. '
        'Do not alter this session’s source or margins. Complete remaining blocks only under comparable accepted '
        'environment conditions; require a qualified observer before the worker/parallelism comparison.', '',
        '## Cooling and host context', '',
        'The accepted initial baseline is 58.95°C. Completed-trial accepted cooling-window means span '
        '56.32–59.43°C; collection k10temp samples span 65.75–75.13°C. Later failed cooling is distinct: '
        'block 3 V13 attempt 001 waited about 1,263 seconds and ended at 44.25°C, below the permitted baseline window. '
        'It never collected a performance trial. The gate requires a stable temperature mean within ±3°C of '
        'baseline, not exactly 60°C; a much cooler host can indeed fail it. If the host settles persistently '
        'near 44°C, prepare a separate session with a newly frozen baseline rather than overwrite this baseline '
        'or combine conditions without disclosing the change. All 17 completed trials pass their recorded '
        'acceptance checks, but those checks do not prove thermal equivalence.', '',
        'Five queue-full HTTP 503 outcomes remain in the denominators: two in block 1 passive and three in '
        'block 1 mutex_late. There are no timeout/network failures in these completed trials.', '',
        '## Integrity and limitations', '',
        f'{len(rows)} valid completed attempts; {sum(not a["valid"] for a in audit)} preserved incomplete/invalid attempts. '
        'The full qualification remains pending. Practical margins are unchanged: 1 pp deadline success, '
        '0.1 pp failure, 5% CPU/job and 10% p99. Individual requests are not independent experiment repetitions.', '',
        'Clock/path and allocation/store comparisons are bundles. V13 versus mutex_late is also a bundle. '
        'Handler execution timestamps do not establish runnable readiness; wall intervals do not isolate quota pauses. '
        'Accepted cooling and host samples do not directly measure hardware thermal throttling.', '',
        '[Detailed data and attempt audit](review.json)', '']
    (OUT / 'report.md').write_text('\n'.join(lines))
    print(json.dumps(dict(completed=len(rows), complete_blocks=complete_blocks,
        invalid=[a for a in audit if not a['valid']],
        trials=[{k:r[k] for k in ('rep','recorder_arm','timely_500_fraction','timely_1000_fraction',
            'cpu_usec_per_completed_work','p99_e2e_ms','late_success_work_before','failure_count')} for r in rows],
        contrasts=contrasts, report=str(OUT/'report.md')), indent=2))


if __name__ == '__main__':
    review()
