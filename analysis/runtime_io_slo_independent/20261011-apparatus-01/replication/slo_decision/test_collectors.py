"""Run adapted retained collection paths with synthetic processes/services only."""
import ast
import copy
import json
import math
import os
from pathlib import Path
import signal
import sys
import time
import traceback
import tempfile
from types import SimpleNamespace as NS
import unittest

import collectors as a
import evaluation as e
import freeze_design as design

ROOT = Path(__file__).resolve().parents[2]
def functions(filename, names, namespace):
    tree=ast.parse((ROOT/'diagnostic'/filename).read_text())
    tree.body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(tree,filename,'exec'),namespace)
    return namespace


# Compile the retained validators directly, without importing analysis/plotting
# dependencies or loading any historical outcome. Scientific vectors are frozen.
frozen=ROOT/'analysis/runtime_io_slo_independent/20261011-v1-frozen'
go_design=a.read(frozen/'retained_go_design.json')
go_ns=functions('v31_common.py',{'validate_client','technical_client'},
    dict(schedule=design.go_vector,math=math))
go=NS(**go_ns, warmup_config=design.warmup_config,
      validation_configs=lambda:copy.deepcopy(go_design['validation_configs']))
input_sha='befb815ea245bd525f5e686b3507deab15819b7a43b5751a17d6e19396ae5625'
ng_ns=dict(require=e.require, PROTOCOL=dict(validation_intervals_ns=dict(A=250000000,B=166666667,C=125000000),
    validation_offers=300,warmup_offers=25,block_orders=design.ORDERS))
functions('nginx_prediction_common.py',{'config','configs'},ng_ns)
ng=NS(**ng_ns, n=NS(INPUT_SHA=input_sha,SOFTWARE=Path('/synthetic'),source_hashes=lambda:{}),
      read=a.read,save=lambda p,v:p.write_text(json.dumps(v)),sources=lambda:{})
ng_model=NS(**functions('nginx_prediction_model.py',{'outcomes'},dict(c=ng)))
drained=functions('nginx_qualify.py',{'drained'},dict())['drained']
go_study=NS(c=go)
nginx_study=NS(c=ng,model=ng_model)


def ng_client(cfg,prefix='measurement'):
    count=cfg['warmup_count'] if prefix=='warmup' else cfg['count']
    interval=cfg['interval_ns']
    return dict(Schema='nginx-client-v1',Count=count,IntervalNs=interval,Rows=[dict(
        ID=f'{prefix}-{i}',EchoID=f'{prefix}-{i}',ScheduledNs=i*interval,DispatchNs=i*interval+10,
        HeadersNs=i*interval+20,BodyDoneNs=i*interval+50,Error='',DecodeError='',Status=200,
        ContentEncoding='gzip',ContentType='application/x-ndjson',DecodedBytes=1048576,
        DecodedSHA256=input_sha,BodyBytes=100) for i in range(count)])


def go_client(cfg):
    offsets = design.go_vector(cfg)
    rows = [dict(ID=i, ScheduledOffsetNs=stamp, EndToEndLatencyNs=50,
                 CompletedOffsetNs=stamp+50, Error='', StatusCode=200)
            for i, stamp in enumerate(offsets)]
    return dict(total_scheduled=len(rows), requests=rows, client_dropped=0,
        total_completed=len(rows), total_dispatched=len(rows), total_success=len(rows),
        total_503=0, total_errors=0, missed_arrivals=0, dispatch_lag_summary=dict(p99_ms=0),
        pattern=cfg['traffic_pattern'], duration_sec=cfg['duration_sec'], target_rate=cfg['rate'],
        burst_low_rate=cfg['burst_low'], burst_high_rate=cfg['burst_high'],
        burst_period_sec=cfg['burst_period_sec'], burst_low_duration_sec=cfg['burst_low_duration_sec'],
        client_trace_enabled=True)


