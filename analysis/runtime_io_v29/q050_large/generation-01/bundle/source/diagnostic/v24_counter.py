#!/usr/bin/env python3
"""Bounded normal-user cpu.stat sampler; no tracing or target HTTP requests."""
import argparse
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


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--path',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--interval',type=float,default=.02);p.add_argument('--duration',type=float,default=110)
    args=p.parse_args()
    if args.interval!=.02 or args.duration!=110:raise ValueError('fixed 20 ms / 110 s sampler contract')
    if args.output.exists():raise ValueError('refuse overwrite')
    running=True
    def stop(signum,frame):
        nonlocal running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    samples=[];begin=time.monotonic_ns();cpu_begin=time.process_time_ns();failure=None
    try:
        while running and time.monotonic_ns()-begin<110_000_000_000:
            samples.append(read_counter(args.path))
            if len(samples)==1:
                args.output.with_suffix(".ready.json").write_text(json.dumps(samples[0])+"\n")
            time.sleep(args.interval)
    except BaseException as exc:
        failure=str(exc);raise
    finally:
        value=dict(schema=1,path=str(args.path),interval_sec=args.interval,duration_bound_sec=args.duration,
            started_ns=begin,finished_ns=time.monotonic_ns(),own_cpu_ns=time.process_time_ns()-cpu_begin,
            affinity=sorted(os.sched_getaffinity(0)),failure=failure,samples=samples)
        args.output.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
