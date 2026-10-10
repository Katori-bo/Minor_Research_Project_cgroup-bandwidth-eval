"""Offline composition, schedules, bounded inference, raw replay and lifecycle checks."""
import bisect
import copy
import itertools
import json
import math
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import v27r2_common as c
import v27r2_model as model
import v27r2_raw as raw
import v27r2_study as runner
import v27r2_verify as verify
import v27r2_service as service
import v24r3_counter as native


def client_fixture(cfg):
    rows=[];entries=[];jobs=[];handlers=[];start=1_000_000_000;last=0
    for i,t in enumerate(c.schedule(cfg)):
        entry=start+t+10_000;admit=entry+10_000
        worker=max(admit+1000,last)
        high=cfg['traffic_pattern']=='bursty' and t % 15_000_000_000>=10_000_000_000
        busy=high or worker>admit+1000
        processing=6_700_000 if busy else 4_550_000
        completion=worker+processing;last=completion
        resume=completion+1000;end=resume+10_000
        rows.append(dict(ID=i,ScheduledOffsetNs=t,Error='',StatusCode=200,TimedOut=False,
                         DispatchLagNs=1000,HeadersOffsetNs=100_000,EndToEndLatencyNs=end-start-t+1000,
                         CompletedOffsetNs=end-start+1000))
        entries.append(dict(id=i,entry_ns=entry,exit_ns=end+1,admitted=True))
        jobs.append(dict(id=i,admission_ns=admit,worker_start_ns=worker,completion_ns=completion,
                         processing_ns=processing,queue_wait_ns=worker-admit))
        handlers.append(dict(id=i,entry_ns=entry,admission_ns=admit,resume_ns=resume,
                             write_start_ns=resume+1,write_end_ns=end,handler_exit_ns=end+2,
                             post_work_wait_ns=1000,pre_admission_ns=10_000))
    anchors=[dict(label=f'{phase}_{i}',before_ns=t-100,after_ns=t+100,server_ns=t,generation=1)
             for phase,t in [('start',1000),('stop',70_000_000_000)] for i in range(3)]
    n=len(rows)
    client=dict(total_scheduled=n,requests=rows,total_completed=n,total_dispatched=n,
                total_success=n,total_503=0,total_errors=0,client_dropped=0,missed_arrivals=0,
                pattern=cfg['traffic_pattern'],duration_sec=cfg['duration_sec'],target_rate=cfg['rate'],
                burst_low_rate=cfg['burst_low'],burst_high_rate=cfg['burst_high'],burst_period_sec=15,
                burst_low_duration_sec=10,client_trace_enabled=True,clock_anchors=anchors,client_test_start_ns=start,
                elapsed_including_drain_sec=cfg['duration_sec']+1,client_cpu_usec=1000,
                dispatch_lag_summary={'p99_ms':.001})
    server=dict(runtime_variant='stock',runtime_capture=False,custom_recording=False,
                worker_yield=False,entry_protocol='all-outcomes-v1',workers=1,gomaxprocs=1,
                queue_cap=128,go_version='go1.26.1',instrument=True,active_handlers=0,queue_len=0,
                completed=n,admitted=n,rejected=0,events=jobs,handler_events=handlers,
                entry_events=entries,clock_generation=1)
    return client,server


