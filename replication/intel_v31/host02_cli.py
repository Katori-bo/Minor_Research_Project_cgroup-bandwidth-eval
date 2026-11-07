#!/usr/bin/env python3
"""Inspect the declared host, import the pinned image, and prepare offline assets."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'diagnostic'), str(ROOT / 'scripts'), str(ROOT / 'analysis')]
import v31_common as c
import host02_platform as hardware
from environment_controls import power_settings


def command(argv):
    p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise ValueError('Command failed: ' + ' '.join(argv) + '\n' + p.stderr.strip())
    return p.stdout.strip()


def check(require_image=True):
    if os.geteuid() == 0:
        raise ValueError('Use the normal user; do not sudo the whole campaign')
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise ValueError('This package is for the supplied native x86-64 Linux host')
    c.verify_package()
    c.design()
    cpu = Path('/proc/cpuinfo').read_text()
    if 'Intel(R) Core(TM) i5-10300H' not in cpu:
        raise ValueError('CPU differs from the supplied i5-10300H inventory')
    topology = hardware.check_topology()
    sensors = hardware.temperatures()
    if not {0, 1, 2, 3} <= os.sched_getaffinity(0):
        raise ValueError('Required server/control CPUs are unavailable to this user session')
    for tool in ('docker', 'systemd-inhibit', 'taskset', 'sudo', 'pgrep', 'bpftool'):
        if not shutil.which(tool):
            raise ValueError(f'Missing prerequisite: {tool}. Install/qualify it before collection; no workload started.')
    # Ubuntu may ship a bpftool wrapper without its matching tools binary.
    bpf_version = command(['bpftool', 'version'])
    detected = subprocess.run(['systemd-detect-virt'], capture_output=True, text=True, timeout=10)
    if detected.stdout.strip() != 'none':
        raise ValueError('Native-host requirement not established by systemd-detect-virt')
    info = json.loads(command(['docker', 'info', '--format', '{{json .}}']))
    if (str(info.get('CgroupVersion')) != '2' or info.get('CgroupDriver') != 'systemd'
            or any('rootless' in s for s in info.get('SecurityOptions', []))):
        raise ValueError('Rootful local Docker with cgroup v2/systemd is required')
    context = json.loads(command(['docker', 'context', 'inspect']))[0]
    endpoint = os.environ.get('DOCKER_HOST') or context['Endpoints']['docker']['Host']
    if not endpoint.startswith('unix://'):
        raise ValueError('Docker must use a local Unix socket, not a remote daemon')
    if not {'cpu', 'cpuset'} <= set(Path('/sys/fs/cgroup/cgroup.controllers').read_text().split()):
        raise ValueError('Required cgroup v2 controllers missing')
    # Default Ubuntu permissions may hide tracefs contents from normal users.
    # Actual completeness/readability is checked by the retained sudo inventory.
    if not Path('/sys/kernel/tracing').is_dir():
        raise ValueError('tracefs mount directory unavailable; return this error for apparatus review')
    c.capacity(ROOT)
    settings = power_settings(include_profile=True)
    if not settings['external_power'] or not any(v == '1' for v in settings['external_power'].values()):
        raise ValueError('Connect AC power; external power must be readable')
    if settings.get('desktop_profile') not in (None, 'balanced'):
        raise ValueError('Select the balanced desktop power profile before qualification')
    identity = c.read(ROOT / 'assets/retained_identity.json')
    if require_image:
        image = json.loads(command(['docker', 'image', 'inspect', identity['image']]))[0]
        if image['Id'] != identity['image'] or image['Architecture'] != 'amd64' or image['Os'] != 'linux':
            raise ValueError('Retained service image identity/platform differs')
    report = dict(host='host02', cpu='i5-10300H', kernel=platform.release(),
        python=platform.python_version(), docker=info['ServerVersion'], topology=topology,
        temperatures_c=sensors, power=settings, bpftool=bpf_version,
        os_release=Path('/etc/os-release').read_text(),
        virtualization=detected.stdout.strip(), cgroup_version=info['CgroupVersion'],
        cgroup_driver=info['CgroupDriver'], docker_local_context=endpoint,
        disk_free_gib=round(shutil.disk_usage(ROOT).free / 1024**3, 2),
        service_image_checked=require_image, collection_started=False,
        runtime_qualified=False)
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('verify-package', 'check', 'setup'))
    args = parser.parse_args()
    if args.command == 'verify-package':
        c.verify_package()
        c.design()
        print('Host02 package identities and unchanged primary scientific contract verified.')
    elif args.command == 'check':
        check()
    else:
        check(require_image=False)
        session = c.PARENT / 'generation-01'
        if session.exists():
            raise ValueError('Existing setup/attempt preserved; do not rerun setup or overwrite it')
        # Normal-user Docker import of an already sealed archive; no container starts.
        subprocess.run(['docker', 'image', 'load', '--input', str(ROOT / 'assets/service-image.tar')],
                       check=True, timeout=180)
        report = check()
        c.save(ROOT / 'runs/host02/setup_host.json', report)
        subprocess.run([sys.executable, '-B', str(ROOT / 'diagnostic/v31_study.py'),
                        'prepare-offline', '--directory', str(session)], check=True, timeout=240)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('STOP: ' + str(exc), file=sys.stderr)
        sys.exit(1)
