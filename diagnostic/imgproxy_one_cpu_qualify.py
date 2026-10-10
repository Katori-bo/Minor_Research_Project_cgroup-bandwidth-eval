#!/usr/bin/env python3
"""A new prospective imgproxy qualification: one granted logical CPU."""
import argparse
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

import imgproxy_qualify as q
import leftover_observer_review as observer

ROOT = q.ROOT
BASE = ROOT / 'analysis/runtime_io_imgproxy_one_cpu_qualification/generation-01'
LIMITS = dict(q.LIMITS, **{'cpuset.cpus.effective': '2'})
FILES = ('diagnostic/imgproxy_one_cpu_qualify.py',
         'diagnostic/test_imgproxy_one_cpu_qualification.py',
         'diagnostic/start_imgproxy_one_cpu_qualification.sh',
         'docs/runtime_io_imgproxy_one_cpu_qualification_20261009.md')
PROTOCOL = dict(candidate='imgproxy-one-cpu-generation-01',
    role='prospective engineering qualification; no scientific replication',
    reason='Enforce a single granted logical CPU despite native worker threads; cause of prior throttle remains unknown.',
    resource_change={'old_cpuset': '2,4', 'new_cpuset': '2'},
    functional_created_cap=2, pilot_created_cap=12, retries=0,
    pilot_total_sec=1200, cleanup_reserve_sec=120, active_trial_sec=120,
    settling_sec=10, pairs=6, pair_orders=q.PROTOCOL['pair_orders'],
    rate=5, interval_ns=200000000, warmup_offers=25, measurement_offers=200,
    limits=LIMITS, gomaxprocs=1, application_workers=1, queue_capacity=128,
    recorded_events_capacity=1024, observer_gates=q.PROTOCOL['observer_gates'],
    image_operation_changed=False, application_binaries_changed=False,
    quota_changed=False, client_changed=False, periodic_memory_free_changed=False,
    counter_sampler=False, scientific_collection=False,
    original_qualification_status='unavailable; retained, never replaced',
    execution_model_gate='Single-CPU allowance constrains simultaneous CPU execution, not background interference or worker/service-time equivalence.')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def historical_inputs():
    q.verify()
    for relative in ('runtime_io_imgproxy_feasibility_review/20261009-generation01',
                     'runtime_io_imgproxy_throttle_probe_review/20261009-generation01'):
        seal = ROOT / 'analysis' / relative / 'evidence-seal.json'
        for name, digest in q.read(seal)['files_sha256'].items():
            require(q.prep.sha(ROOT / name) == digest, 'Historical evidence changed: ' + name)


def source_hashes():
    return {name: q.prep.sha(ROOT / name) for name in FILES}


def create_argv(service, gate_directory):
    return ['docker', 'create', '--name', service.name, '--label', q.LABEL + '=' + service.nonce,
        '--cpuset-cpus', '2', '--cpu-period', '100000', '--cpu-quota', '25000',
        '--memory', '512m', '--pids-limit', '128', '--read-only', '--tmpfs', '/tmp:rw,size=64m',
        '--mount', f'type=bind,src={gate_directory},dst=/qualification,readonly',
        '-p', '127.0.0.1::8080', '-e', 'GOMAXPROCS=1', '-e', 'IMGPROXY_WORKERS=1',
        '-e', 'IMGPROXY_REQUESTS_QUEUE_SIZE=128', '-e', 'IMGPROXY_LOCAL_FILESYSTEM_ROOT=/input',
        '-e', 'IMGPROXY_LOG_LEVEL=error', '-e', 'IMGPROXY_USE_ETAG=false',
        '-e', 'IMGPROXY_USE_LAST_MODIFIED=false',
        '-e', 'IMGPROXY_QUALIFICATION=' + ('1' if service.arm == 'observed' else '0'), service.image]


