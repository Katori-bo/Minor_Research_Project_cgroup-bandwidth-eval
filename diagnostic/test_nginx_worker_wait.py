"""Counter/chronology/equivalence oracles and fake-service orchestration only."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nginx_worker_wait_common as c
import nginx_worker_wait_model as m
import nginx_worker_wait_study as run


EXPECTED = dict(pid=31, parent=30, start_ticks=70, exe_sha256='hash')


def stat(pid=31, parent=30, ticks=70, state='S', cpu=2):
    fields = ['0'] * 50
    fields[0], fields[1], fields[19], fields[36] = state, str(parent), str(ticks), str(cpu)
    return str(pid) + ' (worker (test)) ' + ' '.join(fields)


def snap(at, running, wait, slices):
    text = f'{running} {wait} {slices}\n'
    return dict(read_started_ns=at, read_finished_ns=at + 10, stat_before=stat(),
                stat_after=stat(), schedstat_raw=text, counters=m.w.parse_schedstat(text))


def evidence():
    b = snap(0, 100000000, 1000000, 10)
    a = snap(1000000000, 600000000, 1100000, 40)
    idle = snap(1100000020, 600100000, 1101000, 41)
    events = dict(warmup_call_started_ns=20, warmup_call_finished_ns=900000000,
        feature_saved_ns=1000000100, status_started_ns=1100000040,
        status_finished_ns=1100000050, decision_sealed_ns=1100000060, measurement_started_ns=1100000070)
    return dict(before=b, after=a, idle_after=idle, events=events, observer_wall_ns=75,
                operations=[dict(started_ns=0, finished_ns=15),
                            dict(started_ns=999999990, finished_ns=1000000050)])


def rows(schedule, miss_gain=0, mean_gain=0, warm_gain=0, miss_base=80):
    return [dict(config=cfg, measurement_miss_pct=miss_base + (miss_gain if cfg['arm'] == 'on' else 0),
                 measurement_mean_ns=20000000 + (mean_gain if cfg['arm'] == 'on' else 0),
                 warmup_mean_ns=20000000 + (warm_gain if cfg['arm'] == 'on' else 0))
            for cfg in schedule['overhead']]


class QualificationTests(unittest.TestCase):
    def test_schedule_exact_pairs_and_budget(self):
        s = c.schedule(1)
        self.assertEqual(s, c.schedule(1))
        self.assertEqual(len(s['overhead']), 24)
        self.assertEqual(sum(x['count'] + 25 for group in ('boundary', 'overhead') for x in s[group]), 7890)
        for b in range(1, 7):
            for rate in (4, 8):
                pair = [x for x in s['overhead'] if x['block'] == b and x['rate_rps'] == rate]
                self.assertEqual({x['arm'] for x in pair}, {'off', 'on'})

    def test_task_stat_parentheses(self):
        r = m.parse_task_stat(stat())
        self.assertEqual((r['pid'], r['parent'], r['start_ticks'], r['processor']), (31, 30, 70, 2))

    def test_identity_and_quiescence(self):
        for text in (stat(ticks=71), stat(parent=29), stat(state='R'), stat(cpu=3)):
            s = snap(0, 1, 1, 1); s['stat_after'] = text
            with self.assertRaises(ValueError): m.check_snapshot(s, EXPECTED)

    def test_counter_raw_and_read_duration(self):
        s = snap(0, 1, 1, 1); s['counters']['running_ns'] = 2
        with self.assertRaises(ValueError): m.check_snapshot(s, EXPECTED)
        s = snap(0, 1, 1, 1); s['read_finished_ns'] = 2000001
        with self.assertRaises(ValueError): m.check_snapshot(s, EXPECTED)

    def test_valid_boundary_remains_provisional(self):
        result = m.check_boundary(evidence(), EXPECTED, 500000)
        self.assertTrue(result['operational_boundary_checks'])
        self.assertFalse(result['absolute_wait_accuracy_verified'])
        self.assertFalse(result['feature']['hardware_qualified'])

    def test_reversed_counters(self):
        e = evidence(); e['after'] = snap(1000000000, 90000000, 1000000, 40)
        with self.assertRaises(ValueError): m.check_boundary(e, EXPECTED, 500000)

    def test_health_request_before_snapshot_fails(self):
        e = evidence(); e['events']['status_started_ns'] = e['after']['read_started_ns'] - 1
        with self.assertRaises(ValueError): m.check_boundary(e, EXPECTED, 500000)

    def test_future_measurement_before_decision_fails(self):
        e = evidence(); e['events']['measurement_started_ns'] = e['events']['decision_sealed_ns'] - 1
        with self.assertRaises(ValueError): m.check_boundary(e, EXPECTED, 500000)

    def test_cpu_residual_and_idle_carryover(self):
        with self.assertRaises(ValueError): m.check_boundary(evidence(), EXPECTED, 503000)
        e = evidence(); e['idle_after'] = snap(1100000020, 600300000, 1101000, 41)
        with self.assertRaises(ValueError): m.check_boundary(e, EXPECTED, 500000)

    def test_observer_budget(self):
        e = evidence(); e['observer_wall_ns'] = 20000001
        with self.assertRaises(ValueError): m.check_boundary(e, EXPECTED, 500000)

    def test_zero_wait_can_be_valid_without_assurance(self):
        e = evidence()
        e['after'] = snap(1000000000, 600000000, 1000000, 40)
        e['idle_after'] = snap(1100000020, 600100000, 1000000, 41)
        result = m.check_boundary(e, EXPECTED, 500000)
        self.assertEqual(result['feature']['runnable_wait_ns_per_offer'], 0)
        self.assertFalse(result['feature']['hardware_qualified'])

    def test_equivalence_requires_interval_inside_margin(self):
        s = c.schedule(2)
        self.assertTrue(m.compare(rows(s), s)['qualified'])
        self.assertFalse(m.compare(rows(s, miss_gain=2.01), s)['qualified'])
        self.assertFalse(m.compare(rows(s, mean_gain=100001), s)['qualified'])
        self.assertFalse(m.compare(rows(s, warm_gain=-100001), s)['qualified'])

    def test_zero_mean_with_wide_interval_inconclusive(self):
        r = m.interval([-3, 3, -3, 3, -3, 3], 2)
        self.assertEqual(r['mean'], 0)
        self.assertFalse(r['equivalence_supported'])

    def test_missing_pair_and_saturated_endpoint(self):
        s = c.schedule(3)
        with self.assertRaises(ValueError): m.compare(rows(s)[:-1], s)
        self.assertFalse(m.compare(rows(s, miss_base=0), s)['qualified'])

    def test_t_multiplier_coverage(self):
        # Exact df5 t CDF from integrating cos(theta)^4, theta=atan(t/sqrt(5)).
        theta = math.atan(c.PROTOCOL['paired_t_multiplier'] / math.sqrt(5))
        cdf = .5 + theta / math.pi + 2 * math.sin(2 * theta) / (3 * math.pi) + math.sin(4 * theta) / (12 * math.pi)
        self.assertLessEqual(2 * (1 - cdf), .005)


class OrchestrationTests(unittest.TestCase):
    def check_arm(self, arm):
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp) / 'case'
            cfg = c.cfg('overhead', 1, 4, arm, 1)
            events = []; captures = []
            scan = dict(main_pid=30, vanished_during_scan=False, processes=[
                dict(pid=30, parent=9, start_ticks=60, tids=[30], affinity=[2], exe_sha256='hash'),
                dict(pid=31, parent=30, start_ticks=70, tids=[31], affinity=[2], exe_sha256='hash')])

            class FakeService:
                def __init__(self, directory, performance, cfg):
                    self.directory = directory; self.requests = 0
                    self.manifest = dict(nginx_sha256='hash'); self.group = Path(temp)
                def start(self): events.append('start')
                def guard(self): return scan
                def status(self):
                    events.append('status'); self.requests += 1
                    return dict(active=1, reading=0, writing=1, waiting=0, requests=self.requests)
                def collect(self, phase, count):
                    events.append(phase)
                    if phase == 'measurement':
                        self_test.assertTrue((case / 'decision-boundary.json').exists())
                        self_test.assertEqual((case / 'worker-before.json').exists(), arm == 'on')
                        self_test.assertEqual((case / 'provisional-feature.json').exists(), arm == 'on')
                    self.requests += count
                    c.save(case / (phase + '.json'), {})
                def close(self): events.append('close')

            def fake_capture(case, name, expected):
                captures.append(name); events.append(name)
                value = snap(run.time.monotonic_ns(), 100000000 if name.endswith('before') else 600000000,
                             1000000 if name.endswith('before') else 1100000,
                             10 if name.endswith('before') else 40)
                c.save(case / (name + '.json'), value)
                return value

            self_test = self
            counters = iter([dict(usage_usec=0), dict(usage_usec=500000),
                             dict(usage_usec=500000), dict(usage_usec=1000000)])
            with patch.object(run, 'check_live', return_value={}), patch.object(run.h, 'desktop_absent'), \
                 patch.object(run.time, 'sleep'), patch.object(run.reuse.old, 'Service', FakeService), \
                 patch.object(run.reuse, 'offer_budget'), patch.object(run.h.fixtures, 'stat', side_effect=lambda _: next(counters)), \
                 patch.object(run, 'capture', side_effect=fake_capture), \
                 patch.object(run.reuse.m, 'outcomes', return_value=[dict(success=True)] * 25), \
                 patch.object(run.reuse, 'integrity_exits', return_value=[]), \
                 patch.object(run, 'analyze', return_value=dict(domain_exits=[])), \
                 patch.object(run, 'identity'), patch.object(run.q, 'evidence_seal'):
                run.trial(case, cfg)
            self.assertEqual(captures, ['worker-before', 'worker-after'] if arm == 'on' else [])
            if arm == 'on':
                self.assertLess(events.index('worker-before'), events.index('warmup'))
                self.assertLess(events.index('warmup'), events.index('worker-after'))
                self.assertEqual(events[events.index('worker-after') + 1], 'status')
            self.assertEqual(events[-1], 'close')

    def test_observer_on_actual_call_order_with_fake_service(self): self.check_arm('on')
    def test_observer_off_has_no_counter_capture(self): self.check_arm('off')


if __name__ == '__main__': unittest.main()
