#!/usr/bin/env python3
"""Fresh native-child gzip qualification; frozen imgproxy measurements are untouched."""
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
import traceback
import uuid

import gzip_candidate_prepare as selection
import gzip_qualification_build as build
import imgproxy_qualify as helpers
import leftover_observer_review as observer

ROOT, BASE, SOFTWARE = build.ROOT, build.BASE, build.SOFTWARE
LABEL = 'research.gzip.qualification.owner'
LIMITS = selection.SPEC['qualification']['limits']
PROTOCOL = dict(selection.SPEC['qualification'], candidate=selection.SPEC['candidate'],
    application_user=f'{os.getuid()}:{os.getgid()}', preparation_measurement_offers=25,
    preparation_total_sec=300, preparation_cleanup_reserve_sec=120,
    mandatory_audit='Both arms verify gated child PID/start ticks, pidfd, affinity, same cgroup, exec and reap.',
    cpu_window_end='After client drain and one common audit/idle confirmation, before raw event export.',
    per_job_timeout_sec=10, request_timeout_sec=10, recorded_events_capacity=1024,
    scientific_collection=False, ready_for_scientific_collection=False)
FILES = ('diagnostic/gzip_service.c', 'diagnostic/gzip_qualify.py',
    'diagnostic/gzip_qualification_build.py', 'diagnostic/test_gzip_qualification.py',
    'diagnostic/gzip_client/main.go', 'diagnostic/gzip_client/go.mod',
    'diagnostic/start_gzip_qualification.sh', 'docs/runtime_io_gzip_runner_20261009.md')
read, save, cmd = helpers.read, helpers.save, helpers.cmd
sha = selection.sha


def require(ok, message):
    if not ok: raise ValueError(message)


def inputs():
    selection.verify()
    if (SOFTWARE / 'manifest.json').exists():
        require(read(SOFTWARE / 'manifest.json')['source_sha256'] == sha(ROOT / 'diagnostic/gzip_service.c'),
                'Built native source differs from current service source')
    # Protect the reused ownership/clock/cgroup helper closure without modifying it.
    for name, digest in read(helpers.BASE / 'bundle-seal.json')['files_sha256'].items():
        require(sha(ROOT / name) == digest, 'Reused sealed input changed: ' + name)


def sources():
    return {name: sha(ROOT / name) for name in FILES}


def inspect_owned(name, nonce):
    p = subprocess.run(['docker', 'inspect', name], capture_output=True, text=True, timeout=15)
    if p.returncode:
        if 'no such' in p.stderr.lower(): return None
        raise RuntimeError(p.stderr)
    value = json.loads(p.stdout)[0]
    require(value['Config'].get('Labels', {}).get(LABEL) == nonce, 'Gzip ownership nonce differs')
    return value


def remove_owned(name, nonce):
    value = inspect_owned(name, nonce)
    if value is not None: cmd(['docker', 'rm', '-f', value['Id']])
    require(inspect_owned(name, nonce) is None, 'Owned gzip container remains')


def watchdog(directory):
    owner = read(directory / 'ownership.json')
    while not (directory / 'cleanup.json').exists():
        if not helpers.same_owner(owner['owner']) or time.monotonic() >= owner['deadline_monotonic']:
            errors = []
            client_path = directory / 'client-ownership.json'
            if client_path.exists():
                client = read(client_path)
                if helpers.same_owner(client):
                    try: os.killpg(client['pid'], signal.SIGKILL)
                    except ProcessLookupError: pass
            try: remove_owned(owner['container'], owner['nonce'])
            except Exception as exc: errors.append(str(exc))
            save(directory / 'watchdog-cleanup.json', dict(invalidated=True, errors=errors))
            if helpers.same_owner(owner['owner']): os.kill(owner['owner']['pid'], signal.SIGTERM)
            return
        time.sleep(.5)


def proc_identity(pid):
    text = Path(f'/proc/{pid}/stat').read_text()
    fields = text.rsplit(') ', 1)[1].split()
    return dict(pid=pid, start_ticks=int(fields[19]), parent=int(fields[1]))


