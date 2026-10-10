"""Failure-focused checks for the new single-CPU contract and evidence retention."""
from pathlib import Path
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import imgproxy_one_cpu_qualify as one

q = one.q


class OneCpuTests(unittest.TestCase):
    def test_creation_retains_pinned_image_and_budget(self):
        service = types.SimpleNamespace(name='owned', nonce='nonce', arm='observed', image='sha256:pinned')
        argv = one.create_argv(service, Path('/tmp/gate'))
        for flag, value in (('--cpuset-cpus', '2'), ('--cpu-period', '100000'),
                            ('--cpu-quota', '25000'), ('--pids-limit', '128')):
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertEqual(argv[-1], 'sha256:pinned')
        self.assertNotIn('--privileged', argv)
        self.assertIn('IMGPROXY_QUALIFICATION=1', argv)
        self.assertIn('GOMAXPROCS=1', argv)
        self.assertIn('IMGPROXY_WORKERS=1', argv)

    def test_runtime_guard_rejects_added_cpu(self):
        with tempfile.TemporaryDirectory() as name:
            group = Path(name)
            for key, value in one.LIMITS.items():
                (group / key).write_text(value)
            (group / 'cgroup.procs').write_text('123')
            service = one.Service.__new__(one.Service)
            service.limits = dict(one.LIMITS)
            service.started = time.monotonic()
            service.performance = False
            service.identity = {'pid': 123, 'start_ticks': 1}
            service.pid = 123
            service.group = group
            service.watcher = types.SimpleNamespace(poll=lambda: None)
            with patch.object(q, 'same_owner', return_value=True), patch.object(q.bridge, 'cgroup', return_value=group):
                service.guard()
                (group / 'cpuset.cpus.effective').write_text('2,4')
                with self.assertRaisesRegex(ValueError, 'resources'):
                    service.guard()

    def test_partial_and_overflow_events_saved_before_rejection(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'events.json'
            service = types.SimpleNamespace(guard=lambda: None, base='http://local')
            raw = b'{"Records":[],"Overflow":1}'
            with patch.object(q, 'fetch', return_value=(raw, {})), patch.object(one.time, 'monotonic', side_effect=[0, 4]):
                with self.assertRaisesRegex(ValueError, 'Incomplete'):
                    one.export_preserved(service, path, 226)
            self.assertEqual(q.read(path), {'Records': [], 'Overflow': 1})

    def test_domain_failure_keeps_export_before_cleanup(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name) / 'observed'
            steps = []

            class FakeService:
                pid = 123
                group = Path('/unused')
                base = 'http://local'

                def __init__(self, *args): pass
                def start(self): steps.append('start')
                def collect(self, prefix, count): steps.append(prefix)
                def close(self): steps.append('close')

            def export(service, path, expected):
                steps.append('export')
                q.save(path, dict(Records=['retained']))

            def classify(*args):
                steps.append('classify')
                self.assertTrue((directory / 'events.json').exists())
                raise ValueError('Measurement throttling; no replacement allowed')

            image = types.SimpleNamespace(load=lambda: None, format='JPEG', size=(300, 300))
            with patch.object(one, 'Service', FakeService), patch.object(one, 'source_hashes', return_value={}), \
                 patch.object(q, 'fetch', return_value=(b'jpeg', {})), patch('PIL.Image.open', return_value=image), \
                 patch.object(q.bridge, 'snapshot', return_value={}), patch.object(q.fixtures, 'stat', return_value={'nr_throttled': 1}), \
                 patch.object(one, 'export_preserved', side_effect=export), patch.object(one, 'classify_case', side_effect=classify):
                with self.assertRaisesRegex(ValueError, 'Measurement throttling'):
                    one.trial(directory, 'observed', True)
            self.assertEqual(steps, ['start', 'warmup', 'measurement', 'export', 'classify', 'close'])
            self.assertEqual(q.read(directory / 'events.json')['Records'], ['retained'])
            self.assertTrue((directory / 'failure.json').exists())

    def test_early_failure_retains_partial_export(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name) / 'observed'
            closed = []

            class FakeService:
                base = 'http://local'
                def __init__(self, *args): pass
                def start(self): raise RuntimeError('startup failed after port obtained')
                def close(self): closed.append(True)

            def export(service, path, expected):
                self.assertEqual(expected, 0)
                q.save(path, dict(Records=[]))

            with patch.object(one, 'Service', FakeService), patch.object(one, 'source_hashes', return_value={}), \
                 patch.object(one, 'export_preserved', side_effect=export):
                with self.assertRaisesRegex(RuntimeError, 'startup failed'):
                    one.trial(directory, 'observed', True)
            self.assertEqual(closed, [True])
            self.assertTrue((directory / 'events.json').exists())

    def test_incomplete_pilot_cannot_replay_as_success(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            (base / 'pilot').mkdir()
            q.save(base / 'pilot/summary.json', dict(status='qualification_unavailable'))
            with patch.object(one, 'BASE', base), patch.object(one, 'verify'):
                with self.assertRaisesRegex(ValueError, 'incomplete/unavailable'):
                    one.replay()

    def test_measured_throttle_remains_a_hard_gate(self):
        with tempfile.TemporaryDirectory() as name:
            case = Path(name)
            body = (q.BASE / 'functional/attempt-03/stock/output.jpg').read_bytes()
            (case / 'output.jpg').write_bytes(body)
            digest = q.prep.sha(case / 'output.jpg')
            for prefix, count in (('warmup', 25), ('measurement', 200)):
                rows = []
                for i in range(count):
                    scheduled = i * 200000000
                    rows.append(dict(ID=f'{prefix}-{i}', EchoID=f'{prefix}-{i}',
                        ScheduledNs=scheduled, DispatchNs=scheduled + 5, HeadersNs=scheduled + 46,
                        BodyDoneNs=scheduled + 50, Status=200, Error='', ContentType='image/jpeg',
                        BodySHA256=digest, BodyBytes=len(body)))
                q.save(case / (prefix + '.json'), dict(Schema='imgproxy-client-v1', Count=count,
                    IntervalNs=200000000, Rows=rows))
            q.save(case / 'measurement-counters.json', dict(before={'usage_usec': 0, 'nr_throttled': 2},
                after={'usage_usec': 100, 'nr_throttled': 3}, delta={'usage_usec': 100, 'nr_throttled': 1}))
            with self.assertRaisesRegex(ValueError, 'Measurement throttling'):
                one.classify_case(case, 'stock', True)
            # Startup/warmup throttles alone do not invalidate a zero-delta measurement.
            q.save(case / 'measurement-counters.json', dict(before={'usage_usec': 0, 'nr_throttled': 2},
                after={'usage_usec': 100, 'nr_throttled': 2}, delta={'usage_usec': 100, 'nr_throttled': 0}))
            self.assertEqual(one.classify_case(case, 'stock', True)['recorded_throttled_periods'], 0)

    def test_functional_stage_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as name:
            base = Path(name)
            (base / 'functional').mkdir()
            q.save(base / 'protocol.json', one.PROTOCOL)
            with patch.object(one, 'BASE', base), patch.object(one, 'historical_inputs'), patch.object(one, 'trial') as trial:
                with self.assertRaises(FileExistsError): one.functional()
                trial.assert_not_called()

    def test_new_seal_rejects_source_changes(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            base = root / 'new'
            base.mkdir()
            (root / 'runner.py').write_text('changed')
            q.save(base / 'bundle-seal.json', dict(protocol=one.PROTOCOL, baseline=q.common.baseline(),
                files_sha256={'runner.py': 'not-the-hash'}))
            with patch.object(one, 'ROOT', root), patch.object(one, 'BASE', base), patch.object(one, 'historical_inputs'):
                with self.assertRaisesRegex(ValueError, 'sealed input changed'):
                    one.verify()


if __name__ == '__main__': unittest.main()
