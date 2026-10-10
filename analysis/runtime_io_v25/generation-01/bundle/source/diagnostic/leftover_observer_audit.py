#!/usr/bin/env python3
"""Read-only host observer inventory. Never attach, detach or change a setting."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {'perf', 'bpftrace', 'trace-cmd', 'bpftool', 'bpf', 'trace-cmd-record'}


def read(path):
    try:
        return {'ok': True, 'text': Path(path).read_text().strip()}
    except (OSError, UnicodeError) as e:
        return {'ok': False, 'error': str(e)}


def command(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=10,
                           env=dict(os.environ, LC_ALL='C'))
        return dict(argv=argv, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except (OSError, subprocess.TimeoutExpired) as e:
        return dict(argv=argv, returncode=None, stdout='', stderr=str(e))


def trace_state(path):
    fields = ('current_tracer', 'tracing_on', 'events/enable', 'kprobe_events',
              'uprobe_events', 'dynamic_events', 'set_ftrace_filter', 'set_ftrace_pid')
    state = {n: read(path/n) for n in fields}
    enabled = []
    errors = []
    # Read individual event enable flags. Do not read trace_pipe or trace buffers.
    for p in sorted((path/'events').glob('*/*/enable')):
        value = read(p)
        if not value['ok']: errors.append(str(p))
        elif value['text'] == '1': enabled.append(str(p.parent.relative_to(path/'events')))
    return dict(path=str(path), controls=state, enabled_events=enabled,
                event_read_errors=errors)


def processes():
    rows, owners, denied = [], [], []
    started = time.monotonic()
    complete = True
    for p in sorted(Path('/proc').iterdir()):
        if not p.name.isdigit(): continue
        if time.monotonic()-started > 25:
            complete = False; break
        try:
            comm = (p/'comm').read_text().strip()
            fields = (p/'stat').read_text().split(') ', 1)[1].split()
            # Keep only script basenames, never general command arguments or env.
            args = (p/'cmdline').read_bytes().split(b'\0')
            scripts = [Path(a.decode(errors='replace')).name for a in args if a.endswith(b'.py')]
            row = dict(pid=int(p.name), comm=comm, ppid=int(fields[1]),
                       start_ticks=int(fields[19]), uid=p.stat().st_uid, scripts=scripts)
            rows.append(row)
            try:
                fds = list((p/'fd').iterdir())
                for fd in fds:
                    try: link = os.readlink(fd)
                    except FileNotFoundError: continue
                    if 'perf_event' in link:
                        owners.append(dict(**row, fd=int(fd.name), target=link,
                                           fdinfo=read(p/'fdinfo'/fd.name)))
            except FileNotFoundError:
                continue
            except PermissionError:
                denied.append(int(p.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            denied.append(int(p.name))
    suspicious = [r for r in rows if r['comm'] in TOOLS or
        any(s in ('period_cost_perf.py', 'kernel_fixtures.py', 'kernel_service_bridge.py')
            for s in r['scripts'])]
    return dict(rows=rows, observer_candidates=suspicious, perf_fd_owners=owners,
                permission_denied_pids=sorted(set(denied)), scan_complete=complete)


def assess(value):
    missing, findings = [], []
    proc = value['processes']
    if not proc['scan_complete'] or proc['permission_denied_pids']:
        missing.append('process/perf descriptor inventory incomplete')
    if proc['observer_candidates']: findings.append('observer process candidates present')
    if proc['perf_fd_owners']: findings.append('open perf-event descriptors present')
    trace = value['tracefs']
    if not trace['root_readable'] or trace['instance_error']:
        missing.append('tracefs root/instance inventory incomplete')
    for state in trace['states']:
        controls = state['controls']
        required = ('current_tracer', 'tracing_on', 'events/enable')
        if any(not controls[k]['ok'] for k in required) or state['event_read_errors']:
            missing.append('tracefs controls/events incomplete: '+state['path'])
        active = controls['tracing_on'].get('text') == '1'
        configured = (controls['current_tracer'].get('text') not in (None, 'nop') or
                      controls['events/enable'].get('text') not in (None, '0') or state['enabled_events'])
        if active and configured: findings.append('active tracing: '+state['path'])
        for key in ('kprobe_events','uprobe_events','dynamic_events'):
            if controls[key]['ok'] and controls[key]['text']:
                findings.append('defined probes need ownership review: '+state['path']+'/'+key)
    for kind, receipt in value['bpf'].items():
        if receipt.get('returncode') != 0:
            missing.append('BPF '+kind+' inventory unavailable')
        elif receipt.get('items'):
            findings.append('BPF '+kind+' objects need ownership review')
    return dict(status='review_active_or_configured_observers' if findings else
        'audit_incomplete' if missing else 'no_observer_evidence_in_complete_snapshot',
        findings=sorted(set(findings)), missing=sorted(set(missing)),
        clear_snapshot=not findings and not missing,
        historical_cause_established=False,
        limitation='An inventory is a snapshot, not proof of historical absence. '
                   'BPF objects can belong to ordinary system services; presence alone is not a leak.')


def inventory(allow_partial=False):
    if os.geteuid() != 0 and not allow_partial:
        raise ValueError('root read access is required for the complete descriptor/tracing audit')
    root = Path('/sys/kernel/tracing')
    state_before = {n:read(root/n) for n in ('current_tracer','tracing_on','events/enable')}
    states, error = [], None
    try:
        paths = [root] + sorted(p for p in (root/'instances').iterdir() if p.is_dir())
        states = [trace_state(p) for p in paths]
    except OSError as e: error = str(e)
    bpf = {}
    for kind in ('prog','link','map'):
        receipt = command(['bpftool','-j',kind,'show'])
        if receipt['returncode'] == 0:
            try: receipt['items'] = json.loads(receipt['stdout'])
            except ValueError: receipt['returncode'] = None
        bpf[kind] = receipt
    packages = read('/var/log/pacman.log')
    relevant = [s for s in packages.get('text','').splitlines() if s.startswith('[2026-10-') and
        re.search(r'\[ALPM\] (installed|upgraded|removed) ',s)]
    sys.path.insert(0,str(ROOT/'scripts'))
    from environment_controls import power_settings
    result = dict(schema=1, at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        kernel=platform.release(), boot_id=read('/proc/sys/kernel/random/boot_id'), uid=os.geteuid(),
        audit_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        processes=processes(), bpf=bpf,
        tracefs=dict(root_readable=all(v['ok'] for v in state_before.values()),
                     instance_error=error, states=states, root_controls_before=state_before,
                     root_controls_after={n:read(root/n) for n in state_before}),
        settings={p:read(p) for p in ('/proc/sys/kernel/perf_event_paranoid',
             '/proc/sys/kernel/unprivileged_bpf_disabled','/proc/sys/kernel/sched_cfs_bandwidth_slice_us')},
        power_settings=power_settings(include_profile=True), package_changes_october=relevant,
        running_services=command(['systemctl','list-units','--type=service','--state=running',
                                  '--no-pager','--plain']),
        observation_started=False, configuration_changed=False)
    result['assessment'] = assess(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-partial', action='store_true', help='Retain inaccessible sections explicitly; never treat them as clear.')
    a = p.parse_args()
    output = a.output.absolute()
    allowed = ROOT/'analysis/runtime_io_leftover_observer_audit'
    if output.parent != allowed or output.is_symlink() or output.exists():
        raise ValueError('use a new JSON file directly inside the dedicated audit directory')
    value = inventory(a.allow_partial)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x') as f: json.dump(value,f,indent=2); f.write('\n')
    if os.environ.get('SUDO_UID'):
        os.chown(output,int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID']))
    print(json.dumps(value['assessment'],indent=2))
    print('Audit: '+str(output))


if __name__ == '__main__':
    main()