def scan_group(pid, group, main_identity, manifest, arm):
    require(helpers.process_identity(pid) == main_identity, 'Wrapper PID identity changed')
    pids = [int(p) for p in (group / 'cgroup.procs').read_text().split()]
    require(pid in pids and len(pids) <= 2, 'Unknown/multiple native processes in service cgroup')
    observed, vanished = [], []
    for process in pids:
        try:
            identity = proc_identity(process)
            require(process == pid or identity['parent'] == pid, 'Native child parent differs')
            require(helpers.bridge.cgroup(process) == group, 'Process cgroup changed')
            executable = sha(Path(f'/proc/{process}/exe'))
            allowed = {manifest['binaries'][arm]} if process == pid else {manifest['binaries'][arm], manifest['gzip_sha256']}
            require(executable in allowed, 'Unknown native executable')
            tids = sorted(int(p.name) for p in Path(f'/proc/{process}/task').iterdir())
            require(len(tids) <= (2 if process == pid else 1), 'Unexpected service/native thread count')
            live = []
            for tid in tids:
                try:
                    require(helpers.bridge.cgroup(tid) == group and os.sched_getaffinity(tid) == {2},
                            f'Thread resource mismatch: tid={tid}')
                    live.append(tid)
                except (FileNotFoundError, ProcessLookupError): vanished.append(tid)
            # Child may exec/reap between reads; it remains a tracked direct child.
            try: after = proc_identity(process)
            except (FileNotFoundError, ProcessLookupError):
                if process == pid: raise
                vanished.append(process); continue
            require(identity == after, 'PID reused during native process scan')
            require(process in live, 'Main process thread unavailable')
            observed.append(dict(**identity, exe_sha256=executable, tids=live, affinity=[2]))
        except (FileNotFoundError, ProcessLookupError):
            if process == pid: raise
            vanished.append(process)
    return dict(cgroup=str(group), processes=observed, vanished_during_scan=vanished,
                main_pid=pid, affinity=[2])


