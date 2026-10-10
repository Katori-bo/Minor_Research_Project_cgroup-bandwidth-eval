#!/usr/bin/env python3
"""Component comparison only: never writes a passing pilot gate."""
import statistics
import run as runner
import analyze

MODES = ('baseline', 'runtime', 'custom', 'combined')


def contrasts(rows):
    """Within-block differences; retain failures and separate successful latency."""
    fields = ('rejection_fraction', 'timeout_fraction', 'error_fraction',
              'cpu_usec_per_completed_work', 'client_cpu_usec_per_scheduled',
              'p99_e2e_ms', 'p99_queue_ms', 'p99_processing_ms', 'p99_post_work_ms')
    result = []
    for block in range(1, 5):
        cells = {r['component_mode']: r for r in rows if r['rep'] == block}
        if set(cells) != set(MODES): raise ValueError('incomplete component block')
        for mode in MODES[1:]:
            row = dict(block=block, mode=mode)
            for field in fields:
                a, b = cells[mode][field], cells['baseline'][field]
                row[field+'_minus_baseline'] = a-b if a is not None and b is not None else None
            result.append(row)
    return result


def analyze_components(session):
    meta = runner.verify_session(session, check_current=False)
    if not meta.get('components'): raise ValueError('not a component session')
    out = session / 'analysis'
    out.mkdir(exist_ok=True)
    rows, audit, issues, seals = [], [], [], {}
    for order, config in enumerate(runner.read(session / 'matrix.json'), 1):
        good = []
        for d in runner.attempt_dirs(session / 'attempts' / config['run_id']):
            errors = runner.validation_errors(d, config, False)
            audit.append(dict(run_id=config['run_id'], attempt=d.name,
                              valid=not errors, errors='; '.join(errors)))
            if not errors: good.append(d)
        if len(good) != 1:
            issues.append(f'{config["run_id"]}: {len(good)} valid attempts')
            continue
        d = good[0]
        row = analyze.trial_row(order, config, d)
        lg = runner.read(d / 'loadgen.json')
        row.update(component_mode=config['component_mode'],
                   custom_recording=runner.custom_recording(config),
                   error_fraction=lg['total_errors']/lg['total_scheduled'])
        # Runtime-only has no request association, not zero matched requests.
        if not (config['runtime_trace'] and runner.custom_recording(config)):
            for key in ('matched_slow_count', 'matched_typical_count', 'matched_slow_with_socket_write'):
                row[key] = None
        if runner.custom_recording(config):
            status = runner.read(d / 'trace_status.json')
            row.update(io_events=len(status['io_events']), io_events_dropped=status['io_events_dropped'])
        rows.append(row)
        seals[config['run_id']] = runner.sha(d / 'complete.json')
    analyze.writecsv(out / 'attempt_audit.csv', audit)
    runner.put(out / 'validation.json', dict(passed=not issues and len(rows)==16, issues=issues))
    # Deliberately no pilot_gate.json: this study cannot authorize full collection.
    if issues or len(rows) != 16: raise SystemExit('Incomplete component study: ' + '; '.join(issues))
    analyze.writecsv(out / 'trials.csv', rows)
    analyze.writecsv(out / 'contrasts.csv', contrasts(rows))
    lines = ['# Tracing component comparison', '',
             'Diagnostic evidence only. This is not a passed pilot and cannot unlock full collection.', '',
             'Base server/client timing stays enabled in every mode. Runtime-only has no request-level scheduler association or final-flush guarantee. Custom-only has no scheduler evidence. Only combined mode receives full lifecycle analysis.', '',
             '| Mode | Rejection range | Error range (includes timeouts) | Median successful p99 ms | Median CPU µs/completed work |',
             '|---|---:|---:|---:|---:|']
    for mode in MODES:
        group = [r for r in rows if r['component_mode']==mode]
        def med(key):
            values = [r[key] for r in group if r[key] is not None]
            return statistics.median(values) if values else float('nan')
        lines.append(f'| {mode} | {min(r["rejection_fraction"] for r in group):.3%}–{max(r["rejection_fraction"] for r in group):.3%} | '
                     f'{min(r["error_fraction"] for r in group):.3%}–{max(r["error_fraction"] for r in group):.3%} | '
                     f'{med("p99_e2e_ms"):.3f} | {med("cpu_usec_per_completed_work"):.1f} |')
    lines += ['', 'Inspect per-trial results and within-block differences in contrasts.csv; four repeats are descriptive, not a causal verdict. Lower successful-request latency with more failures is not an improvement.', '',
              'Host monitor retains per-core utilization and process interval CPU deltas. Deltas exclude processes missing at either endpoint; last_cpu is a sample, not interval core attribution.', '',
              'Choose any optimization only after reviewing scheduler waits and component differences, then validate it in a fresh six-trial pilot with the unchanged gates.', '']
    (out / 'report.md').write_text('\n'.join(lines))
    runner.put(out / 'component_summary.json', dict(eligible_for_full=False, completion_sha256=seals,
                                                   mode_count=4, trials=16))
    print(out / 'report.md')


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    analyze_components(parser.parse_args().session.resolve())