class Service(q.Service):
    def start(self):
        gate = self.directory / 'qualification'
        gate.mkdir()
        os.mkfifo(gate / 'start.fifo', 0o600)
        q.save(self.directory / 'ownership.json', dict(owner=q.process_identity(os.getpid()),
            container=self.name, nonce=self.nonce,
            deadline_monotonic=self.started + PROTOCOL['active_trial_sec']))
        # Keep the original independently executing nonce/PID-identity watchdog.
        self.watch_log = (self.directory / 'watchdog.log').open('x')
        self.watcher = subprocess.Popen([sys.executable, '-B', q.__file__, 'watchdog',
            '--directory', str(self.directory)], stdout=self.watch_log,
            stderr=subprocess.STDOUT, start_new_session=True)
        argv = create_argv(self, gate)
        q.cmd(argv)
        q.cmd(['docker', 'start', self.name])
        value = q.inspect_owned(self.name, self.nonce)
        q.save(self.directory / 'container.json', dict(argv=argv, inspect=value))
        require(value['Image'] == self.image, 'Pinned image differs')
        self.pid = value['State']['Pid']
        self.identity = q.process_identity(self.pid)
        self.group = q.bridge.cgroup(self.pid)
        self.limits = {n: (self.group / n).read_text().strip() for n in LIMITS}
        require(self.limits == LIMITS, 'Single-CPU resource contract differs: ' + str(self.limits))
        q.save(self.directory / 'initial.json', dict(pid=self.pid, cgroup=str(self.group),
            limits=self.limits, namespaces=q.bridge.namespaces(self.pid),
            ancestors=q.bridge.ancestors(self.group)))
        q.bridge.stopped(self.pid, state='S')
        require(len(list(Path(f'/proc/{self.pid}/task').iterdir())) == 1 and
                (self.group / 'cgroup.procs').read_text().split() == [str(self.pid)],
                'Startup gate is not the sole single-thread process')
        packaged = self.directory / 'packaged-server'
        q.cmd(['docker', 'cp', self.name + ':/server', str(packaged)])
        digest = q.prep.sha(packaged)
        require(digest == q.read(q.SOFTWARE / 'manifest.json')['binaries'][self.arm],
                'Actual packaged server hash differs')
        q.save(self.directory / 'executable.json', dict(sha256=digest))
        packaged.unlink()
        q.bridge.release_fifo(gate / 'start.fifo')
        port = q.cmd(['docker', 'port', self.name, '8080/tcp']).rsplit(':', 1)[1]
        self.base = 'http://127.0.0.1:' + port
        until = time.monotonic() + 15
        while True:
            self.guard()
            try:
                q.fetch(self.base, 'health')
                return self
            except OSError:
                if time.monotonic() > until:
                    raise TimeoutError('Imgproxy startup timeout')
                time.sleep(.1)

    def guard(self):
        require(self.limits == LIMITS, 'Single-CPU constraint changed')
        super().guard()


def export_preserved(service, path, expected):
    until = time.monotonic() + 3
    while True:
        service.guard()
        body, _ = q.fetch(service.base, 'qualification/events')
        value = json.loads(body)
        q.save(path, value)  # Preserve even partial/overflowed data before classifying.
        if len(value['Records']) >= expected:
            return value
        if time.monotonic() > until:
            raise ValueError('Incomplete raw server records retained')
        time.sleep(.05)


def classify_case(directory, arm, performance):
    expected_hash = q.prep.sha(directory / 'output.jpg')
    require(expected_hash == q.read(q.BASE / 'functional/attempt-03/summary.json')['rows'][0]['body_sha256'],
            'Original image output identity differs')
    prefix, count = ('measurement', 200) if performance else ('functional', 8)
    client = q.read(directory / (prefix + '.json'))
    timing = q.validate_client(client, prefix, count, expected_hash)
    result = dict(arm=arm, **timing)
    ids = {'image-check'} | {r['ID'] for r in client['Rows']}
    if performance:
        warmup = q.read(directory / 'warmup.json')
        q.validate_client(warmup, 'warmup', 25, expected_hash)
        ids |= {r['ID'] for r in warmup['Rows']}
        counters = q.read(directory / 'measurement-counters.json')
        delta = {k: counters['after'][k] - counters['before'][k] for k in counters['before']}
        require(delta == counters['delta'] and all(v >= 0 for v in delta.values()), 'Counter regression/delta differs')
        result.update(cpu_per_offer_usec=delta['usage_usec'] / 200,
                      recorded_throttled_periods=delta['nr_throttled'])
    else:
        result['functional_only'] = True
    if arm == 'observed':
        server = q.read(directory / 'events.json')
        require(len(server['Records']) == len(ids) and {r['ID'] for r in server['Records']} == ids,
                'All-offer server identities differ')
        require(all(r['Success'] for r in server['Records']), 'Server request unsuccessful')
        if performance:
            q.join_records(warmup, server)
        result.update(q.join_records(client, server))
        if performance:
            result['cpu_to_worker_wall_ratio'] = delta['usage_usec'] * 1000 / result['total_worker_held_lower_ns']
    if performance:
        # All raw records were saved before applying these unchanged acceptance gates.
        require(delta['nr_throttled'] == 0, 'Measurement throttling; no replacement allowed')
        require(timing['dispatch_p99_ns'] <= 2000000 and timing['dispatch_max_ns'] <= 10000000,
                'Dispatch timing gate failed')
        if arm == 'observed':
            require(result['queue_le_100us_fraction'] >= .99, 'Pilot queue domain exit')
    return result


