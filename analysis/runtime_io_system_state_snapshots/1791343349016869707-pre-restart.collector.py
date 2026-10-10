#!/usr/bin/env python3
"""Read-only pre/post-restart evidence capture; never change host settings."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'analysis/runtime_io_system_state_snapshots'


def read(path):
    try:
        return {'ok': True, 'text': Path(path).read_text().strip()}
    except (OSError, UnicodeError) as exc:
        return {'ok': False, 'error': str(exc)}


def command(argv):
    if not shutil.which(argv[0]):
        return {'ok': False, 'argv': argv, 'error': 'command unavailable'}
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=12,
                                env=dict(os.environ, LC_ALL='C'))
        return {'ok': result.returncode == 0, 'argv': argv,
                'returncode': result.returncode, 'stdout': result.stdout,
                'stderr': result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'argv': argv, 'error': str(exc)}


def files(paths):
    return {str(p): read(p) for p in sorted(set(map(Path, paths)))}


def processes():
    rows = {}
    errors = []
    for p in Path('/proc').glob('[0-9]*'):
        try:
            fields = (p / 'stat').read_text().rsplit(') ', 1)[1].split()
            rows[p.name] = dict(comm=(p / 'comm').read_text().strip(),
                                uid=p.stat().st_uid, start_ticks=int(fields[19]),
                                cpu_ticks=int(fields[11]) + int(fields[12]),
                                rss_pages=int(fields[21]), threads=int(fields[17]))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (OSError, ValueError, IndexError) as exc:
            errors.append({'pid': p.name, 'error': str(exc)})
    # No command arguments, environment variables, general file descriptors,
    # journal messages or general user configuration contents are collected.
    return {'rows': rows, 'errors': errors}


def dynamic_state():
    paths = ['/proc/uptime', '/proc/loadavg', '/proc/meminfo', '/proc/stat',
             '/proc/pressure/cpu', '/proc/pressure/memory', '/proc/pressure/io',
             '/proc/interrupts', '/proc/softirqs']
    cpu = Path('/sys/devices/system/cpu')
    paths += list(cpu.glob('cpufreq/policy*/scaling_cur_freq'))
    paths += list(cpu.glob('cpu*/cpuidle/state*/usage'))
    paths += list(cpu.glob('cpu*/cpuidle/state*/time'))
    paths += list(Path('/sys/class/power_supply').glob('*/online'))
    paths += list(Path('/sys/class/power_supply').glob('*/status'))
    sensors = {}
    for base in sorted(Path('/sys/class/hwmon').glob('hwmon*')):
        for p in base.glob('temp*_input'):
            key = ':'.join((read(base / 'name').get('text', base.name),
                            read(p.with_name(p.name.replace('_input', '_label')))
                            .get('text', p.stem)))
            sensors[key] = {'value': read(p), 'path': str(p)}
    return {'files': files(paths), 'temperature_sensors': sensors,
            'processes': processes()}


def capture(label):
    cpu = Path('/sys/devices/system/cpu')
    paths = [cpu / n for n in ('online', 'offline', 'present', 'possible')]
    paths += [cpu / 'cpufreq/boost', cpu / 'amd_pstate/status',
              cpu / 'smt/control', cpu / 'smt/active',
              Path('/sys/firmware/acpi/platform_profile'),
              Path('/sys/firmware/acpi/platform_profile_choices')]
    for pattern in ('cpufreq/policy*',):
        for base in cpu.glob(pattern):
            paths += [base / n for n in ('scaling_driver', 'scaling_governor',
                      'energy_performance_preference', 'scaling_min_freq',
                      'scaling_max_freq', 'cpuinfo_min_freq', 'cpuinfo_max_freq',
                      'related_cpus', 'affected_cpus', 'boost') if (base / n).exists()]
    for pattern in ('cpu*/topology/*', 'cpu*/acpi_cppc/*', 'cpu*/microcode/version',
                    'cpu*/cpuidle/state*/name', 'cpu*/cpuidle/state*/disable',
                    'cpu*/cpuidle/state*/latency', 'cpu*/cpuidle/state*/residency'):
        paths += [p for p in cpu.glob(pattern) if p.is_file() and p.name != 'feedback_ctrs']
    paths += [Path('/sys/class/dmi/id') / n for n in
              ('bios_vendor', 'bios_version', 'bios_date', 'product_name', 'board_name')]
    paths += list(Path('/sys/class/drm').glob('card*/device/power_dpm_force_performance_level'))
    paths += [Path('/proc/sys') / n for n in (
        'kernel/perf_event_paranoid', 'kernel/unprivileged_bpf_disabled',
        'kernel/sched_cfs_bandwidth_slice_us', 'kernel/sched_autogroup_enabled',
        'kernel/nmi_watchdog', 'kernel/numa_balancing', 'kernel/randomize_va_space',
        'vm/swappiness', 'vm/dirty_background_ratio', 'vm/dirty_ratio')]
    paths += list(Path('/sys/kernel/mm/transparent_hugepage').glob('enabled'))
    paths += list(Path('/sys/kernel/mm/transparent_hugepage').glob('defrag'))
    paths += [Path('/sys/fs/cgroup') / n for n in (
        'cgroup.controllers', 'cgroup.subtree_control', 'cpu.max', 'cpu.max.burst',
        'cpu.weight', 'cpuset.cpus.effective', 'memory.max') if (Path('/sys/fs/cgroup') / n).exists()]
    fixed = files(paths)
    commands = {
        'packages': ['pacman', '-Q'],
        'cpu_inventory': ['lscpu', '--json'],
        'power_profile': ['powerprofilesctl', 'get'],
        'power_profile_details': ['powerprofilesctl', 'list'],
        'enabled_services': ['systemctl', 'list-unit-files', '--type=service',
                             '--no-legend', '--no-pager'],
        'running_services': ['systemctl', 'list-units', '--type=service',
                             '--state=running', '--no-legend', '--no-pager', '--plain'],
        'running_user_services': ['systemctl', '--user', 'list-units', '--type=service',
                                  '--state=running', '--no-legend', '--no-pager', '--plain'],
        'docker_runtime': ['docker', 'info', '--format',
            '{{json .ServerVersion}} {{json .CgroupDriver}} {{json .CgroupVersion}} '
            '{{json .Driver}} {{json .DockerRootDir}} {{json .KernelVersion}} '
            '{{json .SecurityOptions}}'],
        'docker_containers': ['docker', 'ps', '--no-trunc', '--format',
                              '{{.ID}} {{.Names}} {{.Image}} {{.Status}}'],
        'docker_images': ['docker', 'image', 'ls', '--no-trunc', '--digests',
                         '--format', '{{.ID}} {{.Repository}}:{{.Tag}} {{.Digest}}'],
        'research_head': ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
        'research_changes': ['git', '-C', str(ROOT), 'status', '--porcelain'],
    }
    started = datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=5) as pool:
        receipts = dict(zip(commands, pool.map(command, commands.values())))
    # A short activity sample is separate from fixed settings. It runs after
    # command inventories so their subprocess CPU does not dominate the sample.
    t0 = time.monotonic()
    first = dynamic_state()
    time.sleep(5)
    last = dynamic_state()
    elapsed = time.monotonic() - t0
    hz = os.sysconf('SC_CLK_TCK')
    activity = []
    for pid, row in last['processes']['rows'].items():
        old = first['processes']['rows'].get(pid)
        if old and old['start_ticks'] == row['start_ticks']:
            activity.append(dict(pid=int(pid), comm=row['comm'], uid=row['uid'],
                one_core_cpu_percent=100 * (row['cpu_ticks'] - old['cpu_ticks']) / hz / elapsed,
                rss_bytes=row['rss_pages'] * os.sysconf('SC_PAGE_SIZE')))
    source_hashes = {}
    for base in (ROOT / 'diagnostic', ROOT / 'scripts'):
        for p in sorted(base.glob('*')):
            if p.is_file() and p.suffix in ('.py', '.sh', '.go'):
                source_hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    cpuinfo = read('/proc/cpuinfo')
    return dict(schema=1, label=label, started_utc=started,
        finished_utc=datetime.now(timezone.utc).isoformat(), uid=os.geteuid(),
        boot_id=read('/proc/sys/kernel/random/boot_id'),
        kernel=dict(release=platform.release(), version=platform.version(),
                    command_line=read('/proc/cmdline'), os_release=read('/etc/os-release'),
                    microcode=sorted(set(re.findall(r'^microcode\s*:\s*(.*)$',
                                  cpuinfo.get('text', ''), re.M)))),
        configuration=fixed, commands=receipts, source_hashes=source_hashes,
        activity=dict(sample_sec=elapsed, first=first, last=last,
                      processes=sorted(activity, key=lambda r: -r['one_core_cpu_percent'])),
        configuration_readback=files(paths),
        limitations=['Snapshot taken while the research app is open; not a benchmark baseline.',
                     'Five-second activity and frequency/temperature samples are transient.',
                     'Root-only BPF/tracing/descriptor ownership is not audited by this capture.',
                     'Recorded frequency readings are not execution-weighted worker clocks.',
                     'A reboot changes multiple conditions; a difference alone does not prove causation.'],
        configuration_changed=False, performance_experiment_launched=False)


def flatten(value, prefix=''):
    if isinstance(value, dict):
        for key in sorted(value):
            yield from flatten(value[key], prefix + '/' + key)
    else:
        yield prefix, value


def comparison(before, after):
    def settings(value):
        result = dict(kernel=value['kernel'], source_hashes=value['source_hashes'])
        result['configuration'] = {k: v['text'] for k, v in value['configuration'].items() if v['ok']}
        # Only successful command data is compared as observed configuration.
        for key in ('packages', 'cpu_inventory', 'power_profile', 'power_profile_details',
                    'enabled_services', 'docker_runtime', 'docker_images', 'research_head'):
            receipt = value['commands'][key]
            if receipt['ok']:
                text = receipt['stdout']
                if key == 'cpu_inventory':
                    inventory = json.loads(text)
                    inventory['lscpu'] = [row for row in inventory['lscpu']
                        if row['field'] not in ('CPU(s) scaling MHz:', 'CPU MHz:')]
                    text = inventory
                if key in ('packages', 'enabled_services', 'docker_images'):
                    text = '\n'.join(sorted(text.splitlines()))
                result[key] = text
        return dict(flatten(result))
    a, b = settings(before), settings(after)
    changes = [dict(field=k, before=a.get(k), after=b.get(k)) for k in sorted(set(a) | set(b))
               if a.get(k) != b.get(k)]
    gaps = []
    for name, value in (('before', before), ('after', after)):
        gaps += [dict(snapshot=name, section='configuration', field=k, detail=v)
                 for k, v in value['configuration'].items() if not v['ok']]
        gaps += [dict(snapshot=name, section='commands', field=k, detail=v)
                 for k, v in value['commands'].items() if not v['ok']]
    return dict(schema=1, before_label=before['label'], after_label=after['label'],
        before_boot=before['boot_id'], after_boot=after['boot_id'],
        recorded_configuration_changes=changes, coverage_gaps=gaps,
        before_activity=before['activity']['processes'][:20],
        after_activity=after['activity']['processes'][:20],
        limitations=['Activity is descriptive and expected to vary across boots.',
                     'Missing/new readable entries may reflect coverage rather than a changed setting.',
                     'Snapshot differences are candidate explanations, not causal findings.'],
        historical_cause_established=False)


def save(value, kind):
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / f'{time.time_ns()}-{kind}.json'
    with path.open('x') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_suffix('.sha256').write_text(digest + '  ' + path.name + '\n')
    print(path)
    return path


def load(path):
    receipt = path.with_suffix('.sha256').read_text().split()[0]
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt:
        raise ValueError('Snapshot hash receipt mismatch: ' + str(path))
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    c = commands.add_parser('capture')
    c.add_argument('--label', required=True, choices=('pre-restart', 'post-restart'))
    c.add_argument('--compare-before', type=Path,
                   help='Verify the earlier snapshot and also save a comparison; post-restart only.')
    d = commands.add_parser('compare')
    d.add_argument('before', type=Path)
    d.add_argument('after', type=Path)
    args = parser.parse_args()
    if args.command == 'capture':
        if args.compare_before and args.label != 'post-restart':
            parser.error('--compare-before requires --label post-restart')
        before = load(args.compare_before) if args.compare_before else None
        value = capture(args.label)
        save(value, args.label)
        print('Unavailable commands:', ', '.join(k for k, v in value['commands'].items() if not v['ok']) or 'none')
        print('Settings changed during capture:', value['configuration'] != value['configuration_readback'])
        if before is not None:
            result = comparison(before, value)
            save(result, 'comparison')
            print('Recorded configuration differences:', len(result['recorded_configuration_changes']))
            print('Coverage gaps:', len(result['coverage_gaps']))
    else:
        result = comparison(load(args.before), load(args.after))
        save(result, 'comparison')
        print('Recorded configuration differences:', len(result['recorded_configuration_changes']))
        print('Coverage gaps:', len(result['coverage_gaps']))


if __name__ == '__main__':
    main()
