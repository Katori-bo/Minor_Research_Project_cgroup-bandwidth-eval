"""Regression tests for data integrity, interrupted attempts, and scientific summaries."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze
import run


class SavedTrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='quota-followup-test-')
        self.session = Path(self.temp.name)
        self.config = dict(next(c for c in run.matrix() if c['study'] == 'B' and c['pattern'] == 'steady'), rate=.05)
        self.d = self.session / 'attempts' / self.config['run_id'] / '001'
        self.d.mkdir(parents=True)
        self.power = {'desktop_profile': 'balanced', 'external_power': {'AC': '1'}}
        run.put(self.session / 'environment.json', {'baseline_c': {'package': 40}, 'power_settings': self.power})
        runtime = {'workers': self.config['workers'], 'gomaxprocs': 2, 'queue_cap': 128,
                   'instrument': True, 'go_version': 'go1.26.1'}
        requests = []
        events = []
        for i in range(3):
            requests.append(dict(ID=i, StatusCode=200, Error='', ScheduledOffsetNs=i * 20_000_000_000,
                DispatchLagNs=1000, ServiceLatencyNs=5_999_000, EndToEndLatencyNs=6_000_000,
                CompletedOffsetNs=i * 20_000_000_000 + 6_000_000, QueueWaitNs=1000, ProcessingNs=5_000_000,
                QueueDepth=0, ServerTimingPresent=True, ServerTimingError='', TimedOut=False))
            events.append(dict(id=i, admission_ns=i * 20_000_000_000, worker_start_ns=i * 20_000_000_000 + 1000,
                completion_ns=i * 20_000_000_000 + 5_001_000, queue_wait_ns=1000, processing_ns=5_000_000,
                depth_at_admission=0, client_gone_at_completion=False))
        lg = dict(duration_sec=60, pattern='steady', target_rate=.05, total_scheduled=3,
            total_dispatched=3, total_completed=3, total_success=3, total_503=0, total_errors=0,
            client_dropped=0, missed_arrivals=0, dispatch_lag_summary={'p99_ms': .001},
            requests=requests, successful_throughput_rps=.05)
        srv = dict(runtime, admitted=3, completed=3, rejected=0, client_gone_at_completion=0,
                   active_handlers=0, queue_len=0, queue_max=0, events=events)
        limits = {'/test/cg': {'cpu.max': f"{self.config['quota_us']} {self.config['period_us']}",
            'cpu.max.burst': '0', 'cpuset.cpus.effective': '2,4'}, '/test': {'cpu.max': 'max 100000'}}
        samples = [{'elapsed_sec': second, 'temperatures': {'package': 40},
                    'power_settings': run.comparable_power(self.power)} for second in (0, 60)]
        thermal = run.window_summary(samples, {'package': 40})
        monitor = [{'temps_c': {'package': 40}, 'power_settings': run.comparable_power(self.power),
                    'cgroup_cpu_stat': {'usage_usec': 15000}} for _ in range(42)]
        initial = dict(usage_usec=0, nr_periods=0, nr_throttled=0, throttled_usec=0)
        final = dict(usage_usec=15000, nr_periods=600, nr_throttled=0, throttled_usec=0)
        report = dict(run_id=self.config['run_id'], config=self.config, runtime=runtime, runtime_end=runtime,
            limits=limits, cgroup_path='/test/cg', quality_flags=[], power_before=self.power, power_after=self.power,
            monitor_samples=42, cgroup_initial=initial, cgroup_final=final, cgroup_delta=final, elapsed_sec=60,
            cpu_usage_cores=.00025, throttling_fraction=0, thermal=thermal, server_unseen_dispatched=0,
            measurement_started_at='2026-09-26T00:00:00+00:00')
        for name, value in {'config.json': self.config, 'result.json': report, 'loadgen.json': lg,
            'server_metrics.json': srv, 'limits.json': limits, 'monitor.json': monitor,
            'settling.json': {'accepted': True, 'policy': run.POLICY, 'samples': samples}}.items():
            run.put(self.d / name, value)
        run.complete_attempt(self.d)

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, file, change, reseal=False):
        value = run.read(self.d / file)
        change(value)
        run.put(self.d / file, value)
        if reseal:
            run.complete_attempt(self.d)

    def test_valid_trial_can_be_reused(self):
        self.assertEqual(run.validation_errors(self.d, self.config, False), [])

    def test_changed_file_is_not_silently_reused(self):
        self.mutate('loadgen.json', lambda value: value.update(total_success=0))
        self.assertIn('attempt file hashes changed', run.validation_errors(self.d, self.config, False))

    def test_validation_recomputes_counts_even_with_new_hashes(self):
        self.mutate('loadgen.json', lambda value: value.update(total_success=0), reseal=True)
        self.assertIn('outcome accounting', run.validation_errors(self.d, self.config, False))

    def test_power_change_is_found_even_when_saved_flags_are_empty(self):
        self.mutate('monitor.json', lambda value: value[0].update(power_settings={'external_power': {'AC': '0'}}), reseal=True)
        self.assertTrue(any('power_changed' in e for e in run.validation_errors(self.d, self.config, False)))

    def test_server_timestamps_are_checked(self):
        self.mutate('server_metrics.json', lambda value: value['events'][0].update(completion_ns=0), reseal=True)
        self.assertIn('server event timing', run.validation_errors(self.d, self.config, False))

    def test_failed_attempt_never_counts_as_success(self):
        run.put(self.d / 'failure.json', {'error': 'interrupted'})
        run.complete_attempt(self.d)
        self.assertEqual(run.validation_errors(self.d, self.config, False), ['failed attempt'])

    def test_interrupt_retains_evidence_and_uses_a_new_attempt(self):
        digest = run.sha(self.d / 'loadgen.json')
        (self.d.parent / '003').mkdir()
        self.assertEqual(run.next_attempt(self.d.parent), 4)
        with patch.object(run, 'power_settings', return_value=self.power), patch.object(run.old, 'settle', side_effect=KeyboardInterrupt('test interruption')):
            with self.assertRaises(KeyboardInterrupt):
                run.run_attempt(self.session, self.config, False, 4)
        self.assertTrue((self.d.parent / '004/failure.json').exists())
        self.assertEqual(run.sha(self.d / 'loadgen.json'), digest)
        self.assertEqual(run.next_attempt(self.d.parent), 5)

    def test_missing_completion_marker_is_incomplete(self):
        (self.d / 'complete.json').unlink()
        self.assertFalse(run.validate(self.d, self.config, False))

    def test_throughput_window_excludes_late_responses_but_cohort_retains_them(self):
        def late(value):
            value['requests'][-1]['CompletedOffsetNs'] = 61_000_000_000
        self.mutate('loadgen.json', late)
        row = analyze.trial_row(1, self.config, self.d)
        self.assertAlmostEqual(row['successful_rps'], 2 / 60)
        self.assertAlmostEqual(row['cohort_success_rps'], 3 / 60)


class MechanismAndControlTests(unittest.TestCase):
    def test_drain_waits_for_both_jobs_and_handlers(self):
        states = [dict(admitted=2, completed=1, queue_len=0, active_handlers=0),
                  dict(admitted=2, completed=2, queue_len=0, active_handlers=1),
                  dict(admitted=2, completed=2, queue_len=0, active_handlers=0)]
        with patch.object(run, 'get', side_effect=states) as get, patch.object(run.time, 'sleep'):
            self.assertEqual(run.drain()['completed'], 2)
        self.assertEqual(get.call_count, 3)

    def test_known_interaction_and_bootstrap(self):
        cells = {(100, 1): [10] * 5, (100, 4): [20] * 5, (250, 1): [30] * 5, (250, 4): [30] * 5}
        self.assertEqual(analyze.interaction(cells), 10)
        self.assertAlmostEqual(analyze.ratio_of_ratios(cells), 2)
        self.assertEqual(analyze.boot(cells, analyze.interaction), [10, 10])

    def test_constant_environment_does_not_crash_analysis(self):
        self.assertIsNone(analyze.correlation([1, 2, 3], [40, 40, 40]))
        self.assertIsNone(analyze.correlation([1], [3]))

    def test_full_analysis_keeps_studies_and_traffic_patterns_separate(self):
        rows = []
        for order, config in enumerate(run.matrix(), 1):
            row = dict(config, period_ms=config['period_us'] / 1000, order=order, start_temp_c=40,
                       p99_e2e_ms=10 * config['workers'],
                       p99_processing_all_completed_ms=config['gomaxprocs'],
                       server_completed_rps_including_server_drain=100, successful_rps=100)
            rows.append(row)
        result = analyze.summarize_full(rows)
        self.assertEqual(result['steady']['interaction_ms'], 0)
        self.assertEqual(result['bursty']['interaction_ms'], 0)
        self.assertEqual(result['A']['p99_processing_all_completed_ms']['g2_minus_g1'], 1)
        self.assertIsNone(result['collection_order']['correlation_temperature_within_condition_log_p99_residual'])
        next(r for r in rows if r['study'] == 'B' and r['pattern'] == 'steady')['p99_e2e_ms'] = None
        next(r for r in rows if r['study'] == 'A')['p99_processing_all_completed_ms'] = None
        missing = analyze.summarize_full(rows)
        self.assertIn('unavailable', missing['steady'])
        self.assertIn('unavailable', missing['A']['p99_processing_all_completed_ms'])

    def test_matrix_retains_extension_and_loads_replication(self):
        rows = run.matrix()
        self.assertEqual(len(rows), 50)
        self.assertEqual(len({r['run_id'] for r in rows}), 50)
        b = [r for r in rows if r['study'] == 'B']
        self.assertEqual(len(b), 40)
        self.assertTrue(all(r['rate'] == 113.21 and r['gomaxprocs'] == 2 and 2 * r['quota_us'] == r['period_us'] for r in b))
        a = [r for r in rows if r['study'] == 'A']
        self.assertTrue(all(r['rate'] == 176.41 for r in a))
        self.assertEqual(len(run.pilot_matrix()), 8)

    def test_pilot_overhead_gate(self):
        rows = []
        for i, enabled in enumerate((True, False, False, True)):
            rows.append(dict(run_id=f'pilot_overhead_{i}', instrument=enabled, study='B',
                cpu_usec_per_completed_work=120 if enabled else 100,
                p99_queue_success_ms=1, p99_processing_success_ms=1))
        rows += [dict(run_id=f'A{g}', study='A', instrument=True, cpu_cores=.5,
                      p99_queue_success_ms=1, p99_processing_success_ms=1) for g in (1, 2)]
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])


if __name__ == '__main__':
    unittest.main()