def trial(directory, arm, performance=False):
    directory.mkdir()
    q.save(directory / 'sources-at-start.json', source_hashes())
    service = Service(directory, arm, performance)
    try:
        service.start()
        body, _ = q.fetch(service.base, q.read(q.SOFTWARE / 'manifest.json')['workload']['path'].lstrip('/'),
                          {'X-Request-ID': 'image-check'})
        (directory / 'output.jpg').write_bytes(body)
        from PIL import Image
        image = Image.open(io.BytesIO(body))
        image.load()
        require(image.format == 'JPEG' and image.size == (300, 300), 'Decoded image differs')
        if performance:
            service.collect('warmup', 25)
            q.save(directory / 'threads-before.json', q.bridge.snapshot(service.pid, service.group))
            before = q.fixtures.stat(service.group)
            q.save(directory / 'measurement-before.json', before)
            try:
                service.collect('measurement', 200)
            finally:
                try:
                    after = q.fixtures.stat(service.group)
                    q.save(directory / 'measurement-counters.json', dict(before=before, after=after,
                        delta={k: after[k] - before[k] for k in before}))
                except Exception as counter_error:
                    q.save(directory / 'counter-failure.json', dict(error=str(counter_error)))
                    raise
            q.save(directory / 'threads-after.json', q.bridge.snapshot(service.pid, service.group))
        else:
            service.collect('functional', 8)
        if arm == 'observed':
            export_preserved(service, directory / 'events.json', 226 if performance else 9)
        result = classify_case(directory, arm, performance)
        q.save(directory / 'result.json', result)
        return result
    except BaseException as exc:
        q.save(directory / 'failure.json', dict(error=str(exc), traceback=traceback.format_exc()))
        # Best-effort raw export also covers early client failure, before owned cleanup.
        if arm == 'observed' and hasattr(service, 'base') and not (directory / 'events.json').exists():
            try:
                export_preserved(service, directory / 'events.json', 0)
            except Exception as export_error:
                q.save(directory / 'export-failure.json', dict(error=str(export_error)))
        raise
    finally:
        service.close()


def check_case_identity(case, arm):
    require(not q.read(case / 'cleanup.json')['errors'], 'Cleanup unverified')
    require(q.read(case / 'cleanup.json')['elapsed_sec'] <= 120, 'Active trial cap exceeded')
    require(not (case / 'watchdog-cleanup.json').exists() and not (case / 'failure.json').exists(),
            'Case invalidated')
    container = q.read(case / 'container.json')['inspect']
    require(container['Image'] == q.read(q.SOFTWARE / 'images.json')[arm], 'Image differs')
    require(container['Config']['Labels'][q.LABEL] == q.read(case / 'ownership.json')['nonce'], 'Ownership differs')
    require(container['HostConfig']['CpusetCpus'] == '2' and
            q.read(case / 'initial.json')['limits'] == LIMITS, 'Single-CPU runtime differs')
    require(q.read(case / 'executable.json')['sha256'] ==
            q.read(q.SOFTWARE / 'manifest.json')['binaries'][arm], 'Executable differs')
    require(q.read(case / 'sources-at-start.json') == source_hashes(), 'New runner sources changed')


def prepare():
    historical_inputs()
    BASE.mkdir(parents=True, exist_ok=False)
    q.save(BASE / 'protocol.json', PROTOCOL)
    print('New one-CPU candidate declared; original results remain unchanged.')


