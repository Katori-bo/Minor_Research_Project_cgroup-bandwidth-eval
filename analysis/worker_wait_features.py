"""Offline worker counter contract; no procfs reads, traffic, or predictor fitting."""
from fractions import Fraction


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonnegative_int(value, name):
    require(type(value) is int and value >= 0, 'Invalid ' + name)


def parse_schedstat(text):
    fields = text.split()
    require(len(fields) == 3 and all(x.isascii() and x.isdecimal() for x in fields),
            'Expected three unsigned schedstat fields')
    return dict(zip(('running_ns', 'runnable_wait_ns', 'timeslices'), map(int, fields)))


def select_worker(scan, executable_sha256):
    """Select the guarded single worker by parent relationship, never PID ordering."""
    require(not scan['vanished_during_scan'], 'Process vanished during scan')
    processes = scan['processes']
    require(len(processes) == 2 and len({p['pid'] for p in processes}) == 2,
            'Expected exactly two distinct master/worker processes')
    main = scan['main_pid']
    masters = [p for p in processes if p['pid'] == main]
    workers = [p for p in processes if p['pid'] != main and p['parent'] == main]
    require(len(masters) == len(workers) == 1, 'Ambiguous master/worker relationship')
    for p in processes:
        require(p['tids'] == [p['pid']] and p['affinity'] == [2] and
                p['exe_sha256'] == executable_sha256, 'Foreign worker topology/binary')
        nonnegative_int(p['start_ticks'], 'process start ticks')
    return {k: workers[0][k] for k in ('pid', 'start_ticks', 'parent', 'exe_sha256')}


def interval(before, after, offered, accounting_qualified):
    """Only acquired interval records. A sysctl value alone is not qualification."""
    require(accounting_qualified is True, 'Worker accounting has not been qualified')
    require(type(offered) is int and offered > 0, 'Positive scheduled-offer count required')
    require(before['identity'] == after['identity'], 'Worker identity changed')
    require(before['read_started_ns'] <= before['read_finished_ns'] <=
            after['read_started_ns'] <= after['read_finished_ns'] and
            before['read_started_ns'] < after['read_finished_ns'], 'Counter read boundaries reversed')
    for snapshot in (before, after):
        for key in ('read_started_ns', 'read_finished_ns'):
            nonnegative_int(snapshot[key], key)
        require(snapshot['identity_before'] == snapshot['identity'] == snapshot['identity_after'],
                'Worker identity raced during counter read')
        for k in ('running_ns', 'runnable_wait_ns', 'timeslices'):
            nonnegative_int(snapshot['counters'][k], k)
    delta = {k: after['counters'][k] - before['counters'][k]
             for k in ('running_ns', 'runnable_wait_ns', 'timeslices')}
    require(all(x >= 0 for x in delta.values()), 'Counter reset or reversal')
    require(delta['running_ns'] + delta['runnable_wait_ns'] > 0,
            'No observed worker activity; feature unavailable, not evidence of zero contention')
    return dict(offered=offered, delta=delta,
                running_ns_per_offer=delta['running_ns'] / offered,
                runnable_wait_ns_per_offer=delta['runnable_wait_ns'] / offered,
                read_span_ns=after['read_finished_ns'] - before['read_started_ns'],
                read_bracket_widths_ns=[s['read_finished_ns'] - s['read_started_ns'] for s in (before, after)],
                per_request_attribution=False, future_risk_certificate=False)


def reference(intervals):
    require(bool(intervals), 'Empty reference intervals')
    n = sum(i['offered'] for i in intervals)
    require(n > 0, 'Empty reference offer count')
    return dict(offered=n, running_ns_per_offer=sum(i['delta']['running_ns'] for i in intervals) / n,
                runnable_wait_ns_per_offer=sum(i['delta']['runnable_wait_ns'] for i in intervals) / n)


def drift(probe, baseline):
    """Signed features only. No cutoff, assurance, deadline forecast, or target data."""
    return dict(cpu_change_ns_per_offer=probe['running_ns_per_offer'] - baseline['running_ns_per_offer'],
                wait_change_ns_per_offer=probe['runnable_wait_ns_per_offer'] - baseline['runnable_wait_ns_per_offer'],
                future_outcomes_used=False, fitted=False)


def miss_fraction(outcomes, deadline_ns):
    require(bool(outcomes), 'Empty all-offer outcome population')
    nonnegative_int(deadline_ns, 'deadline')
    for o in outcomes:
        require(type(o['success']) is bool, 'Success status must be explicit')
        if o['success']:
            nonnegative_int(o['e2e_ns'], 'successful response time')
    return Fraction(sum(not o['success'] or o['e2e_ns'] > deadline_ns for o in outcomes), len(outcomes))
