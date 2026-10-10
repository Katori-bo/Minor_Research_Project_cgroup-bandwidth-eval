#!/usr/bin/env python3
"""Bounded engineering qualification. No calibration fit or scientific validation."""
import argparse
import io
import json
import math
import os
from pathlib import Path
import signal
import statistics
import subprocess
import sys
import time
import traceback
import urllib.request
import uuid

import imgproxy_prepare as prep
import kernel_observer_common as common
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures

BASE, SOFTWARE, ROOT = prep.BASE, prep.SOFTWARE, prep.ROOT
LABEL = 'research.imgproxy.qualification.owner'
LIMITS = {'cpu.max':'25000 100000', 'cpu.max.burst':'0',
          'cpuset.cpus.effective':'2,4', 'memory.max':str(512*1024**2), 'pids.max':'128'}
FILES = ('diagnostic/imgproxy_prepare.py', 'diagnostic/imgproxy_qualify.py',
         'diagnostic/test_imgproxy_qualification.py',
         'diagnostic/imgproxy_client/main.go', 'diagnostic/imgproxy_client/go.mod',
         'diagnostic/start_imgproxy_qualification.sh', 'docs/runtime_io_imgproxy_qualification_20261009.md',
         'diagnostic/kernel_start_gate.c', 'diagnostic/kernel_observer_common.py',
         'diagnostic/kernel_service_bridge.py', 'diagnostic/kernel_fixtures.py',
         'diagnostic/leftover_observer_audit.py', 'diagnostic/leftover_observer_review.py')
PROTOCOL = dict(status='engineering qualification only', functional_created_cap=6,
    pilot_created_cap=12, pilot_total_sec=1200, cleanup_reserve_sec=120,
    active_trial_sec=120, retries=0, settling_sec=10,
    pairs=6, pair_orders=['stock,observed','observed,stock']*3,
    rate=5, interval_ns=200000000, warmup_offers=25, measurement_offers=200,
    measurement_sec=40, limits=LIMITS, gomaxprocs=1, application_workers=1,
    queue_capacity=128, recorded_events_capacity=1024,
    observer_gates=dict(cpu_per_offer_upper_relative=0.05, median_latency_upper_relative=0.05,
        t_multiplier=2.571, df=5, dispatch_p99_ns=2000000, dispatch_max_ns=10000000,
        required_success_fraction=1, required_queue_le_100us_fraction=0.99,
        recorded_measurement_throttled_periods=0),
    execution_model_gate='pending separate concurrency review; this pilot cannot prove serial native CPU execution',
    scientific_collection=False)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def read(path):
    return json.loads(path.read_text())


def cmd(argv, timeout=20):
    p=subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if p.returncode: raise RuntimeError(repr(argv)+': '+p.stderr[-2000:])
    return p.stdout.strip()


def inspect_owned(name, nonce):
    p=subprocess.run(['docker','inspect',name],capture_output=True,text=True,timeout=15)
    if p.returncode:
        if 'no such' in p.stderr.lower(): return None
        raise RuntimeError(p.stderr)
    value=json.loads(p.stdout)[0]
    if value['Config'].get('Labels',{}).get(LABEL)!=nonce: raise ValueError('container ownership differs')
    return value


def remove_owned(name, nonce):
    value=inspect_owned(name,nonce)
    if value is not None: cmd(['docker','rm','-f',value['Id']])
    if inspect_owned(name,nonce) is not None: raise ValueError('owned container remains')


def same_owner(identity):
    try:
        return process_identity(identity['pid'])==identity
    except (FileNotFoundError, ProcessLookupError):
        return False


def process_identity(pid):
    fields=Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1].split()
    return dict(pid=pid,start_ticks=int(fields[19]))


