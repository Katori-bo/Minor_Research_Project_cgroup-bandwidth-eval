#!/usr/bin/env python3
"""Fixed four-cell counter helper; CPU policies are read-only in this continuation."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import sys
import time

import execution_state_continuation as screen

c=screen.c;hw=screen.pilot.hw;bridge=screen.pilot.base.bridge;controls=screen.pilot.controls


def helper(session):
    if os.geteuid()!=0 or not os.environ.get('SUDO_UID'):raise ValueError('use external normal-user sudo')
    m=screen.verify(session);owner=c.read(session/'owner.json')
    uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
    if owner['uid']!=uid or not c.same_process(owner):raise ValueError('owner mismatch')
    before=m['controls_before']
    if controls.snapshot()!=before:raise ValueError('automatic CPU settings changed')
    os.sched_setaffinity(0,{0,1})
    active=None;index=0;fixtures_done=False;condition_ready=False;started=time.monotonic()
    out=session/'speed_control';out.mkdir();c.save(out/'original.json',before)
    def reply(value):print(json.dumps(value,allow_nan=False),flush=True)
    def give(directory):
        for p in [directory,*directory.rglob('*')]:
            if not p.is_symlink() and p.stat().st_uid==0:os.chown(p,uid,gid)
    def terminate(_s,_f):raise KeyboardInterrupt('continuation helper interrupted; detach owned counters')
    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):signal.signal(sig,terminate)
    try:
        reply(dict(ready=True))
        while True:
            remaining=screen.LIMITS['wall_ceiling_sec']+60-(time.monotonic()-started)
            if remaining<=0:raise TimeoutError('continuation helper lifetime exceeded')
            if not c.same_process(owner):raise ValueError('owner died')
            if controls.snapshot()!=before:raise ValueError('automatic CPU bounds/policy changed')
            ready,_,_=select.select([sys.stdin.buffer],[],[],min(1,remaining))
            if not ready:continue
            request=json.loads(hw.line(sys.stdin.buffer,5))
            if set(request)!={'op'} or not c.same_process(owner):raise ValueError('IPC or owner mismatch')
            screen.verify(session);op=request['op']
            if op=='fixtures' and not fixtures_done and index==0 and active is None:
                fixtures=session/'counter_fixtures';fixtures.mkdir()
                try:
                    for name,mode in [('compute_1','compute'),('compute_2','compute'),('compute_3','compute'),('compute_sleep','sleep')]:
                        hw.fixture(fixtures/name,mode,session/'preparation/fixture')
                    result=screen.pilot.pc.validate_fixtures(fixtures);c.save(fixtures/'result.json',result);c.seal(fixtures)
                finally:give(fixtures)
                fixtures_done=True;reply(result)
            elif op=='condition' and fixtures_done and active is None and not condition_ready and index<4:
                spec=screen.matrix()[index]
                if spec['condition']!='automatic':raise ValueError('continuation condition must be automatic')
                actual=controls.snapshot()
                if actual!=before:raise ValueError('automatic settings differ')
                c.save(out/f'condition_{index}.json',dict(trial=spec['trial'],observed=actual,monotonic_ns=time.monotonic_ns()))
                condition_ready=True;reply(dict(condition='automatic',verified=True))
            elif op=='attach' and fixtures_done and condition_ready and active is None and index<4:
                spec=screen.matrix()[index];d=session/'trials'/spec['trial']
                if c.read(d/'pilot_config.json')!=spec:raise ValueError('trial differs from fixed continuation sequence')
                initial=c.read(d/'initial.json');process=initial['process_identity'];group=Path(initial['cgroup'])
                container=c.read(d/'container.json')['inspect']
                expected=Path('/sys/fs/cgroup/system.slice/docker-'+container['Id']+'.scope')
                if group!=expected or not c.same_process(process) or bridge.cgroup(process['pid'])!=group:raise ValueError('live owned cgroup mismatch')
                c.validate_resources(initial['initial_limits'],container['HostConfig'],m['resource_baseline'],screen.pilot.config_for(spec))
                if container['Image']!=m['minimal_image'] or initial['container_server_sha256']!=m['minimal_server_sha256']:raise ValueError('computation executable changed')
                active=hw.Counter(d,group,spec['counters']);reply(dict(attached=True,trial=spec['trial']))
            elif op in ('enable','disable') and active:reply(active.control(op))
            elif op=='detach' and active and active.state=='disabled':
                active.close();give(active.directory);active=None;index+=1;condition_ready=False;reply(dict(detached=True))
            elif op=='finish' and active is None and index==4:
                if controls.snapshot()!=before:raise ValueError('automatic controls differ at finish')
                reply(dict(finished=True,detached_trials=index,settings_unchanged=True));return
            else:raise ValueError('unknown/out-of-order continuation operation')
    finally:
        try:
            if active:
                try:active.close()
                finally:give(active.directory)
        finally:
            actual=controls.snapshot()
            c.save(out/'restoration.json',dict(restored=actual==before,observed=actual,changes_applied=[],
                note='Read-only CPU-policy helper; checks unchanged settings, performs no bound writes.'))
            c.seal(out);give(out)
            fixtures=session/'counter_fixtures'
            if fixtures.exists():
                if not (fixtures/'seal.json').exists():c.seal(fixtures)
                give(fixtures)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True);a=p.parse_args()
    try:helper(screen.owned(a.directory))
    except BaseException as e:print(str(e),file=sys.stderr);raise SystemExit(1)
