#!/usr/bin/env python3
"""Validate all trials and compare scheduling, failures and throughput together."""
import argparse
from pathlib import Path
import statistics as stats

import analyze
import fairness_study as study
import inspect_http_cleanup
import inspect_long_wait_events as raw_events
import inspect_yield_queue as queue
import run
import trace_analysis

FIELDS=('rejection_fraction','timeout_fraction','error_fraction','successful_rps',
        'cpu_usec_per_completed_work','client_cpu_usec_per_scheduled','p50_e2e_ms','p99_e2e_ms',
        'p99_queue_ms','p99_post_work_ms','network_ready_p99_ms','cleanup_wait_p99_ms')


def contrasts(rows):
    result=[]
    for block in range(1,5):
        group=[r for r in rows if r['rep']==block]
        cells={r['runtime_mode']:r for r in group}
        if len(group)!=4 or set(cells)!=set(study.MODES):
            raise ValueError('incomplete or duplicate fairness block')
        row=dict(block=block)
        for field in FIELDS:
            def diff(a,b):
                x,y=cells[a][field],cells[b][field]
                return x-y if x is not None and y is not None else None
            row[field+'_patch_effect_trace_off']=diff('patched_off','stock_off')
            row[field+'_patch_effect_trace_on']=diff('patched_on','stock_on')
            row[field+'_trace_effect_stock']=diff('stock_on','stock_off')
            row[field+'_trace_effect_patched']=diff('patched_on','patched_off')
            a,b=row[field+'_trace_effect_patched'],row[field+'_trace_effect_stock']
            row[field+'_interaction']=a-b if a is not None and b is not None else None
        result.append(row)
    return result


def comparison(rows,treatment,reference):
    groups={mode:[r for r in rows if r['runtime_mode']==mode] for mode in (treatment,reference)}
    if any(len(g)!=4 or {r['rep'] for r in g}!={1,2,3,4} for g in groups.values()):
        raise ValueError('comparison requires four distinct repetitions in each arm')
    def ratio(field):
        values=[[r[field] for r in groups[m]] for m in (treatment,reference)]
        if any(v is None or v<=0 for g in values for v in g):return None
        return stats.median(values[0])/stats.median(values[1])
    ratios={f:ratio(f) for f in ('cpu_usec_per_completed_work','client_cpu_usec_per_scheduled','p99_e2e_ms','successful_rps')}
    failures={m:max(r['rejection_fraction']+r['timeout_fraction'] for r in g) for m,g in groups.items()}
    checks={f+'_ratio_at_most_1_10':ratios[f] is not None and ratios[f]<=1.10
            for f in ('cpu_usec_per_completed_work','client_cpu_usec_per_scheduled','p99_e2e_ms')}
    checks['failure_rate_difference_at_most_0_001']=failures[treatment]<=failures[reference]+.001
    checks['client_trace_coverage_at_least_0_99']=all(r['trace_coverage'] is not None and r['trace_coverage']>=.99
                                                    for g in groups.values() for r in g)
    timing=('p99_pre_admission_ms','p99_post_work_ms','p99_resume_to_write_ms','p99_write_call_ms',
            'p99_write_to_exit_ms','p99_request_to_first_byte_ms','p99_first_byte_to_body_done_ms')
    checks['all_diagnostic_timing_observed']=all(r.get(field) is not None for g in groups.values()
                                              for r in g for field in timing)
    checks['all_enabled_traces_complete']=all(r.get('runtime_trace_complete') is True
                                             for g in groups.values() for r in g if r.get('runtime_trace'))
    return dict(treatment=treatment,reference=reference,ratios=ratios,max_rejection_plus_timeout=failures,
                checks=checks,original_numeric_screens_passed=all(checks.values()),
                throughput_review_required=True,eligible_for_full=False)


def screens(rows):
    return dict(eligible_for_full=False,limits=dict(cpu_ratio=1.10,client_cpu_ratio=1.10,p99_ratio=1.10,
                 failure_fraction_difference=.001,client_trace_coverage=.99),
                patch_trace_off=comparison(rows,'patched_off','stock_off'),
                patch_trace_on=comparison(rows,'patched_on','stock_on'),
                tracing_stock=comparison(rows,'stock_on','stock_off'),
                tracing_patched=comparison(rows,'patched_on','patched_off'),
                interpretation='Original numeric limits applied descriptively to four balanced repetitions; '
                'this is not the existing six-trial qualification pilot. Throughput and errors require review. '
                'No gate file or full-collection eligibility is created.')


