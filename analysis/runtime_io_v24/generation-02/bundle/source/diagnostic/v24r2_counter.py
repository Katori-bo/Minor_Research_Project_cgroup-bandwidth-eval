#!/usr/bin/env python3
"""Bounded normal-user cpu.stat sampler; no tracing or target HTTP requests."""
import argparse
from contextlib import contextmanager
import gc
import json
import os
from pathlib import Path
import signal
import time


def read_counter(path):
    before=time.monotonic_ns()
    values={}
    for line in Path(path).read_text().splitlines():
        key,value=line.split();values[key]=int(value)
    after=time.monotonic_ns()
    if any(value<0 for value in values.values()) or 'usage_usec' not in values:
        raise ValueError('invalid cpu.stat')
    return dict(before_ns=before,after_ns=after,cpu_stat=values)


@contextmanager
def suspend_cyclic_gc():
    """Avoid periodic scans of retained, acyclic records in this bounded process."""
    enabled = gc.isenabled()
    gc.disable()
    try:
        yield enabled
    finally:
        if enabled:
            gc.enable()
        else:
            gc.disable()


def capture(path, output, keep_running):
    if output.exists():
        raise ValueError('refuse overwrite')
    samples = []
    value = None
    failure = None
    try:
        with suspend_cyclic_gc() as enabled_before:
            collections_before = [row['collections'] for row in gc.get_stats()]
            begin = time.monotonic_ns()
            cpu_begin = time.process_time_ns()
            try:
                while keep_running() and time.monotonic_ns()-begin < 110_000_000_000:
                    samples.append(read_counter(path))
                    if len(samples) == 1:
                        output.with_suffix('.ready.json').write_text(json.dumps(samples[0])+'\n')
                    time.sleep(.02)
            except BaseException as exc:
                failure = str(exc)
                raise
            finally:
                # Close the timed lifetime before restoring GC or serializing records.
                finished = time.monotonic_ns()
                cpu_finished = time.process_time_ns()
                value = dict(schema=2, sampler_revision='v24r2-gc-suspended',
                    path=str(path), interval_sec=.02, duration_bound_sec=110,
                    started_ns=begin, finished_ns=finished,
                    own_cpu_ns=cpu_finished-cpu_begin,
                    affinity=sorted(os.sched_getaffinity(0)), failure=failure, samples=samples,
                    gc_policy='suspended_during_bounded_capture',
                    gc_was_enabled=enabled_before,
                    gc_enabled_during_capture=gc.isenabled(),
                    gc_collections_before=collections_before,
                    gc_collections_after=[row['collections'] for row in gc.get_stats()])
    finally:
        if value is not None:
            value['gc_enabled_after_capture'] = gc.isenabled()
            output.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--path',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--interval',type=float,default=.02);p.add_argument('--duration',type=float,default=110)
    args=p.parse_args()
    if args.interval!=.02 or args.duration!=110:raise ValueError('fixed 20 ms / 110 s sampler contract')
    running=True
    def stop(signum,frame):
        nonlocal running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    capture(args.path, args.output, lambda: running)


if __name__=='__main__':main()
