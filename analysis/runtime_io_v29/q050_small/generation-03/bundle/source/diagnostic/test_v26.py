"""Offline low-load, raw-accounting, provenance, retry and lifecycle checks."""
import copy
import json
import tempfile
import types
import unittest
import shutil
from pathlib import Path
from unittest.mock import patch

import v26_common as c
import v26_model as model
import v26_raw as raw
import v26_study as runner
import v26_verify as verify
import v26_service as service
import v24r3_counter as native


def fixture(index=0):
    cfg=c.matrix()[index]
    jobs=[dict(id=i,admission_ns=t,worker_start_ns=t+1_000_000,
               completion_ns=t+4_000_000,processing_ns=3_000_000,queue_wait_ns=1_000_000)
          for i,t in enumerate(c.schedule(cfg))]
    derived=dict(clocks=dict(client_test_start_ns=0,server_minus_client_lower_ns=0,
                            server_minus_client_upper_ns=10_000),
                 summary=dict(cpu_usec_per_completed_work=4500,timely_500_fraction=1))
    server=dict(events=jobs,clock_generation=1)
    anchors=[dict(label=f'{phase}_{i}',before_ns=10_000_000_000-1000+stamp,
                  after_ns=10_000_000_000+1000+stamp,server_ns=stamp,generation=1)
             for phase,stamp in [('start',0),('stop',31_000_000_000)] for i in range(3)]
    samples=[]
    for i in range(1701):
        host=8_000_000_000+i*20_000_000
        usage=10_000_000+round((host-10_000_000_000)/1e9*cfg['rate']*4500)
        samples.append(dict(before_ns=host-500,after_ns=host+500,scheduled_ns=host-500,
                            thread_cpu_before_ns=i*1000,thread_cpu_after_ns=i*1000+500,
                            read_errno=0,cpu_stat=dict(usage_usec=usage,user_usec=usage-1000,
                                                      system_usec=1000,nr_throttled=0)))
    probe=dict(schema=3,sampler_revision='v24r3-native',cadence='absolute_skip_missed',
               record_capacity=6000,raw_capacity=4096,skipped_deadlines=0,
               thread_cpu_started_ns=0,thread_cpu_finished_ns=10_000_000,
               path='/owned/cpu.stat',interval_sec=.02,duration_bound_sec=110,affinity=[0,1],
               failure=None,own_cpu_ns=10_000_000,started_ns=samples[0]['before_ns'],
               finished_ns=samples[-1]['after_ns'],samples=samples,pid=123,uid=1000)
    return cfg,derived,server,anchors,probe


def evaluate(index=0):
    cfg,d,s,a,p=fixture(index)
    return model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')


def client_fixture(cfg):
    rows=[];entries=[];jobs=[];handlers=[]
    start=1_000_000_000
    for i,t in enumerate(c.schedule(cfg)):
        entry=start+t+10_000;admit=entry+10_000;worker=admit+1_000_000;completion=worker+3_000_000
        resume=completion+1_000;end=resume+10_000
        rows.append(dict(ID=i,ScheduledOffsetNs=t,Error='',StatusCode=200,TimedOut=False,
                         DispatchLagNs=1000,HeadersOffsetNs=100_000,EndToEndLatencyNs=end-start-t+1000,
                         CompletedOffsetNs=end-start+1000))
        entries.append(dict(id=i,entry_ns=entry,exit_ns=end+1,admitted=True))
        jobs.append(dict(id=i,admission_ns=admit,worker_start_ns=worker,completion_ns=completion,
                         processing_ns=3_000_000,queue_wait_ns=1_000_000))
        handlers.append(dict(id=i,entry_ns=entry,admission_ns=admit,resume_ns=resume,
                             write_start_ns=resume+1,write_end_ns=end,handler_exit_ns=end+2,
                             post_work_wait_ns=1000,pre_admission_ns=10_000))
    anchors=[dict(label=f'{phase}_{i}',before_ns=t-100,after_ns=t+100,server_ns=t,generation=1)
             for phase,t in [('start',1000),('stop',32_000_000_000)] for i in range(3)]
    n=len(rows)
    client=dict(total_scheduled=n,requests=rows,total_completed=n,total_dispatched=n,
                total_success=n,total_503=0,total_errors=0,client_dropped=0,missed_arrivals=0,
                pattern='steady',duration_sec=cfg['duration_sec'],target_rate=cfg['rate'],
                burst_low_rate=cfg['rate'],burst_high_rate=cfg['rate'],burst_period_sec=10,
                client_trace_enabled=True,clock_anchors=anchors,client_test_start_ns=start,
                elapsed_including_drain_sec=cfg['duration_sec'],client_cpu_usec=1000,
                dispatch_lag_summary={'p99_ms':.001})
    server=dict(runtime_variant='stock',runtime_capture=False,custom_recording=False,
                worker_yield=False,entry_protocol='all-outcomes-v1',workers=1,gomaxprocs=1,
                queue_cap=128,go_version='go1.26.1',instrument=True,active_handlers=0,queue_len=0,
                completed=n,admitted=n,rejected=0,events=jobs,handler_events=handlers,
                entry_events=entries,clock_generation=1)
    return client,server


