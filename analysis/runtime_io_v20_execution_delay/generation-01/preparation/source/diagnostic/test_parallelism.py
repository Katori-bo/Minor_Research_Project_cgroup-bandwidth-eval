from copy import deepcopy
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import build_parallelism as build
import parallelism_analysis as analysis
import parallelism_study as study
import parallelism_progress as progress
import run


def fixture():
    # Server time = client-origin time + 1000 ns. Workload origin at 200 ns.
    anchors=[dict(label=f'{phase}_{i}',before_ns=stamp-10,after_ns=stamp+10,
                  server_ns=stamp+1000,generation=1)
             for phase,stamp in (('start',100),('stop',6_000_000_300)) for i in range(3)]
    requests=[]
    for i,status in enumerate((200,503,0,0)):
        requests.append(dict(ID=i,StatusCode=status,Error='' if status else 'cancelled',TimedOut=i==2,
            ScheduledOffsetNs=0,DispatchLagNs=0,HeadersOffsetNs=3_000_000_000))
    client=dict(total_scheduled=4,requests=requests,clock_anchors=anchors,client_test_start_ns=200,
                elapsed_including_drain_sec=6)
    entries=[dict(id=i,entry_ns=1_000_001_200+i*10,exit_ns=2_000_001_200+i*10,admitted=i!=1)
             for i in range(3)]
    server=dict(entry_protocol='all-outcomes-v1',runtime_variant='stock',clock_generation=1,
        runtime_capture=False,custom_recording=False,worker_yield=False,active_handlers=0,queue_len=0,
        completed=2,admitted=2,rejected=1,entry_events=entries,events=[dict(id=0),dict(id=2)],
        handler_events=[dict(id=0,entry_ns=entries[0]['entry_ns'])])
    return client,server


def screen_rows():
    rows=[]
    for block in range(1,5):
        for g in (2,1):
            rows.append(dict(run_id=f'b{block}_g{g}',rep=block,gomaxprocs=g,trace_coverage=1,
                certainly_long_entry_rate=.2 if g==2 else .05,possibly_long_entry_rate=.2 if g==2 else .06,
                p99_e2e_ms=4000 if g==2 else 1000,successful_rps=100,failure_fraction=0,
                cpu_usec_per_completed_work=4000 if g==2 else 3500))
    return rows


