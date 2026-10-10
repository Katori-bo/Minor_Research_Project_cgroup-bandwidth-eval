"""Adversarial evidence tests; these do not run a performance workload."""
import copy
import unittest
import trace_analysis as ta


def fixture():
    offset = 10000
    status = dict(complete=True, active=False, pending_responses=0, io_events_dropped=0,
                  runtime_trace_overflow=False, clock_anchors=[
                      dict(label='start', before_ns=10, after_ns=12),
                      dict(label='stop', before_ns=1000, after_ns=1002)], io_events=[])
    parsed = dict(event_count=100, first_ns=10000, last_ns=11100,
                  anchors=dict(start=10011, stop=11001), transitions={}, tasks={},
                  connections=[], task_begins={}, task_ends={})
    server = dict(go_version='go1.26.1', admitted=2, rejected=1, events=[], handler_events=[])
    client = dict(requests=[])
    def ev(kind, conn, req, start, end=None, known=True, error=''):
        item = dict(kind=kind, conn=conn, request=req, request_known=known,
                    start_ns=start, end_ns=start if end is None else end, bytes=0, error=error)
        status['io_events'].append(item)
        return item
    for req, conn, g, start, end, done in ((0,1,10,100,300,650),(1,2,11,150,200,230),(2,3,12,160,240,280)):
        ev('accept', conn, 0, start-40, known=False)
        active = ev('conn_active',conn,0,start-10,known=False)
        ev('handler_entry',conn,req,start)
        ev('rejected' if req==1 else 'admitted',conn,req,start+5)
        ev('handler_exit',conn,req,end)
        ev('write',conn,req,600 if req==0 else end+10,620 if req==0 else end+20,
           error='broken pipe' if req==2 else '')
        ev('conn_idle' if req!=2 else 'conn_closed',conn,req,done)
        for state, stamp in (('active',start-10),('idle' if req!=2 else 'closed',done)):
            parsed['connections'].append(dict(conn=conn,state=state,g=g,time=stamp+offset+1))
        parsed['tasks'][str(req)] = dict(task=req+1,conn=conn,handler_g=g,handler_log_time=start+offset+3)
        parsed['task_begins'][str(req+1)] = start+offset+2
        parsed['task_ends'][str(req+1)] = end+offset+2
        parsed['transitions'][str(g)] = [[10000,'Undetermined','Running','']]
        client['requests'].append(dict(ID=req,StatusCode=200 if req==0 else 503 if req==1 else 0,
            Error='timeout' if req==2 else '',TimedOut=req==2,EndToEndLatencyNs=800))
        if req != 1:
            wg = g+10
            parsed['transitions'][str(wg)] = [[10000,'Undetermined','Running','']]
            parsed['tasks'][str(req)].update(worker_task=req+1,worker_g=wg,worker_log_time=offset+start+10)
            server['events'].append(dict(id=req,worker_start_ns=start+20,
                completion_ns=250 if req==0 else 480,queue_wait_ns=15,processing_ns=130 if req==0 else 300))
    parsed['transitions']['10'] += [[10300,'Running','Runnable',''],[10600,'Runnable','Running','']]
    server['handler_events']=[dict(id=0,resume_ns=260,write_start_ns=270,write_end_ns=280,
                                  post_work_wait_ns=10,write_error='')]
    client['requests'].append(dict(ID=3,StatusCode=0,Error='connect timeout',TimedOut=True,EndToEndLatencyNs=900))
    return status, client, server, parsed


