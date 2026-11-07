"""Failure-focused policy restoration and forecast provenance tests, no sysfs writes."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import nginx_deadline_panel_common as c
import nginx_deadline_panel_guard as g
import nginx_deadline_panel_model as m
import nginx_deadline_panel_study as study
import test_nginx_prediction as oldtest


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


def calibration(schedule):
    return [dict(config=cfg,domain_exits=[],outcomes=[dict(success=True,
        e2e_ns=(10 if cfg['policy']=='P0' else 30)*1000000) for _ in range(400)])
        for cfg in schedule['calibration']]


def validation(schedule):
    return [dict(config=cfg,domain_exits=[],outcomes=[dict(success=True,
        e2e_ns=(10 if cfg['policy']=='P0' else 30)*1000000) for _ in range(300)],
        warmup_outcomes=[dict(success=True,e2e_ns=10000000) for _ in range(25)])
        for cfg in schedule['validation']]


class PanelTests(unittest.TestCase):
    def setUp(self):
        self.s=c.schedule(1234);self.f=m.fit(calibration(self.s),self.s)

    def test_randomized_balanced_schedule_and_cost(self):
        self.assertEqual(self.s,c.schedule(1234))
        self.assertEqual([r['index'] for r in self.s['validation']],list(range(1,25)))
        self.assertEqual(sorted(r['policy'] for r in self.s['calibration']),['P0','P0','P1','P1'])
        for b in range(1,7):
            self.assertEqual(sorted((r['policy'],r['rate_rps']) for r in self.s['validation'] if r['block']==b),sorted(c.CELLS))
        counts={k:sum(r['count']+r['warmup_count'] for r in self.s[k])
                for k in ('qualification','calibration','validation')}
        self.assertEqual(counts,dict(qualification=1030,calibration=1700,validation=7800))
        self.assertEqual(sum(counts.values()),10530)
        self.assertEqual([(r['policy'],r['count']) for r in self.s['qualification'] if r['role']=='qualification_lifetime'],[('P0',400),('P1',400)])

    def test_calibration_refuses_validation_reorder_missing_or_corrupt(self):
        for mode in ('validation','reorder','missing','corrupt'):
            rows=calibration(self.s)
            if mode=='validation':rows[0]['config']=self.s['validation'][0]
            if mode=='reorder':rows[0],rows[1]=rows[1],rows[0]
            if mode=='missing':rows[0]['outcomes'].pop()
            if mode=='corrupt':rows[0]['domain_exits']=['response_integrity']
            with self.subTest(mode=mode),self.assertRaises(ValueError):m.fit(rows,self.s)

    def test_cutoffs_exact_all_offer_lower_order_statistics(self):
        ref=m.reference([dict(success=True,e2e_ns=i+1) for i in range(760)]+
                        [dict(success=False,e2e_ns=None) for _ in range(40)])
        panel=m.cutoffs(ref)
        self.assertEqual([d['rank'] for d in panel],[79,199,399,599,719])
        self.assertEqual([d['deadline_ns'] for d in panel],[80,200,400,600,720])
        self.assertAlmostEqual(m.reference_probability(ref,720),80/800)

    def test_unavailable_quantile_preserves_failure_mass(self):
        rows=calibration(self.s)
        for row in rows:
            for o in row['outcomes'][350:]:o.update(success=False,e2e_ns=None)
        f=m.fit(rows,self.s)
        self.assertFalse(f['panel_available'])
        self.assertEqual(f['references']['pooled']['failed_offers'],200)
        self.assertTrue(all(f['panels'][p][-1]['deadline_ns'] is None for p in c.POLICIES))
        with self.assertRaises(ValueError):m.deadlines(f,self.s['validation'][0])

    def test_exact_deadline_is_success_failures_are_misses(self):
        ref=m.reference([dict(success=True,e2e_ns=10),dict(success=True,e2e_ns=11),dict(success=False,e2e_ns=None)])
        self.assertEqual(m.reference_probability(ref,10),2/3)
        self.assertEqual(m.miss_fraction([dict(success=True,e2e_ns=10),dict(success=False,e2e_ns=None)],10),.5)

    def test_perfect_matched_and_fair_pooled_comparison(self):
        result=m.compare(validation(self.s),self.f,self.s)
        self.assertEqual(result['status'],'deadline_panel_accuracy_both_supported')
        self.assertTrue(result['equal_acquisition_for_methods'])
        for p in c.POLICIES:
            self.assertEqual(result['policies'][p]['methods']['matched']['worst_cutoff_block_score']['mean'],0)
        self.assertEqual(result['policies']['P0']['methods']['pooled']['worst_cutoff_block_score']['mean'],50)
        self.assertFalse(result['novelty_established'])

    def test_independent_policy_verdicts_and_future_shift(self):
        rows=validation(self.s)
        for r in rows:
            if r['config']['policy']=='P0':
                for o in r['outcomes']:o['e2e_ns']=20000000
        result=m.compare(rows,self.f,self.s)
        self.assertEqual(result['status'],'deadline_panel_accuracy_partly_supported')
        self.assertEqual(result['matched_accuracy_supported'],dict(P0=False,P1=True))

    def test_hard_cutoff_not_hidden_in_panel_average(self):
        rows=calibration(self.s)
        for r in rows:
            r['outcomes']=[dict(success=True,e2e_ns=i*1000+10000000) for i in range(400)]
        f=m.fit(rows,self.s);targets=validation(self.s)
        # Exactly reproduces the reference at both rates except moving 8% of
        # probability mass across only the median cutoff. Panel average <5pp.
        for r in targets:
            r['outcomes']=[dict(success=True,e2e_ns=(i*400//300)*1000+10000000) for i in range(300)]
            median=f['panels'][r['config']['policy']][2]['deadline_ns']
            eligible=[o for o in r['outcomes'] if median-40000<=o['e2e_ns']<=median]
            self.assertGreaterEqual(len(eligible),24)
            for o in eligible[:24]:o['e2e_ns']=median+1
        result=m.compare(targets,f,self.s)
        for p in c.POLICIES:
            scores=result['policies'][p]['methods']['matched']
            self.assertLess(scores['panel_average']['mean'],5)
            self.assertGreater(scores['worst_cutoff_block_score']['mean'],5)
            self.assertFalse(result['policies'][p]['matched_accuracy_supported'])

    def test_duplicates_remain_five_labels_but_one_computation_deadline(self):
        for p in c.POLICIES:self.assertEqual(len(self.f['panels'][p]),5)
        self.assertEqual(len(m.deadlines(self.f,self.s['validation'][0])),2)
        result=m.compare(validation(self.s),self.f,self.s)
        self.assertTrue(all(len(r['panel'])==5 for r in result['errors']))

    def test_incomplete_validation_or_reordering_refused(self):
        for mode in ('cohort','outcome','warmup','reorder'):
            rows=validation(self.s)
            if mode=='cohort':rows.pop()
            if mode=='outcome':rows[0]['outcomes'].pop()
            if mode=='warmup':rows[0]['warmup_outcomes'].pop()
            if mode=='reorder':rows[0],rows[1]=rows[1],rows[0]
            with self.subTest(mode=mode),self.assertRaises(ValueError):m.compare(rows,self.f,self.s)

    def test_throttling_failures_retained_in_scores(self):
        rows=validation(self.s)
        for r in rows:
            r['observations']=['measurement_throttling'];r['outcomes'][0].update(success=False,e2e_ns=None)
        result=m.compare(rows,self.f,self.s)
        self.assertEqual(len(result['errors']),24)
        self.assertEqual(result['errors'][0]['panel'][0]['observed'],1/300)
        self.assertNotEqual(result['status'],'technical_invalid')
        self.assertTrue(all('measurement_throttling' in r['observations'] for r in result['cohort_observations']))

    def test_warmup_weight_failure_mass_and_undeclared_cutoff(self):
        cfg=self.s['validation'][0];warm=[dict(success=False,e2e_ns=None) for _ in range(25)]
        d=self.f['panels'][cfg['policy']][0]['deadline_ns'];pred=m.predictions(self.f,cfg,warm,d)
        self.assertEqual(pred['warmup'],1)
        self.assertAlmostEqual(pred['matched_update'],25/825)
        with self.assertRaises(ValueError):m.predictions(self.f,cfg,warm,123)
        altered=copy.deepcopy(self.f);altered['validation_used']=True
        with self.assertRaises(ValueError):m.deadlines(altered,cfg)
        altered=copy.deepcopy(self.f);altered['panels'][cfg['policy']][0]['deadline_ns']+=1
        with self.assertRaises(ValueError):m.deadlines(altered,cfg)

    def test_rounded_t_multiplier_family_coverage(self):
        # Exact df=5 Student-t upper tail via x=sqrt(5)*tan(theta),
        # density integration cos(theta)^4, no external numerical library.
        import math
        t=c.PROTOCOL['primary_t_multiplier'];theta=math.atan(t/math.sqrt(5))
        primitive=3*theta/8+math.sin(2*theta)/4+math.sin(4*theta)/32
        tail=.5-primitive/(3*math.pi/8)
        self.assertLessEqual(2*tail,.025)
        self.assertGreater(2*tail,.0249)
        self.assertLessEqual(2*(2*tail),.05)

    def test_actual_long_calibration_parser_and_lifetime_reserve(self):
        for cfg in self.s['qualification']+self.s['calibration']:
            self.assertTrue(all(o['success'] for o in m.outcomes(oldtest.client(cfg),cfg)))
            service=type('Service',(),dict(started=0))()
            with patch.object(study.time,'monotonic',return_value=0):study.offer_budget(service,cfg,True)
        cfg=self.s['calibration'][0]
        with patch.object(study.time,'monotonic',return_value=30),self.assertRaises(ValueError):study.offer_budget(service,cfg,True)
        with patch.object(study.time,'monotonic',return_value=33),self.assertRaises(ValueError):study.offer_budget(service,cfg,False)


class BarrierTests(unittest.TestCase):
    def test_raw_replay_rejects_future_or_tampered_warm_forecasts(self):
        s=c.schedule(1);cfg=s['validation'][0];f=m.fit(calibration(s),s);row=validation(s)[0]
        ref=dict(sealed_monotonic=1,evidence_seal_sha256='fixture')
        with tempfile.TemporaryDirectory() as temp,patch.object(c,'verify_evidence'), \
             patch.object(study,'identity'),patch.object(study,'analyze',return_value=row):
            case=Path(temp)
            c.save(case/'result.json',row)
            c.save(case/'trial-start.json',dict(monotonic=2,forecast_ref=ref))
            c.save(case/'warmup-timing.json',dict(started_monotonic=3,finished_monotonic=4))
            c.save(case/'measurement-start.json',dict(monotonic=6))
            warm=dict(predictions={str(d):m.predictions(f,cfg,row['warmup_outcomes'],d) for d in m.deadlines(f,cfg)},
                sealed_monotonic=5,measurement_used=False,forecast_ref=ref)
            c.save(case/'warmup-forecast.json',warm)
            self.assertEqual(study.replay_case(case,cfg,f,ref),row)
            for mode in ('future','tampered','flag','acquisition'):
                value=copy.deepcopy(warm)
                if mode=='future':value['sealed_monotonic']=7
                if mode=='tampered':next(iter(value['predictions'].values()))['matched']+=.1
                if mode=='flag':value['measurement_used']=True
                if mode=='acquisition':value['sealed_monotonic']=3.5
                (case/'warmup-forecast.json').write_text(json.dumps(value))
                with self.subTest(mode=mode),self.assertRaises(ValueError):study.replay_case(case,cfg,f,ref)

    def test_fake_service_seals_all_cutoffs_before_measurement_and_cleans_up(self):
        s=c.schedule(1);cfg=s['validation'][0];f=m.fit(calibration(s),s)
        events=[];ref=dict(sealed_monotonic=0,evidence_seal_sha256='fixture')
        class Policy:
            def __init__(self,case):pass
            def set(self,p):return {}
            def check(self):return {}
            def close(self):events.append('policy_closed')
        class Service:
            def __init__(self,case,*args):self.case=case;self.group='fake';self.started=study.time.monotonic()
            def start(self):events.append('service_started')
            def status(self):return {}
            def guard(self):return {}
            def collect(self,prefix,count):
                if prefix=='measurement':
                    warm=c.read(self.case/'warmup-forecast.json')
                    if sorted(map(int,warm['predictions']))!=m.deadlines(f,cfg):raise AssertionError('Missing panel')
                    if warm['measurement_used']:raise AssertionError('Future used')
                    if warm['sealed_monotonic']>c.read(self.case/'measurement-start.json')['monotonic']:raise AssertionError('Future seal')
                    events.append('measurement_started')
                c.save(self.case/(prefix+'.json'),oldtest.client(cfg,prefix))
            def close(self):events.append('service_closed')
        with tempfile.TemporaryDirectory() as temp,patch.object(study,'Policy',Policy), \
             patch.object(study.old,'Service',Service),patch.object(study.h,'desktop_absent'), \
             patch.object(study.time,'sleep'),patch.object(study.h.fixtures,'stat',return_value={'usage_usec':0}), \
             patch.object(study.q,'drained',return_value=True),patch.object(study,'sibling_context',return_value={}), \
             patch.object(study,'analyze',return_value={}),patch.object(study,'identity'), \
             patch.object(c,'sources',return_value={}),patch.object(c.old.n,'source_hashes',return_value={}):
            study.trial(Path(temp)/'case',cfg,f,ref)
        self.assertEqual(events,['service_started','measurement_started','service_closed','policy_closed'])


if __name__=='__main__':unittest.main()
