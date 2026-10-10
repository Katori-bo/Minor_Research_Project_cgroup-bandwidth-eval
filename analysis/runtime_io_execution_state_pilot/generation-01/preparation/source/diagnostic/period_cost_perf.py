#!/usr/bin/env python3
"""Bounded root counter helper. IPC accepts operations only, never commands/paths."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time
import uuid

import execution_delay_common as old
import kernel_fixtures as fixtures
import kernel_service_bridge as bridge


def stop(process):
    if process is not None and process.poll() is None:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


class Counter:
    def __init__(self, directory, group, enabled):
        self.directory, self.group, self.enabled = directory, group, enabled
        self.process = None
        self.handles = []
        self.controls = []
        self.started = time.monotonic()
        self.closed = False
        self.state = 'disabled'
        self.ctl_r, self.ctl_w = os.pipe()
        self.ack_r, self.ack_w = os.pipe()
        relative = str(group.relative_to('/sys/fs/cgroup'))
        self.argv = ['/usr/bin/perf', 'stat', '-a', '-C', '2,4', '-A', '-j', '-D', '-1',
                     '--timeout', '300000', '--control', f'fd:{self.ctl_r},{self.ack_w}',
                     '-o', str(directory/'perf.jsonl')]
        self.argv += ['-e', '{cycles:u,instructions:u}', '-G', relative] if enabled else ['-n']
        # A blocked child gives a graceful zero-status end: closing stdin lets
        # perf flush final counts, without racing its signal handler.
        self.argv += ['--', '/usr/bin/cat']
        old.save(directory/'perf_argv.json', self.argv)
        try:
            err = (directory/'perf.stderr').open('x')
            self.handles.append(err)
            self.process = subprocess.Popen(self.argv, stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL, stderr=err, start_new_session=True,
                pass_fds=(self.ctl_r, self.ack_w), env=dict(os.environ, LC_ALL='C'),
                preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))
            os.close(self.ctl_r); self.ctl_r = None
            os.close(self.ack_w); self.ack_w = None
            self.control('disable')  # Acknowledgement also proves collector startup.
        except BaseException:
            self.close()
            raise

    def control(self, op):
        if op not in ('enable', 'disable') or self.process.poll() is not None:
            raise ValueError('invalid operation or perf exited early')
        if op == 'enable' and self.state != 'disabled':
            raise ValueError('counter already enabled')
        before_ns = time.monotonic_ns()
        before = fixtures.stat(self.group)
        os.write(self.ctl_w, (op+'\n').encode())
        until = time.monotonic()+5
        data = b''
        while b'\n' not in data:
            if self.process.poll() is not None:
                raise ValueError('perf startup/control failed; inspect perf.stderr')
            remaining = until-time.monotonic()
            if remaining <= 0:
                raise TimeoutError('perf control acknowledgement timeout')
            ready, _, _ = select.select([self.ack_r], [], [], min(.1, remaining))
            if ready:
                block = os.read(self.ack_r, 32)
                if not block:
                    raise EOFError('perf acknowledgement pipe closed')
                data += block
        # perf 7.2 writes its C-string terminator along with the acknowledgement.
        if data not in (b'ack\n', b'ack\n\x00'):
            raise ValueError('unexpected perf acknowledgement')
        after = fixtures.stat(self.group)
        receipt = dict(op=op, before_ns=before_ns, after_ns=time.monotonic_ns(),
                       cpu_before=before, cpu_after=after)
        self.controls.append(receipt)
        self.state = 'enabled' if op == 'enable' else 'disabled'
        return receipt

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.process is not None:
                self.process.stdin.close()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGTERM)
                    try: self.process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(self.process.pid, signal.SIGKILL)
                        self.process.wait(timeout=3)
        finally:
            for fd in (self.ctl_r, self.ctl_w, self.ack_r, self.ack_w):
                if fd is not None:
                    os.close(fd)
            for h in self.handles:
                h.close()
            old.save(self.directory/'perf_receipt.json', dict(enabled=self.enabled,
                returncode=None if self.process is None else self.process.returncode,
                controls=self.controls, cgroup=str(self.group), argv=self.argv))


def line(stream, seconds, process=None):
    until = time.monotonic()+seconds
    data = bytearray()
    fd = stream.fileno()
    while not data.endswith(b'\n'):
        remaining = until-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('bounded IPC timeout')
        ready, _, _ = select.select([fd], [], [], min(.2, remaining))
        if ready:
            value = os.read(fd, 1)
            if not value:
                raise EOFError('IPC disconnected')
            data += value
            if len(data) > 65536:
                raise ValueError('IPC frame too large')
        elif process is not None and process.poll() is not None:
            raise ValueError('helper/fixture exited early')
    return data.decode().strip()


def fixture(directory, mode, executable):
    directory.mkdir()
    group = Path('/sys/fs/cgroup')/('quota-period-cost-fixture-'+uuid.uuid4().hex)
    worker = counter = None
    error = None
    cleanup = []
    try:
        group.mkdir()
        for name, value in {'cpu.max': 'max 100000', 'cpu.max.burst': '0',
                            'cpuset.cpus': '2,4', 'pids.max': '16', 'memory.max': str(256*1024**2)}.items():
            (group/name).write_text(value)
        if (group/'cpuset.cpus.effective').read_text().strip() != '2,4':
            raise ValueError('fixture CPU scope differs')
        worker = subprocess.Popen([str(executable), mode], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            preexec_fn=lambda: os.sched_setaffinity(0, {2}))
        if line(worker.stdout, 3, worker) != 'READY':
            raise ValueError('fixture did not enter barrier')
        (group/'cgroup.procs').write_text(str(worker.pid))
        old.save(directory/'fixture_identity.json', dict(mode=mode, cgroup=str(group),
            process=old.process_identity(worker.pid), cpus=[2,4], executable_sha256=old.digest(executable)))
        counter = Counter(directory, group, True)
        start = counter.control('enable')
        worker.stdin.write(b'G'); worker.stdin.flush()
        output = [line(worker.stdout, 15, worker), line(worker.stdout, 15, worker)]
        if not output[0].startswith('CHILD ') or output[1] != output[0].replace('CHILD ', 'DONE ', 1):
            raise ValueError('fixed-work parent/child digests differ')
        finish = counter.control('disable')
        counter.close()
        worker.stdin.write(b'Q'); worker.stdin.flush()
        worker.wait(timeout=3)
        if worker.returncode or worker.stderr.read():
            raise ValueError('fixture exited with error')
        old.save(directory/'fixture.json', dict(mode=mode, start=start, stop=finish, output=output))
    except BaseException as e:
        error = str(e)
        raise
    finally:
        if counter:
            try: counter.close()
            except Exception as e: cleanup.append(str(e))
        if worker:
            if worker.poll() is None:
                worker.kill(); worker.wait(timeout=3)
            for stream in (worker.stdin, worker.stdout, worker.stderr):
                stream.close()
        if group.exists():
            try:
                if (group/'cgroup.procs').read_text().strip():
                    raise ValueError('owned fixture cgroup not empty')
                group.rmdir()
            except Exception as e: cleanup.append(str(e))
        old.save(directory/'cleanup.json', dict(errors=cleanup, error=error, cgroup_removed=not group.exists()))
        if cleanup:
            raise ValueError('fixture cleanup needs review: '+repr(cleanup))


def helper(session):
    import period_cost as pc
    if os.geteuid() != 0 or not os.environ.get('SUDO_UID'):
        raise ValueError('root helper must be launched through the external normal-user launcher')
    pc.verify_preparation(session)
    owner = old.read(session/'owner.json')
    if owner['uid'] != int(os.environ['SUDO_UID']) or not old.same_process(owner):
        raise ValueError('helper owner mismatch')
    os.sched_setaffinity(0, {0,1})
    active = None
    index = 0
    fixtures_done = False
    started = time.monotonic()
    def reply(value):
        print(json.dumps(value, allow_nan=False), flush=True)
    def return_evidence(directory):
        for path in directory.rglob('*'):
            if not path.is_symlink() and path.stat().st_uid == 0:
                os.chown(path, int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID']))
    reply(dict(ready=True))
    try:
        while True:
            # No capture may outlive its normal-user owner or a bounded active trial.
            timeout = min(300 if active else 1900, 10800-(time.monotonic()-started))
            if timeout <= 0:
                raise TimeoutError('three-hour pilot ceiling reached')
            request = json.loads(line(sys.stdin.buffer, timeout))
            if not old.same_process(owner) or time.monotonic()-started > 10800:
                raise ValueError('normal-user owner exited or three-hour pilot ceiling reached')
            if set(request) != {'op'}:
                raise ValueError('IPC arguments rejected')
            op = request['op']
            pc.verify_preparation(session)
            if op == 'fixtures' and not fixtures_done and index == 0 and active is None:
                out = session/'counter_fixtures'; out.mkdir()
                for name, mode in [('compute_1','compute'),('compute_2','compute'),
                                   ('compute_3','compute'),('compute_sleep','sleep')]:
                    fixture(out/name, mode, session/'preparation/fixture')
                result = pc.validate_fixtures(out)
                old.save(out/'result.json', result); old.seal(out)
                return_evidence(out)
                fixtures_done = True
                reply(result)
            elif op == 'attach' and fixtures_done and active is None and index < 16:
                spec = pc.matrix()[index]
                directory = session/'trials'/spec['trial']
                if old.read(directory/'pilot_config.json') != spec:
                    raise ValueError('trial differs from frozen helper sequence')
                initial = old.read(directory/'initial.json')
                process = initial['process_identity']
                group = Path(initial['cgroup'])
                container = old.read(directory/'container.json')['inspect']
                expected = Path('/sys/fs/cgroup/system.slice/docker-'+container['Id']+'.scope')
                if group != expected or bridge.cgroup(process['pid']) != group or not old.same_process(process):
                    raise ValueError('live service cgroup/process identity mismatch')
                old.validate_resources(initial['initial_limits'], container['HostConfig'],
                                       initial['resource_baseline'], pc.legacy_config(spec))
                if initial['container_server_sha256'] != old.read(session/'preparation/manifest.json')['server_sha256']:
                    raise ValueError('service executable differs')
                active = Counter(directory, group, spec['counters'])
                reply(dict(attached=True, trial=spec['trial']))
            elif op in ('enable','disable') and active:
                reply(active.control(op))
            elif op == 'detach' and active and active.state == 'disabled':
                active.close(); return_evidence(active.directory); active = None; index += 1
                reply(dict(detached=True))
            elif op == 'finish' and active is None:
                reply(dict(finished=True, detached_trials=index)); return
            else:
                raise ValueError('unknown or out-of-order helper operation')
    finally:
        if active:
            active.close()
        if (session/'counter_fixtures').exists() and not (session/'counter_fixtures/seal.json').exists():
            old.seal(session/'counter_fixtures')
        # Root-created counter evidence is made available to the launching user.
        return_evidence(session)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    from period_cost import owned_directory
    try:
        helper(owned_directory(args.directory))
    except BaseException as e:
        print(str(e), file=sys.stderr)
        raise SystemExit(1)