def watchdog(directory):
    # Independent cleanup also covers a killed parent or a stuck client.
    owner=read(directory/'ownership.json')
    while not (directory/'cleanup.json').exists():
        if not same_owner(owner['owner']) or time.monotonic()>=owner['deadline_monotonic']:
            errors=[]
            client_path=directory/'client-ownership.json'
            if client_path.exists():
                client=read(client_path)
                if same_owner(client):
                    try: os.killpg(client['pid'],signal.SIGKILL)
                    except ProcessLookupError: pass
            try: remove_owned(owner['container'],owner['nonce'])
            except Exception as exc: errors.append(str(exc))
            save(directory/'watchdog-cleanup.json',dict(invalidated=True,errors=errors))
            if same_owner(owner['owner']): os.kill(owner['owner']['pid'],signal.SIGTERM)
            return
        time.sleep(.5)


def desktop_absent():
    p=subprocess.run(['pgrep','-x','ChatGPT|Codex'],capture_output=True,text=True,timeout=3)
    if p.returncode!=1: raise ValueError('fully quit Codex/ChatGPT before overhead qualification')


def fetch(base, endpoint, headers=None):
    with urllib.request.urlopen(urllib.request.Request(base+'/'+endpoint,headers=headers or {}),timeout=3) as r:
        return r.read(),dict(r.headers)


def join_records(client, server):
    rows=client['Rows']; records=server['Records']
    if (server['Schema']!='imgproxy-qualification-v1' or server['Overflow'] or server['GOMAXPROCS']!=1
        or server['GoVersion']!='go1.27.1' or server['Capacity']!=1024):
        raise ValueError('server recorder contract differs')
    index={r['ID']:r for r in records}
    if len(index)!=len(records): raise ValueError('duplicate server request ID')
    queues=[]; process=[]; held=[]
    for row in rows:
        s=index[row['ID']]
        order=['ExecuteStartNs','QueueStartNs','QueueDoneNs','ProcessStartNs','ProcessDoneNs',
               'ResponseStartNs','ResponseDoneNs','ReleaseBeforeNs','ReleaseAfterNs','ExecuteDoneNs']
        if not s['Success'] or any(s[a]>s[b] for a,b in zip(order,order[1:])):
            raise ValueError('server success or monotonic stage order differs')
        q=s['QueueDoneNs']-s['QueueStartNs']; p=s['ProcessDoneNs']-s['ProcessStartNs']
        if row['TimingError'] or row['QueueNs']!=q or row['ProcessNs']!=p:
            raise ValueError('header/raw timing join differs')
        if row['BodyDoneNs']-row['DispatchNs']<q+p:
            raise ValueError('negative client/queue/process residual')
        queues.append(q); process.append(p); held.append(s['ReleaseBeforeNs']-s['QueueDoneNs'])
    return dict(queue_le_100us_fraction=sum(q<=100000 for q in queues)/len(rows),
                median_queue_ns=statistics.median(queues), total_process_ns=sum(process),
                total_worker_held_lower_ns=sum(held))


def validate_client(value, prefix, count, expected_hash=None):
    if value['Schema']!='imgproxy-client-v1' or value['Count']!=count or value['IntervalNs']!=PROTOCOL['interval_ns']:
        raise ValueError('client settings differ')
    rows=value['Rows']
    if len(rows)!=count: raise ValueError('all-offer count differs')
    for i,r in enumerate(rows):
        if (r['ID']!=prefix+'-'+str(i) or r['EchoID']!=r['ID'] or r['Error'] or r['Status']!=200
            or r['ContentType']!='image/jpeg' or r['BodyBytes']<=0
            or not r['ScheduledNs']==i*PROTOCOL['interval_ns']<=r['DispatchNs']<=r['HeadersNs']<=r['BodyDoneNs']
            or expected_hash is not None and r['BodySHA256']!=expected_hash):
            raise ValueError('client identity, full-body output or timing failed')
    lag=sorted(r['DispatchNs']-r['ScheduledNs'] for r in rows)
    return dict(median_e2e_ns=statistics.median(r['BodyDoneNs']-r['ScheduledNs'] for r in rows),
        dispatch_p99_ns=lag[math.ceil(.99*count)-1],dispatch_max_ns=max(lag),
        body_sha256=rows[0]['BodySHA256'],offers=count)


