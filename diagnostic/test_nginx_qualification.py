"""Failure-focused guards for stock application, complete gzip bodies and accounting."""
import copy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import nginx_qualify as q
n = q.n


def client(prefix='measurement', count=1):
    rows = []
    for i in range(count):
        scheduled = i * 200000000
        rows.append(dict(ID=f'{prefix}-{i}', EchoID=f'{prefix}-{i}', ScheduledNs=scheduled,
            DispatchNs=scheduled + 5, HeadersNs=scheduled + 30, BodyDoneNs=scheduled + 50,
            Error='', DecodeError='', Status=200, ContentEncoding='gzip', ContentType='application/x-ndjson',
            BodyBytes=250000, BodySHA256='a' * 64, DecodedBytes=1048576, DecodedSHA256=n.INPUT_SHA))
    return dict(Schema='nginx-client-v1', Count=count, IntervalNs=200000000, Rows=rows)


def status(requests=10, **extra):
    return dict(active=1, accepts=requests, handled=requests, requests=requests,
                reading=0, writing=1, waiting=0, **extra)


class BodyTests(unittest.TestCase):
    def test_complete_compressed_and_decoded_body(self):
        self.assertEqual(q.validate_client(client(), 'measurement', 1)['offers'], 1)

    def test_bad_compression_decoding_hash_identity_or_incomplete_body(self):
        for key, value in [('ContentEncoding', ''), ('DecodeError', 'checksum mismatch'),
            ('DecodedSHA256', 'bad'), ('DecodedBytes', 3), ('BodyBytes', 2097153),
            ('Error', 'unexpected EOF'), ('EchoID', 'other'), ('BodyDoneNs', 1)]:
            with self.subTest(key=key):
                value_client = client(); value_client['Rows'][0][key] = value
                with self.assertRaises(ValueError): q.validate_client(value_client, 'measurement', 1)

    def test_missing_dropped_or_duplicated_offers_rejected(self):
        for mode in ('missing', 'dropped', 'duplicate'):
            value = client(count=2)
            if mode == 'missing': value['Rows'].pop()
            if mode == 'dropped': value['Rows'][1]['Error'] = 'client in-flight cap reached'
            if mode == 'duplicate': value['Rows'][1] = copy.deepcopy(value['Rows'][0])
            with self.subTest(mode=mode), self.assertRaises(ValueError): q.validate_client(value, 'measurement', 2)

    def test_client_overlap_is_descriptive_and_not_server_queue(self):
        value = client(count=2); value['Rows'][0]['BodyDoneNs'] = 300000000
        result = q.validate_client(value, 'measurement', 2)
        self.assertEqual(result['max_simultaneous_client_response_windows'], 2)
        self.assertNotIn('queue_le_100us_fraction', result)


