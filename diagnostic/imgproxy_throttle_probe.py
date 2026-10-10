#!/usr/bin/env python3
"""One bounded forensic probe; preserves the stopped qualification unchanged."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import imgproxy_qualify as q

ROOT=q.ROOT
BASE=ROOT/'analysis/runtime_io_imgproxy_throttle_probe/generation-01'
SOFTWARE=BASE/'software'
PROTOCOL=dict(role='forensic localization only; not a replacement qualification',
    functional_created_cap=1,run_created_cap=1,retries=0,total_sec=300,cleanup_reserve_sec=120,
    active_service_sec=120,settling_sec=10,idle_sec=40,warmup_offers=25,measurement_offers=200,
    rate=5,interval_ns=200000000,measurement_sec=40,counter_interval_sec=.004,
    counter_sample_cap=32000,limits=q.LIMITS,scientific_collection=False,
    settings_changed=False,observer_cost_qualification=False,
    caveat='Counter update intervals are not scheduler throttle start/end timestamps. Monitoring overhead is not qualified.')
FILES=('diagnostic/imgproxy_throttle_probe.py','diagnostic/test_imgproxy_throttle_probe.py',
       'diagnostic/start_imgproxy_throttle_probe.sh','docs/runtime_io_imgproxy_throttle_probe_20261009.md')


def prepare():
    q.verify(); SOFTWARE.mkdir(parents=True,exist_ok=False)
    source=ROOT/'diagnostic/imgproxy_client/main.go'; text=source.read_text()
    replacements=[('\t"sync"','\t"sync"\n\t"syscall"\n\t"unsafe"'),
        ('\tstart := time.Now()', '\tmonotonicBefore := monotonicNS()\n\tstart := time.Now()\n\tmonotonicAfter := monotonicNS()'),
        ('\t\tSchema     string','\t\tMonotonicBeforeNs, MonotonicAfterNs int64\n\t\tSchema     string'),
        ('{"imgproxy-client-v1", *count, *interval, rows}', '{monotonicBefore, monotonicAfter, "imgproxy-client-v1", *count, *interval, rows}')]
    for old,new in replacements:
        if text.count(old)!=1: raise ValueError('frozen client anchor changed')
        text=text.replace(old,new)
    text+='''\nfunc monotonicNS() int64 {
    var value syscall.Timespec
    _, _, errno := syscall.RawSyscall(syscall.SYS_CLOCK_GETTIME, 1, uintptr(unsafe.Pointer(&value)), 0)
    if errno != 0 { panic(errno) }
    return value.Sec*1000000000 + value.Nsec
}
'''
    (SOFTWARE/'main.go').write_text(text)
    (SOFTWARE/'go.mod').write_text((ROOT/'diagnostic/imgproxy_client/go.mod').read_text())
    go=q.SOFTWARE/'toolchain/go/bin/go'
    q.cmd([str(go.parent/'gofmt'),'-w',str(SOFTWARE/'main.go')])
    env=dict(os.environ,GOTOOLCHAIN='local',GOENV='off',CGO_ENABLED='0',GOPROXY='off',GOSUMDB='off',
             GOCACHE='/tmp/imgproxy-build-cache',GOMAXPROCS='2')
    with (SOFTWARE/'build.log').open('x') as log:
        subprocess.run([str(go),'build','-trimpath','-o',str(SOFTWARE/'client'),'.'],cwd=SOFTWARE,env=env,
                       stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        subprocess.run([str(go),'vet','.'],cwd=SOFTWARE,env=env,
                       stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
    q.save(BASE/'protocol.json',PROTOCOL)
    print('Forensic client and protocol prepared; application and quota unchanged.')


class Service(q.Service):
    def collect(self,prefix,count):
        out=self.directory/(prefix+'.json')
        args=[str(SOFTWARE/'client'),'--url',self.base+q.read(q.SOFTWARE/'manifest.json')['workload']['path'],
              '--prefix',prefix,'--count',str(count),'--interval-ns','200000000','--instrumented']
        before=time.monotonic_ns()
        with out.open('x') as log,(self.directory/(prefix+'.stderr')).open('x') as err:
            self.client=subprocess.Popen(args,stdout=log,stderr=err,start_new_session=True)
            q.save(self.directory/'client-ownership.json',q.process_identity(self.client.pid))
            until=time.monotonic()+count/5+12
            try:
                while self.client.poll() is None:
                    self.guard()
                    if time.monotonic()>until: raise TimeoutError('bounded forensic client drain')
                    time.sleep(.25)
                if self.client.returncode: raise ValueError('forensic client exited with failure')
            finally:
                if self.client.poll() is None: q.bridge.stop_known(self.client)
        after=time.monotonic_ns(); value=q.read(out)
        q.save(self.directory/(prefix+'-bounds.json'),dict(launch_before_ns=before,exit_after_ns=after))
        return value


def validate_anchor(value,before,after):
    if not before<=value['MonotonicBeforeNs']<=value['MonotonicAfterNs']<=after:
        raise ValueError('client monotonic origin lies outside supervisor bounds')


class Sampler:
    def __init__(self,group):
        self.group=group; self.rows=[]; self.error=None; self.stop_event=threading.Event()
        self.thread=threading.Thread(target=self.loop,daemon=True)

    def loop(self):
        try:
            while not self.stop_event.is_set():
                if len(self.rows)>=PROTOCOL['counter_sample_cap']: raise ValueError('counter sample cap')
                before=time.monotonic_ns(); stat=q.fixtures.stat(self.group); after=time.monotonic_ns()
                self.rows.append(dict(before_ns=before,after_ns=after,cpu_stat=stat))
                self.stop_event.wait(PROTOCOL['counter_interval_sec'])
        except Exception as exc: self.error=str(exc); self.stop_event.set()

    def start(self): self.thread.start()

    def stop(self,path):
        self.stop_event.set(); self.thread.join(timeout=3)
        q.save(path,dict(interval_sec=.004,rows=self.rows,error=self.error))
        if self.thread.is_alive() or self.error: raise ValueError('counter sampler unavailable: '+str(self.error))


def export_preserved(service,path,expected):
    until=time.monotonic()+3
    while True:
        service.guard(); body,_=q.fetch(service.base,'qualification/events'); value=json.loads(body)
        q.save(path,value)
        if len(value['Records'])>=expected: return value
        if time.monotonic()>until: raise ValueError('incomplete raw server records retained')
        time.sleep(.05)


def counter_changes(samples,clients):
    changes=[]
    for previous,current in zip(samples,samples[1:]):
        delta=current['cpu_stat']['nr_throttled']-previous['cpu_stat']['nr_throttled']
        if delta<0: raise ValueError('throttle counter regressed')
        if not delta: continue
        low=previous['before_ns']; high=current['after_ns']; overlap=[]
        for phase,client in clients.items():
            for row in client['Rows']:
                if row['DispatchNs']<0 or row['BodyDoneNs']<0: continue
                begin_low=client['MonotonicBeforeNs']+row['DispatchNs']
                begin_high=client['MonotonicAfterNs']+row['DispatchNs']
                end_low=client['MonotonicBeforeNs']+row['BodyDoneNs']
                end_high=client['MonotonicAfterNs']+row['BodyDoneNs']
                if low<=end_high and high>=begin_low:
                    overlap.append(dict(phase=phase,id=row['ID'],
                        relation='update_interval_inside_request' if low>=begin_high and high<=end_low else 'possible_overlap'))
        changes.append(dict(update_interval_ns=[low,high],nr_throttled_delta=delta,
            throttled_usec_delta=current['cpu_stat']['throttled_usec']-previous['cpu_stat']['throttled_usec'],
            request_window_overlaps=overlap))
    return changes


def output_hash():
    path=q.BASE/'functional/attempt-03/summary.json'
    return q.read(path)['rows'][0]['body_sha256']


def functional():
    q.verify(); directory=BASE/'functional'; directory.mkdir()
    os.sched_setaffinity(0,{0,1}); service=Service(directory,'observed',False); sampler=None
    try:
        service.start(); sampler=Sampler(service.group); sampler.start()
        client=service.collect('functional',4)
        sampler.stop(directory/'counter-timeline.json'); sampler=None
        server=export_preserved(service,directory/'events.json',4)
        bounds=q.read(directory/'functional-bounds.json')
        validate_anchor(client,bounds['launch_before_ns'],bounds['exit_after_ns'])
        result=q.validate_client(client,'functional',4,output_hash()); result.update(q.join_records(client,server))
        if len(server['Records'])!=4: raise ValueError('functional server count differs')
        q.save(directory/'result.json',dict(passed=True,**result,scientific_collection=False))
    except BaseException as exc:
        q.save(directory/'failure.json',dict(error=str(exc))); raise
    finally:
        if sampler is not None:
            try: sampler.stop(directory/'counter-timeline.json')
            except Exception as exc: q.save(directory/'sampler-failure.json',dict(error=str(exc)))
        service.close()
    print('Forensic client anchors, image output and raw joins verified.')


def seal():
    q.verify()
    if not q.read(BASE/'functional/result.json')['passed'] or q.read(BASE/'functional/cleanup.json')['errors']:
        raise ValueError('forensic functional qualification incomplete')
    paths=[ROOT/n for n in FILES]+[BASE/'protocol.json',q.BASE/'bundle-seal.json']
    paths.extend(p for p in SOFTWARE.iterdir() if p.is_file())
    paths.extend(p for p in (BASE/'functional').rglob('*') if p.is_file())
    value=dict(protocol=PROTOCOL,files_sha256={str(p.relative_to(ROOT)):q.prep.sha(p) for p in paths})
    with (BASE/'bundle-seal.json').open('x') as f: json.dump(value,f,indent=2); f.write('\n')
    print('Single forensic probe sealed; original pilot remains stopped.')


def verify():
    q.verify(); value=q.read(BASE/'bundle-seal.json')
    if value['protocol']!=PROTOCOL: raise ValueError('forensic protocol differs')
    for name,digest in value['files_sha256'].items():
        if q.prep.sha(ROOT/name)!=digest: raise ValueError('forensic sealed input changed: '+name)


def run():
    verify(); q.desktop_absent(); os.sched_setaffinity(0,{0,1})
    directory=BASE/'run'; directory.mkdir()
    started=time.monotonic(); service=None; sampler=None; clients={}; windows={}
    try:
        import leftover_observer_review as observer
        path=ROOT/'analysis/runtime_io_leftover_observer_audit'/('imgproxy-probe-'+str(time.time_ns())+'.json')
        q.cmd(['sudo','-n',sys.executable,'-B',str(ROOT/'diagnostic/leftover_observer_audit.py'),'--output',str(path)],timeout=60)
        inventory=q.read(path)
        if not inventory['assessment']['clear_snapshot'] and not observer.review(path)['performance_eligible']:
            raise ValueError('observer inventory not eligible')
        q.save(directory/'observer-inventory.json',dict(path=str(path),sha256=q.prep.sha(path)))
        time.sleep(10)
        if time.monotonic()-started+120>PROTOCOL['total_sec']-PROTOCOL['cleanup_reserve_sec']:
            raise TimeoutError('forensic total active budget exhausted before service creation')
        service=Service(directory/'service','observed',True); service.directory.mkdir(); service.start()
        sampler=Sampler(service.group); sampler.start()
        print('Forensic probe: 40 seconds idle, then warmup and 40 seconds at the original 5 req/s.',flush=True)
        before=q.fixtures.stat(service.group); idle_start=time.monotonic_ns()
        until=time.monotonic()+40
        while time.monotonic()<until: service.guard(); time.sleep(.25)
        windows['idle']=dict(before=before,after=q.fixtures.stat(service.group),start_ns=idle_start,end_ns=time.monotonic_ns())
        print('Idle window complete; collecting the unchanged image workload.',flush=True)
        clients['warmup']=service.collect('warmup',25)
        before=q.fixtures.stat(service.group); measured_start=time.monotonic_ns()
        clients['measurement']=service.collect('measurement',200)
        windows['measurement']=dict(before=before,after=q.fixtures.stat(service.group),start_ns=measured_start,end_ns=time.monotonic_ns())
        # Persist counters and the bounded raw server buffer before any data classification.
        q.save(directory/'windows.json',windows)
        sampler.stop(directory/'counter-timeline.json'); sampler=None
        server=export_preserved(service,directory/'events.json',225)
        for phase,client in clients.items():
            bounds=q.read(service.directory/(phase+'-bounds.json'))
            validate_anchor(client,bounds['launch_before_ns'],bounds['exit_after_ns'])
        timing={phase:q.validate_client(c,phase,25 if phase=='warmup' else 200,output_hash()) for phase,c in clients.items()}
        joined={phase:q.join_records(c,server) for phase,c in clients.items()}
        expected={r['ID'] for c in clients.values() for r in c['Rows']}
        if len(server['Records'])!=225 or {r['ID'] for r in server['Records']}!=expected: raise ValueError('forensic all-offer IDs differ')
        deltas={phase:{k:w['after'][k]-w['before'][k] for k in w['before']} for phase,w in windows.items()}
        if any(v<0 for d in deltas.values() for v in d.values()): raise ValueError('counter regression')
        timeline=q.read(directory/'counter-timeline.json')['rows']; changes=counter_changes(timeline,clients)
        maximum_gap=max(b['after_ns']-a['before_ns'] for a,b in zip(timeline,timeline[1:]))
        observed=any(d['nr_throttled']>0 for d in deltas.values()) or bool(changes)
        result=dict(status='throttling_observed' if observed else 'throttling_not_observed_in_this_probe',
            window_counter_deltas=deltas,client_timings=timing,paired_timings=joined,
            counter_changes=changes,counter_samples=len(timeline),maximum_sample_gap_ns=maximum_gap,
            scientific_collection=False,qualification_pass=False,causal_mechanism_established=False,
            caveat=PROTOCOL['caveat'])
        q.save(directory/'summary.json',result)
    except BaseException as exc:
        q.save(directory/'summary.json',dict(status='forensic_probe_unavailable',error=str(exc),
            scientific_collection=False,qualification_pass=False)); raise
    finally:
        if sampler is not None:
            try: sampler.stop(directory/'counter-timeline.json')
            except Exception as exc: q.save(directory/'sampler-failure.json',dict(error=str(exc)))
        if service is not None: service.close()
        q.save(directory/'lifetime.json',dict(elapsed_sec=time.monotonic()-started,protocol=PROTOCOL))
    q.save(directory/'evidence-seal.json',dict(files_sha256={str(p.relative_to(directory)):q.prep.sha(p)
        for p in sorted(directory.rglob('*')) if p.is_file()}))
    print('Forensic probe: '+result['status']+'. Original qualification remains unavailable.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=('prepare','functional','seal','verify','run')); args=p.parse_args()
    signal.signal(signal.SIGTERM,q.handle_signal); signal.signal(signal.SIGINT,q.handle_signal)
    globals()[args.phase]()
