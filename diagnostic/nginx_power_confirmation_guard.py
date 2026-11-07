#!/usr/bin/env python3
"""Fixed CPU2 EPP lease with a root-side restoration watchdog, no command overrides."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'analysis/runtime_io_nginx_power_confirmation/generation-01'
POLICY_ROOT = Path('/sys/devices/system/cpu/cpufreq')
FIELDS = ('related_cpus', 'affected_cpus', 'scaling_driver', 'scaling_governor',
          'scaling_min_freq', 'scaling_max_freq', 'energy_performance_preference')
TARGET = 'policy2'
PREFS = {'P0': 'balance_performance', 'P1': 'performance'}
LOCK = Path('/run/lock/cpu-quota-nginx-power-policy.lock')


def identity(pid):
    fields = Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1].split()
    return dict(pid=pid, start_ticks=int(fields[19]))


def alive(owner):
    try:
        return identity(owner['pid']) == owner
    except (FileNotFoundError, ProcessLookupError):
        return False


def snapshot():
    return {p.name: {f: (p / f).read_text().strip() for f in FIELDS if (p / f).exists()}
            for p in sorted(POLICY_ROOT.glob('policy*'))}


def check_baseline(value):
    t = value[TARGET]
    if not (t['related_cpus'] == t['affected_cpus'] == '2' and
            t['scaling_driver'] == 'amd-pstate-epp' and t['scaling_governor'] == 'powersave'
            and t['energy_performance_preference'] == PREFS['P0']):
        raise ValueError('Foreign CPU2 policy baseline or shared policy scope')


def expected(original, policy):
    value = json.loads(json.dumps(original))
    value[TARGET]['energy_performance_preference'] = PREFS[policy]
    return value


def write_pref(value):
    with (POLICY_ROOT / TARGET / 'energy_performance_preference').open('w') as f:
        f.write(value)


def atomic(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n'); f.flush(); os.fsync(f.fileno())
    temporary.replace(path)


class Lease:
    def __init__(self, directory, baseline=None):
        self.directory = directory
        self.original = snapshot()
        check_baseline(self.original)
        if baseline is not None and self.original != baseline:
            raise ValueError('Host policy fields changed from the sealed preparation baseline')
        self.current = 'P0'
        self.changed = False
        self.events = []
        self.journal('armed')

    def journal(self, status, **extra):
        atomic(self.directory / 'policy-journal.json', dict(status=status,
            original=self.original, current_policy=self.current, events=self.events, **extra))

    def check(self):
        actual = snapshot()
        if actual != expected(self.original, self.current):
            raise ValueError('Policy boundary readback differs, including non-target settings')
        return dict(policy=self.current, snapshot=actual, monotonic=time.monotonic())

    def set(self, policy):
        if policy not in PREFS:
            raise ValueError('Foreign policy command')
        self.check()
        # Persist intent before the sysfs write so any interruption restores P0.
        self.changed = True
        self.journal('changing', intended_policy=policy)
        write_pref(PREFS[policy])
        self.current = policy
        value = self.check()
        self.events.append(value)
        self.journal('active')
        return value

    def restore(self, reason):
        errors = []
        if self.changed:
            try:
                # Only restore the declared EPP field; never overwrite other host settings.
                write_pref(self.original[TARGET]['energy_performance_preference'])
            except BaseException as exc:
                errors.append(str(exc))
        actual = snapshot()
        if actual != self.original:
            errors.append('Complete original policy snapshot was not restored')
        self.journal('restored' if not errors else 'restoration_failed', reason=reason,
                     restored_snapshot=actual, errors=errors)
        return dict(restored=not errors, errors=errors, snapshot=actual, reason=reason)


def response(value):
    print(json.dumps(value, allow_nan=False), flush=True)


def run(directory, baseline=None):
    owner = json.loads((directory / 'policy-owner.json').read_text())
    if set(owner) != {'owner', 'deadline_monotonic'} or not alive(owner['owner']):
        raise ValueError('Policy lease owner absent')
    now = time.monotonic()
    if not now < owner['deadline_monotonic'] <= now + 150:
        raise ValueError('Foreign lease lifetime')
    lock = LOCK.open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lease = None; reason = 'unexpected_exit'; completed = False
    try:
        lease = Lease(directory, baseline)
        response(dict(ok=True, armed=lease.check()))
        while True:
            if not alive(owner['owner']):
                reason = 'owner_absent'; break
            if time.monotonic() >= owner['deadline_monotonic']:
                reason = 'lease_deadline'; break
            readable, _, _ = select.select([sys.stdin], [], [], .25)
            if not readable:
                continue
            line = sys.stdin.readline(256)
            if not line:
                reason = 'control_eof'; break
            request = json.loads(line)
            if request == {'op': 'check'}:
                response(dict(ok=True, readback=lease.check()))
            elif set(request) == {'op', 'policy'} and request['op'] == 'set':
                response(dict(ok=True, readback=lease.set(request['policy'])))
            elif request == {'op': 'finish'}:
                reason = 'normal_finish'; completed = True; break
            else:
                raise ValueError('Unknown or foreign policy command')
    except BaseException as exc:
        reason = 'exception: ' + str(exc)
        response(dict(ok=False, error=str(exc)))
    finally:
        if lease is not None:
            restored = lease.restore(reason)
            response(dict(ok=restored['restored'] and completed, restoration=restored))
        lock.close()


def interrupted(signum, frame):
    raise RuntimeError('policy helper signal ' + str(signum))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    if os.geteuid() != 0 or BASE.resolve() not in directory.parents or not directory.is_dir():
        raise SystemExit('Fixed study directory and root required; no alternate sysfs paths')
    if (directory / 'policy-journal.json').exists():
        raise SystemExit('Policy lease cannot be resumed or overwritten')
    for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(signum, interrupted)
    # Authenticate sudo in the caller's controlling terminal first, then detach
    # the privileged watcher itself so parent termination does not remove it.
    if os.getpgrp() != os.getpid():
        os.setsid()
    run(directory, json.loads((BASE / 'policy-baseline.json').read_text()))
