"""Offline control-design checks; no live service, Docker, sudo or workload."""
import copy
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import v25_common as c
import v25_model as model
import v25_study as runner
import v25_verify as verify
import v24r3_common as previous
from test_v24r3 import phase_fixture


def fixture(size='small', on=True):
    _,derived,server,anchors,probe=phase_fixture(size,1,on)
    cfg=next(r for r in c.matrix() if r['size']==size and r['counter_probe']==on)
    return cfg,derived,server,anchors,probe


def rows(effect=0):
    result=[]
    for cfg in c.matrix():
        value=dict(trial=cfg['trial'],size=cfg['size'],block=cfg['block'],repeat=cfg['repeat'],
            order=cfg['order'],counter_probe=cfg['counter_probe'],recording_quality_pass=True,
            busy_capacity_rps=100+(cfg['repeat']-1)*.1,whole_cpu_usec_per_job=5000+(cfg['repeat']-1)*2,
            miss_pct=10+(cfg['repeat']-1)*.1+(effect if cfg['counter_probe'] else 0))
        if cfg['counter_probe']:
            value.update(measurement_quality=dict(pass_budget=True),phases={key:dict(state_eligible=False) for key in ('busy','low')})
        result.append(value)
    return result


class V25ControlTests(unittest.TestCase):
    def test_design_balances_sizes_conditions_repeats_and_group_positions(self):
        matrix=c.matrix();self.assertEqual(len(matrix),16)
        for size in ('small','large'):
            for on in (False,True):
                chosen=[r for r in matrix if r['size']==size and r['counter_probe']==on]
                self.assertEqual(len(chosen),4)
                self.assertEqual(sorted(r['repeat'] for r in chosen),[1,1,2,2])
                self.assertEqual(sorted((r['order']-1)%4 for r in chosen),[0,1,2,3])

    def test_two_order_contrasts_are_opposite_for_each_size(self):
        report=model.report(rows(),c.design())
        for size in ('small','large'):
            self.assertEqual({r['order'] for r in report['by_size'][size]['order_contrasts']},{'on_then_off','off_then_on'})

    def test_original_schedules_windows_and_collector_are_reused(self):
        self.assertEqual(c.design()['windows'],previous.design()['windows'])
        self.assertEqual(c.design()['sampler'],previous.design()['sampler'])
        for size in ('small','large'):
            cfg=next(r for r in c.matrix() if r['size']==size)
            old=next(r for r in previous.matrix() if r['size']==size)
            self.assertEqual(c.schedule(cfg),previous.schedule(old))
        self.assertEqual(c.digest(c.BUILD/'counter'),c.digest(c.PREVIOUS/'bundle/counter'))
        verify.verify_software_receipt()

    def test_functional_configs_still_have_exact_schedules(self):
        self.assertEqual(len(c.functional_configs()),4)
        for cfg in c.functional_configs():
            c.validate_config(cfg,True);self.assertGreater(len(c.schedule(cfg)),0)

    def test_valid_variation_does_not_turn_into_recording_failure(self):
        report=model.report(rows(effect=5),c.design())
        self.assertTrue(report['complete']);self.assertTrue(report['recording_quality_pass'])
        self.assertEqual(report['decision'],'control_design_screen_complete')
        self.assertFalse(report['equivalence_established'])
        self.assertFalse(report['by_size']['large']['diagnostics']['miss_pp']['overall_mean_difference_within_reference'])

    def test_ineligible_states_are_reported_without_retrying_or_rejecting_data(self):
        report=model.report(rows(),c.design())
        self.assertTrue(report['complete'])
        self.assertEqual(report['by_size']['small']['eligible_on_trials'],0)
        self.assertFalse(report['scientific_explanation_established'])

    def test_same_condition_variation_and_signed_effect_are_separate(self):
        report=model.report(rows(effect=-2),c.design())
        entry=report['by_size']['small']
        self.assertAlmostEqual(entry['overall_mean_signed_difference']['miss_pp'],-2)
        self.assertAlmostEqual(entry['diagnostics']['miss_pp']['observed_maximum_repeat_difference'],.1)
        self.assertTrue(entry['diagnostics']['miss_pp']['both_order_contrasts_exceed_observed_repeat_differences'])

    def test_opposite_order_effects_remain_unresolved(self):
        values=rows()
        for r in values:
            if r['counter_probe']:r['miss_pct']+=3 if r['block']<=2 else -3
        report=model.report(values,c.design())
        self.assertFalse(report['by_size']['small']['diagnostics']['miss_pp']['both_order_contrasts_same_sign'])

    def test_trials_are_replicates_not_individual_requests(self):
        report=model.report(rows(),c.design())
        for size in ('small','large'):
            for cond in ('off','on'):
                self.assertEqual(report['by_size'][size]['condition_summaries'][cond]['miss_pct']['n'],4)

    def test_missing_duplicate_foreign_and_identity_tamper_are_detected(self):
        values=rows();self.assertFalse(model.report(values[:-1],c.design())['complete'])
        with self.assertRaisesRegex(ValueError,'duplicate'):model.report(values+[values[0]],c.design())
        bad=copy.deepcopy(values);bad[0]['trial']='foreign'
        with self.assertRaisesRegex(ValueError,'foreign'):model.report(bad,c.design())
        bad=copy.deepcopy(values);bad[0]['order']+=1
        with self.assertRaisesRegex(ValueError,'identity'):model.report(bad,c.design())

    def test_nonfinite_metrics_and_missing_quality_are_rejected(self):
        for key,value in [('miss_pct',float('nan')),('busy_capacity_rps',0),('whole_cpu_usec_per_job',-1)]:
            bad=rows();bad[0][key]=value
            with self.assertRaisesRegex(ValueError,'quality'):model.report(bad,c.design())
        bad=rows();next(r for r in bad if r['counter_probe'])['measurement_quality']['pass_budget']=False
        with self.assertRaisesRegex(ValueError,'quality missing'):model.report(bad,c.design())

    def test_positive_queue_five_is_busy_and_legacy_margin_is_still_reported(self):
        cfg,d,s,a,p=fixture()
        with patch.object(model.retained.queue,'min_window',return_value=5):
            result=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertTrue(result['phases']['busy']['state_eligible'])
        self.assertFalse(result['phases']['busy']['legacy_v24_state_margin_pass'])

    def test_zero_queue_is_ineligible_but_recording_is_valid(self):
        cfg,d,s,a,p=fixture();s['events']=[dict(j,admission_ns=j['worker_start_ns']) for j in s['events']]
        result=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertTrue(result['recording_quality_pass'])
        self.assertFalse(result['phases']['busy']['state_eligible'])

    def test_missing_throttle_counter_is_not_assumed_zero(self):
        cfg,d,s,a,p=fixture()
        result=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertFalse(result['phases']['low']['state_eligible'])

    def test_low_state_requires_small_queue_and_no_throttling(self):
        cfg,d,s,a,p=fixture()
        for sample in p['samples']:sample['cpu_stat']['nr_throttled']=0
        result=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertTrue(result['phases']['low']['state_eligible'])
        for i,sample in enumerate(p['samples']):sample['cpu_stat']['nr_throttled']=i
        result=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        self.assertFalse(result['phases']['low']['state_eligible'])

    def test_actual_recording_gaps_still_fail(self):
        cfg,d,s,a,p=fixture();p['samples']=[r for r in p['samples'] if not 12e9<r['before_ns']<12.15e9]
        with self.assertRaisesRegex(ValueError,'gap'):model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')

    def test_foreground_runs_sixteen_then_replays_after_disarming_watchdog(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);collected=[]
            def watcher(s,phase,seconds):
                self.assertEqual((phase,seconds),('measurement',5400))
                c.save(s/(phase+'_lifetime.json'),dict(started_monotonic=0,deadline_monotonic=1e12))
                return types.SimpleNamespace(),(s/'watch.log').open('w')
            def replay(argv,timeout):
                self.assertEqual(argv[2],'analyze');self.assertEqual(timeout,600)
                self.assertTrue((session/'measurement_finished.json').exists());self.assertTrue(stop.called)
                self.assertEqual(c.read(session/'collection_receipt.json')['completed_slots'],16)
                return types.SimpleNamespace(returncode=0)
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),\
                 patch.object(runner,'bind_observer_inventory'),patch.object(runner,'environment'),\
                 patch.object(runner,'start_watchdog',side_effect=watcher),patch.object(runner,'collect_slot',side_effect=lambda s,cfg:collected.append(cfg['trial'])),\
                 patch.object(runner.os,'sched_setaffinity'),patch.object(runner.fixtures,'stop') as stop,patch.object(runner.subprocess,'run',side_effect=replay):
                runner.foreground(session,Path('/unused'))
            self.assertEqual(collected,[r['trial'] for r in c.matrix()])

    def test_no_resume_after_any_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);(session/'slots/first/attempt-1').mkdir(parents=True)
            with patch.object(verify,'verify_preparation'),patch.object(runner,'require_quiet_host'),patch.object(runner.run.old,'check_topology'),\
                 patch.object(runner.os,'sched_setaffinity'),patch.object(runner,'start_watchdog') as start:
                with self.assertRaisesRegex(ValueError,'resume prohibited'):runner.foreground(session)
                start.assert_not_called()

    def test_saved_phase_accounting_tamper_fails_raw_replay(self):
        cfg,d,s,a,p=fixture();expected=model.trial(d,s,a,p,cfg,c.design(),'/owned/cpu.stat')
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);trial=session/'trial';trial.mkdir()
            manifest={key:key for key in ('image','server_sha256','loadgen_sha256','gate_sha256')};manifest['resource_baseline']={}
            payload={'config.json':cfg,'complete.json':dict(valid=True,functional=False),'derived.json':d,'identity.json':manifest,
                'initial.json':dict(resource_baseline={},cgroup='/owned'),'server_metrics.json':s,'host_server_anchors.json':a,
                'environment.json':{},'warmup.json':{},'loadgen.json':{},'phase_accounting.json':expected}
            for name,value in payload.items():c.save(trial/name,value)
            c.save(session/'environment.json',{});c.seal(trial)
            with patch.object(verify.raw,'replay',return_value=d),patch.object(verify,'counter_input',return_value=p),patch.object(c,'technical_client'):
                verify.verify_trial(session,trial,manifest)
                altered=copy.deepcopy(expected);altered['recording_quality_pass']=False
                c.save(trial/'phase_accounting.json',altered);c.seal(trial)
                with self.assertRaisesRegex(ValueError,'independent replay'):verify.verify_trial(session,trial,manifest)

    def test_completion_report_checks_trial_detail_against_replayed_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);values=rows();refs={}
            for row in values:
                d=session/'slots'/row['trial']/'attempt-1';d.mkdir(parents=True)
                c.save(d/'started.json',dict(monotonic_ns=1_000_000_000))
                c.save(d/'complete.json',dict(finished_monotonic_ns=2_000_000_000))
                refs[row['trial']]=dict(path=str(d.relative_to(session)),seal='mock-verified')
            prep=session/'preparation';prep.mkdir();c.save(prep/'manifest.json',{});c.seal(prep)
            life=dict(started_monotonic=0,deadline_monotonic=5400,boot='same-boot')
            c.save(session/'measurement_lifetime.json',life)
            c.save(session/'collection_receipt.json',dict(life,completed_slots=16,collection_finished_monotonic=3))
            out=session/'analysis/one';out.mkdir(parents=True)
            saved=dict(result=model.report(values,c.design()),trial_refs=refs,trial_accounting=values,
                preparation_seal=c.digest(prep/'seal.json'),collection_receipt_sha256=c.digest(session/'collection_receipt.json'),
                measurement_lifetime_sha256=c.digest(session/'measurement_lifetime.json'),technical_failures=[])
            def write_report():
                c.save(out/'report.json',saved);c.seal(out)
                c.save(session/'latest_analysis.json',dict(path='analysis/one',seal=c.digest(out/'seal.json')))
            write_report()
            with patch.object(verify,'verify_preparation',return_value=dict(baseline=dict(boot_id='same-boot'))),\
                 patch.object(verify,'verify_environment'),patch.object(verify,'verify_observer'),patch.object(verify,'rows',return_value=(values,refs)):
                self.assertTrue(verify.verify_completion(session)['complete'])
                saved['trial_accounting']=values[:-1];write_report()
                with self.assertRaisesRegex(ValueError,'raw replay'):verify.verify_completion(session)


if __name__=='__main__':unittest.main()
