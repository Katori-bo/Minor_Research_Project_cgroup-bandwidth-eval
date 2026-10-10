#!/usr/bin/env python3
"""Recover request metrics into a fresh report without qualifying scheduler timing.

The original workflow, failed analysis, frozen sources and raw attempts are
read-only inputs. This does not launch collection or mark the study complete.
"""
import argparse
from pathlib import Path
import statistics

import analyze
import fairness_analysis as fairness
import fairness_study as study
import inspect_http_cleanup as cleanup
import run
import trace_analysis


def recover(session, output):
    if output.exists() or output.is_relative_to(session):
        raise ValueError('recovery output must be fresh and outside the frozen session')
    study.verify_frozen(session)
    plan = run.read(session / 'matrix.json')
    if len(plan) != 16 or len({c['run_id'] for c in plan}) != 16:
        raise ValueError('expected 16 distinct trials')
    selected, audit = [], []
    for config in plan:
        good = []
        for attempt in run.attempt_dirs(session / 'attempts' / config['run_id']):
            errors = run.validation_errors(attempt, config, False)
            audit.append(dict(run_id=config['run_id'], attempt=attempt.name,
                              valid=not errors, errors='; '.join(errors)))
            if not errors:
                good.append(attempt)
        if len(good) != 1:
            raise ValueError(f'{config["run_id"]}: {len(good)} valid attempts')
        selected.append((config, good[0]))
    # Hash every sealed input before and after recovery, including runtime traces.
    inputs = {str(p.relative_to(session)): run.sha(p)
              for _, attempt in selected for p in attempt.rglob('*') if p.is_file()}
    rows, scheduler_audit = [], []
    for order, (config, attempt) in enumerate(selected, 1):
        print('RECOVER REQUEST METRICS:', config['run_id'], flush=True)
        row = analyze.trial_row(order, config, attempt)
        lg, server = run.read(attempt / 'loadgen.json'), run.read(attempt / 'server_metrics.json')
        row.update(runtime_mode=config['runtime_mode'], runtime_variant=config['runtime_variant'],
                   worker_yield=False, service_image=config['service_image'],
                   rejected=lg['total_503'], timeouts=sum(q['TimedOut'] for q in lg['requests']),
                   errors=lg['total_errors'], completed_jobs=server['completed'],
                   error_fraction=lg['total_errors'] / lg['total_scheduled'],
                   all_failure_fraction=(lg['total_503'] + lg['total_errors']) / lg['total_scheduled'])
        row.update(network_ready_p99_ms=None, cleanup_wait_p99_ms=None)
        rows.append(row)
        if not config['runtime_trace']:
            continue
        dump = session / 'analysis/parsed' / (config['run_id'] + '.txt')
        parsed, requests = run.read(attempt / 'trace_scheduler.json'), run.read(attempt / 'trace_requests.json')
        with dump.open() as stream:
            if trace_analysis.parse_lines(stream) != parsed:
                raise ValueError('parsed dump differs from sealed scheduler evidence')
        with dump.open() as stream:
            index = cleanup.index_events(stream)
        item = dict(run_id=config['run_id'], parsed_sha256=run.sha(dump),
                    clock_mapping=requests['clock_mapping'])
        try:
            result = cleanup.join(parsed, requests, server, index)
            item.update(cleanup_join_passed=True, requests_matched=result['requests_matched'])
        except ValueError as exc:
            item.update(cleanup_join_passed=False, error=str(exc))
            if str(exc) == 'cleanup wake follows final connection boundary':
                tb = exc.__traceback__
                while tb and tb.tb_frame.f_code.co_name != 'join':
                    tb = tb.tb_next
                if tb:
                    loc = tb.tb_frame.f_locals
                    request = loc['request']
                    end = request['intervals']['handler_exit_to_connection_done']['end_ns'] + loc['offset']
                    item.update(request_id=request['id'], handler_g=loc['handler'],
                                wait_start_ns=loc['begin'], decoded_wake_ns=loc['finish'],
                                mapped_connection_done_ns=end, overshoot_ns=loc['finish']-end)
        scheduler_audit.append(item)
    contrasts = fairness.contrasts(rows)
    review = fairness.screens(rows)
    for item in review.values():
        if isinstance(item, dict) and 'checks' in item:
            item['scope'] = 'request-metric screens only; scheduler timing unresolved'
    if any(run.sha(session / path) != digest for path, digest in inputs.items()):
        raise ValueError('raw inputs changed during recovery')
    output.mkdir(parents=True, exist_ok=False)
    analyze.writecsv(output / 'trials.csv', rows)
    analyze.writecsv(output / 'contrasts.csv', contrasts)
    analyze.writecsv(output / 'attempt_audit.csv', audit)
    run.put(output / 'screens.json', review)
    run.put(output / 'scheduler_audit.json', scheduler_audit)
    run.put(output / 'provenance.json', dict(session=str(session), raw_sha256=inputs,
        recovery_source_sha256=run.sha(Path(__file__)), analysis_sources=run.provenance(),
        raw_inputs_unchanged=True, workflow_changed=False))
    run.put(output / 'recovery_status.json', dict(state='partial_request_metrics_recovered',
        original_analysis_passed=False, request_metrics_revalidated=16,
        scheduler_timing_qualified=False, eligible_for_full=False, recovered_at=run.now()))
    def med(group, key, spec='.3f'):
        return format(statistics.median(r[key] for r in group), spec)
    lines = ['# Recovered request metrics — scheduler analysis unresolved', '',
        'All 16 saved attempts pass the existing sealed-input, workload, environment and request-accounting checks. '
        'Their raw files were hashed before and after recovery and are unchanged. The original workflow remains failed.', '',
        'This is a partial report. Scheduler cleanup joins fail in two stock/tracing-on trials. '
        'Scheduler wait estimates are omitted for every cell pending investigation. No collection was rerun, '
        'no acceptance threshold changed, and no completed-study or qualification gate was created.', '',
        '| Mode | Rejection range | Timeout range | Total errors including timeouts | Median successful req/s | Median successful p99 ms | Median CPU µs/job |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for mode in study.MODES:
        group = [r for r in rows if r['runtime_mode'] == mode]
        lines.append(f'| {mode} | {min(r["rejection_fraction"] for r in group):.3%}–{max(r["rejection_fraction"] for r in group):.3%} | '
            f'{min(r["timeout_fraction"] for r in group):.3%}–{max(r["timeout_fraction"] for r in group):.3%} | '
            f'{sum(r["errors"] for r in group)} | {med(group,"successful_rps",".2f")} | '
            f'{med(group,"p99_e2e_ms")} | {med(group,"cpu_usec_per_completed_work",".1f")} |')
    lines += ['', '| Comparison | CPU/job ratio | Client CPU/request ratio | Successful p99 ratio | Throughput ratio | Request-metric screens |',
              '|---|---:|---:|---:|---:|---|']
    for label in ('patch_trace_off', 'patch_trace_on', 'tracing_stock', 'tracing_patched'):
        screen = review[label]
        ratios = screen['ratios']
        fmt = lambda v: format(v, '.4f') if v is not None else 'NA'
        lines.append(f'| {label} | {fmt(ratios["cpu_usec_per_completed_work"])} | '
            f'{fmt(ratios["client_cpu_usec_per_scheduled"])} | {fmt(ratios["p99_e2e_ms"])} | '
            f'{fmt(ratios["successful_rps"])} | {"PASS" if screen["original_numeric_screens_passed"] else "FAIL"} |')
    lines += ['', 'Original descriptive limits: CPU/job, client CPU/request and successful p99 ratios ≤1.10; '
        'maximum rejection-plus-timeout difference ≤0.001; client trace coverage ≥99%. '
        'Four balanced blocks are descriptive and do not replace the six-trial qualification pilot. '
        'Errors include timeouts; do not count them twice. Successful p99 excludes rejected and failed requests.', '',
        '## Scheduler evidence mismatch', '']
    for item in scheduler_audit:
        if not item['cleanup_join_passed']:
            lines.append(f'- {item["run_id"]}: {item["error"]}; request {item.get("request_id")}; '
                f'decoded wake overshoots the mapped boundary by {item.get("overshoot_ns",0)/1e6:.3f} ms '
                f'versus clock-map uncertainty {item["clock_mapping"]["uncertainty_ns"]} ns.')
    lines += ['', 'The large mismatch cannot be explained by the saved clock-map uncertainty. '
        'The decoded stream contains sequences of events spaced by only a few nanoseconds near these mismatches. '
        'Timestamp adjustment by the Go decoder is a candidate explanation, not an established cause. '
        'The [Go trace reader](https://go.dev/src/internal/trace/reader.go) enforces increasing event timestamps; '
        'raw wire events and the exact pinned reader must be checked before using these scheduler durations.', '',
        'Next: diagnose the decoded scheduler timestamps against raw wire events and service-local boundaries. '
        'Keep the original failed validation visible. Decide on any new measurement only after that audit.','']
    (output / 'report.md').write_text('\n'.join(lines))
    print('PARTIAL RECOVERY:', output / 'report.md', flush=True)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('session', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    recover(args.session.resolve(), args.output.resolve())
