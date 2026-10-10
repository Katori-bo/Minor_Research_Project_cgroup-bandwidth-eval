#!/usr/bin/env python3
"""Bounded stock-NGINX full-response feasibility; no FIFO or prediction claim."""
import argparse
import gzip
import json
import math
import os
from pathlib import Path
import re
import signal
import statistics
import subprocess
import sys
import time
import traceback
import uuid

import nginx_common as n

h = n.prior.helpers
LABEL = 'research.nginx.feasibility.owner'


def inspect_owned(name, nonce):
    p = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=15)
    if p.returncode:
        if 'no such' in p.stderr.lower(): return None
        raise RuntimeError(p.stderr)
    value = json.loads(p.stdout)[0]
    n.require(value['Config'].get('Labels', {}).get(LABEL) == nonce, 'NGINX ownership nonce differs')
    return value


def remove_owned(name, nonce):
    value = inspect_owned(name, nonce)
    if value is not None: h.cmd(['docker', 'rm', '-f', value['Id']])
    n.require(inspect_owned(name, nonce) is None, 'Owned NGINX container remains')


def watchdog(directory):
    owner = n.read(directory / 'ownership.json')
    while not (directory / 'cleanup.json').exists():
        if not h.same_owner(owner['owner']) or time.monotonic() >= owner['deadline_monotonic']:
            errors = []
            path = directory / 'client-ownership.json'
            if path.exists():
                client = n.read(path)
                if h.same_owner(client):
                    try: os.killpg(client['pid'], signal.SIGKILL)
                    except ProcessLookupError: pass
            try: remove_owned(owner['container'], owner['nonce'])
            except Exception as exc: errors.append(str(exc))
            n.save(directory / 'watchdog-cleanup.json', dict(invalidated=True, errors=errors))
            if h.same_owner(owner['owner']): os.kill(owner['owner']['pid'], signal.SIGTERM)
            return
        time.sleep(.5)


def parse_status(body):
    pattern = rb'Active connections: (\d+)\s+server accepts handled requests\s+(\d+) (\d+) (\d+)\s+Reading: (\d+) Writing: (\d+) Waiting: (\d+)\s*'
    match = re.fullmatch(pattern, body)
    n.require(match is not None, 'Stock stub_status framing differs')
    return dict(zip(('active', 'accepts', 'handled', 'requests', 'reading', 'writing', 'waiting'),
                    (int(v) for v in match.groups())))


def drained(value):
    return value['active'] == 1 and value['reading'] == 0 and value['writing'] == 1 and value['waiting'] == 0


def validate_client(client, prefix, count):
    n.require(client['Schema'] == 'nginx-client-v1' and client['Count'] == count and
              client['IntervalNs'] == 200000000 and len(client['Rows']) == count, 'NGINX client contract differs')
    rows = client['Rows']
    for i, row in enumerate(rows):
        n.require(row['ID'] == row['EchoID'] == f'{prefix}-{i}' and row['Status'] == 200 and
                  not row['Error'] and not row['DecodeError'] and row['ContentEncoding'] == 'gzip' and
                  row['ContentType'] == 'application/x-ndjson' and row['DecodedBytes'] == 1048576 and
                  row['DecodedSHA256'] == n.INPUT_SHA and 0 < row['BodyBytes'] <= 2097152,
                  'NGINX complete encoded/decoded outcome failed')
        n.require(row['ScheduledNs'] == i * 200000000 <= row['DispatchNs'] <= row['HeadersNs'] <= row['BodyDoneNs'],
                  'NGINX client milestone order failed')
    lag = sorted(r['DispatchNs'] - r['ScheduledNs'] for r in rows)
    # Client response-window overlap includes decoding-independent full-body
    # completion, not an inferred server queue or service serialization proof.
    outstanding = 0; maximum = 0; timeline = []
    for r in rows: timeline.extend([(r['DispatchNs'], 1), (r['BodyDoneNs'], -1)])
    for _, change in sorted(timeline):
        outstanding += change; maximum = max(maximum, outstanding)
    return dict(offers=count, median_e2e_ns=statistics.median(r['BodyDoneNs'] - r['ScheduledNs'] for r in rows),
        max_e2e_ns=max(r['BodyDoneNs'] - r['ScheduledNs'] for r in rows),
        dispatch_p99_ns=lag[math.ceil(.99 * count) - 1], dispatch_max_ns=max(lag),
        max_simultaneous_client_response_windows=maximum, decoded_sha256=n.INPUT_SHA)