def fixture(index=0):
    cfg=c.matrix()[index];client,server=client_fixture(cfg)
    derived=dict(clocks=dict(client_test_start_ns=1_000_000_000,server_minus_client_lower_ns=-100,
                            server_minus_client_upper_ns=100),
                 summary=dict(cpu_usec_per_completed_work=3600 if cfg['low_rate']==15 else 3780,
                              timely_500_fraction=.98,failure_fraction=0,warmup_all_successful=True))
    anchors=[dict(label=f'{phase}_{i}',before_ns=10_000_000_000-1000+stamp,
                  after_ns=10_000_000_000+1000+stamp,server_ns=stamp,generation=1)
             for phase,stamp in [('start',0),('stop',70_000_000_000)] for i in range(3)]
    jobs=server['events'];starts=[j['worker_start_ns'] for j in jobs];cost=[];totals=[0]
    for j in jobs:
        cost.append(j['processing_ns']/1000*(.5 if j['processing_ns']==6_700_000 else 1))
        totals.append(totals[-1]+cost[-1])
    def usage(t):
        i=bisect.bisect_right(starts,t)-1
        if i<0:return 10_000_000
        fraction=min(1,max(0,(t-starts[i])/jobs[i]['processing_ns']))
        return 10_000_000+round(totals[i]+fraction*cost[i])
    samples=[]
    for i in range(3401):
        host=8_000_000_000+i*20_000_000;server_time=host-10_000_000_000
        u=usage(server_time)
        throttle=sum(max(0,min(50,math.floor((server_time/1e9-1-(10+15*k))*10))) for k in range(4))
        samples.append(dict(before_ns=host-500,after_ns=host+500,scheduled_ns=host-500,
                            thread_cpu_before_ns=i*1000,thread_cpu_after_ns=i*1000+500,
                            read_errno=0,cpu_stat=dict(usage_usec=u,user_usec=u-1000,system_usec=1000,nr_throttled=throttle)))
    probe=dict(schema=3,sampler_revision='v24r3-native',cadence='absolute_skip_missed',
               record_capacity=6000,raw_capacity=4096,skipped_deadlines=0,
               thread_cpu_started_ns=0,thread_cpu_finished_ns=10_000_000,
               path='/owned/cpu.stat',interval_sec=.02,duration_bound_sec=110,affinity=[0,1],
               failure=None,own_cpu_ns=10_000_000,started_ns=samples[0]['before_ns'],
               finished_ns=samples[-1]['after_ns'],samples=samples,pid=123,uid=1000)
    return cfg,derived,server,anchors,probe


def evaluate(index=0):
    cfg,d,s,a,p=fixture(index)
    return model.trial(d,s,a,p if cfg['counter_probe'] else None,cfg,c.design(),'/owned/cpu.stat')


def all_rows():return [evaluate(i) for i in range(16)]


