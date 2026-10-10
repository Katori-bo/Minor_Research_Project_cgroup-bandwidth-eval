from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_decision_probe as build
import decision_analysis as analysis
import decision_probe as probe
import inspect_selected_ahead as offline
import run


def event(kind,g,stamp,**kwargs):
    return dict(sequence=0,time_ns=stamp,kind=kind,g=g,actor_g=g,m=1,p=0,
                source=0,pending=False,fair=False,inherit=False,network=False,
                schedtick=1,request=0,start_pc=1,function='',**kwargs)


def fixture():
    def ev(kind,g,stamp,**kwargs):
        e=event(kind,g,stamp);e.update(kwargs);return e
    events=[ev(4,30,1050,request=9),ev(1,10,1100,p=-1,network=True),
        ev(2,20,1200,source=3,pending=True,fair=True),ev(3,20,1250),ev(5,20,1275,request=9),
        ev(2,10,2000,source=15),ev(3,10,2100),ev(4,10,2200,request=0)]
    for i,e in enumerate(events,1):e['sequence']=i
    server=dict(scheduler_observation_enabled=True,events=[dict(id=9)],
        scheduler_capture=dict(events=events,reserved=len(events),capacity=262144,schema=1,
            window='trace_start_to_drained_trace_stop',stopped_ns=3000))
    status=dict(scheduler_clock_anchors=[dict(label='start',before_ns=0,after_ns=0,runtime_ns=1000),
        dict(label='stop',before_ns=2000,after_ns=2000,runtime_ns=3000)],
        io_events=[dict(kind='handler_entry',conn=1,request=0,request_known=True,start_ns=1200),
                   dict(kind='handler_entry',conn=2,request=9,request_known=True,start_ns=50)])
    client=dict(requests=[dict(ID=i,TimedOut=False,Error='',StatusCode=200) for i in (0,9)])
    return server,status,client