class Integration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.now = 100
        self.events, self.stopped = [], []
        self.fail_phase = None; self.bad_warmup = False; self.late = False
        self.boot_value = 'boot'

    def clock(self):
        self.now += 1
        return self.now

    def setup_adapter(self, app):
        self.app = app
        self.session = self.root / 'session'; self.session.mkdir()
        a.save(self.session / 'environment.json', dict(baseline_c={}, power_settings={}))
        self.cfgs = go.validation_configs() if app == 'Go' else ng.configs('validation')
        self.cfg = self.cfgs[0]; self.case = self.root / 'case'
        namespace = dict(vars(go_study if app == 'Go' else nginx_study),
                         os=os,Path=Path,signal=signal,traceback=traceback,math=math)
        self.reader = a.OfferReader(app, namespace)
        self.barrier = a.DurableBarrier(self.root / 'decisions', 'plan', 'campaign', 'boot', self.clock)
        self.hook = a.ForecastHook(self.barrier, self.reader, self.cfgs,
            a.CampaignBudget(app, 0, self.clock), lambda:self.boot_value,
            lambda p:self.stopped.append(p.pid), self.clock)
        self.barrier.freeze_calibration([50]*1600, [50], {'synthetic':True})
        test = self
        class Process:
            pid = 123; returncode = 0
            def poll(self): return self.returncode
        def popen(argv, **kwargs):
            phase = ('warmup' if '-output' in argv and Path(argv[-1]).name == 'warmup.json'
                     else 'loadgen') if app == 'Go' else argv[argv.index('--prefix')+1]
            test.events.append(phase)
            if phase != 'warmup':
                key = test.hook.key(test.cfg)
                test.assertTrue((test.barrier.directory / (key+'_permit.json')).exists())
                test.assertTrue((test.barrier.directory / (key+'_forecast.json')).exists())
                test.assertFalse((test.case / ('loadgen.json' if app=='Go' else 'measurement.json')).exists()
                                 and app == 'Go')
            raw = go_client(go.warmup_config(test.cfg) if phase=='warmup' else test.cfg) if app=='Go' else ng_client(test.cfg,phase)
            if test.bad_warmup and phase=='warmup':
                if app=='Go': raw['total_scheduled'] -= 1
                else: raw['Rows'][0]['DecodedSHA256']='corrupt'
            if app=='Go': a.save(Path(argv[-1]),raw)
            else: json.dump(raw,kwargs['stdout']); kwargs['stdout'].flush()
            if test.fail_phase == phase: raise RuntimeError('synthetic child failure')
            return Process()
        self.popen = popen
        fake_time = NS(monotonic_ns=self.clock, monotonic=lambda:self.clock()/1e9,
                       time=lambda:0, sleep=lambda _:None, time_ns=self.clock)
        namespace.update(subprocess=NS(Popen=popen, STDOUT=-2), time=fake_time)
        if app == 'Go':
            class Service:
                def __init__(self,*_): self.base='synthetic'; self.group=test.root
                def create(self): test.events.append('create')
                def release(self): test.events.append('release')
                def observe(self): return dict(after_ns=test.clock())
                def guard(self): pass
                def close(self,*_): test.events.append('close')
            class Monitor:
                def __init__(self,*_):pass
                def start(self,*_):pass
                def finish(self,*_):pass
                def stop(self):test.events.append('monitor_stop')
            common = NS(**vars(go))
            common.capacity=lambda _:None; common.seal=lambda _:None
            common.read=a.read;common.save=lambda p,v:p.write_text(json.dumps(v))
            common.matrix=lambda:self.cfgs
            common.process_identity=lambda pid:dict(pid=pid)
            common.design=lambda:{}
            namespace.update(Service=Service, HostMonitor=Monitor, c=common,
                power_settings=lambda **_: {}, analysis=NS(replay=lambda *_:{}),
                model=NS(trial=lambda *_:{}), fixtures=NS(stop=lambda p,*_:test.stopped.append(p.pid)),
                bridge=NS(anchors=lambda *_:[]))
            source = a.adapt_source((ROOT/'diagnostic/v31_study.py').read_text(), app)
        else:
            class BaseService:
                def __init__(self,directory,performance):
                    self.directory=directory;self.base='synthetic';self.group=test.root
                def start(self):test.events.append('create')
                def status(self):
                    return dict(active=1,reading=0,writing=1,waiting=0,
                        requests=10 if 'measurement' not in test.events else 311)
                def guard(self):return {}
                def close(self):test.events.append('close')
            q = NS(Service=BaseService,drained=drained,evidence_seal=lambda _:None,
                   identity=lambda _:None)
            namespace.update(q=q, h=NS(process_identity=lambda pid:{'pid':pid},
                fixtures=NS(stat=lambda _:dict(nr_throttled=0,throttled_usec=0,usage_usec=0)),
                bridge=NS(stop_known=lambda p:test.stopped.append(p.pid))))
            source = a.adapt_source((ROOT/'diagnostic/nginx_prediction_study.py').read_text(), app)
        self.ns = a.bind(source,namespace,self.hook)
        if app=='Go':
            self.ns.update(require_quiet_host=lambda:None,bounded_settle=lambda *_args,**_kw:None,
                           drain=lambda _:dict(),reset=lambda _:dict())
        return self.ns

    def run_trial(self):
        if self.app=='Go': return self.ns['collect'](self.session,self.case,self.cfg,'run')
        return self.ns['trial'](self.case,self.cfg,True)

    def test_actual_adapted_paths_seal_before_target_and_replay(self):
        for app in ('Go','NGINX'):
            with self.subTest(app=app):
                # Separate fixture identities/dirs for the second application.
                if app=='NGINX': self.tearDown();self.setUp()
                self.setup_adapter(app); self.run_trial()
                self.assertLess(self.events.index('warmup'),self.events.index('loadgen' if app=='Go' else 'measurement'))
                self.assertIn('close',self.events)
                scored = a.replay_window(self.barrier.directory,self.reader,self.cfg,self.case,'plan','campaign','boot')
                self.assertEqual(len(scored),6)
                self.assertFalse(any(s['score']['false_assurance'] for cell in scored for s in cell['methods'].values()))

    def test_no_calibration_blocks_target_service_and_warmup(self):
        for app in ('Go','NGINX'):
            if app=='NGINX': self.setUp()
            self.setup_adapter(app);del self.barrier.reference
            with self.assertRaises(ValueError):self.run_trial()
            self.assertEqual(self.events,[])

    def test_bad_warmup_blocks_target_and_closes_service(self):
        for app in ('Go','NGINX'):
            if app=='NGINX': self.setUp()
            self.setup_adapter(app);self.bad_warmup=True
            with self.assertRaises(ValueError):self.run_trial()
            self.assertIn('close',self.events)
            self.assertEqual(self.events.count('warmup'),1)
            self.assertNotIn('loadgen',self.events);self.assertNotIn('measurement',self.events)
            self.assertTrue((self.case / ('interruption.json' if app=='Go' else 'failure.json')).exists())

    def test_budget_exhausted_before_service_creation(self):
        self.setup_adapter('Go');self.now=12600*10**9
        with self.assertRaises(ValueError):self.run_trial()
        self.assertEqual(self.events,[])

    def test_boot_change_before_target_preserves_warmup_and_cleanup(self):
        self.setup_adapter('NGINX');self.boot_value='other'
        with self.assertRaises(ValueError):self.run_trial()
        self.assertEqual(self.events,['create','warmup','close'])
        self.assertTrue((self.case/'warmup.json').exists())

    def test_no_retry_after_failed_warmup_or_success(self):
        self.setup_adapter('NGINX');self.bad_warmup=True
        with self.assertRaises(ValueError):self.run_trial()
        self.bad_warmup=False;self.case=self.root/'another_case'
        with self.assertRaises(ValueError):self.run_trial()
        self.assertFalse(self.case.exists())

    def test_late_barrier_blocks_popen(self):
        self.setup_adapter('Go');self.hook.before_trial(self.case,self.cfg)
        self.case.mkdir();a.save(self.case/'warmup.json',go_client(go.warmup_config(self.cfg)))
        self.hook.warmup_ready(self.case,self.cfg);self.now+=10**9+1
        with self.assertRaises(ValueError):self.hook.spawn(self.case,self.cfg,'loadgen',self.popen,[])
        self.assertEqual(self.events,[])

    def test_release_failure_cleans_child_not_yet_received_by_load_loop(self):
        self.setup_adapter('NGINX')
        self.barrier.record_target_release=lambda *_:(_ for _ in ()).throw(ValueError('release failed'))
        with self.assertRaises(ValueError):self.run_trial()
        self.assertEqual(self.stopped,[123]);self.assertIn('close',self.events)
        self.assertTrue((self.case/'measurement.json').exists())

    def test_raw_mutation_and_receipt_mutation_fail_replay(self):
        self.setup_adapter('NGINX');self.run_trial()
        path=self.case/'warmup.json';path.write_text(path.read_text()+' ')
        with self.assertRaises(ValueError):a.replay_window(self.barrier.directory,self.reader,self.cfg,self.case,'plan','campaign','boot')

    def test_receipt_timing_mutation_fails_even_with_recomputed_hashes(self):
        self.setup_adapter('NGINX');self.run_trial();key=self.hook.key(self.cfg)
        path=self.barrier.directory/(key+'_release.json');value=a.read(path)
        value['target_spawn_before_ns']=0;path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):a.replay_window(self.barrier.directory,self.reader,self.cfg,self.case,'plan','campaign','boot')

    def test_retained_host_guard_failure_stops_owned_service(self):
        self.setup_adapter('Go')
        base=self.ns['Service']
        class GuardFailure(base):
            def observe(self):raise ValueError('synthetic host guard failed')
        self.ns['Service']=GuardFailure
        with self.assertRaises(ValueError):self.run_trial()
        self.assertNotIn('warmup',self.events);self.assertIn('close',self.events)
        self.assertIn('monitor_stop',self.events)

    def test_retained_load_timeout_stops_owned_child_and_service(self):
        self.setup_adapter('Go')
        class Hung:
            pid=123;returncode=None
            def poll(self):return None
        self.ns['subprocess'].Popen=lambda *_args,**_kw: Hung()
        elapsed=[0]
        def ticking():elapsed[0]+=10;return elapsed[0]
        self.ns['time'].monotonic=ticking
        with self.assertRaises(TimeoutError):self.run_trial()
        self.assertIn(123,self.stopped);self.assertIn('close',self.events)
        self.assertTrue((self.case/'interruption.json').exists())

    def test_foreign_configuration_cannot_start(self):
        self.setup_adapter('Go');self.cfg=dict(self.cfg,rate=6)
        with self.assertRaises(ValueError):self.run_trial()
        self.assertEqual(self.events,[])


