"""Offline forecast leakage, estimator, all-outcome and lifecycle regression tests."""
import copy
from contextlib import ExitStack
import math
from pathlib import Path
import shutil
import statistics as st
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import v28_common as c
import v28_model as model
import v28_raw as raw
import v28_study as runner
import v28_verify as verify
import v28_monitor_control as control
import test_v27r3 as retained_fixture
import test_v27r3_monitor as monitor_fixture


def calibration_rows():
    result=[]
    for cfg in c.calibration_configs():
        rate=cfg['low_rate'];kind=cfg['role'];wall=61 if kind=='mixed' else 30
        n=0 if kind=='idle' else len(c.schedule(cfg))
        cpu=.002*wall+.0033333333333333335*n
        row=dict(trial=cfg['trial'],role=kind,block=cfg['block'],order=cfg['order'],low_rate=rate,
            period_sec=cfg['burst_period_sec'],offers=n,completed=n,cpu_sec=cpu,accounted_wall_sec=wall,
            utilization=cpu/wall,throughput_rps=n/wall,throttled_periods=0,all_successful=True,
            miss_pct=None if kind=='idle' else 0,state_eligible=True,queue_peak=0 if kind!='mixed' else 80)
        if kind=='mixed':row.update(busy_capacity_rps=150,busy_capacity_bounds_rps=[149.9,150.1],whole_cpu_sec_per_job=cpu/n)
        result.append(row)
    return result


def validation_rows(cal,pred):
    return [dict(trial=cfg['trial'],role='validation',block=cfg['block'],order=cfg['order'],
        low_rate=cfg['low_rate'],period_sec=cfg['burst_period_sec'],all_successful=True,
        state_eligible=True,busy_capacity_rps=150,busy_capacity_bounds_rps=[149.9,150.1],
        miss_pct=pred['busy'][cfg['trial']]['miss_pct']) for cfg in c.validation_configs()]


def clock_anchors():
    return [dict(label=f'{phase}_{i}',before_ns=t-100,after_ns=t+100,server_ns=t,generation=1)
            for phase,t in (('start',1000),('stop',3_000_000_000)) for i in range(3)]


def idle_server():
    cfg=next(x for x in c.functional_configs() if x['role']=='steady')
    with patch.object(retained_fixture,'c',c):_,server=retained_fixture.client_fixture(cfg)
    server.update(completed=0,admitted=0,rejected=0,queue_len=0,active_handlers=0,
                  events=[],handler_events=[],entry_events=[])
    return server