class Service:
    def __init__(self, directory, arm, performance):
        self.directory, self.arm, self.performance = directory, arm, performance
        self.name, self.nonce = 'quota-gzip-' + uuid.uuid4().hex, uuid.uuid4().hex
        self.started = time.monotonic(); self.client = self.watcher = None
        self.manifest = read(SOFTWARE / 'manifest.json'); self.image = read(SOFTWARE / 'images.json')[arm]

    def start(self):
        gate = self.directory / 'qualification'; gate.mkdir(); os.mkfifo(gate / 'start.fifo', 0o600)
        save(self.directory / 'ownership.json', dict(owner=helpers.process_identity(os.getpid()),
             container=self.name, nonce=self.nonce, deadline_monotonic=self.started + 120))
        self.watch_log = (self.directory / 'watchdog.log').open('x')
        self.watcher = subprocess.Popen([sys.executable, '-B', __file__, 'watchdog', '--directory', str(self.directory)],
            stdout=self.watch_log, stderr=subprocess.STDOUT, start_new_session=True)
        argv = ['docker', 'create', '--name', self.name, '--label', LABEL + '=' + self.nonce,
            '--user', PROTOCOL['application_user'], '--cpuset-cpus', '2', '--cpu-period', '100000',
            '--cpu-quota', '25000', '--memory', '512m', '--pids-limit', '128', '--read-only',
            '--tmpfs', '/tmp:rw,size=64m', '--mount', f'type=bind,src={gate},dst=/qualification,readonly',
            '-p', '127.0.0.1::8080', self.image]
        cmd(argv); cmd(['docker', 'start', self.name])
        value = inspect_owned(self.name, self.nonce)
        save(self.directory / 'container.json', dict(argv=argv, inspect=value))
        require(value['Image'] == self.image, 'Pinned gzip image differs')
        self.pid = value['State']['Pid']; self.identity = helpers.process_identity(self.pid)
        self.group = helpers.bridge.cgroup(self.pid)
        require({n: (self.group / n).read_text().strip() for n in LIMITS} == LIMITS, 'Native service limits differ')
        save(self.directory / 'initial.json', dict(pid=self.pid, identity=self.identity,
            cgroup=str(self.group), limits=LIMITS, namespaces=helpers.bridge.namespaces(self.pid),
            ancestors=helpers.bridge.ancestors(self.group), user=PROTOCOL['application_user']))
        helpers.bridge.stopped(self.pid, state='S')
        require((self.group / 'cgroup.procs').read_text().split() == [str(self.pid)] and
                len(list(Path(f'/proc/{self.pid}/task').iterdir())) == 1, 'Startup gate is not sole thread/process')
        actual = {}
        for item, target, expected in (('server', '/server', self.manifest['binaries'][self.arm]),
                ('gzip', '/application/gzip', self.manifest['gzip_sha256'])):
            path = self.directory / ('packaged-' + item)
            cmd(['docker', 'cp', self.name + ':' + target, str(path)])
            actual[item] = sha(path); require(actual[item] == expected, 'Packaged executable differs: ' + item)
            path.unlink()
        save(self.directory / 'executables.json', actual)
        helpers.bridge.release_fifo(gate / 'start.fifo')
        self.base = 'http://127.0.0.1:' + cmd(['docker', 'port', self.name, '8080/tcp']).rsplit(':', 1)[1]
        until = time.monotonic() + 15
        while True:
            self.guard()
            try: self.fetch('health'); break
            except OSError:
                if time.monotonic() > until: raise TimeoutError('Native service startup')
                time.sleep(.1)

    def guard(self):
        require(time.monotonic() - self.started < 120, 'Native service active deadline')
        if self.performance: helpers.desktop_absent()
        require(self.watcher.poll() is None, 'Independent watchdog exited')
        require({n: (self.group / n).read_text().strip() for n in LIMITS} == LIMITS, 'Live native limits changed')
        return scan_group(self.pid, self.group, self.identity, self.manifest, self.arm)

    def fetch(self, endpoint):
        body, _ = helpers.fetch(self.base, endpoint)
        return json.loads(body)

    def collect(self, prefix, count):
        argv = [str(SOFTWARE / 'client'), '--url', self.base + '/compress', '--prefix', prefix,
                '--count', str(count), '--interval-ns', '200000000']
        if self.arm == 'observed': argv.append('--instrumented')
        with (self.directory / (prefix + '.json')).open('x') as log, (self.directory / (prefix + '.stderr')).open('x') as error:
            self.client = subprocess.Popen(argv, stdout=log, stderr=error, start_new_session=True)
            save(self.directory / 'client-ownership.json', helpers.process_identity(self.client.pid))
            until = time.monotonic() + count / 5 + 12
            try:
                while self.client.poll() is None:
                    self.guard()
                    if time.monotonic() > until: raise TimeoutError('Native client drain')
                    time.sleep(.25)
                require(self.client.returncode == 0, 'Native client exited with error')
            finally:
                if self.client.poll() is None: helpers.bridge.stop_known(self.client)
        return read(self.directory / (prefix + '.json'))

    def idle(self, expected):
        until = time.monotonic() + 3
        while True:
            self.guard(); value = self.fetch('health')
            save(self.directory / 'idle-audit.json', value)
            if value['Completed'] >= expected and value['Started'] == value['Completed'] and not value['Queued'] and not value['ActivePID']:
                return value
            if time.monotonic() > until: raise ValueError('Native jobs did not drain')
            time.sleep(.05)

    def export(self):
        self.guard()
        save(self.directory / 'audit.json', self.fetch('qualification/audit'))
        if self.arm == 'observed': save(self.directory / 'events.json', self.fetch('qualification/events'))

    def close(self):
        errors = []
        try: remove_owned(self.name, self.nonce)
        except Exception as exc: errors.append(str(exc))
        save(self.directory / 'cleanup.json', dict(errors=errors, elapsed_sec=time.monotonic() - self.started))
        if self.watcher is not None:
            try: self.watcher.wait(timeout=3)
            except subprocess.TimeoutExpired: helpers.bridge.stop_known(self.watcher)
            self.watch_log.close()
        require(not errors, 'Native owned cleanup unverified')