class Service:
    def __init__(self,directory,arm,performance=False):
        self.directory,self.arm,self.performance=directory,arm,performance
        self.name='quota-imgproxy-'+uuid.uuid4().hex; self.nonce=uuid.uuid4().hex
        self.watcher=None; self.client=None; self.started=time.monotonic()
        self.image=read(SOFTWARE/'images.json')[arm]

    def start(self):
        q=self.directory/'qualification'; q.mkdir(); os.mkfifo(q/'start.fifo',0o600)
        save(self.directory/'ownership.json',dict(owner=process_identity(os.getpid()),
            container=self.name,nonce=self.nonce,deadline_monotonic=self.started+PROTOCOL['active_trial_sec']))
        self.watch_log=(self.directory/'watchdog.log').open('x')
        self.watcher=subprocess.Popen([sys.executable,'-B',__file__,'watchdog','--directory',str(self.directory)],
            stdout=self.watch_log,stderr=subprocess.STDOUT,start_new_session=True)
        argv=['docker','create','--name',self.name,'--label',LABEL+'='+self.nonce,
            '--cpuset-cpus','2,4','--cpu-period','100000','--cpu-quota','25000',
            '--memory','512m','--pids-limit','128','--read-only','--tmpfs','/tmp:rw,size=64m',
            '--mount',f'type=bind,src={q},dst=/qualification,readonly',
            '-p','127.0.0.1::8080','-e','GOMAXPROCS=1','-e','IMGPROXY_WORKERS=1',
            '-e','IMGPROXY_REQUESTS_QUEUE_SIZE=128','-e','IMGPROXY_LOCAL_FILESYSTEM_ROOT=/input',
            '-e','IMGPROXY_LOG_LEVEL=error','-e','IMGPROXY_USE_ETAG=false','-e','IMGPROXY_USE_LAST_MODIFIED=false',
            '-e','IMGPROXY_QUALIFICATION='+('1' if self.arm=='observed' else '0'),self.image]
        cmd(argv); cmd(['docker','start',self.name]); value=inspect_owned(self.name,self.nonce)
        save(self.directory/'container.json',dict(argv=argv,inspect=value))
        if value['Image']!=self.image: raise ValueError('pinned image differs')
        self.pid=value['State']['Pid']; self.identity=process_identity(self.pid)
        self.group=bridge.cgroup(self.pid); self.limits={n:(self.group/n).read_text().strip() for n in LIMITS}
        if self.limits!=LIMITS: raise ValueError('CPU/memory/PID contract differs: '+str(self.limits))
        save(self.directory/'initial.json',dict(pid=self.pid,cgroup=str(self.group),limits=self.limits,
            namespaces=bridge.namespaces(self.pid),ancestors=bridge.ancestors(self.group)))
        bridge.stopped(self.pid,state='S')
        if len(list(Path(f'/proc/{self.pid}/task').iterdir()))!=1 or (self.group/'cgroup.procs').read_text().split()!=[str(self.pid)]:
            raise ValueError('startup gate is not the sole single-thread process')
        packaged=self.directory/'packaged-server'
        cmd(['docker','cp',self.name+':/server',str(packaged)])
        if prep.sha(packaged)!=read(SOFTWARE/'manifest.json')['binaries'][self.arm]:
            raise ValueError('actual packaged server hash differs')
        save(self.directory/'executable.json',dict(sha256=prep.sha(packaged)))
        # The immutable hash and image are retained; discard only this temporary copy.
        packaged.unlink()
        bridge.release_fifo(q/'start.fifo')
        port=cmd(['docker','port',self.name,'8080/tcp']).rsplit(':',1)[1]; self.base='http://127.0.0.1:'+port
        until=time.monotonic()+15
        while True:
            self.guard()
            try: fetch(self.base,'health'); break
            except OSError:
                if time.monotonic()>until: raise TimeoutError('imgproxy startup timeout')
                time.sleep(.1)
        return self

    def guard(self):
        if time.monotonic()-self.started>=PROTOCOL['active_trial_sec']: raise TimeoutError('active trial limit')
        if self.performance: desktop_absent()
        if (not same_owner(self.identity) or bridge.cgroup(self.pid)!=self.group
            or (self.group/'cgroup.procs').read_text().split()!=[str(self.pid)]
            or {n:(self.group/n).read_text().strip() for n in LIMITS}!=self.limits
            or self.watcher.poll() is not None): raise ValueError('service identity/resources/watchdog changed')

    def collect(self,prefix,count):
        manifest=read(SOFTWARE/'manifest.json'); out=self.directory/(prefix+'.json')
        args=[str(SOFTWARE/'client'),'--url',self.base+manifest['workload']['path'],
            '--prefix',prefix,'--count',str(count),'--interval-ns',str(PROTOCOL['interval_ns'])]
        if self.arm=='observed': args.append('--instrumented')
        with out.open('x') as log, (self.directory/(prefix+'.stderr')).open('x') as err:
            self.client=subprocess.Popen(args,stdout=log,stderr=err,start_new_session=True)
            save(self.directory/'client-ownership.json',process_identity(self.client.pid))
            until=time.monotonic()+count/5+12
            try:
                while self.client.poll() is None:
                    self.guard()
                    if time.monotonic()>until: raise TimeoutError('client drain limit')
                    time.sleep(.25)
                if self.client.returncode: raise ValueError('client exited with failure')
            finally:
                if self.client.poll() is None: bridge.stop_known(self.client)
        return read(out)

    def export(self,expected):
        until=time.monotonic()+3
        while True:
            self.guard(); body,_=fetch(self.base,'qualification/events'); value=json.loads(body)
            if len(value['Records'])==expected: return value
            if len(value['Records'])>expected or time.monotonic()>until: raise ValueError('server record count differs')
            time.sleep(.05)

    def close(self):
        errors=[]
        try: remove_owned(self.name,self.nonce)
        except Exception as exc: errors.append(str(exc))
        save(self.directory/'cleanup.json',dict(errors=errors,elapsed_sec=time.monotonic()-self.started))
        if self.watcher is not None:
            try: self.watcher.wait(timeout=3)
            except subprocess.TimeoutExpired: bridge.stop_known(self.watcher)
            self.watch_log.close()
        if errors: raise ValueError('cleanup unverified: '+str(errors))


