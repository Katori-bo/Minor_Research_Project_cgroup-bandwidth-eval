"""V20 accounting, prospective decision and ownership regressions; no Docker calls."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, Mock

import execution_delay_common as c
import execution_delay_analysis as a
import execution_delay_service as service
import execution_delay_study as runner
import verify_execution_delay as verify
import parallelism_analysis


def retained():
    report = c.read(c.V19/'analysis/1791186642269289872/report.json')
    d = c.V19/report['attempts']['b1_one']['path']
    return c.read(d/'loadgen.json'), c.read(d/'server_metrics.json')


def totals(client, server):
    rows = client['requests']
    client.update(total_completed=len(rows), total_dispatched=len(rows),
        total_success=sum(not q['Error'] and q['StatusCode'] == 200 for q in rows),
        total_503=sum(not q['Error'] and q['StatusCode'] == 503 for q in rows),
        total_errors=sum(bool(q['Error']) or q['StatusCode'] not in (200, 503) for q in rows))
    server.update(admitted=len(server['events']), completed=len(server['events']),
        rejected=sum(not e['admitted'] for e in server['entry_events']))


def fixture_data():
    client, server = retained()
    selected = set(range(6))
    client['requests'] = [q for q in client['requests'] if q['ID'] in selected]
    client.update(total_scheduled=6, client_dropped=0, missed_arrivals=0, duration_sec=2)
    for key in ('events', 'handler_events', 'entry_events'):
        server[key] = [r for r in server[key] if r['id'] in selected]
    totals(client, server)
    vector = [q['ScheduledOffsetNs'] for q in sorted(client['requests'], key=lambda q: q['ID'])]
    return client, server, vector


def move_completion(client, server, rid, completion_ms, resume_ms, e2e_ms):
    mapping = parallelism_analysis.clock_mapping(client, server)
    q = next(q for q in client['requests'] if q['ID'] == rid)
    job = next(j for j in server['events'] if j['id'] == rid)
    h = next(h for h in server['handler_events'] if h['id'] == rid)
    entry = next(e for e in server['entry_events'] if e['id'] == rid)
    origin = mapping['client_test_start_ns']+q['ScheduledOffsetNs']+mapping['server_minus_client_lower_ns']
    job['completion_ns'] = origin+int(completion_ms*1e6)
    job['processing_ns'] = job['completion_ns']-job['worker_start_ns']
    h['resume_ns'] = origin+int(resume_ms*1e6)
    h['post_work_wait_ns'] = h['resume_ns']-job['completion_ns']
    h['write_start_ns'] = h['resume_ns']+1
    h['write_end_ns'] = h['resume_ns']+2
    entry['exit_ns'] = h['resume_ns']+3
    h['handler_exit_ns'] = h['resume_ns']+4
    q['EndToEndLatencyNs'] = int(e2e_ms*1e6)
    q['CompletedOffsetNs'] = q['ScheduledOffsetNs']+q['EndToEndLatencyNs']


class OwnershipTests(unittest.TestCase):
    def test_docker_absent_object_capitalization_and_permission_failure(self):
        for error in ('Error: No such object: owned', 'error: no such object: owned', 'No such container: owned'):
            with patch.object(service.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', error)):
                self.assertIsNone(service.owned_inspect('owned', 'nonce'))
        with patch.object(service.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'permission denied')):
            with self.assertRaisesRegex(ValueError, 'inspection failed'):
                service.owned_inspect('owned', 'nonce')

    def test_independent_export_tamper_rejected(self):
        rows = [dict(id=1, timely_500=True, missing=None)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'requests.csv'
            runner.export_csv(path, rows)
            verify.verify_export(path, rows)
            path.write_text(path.read_text().replace('True', 'False'))
            with self.assertRaisesRegex(ValueError, 'export'):
                verify.verify_export(path, rows)

    def test_reused_owner_pid_refuses_signal(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner.os, 'kill') as kill:
            owner = c.process_identity(os.getpid())
            owner['start_ticks'] = str(int(owner['start_ticks'])+1)
            c.save(Path(tmp)/'owner.json', owner)
            with self.assertRaisesRegex(ValueError, 'reused'):
                runner.stop(Path(tmp))
            kill.assert_not_called()

    def test_foreign_container_cleanup_refused(self):
        value = dict(Id='foreign-id', Config=dict(Labels={service.LABEL: 'someone-else'}))
        response = subprocess.CompletedProcess([], 0, json.dumps([value]), '')
        with patch.object(service.subprocess, 'run', return_value=response), patch.object(service, 'command') as command:
            with self.assertRaisesRegex(ValueError, 'ownership changed'):
                service.remove_owned('same-name', 'original-nonce')
            command.assert_not_called()

    def test_cleanup_uses_immutable_id_after_nonce_check(self):
        with patch.object(service, 'owned_inspect', side_effect=[dict(Id='immutable-id'), None]), patch.object(service, 'command') as command:
            service.remove_owned('mutable-name', 'nonce')
            command.assert_called_once_with(['docker', 'rm', '-f', 'immutable-id'], timeout=20)

    def test_watchdog_owner_death_records_invalidation(self):
        child = subprocess.Popen([sys.executable, '-c', 'pass'])
        owner = c.process_identity(child.pid)
        child.wait(timeout=5)
        with tempfile.TemporaryDirectory() as tmp, patch.object(service, 'remove_owned') as remove:
            d = Path(tmp)
            c.save(d/'ownership.json', dict(owner=owner, container='owned', nonce='nonce', started_monotonic=time.monotonic()))
            service.watchdog(d)
            remove.assert_called_once_with('owned', 'nonce')
            self.assertTrue(c.read(d/'watchdog_cleanup.json')['invalidated'])

    def test_active_watchdog_timeout_signals_only_verified_owner(self):
        owner = c.process_identity(os.getpid())
        with tempfile.TemporaryDirectory() as tmp, patch.object(service.os, 'kill') as kill, patch.object(service, 'remove_owned'):
            d = Path(tmp)
            c.save(d/'ownership.json', dict(owner=owner, container='owned', nonce='nonce', started_monotonic=time.monotonic()-361))
            service.watchdog(d)
            kill.assert_called_once_with(owner['pid'], signal.SIGTERM)
            self.assertEqual(c.read(d/'watchdog_cleanup.json')['reason'], 'active-trial watchdog expired')

    def test_changed_source_and_seal_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d/'raw').write_text('original')
            c.seal(d)
            (d/'raw').write_text('changed')
            with self.assertRaises(ValueError):
                c.verify_seal(d)
            (d/'link').symlink_to(d/'raw')
            with self.assertRaises(ValueError):
                c.seal(d)
        previous = copy.deepcopy(c.read(c.V19/'preparation/manifest.json'))
        name = next(iter(previous['sources']))
        previous['sources'][name] = 'changed'
        with patch.object(c, 'read', return_value=previous), self.assertRaisesRegex(ValueError, 'V19 frozen source'):
            c.source_hashes()


class ProtocolTests(unittest.TestCase):
    def test_four_factor_cells_positions_and_pair_order(self):
        from itertools import combinations
        matrix=c.matrix()
        self.assertEqual(len(matrix),16)
        self.assertEqual([v['order'] for v in matrix],list(range(1,17)))
        for arm in c.ARMS:
            self.assertEqual([sum(o[i]==arm for o in c.ORDERS) for i in range(4)],[1]*4)
        for x,y in combinations(c.ARMS,2):
            self.assertEqual(sum(o.index(x)<o.index(y) for o in c.ORDERS),2)
        self.assertEqual(len(c.rehearsals()),4)
        for conf in matrix:
            self.assertEqual(conf['workers'],1)
            self.assertEqual(conf['gomaxprocs'],1)
            self.assertEqual(conf['quota_us']/conf['period_us'],.5)
            self.assertEqual(c.schedule(conf),c.arrivals())
            c.validate_config(conf)

    def test_only_yield_and_cpu_contract_change(self):
        def normalize(conf):
            argv=c.service_argv('original',Path('/qualification'),'owned',conf)
            self.assertIn('WORKERS=1',argv)
            self.assertIn('GOMAXPROCS=1',argv)
            self.assertNotIn('--memory',argv)
            self.assertNotIn('--pids-limit',argv)
            argv[argv.index('--cpu-quota')+1]='QUOTA'
            argv[argv.index('--cpu-period')+1]='PERIOD'
            argv[argv.index('WORKER_YIELD='+str(int(conf['worker_yield'])))]='YIELD'
            return argv
        self.assertEqual(len({tuple(normalize(conf)) for conf in c.matrix()}),1)

    def test_existing_binary_boolean_env_requires_zero_or_one(self):
        text=(c.ORIGINAL_BUILD/'prepared/service/main.go').read_text()
        boolean=text[text.index('func booleanEnv('):text.index('\nfunc main()')]
        self.assertIn('case "0":',boolean)
        self.assertIn('case "1":',boolean)
        self.assertNotIn('case "true"',boolean)
        for conf in c.matrix():
            env=[a for a in c.service_argv('image',Path('/q'),'owned',conf) if a.startswith('WORKER_YIELD=')]
            self.assertEqual(env,['WORKER_YIELD='+('1' if conf['worker_yield'] else '0')])

    def test_config_bool_integer_and_wrong_factor_rejected(self):
        for mutation in ({'workers':4},{'workers':True},{'worker_yield':1},{'worker_yield':True},
                         {'period_us':250000},{'quota_us':20000},{'duration_sec':59}):
            with self.assertRaises(ValueError): c.validate_config(dict(c.matrix()[0],**mutation))

    def test_resource_contract_and_historical_defaults(self):
        baseline=c.read(c.V19/'preparation/manifest.json')['resource_baseline']
        for conf in c.matrix()[:4]:
            limits=dict(baseline['limits'],**{'cpu.max':f"{conf['quota_us']} {conf['period_us']}"})
            host=dict(baseline['host_config'],CpuQuota=conf['quota_us'],CpuPeriod=conf['period_us'],CpusetCpus='2,4')
            c.validate_resources(limits,host,baseline,conf)
            for changed in (dict(limits,**{'cpu.max.burst':'1000'}),dict(limits,**{'pids.max':'128'})):
                with self.assertRaises(ValueError): c.validate_resources(changed,host,baseline,conf)
            with self.assertRaises(ValueError): c.validate_resources(limits,dict(host,CpuQuota=20000),baseline,conf)

    def test_six_functional_checks_leave_measurement_schedule_unchanged(self):
        self.assertEqual(len(c.functional_configs()),6)
        for conf in c.functional_configs():
            c.validate_config(conf,True)
            self.assertEqual(len(c.schedule(conf)),453 if conf['timeout_sec']<1 else 114)
        self.assertEqual(len(c.arrivals()),6793)

    def test_actual_yield_state_and_no_trace_required(self):
        _,server=retained()
        c.validate_state(server,c.fixture('A'),True)
        with self.assertRaises(ValueError): c.validate_state(server,c.fixture('B'),True)
        server['worker_yield']=True
        c.validate_state(server,c.fixture('B'),True)
        server['runtime_capture']=True
        with self.assertRaises(ValueError): c.validate_state(server,c.fixture('B'))

    def test_no_docker_in_independent_verifier_and_live_status(self):
        text=Path(verify.__file__).read_text()
        self.assertNotIn('subprocess',text)
        self.assertNotIn('import execution_delay_study',text)
        self.assertNotIn('bpftrace',Path(service.__file__).read_text())
        with tempfile.TemporaryDirectory() as tmp, patch.object(c,'verify_seal',side_effect=AssertionError('hash')),patch.object(a,'replay',side_effect=AssertionError('replay')):
            runner.status(Path(tmp))

    def test_valid_unfavorable_attempt_never_replaced_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); conf=c.matrix()[0]; d=session/'trials'/conf['trial']/'attempt-1'
            c.save(d/'complete.json',dict(valid=True)); c.save(d/'derived.json',dict(summary=dict(timely_500_fraction=0)))
            c.seal(d)
            self.assertEqual(len(runner.pending(session,'resume')),15)
            self.assertNotIn(conf['trial'],[v['trial'] for v in runner.pending(session,'resume')])
            (d/'extra').write_text('tamper')
            with self.assertRaises(ValueError): runner.pending(session,'resume')

    def test_reference_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ('../outside','/tmp/outside'):
                with self.assertRaises(ValueError): c.resolve(Path(tmp),bad)

    def test_changed_live_limits_stop_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); d=session/'attempt'; d.mkdir()
            c.save(session/'preparation/manifest.json',{})
            svc=service.Service(session,c.fixture('A'),d,watch=False)
            svc.pid=os.getpid(); svc.process=c.process_identity(svc.pid); svc.group=session/'group'; svc.group.mkdir()
            svc.expected_limits={'cpu.max':'50000 100000'}
            (svc.group/'cpu.max').write_text('50000 100000')
            with patch.object(service.bridge,'cgroup',return_value=svc.group):
                svc.guard()
                (svc.group/'cpu.max').write_text('10000 20000')
                with self.assertRaisesRegex(ValueError,'limits changed'): svc.guard()

    def test_invalid_completion_kind_rejected_before_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); c.save(d/'config.json',c.fixture('A'))
            c.save(d/'complete.json',dict(valid=True,functional=False,performance_run=True))
            with self.assertRaisesRegex(ValueError,'marker kind'): verify.verify_trial(d,d,{},True)


class AccountingTests(unittest.TestCase):
    def test_actual_six_v19_one_worker_crossings_and_publication_bounds(self):
        report=c.read(c.V19/'analysis/1791186642269289872/report.json'); total=0
        for block in range(1,7):
            d=c.V19/report['attempts'][f'b{block}_one']['path']
            rows,_,_=a.join(c.read(d/'loadgen.json'),c.read(d/'server_metrics.json'),c.matrix()[0])
            crossing=[r for r in rows if r['deadline_class']=='computed_before_handler_resumed_after']
            total+=len(crossing)
            self.assertTrue(all(r['available_result_deadline_crossing'] for r in crossing))
            self.assertTrue(all(r['post_publication_wait_lower_bound_ns']>0 for r in crossing))
            self.assertEqual(len(rows),6793)
        self.assertEqual(total,1182)

    def test_all_outcomes_retained_and_missing_handler_not_zero(self):
        client,server,vector=fixture_data(); q={q['ID']:q for q in client['requests']}
        q[1]['StatusCode']=503
        q[2].update(StatusCode=0,Error='request timeout',TimedOut=True)
        q[4]['StatusCode']=500
        client['requests']=[v for v in client['requests'] if v['ID']!=3]; client['client_dropped']=1
        for key in ('events','handler_events'): server[key]=[r for r in server[key] if r['id'] not in (1,3)]
        server['handler_events']=[r for r in server['handler_events'] if r['id']!=2]
        server['entry_events']=[r for r in server['entry_events'] if r['id']!=3]
        next(e for e in server['entry_events'] if e['id']==1)['admitted']=False
        totals(client,server)
        with patch.object(c,'arrivals',return_value=vector): rows,_,_=a.join(client,server,c.fixture('A'))
        self.assertEqual([r['outcome'] for r in rows],['success','rejected','timeout','client_dropped','error','success'])
        self.assertIsNone(rows[2]['completion_to_resume_ns'])
        self.assertIsNone(rows[2]['post_publication_wait_lower_bound_ns'])
        self.assertEqual(rows[2]['publication_bound_status'],'handler_unobserved')
        self.assertIsNone(rows[3]['e2e_ns'])

    def test_deadline_exact_and_ambiguous_classifications(self):
        for completion,resume,e2e,expected in [(490,510,550,'computed_before_handler_resumed_after'),
                (500,520,550,'computed_before_handler_resumed_after'),
                (500.01,520,550,'computation_boundary_ambiguous'),
                (490,500,550,'handler_resumed_before_client_finished_after'),(450,475,500,'timely')]:
            client,server,_=fixture_data()
            client['requests']=[q for q in client['requests'] if q['ID']==0]
            client['total_scheduled']=1
            for k in ('events','handler_events','entry_events'): server[k]=[r for r in server[k] if r['id']==0]
            totals(client,server); move_completion(client,server,0,completion,resume,e2e)
            with patch.object(c,'arrivals',return_value=[0]): rows,_,_=a.join(client,server,c.fixture('A'))
            self.assertEqual(rows[0]['deadline_class'],expected)
            self.assertIsNone(rows[0]['post_publication_wait_lower_bound_ns'])

    def test_success_missing_marker_and_raw_mutations_rejected(self):
        for mutation in ('missing_handler','count','duplicate','schedule','generation','processing','worker_overlap'):
            client,server,vector=fixture_data()
            if mutation=='missing_handler': server['handler_events'].pop()
            elif mutation=='count': client['total_success']-=1
            elif mutation=='duplicate': client['requests'][1]['ID']=0
            elif mutation=='schedule': client['requests'][1]['ScheduledOffsetNs']+=1
            elif mutation=='generation': client['clock_anchors'][0]['generation']+=1
            elif mutation=='processing': server['events'][0]['processing_ns']+=1
            else:
                j=sorted(server['events'],key=lambda j:j['worker_start_ns'])[1]
                j['worker_start_ns']=server['events'][0]['worker_start_ns']+1
                j['processing_ns']=j['completion_ns']-j['worker_start_ns']
                j['queue_wait_ns']=j['worker_start_ns']-j['admission_ns']
            with patch.object(c,'arrivals',return_value=vector),self.assertRaises(ValueError): a.join(client,server,c.fixture('A'))

    def test_no_inferred_client_drop_without_counter_conservation(self):
        client,server,vector=fixture_data(); client['requests'].pop()
        with patch.object(c,'arrivals',return_value=vector),self.assertRaisesRegex(ValueError,'dropped offers'):
            a.join(client,server,c.fixture('A'))

    def test_cpu_window_and_incomplete_whole_cohort_gap(self):
        rows=[dict(success=True,timely_500=True,timely_1000=True,e2e_ns=1_000_000,worker_observed=True,
            handler_observed=True,completion_to_resume_ns=10,deadline_class='timely',outcome='success',drained_response=False),
            dict(success=False,timely_500=False,timely_1000=False,e2e_ns=None,worker_observed=False,
            handler_observed=False,completion_to_resume_ns=None,deadline_class='unsuccessful',outcome='client_dropped',drained_response=False)]
        for r in rows:
            r.update(queue_ns=None,processing_wall_ns=None,scheduled_to_entry_upper_ns=None,resume_to_client_upper_ns=None,
                post_publication_wait_lower_bound_ns=None,available_result_deadline_crossing=False,publication_bound_status='unknown')
        obs=dict(measurement_start=dict(before_ns=1,after_ns=2,cpu_stat=dict(usage_usec=100)),
                 measurement_stop=dict(before_ns=3,after_ns=4,cpu_stat=dict(usage_usec=700)))
        client=dict(elapsed_including_drain_sec=60,client_dropped=1,missed_arrivals=1,client_cpu_usec=100)
        result=a.summarize(c.matrix()[0],client,dict(completed=1),rows,dict(uncertainty_ns=1),{},obs)
        self.assertEqual(result['timely_500_fraction'],.5)
        self.assertEqual(result['cpu_usec_per_completed_work'],600)
        self.assertEqual(result['completion_to_resume_ns']['mean'],10)
        self.assertIsNone(result['gap_mean_all_offers_ns'])
        self.assertEqual(result['gap_unobserved_count'],1)
        obs['measurement_stop']['cpu_stat']['usage_usec']=99
        with self.assertRaises(ValueError): a.summarize(c.matrix()[0],client,dict(completed=1),rows,dict(uncertainty_ns=1),{},obs)

    def test_publication_bounds_unknown_and_clock_uncertainty(self):
        jobs={0:dict(id=0,worker_start_ns=0,completion_ns=100),1:dict(id=1,worker_start_ns=200,completion_ns=300)}
        handlers={0:dict(resume_ns=400),1:dict(resume_ns=350)}
        def rows():
            return [dict(id=i,completion_after_offered_lower_ns=499_999_850,completion_after_offered_upper_ns=499_999_901,
                deadline_class='computed_before_handler_resumed_after') for i in range(2)]
        rr=rows(); a.attach_publication_bounds(rr,jobs,handlers,{'workers':1})
        self.assertFalse(rr[0]['publication_before500_certain'])
        self.assertEqual(rr[0]['post_publication_wait_lower_bound_ns'],200)
        self.assertIsNone(rr[1]['post_publication_wait_lower_bound_ns'])
        rr=rows(); a.attach_publication_bounds(rr,jobs,{0:dict(resume_ns=200)}, {'workers':1})
        self.assertIsNone(rr[0]['post_publication_wait_lower_bound_ns'])
        self.assertEqual(rr[0]['publication_bound_status'],'handler_resumed_before_or_at_bound')
        with self.assertRaises(ValueError): a.attach_publication_bounds(rows(),jobs,handlers,{'workers':4})


class DecisionTests(unittest.TestCase):
    def rows(self,gaps=(100,70,70,49)):
        return [dict(block=b,arm=arm,timely_500_fraction=.8,timely_1000_fraction=1,failure_fraction=0,
            cpu_usec_per_completed_work=3500,p99_e2e_ms=750,gap_mean_all_offers_ns=gap*1e6,
            gap_p99_all_offers_ns=gap*2e6,gap_coverage_fraction=1,gap_gt50ms_fraction=.4,
            available_result_crossing_fraction=.03) for b in range(1,5) for arm,gap in zip(c.ARMS,gaps)]

    def test_four_paired_contrasts_interaction_and_df3(self):
        report=a.compare(self.rows())
        self.assertEqual(report['decision'],'mixed_execution_opportunity_and_temporal_supply_signals')
        self.assertAlmostEqual(report['blocks'][0]['interaction']['gap_mean_ns'],9e6)
        for label in ('yield_100','yield_20','period_no_yield','period_yield'):
            s=report['contrasts'][label]['statistics']['gap_mean_relative_reduction']
            self.assertEqual(s['n'],4); self.assertEqual(s['mean_ci95']['degrees_of_freedom'],3)
        self.assertFalse(report['eligible_for_automatic_confirmation'])
        self.assertFalse(report['repeatability_established'])

    def test_execution_only_period_only_and_no_signal(self):
        for gaps,decision in [((100,70,100,70),'execution_opportunity_signal'),
                ((100,100,70,70),'temporal_supply_signal'),((100,100,100,100),'no_clear_execution_delay_signal'),
                ((100,90,90,60),'period_dependent_execution_opportunity_signal'),
                ((100,90,90,70),'combined_intervention_signal_requires_review'),
                ((100,95,70,90),'yield_dependent_temporal_supply_signal')]:
            self.assertEqual(a.compare(self.rows(gaps))['decision'],decision)

    def test_exact_25_percent_threshold_and_three_positive_blocks(self):
        rows=self.rows((100,75,100,75)); report=a.compare(rows)
        self.assertTrue(report['contrasts']['yield_100']['descriptive_signal_pass'])
        next(r for r in rows if r['block']==4 and r['arm']=='B')['gap_mean_all_offers_ns']=125e6
        self.assertTrue(a.compare(rows)['contrasts']['yield_100']['descriptive_signal_pass'])
        next(r for r in rows if r['block']==3 and r['arm']=='B')['gap_mean_all_offers_ns']=125e6
        self.assertFalse(a.compare(rows)['contrasts']['yield_100']['descriptive_signal_pass'])

    def test_deadline_loss_cannot_pass_gap_signal(self):
        rows=self.rows()
        for r in rows:
            if r['arm']=='B': r['timely_500_fraction']=.79
        self.assertFalse(a.compare(rows)['contrasts']['yield_100']['descriptive_signal_pass'])

    def test_guardrail_failure_preserves_effects(self):
        rows=self.rows(); rows[1]['cpu_usec_per_completed_work']=4000
        report=a.compare(rows)
        self.assertEqual(report['decision'],'guardrail_tradeoff_requires_review')
        self.assertTrue(report['contrasts']['yield_100']['descriptive_signal_pass'])
        self.assertFalse(report['interpretation_eligible'])
        for field,value in [('failure_fraction',.002),('timely_1000_fraction',.98),('p99_e2e_ms',850),('p99_e2e_ms',None)]:
            rows=self.rows(); rows[1][field]=value
            self.assertFalse(a.compare(rows)['guardrails_pass'])

    def test_missing_gaps_and_zero_baseline_are_unassessable(self):
        rows=self.rows(); rows[1]['gap_mean_all_offers_ns']=None; rows[1]['gap_coverage_fraction']=.99
        self.assertEqual(a.compare(rows)['decision'],'inconclusive_whole_cohort_gap_metric')
        self.assertFalse(a.compare(rows)['contrasts']['yield_100']['descriptive_signal_pass'])
        self.assertEqual(a.compare(self.rows((0,0,0,0)))['decision'],'inconclusive_whole_cohort_gap_metric')

    def test_incomplete_duplicate_and_interrupted_evidence(self):
        self.assertEqual(a.compare(self.rows()[:-1])['decision'],'incomplete_evidence')
        with self.assertRaises(ValueError): a.compare(self.rows()+[self.rows()[0]])
        report=a.compare(self.rows(),[1])
        self.assertEqual(report['decision'],'inconclusive_interrupted_blocks')
        self.assertFalse(report['interpretation_eligible'])

    def test_guardrail_boundaries_are_inclusive(self):
        rows=self.rows(); rows[1].update(timely_1000_fraction=.99,failure_fraction=.001,
            cpu_usec_per_completed_work=3675,p99_e2e_ms=825)
        self.assertTrue(a.compare(rows)['guardrails_pass'])
        rows[1]['p99_e2e_ms']=825.01
        self.assertFalse(a.compare(rows)['guardrails_pass'])


if __name__=='__main__':
    unittest.main()
