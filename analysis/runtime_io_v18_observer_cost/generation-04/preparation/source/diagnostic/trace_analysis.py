#!/usr/bin/env python3
"""Validate pinned Go trace evidence and join service-local request boundaries.

Go Running is a runtime state, not proof of on-CPU execution. Connection read
windows include idle/read-ahead time and never establish request byte arrival.
"""
import argparse
import hashlib
import bisect
import json
from pathlib import Path
import re
import subprocess
import tempfile

ANALYSIS_VERSION = 2
HEADER = re.compile(r'^M=\S+ P=\S+ G=(-?\d+) (\w+) Time=(\d+) (.*)$')
TRANSITION = re.compile(r'GoID=(\d+) (\w+)->(\w+) Reason="([^"]*)"')
LOG_REQUEST = re.compile(r'Task=(\d+) Category="request" Message="id=(\d+) conn=(\d+)"')
LOG_WORKER = re.compile(r'Task=(\d+) Category="request" Message="worker_start id=(\d+)"')
LOG_CLOCK = re.compile(r'Category="clock" Message="(start|stop)"')
LOG_CONN = re.compile(r'Category="connection" Message="conn=(\d+) state=(\w+)"')
TASK_ID = re.compile(r'ID=(\d+)')
LIMITATIONS = [
    'go_running_ns is Go scheduler state time; OS descheduling or CPU quota throttling can occur within it.',
    'Connection pre-handler context includes idle, read-ahead and parsing; socket reads have no request byte framing.',
    'ConnState Active follows readRequest in Go 1.26.1, including parse errors; only a matched handler establishes a valid request.',
    'Socket Write return and connection Idle/Closed do not establish client receipt.',
    'Client and service absolute clocks are never subtracted.',
    'Reads spanning capture boundaries can be absent; read evidence is contextual, not an exhaustive packet timeline.',
]


def parse_lines(lines):
    result = dict(transitions={}, tasks={}, anchors={}, connections=[], task_ends={},
                  task_begins={}, event_count=0, first_ns=None, last_ns=None)
    for line in lines:
        match = HEADER.match(line)
        if not match:
            continue
        g, kind, stamp, detail = match.groups()
        g, stamp = int(g), int(stamp)
        result['event_count'] += 1
        if result['first_ns'] is None: result['first_ns'] = stamp
        result['last_ns'] = stamp
        if kind == 'StateTransition':
            found = TRANSITION.search(detail)
            if found:
                goid, old, new, reason = found.groups()
                result['transitions'].setdefault(goid, []).append([stamp, old, new, reason])
        elif kind in ('TaskBegin', 'TaskEnd'):
            found = TASK_ID.search(detail)
            if found:
                dest = result['task_begins' if kind == 'TaskBegin' else 'task_ends']
                if found[1] in dest: raise ValueError('duplicate runtime task boundary')
                dest[found[1]] = stamp
        elif kind == 'Log':
            found = LOG_REQUEST.search(detail)
            if found:
                task, req, conn = map(int, found.groups())
                item = result['tasks'].setdefault(str(req), {})
                if 'task' in item: raise ValueError(f'{req}: duplicate handler task log')
                item.update(task=task, conn=conn, handler_g=g, handler_log_time=stamp)
            found = LOG_WORKER.search(detail)
            if found:
                task, req = map(int, found.groups())
                item = result['tasks'].setdefault(str(req), {})
                if 'worker_g' in item: raise ValueError(f'{req}: duplicate worker task log')
                item.update(worker_task=task, worker_g=g, worker_log_time=stamp)
            found = LOG_CLOCK.search(detail)
            if found:
                if found[1] in result['anchors']: raise ValueError('duplicate clock log')
                result['anchors'][found[1]] = stamp
            found = LOG_CONN.search(detail)
            if found:
                result['connections'].append(dict(conn=int(found[1]), state=found[2], g=g, time=stamp))
    if not result['event_count'] or not result['transitions']:
        raise ValueError('missing runtime scheduler events')
    return result