def trial(directory,arm,performance=False):
    directory.mkdir()
    save(directory/'sources-at-start.json',{n:prep.sha(ROOT/n) for n in FILES})
    service=Service(directory,arm,performance)
    result=None
    try:
        service.start()
        # Correctness fetch is before warmup and CPU measurements.
        body,headers=fetch(service.base,read(SOFTWARE/'manifest.json')['workload']['path'].lstrip('/'),{'X-Request-ID':'image-check'})
        from PIL import Image
        image=Image.open(io.BytesIO(body)); image.load()
        if image.format!='JPEG' or image.size!=(300,300): raise ValueError('decoded image output differs')
        import hashlib
        expected_hash=hashlib.sha256(body).hexdigest(); (directory/'output.jpg').write_bytes(body)
        if performance:
            warm=service.collect('warmup',25); validate_client(warm,'warmup',25,expected_hash)
            before=fixtures.stat(service.group); save(directory/'threads-before.json',bridge.snapshot(service.pid,service.group))
            value=service.collect('measurement',200)
            after=fixtures.stat(service.group); save(directory/'threads-after.json',bridge.snapshot(service.pid,service.group))
            timing=validate_client(value,'measurement',200,expected_hash)
            counters={k:after[k]-before[k] for k in before}
            save(directory/'measurement-counters.json',dict(before=before,after=after,delta=counters))
            if any(v<0 for v in counters.values()): raise ValueError('counter regression')
            if counters['nr_throttled']: raise ValueError('measurement throttling; no replacement allowed')
            if timing['dispatch_p99_ns']>2000000 or timing['dispatch_max_ns']>10000000: raise ValueError('dispatch timing gate failed')
            result=dict(arm=arm,**timing,cpu_per_offer_usec=counters['usage_usec']/200,
                recorded_throttled_periods=counters['nr_throttled'])
            expected=226
        else:
            value=service.collect('functional',8); timing=validate_client(value,'functional',8,expected_hash)
            result=dict(arm=arm,**timing,functional_only=True); expected=9
        if arm=='observed':
            server=service.export(expected); save(directory/'events.json',server)
            expected_ids={'image-check'}|{r['ID'] for r in value['Rows']}
            if performance:
                expected_ids|={r['ID'] for r in warm['Rows']}
                join_records(warm,server)
            if {r['ID'] for r in server['Records']}!=expected_ids: raise ValueError('all request IDs do not join')
            result.update(join_records(value,server))
            if performance and result['queue_le_100us_fraction']<.99: raise ValueError('pilot queue domain exit')
            if performance:
                result['cpu_to_worker_wall_ratio']=counters['usage_usec']*1000/result['total_worker_held_lower_ns']
        save(directory/'result.json',result)
        return result
    except BaseException as exc:
        save(directory/'failure.json',dict(error=str(exc),traceback=traceback.format_exc()))
        raise
    finally:
        service.close()


