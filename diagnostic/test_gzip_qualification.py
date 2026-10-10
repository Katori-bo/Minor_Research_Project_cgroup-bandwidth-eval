"""Failure-focused tests for full bodies, native identity proofs and paired gates."""
import copy
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import gzip_qualify as q


def fixture():
    correct = q.read(q.selection.BASE / 'correctness/result.json')
    row = dict(ID='measurement-0', EchoID='measurement-0', ScheduledNs=0, DispatchNs=5,
        HeadersNs=46, BodyDoneNs=50, Status=200, Error='', TimingError='', QueueNs=10,
        ProcessNs=20, BodyBytes=correct['output_bytes'], BodySHA256=correct['output_sha256'], ContentType='application/gzip')
    client = dict(Schema='gzip-client-v1', Count=1, IntervalNs=200000000, Rows=[row])
    event = dict(ID='measurement-0', EnqueuedNs=2, AcquiredNs=12, SpawnBeforeNs=15,
        SpawnAfterNs=17, DrainedNs=30, ReapedNs=32, ResponseBeforeNs=35, ResponseAfterNs=40,
        ReleasedNs=42, Success=True)
    auditrow = dict(ID='measurement-0', PID=3, StartTicks=123, PIDFD=True, AffinityCPU2=True,
        CgroupSame=True, SingleThreadAtGate=True, ExecSucceeded=True, Reaped=True,
        ExitCode=0, BodyBytes=correct['output_bytes'], Success=True)
    common = dict(Schema='gzip-service-v1', Observed=True, Capacity=1024, Overflow=0,
        Started=1, Completed=1, Queued=0, ActivePID=0, ParentPID=1)
    return client, dict(common, Records=[event]), dict(common, Records=[auditrow])


class NativeTests(unittest.TestCase):
    def test_complete_gzip_body_and_raw_join(self):
        client, events, audit = fixture()
        q.validate_client(client, 'measurement', 1, True)
        q.validate_audit(audit, {'measurement-0'}, True)
        self.assertEqual(q.join(client, events)['total_process_ns'], 20)

    def test_wrong_body_type_hash_id_size_and_incomplete_body_fail(self):
        for key, value in [('ContentType', 'image/jpeg'), ('BodySHA256', 'wrong'), ('BodyBytes', 1),
                           ('EchoID', 'wrong'), ('Error', 'unexpected EOF'), ('BodyDoneNs', 4)]:
            client, _, _ = fixture(); client['Rows'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): q.validate_client(client, 'measurement', 1, True)

    def test_native_gate_identity_exec_reap_failures(self):
        for key, value in [('PIDFD', False), ('StartTicks', 0), ('AffinityCPU2', False),
                           ('CgroupSame', False), ('SingleThreadAtGate', False),
                           ('ExecSucceeded', False), ('Reaped', False), ('ExitCode', 1)]:
            _, _, audit = fixture(); audit['Records'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): q.validate_audit(audit, {'measurement-0'}, True)

    def test_overflow_duplicate_or_active_job_rejected(self):
        for kind in ('overflow', 'duplicate', 'active'):
            _, _, audit = fixture()
            if kind == 'overflow': audit['Overflow'] = 1
            if kind == 'duplicate': audit['Records'].append(copy.deepcopy(audit['Records'][0]))
            if kind == 'active': audit['ActivePID'] = 3
            with self.subTest(kind=kind), self.assertRaises(ValueError): q.validate_audit(audit, {'measurement-0'}, True)

    def test_negative_residual_reversed_stage_and_header_mismatch(self):
        for kind in ('residual', 'stage', 'header'):
            client, events, _ = fixture()
            if kind == 'residual': client['Rows'][0]['BodyDoneNs'] = 34
            if kind == 'stage': events['Records'][0]['DrainedNs'] = 14
            if kind == 'header': client['Rows'][0]['QueueNs'] = 9
            with self.subTest(kind=kind), self.assertRaises(ValueError): q.join(client, events)

    def test_overlapping_workers_rejected(self):
        client, events, _ = fixture()
        other = dict(events['Records'][0], ID='other', AcquiredNs=13)
        events['Records'].append(other)
        with self.assertRaisesRegex(ValueError, 'one-worker'): q.join(client, events)


