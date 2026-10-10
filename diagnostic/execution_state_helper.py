#!/usr/bin/env python3
"""Sealed, fixed-scope CPU-bound and cgroup-counter helper with restoration."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import sys
import time

import execution_state_pilot as screen
import execution_state_controls as controls
import period_cost_perf as hw

c, bridge = screen.c, screen.base.bridge


def helper(session):
    if os.geteuid()!=0 or not os.environ.get('SUDO_UID'):
        raise ValueError('launch helper only through normal-user external sudo')
    manifest=screen.verify(session)
    owner=c.read(session/'owner.json')
    uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
    if owner['uid']!=uid or not c.same_process(owner): raise ValueError('owner identity mismatch')
    if controls.snapshot()!=manifest['controls_before']: raise ValueError('original controls changed')
    os.sched_setaffinity(0,{0,1})
    active=None; index=0; fixtures_done=False; tested=False; started=time.monotonic()
    before=manifest['controls_before']; expected=before
    out=session/'speed_control'; out.mkdir(); c.save(out/'original.json',before)
    transition=0; condition_ready=False

    def reply(value): print(json.dumps(value,allow_nan=False),flush=True)

    def give(directory):
        for p in directory.rglob('*'):
            if not p.is_symlink() and p.stat().st_uid==0: os.chown(p,uid,gid)
        if directory.stat().st_uid==0: os.chown(directory,uid,gid)

    def terminate(_s,_f): raise KeyboardInterrupt('helper interrupted; restore original CPU bounds')

    for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,terminate)
    try:
        reply(dict(ready=True))
        while True:
            remaining=screen.LIMITS['wall_ceiling_sec']+60-(time.monotonic()-started)
            if remaining<=0: raise TimeoutError('execution helper lifetime exceeded')
            if not c.same_process(owner): raise ValueError('owner died; restore bounds')
            if controls.snapshot()!=expected: raise ValueError('CPU-bound intervention overwritten')
            # Poll ownership and settings even during long idle/settling waits.
            ready,_,_=select.select([sys.stdin.buffer],[],[],min(1,remaining))
            if not ready: continue
            request=json.loads(hw.line(sys.stdin.buffer,5))
            if not c.same_process(owner) or set(request)!={'op'}: raise ValueError('owner or IPC mismatch')
            screen.verify(session)
            op=request['op']
            if op=='selftest' and not tested and index==0 and active is None:
                controls.set_bounds(manifest['control_plan']['constrained'])
                actual=controls.snapshot()
                if actual!=manifest['control_plan']['constrained']: raise ValueError('constrained control readback failed')
                restored=controls.restore(before)
                c.save(out/'selftest.json',dict(constrained_readback=actual,restoration=restored))
                if not restored['restored']: raise ValueError('control selftest restoration failed')
                tested=True; expected=before; reply(dict(control_selftest=True,restored=True))
            elif op=='fixtures' and tested and not fixtures_done and index==0 and active is None:
                fixtures=session/'counter_fixtures'; fixtures.mkdir()
                try:
                    for name,mode in [('compute_1','compute'),('compute_2','compute'),
                                      ('compute_3','compute'),('compute_sleep','sleep')]:
                        hw.fixture(fixtures/name,mode,session/'preparation/fixture')
                    result=screen.pc.validate_fixtures(fixtures)
                    c.save(fixtures/'result.json',result); c.seal(fixtures)
                finally: give(fixtures)
                fixtures_done=True; reply(result)
            elif op=='condition' and fixtures_done and active is None and index<16 and not condition_ready:
                spec=screen.matrix()[index]; condition=spec['condition']
                expected=manifest['control_plan'][condition]
                controls.set_bounds(expected)
                actual=controls.snapshot()
                if actual!=expected: raise ValueError('CPU bound application readback failed')
                c.save(out/f'condition_{transition}.json',dict(condition=condition,trial=spec['trial'],
                    observed=actual,monotonic_ns=time.monotonic_ns()))
                transition+=1; condition_ready=True; reply(dict(condition=condition,verified=True))
            elif op=='attach' and fixtures_done and active is None and index<16 and condition_ready:
                spec=screen.matrix()[index]; d=session/'trials'/spec['trial']
                if c.read(d/'pilot_config.json')!=spec: raise ValueError('trial differs from sealed order')
                initial=c.read(d/'initial.json'); process=initial['process_identity']
                group=Path(initial['cgroup']); container=c.read(d/'container.json')['inspect']
                group_expected=Path('/sys/fs/cgroup/system.slice/docker-'+container['Id']+'.scope')
                if group!=group_expected or not c.same_process(process) or bridge.cgroup(process['pid'])!=group:
                    raise ValueError('live owned cgroup/process mismatch')
                c.validate_resources(initial['initial_limits'],container['HostConfig'],
                    manifest['resource_baseline'],screen.config_for(spec))
                if (container['Image']!=manifest['minimal_image'] or
                    initial['container_server_sha256']!=manifest['minimal_server_sha256']):
                    raise ValueError('wrong minimal executable')
                active=hw.Counter(d,group,spec['counters']); reply(dict(attached=True,trial=spec['trial']))
            elif op in ('enable','disable') and active: reply(active.control(op))
            elif op=='detach' and active and active.state=='disabled':
                active.close(); give(active.directory); active=None; index+=1; condition_ready=False
                reply(dict(detached=True))
            elif op=='finish' and active is None and index in (8,16):
                gate=c.read(session/'feasibility.json')
                if (index==8)==gate['feasibility_passed']: raise ValueError('finish does not follow gate')
                restored=controls.restore(before); expected=before
                c.save(out/'restoration.json',restored)
                if not restored['restored']: raise ValueError('original CPU bounds not restored')
                reply(dict(finished=True,detached_trials=index,restored=True)); return
            else: raise ValueError('unknown/out-of-order fixed operation')
    finally:
        # Restoration must run even if perf cleanup fails or the parent dies.
        try:
            if active:
                try: active.close()
                finally: give(active.directory)
        finally:
            result=controls.restore(before)
            c.save(out/'restoration.json',result); c.seal(out); give(out)
            fixtures=session/'counter_fixtures'
            if fixtures.exists():
                if not (fixtures/'seal.json').exists(): c.seal(fixtures)
                give(fixtures)
            if not result['restored']: print('RESTORATION FAILED: '+json.dumps(result),file=sys.stderr)


def recovery(session):
    if os.geteuid()!=0 or not os.environ.get('SUDO_UID'):
        raise ValueError('use external sudo for recovery')
    m=screen.verify(session)
    owner=c.read(session/'owner.json')
    uid,gid=int(os.environ['SUDO_UID']),int(os.environ['SUDO_GID'])
    if owner['uid']!=uid or c.same_process(owner): raise ValueError('owner mismatch or experiment still alive')
    if c.read(session/'speed_control/original.json')!=m['controls_before']:
        raise ValueError('original snapshot differs')
    result=controls.restore(m['controls_before'])
    out=session/'recovery'/str(time.time_ns()); out.mkdir(parents=True)
    c.save(out/'restoration.json',result); c.seal(out)
    for p in [out,*out.rglob('*')]:
        if not p.is_symlink(): os.chown(p,uid,gid)
    print(json.dumps(result,indent=2),flush=True)
    if not result['restored']: raise ValueError('bounds recovery failed; inspect saved receipt')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--directory',required=True)
    p.add_argument('--restore-controls',action='store_true')
    a=p.parse_args()
    try: (recovery if a.restore_controls else helper)(screen.owned(a.directory))
    except BaseException as e:
        print(str(e),file=sys.stderr); raise SystemExit(1)
