"""Pilot coverage uses bridge semantics without a quota-positive-control requirement."""
import json
import kernel_fixture_analysis as primitive


def clock_join(samples, client_mapping, generation):
    labels = {f'{phase}_{i}' for phase in ('start', 'stop') for i in range(3)}
    if len(samples) != 6 or {s['label'] for s in samples} != labels:
        raise ValueError('six kernel/server clock anchors required')
    lower, upper = [], []
    for s in samples:
        if s['generation'] != generation or not 0 <= s['before_ns'] <= s['after_ns'] or s['server_ns'] < 0:
            raise ValueError('clock generation/bracket mismatch')
        lower.append(s['before_ns'] - s['server_ns'])
        upper.append(s['after_ns'] - s['server_ns'])
    lo, hi = max(lower), min(upper)
    if lo > hi or hi-lo > 1_000_000:
        raise ValueError('kernel/server clock anchors disagree or exceed 1 ms')
    clo = lo + client_mapping['server_minus_client_lower_ns']
    chi = hi + client_mapping['server_minus_client_upper_ns']
    if chi-clo > 2_000_000:
        raise ValueError('composed kernel/client clock uncertainty exceeds 2 ms')
    return dict(kernel_minus_server_lower_ns=lo, kernel_minus_server_upper_ns=hi,
                kernel_minus_client_lower_ns=clo, kernel_minus_client_upper_ns=chi,
                uncertainty_ns=chi-clo,
                assumption='CLOCK_MONOTONIC unit slope; zero time-namespace offsets; no generation reset')


def coverage(raw, stderr, metadata, snapshots):
    rows, begin, end = primitive.records(raw, stderr)
    root = metadata['pid']; targets = {root}; live = {root}; dead = set()
    residency = {}; cpus = set(); switches = {}; created = set()
    # Input arrival order differs across perf buffers. Kernel timestamps order
    # fork before child scheduling, and exit before its final switch out.
    for r in sorted((r for r in rows if r[0] not in ('T', 'U')), key=lambda r:r[1]):
        kind, ts, cpu = r[:3]
        if kind == 'F':
            parent, child = r[3:]
            if parent not in live or child in live:
                raise ValueError('unknown parent or duplicate live child')
            targets.add(child); live.add(child); created.add(child)
        elif kind == 'X':
            tid = r[3]
            if tid not in live: raise ValueError('unaccounted thread exit')
            dead.add(tid); live.remove(tid)
        elif kind == 'W':
            if r[3] not in live or r[4] not in (2, 4):
                raise ValueError('unaccounted wakeup or wrong target CPU')
        else:
            _, _, _, prev, nxt, state, pt, nt = r
            if cpu not in (2, 4): raise ValueError('target scheduled outside CPUs2,4')
            if pt != int(prev in targets) or nt != int(nxt in targets):
                raise ValueError('scheduler membership mismatch')
            if pt:
                if cpu not in residency or residency[cpu][0] != prev:
                    raise ValueError('unmatched target switch out')
                switches[cpu] = switches.get(cpu, 0) + ts-residency.pop(cpu)[1]
            if nt:
                if cpu in residency or nxt not in live:
                    raise ValueError('unmatched target switch in')
                residency[cpu] = (nxt, ts); cpus.add(cpu)
            if prev in dead:
                dead.remove(prev); targets.remove(prev)
    if live or dead or residency:
        raise ValueError('open thread/scheduling lifecycle at capture end')
    for snapshot in snapshots:
        if not begin < snapshot['before_ns'] <= snapshot['after_ns'] < end:
            raise ValueError('thread snapshot outside capture')
        # Compare /proc enumeration to reconstructed lifecycle on both bounds.
        # New/exiting threads inside the enumeration bracket remain ambiguous.
        starts = {root:begin}; finishes = {}
        for r in rows:
            if r[0] == 'F': starts[r[4]] = r[1]
            elif r[0] == 'X': finishes[r[3]] = r[1]
        certain = {t for t,s in starts.items() if s <= snapshot['before_ns'] and finishes.get(t,end) > snapshot['after_ns']}
        possible = {t for t,s in starts.items() if s <= snapshot['after_ns'] and finishes.get(t,end) > snapshot['before_ns']}
        observed = set(snapshot['tids'])
        if not certain <= observed <= possible:
            raise ValueError('live /proc threads disagree with captured lifecycle')
    intervals, attempts = primitive.quota_intervals(rows, metadata['cgroup_id'])
    if any(v['cpu'] not in (2,4) for v in intervals): raise ValueError('wrong quota CPU')
    return dict(passed=True, received_events=len(rows), created_tids=sorted(created),
                observed_cpus=sorted(cpus), residency_ns_by_cpu=switches,
                throttle_attempts=attempts, quota_intervals=intervals,
                capture_begin_ns=begin, capture_end_ns=end,
                observer_cost_qualified=False, service_request_attribution=False)