class OwnershipTests(unittest.TestCase):
    def test_wrong_nonce_never_removes(self):
        value = subprocess.CompletedProcess([], 0, '[{"Config":{"Labels":{"' + q.LABEL + '":"other"}}}]', '')
        with patch.object(q.subprocess, 'run', return_value=value), patch.object(q, 'cmd') as mutate:
            with self.assertRaises(ValueError): q.remove_owned('name', 'ours')
            mutate.assert_not_called()

    def test_cleanup_uses_immutable_id(self):
        with patch.object(q, 'inspect_owned', side_effect=[{'Id': 'immutable'}, None]), patch.object(q, 'cmd') as mutate:
            q.remove_owned('name', 'nonce'); mutate.assert_called_once_with(['docker', 'rm', '-f', 'immutable'])

    def test_owner_death_stops_owned_client_and_container(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            q.save(p / 'ownership.json', dict(owner={'pid': 1, 'start_ticks': 1}, container='owned', nonce='nonce', deadline_monotonic=1e30))
            q.save(p / 'client-ownership.json', dict(pid=2, start_ticks=2))
            with patch.object(q.helpers, 'same_owner', side_effect=[False, True, False]), \
                 patch.object(q, 'remove_owned') as remove, patch.object(q.os, 'killpg') as stop:
                q.watchdog(p)
                remove.assert_called_once_with('owned', 'nonce'); stop.assert_called_once_with(2, q.signal.SIGKILL)
            self.assertTrue(q.read(p / 'watchdog-cleanup.json')['invalidated'])

    def test_unknown_process_rejected_before_inspection(self):
        with tempfile.TemporaryDirectory() as name:
            group = Path(name); (group / 'cgroup.procs').write_text('1 2 3')
            with patch.object(q.helpers, 'process_identity', return_value={'pid': 1, 'start_ticks': 1}):
                with self.assertRaisesRegex(ValueError, 'multiple native'):
                    q.scan_group(1, group, {'pid': 1, 'start_ticks': 1}, {}, 'reference')

    def test_live_one_cpu_scan_rejects_affinity_change_and_pid_reuse(self):
        for mode in ('valid', 'affinity', 'reuse'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                group = Path(name); (group / 'cgroup.procs').write_text('1')
                owner = {'pid': 1, 'start_ticks': 1}
                before = dict(owner, parent=0); after = dict(before, start_ticks=2) if mode == 'reuse' else before
                with patch.object(q.helpers, 'process_identity', return_value=owner), \
                     patch.object(q, 'proc_identity', side_effect=[before, after]), \
                     patch.object(q.helpers.bridge, 'cgroup', return_value=group), \
                     patch.object(q, 'sha', return_value='server'), \
                     patch.object(Path, 'iterdir', return_value=iter([Path('/proc/1/task/1')])), \
                     patch.object(q.os, 'sched_getaffinity', return_value={2, 4} if mode == 'affinity' else {2}):
                    if mode == 'valid':
                        self.assertEqual(q.scan_group(1, group, owner, {'binaries': {'reference': 'server'}}, 'reference')['affinity'], [2])
                    else:
                        with self.assertRaisesRegex(ValueError, 'resource mismatch|PID reused'):
                            q.scan_group(1, group, owner, {'binaries': {'reference': 'server'}}, 'reference')


class CostTests(unittest.TestCase):
    def rows(self, changes):
        return [dict(pair=i, arm=arm, cpu_per_offer_usec=100 * (1 + value), median_e2e_ns=1000 * (1 + value))
            for i, change in enumerate(changes, 1) for arm, value in [('reference', 0), ('observed', change)]]

    def test_small_overhead_and_large_uncertainty(self):
        self.assertTrue(q.paired_effects(self.rows([.01] * 6))['cpu_per_offer_usec']['upper_le_5pct'])
        self.assertFalse(q.paired_effects(self.rows([-.1, .1] * 3))['cpu_per_offer_usec']['upper_le_5pct'])

    def test_missing_pair_or_nonpositive_endpoint(self):
        rows = self.rows([.01] * 6)
        with self.assertRaises(ValueError): q.paired_effects(rows[:-1])
        rows[0]['cpu_per_offer_usec'] = 0
        with self.assertRaises(ValueError): q.paired_effects(rows)


class PreservationTests(unittest.TestCase):
    def case(self, directory, throttles=0, dispatch=5):
        client, _, audit = fixture()
        client['Rows'][0]['DispatchNs'] = dispatch
        client['Rows'][0]['HeadersNs'] = dispatch + 41
        client['Rows'][0]['BodyDoneNs'] = dispatch + 45
        warmup = dict(client, Count=25, Rows=[])
        for i in range(25):
            row = dict(client['Rows'][0], ID=f'warmup-{i}', EchoID=f'warmup-{i}')
            for key in ('ScheduledNs', 'DispatchNs', 'HeadersNs', 'BodyDoneNs'):
                row[key] += i * 200000000
            warmup['Rows'].append(row)
        ids = ['image-check'] + [r['ID'] for r in warmup['Rows']] + ['measurement-0']
        audit.update(Observed=False, Started=27, Completed=27,
                     Records=[dict(audit['Records'][0], ID=name) for name in ids])
        counters = dict(before={'usage_usec': 0, 'nr_throttled': 0},
                        after={'usage_usec': 100, 'nr_throttled': throttles},
                        delta={'usage_usec': 100, 'nr_throttled': throttles})
        for name, value in [('measurement', client), ('warmup', warmup), ('audit', audit),
                            ('measurement-counters', counters)]:
            q.save(directory / (name + '.json'), value)

    def test_throttle_is_retained_in_preparation_and_fails_pilot(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory, throttles=1)
            self.assertEqual(q.analyze(directory, 'reference', 1, False)['domain_exits'], ['measurement_throttling'])
            with self.assertRaisesRegex(ValueError, 'measurement_throttling.*no replacement'):
                q.analyze(directory, 'reference', 1, True)
            self.assertEqual(q.read(directory / 'measurement-counters.json')['delta']['nr_throttled'], 1)

    def test_dispatch_failure_applies_to_reference_arm(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory, dispatch=11000000)
            with self.assertRaisesRegex(ValueError, 'dispatch_gate'):
                q.analyze(directory, 'reference', 1, True)

    def test_corrupt_counter_difference_cannot_be_annotated_away(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory)
            value = q.read(directory / 'measurement-counters.json'); value['delta']['usage_usec'] = 99
            q.save(directory / 'measurement-counters.json', value)
            with self.assertRaisesRegex(ValueError, 'counter differences'):
                q.analyze(directory, 'reference', 1, False)

    def test_failed_domain_gate_exports_raw_records_before_cleanup(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name) / 'case'; order = []
            body = (q.selection.BASE / 'correctness/compress-1.gz').read_bytes()
            with patch.object(q, 'Service') as service_type, \
                 patch.object(q.helpers, 'fetch', return_value=(body, {})), \
                 patch.object(q.helpers.fixtures, 'stat', return_value={'usage_usec': 0, 'nr_throttled': 0}), \
                 patch.object(q, 'analyze', side_effect=lambda *a: (order.append('gate'), q.require(False, 'measurement_throttling'))[-1]):
                service = service_type.return_value
                service.guard.return_value = {}
                service.export.side_effect = lambda: (order.append('export'), q.save(directory / 'audit.json', {'retained': True}))
                service.close.side_effect = lambda: order.append('cleanup')
                with self.assertRaisesRegex(ValueError, 'measurement_throttling'):
                    q.trial(directory, 'reference', 1, True)
            self.assertEqual(order, ['export', 'gate', 'cleanup'])
            self.assertTrue(q.read(directory / 'audit.json')['retained'])
            self.assertIn('measurement_throttling', q.read(directory / 'failure.json')['error'])


if __name__ == '__main__': unittest.main()
