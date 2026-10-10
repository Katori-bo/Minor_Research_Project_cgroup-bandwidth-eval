#!/usr/bin/env python3
"""Small known workload, held on stdin until the observer is ready."""
import json
import os
import sys
import threading
import time


def emit(event, **fields):
    print(json.dumps(dict(event=event, monotonic_ns=time.monotonic_ns(),
                          tid=threading.get_native_id(), **fields)), flush=True)


def main():
    mode = sys.argv[1]
    if mode not in ('sleep', 'cpu', 'quota'): raise ValueError('unknown fixture')
    emit('ready', pid=os.getpid(), affinity=sorted(os.sched_getaffinity(0)))
    if sys.stdin.readline().strip() != 'GO': raise ValueError('missing start barrier')
    emit('start', cpu_ns=time.process_time_ns())
    def companion():
        emit('thread_start')
        time.sleep(.2)
        emit('thread_end')
    thread=threading.Thread(target=companion)
    thread.start()
    emit('phase_start', mode=mode)
    if mode == 'sleep': time.sleep(.6)
    else:
        end=time.monotonic() + (1.8 if mode == 'quota' else .6)
        value=0
        while time.monotonic() < end:
            for _ in range(1024): value=(value*1664525+1013904223)&0xffffffff
    emit('phase_end', mode=mode)
    thread.join()
    # Allow the last quota transition to close before observer shutdown.
    time.sleep(.15)
    emit('end', cpu_ns=time.process_time_ns())


if __name__ == '__main__': main()