def analyze(case, count, enforce):
    validate_client(n.read(case / 'warmup.json'), 'warmup', 25)
    timing = validate_client(n.read(case / 'measurement.json'), 'measurement', count)
    counts = n.read(case / 'measurement-counters.json')
    delta = {k: counts['after'][k] - counts['before'][k] for k in counts['before']}
    n.require(delta == counts['delta'] and all(v >= 0 for v in delta.values()), 'NGINX counter replay failed')
    status = n.read(case / 'status-window.json')
    before, afters = status['before'], status['after_checks']
    n.require(drained(before) and afters and drained(afters[-1]), 'NGINX worker did not drain')
    n.require(afters[-1]['requests'] - before['requests'] == count + len(afters), 'NGINX request conservation failed')
    n.require(all(a['requests'] <= b['requests'] for a, b in zip([before, *afters], afters)),
              'NGINX status counters reversed')
    exits = []
    if delta['nr_throttled']: exits.append('measurement_throttling')
    if timing['dispatch_p99_ns'] > 2000000 or timing['dispatch_max_ns'] > 10000000: exits.append('dispatch_gate')
    result = dict(**timing, measurement_counter_delta=delta, cpu_per_offer_usec=delta['usage_usec'] / count,
        domain_exits=exits, stock_request_conservation=True, server_queue_observed=False,
        scientific_collection=False)
    if enforce: n.require(not exits, 'NGINX feasibility gate failed: ' + ','.join(exits) + '; no replacement allowed')
    return result