def validate_client(client, prefix, count, observed):
    correct = read(selection.BASE / 'correctness/result.json')
    require(client['Schema'] == 'gzip-client-v1' and client['Count'] == count and
            client['IntervalNs'] == 200000000 and len(client['Rows']) == count, 'Native client contract differs')
    for i, row in enumerate(client['Rows']):
        require(row['ID'] == row['EchoID'] == f'{prefix}-{i}' and not row['Error'] and row['Status'] == 200 and
            row['ContentType'] == 'application/gzip' and row['BodyBytes'] == correct['output_bytes'] and
            row['BodySHA256'] == correct['output_sha256'], 'Native complete-response outcome failed')
        require(row['ScheduledNs'] == i * 200000000 <= row['DispatchNs'] <= row['HeadersNs'] <= row['BodyDoneNs'],
                'Native client milestone order differs')
        if observed: require(not row['TimingError'] and row['QueueNs'] >= 0 and row['ProcessNs'] > 0, 'Native timing headers failed')
    lag = sorted(r['DispatchNs'] - r['ScheduledNs'] for r in client['Rows'])
    return dict(offers=count, median_e2e_ns=statistics.median(r['BodyDoneNs'] - r['ScheduledNs'] for r in client['Rows']),
                dispatch_p99_ns=lag[math.ceil(.99 * count) - 1], dispatch_max_ns=max(lag),
                body_sha256=correct['output_sha256'])


def validate_audit(audit, ids, observed):
    require(audit['Schema'] == 'gzip-service-v1' and audit['Observed'] is observed and audit['Capacity'] == 1024 and
            audit['Overflow'] == 0 and audit['Started'] == audit['Completed'] == len(ids) and
            audit['Queued'] == audit['ActivePID'] == 0 and audit['ParentPID'] == 1, 'Native lifecycle contract differs')
    rows = audit['Records']
    require(len(rows) == len(ids) and {r['ID'] for r in rows} == ids, 'Native job identities incomplete/duplicated')
    correct = read(selection.BASE / 'correctness/result.json')
    for row in rows:
        require(row['PID'] > 1 and row['StartTicks'] > 0 and row['ExitCode'] == 0 and
                row['BodyBytes'] == correct['output_bytes'] and all(row[k] is True for k in
                ('PIDFD', 'AffinityCPU2', 'CgroupSame', 'SingleThreadAtGate', 'ExecSucceeded', 'Reaped', 'Success')),
                'Native job identity/exec/reap proof failed')


def join(client, events):
    fields = ('EnqueuedNs', 'AcquiredNs', 'SpawnBeforeNs', 'SpawnAfterNs', 'DrainedNs', 'ReapedNs',
              'ResponseBeforeNs', 'ResponseAfterNs', 'ReleasedNs')
    index = {r['ID']: r for r in events['Records']}
    require(len(index) == len(events['Records']) and not events['Overflow'], 'Native event overflow/duplicate')
    for previous, current in zip(events['Records'], events['Records'][1:]):
        require(previous['ReleasedNs'] <= current['AcquiredNs'] and previous['EnqueuedNs'] <= current['EnqueuedNs'],
                'Native FIFO/one-worker order violated')
    queues, process, held = [], [], []
    for row in client['Rows']:
        event = index[row['ID']]
        require(event['Success'] and event[fields[0]] > 0 and
                all(event[a] <= event[b] for a, b in zip(fields, fields[1:])), 'Native stage order failed')
        queue = event['AcquiredNs'] - event['EnqueuedNs']; duration = event['ReapedNs'] - event['AcquiredNs']
        require(row['QueueNs'] == queue and row['ProcessNs'] == duration and
                row['BodyDoneNs'] - row['DispatchNs'] >= queue + duration, 'Native header/raw join or residual failed')
        queues.append(queue); process.append(duration); held.append(event['ReleasedNs'] - event['AcquiredNs'])
    return dict(queue_le_100us_fraction=sum(q <= 100000 for q in queues) / len(queues),
        total_process_ns=sum(process), total_worker_held_ns=sum(held), max_queue_ns=max(queues))