class V26Tests(unittest.TestCase):
    def test_fixed_order_and_integer_oracle_for_every_schedule_offset(self):
        self.assertEqual([r['rate'] for r in c.matrix()],[15,30,30,15])
        self.assertEqual([r['repeat'] for r in c.matrix()],[1,1,2,2])
        for cfg in c.matrix():
            c.validate_config(cfg)
            for trial in (cfg,c.warmup_config(cfg)):
                n=trial['rate']*trial['duration_sec']
                oracle=[(2*i*1_000_000_000+trial['rate'])//(2*trial['rate']) for i in range(n)]
                self.assertEqual(c.schedule(trial),oracle)
                self.assertTrue(all(0<=t<trial['duration_sec']*1e9 for t in oracle))

    def test_functional_success_and_cancellation_configs_are_separate(self):
        cfgs=c.functional_configs();self.assertEqual(len(cfgs),4)
        self.assertEqual([r['rate'] for r in cfgs if r['timeout_sec']>=1],[15,30])
        for cfg in cfgs:
            c.validate_config(cfg,True);self.assertEqual(cfg['duration_sec'],2)
            self.assertGreater(len(c.schedule(cfg)),0)

    def test_boolean_treatment_and_exact_config_are_required(self):
        for changed in ({'counter_probe':1},{'rate':20},{'duration_sec':60},{'iterations':88000}):
            with self.assertRaises(ValueError):c.validate_config(dict(c.matrix()[0],**changed))

    def test_retained_binary_and_software_receipts_match_v25(self):
        verify.verify_software_receipt()
        self.assertEqual(c.digest(c.BUILD/'counter'),c.digest(c.PREVIOUS/'bundle/counter'))
        for name,h in c.read(c.PREVIOUS/'bundle/manifest.json')['sources'].items():
            self.assertEqual(c.digest(c.ROOT/name),h,name)

    def test_all_four_valid_qualified_records_pass_without_busy_checks(self):
        result=model.report([evaluate(i) for i in range(4)],c.design())
        self.assertEqual(result['decision'],'both_low_rates_qualified')
        self.assertEqual(result['busy_delivery_check'],'inapplicable_no_busy_phase')
        self.assertFalse(result['equivalence_established']);self.assertFalse(result['scientific_explanation_established'])
        for row in result['by_rate'].values():self.assertEqual(row['qualified'],2)

    def test_one_failed_state_is_valid_complete_and_cannot_qualify(self):
        rows=[evaluate(i) for i in range(4)];rows[0]['phases']['low']['state_eligible']=False
        result=model.report(rows,c.design())
        self.assertTrue(result['complete']);self.assertTrue(result['recording_quality_pass'])
        self.assertEqual(result['decision'],'low_state_qualification_failed')
        self.assertEqual(result['by_rate']['15']['qualified'],1)

    def test_incomplete_duplicate_foreign_and_rate_tamper(self):
        rows=[evaluate(i) for i in range(4)]
        self.assertEqual(model.report(rows[:-1],c.design())['decision'],'pilot_incomplete')
        self.assertFalse(model.report([],c.design())['both_low_rates_qualified'])
        with self.assertRaisesRegex(ValueError,'duplicate'):model.report(rows+[rows[0]],c.design())
        rows[0]['trial']='foreign'
        with self.assertRaisesRegex(ValueError,'foreign'):model.report(rows,c.design())
        rows=[evaluate(i) for i in range(4)];rows[0]['rate']=30
        with self.assertRaisesRegex(ValueError,'identity'):model.report(rows,c.design())

    def test_four_records_without_collection_receipt_cannot_qualify(self):
        result=model.report([evaluate(i) for i in range(4)],c.design(),collection_complete=False)
        self.assertTrue(result['recording_quality_pass'])
        self.assertFalse(result['complete']);self.assertFalse(result['both_low_rates_qualified'])
        self.assertEqual(result['decision'],'pilot_incomplete')

    def test_nonfinite_cost_and_missing_measurement_quality_fail(self):
        rows=[evaluate(i) for i in range(4)];rows[0]['whole_cpu_usec_per_job']=float('nan')
        with self.assertRaisesRegex(ValueError,'quality'):model.report(rows,c.design())
        rows=[evaluate(i) for i in range(4)];rows[0]['measurement_quality']['pass_budget']=False
        with self.assertRaisesRegex(ValueError,'quality'):model.report(rows,c.design())

    def test_missing_and_positive_throttling_never_qualify(self):
        for missing in (True,False):
            cfg,d,s,a,p=fixture()
            for i,r in enumerate(p['samples']):
                if missing:r['cpu_stat'].pop('nr_throttled')
                else:r['cpu_stat']['nr_throttled']=i
            row=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
            self.assertTrue(row['recording_quality_pass']);self.assertFalse(row['phases']['low']['state_eligible'])

    def test_queue_maximum_two_fails_state_but_not_measurement(self):
        cfg,d,s,a,p=fixture()
        # Move one future job's admission into an earlier job's waiting interval.
        s['events'][90]['admission_ns']=s['events'][89]['admission_ns']
        row=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertGreater(max(row['phases']['low']['queue_maxima']),1)
        self.assertFalse(row['phases']['low']['state_eligible']);self.assertTrue(row['recording_quality_pass'])

    def test_counter_gap_and_missing_full_measurement_coverage_fail(self):
        cfg,d,s,a,p=fixture();p['samples']=[r for r in p['samples'] if not 12e9<r['before_ns']<12.15e9]
        with self.assertRaisesRegex(ValueError,'gap'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        cfg,d,s,a,p=fixture();p['samples']=[r for r in p['samples'] if r['before_ns']>12e9]
        with self.assertRaisesRegex(ValueError,'enclosing'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')

    def test_clock_disagreement_and_wrong_native_path_fail(self):
        cfg,d,s,a,p=fixture();a[-1]['server_ns']+=2_000_000
        with self.assertRaises(ValueError):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        cfg,d,s,a,p=fixture()
        with self.assertRaisesRegex(ValueError,'identity'):model.trial(d,s,a,p,cfg,c.design(),'/foreign/cpu.stat')

    def test_uncertainty_failure_does_not_search_another_window(self):
        cfg,d,s,a,p=fixture()
        design=copy.deepcopy(c.design());design['measurement_quality']['max_cost_relative_bound_width']=.00001
        with self.assertRaisesRegex(ValueError,'uncertainty'):model.trial(d,s,a,p,cfg,design,'/owned/cpu.stat')
        self.assertEqual(c.design()['windows'],{'low':[[5,25]]})

    def test_descriptive_deadline_failure_does_not_fail_low_state(self):
        cfg,d,s,a,p=fixture();d['summary']['timely_500_fraction']=.1
        row=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertTrue(row['phases']['low']['state_eligible']);self.assertAlmostEqual(row['miss_pct'],90)

    def test_raw_stage_join_replays_entire_steady_cohort_and_conserves_budget(self):
        for cfg in c.matrix()[:2]:
            client,server=client_fixture(cfg)
            rows,_,_=raw.join(client,server,cfg)
            self.assertEqual(len(rows),cfg['rate']*30)
            self.assertTrue(all(r['phase']=='steady' and r['timely_500'] for r in rows))
            client['requests'][5]['ScheduledOffsetNs']+=1
            with self.assertRaisesRegex(ValueError,'offsets'):raw.join(client,server,cfg)

    def test_dropped_rejected_error_and_slow_dispatch_are_technical_failures(self):
        client,_=client_fixture(c.matrix()[0]);c.technical_client(client)
        for key,value in [('client_dropped',1),('missed_arrivals',1),('total_503',1),('total_errors',1)]:
            bad=copy.deepcopy(client);bad[key]=value
            with self.assertRaises(ValueError):c.technical_client(bad)
        client['dispatch_lag_summary']['p99_ms']=2.01
        with self.assertRaisesRegex(ValueError,'dispatch'):c.technical_client(client)

    def test_foreign_container_and_immutable_cleanup_id(self):
        value=dict(Id='id',Config=dict(Labels={service.LABEL:'foreign'}))
        with patch.object(service.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=json.dumps([value]))):
            with self.assertRaisesRegex(ValueError,'ownership'):service.owned_inspect('name','owner')
        with patch.object(service,'owned_inspect',side_effect=[dict(Id='immutable'),None]),patch.object(service,'command') as command:
            service.remove_owned('name','owner');command.assert_called_once_with(['docker','rm','-f','immutable'],timeout=20)

    def test_no_resume_after_attempt_or_lifetime_marker(self):
        for marker in ('attempt','lifetime'):
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp)
                if marker=='attempt':(session/'slots/first/attempt-1').mkdir(parents=True)
                else:c.save(session/'measurement_lifetime.json',{})
                with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),\
                     patch.object(runner.run.old,'check_topology'),patch.object(runner.os,'sched_setaffinity'),\
                     patch.object(runner,'start_watchdog') as start:
                    with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.foreground(session)
                    start.assert_not_called()

    def test_four_slots_then_replay_after_collection_watchdog_disarmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);collected=[]
            def watcher(s,phase,seconds):
                self.assertEqual((phase,seconds),('measurement',2700))
                c.save(s/'measurement_lifetime.json',dict(started_monotonic=0,deadline_monotonic=1e12))
                return types.SimpleNamespace(),(s/'watch.log').open('w')
            def replay(argv,timeout):
                self.assertEqual(argv[2],'analyze');self.assertEqual(timeout,600)
                self.assertTrue((session/'measurement_finished.json').exists());self.assertTrue(stop.called)
                self.assertEqual(c.read(session/'collection_receipt.json')['completed_slots'],4)
                return types.SimpleNamespace(returncode=0)
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),\
                 patch.object(runner.run.old,'check_topology'),patch.object(runner,'bind_observer_inventory'),\
                 patch.object(runner,'environment'),patch.object(runner.os,'sched_setaffinity'),\
                 patch.object(runner,'start_watchdog',side_effect=watcher),patch.object(runner,'collect_slot',side_effect=lambda s,cfg:collected.append(cfg['trial'])),\
                 patch.object(runner.fixtures,'stop') as stop,patch.object(runner.subprocess,'run',side_effect=replay):
                runner.foreground(session,Path('/unused'))
            self.assertEqual(collected,[r['trial'] for r in c.matrix()])

    def test_one_retry_same_slot_and_second_failure_stops(self):
        cfg=c.matrix()[0]
        for fail_twice in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);c.save(session/'preparation/manifest.json',{})
                calls=[]
                def collect(s,d,actual,mode):
                    calls.append(actual);d.mkdir(parents=True)
                    c.save(d/'cleanup.json',dict(errors=[],watchdog_intervened=False))
                    if fail_twice or len(calls)==1:raise ValueError('technical fixture')
                    c.save(d/'complete.json',dict(valid=True))
                with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),\
                     patch.object(verify,'verify_environment'),patch.object(verify,'verify_trial'),\
                     patch.object(runner,'collect',side_effect=collect):
                    if fail_twice:
                        with self.assertRaisesRegex(ValueError,'technical fixture'):runner.collect_slot(session,cfg)
                    else:runner.collect_slot(session,cfg)
                self.assertEqual(calls,[cfg,cfg]);self.assertEqual(len(runner.failures(session)),2 if fail_twice else 1)

    def test_cleanup_failure_prevents_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'preparation/manifest.json',{})
            def collect(s,d,cfg,mode):
                d.mkdir(parents=True);c.save(d/'cleanup.json',dict(errors=['owned resource remains'],watchdog_intervened=False))
                raise ValueError('technical fixture')
            with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),\
                 patch.object(verify,'verify_environment'),patch.object(runner,'collect',side_effect=collect) as collect_call:
                with self.assertRaisesRegex(ValueError,'cleanup'):runner.collect_slot(session,c.matrix()[0])
                self.assertEqual(collect_call.call_count,1)

    def test_missing_or_foreign_observer_inventory_blocks_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp)
            with self.assertRaisesRegex(ValueError,'root observer'):runner.bind_observer_inventory(session,None)
            with patch.object(verify.observer,'review',return_value=dict(boot_id='foreign')):
                with self.assertRaisesRegex(ValueError,'another boot'):runner.bind_observer_inventory(session,session/'audit.json')

    def test_resealed_saved_phase_tamper_fails_independent_replay(self):
        cfg,d,s,a,p=fixture();expected=evaluate()
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
                altered=copy.deepcopy(expected);altered['phases']['low']['state_eligible']=False
                c.save(trial/'phase_accounting.json',altered);c.seal(trial)
                with self.assertRaisesRegex(ValueError,'independent replay'):verify.verify_trial(session,trial,manifest)

    def test_counter_raw_decoding_and_capture_through_drain_are_replayed(self):
        cfg,_,_,_,p=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);trial=session/'trial';trial.mkdir()
            document=copy.deepcopy(p)
            document['samples']=[{**{k:v for k,v in row.items() if k!='cpu_stat'},
                                  'raw':''.join(f'{k} {v}\n' for k,v in row['cpu_stat'].items())}
                                 for row in p['samples']]
            c.save(trial/'counter.raw.json',document)
            decoded=native.decode(document);decoded['raw_sha256']=c.digest(trial/'counter.raw.json')
            payload={'counter.json':decoded,'initial.json':dict(cgroup='/owned'),
                     'counter_argv.json':[str(session/'preparation/counter'),'--path','/owned/cpu.stat',
                                          '--output',str(trial/'counter.raw.json')],
                     'observations.json':dict(measurement_stop=dict(after_ns=p['finished_ns']-1000)),
                     'counter.ready.json':p['samples'][0],
                     'counter_readiness.json':dict(token='READY',received_monotonic_ns=p['started_ns']+2000),
                     'counter_process.json':dict(pid=123,uid=1000),'ownership.json':dict(owner=dict(uid=1000))}
            for name,value in payload.items():c.save(trial/name,value)
            self.assertEqual(verify.counter_input(session,trial,cfg),decoded)
            altered=copy.deepcopy(decoded);altered['samples'][10]['cpu_stat']['usage_usec']+=1
            c.save(trial/'counter.json',altered)
            with self.assertRaisesRegex(ValueError,'decoding'):verify.counter_input(session,trial,cfg)
            c.save(trial/'counter.json',decoded)
            c.save(trial/'observations.json',dict(measurement_stop=dict(after_ns=p['finished_ns']+1)))
            with self.assertRaisesRegex(ValueError,'full drain'):verify.counter_input(session,trial,cfg)

    def test_completion_report_tamper_and_incomplete_after_exhausted_retry(self):
        for incomplete in (False,True):
            with tempfile.TemporaryDirectory() as tmp:
                session=Path(tmp);values=[evaluate(i) for i in range(1 if incomplete else 4)];refs={}
                for row in values:
                    d=session/'slots'/row['trial']/'attempt-1';d.mkdir(parents=True)
                    c.save(d/'started.json',dict(monotonic_ns=1_000_000_000))
                    c.save(d/'complete.json',dict(finished_monotonic_ns=2_000_000_000))
                    refs[row['trial']]=dict(path=str(d.relative_to(session)),seal='mock-verified')
                if incomplete:
                    for i in (1,2):(session/'slots'/c.matrix()[1]['trial']/f'attempt-{i}').mkdir(parents=True)
                prep=session/'preparation';prep.mkdir();c.save(prep/'manifest.json',{});c.seal(prep)
                life=dict(started_monotonic=0,deadline_monotonic=2700,boot='same-boot')
                c.save(session/'measurement_lifetime.json',life)
                if not incomplete:
                    c.save(session/'collection_receipt.json',dict(life,completed_slots=4,collection_finished_monotonic=3))
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
                    self.assertEqual(result['decision'],'pilot_incomplete' if incomplete else 'both_low_rates_qualified')
                    saved['trial_accounting']=[];save_report()
                    with self.assertRaisesRegex(ValueError,'raw replay'):verify.verify_completion(session)

    def test_valid_failed_state_trial_is_not_retried_or_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c.save(session/'preparation/manifest.json',{})
            def collect(s,d,cfg,mode):
                d.mkdir(parents=True);c.save(d/'complete.json',dict(valid=True))
                c.save(d/'phase_accounting.json',dict(state_eligible=False))
            with patch.object(verify,'accepted',return_value=None),patch.object(verify,'verify_preparation'),\
                 patch.object(verify,'verify_environment'),patch.object(verify,'verify_trial'),\
                 patch.object(runner,'collect',side_effect=collect) as called:
                runner.collect_slot(session,c.matrix()[0])
                self.assertEqual(called.call_count,1);self.assertEqual(runner.failures(session),[])

    def test_complete_raw_record_replay_and_phase_analysis_without_service(self):
        cfg=c.matrix()[0];client,server=client_fixture(cfg)
        warm_cfg=c.warmup_config(cfg);warm_client,warm_server=client_fixture(warm_cfg)
        latest=c.read(c.PREVIOUS/'latest_analysis.json')
        previous=c.read(c.PREVIOUS/latest['path']/'report.json')
        reference=previous['trial_refs'][next(r['trial'] for r in previous['trial_accounting'] if r['counter_probe'])]
        retained=c.PREVIOUS/reference['path'];c.verify_seal(retained)
        manifest=c.read(c.PREVIOUS/'preparation/manifest.json')
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);trial=session/'slots'/cfg['trial']/'attempt-1';trial.mkdir(parents=True)
            c.save(session/'preparation/manifest.json',manifest)
            initial=c.read(retained/'initial.json');container=c.read(retained/'container.json')
            identity=c.read(retained/'identity.json');identity['health']=server
            initial['cgroup']='/owned'
            identity['process_identity_after_exec']=initial['process_identity']
            reset_health=copy.deepcopy(server)
            reset_health.update(completed=0,admitted=0,rejected=0,events=[],entry_events=[],handler_events=[])
            limits=initial['initial_limits']
            observations={}
            for label,stamp,cpu in [('startup',8_000_000_000,1_000_000),
                                    ('measurement_start',10_900_000_000,2_000_000),
                                    ('measurement_stop',41_100_000_000,4_025_000),
                                    ('final',41_200_000_000,4_025_100)]:
                observations[label]=dict(before_ns=stamp,after_ns=stamp+100,
                                        cpu_stat=dict(usage_usec=cpu,user_usec=cpu-1000,system_usec=1000),limits=limits)
            anchors=[dict(label=f'{phase}_{i}',before_ns=10_000_000_000-100+stamp,
                          after_ns=10_000_000_000+100+stamp,server_ns=stamp,generation=1)
                     for phase,stamp in [('start',0),('stop',32_000_000_000)] for i in range(3)]
            def argv(name,config):
                return [str(session/'preparation/loadgen'),'-url', 'http://127.0.0.1:1234/work?iterations=44000',
                        '-duration',str(config['duration_sec'])+'s','-rate',str(config['rate']),'-pattern','steady',
                        '-burst-low',str(config['burst_low']),'-burst-high',str(config['burst_high']),
                        '-burst-period','10s','-concurrency','512','-timeout',str(config['timeout_sec'])+'s',
                        '-trace-client=true','-output',str(trial/(name+'.json'))]
            for cl in (client,warm_client):cl['target_url']='http://127.0.0.1:1234/work?iterations=44000'
            payload={'config.json':cfg,'cleanup.json':dict(errors=[],container_removed=True,cgroup_removed=True,
                        tracing_used=False,watchdog_intervened=False),'initial.json':initial,'identity.json':identity,
                     'container.json':container,'loadgen.json':client,'warmup.json':warm_client,
                     'server_metrics.json':server,'warmup_server_metrics.json':warm_server,
                     'loadgen_argv.json':argv('loadgen',cfg),'warmup_argv.json':argv('warmup',warm_cfg),
                     'host_server_anchors.json':anchors,'reset.json':dict(health=reset_health),
                     'settling.json':dict(accepted=True),'environment.json':dict(power_settings={}),
                     'monitor.json':[dict(chatgpt_present=False,process_cpu_deltas=[],power_settings={}) for _ in range(50)],
                     'observations.json':observations,'thread_snapshots.json':[dict(affinity=[2,4],cgroup='/owned',
                         before_ns=10_000_000_000,after_ns=10_000_000_100,tids=[123])]}
            for name,value in payload.items():c.save(trial/name,value)
            shutil.copy2(c.ORIGINAL/'image.server',trial/'container.server')
            (trial/'qualification').mkdir();shutil.copy2(c.ORIGINAL/'gate',trial/'qualification/gate')
            c.seal(trial)
            derived=raw.replay(trial)
            self.assertEqual(derived['summary']['offered'],450)
            self.assertAlmostEqual(derived['summary']['cpu_usec_per_completed_work'],4500)
            _,_,_,_,probe=fixture()
            row=model.trial(derived,server,anchors,probe,cfg,c.design(),'/owned/cpu.stat')
            self.assertTrue(row['phases']['low']['state_eligible'])
            payload['monitor.json']=payload['monitor.json'][:44]
            c.save(trial/'monitor.json',payload['monitor.json']);c.seal(trial)
            with self.assertRaisesRegex(ValueError,'monitor coverage'):raw.replay(trial)


if __name__=='__main__':unittest.main()
