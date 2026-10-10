#!/usr/bin/env python3
"""Four-cell scheduling comparison; never qualifies a performance pilot."""
import argparse
from pathlib import Path
import statistics
import analyze
import inspect_http_cleanup
import run as runner

MODES = ('plain', 'trace', 'yield', 'yield_trace')
FIELDS = ('rejection_fraction', 'timeout_fraction', 'error_fraction', 'successful_rps',
          'cpu_usec_per_completed_work', 'client_cpu_usec_per_scheduled',
          'p50_e2e_ms', 'p99_e2e_ms', 'p99_queue_ms', 'p99_processing_ms', 'p99_post_work_ms')


def difference(a, b):
    return a-b if a is not None and b is not None else None


def median_text(group, key, spec):
    values = [r[key] for r in group if r[key] is not None]
    return format(statistics.median(values), spec) if values else 'NA'


def contrasts(rows):
    result = []
    for block in range(1, 5):
        group = [r for r in rows if r['rep'] == block]
        cells = {r['yield_mode']: r for r in group}
        if len(group) != 4 or set(cells) != set(MODES):
            raise ValueError('incomplete or duplicate factorial block')
        row = dict(block=block)
        for field in FIELDS:
            plain_trace = difference(cells['trace'][field], cells['plain'][field])
            yielded_trace = difference(cells['yield_trace'][field], cells['yield'][field])
            row[field+'_trace_penalty_without_yield'] = plain_trace
            row[field+'_trace_penalty_with_yield'] = yielded_trace
            row[field+'_yield_effect_trace_off'] = difference(cells['yield'][field], cells['plain'][field])
            row[field+'_yield_effect_trace_on'] = difference(cells['yield_trace'][field], cells['trace'][field])
            row[field+'_interaction'] = difference(yielded_trace, plain_trace)
        result.append(row)
    return result