class Extraction(unittest.TestCase):
    def test_go_failed_and_missing_offers_preserved(self):
        cfg=go.validation_configs()[0];raw=go_client(cfg)
        raw['requests'].pop();raw.update(client_dropped=1,total_completed=299,total_dispatched=299,total_success=298,total_errors=1)
        raw['requests'][0].update(Error='timeout',StatusCode=0)
        values=a.OfferReader('Go',vars(go_study)).values(raw,cfg)
        self.assertEqual(len(values),300);self.assertEqual(values.count(None),2)

    def test_nginx_transport_failure_is_miss_corruption_is_unavailable(self):
        cfg=ng.configs('validation')[0];raw=ng_client(cfg)
        raw['Rows'][0].update(Error='timeout',Status=0)
        reader=a.OfferReader('NGINX',vars(nginx_study))
        self.assertIsNone(reader.values(raw,cfg)[0])
        raw['Rows'][1]['DecodedSHA256']='wrong'
        with self.assertRaises(ValueError):reader.values(raw,cfg)

    def test_isolated_sources_exclude_campaign_and_retry_entry_points(self):
        for app,path in [('Go','v31_study.py'),('NGINX','nginx_prediction_study.py')]:
            source=a.adapt_source((ROOT/'diagnostic'/path).read_text(),app)
            names={n.name for n in ast.parse(source).body}
            self.assertFalse(names & {'campaign','main','collect_slot','run_group','prepare_runtime'})
            with self.assertRaises(ValueError):a.adapt_source('',app)


if __name__=='__main__':unittest.main()
