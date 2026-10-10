#!/usr/bin/env python3
"""Join HTTP cleanup Cond waits to the exact background reader which wakes them.

Read-only diagnostic analysis; this never changes or qualifies a collection.
"""
import argparse
import bisect
import collections
import json
import math
from pathlib import Path
import subprocess
import tempfile
import run
import trace_analysis as trace


def blocks(lines):
    block = []
    for line in lines:
        if trace.HEADER.match(line):
            if block:
                yield block
            block = []
        block.append(line)
    if block:
        yield block


def stacks(block):
    result = {'TransitionStack': [], 'Stack': []}
    current = None
    for line in block[1:]:
        if line.strip() in ('TransitionStack=', 'Stack='):
            current = line.strip()[:-1]
        elif current and line.strip():
            result[current].append(line.strip())
    return {key: '\n'.join(value) for key, value in result.items()}


def index_events(lines):
    waits, wakes, creates = [], {}, {}
    for block in blocks(lines):
        header = trace.HEADER.match(block[0])
        if not header or header[2] != 'StateTransition':
            continue
        event = trace.TRANSITION.search(header[4])
        if not event:
            continue
        goroutine, old, new, _ = event.groups()
        goroutine, stamp, actor = int(goroutine), int(header[3]), int(header[1])
        stack = stacks(block)
        if (old != 'Waiting' and new == 'Waiting' and
                'sync.(*Cond).Wait' in stack['TransitionStack'] and
                'net/http.(*connReader).abortPendingRead' in stack['TransitionStack']):
            waits.append((goroutine, stamp))
        if (old == 'Waiting' and new == 'Runnable' and
                'sync.(*Cond).Broadcast' in stack['Stack'] and
                'net/http.(*connReader).backgroundRead' in stack['Stack']):
            wakes[goroutine, stamp] = actor
        if (old == 'NotExist' and new == 'Runnable' and
                'net/http.(*connReader).startBackgroundRead' in stack['Stack'] and
                'net/http.(*connReader).backgroundRead' in stack['TransitionStack']):
            creates[goroutine] = (actor, stamp)
    return dict(waits=waits, wakes=wakes, creates=creates)


def snapshot_series(parsed):
    # Go generation censuses can repeat Waiting->Waiting with an empty reason.
    # That is not a wake or a new unknown wait. Preserve its existing reason.
    trace.scheduler_series(parsed)  # Validate the original transition chains.
    series = {}
    for goroutine, events in parsed['transitions'].items():
        previous_reason, rows = '', []
        for stamp, old, new, reason in events:
            if old == new and not reason:
                reason = previous_reason
            if not rows and old == 'NotExist':
                rows.append((parsed['first_ns'], 'NotExist', ''))
            rows.append((stamp, new, reason))
            previous_reason = reason
        series[int(goroutine)] = rows
    return series


