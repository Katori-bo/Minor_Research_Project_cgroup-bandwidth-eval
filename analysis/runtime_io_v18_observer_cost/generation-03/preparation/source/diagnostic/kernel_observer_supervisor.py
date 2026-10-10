"""Bounded privilege owner. Only fixed, argument-free socket operations are exposed."""
import fcntl
import os
from pathlib import Path
import pwd
import select
import signal
import socket
import subprocess
import time
import uuid

import kernel_observer_common as c
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures


def command(argv, timeout=20):
    return subprocess.check_output(argv, text=True, stderr=subprocess.PIPE, timeout=timeout).strip()


class OwnedService:
    def __init__(self, session, config, attempt, uid, gid):
        self.session=session; self.config=config; self.directory=attempt; self.uid=uid; self.gid=gid
        self.container=None; self.group=None; self.observer=None; self.owned=set(); self.logs={}
        self.bytes=0; self.started=time.monotonic(); self.closed=False; self.released=False
        self.before=fixtures.root_state(); self.pipes={}; self.snapshots=[]

    def publish(self, name, value):
        c.save(self.directory/name, value); os.chown(self.directory/name, self.uid, self.gid)

    def create(self):
        frozen=self.session/'preparation'
        manifest=c.read(frozen/'manifest.json')
        qualification=self.directory/'qualification'; qualification.mkdir()
        os.chown(qualification,self.uid,self.gid)
        import shutil
        shutil.copy2(frozen/'gate',qualification/'gate'); os.mkfifo(qualification/'start.fifo',0o600)
        for p in qualification.iterdir(): os.chown(p,self.uid,self.gid)
        name='quota-v18-cost-'+uuid.uuid4().hex
        argv=['docker','create','--name',name,'--label','research.v18.cost='+str(self.session),
              '--cpuset-cpus','2,4','--cpu-period','100000','--cpu-quota','50000',
              '--mount',f'type=bind,src={qualification},dst=/qualification,readonly',
              '--entrypoint','/qualification/gate','-e','GOMAXPROCS=1','-e','WORKERS=4',
              '-e','QUEUE_SIZE=128','-e','INSTRUMENT=1','-p','127.0.0.1::8080',manifest['image'],'--server']
        # A failed docker create may still leave the uniquely named owned container.
        self.container=name
        command(argv); command(['docker','start',self.container])
        inspect=__import__('json').loads(command(['docker','inspect',self.container]))[0]
        self.pid=inspect['State']['Pid']; bridge.stopped(self.pid,state='S'); self.group=bridge.cgroup(self.pid)
        if os.sched_getaffinity(self.pid)!={2,4} or (self.group/'cgroup.procs').read_text().split()!=[str(self.pid)]:
            raise ValueError('startup ownership/affinity mismatch')
        limits={n:(self.group/n).read_text().strip() for n in ('cpu.max','cpu.max.burst','cpuset.cpus.effective','memory.max','pids.max')}
        expected={'cpu.max':'50000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2,4','memory.max':'max','pids.max':'max'}
        host=inspect['HostConfig']
        if limits!=expected or host['Memory']!=0 or host['MemorySwap']!=0 or host.get('PidsLimit') not in (None,0):
            raise ValueError('CPU or historical memory/PID limits differ')
        if inspect['Image']!=manifest['image'] or len(inspect['Mounts'])!=1 or inspect['Mounts'][0]['Destination']!='/qualification':
            raise ValueError('original packaged image/mount mismatch')
        if c.digest(Path(f'/proc/{self.pid}/exe'))!=manifest['gate_sha256']: raise ValueError('startup gate identity differs')
        self.metadata=dict(pid=self.pid,cgroup=str(self.group),cgroup_id=self.group.stat().st_ino,capped=True,
                           initial_limits=limits, time_namespaces=bridge.namespaces(self.pid),
                           uncapped_ancestors=bridge.ancestors(self.group),initial_cpu_stat=fixtures.stat(self.group),
                           startup='single-thread FIFO before original /server exec')
        if self.metadata['initial_cpu_stat'].get('nr_throttled',0): raise ValueError('gate already throttled')
        self.publish('container.json',dict(argv=argv,inspect=inspect)); self.publish('initial.json',self.metadata)
        port=command(['docker','port',self.container,'8080/tcp']).rsplit(':',1)[1]
        self.base=f'http://127.0.0.1:{port}'
        if self.config['arm']=='on':
            for name in ('events.txt','observer.stderr'):
                f=(self.directory/name).open('xb'); os.chown(self.directory/name,self.uid,self.gid); self.logs[name]=f
            argv=['/usr/bin/bpftrace','-q','-k','-B','line',str(frozen/'kernel_observer.bt'),str(self.pid),str(self.metadata['cgroup_id'])]
            self.observer=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE, start_new_session=True,
                env={'PATH':'/usr/bin:/bin','LC_ALL':'C'},preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
            self.capture_started=time.monotonic()
            self.pipes={self.observer.stdout.fileno():'events.txt',self.observer.stderr.fileno():'observer.stderr'}
            for fd in self.pipes: os.set_blocking(fd,False)
            until=time.monotonic()+30
            while b'BEGIN ' not in (self.directory/'events.txt').read_bytes():
                self.guard(check_worker=False)
                if time.monotonic()>until: raise TimeoutError('observer attach timeout')
                time.sleep(.02)
            self.owned=fixtures.owned_ids(self.observer.pid)
            self.metadata['owned_bpf_ids']=sorted(self.owned); self.publish('initial.json',self.metadata)
        return dict(base=self.base,cgroup=str(self.group))

    def pump(self):
        ready=select.select(list(self.pipes),[],[],0)[0] if self.pipes else []
        for fd in ready:
            try: block=os.read(fd,65536)
            except BlockingIOError: continue
            if not block: del self.pipes[fd]; continue
            if self.bytes+len(block)>c.RAW_LIMIT:
                # Preserve the overflowing chunk separately, never silently discard it.
                self.publish('raw_limit_violation.json',dict(retained_bytes=self.bytes,overflow_bytes=len(block)))
                with (self.directory/'overflow.bin').open('ab') as f: f.write(block)
                os.chown(self.directory/'overflow.bin',self.uid,self.gid)
                raise ValueError('1 GiB observer output ceiling exceeded')
            self.bytes+=len(block); f=self.logs[self.pipes[fd]]; f.write(block); f.flush()

    def guard(self, check_worker=True):
        self.pump()
        if time.monotonic()-self.started>c.WATCHDOG_SEC: raise TimeoutError('360-second active-trial watchdog')
        if self.observer:
            if self.observer.poll() is not None: raise ValueError('observer exited before final service exit')
            if time.monotonic()-self.capture_started>=c.CAPTURE_SEC: raise TimeoutError('300-second capture ceiling')
            if (self.directory/'observer.stderr').stat().st_size: raise ValueError('observer diagnostics')
        if check_worker:
            if not Path(f'/proc/{self.pid}').exists(): raise ValueError('service worker died')
            if Path(f'/proc/{self.pid}/stat').read_text().split(') ',1)[1][0] in ('Z','X'):
                raise ValueError('service worker died')
            if bridge.cgroup(self.pid)!=self.group: raise ValueError('owned worker identity changed')

    def release(self):
        self.guard(); bridge.release_fifo(self.directory/'qualification/start.fifo'); self.released=True
        until=time.monotonic()+10
        while True:
            self.guard()
            try:
                health=bridge.get(self.base,'health'); break
            except OSError:
                if time.monotonic()>until: raise TimeoutError('service startup timeout')
                time.sleep(.05)
        manifest=c.read(self.session/'preparation/manifest.json'); exe=Path(f'/proc/{self.pid}/exe')
        sha=c.digest(exe)
        if os.readlink(exe)!='/server' or sha!=manifest['server_sha256']: raise ValueError('running packaged executable differs')
        self.publish('identity.json',dict(health=health,server_sha256=sha,expected_server_sha256=manifest['server_sha256'],
            image=manifest['image'],expected_image=manifest['image'],loadgen_sha256=manifest['loadgen_sha256'],
            expected_loadgen_sha256=manifest['loadgen_sha256']))
        return dict(health=health)

    def observe(self):
        self.guard(); snap=bridge.snapshot(self.pid,self.group); self.snapshots.append(snap)
        before=time.monotonic_ns(); stat=fixtures.stat(self.group); after=time.monotonic_ns()
        self.publish('thread_snapshots.json',self.snapshots)
        return dict(before_ns=before,after_ns=after,cpu_stat=stat)

    def close(self, failure=None):
        if self.closed:
            previous=c.read(self.directory/'cleanup.json')
            if previous['errors']: raise ValueError('owned cleanup remains unverified')
            return previous
        errors=[]; detached=False; removed=False
        if self.container:
            try: command(['docker','stop','--time','2',self.container],timeout=10)
            except Exception as e: errors.append('service stop: '+str(e))
        if self.observer:
            try:
                # Keep consuming pipes through service exit and collector END.
                until=time.monotonic()+.3
                while time.monotonic()<until: self.pump(); time.sleep(.01)
                if not self.owned: self.owned=fixtures.owned_ids(self.observer.pid)
                self.observer.send_signal(signal.SIGINT)
                until=time.monotonic()+10
                while self.observer.poll() is None:
                    self.pump()
                    if time.monotonic()>until: raise TimeoutError('observer stop timeout')
                    time.sleep(.01)
                while self.pipes: self.pump(); time.sleep(.01)
                if self.observer.returncode: raise ValueError('observer nonzero exit')
            except Exception as e:
                errors.append('observer stop: '+str(e)); fixtures.stop(self.observer,signal.SIGINT)
        for f in self.logs.values(): f.close()
        try:
            fixtures.wait_detached(self.owned); detached=True
        except Exception as e: errors.append('detach: '+str(e))
        if self.container:
            try:
                logs=subprocess.run(['docker','logs',self.container],capture_output=True,timeout=10,check=True)
                for name,data in (('container.stdout',logs.stdout),('container.stderr',logs.stderr)):
                    (self.directory/name).write_bytes(data); os.chown(self.directory/name,self.uid,self.gid)
            except Exception as e: errors.append('service logs: '+str(e))
            try:
                command(['docker','rm','-f',self.container]); removed=True
            except Exception as e: errors.append('container removal: '+str(e))
        until=time.monotonic()+5
        while self.group and self.group.exists() and time.monotonic()<until: time.sleep(.05)
        group_removed=self.group is not None and not self.group.exists()
        if not group_removed: errors.append('cgroup removal unverified')
        try: after=fixtures.root_state(); unchanged=after==self.before
        except Exception as e: after=None; unchanged=False; errors.append(str(e))
        if not unchanged: errors.append('root tracing controls changed')
        result=dict(errors=errors,failure=failure,detached=detached,owned_bpf_ids=sorted(self.owned),
                    container_removed=removed,cgroup_removed=group_removed,root_controls_unchanged=unchanged,
                    root_controls_before=self.before,root_controls_after=after,raw_bytes=self.bytes,
                    observer_returncode=None if self.observer is None else self.observer.returncode)
        self.publish('cleanup.json',result); self.closed=True
        if errors: raise ValueError('owned cleanup requires review: '+'; '.join(errors))
        return result


