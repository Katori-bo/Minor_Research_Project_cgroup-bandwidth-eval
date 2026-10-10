import copy
import json
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import execution_state_continuation as s
import execution_state_continuation_helper as helper


def old_rows():return s.parent_rows()


def new_rows():
    source={r['arm']:r for r in old_rows() if r['condition']=='automatic'}
    return [dict(source[r['arm']],**r) for r in s.matrix()]


class Continuation(unittest.TestCase):
    def test_only_remaining_automatic_cells_in_source_order(self):
        self.assertEqual([r['trial'] for r in s.matrix()],['b2_D','b2_C','b2_B','b2_A'])
        self.assertTrue(all(r['condition']=='automatic' for r in s.matrix()))
        self.assertEqual([r['order'] for r in s.matrix()],[13,14,15,16])

    def test_collector_adapter_restores_everything_on_error(self):
        original=s.pilot.matrix;limits=dict(s.pilot.LIMITS)
        with self.assertRaises(RuntimeError):
            with s.collector_context():
                self.assertEqual(s.pilot.matrix(),s.matrix())
                self.assertEqual(s.pilot.LIMITS['wall_ceiling_sec'],4500)
                raise RuntimeError('test')
        self.assertIs(s.pilot.matrix,original);self.assertEqual(s.pilot.LIMITS,limits)

    def test_cadence_duration_thermal_thresholds_preserved(self):
        with s.collector_context():
            policy=s.pilot.thermal_policy(True)
            self.assertEqual(policy['initial_idle_sec'],1200)
            for f in ['window_sec','max_range_c','max_abs_slope_c_per_min','baseline_tolerance_c']:
                self.assertEqual(policy[f],s.pilot.ORIGINAL_THERMAL_POLICY[f])
            for r in s.matrix():self.assertEqual(s.pilot.durations(r)['MINIMAL_MEASURE_MS'],'60000')

    def test_no_large_period_signal_and_no_causal_combination(self):
        result=s.compare(new_rows(),old_rows())
        self.assertEqual(result['decision'],'continuation_no_consistent_large_period_signal')
        self.assertTrue(result['observer_qualified'])
        self.assertFalse(result['original_uninterrupted_protocol_complete'])
        self.assertFalse(result['cross_session_interaction_causal'])
        self.assertFalse(result['historical_cause_established'])

    def test_penalty_requires_both_observer_states(self):
        rows=new_rows()
        for r in rows:
            if r['period_ms']==20:r['cpu_usec_per_completed_work']*=1.08;r['capacity']/=1.08
        self.assertEqual(s.compare(rows,old_rows())['decision'],'shorter_period_penalty_observed_in_new_baseline_continuation')

    def test_observer_failure_prevents_positive_interpretation(self):
        rows=new_rows()
        for r in rows:
            if r['counters']:r['cpu_usec_per_completed_work']*=1.03
        self.assertEqual(s.compare(rows,old_rows())['decision'],'continuation_observer_not_qualified')

    def test_missing_duplicate_nonfinite_rejected(self):
        rows=new_rows();old=old_rows()
        for bad in [rows[:-1],rows[:-1]+[rows[0]]]:
            with self.assertRaises(ValueError):s.compare(bad,old)
        for value in [0,float('nan'),float('inf')]:
            bad=copy.deepcopy(rows);bad[0]['cpu_usec_per_completed_work']=value
            with self.assertRaises(ValueError):s.compare(bad,old)

    def test_parent_raw_replay_still_passes(self):
        rows=old_rows();self.assertEqual(len(rows),12)
        self.assertEqual(s.pilot.compare(rows[:8],False),s.c.read(s.SOURCE/'feasibility.json'))

    def test_final_analysis_verifies_extended_baseline_and_restores_policy(self):
        before=dict(s.gc.run.old.POLICY)
        self.assertEqual(s.verified_environment(s.SOURCE),s.c.read(s.SOURCE/'conditions/automatic/environment.json'))
        self.assertEqual(s.gc.run.old.POLICY,before)

    def test_saved_functional_replay_uses_continuation_adapter(self):
        for period in (100,20):
            d=s.SOURCE/'preparation/functional'/str(period)
            self.assertEqual(s.replay(d,s.SOURCE,True),s.c.read(d/'pilot_derived.json'))

    def test_remaining_labels_exercise_real_performance_validation(self):
        # Relabel only the reader's in-memory spec for this unit test. No raw
        # files are edited, and no relabeled result is saved or used as data.
        for spec in s.matrix():
            d=s.SOURCE/'trials'/('b1_'+spec['arm']);read=s.c.read
            def labeled(path):
                return dict(spec) if path==d/'pilot_config.json' else read(path)
            with patch.object(s.c,'read',side_effect=labeled), \
                 patch.object(s.pilot,'verify_trial_settling',wraps=s.pilot.verify_trial_settling) as thermal, \
                 patch.object(s.pilot,'counter_metrics',wraps=s.pilot.counter_metrics) as counters:
                result=s.replay(d,s.SOURCE)
            thermal.assert_called_once();counters.assert_called_once()
            self.assertEqual(result['summary']['trial'],spec['trial'])
            self.assertEqual(result['summary']['condition'],'automatic')
            self.assertEqual(result['counter']['counts'] is not None,spec['counters'])

    def helper_case(self,cleanup_failure=False,extra_arg=False):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);original=s.pilot.controls.snapshot()
            manifest=dict(controls_before=original,resource_baseline={},minimal_image='image',minimal_server_sha256='sha')
            s.c.save(session/'owner.json',dict(uid=1000));ops=['fixtures']
            for spec in s.matrix():
                d=session/'trials'/spec['trial'];d.mkdir(parents=True)
                s.c.save(d/'pilot_config.json',spec)
                s.c.save(d/'initial.json',dict(process_identity=dict(pid=1),cgroup='/sys/fs/cgroup/system.slice/docker-owned.scope',initial_limits={},container_server_sha256='sha'))
                s.c.save(d/'container.json',dict(inspect=dict(Id='owned',HostConfig={},Image='image')))
                ops+=['condition','attach','enable','disable','detach']
            ops+=['finish']
            messages=['{"op":"'+op+'"}' for op in ops]
            if extra_arg:messages=['{"op":"fixtures","command":"bad"}']
            class Counter:
                def __init__(self,d,g,e):self.directory=d;self.state='disabled'
                def control(self,op):self.state='enabled' if op=='enable' else 'disabled';return {}
                def close(self):
                    if cleanup_failure:raise RuntimeError('counter cleanup failed')
            with patch.dict(helper.os.environ,{'SUDO_UID':'1000','SUDO_GID':'1000'}), \
                 patch.object(helper.os,'geteuid',return_value=0),patch.object(helper.os,'sched_setaffinity'), \
                 patch.object(helper.signal,'signal'),patch.object(helper.screen,'verify',return_value=manifest), \
                 patch.object(helper.c,'same_process',return_value=True),patch.object(helper.os,'chown'), \
                 patch.object(helper.controls,'snapshot',return_value=original), \
                 patch.object(helper.controls,'set_bounds') as writes,patch.object(helper.controls,'restore') as restores, \
                 patch.object(helper.select,'select',return_value=([1],[],[])), \
                 patch.object(helper.hw,'line',side_effect=messages), \
                 patch.object(helper.hw,'fixture',side_effect=lambda d,m,e:d.mkdir()), \
                 patch.object(helper.screen.pilot.pc,'validate_fixtures',return_value=dict(passed=True)), \
                 patch.object(helper.c,'validate_resources'), \
                 patch.object(helper.bridge,'cgroup',return_value=Path('/sys/fs/cgroup/system.slice/docker-owned.scope')), \
                 patch.object(helper.hw,'Counter',Counter),patch('builtins.print'):
                if cleanup_failure:
                    with self.assertRaises(RuntimeError):helper.helper(session)
                elif extra_arg:
                    with self.assertRaises(ValueError):helper.helper(session)
                else:helper.helper(session)
                writes.assert_not_called();restores.assert_not_called()
                receipt=s.c.read(session/'speed_control/restoration.json')
                self.assertTrue(receipt['restored']);self.assertEqual(receipt['changes_applied'],[])

    def test_helper_finishes_exact_four_with_read_only_cpu_settings(self):self.helper_case()
    def test_helper_cleanup_failure_still_saves_control_receipt(self):self.helper_case(cleanup_failure=True)
    def test_helper_rejects_extra_ipc_arguments(self):self.helper_case(extra_arg=True)

    def test_streaming_monitor_writes_before_exit_and_finalizes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'host.json'
            process=subprocess.Popen([sys.executable,str(s.ROOT/'diagnostic/execution_state_stream_monitor.py'),
                '--interval','.1','--output',str(output)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            try:
                until=time.monotonic()+10
                while time.monotonic()<until:
                    if process.poll() is not None:raise AssertionError(process.stderr.read().decode())
                    if output.exists() and output.stat().st_size>100:break
                    time.sleep(.05)
                self.assertGreater(output.stat().st_size,100)
                process.send_signal(signal.SIGINT);stdout,stderr=process.communicate(timeout=5)
                self.assertEqual(process.returncode,0,stderr.decode())
                rows=json.loads(output.read_text());self.assertGreaterEqual(len(rows),1)
                for f in ['timestamp','process_cpu_deltas','power_settings','cpu_util_pct','temps_c','freqs_mhz']:
                    self.assertIn(f,rows[0])
            finally:
                if process.poll() is None:process.kill();process.communicate()

if __name__=='__main__':unittest.main()