class TraceEvidenceTests(unittest.TestCase):
    def test_zero_id_outcomes_external_gaps_and_other_work(self):
        result = ta.build_analysis(*fixture())
        self.assertEqual(result['outcome_counts'], dict(success=1,rejected=1,timeout=2,error=0))
        rows = {r['id']:r for r in result['all_requests']}
        self.assertEqual(rows[0]['socket_write_count'],1)
        gap=rows[0]['intervals']['handler_exit_to_first_socket_write']
        self.assertEqual(gap['states'], {'runnable_ns':300})
        self.assertEqual(gap['other_job_id_sample'],[2])
        self.assertIn('connection_context_before_handler', rows[0]['intervals'])
        self.assertEqual(rows[2]['socket_write_error_count'],1)
        self.assertEqual(rows[3]['server_observation'],'unobserved')
        self.assertNotIn('executing_ns',str(result))

    def test_missing_scheduler_evidence_fails_for_success_and_timeout(self):
        for g in ('10','12','22'):
            data=fixture()
            del data[3]['transitions'][g]
            with self.subTest(g=g), self.assertRaisesRegex(ValueError,'scheduler coverage'):
                ta.build_analysis(*data)

    def test_broken_transition_chain_fails(self):
        data=fixture()
        data[3]['transitions']['10'][2][1]='Waiting'
        with self.assertRaisesRegex(ValueError,'transition chain'): ta.build_analysis(*data)

    def test_missing_initial_state_fails(self):
        data=fixture()
        data[3]['transitions']['10'].pop(0)
        with self.assertRaisesRegex(ValueError,'initial scheduler'): ta.build_analysis(*data)

    def test_failed_request_missing_exit_or_worker_fails(self):
        for kind in ('handler_exit','admitted'):
            data=fixture()
            data[0]['io_events']=[e for e in data[0]['io_events'] if not(e['request']==2 and e['kind']==kind)]
            with self.subTest(kind=kind), self.assertRaises(ValueError): ta.build_analysis(*data)

    def test_missing_final_boundary_or_duplicate_exit_fails(self):
        for duplicate in (False,True):
            data=fixture()
            if duplicate: data[0]['io_events'].append(copy.deepcopy(next(e for e in data[0]['io_events'] if e['kind']=='handler_exit')))
            else: data[0]['io_events']=[e for e in data[0]['io_events'] if not(e['conn']==1 and e['kind']=='conn_idle')]
            with self.subTest(duplicate=duplicate), self.assertRaises(ValueError): ta.build_analysis(*data)

    def test_task_mismatch_missing_end_and_rejection_mismatch_fail(self):
        for mode in ('worker','end','rejection'):
            data=fixture()
            if mode=='worker': data[3]['tasks']['2']['worker_task']=999
            elif mode=='end': del data[3]['task_ends']['3']
            else: data[1]['requests'][1]['StatusCode']=200
            with self.subTest(mode=mode), self.assertRaises(ValueError): ta.build_analysis(*data)

    def test_incomplete_capture_and_bad_clock_fail(self):
        for mode in ('dropped','active','pending','clock'):
            data=fixture()
            if mode=='dropped': data[0]['io_events_dropped']=1
            elif mode=='active': data[0]['active']=True
            elif mode=='pending': data[0]['pending_responses']=1
            else: data[3]['anchors']['stop']+=100
            with self.subTest(mode=mode), self.assertRaises(ValueError): ta.build_analysis(*data)

    def test_capture_does_not_cover_final_flush_fails(self):
        data=fixture()
        data[3]['last_ns']=10600
        with self.assertRaisesRegex(ValueError,'outside runtime capture'): ta.build_analysis(*data)

    def test_reads_remain_ambiguous_even_with_multiple_requests(self):
        data=fixture()
        data[0]['io_events'].append(dict(kind='read',conn=1,request=0,request_known=False,
                                      start_ns=65,end_ns=80,bytes=500))
        row=ta.build_analysis(*data)['all_requests'][0]
        self.assertEqual(row['read_association'],'ambiguous_http_framing')
        self.assertFalse(row['context_reads'][0]['request_known'])

    def test_parser_rejects_duplicate_logs_and_missing_states(self):
        state='M=1 P=0 G=10 StateTransition Time=1 GoID=10 Undetermined->Running Reason=""\n'
        log='M=1 P=0 G=10 Log Time=2 Task=1 Category="request" Message="id=0 conn=1"\n'
        with self.assertRaisesRegex(ValueError,'duplicate'): ta.parse_lines([state,log,log])
        with self.assertRaisesRegex(ValueError,'scheduler'): ta.parse_lines([log])

    def test_drain_waits_for_final_response_not_just_handler(self):
        from unittest.mock import patch
        import run
        ready=dict(admitted=1,completed=1,queue_len=0,active_handlers=0,trace_pending_responses=0)
        with patch.object(run,'get',side_effect=[dict(ready,trace_pending_responses=1),ready]), patch.object(run.time,'sleep') as sleep:
            self.assertEqual(run.drain(),ready)
            sleep.assert_called_once()

if __name__=='__main__': unittest.main()
