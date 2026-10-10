#!/usr/bin/env python3
"""Scoped Arch tool installation and non-recording kernel capability inventory."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

TOOLS = ('perf', 'trace-cmd', 'bpftrace', 'bpf')
ALLOWED = frozenset(TOOLS + ('libtraceevent', 'libpfm', 'libtracefs', 'clang', 'bcc'))
SCHED_EVENTS = ('sched:sched_switch', 'sched:sched_wakeup', 'sched:sched_wakeup_new',
                'sched:sched_process_fork', 'sched:sched_process_exit')


def command(args, timeout=30):
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=timeout,
                           env={**os.environ, 'LC_ALL': 'C'})
        return dict(argv=args, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except (OSError, subprocess.TimeoutExpired) as e:
        return dict(argv=args, returncode=None, stdout='', stderr=str(e))


def checked(args):
    r = command(args)
    if r['returncode'] != 0:
        raise RuntimeError(r['stderr'] or r['stdout'])
    return r['stdout']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def packages():
    return dict(line.split(maxsplit=1) for line in checked(['pacman', '-Q']).splitlines())


def validate_transaction(rows, installed):
    names = [r['name'] for r in rows]
    if len(names) != len(set(names)) or not set(names) <= ALLOWED:
        raise ValueError('transaction includes an unexpected or duplicate package')
    for r in rows:
        if r['repository'] != 'extra' or r['download_bytes'] < 0:
            raise ValueError('unexpected repository or size')
        if r['name'] in installed:
            raise ValueError('refusing replacement/upgrade of an existing package: ' + r['name'])


def transaction():
    if 'ID=arch\n' not in Path('/etc/os-release').read_text():
        raise ValueError('this setup is specific to the verified Arch host')
    if Path('/var/lib/pacman/db.lck').exists():
        raise ValueError('pacman is busy; no lock removal is attempted')
    before = packages()
    raw = checked(['pacman', '-Sp', '--needed', '--print-format', '%n %v %s %r', *TOOLS])
    rows = []
    for line in raw.splitlines():
        name, version, size, repository = line.split()
        rows.append(dict(name=name, version=version, download_bytes=int(size), repository=repository))
    validate_transaction(rows, before)
    if shutil.disk_usage('/').free < 2 * 1024**3:
        raise ValueError('less than 2 GiB free; installation stopped')
    return dict(schema=1, kernel=platform.release(), requested=list(TOOLS), transaction=rows,
                download_bytes=sum(r['download_bytes'] for r in rows), installed_before=before,
                database_sha256={str(p): digest(p) for p in sorted(Path('/var/lib/pacman/sync').glob('*.db'))},
                pacman_config_sha256=digest('/etc/pacman.conf'),
                helper_sha256=digest(__file__))


def install(plan):
    if os.geteuid() != 0:
        raise ValueError('installation needs sudo in the external terminal')
    expected = json.loads(Path(plan).read_text())
    if transaction() != expected:
        raise ValueError('package, host, helper or repository state changed since preview; stopped')
    if not expected['transaction']:
        print('Requested tools are already installed.')
        return
    # No repository refresh, full upgrade, force, dependency bypass or config changes.
    subprocess.run(['pacman', '-S', '--needed', '--noconfirm', *TOOLS], check=True)
    after = packages()
    validate_installation(expected, after)
    print('Installation verified: existing package versions unchanged.')


def validate_installation(plan, after):
    before = plan['installed_before']
    if any(after.get(k) != v for k, v in before.items()):
        raise ValueError('an existing package changed; inspect installation log before research')
    expected = {r['name']: r['version'] for r in plan['transaction']}
    if {k: v for k, v in after.items() if k not in before} != expected:
        raise ValueError('installed package changes do not match the preview')


def read_file(path):
    try:
        return dict(ok=True, text=Path(path).read_text())
    except (OSError, UnicodeError) as e:
        return dict(ok=False, error=str(e))


def inventory():
    root = Path('/sys/kernel/tracing')
    available = read_file(root / 'available_events')
    events = sorted(available.get('text', '').splitlines())
    formats = {}
    for event in SCHED_EVENTS + tuple(e for e in events if 'throttl' in e.lower() or 'cfs_bandwidth' in e):
        group, name = event.split(':', 1)
        formats[event] = read_file(root / 'events' / group / name / 'format')
    functions = read_file(root / 'available_filter_functions')
    selected = [s for s in functions.get('text', '').splitlines()
                if any(k in s for k in ('throttle_cfs_rq', 'sched_cfs_period_timer', 'sched_cfs_slack_timer'))]
    config = {}
    try:
        text = gzip.open('/proc/config.gz', 'rt').read()
        config = {s.split('=', 1)[0]: s.split('=', 1)[1] for s in text.splitlines()
                  if s.startswith(('CONFIG_FTRACE=', 'CONFIG_TRACING=', 'CONFIG_TRACEPOINTS=',
                      'CONFIG_KPROBES=', 'CONFIG_KPROBE_EVENTS=', 'CONFIG_BPF_SYSCALL=',
                      'CONFIG_BPF_EVENTS=', 'CONFIG_DEBUG_INFO_BTF=', 'CONFIG_CFS_BANDWIDTH=',
                      'CONFIG_PERF_EVENTS='))}
    except OSError as e:
        config['error'] = str(e)
    versions = {}
    for name, args in {'perf':['--version'], 'trace-cmd':['-V'],
                       'bpftrace':['--version'], 'bpftool':['version']}.items():
        path = shutil.which(name)
        versions[name] = command([path, *args]) if path else dict(missing=True)
    probes = {}
    if os.geteuid() == 0 and shutil.which('bpftrace'):
        # -l/-lv list probe metadata; no tracing program is attached.
        for name in ('throttle_cfs_rq', 'unthrottle_cfs_rq'):
            probes[name] = command(['bpftrace', '-lv', 'fentry:' + name])
    return dict(schema=1, at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kernel=platform.release(), uid=os.geteuid(), packages=packages(), tools=versions,
        kernel_config=config, btf=dict(exists=Path('/sys/kernel/btf/vmlinux').exists(),
            sha256=digest('/sys/kernel/btf/vmlinux') if Path('/sys/kernel/btf/vmlinux').exists() else None),
        controls={p:read_file(p) for p in ('/proc/sys/kernel/perf_event_paranoid',
            '/proc/sys/kernel/unprivileged_bpf_disabled', '/sys/kernel/security/lockdown')},
        tracefs=dict(available_events=available, formats=formats,
            quota_function_candidates=selected,
            function_list_error=functions.get('error'),
            instances_directory_exists=(root / 'instances').exists(),
            current_tracer=read_file(root / 'current_tracer'), tracing_on=read_file(root / 'tracing_on')),
        typed_function_candidates=probes,
        observation_started=False, quota_mechanism_verified=False,
        limitation='Availability is not qualification. No request trace, throttle interval or goroutine readiness measured.')


def assessment(value):
    events = set(value['tracefs']['available_events'].get('text', '').splitlines())
    named = {e for e in events if 'throttl' in e.lower() or 'cfs_bandwidth' in e}
    cpu_candidates = {e for e in named if e.split(':', 1)[0] in ('sched', 'cgroup')}
    missing = [k for k, v in value['tools'].items() if v.get('missing')]
    failed = [k for k, v in value['tools'].items() if not v.get('missing') and not version_ok(k, v)]
    return dict(tools_missing=missing, protected_inventory_read=value['tracefs']['available_events']['ok'],
        tool_version_checks_failed=failed,
        scheduler_events_missing=sorted(set(SCHED_EVENTS) - events),
        quota_event_candidates=sorted(cpu_candidates),
        non_cpu_throttle_named_events=sorted(named-cpu_candidates),
        quota_function_candidates=value['tracefs']['quota_function_candidates'],
        status='review_inventory_before_fixture' if not missing and not failed and value['tracefs']['available_events']['ok'] else 'setup_incomplete',
        observation_qualified=False, performance_batch_ready=False)


def version_ok(name, result):
    # trace-cmd 3.4 prints its version and usage, then exits 255 for -V/--version.
    # Retain the actual exit code; accept only its specific version banner.
    return result.get('returncode') == 0 or (name == 'trace-cmd' and
        result.get('returncode') == 255 and not result.get('stderr') and
        re.search(r'^trace-cmd version \d+\.\d+(?:\.\d+)?\b', result.get('stdout', ''), re.M) is not None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('plan', 'install', 'inventory', 'assess'))
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--inventory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.action == 'install':
        if not args.plan: parser.error('--plan required')
        install(args.plan)
        return
    if args.action == 'plan': value = transaction()
    elif args.action == 'inventory': value = inventory()
    else:
        if not args.inventory: parser.error('--inventory required')
        value = assessment(json.loads(args.inventory.read_text()))
    text = json.dumps(value, indent=2) + '\n'
    if args.output:
        with args.output.open('x') as f: f.write(text)
    else: print(text, end='')


if __name__ == '__main__':
    main()
