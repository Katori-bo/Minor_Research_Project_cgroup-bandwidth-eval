#!/usr/bin/env python3
import sys
import os
import time
import json
import argparse
import glob
import signal
import subprocess
from environment_controls import power_settings

running = True

def handle_stop(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, handle_stop)
signal.signal(signal.SIGINT, handle_stop)

def get_cpu_times():
    """Reads /proc/stat and returns {cpu_id: (user, nice, system, idle, iowait, irq, softirq, steal)}"""
    cpu_times = {}
    with open('/proc/stat', 'r') as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            if name.startswith('cpu'):
                vals = [int(x) for x in parts[1:9]]
                cpu_times[name] = vals
    return cpu_times

def get_temperatures():
    """Reads /sys/class/thermal/thermal_zone*/temp"""
    temps = {}
    for hw in glob.glob('/sys/class/hwmon/hwmon*'):
        try:
            with open(os.path.join(hw, 'name')) as f:
                name = f.read().strip()
            if name == 'k10temp':
                for sensor in glob.glob(os.path.join(hw, 'temp*_input')):
                    with open(sensor) as f:
                        temps[name + ':' + os.path.basename(sensor)] = int(f.read()) / 1000.0
        except OSError:
            pass
    for zone in glob.glob('/sys/class/thermal/thermal_zone*'):
        z_name = os.path.basename(zone)
        try:
            with open(os.path.join(zone, 'temp'), 'r') as f:
                t = int(f.read().strip()) / 1000.0
                temps[z_name] = t
        except Exception:
            pass
    return temps

def get_frequencies():
    """Reads scaling_cur_freq for all CPUs"""
    freqs = {}
    for path in glob.glob('/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq'):
        parts = path.split('/')
        cpu_name = parts[5]
        try:
            with open(path, 'r') as f:
                khz = int(f.read().strip())
                freqs[cpu_name] = khz / 1000.0  # in MHz
        except Exception:
            pass
    return freqs

def read_cgroup_cpu_stat(cgroup_rel_path):
    """Reads /sys/fs/cgroup/<path>/cpu.stat"""
    full_path = os.path.join('/sys/fs/cgroup', cgroup_rel_path.lstrip('/'), 'cpu.stat')
    stats = {}
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2:
                    stats[parts[0]] = int(parts[1])
    return stats


def process_snapshot(proc_root='/proc'):
    """Process CPU ticks, keyed by PID + start time to avoid PID reuse errors.

    Short-lived/exited processes can be missed. Last CPU is a location sample,
    not attribution of the entire interval's CPU time to that core.
    """
    result = {}
    for path in glob.glob(os.path.join(proc_root, '[0-9]*', 'stat')):
        try:
            with open(path) as stream:
                line = stream.read()
            left, right = line.index('('), line.rindex(')')
            pid, comm = int(line[:left].strip()), line[left+1:right]
            fields = line[right+2:].split()  # begins at /proc stat field 3
            start = int(fields[19])
            result[(pid, start)] = dict(pid=pid, start_ticks=start, comm=comm,
                cpu_ticks=int(fields[11])+int(fields[12]), last_cpu=int(fields[36]))
        except (OSError, ValueError, IndexError):
            continue  # Process exited or is not readable; never invent a delta.
    return result


def process_deltas(previous, current, elapsed, ticks_per_second):
    rows = []
    for key, record in current.items():
        if key not in previous: continue
        ticks = record['cpu_ticks'] - previous[key]['cpu_ticks']
        if ticks < 0: continue
        seconds = ticks / ticks_per_second
        rows.append(dict(record, cpu_delta_ticks=ticks, cpu_delta_sec=seconds,
                         cpu_pct_one_core=100*seconds/elapsed))
    return sorted(rows, key=lambda r: (-r['cpu_delta_ticks'], r['pid']))

def main():
    global running
    parser = argparse.ArgumentParser(description="Host and Cgroup Resource Sampler")
    parser.add_argument("--cgroup-path", default="", help="Relative cgroup path from /proc/<pid>/cgroup")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    parser.add_argument("--output", required=True, help="Output JSON log file")
    args = parser.parse_args()

    records = []
    prev_cpu_times = get_cpu_times()
    prev_processes = process_snapshot()
    prev_time = time.monotonic()
    ticks_per_second = os.sysconf('SC_CLK_TCK')

    try:
        while running:
            time.sleep(args.interval)
            if not running:
                break
            now = time.time()
            cur_cpu_times = get_cpu_times()
            cur_processes = process_snapshot()
            sample_time = time.monotonic()
            process_interval = sample_time - prev_time

            util = {}
            for cpu_name, cur_vals in cur_cpu_times.items():
                if cpu_name in prev_cpu_times:
                    prev_vals = prev_cpu_times[cpu_name]
                    deltas = [c - p for c, p in zip(cur_vals, prev_vals)]
                    total = sum(deltas)
                    idle = deltas[3] + deltas[4]
                    active = total - idle
                    pct = (float(active) / total * 100.0) if total > 0 else 0.0
                    util[cpu_name] = round(pct, 2)

            entry = {
                "timestamp": round(now, 3),
                "process_interval_sec": process_interval,
                "process_cpu_deltas": process_deltas(prev_processes, cur_processes, process_interval, ticks_per_second),
                "chatgpt_present": any(r["comm"] == "ChatGPT" for r in cur_processes.values()),
                "process_snapshot_count": len(cur_processes),
                "cpu_util_pct": util,
                "temps_c": get_temperatures(),
                "freqs_mhz": get_frequencies(),
                "power_settings": power_settings(),
                "processes": subprocess.run(
                    ['ps', '-eo', 'pid,comm,pcpu,psr', '--sort=-pcpu'],
                    capture_output=True, text=True, check=True
                ).stdout.splitlines()[:31]
            }

            if args.cgroup_path:
                entry["cgroup_cpu_stat"] = read_cgroup_cpu_stat(args.cgroup_path)

            records.append(entry)
            prev_cpu_times = cur_cpu_times
            prev_time = sample_time
            prev_processes = cur_processes
    except Exception as exc:
        print(f'Monitor failed: {exc}', file=sys.stderr)
        raise
    finally:
        with open(args.output, 'w') as f:
            json.dump(records, f, indent=2)

if __name__ == "__main__":
    main()