class ParallelismTests(unittest.TestCase):
    def test_all_outcomes_request_zero_and_unknown_entry_are_retained(self):
        client,server=fixture();result=analysis.entry_analysis(client,server)
        self.assertEqual(result['entry_count'],3);self.assertEqual(result['missing_entry_count'],1)
        self.assertEqual([r['outcome'] for r in result['requests']],['success','rejected','timeout','error'])
        self.assertIsNone(result['requests'][3]['scheduled_to_entry_lower_ns'])
        self.assertEqual(result['mapping']['uncertainty_ns'],20)
        self.assertEqual(result['certainly_long_entry_count'],2)
        self.assertEqual(result['possibly_long_entry_count'],4)
        self.assertEqual(result['horizons_seconds']['1']['possible_entered'],3)

    def test_generation_drift_wide_brackets_duplicate_anchors_fail(self):
        for change in ('generation','drift','wide','duplicate','start'):
            client,server=fixture()
            if change=='generation':client['clock_anchors'][-1]['generation']=2
            elif change=='drift':client['clock_anchors'][-1]['server_ns']+=100
            elif change=='wide':
                for a in client['clock_anchors']:a['after_ns']+=2_000_000
                client['client_test_start_ns']+=3_000_000
                for a in client['clock_anchors'][3:]:a['before_ns']+=3_000_000;a['after_ns']+=3_000_000;a['server_ns']+=3_000_000
            elif change=='duplicate':client['clock_anchors'][-1]['label']='stop_0'
            else:client['clock_anchors'][0]['after_ns']=201
            with self.assertRaises(ValueError,msg=change):analysis.clock_mapping(client,server)

    def test_contradictory_duplicate_missing_success_and_impossible_clock_fail(self):
        for change in ('duplicate','success','admission','causal','timing','observer'):
            client,server=fixture()
            if change=='duplicate':server['entry_events'][2]['id']=0
            elif change=='success':client['requests'][3].update(StatusCode=200,Error='')
            elif change=='admission':server['entry_events'][1]['admitted']=True
            elif change=='causal':client['requests'][0]['DispatchLagNs']=4_000_000_000
            elif change=='timing':server['handler_events'][0]['entry_ns']+=1
            else:server['custom_recording']=True
            with self.assertRaises(ValueError,msg=change):analysis.entry_analysis(client,server)

    def test_balanced_matrix_only_parallelism_changes_and_stock_image_shared(self):
        plan=study.matrix(dict(images=dict(service='stock-image')))
        self.assertEqual([c['gomaxprocs'] for c in plan],[2,1,1,2,1,2,2,1])
        self.assertEqual(len({c['run_id'] for c in plan}),8)
        fixed=('workers','period_us','quota_us','iterations','rate','burst_low','burst_high',
               'duration_sec','warmup_sec','service_image','runtime_trace','custom_recording','worker_yield')
        self.assertEqual(len({tuple(c[k] for k in fixed) for c in plan}),1)
        for c in plan:
            self.assertEqual((c['workers'],c['duration_sec'],c['warmup_sec']),(4,60,20))
            self.assertFalse(c['runtime_trace'] or c['custom_recording'] or c['worker_yield'])

    def test_screen_bounds_missing_baseline_failure_and_capacity_reporting(self):
        rows=screen_rows();screen=analysis.comparison(rows)
        self.assertTrue(screen['passed']);self.assertEqual(screen['cpu_per_job_ratio'],.875)
        rows[1]['possibly_long_entry_rate']=.21
        self.assertFalse(analysis.comparison(rows)['passed'])
        rows=screen_rows();rows[1].update(trace_coverage=None,p99_e2e_ms=None,cpu_usec_per_completed_work=None)
        self.assertEqual(analysis.comparison(rows)['interpretation'],'inconclusive')
        rows=screen_rows();rows[0]['certainly_long_entry_rate']=0
        self.assertEqual(analysis.comparison(rows)['interpretation'],'inconclusive')
        rows=screen_rows()
        for r in rows:
            if r['gomaxprocs']==1:r['failure_fraction']=.002
        self.assertFalse(analysis.comparison(rows)['passed'])

    def test_source_transformation_keeps_success_timings_and_stock_runtime(self):
        original=(run.HERE/'service/main.go').read_text();source=build.service_source(original)
        self.assertIn('entryEvent{ID:id',source)
        self.assertIn('case <-r.Context().Done()',source)
        self.assertIn('s.entries = nil',source)
        self.assertIn('timing = &handlerEvent',source)
        self.assertNotIn('researchObserveDecisions',source)
        client=build.client_source((run.HERE/'loadgen/main.go').read_text())
        self.assertIn('arrivalOffset(scheduledCount',client)
        self.assertIn('clockSamples(clockOrigin, *targetURL, "start")',client)
        self.assertIn('ClockAnchors: anchors',client)

    def test_quiet_guard_prevents_spawn(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(study.pipeline,'is_running',return_value=False),\
            patch.object(run,'require_quiet_host',side_effect=ValueError('desktop present')),\
            patch.object(study.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'desktop'):study.launch(Path(tmp))
            spawn.assert_not_called()

    def test_frozen_session_rejects_source_matrix_build_and_fixture_tampering(self):
        for changed in ('source','matrix','prepared','fixture'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);bundle=root/'build';(bundle/'prepared').mkdir(parents=True)
                (bundle/'prepared/main.go').write_text('stock fixture')
                (bundle/'loadgen').write_bytes(b'fixture')
                value=dict(images=dict(service='fixture'),prepared_sha256=build.prepared_hashes(bundle/'prepared'),
                           loadgen_sha256=run.sha(bundle/'loadgen'))
                run.put(bundle/'build.json',value)
                run.put(bundle/'functional_verification.json',dict(files_sha256={}))
                with patch.object(build,'DEFAULT',bundle),patch.object(run,'require_quiet_host'),\
                    patch.object(study,'time_offsets'),patch.object(run.old,'check_topology',return_value={}),\
                    patch.object(run,'capture',return_value='fixture'),patch.object(run,'power_settings',return_value={}):
                    session=root/'session';study.create(session,value)
                    self.assertEqual(study.verify_session(session,current=False)['study'],'bursty_parallelism_v1')
                    target={'source':session/'source/diagnostic/parallelism_study.py',
                            'matrix':session/'matrix.json','prepared':session/'stock_build/prepared/main.go',
                            'fixture':session/'stock_build/functional_verification.json'}[changed]
                    target.write_text(target.read_text()+'\n')
                    with self.assertRaises(ValueError,msg=changed):study.verify_session(session,current=False)

    def test_shifted_time_namespace_is_refused(self):
        with patch.object(Path,'read_text',return_value='monotonic 0 0\nboottime 0 0\n'):
            self.assertEqual(study.time_offsets()['monotonic'],[0,0])
        for text in ('monotonic 1 0\nboottime 0 0\n','monotonic 0 0\n'):
            with patch.object(Path,'read_text',return_value=text):
                with self.assertRaises(ValueError):study.time_offsets()

    def test_progress_reads_completed_current_phase_and_temperatures(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(progress.pipeline,'is_running',return_value=True),\
            patch.object(run.old,'temperatures',return_value={'k10temp:Tctl':43.5}):
            directory=Path(tmp);session=directory/'session'
            run.put(directory/'workflow-status.json',dict(state='running',stage='collect-8-trials',created_at=run.now()))
            run.put(session/'status.json',dict(completed=3,total=8,state='running',current='parallelism_b2_g2'))
            run.put(session/'environment.json',dict(baseline_c={'k10temp:Tctl':40.0}))
            attempt=session/'attempts/parallelism_b2_g2/001'
            run.put(attempt/'started.json',dict(at=run.now()))
            run.put(attempt/'settling.json',dict(accepted=False,policy={'window_sec':60},samples=[dict(elapsed_sec=30)]))
            value=progress.snapshot(directory)
            self.assertEqual((value['completed'],value['percent'],value['phase']),(3,37.5,'trial cooling / settling'))
            self.assertEqual(value['temperatures'],{'k10temp:Tctl':43.5})
            run.put(attempt/'settling.json',dict(accepted=True))
            self.assertEqual(progress.snapshot(directory)['phase'],'service startup / warmup (20 s)')
            (attempt/'monitor.log').touch()
            self.assertEqual(progress.snapshot(directory)['phase'],'measurement (60 s) / client drain')
            run.put(attempt/'loadgen.json',{})
            self.assertEqual(progress.snapshot(directory)['phase'],'draining / exporting / validating')
            output=io.StringIO()
            with contextlib.redirect_stdout(output):progress.print_progress(value)
            self.assertIn('3/8 complete (37.5%)',output.getvalue())
            self.assertIn('43.5°C',output.getvalue());self.assertIn('40.0°C',output.getvalue())

    def test_progress_initial_idle_and_dead_process_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run.old,'temperatures',return_value={}):
            directory=Path(tmp);session=directory/'session'
            run.put(directory/'workflow-status.json',dict(state='running',stage='collect-8-trials',created_at=run.now()))
            run.put(session/'initial-settling.json',dict(accepted=False,policy={'initial_idle_sec':600},
                                                      samples=[dict(elapsed_sec=120)]))
            with patch.object(progress.pipeline,'is_running',return_value=True):
                value=progress.snapshot(directory)
                self.assertEqual(value['phase'],'initial / resume idle and cooling')
                self.assertEqual(value['settling_minimum_sec'],600)
            with patch.object(progress.pipeline,'is_running',return_value=False):
                self.assertEqual(progress.snapshot(directory)['state'],'interrupted')

    def test_watch_interrupt_only_closes_read_only_display(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run.old,'temperatures',return_value={}),\
            patch.object(progress.os,'sched_setaffinity') as affinity,\
            patch.object(progress.time,'sleep',side_effect=KeyboardInterrupt),\
            patch.object(study,'launch') as launch,contextlib.redirect_stdout(io.StringIO()) as output:
            progress.watch(Path(tmp))
            launch.assert_not_called();affinity.assert_called_once_with(0,{0,1})
            self.assertIn('background experiment continues',output.getvalue())


if __name__=='__main__':unittest.main()
