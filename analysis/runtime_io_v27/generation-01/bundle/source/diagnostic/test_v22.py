"""V22 transfer, leakage, conservation, uncertainty and lifecycle regressions; no Docker."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import v22_common as c
import v22_model as model
import v22_raw as raw
import v22_verify as verify
import v22_study as runner
import v22_service as service


def calibration_fixture(name='cal_1',mu=150):
    vec=c.read(c.DESIGN/'A_offsets_ns.json');pred,_=model.simulate(vec,mu)
    jobs=[dict(id=p['id'],admission_ns=vec[p['id']],worker_start_ns=p['start_ns'],
               completion_ns=p['completion_sec']*1e9) for p in pred if not p['rejected']]
    derived=dict(clocks=dict(client_test_start_ns=0,server_minus_client_lower_ns=0,server_minus_client_upper_ns=0),
                 summary=dict(trial=name,cpu_usec_per_completed_work=1e6*.5/mu))
    return derived,dict(events=jobs)


class ModelTests(unittest.TestCase):
    def test_even_arrivals_empty_queue_and_no_misses_at_sufficient_capacity(self):
        _,s=model.simulate(c.read(c.DESIGN/'B_offsets_ns.json'),150)
        self.assertEqual(s['offers'],6793);self.assertEqual(s['queue_peak'],0)
        self.assertEqual(s['miss_pct'],0);self.assertEqual(s['rejections'],0)

    def test_finite_buffer_has_one_active_plus128_waiting(self):
        p,s=model.simulate([0]*130,1)
        self.assertEqual(s['rejections'],1);self.assertEqual(s['queue_peak'],128)
        self.assertFalse(p[128]['rejected']);self.assertTrue(p[129]['rejected'])

    def test_completion_at_arrival_admits_before_rejection_and_deadline_inclusive(self):
        p,_=model.simulate([0,500000000],2)
        self.assertEqual([r['start_sec'] for r in p],[0,.5])
        self.assertTrue(all(r['timely_500'] for r in p))

    def test_invalid_capacity_is_not_silently_repaired(self):
        for mu in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):model.simulate([0],mu)

    def test_queue_conservation_and_simultaneous_changes(self):
        q=model.series([0,1],[1,2]);self.assertEqual(q[1],[1,1,0])
        with self.assertRaises(ValueError):model.series([1],[0])

    def test_recovery_last_return_after_rebound_not_first_empty(self):
        q=([0,11e9,12e9,13e9],[10,0,9,0])
        self.assertEqual(model.recover(q,10e9),3)

    def test_recovery_excludes_next_high_phase_exact_boundary(self):
        q=([0,11e9,15e9,16e9],[10,0,10,0])
        self.assertEqual(model.recover(q,10e9),1)

    def test_recovery_still_backlogged_is_censored(self):
        self.assertIsNone(model.recover(([0,16e9],[10,0]),10e9))

    def test_common_clock_shift_range_preserves_shared_origin(self):
        q=([0,11e9,15.01e9,21e9,25.01e9,31e9,35.01e9,41e9,45.01e9,51e9],
           [10,0,10,0,10,0,10,0,10,0])
        bounds=model.recovery_bounds(q,(-1e6,1e6))
        self.assertFalse(bounds['possibly_censored'])
        self.assertAlmostEqual(bounds['lower_sec'],.999)
        self.assertAlmostEqual(bounds['upper_sec'],1.001)

    def test_clock_boundary_can_make_recovery_possibly_censored(self):
        q=([0,15e9],[10,0])
        b=model.recovery_bounds(q,(-1e6,1e6),switches=(10,))
        self.assertTrue(b['possibly_censored'])

    def test_calibration_uses_fixed_windows_and_two_positive_rates(self):
        a,sa=calibration_fixture();b,sb=calibration_fixture('cal_2')
        result=model.calibration([a,b],[sa,sb],c.design())
        self.assertTrue(result['passed']);self.assertAlmostEqual(result['mu_busy'],150)
        self.assertAlmostEqual(result['mu_cpu'],150);self.assertLess(result['sensitivity_lower'],150)

    def test_calibration_without_saturation_fails_instead_of_selecting_windows(self):
        a,sa=calibration_fixture(mu=200);b,sb=calibration_fixture('cal_2',200)
        result=model.calibration([a,b],[sa,sb],c.design())
        self.assertFalse(result['passed']);self.assertEqual(result['decision'],'inadequate_backlog')

    def test_calibration_disagreement_is_not_refit(self):
        a,sa=calibration_fixture(mu=130);b,sb=calibration_fixture('cal_2',150)
        result=model.calibration([a,b],[sa,sb],c.design())
        self.assertFalse(result['passed']);self.assertGreater(result['relative_disagreement'],.05)

    def test_validation_or_duplicate_calibration_cannot_supply_capacity(self):
        a,sa=calibration_fixture('b1_A');b,sb=calibration_fixture('cal_2')
        with self.assertRaisesRegex(ValueError,'non-calibration'):model.calibration([a,b],[sa,sb],c.design())
        a,sa=calibration_fixture()
        with self.assertRaisesRegex(ValueError,'duplicate'):model.calibration([a,a],[sa,sa],c.design())

    def test_primary_failure_is_not_rescued_by_good_queue_metrics(self):
        obs=dict(miss_pct=10,offers=6793,queue_peak=0,rejections=0,recovery={})
        forecast=dict(miss_pct=13.01,queue_peak=0,rejections=0,recovery_mean_sec=None)
        self.assertFalse(model.evaluate(obs,forecast,'B')['checks']['primary'])

    def test_recovery_uses_worst_bracket_not_favorable_midpoint(self):
        obs=dict(miss_pct=0,offers=6793,queue_peak=0,rejections=0,
            recovery=dict(lower_sec=0,upper_sec=.6,possibly_censored=False))
        forecast=dict(miss_pct=0,queue_peak=0,rejections=0,recovery_mean_sec=.3)
        self.assertFalse(model.evaluate(obs,forecast,'A')['checks']['recovery'])

    def test_paired_contrast_error_can_fail_with_each_trial_within3pp(self):
        prediction=dict(point={'M_busy':{'A':{'miss_pct':10},'B':{'miss_pct':10}}},safely_below_capacity_even=False)
        trials=[]
        for b in range(1,5):
            for arm,actual,error in [('A',7,3),('B',13,-3)]:
                checks=dict(primary=True,queue=True,rejection=True,recovery=True if arm=='A' else None)
                models={m:dict(errors={'miss_error_pp':error},checks=checks) for m in ('M_busy','M_cpu')}
                trials.append(dict(trial=f'b{b}_{arm}',arm=arm,observed={'miss_pct':actual},models=models))
        result=model.report(trials,prediction)
        self.assertFalse(result['primary_pass']);self.assertEqual(result['decision'],'primary_transfer_fail')

    def test_incomplete_data_cannot_pass_even_if_every_present_trial_passes(self):
        result=model.report([],dict(point={'M_busy':{}},safely_below_capacity_even=False))
        self.assertEqual(result['decision'],'incomplete_validation');self.assertFalse(result['primary_pass'])


class ProtocolAndGateTests(unittest.TestCase):
    def test_missing_or_foreign_boot_observer_inventory_blocks_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp)
            with self.assertRaisesRegex(ValueError,'root observer'):runner.bind_observer_inventory(s,None)
            with patch.object(verify.observer,'review',return_value={'boot_id':'foreign'}):
                with self.assertRaisesRegex(ValueError,'another boot'):runner.bind_observer_inventory(s,s/'audit.json')
            self.assertFalse((s/'observer_review').exists())

    def test_desktop_guard_detects_app_and_fails_on_inventory_error(self):
        import subprocess
        for code in (0,2):
            with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],code,'','')):
                with self.assertRaisesRegex(ValueError,'fully quit'):c.require_desktop_absent()
        with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','')):
            c.require_desktop_absent()

    def test_sealed_predictions_recompute_and_resealed_corruption_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);(s/'preparation').mkdir();c.save(s/'preparation/seal.json',{})
            c.save(s/'environment_seal.json',{})
            fixture={}
            for cfg in c.matrix():
                if cfg['role']!='calibration':continue
                derived,server=calibration_fixture(cfg['trial'])
                d=s/'slots'/cfg['trial']/'attempt-1';d.mkdir(parents=True)
                c.save(d/'config.json',cfg);c.save(d/'server_metrics.json',server)
                c.save(d/'complete.json',{'valid':True});c.seal(d);fixture[str(d)]=derived
            manifest={'design_seal':c.digest(c.DESIGN/'seal.json')}
            # Only raw-trial/host prerequisites are synthetic; calibration, package
            # sealing, all 101 sensitivity capacities and recomputation are real.
            with patch.object(verify,'verify_qualification',return_value=manifest),\
                    patch.object(verify,'verify_trial',side_effect=lambda session,d,m:fixture[str(d)]):
                summary=runner.freeze_predictions(s)
                self.assertIsNotNone(summary)
                self.assertEqual(summary,verify.verify_predictions(s,recompute=True))
                per_id=c.read(s/'predictions/per_id.json')
                per_id['M_busy']['A'][0]['timely_500']=False
                c.save(s/'predictions/per_id.json',per_id);c.seal(s/'predictions')
                with self.assertRaisesRegex(ValueError,'recomputation'):
                    verify.verify_predictions(s,recompute=True)

    def test_retained_raw_stage_records_join_for_burst_and_even_patterns(self):
        from test_execution_delay import fixture_data,totals
        for arm in ('A','B'):
            client,server,offsets=fixture_data()
            cfg=next(x for x in c.functional_configs() if x['trial']=='functional_'+arm)
            if arm=='B':
                client['requests']=[r for r in client['requests'] if r['ID']==0]
                for key in ('events','handler_events','entry_events'):
                    server[key]=[r for r in server[key] if r['id']==0]
                client.update(total_scheduled=1,pattern='steady',target_rate=cfg['rate'])
                totals(client,server);offsets=[0]
            with patch.object(c,'schedule',return_value=offsets):
                rows,_,_=raw.join(client,server,cfg)
                self.assertEqual(len(rows),len(offsets))
                client['requests'][0]['ScheduledOffsetNs']+=1
                with self.assertRaisesRegex(ValueError,'offset'):raw.join(client,server,cfg)

    def test_both_arms_have_identical_canonical_warmup(self):
        cfg=c.matrix()[1];warm=c.warmup_config(cfg)
        self.assertEqual(warm['traffic_pattern'],'bursty');self.assertEqual(c.schedule(warm),c.read(c.DESIGN/'warmup_offsets_ns.json'))

    def test_exact_even_vector_matches_native_source_arithmetic(self):
        import math
        cfg=next(x for x in c.matrix() if x['arm']=='B')
        self.assertEqual(c.schedule(cfg),[math.floor(i/cfg['rate']*1e9+.5) for i in range(6793)])
        self.assertEqual(math.floor(6793/cfg['rate']*1e9+.5),60_000_000_000)

    def test_validation_is_gated_before_creating_container_or_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);d=s/'attempt';cfg=next(x for x in c.matrix() if x['role']=='validation')
            with patch.object(verify,'verify_predictions',side_effect=ValueError('no prediction seal')),patch.object(runner,'Service') as svc:
                with self.assertRaisesRegex(ValueError,'no prediction'):runner.collect(s,d,cfg,'run')
                svc.assert_not_called();self.assertFalse(d.exists())

    def test_forecast_cannot_be_replaced_after_validation_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);cfg=next(x for x in c.matrix() if x['role']=='validation')
            (s/'slots'/cfg['trial']/'attempt-1').mkdir(parents=True)
            with patch.object(verify,'verify_qualification',return_value={}):
                with self.assertRaisesRegex(ValueError,'after validation'):runner.freeze_predictions(s)

    def test_calibration_loader_never_reads_validation_or_qualification(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);called=[]
            def choose(session,cfg):
                called.append(cfg['trial']);d=s/cfg['trial'];d.mkdir();c.save(d/'server_metrics.json',{});c.save(d/'seal.json',{})
                return d
            with patch.object(verify,'accepted',side_effect=choose),patch.object(verify,'verify_trial',return_value={}):
                _,_,refs=verify.calibration_inputs(s,{})
            self.assertEqual(called,['cal_1','cal_2']);self.assertEqual(set(refs),{'cal_1','cal_2'})

    def test_no_duplicate_accepted_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);cfg=c.matrix()[0]
            for i in range(2):
                d=s/'slots'/cfg['trial']/f'attempt-{i}';d.mkdir(parents=True);c.save(d/'complete.json',{'valid':True});c.seal(d)
            with self.assertRaisesRegex(ValueError,'replacement'):verify.accepted(s,cfg)

    def test_sealed_tamper_not_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);c.save(d/'x.json',{'x':1});c.seal(d);c.save(d/'x.json',{'x':2})
            with self.assertRaises(ValueError):c.verify_seal(d)

    def test_dispatch_failure_is_technical_but_service_error_is_not(self):
        client=dict(client_dropped=0,missed_arrivals=0,dispatch_lag_summary={'p99_ms':1},total_errors=5)
        c.technical_client(client)
        for field in ('client_dropped','missed_arrivals'):
            bad=dict(client,**{field:1})
            with self.assertRaises(ValueError):c.technical_client(bad)

    def test_partial_failed_collection_does_not_replace_accepted_adverse_trial(self):
        cfg=c.matrix()[4]
        with patch.object(verify,'accepted',return_value=Path('/accepted')),patch.object(runner,'collect') as collector:
            runner.collect_slot(Path('/session'),cfg);collector.assert_not_called()

    def test_docker_foreign_ownership_is_rejected(self):
        import json,subprocess
        response=subprocess.CompletedProcess([],0,json.dumps([dict(Config={'Labels':{service.LABEL:'foreign'}})]),'')
        with patch.object(service.subprocess,'run',return_value=response):
            with self.assertRaisesRegex(ValueError,'ownership'):service.owned_inspect('owned','ours')


if __name__=='__main__':unittest.main()
