"""V30 numerical, fresh-data, held-out endpoint and lifecycle regressions."""
from pathlib import Path
from fractions import Fraction
import copy
import tempfile
import unittest
from unittest.mock import patch
import v30_common as c
import v30_model as model
import v30_study as study
import v30_campaign as campaign
from test_periodic_budget_model import *


def synthetic_report_inputs(observed=0,periodic=0,fluid=10):
    rows=[];pred=dict(methods={model.PRIMARY:{},model.FLUID:{}},sampled_envelopes={})
    for cfg in c.validation_configs():
        trial=cfg['trial'];grid={str(ms):observed for ms in c.DEADLINES_MS}
        rows.append(dict(trial=trial,block=cfg['block'],profile=cfg['profile'],state_eligible=True,deadline_miss_pct=grid))
        pred['sampled_envelopes'][trial]={str(ms):[0,100] for ms in c.DEADLINES_MS}
        for name,value in ((model.PRIMARY,periodic),(model.FLUID,fluid)):
            pred['methods'][name][trial]=dict(status='available',deadline_miss_pct={str(ms):value for ms in c.DEADLINES_MS})
    return rows,pred


class ScientificContractTests(unittest.TestCase):
    def test_frozen_schedule_and_balanced_blocks(self):
        self.assertEqual(len(c.calibration_configs()),16);self.assertEqual(len(c.validation_configs()),18)
        self.assertEqual(sum(len(c.schedule(x)) for x in c.validation_configs()),16200)
        for block,order in enumerate(('ABC','BCA','CAB','ACB','CBA','BAC'),1):
            self.assertEqual(''.join(x['profile'] for x in c.validation_configs() if x['block']==block),order)
        self.assertEqual(c.calibration_configs(),c.read(c.ROOT/'analysis/runtime_io_v29/q025_large/generation-04/bundle/manifest.json')['matrix'][:16])
        for cfg in c.validation_configs():
            vector=[]
            if cfg['profile'] in ('A','B'):
                rate=4 if cfg['profile']=='A' else 18
                stamps=[Fraction(i,rate)*10**9 for i in range(rate*60)]
            else:
                stamps=[(Fraction(cycle*2+start)+Fraction(i,rate))*10**9 for cycle in range(30) for start,rate in ((0,4),(1,42)) for i in range(rate)]
            for stamp in stamps:vector.append((2*stamp.numerator+stamp.denominator)//(2*stamp.denominator))
            self.assertEqual(c.schedule(cfg),vector)

    def test_config_directory_and_ownership_isolation(self):
        with self.assertRaises(ValueError):c.owned_directory(c.ROOT/'analysis/runtime_io_v29/q025_large/generation-04')
        with self.assertRaises(ValueError):c.owned_directory(c.PARENT/'generation-02')
        with self.assertRaises(ValueError):c.validate_config(dict(c.matrix()[0],quota_us=50000))
        import v30_service
        self.assertEqual(v30_service.LABEL,'research.v30.owner')
        self.assertEqual(campaign.session_for('q025_large'),c.PARENT/'generation-01')

    def test_functional_cases_include_new_profiles_and_cancellation(self):
        configs=c.functional_configs();self.assertEqual(len(configs),6)
        self.assertTrue(any(x.get('profile')=='C' and x['burst_period_sec']==2 for x in configs))
        self.assertTrue(any(x.get('profile')=='A' and x['traffic_pattern']=='steady' for x in configs))
        self.assertEqual(configs[-1]['timeout_sec'],.001)

    def test_calibration_rejects_validation_and_missing_rows(self):
        with self.assertRaises(ValueError):model.calibrate([],c.design())
        with self.assertRaises(ValueError):model.calibrate([dict(trial=x['trial'],role='validation') for x in c.calibration_configs()],c.design())

    def test_delay_residual_uses_only_four_fresh_calibration_trials(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);refs={}
            for cfg in c.calibration_configs():
                d=session/cfg['trial'];d.mkdir()
                sample=dict(success=True,queue_ns=50000,e2e_ns=1050000,processing_wall_ns=900000)
                c.save(d/'derived.json',dict(requests=[sample]));c.seal(d)
                refs[cfg['trial']]=dict(path=cfg['trial'],seal=c.digest(d/'seal.json'))
            base=dict(usable=True,methods={});mixed=[dict(role='mixed',busy_capacity_bounds_rps=[34,36])]*4
            with patch.object(model,'calibrate',return_value=copy.deepcopy(base)):
                result=model.fit_calibration(session,mixed,refs)
            self.assertEqual(result['delay_samples'],4)
            self.assertEqual(result['delay_sec'],[.0001]*4)
            bad=dict(refs);bad['v30_b1_A']=next(iter(refs.values()))
            with patch.object(model,'calibrate',return_value=copy.deepcopy(base)),self.assertRaises(ValueError):model.fit_calibration(session,mixed,bad)
            cfg=next(x for x in c.calibration_configs() if x['role']=='steady' and x['reference_low_rate']==15)
            d=session/cfg['trial'];value=c.read(d/'derived.json');value['requests'][0]['e2e_ns']=1
            c.save(d/'derived.json',value);c.seal(d);refs[cfg['trial']]['seal']=c.digest(d/'seal.json')
            with patch.object(model,'calibrate',return_value=copy.deepcopy(base)):
                result=model.fit_calibration(session,mixed,refs)
            self.assertFalse(result['usable']);self.assertEqual(result['decision'],'calibration_delay_unavailable')

    def test_primary_confirmation_and_block_interval(self):
        rows,pred=synthetic_report_inputs();report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(report['decision'],'short_deadline_prediction_confirmed')
        self.assertEqual(report['paired_improvement']['model_based_95_interval'],[10,10])
        self.assertEqual(report['paired_improvement']['df'],5)

    def test_useful_decision_gate_rejects_all_profiles_failing(self):
        rows,pred=synthetic_report_inputs(observed=20,periodic=20,fluid=30)
        report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(report['methods'][model.PRIMARY]['mae_pp'],0)
        self.assertFalse(report['gates']['some_profile_meets_slo_every_block'])
        self.assertNotEqual(report['decision'],'short_deadline_prediction_confirmed')

    def test_decision_mismatch_and_accuracy_failure_are_retained(self):
        rows,pred=synthetic_report_inputs(observed=4,periodic=6,fluid=20)
        result=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertTrue(result['gates']['periodic_mean_block_mae_le_3']);self.assertFalse(result['gates']['all_trial_slo_decisions_match'])
        rows,pred=synthetic_report_inputs(observed=0,periodic=4,fluid=20)
        result=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertFalse(result['gates']['periodic_mean_block_mae_le_3'])

    def test_secondary_outcomes_cannot_change_primary_decision(self):
        rows,pred=synthetic_report_inputs();before=model.report(rows,dict(usable=True),pred,c.design(),True)
        for row in rows:row['deadline_miss_pct']['500']=99
        after=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(before['decision'],after['decision'])
        self.assertEqual(after['deadline_grid'][model.PRIMARY]['500']['mae_pp'],99)

    def test_failed_offer_is_an_outcome_and_empty_queue_is_eligible(self):
        cfg=c.validation_configs()[0]
        s=dict(counter_window=dict(after_ns=60*10**9,before_ns=0,delta=dict(usage_usec=1,nr_throttled=0)),offered=2,completed_computations=1,
               failure_fraction=.5,warmup_all_successful=True,clock_uncertainty_ns=1000,logical_backlogs=dict(admitted_not_started=dict(peak=0)))
        req=[dict(success=False),dict(success=True,e2e_ns=30000000,completion_after_offered_lower_ns=29000000,completion_after_offered_upper_ns=31000000)]
        row=model.trial(dict(summary=s,requests=req),{},[],None,cfg,c.design(),'unused')
        self.assertTrue(row['state_eligible']);self.assertFalse(row['all_successful'])
        self.assertEqual(row['deadline_miss_pct']['25'],100);self.assertEqual(row['deadline_miss_pct']['500'],50)

    def test_incomplete_duplicate_or_foreign_data_never_confirmed(self):
        rows,pred=synthetic_report_inputs()
        self.assertFalse(model.report(rows[:-1],dict(usable=True),pred,c.design(),True)['complete'])
        with self.assertRaises(ValueError):model.report(rows+[rows[0]],dict(usable=True),pred,c.design(),True)

    def test_empirical_delay_cdf_and_rejected_offers(self):
        result=model.probabilities([.024,None],[0,.002])
        self.assertEqual(result['25'],[.5,1]);self.assertEqual(result['500'],[0,1])
        with self.assertRaises(ValueError):model.probabilities([0],[-.001])

    def test_negative_block_and_uncertainty_gate(self):
        rows,pred=synthetic_report_inputs()
        for cfg in c.validation_configs():
            if cfg['block']==1:pred['methods'][model.FLUID][cfg['trial']]['deadline_miss_pct']['25']=0
        result=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertFalse(result['gates']['every_block_positive'])
        self.assertEqual(result['paired_improvement']['df'],5)
        rows,pred=synthetic_report_inputs()
        for cfg in c.validation_configs():
            pred['methods'][model.FLUID][cfg['trial']]['deadline_miss_pct']['25']=1 if cfg['block']<6 else 30
        result=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertTrue(result['gates']['every_block_positive']);self.assertFalse(result['gates']['improvement_95_lower_ge_5'])

    def test_forecast_vectors_against_aggregate_phase_and_delay_counting(self):
        from periodic_budget_model import misses,delayed_misses
        offsets=[0,1000000,60000000,120000000,150000000]
        cfg=c.validation_configs()[0]
        cal=dict(usable=True,delay_status='available',delay_sec=[0,.001,.003],
                 capacity_sensitivity_rps=[35,35],methods=dict(busy=dict(status='available',capacity_rps=35),quadratic=dict(status='unavailable',reason='synthetic unavailable comparator')))
        with patch.object(c,'schedule',return_value=offsets):summary,per,envelope=model.forecast_profile(cal,cfg)
        expected=[];expected_delay=[]
        for phase in model.PHASES:
            lat=model.replay(offsets,35,.025,.1,phase,1)
            expected.append(misses(lat,c.DEADLINES_MS));expected_delay.append(delayed_misses(lat,cal['delay_sec'],c.DEADLINES_MS))
        for ms in map(str,c.DEADLINES_MS):
            self.assertAlmostEqual(summary['periodic_uniform_phase']['deadline_miss_pct'][ms],sum(x[ms] for x in expected)/100)
            self.assertAlmostEqual(summary[model.PRIMARY]['deadline_miss_pct'][ms],sum(x[ms] for x in expected_delay)/100)
        self.assertEqual(summary['fluid_quadratic']['status'],'unavailable')
        for name,grid in per.items():
            for i in range(len(offsets)):
                values=[grid[str(ms)][i] for ms in c.DEADLINES_MS]
                if name!='discovery_switch':self.assertEqual(values,sorted(values,reverse=True))
                self.assertTrue(all(0<=x<=1 for x in values))
        for ms in c.DEADLINES_MS:
            expected_method=model.PRIMARY if ms<=25 else model.FLUID
            self.assertEqual(per['discovery_switch'][str(ms)],per[expected_method][str(ms)])

    def test_forecast_freeze_refuses_existing_validation(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(study.verify,'attempts',return_value=[Path('/tmp/attempt')]),patch.object(model,'forecast') as forecast:
            with self.assertRaises(ValueError):study.freeze_predictions(Path(temp))
            forecast.assert_not_called()


class LifecycleTests(unittest.TestCase):
    def test_bounds_and_prompt(self):
        d=c.design();self.assertEqual(campaign.TOTAL_SEC,12600)
        self.assertLess(sum(d['lifetime_sec'][x] for x in ('preparation','observer','measurement','analysis','cleanup_reserve')),campaign.TOTAL_SEC)
        with patch.object(campaign.sys.stdin,'isatty',return_value=True),patch.object(campaign,'invoke') as invoke:
            campaign.collect_observer_inventory(Path('/tmp/unused'),Path('/tmp/unused-audit'),123)
        self.assertEqual(invoke.call_args.args[1][0],'sudo');self.assertNotIn('-n',invoke.call_args.args[1])
        self.assertFalse(invoke.call_args.kwargs['new_session'])

    def test_missing_terminal_and_cleanup_reserve_prevent_dispatch(self):
        with patch.object(campaign.sys.stdin,'isatty',return_value=False),patch.object(campaign,'invoke') as invoke:
            with self.assertRaises(ValueError):campaign.collect_observer_inventory(Path('/tmp/unused'),Path('/tmp/unused-audit'),123)
            invoke.assert_not_called()
        with tempfile.TemporaryDirectory() as temp,patch.object(campaign.subprocess,'Popen') as launch:
            with self.assertRaises(TimeoutError):campaign.invoke(Path(temp),['unused'],campaign.time.monotonic()+100)
            launch.assert_not_called()

    def test_shared_terminal_cleanup_signals_only_child(self):
        with patch.object(campaign.c,'same_process',side_effect=[True,False,False]),patch.object(campaign.os,'kill') as kill,patch.object(campaign.os,'killpg') as group:
            campaign.terminate(dict(pid=123),False)
            kill.assert_called_once_with(123,campaign.signal.SIGTERM);group.assert_not_called()

    def test_expired_lifetime_prevents_first_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);c.save(session/'measurement_lifetime.json',dict(deadline_monotonic=study.time.monotonic()-1))
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study,'collect') as collect:
                with self.assertRaises(TimeoutError):study.collect_slot(session,c.matrix()[0])
                collect.assert_not_called()

    def test_interrupt_never_retries(self):
        self.exercise_retry(InterruptedError('intentional stop'),1)

    def test_expiry_during_failure_prevents_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);c.save(session/'measurement_lifetime.json',dict(deadline_monotonic=study.time.monotonic()+100))
            def expired(_session,directory,cfg,phase):
                directory.mkdir(parents=True);c.save(directory/'cleanup.json',dict(errors=[],watchdog_intervened=False))
                c.save(session/'measurement_lifetime.json',dict(deadline_monotonic=study.time.monotonic()-1))
                raise TimeoutError('measurement expiry')
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study.verify,'verify_preparation'),patch.object(study.verify,'verify_environment'),patch.object(study,'failures',return_value=[]),patch.object(study,'collect',side_effect=expired) as collect:
                with self.assertRaises(TimeoutError):study.collect_slot(session,c.matrix()[0])
                self.assertEqual(collect.call_count,1)

    def test_cleanup_is_owner_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);owner=dict(pid=123,start_ticks='1',uid=1000)
            c.save(session/'ours/ownership.json',dict(owner=owner,container='ours',nonce='n'))
            c.save(session/'other/ownership.json',dict(owner=dict(pid=456),container='other',nonce='x'))
            with patch.object(campaign,'remove_owned') as remove:
                self.assertEqual(campaign.cleanup_context(session,owner),[])
                remove.assert_called_once_with('ours','n')

    def test_ordinary_failure_permits_one_retry(self):
        self.exercise_retry(RuntimeError('ordinary technical failure'),2)

    def test_active_deadline_timeout_is_terminal(self):
        self.exercise_retry(TimeoutError('active service deadline'),1)

    def exercise_retry(self,error,count):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);c.save(session/'preparation/manifest.json',{});calls=[]
            def collect(_session,directory,cfg,phase):
                directory.mkdir(parents=True);calls.append(directory)
                c.save(directory/'cleanup.json',dict(errors=[],watchdog_intervened=False))
                if len(calls)==1:raise error
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study.verify,'verify_preparation'),patch.object(study.verify,'verify_environment'),patch.object(study.verify,'verify_trial'),patch.object(study,'failures',return_value=[]),patch.object(study,'collect',side_effect=collect):
                if count==1:
                    with self.assertRaises(type(error)):study.collect_slot(session,c.matrix()[0])
                else:study.collect_slot(session,c.matrix()[0])
            self.assertEqual(len(calls),count)


if __name__=='__main__':unittest.main()