def analyze(case, arm, count, enforce):
    observed = arm == 'observed'; client = read(case / 'measurement.json')
    warmup = read(case / 'warmup.json')
    timing = validate_client(client, 'measurement', count, observed)
    validate_client(warmup, 'warmup', 25, observed)
    ids = {'image-check'} | {r['ID'] for c in (client, warmup) for r in c['Rows']}
    audit = read(case / 'audit.json'); validate_audit(audit, ids, observed)
    counters = read(case / 'measurement-counters.json')
    delta = {key: counters['after'][key] - counters['before'][key] for key in counters['before']}
    require(delta == counters['delta'] and all(v >= 0 for v in delta.values()), 'Native counter differences failed')
    result = dict(arm=arm, **timing, cpu_per_offer_usec=delta['usage_usec'] / count,
                  recorded_throttled_periods=delta['nr_throttled'], native_jobs_verified=len(ids))
    if observed:
        events = read(case / 'events.json')
        require(events['Observed'] is True and events['Schema'] == 'gzip-service-v1' and events['Capacity'] == 1024 and
                events['Completed'] == len(ids) and len(events['Records']) == len(ids) and
                {r['ID'] for r in events['Records']} == ids, 'Native complete event set differs')
        join(warmup, events); result.update(join(client, events))
    exits = []
    if delta['nr_throttled']: exits.append('measurement_throttling')
    if timing['dispatch_p99_ns'] > 2000000 or timing['dispatch_max_ns'] > 10000000: exits.append('dispatch_gate')
    if observed and result['queue_le_100us_fraction'] < .99: exits.append('queue_domain')
    result['domain_exits'] = exits
    if enforce: require(not exits, 'Gzip qualification gate failed: ' + ','.join(exits) + '; no replacement allowed')
    return result


def trial(case, arm, count, performance):
    case.mkdir(); save(case / 'sources-at-start.json', sources())
    service = Service(case, arm, performance)
    try:
        service.start()
        body, _ = helpers.fetch(service.base, 'compress', {'X-Request-ID': 'image-check'})
        (case / 'output.gz').write_bytes(body)
        require(hashlib.sha256(body).hexdigest() == read(selection.BASE / 'correctness/result.json')['output_sha256'] and
                gzip.decompress(body) == (selection.BASE / 'input/corpus.ndjson').read_bytes(), 'Native correctness body failed')
        service.idle(1)
        service.collect('warmup', 25); service.idle(26)
        save(case / 'threads-before.json', service.guard())
        before = helpers.fixtures.stat(service.group); save(case / 'measurement-before.json', before)
        try:
            service.collect('measurement', count); service.idle(26 + count)
        finally:
            after = helpers.fixtures.stat(service.group)
            save(case / 'measurement-counters.json', dict(before=before, after=after,
                delta={k: after[k] - before[k] for k in before}))
        save(case / 'threads-after.json', service.guard())
        service.export()  # Preserve audit and events before applying any domain gates.
        result = analyze(case, arm, count, performance)
        save(case / 'result.json', result); return result
    except BaseException as exc:
        save(case / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        if hasattr(service, 'base') and not (case / 'audit.json').exists():
            try: service.export()
            except Exception as export_error: save(case / 'export-failure.json', dict(error=str(export_error)))
        raise
    finally: service.close()


def identity(case, arm):
    require(not read(case / 'cleanup.json')['errors'] and not (case / 'watchdog-cleanup.json').exists() and
            not (case / 'failure.json').exists(), 'Native case cleanup/invalidation failed')
    require(read(case / 'cleanup.json')['elapsed_sec'] <= 120, 'Native case lifetime exceeded')
    container = read(case / 'container.json')['inspect']; manifest = read(SOFTWARE / 'manifest.json')
    require(container['Image'] == read(SOFTWARE / 'images.json')[arm] and
            container['Config']['Labels'][LABEL] == read(case / 'ownership.json')['nonce'] and
            container['Config']['User'] == PROTOCOL['application_user'], 'Native runtime identity differs')
    require(read(case / 'initial.json')['limits'] == LIMITS and container['HostConfig']['CpuQuota'] == 25000 and
            container['HostConfig']['CpuPeriod'] == 100000 and container['HostConfig']['CpusetCpus'] == '2',
            'Native resource identity differs')
    require(read(case / 'executables.json') == dict(server=manifest['binaries'][arm], gzip=manifest['gzip_sha256']),
            'Native actual executable identity differs')
    require(read(case / 'sources-at-start.json') == sources(), 'Native source changed')
    for phase in ('before', 'after'):
        snapshot = read(case / f'threads-{phase}.json')
        require(snapshot['affinity'] == [2] and snapshot['main_pid'] == read(case / 'initial.json')['pid'] and
                any(p['pid'] == snapshot['main_pid'] for p in snapshot['processes']), 'Native snapshot identity differs')


def prepare():
    inputs(); selection.save(BASE / 'protocol.json', PROTOCOL)
    print('Fresh gzip protocol written; no performance collection.')


def functional():
    inputs(); require(read(BASE / 'protocol.json') == PROTOCOL, 'Fresh gzip protocol differs')
    directory = BASE / 'functional'; directory.mkdir()
    os.sched_setaffinity(0, {0, 1}); started = time.monotonic(); rows = []
    try:
        for arm in ('reference', 'observed'):
            require(time.monotonic() - started + 120 <= 180, 'Preparation active budget exhausted')
            rows.append(trial(directory / arm, arm, 25, False))
        for i, arm in enumerate(('reference', 'observed')):
            identity(directory / arm, arm)
            require(analyze(directory / arm, arm, 25, False) == rows[i], 'Preparation full-path replay failed')
        save(directory / 'summary.json', dict(functional_pass=True, rows=rows, elapsed_sec=time.monotonic() - started,
            scientific_collection=False, observer_cost_qualified=False,
            preparation_domain_exits_retained=True))
    finally:
        save(directory / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(directory)): sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}))
    print('Both native service arms and full measurement/child paths replay; performance remains unqualified.')