class DecisionTests(unittest.TestCase):
    def test_ready_wait_joins_request_zero_and_actual_forced_worker_choice(self):
        server,status,client=fixture();result=analysis.analyze_capture(server,status,client,True)
        self.assertEqual(result['matched_prehandler_network_waits'],1)
        e=result['examples'][0]
        self.assertEqual((e['request_id'],e['g'],e['wait_ns']),(0,10,1000))
        self.assertEqual(e['by_role'],{'worker':1})
        self.assertEqual(e['by_source'],{'fair_global':1})
        self.assertEqual(e['forced_selected_goroutines'][0]['g'],20)
        self.assertEqual(e['final_selection_source'],'regular_local')

    def test_diverted_selection_does_not_claim_source_of_different_dispatch(self):
        server,status,client=fixture();server['scheduler_capture']['events'][2]['g']=99
        e=analysis.analyze_capture(server,status,client,True)['examples'][0]
        self.assertEqual(e['by_source'],{'unmatched_direct_execute':1})
        self.assertEqual(e['forced_selections_ahead'],1)
        self.assertEqual(e['forced_dispatches_ahead'],0)
        self.assertIsNone(e['forced_selected_goroutines'][0]['matched_dispatch_ns'])

    def test_later_network_wake_prevents_link_to_earlier_running_segment(self):
        server,status,client=fixture();events=server['scheduler_capture']['events']
        extra=event(1,10,2150);extra['network']=True
        events.insert(-1,extra)
        for i,e in enumerate(events,1):e['sequence']=i
        server['scheduler_capture']['reserved']=len(events)
        result=analysis.analyze_capture(server,status,client,True)
        self.assertEqual(result['matched_prehandler_network_waits'],0)
        self.assertEqual(result['unresolved_wakes'][0]['g'],10)

    def test_cleanup_reuse_overlap_is_kept_separate(self):
        server,status,client=fixture();events=server['scheduler_capture']['events']
        extra=event(4,10,1075);extra['request']=7;events.insert(1,extra)
        for i,e in enumerate(events,1):e['sequence']=i
        server['scheduler_capture']['reserved']=len(events)
        status['io_events'] += [dict(kind='handler_entry',conn=1,request=7,request_known=True,start_ns=75),
                               dict(kind='conn_idle',conn=1,request=7,request_known=True,start_ns=200)]
        client['requests'].append(dict(ID=7,TimedOut=False,Error='',StatusCode=200))
        result=analysis.analyze_capture(server,status,client,True)
        self.assertEqual(result['matched_prehandler_network_waits'],0)
        self.assertEqual(result['cleanup_ambiguous'][0]['request_id'],0)

    def test_overflow_missing_publication_bad_source_marker_and_clock_fail(self):
        for change in ('overflow','missing','source','zero','clock'):
            server,status,client=fixture()
            if change=='overflow':server['scheduler_capture']['reserved']=262145
            if change=='missing':server['scheduler_capture']['events'].pop()
            if change=='source':server['scheduler_capture']['events'][2]['source']=99
            if change=='zero':server['scheduler_capture']['events'][-1]['request']=1
            if change=='clock':status['scheduler_clock_anchors'][-1]['runtime_ns']+=1
            with self.assertRaises(ValueError,msg=change):analysis.analyze_capture(server,status,client,True)

    def test_control_waits_are_unavailable(self):
        server,status,client=fixture();server['scheduler_observation_enabled']=False
        server['scheduler_capture'].update(events=[],reserved=0)
        result=analysis.analyze_capture(server,status,client,False)
        self.assertNotIn('ready_wait_p99_ms',result)
        server['scheduler_capture']['events']=[event(4,10,1100)];server['scheduler_capture']['reserved']=1
        with self.assertRaises(ValueError):analysis.analyze_capture(server,status,client,False)

    def test_queue_policy_and_balanced_workload_are_preserved(self):
        source=(run.ROOT/'analysis/runtime_io_v9_candidate/prepared/proc.go').read_text()
        a=build.runtime_source(source,False);b=build.runtime_source(source,True)
        self.assertEqual(a.replace('const researchObserveDecisions = false','const researchObserveDecisions = true'),b)
        self.assertEqual(b.count('researchDecisionRecord(2, gp,'),len(build.REASONS))
        rows=probe.matrix(dict(images=dict(control='a',observed='b')))
        self.assertEqual(len(rows),8)
        self.assertEqual([r['probe_mode'] for r in rows[::2]],['control','observed','observed','control'])
        for r in rows:
            self.assertFalse(r['runtime_trace']);self.assertFalse(r['worker_yield'])
            original=run.pilot_matrix()[0]
            self.assertTrue(all(r[k]==v for k,v in original.items() if k not in ('run_id','rep','runtime_trace')))

    def test_quiet_host_guard_prevents_measurement_launch(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(probe.pipeline,'is_running',return_value=False),\
            patch.object(run,'require_quiet_host',side_effect=RuntimeError('desktop app present')),\
            patch.object(probe.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'desktop'):probe.launch(Path(tmp))
            spawn.assert_not_called()

    def test_frozen_bundle_rejects_tampering(self):
        value=run.read(build.DEFAULT/'build.json')
        with tempfile.TemporaryDirectory() as tmp,patch.object(run,'require_quiet_host'),\
            patch.object(run.old,'check_topology',return_value={'fixture':True}),\
            patch.object(run,'capture',return_value='fixture'),\
            patch.object(run,'power_settings',return_value={'fixture':True}):
            p=Path(tmp)/'session';probe.create(p,value)
            self.assertTrue(probe.verify_session(p)['decision_probe'])
            frozen=p/'probe_build/observed_runtime/proc.go';frozen.write_text(frozen.read_text()+'\n// changed\n')
            with self.assertRaisesRegex(ValueError,'frozen probe source'):probe.verify_session(p)

    def test_offline_role_conflicts_remain_ambiguous(self):
        requests=dict(all_requests=[dict(handler_g=7,worker_g=7)])
        self.assertEqual(offline.roles([],requests)[7],'ambiguous')
        rows=[dict(actor_g=8,target_g=7,Stack='runtime.traceAdvance',
                   TransitionStack='net/http.(*connReader).backgroundRead')]
        roles=offline.roles(rows,dict(all_requests=[]))
        self.assertEqual(roles,{8:'trace_advancer',7:'http_background_reader'})

    def test_eight_trial_report_keeps_failed_observer_screen_without_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);session=directory/'session';session.mkdir()
            plan=probe.matrix(dict(images=dict(control='a',observed='b')))
            run.put(session/'matrix.json',plan)
            for config in plan:
                attempt=session/'attempts'/config['run_id']/'001';attempt.mkdir(parents=True)
                server,status,client=fixture()
                enabled=config['probe_mode']=='observed'
                if not enabled:
                    server['scheduler_observation_enabled']=False
                    server['scheduler_capture'].update(events=[],reserved=0)
                server['completed']=1
                client.update(total_errors=0,total_scheduled=2)
                run.put(attempt/'server_metrics.json',server);run.put(attempt/'trace_status.json',status)
                run.put(attempt/'loadgen.json',client);run.put(attempt/'complete.json',dict(fixture=True))
            def trial_row(order,config,attempt):
                row=dict(rep=config['rep'],run_id=config['run_id'],runtime_trace=False,
                    cpu_usec_per_completed_work=2 if config['probe_mode']=='observed' else 1,
                    client_cpu_usec_per_scheduled=1,p99_e2e_ms=1,successful_rps=1,
                    rejection_fraction=0,timeout_fraction=0,trace_coverage=1)
                for key in ('p99_pre_admission_ms','p99_post_work_ms','p99_resume_to_write_ms',
                    'p99_write_call_ms','p99_write_to_exit_ms','p99_request_to_first_byte_ms',
                    'p99_first_byte_to_body_done_ms'):row[key]=1
                return row
            with patch.object(probe,'verify_session'),patch.object(run,'validate',return_value=True),\
                patch.object(probe.analyze,'trial_row',side_effect=trial_row):
                probe.analyze_results(directory)
            out=session/'analysis'
            self.assertTrue(run.read(out/'validation.json')['passed'])
            self.assertFalse(run.read(out/'observer_screens.json')['original_numeric_screens_passed'])
            self.assertIn('screens: FAIL',(out/'report.md').read_text())
            self.assertEqual(len(run.read(out/'scheduler_attribution.json')),8)
            self.assertFalse(run.read(directory/'completion.json')['eligible_for_full'])
            self.assertFalse((out/'pilot_gate.json').exists())


if __name__=='__main__':unittest.main()