def analyze_yield(session):
    meta = runner.verify_session(session, check_current=False)
    if not meta.get('yield_study') or meta.get('pilot') or meta.get('components'):
        raise ValueError('not a standalone worker-yield study')
    out = session/'analysis'
    out.mkdir(exist_ok=True)
    # A failed or interrupted analysis must not leave an earlier passing stamp.
    runner.put(out/'validation.json', dict(passed=False, issues=['analysis not complete']))
    rows, audit, issues, seals = [], [], [], {}
    for order, config in enumerate(runner.read(session/'matrix.json'), 1):
        good = []
        for directory in runner.attempt_dirs(session/'attempts'/config['run_id']):
            errors = runner.validation_errors(directory, config, False)
            audit.append(dict(run_id=config['run_id'], attempt=directory.name,
                              valid=not errors, errors='; '.join(errors)))
            if not errors:
                good.append(directory)
        if len(good) != 1:
            issues.append(f'{config["run_id"]}: {len(good)} valid attempts')
            continue
        directory = good[0]
        row = analyze.trial_row(order, config, directory)
        lg = runner.read(directory/'loadgen.json')
        status = runner.read(directory/'trace_status.json')
        row.update(yield_mode=config['yield_mode'], worker_yield=config['worker_yield'],
                   custom_recording=True, error_fraction=lg['total_errors']/lg['total_scheduled'],
                   io_events=len(status['io_events']), io_events_dropped=status['io_events_dropped'])
        cleanup = None
        if config['runtime_trace']:
            print('CLEANUP ANALYSIS:', config['run_id'], flush=True)
            try:
                cleanup = inspect_http_cleanup.inspect(directory)
                runner.put(out/(config['run_id']+'_http_cleanup.json'), cleanup)
            except (ValueError, OSError, runner.sp.CalledProcessError) as exc:
                issues.append(f'{config["run_id"]}: cleanup analysis: {exc}')
        row.update(cleanup_waits_matched=cleanup['requests_matched'] if cleanup else None,
                   cleanup_wait_p99_ms=cleanup['wait_ms']['p99'] if cleanup else None,
                   cleanup_wait_max_ms=cleanup['max_wait_ms'] if cleanup else None,
                   cleanup_waits_at_least_1ms=cleanup['waits_at_least_1ms'] if cleanup else None,
                   cleanup_reader_runnable_share=cleanup['reader_runnable_share'] if cleanup else None,
                   cleanup_long_waits_reader_never_ran=cleanup['long_waits_reader_never_ran_before_cleanup'] if cleanup else None)
        rows.append(row)
        seals[config['run_id']] = runner.sha(directory/'complete.json')
    analyze.writecsv(out/'attempt_audit.csv', audit)
    if len(rows) != 16:
        issues.append(f'{len(rows)} of 16 trials available')
    runner.put(out/'validation.json', dict(passed=not issues, issues=issues))
    if issues:
        raise SystemExit('Incomplete yield study: ' + '; '.join(issues))
    analyze.writecsv(out/'trials.csv', rows)
    analyze.writecsv(out/'contrasts.csv', contrasts(rows))
    lines = ['# Worker yielding and runtime tracing comparison', '',
             'Mechanistic evidence only. This study cannot qualify a pilot or unlock full collection.', '',
             'Custom connection recording, base timing and the workload stay enabled and fixed in every mode. Yielding calls runtime.Gosched once after each completed CPU job and reply publication. Runtime tracing is the second independent treatment.', '',
             '| Mode | Rejection range | Timeout range | Median successful requests/s | Median successful p99 ms | Median CPU µs/completed work |',
             '|---|---:|---:|---:|---:|---:|']
    for mode in MODES:
        group = [r for r in rows if r['yield_mode'] == mode]
        lines.append(f'| {mode} | {min(r["rejection_fraction"] for r in group):.3%}–{max(r["rejection_fraction"] for r in group):.3%} | '
                     f'{min(r["timeout_fraction"] for r in group):.3%}–{max(r["timeout_fraction"] for r in group):.3%} | '
                     f'{median_text(group, "successful_rps", ".2f")} | {median_text(group, "p99_e2e_ms", ".3f")} | {median_text(group, "cpu_usec_per_completed_work", ".1f")} |')
    lines += ['', '| Traced mode | Median cleanup wait p99 ms | Median waits ≥1 ms | Median reader Runnable share |',
              '|---|---:|---:|---:|']
    for mode in ('trace', 'yield_trace'):
        group = [r for r in rows if r['yield_mode'] == mode]
        lines.append(f'| {mode} | {median_text(group, "cleanup_wait_p99_ms", ".3f")} | {median_text(group, "cleanup_waits_at_least_1ms", ".1f")} | {median_text(group, "cleanup_reader_runnable_share", ".4%")} |')
    lines += ['', 'Within each balanced block, contrasts.csv reports the tracing penalty with and without yielding, the yield effect with tracing off/on, and their difference (interaction). Fractions are unitless; multiply by 100 for percentage points. Four blocks are descriptive, not a definitive causal estimate.', '',
              'Lower rejection together with shorter helper waits and a smaller tracing penalty would support the scheduling hypothesis. Improved successful latency alone is insufficient, and throughput or CPU penalties must be assessed. Both tracing-off cells still have custom recording; this does not establish suitability for an uninstrumented service.', '',
              'Trace-off helper scheduler state is unavailable, not zero. Cleanup wait counts include only observed Cond waits; each JSON retains excluded/missing associations. State-duration sums overlap and Go Running is not measured CPU execution.', '',
              'No pilot_gate.json is written. The original qualification workload and acceptance thresholds are unchanged; any eventual candidate needs a separately planned fresh qualification pilot.', '']
    (out/'report.md').write_text('\n'.join(lines))
    runner.put(out/'yield_summary.json', dict(eligible_for_full=False, completion_sha256=seals,
                                             mode_count=4, trials=16))
    print('STUDY COMPLETE:', out/'report.md', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    analyze_yield(parser.parse_args().session.resolve())