def seal():
    inputs(); require(read(BASE / 'protocol.json') == PROTOCOL, 'Gzip protocol differs')
    summary = read(BASE / 'functional/summary.json'); require(summary['functional_pass'], 'Preparation incomplete')
    for i, arm in enumerate(('reference', 'observed')):
        case = BASE / 'functional' / arm; identity(case, arm)
        require(analyze(case, arm, 25, False) == summary['rows'][i], 'Native preparation replay failed')
    require(read(BASE / 'preparation-review.json')['tests_passed'], 'Failure-focused tests not reviewed')
    paths = [ROOT / name for name in FILES]
    paths += [BASE / 'protocol.json', BASE / 'tests.log', BASE / 'preparation-review.json',
              selection.BASE / 'selection-seal.json', helpers.BASE / 'bundle-seal.json']
    paths += [p for parent in (SOFTWARE, BASE / 'functional') for p in parent.rglob('*') if p.is_file()]
    selection.save(BASE / 'bundle-seal.json', dict(protocol=PROTOCOL, baseline=helpers.common.baseline(),
        files_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}))
    print('Gzip runner/runtime/inputs and full-path preparation sealed. External pilot unstarted.')


def verify(boot=True):
    inputs(); sealed = read(BASE / 'bundle-seal.json')
    require(sealed['protocol'] == PROTOCOL, 'Native sealed protocol differs')
    if boot: require(sealed['baseline'] == helpers.common.baseline(), 'Native host boot changed')
    for name, digest in sealed['files_sha256'].items(): require(sha(ROOT / name) == digest, 'Gzip sealed input changed: ' + name)


def replay(check_seal=True):
    verify(False); directory = BASE / 'pilot'; summary = read(directory / 'summary.json')
    require(summary['status'] in ('observer_cost_qualified', 'observer_cost_not_qualified'), 'Native pilot incomplete or failed')
    if check_seal:
        sealed = read(directory / 'evidence-seal.json')['files_sha256']
        actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p != directory / 'evidence-seal.json'}
        require(set(sealed) == actual, 'Native pilot file set differs')
        for name, digest in sealed.items(): require(sha(directory / name) == digest, 'Native pilot evidence changed')
    rows = []
    for pair, order in enumerate(PROTOCOL['pair_orders'], 1):
        for arm in order.split(','):
            case = directory / f'p{pair}_{arm}'; identity(case, arm)
            result = analyze(case, arm, 200, True)
            require(result == read(case / 'result.json'), 'Native trial replay differs')
            rows.append(dict(result, pair=pair))
    effects = paired_effects(rows)
    status = 'observer_cost_qualified' if all(v['upper_le_5pct'] for v in effects.values()) else 'observer_cost_not_qualified'
    require(rows == summary['rows'] and effects == summary['effects'] and status == summary['status'], 'Native paired replay differs')
    require(not summary['scientific_collection'] and not summary['ready_for_scientific_collection'], 'Unsupported science claim')
    ref = read(directory / 'observer-inventory.json')
    require(sha(Path(ref['path'])) == ref['sha256'] and observer.review(Path(ref['path']))['performance_eligible'],
            'Native root inventory differs')
    require(summary['elapsed_sec'] <= 1200, 'Native pilot lifetime exceeded')
    return dict(passed=True, status=status, pairs=6, measurement_offers=2400, scientific_collection=False)