def network_waits(parsed_path,trace):
    """Describe HTTP network-read wakeups over the retained capture.

    Includes idle/close wakeups; these are scheduler waits, not per-request
    latency or an exact pre-handler partition. Trace-off is unavailable.
    """
    rows=[e for e in raw_events.events(parsed_path) if e is not None]
    http={r['handler_g'] for r in trace['all_requests'] if 'handler_g' in r}
    workers={r['worker_g'] for r in trace['all_requests'] if 'worker_g' in r}
    matched,missing=raw_events.wakeup_latencies(rows,rows[0]['time_ns'],rows[-1]['time_ns']+1,workers,http,set())
    cohort=[r for r in matched if r['category']=='no_P_network_to_http']
    unresolved=[r for r in missing if r['category']=='no_P_network_to_http']
    values=[r['latency_ns']/1e6 for r in cohort]
    return dict(network_ready_count=len(values),network_ready_unresolved_count=len(unresolved),
                network_ready_p50_ms=queue.percentile(values,50),network_ready_p99_ms=queue.percentile(values,99),
                network_ready_max_ms=max(values) if values else None,
                longest_examples=sorted(cohort,key=lambda r:r['latency_ns'],reverse=True)[:10],
                unresolved_examples=unresolved,
                limitations='HTTP goroutines identified from observed handlers; includes network-read idle/close wakes. '
                'Actual wake to first run is one runtime clock, not CPU time or a request latency partition.')


