#!/usr/bin/env python3
"""Root helper restricted to the sealed closing-test sequence and owned cgroups."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import minimal_counter_closing as screen
import period_cost_perf as hw

c, bridge = screen.c, screen.base.bridge


def helper(session):
    if os.geteuid()!=0 or not os.environ.get('SUDO_UID'):
        raise ValueError('launch helper only through normal-user external sudo')
    manifest=screen.verify(session)
    owner=c.read(session/'owner.json')
    uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
    if owner['uid']!=uid or not c.same_process(owner): raise ValueError('owner identity mismatch')
    os.sched_setaffinity(0,{0,1})
    active=None; index=0; fixtures_done=False; started=time.monotonic()

    def reply(value): print(json.dumps(value,allow_nan=False),flush=True)

    def give(directory):
        for p in directory.rglob('*'):
            if not p.is_symlink() and p.stat().st_uid==0: os.chown(p,uid,gid)
        if directory.stat().st_uid==0: os.chown(directory,uid,gid)

    reply(dict(ready=True))
    try:
        while True:
            remaining=screen.LIMITS['wall_ceiling_sec']+60-(time.monotonic()-started)
            if remaining<=0: raise TimeoutError('closing helper lifetime exceeded')
            request=json.loads(hw.line(sys.stdin.buffer,min(300,remaining) if active else remaining))
            if not c.same_process(owner) or set(request)!={'op'}:
                raise ValueError('owner died or IPC arguments rejected')
            screen.verify(session)
            op=request['op']
            if op=='fixtures' and not fixtures_done and index==0 and active is None:
                out=session/'counter_fixtures'; out.mkdir()
                try:
                    for name,mode in [('compute_1','compute'),('compute_2','compute'),
                                      ('compute_3','compute'),('compute_sleep','sleep')]:
                        hw.fixture(out/name,mode,session/'preparation/fixture')
                    result=screen.pc.validate_fixtures(out)
                    c.save(out/'result.json',result); c.seal(out)
                finally: give(out)
                fixtures_done=True; reply(result)
            elif op=='attach' and fixtures_done and active is None and index<8:
                spec=screen.matrix()[index]; d=session/'trials'/spec['trial']
                if c.read(d/'closing_config.json')!=spec: raise ValueError('trial differs from fixed sequence')
                initial=c.read(d/'initial.json'); process=initial['process_identity']
                group=Path(initial['cgroup']); container=c.read(d/'container.json')['inspect']
                expected=Path('/sys/fs/cgroup/system.slice/docker-'+container['Id']+'.scope')
                if group!=expected or not c.same_process(process) or bridge.cgroup(process['pid'])!=group:
                    raise ValueError('live owned cgroup/process mismatch')
                c.validate_resources(initial['initial_limits'],container['HostConfig'],
                    manifest['resource_baseline'],screen.config_for(spec))
                if (container['Image']!=manifest['minimal_image'] or
                        initial['container_server_sha256']!=manifest['minimal_server_sha256']):
                    raise ValueError('wrong computation executable')
                active=hw.Counter(d,group,spec['counters']); reply(dict(attached=True,trial=spec['trial']))
            elif op in ('enable','disable') and active:
                reply(active.control(op))
            elif op=='detach' and active and active.state=='disabled':
                active.close(); give(active.directory); active=None; index+=1; reply(dict(detached=True))
            elif op=='finish' and active is None and index==8:
                reply(dict(finished=True,detached_trials=index)); return
            else: raise ValueError('unknown/out-of-order operation')
    finally:
        if active:
            try: active.close()
            finally: give(active.directory)
        out=session/'counter_fixtures'
        if out.exists():
            if not (out/'seal.json').exists(): c.seal(out)
            give(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--directory',required=True)
    a=p.parse_args()
    try: helper(screen.owned(a.directory))
    except BaseException as e:
        print(str(e),file=sys.stderr); raise SystemExit(1)