def paired_effects(rows):
    expected = {(i, arm) for i in range(1, 7) for arm in ('reference', 'observed')}
    require(len(rows) == 12 and {(r['pair'], r['arm']) for r in rows} == expected, 'Six native complete pairs required')
    effects = {}
    for key in ('cpu_per_offer_usec', 'median_e2e_ns'):
        require(all(math.isfinite(r[key]) and r[key] > 0 for r in rows), 'Invalid native cost endpoint')
        ratios = [next(r[key] for r in rows if r['pair'] == i and r['arm'] == 'observed') /
                  next(r[key] for r in rows if r['pair'] == i and r['arm'] == 'reference') - 1 for i in range(1, 7)]
        mean = statistics.mean(ratios); half = 2.571 * statistics.stdev(ratios) / math.sqrt(6)
        effects[key] = dict(pair_relative_changes=ratios, mean=mean, ci95=[mean - half, mean + half], upper_le_5pct=mean + half <= .05)
    return effects


def pilot():
    verify(); helpers.desktop_absent(); os.sched_setaffinity(0, {0, 1})
    directory = BASE / 'pilot'; directory.mkdir(); started = time.monotonic(); rows = []
    save(directory / 'lifetime.json', dict(protocol=PROTOCOL, started_monotonic=started))
    try:
        path = ROOT / 'analysis/runtime_io_leftover_observer_audit' / ('gzip-' + str(time.time_ns()) + '.json')
        cmd(['sudo', '-n', sys.executable, '-B', str(ROOT / 'diagnostic/leftover_observer_audit.py'), '--output', str(path)], timeout=60)
        require(observer.review(path)['performance_eligible'], 'Native root inventory not eligible')
        save(directory / 'observer-inventory.json', dict(path=str(path), sha256=sha(path)))
        for pair, order in enumerate(PROTOCOL['pair_orders'], 1):
            for arm in order.split(','):
                require(time.monotonic() - started + 130 <= 1080, 'Gzip total active budget')
                helpers.desktop_absent(); time.sleep(10)
                print(f'Gzip qualification pair {pair}/6: {arm}', flush=True)
                result = trial(directory / f'p{pair}_{arm}', arm, 200, True)
                rows.append(dict(result, pair=pair))
        effects = paired_effects(rows)
        status = 'observer_cost_qualified' if all(v['upper_le_5pct'] for v in effects.values()) else 'observer_cost_not_qualified'
        save(directory / 'summary.json', dict(status=status, rows=rows, effects=effects,
            elapsed_sec=time.monotonic() - started, scientific_collection=False, ready_for_scientific_collection=False))
        save(directory / 'replay.json', replay(False))
    except BaseException as exc:
        save(directory / 'summary.json', dict(status='qualification_unavailable', error=str(exc), rows=rows,
            elapsed_sec=time.monotonic() - started, scientific_collection=False, ready_for_scientific_collection=False))
        raise
    finally:
        save(directory / 'finished-lifetime.json', dict(elapsed_sec=time.monotonic() - started))
        save(directory / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(directory)): sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}))
    print('Gzip qualification: ' + status + '; scientific collection remains unstarted.', flush=True)
    print('Summary: ' + str(directory / 'summary.json'), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare', 'functional', 'seal', 'verify', 'replay', 'pilot', 'watchdog'))
    p.add_argument('--directory', type=Path)
    args = p.parse_args()
    if args.phase == 'watchdog':
        require(args.directory is not None, 'Owned watchdog directory missing'); watchdog(args.directory)
    else:
        require(args.directory is None, 'No runtime directory overrides')
        signal.signal(signal.SIGTERM, helpers.handle_signal); signal.signal(signal.SIGINT, helpers.handle_signal)
        if args.phase == 'replay': print(json.dumps(replay(), indent=2))
        else: globals()[args.phase]()