def functional():
    historical_inputs()
    require(q.read(BASE / 'protocol.json') == PROTOCOL, 'Protocol differs')
    directory = BASE / 'functional'
    directory.mkdir()
    os.sched_setaffinity(0, {0, 1})
    rows = [trial(directory / arm, arm) for arm in ('stock', 'observed')]
    require(rows[0]['body_sha256'] == rows[1]['body_sha256'], 'Stock/observed outputs differ')
    for arm in ('stock', 'observed'):
        check_case_identity(directory / arm, arm)
    q.save(directory / 'summary.json', dict(functional_pass=True, rows=rows,
        scientific_collection=False, observer_cost_qualified=False))
    print('Both one-CPU functional services passed; no performance qualification claimed.')


def seal():
    historical_inputs()
    require(q.read(BASE / 'protocol.json') == PROTOCOL, 'Protocol differs')
    summary = q.read(BASE / 'functional/summary.json')
    require(summary['functional_pass'], 'Functional qualification required')
    for i, arm in enumerate(('stock', 'observed')):
        case = BASE / 'functional' / arm
        check_case_identity(case, arm)
        require(classify_case(case, arm, False) == summary['rows'][i], 'Functional replay differs')
    tests = q.read(BASE / 'preparation-review.json')
    require(tests['tests_passed'] and tests['functional_pass'] and not tests['scientific_collection'],
            'Preparation review unavailable')
    paths = [ROOT / name for name in FILES]
    paths += [BASE / 'protocol.json', BASE / 'preparation-review.json', BASE / 'tests.log',
              q.BASE / 'bundle-seal.json']
    paths += [ROOT / 'analysis' / name / 'evidence-seal.json' for name in
              ('runtime_io_imgproxy_feasibility_review/20261009-generation01',
               'runtime_io_imgproxy_throttle_probe_review/20261009-generation01')]
    paths += [p for p in (BASE / 'functional').rglob('*') if p.is_file()]
    with (BASE / 'bundle-seal.json').open('x') as f:
        json.dump(dict(protocol=PROTOCOL, baseline=q.common.baseline(),
            files_sha256={str(p.relative_to(ROOT)): q.prep.sha(p) for p in paths}), f, indent=2)
        f.write('\n')
    print('Separate one-CPU bundle sealed; performance pilot has not started.')


def verify(check_boot=True):
    # The original bundle protects the entire imported helper/runtime/client closure.
    if check_boot:
        historical_inputs()
    else:
        for name, digest in q.read(q.BASE / 'bundle-seal.json')['files_sha256'].items():
            require(q.prep.sha(ROOT / name) == digest, 'Original sealed input changed: ' + name)
    seal = q.read(BASE / 'bundle-seal.json')
    require(seal['protocol'] == PROTOCOL, 'New protocol differs')
    if check_boot:
        require(seal['baseline'] == q.common.baseline(), 'Host boot differs')
    for name, digest in seal['files_sha256'].items():
        require(q.prep.sha(ROOT / name) == digest, 'New sealed input changed: ' + name)


def review_inventory(path):
    require(observer.review(path)['performance_eligible'], 'Root observer inventory ineligible')