def parse_trace(path, decoder=None, decoder_sha256=None):
    command = ['docker', 'run', '--rm', '-v', f'{path.parent}:/trace:ro',
               'golang:1.26.1-alpine', 'go', 'tool', 'trace', '-d=parsed', f'/trace/{path.name}']
    if decoder is not None:
        if not decoder_sha256 or hashlib.sha256(decoder.read_bytes()).hexdigest() != decoder_sha256:
            raise ValueError('pinned trace decoder hash mismatch')
        command = [str(decoder), '-d=parsed', str(path)]
    # stderr is a file so a parser failure cannot deadlock on a full stderr pipe.
    with tempfile.TemporaryFile(mode='w+') as errors:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors, text=True)
        try:
            result = parse_lines(proc.stdout)
        except BaseException:
            proc.kill()
            proc.wait()
            raise
        finally:
            proc.stdout.close()
        code = proc.wait()
        if code:
            errors.seek(0)
            raise ValueError(f'Go trace parse failed ({code}): {errors.read(2000)}')
    return result


def clock_map(captured, parsed):
    if len(captured) != 2 or {a['label'] for a in captured} != {'start', 'stop'}:
        raise ValueError('expected distinct start and stop clock anchors')
    bounds = []
    for anchor in captured:
        timestamp = parsed.get(anchor['label'])
        if timestamp is None: raise ValueError(f'missing runtime clock anchor {anchor["label"]}')
        before, after = anchor['before_ns'], anchor['after_ns']
        if before > after: raise ValueError('reversed clock anchor bracket')
        bounds.append((timestamp - after, timestamp - before))
    low, high = max(b[0] for b in bounds), min(b[1] for b in bounds)
    if low > high: raise ValueError(f'clock mappings disagree: {bounds}')
    if high - low > 1_000_000: raise ValueError('clock mapping uncertainty exceeds 1 ms')
    if parsed['start'] >= parsed['stop']: raise ValueError('reversed capture anchors')
    return dict(offset_low_ns=low, offset_high_ns=high, uncertainty_ns=high-low, anchor_count=2)


def state_name(state, reason):
    if state == 'Running': return 'go_running_ns'
    if state == 'Runnable': return 'runnable_ns'
    if state == 'Syscall': return 'syscall_ns'
    if state == 'NotExist': return 'not_created_or_ended_ns'
    if state == 'Waiting':
        return 'network_wait_ns' if reason == 'network' else 'sync_or_other_wait_ns'
    return 'unknown_ns'


def state_durations(series, start, end):
    if not series or end < start: return {'unknown_ns': max(0, end-start)}
    index = bisect.bisect_right([row[0] for row in series], start)-1
    cursor = start
    state = series[index][1:] if index >= 0 else ('Undetermined', '')
    result = {}
    for stamp, new, reason in series[index+1:]:
        if stamp >= end: break
        if stamp > cursor:
            key = state_name(*state)
            result[key] = result.get(key, 0) + stamp-cursor
            cursor = stamp
        state = new, reason
    if end > cursor:
        key = state_name(*state)
        result[key] = result.get(key, 0) + end-cursor
    return result


def scheduler_series(parsed):
    if not parsed['event_count'] or not parsed['transitions']:
        raise ValueError('missing runtime scheduler events')
    series = {}
    for goid, events in parsed['transitions'].items():
        previous, previous_time = None, -1
        rows = []
        for stamp, old, new, reason in events:
            if stamp < previous_time or (previous is not None and old != previous):
                raise ValueError(f'G{goid}: broken scheduler transition chain')
            if previous is None and old not in ('Undetermined', 'NotExist'):
                raise ValueError(f'G{goid}: missing initial scheduler state')
            if previous is None and old == 'NotExist':
                rows.append((parsed['first_ns'], 'NotExist', ''))
            rows.append((stamp, new, reason))
            previous, previous_time = new, stamp
        series[int(goid)] = rows
    return series


def unique(rows, key, label):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows): raise ValueError(f'duplicate {label}')
    return result


