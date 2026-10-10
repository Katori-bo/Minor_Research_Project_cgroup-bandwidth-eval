import copy
from pathlib import Path
import unittest
from unittest.mock import patch
import v20_background_app as s


def monitor(opened):
    return [dict(process_interval_sec=1,chatgpt_present=opened,
        process_cpu_deltas=[dict(comm='plasmashell',cpu_delta_sec=.1)]+
        ([dict(comm='ChatGPT',cpu_delta_sec=.02)] if opened else [])) for _ in range(80)]


def rows():
    out=[]
    for spec in s.matrix():
        cost=3600*(1.056 if spec['period_ms']==20 else 1)
        if spec['app_open']: cost=3600*(.987 if spec['period_ms']==20 else 1)
        out.append(dict(spec,cpu_usec_per_completed_work=cost,capacity=150,
                        timely_500_fraction=.8))
    return out


class Background(unittest.TestCase):
    def test_opposite_order_preserves_original_contract(self):
        self.assertEqual([r['arm'] for r in s.matrix()],list('ABCDDCBA'))
        self.assertEqual([r['order'] for r in s.matrix()],list(range(1,9)))
        for spec in s.matrix():
            cfg=s.original_config(spec);s.c.validate_config(cfg)
            self.assertEqual(cfg['duration_sec'],60)
            self.assertFalse(cfg['worker_yield'])
            self.assertEqual(len(s.c.schedule(cfg)),6793)

    def test_presence_is_required_in_every_sample(self):
        r=monitor(True);self.assertTrue(s.monitor_condition(r,True)['app_open'])
        r[-1]=monitor(False)[0]
        with self.assertRaises(ValueError):s.monitor_condition(r,True)

    def test_closed_rejects_app_and_flags_disagreement(self):
        with self.assertRaises(ValueError):s.monitor_condition(monitor(True),False)
        r=monitor(True);r[0]['chatgpt_present']=False
        with self.assertRaises(ValueError):s.monitor_condition(r,True)

    def test_insufficient_samples_rejected(self):
        with self.assertRaises(ValueError):s.monitor_condition(monitor(False)[:-1],False)

    def test_host_cpu_uses_interval_deltas(self):
        r=s.monitor_condition(monitor(True),True)
        self.assertAlmostEqual(r['named_app_cpu_pct_one_core'],2)
        self.assertAlmostEqual(r['plasma_kwin_cpu_pct_one_core'],10)

    def test_large_interaction_screen(self):
        r=s.compare(rows())
        self.assertEqual(r['decision'],'app_presence_changes_period_contrast_in_this_screen')
        self.assertFalse(r['historical_cause_established'])

    def test_app_slowing_both_periods_equally_is_not_interaction(self):
        a=rows()
        for r in a:
            r['cpu_usec_per_completed_work']=3600*(1.056 if r['period_ms']==20 else 1)*(1.2 if r['app_open'] else 1)
        self.assertEqual(s.compare(a)['decision'],'app_presence_did_not_show_a_consistent_large_period_interaction')

    def test_missing_cell_rejected(self):
        with self.assertRaises(ValueError):s.compare(rows()[:-1])

    def test_intentional_quiet_exception_preserves_raw_flags(self):
        directory=Path('/tmp/background-test');raw=monitor(True);before=copy.deepcopy(raw)
        spec=s.matrix()[2]
        saved={'background_config.json':spec,'config.json':s.original_config(spec),'monitor.json':raw}
        def read(p):return saved[p.name]
        def replay(p,functional=False):
            self.assertTrue(all(not r['chatgpt_present'] for r in s.c.read(p/'monitor.json')))
            return dict(summary={})
        with patch.object(s.c,'read',side_effect=read),patch.object(s,'RAW_REPLAY',side_effect=replay):
            result=s.replay(directory)
        self.assertEqual(raw,before)
        self.assertTrue(result['background_state']['app_open'])

    def test_thermal_criteria_not_relaxed(self):
        for initial in (False,True):
            p=s.policy(initial)
            for k in ('window_sec','max_range_c','max_abs_slope_c_per_min','baseline_tolerance_c'):
                self.assertEqual(p[k],s.ORIGINAL_POLICY[k])

    def test_idle_app_uses_original_affinity_instead_of_controller_affinity(self):
        app=s.App([0,1,2,3,4,5])
        self.assertEqual(app.affinity,{0,1,2,3,4,5})

    def test_cleanup_targets_only_owned_group(self):
        app=s.App([0,1]);process=unittest.mock.Mock();process.pid=12345;app.process=process
        with patch.object(s,'group_members',return_value=[]),patch.object(s.os,'killpg') as kill:
            app.close()
        kill.assert_called_once_with(12345,s.signal.SIGTERM)
        process.wait.assert_called_once_with(timeout=5)

    def test_main_app_reaped_during_helper_cleanup(self):
        app=s.App([0,1]);process=unittest.mock.Mock();process.pid=12345;app.process=process
        with patch.object(s,'group_members',side_effect=[[dict(pid=12346)],[],[]]),\
                patch.object(s.os,'killpg'),patch.object(s.time,'sleep'):
            app.close()
        process.poll.assert_called_once()


if __name__=='__main__':unittest.main()
