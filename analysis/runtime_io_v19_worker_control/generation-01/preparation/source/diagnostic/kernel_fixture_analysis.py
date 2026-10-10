"""Fail-closed checks for known workloads, not a service-causality analysis."""
import json
import re


def records(text, stderr):
    if re.search(r'lost|dropped|error|warning|failed', stderr, re.I):
        raise ValueError('observer diagnostics require review: ' + stderr[:1000])
    rows=[];begin=[];end=[]
    sizes={'S':8, 'W':5, 'F':5, 'X':4, 'T':8, 'U':8}
    for line in text.splitlines():
        if not line.strip():continue
        parts=line.split();kind=parts[0]
        if kind in ('BEGIN','END'):
            if len(parts)!=3:raise ValueError('bad lifecycle record')
            (begin if kind=='BEGIN' else end).append([int(x) for x in parts[1:]])
        elif kind in sizes:
            if len(parts)!=sizes[kind]:raise ValueError('bad '+kind+' record')
            rows.append([kind,*[int(x) for x in parts[1:]]])
        else:raise ValueError('unexpected output: '+line[:200])
    if len(begin)!=1 or len(end)!=1 or end[0][1]!=len(rows):
        raise ValueError('missing lifecycle or emitted/received count mismatch')
    for row in rows:
        ts=row[2] if row[0] in ('T','U') else row[1]
        if not begin[0][0]<=ts<=end[0][0]:raise ValueError('event outside lifecycle')
    return rows,begin[0][0],end[0][0]


def quota_intervals(rows, cgid):
    active={};intervals=[];attempts=0
    for r in sorted((r for r in rows if r[0] in ('T','U')),key=lambda r:r[2]):
        kind,start,end,cpu,cgroup,ptr,a,b=r
        if cgroup!=cgid or start<=0 or start>end:raise ValueError('bad quota identity/clock bracket')
        key=(cpu,ptr)
        if kind=='T':
            attempts+=1
            if a==0 and b==0:continue
            if a!=1 or b!=1 or key in active:raise ValueError('unexpected/duplicate throttle transition')
            active[key]=(start,end)
        elif a==1 and b==0:
            if key not in active:raise ValueError('unthrottle without known onset')
            onset=active.pop(key)
            if start<onset[1]:raise ValueError('overlapping transition brackets')
            intervals.append(dict(cpu=cpu,rq_identity=ptr,start_lower_ns=onset[0],start_upper_ns=onset[1],
                end_lower_ns=start,end_upper_ns=end,duration_lower_ns=start-onset[1],duration_upper_ns=end-onset[0]))
        elif (a,b) not in ((0,0),(1,1)):
            raise ValueError('unexpected unthrottle state')
    if active:raise ValueError('open quota interval at capture end')
    return intervals,attempts


def validate(raw, worker_text, stderr, metadata):
    rows,start,end=records(raw,stderr)
    worker=[json.loads(line) for line in worker_text.splitlines() if line.strip()]
    def one(event):
        found=[v for v in worker if v['event']==event]
        if len(found)!=1:raise ValueError('missing/duplicate worker '+event)
        return found[0]
    ready=one('ready');ws=one('start');we=one('end');phase_start=one('phase_start');phase_end=one('phase_end')
    if ready['pid']!=metadata['pid'] or ready['affinity']!=[metadata['cpu']]:raise ValueError('wrong worker identity/affinity')
    if not start<ws['monotonic_ns']<phase_start['monotonic_ns']<phase_end['monotonic_ns']<we['monotonic_ns']<end:
        raise ValueError('workload clock/lifecycle ordering failed')
    tids={ready['pid'],one('thread_start')['tid']}
    if {r[4] for r in rows if r[0]=='F'} != tids-{ready['pid']}:
        raise ValueError('new thread accounting failed')
    if {r[3] for r in rows if r[0]=='X'} != tids:raise ValueError('exit accounting failed')
    scheduled={};residency=0
    for r in sorted((r for r in rows if r[0]=='S'),key=lambda r:r[1]):
        _,ts,cpu,prev,nxt,state,prev_target,next_target=r
        if cpu!=metadata['cpu']:raise ValueError('worker ran outside declared CPU')
        if prev_target:
            if cpu not in scheduled or scheduled[cpu][0]!=prev:raise ValueError('unmatched switch out')
            residency+=ts-scheduled.pop(cpu)[1]
        if next_target:
            if cpu in scheduled:raise ValueError('unmatched switch in')
            scheduled[cpu]=(nxt,ts)
    if scheduled:raise ValueError('open scheduled residency')
    intervals,attempts=quota_intervals(rows,metadata['cgroup_id'])
    cpu_ns=we['cpu_ns']-ws['cpu_ns'];wall_ns=we['monotonic_ns']-ws['monotonic_ns']
    # Scheduled residency includes kernel/interrupt time and the process exit tail;
    # it is not an exact instruction-execution or process CPU counter.
    if cpu_ns<0 or residency<=0 or cpu_ns>residency+20_000_000:raise ValueError('CPU/residency conservation failed')
    nr=metadata['cpu_stat_delta'].get('nr_throttled',0)
    if metadata['mode']=='quota':
        if len(intervals)<3 or nr<3 or cpu_ns<300_000_000:raise ValueError('quota positive control failed')
    else:
        if intervals or nr:raise ValueError('uncapped negative control produced quota pauses')
        if metadata['mode']=='sleep' and cpu_ns>100_000_000:raise ValueError('sleep fixture used excessive CPU')
        if metadata['mode']=='cpu' and cpu_ns<100_000_000:raise ValueError('CPU fixture did not run enough work')
    return dict(passed=True,mode=metadata['mode'],received_events=len(rows),thread_ids=sorted(tids),
        throttle_attempts=attempts,successful_throttle_intervals=len(intervals),quota_intervals=intervals,
        cpu_stat_nr_throttled=nr,process_cpu_ms=cpu_ns/1e6,work_wall_ms=wall_ns/1e6,
        scheduled_residency_ms=residency/1e6,clock='CLOCK_MONOTONIC',
        loss_check='kernel emitted count equals received records; no diagnostics',
        observer_cost_qualified=False,service_request_attribution=False)
