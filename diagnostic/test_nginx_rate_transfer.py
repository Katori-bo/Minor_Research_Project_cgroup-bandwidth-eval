"""Forecast, provenance, fixed-policy and lifetime tests; no real workload/sysfs writes."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import nginx_rate_transfer_common as c
import nginx_rate_transfer_model as m
import nginx_rate_transfer_study as study
import nginx_power_confirmation_guard as guard
import test_nginx_prediction as oldtest


def calibration(schedule):
    return [dict(config=cfg, domain_exits=[], outcomes=[dict(success=True,
        e2e_ns=(10000000 if cfg['rate_rps'] == 4 else 30000000 if cfg['rate_rps'] == 8
                else 10000000 if i < 200 else 30000000)) for i in range(400)])
        for cfg in schedule['calibration']]


def validation(schedule):
    return [dict(config=cfg, domain_exits=[], observations=[], outcomes=[dict(success=True,
        e2e_ns=10000000 if cfg['rate_rps'] == 4 else 30000000) for _ in range(300)],
        warmup_outcomes=[dict(success=True, e2e_ns=10000000 if cfg['rate_rps'] == 4 else 30000000)
                        for _ in range(25)]) for cfg in schedule['validation']]


class ForecastTests(unittest.TestCase):
    def setUp(self): self.s = c.schedule(1234)

    def test_balanced_fresh_calibration_and_six_validation_blocks(self):
        self.assertEqual(self.s, c.schedule(1234))
        self.assertEqual([r['index'] for r in self.s['validation']], list(range(1, 13)))
        self.assertEqual(sorted(r['rate_rps'] for r in self.s['calibration']), [4, 4, 5, 5, 8, 8])
        for block in range(1, 7):
            self.assertEqual(sorted(r['rate_rps'] for r in self.s['validation'] if r['block'] == block), [4, 8])
        self.assertTrue(all(r['policy'] == 'P0' for rows in ('qualification', 'calibration', 'validation') for r in self.s[rows]))

    def test_no_foreign_policy_validation_rate_or_nonvalidation_block(self):
        for args in [('calibration', 1, 'P1', 4), ('validation', 1, 'P0', 5, 1),
                     ('calibration', 1, 'P0', 4, 1), ('qualification_lifetime', 4, 'P0', 8)]:
            with self.subTest(args=args), self.assertRaises(ValueError): c.config(*args)

    def test_declared_scientific_and_lifetime_offer_counts(self):
        self.assertEqual(sum(r['count'] for r in self.s['calibration']), 2400)
        self.assertEqual(sum(r['count'] for r in self.s['validation']), 3600)
        self.assertEqual(sum(r['count']+r['warmup_count'] for r in self.s['calibration']+self.s['validation']), 6450)
        self.assertEqual(sum(r['count']+r['warmup_count'] for r in self.s['qualification']), 560)
        self.assertEqual(self.s['qualification'][-1]['count'], 400)
        self.assertEqual(self.s['qualification'][-1]['interval_ns'], 250000000)

    def test_calibration_rejects_labels_missing_and_integrity_but_retains_failures(self):
        for mode in ('validation', 'missing', 'integrity'):
            rows = calibration(self.s)
            if mode == 'validation': rows[0]['config'] = self.s['validation'][0]
            if mode == 'missing': rows[0]['outcomes'].pop()
            if mode == 'integrity': rows[0]['domain_exits'] = ['response_integrity']
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.fit(rows, self.s)
        rows = calibration(self.s)
        for r in rows:
            r['observations'] = ['measurement_throttling']
            r['outcomes'][0].update(success=False, e2e_ns=None)
        forecast = m.fit(rows, self.s)
        self.assertEqual(forecast['references']['4']['failed_offers'], 2)
        self.assertEqual(m.reference_probability(forecast['references']['4'],20565395),2/800)

    def test_known_rate_difference_transfers_and_beats_equal_count_5_reference(self):
        f = m.fit(calibration(self.s), self.s); result = m.compare(validation(self.s), f, self.s)
        self.assertEqual(f['references']['4']['offers'], f['references']['5']['offers'])
        self.assertEqual(f['references']['pooled']['offers'], 2400)
        self.assertEqual(result['status'], 'rate_matching_transfer_supported')
        self.assertEqual(result['primary']['methods']['matched']['mean'], 0)
        self.assertEqual(result['primary']['methods']['baseline']['mean'], 50)
        self.assertEqual(result['primary']['matched_gain_pp']['mean'], 50)
        self.assertEqual(len(result['primary']['matched_gain_pp']['blocks']), 6)

    def test_unknown_within_rate_change_fails_absolute_accuracy(self):
        f = m.fit(calibration(self.s), self.s); rows = validation(self.s)
        for row in rows:
            for o in row['outcomes']: o['e2e_ns'] = 30000000 if row['config']['rate_rps'] == 4 else 10000000
        result = m.compare(rows, f, self.s)
        self.assertFalse(result['useful_absolute_accuracy']); self.assertFalse(result['useful_gain'])
        self.assertEqual(result['status'], 'rate_matching_transfer_not_supported')

    def test_accuracy_without_advantage_and_saturation_are_distinct(self):
        cal = calibration(self.s); val = validation(self.s)
        for row in cal+val:
            for o in row['outcomes']: o['e2e_ns'] = 10000000
        result = m.compare(val, m.fit(cal,self.s), self.s)
        self.assertTrue(result['useful_absolute_accuracy']); self.assertFalse(result['useful_gain'])
        self.assertFalse(result['combined_claim_supported']); self.assertTrue(result['primary']['endpoint_saturated'])
        self.assertEqual(result['status'],'rate_matched_accuracy_supported_advantage_not_supported')

    def test_partial_reordered_or_incomplete_validation_is_not_final_evidence(self):
        f = m.fit(calibration(self.s), self.s)
        for mode in ('partial', 'reorder', 'offers'):
            rows = validation(self.s)
            if mode == 'partial': rows.pop()
            if mode == 'reorder': rows[0], rows[1] = rows[1], rows[0]
            if mode == 'offers': rows[0]['outcomes'].pop()
            with self.subTest(mode=mode), self.assertRaises(ValueError): m.compare(rows,f,self.s)

    def test_failed_warmup_update_denominators(self):
        f = m.fit(calibration(self.s), self.s); cfg = self.s['validation'][0]
        warm = [dict(success=False,e2e_ns=None) for _ in range(25)]
        pred = m.predictions(f,cfg,warm,20565395)
        self.assertEqual(pred['warmup'],1)
        self.assertAlmostEqual(pred['baseline_update'],425/825)
        self.assertAlmostEqual(pred['pooled_update'],1225/2425)
        self.assertAlmostEqual(pred['matched_update'],(pred['matched']*800+25)/825)
        with self.assertRaises(ValueError): m.predictions(f,cfg,warm[:-1],20565395)

    def test_all_failed_calibration_and_validation_preserve_failure_mass(self):
        cal = calibration(self.s); val = validation(self.s)
        for row in cal+val:
            for o in row['outcomes']: o.update(success=False,e2e_ns=None)
        f = m.fit(cal,self.s); result = m.compare(val,f,self.s)
        self.assertEqual(f['references']['pooled']['failed_offers'],2400)
        self.assertEqual(result['primary']['methods']['matched']['mean'],0)
        self.assertTrue(result['primary']['endpoint_saturated'])

    def test_throttled_validation_retained_and_integrity_never_accepted(self):
        f = m.fit(calibration(self.s),self.s); val = validation(self.s)
        for row in val:
            row['observations'] = ['measurement_throttling']
            row['outcomes'][0].update(success=False,e2e_ns=None)
        result = m.compare(val,f,self.s)
        self.assertNotEqual(result['status'],'technical_invalid')
        self.assertEqual(len(result['primary']['errors']),12)
        val[0]['domain_exits'] = ['response_integrity']
        self.assertEqual(m.compare(val,f,self.s)['status'],'technical_invalid')

    def test_strict_deadline_equality_and_failed_offer_denominator(self):
        ref = m.reference([dict(success=True,e2e_ns=20565395),dict(success=True,e2e_ns=20565396),
                           dict(success=False,e2e_ns=None)])
        self.assertEqual(m.reference_probability(ref,20565395),2/3)

    def test_every_rate_schedule_parses_unchanged_native_client(self):
        for cfg in self.s['qualification']+self.s['calibration']+self.s['validation']:
            self.assertTrue(all(o['success'] for o in m.outcomes(oldtest.client(cfg),cfg)))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_longest_schedule_keeps_120_second_watchdog_and_rejects_late_start(self):
        cfg = c.schedule(1)['qualification'][-1]
        self.assertEqual(c.PROTOCOL['service_active_sec'],120)
        with patch.object(study.time,'monotonic',return_value=4):
            study.offer_budget(SimpleNamespace(started=0),cfg,True)
        with patch.object(study.time,'monotonic',return_value=7), self.assertRaises(ValueError):
            study.offer_budget(SimpleNamespace(started=0),cfg,True)
        with patch.object(study.time,'monotonic',return_value=13), self.assertRaises(ValueError):
            study.offer_budget(SimpleNamespace(started=0),cfg,False)

    def test_fixed_policy_does_not_write_and_refuses_policy_change(self):
        baseline = dict(policy2=dict(related_cpus='2',affected_cpus='2',scaling_driver='amd-pstate-epp',
            scaling_governor='powersave',scaling_min_freq='1000',scaling_max_freq='4000',
            energy_performance_preference='balance_performance'))
        c.save(self.root/'policy-baseline.json',baseline)
        case = self.root/'case'; case.mkdir()
        with patch.object(c,'BASE',self.root),patch.object(guard,'snapshot',return_value=copy.deepcopy(baseline)), \
             patch.object(guard,'write_pref',side_effect=AssertionError('No host mutation allowed')) as write:
            policy = study.FixedPolicy(case); policy.set('P0')
            with self.assertRaises(ValueError): policy.set('P1')
            policy.close(); self.assertEqual(write.call_count,0)
            self.assertFalse(c.read(case/'policy-final-check.json')['host_policy_writes'])
            changed = copy.deepcopy(baseline); changed['policy2']['scaling_min_freq'] = '2000'
            with patch.object(guard,'snapshot',return_value=changed), self.assertRaises(ValueError): policy.check()

    def test_collection_continues_after_throttling_without_replacement(self):
        configs = c.schedule(1)['qualification'][:2]
        results = [dict(config=cfg,domain_exits=[],observations=['measurement_throttling']) for cfg in configs]
        with patch.object(c,'verify_prepared'),patch.object(study.h,'desktop_absent'), \
             patch.object(study,'trial',side_effect=results) as trial, \
             patch.object(study,'replay_case',side_effect=results),patch.object(study.q,'evidence_seal'):
            rows = study.run_group(self.root/'smoke',configs,study.time.monotonic(),600)
            self.assertEqual(rows,results); self.assertEqual(trial.call_count,2)

    def test_collection_stops_on_integrity_without_replacement(self):
        configs = c.schedule(1)['qualification'][:2]
        result = dict(config=configs[0],domain_exits=['response_integrity'],observations=[])
        with patch.object(c,'verify_prepared'),patch.object(study.h,'desktop_absent'), \
             patch.object(study,'trial',return_value=result) as trial, \
             patch.object(study,'replay_case',return_value=result),patch.object(study.q,'evidence_seal'):
            with self.assertRaises(ValueError): study.run_group(self.root/'smoke',configs,study.time.monotonic(),600)
            self.assertEqual(trial.call_count,1)
            self.assertTrue(c.read(self.root/'smoke/summary.json')['no_replacement'])

    def test_corruption_stops_but_partial_transport_and_non200_remain_misses(self):
        cfg = c.schedule(1)['qualification'][0]
        for mode in ('corrupt','partial','http','cap'):
            value = oldtest.client(cfg); r = value['Rows'][0]; r['DecodeError'] = 'unexpected EOF'
            if mode == 'partial': r['Error'] = 'unexpected EOF'
            if mode == 'http': r['Status'] = 503
            if mode == 'cap': r['Error'] = 'response exceeds body cap'
            records = m.outcomes(value,cfg)
            self.assertFalse(records[0]['success'])
            self.assertEqual(bool(study.integrity_exits(value,records)),mode in ('corrupt','cap'))

    def test_real_prior_throttle_raw_records_are_retained_with_counter_accounting(self):
        import nginx_power_common as pilot
        source = pilot.BASE/'campaign/validation/cohort-12'
        cfg = c.read(source/'study-config.json')
        for name in ('warmup.json','measurement.json','measurement-counters.json',
                     'measurement-before.json','status-window.json'):
            (self.root/name).write_bytes((source/name).read_bytes())
        counters = c.read(source/'measurement-counters.json')
        c.save(self.root/'warmup-before.json',counters['before'])
        c.save(self.root/'warmup-counters.json',dict(before=counters['before'],after=counters['before'],
            delta={k:0 for k in counters['before']}))
        result = study.analyze(self.root,cfg)
        self.assertEqual(result['domain_exits'],[])
        self.assertIn('measurement_throttling',result['observations'])
        self.assertEqual(result['offers'],300)
        changed = copy.deepcopy(counters); changed['delta']['nr_throttled'] += 1
        (self.root/'measurement-counters.json').write_text(__import__('json').dumps(changed))
        with self.assertRaises(ValueError): study.analyze(self.root,cfg)

    def test_fixed_policy_changes_at_cleanup_are_recorded_and_never_overwritten(self):
        baseline = dict(policy2=dict(related_cpus='2',affected_cpus='2',scaling_driver='amd-pstate-epp',
            scaling_governor='powersave',scaling_min_freq='1000',scaling_max_freq='4000',
            energy_performance_preference='balance_performance'))
        c.save(self.root/'policy-baseline.json',baseline)
        case = self.root/'case'; case.mkdir()
        changed = copy.deepcopy(baseline); changed['policy2']['scaling_min_freq'] = '2000'
        with patch.object(c,'BASE',self.root),patch.object(guard,'snapshot',return_value=copy.deepcopy(baseline)), \
             patch.object(guard,'write_pref',side_effect=AssertionError('Never restore by writing')) as write:
            policy = study.FixedPolicy(case)
            with patch.object(guard,'snapshot',return_value=changed),self.assertRaises(ValueError): policy.close()
            self.assertTrue((case/'policy-final-error.json').exists())
            self.assertEqual(changed['policy2']['scaling_min_freq'],'2000'); self.assertEqual(write.call_count,0)

    def test_prediction_barriers_reject_future_calibration_or_warmup(self):
        sched = c.schedule(1); cfg = sched['validation'][0]; forecast = m.fit(calibration(sched),sched)
        result = validation(sched)[0]
        for mode in ('valid','global_late','warm_late','warm_timing_late','measurement_used'):
            case = self.root/mode; case.mkdir()
            ref = dict(sealed_monotonic=12 if mode != 'global_late' else 14,evidence_seal_sha256='test')
            c.save(case/'trial-start.json',dict(monotonic=13,forecast_ref=ref))
            c.save(case/'result.json',result)
            c.save(case/'measurement-start.json',dict(monotonic=16))
            c.save(case/'warmup-timing.json',dict(started_monotonic=13,finished_monotonic=14 if mode != 'warm_timing_late' else 16))
            c.save(case/'warmup-forecast.json',dict(predictions={str(d):m.predictions(forecast,cfg,result['warmup_outcomes'],d)
                for d in [20565395,*c.PROTOCOL['secondary_deadlines_ns']]},
                sealed_monotonic=15 if mode != 'warm_late' else 17,measurement_used=mode == 'measurement_used',forecast_ref=ref))
            with patch.object(c,'verify_evidence'),patch.object(study,'identity'),patch.object(study,'analyze',return_value=result):
                if mode == 'valid': self.assertEqual(study.replay_case(case,cfg,forecast,ref),result)
                else:
                    with self.subTest(mode=mode),self.assertRaises(ValueError): study.replay_case(case,cfg,forecast,ref)


if __name__ == '__main__': unittest.main()
