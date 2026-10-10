"""Ideal work-conserving periodic-budget FIFO; not a Linux service guarantee."""
from bisect import bisect_right
from collections import deque
import math


def replay(offsets_ns,capacity_rps,quota_sec,period_sec,phase_sec=0.,initial_fraction=1.):
    if not (math.isfinite(capacity_rps) and capacity_rps>0 and 0<quota_sec<=period_sec
            and 0<=phase_sec<period_sec and 0<=initial_fraction<=1):
        raise ValueError('invalid periodic-server parameters')
    if not offsets_ns or any(a>b for a,b in zip(offsets_ns,offsets_ns[1:])):
        raise ValueError('nonempty ordered offer vector required')
    demand=(quota_sec/period_sec)/capacity_rps
    reset=phase_sec if phase_sec>0 else period_sec
    credit=initial_fraction*quota_sec
    end=0.;pending=deque();latencies=[];eps=1e-12
    for stamp in offsets_ns:
        arrival=stamp/1e9
        while pending and pending[0]<=arrival:pending.popleft()
        if len(pending)>=129:
            latencies.append(None);continue
        t=max(arrival,end)
        left=demand
        while left>eps:
            if t>=reset-eps:
                cycles=max(1,math.floor((t-reset+eps)/period_sec)+1)
                reset+=cycles*period_sec;credit=quota_sec
            if credit<=eps:
                t=reset;continue
            take=min(left,credit,reset-t)
            if take<=0:raise ArithmeticError('periodic replay failed to advance')
            t+=take;left-=take;credit-=take
        end=t;pending.append(end);latencies.append(end-arrival)
    return latencies


def misses(latencies,deadlines_ms):
    good=sorted(x for x in latencies if x is not None)
    return {str(ms):100*(len(latencies)-bisect_right(good,ms/1000))/len(latencies)
            for ms in deadlines_ms}


def delayed_misses(latencies,delays_sec,deadlines_ms):
    if not delays_sec or any(x<0 for x in delays_sec):
        raise ValueError('nonnegative calibration delays required')
    delays=sorted(delays_sec);n=len(delays)
    return {str(ms):100*sum(1 if x is None else
                1-bisect_right(delays,ms/1000-x)/n for x in latencies)/len(latencies)
            for ms in deadlines_ms}
