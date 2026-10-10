"""V31 independent counting, design, lifecycle and scientific decision checks."""
from pathlib import Path
from fractions import Fraction
import copy
import tempfile
import unittest
from unittest.mock import patch
import v31_common as c
import v31_model as model
import v31_study as study
import v31_campaign as campaign
from test_periodic_budget_model import *


def synthetic_report_inputs(observed=0,cdf=0,periodic=10):
    rows=[];pred=dict(methods={model.PRIMARY:{},model.COMPARATOR:{}},sampled_envelopes={})
    for cfg in c.validation_configs():
        trial=cfg['trial']
        rows.append(dict(trial=trial,block=cfg['block'],profile=cfg['profile'],order=cfg['order'],
            scientific_domain_pass=True,deadline_miss_pct={str(ms):observed for ms in c.DEADLINES_MS}))
        for name,value in ((model.PRIMARY,cdf),(model.COMPARATOR,periodic)):
            pred['methods'][name][trial]=dict(status='available',deadline_miss_pct={str(ms):value for ms in c.DEADLINES_MS})
    return rows,pred


class ScientificContractTests(unittest.TestCase):
    def test_new_schedules_and_balanced_blocks(self):
        self.assertEqual(len(c.calibration_configs()),16);self.assertEqual(len(c.validation_configs()),18)
        self.assertEqual(sum(len(c.schedule(x)) for x in c.validation_configs()),12600)
        for block,order in enumerate(('ABC','BCA','CAB','ACB','CBA','BAC'),1):
            self.assertEqual(''.join(x['profile'] for x in c.validation_configs() if x['block']==block),order)
        import v30_common as prior
        for a,b in zip(c.calibration_configs(),prior.calibration_configs()):
            self.assertEqual(dict(a,trial=b['trial']),b)
        for cfg in c.validation_configs():
            rate={'A':5,'B':11,'C':19}[cfg['profile']]
            for seconds,current in ((60,cfg),(20,c.warmup_config(cfg))):
                expected=[(2*(Fraction(i,rate)*10**9).numerator+(Fraction(i,rate)*10**9).denominator)//(2*(Fraction(i,rate)*10**9).denominator) for i in range(rate*seconds)]
                self.assertEqual(c.schedule(current),expected)

    def test_configuration_and_ownership_isolation(self):
        import v31_service
        self.assertEqual(v31_service.LABEL,'research.v31.owner')
        self.assertEqual(campaign.session_for('q025_large'),c.PARENT/'generation-01')
        for p in (c.ROOT/'analysis/runtime_io_v30/generation-01',c.PARENT/'generation-02'):
            with self.assertRaises(ValueError):c.owned_directory(p)
        with self.assertRaises(ValueError):c.validate_config(dict(c.matrix()[0],quota_us=50000))
        self.assertEqual(len(c.functional_configs()),6)
        self.assertEqual(c.functional_configs()[-1]['timeout_sec'],.001)
        self.assertEqual(c.design()['container_bounds']['created'],42)

    def test_dropped_offers_alone_do_not_trigger_technical_retry(self):
        c.technical_client(dict(client_dropped=3,missed_arrivals=0,dispatch_lag_summary=dict(p99_ms=1)))
        with self.assertRaises(ValueError):c.technical_client(dict(client_dropped=0,missed_arrivals=1,dispatch_lag_summary=dict(p99_ms=1)))

    def test_calibration_rejects_validation_and_missing_rows(self):
        with self.assertRaises(ValueError):model.calibrate([],c.design())
        with self.assertRaises(ValueError):model.calibrate([dict(trial=x['trial'],role='validation') for x in c.calibration_configs()],c.design())

    def timing_fixture(self,session):
        refs={}
        for cfg in c.calibration_configs():
            d=session/cfg['trial'];d.mkdir()
            samples=[dict(id=0,success=True,queue_ns=50000,e2e_ns=10050000,processing_wall_ns=8000000),
                dict(id=1,success=True,queue_ns=100000,e2e_ns=11100000,processing_wall_ns=9500000),
                dict(id=2,success=True,queue_ns=100001,e2e_ns=1,processing_wall_ns=1),
                dict(id=3,success=False,queue_ns=None,e2e_ns=None,processing_wall_ns=None)]
            c.save(d/'config.json',cfg);c.save(d/'derived.json',dict(requests=samples));c.seal(d)
            refs[cfg['trial']]=dict(path=cfg['trial'],seal=c.digest(d/'seal.json'))
        return refs

    def fit_fixture(self,session,refs):
        base=dict(usable=True,methods={});values=[dict(role='mixed',busy_capacity_bounds_rps=[34,36])]*4
        with patch.object(model,'calibrate',return_value=copy.deepcopy(base)):
            return model.fit_calibration(session,values,refs)

    def test_fresh_paired_timing_and_cohort_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);refs=self.timing_fixture(session);result=self.fit_fixture(session,refs)
            self.assertTrue(result['usable']);self.assertEqual(result['timing_samples'],8)
            self.assertEqual(result['timing_trial_count'],4)
            for cohort in result['timing_cohorts'].values():
                self.assertEqual(cohort['accepted'],2);self.assertEqual(cohort['offered'],4)
                self.assertEqual(cohort['deadline_miss_pct'][model.PRIMARY]['10'],50)
            self.assertEqual(sorted(set(result['delay_sec'])),[.0015,.002])
            self.assertEqual({r['total_ns'] for r in result['paired_samples']},{10000000,11000000})
            bad=dict(refs);bad[c.validation_configs()[0]['trial']]=next(iter(refs.values()))
            with self.assertRaises(ValueError):self.fit_fixture(session,bad)

    def test_negative_residual_empty_cohort_and_source_mutation_rejected(self):
        for fault in ('negative','empty','mutated'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                session=Path(temp);refs=self.timing_fixture(session)
                cfg=next(x for x in c.calibration_configs() if x['role']=='steady' and x['reference_low_rate']==15)
                d=session/cfg['trial'];value=c.read(d/'derived.json')
                if fault=='empty':value['requests']=[]
                else:value['requests'][0]['e2e_ns']=1
                c.save(d/'derived.json',value)
                if fault=='mutated':
                    with self.assertRaises(ValueError):self.fit_fixture(session,refs)
                else:
                    c.seal(d);refs[cfg['trial']]['seal']=c.digest(d/'seal.json')
                    result=self.fit_fixture(session,refs)
                    self.assertFalse(result['usable']);self.assertEqual(result['decision'],'calibration_timing_unavailable')

    def test_cdf_convolution_pairing_and_exact_boundary_oracles(self):
        samples=[dict(worker_ns=7000000,residual_ns=4000000,total_ns=11000000),
                 dict(worker_ns=9000000,residual_ns=1000000,total_ns=10000000)]
        grid=model.timing_grid(samples)
        for ms in c.DEADLINES_MS:
            direct=sum(s['total_ns']>ms*1000000 for s in samples)/len(samples)
            independent=sum(a['worker_ns']+b['residual_ns']>ms*1000000 for a in samples for b in samples)/4
            median=sum(8000000+s['residual_ns']>ms*1000000 for s in samples)/2
            self.assertEqual(grid[model.PRIMARY][str(ms)],direct)
            self.assertEqual(grid['independent_worker_response_convolution'][str(ms)],independent)
            self.assertEqual(grid['median_worker_plus_response'][str(ms)],median)
        self.assertEqual(grid[model.PRIMARY]['10'],.5)
        self.assertEqual(grid['independent_worker_response_convolution']['10'],.5)
        self.assertEqual(model.empirical_probability([10000000]*19+[10000001],10),.05)
        for values in ([],[-1],[float('nan')]):
            with self.assertRaises(ValueError):model.empirical_probability(values,10)

    def test_primary_confirmation_uses_periodic_not_fluid(self):
        rows,pred=synthetic_report_inputs();report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(report['decision'],'low_queue_timing_prediction_confirmed')
        self.assertEqual(report['paired_improvement']['model_based_95_interval'],[10,10])
        self.assertEqual(report['paired_improvement']['df'],5)
        self.assertEqual(report['methods'][model.PRIMARY]['mae_pp'],0)

    def test_10_and_12ms_decisions_are_separate_gates(self):
        for deadline in (10,12):
            rows,pred=synthetic_report_inputs()
            pred['methods'][model.PRIMARY][rows[0]['trial']]['deadline_miss_pct'][str(deadline)]=6
            report=model.report(rows,dict(usable=True),pred,c.design(),True)
            self.assertFalse(report['gates']['all_trial_slo_decisions_match_'+str(deadline)+'ms'])
            self.assertNotEqual(report['decision'],'low_queue_timing_prediction_confirmed')

    def test_useful_12ms_profile_gate(self):
        rows,pred=synthetic_report_inputs(observed=20,cdf=20,periodic=30)
        report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(report['methods'][model.PRIMARY]['mae_pp'],0)
        self.assertFalse(report['gates']['some_profile_meets_12ms_slo_every_block'])

    def test_adverse_domain_exit_keeps_all_trials_and_errors(self):
        rows,pred=synthetic_report_inputs();rows[0]['scientific_domain_pass']=False
        report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(report['decision'],'scientific_domain_exit')
        self.assertEqual(report['accepted_validation_trials'],18)
        self.assertEqual(len(report['methods'][model.PRIMARY]['errors']),18)
        self.assertEqual(len(report['blocks']),6)

    def test_secondary_diagnostics_cannot_change_confirmation(self):
        rows,pred=synthetic_report_inputs();before=model.report(rows,dict(usable=True),pred,c.design(),True)
        for row in rows:row['deadline_miss_pct']['10.5']=99
        after=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertEqual(before['decision'],after['decision'])
        self.assertEqual(after['deadline_grid'][model.PRIMARY]['10.5']['mae_pp'],99)

    def test_uneven_block_improvements_and_accuracy_gates(self):
        rows,pred=synthetic_report_inputs(cdf=4,periodic=20)
        report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertFalse(report['gates']['cdf_mean_block_mae_le_3'])
        rows,pred=synthetic_report_inputs()
        for row in rows:
            pred['methods'][model.COMPARATOR][row['trial']]['deadline_miss_pct']['10']=1 if row['block']<6 else 30
        report=model.report(rows,dict(usable=True),pred,c.design(),True)
        self.assertTrue(report['gates']['every_block_positive']);self.assertFalse(report['gates']['improvement_95_lower_ge_5'])
        rows,pred=synthetic_report_inputs()
        for row in rows:
            if row['block']==1:pred['methods'][model.COMPARATOR][row['trial']]['deadline_miss_pct']['10']=0
        self.assertFalse(model.report(rows,dict(usable=True),pred,c.design(),True)['gates']['every_block_positive'])

    def test_incomplete_duplicate_foreign_and_wrong_block_never_confirm(self):
        rows,pred=synthetic_report_inputs()
        self.assertFalse(model.report(rows[:-1],dict(usable=True),pred,c.design(),True)['complete'])
        with self.assertRaises(ValueError):model.report(rows+[rows[0]],dict(usable=True),pred,c.design(),True)
        rows[0]['block']=2
        with self.assertRaises(ValueError):model.report(rows,dict(usable=True),pred,c.design(),True)

    def trial_fixture(self,unknown=0,throttled=0):
        cfg=c.validation_configs()[0];n=100
        requests=[dict(success=True,worker_observed=True,queue_ns=100000,e2e_ns=10000000,
            completion_after_offered_lower_ns=9000000,completion_after_offered_upper_ns=11000000) for _ in range(n)]
        for i in range(unknown):requests[i]=dict(success=False,worker_observed=False,queue_ns=None,e2e_ns=None)
        s=dict(counter_window=dict(after_ns=60*10**9,before_ns=0,delta=dict(usage_usec=1,nr_throttled=throttled)),offered=n,
            completed_computations=n-unknown,failure_fraction=unknown/n,warmup_all_successful=True,
            clock_uncertainty_ns=1000,logical_backlogs=dict(admitted_not_started=dict(peak=0)))
        return model.trial(dict(summary=s,requests=requests),{},[],None,cfg,c.design(),'unused')

    def test_domain_denominator_unknown_intervals_and_throttling(self):
        good=self.trial_fixture();self.assertTrue(good['scientific_domain_pass'])
        self.assertEqual(good['deadline_miss_pct']['10'],0)
        one=self.trial_fixture(unknown=1);self.assertTrue(one['scientific_domain_pass'])
        self.assertEqual(one['deadline_miss_pct']['10'],1)
        two=self.trial_fixture(unknown=2);self.assertFalse(two['scientific_domain_pass'])
        self.assertEqual(two['deadline_miss_pct']['500'],2)
        self.assertEqual(two['domain']['all_offers'],100)
        self.assertFalse(self.trial_fixture(throttled=1)['scientific_domain_pass'])

    def test_stage_counts_conserve_misses_at_boundary(self):
        requests=[dict(success=False),dict(success=True,e2e_ns=11000000,completion_after_offered_lower_ns=10000001,completion_after_offered_upper_ns=11000000),
            dict(success=True,e2e_ns=11000000,completion_after_offered_lower_ns=9000000,completion_after_offered_upper_ns=10000000),
            dict(success=True,e2e_ns=11000000,completion_after_offered_lower_ns=9000000,completion_after_offered_upper_ns=10000001)]
        result=model.stage_counts(requests,10)
        self.assertEqual(result['misses'],4)
        self.assertEqual([v for k,v in result.items() if k!='misses'],[1,1,1,1])

    def test_forecast_vectors_and_phase_delay_counting(self):
        from periodic_budget_model import delayed_misses
        offsets=[0,1000000,60000000,120000000,150000000];cfg=c.validation_configs()[0]
        samples=[dict(worker_ns=8000000,residual_ns=1000000,total_ns=9000000),dict(worker_ns=9000000,residual_ns=2000000,total_ns=11000000)]
        cal=dict(usable=True,timing_status='available',delay_sec=[.001,.002],paired_samples=samples,
            capacity_sensitivity_rps=[35,35],methods=dict(busy=dict(status='available',capacity_rps=35),quadratic=dict(status='unavailable',reason='synthetic')))
        with patch.object(c,'schedule',return_value=offsets):summary,per,envelope=model.forecast_profile(cal,cfg)
        expected=[delayed_misses(model.replay(offsets,35,.025,.1,phase,1),cal['delay_sec'],c.DEADLINES_MS) for phase in model.PHASES]
        for ms in c.DEADLINES_MS:
            self.assertAlmostEqual(summary[model.COMPARATOR]['deadline_miss_pct'][str(ms)],sum(x[str(ms)] for x in expected)/100)
            self.assertEqual(per[model.PRIMARY][str(ms)],[sum(r['total_ns']>ms*1000000 for r in samples)/2]*len(offsets))
        self.assertNotIn('discovery_switch',per)
        self.assertEqual(summary['fluid_quadratic']['status'],'unavailable')
        for grid in per.values():
            for i in range(len(offsets)):
                values=[grid[str(ms)][i] for ms in c.DEADLINES_MS]
                self.assertEqual(values,sorted(values,reverse=True));self.assertTrue(all(0<=x<=1 for x in values))

    def test_forecast_freeze_rejects_existing_validation_or_prediction(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(study.verify,'attempts',return_value=[Path('/tmp/attempt')]),patch.object(model,'forecast') as forecast:
            with self.assertRaises(ValueError):study.freeze_predictions(Path(temp))
            forecast.assert_not_called()
        with tempfile.TemporaryDirectory() as temp,patch.object(study.verify,'attempts',return_value=[]),patch.object(model,'forecast') as forecast:
            session=Path(temp);(session/'predictions').mkdir()
            with self.assertRaises(ValueError):study.freeze_predictions(session)
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