def replay(check_evidence=True):
    verify(check_boot=False)
    directory = BASE / 'pilot'
    summary = q.read(directory / 'summary.json')
    require(summary['status'] in ('observer_cost_qualified', 'observer_cost_not_qualified'),
            'Pilot incomplete/unavailable; preserved failure cannot pass')
    if check_evidence:
        seal = q.read(directory / 'evidence-seal.json')['files_sha256']
        actual = {str(p.relative_to(directory)) for p in directory.rglob('*')
                  if p.is_file() and p != directory / 'evidence-seal.json'}
        require(actual == set(seal), 'Pilot evidence file set differs')
        for name, digest in seal.items():
            require(q.prep.sha(directory / name) == digest, 'Pilot evidence changed: ' + name)
    rows = []
    for pair, order in enumerate(PROTOCOL['pair_orders'], 1):
        for arm in order.split(','):
            case = directory / f'p{pair}_{arm}'
            check_case_identity(case, arm)
            result = classify_case(case, arm, True)
            require(result == q.read(case / 'result.json'), 'Trial replay differs')
            rows.append(dict(result, pair=pair))
    effects = q.effects_from(rows)
    status = 'observer_cost_qualified' if all(v['upper_le_5pct'] for v in effects.values()) else 'observer_cost_not_qualified'
    require(rows == summary['rows'] and effects == summary['effects'] and status == summary['status'],
            'Paired summary replay differs')
    require(not summary['scientific_collection'] and not summary['ready_for_scientific_collection'],
            'Engineering evidence mislabeled')
    ref = q.read(directory / 'observer-inventory.json')
    require(q.prep.sha(Path(ref['path'])) == ref['sha256'], 'Root inventory changed')
    review_inventory(Path(ref['path']))
    require(summary['elapsed_sec'] <= PROTOCOL['pilot_total_sec'], 'Pilot total cap exceeded')
    return dict(passed=True, status=status, pairs=6, measurement_offers=2400,
                scientific_collection=False, original_pilot_replaced=False)


def pilot():
    verify()
    q.desktop_absent()
    os.sched_setaffinity(0, {0, 1})
    directory = BASE / 'pilot'
    directory.mkdir()
    started = time.monotonic()
    deadline = started + PROTOCOL['pilot_total_sec'] - PROTOCOL['cleanup_reserve_sec']
    rows = []
    q.save(directory / 'lifetime.json', dict(started_monotonic=started,
        deadline_monotonic=deadline, protocol=PROTOCOL))
    try:
        evidence = ROOT / 'analysis/runtime_io_leftover_observer_audit' / ('imgproxy-one-cpu-' + str(time.time_ns()) + '.json')
        q.cmd(['sudo', '-n', sys.executable, '-B', str(ROOT / 'diagnostic/leftover_observer_audit.py'),
               '--output', str(evidence)], timeout=60)
        review_inventory(evidence)
        q.save(directory / 'observer-inventory.json', dict(path=str(evidence), sha256=q.prep.sha(evidence)))
        for pair, order in enumerate(PROTOCOL['pair_orders'], 1):
            for arm in order.split(','):
                q.desktop_absent()
                if time.monotonic() + PROTOCOL['settling_sec'] + PROTOCOL['active_trial_sec'] > deadline:
                    raise TimeoutError('Total qualification limit')
                time.sleep(PROTOCOL['settling_sec'])
                print(f'One-CPU qualification pair {pair}/6: {arm}', flush=True)
                row = trial(directory / f'p{pair}_{arm}', arm, True)
                rows.append(dict(row, pair=pair))
        effects = q.effects_from(rows)
        status = 'observer_cost_qualified' if all(v['upper_le_5pct'] for v in effects.values()) else 'observer_cost_not_qualified'
        q.save(directory / 'summary.json', dict(status=status, rows=rows, effects=effects,
            elapsed_sec=time.monotonic() - started, scientific_collection=False,
            ready_for_scientific_collection=False, single_cpu_constraint_verified=True,
            original_pilot_replaced=False,
            next_step='Review background interference and timing/model assumptions before a sealed prospective science protocol.'))
        q.save(directory / 'replay.json', replay(check_evidence=False))
    except BaseException as exc:
        q.save(directory / 'summary.json', dict(status='qualification_unavailable', error=str(exc),
            rows=rows, elapsed_sec=time.monotonic() - started, scientific_collection=False,
            ready_for_scientific_collection=False, original_pilot_replaced=False))
        raise
    finally:
        q.save(directory / 'finished-lifetime.json', dict(elapsed_sec=time.monotonic() - started))
        q.save(directory / 'evidence-seal.json', dict(files_sha256={str(p.relative_to(directory)): q.prep.sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}))
    print('One-CPU qualification: ' + status + '; scientific collection remains unstarted.', flush=True)
    print('Summary: ' + str(directory / 'summary.json'), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=('prepare', 'functional', 'seal', 'verify', 'pilot', 'replay'))
    args = p.parse_args()
    signal.signal(signal.SIGTERM, q.handle_signal)
    signal.signal(signal.SIGINT, q.handle_signal)
    if args.phase == 'replay':
        print(json.dumps(replay(), indent=2))
    else:
        globals()[args.phase]()