class AccountingTests(unittest.TestCase):
    def case(self, directory, throttles=0):
        for name, value in [('measurement', client()), ('warmup', client('warmup', 25)),
            ('status-window', {'before': status(10), 'after_checks': [status(12)]}),
            ('measurement-counters', dict(before={'usage_usec': 0, 'nr_throttled': 0},
                after={'usage_usec': 100, 'nr_throttled': throttles},
                delta={'usage_usec': 100, 'nr_throttled': throttles}))]:
            n.save(directory / (name + '.json'), value)

    def test_stock_status_parse_and_drain(self):
        value = q.parse_status(b'Active connections: 1 \nserver accepts handled requests\n 10 10 10 \nReading: 0 Writing: 1 Waiting: 0 \n')
        self.assertTrue(q.drained(value))
        with self.assertRaises(ValueError): q.parse_status(b'unexpected response')

    def test_throttle_annotated_in_preparation_and_rejected_externally(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory, 1)
            self.assertEqual(q.analyze(directory, 1, False)['domain_exits'], ['measurement_throttling'])
            with self.assertRaisesRegex(ValueError, 'measurement_throttling.*no replacement'):
                q.analyze(directory, 1, True)

    def test_extra_request_or_undrained_worker_rejected(self):
        for mode in ('extra', 'active'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                directory = Path(name); self.case(directory)
                value = n.read(directory / 'status-window.json')
                value['after_checks'][0]['requests' if mode == 'extra' else 'writing'] += 1
                n.save(directory / 'status-window.json', value)
                with self.assertRaises(ValueError): q.analyze(directory, 1, False)

    def test_multiple_drain_queries_counted_without_hiding_extra_work(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory)
            value = n.read(directory / 'status-window.json')
            value['after_checks'] = [dict(status(12), writing=2, active=2), status(13)]
            n.save(directory / 'status-window.json', value)
            self.assertTrue(q.analyze(directory, 1, True)['stock_request_conservation'])

    def test_counter_corruption_is_never_a_diagnostic_annotation(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory)
            value = n.read(directory / 'measurement-counters.json'); value['delta']['usage_usec'] = 99
            n.save(directory / 'measurement-counters.json', value)
            with self.assertRaisesRegex(ValueError, 'counter replay'): q.analyze(directory, 1, False)

    def test_dispatch_failure_and_no_imported_queue_claim(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory)
            self.assertFalse(q.analyze(directory, 1, True)['server_queue_observed'])
            value = n.read(directory / 'measurement.json')
            for key in ('DispatchNs', 'HeadersNs', 'BodyDoneNs'): value['Rows'][0][key] += 11000000
            n.save(directory / 'measurement.json', value)
            with self.assertRaisesRegex(ValueError, 'dispatch_gate'): q.analyze(directory, 1, True)


class OwnershipTests(unittest.TestCase):
    def test_wrong_nonce_never_removes(self):
        result = subprocess.CompletedProcess([], 0, '[{"Config":{"Labels":{"' + q.LABEL + '":"other"}}}]', '')
        with patch.object(q.subprocess, 'run', return_value=result), patch.object(q.h, 'cmd') as mutate:
            with self.assertRaises(ValueError): q.remove_owned('owned', 'ours')
            mutate.assert_not_called()

    def test_cleanup_uses_immutable_id(self):
        with patch.object(q, 'inspect_owned', side_effect=[{'Id': 'immutable'}, None]), patch.object(q.h, 'cmd') as mutate:
            q.remove_owned('owned', 'nonce'); mutate.assert_called_once_with(['docker', 'rm', '-f', 'immutable'])

    def test_owned_startup_logs_are_saved_before_container_removal(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); order = []
            service = q.Service(directory, False)
            with patch.object(q, 'inspect_owned', return_value={'Id': 'immutable'}), \
                 patch.object(q.subprocess, 'run', side_effect=lambda *a, **k: (order.append('logs'), subprocess.CompletedProcess([], 0, '', 'startup diagnostic'))[-1]), \
                 patch.object(q, 'remove_owned', side_effect=lambda *a: order.append('remove')):
                service.close()
            self.assertEqual(order, ['logs', 'remove'])
            self.assertEqual(n.read(directory / 'container-logs.json')['stderr'], 'startup diagnostic')

    def test_worker_respawn_or_extra_thread_fails(self):
        for mode in ('valid', 'respawn', 'thread'):
            value = dict(processes=[dict(pid=1, start_ticks=1, tids=[1]), dict(pid=2, start_ticks=2, tids=[2])],
                         vanished_during_scan=[])
            if mode == 'respawn': value['processes'][1]['start_ticks'] = 3
            if mode == 'thread': value['processes'][1]['tids'].append(3)
            with self.subTest(mode=mode), patch.object(n.prior, 'scan_group', return_value=value):
                service = q.Service(Path('/unused'), False)
                service.pid = 1; service.main_identity = {'pid': 1, 'start_ticks': 1}; service.group = Path('/unused')
                service.expected = {'1': 1, '2': 2}
                if mode == 'valid': self.assertEqual(len(service.scan()['processes']), 2)
                else:
                    with self.assertRaises(ValueError): service.scan()

    def test_owner_death_stops_owned_client_and_container(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)
            n.save(directory / 'ownership.json', dict(owner={'pid': 1, 'start_ticks': 1}, container='owned', nonce='nonce', deadline_monotonic=1e30))
            n.save(directory / 'client-ownership.json', dict(pid=2, start_ticks=2))
            with patch.object(q.h, 'same_owner', side_effect=[False, True, False]), \
                 patch.object(q, 'remove_owned') as remove, patch.object(q.os, 'killpg') as stop:
                q.watchdog(directory)
                remove.assert_called_once_with('owned', 'nonce'); stop.assert_called_once_with(2, q.signal.SIGKILL)
            self.assertTrue(n.read(directory / 'watchdog-cleanup.json')['invalidated'])

    def test_failed_gate_preserves_status_counters_and_then_cleans_up(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name) / 'case'; order = []
            def fail(*args):
                self.assertTrue((directory / 'status-window.json').exists())
                self.assertTrue((directory / 'measurement-counters.json').exists())
                order.append('gate'); raise ValueError('measurement_throttling')
            with patch.object(q, 'Service') as factory, patch.object(q.h.fixtures, 'stat', return_value={'usage_usec': 0}), \
                 patch.object(q, 'analyze', side_effect=fail):
                service = factory.return_value; service.guard.return_value = {}
                service.status.side_effect = [status(10), status(12)]
                service.close.side_effect = lambda: order.append('cleanup')
                with self.assertRaisesRegex(ValueError, 'measurement_throttling'): q.trial(directory, 1, True)
            self.assertEqual(order, ['gate', 'cleanup'])
            self.assertIn('measurement_throttling', n.read(directory / 'failure.json')['error'])


if __name__ == '__main__': unittest.main()