def write_protocol():
    save(BASE/'protocol.json',PROTOCOL)
    print('Pre-measurement engineering protocol written')


def functional():
    if read(BASE/'protocol.json')!=PROTOCOL: raise ValueError('protocol differs')
    parent=BASE/'functional'; parent.mkdir(exist_ok=True)
    if len(list(parent.rglob('ownership.json')))+2>PROTOCOL['functional_created_cap']: raise ValueError('functional creation cap')
    directory=parent/('attempt-'+str(len(list(parent.iterdir()))+1).zfill(2)); directory.mkdir()
    os.sched_setaffinity(0,{0,1})
    rows=[trial(directory/arm,arm) for arm in ('stock','observed')]
    if rows[0]['body_sha256']!=rows[1]['body_sha256']: raise ValueError('stock/observed output differs')
    save(directory/'summary.json',dict(functional_pass=True,rows=rows,performance_qualified=False))
    print('Functional pass: stock/observed JPEG output and paired request timings agree.')


def seal():
    passed=sorted((BASE/'functional').glob('attempt-*/summary.json'))
    if not passed or not read(passed[-1])['functional_pass']: raise ValueError('functional qualification required')
    targets={n:prep.sha(ROOT/n) for n in FILES}
    # Include the local helper import closure, not only the entry-point scripts.
    for module in list(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if name is not None:
            file=Path(name).resolve()
            if file.is_file() and file.suffix=='.py' and file.parent==ROOT/'diagnostic':
                targets[str(file.relative_to(ROOT))]=prep.sha(file)
    for p in [BASE/'protocol.json',SOFTWARE/'manifest.json',SOFTWARE/'images.json',
              SOFTWARE/'qualification.patch',SOFTWARE/'client',SOFTWARE/'gate',
              SOFTWARE/'imgproxy-stock',SOFTWARE/'imgproxy-observed',passed[-1]]:
        targets[str(p.relative_to(ROOT))]=prep.sha(p)
    for p in passed[-1].parent.rglob('*'):
        if p.is_file(): targets[str(p.relative_to(ROOT))]=prep.sha(p)
    path=BASE/'bundle-seal.json'
    with path.open('x') as f: json.dump(dict(files_sha256=targets,baseline=common.baseline(),protocol=PROTOCOL),f,indent=2); f.write('\n')
    print('Qualification bundle sealed; overhead pilot has not started.')


def verify():
    sealed=read(BASE/'bundle-seal.json')
    if sealed['protocol']!=PROTOCOL or sealed['baseline']!=common.baseline(): raise ValueError('protocol/host boot differs')
    for n,sha in sealed['files_sha256'].items():
        if prep.sha(ROOT/n)!=sha: raise ValueError('sealed input changed: '+n)
    return sealed


def effects_from(rows):
    expected={(pair,arm) for pair in range(1,7) for arm in ('stock','observed')}
    if len(rows)!=12 or {(r['pair'],r['arm']) for r in rows}!=expected:
        raise ValueError('six complete paired blocks required')
    if any(not math.isfinite(r[key]) or r[key]<=0 for r in rows for key in ('cpu_per_offer_usec','median_e2e_ns')):
        raise ValueError('positive finite paired endpoints required')
    effects={}
    for key in ('cpu_per_offer_usec','median_e2e_ns'):
        ratios=[next(r[key] for r in rows if r['pair']==i and r['arm']=='observed')/
                next(r[key] for r in rows if r['pair']==i and r['arm']=='stock')-1 for i in range(1,7)]
        mean=statistics.mean(ratios); half=2.571*statistics.stdev(ratios)/math.sqrt(6)
        effects[key]=dict(pair_relative_changes=ratios,mean=mean,ci95=[mean-half,mean+half],upper_le_5pct=mean+half<=.05)
    return effects


def replay():
    # Offline reconstruction from all-offer client records and actual CPU counters.
    sealed=read(BASE/'bundle-seal.json')
    for n,sha in sealed['files_sha256'].items():
        if prep.sha(ROOT/n)!=sha: raise ValueError('sealed input changed: '+n)
    directory=BASE/'pilot'; summary=read(directory/'summary.json'); rows=[]
    if summary['status'] not in ('observer_cost_qualified','observer_cost_not_qualified'):
        raise ValueError('pilot is incomplete or unavailable')
    for pair,order in enumerate(PROTOCOL['pair_orders'],1):
        for arm in order.split(','):
            case=directory/f'p{pair}_{arm}'
            if read(case/'cleanup.json')['errors']: raise ValueError('cleanup failed')
            if (case/'watchdog-cleanup.json').exists() or (case/'failure.json').exists():
                raise ValueError('case invalidated')
            container=read(case/'container.json')['inspect']; owner=read(case/'ownership.json')
            if (container['Image']!=read(SOFTWARE/'images.json')[arm]
                or container['Config']['Labels'].get(LABEL)!=owner['nonce']
                or read(case/'initial.json')['limits']!=LIMITS
                or read(case/'executable.json')['sha256']!=read(SOFTWARE/'manifest.json')['binaries'][arm]):
                raise ValueError('case identity differs')
            for n,sha in read(case/'sources-at-start.json').items():
                if prep.sha(ROOT/n)!=sha: raise ValueError('case source changed')
            body_hash=prep.sha(case/'output.jpg')
            warm=read(case/'warmup.json'); validate_client(warm,'warmup',25,body_hash)
            value=read(case/'measurement.json'); timing=validate_client(value,'measurement',200,body_hash)
            counts=read(case/'measurement-counters.json')
            delta={k:counts['after'][k]-counts['before'][k] for k in counts['before']}
            if (delta!=counts['delta'] or any(v<0 for v in delta.values()) or delta['nr_throttled']
                or timing['dispatch_p99_ns']>2000000 or timing['dispatch_max_ns']>10000000):
                raise ValueError('measurement counter/dispatch gate differs')
            row=dict(arm=arm,**timing,cpu_per_offer_usec=delta['usage_usec']/200,
                recorded_throttled_periods=delta['nr_throttled'])
            if arm=='observed':
                server=read(case/'events.json')
                if len(server['Records'])!=226: raise ValueError('server count differs')
                expected_ids={'image-check'}|{r['ID'] for r in warm['Rows']}|{r['ID'] for r in value['Rows']}
                if {r['ID'] for r in server['Records']}!=expected_ids: raise ValueError('raw all-offer IDs differ')
                join_records(warm,server)
                row.update(join_records(value,server))
                if row['queue_le_100us_fraction']<.99: raise ValueError('queue-domain exit')
                row['cpu_to_worker_wall_ratio']=delta['usage_usec']*1000/row['total_worker_held_lower_ns']
            if row!=read(case/'result.json'): raise ValueError('reconstructed result differs')
            row['pair']=pair; rows.append(row)
    effects=effects_from(rows)
    status='observer_cost_qualified' if all(v['upper_le_5pct'] for v in effects.values()) else 'observer_cost_not_qualified'
    if rows!=summary['rows'] or effects!=summary['effects'] or status!=summary['status']:
        raise ValueError('summary reconstruction differs')
    if summary['ready_for_scientific_collection'] or summary['scientific_collection']:
        raise ValueError('engineering evidence mislabeled as scientific collection')
    inventory=read(directory/'observer-inventory.json')
    if prep.sha(Path(inventory['path']))!=inventory['sha256']: raise ValueError('observer inventory changed')
    print('Offline replay passed: '+status)
    return dict(passed=True,status=status,all_offers=2400,pairs=6,scientific_collection=False)


def pilot():
    verify(); desktop_absent()
    directory=BASE/'pilot'; directory.mkdir()
    os.sched_setaffinity(0,{0,1})
    deadline=time.monotonic()+PROTOCOL['pilot_total_sec']-PROTOCOL['cleanup_reserve_sec']
    started=time.monotonic(); rows=[]
    save(directory/'lifetime.json',dict(started_monotonic=started,deadline_monotonic=deadline,protocol=PROTOCOL))
    try:
        import leftover_observer_audit as audit
        import leftover_observer_review as review
        evidence=ROOT/'analysis/runtime_io_leftover_observer_audit'/('imgproxy-'+str(time.time_ns())+'.json')
        cmd(['sudo','-n',sys.executable,'-B',str(ROOT/'diagnostic/leftover_observer_audit.py'),'--output',str(evidence)],timeout=60)
        inventory=read(evidence)
        if inventory['uid']!=0 or inventory['assessment']!=audit.assess(inventory): raise ValueError('observer inventory differs')
        if not inventory['assessment']['clear_snapshot'] and not review.review(evidence)['performance_eligible']:
            raise ValueError('leftover observer inventory not eligible')
        save(directory/'observer-inventory.json',dict(path=str(evidence),sha256=prep.sha(evidence)))
        for pair,order in enumerate(PROTOCOL['pair_orders'],1):
            for arm in order.split(','):
                desktop_absent()
                if time.monotonic()+130>deadline: raise TimeoutError('total qualification limit')
                time.sleep(PROTOCOL['settling_sec'])
                print(f'Qualification pair {pair}/6: {arm}',flush=True)
                row=trial(directory/f'p{pair}_{arm}',arm,performance=True); row['pair']=pair; rows.append(row)
        effects=effects_from(rows)
        passed=all(v['upper_le_5pct'] for v in effects.values())
        result=dict(status='observer_cost_qualified' if passed else 'observer_cost_not_qualified',
            rows=rows,effects=effects,elapsed_sec=time.monotonic()-started,
            scientific_collection=False,ready_for_scientific_collection=False,
            next_step='Review native concurrency/execution assumptions and draft the prospective protocol.')
        save(directory/'summary.json',result)
        save(directory/'replay.json',replay())
        save(directory/'evidence-seal.json',dict(files_sha256={str(p.relative_to(directory)):prep.sha(p)
            for p in sorted(directory.rglob('*')) if p.is_file()}))
        print('Qualification: '+result['status']+'; scientific collection remains unstarted.',flush=True)
    except BaseException as exc:
        save(directory/'summary.json',dict(status='qualification_unavailable',error=str(exc),rows=rows,
            scientific_collection=False,ready_for_scientific_collection=False,elapsed_sec=time.monotonic()-started))
        raise


def handle_signal(signum, frame):
    raise RuntimeError('terminal signal '+str(signum))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=('write-protocol','functional','seal','verify','replay','pilot','watchdog'))
    p.add_argument('--directory',type=Path); args=p.parse_args()
    if args.phase=='watchdog': watchdog(args.directory)
    else:
        signal.signal(signal.SIGTERM,handle_signal); signal.signal(signal.SIGINT,handle_signal)
        if args.phase=='write-protocol': write_protocol()
        else: globals()[args.phase]()
