"""Failure-focused policy restoration and forecast provenance tests, no sysfs writes."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nginx_power_common as c
import nginx_power_guard as g
import nginx_power_model as m
import test_nginx_prediction as oldtest


def calibration(schedule):
    return [dict(config=cfg, domain_exits=[], outcomes=[dict(success=True,
        e2e_ns=10000000 if cfg['policy'] == 'P0' else 30000000) for _ in range(400)])
        for cfg in schedule['calibration']]


def validation(schedule):
    return [dict(config=cfg, domain_exits=[], outcomes=[dict(success=True,
        e2e_ns=10000000 if cfg['policy'] == 'P0' else 30000000) for _ in range(300)],
        warmup_outcomes=[dict(success=True, e2e_ns=10000000 if cfg['policy'] == 'P0' else 30000000)
                        for _ in range(25)]) for cfg in schedule['validation']]


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.s = c.schedule(1234)

    def test_randomization_balanced_distinct_indices_and_replay(self):
        self.assertEqual(self.s, c.schedule(1234))
        self.assertEqual([r['index'] for r in self.s['validation']], list(range(1, 25)))
        self.assertEqual([r['policy'] for r in self.s['calibration']].count('P0'), 2)
        for b in range(1, 7):
            self.assertEqual(sorted((r['policy'], r['rate_rps']) for r in self.s['validation']
                                    if r['block'] == b), sorted(c.CELLS))

    def test_calibration_refuses_known_validation_labels_or_missing_samples(self):
        for mode in ('validation', 'missing', 'failure', 'domain'):
            rows = calibration(self.s)
            if mode == 'validation': rows[0]['config'] = self.s['validation'][0]
            if mode == 'missing': rows[0]['outcomes'].pop()
            if mode == 'failure': rows[0]['outcomes'][0]['success'] = False
            if mode == 'domain': rows[0]['domain_exits'] = ['measurement_throttling']
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.fit(rows, self.s)

    def test_strict_deadline_and_failed_offers(self):
        rows = [dict(success=True, e2e_ns=20565395), dict(success=False, e2e_ns=None)]
        self.assertEqual(m.miss_fraction(rows, 20565395), .5)
        self.assertEqual(m.probability([20565394, 20565395, 20565396], 20565395), 1 / 3)

    def test_known_policy_shift_matched_vs_equal_budget_pooled(self):
        f = m.fit(calibration(self.s), self.s)
        result = m.compare(validation(self.s), f, self.s)
        self.assertTrue(result['useful_gain']); self.assertTrue(result['useful_absolute_accuracy'])
        self.assertEqual(result['primary']['methods']['matched']['mean'], 0)
        self.assertEqual(result['primary']['methods']['pooled']['mean'], 50)
        self.assertEqual(len(result['primary']['matched_gain_pp']['blocks']), 6)
        self.assertAlmostEqual(result['primary']['conditional_sharp_null_randomization_p'], 2 / 4096)

    def test_unknown_within_policy_shift_fails_matching(self):
        f = m.fit(calibration(self.s), self.s); rows = validation(self.s)
        for row in rows:
            for o in row['outcomes']: o['e2e_ns'] = 30000000 if row['config']['policy'] == 'P0' else 10000000
        self.assertFalse(m.compare(rows, f, self.s)['useful_absolute_accuracy'])

    def test_reordering_and_incomplete_validation_refused(self):
        f = m.fit(calibration(self.s), self.s)
        for mode in ('missing', 'reorder'):
            rows = validation(self.s)
            if mode == 'missing': rows.pop()
            else: rows[0], rows[1] = rows[1], rows[0]
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.compare(rows, f, self.s)

    def test_warmup_weight_and_unavailable_warmup(self):
        f = m.fit(calibration(self.s), self.s); cfg = self.s['validation'][0]
        warm = [dict(success=True, e2e_ns=30000000) for _ in range(25)]
        pred = m.predictions(f, cfg, warm, 20565395)
        self.assertAlmostEqual(pred['pooled_update'], (800 + 25) / 1625)
        warm[0]['success'] = False
        with self.assertRaises(ValueError): m.predictions(f, cfg, warm, 20565395)

    def test_schedules_parse_original_client_endpoint(self):
        for cfg in self.s['qualification'] + self.s['calibration']:
            self.assertTrue(all(o['success'] for o in m.outcomes(oldtest.client(cfg), cfg)))


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.policies = self.root / 'policies'; self.policies.mkdir()
        for number in (0, 2, 3):
            p = self.policies / f'policy{number}'; p.mkdir()
            values = dict(related_cpus=str(number), affected_cpus=str(number), scaling_driver='amd-pstate-epp',
                scaling_governor='powersave', scaling_min_freq='1000', scaling_max_freq='4000',
                energy_performance_preference='balance_performance')
            for key, value in values.items(): (p / key).write_text(value)
        self.patch = patch.object(g, 'POLICY_ROOT', self.policies); self.patch.start(); self.addCleanup(self.patch.stop)

    def test_only_target_epp_changes_and_full_restoration(self):
        lease = g.Lease(self.root)
        original = copy.deepcopy(lease.original)
        lease.set('P1'); self.assertEqual(g.snapshot(), g.expected(original, 'P1'))
        self.assertTrue(lease.restore('test')['restored']); self.assertEqual(g.snapshot(), original)

    def test_foreign_baseline_refused_before_mutation(self):
        path = self.policies / 'policy2/scaling_governor'; path.write_text('performance')
        original = g.snapshot()
        with self.assertRaises(ValueError): g.Lease(self.root)
        self.assertEqual(g.snapshot(), original)

    def test_shared_policy_scope_refused(self):
        (self.policies / 'policy2/related_cpus').write_text('2 3')
        with self.assertRaises(ValueError): g.Lease(self.root)

    def test_between_cohort_policy_change_refused_against_sealed_baseline(self):
        baseline = g.snapshot()
        (self.policies / 'policy2/scaling_min_freq').write_text('2000')
        changed = g.snapshot()
        with self.assertRaises(ValueError): g.Lease(self.root, baseline)
        self.assertEqual(g.snapshot(), changed)

    def test_foreign_command_does_not_write(self):
        lease = g.Lease(self.root); original = g.snapshot()
        with self.assertRaises(ValueError): lease.set('arbitrary')
        self.assertEqual(g.snapshot(), original)

    def test_postwrite_readback_failure_still_restores_original(self):
        lease = g.Lease(self.root); real = g.write_pref
        def corrupt(value):
            real('balance_power' if value == 'performance' else value)
        with patch.object(g, 'write_pref', side_effect=corrupt):
            with self.assertRaises(ValueError): lease.set('P1')
        self.assertTrue(lease.restore('readback_failure')['restored'])

    def test_other_policy_change_is_detected_and_never_overwritten(self):
        lease = g.Lease(self.root); lease.set('P1')
        other = self.policies / 'policy3/scaling_min_freq'; other.write_text('2000')
        with self.assertRaises(ValueError): lease.check()
        self.assertFalse(lease.restore('foreign_setting')['restored'])
        self.assertEqual(other.read_text(), '2000')
        self.assertEqual((self.policies / 'policy2/energy_performance_preference').read_text(), 'balance_performance')

    def daemon_fixture(self, requests, owner_checks=None, deadline_after_set=False):
        clock = {'now': 1.0}
        owner = dict(pid=123, start_ticks=1)
        (self.root / 'policy-owner.json').write_text(json.dumps(dict(owner=owner, deadline_monotonic=100)))
        stream = io.StringIO(requests); output = io.StringIO()
        real_set = g.Lease.set
        def setting(lease, policy):
            result = real_set(lease, policy)
            if deadline_after_set: clock['now'] = 101
            return result
        alive = patch.object(g, 'alive', side_effect=owner_checks) if owner_checks else patch.object(g, 'alive', return_value=True)
        with patch.object(g, 'LOCK', self.root / 'lock'), alive, \
             patch.object(g.time, 'monotonic', side_effect=lambda: clock['now']), \
             patch.object(g.select, 'select', return_value=([stream], [], [])), \
             patch.object(g.sys, 'stdin', stream), patch.object(g.sys, 'stdout', output), \
             patch.object(g.Lease, 'set', setting):
            g.run(self.root)
        journal = json.loads((self.root / 'policy-journal.json').read_text())
        self.assertEqual(journal['status'], 'restored')
        self.assertEqual(g.snapshot(), journal['original'])
        return journal

    def test_independent_daemon_restores_after_owner_exit(self):
        journal = self.daemon_fixture('{"op":"set","policy":"P1"}\n', [True, True, False])
        self.assertEqual(journal['reason'], 'owner_absent')

    def test_independent_daemon_restores_after_control_eof(self):
        self.assertEqual(self.daemon_fixture('{"op":"set","policy":"P1"}\n')['reason'], 'control_eof')

    def test_independent_daemon_restores_after_deadline(self):
        journal = self.daemon_fixture('{"op":"set","policy":"P1"}\n', deadline_after_set=True)
        self.assertEqual(journal['reason'], 'lease_deadline')

    def test_independent_daemon_restores_after_rejected_command(self):
        journal = self.daemon_fixture('{"op":"set","policy":"P1"}\n{"op":"arbitrary"}\n')
        self.assertTrue(journal['reason'].startswith('exception:'))


if __name__ == '__main__': unittest.main()
