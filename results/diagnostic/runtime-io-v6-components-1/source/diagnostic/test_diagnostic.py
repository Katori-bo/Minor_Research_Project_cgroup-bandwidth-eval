"""No workload is launched by these configuration and analysis checks."""
import unittest
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import analyze
import run
import pipeline
import trace_analysis
from analysis import completed
from environment_controls import external_power_settings


class DiagnosticPlanTests(unittest.TestCase):
    def test_trace_clock_mapping_and_goroutine_states(self):
        captured = [dict(label='start', before_ns=100, after_ns=110),
                    dict(label='stop', before_ns=300, after_ns=310)]
        mapped = trace_analysis.clock_map(captured, {'start': 1105, 'stop': 1305})
        self.assertEqual((mapped['offset_low_ns'], mapped['offset_high_ns']), (995, 1005))
        self.assertEqual(trace_analysis.state_durations(
            [(1000, 'Running', ''), (1010, 'Runnable', ''),
             (1020, 'Waiting', 'network'), (1030, 'Running', '')], 1005, 1035),
            {'go_running_ns': 10, 'runnable_ns': 10, 'network_wait_ns': 10})
        with self.assertRaises(ValueError):
            trace_analysis.clock_map(captured, {'start': 1105, 'stop': 1405})

    def test_response_event_validates_ids_order_and_preserves_write_failures(self):
        worker = dict(id=7, admission_ns=2, completion_ns=5)
        handler = dict(id=7, entry_ns=1, admission_ns=2, resume_ns=6,
                       pre_admission_ns=1, post_work_wait_ns=1, write_start_ns=7,
                       write_end_ns=8, handler_exit_ns=9, write_calls=1,
                       write_bytes=30, write_error='')
        self.assertTrue(run.response_event_valid(handler, worker))
        self.assertFalse(run.response_event_valid(dict(handler, id=8), worker))
        self.assertFalse(run.response_event_valid(dict(handler, write_end_ns=10), worker))
        self.assertFalse(run.response_event_valid(dict(handler, handler_exit_ns=-1), worker))
        self.assertFalse(run.response_event_valid(dict(handler, write_calls=0), worker))
        self.assertFalse(run.response_event_valid({}, worker))
        self.assertFalse(run.response_event_valid(handler, None))
        self.assertTrue(run.response_event_valid(dict(handler, write_bytes=0, write_error='broken pipe'), worker))

    def test_signed_difference_retains_overlap_and_uses_matching_request(self):
        handler = dict(entry_ns=10, resume_ns=30, write_start_ns=40, write_end_ns=90, handler_exit_ns=110)
        values = analyze.response_durations(dict(EndToEndLatencyNs=80), handler)
        self.assertEqual(values['e2e_minus_handler_span'], -20)
        self.assertEqual(values['write_call'], 50)
        self.assertEqual(values['write_to_exit'], 20)

    def test_trial_analysis_joins_ids_before_quantiles(self):
        requests = []
        handlers = []
        for request_id, e2e, span in ((7, 1000, 800), (2, 900, 100)):
            requests.append(dict(ID=request_id, StatusCode=200, Error='', TimedOut=False,
                TraceIssue='', ServerTimingPresent=True, PreAdmissionNs=0, QueueWaitNs=10_000_000,
                ProcessingNs=10_000_000, PostWorkWaitNs=30_000_000, EndToEndLatencyNs=e2e*1_000_000,
                GotConnOffsetNs=10, WroteRequestOffsetNs=20, FirstByteOffsetNs=e2e*1_000_000-100,
                HeadersOffsetNs=e2e*1_000_000-50, BodyDoneOffsetNs=e2e*1_000_000))
            handlers.append(dict(id=request_id, entry_ns=0, resume_ns=50_000_000,
                write_start_ns=60_000_000, write_end_ns=70_000_000, handler_exit_ns=span*1_000_000,
                write_error=''))
        source = {'loadgen.json': dict(requests=requests, total_scheduled=2, total_success=2,
                    total_503=0, client_cpu_usec=100),
                  'server_metrics.json': dict(handler_events=list(reversed(handlers)), completed=2,
                    queue_max=1, client_gone_at_completion=0),
                  'result.json': dict(cpu_usage_cores=.5, throttling_fraction=.5,
                    cgroup_delta=dict(usage_usec=100))}
        config = run.matrix()[0]
        with patch.object(run, 'read', side_effect=lambda p: source[p.name]):
            row = analyze.trial_row(1, config, Path('/tmp/001'))
        self.assertEqual(row['p99_e2e_minus_handler_span_ms'], 800)
        self.assertAlmostEqual(row['top1pct_e2e_minus_handler_span_share'], .2)
        self.assertEqual(row['negative_handler_difference_count'], 0)
        source['server_metrics.json']['handler_events'] = handlers[:1]
        with patch.object(run, 'read', side_effect=lambda p: source[p.name]), self.assertRaises(KeyError):
            analyze.trial_row(1, config, Path('/tmp/001'))
        source['server_metrics.json']['handler_events'] = []
        for request in requests:
            request.update(ServerTimingPresent=False, TraceIssue='disabled')
        with patch.object(run, 'read', side_effect=lambda p: source[p.name]):
            row = analyze.trial_row(1, dict(config, instrument=False, client_trace=False), Path('/tmp/001'))
        self.assertIsNone(row['p99_write_call_ms'])
        self.assertIsNone(row['p99_e2e_minus_handler_span_ms'])
        self.assertIsNone(row['top1pct_e2e_minus_handler_span_share'])

    def test_pipeline_stops_after_pilot_unless_full_requested(self):
        for full_collection in (False, True):
            with TemporaryDirectory() as name:
                directory = Path(name)
                stages = []
                def stage(root, kind, command, lock):
                    stages.append(kind)
                    if kind == 'pilot-collection':
                        (root / 'pilot').mkdir()
                        run.put(root / 'pilot/matrix.json', run.pilot_matrix())
                with patch.object(pipeline, 'stage_command', side_effect=stage), \
                     patch.object(pipeline, 'collection_command', return_value=['collect']), \
                     patch.object(run, 'verify_build'), patch.object(run, 'require_pilot'), \
                     patch.object(pipeline, 'write_completion') as full_completion:
                    pipeline.execute(directory, None, full_collection=full_collection)
                self.assertEqual('full-collection' in stages, full_collection)
                self.assertEqual(full_completion.called, full_collection)
                self.assertEqual((directory / 'PILOT_COMPLETED.md').exists(), not full_collection)

    def test_completed_audit_recomputes_raw_outcomes_and_detects_changed_evidence(self):
        requests = [dict(StatusCode=200, Error='', EndToEndLatencyNs=n, TimedOut=False)
                    for n in (1_000_000, 2_000_000)]
        requests += [dict(StatusCode=503, Error='', TimedOut=False),
                     dict(StatusCode=0, Error='timeout', TimedOut=True)]
        raw = dict(requests=requests, total_success=2, total_503=1, total_completed=4, total_scheduled=4)
        summary = completed.summarize_trial(run.matrix()[0], raw,
                    dict(cgroup_delta=dict(nr_periods=10, nr_throttled=7)))
        self.assertEqual(summary['p99_e2e_ms'], 2)
        self.assertEqual(summary['rejection_fraction'], .25)
        self.assertEqual(summary['timeout_fraction'], .25)
        with TemporaryDirectory() as name:
            directory = Path(name)
            evidence = directory / 'loadgen.json'
            evidence.write_text(json.dumps(raw))
            run.put(directory / 'complete.json', dict(schema=3,
                files={'loadgen.json': hashlib.sha256(evidence.read_bytes()).hexdigest()}))
            completed.verify_attempt(directory)
            evidence.write_text('{}')
            with self.assertRaises(ValueError):
                completed.verify_attempt(directory)

    def test_offline_usb_power_source_does_not_change_power_record(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, kind, online in [('ACAD', 'Mains', '1'),
                                       ('ucsi-source-psy-USBC000:001', 'USB', '0')]:
                supply = root / name
                supply.mkdir()
                (supply / 'type').write_text(kind)
                (supply / 'online').write_text(online)
            self.assertEqual(external_power_settings(root.iterdir()), {'ACAD': '1'})
            (root / 'ucsi-source-psy-USBC000:001' / 'online').write_text('1')
            self.assertEqual(external_power_settings(root.iterdir()),
                             {'ACAD': '1', 'ucsi-source-psy-USBC000:001': '1'})
            (root / 'ACAD' / 'online').write_text('0')
            self.assertEqual(external_power_settings(root.iterdir())['ACAD'], '0')

    def test_client_launch_preserves_flags_after_trace_toggle(self):
        for enabled in (True, False):
            config = dict(run.matrix()[0], client_trace=enabled)
            with TemporaryDirectory() as directory, patch.object(run.sp, 'Popen') as popen:
                popen.return_value.wait.return_value = 0
                popen.return_value.poll.return_value = 0
                output = Path(directory) / 'client.json'
                run.run_client(config, 1, output)
                args = popen.call_args.args[0]
                self.assertIn(f'-trace-client={str(enabled).lower()}', args)
                self.assertNotIn('-trace-client', args)
                self.assertEqual(args[args.index('-output') + 1], str(output))
                self.assertEqual(args[args.index('-burst-period') + 1], '10s')

    def test_frozen_matrix_and_pilot(self):
        rows = run.matrix()
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({r['run_id'] for r in rows}), 20)
        self.assertEqual(run.matrix(), rows)
        self.assertEqual({(r['period_us'], r['workers']) for r in rows},
                         {(100000, 1), (100000, 4), (250000, 1), (250000, 4)})
        for row in rows:
            self.assertEqual(row['quota_us'] * 2, row['period_us'])
            self.assertEqual((row['gomaxprocs'], row['pattern'], row['rate']), (2, 'bursty', 113.21))
            self.assertTrue(row['client_trace'])
            self.assertEqual((row['warmup_sec'], row['duration_sec'], row['timeout_sec']), (20, 60, 5))
        pilot = run.pilot_matrix()
        self.assertEqual(len(pilot), 6)
        self.assertEqual([r['runtime_trace'] for r in pilot[:4]], [True, False, False, True])
        self.assertTrue(all(r['instrument'] and r['client_trace'] for r in pilot))
        self.assertEqual({(r['period_us'], r['workers']) for r in pilot if r['runtime_trace']},
                         {(100000, 1), (100000, 4)})

    def test_interaction_uses_trials_as_units(self):
        cells = {(100, 1): [1.0] * 5, (100, 4): [5.0] * 5,
                 (250, 1): [2.0] * 5, (250, 4): [4.0] * 5}
        self.assertEqual(analyze.interaction(cells), 2.0)
        self.assertEqual(analyze.boot(cells, analyze.interaction), [2.0, 2.0])

    def test_pilot_gate_rejects_missing_timing_and_excess_overhead(self):
        fields = dict(p99_e2e_ms=100., client_cpu_usec_per_scheduled=10.,
                      trace_coverage=1., p99_pre_admission_ms=.01, p99_post_work_ms=.01,
                      p99_resume_to_write_ms=.01, p99_write_call_ms=.01,
                      p99_write_to_exit_ms=.01,
                      p99_request_to_first_byte_ms=1., p99_first_byte_to_body_done_ms=.01,
                      runtime_trace_complete=True, rejection_fraction=0., timeout_fraction=0.)
        rows = [dict(run_id=f'trace_overhead_{i}', period_ms=100., workers=4,
                     instrument=True, runtime_trace=on, cpu_usec_per_completed_work=100,
                     **fields) for i, on in enumerate((True, False, False, True), 1)]
        rows += [dict(run_id=f'trace_p100000_w1_{"on" if on else "off"}', period_ms=100., workers=1,
                     instrument=True, runtime_trace=on, cpu_usec_per_completed_work=100,
                     **fields) for on in (True, False)]
        self.assertTrue(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['cpu_usec_per_completed_work'] = 130
        rows[3]['cpu_usec_per_completed_work'] = 130
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['cpu_usec_per_completed_work'] = 100
        rows[3]['cpu_usec_per_completed_work'] = 100
        rows[0]['client_cpu_usec_per_scheduled'] = 13
        rows[3]['client_cpu_usec_per_scheduled'] = 13
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['client_cpu_usec_per_scheduled'] = 10
        rows[3]['client_cpu_usec_per_scheduled'] = 10
        rows[0]['p99_e2e_ms'] = 130
        rows[3]['p99_e2e_ms'] = 130
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['p99_e2e_ms'] = 100
        rows[3]['p99_e2e_ms'] = 100
        rows[4]['p99_post_work_ms'] = None
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[4]['p99_post_work_ms'] = .01
        rows[4]['p99_write_call_ms'] = None
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[4]['p99_write_call_ms'] = .01
        rows[0]['rejection_fraction'] = .01
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])


if __name__ == '__main__':
    unittest.main()
