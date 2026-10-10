"""Normal-user Docker ownership, FIFO startup and independent bounded cleanup."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import uuid

import worker_control_common as c
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures
import repeatability_analysis

LABEL = 'research.v19.owner'
WATCHDOG_SEC = 360


def command(argv, timeout=20):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError('command failed: '+repr(argv)+': '+p.stderr.strip())
    return p.stdout.strip()


def owned_inspect(container, nonce):
    p = subprocess.run(['docker', 'inspect', container], capture_output=True, text=True, timeout=15)
    if p.returncode:
        if 'No such' in p.stderr:
            return None
        raise ValueError('owned-container inspection failed: '+p.stderr)
    value = json.loads(p.stdout)[0]
    if value['Config'].get('Labels', {}).get(LABEL) != nonce:
        raise ValueError('container ownership changed; refusing cleanup')
    return value


def remove_owned(container, nonce):
    value = owned_inspect(container, nonce)
    if value is not None:
        # Immutable full ID, not a name that can be reused after inspection.
        command(['docker', 'rm', '-f', value['Id']], timeout=20)
    if owned_inspect(container, nonce) is not None:
        raise ValueError('owned container remains after cleanup')


def watchdog(directory):
    ownership = c.read(directory/'ownership.json')
    while True:
        if (directory/'cleanup.json').exists():
            return
        dead = not c.same_process(ownership['owner'])
        expired = time.monotonic()-ownership['started_monotonic'] > WATCHDOG_SEC
        if dead or expired:
            if expired and c.same_process(ownership['owner']):
                os.kill(ownership['owner']['pid'], signal.SIGTERM)
            reason = 'owner exited' if dead else 'active-trial watchdog expired'
            errors = []
            try:
                remove_owned(ownership['container'], ownership['nonce'])
            except Exception as e:
                errors.append(str(e))
            c.save(directory/'watchdog_cleanup.json', dict(invalidated=True, reason=reason,
                   errors=errors, owner=ownership['owner'], container=ownership['container']))
            return
        time.sleep(.5)


class Service:
    def __init__(self, session, config, directory, watch=True):
        self.session, self.config, self.directory = session, config, directory
        self.manifest = c.read(session/'preparation/manifest.json')
        self.container = 'quota-v19-'+uuid.uuid4().hex
        self.nonce = uuid.uuid4().hex
        self.group = None
        self.pid = None
        self.closed = False
        self.created = False
        self.watch = watch
        self.watcher = None
        self.started = time.monotonic()
        self.snapshots = []

    def create(self):
        q = self.directory/'qualification'
        q.mkdir()
        shutil.copy2(self.session/'preparation/gate', q/'gate')
        os.mkfifo(q/'start.fifo', 0o600)
        argv = c.service_argv(self.manifest['image'], q, self.container, self.config)
        argv[2:2] = ['--label', LABEL+'='+self.nonce]
        c.save(self.directory/'ownership.json', dict(owner=c.process_identity(os.getpid()),
            container=self.container, nonce=self.nonce, started_monotonic=self.started))
        # Persist ownership before issuing create; partial create is cleaned in finally.
        self.created = True
        command(argv)
        if self.watch:
            self.watch_log = (self.directory/'watchdog.log').open('x')
            self.watcher = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                '--watchdog', str(self.directory)], stdout=self.watch_log, stderr=subprocess.STDOUT,
                start_new_session=True, preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
        command(['docker', 'start', self.container])
        inspect = owned_inspect(self.container, self.nonce)
        self.pid = inspect['State']['Pid']
        bridge.stopped(self.pid, state='S')
        self.process = c.process_identity(self.pid)
        self.group = bridge.cgroup(self.pid)
        if os.sched_getaffinity(self.pid) != {2, 4} or (self.group/'cgroup.procs').read_text().split() != [str(self.pid)]:
            raise ValueError('single-thread startup affinity/ownership mismatch')
        limits = {n: (self.group/n).read_text().strip() for n in
                  ('cpu.max', 'cpu.max.burst', 'cpuset.cpus.effective', 'memory.max', 'pids.max')}
        c.validate_resources(limits, inspect['HostConfig'], self.manifest['resource_baseline'])
        if (inspect['Image'] != self.manifest['image'] or len(inspect['Mounts']) != 1
                or inspect['Mounts'][0]['Destination'] != '/qualification' or inspect['Mounts'][0]['RW']):
            raise ValueError('packaged image/startup mount differs')
        if inspect['Path'] != '/qualification/gate' or inspect['Args'] != ['--server']:
            raise ValueError('startup command differs')
        if c.digest(q/'gate') != self.manifest['gate_sha256']:
            raise ValueError('startup gate hash differs')
        # Normal users cannot dereference a root-owned container process's /proc/exe.
        # Read the actual packaged file through the already-authorized Docker daemon
        # before release. The verified gate execs /server in the same process.
        command(['docker', 'cp', self.container+':/server', str(self.directory/'container.server')])
        if c.digest(self.directory/'container.server') != self.manifest['server_sha256']:
            raise ValueError('actual container executable differs')
        metadata = dict(pid=self.pid, process_identity=self.process, cgroup=str(self.group),
            cgroup_id=self.group.stat().st_ino, capped=True, initial_limits=limits,
            resource_baseline=self.manifest['resource_baseline'], time_namespaces=bridge.namespaces(self.pid),
            uncapped_ancestors=bridge.ancestors(self.group), initial_cpu_stat=fixtures.stat(self.group),
            gate_sha256=c.digest(q/'gate'), container_server_sha256=c.digest(self.directory/'container.server'),
            startup='single-thread FIFO then verified gate exec into packaged /server')
        if metadata['initial_cpu_stat'].get('nr_throttled', 0):
            raise ValueError('startup gate already throttled')
        c.save(self.directory/'container.json', dict(argv=argv, inspect=inspect))
        c.save(self.directory/'initial.json', metadata)
        port = command(['docker', 'port', self.container, '8080/tcp']).rsplit(':', 1)[1]
        self.base = 'http://127.0.0.1:'+port
        return dict(base=self.base, cgroup=str(self.group))

    def guard(self):
        if time.monotonic()-self.started > WATCHDOG_SEC:
            raise TimeoutError('360-second active-trial watchdog')
        if not c.same_process(self.process) or bridge.cgroup(self.pid) != self.group:
            raise ValueError('owned service process died or identity changed')
        if self.watcher and self.watcher.poll() is not None:
            raise ValueError('independent watchdog exited early')

    def release(self):
        self.guard()
        bridge.release_fifo(self.directory/'qualification/start.fifo')
        until = time.monotonic()+10
        while True:
            self.guard()
            try:
                health = bridge.get(self.base, 'health')
                break
            except OSError:
                if time.monotonic() > until:
                    raise TimeoutError('service startup timeout')
                time.sleep(.05)
        if Path(f'/proc/{self.pid}/comm').read_text().strip() != 'server':
            raise ValueError('FIFO did not exec retained server in original process')
        repeatability_analysis.validate_state(health, 'legacy_a')
        if (health['workers'] != self.config['workers'] or health['gomaxprocs'] != 1
                or health['queue_cap'] != 128 or health['go_version'] != 'go1.26.1' or not health['instrument']):
            raise ValueError('actual service/runtime settings differ')
        c.save(self.directory/'identity.json', dict(health=health,
            image=self.manifest['image'], server_sha256=self.manifest['server_sha256'],
            loadgen_sha256=self.manifest['loadgen_sha256'], gate_sha256=self.manifest['gate_sha256'],
            executable_verification='Docker-copy packaged file hash plus verified gate exec/same PID and server health',
            process_identity_after_exec=c.process_identity(self.pid)))
        return health

    def observe(self):
        self.guard()
        self.snapshots.append(bridge.snapshot(self.pid, self.group))
        c.save(self.directory/'thread_snapshots.json', self.snapshots)
        before = time.monotonic_ns()
        counters = fixtures.stat(self.group)
        return dict(before_ns=before, after_ns=time.monotonic_ns(), cpu_stat=counters)

    def close(self, failure=None):
        if self.closed:
            result = c.read(self.directory/'cleanup.json')
            if result['errors']:
                raise ValueError('owned cleanup remains unverified')
            return result
        if self.watcher:
            fixtures.stop(self.watcher, signal.SIGTERM)
            self.watch_log.close()
        errors = []
        removed = False
        if self.created:
            try:
                inspected = owned_inspect(self.container, self.nonce)
                if inspected is not None:
                    logs = subprocess.run(['docker', 'logs', inspected['Id']], capture_output=True, timeout=10)
                    (self.directory/'container.stdout').write_bytes(logs.stdout)
                    (self.directory/'container.stderr').write_bytes(logs.stderr)
                    if logs.returncode:
                        raise ValueError('owned service logs unavailable')
                remove_owned(self.container, self.nonce)
                removed = True
            except Exception as e:
                errors.append(str(e))
        until = time.monotonic()+5
        while self.group and self.group.exists() and time.monotonic() < until:
            time.sleep(.05)
        group_removed = self.group is not None and not self.group.exists()
        if self.group is not None and not group_removed:
            errors.append('owned cgroup still exists')
        result = dict(errors=errors, failure=failure, container_removed=removed,
                      cgroup_removed=group_removed, tracing_used=False,
                      watchdog_intervened=(self.directory/'watchdog_cleanup.json').exists())
        c.save(self.directory/'cleanup.json', result)
        self.closed = True
        if errors:
            raise ValueError('owned cleanup requires review: '+'; '.join(errors))
        return result


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--watchdog':
        raise SystemExit('internal bounded-watchdog entry point only')
    watchdog(Path(sys.argv[2]))