class Service:
    def __init__(self, directory, performance):
        self.directory, self.performance = directory, performance
        self.name, self.nonce = 'quota-nginx-' + uuid.uuid4().hex, uuid.uuid4().hex
        self.started = time.monotonic(); self.client = self.watcher = None
        self.image = n.read(n.SOFTWARE / 'image.json')['id']
        self.manifest = n.read(n.SOFTWARE / 'manifest.json')
        self.expected = None

    def scan(self):
        digest = self.manifest['nginx_sha256']
        value = n.prior.scan_group(self.pid, self.group, self.main_identity,
            dict(binaries={'stock': digest}, gzip_sha256=digest), 'stock')
        n.require(len(value['processes']) == 2 and not value['vanished_during_scan'] and
                  all(len(p['tids']) == 1 for p in value['processes']), 'Stock master/worker process or thread set differs')
        identities = {str(p['pid']): p['start_ticks'] for p in value['processes']}
        if self.expected is not None: n.require(identities == self.expected, 'NGINX worker respawn/PID identity changed')
        return value

    def guard(self):
        n.require(time.monotonic() - self.started < 120, 'NGINX service active deadline')
        if self.performance: h.desktop_absent()
        n.require(self.watcher.poll() is None, 'NGINX independent watchdog exited')
        n.require({k: (self.group / k).read_text().strip() for k in n.LIMITS} == n.LIMITS, 'NGINX live limits changed')
        return self.scan()

    def start(self):
        gate = self.directory / 'qualification'; gate.mkdir(); os.mkfifo(gate / 'start.fifo', 0o600)
        n.save(self.directory / 'ownership.json', dict(owner=h.process_identity(os.getpid()), container=self.name,
            nonce=self.nonce, deadline_monotonic=self.started + 120))
        self.watch_log = (self.directory / 'watchdog.log').open('x')
        self.watcher = subprocess.Popen([sys.executable, '-B', __file__, 'watchdog', '--directory', str(self.directory)],
            stdout=self.watch_log, stderr=subprocess.STDOUT, start_new_session=True)
        argv = ['docker', 'create', '--name', self.name, '--label', LABEL + '=' + self.nonce,
            '--user', n.PROTOCOL['application_user'], '--cpuset-cpus', '2', '--cpu-period', '100000',
            '--cpu-quota', '25000', '--memory', '512m', '--pids-limit', '128', '--read-only',
            '--tmpfs', '/tmp:rw,size=64m', '--mount', f'type=bind,src={gate},dst=/qualification,readonly',
            '-p', '127.0.0.1::8080', self.image]
        h.cmd(argv); h.cmd(['docker', 'start', self.name])
        value = inspect_owned(self.name, self.nonce)
        n.save(self.directory / 'container.json', dict(argv=argv, inspect=value))
        n.require(value['Image'] == self.image, 'NGINX immutable image differs')
        self.pid = value['State']['Pid']; self.main_identity = h.process_identity(self.pid)
        self.group = h.bridge.cgroup(self.pid)
        n.require({k: (self.group / k).read_text().strip() for k in n.LIMITS} == n.LIMITS, 'NGINX initial limits differ')
        n.save(self.directory / 'initial.json', dict(pid=self.pid, identity=self.main_identity, cgroup=str(self.group),
            limits=n.LIMITS, namespaces=h.bridge.namespaces(self.pid), ancestors=h.bridge.ancestors(self.group)))
        h.bridge.stopped(self.pid, state='S')
        n.require((self.group / 'cgroup.procs').read_text().split() == [str(self.pid)], 'NGINX gate not sole process')
        actual = {}
        for name, digest in self.manifest['runtime_files_sha256'].items():
            path = self.directory / 'packaged-check'
            h.cmd(['docker', 'cp', self.name + ':/' + name, str(path)])
            actual[name] = n.sha(path); path.unlink()
            n.require(actual[name] == digest, 'NGINX packaged runtime changed: ' + name)
        n.save(self.directory / 'runtime-identity.json', actual)
        h.bridge.release_fifo(gate / 'start.fifo')
        self.base = 'http://127.0.0.1:' + h.cmd(['docker', 'port', self.name, '8080/tcp']).rsplit(':', 1)[1]
        until = time.monotonic() + 10
        while len((self.group / 'cgroup.procs').read_text().split()) != 2:
            if time.monotonic() > until: raise TimeoutError('NGINX worker startup')
            time.sleep(.05)
        snapshot = self.scan(); self.expected = {str(p['pid']): p['start_ticks'] for p in snapshot['processes']}
        n.save(self.directory / 'process-identities.json', self.expected)
        while True:
            self.guard()
            try: self.status(); break
            except OSError:
                if time.monotonic() > until: raise TimeoutError('NGINX HTTP startup')
                time.sleep(.1)

    def status(self):
        body, _ = h.fetch(self.base, 'health')
        return parse_status(body)

    def collect(self, prefix, count):
        argv = [str(n.SOFTWARE / 'client'), '--url', self.base + '/compress', '--prefix', prefix,
                '--count', str(count), '--interval-ns', '200000000']
        with (self.directory / (prefix + '.json')).open('x') as output, (self.directory / (prefix + '.stderr')).open('x') as error:
            self.client = subprocess.Popen(argv, stdout=output, stderr=error, start_new_session=True)
            n.save(self.directory / 'client-ownership.json', h.process_identity(self.client.pid))
            until = time.monotonic() + count / 5 + 12
            try:
                while self.client.poll() is None:
                    self.guard()
                    if time.monotonic() > until: raise TimeoutError('NGINX client drain')
                    time.sleep(.25)
                n.require(self.client.returncode == 0, 'NGINX client failed')
            finally:
                if self.client.poll() is None: h.bridge.stop_known(self.client)

    def close(self):
        errors = []
        try: remove_owned(self.name, self.nonce)
        except Exception as exc: errors.append(str(exc))
        n.save(self.directory / 'cleanup.json', dict(errors=errors, elapsed_sec=time.monotonic() - self.started))
        if self.watcher is not None:
            try: self.watcher.wait(timeout=3)
            except subprocess.TimeoutExpired: h.bridge.stop_known(self.watcher)
            self.watch_log.close()
        n.require(not errors, 'NGINX owned cleanup unavailable')