def analyze_session(session):
    meta=study.verify_frozen(session)
    out=session/'analysis';out.mkdir(exist_ok=True)
    run.put(out/'validation.json',dict(passed=False,issues=['analysis not complete']))
    rows,audit,issues,seals=[],[],[],{}
    decoder=session/'tools/go-trace'
    for order,config in enumerate(run.read(session/'matrix.json'),1):
        good=[]
        for directory in run.attempt_dirs(session/'attempts'/config['run_id']):
            errors=run.validation_errors(directory,config,False)
            audit.append(dict(run_id=config['run_id'],attempt=directory.name,valid=not errors,errors='; '.join(errors)))
            if not errors:good.append(directory)
        if len(good)!=1:
            issues.append(f'{config["run_id"]}: {len(good)} valid attempts');continue
        directory=good[0];row=analyze.trial_row(order,config,directory)
        lg=run.read(directory/'loadgen.json');srv=run.read(directory/'server_metrics.json')
        row.update(runtime_mode=config['runtime_mode'],runtime_variant=config['runtime_variant'],
                   service_image=config['service_image'],worker_yield=False,
                   scheduled=lg['total_scheduled'],success=lg['total_success'],rejected=lg['total_503'],
                   timeouts=sum(r['TimedOut'] for r in lg['requests']),errors=lg['total_errors'],completed_jobs=srv['completed'],
                   error_fraction=lg['total_errors']/lg['total_scheduled'],
                   all_failure_fraction=(lg['total_503']+lg['total_errors'])/lg['total_scheduled'])
        row.update(network_ready_count=None,network_ready_unresolved_count=None,network_ready_p50_ms=None,
                   network_ready_p99_ms=None,network_ready_max_ms=None,cleanup_wait_p99_ms=None,
                   cleanup_wait_max_ms=None,cleanup_waits_matched=None)
        if config['runtime_trace']:
            print('SCHEDULER ANALYSIS:',config['run_id'],flush=True)
            dumps=out/'parsed';dumps.mkdir(exist_ok=True)
            path=dumps/(config['run_id']+'.txt')
            try:
                with path.open('w') as stream:
                    run.sp.run([str(decoder),'-d=parsed',str(directory/'runtime.trace')],stdout=stream,check=True)
                with path.open() as stream:
                    if trace_analysis.parse_lines(stream)!=run.read(directory/'trace_scheduler.json'):
                        raise ValueError('raw dump differs from sealed scheduler')
                cleanup=inspect_http_cleanup.inspect(directory,path)
                run.put(out/(config['run_id']+'_http_cleanup.json'),cleanup)
                waits=network_waits(path,run.read(directory/'trace_requests.json'))
                run.put(out/(config['run_id']+'_network_ready.json'),waits)
                row.update({k:v for k,v in waits.items() if k.startswith('network_ready_')})
                row.update(cleanup_wait_p99_ms=cleanup['wait_ms']['p99'],cleanup_wait_max_ms=cleanup['max_wait_ms'],
                           cleanup_waits_matched=cleanup['requests_matched'])
            except (ValueError,OSError,run.sp.CalledProcessError) as exc:
                issues.append(config['run_id']+': scheduler analysis: '+str(exc))
        rows.append(row);seals[config['run_id']]=run.sha(directory/'complete.json')
    analyze.writecsv(out/'attempt_audit.csv',audit)
    if len(rows)!=16:issues.append(f'{len(rows)} of 16 trials available')
    if issues:
        run.put(out/'validation.json',dict(passed=False,issues=issues,eligible_for_full=False))
        raise RuntimeError('; '.join(issues))
    analyze.writecsv(out/'trials.csv',rows);analyze.writecsv(out/'contrasts.csv',contrasts(rows))
    review=screens(rows);run.put(out/'screens.json',review)
    def med(group,key,spec='.3f'):
        values=[r[key] for r in group if r[key] is not None]
        return format(stats.median(values),spec) if values else 'NA'
    lines=['# Stock versus patched Go runtime: final comparison','',
           'All 16 trials validated. Completion does not establish a successful correction.', '',
           'The only treatments are stock/patched runtime and runtime tracing off/on. Worker yielding is off throughout. '
           'Original work, quota, queue, client bursts, timing and host controls are fixed.', '',
           '| Mode | Rejection range | Timeout range | Total errors (includes timeouts) | Median successful req/s | Median successful p99 ms | Median CPU µs/job |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for mode in study.MODES:
        g=[r for r in rows if r['runtime_mode']==mode]
        lines.append(f'| {mode} | {min(r["rejection_fraction"] for r in g):.3%}–{max(r["rejection_fraction"] for r in g):.3%} | '
          f'{min(r["timeout_fraction"] for r in g):.3%}–{max(r["timeout_fraction"] for r in g):.3%} | {sum(r["errors"] for r in g)} | '
          f'{med(g,"successful_rps",".2f")} | {med(g,"p99_e2e_ms")} | {med(g,"cpu_usec_per_completed_work",".1f")} |')
    lines+=['','| Traced runtime | Median trial HTTP network-ready p99 ms | Median trial cleanup wait p99 ms |',
            '|---|---:|---:|']
    for mode in ('stock_on','patched_on'):
        g=[r for r in rows if r['runtime_mode']==mode]
        lines.append(f'| {mode} | {med(g,"network_ready_p99_ms")} | {med(g,"cleanup_wait_p99_ms")} |')
    lines+=['','## Original numeric performance screens','',
            'These four-repetition screens use the original thresholds but are not the six-trial qualification pilot. '
            'Throughput is reported for review, and lower successful latency alone does not establish success.', '',
            '| Comparison | CPU/job ratio | Client CPU/request ratio | Successful p99 ratio | Throughput ratio | Numeric screens |',
            '|---|---:|---:|---:|---:|---|']
    for label in ('patch_trace_off','patch_trace_on','tracing_stock','tracing_patched'):
        s=review[label];rr=s['ratios']
        fmt=lambda value:format(value,'.4f') if value is not None else 'NA'
        lines.append(f'| {label} | {fmt(rr["cpu_usec_per_completed_work"])} | {fmt(rr["client_cpu_usec_per_scheduled"])} | '
                     f'{fmt(rr["p99_e2e_ms"])} | {fmt(rr["successful_rps"])} | {"PASS" if s["original_numeric_screens_passed"] else "FAIL"} |')
    lines+=['','Thresholds: CPU/job, client CPU/request and successful p99 ratios ≤1.10; maximum rejection-plus-timeout '
            'fraction difference ≤0.001; client trace coverage ≥99%. See screens.json for each individual check.', '',
            'Within-block contrasts are saved without pooling requests as independent trials. Four blocks remain descriptive.', '',
            'Network-ready summaries include HTTP network-read idle/close wakeups; they are same-clock scheduler waits, not '
            'a partition of individual request latency. Trace-off scheduler data is unavailable, not zero. Go Running state '
            'is not measured CPU execution. Errors include timeouts and must not be added to timeout counts twice.', '',
            'Wakeups without a first run before capture ended are counted as unresolved in trials.csv and retained '
            'in the network-ready files. Percentiles cover matched wakeups only; review unresolved examples alongside them.', '',
            'Assess the patched/tracing-off solution against stock/tracing-off, and assess tracing perturbation within each '
            'runtime separately. A shorter wait paired with worse failures or throughput is a tradeoff. No larger collection '
            'or qualification gate is created automatically.','']
    (out/'report.md').write_text('\n'.join(lines))
    run.put(out/'summary.json',dict(trials=16,completion_sha256=seals,eligible_for_full=False))
    run.put(out/'validation.json',dict(passed=True,issues=[],trials=16,eligible_for_full=False))
    print('FAIRNESS ANALYSIS COMPLETE:',out/'report.md',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('session',type=Path)
    analyze_session(parser.parse_args().session.resolve())