def build_analysis(status, loadgen, server, parsed):
    if not status['complete'] or status['active'] or status['io_events_dropped'] or status['runtime_trace_overflow']:
        raise ValueError('incomplete trace capture')
    if status.get('pending_responses', -1) != 0: raise ValueError('responses not fully drained')
    if any(status.get(k) for k in ('start_error','stop_error','trace_write_error')):
        raise ValueError('trace capture I/O error')
    mapping = clock_map(status['clock_anchors'], parsed['anchors'])
    offset = (mapping['offset_low_ns']+mapping['offset_high_ns'])//2
    uncertainty = mapping['uncertainty_ns']
    series = scheduler_series(parsed)
    requests = unique(loadgen['requests'], 'ID', 'client request')
    workers = unique(server['events'], 'id', 'worker event')
    handlers = unique(server['handler_events'], 'id', 'handler event')
    tasks = {int(k): v for k, v in parsed['tasks'].items()}
    io = status['io_events']
    def kind(name): return [e for e in io if e['kind'] == name]
    entries = unique(kind('handler_entry'), 'request', 'handler entry')
    exits = unique(kind('handler_exit'), 'request', 'handler exit')
    admitted = unique(kind('admitted'), 'request', 'admission marker')
    rejected = unique(kind('rejected'), 'request', 'rejection marker')
    if set(entries) != set(exits) or set(entries) != set(tasks):
        raise ValueError('missing handler entry/exit/runtime task')
    if (set(admitted) & set(rejected) or set(entries) != set(admitted) | set(rejected)
            or set(workers) != set(admitted) or set(handlers)-set(admitted)
            or set(entries)-set(requests)):
        raise ValueError('server admission/rejection/request association mismatch')
    if len(admitted) != server['admitted'] or len(rejected) != server['rejected']:
        raise ValueError('server outcome count mismatch')
    for ev in io:
        if not (0 <= ev['start_ns'] <= ev['end_ns'] and ev['conn'] > 0):
            raise ValueError('invalid I/O timing or connection')
        if ev['request_known']:
            if ev['request'] not in entries or entries[ev['request']]['conn'] != ev['conn']:
                raise ValueError('invalid I/O request association')
    # Match lifecycle events to runtime logs by connection/state order, not socket calls.
    logs = {}
    for log in parsed['connections']:
        logs.setdefault((log['conn'], log['state']), []).append(log)
    lifecycle = {}
    keys = {(e['conn'], e['kind'][5:]) for e in io if e['kind'].startswith('conn_')}
    if keys != set(logs): raise ValueError('missing connection lifecycle event/log')
    for key in keys:
        events = sorted([e for e in io if (e['conn'], e['kind']) == (key[0], 'conn_'+key[1])], key=lambda e:e['start_ns'])
        matches = logs.get(key, [])
        if len(events) != len(matches): raise ValueError('missing connection runtime log')
        for e, log in zip(events, matches):
            if log['time'] < e['start_ns']+offset-uncertainty:
                raise ValueError('connection log clock/order mismatch')
            lifecycle[id(e)] = log
    completions = sorted((e['completion_ns'], e['id']) for e in workers.values())
    completion_times = [e[0] for e in completions]
    rows = []
    for req, q in requests.items():
        outcome = ('success' if q['StatusCode'] == 200 and not q['Error'] else
                   'rejected' if q['StatusCode'] == 503 and not q['Error'] else
                   'timeout' if q.get('TimedOut') else 'error')
        row = dict(id=req, outcome=outcome, status=q['StatusCode'], error=q['Error'],
                   e2e_ns=q['EndToEndLatencyNs'], socket_write_count=0, intervals={},
                   client_offsets={k:q[k] for k in ('GotConnOffsetNs','WroteRequestOffsetNs','FirstByteOffsetNs','BodyDoneOffsetNs') if k in q})
        rows.append(row)
        if req not in entries:
            if outcome in ('success', 'rejected') or req in workers:
                raise ValueError(f'{req}: missing server request evidence')
            row.update(server_observation='unobserved', unresolved='No server handler was observed; client failure cannot be located on the server.')
            continue
        t, first, last = tasks[req], entries[req], exits[req]
        conn, g = first['conn'], t.get('handler_g')
        a, b = first['start_ns'], last['start_ns']
        if not (first['request_known'] and last['request_known'] and t.get('conn') == conn == last['conn'] and a <= b):
            raise ValueError(f'{req}: handler connection/order mismatch')
        taskid = str(t['task'])
        begin, end = parsed['task_begins'].get(taskid), parsed['task_ends'].get(taskid)
        if (begin is None or end is None or not a+offset-uncertainty <= begin <= t['handler_log_time'] <= end
                or end < b+offset-uncertainty):
            raise ValueError(f'{req}: missing or unordered task boundaries')
        same = sorted([e for e in io if e['conn'] == conn], key=lambda e:e['start_ns'])
        terminals = [e for e in same if e['kind'] in ('conn_idle','conn_closed') and e['request_known'] and e['request'] == req]
        if len(terminals) != 1: raise ValueError(f'{req}: missing/duplicate final connection boundary')
        terminal = terminals[0]
        if b > terminal['start_ns'] or lifecycle[id(terminal)]['g'] != g:
            raise ValueError(f'{req}: final connection goroutine/order mismatch')
        socket = [e for e in same if e['kind'] == 'write' and e['request_known'] and e['request'] == req]
        for e in same:
            if (e['kind'] == 'write' and a <= e['start_ns'] < terminal['start_ns']
                    and (not e['request_known'] or e['request'] != req)):
                raise ValueError(f'{req}: unassociated or conflicting write in request lifetime')
            if e['kind']=='handler_entry' and a < e['start_ns'] < terminal['start_ns']:
                raise ValueError(f'{req}: overlapping HTTP/1 request lifetimes')
        if outcome in ('success','rejected') and not socket:
            raise ValueError(f'{req}: no associated socket write')
        for e in socket:
            if not a <= e['start_ns'] <= e['end_ns'] <= terminal['start_ns']:
                raise ValueError(f'{req}: socket write outside request lifetime')
        row.update(server_observation='observed', conn=conn, handler_g=g,
                   server_outcome='admitted' if req in admitted else 'rejected',
                   socket_write_count=len(socket), socket_write_error_count=sum(bool(e.get('error')) for e in socket),
                   socket_writes=socket, final_connection_state=terminal['kind'],
                   connection_reuse_index=sum(e['kind']=='handler_entry' and e['start_ns']<a for e in same),
                   handler_span_ns=b-a, outside_handler_signed_ns=q['EndToEndLatencyNs']-(b-a),
                   read_association='ambiguous_http_framing')
        def window(name, start, finish, goid=g, association='request'):
            if start > finish: raise ValueError(f'{req}: reversed {name}')
            lo, hi = start+offset, finish+offset
            if lo < parsed['first_ns'] or hi > parsed['last_ns']:
                raise ValueError(f'{req}: {name} outside runtime capture')
            states = state_durations(series.get(goid), lo, hi)
            if goid not in series or states.get('unknown_ns', 0):
                raise ValueError(f'{req}: missing scheduler coverage for {name}')
            if association == 'request' and states.get('not_created_or_ended_ns', 0) > uncertainty:
                raise ValueError(f'{req}: dead goroutine during {name}')
            other = [rid for _, rid in completions[bisect.bisect_left(completion_times,start):bisect.bisect_right(completion_times,finish)] if rid != req]
            row['intervals'][name] = dict(start_ns=start, end_ns=finish, duration_ns=finish-start,
                goroutine=goid, states=states, association=association,
                other_jobs_completed=len(other), other_job_id_sample=other[:20],
                clock_mapping_uncertainty_ns=uncertainty)
        window('handler', a, b)
        window('handler_exit_to_connection_done', b, terminal['start_ns'])
        active = [e for e in same if e['kind']=='conn_active' and e['start_ns'] <= a]
        previous = [e for e in same if e['kind'] in ('accept','conn_idle') and e['start_ns'] < a]
        if previous:
            baseline = previous[-1]['start_ns']
            window('connection_context_before_handler', baseline, a, association='connection_context_not_request_arrival')
            row['context_reads'] = [e for e in same if e['kind']=='read' and e['end_ns']>=baseline and e['start_ns']<=a]
            active = [e for e in active if e['start_ns']>=baseline]
        else:
            row['pre_handler_unresolved'] = 'Connection accept/previous idle was outside capture.'
        if active:
            if lifecycle[id(active[-1])]['g'] != g: raise ValueError('active connection goroutine mismatch')
            window('read_request_return_to_handler', active[-1]['start_ns'], a)
        else:
            row['pre_handler_unresolved'] = 'No per-request Active callback; buffered/pipelined framing or capture boundary prevents a parse-return association.'
        if socket:
            first_write, final_write = min(e['start_ns'] for e in socket), max(e['end_ns'] for e in socket)
            if first_write >= b: window('handler_exit_to_first_socket_write', b, first_write)
            else: row['write_overlaps_handler'] = True
            for i, e in enumerate(socket): window(f'socket_write_{i}', e['start_ns'], e['end_ns'])
            window('final_socket_write_to_connection_done', final_write, terminal['start_ns'])
            row.update(first_socket_write_after_exit_ns=first_write-b, last_socket_write_end_ns=final_write)
        work, h = workers.get(req), handlers.get(req)
        if req in admitted:
            if t.get('worker_task') != t['task'] or not t.get('worker_g'):
                raise ValueError(f'{req}: worker task mismatch')
            window('worker', work['worker_start_ns'], work['completion_ns'], t['worker_g'])
            row.update(worker_g=t['worker_g'], queue_ns=work['queue_wait_ns'], processing_ns=work['processing_ns'])
        elif t.get('worker_g') or outcome == 'success':
            raise ValueError(f'{req}: rejected request has worker/success')
        if outcome == 'rejected' and req not in rejected: raise ValueError('rejection outcome mismatch')
        if outcome == 'success' and h is None: raise ValueError('successful request missing handler timing')
        if h:
            window('worker_completion_to_handler_resume', work['completion_ns'], h['resume_ns'])
            window('handler_resume_to_application_write', h['resume_ns'], h['write_start_ns'])
            window('application_write', h['write_start_ns'], h['write_end_ns'])
            window('application_write_to_handler_exit', h['write_end_ns'], b)
            row.update(post_work_ns=h['post_work_wait_ns'], application_write_error=h['write_error'])
        row['unresolved'] = 'Connection context does not timestamp this request arriving; final socket write does not prove client delivery. Go Running does not prove continuous CPU execution.'
    successful = sorted([r for r in rows if r['outcome']=='success'], key=lambda r:r['e2e_ns'])
    n = max(1, (len(successful)+99)//100)
    middle = max(0, len(successful)//2-n//2)
    matched = [dict(group=group, **r) for group, selection in (
        ('slow', successful[-n:]), ('typical', successful[middle:middle+n])) for r in selection]
    return dict(analysis_version=ANALYSIS_VERSION, complete=True, go_version=server['go_version'],
        runtime_event_count=parsed['event_count'], clock_mapping=mapping,
        successful_request_count=len(successful), request_count=len(rows),
        outcome_counts={outcome:sum(r['outcome']==outcome for r in rows) for outcome in ('success','rejected','timeout','error')},
        unobserved_request_count=sum(r['server_observation']=='unobserved' for r in rows),
        matched=matched, all_requests=rows, limitations=LIMITATIONS)


def write_report(directory, result):
    lines = ['# Request boundary evidence', '', *['- '+s for s in result['limitations']], '',
             'All outcomes: '+json.dumps(result['outcome_counts']), '',
             'Clock mapping uncertainty (ns): '+str(result['clock_mapping']['uncertainty_ns']), '',
             '| Group / request | Interval | ms | Go Running ms | Runnable ms | Network wait ms | Other wait ms | Syscall ms | Other jobs completed |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for row in result['matched']:
        for name, interval in row['intervals'].items():
            states = interval['states']
            lines.append(f'| {row["group"]} / {row["id"]} | {name} | {interval["duration_ns"]/1e6:.4f} | '
                f'{states.get("go_running_ns",0)/1e6:.4f} | {states.get("runnable_ns",0)/1e6:.4f} | '
                f'{states.get("network_wait_ns",0)/1e6:.4f} | {states.get("sync_or_other_wait_ns",0)/1e6:.4f} | '
                f'{states.get("syscall_ns",0)/1e6:.4f} | {interval["other_jobs_completed"]} |')
    lines += ['', 'Intervals overlap and must not be summed. JSON retains every outcome, syscall/other-wait time, read context and write errors.',
              'No automatic mechanism or intervention is inferred. Inspect matched intervals and their association limits before proposing a controlled intervention.', '']
    (directory/'trace_report.md').write_text('\n'.join(lines))


def analyze(directory, decoder=None, decoder_sha256=None):
    parsed = parse_trace(directory/'runtime.trace', decoder, decoder_sha256)
    (directory/'trace_scheduler.json').write_text(json.dumps(parsed)+'\n')
    result = build_analysis(*[json.loads((directory/name).read_text()) for name in
        ('trace_status.json','loadgen.json','server_metrics.json')], parsed)
    (directory/'trace_requests.json').write_text(json.dumps(result, indent=2)+'\n')
    write_report(directory, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt', type=Path)
    parser.add_argument('--decoder', type=Path)
    parser.add_argument('--decoder-sha256')
    args = parser.parse_args()
    if bool(args.decoder) != bool(args.decoder_sha256):
        parser.error('decoder and its hash are required together')
    analyze(args.attempt.resolve(), args.decoder.resolve() if args.decoder else None, args.decoder_sha256)