def trial(case, count, performance, direct_checks=0):
    case.mkdir(); n.save(case / 'sources-at-start.json', n.source_hashes())
    service = Service(case, performance)
    try:
        service.start()
        for i in range(direct_checks):
            body, headers = h.fetch(service.base, 'compress', {'Accept-Encoding': 'gzip', 'X-Request-ID': f'check-{i}'})
            (case / f'check-{i}.gz').write_bytes(body)
            n.require(headers['Content-Encoding'] == 'gzip' and headers['X-Request-ID'] == f'check-{i}' and
                      gzip.decompress(body) == (n.BASE / 'input/corpus.ndjson').read_bytes(), 'NGINX direct correctness failed')
        service.collect('warmup', 25)
        status_before = service.status(); n.require(drained(status_before), 'NGINX warmup did not drain')
        n.save(case / 'threads-before.json', service.guard())
        before = h.fixtures.stat(service.group); n.save(case / 'measurement-before.json', before)
        afters = []
        try:
            service.collect('measurement', count)
            until = time.monotonic() + 3
            while True:
                afters.append(service.status())
                n.save(case / 'status-window.json', dict(before=status_before, after_checks=afters))
                if drained(afters[-1]): break
                if time.monotonic() > until: raise TimeoutError('NGINX measured requests did not drain')
                time.sleep(.05)
        finally:
            after = h.fixtures.stat(service.group)
            n.save(case / 'measurement-counters.json', dict(before=before, after=after,
                delta={k: after[k] - before[k] for k in before}))
        n.save(case / 'threads-after.json', service.guard())
        result = analyze(case, count, performance)
        n.save(case / 'result.json', result); return result
    except BaseException as exc:
        n.save(case / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        raise
    finally: service.close()


def identity(case):
    n.require(not n.read(case / 'cleanup.json')['errors'] and n.read(case / 'cleanup.json')['elapsed_sec'] <= 120 and
              not (case / 'watchdog-cleanup.json').exists() and not (case / 'failure.json').exists(), 'NGINX case invalidated')
    container = n.read(case / 'container.json')['inspect']; initial = n.read(case / 'initial.json')
    host = container['HostConfig']
    n.require(container['Image'] == n.read(n.SOFTWARE / 'image.json')['id'] and
              container['Config']['Labels'][LABEL] == n.read(case / 'ownership.json')['nonce'] and
              container['Config']['User'] == n.PROTOCOL['application_user'], 'NGINX runtime ownership differs')
    n.require(initial['limits'] == n.LIMITS and host['CpuQuota'] == 25000 and
              host['CpuPeriod'] == 100000 and host['CpusetCpus'] == '2', 'NGINX resource evidence differs')
    n.require(n.read(case / 'runtime-identity.json') == n.read(n.SOFTWARE / 'manifest.json')['runtime_files_sha256'] and
              n.read(case / 'sources-at-start.json') == n.source_hashes(), 'NGINX runtime/source identity differs')
    expected = n.read(case / 'process-identities.json')
    for phase in ('before', 'after'):
        snapshot = n.read(case / f'threads-{phase}.json')
        n.require(snapshot['affinity'] == [2] and snapshot['cgroup'] == initial['cgroup'] and
                  snapshot['main_pid'] == initial['pid'] and not snapshot['vanished_during_scan'] and
                  len(snapshot['processes']) == 2 and all(len(p['tids']) == 1 for p in snapshot['processes']) and
                  {str(p['pid']): p['start_ticks'] for p in snapshot['processes']} == expected, 'NGINX process snapshots differ')


def evidence_seal(directory):
    n.save(directory / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(directory)): n.sha(p)
        for p in sorted(directory.rglob('*')) if p.is_file() and p != directory / 'evidence-seal.json'}))


def functional():
    n.inputs(); os.sched_setaffinity(0, {0, 1})
    directory = n.BASE / 'functional'; directory.mkdir(); started = time.monotonic()
    try:
        result = trial(directory / 'case', 25, False, 2)
        identity(directory / 'case')
        n.require(analyze(directory / 'case', 25, False) == result, 'NGINX full preparation replay differs')
        n.save(directory / 'summary.json', dict(functional_pass=True, result=result,
            elapsed_sec=time.monotonic() - started, scientific_collection=False, performance_qualified=False))
    finally: evidence_seal(directory)
    print('Real stock NGINX preparation and full response/accounting/cleanup replay passed.')


