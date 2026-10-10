"""Bounded readiness/count control and independent host-monitor record checks."""
import os
import signal
import subprocess
import sys
import time

import kernel_fixtures as fixtures
import v27r3_common as c
sys.path.insert(0, str(c.ROOT/'scripts'))
from environment_controls import comparable_power


class HostMonitor:
    def __init__(self, directory, guard):
        self.directory, self.guard = directory, guard
        self.process = None
        self.log = None

    def start(self, group, argv=None):
        self.log = (self.directory/'monitor.log').open('x')
        command = argv or [sys.executable, '-B', str(c.ROOT/'diagnostic/v27r3_monitor.py'),
            '--cgroup-path', str(group).removeprefix('/sys/fs/cgroup'),
            '--output', str(self.directory/'monitor.json'),
            '--progress', str(self.directory/'monitor_progress.json')]
        c.save(self.directory/'monitor_argv.json', command)
        self.process = subprocess.Popen(command, stdout=self.log, stderr=subprocess.STDOUT,
            preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
        c.save(self.directory/'monitor_process.json', c.process_identity(self.process.pid))
        self.wait(1, 0, c.design()['monitor_lifecycle']['readiness_bound_sec'], 'monitor_readiness.json')

    def wait(self, minimum, after_ns, seconds, receipt):
        started = time.monotonic_ns()
        deadline = time.monotonic() + seconds
        path = self.directory/'monitor_progress.json'
        latest = None
        while True:
            self.guard()
            if self.process.poll() is not None:
                raise ValueError('host monitor exited before required coverage')
            if path.exists():
                latest = c.read(path)
                if (latest['pid'] != self.process.pid or type(latest['count']) is not int
                        or latest['count'] < 1):
                    raise ValueError('host monitor progress identity/count differs')
                if latest['count'] >= minimum and latest['last_before_ns'] >= after_ns:
                    c.save(self.directory/receipt, dict(wait_started_ns=started,
                        received_ns=time.monotonic_ns(), minimum_records=minimum,
                        required_after_ns=after_ns, bound_sec=seconds, status=latest))
                    return latest
            if time.monotonic() >= deadline:
                count = 0 if latest is None else latest['count']
                raise TimeoutError(f'host monitor coverage timeout: {count} records; required {minimum} and post-drain sample')
            time.sleep(.1)

    def finish(self, after_ns):
        self.wait(c.design()['host_monitor_min_records'], after_ns,
                  c.design()['monitor_lifecycle']['completion_bound_sec'], 'monitor_completion.json')
        self.stop()

    def stop(self):
        if self.process is None:
            return
        try:
            fixtures.stop(self.process, signal.SIGINT)
            if self.process.returncode:
                raise ValueError('host monitor failed: exit '+str(self.process.returncode))
        finally:
            self.log.close()
            self.process = None


def validate(directory, records, environment, observations):
    design = c.design()
    minimum = design['host_monitor_min_records']
    if len(records) < minimum:
        raise ValueError(f'monitor coverage failure: {len(records)} records; required {minimum}')
    if any(m['chatgpt_present'] or any(p['comm'] in ('Codex', 'ChatGPT')
            for p in m['process_cpu_deltas']) for m in records):
        raise ValueError('monitor quiet failure: desktop app detected')
    if any(m['power_settings'] != comparable_power(environment['power_settings']) for m in records):
        raise ValueError('monitor power failure: settings differ')
    previous = 0
    for m in records:
        if not previous <= m['record_before_ns'] <= m['record_after_ns']:
            raise ValueError('monitor record order/clock failure')
        previous = m['record_after_ns']
    if (records[0]['record_after_ns'] > observations['startup']['before_ns']
            or records[-1]['record_before_ns'] < observations['final']['after_ns']):
        raise ValueError('monitor endpoint coverage failure')
    identity = c.read(directory/'monitor_process.json')
    for name, required, after, bound in (
            ('monitor_readiness.json', 1, 0, design['monitor_lifecycle']['readiness_bound_sec']),
            ('monitor_completion.json', minimum, observations['final']['after_ns'],
             design['monitor_lifecycle']['completion_bound_sec'])):
        receipt = c.read(directory/name)
        status = receipt['status']
        count = status['count']
        if (type(count) is not int or not required <= count <= len(records)
                or status['pid'] != identity['pid'] or receipt['minimum_records'] != required
                or receipt['required_after_ns'] != after or receipt['bound_sec'] != bound
                or not 0 <= receipt['received_ns']-receipt['wait_started_ns'] <= (bound+.2)*1e9):
            raise ValueError('monitor lifecycle receipt differs')
        expected = dict(pid=identity['pid'], count=count,
            first_before_ns=records[0]['record_before_ns'], first_after_ns=records[0]['record_after_ns'],
            last_before_ns=records[count-1]['record_before_ns'], last_after_ns=records[count-1]['record_after_ns'])
        if (status != expected or status['last_before_ns'] < after
                or status['last_after_ns'] > receipt['received_ns']):
            raise ValueError('monitor progress does not match saved records')
    if c.read(directory/'monitor_readiness.json')['received_ns'] > observations['startup']['before_ns']:
        raise ValueError('monitor readiness occurred after startup observation')
