"""Failure-focused policy restoration and forecast provenance tests, no sysfs writes."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nginx_power_confirmation_common as c
import nginx_power_confirmation_guard as g
import nginx_power_confirmation_model as m
import nginx_power_confirmation_study as study
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
        for mode in ('validation', 'missing', 'domain'):
            rows = calibration(self.s)
            if mode == 'validation': rows[0]['config'] = self.s['validation'][0]
            if mode == 'missing': rows[0]['outcomes'].pop()
            if mode == 'domain': rows[0]['domain_exits'] = ['response_integrity']
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

    def test_warmup_weight_and_failed_mass(self):
        f = m.fit(calibration(self.s), self.s); cfg = self.s['validation'][0]
        warm = [dict(success=True, e2e_ns=30000000) for _ in range(25)]
        pred = m.predictions(f, cfg, warm, 20565395)
        self.assertAlmostEqual(pred['pooled_update'], (800 + 25) / 1625)
        warm[0]['success'] = False
        self.assertEqual(m.predictions(f, cfg, warm, 20565395), pred)
        warm = [dict(success=False, e2e_ns=None) for _ in range(25)]
        self.assertEqual(m.predictions(f, cfg, warm, 20565395)['warmup'], 1)

    def test_failed_calibration_mass_and_all_failed_references(self):
        rows = calibration(self.s)
        for row in rows:
            row['observations'] = ['measurement_throttling']
            for o in row['outcomes']: o.update(success=False, e2e_ns=None)
        f = m.fit(rows, self.s)
        self.assertEqual(f['references']['pooled']['offers'], 1600)
        self.assertEqual(f['references']['pooled']['failed_offers'], 1600)
        pred = m.predictions(f, self.s['validation'][0],
            [dict(success=True, e2e_ns=10000000) for _ in range(25)], 20565395)
        self.assertEqual(pred['matched'], 1)
        self.assertAlmostEqual(pred['matched_update'], 800 / 825)

    def test_validation_throttling_and_failures_remain_in_complete_score(self):
        f = m.fit(calibration(self.s), self.s); rows = validation(self.s)
        for row in rows:
            row['observations'] = ['measurement_throttling']
            row['outcomes'][0].update(success=False, e2e_ns=None)
        result = m.compare(rows, f, self.s)
        self.assertEqual(len(result['primary']['errors']), 24)
        self.assertNotEqual(result['status'], 'technical_invalid')
        for row, e in zip(rows, result['primary']['errors']):
            self.assertEqual(e['observed'], 1 / 300 if row['config']['policy'] == 'P0' else 1)

    def test_mixed_reference_strict_threshold_failure_denominator(self):
        ref = m.reference([dict(success=True, e2e_ns=20565395),
            dict(success=True, e2e_ns=20565396), dict(success=False, e2e_ns=None)])
        self.assertEqual(m.reference_probability(ref, 20565395), 2 / 3)

    def test_schedules_parse_original_client_endpoint(self):
        for cfg in self.s['qualification'] + self.s['calibration']:
            self.assertTrue(all(o['success'] for o in m.outcomes(oldtest.client(cfg), cfg)))


class InclusionTests(unittest.TestCase):
    def setUp(self):
        self.cfg = c.schedule(1)['qualification'][0]

    def test_complete_corruption_stops_but_transport_and_http_failures_are_misses(self):
        for mode in ('corrupt', 'partial', 'http', 'cap'):
            value = oldtest.client(self.cfg)
            r = value['Rows'][0]
            r['DecodeError'] = 'unexpected EOF'
            if mode == 'partial': r['Error'] = 'unexpected EOF'
            if mode == 'http': r['Status'] = 503
            if mode == 'cap': r['Error'] = 'response exceeds body cap'
            records = m.outcomes(value, self.cfg)
            self.assertFalse(records[0]['success'])
            self.assertEqual(bool(study.integrity_exits(value, records)), mode in ('corrupt', 'cap'))

    def test_invalid_failed_response_timing_is_technical_error(self):
        value = oldtest.client(self.cfg); value['Rows'][0]['Status'] = 503
        value['Rows'][0]['BodyDoneNs'] = value['Rows'][0]['DispatchNs'] - 1
        with self.assertRaises(ValueError): m.outcomes(value, self.cfg)

    def test_stopped_pilot_raw_throttling_becomes_annotation_only_in_new_analysis(self):
        import nginx_power_common as pilot
        source = pilot.BASE / 'campaign/validation/cohort-12'
        cfg = c.read(source / 'study-config.json'); before_hash = c.sha(source / 'evidence-seal.json')
        with tempfile.TemporaryDirectory() as temp:
            case = Path(temp)
            for name in ('warmup.json', 'measurement.json', 'measurement-counters.json',
                         'measurement-before.json', 'status-window.json'):
                (case / name).write_bytes((source / name).read_bytes())
            counters = c.read(source / 'measurement-counters.json')
            c.save(case / 'warmup-before.json', counters['before'])
            c.save(case / 'warmup-counters.json', dict(before=counters['before'], after=counters['before'],
                delta={k: 0 for k in counters['before']}))
            result = study.analyze(case, cfg)
            self.assertEqual(result['domain_exits'], [])
            self.assertIn('measurement_throttling', result['observations'])
            self.assertEqual(result['offers'], 300)
        self.assertEqual(before_hash, c.sha(source / 'evidence-seal.json'))

    def test_collection_continues_after_retained_throttling_without_replacement(self):
        configs = c.schedule(1)['qualification'][:2]
        results = [dict(config=cfg, domain_exits=[], observations=['measurement_throttling']) for cfg in configs]
        with tempfile.TemporaryDirectory() as temp, patch.object(c, 'verify_prepared'), \
             patch.object(study.h, 'desktop_absent'), patch.object(study, 'trial', side_effect=results) as trial, \
             patch.object(study, 'replay_case', side_effect=results), patch.object(study.q, 'evidence_seal'):
            rows = study.run_group(Path(temp) / 'smoke', configs, study.time.monotonic(), 600)
            self.assertEqual(rows, results); self.assertEqual(trial.call_count, 2)
            self.assertTrue(c.read(Path(temp) / 'smoke/summary.json')['complete'])


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
