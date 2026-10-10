"""Scientific transfer, leak prevention and owned unattended-lifecycle checks."""
from fractions import Fraction
import copy
from pathlib import Path
import statistics as st
import tempfile
import unittest
from unittest.mock import patch

import v29_common as c
import v29_model as model
import v29_campaign as campaign


def calibration_rows():
    result=[]
    for cfg in c.calibration_configs():
        kind=cfg['role'];wall=61 if kind=='mixed' else 30
        n=len(c.schedule(cfg));demand=(1/300)*(cfg['iterations']/44000)
        cpu=.002*wall+demand*n
        row=dict(trial=cfg['trial'],context=c.ACTIVE,role=kind,block=cfg['block'],order=cfg['order'],
                 low_rate=cfg['low_rate'],period_sec=cfg['burst_period_sec'],offers=n,completed=n,
                 cpu_sec=cpu,accounted_wall_sec=wall,utilization=cpu/wall,throughput_rps=n/wall,
                 all_successful=True,state_eligible=True,queue_peak=0,throttled_periods=0)
        if kind=='mixed':
            capacity=150*c.SCALE
            row.update(busy_capacity_rps=capacity,busy_capacity_bounds_rps=[capacity*.999,capacity*1.001],whole_cpu_sec_per_job=cpu/n)
        result.append(row)
    return result


def validation_rows(predictions):
    capacity=150*c.SCALE
    return [dict(trial=cfg['trial'],role='validation',context=c.ACTIVE,block=cfg['block'],order=cfg['order'],
                 low_rate=cfg['low_rate'],period_sec=cfg['burst_period_sec'],all_successful=True,state_eligible=True,
                 busy_capacity_rps=capacity,busy_capacity_bounds_rps=[capacity*.999,capacity*1.001],
                 miss_pct=predictions['busy'][cfg['trial']]['miss_pct'],
                 deadline_miss_pct=copy.deepcopy(predictions['busy'][cfg['trial']]['deadline_miss_pct']))
            for cfg in c.validation_configs()]


