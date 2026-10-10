"""V23 factor transfer, period-aware recovery and calibration leakage regressions."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import v23_common as c
import v23_model as model
import v23_raw as raw
import v23_verify as verify
import v23_study as runner


def fixture(size,index,mu):
    vec=c.read(c.DESIGN/(size+'_C_offsets_ns.json'));pred,_=model.simulate(vec,mu)
    jobs=[dict(id=r['id'],admission_ns=vec[r['id']],worker_start_ns=r['start_ns'],
               completion_ns=r['completion_sec']*1e9) for r in pred if not r['rejected']]
    return dict(clocks=dict(client_test_start_ns=0,server_minus_client_lower_ns=0,server_minus_client_upper_ns=0),
        summary=dict(trial=f'cal_{size}_{index}',cpu_usec_per_completed_work=.5/mu*1e6)),dict(events=jobs)


class V23Tests(unittest.TestCase):
    def test_cohorts_normalize_sha_work_and_native_inverse_matches_every_offset(self):
        for cfg in c.matrix():
            vec=c.schedule(cfg);self.assertEqual(len(vec)*cfg['iterations'],298848000)
            native=dict(cfg,functional=True)
            self.assertEqual(vec,c.schedule(native))
            self.assertEqual(len(vec),6792 if cfg['size']=='small' else 3396)

    def test_balanced_positions_and_arm_orders_at_each_size(self):
        positions={};pairs={s:[] for s in ('small','large')}
        for b in range(1,5):
            rows=[r for r in c.matrix() if r['role']=='validation' and r['block']==b]
            for pos,r in enumerate(rows):positions.setdefault((r['size'],r['arm']),[]).append(pos)
            for size in pairs:pairs[size].append(''.join(r['arm'] for r in rows if r['size']==size))
        self.assertTrue(all(sorted(v)==[0,1,2,3] for v in positions.values()))
        self.assertTrue(all(v.count('AB')==2 and v.count('BA')==2 for v in pairs.values()))

    def test_same_size_warmup_is_identical_for_both_treatments(self):
        for size in ('small','large'):
            cfg=[r for r in c.matrix() if r['role']=='qualification' and r['size']==size]
            vectors=[c.schedule(c.warmup_config(r)) for r in cfg]
            self.assertEqual(vectors[0],vectors[1]);self.assertEqual(c.warmup_config(cfg[0])['burst_period_sec'],10)
            self.assertEqual(vectors[0],c.read(c.DESIGN/(size+'_warmup_offsets_ns.json')))

    def test_short_and_long_burst_forecasts_differ_without_refitting(self):
        cfgs=[r for r in c.matrix() if r['role']=='qualification' and r['size']=='small']
        sm={r['arm']:model.simulate(c.schedule(r),150,r['burst_period_sec'])[1] for r in cfgs}
        self.assertEqual(sm['A']['miss_pct'],0);self.assertGreater(sm['B']['miss_pct'],0)
        self.assertEqual(len(sm['A']['recovery_cycles_sec']),19);self.assertEqual(len(sm['B']['recovery_cycles_sec']),4)

    def test_recovery_censoring_uses_new_half_cycle_horizon(self):
        q=([0,5e9],[10,0])
        short=model.recovery_bounds(q,(0,0),switches=(3,),horizon_sec=1.5)
        long=model.recovery_bounds(q,(0,0),switches=(3,),horizon_sec=6)
        self.assertTrue(short['possibly_censored']);self.assertFalse(long['possibly_censored'])
        self.assertEqual(long['lower_sec'],2)

    def test_completion_tie_and_finite_queue_are_preserved(self):
        rows,summary=model.simulate([0]*130,1,3)
        self.assertEqual(summary['queue_peak'],128);self.assertEqual(summary['rejections'],1)
        rows,_=model.simulate([0,500000000],2,12)
        self.assertEqual(rows[1]['start_sec'],.5);self.assertTrue(all(r['timely_500'] for r in rows))

    def test_work_sizes_require_their_own_independent_calibration(self):
        a,sa=fixture('small',1,150);b,sb=fixture('small',2,150)
        result=model.calibration([a,b],[sa,sb],c.design(),'small')
        self.assertTrue(result['passed']);self.assertEqual(result['mu_busy'],150)
        with self.assertRaisesRegex(ValueError,'non-calibration'):
            model.calibration([a,b],[sa,sb],c.design(),'large')

    def test_invalid_or_duplicate_calibration_is_not_replaced(self):
        a,sa=fixture('small',1,200);b,sb=fixture('small',2,200)
        self.assertFalse(model.calibration([a,b],[sa,sb],c.design(),'small')['passed'])
        a,sa=fixture('small',1,150)
        with self.assertRaisesRegex(ValueError,'duplicate'):
            model.calibration([a,a],[sa,sa],c.design(),'small')

    def test_calibration_loader_reads_only_selected_size_and_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);called=[]
            def choose(session,cfg):
                called.append(cfg['trial']);d=s/cfg['trial'];d.mkdir()
                c.save(d/'server_metrics.json',{});c.save(d/'seal.json',{});return d
            with patch.object(verify,'accepted',side_effect=choose),patch.object(verify,'verify_trial',return_value={}):
                _,_,refs=verify.calibration_inputs(s,{},'large')
            self.assertEqual(called,['cal_large_1','cal_large_2']);self.assertEqual(set(refs),set(called))

    def test_all_size_predictions_seal_together_and_resealed_corruption_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);(s/'preparation').mkdir();c.save(s/'preparation/seal.json',{});c.save(s/'environment_seal.json',{})
            fixture_rows={}
            for cfg in c.matrix():
                if cfg['role']!='calibration':continue
                size=cfg['size'];index=int(cfg['trial'][-1]);mu=150 if size=='small' else 75
                derived,server=fixture(size,index,mu);d=s/'slots'/cfg['trial']/'attempt-1';d.mkdir(parents=True)
                c.save(d/'config.json',cfg);c.save(d/'server_metrics.json',server);c.save(d/'complete.json',{'valid':True});c.seal(d)
                fixture_rows[str(d)]=derived
            manifest={'design_seal':c.digest(c.DESIGN/'seal.json')}
            with patch.object(verify,'verify_qualification',return_value=manifest),patch.object(verify,'verify_trial',side_effect=lambda session,d,m:fixture_rows[str(d)]):
                forecast=runner.freeze_predictions(s);self.assertEqual(set(forecast['by_size']),{'small','large'})
                self.assertEqual(forecast,verify.verify_predictions(s,recompute=True))
                rows=c.read(s/'predictions/per_id.json');rows['large']['M_busy']['A'][0]['timely_500']=False
                c.save(s/'predictions/per_id.json',rows);c.seal(s/'predictions')
                with self.assertRaisesRegex(ValueError,'recomputation'):verify.verify_predictions(s,recompute=True)

    def test_no_validation_before_forecasts_or_replacement_after_attempt(self):
        cfg=next(r for r in c.matrix() if r['role']=='validation')
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp);d=s/'attempt'
            with patch.object(verify,'verify_predictions',side_effect=ValueError('missing forecasts')),patch.object(runner,'Service') as service:
                with self.assertRaisesRegex(ValueError,'missing'):runner.collect(s,d,cfg,'run')
                service.assert_not_called();self.assertFalse(d.exists())
            (s/'slots'/cfg['trial']/'attempt-1').mkdir(parents=True)
            with patch.object(verify,'verify_qualification',return_value={}):
                with self.assertRaisesRegex(ValueError,'after validation'):runner.freeze_predictions(s)

    def test_each_size_needs_all_trials_and_contrasts(self):
        prediction={'by_size':{size:{'point':{'M_busy':{'A':{'miss_pct':0},'B':{'miss_pct':10}}}} for size in ('small','large')}}
        rows=[]
        for cfg in c.matrix():
            if cfg['role']!='validation':continue
            models={name:dict(errors={'miss_error_pp':0},checks=dict(primary=True,queue=True,rejection=True,recovery=True)) for name in ('M_busy','M_cpu')}
            rows.append(dict(trial=cfg['trial'],size=cfg['size'],arm=cfg['arm'],observed={'miss_pct':0 if cfg['arm']=='A' else 10},models=models))
        self.assertTrue(model.report(rows,prediction)['primary_pass'])
        partial=model.report([r for r in rows if r['trial']!='b4_large_B'],prediction)
        self.assertFalse(partial['primary_pass']);self.assertTrue(partial['by_size']['small']['primary_pass'])
        bad=copy.deepcopy(rows);bad[0]['models']['M_busy']['checks']['primary']=False
        result=model.report(bad,prediction);self.assertFalse(result['primary_pass']);self.assertTrue(result['by_size']['large']['primary_pass'])
        contrast=copy.deepcopy(rows)
        for r in contrast:
            if r['trial']=='b1_small_A':r['observed']['miss_pct']=3
            if r['trial']=='b1_small_B':r['observed']['miss_pct']=7
        result=model.report(contrast,prediction);self.assertFalse(result['primary_pass'])
        self.assertTrue(all(r['models']['M_busy']['checks']['primary'] for r in contrast))

    def test_retained_stage_join_supports_new_pattern_metadata(self):
        from test_execution_delay import fixture_data,totals
        for cfg in c.functional_configs():
            client,server,_=fixture_data();client['requests']=[r for r in client['requests'] if r['ID']==0]
            for key in ('events','handler_events','entry_events'):server[key]=[r for r in server[key] if r['id']==0]
            client.update(total_scheduled=1,pattern=cfg['traffic_pattern'],target_rate=cfg['rate'],
                burst_low_rate=cfg['burst_low'],burst_high_rate=cfg['burst_high'],burst_period_sec=cfg['burst_period_sec'])
            totals(client,server)
            with patch.object(c,'schedule',return_value=[0]):
                rows,_,_=raw.join(client,server,cfg);self.assertEqual(len(rows),1)

    def test_observer_and_resource_ownership_prerequisites_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=Path(tmp)
            with self.assertRaisesRegex(ValueError,'root observer'):runner.bind_observer_inventory(s,None)
            with patch.object(verify.observer,'review',return_value={'boot_id':'foreign'}):
                with self.assertRaisesRegex(ValueError,'another boot'):runner.bind_observer_inventory(s,s/'audit.json')


if __name__=='__main__':unittest.main()