class V27r2Tests(unittest.TestCase):
    def test_balanced_order_and_both_pair_directions(self):
        cfgs=c.matrix();self.assertEqual(len(cfgs),16)
        for rate,on in itertools.product((15,30),(False,True)):
            rows=[r for r in cfgs if r['low_rate']==rate and r['counter_probe']==on]
            self.assertEqual(sorted((r['order']-1)%4 for r in rows),[0,1,2,3])
        for on in (False,True):
            directions=[]
            for block in range(1,5):
                a=next(r for r in cfgs if r['block']==block and r['low_rate']==15 and r['counter_probe']==on)
                b=next(r for r in cfgs if r['block']==block and r['low_rate']==30 and r['counter_probe']==on)
                directions.append(a['order']<b['order'])
            self.assertEqual(sum(directions),2)

    def test_every_offset_against_integer_oracle_and_identical_high_work(self):
        high=[]
        for rate in (15,30):
            cfg=next(r for r in c.matrix() if r['low_rate']==rate)
            expected=[]
            for k in range(4):
                expected += [k*15_000_000_000+(2*i*1_000_000_000+rate)//(2*rate) for i in range(10*rate)]
                expected += [k*15_000_000_000+10_000_000_000+(2*i*5_000_000_000+849)//(2*849) for i in range(849)]
            self.assertEqual(c.schedule(cfg),expected)
            self.assertEqual(len(expected),3996 if rate==15 else 4596)
            high.append([t for t in expected if t%15_000_000_000>=10_000_000_000])
            warm=c.warmup_config(cfg)
            self.assertEqual(c.schedule(warm),[(2*i*1_000_000_000+rate)//(2*rate) for i in range(20*rate)])
        self.assertEqual(high[0],high[1]);self.assertEqual(len(high[0]),3396)

    def test_functional_full_cycle_and_cancellation(self):
        cfgs=c.functional_configs();self.assertEqual(len(cfgs),4)
        for cfg in cfgs:
            c.validate_config(cfg,True)
            if cfg['timeout_sec']>=1:
                self.assertEqual(cfg['duration_sec'],15)
                self.assertTrue(any(t>=10_000_000_000 for t in c.schedule(cfg)))
            else:self.assertEqual(cfg['duration_sec'],2)
        for changed in ({'counter_probe':1},{'low_rate':20},{'burst_low_duration_sec':5}):
            with self.assertRaises(ValueError):c.validate_config(dict(c.matrix()[0],**changed))

    def test_client_build_binary_exports_match_all_frozen_vectors(self):
        c.verify_client_build()
        for cfg in c.matrix():
            for label,config in [('measurement',cfg),('warmup',c.warmup_config(cfg))]:
                self.assertEqual(c.read(c.CLIENT_BUILD/f'schedule_exports/rate{cfg["low_rate"]}_{label}.json'),c.schedule(config))

    def test_supported_full_screen_and_no_universal_claim(self):
        result=model.report(all_rows(),c.design())
        self.assertEqual(result['decision'],'composition_screen_supported')
        self.assertTrue(result['composition_screen_pass'])
        self.assertFalse(result['equivalence_established']);self.assertFalse(result['novelty_established'])

    def test_absent_effect_and_large_busy_change(self):
        rows=all_rows()
        for r in rows:r['whole_cpu_usec_per_job']=3600
        self.assertEqual(model.report(rows,c.design())['decision'],'composition_effect_below_target')
        rows=all_rows()
        for r in rows:
            if r['low_rate']==30:
                r['busy_capacity_rps']*=1.04;r['busy_capacity_bounds_rps']=[x*1.04 for x in r['busy_capacity_bounds_rps']]
        self.assertEqual(model.report(rows,c.design())['decision'],'busy_capacity_changed_materially')

    def test_small_busy_mean_with_wide_uncertainty_is_inconclusive(self):
        rows=all_rows()
        for r in rows:
            if r['low_rate']==30:
                scale=1+[-.018,.018,-.018,.018][r['block']-1]
                r['busy_capacity_rps']*=scale;r['busy_capacity_bounds_rps']=[x*scale for x in r['busy_capacity_bounds_rps']]
        result=model.report(rows,c.design())
        self.assertFalse(result['busy_stability_screen_pass']);self.assertFalse(result['composition_screen_pass'])
        self.assertEqual(result['decision'],'composition_inconclusive')

    def test_observer_treatment_interaction_not_just_grand_mean(self):
        rows=all_rows()
        for r in rows:
            if r['counter_probe'] and r['low_rate']==30:r['whole_cpu_usec_per_job']*=1.05
        result=model.report(rows,c.design())
        self.assertTrue(result['cost_screen_pass']);self.assertFalse(result['observer_interaction_screen_pass'])
        self.assertEqual(result['decision'],'observer_interaction_unresolved')

    def test_cost_direction_and_heterogeneity_cannot_be_hidden(self):
        rows=all_rows()
        for r in rows:
            if r['low_rate']==30:r['whole_cpu_usec_per_job']*=.9
        result=model.report(rows,c.design());self.assertFalse(result['cost_screen_pass'])
        self.assertEqual(result['decision'],'composition_effect_below_target')
        rows=all_rows()
        for r in rows:
            if r['low_rate']==30:r['whole_cpu_usec_per_job']*= [1.08,1.08,1.08,.91][r['block']-1]
        self.assertFalse(model.report(rows,c.design())['composition_screen_pass'])

    def test_state_and_unsuccessful_cohorts_are_completed_failures(self):
        for field in ('busy_queue_eligible','cohort_all_successful'):
            rows=all_rows();rows[0][field]=False
            result=model.report(rows,c.design())
            self.assertTrue(result['complete']);self.assertTrue(result['recording_quality_pass'])
            self.assertEqual(result['decision'],'mixed_state_qualification_failed' if field=='busy_queue_eligible' else 'cohort_outcomes_ineligible')
        rows=all_rows();next(r for r in rows if r['counter_probe'])['phases']['low']['state_eligible']=False
        self.assertEqual(model.report(rows,c.design())['decision'],'mixed_state_qualification_failed')

    def test_incomplete_no_receipt_duplicate_foreign_and_identity(self):
        rows=all_rows()
        for selected,receipt in [(rows[:-1],True),(rows,False),([],False)]:
            self.assertEqual(model.report(selected,c.design(),receipt)['decision'],'composition_incomplete')
        with self.assertRaisesRegex(ValueError,'duplicate'):model.report(rows+[rows[0]],c.design())
        rows[0]['trial']='foreign'
        with self.assertRaisesRegex(ValueError,'foreign'):model.report(rows,c.design())
        rows=all_rows();rows[0]['low_rate']=20
        with self.assertRaisesRegex(ValueError,'identity'):model.report(rows,c.design())

    def test_interval_encloses_every_vertex_and_internal_point(self):
        bounds=[[3,4],[4,4.1],[2,3],[4.2,4.4]]
        out=model.interval_summary(bounds,3.182446305284263)
        for values in list(itertools.product(*bounds))+[[3.5,4.05,2.5,4.3]]:
            import statistics as st
            half=3.182446305284263*st.stdev(values)/2
            self.assertLessEqual(out['model_based_95_interval'][0],st.mean(values)-half+1e-12)
            self.assertGreaterEqual(out['model_based_95_interval'][1],st.mean(values)+half-1e-12)
        for bad in (bounds[:-1],[[4,3]]*4,[[float('nan'),4]]*4):
            with self.assertRaises(ValueError):model.interval_summary(bad,3.182446305284263)

    def test_missing_throttle_and_queue_two_fail_low_state(self):
        index=next(i for i,r in enumerate(c.matrix()) if r['counter_probe'])
        cfg,d,s,a,p=fixture(index)
        for x in p['samples']:x['cpu_stat'].pop('nr_throttled')
        row=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertFalse(row['phases']['low']['state_eligible']);self.assertTrue(row['recording_quality_pass'])
        cfg,d,s,a,p=fixture(index)
        job=next(j for j in s['events'] if 4_000_000_000<j['admission_ns']<5_000_000_000)
        following=s['events'][job['id']+1];following['admission_ns']=job['admission_ns']
        self.assertFalse(model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')['phases']['low']['state_eligible'])

    def test_clock_gap_coverage_path_and_bound_quality(self):
        index=next(i for i,r in enumerate(c.matrix()) if r['counter_probe'])
        cfg,d,s,a,p=fixture(index);p['samples']=[r for r in p['samples'] if not 14e9<r['before_ns']<14.15e9]
        with self.assertRaisesRegex(ValueError,'gap'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        cfg,d,s,a,p=fixture(index);p['samples']=[r for r in p['samples'] if r['before_ns']>13e9]
        with self.assertRaisesRegex(ValueError,'enclosing'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        cfg,d,s,a,p=fixture(index);a[-1]['server_ns']+=2_000_000
        with self.assertRaises(ValueError):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        cfg,d,s,a,p=fixture(index)
        with self.assertRaisesRegex(ValueError,'identity'):model.trial(d,s,a,p,cfg,c.design(),'/foreign')
        design=copy.deepcopy(c.design());design['measurement_quality']['max_cost_relative_bound_width']=.00001
        with self.assertRaisesRegex(ValueError,'uncertainty'):model.trial(d,s,a,p,cfg,design,'/owned/cpu.stat')

    def test_off_no_counters_and_warmup_failure_ineligible(self):
        cfg,d,s,a,p=fixture();cfg=dict(cfg,counter_probe=False)
        with self.assertRaisesRegex(ValueError,'off trial'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        d['summary']['warmup_all_successful']=False
        self.assertFalse(model.trial(d,s,a,None,cfg,c.design(),'/owned/cpu.stat')['cohort_all_successful'])

    def test_all_offer_join_and_asymmetric_phase_labels(self):
        for rate in (15,30):
            cfg=next(r for r in c.matrix() if r['low_rate']==rate)
            client,server=client_fixture(cfg);rows,_,_=raw.join(client,server,cfg)
            self.assertEqual(sum(r['phase']=='high' for r in rows),3396)
            self.assertEqual(sum(r['phase']=='low' for r in rows),40*rate)
            client['requests'][0]['ScheduledOffsetNs']+=1
            with self.assertRaisesRegex(ValueError,'offsets'):raw.join(client,server,cfg)

    def test_dispatch_failures_but_service_outcomes_not_retried(self):
        client,_=client_fixture(c.matrix()[0])
        client['total_503']=1;client['total_errors']=1;c.technical_client(client)
        for key,value in [('client_dropped',1),('missed_arrivals',1),('dispatch_lag_summary',{'p99_ms':2.01})]:
            bad=copy.deepcopy(client);bad[key]=value
            with self.assertRaises(ValueError):c.technical_client(bad)

    def test_owned_cleanup_and_no_resume(self):
        with patch.object(service,'owned_inspect',side_effect=[dict(Id='immutable'),None]),patch.object(service,'command') as command:
            service.remove_owned('name','owner');command.assert_called_once_with(['docker','rm','-f','immutable'],timeout=20)
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'measurement_lifetime.json',{})
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),\
                 patch.object(runner.run.old,'check_topology'),patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'start_watchdog') as start:
                with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.foreground(session)
                start.assert_not_called()

    def test_one_retry_then_second_failure_and_cleanup_stop(self):
        cfg=c.matrix()[0]
        for twice,cleanup_error in [(False,False),(True,False),(True,True)]:
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);c.save(session/'preparation/manifest.json',{});calls=[]
                def collect(s,d,actual,mode):
                    calls.append(actual);d.mkdir(parents=True)
                    c.save(d/'cleanup.json',dict(errors=['owned'] if cleanup_error else [],watchdog_intervened=False))
                    if twice or len(calls)==1:raise ValueError('technical fixture')
                    c.save(d/'complete.json',dict(valid=True))
                with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),\
                     patch.object(verify,'verify_environment'),patch.object(verify,'verify_trial'),patch.object(runner,'collect',side_effect=collect):
                    if twice:
                        with self.assertRaises(ValueError):runner.collect_slot(session,cfg)
                    else:runner.collect_slot(session,cfg)
                self.assertEqual(len(calls),1 if cleanup_error else 2)
                self.assertTrue(all(x==cfg for x in calls))

    def test_sixteen_slots_replay_after_watchdog_disarmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);collected=[]
            def watcher(s,phase,seconds):
                self.assertEqual((phase,seconds),('measurement',5400))
                c.save(s/'measurement_lifetime.json',dict(started_monotonic=0,deadline_monotonic=1e12))
                return types.SimpleNamespace(),(s/'watch.log').open('w')
            def replay(argv,timeout):
                self.assertEqual(argv[2],'analyze');self.assertEqual(timeout,600)
                self.assertTrue((session/'measurement_finished.json').exists());self.assertTrue(stop.called)
                self.assertEqual(c.read(session/'collection_receipt.json')['completed_slots'],16)
                return types.SimpleNamespace(returncode=0)
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),\
                 patch.object(runner.run.old,'check_topology'),patch.object(runner,'bind_observer_inventory'),\
                 patch.object(runner,'environment'),patch.object(runner.os,'sched_setaffinity'),\
                 patch.object(runner,'start_watchdog',side_effect=watcher),patch.object(runner,'collect_slot',side_effect=lambda s,cfg:collected.append(cfg['trial'])),\
                 patch.object(runner.fixtures,'stop') as stop,patch.object(runner.subprocess,'run',side_effect=replay):runner.foreground(session,Path('/unused'))
            self.assertEqual(collected,[r['trial'] for r in c.matrix()])

    def test_valid_scientific_failure_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'preparation/manifest.json',{})
            def collect(s,d,cfg,mode):
                d.mkdir(parents=True);c.save(d/'complete.json',dict(valid=True));c.save(d/'phase_accounting.json',dict(state_eligible=False))
            with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),\
                 patch.object(verify,'verify_environment'),patch.object(verify,'verify_trial'),patch.object(runner,'collect',side_effect=collect) as call:
                runner.collect_slot(session,c.matrix()[0]);self.assertEqual(call.call_count,1)

    def test_counter_decoding_drain_and_off_presence(self):
        index=next(i for i,r in enumerate(c.matrix()) if r['counter_probe']);cfg,_,_,_,p=fixture(index)
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);trial=session/'trial';trial.mkdir()
            document=copy.deepcopy(p);document['samples']=[{**{k:v for k,v in row.items() if k!='cpu_stat'},
                'raw':''.join(f'{k} {v}\n' for k,v in row['cpu_stat'].items())} for row in p['samples']]
            c.save(trial/'counter.raw.json',document);decoded=native.decode(document);decoded['raw_sha256']=c.digest(trial/'counter.raw.json')
            payload={'counter.json':decoded,'initial.json':dict(cgroup='/owned'),
                'counter_argv.json':[str(session/'preparation/counter'),'--path','/owned/cpu.stat','--output',str(trial/'counter.raw.json')],
                'observations.json':dict(measurement_stop=dict(after_ns=p['finished_ns']-1000)),
                'counter.ready.json':p['samples'][0],'counter_readiness.json':dict(token='READY',received_monotonic_ns=p['started_ns']+2000),
                'counter_process.json':dict(pid=123,uid=1000),'ownership.json':dict(owner=dict(uid=1000))}
            for name,value in payload.items():c.save(trial/name,value)
            self.assertEqual(verify.counter_input(session,trial,cfg),decoded)
            bad=copy.deepcopy(decoded);bad['samples'][10]['cpu_stat']['usage_usec']+=1;c.save(trial/'counter.json',bad)
            with self.assertRaisesRegex(ValueError,'decoding'):verify.counter_input(session,trial,cfg)
            c.save(trial/'counter.json',decoded);c.save(trial/'observations.json',dict(measurement_stop=dict(after_ns=p['finished_ns']+1)))
            with self.assertRaisesRegex(ValueError,'full drain'):verify.counter_input(session,trial,cfg)
            with self.assertRaisesRegex(ValueError,'off treatment'):verify.counter_input(session,trial,dict(cfg,counter_probe=False))

    def test_resealed_phase_tamper_fails_independent_replay(self):
        index=next(i for i,r in enumerate(c.matrix()) if r['counter_probe']);cfg,d,s,a,p=fixture(index);expected=evaluate(index)
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);trial=session/'trial';trial.mkdir()
            manifest={key:key for key in ('image','server_sha256','loadgen_sha256','gate_sha256')};manifest['resource_baseline']={}
            payload={'config.json':cfg,'complete.json':dict(valid=True,functional=False),'derived.json':d,'identity.json':manifest,
                     'initial.json':dict(resource_baseline={},cgroup='/owned'),'server_metrics.json':s,'host_server_anchors.json':a,
                     'environment.json':{},'warmup.json':{},'loadgen.json':{},'phase_accounting.json':expected}
            for name,value in payload.items():c.save(trial/name,value)
            c.save(session/'environment.json',{});c.seal(trial)
            with patch.object(verify.raw,'replay',return_value=d),patch.object(verify,'counter_input',return_value=p),patch.object(c,'technical_client'):
                verify.verify_trial(session,trial,manifest)
                altered=copy.deepcopy(expected);altered['phases']['low']['state_eligible']=False;c.save(trial/'phase_accounting.json',altered);c.seal(trial)
                with self.assertRaisesRegex(ValueError,'independent replay'):verify.verify_trial(session,trial,manifest)

    def test_completion_report_tamper_and_incomplete_after_exhausted_retry(self):
        for incomplete in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);values=[evaluate(i) for i in range(1 if incomplete else 16)];refs={}
                for row in values:
                    d=session/'slots'/row['trial']/'attempt-1';d.mkdir(parents=True)
                    c.save(d/'started.json',dict(monotonic_ns=1_000_000_000))
                    c.save(d/'complete.json',dict(finished_monotonic_ns=2_000_000_000))
                    refs[row['trial']]=dict(path=str(d.relative_to(session)),seal='mock-verified')
                if incomplete:
                    for i in (1,2):(session/'slots'/c.matrix()[1]['trial']/f'attempt-{i}').mkdir(parents=True)
                prep=session/'preparation';prep.mkdir();c.save(prep/'manifest.json',{});c.seal(prep)
                life=dict(started_monotonic=0,deadline_monotonic=5400,boot='same-boot')
                c.save(session/'measurement_lifetime.json',life)
                if not incomplete:
                    c.save(session/'collection_receipt.json',dict(life,completed_slots=16,collection_finished_monotonic=3))
                out=session/'analysis/one';out.mkdir(parents=True)
                saved=dict(result=model.report(values,c.design()),trial_refs=refs,trial_accounting=values,
                           preparation_seal=c.digest(prep/'seal.json'),
                           collection_receipt_sha256=None if incomplete else c.digest(session/'collection_receipt.json'),
                           measurement_lifetime_sha256=c.digest(session/'measurement_lifetime.json'),
                           technical_failures=[str(p.relative_to(session)) for p in runner.failures(session)])
                def save_report():
                    c.save(out/'report.json',saved);c.seal(out)
                    c.save(session/'latest_analysis.json',dict(path='analysis/one',seal=c.digest(out/'seal.json')))
                save_report()
                with patch.object(verify,'verify_preparation',return_value=dict(baseline=dict(boot_id='same-boot'))),\
                     patch.object(verify,'verify_environment'),patch.object(verify,'verify_observer'),\
                     patch.object(verify,'rows',return_value=(values,refs)):
                    result=verify.verify_completion(session)
                    self.assertEqual(result['decision'],'composition_incomplete' if incomplete else 'composition_screen_supported')
                    saved['trial_accounting']=[];save_report()
                    with self.assertRaisesRegex(ValueError,'raw replay'):verify.verify_completion(session)

    def test_complete_raw_replay_both_rates_and_monitor_budget(self):
        prior=c.read(c.PREVIOUS/c.read(c.PREVIOUS/'latest_analysis.json')['path']/'report.json')
        retained=c.PREVIOUS/prior['trial_refs']['low15_r1']['path'];c.verify_seal(retained)
        manifest=c.read(c.PREVIOUS/'preparation/manifest.json')
        for rate in (15,30):
            index=next(i for i,r in enumerate(c.matrix()) if r['counter_probe'] and r['low_rate']==rate)
            cfg=c.matrix()[index];client,server=client_fixture(cfg)
            warm_cfg=c.warmup_config(cfg);warm_client,warm_server=client_fixture(warm_cfg)
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);trial=session/'slots'/cfg['trial']/'attempt-1';trial.mkdir(parents=True)
                c.save(session/'preparation/manifest.json',manifest)
                initial=c.read(retained/'initial.json');container=c.read(retained/'container.json')
                identity=c.read(retained/'identity.json');identity['health']=server
                identity['loadgen_sha256']=c.digest(c.CLIENT_BUILD/'loadgen')
                initial['cgroup']='/owned';identity['process_identity_after_exec']=initial['process_identity']
                reset_health=copy.deepcopy(server);reset_health.update(completed=0,admitted=0,rejected=0,events=[],entry_events=[],handler_events=[])
                limits=initial['initial_limits'];observations={}
                n=len(client['requests'])
                for label,stamp,cpu in [('startup',8_000_000_000,1_000_000),
                                        ('measurement_start',10_900_000_000,2_000_000),
                                        ('measurement_stop',72_000_000_000,2_000_000+n*3600),
                                        ('final',72_100_000_000,2_000_100+n*3600)]:
                    observations[label]=dict(before_ns=stamp,after_ns=stamp+100,
                        cpu_stat=dict(usage_usec=cpu,user_usec=cpu-1000,system_usec=1000),limits=limits)
                anchors=[dict(label=f'{phase}_{i}',before_ns=10_000_000_000-100+stamp,
                    after_ns=10_000_000_000+100+stamp,server_ns=stamp,generation=1)
                    for phase,stamp in [('start',0),('stop',70_000_000_000)] for i in range(3)]
                def argv(name,config):
                    return [str(session/'preparation/loadgen'),'-url','http://127.0.0.1:1234/work?iterations=44000',
                        '-duration',str(config['duration_sec'])+'s','-rate',str(config['rate']),'-pattern',config['traffic_pattern'],
                        '-burst-low',str(config['burst_low']),'-burst-high',str(config['burst_high']),
                        '-burst-period','15s','-burst-low-duration','10s','-concurrency','512','-timeout',str(config['timeout_sec'])+'s',
                        '-trace-client=true','-output',str(trial/(name+'.json'))]
                for cl in (client,warm_client):cl['target_url']='http://127.0.0.1:1234/work?iterations=44000'
                payload={'config.json':cfg,'cleanup.json':dict(errors=[],container_removed=True,cgroup_removed=True,tracing_used=False,watchdog_intervened=False),
                    'initial.json':initial,'identity.json':identity,'container.json':container,'loadgen.json':client,'warmup.json':warm_client,
                    'server_metrics.json':server,'warmup_server_metrics.json':warm_server,'loadgen_argv.json':argv('loadgen',cfg),'warmup_argv.json':argv('warmup',warm_cfg),
                    'host_server_anchors.json':anchors,'reset.json':dict(health=reset_health),'settling.json':dict(accepted=True),'environment.json':dict(power_settings={}),
                    'monitor.json':[dict(chatgpt_present=False,process_cpu_deltas=[],power_settings={}) for _ in range(80)],
                    'observations.json':observations,'thread_snapshots.json':[dict(affinity=[2,4],cgroup='/owned',before_ns=10_000_000_000,after_ns=10_000_000_100,tids=[123])]}
                for name,value in payload.items():c.save(trial/name,value)
                shutil.copy2(c.ORIGINAL/'image.server',trial/'container.server')
                (trial/'qualification').mkdir();shutil.copy2(c.ORIGINAL/'gate',trial/'qualification/gate');c.seal(trial)
                derived=raw.replay(trial)
                self.assertEqual(derived['summary']['offered'],3996 if rate==15 else 4596)
                self.assertTrue(derived['summary']['warmup_all_successful'])
                self.assertAlmostEqual(derived['summary']['cpu_usec_per_completed_work'],3600)
                _,_,_,_,probe=fixture(index)
                row=model.trial(derived,server,anchors,probe,cfg,c.design(),'/owned/cpu.stat')
                self.assertTrue(row['phases']['low']['state_eligible']);self.assertTrue(row['busy_queue_eligible'])
                c.save(trial/'monitor.json',payload['monitor.json'][:79]);c.seal(trial)
                with self.assertRaisesRegex(ValueError,'monitor coverage'):raw.replay(trial)

    def test_missing_or_foreign_observer_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp)
            with self.assertRaisesRegex(ValueError,'root observer'):runner.bind_observer_inventory(session,None)
            with patch.object(verify.observer,'review',return_value=dict(boot_id='foreign')):
                with self.assertRaisesRegex(ValueError,'another boot'):runner.bind_observer_inventory(session,session/'audit.json')

    def test_sampler_off_cannot_supply_phase_counters_to_report(self):
        rows=all_rows();next(r for r in rows if not r['counter_probe'])['phases']={}
        with self.assertRaisesRegex(ValueError,'off trial'):model.report(rows,c.design())

    def test_original_client_report_is_rejected_missing_clocks(self):
        failed=c.FAILED/'preparation/functional/functional_rate15'
        client=c.read(failed/'loadgen.json');server=c.read(failed/'server_metrics.json');cfg=c.read(failed/'config.json')
        with self.assertRaisesRegex(ValueError,'missing required clock'):
            raw.join(client,server,cfg)

    def test_compiled_binary_json_replays_without_injected_fields(self):
        for pattern in ('steady','bursty'):
            d=c.CLIENT_BUILD/('compiled_report_'+pattern);c.verify_seal(d)
            receipt=c.read(d/'report.json');client=c.read(d/'loadgen.json')
            rows,mapping,logical=raw.join(client,c.read(d/'server_metrics.json'),c.read(d/'config.json'))
            self.assertEqual(len(rows),receipt['requests'])
            self.assertTrue(receipt['compiled_client_report_replay_passed'])
            self.assertEqual(receipt['clock_anchors'],6);self.assertFalse(receipt['clock_fields_injected'])
            self.assertEqual(receipt['binary_sha256'],c.digest(c.CLIENT_BUILD/'loadgen'))
            broken=copy.deepcopy(client);broken.pop('clock_anchors')
            with self.assertRaisesRegex(ValueError,'missing required clock'):
                raw.join(broken,c.read(d/'server_metrics.json'),c.read(d/'config.json'))

    def test_failed_generation_binary_report_has_no_clocks(self):
        failed=c.FAILED/'preparation/functional/functional_rate15'
        client=c.read(failed/'loadgen.json');identity=c.read(failed/'identity.json')
        self.assertEqual(identity['loadgen_sha256'],c.digest(c.FAILED/'bundle/loadgen'))
        self.assertEqual(client['total_success'],999)
        self.assertNotIn('clock_anchors',client);self.assertNotIn('client_test_start_ns',client)

    def test_scientific_design_unchanged_from_failed_generation(self):
        previous=c.read(c.ROOT/'analysis/runtime_io_v27_design/20261007/design.json')
        revised=copy.deepcopy(c.design())
        self.assertEqual(revised.pop('software_revision'),2)
        revised.pop('failed_generation_bundle_seal');revised.pop('failed_generation_preparation_seal')
        self.assertEqual(revised,previous)


if __name__=='__main__':unittest.main()
