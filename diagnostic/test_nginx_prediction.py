"""Failure-focused tests for fresh-only forecasts and prospective execution barriers."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nginx_prediction_common as c
import nginx_prediction_model as m
import nginx_prediction_study as s
import test_nginx_qualification as old


def client(cfg, prefix='measurement'):
    count = cfg['count'] if prefix == 'measurement' else cfg['warmup_count']
    value = old.client(prefix, count)
    value['IntervalNs'] = cfg['interval_ns']
    for i, row in enumerate(value['Rows']):
        offset = i * cfg['interval_ns'] - row['ScheduledNs']
        for key in ('ScheduledNs', 'DispatchNs', 'HeadersNs', 'BodyDoneNs'): row[key] += offset
    return value


def calibrations():
    return [dict(config=cfg, domain_exits=[], outcomes=[dict(success=True, e2e_ns=10 if i < 200 else 20)
             for i in range(400)]) for cfg in c.configs('calibration')]


def validations(fraction=.5):
    return [dict(config=cfg, domain_exits=[], outcomes=[dict(success=True,
                 e2e_ns=20 if i < round(fraction * 300) else 10) for i in range(300)])
            for cfg in c.configs('validation')]


class ModelTests(unittest.TestCase):
    def test_all_three_exact_integer_schedules(self):
        for cfg in c.configs('preparation'):
            rows = m.outcomes(client(cfg), cfg)
            self.assertEqual(len(rows), 20)
            self.assertTrue(all(r['e2e_ns'] == 50 for r in rows))

    def test_missing_duplicate_foreign_schedule_rejected(self):
        cfg = c.configs('preparation')[0]
        for mode in ('missing', 'duplicate', 'spacing'):
            value = client(cfg)
            if mode == 'missing': value['Rows'].pop()
            if mode == 'duplicate': value['Rows'][1] = copy.deepcopy(value['Rows'][0])
            if mode == 'spacing': value['IntervalNs'] += 1
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.outcomes(value, cfg)

    def test_full_body_endpoint_and_no_queue_subtraction(self):
        cfg = c.configs('preparation')[0]; value = client(cfg)
        value['Rows'][0]['QueueNs'] = 999999999
        value['Rows'][0]['BodyDoneNs'] = 150
        rows = m.outcomes(value, cfg)
        self.assertEqual(rows[0]['e2e_ns'], 150)
        self.assertEqual(m.miss_fraction(rows, 50), 1 / 20)
        self.assertEqual(m.miss_fraction(rows, 150), 0)

    def test_failed_and_dropped_offers_remain_misses(self):
        cfg = c.configs('preparation')[0]; value = client(cfg)
        value['Rows'][0].update(Error='timeout', Status=0, HeadersNs=-1, BodyDoneNs=10000000000)
        value['Rows'][1].update(Error='client in-flight cap reached', Status=0, DispatchNs=0,
                                HeadersNs=-1, BodyDoneNs=-1)
        rows = m.outcomes(value, cfg)
        self.assertFalse(rows[0]['success']); self.assertTrue(rows[1]['dropped'])
        self.assertEqual(m.miss_fraction(rows, 10**12), .1)

    def test_corrupt_decoded_body_is_unsuccessful(self):
        cfg = c.configs('preparation')[0]; value = client(cfg)
        value['Rows'][0]['DecodedSHA256'] = 'bad'
        self.assertFalse(m.outcomes(value, cfg)[0]['success'])

    def test_primary_lower_median_ties_and_exact_boundary(self):
        forecast = m.fit(calibrations())
        self.assertEqual(forecast['primary_deadline_ns'], 10)
        self.assertEqual(forecast['predictions']['10'], .5)
        self.assertEqual(m.probability([10] * 1600, 10), 0)
        self.assertEqual(m.probability([9, 10, 11], 10), 1 / 3)

    def test_fit_refuses_pilot_validation_missing_or_failed_calibration(self):
        for mode in ('pilot', 'validation', 'missing', 'failure', 'exit'):
            values = calibrations()
            if mode in ('pilot', 'validation'): values[0]['config'] = c.configs(mode)[0]
            if mode == 'missing': values.pop()
            if mode == 'failure': values[0]['outcomes'][0]['success'] = False
            if mode == 'exit': values[0]['domain_exits'] = ['measurement_throttling']
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.fit(values)

    def test_accuracy_pass_failure_and_applicability_distinguished(self):
        forecast = m.fit(calibrations())
        self.assertEqual(m.compare(validations(), forecast)['status'], 'full_response_prediction_accuracy_supported')
        self.assertEqual(m.compare(validations(.8), forecast)['status'], 'full_response_prediction_accuracy_not_supported')
        rows = validations(); rows[0]['domain_exits'] = ['measurement_throttling']
        self.assertEqual(m.compare(rows, forecast)['status'], 'scientific_applicability_exit')

    def test_six_blocks_do_not_treat_requests_as_replicates(self):
        forecast = m.fit(calibrations()); rows = validations()
        rows[0]['outcomes'] = [dict(success=True, e2e_ns=20) for _ in range(300)]
        result = m.compare(rows, forecast)
        self.assertEqual(len(result['block_mae_pp']), 6)
        self.assertGreater(result['conditional_model_based_95_interval_pp'][1], result['mean_block_mae_pp'])
        self.assertEqual(set(result['per_profile_mae_pp']), set('ABC'))
        self.assertEqual(len(result['calibration_cohort_sensitivity_mae_pp']), 4)

    def test_incomplete_reordered_or_foreign_validation_rejected(self):
        forecast = m.fit(calibrations())
        for mode in ('missing', 'reordered', 'foreign'):
            rows = validations()
            if mode == 'missing': rows.pop()
            if mode == 'reordered': rows[0], rows[1] = rows[1], rows[0]
            if mode == 'foreign': rows[0]['config'] = c.configs('pilot')[0]
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.compare(rows, forecast)


class EvidenceTests(unittest.TestCase):
    def case(self, directory, role='preparation'):
        cfg = c.configs(role)[0]
        c.save(directory / 'study-config.json', cfg)
        c.save(directory / 'measurement.json', client(cfg))
        c.save(directory / 'warmup.json', client(cfg, 'warmup'))
        before = dict(usage_usec=0, nr_throttled=0, throttled_usec=0)
        after = dict(usage_usec=100, nr_throttled=0, throttled_usec=0)
        c.save(directory / 'measurement-before.json', before)
        c.save(directory / 'measurement-counters.json', dict(before=before, after=after, delta=after))
        c.save(directory / 'status-window.json', dict(before=old.status(10),
               after_checks=[old.status(10 + cfg['count'] + 1)]))
        return cfg

    def test_throttle_body_dispatch_and_counter_failures_preserved(self):
        for mode in ('throttle', 'body', 'dispatch', 'counter'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                directory = Path(name); self.case(directory)
                if mode == 'throttle':
                    value = c.read(directory / 'measurement-counters.json')
                    for part in ('after', 'delta'): value[part]['throttled_usec'] = 1
                    c.save(directory / 'measurement-counters.json', value)
                    self.assertIn('measurement_throttling', s.analyze(directory)['domain_exits'])
                elif mode == 'counter':
                    value = c.read(directory / 'measurement-counters.json'); value['delta']['usage_usec'] = 9
                    c.save(directory / 'measurement-counters.json', value)
                    with self.assertRaisesRegex(ValueError, 'counter replay'): s.analyze(directory)
                else:
                    value = c.read(directory / 'measurement.json')
                    if mode == 'body': value['Rows'][0]['DecodedSHA256'] = 'bad'
                    else:
                        for k in ('DispatchNs', 'HeadersNs', 'BodyDoneNs'): value['Rows'][0][k] += 11000000
                    c.save(directory / 'measurement.json', value)
                    self.assertIn('response_integrity' if mode == 'body' else 'dispatch_gate', s.analyze(directory)['domain_exits'])

    def test_transport_failure_has_bounded_accounting_and_all_offer_miss(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); cfg = self.case(directory, 'validation')
            value = c.read(directory / 'measurement.json')
            value['Rows'][0].update(Error='timeout', Status=0, BodyDoneNs=10000000000)
            c.save(directory / 'measurement.json', value)
            result = s.analyze(directory)
            self.assertEqual(result['unsuccessful'], 1)
            self.assertFalse(result['stock_request_accounting']['exact'])
            self.assertEqual(m.miss_fraction(result['outcomes'], 10**12), 1 / 300)
            self.assertEqual(result['domain_exits'], [])

    def test_extra_stock_request_fails(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); self.case(directory)
            value = c.read(directory / 'status-window.json'); value['after_checks'][0]['requests'] += 1
            c.save(directory / 'status-window.json', value)
            with self.assertRaisesRegex(ValueError, 'conservation'): s.analyze(directory)

    def test_seal_detects_mutation_and_added_file(self):
        for mode in ('mutation', 'addition'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as name:
                directory = Path(name); (directory / 'raw').write_text('original'); s.q.evidence_seal(directory)
                c.verify_evidence(directory)
                (directory / ('raw' if mode == 'mutation' else 'extra')).write_text('changed')
                with self.assertRaises(ValueError): c.verify_evidence(directory)

    def test_validation_before_forecast_or_changed_reference_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name); cfg = self.case(directory, 'validation')
            ref = dict(evidence_seal_sha256='fixed', sealed_monotonic=20)
            c.save(directory / 'trial-start.json', dict(monotonic=10, forecast_ref=ref))
            with patch.object(c, 'verify_evidence'), patch.object(s, 'identity'):
                with self.assertRaisesRegex(ValueError, 'preceded'): s.replay_case(directory, cfg, ref)
                with self.assertRaisesRegex(ValueError, 'reference'):
                    s.replay_case(directory, cfg, dict(ref, evidence_seal_sha256='other'))

    def test_raw_measurement_saved_before_failed_classification_and_cleanup(self):
        with tempfile.TemporaryDirectory() as name:
            case = Path(name) / 'case'; cfg = c.configs('preparation')[0]; order = []
            def fail(*args):
                self.assertTrue((case / 'status-window.json').exists())
                self.assertTrue((case / 'measurement-counters.json').exists())
                order.append('classify'); raise ValueError('bad measurement')
            with patch.object(s, 'Service') as factory, patch.object(s.h.fixtures, 'stat', return_value={'usage_usec': 0}), \
                 patch.object(s, 'analyze', side_effect=fail):
                service = factory.return_value; service.guard.return_value = {}
                service.status.side_effect = [old.status(10), old.status(31)]
                service.close.side_effect = lambda: order.append('cleanup')
                with self.assertRaisesRegex(ValueError, 'bad measurement'): s.trial(case, cfg, False)
            self.assertEqual(order, ['classify', 'cleanup'])
            self.assertTrue((case / 'failure.json').exists())
            c.verify_evidence(case)

    def test_campaign_failure_stops_before_calibration_and_is_sealed(self):
        with tempfile.TemporaryDirectory() as name:
            with patch.object(c, 'BASE', Path(name)), patch.object(c, 'verify'), \
                 patch.object(s.h, 'desktop_absent'), patch.object(s.os, 'sched_setaffinity'), \
                 patch.object(s, 'inventory'), patch.object(s, 'run_group', side_effect=ValueError('pilot exit')) as group:
                with self.assertRaisesRegex(ValueError, 'pilot exit'): s.campaign()
                self.assertEqual(group.call_count, 1)
                summary = c.read(Path(name) / 'campaign/summary.json')
                self.assertFalse(summary['complete']); self.assertEqual(summary['stopped_phase'], 'pilot')
                c.verify_evidence(Path(name) / 'campaign')


if __name__ == '__main__': unittest.main()