def supervise(session, mode):
    if os.geteuid()!=0 or not os.environ.get('SUDO_UID'): raise ValueError('use external launcher with local sudo')
    uid=int(os.environ['SUDO_UID']); gid=int(os.environ['SUDO_GID'])
    if uid==0 or session.stat().st_uid!=uid: raise ValueError('original user ownership required')
    os.sched_setaffinity(0,{0,1})
    from kernel_observer_cost import verify_preparation, verify_qualification, pending
    verify_preparation(session,current=True)
    if mode!='qualify': verify_qualification(session)
    if mode=='start' and any((session/'trials').glob('*/attempt-*')):
        raise ValueError('existing performance attempts: use explicit resume')
    if (session/'supervisor_exit.json').exists() and not c.read(session/'supervisor_exit.json')['ownership_released']:
        raise ValueError('previous ownership cleanup is unverified; review retained evidence before a new generation')
    configs=pending(session,mode)
    if not configs and mode=='qualify' and (session/'qualification').exists():
        verify_qualification(session); return
    c.capacity(session)
    lock=(c.ROOT/'.experiment.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    parent,child=socket.socketpair(); parent.settimeout(5)
    protocol=c.Protocol(len(configs)); backend=None; failure=None
    pid=os.fork()
    if pid==0:
        parent.close(); lock.close()
        user=pwd.getpwuid(uid); os.initgroups(user.pw_name,gid); os.setgid(gid); os.setuid(uid)
        os.environ.update(HOME=user.pw_dir,USER=user.pw_name,LOGNAME=user.pw_name)
        for key in list(os.environ):
            if key.startswith('SUDO_'): del os.environ[key]
        try:
            from kernel_observer_cost import worker
            worker(session,mode,configs,child)
            os._exit(0)
        except BaseException as e:
            print('Benchmark stopped: '+str(e),flush=True); os._exit(1)
    child.close()
    starttime=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
    def signal_worker(sig):
        try:
            current=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()[19]
            if current==starttime: os.kill(pid,sig)
        except ProcessLookupError: pass
        except FileNotFoundError: pass
    c.save(session/'owner.json',dict(supervisor_pid=os.getpid(),worker_pid=pid,worker_starttime=starttime,
                                   mode=mode,uid=uid,started=time.time()))
    os.chown(session/'owner.json',uid,gid)
    def interrupt(signum,frame): raise InterruptedError('supervisor interrupted')
    signal.signal(signal.SIGINT,interrupt); signal.signal(signal.SIGTERM,interrupt)
    last=time.monotonic(); deadline=last+2000*(len(configs)+1); cleanup_verified=True
    try:
        while protocol.state!='finished':
            if time.monotonic()>deadline: raise TimeoutError('bounded supervisor lifetime exceeded')
            if backend: backend.guard()
            ready=select.select([parent],[],[],.05)[0]
            if not ready:
                if time.monotonic()-last>2000: raise TimeoutError('supervisor idle timeout')
                if os.waitpid(pid,os.WNOHANG)[0]: raise ChildProcessError('benchmark worker died')
                continue
            request=c.receive(parent); op=protocol.accept(request); last=time.monotonic()
            if op=='create':
                config=configs[protocol.index]; trial_root=session/('rehearsals' if mode=='qualify' else 'trials')/config['trial']
                attempts=sorted(trial_root.glob('attempt-*'))
                if not attempts: raise ValueError('benchmark attempt missing')
                attempt=attempts[-1]
                if attempt.resolve()!=attempt or attempt.stat().st_uid!=uid or c.read(attempt/'config.json')!=config:
                    raise ValueError('attempt ownership/configuration rejected')
                backend=OwnedService(session,config,attempt,uid,gid); result=backend.create()
            elif op=='release': result=backend.release()
            elif op=='observe': result=backend.observe()
            elif op=='end': result=backend.close(); backend=None
            else: result=dict(finished=True)
            c.send(parent,dict(ok=True,result=result))
        until=time.monotonic()+600
        while True:
            waited,status=os.waitpid(pid,os.WNOHANG)
            if waited: break
            if time.monotonic()>until: raise TimeoutError('offline worker completion timeout')
            time.sleep(.1)
        if status: raise ChildProcessError('benchmark worker failed')
    except BaseException as e:
        failure=str(e)
        try: c.send(parent,dict(ok=False,error=failure))
        except Exception: pass
        signal_worker(signal.SIGTERM)
        if backend:
            try: backend.close(failure)
            except Exception as cleanup: failure+='; '+str(cleanup); cleanup_verified=False
            c.save(backend.directory/'interruption.json',dict(error=failure,time=time.time()))
            c.seal(backend.directory)
            for p in backend.directory.rglob('*'):
                if p.is_file(): os.chown(p,uid,gid)
        raise
    finally:
        parent.close()
        try:
            for _ in range(50):
                if os.waitpid(pid,os.WNOHANG)[0]: break
                time.sleep(.1)
            else: signal_worker(signal.SIGKILL); os.waitpid(pid,0)
        except ChildProcessError: pass
        c.save(session/'supervisor_exit.json',dict(error=failure,time=time.time(),ownership_released=cleanup_verified))
        os.chown(session/'supervisor_exit.json',uid,gid); lock.close()