class FrozenTransferTests(unittest.TestCase):
    def test_context_contract_and_no_future_inputs(self):
        matrix=c.matrix()
        self.assertEqual(len(matrix),32)
        self.assertEqual(len(c.calibration_configs()),16)
        self.assertEqual(len(c.validation_configs()),16)
        self.assertTrue(all(x['quota_us']==c.CONTEXT['quota_us'] and x['iterations']==c.CONTEXT['iterations'] and not x['counter_probe'] for x in matrix))
        self.assertLess(max(x['order'] for x in c.calibration_configs()),min(x['order'] for x in c.validation_configs()))
        for reference in (15,30):
            for period in (6,12):
                selected=[x for x in c.validation_configs() if x['reference_low_rate']==reference and x['burst_period_sec']==period]
                self.assertEqual(sorted((x['order']-17)%4 for x in selected),[0,1,2,3])

    def test_fractional_rates_against_exact_rational_oracle(self):
        for cfg in c.validation_configs():
            expected=[];period=cfg['burst_period_sec'];a=cfg['burst_low_duration_sec']
            for cycle in range(60//period):
                for start,duration,rate in ((0,a,cfg['low_rate']),(a,period-a,cfg['burst_high'])):
                    rate=Fraction(str(rate));count=duration*rate
                    self.assertEqual(count.denominator,1)
                    for i in range(int(count)):
                        stamp=(Fraction(cycle*period+start)+i/rate)*10**9
                        expected.append((2*stamp.numerator+stamp.denominator)//(2*stamp.denominator))
            self.assertEqual(expected,c.schedule(cfg))
            self.assertEqual(len(expected),round((3600+40*cfg['reference_low_rate'])*c.SCALE))

    def test_mutated_resource_or_counter_rejected(self):
        cfg=c.matrix()[0]
        for changed in (dict(cfg,quota_us=cfg['quota_us']+1000),dict(cfg,counter_probe=True),dict(cfg,iterations=1)):
            with self.assertRaises(ValueError):c.validate_config(changed)

    def test_context_directory_cannot_point_to_old_paper_run(self):
        with self.assertRaises(ValueError):c.owned_directory(c.HISTORY)
        with self.assertRaises(ValueError):campaign.validate_directory(c.HISTORY)


class CalibrationAndDeadlineTests(unittest.TestCase):
    def test_known_cpu_demand_uses_actual_quota_and_size(self):
        cal=model.calibrate(calibration_rows(),c.design())
        self.assertTrue(cal['usable'])
        demand=(1/300)*(c.CONTEXT['iterations']/44000)
        expected=(c.CONTEXT['quota_us']/100000-.002)/demand
        self.assertAlmostEqual(cal['methods']['regression']['capacity_rps'],expected)
        self.assertAlmostEqual(cal['methods']['quadratic']['capacity_rps'],expected)
        self.assertAlmostEqual(cal['methods']['idle_corrected']['capacity_rps'],expected)
        self.assertEqual(cal['methods']['busy']['capacity_rps'],150*c.SCALE)

    def test_missing_calibration_and_validation_leak_rejected(self):
        with self.assertRaises(ValueError):model.calibrate(calibration_rows()[:-1],c.design())
        rows=calibration_rows();rows[0]['role']='validation'
        with self.assertRaises(ValueError):model.calibrate(rows,c.design())

    def test_failure_is_not_repaired_by_another_context(self):
        rows=calibration_rows();rows[0]['state_eligible']=False
        cal=model.calibrate(rows,c.design())
        self.assertFalse(cal['usable'])
        with self.assertRaises(ValueError):model.forecast(cal,c.validation_configs())

    def test_all_six_deadlines_frozen_and_monotone(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,per_id=model.forecast(cal,c.validation_configs())
        for method in model.METHODS:
            for cfg in c.validation_configs():
                grid=pred[method][cfg['trial']]['deadline_miss_pct']
                self.assertEqual(set(grid),set(map(str,c.DEADLINES_MS)))
                values=[grid[str(ms)] for ms in c.DEADLINES_MS]
                self.assertEqual(values,sorted(values,reverse=True))
                self.assertEqual(grid['500'],pred[method][cfg['trial']]['miss_pct'])
                self.assertEqual(len(per_id[method][cfg['trial']]),len(c.schedule(cfg)))

    def test_secondary_failure_cannot_change_primary_screen(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,_=model.forecast(cal,c.validation_configs())
        rows=validation_rows(pred);before=model.report(rows,cal,pred,c.design(),True)
        for row in rows:row['deadline_miss_pct']['25']+=4
        after=model.report(rows,cal,pred,c.design(),True)
        self.assertEqual(before['decision'],after['decision'])
        self.assertAlmostEqual(after['deadline_grid']['busy']['25']['mae_pp'],4)
        self.assertEqual(after['deadline_grid']['busy']['500']['mae_pp'],0)
        self.assertFalse(after['novelty_established'])

    def test_incomplete_validation_never_becomes_complete(self):
        cal=model.calibrate(calibration_rows(),c.design());pred,_=model.forecast(cal,c.validation_configs())
        rows=validation_rows(pred)
        report=model.report(rows[:-1],cal,pred,c.design(),False)
        self.assertFalse(report['complete']);self.assertEqual(report['decision'],'comparison_incomplete')
        with self.assertRaises(ValueError):model.report(rows+[rows[0]],cal,pred,c.design(),True)


class SupervisorTests(unittest.TestCase):
    def test_inventory_path_satisfies_retained_review_boundary(self):
        import leftover_observer_review as reviewer
        path=campaign.observer_audit_path(campaign.PARENT/'generation-02')
        self.assertEqual(path.parent,reviewer.ROOT/'analysis/runtime_io_leftover_observer_audit')
        # Exercise the real retained reviewer on the original accepted audit;
        # the new launcher must use that same directory contract.
        receipt=c.read(c.HISTORY/'observer_review/receipt.json')
        self.assertTrue(reviewer.review(receipt['audit_path'])['performance_eligible'])

    def test_dead_process_never_receives_signal(self):
        with patch.object(campaign.c,'same_process',return_value=False),patch.object(campaign.os,'killpg') as kill:
            campaign.terminate(dict(pid=123,start_ticks='1',uid=1000))
        kill.assert_not_called()

    def test_cleanup_is_owned_and_context_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);owner=dict(pid=123,start_ticks='1',uid=1000)
            for name,value in (('ours',owner),('others',dict(pid=456,start_ticks='2',uid=1000))):
                c.save(session/name/'ownership.json',dict(owner=value,container=name,nonce=name))
            with patch.object(campaign,'remove_owned') as cleanup:
                self.assertEqual(campaign.cleanup_context(session,owner),[])
                cleanup.assert_called_once_with('ours','ours')

    def test_cleanup_error_is_retained(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);owner=dict(pid=123,start_ticks='1',uid=1000)
            c.save(session/'trial/ownership.json',dict(owner=owner,container='ours',nonce='n'))
            with patch.object(campaign,'remove_owned',side_effect=RuntimeError('owned cleanup failed')):
                self.assertEqual(campaign.cleanup_context(session,owner),['owned cleanup failed'])

    def test_seven_hour_budget_includes_cleanup_reserve(self):
        self.assertEqual(campaign.TOTAL_SEC,25200)
        with tempfile.TemporaryDirectory() as temp,patch.object(campaign.subprocess,'Popen') as launch:
            with self.assertRaises(TimeoutError):campaign.invoke(Path(temp),['unused'],campaign.time.monotonic()+100)
            launch.assert_not_called()


if __name__=='__main__':unittest.main()
