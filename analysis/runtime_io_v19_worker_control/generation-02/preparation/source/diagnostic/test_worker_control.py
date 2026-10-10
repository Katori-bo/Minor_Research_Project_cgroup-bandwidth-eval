"""V19 accounting, prospective decision and ownership regressions; no Docker calls."""
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

import worker_control_common as c
import worker_control_analysis as a
import worker_control_service as service
import worker_control_study as runner
import verify_worker_control as verify
import parallelism_analysis


def retained():
    report = c.read(c.V18/'analysis/1791136492141213329/report.json')
    d = c.V18/report['attempts']['p1_off']['path']
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


class ProtocolTests(unittest.TestCase):
    def test_all_permutations_position_and_pair_balance(self):
        matrix = c.matrix()
        self.assertEqual(len(matrix), 18)
        self.assertEqual([v['order'] for v in matrix], list(range(1, 19)))
        for arm in c.ARMS:
            self.assertEqual([sum(order[i] == arm for order in c.ORDERS) for i in range(3)], [2]*3)
        for x, y in [('four_a', 'four_b'), ('four_a', 'one'), ('four_b', 'one')]:
            self.assertEqual(sum(order.index(x) < order.index(y) for order in c.ORDERS), 3)
        self.assertEqual(len({tuple(order) for order in c.ORDERS}), 6)

    def test_only_worker_count_changes(self):
        args = [c.service_argv('original', Path('/qualification'), 'owned', config) for config in c.matrix()[:3]]
        self.assertEqual(args[0], args[1])
        altered = args[2].copy()
        altered[altered.index('WORKERS=1')] = 'WORKERS=4'
        self.assertEqual(altered, args[0])
        for argv in args:
            self.assertNotIn('--memory', argv)
            self.assertNotIn('--pids-limit', argv)
            self.assertNotIn('--user', argv)

    def test_invalid_configuration(self):
        for mutation in ({'workers': 2}, {'workers': True}, {'duration_sec': 59}, {'arm': 'off'}):
            with self.assertRaises(ValueError):
                c.validate_config(dict(c.matrix()[0], **mutation))

    def test_no_docker_or_root_tracing_in_offline_verifier(self):
        text = Path(verify.__file__).read_text()
        self.assertNotIn('import worker_control_study', text)
        self.assertNotIn('subprocess', text)
        self.assertNotIn('bpftrace', Path(service.__file__).read_text())

    def test_resource_defaults_preserved(self):
        previous = c.read(c.V18/'preparation/manifest.json')['resource_baseline']
        c.validate_resources(previous['limits'], previous['host_config'], previous)
        with self.assertRaises(ValueError):
            c.validate_resources(dict(previous['limits'], **{'pids.max': '128'}), previous['host_config'], previous)
        with self.assertRaises(ValueError):
            c.validate_resources(dict(previous['limits'], **{'cpu.max': '100000 100000'}), previous['host_config'], previous)

    def test_live_status_does_not_replay_or_hash(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(c, 'verify_seal', side_effect=AssertionError('live hash')), patch.object(a, 'replay', side_effect=AssertionError('live replay')):
            runner.status(Path(tmp))

    def test_resume_retains_valid_unfavorable_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = Path(tmp)
            config = c.matrix()[0]
            d = session/'trials'/config['trial']/'attempt-1'
            c.save(d/'complete.json', dict(valid=True))
            c.save(d/'derived.json', dict(summary=dict(timely_500_fraction=0)))
            c.seal(d)
            self.assertEqual(len(runner.pending(session, 'resume')), 17)
            self.assertNotIn(config['trial'], [q['trial'] for q in runner.pending(session, 'resume')])
            (d/'added').write_text('tamper')
            with self.assertRaises(ValueError):
                runner.pending(session, 'resume')

    def test_safe_reference_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ('../outside', '/tmp/outside'):
                with self.assertRaises(ValueError):
                    c.resolve(Path(tmp), bad)


class AccountingTests(unittest.TestCase):
    def test_v18_untraced_crossovers_reproduce_with_tighter_clocks(self):
        report = c.read(c.V18/'analysis/1791136492141213329/report.json')
        total = 0
        for pair in range(1, 7):
            d = c.V18/report['attempts'][f'p{pair}_off']['path']
            rows, mapping, logical = a.join(c.read(d/'loadgen.json'), c.read(d/'server_metrics.json'), c.matrix()[0])
            crossing = [r for r in rows if r['deadline_class'] == 'computed_before_handler_resumed_after']
            total += len(crossing)
            self.assertTrue(all(r['work_starts_inside_gap'] > 0 for r in crossing))
            self.assertEqual(len(rows), 6793)
        self.assertEqual(total, 3565)

    def test_rejection_cancellation_drop_and_unknown_http_retained(self):
        client, server, vector = fixture_data()
        config = c.fixture('four_a')
        q = {q['ID']: q for q in client['requests']}
        q[1].update(StatusCode=503)
        q[2].update(StatusCode=0, Error='request timeout', TimedOut=True)
        q[4].update(StatusCode=500)
        client['requests'] = [v for v in client['requests'] if v['ID'] != 3]
        client['client_dropped'] = 1
        for key in ('events', 'handler_events'):
            server[key] = [r for r in server[key] if r['id'] not in (1, 3)]
        server['handler_events'] = [r for r in server['handler_events'] if r['id'] != 2]
        server['entry_events'] = [r for r in server['entry_events'] if r['id'] != 3]
        next(e for e in server['entry_events'] if e['id'] == 1)['admitted'] = False
        totals(client, server)
        with patch.object(c, 'arrivals', return_value=vector):
            rows, mapping, logical = a.join(client, server, config)
        self.assertEqual([r['outcome'] for r in rows], ['success', 'rejected', 'timeout', 'client_dropped', 'error', 'success'])
        self.assertEqual(len(rows), 6)
        self.assertIsNone(rows[2]['completion_to_resume_ns'])
        self.assertIsNotNone(rows[2]['completion_after_offered_upper_ns'])
        self.assertIsNone(rows[3]['e2e_ns'])
        self.assertIn('inferred', rows[3]['schedule_observation'])
        self.assertFalse(any(r['timely_500'] for r in rows[1:5]))

    def test_exact_deadline_and_conservative_ambiguous_bounds(self):
        client, server, vector = fixture_data()
        move_completion(client, server, 1, 490, 510, 550)
        move_completion(client, server, 2, 500, 520, 550)
        move_completion(client, server, 3, 500.01, 520, 550)
        move_completion(client, server, 4, 490, 500, 550)
        move_completion(client, server, 5, 450, 475, 500)
        with patch.object(c, 'arrivals', return_value=vector):
            rows, mapping, logical = a.join(client, server, c.fixture('four_a'))
        self.assertEqual(rows[1]['deadline_class'], 'computed_before_handler_resumed_after')
        self.assertEqual(rows[2]['deadline_class'], 'computed_before_handler_resumed_after')
        self.assertEqual(rows[3]['deadline_class'], 'computation_boundary_ambiguous')
        self.assertEqual(rows[4]['deadline_class'], 'handler_resumed_before_client_finished_after')
        self.assertEqual(rows[5]['deadline_class'], 'timely')

    def test_missing_successful_markers_are_capture_loss(self):
        client, server, vector = fixture_data()
        server['handler_events'].pop()
        with patch.object(c, 'arrivals', return_value=vector), self.assertRaisesRegex(ValueError, 'successful response lacks'):
            a.join(client, server, c.fixture('four_a'))

    def test_count_id_generation_and_duration_mutations(self):
        for mutation in ('count', 'duplicate', 'schedule', 'generation', 'processing'):
            client, server, vector = fixture_data()
            if mutation == 'count':
                client['total_success'] -= 1
            elif mutation == 'duplicate':
                client['requests'][1]['ID'] = 0
            elif mutation == 'schedule':
                client['requests'][1]['ScheduledOffsetNs'] += 1
            elif mutation == 'generation':
                client['clock_anchors'][0]['generation'] += 1
            else:
                server['events'][0]['processing_ns'] += 1
            with patch.object(c, 'arrivals', return_value=vector), self.assertRaises(ValueError):
                a.join(client, server, c.fixture('four_a'))

    def test_unexplained_missing_client_row_rejected(self):
        client, server, vector = fixture_data()
        client['requests'].pop()
        with patch.object(c, 'arrivals', return_value=vector), self.assertRaisesRegex(ValueError, 'dropped offers'):
            a.join(client, server, c.fixture('four_a'))

    def test_cpu_counter_window_and_all_offer_denominator(self):
        config = c.matrix()[0]
        rows = [dict(success=True, timely_500=True, timely_1000=True, e2e_ns=1_000_000,
            worker_observed=True, handler_observed=True, completion_to_resume_ns=1,
            deadline_class='timely', outcome='success', drained_response=False),
            dict(success=False, timely_500=False, timely_1000=False, e2e_ns=None,
            worker_observed=False, handler_observed=False, completion_to_resume_ns=None,
            deadline_class='unsuccessful', outcome='client_dropped', drained_response=False)]
        for r in rows:
            r.update(queue_ns=None, processing_wall_ns=None, scheduled_to_entry_upper_ns=None, resume_to_client_upper_ns=None)
        obs = dict(measurement_start=dict(before_ns=1, after_ns=2, cpu_stat=dict(usage_usec=100)),
                   measurement_stop=dict(before_ns=3, after_ns=4, cpu_stat=dict(usage_usec=700)))
        client = dict(elapsed_including_drain_sec=60, client_dropped=1, missed_arrivals=1, client_cpu_usec=100)
        value = a.summarize(config, client, dict(completed=1), rows, dict(uncertainty_ns=1), {}, obs)
        self.assertEqual(value['failure_fraction'], .5)
        self.assertEqual(value['timely_500_fraction'], .5)
        self.assertEqual(value['cpu_usec_per_completed_work'], 600)
        self.assertEqual(value['p99_e2e_ms'], 1)
        obs['measurement_stop']['cpu_stat']['usage_usec'] = 99
        with self.assertRaises(ValueError):
            a.summarize(config, client, dict(completed=1), rows, dict(uncertainty_ns=1), {}, obs)

    def test_logical_backlog_area_and_nonzero_missing_bounds(self):
        self.assertEqual(a.backlog([(0, 10), (5, 15)]), dict(peak=2, request_seconds=20/1e9))
        with self.assertRaises(ValueError):
            a.backlog([(5, 4)])
        self.assertEqual(a.distribution([None, 10, 20])['n'], 2)


class DecisionTests(unittest.TestCase):
    def rows(self):
        return [dict(block=b, arm=arm, timely_500_fraction=.8 if arm != 'one' else .85,
            timely_1000_fraction=1, failure_fraction=0, cpu_usec_per_completed_work=3500,
            p99_e2e_ms=750, gap_gt50ms_fraction=.4 if arm != 'one' else .1,
            crossover_fraction=.08 if arm != 'one' else .02) for b in range(1, 7) for arm in c.ARMS]

    def test_useful_signal_is_block_based_and_all_criteria_hold(self):
        report = a.compare(self.rows())
        self.assertEqual(report['decision'], 'useful_worker_control_with_gap_signal')
        self.assertTrue(report['eligible_for_independent_confirmation'])
        self.assertEqual(report['primary_mean_ci95']['degrees_of_freedom'], 5)
        self.assertEqual(report['block_statistics']['timely_500_delta']['n'], 6)

    def test_one_aa_failure_cannot_hide_in_mean(self):
        rows = self.rows()
        rows[1]['timely_500_fraction'] += .02
        report = a.compare(rows)
        self.assertEqual(report['decision'], 'inconclusive_repeatability')
        self.assertFalse(report['eligible_for_independent_confirmation'])

    def test_guardrail_failure_and_missing_p99_do_not_hide_outcomes(self):
        rows = self.rows()
        rows[2]['failure_fraction'] = .002
        self.assertEqual(a.compare(rows)['decision'], 'guardrail_failure')
        rows = self.rows()
        rows[2]['p99_e2e_ms'] = None
        report = a.compare(rows)
        self.assertTrue(report['complete_evidence'])
        self.assertEqual(report['decision'], 'guardrail_failure')

    def test_gap_only_and_primary_only(self):
        rows = self.rows()
        for r in rows:
            if r['arm'] == 'one':
                r['timely_500_fraction'] = .805
        self.assertEqual(a.compare(rows)['decision'], 'gap_reduction_without_useful_deadline_gain')
        rows = self.rows()
        for r in rows:
            r['gap_gt50ms_fraction'] = .4
            r['crossover_fraction'] = .08
        self.assertEqual(a.compare(rows)['decision'], 'useful_worker_control_without_gap_signal')

    def test_incomplete_duplicate_and_interrupted(self):
        self.assertEqual(a.compare(self.rows()[:-1])['decision'], 'incomplete_evidence')
        with self.assertRaises(ValueError):
            a.compare(self.rows()+[self.rows()[0]])
        report = a.compare(self.rows(), [1])
        self.assertEqual(report['decision'], 'inconclusive_interrupted_blocks')
        self.assertFalse(report['eligible_for_independent_confirmation'])

    def test_zero_baseline_does_not_invent_reduction(self):
        rows = self.rows()
        for r in rows:
            r['gap_gt50ms_fraction'] = r['crossover_fraction'] = 0
        report = a.compare(rows)
        self.assertFalse(report['post_computation_signal_pass'])
        self.assertEqual(report['block_statistics']['crossover_fraction_relative_reduction']['n'], 0)

    def test_exact_practical_margins(self):
        rows = self.rows()
        for r in rows:
            if r['arm'] == 'four_b':
                r['timely_500_fraction'] += .01
                r['timely_1000_fraction'] -= .01
                r['failure_fraction'] += .001
                r['cpu_usec_per_completed_work'] *= 1.05
                r['p99_e2e_ms'] *= 1.10
        self.assertTrue(a.compare(rows)['repeatability_pass'])

    def test_small_sample_mean_interval_can_reject_inconsistent_gain(self):
        rows = self.rows()
        effects = [-.15, .075, .075, .075, .075, .075]
        for r in rows:
            if r['arm'] == 'one':
                r['timely_500_fraction'] = .8+effects[r['block']-1]
        report = a.compare(rows)
        self.assertLess(report['primary_mean_ci95']['lower'], 0)
        self.assertFalse(report['primary_signal_pass'])


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
        previous = copy.deepcopy(c.read(c.V18/'preparation/manifest.json'))
        name = next(iter(previous['sources']))
        previous['sources'][name] = 'changed'
        with patch.object(c, 'read', return_value=previous), self.assertRaisesRegex(ValueError, 'V18 frozen source'):
            c.source_hashes()


if __name__ == '__main__':
    unittest.main()
