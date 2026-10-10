#!/usr/bin/env python3
"""Read-only V12 input audit of deadline misses after the worker-work marker.

Writes only new offline review outputs. All deadline choices are exploratory.
This classifies timing opportunities, not counterfactual avoidable misses.
"""
import csv
import hashlib
import json
from pathlib import Path
import statistics

import audit_tradeoff as audit

HERE = Path(__file__).resolve().parent
DEADLINES_MS = (100, 500, 1000)


def main():
    before = audit.hashes()
    audit.study.verify_completion(audit.RESULT)
    completion = audit.read(audit.RESULT / 'completion.json')
    trials, examples = [], []
    prefix_checked = 0
    for config in audit.read(audit.RESULT / 'session/matrix.json'):
        run_id = config['run_id']
        directory = (audit.RESULT / 'session/attempts' / run_id /
                     completion['attempts'][run_id]['attempt'])
        client = audit.read(directory / 'loadgen.json')
        server = audit.read(directory / 'server_metrics.json')
        entry = audit.pa.entry_analysis(client, server)
        mapping = entry['mapping']
        entries = {r['id']: r for r in entry['requests']}
        jobs = {r['id']: r for r in server['events']}
        handlers = {r['id']: r for r in server['handler_events']}

        def bounds(timestamp):
            return (timestamp - mapping['server_minus_client_upper_ns'] -
                    mapping['client_test_start_ns'],
                    timestamp - mapping['server_minus_client_lower_ns'] -
                    mapping['client_test_start_ns'])

        # Independent timestamp-prefix identity, rather than only classification counts.
        for request in client['requests']:
            rid = request['ID']
            if entries[rid]['outcome'] != 'success':
                continue
            job, handler = jobs[rid], handlers[rid]
            lo, hi = bounds(job['completion_ns'])
            prefix = handler['pre_admission_ns'] + job['queue_wait_ns'] + job['processing_ns']
            assert lo - request['ScheduledOffsetNs'] == entries[rid]['scheduled_to_entry_lower_ns'] + prefix
            assert hi - request['ScheduledOffsetNs'] == entries[rid]['scheduled_to_entry_upper_ns'] + prefix
            prefix_checked += 1

        for deadline_ms in DEADLINES_MS:
            counts = dict(offered=len(client['requests']), timely_success=0,
                          missed=0, missed_not_admitted=0,
                          missed_work_certainly_after_deadline=0,
                          missed_work_boundary_ambiguous=0,
                          missed_work_certainly_before_deadline=0,
                          missed_resume_certainly_after_deadline_given_work_before=0)
            margins = {ms: 0 for ms in (1, 10, 25, 50, 100)}
            for request in client['requests']:
                rid = request['ID']
                outcome = entries[rid]['outcome']
                if (outcome == 'success' and request['EndToEndLatencyNs'] <=
                        deadline_ms * 1_000_000):
                    counts['timely_success'] += 1
                    continue
                counts['missed'] += 1
                job = jobs.get(rid)
                assert (job is not None) == entries[rid]['admitted']
                if job is None:
                    counts['missed_not_admitted'] += 1
                    continue
                deadline = request['ScheduledOffsetNs'] + deadline_ms * 1_000_000
                work_lo, work_hi = bounds(job['completion_ns'])
                if work_hi <= deadline:
                    counts['missed_work_certainly_before_deadline'] += 1
                    for margin_ms in margins:
                        margins[margin_ms] += work_hi <= deadline - margin_ms * 1_000_000
                    handler = handlers.get(rid)
                    resume_lo, resume_hi = bounds(handler['resume_ns']) if handler else (None, None)
                    resume_after = resume_lo is not None and resume_lo > deadline
                    counts['missed_resume_certainly_after_deadline_given_work_before'] += resume_after
                    examples.append(dict(run_id=run_id, block=config['rep'],
                        gomaxprocs=config['gomaxprocs'], request_id=rid,
                        deadline_ms=deadline_ms, outcome=outcome,
                        scheduled_phase=audit.phase(request['ScheduledOffsetNs']),
                        scheduled_ns=request['ScheduledOffsetNs'], deadline_ns=deadline,
                        work_completion_lower_ns=work_lo, work_completion_upper_ns=work_hi,
                        handler_resume_lower_ns=resume_lo, handler_resume_upper_ns=resume_hi,
                        client_terminal_ns=request['CompletedOffsetNs'],
                        work_margin_certain_ms=(deadline-work_hi)/1_000_000,
                        resume_certainly_after_deadline=resume_after,
                        post_work_wait_ms=handler['post_work_wait_ns']/1_000_000 if handler else None))
                elif work_lo > deadline:
                    counts['missed_work_certainly_after_deadline'] += 1
                else:
                    counts['missed_work_boundary_ambiguous'] += 1
            assert counts['timely_success'] + counts['missed'] == counts['offered']
            assert counts['missed'] == sum(counts[k] for k in (
                'missed_not_admitted', 'missed_work_certainly_after_deadline',
                'missed_work_boundary_ambiguous', 'missed_work_certainly_before_deadline'))
            trials.append(dict(run_id=run_id, block=config['rep'],
                               gomaxprocs=config['gomaxprocs'], deadline_ms=deadline_ms,
                               clock_uncertainty_ns=mapping['uncertainty_ns'], **counts,
                               work_before_deadline_margin_counts=margins))
    arms = []
    count_keys = [k for k in trials[0] if k in counts]
    for parallelism in (2, 1):
        for deadline in DEADLINES_MS:
            rows = [r for r in trials if r['gomaxprocs'] == parallelism and r['deadline_ms'] == deadline]
            total = {k: sum(r[k] for r in rows) for k in count_keys}
            total['work_before_deadline_margin_counts'] = {
                ms: sum(r['work_before_deadline_margin_counts'][ms] for r in rows)
                for ms in (1, 10, 25, 50, 100)}
            arms.append(dict(gomaxprocs=parallelism, deadline_ms=deadline,
                totals=total, median_trial_timely_success_fraction=statistics.median(
                    r['timely_success']/r['offered'] for r in rows),
                fraction_all_offered_work_before_but_missed=total['missed_work_certainly_before_deadline']/total['offered'],
                fraction_misses_work_before=total['missed_work_certainly_before_deadline']/total['missed']))
    after = audit.hashes()
    assert before == after, 'Original result inputs changed during review.'
    output = dict(status='exploratory_offline_review', source=str(audit.RESULT),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        dependency_sha256=hashlib.sha256(Path(audit.__file__).read_bytes()).hexdigest(),
        checks=dict(completion_seals_verified=True, input_hashes_unchanged=True,
                    mutually_exclusive_miss_accounting=True,
                    independent_prefix_identity_checked_successes=prefix_checked),
        deadlines_ms=DEADLINES_MS, trials=trials, arms=arms,
        input_hashes=before,
        limitations=['Worker completion precedes event storage and reply publication.',
            'An opportunity count is not an estimate of preventable deadline misses.',
            'A resume marker records handler execution, not its runnable transition.',
            'Deadlines and margin thresholds were chosen after collecting the data.',
            'Aggregate counts do not create independent request-level replicates.'])
    (HERE/'deadline_after_work.json').write_text(json.dumps(output, indent=2)+'\n')
    with (HERE/'deadline_after_work_requests.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(examples[0]))
        writer.writeheader()
        writer.writerows(examples)
    for arm in arms:
        print(json.dumps({k:v for k,v in arm.items() if k!='totals'}))
        print(json.dumps(arm['totals']))


if __name__ == '__main__':
    main()