def replay(check_seal=True):
    n.verify(False); directory = n.BASE / 'pilot'; summary = n.read(directory / 'summary.json')
    n.require(summary['status'] == 'stock_full_response_measurement_qualified', 'NGINX pilot incomplete or failed')
    if check_seal:
        sealed = n.read(directory / 'evidence-seal.json')['files_sha256']
        actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p != directory / 'evidence-seal.json'}
        n.require(set(sealed) == actual, 'NGINX pilot file set differs')
        for name, digest in sealed.items(): n.require(n.sha(directory / name) == digest, 'NGINX evidence changed')
    rows = []
    for i in range(1, 4):
        case = directory / f'cohort-{i}'; identity(case)
        result = analyze(case, 200, True)
        n.require(result == n.read(case / 'result.json'), 'NGINX result replay differs'); rows.append(result)
    n.require(rows == summary['rows'] and not summary['scientific_collection'] and
              not summary['ready_for_scientific_collection'] and summary['elapsed_sec'] <= 600, 'NGINX summary differs')
    ref = n.read(directory / 'observer-inventory.json'); path = Path(ref['path'])
    n.require(n.sha(path) == ref['sha256'] and n.prior.observer.review(path)['performance_eligible'], 'NGINX root inventory differs')
    return dict(passed=True, status=summary['status'], cohorts=3, measurement_offers=600,
                server_queue_observed=False, scientific_collection=False)


def pilot():
    n.verify(); h.desktop_absent(); os.sched_setaffinity(0, {0, 1})
    directory = n.BASE / 'pilot'; directory.mkdir(); started = time.monotonic(); rows = []
    n.save(directory / 'lifetime.json', dict(protocol=n.PROTOCOL, started_monotonic=started))
    try:
        path = n.ROOT / 'analysis/runtime_io_leftover_observer_audit' / ('nginx-' + str(time.time_ns()) + '.json')
        h.cmd(['sudo', '-n', sys.executable, '-B', str(n.ROOT / 'diagnostic/leftover_observer_audit.py'), '--output', str(path)], timeout=60)
        n.require(n.prior.observer.review(path)['performance_eligible'], 'NGINX root observer inventory ineligible')
        n.save(directory / 'observer-inventory.json', dict(path=str(path), sha256=n.sha(path)))
        for i in range(1, 4):
            n.require(time.monotonic() - started + 130 <= 480, 'NGINX active campaign budget')
            h.desktop_absent(); time.sleep(10)
            print(f'Stock NGINX qualification cohort {i}/3', flush=True)
            rows.append(trial(directory / f'cohort-{i}', 200, True))
        n.save(directory / 'summary.json', dict(status='stock_full_response_measurement_qualified', rows=rows,
            elapsed_sec=time.monotonic() - started, scientific_collection=False, ready_for_scientific_collection=False,
            original_fifo_queue_domain_established=False))
        n.save(directory / 'replay.json', replay(False))
    except BaseException as exc:
        n.save(directory / 'summary.json', dict(status='qualification_unavailable', error=str(exc), rows=rows,
            elapsed_sec=time.monotonic() - started, scientific_collection=False, ready_for_scientific_collection=False))
        raise
    finally:
        n.save(directory / 'finished-lifetime.json', dict(elapsed_sec=time.monotonic() - started))
        evidence_seal(directory)
    print('Stock NGINX full-response measurements qualified; scientific predictions remain untested.', flush=True)
    print('Summary: ' + str(directory / 'summary.json'), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('functional', 'pilot', 'replay', 'watchdog'))
    p.add_argument('--directory', type=Path); args = p.parse_args()
    if args.phase == 'watchdog':
        n.require(args.directory is not None, 'NGINX watchdog directory missing'); watchdog(args.directory)
    else:
        n.require(args.directory is None, 'No NGINX runtime overrides')
        signal.signal(signal.SIGTERM, h.handle_signal); signal.signal(signal.SIGINT, h.handle_signal)
        if args.phase == 'replay': print(json.dumps(replay(), indent=2))
        else: globals()[args.phase]()