class DesignTests(unittest.TestCase):
    def test_budget_independence_and_balanced_positions(self):
        configs=c.matrix();self.assertEqual(len(configs),32)
        self.assertEqual(len(c.calibration_configs()),16);self.assertEqual(len(c.validation_configs()),16)
        self.assertTrue(all(not x['counter_probe'] for x in configs))
        self.assertLess(max(x['order'] for x in c.calibration_configs()),min(x['order'] for x in c.validation_configs()))
        for low in (15,30):
            for p in (6,12):
                selected=[x for x in c.validation_configs() if x['low_rate']==low and x['burst_period_sec']==p]
                self.assertEqual(sorted((x['order']-17)%4 for x in selected),[0,1,2,3])
        block1=[(x['role'],x['low_rate']) for x in c.calibration_configs() if x['block']==1]
        block2=[(x['role'],x['low_rate']) for x in c.calibration_configs() if x['block']==2]
        self.assertEqual(block1,list(reversed(block2)))

    def test_exact_validation_offsets_against_integer_oracle(self):
        for cfg in c.validation_configs():
            p=cfg['burst_period_sec'];a=cfg['burst_low_duration_sec'];low=cfg['low_rate'];expected=[]
            for k in range(60//p):
                expected += [k*p*10**9+(2*i*10**9+low)//(2*low) for i in range(a*low)]
                expected += [k*p*10**9+a*10**9+(2*i*10**9+180)//360 for i in range((p-a)*180)]
            self.assertEqual(expected,c.schedule(cfg));self.assertEqual(len(expected),3600+40*low)
            self.assertEqual(sum(t%(p*10**9)>=a*10**9 for t in expected),3600)

    def test_idle_has_real_zero_offer_contract(self):
        cfg=next(x for x in c.calibration_configs() if x['role']=='idle')
        self.assertEqual(c.schedule(cfg),[]);self.assertEqual(c.schedule(c.warmup_config(cfg)),[])
        self.assertEqual(c.monitor_minimum(cfg),45)
        self.assertEqual(c.monitor_minimum(c.validation_configs()[0]),80)
        self.assertEqual(len(c.functional_configs()),6)
        with self.assertRaises(ValueError):c.validate_config(dict(cfg,counter_probe=True))


class EstimatorTests(unittest.TestCase):
    def test_linear_analytic_solution_and_idle_correction(self):
        rows=calibration_rows();cal=model.calibrate(rows,c.design());self.assertTrue(cal['usable'])
        self.assertAlmostEqual(cal['idle_cpu_rate'],.002)
        self.assertAlmostEqual(cal['methods']['regression']['capacity_rps'],149.4)
        self.assertAlmostEqual(cal['methods']['idle_corrected']['capacity_rps'],149.4)
        self.assertAlmostEqual(cal['methods']['quadratic']['capacity_rps'],149.4)
        self.assertEqual(cal['methods']['busy']['capacity_rps'],150)

    def test_negative_curvature_and_nonnegative_intercept(self):
        points=[(x,.01+.004*x-.000004*x*x) for x in (0,0,15,30,60,90,120)]
        result=model.regression(points,.5,True)
        self.assertEqual(result['status'],'available');self.assertLess(result['quadratic_sec2'],0)
        cap=result['capacity_rps'];self.assertAlmostEqual(.01+.004*cap-.000004*cap*cap,.5)
        result=model.regression([(x,-.01+.004*x) for x in (0,15,30,60,90,120)],.5)
        self.assertEqual(result['intercept'],0)

    def test_nonphysical_comparator_unavailable_without_capacity_clipping(self):
        for points in ([(x,.001*x) for x in (0,15,30,60)],[(x,0) for x in (0,15,30,60)]):
            result=model.regression(points,.5)
            self.assertEqual(result['status'],'unavailable')

    def test_calibration_failure_and_future_input_rejection(self):
        for key in ('state_eligible','all_successful'):
            rows=calibration_rows();rows[0][key]=False;cal=model.calibrate(rows,c.design())
            self.assertFalse(cal['usable']);self.assertEqual(cal['decision'],'calibration_qualification_failed')
        rows=calibration_rows();mixed=[x for x in rows if x['role']=='mixed'];mixed[0]['busy_capacity_rps']=170
        self.assertFalse(model.calibrate(rows,c.design())['busy_repeatability_pass'])
        with self.assertRaises(ValueError):model.calibrate(calibration_rows()[:-1],c.design())
        rows=calibration_rows();rows[0]['role']='validation'
        with self.assertRaisesRegex(ValueError,'validation data'):model.calibrate(rows,c.design())

    def test_same_fifo_all_methods_and_no_misleading_recovery_fields(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,per_id=model.forecast(cal,c.validation_configs())
        for method in model.METHODS:
            for cfg in c.validation_configs():
                rows=per_id[method][cfg['trial']];summary=pred[method][cfg['trial']]
                self.assertEqual(len(rows),len(c.schedule(cfg)))
                self.assertAlmostEqual(summary['miss_pct'],100*sum(not x['timely_500'] for x in rows)/len(rows))
                self.assertNotIn('recovery_mean_sec',summary)
        self.assertEqual(cal['methods']['regression']['fit_trial_ids'],cal['methods']['quadratic']['fit_trial_ids'])

    def test_comparator_adequacy_stops_superiority_route(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,_=model.forecast(cal,c.validation_configs())
        report=model.report(validation_rows(cal,pred),cal,pred,c.design(),True)
        self.assertEqual(report['decision'],'established_comparator_adequate');self.assertFalse(report['novelty_established'])

    def test_favorable_mean_cannot_hide_one_bad_busy_prediction(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,_=model.forecast(cal,c.validation_configs());rows=validation_rows(cal,pred)
        rows[0]['miss_pct']+=3.01
        self.assertEqual(model.report(rows,cal,pred,c.design(),True)['decision'],'busy_predictive_screen_failed')
        rows=validation_rows(cal,pred);rows[0]['busy_capacity_bounds_rps']=[140,141]
        self.assertEqual(model.report(rows,cal,pred,c.design(),True)['decision'],'busy_predictive_screen_failed')

    def test_scientific_failure_retained_and_incomplete_not_supported(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,_=model.forecast(cal,c.validation_configs());rows=validation_rows(cal,pred)
        for key in ('all_successful','state_eligible'):
            bad=copy.deepcopy(rows);bad[0][key]=False;report=model.report(bad,cal,pred,c.design(),True)
            self.assertTrue(report['complete']);self.assertEqual(report['decision'],'validation_state_or_cohort_failed')
        for selected,receipt in ((rows[:-1],True),(rows,False)):
            self.assertEqual(model.report(selected,cal,pred,c.design(),receipt)['decision'],'comparison_incomplete')
        with self.assertRaises(ValueError):model.report(rows+[rows[0]],cal,pred,c.design(),True)

    def test_advantage_requires_both_baselines_and_block_interval(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,_=model.forecast(cal,c.validation_configs());rows=validation_rows(cal,pred)
        for method in ('regression','quadratic'):
            cal['methods'][method]['capacity_rps']=110
            for cfg in c.validation_configs():pred[method][cfg['trial']]['miss_pct']=pred['busy'][cfg['trial']]['miss_pct']+5
        report=model.report(rows,cal,pred,c.design(),True)
        self.assertEqual(report['decision'],'busy_advantage_over_declared_comparators')
        for method in ('regression','quadratic'):
            for cfg in c.validation_configs():pred[method][cfg['trial']]['miss_pct']=pred['busy'][cfg['trial']]['miss_pct']+([5,5,5,.1][cfg['block']-1])
        self.assertEqual(model.report(rows,cal,pred,c.design(),True)['decision'],'predictive_advantage_inconclusive')
        cal['methods']['quadratic']=dict(status='unavailable',reason='fixture')
        self.assertEqual(model.report(rows,cal,pred,c.design(),True)['decision'],'established_comparator_unavailable')


class RawTests(unittest.TestCase):
    def test_real_sealed_client_json_clock_fields_not_injected(self):
        for kind in ('steady','bursty'):
            directory=c.CLIENT_BUILD/('compiled_report_'+kind)
            report=c.read(directory/'report.json');client=c.read(directory/'loadgen.json');server=c.read(directory/'server_metrics.json')
            cfg=c.read(directory/'config.json')
            cfg=dict(cfg,functional=True)
            self.assertFalse(report['clock_fields_injected'])
            rows,_,_=raw.join(client,server,cfg);self.assertEqual(len(rows),client['total_scheduled'])

    def test_new_schedule_all_offer_join_and_missing_clock_refusal(self):
        for cfg in c.functional_configs():
            if cfg['traffic_pattern']=='idle':continue
            with patch.object(retained_fixture,'c',c):client,server=retained_fixture.client_fixture(cfg)
            client.update(burst_period_sec=cfg['burst_period_sec'],burst_low_duration_sec=cfg['burst_low_duration_sec'])
            rows,_,_=raw.join(client,server,cfg);self.assertEqual(len(rows),len(c.schedule(cfg)))
            client.pop('clock_anchors')
            with self.assertRaisesRegex(ValueError,'clock anchors'):raw.join(client,server,cfg)

    def test_idle_zero_job_and_clock_failures(self):
        server=idle_server();receipt=dict(kind='zero_request_live_service',offers=0,requested_duration_sec=2,
            started_ns=1000,finished_ns=2_000_002_000,samples=[dict(before_ns=1000,after_ns=2000,health=server)])
        raw.idle_receipt(receipt,2,server);raw.idle_clock(clock_anchors(),1)
        receipt['samples'][0]['health']['admitted']=1
        with self.assertRaisesRegex(ValueError,'not empty'):raw.idle_receipt(receipt,2,server)
        anchors=clock_anchors();anchors[-1]['server_ns']+=2_000_000
        with self.assertRaises(ValueError):raw.idle_clock(anchors,1)

    def test_idle_full_asset_observation_replay(self):
        history=next((c.HISTORY/'slots').glob('*/attempt-*'))
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);cfg=next(x for x in c.functional_configs() if x['role']=='idle')
            for name in ('cleanup.json','initial.json','identity.json','container.json','container.server','thread_snapshots.json'):
                shutil.copy2(history/name,d/name)
            (d/'qualification').mkdir();shutil.copy2(history/'qualification/gate',d/'qualification/gate')
            c.save(d/'config.json',cfg);server=idle_server();c.save(d/'server_metrics.json',server)
            c.save(d/'host_server_anchors.json',clock_anchors())
            initial=c.read(d/'initial.json');obs={}
            for i,name in enumerate(('startup','measurement_start','measurement_stop','final')):
                t=[100,1000,2_000_004_000,2_000_005_000][i]
                obs[name]=dict(before_ns=t,after_ns=t+10,limits=initial['initial_limits'],cpu_stat=dict(usage_usec=i*100,nr_throttled=0))
            c.save(d/'observations.json',obs)
            c.save(d/'idle.json',dict(kind='zero_request_live_service',offers=0,requested_duration_sec=2,
                started_ns=1100,finished_ns=2_000_002_000,samples=[dict(before_ns=1100,after_ns=1200,health=server)]))
            c.seal(d);derived=raw.replay(d,True)
            self.assertTrue(derived['idle']);self.assertIsNone(derived['summary']['cpu_usec_per_completed_work'])
            row=model.trial(derived,server,[],None,cfg,c.design(),'unused');self.assertEqual(row['completed'],0)
            identity=c.read(d/'identity.json');identity['image']='changed';c.save(d/'identity.json',identity);c.seal(d)
            with self.assertRaisesRegex(ValueError,'image inspection differs'):raw.replay(d,True)

    def test_steady_throttle_failure_and_busy_unqualified_retained(self):
        cfg=next(x for x in c.calibration_configs() if x['role']=='steady' and x['low_rate']==15)
        with patch.object(retained_fixture,'c',c):client,server=retained_fixture.client_fixture(dict(cfg,functional=True))
        client.update(burst_period_sec=cfg['burst_period_sec'],burst_low_duration_sec=cfg['burst_low_duration_sec'])
        rows,mapping,logical=raw.join(client,server,dict(cfg,functional=True))
        observations=dict(measurement_start=dict(before_ns=0,after_ns=1,cpu_stat=dict(usage_usec=0,nr_throttled=0)),
            measurement_stop=dict(before_ns=30_000_000_000,after_ns=30_000_000_001,cpu_stat=dict(usage_usec=2_000_000,nr_throttled=0)))
        summary=raw.summarize(cfg,client,server,rows,mapping,logical,observations);summary['warmup_all_successful']=True
        derived=dict(summary=summary,clocks=mapping);row=model.trial(derived,server,[],None,cfg,c.design(),'unused')
        self.assertTrue(row['state_eligible']);summary['counter_window']['delta']['nr_throttled']=1
        self.assertFalse(model.trial(derived,server,[],None,cfg,c.design(),'unused')['state_eligible'])
        cfg=c.validation_configs()[0];row=model.trial(derived,server,[],None,cfg,c.design(),'unused')
        self.assertFalse(row['state_eligible'])


class LifecycleTests(unittest.TestCase):
    def test_foreground_freezes_between_roles_and_disarms_before_analysis(self):
        for qualified in (True,False):
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);events=[];collected=[]
                def watchdog(s,phase,seconds):
                    self.assertEqual((phase,seconds),('measurement',7200))
                    c.save(s/'measurement_lifetime.json',dict(started_monotonic=0,deadline_monotonic=1e12))
                    return types.SimpleNamespace(),(s/'watch.log').open('w')
                def freeze(s):
                    self.assertEqual(len(collected),16);self.assertTrue(all(x['role']!='validation' for x in collected))
                    events.append('freeze')
                    if qualified:
                        (s/'predictions').mkdir();c.save(s/'predictions/seal.json',{});return s/'predictions'
                    return None
                def collect(s,cfg):
                    if cfg['role']=='validation':self.assertIn('freeze',events)
                    collected.append(cfg)
                def replay(argv,timeout):
                    self.assertEqual(argv[3],'analyze');self.assertEqual(timeout,600)
                    self.assertTrue((session/'measurement_finished.json').exists());self.assertTrue(stop.called)
                    self.assertEqual(c.read(session/'collection_receipt.json')['completed_slots'],32 if qualified else 16)
                    return types.SimpleNamespace(returncode=0)
                contexts=[patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),
                    patch.object(runner.run.old,'check_topology'),patch.object(runner,'bind_observer_inventory'),
                    patch.object(runner,'environment'),patch.object(runner.os,'sched_setaffinity'),
                    patch.object(runner,'start_watchdog',side_effect=watchdog),patch.object(runner,'collect_slot',side_effect=collect),
                    patch.object(runner,'freeze_predictions',side_effect=freeze),patch.object(verify,'verify_predictions'),
                    patch.object(verify,'accepted',side_effect=lambda s,cfg:Path('/unused') if cfg in collected else None),
                    patch.object(runner.subprocess,'run',side_effect=replay)]
                with ExitStack() as stack:
                    for context in contexts:stack.enter_context(context)
                    stop=stack.enter_context(patch.object(runner.fixtures,'stop'))
                    runner.foreground(session,Path('/unused'))
                self.assertEqual(len(collected),32 if qualified else 16)

    def test_idle_collection_path_keeps_monitor_and_cleanup_order(self):
        events=[]
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);directory=session/'trial';cfg=next(x for x in c.calibration_configs() if x['role']=='idle')
            c.save(session/'environment.json',dict(power_settings={},baseline_c={}))
            class Service:
                group=Path('/sys/fs/cgroup/software-fixture');base='unused'
                def __init__(self,*args):pass
                def create(self):events.append('create')
                def release(self):events.append('release')
                def guard(self):pass
                def observe(self):return dict(before_ns=time.monotonic_ns(),after_ns=time.monotonic_ns())
                def close(self,*args):events.append('close')
            class Monitor:
                def __init__(self,*args):pass
                def start(self,*args):events.append('monitor_ready')
                def finish(self,*args):events.append('monitor_finish')
                def stop(self):events.append('monitor_stop')
            def load(d,s,seconds,name,*args):
                events.append(name);c.save(d/('warmup_idle.json' if name=='warmup' else 'idle.json'),{})
            contexts=[patch.object(runner,'Service',Service),patch.object(runner,'HostMonitor',Monitor),
                patch.object(runner,'require_quiet_host'),patch.object(runner,'update'),patch.object(runner,'bounded_settle'),
                patch.object(c,'capacity'),patch.object(runner,'power_settings',return_value={}),patch.object(runner,'load',side_effect=load),
                patch.object(runner,'drain',return_value={}),patch.object(runner,'reset',return_value={}),
                patch.object(runner.bridge,'anchors',return_value=[]),patch.object(runner.analysis,'replay',return_value={}),
                patch.object(runner.model,'trial',return_value={})]
            with ExitStack() as stack:
                for context in contexts:stack.enter_context(context)
                client=stack.enter_context(patch.object(c,'validate_client'))
                spawn=stack.enter_context(patch.object(runner.subprocess,'Popen'))
                runner.collect(session,directory,cfg,'run')
            self.assertLess(events.index('monitor_ready'),events.index('release'))
            self.assertLess(events.index('warmup'),events.index('loadgen'))
            self.assertLess(events.index('monitor_finish'),events.index('close'))
            client.assert_not_called();spawn.assert_not_called();self.assertTrue(c.read(directory/'complete.json')['valid'])

    def test_monitor_real_process_count_and_endpoint_agreement_both_durations(self):
        for cfg in (c.validation_configs()[0],next(x for x in c.calibration_configs() if x['role']=='idle')):
            with tempfile.TemporaryDirectory() as tmp:
                d=Path(tmp);c.save(d/'config.json',cfg)
                argv=[sys.executable,'-B',str(c.ROOT/'diagnostic/v27r3_monitor_fixture.py'),'.005','.003',
                    '--output',str(d/'monitor.json'),'--progress',str(d/'monitor_progress.json')]
                monitor=control.HostMonitor(d,lambda:None)
                try:
                    monitor.start('/unused',argv);start=time.monotonic_ns();end=time.monotonic_ns();monitor.finish(end)
                finally:monitor.stop()
                records=c.read(d/'monitor.json');control.validate(d,records,dict(power_settings={}),dict(startup=dict(before_ns=start),final=dict(after_ns=end)))
                self.assertGreaterEqual(len(records),c.monitor_minimum(cfg))

    def test_monitor_79_insufficient_and_coverage_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);c.save(d/'config.json',c.validation_configs()[0]);records,env,obs=monitor_fixture.fixture(d)
            control.validate(d,records,env,obs)
            with self.assertRaisesRegex(ValueError,'79 records'):control.validate(d,records[:79],env,obs)
            obs['final']['after_ns']=81_000_000_000
            with self.assertRaisesRegex(ValueError,'endpoint coverage'):control.validate(d,records,env,obs)

    def test_real_zero_request_capture_has_no_client_or_native_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);server=idle_server();cfg=next(x for x in c.functional_configs() if x['role']=='idle')
            service=types.SimpleNamespace(base='unused',observe=lambda:None)
            with patch.object(runner.bridge,'get',return_value=server),patch.object(runner,'update'),patch.object(runner.subprocess,'Popen') as spawn:
                runner.load(d,service,2,'loadgen',d,cfg)
            spawn.assert_not_called();self.assertFalse((d/'loadgen.json').exists())
            raw.idle_receipt(c.read(d/'idle.json'),2,server)

    def test_retry_budget_and_scientific_failure_no_replacement(self):
        cfg=c.matrix()[0]
        for twice,cleanup_error in ((False,False),(True,False),(True,True)):
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);c.save(session/'preparation/manifest.json',{});calls=[]
                def collect(s,d,actual,mode):
                    calls.append(actual);d.mkdir(parents=True)
                    c.save(d/'cleanup.json',dict(errors=['owned'] if cleanup_error else [],watchdog_intervened=False))
                    if twice or len(calls)==1:raise ValueError('technical fixture')
                    c.save(d/'complete.json',dict(valid=True))
                with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),patch.object(verify,'verify_environment'),patch.object(verify,'verify_trial'),patch.object(runner,'collect',side_effect=collect):
                    if twice:
                        with self.assertRaises(ValueError):runner.collect_slot(session,cfg)
                    else:runner.collect_slot(session,cfg)
                self.assertEqual(len(calls),1 if cleanup_error else 2)
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'preparation/manifest.json',{})
            def complete(s,d,actual,mode):
                d.mkdir(parents=True);c.save(d/'complete.json',dict(valid=True));c.save(d/'phase_accounting.json',dict(state_eligible=False))
            with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),patch.object(verify,'verify_environment'),patch.object(verify,'verify_trial'),patch.object(runner,'collect',side_effect=complete) as collect:
                runner.collect_slot(session,cfg);self.assertEqual(collect.call_count,1)

    def test_no_resume_and_no_freeze_after_validation_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'measurement_lifetime.json',{})
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'start_watchdog') as start:
                with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.foreground(session)
                start.assert_not_called()
            (session/'slots'/c.validation_configs()[0]['trial']/'attempt-fixture').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'before forecast freeze'):runner.freeze_predictions(session)

    def test_failed_calibration_stops_before_any_forecast_or_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);rows=calibration_rows();rows[0]['state_eligible']=False
            with patch.object(verify,'verify_preparation',return_value={}),patch.object(verify,'rows',return_value=(rows,{})):
                self.assertIsNone(runner.freeze_predictions(session))
            self.assertFalse((session/'predictions').exists());self.assertTrue((session/'calibration_review/seal.json').exists())

    def test_forecast_seals_reference_only_calibration_and_refuse_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'preparation/manifest.json',{});c.seal(session/'preparation')
            c.save(session/'environment_seal.json',{});rows=calibration_rows();refs={}
            for row in rows:
                d=session/'slots'/row['trial']/'attempt-fixture';d.mkdir(parents=True)
                cfg=next(x for x in c.calibration_configs() if x['trial']==row['trial'])
                c.save(d/'config.json',cfg);c.save(d/'phase_accounting.json',row)
                c.save(d/'complete.json',dict(valid=True,finished_monotonic_ns=time.monotonic_ns()));c.seal(d)
                refs[row['trial']]=dict(path=str(d.relative_to(session)),seal=c.digest(d/'seal.json'))
            with patch.object(verify,'verify_preparation',return_value={}),patch.object(verify,'rows',return_value=(rows,refs)),patch.object(verify,'verify_trial'):
                runner.freeze_predictions(session);verify.verify_predictions(session)
                manifest=c.read(session/'predictions/manifest.json');cfg=c.validation_configs()[0]
                d=session/'slots'/cfg['trial']/'attempt-early';c.save(d/'started.json',dict(monotonic_ns=manifest['frozen_monotonic_ns']-1))
                with self.assertRaisesRegex(ValueError,'preceded freeze'):verify.verify_predictions(session)
                c.save(d/'started.json',dict(monotonic_ns=manifest['frozen_monotonic_ns']+1))
                pred=c.read(session/'predictions/summary.json');pred['busy'][cfg['trial']]['miss_pct']+=1
                c.save(session/'predictions/summary.json',pred);c.seal(session/'predictions')
                with self.assertRaisesRegex(ValueError,'forecasts differ'):verify.verify_predictions(session)


if __name__=='__main__':unittest.main()