def join(parsed, requests, server, index):
    series = snapshot_series(parsed)
    mapping = requests['clock_mapping']
    offset = (mapping['offset_low_ns'] + mapping['offset_high_ns']) // 2
    windows = collections.defaultdict(list)
    for request in requests['all_requests']:
        interval = request['intervals'].get('handler_exit_to_connection_done')
        if interval:
            windows[interval['goroutine']].append((interval['start_ns'] + offset,
                                                  interval['end_ns'] + offset, request))
    completion_times = sorted(event['completion_ns'] + offset for event in server['events'])
    rows, unmatched = [], collections.Counter()
    positions = {int(g): {event[0]: i for i, event in enumerate(events)}
                 for g, events in parsed['transitions'].items()}
    for handler, begin in index['waits']:
        matching = [r for a, b, r in windows[handler] if a <= begin < b]
        if not matching:
            unmatched['outside_work_request_cleanup'] += 1
            continue
        if len(matching) != 1:
            raise ValueError('ambiguous request cleanup association')
        request = matching[0]
        events = parsed['transitions'][str(handler)]
        i = positions[handler][begin] + 1
        snapshots = 0
        while i < len(events) and events[i][2] == 'Waiting':
            snapshots += 1
            i += 1
        if i == len(events):
            unmatched['no_wait_exit_in_capture'] += 1
            continue
        finish = events[i][0]
        reader = index['wakes'].get((handler, finish))
        if reader is None:
            unmatched['no_background_read_broadcast_stack'] += 1
            continue
        creation = index['creates'].get(reader)
        if creation is None:
            unmatched['reader_creation_outside_capture'] += 1
            continue
        if creation[0] != handler or creation[1] > begin:
            raise ValueError('background reader creator/ordering mismatch')
        if finish > request['intervals']['handler_exit_to_connection_done']['end_ns'] + offset:
            raise ValueError('cleanup wake follows final connection boundary')
        states = trace.state_durations(series[reader], begin, finish)
        if states.get('unknown_ns') or states.get('not_created_or_ended_ns'):
            raise ValueError('background reader state coverage unavailable')
        first_running = next((stamp for stamp, _, new, _ in parsed['transitions'][str(reader)]
                              if new == 'Running' and stamp >= creation[1]), None)
        if first_running is None or first_running > finish:
            raise ValueError('waking background reader never entered Running')
        rows.append(dict(request_id=request['id'], outcome=request['outcome'], conn=request['conn'],
                         handler_g=handler, reader_g=reader, reader_created_ns=creation[1],
                         reader_first_running_ns=first_running, wait_start_ns=begin, wake_ns=finish,
                         wait_ns=finish-begin, reader_states=states,
                         reader_never_ran_before_cleanup_wait=first_running > begin,
                         generation_snapshots_crossed=snapshots,
                         other_jobs_completed=bisect.bisect_right(completion_times, finish)-
                                              bisect.bisect_left(completion_times, begin),
                         final_socket_write_before_wait=request['last_socket_write_end_ns'] + offset <= begin))
    values = sorted(row['wait_ns'] for row in rows)
    summed_states = collections.Counter()
    for row in rows:
        summed_states.update(row['reader_states'])
    total = sum(values)
    long_rows = [row for row in rows if row['wait_ns'] >= 1_000_000]
    return dict(requests_matched=len(rows), unmatched=dict(unmatched),
                clock_mapping_uncertainty_ns=mapping['uncertainty_ns'],
                total_observed_cond_waits=len(index['waits']),
                wait_ms={f'p{p}': values[math.ceil(p*len(values)/100)-1]/1e6 if values else None
                         for p in (50, 95, 99)},
                max_wait_ms=max(values, default=0)/1e6,
                waits_at_least_1ms=len(long_rows),
                long_waits_reader_never_ran_before_cleanup=sum(row['reader_never_ran_before_cleanup_wait'] for row in long_rows),
                summed_wait_ns=total, summed_reader_states_ns=dict(summed_states),
                reader_runnable_share=summed_states.get('runnable_ns', 0)/total if total else None,
                all_request_rows=rows,
                longest_examples=sorted(rows, key=lambda row: row['wait_ns'], reverse=True)[:10])


def inspect(attempt, parsed_path=None):
    parsed, requests, server = [run.read(attempt/name) for name in
                                ('trace_scheduler.json', 'trace_requests.json', 'server_metrics.json')]
    status = run.read(attempt/'trace_status.json')
    if not status['complete'] or status['active'] or not requests['complete']:
        raise ValueError('complete retained trace required')
    config = run.read(attempt/'config.json')
    errors = run.validation_errors(attempt, config, True)
    if errors:
        raise ValueError('retained attempt failed validation: ' + '; '.join(errors))
    with tempfile.TemporaryDirectory() as tmp:
        if parsed_path is None:
            parsed_path = Path(tmp)/'parsed.txt'
            command = ['docker', 'run', '--rm', '-v', f'{attempt}:/trace:ro',
                       'golang:1.26.1-alpine', 'go', 'tool', 'trace', '-d=parsed', '/trace/runtime.trace']
            with parsed_path.open('w') as output:
                subprocess.run(command, stdout=output, check=True)
        with parsed_path.open() as stream:
            if trace.parse_lines(stream) != parsed:
                raise ValueError('raw parsed trace differs from sealed scheduler evidence')
        with parsed_path.open() as stream:
            result = join(parsed, requests, server, index_events(stream))
        result.update(attempt=str(attempt), runtime_sha256=run.sha(attempt/'runtime.trace'),
                      completion_sha256=run.sha(attempt/'complete.json'),
                      parsed_dump_sha256=run.sha(parsed_path), parser='Go 1.26.1 -d=parsed',
                      limitations=[
                          'Only observed work-request cleanup Cond waits with matched creator and Broadcast stacks are joined; control routes and missing associations are counted separately.',
                          'State snapshots are not wakes; same-state snapshots retain the preceding wait reason.',
                          'State-duration sums overlap across goroutines and are not wall-clock runtime or CPU execution.',
                          'Go Running can include quota throttling or OS descheduling. Runnable is ready-to-run state, not a measured CPU queue position.',
                          'No tracing-off scheduler capture exists. This comparison identifies a wait dependency, not why tracing changes scheduling or the full cause of queue rejection.',
                          'Socket Write return does not establish client delivery; no absolute client/server timestamps are subtracted.',
                      ])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--parsed-trace', type=Path, help='Previously generated pinned Go dump; verified against sealed scheduler evidence')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    attempt, output = args.attempt.resolve(), args.output.resolve()
    if output.is_relative_to(attempt):
        parser.error('output must be outside the sealed attempt')
    result = inspect(attempt, args.parsed_trace)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    print(output)
