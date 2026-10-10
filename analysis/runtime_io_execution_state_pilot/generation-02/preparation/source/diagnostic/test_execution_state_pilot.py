import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import execution_state_pilot as s
import execution_state_controls as ctl
import execution_state_helper as helper


def before():
    return {str(cpu):dict(scaling_driver='amd-pstate-epp',scaling_governor='powersave',
        energy_performance_preference='balance_performance',scaling_min_freq='1108930',
        scaling_max_freq='4280985',boost='1',related_cpus=str(cpu),
        cpuinfo_min_freq='412625',cpuinfo_max_freq='4280985',
        siblings='2-3' if cpu in (2,3) else '4-5',nominal_freq_mhz='3301') for cpu in ctl.CPUS}


def rows():
    result=[]
    for spec in s.matrix():
        cap=spec['condition']=='constrained'; short=spec['period_ms']==20
        rate=2.64e9 if cap else 3.4e9
        instructions=26709000
        cpu=instructions*2/rate*1e6*(1.1 if short and not cap else 1)
        result.append(dict(spec,cpu_usec_per_completed_work=cpu,capacity=500000/cpu,
            cpu_cores=.5,instructions_per_job=instructions,
            cycles_per_instruction=cpu*rate/1e6/instructions,cycles_per_user_cpu_sec=rate))
    return result


class Pilot(unittest.TestCase):
    def test_saved_performance_trial_reaches_environment_and_counter_checks(self):
        session=s.REPLAY_REGRESSION; directory=session/'trials/b1_A'
        self.assertEqual(s.c.read(directory/'failure.json')['error'],"name 'env' is not defined")
        with patch.object(s,'verify_trial_settling',wraps=s.verify_trial_settling) as thermal, \
             patch.object(s,'verify_speed_coverage',wraps=s.verify_speed_coverage) as coverage, \
             patch.object(s,'counter_metrics',wraps=s.counter_metrics) as counters:
            result=s.replay_measurements(directory,session)
        thermal.assert_called_once()
        self.assertEqual(thermal.call_args.args[1],s.c.read(directory/'environment.json'))
        coverage.assert_called_once(); counters.assert_called_once()
        self.assertEqual(result['summary']['completed'],9107)
        self.assertEqual(result['summary']['condition'],'automatic')
        self.assertIsNone(result['counter']['counts'])
        # A validated measurement must not erase the failed generation's status.
        with self.assertRaisesRegex(ValueError,'failed or interrupted'):
            s.replay(directory,session)

    def test_saved_performance_environment_mismatch_is_rejected(self):
        session=s.REPLAY_REGRESSION; directory=session/'trials/b1_A'
        read=s.c.read
        def altered(path):
            value=read(path)
            if path==directory/'environment.json':
                value=copy.deepcopy(value); value['baseline_c']={}
            return value
        with patch.object(s.c,'read',side_effect=altered):
            with self.assertRaisesRegex(ValueError,'environment provenance differs'):
                s.replay_measurements(directory,session)

    def test_balanced_sequence(self):
        self.assertEqual([r['arm'] for r in s.matrix()],list('ABCDEFGHHGFEDCBA'))
        self.assertEqual([r['order'] for r in s.matrix()],list(range(1,17)))

    def test_interaction_not_common_slowdown(self):
        a=rows()
        for r in a:
            if r['period_ms']==20 and r['condition']=='automatic':
                r['cpu_usec_per_completed_work']/=1.1; r['capacity']*=1.1
        result=s.compare(a)
        self.assertTrue(result['feasibility_passed'])
        self.assertEqual(result['decision'],'close_no_consistent_large_interaction')

    def test_supported_interaction(self):
        result=s.compare(rows())
        self.assertEqual(result['decision'],'supported_execution_control_period_interaction')
        self.assertFalse(result['historical_cause_established'])
        self.assertFalse(result['novelty_established'])

    def test_first_block_gate(self):
        self.assertEqual(s.compare(rows()[:8],False)['decision'],'feasibility_passed_continue_reverse_block')

    def test_counter_overhead_stops(self):
        a=rows()
        for r in a:
            if r['counters']: r['cpu_usec_per_completed_work']*=1.015
        result=s.compare(a)
        self.assertFalse(result['observer_qualified'])
        self.assertEqual(result['decision'],'stop_observer_not_qualified')

    def test_insufficient_speed_separation_stops(self):
        a=rows()
        for r in a: r['cycles_per_user_cpu_sec']=3e9
        self.assertEqual(s.compare(a)['decision'],'stop_execution_conditions_not_distinguished')

    def test_reverse_block_disagreement_not_supported(self):
        a=rows()
        for r in a:
            if r['block']==2 and r['period_ms']==20 and r['condition']=='constrained':
                r['cpu_usec_per_completed_work']*=1.3; r['capacity']/=1.3
        self.assertEqual(s.compare(a)['decision'],'close_no_consistent_large_interaction')

    def test_missing_duplicate_nonfinite_rejected(self):
        for a in [rows()[:-1],rows()[1:]+[rows()[1]]]:
            with self.assertRaises(ValueError): s.compare(a)
        for v in [0,float('nan'),float('inf')]:
            a=rows(); a[0]['cpu_usec_per_completed_work']=v
            with self.assertRaises(ValueError): s.compare(a)

    def test_same_measurement_duration_every_condition(self):
        for r in s.matrix(): self.assertEqual(s.durations(r)['MINIMAL_MEASURE_MS'],'60000')
        self.assertEqual(s.durations(s.matrix()[0],True)['MINIMAL_MEASURE_MS'],'2000')

    def test_original_thermal_thresholds_and_restoration(self):
        previous=dict(s.gc.run.old.POLICY)
        with patch.dict(s.gc.run.old.POLICY,s.thermal_policy(True)):
            self.assertEqual(s.gc.run.old.POLICY['initial_idle_sec'],1200)
        self.assertEqual(previous,s.gc.run.old.POLICY)
        for f in ['window_sec','max_range_c','max_abs_slope_c_per_min','baseline_tolerance_c']:
            self.assertEqual(s.thermal_policy()[f],s.ORIGINAL_THERMAL_POLICY[f])

    def test_target_from_nominal_no_other_mutation(self):
        original=before(); saved=copy.deepcopy(original); plan=ctl.plan(original)
        self.assertEqual(plan['target_khz'],2640000)
        self.assertEqual(original,saved)
        for cpu in ctl.CPUS:
            for key in original[str(cpu)]:
                if key not in ('scaling_min_freq','scaling_max_freq'):
                    self.assertEqual(plan['constrained'][str(cpu)][key],original[str(cpu)][key])

    def test_unsupported_driver_topology_scope_rejected(self):
        for field,value in [('scaling_driver','acpi-cpufreq'),('siblings','2,4'),('related_cpus','2 3')]:
            a=before(); a['2'][field]=value
            with self.assertRaises(ValueError): ctl.plan(a)

    def fake_sysfs(self,root):
        for cpu,r in before().items():
            p=root/f'cpu{cpu}'
            for field in ctl.FIELDS:
                f=p/'cpufreq'/field; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(r[field])
            for field,value in [('topology/thread_siblings_list',r['siblings']),('acpi_cppc/nominal_freq',r['nominal_freq_mhz'])]:
                f=p/field; f.parent.mkdir(parents=True,exist_ok=True); f.write_text(value)

    def test_bound_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fake_sysfs(root); original=ctl.snapshot(root)
            ctl.set_bounds(ctl.plan(original)['constrained'],root)
            self.assertEqual(ctl.snapshot(root),ctl.plan(original)['constrained'])
            self.assertTrue(ctl.restore(original,root)['restored'])
            self.assertEqual(ctl.snapshot(root),original)

    def test_restore_attempts_other_policies_after_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.fake_sysfs(root); original=ctl.snapshot(root)
            ctl.set_bounds(ctl.plan(original)['constrained'],root)
            f=root/'cpu2/cpufreq/scaling_max_freq'; f.unlink(); f.mkdir()
            result=ctl.restore(original,root)
            self.assertFalse(result['restored'])
            self.assertEqual((root/'cpu4/cpufreq/scaling_max_freq').read_text(),'4280985')

    def test_helper_restores_on_partial_control_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); original=before(); manifest=dict(controls_before=original,control_plan=ctl.plan(original))
            def read(path):
                if path.name=='owner.json': return dict(uid=1000)
                raise ValueError(path)
            result=dict(restored=True,errors=[],observed=original)
            with patch.dict(helper.os.environ,{'SUDO_UID':'1000','SUDO_GID':'1000'}), \
                 patch.object(helper.os,'geteuid',return_value=0),patch.object(helper.os,'sched_setaffinity'), \
                 patch.object(helper.signal,'signal'),patch.object(helper.screen,'verify',return_value=manifest), \
                 patch.object(helper.c,'read',side_effect=read),patch.object(helper.c,'same_process',return_value=True), \
                 patch.object(helper.os,'chown'),patch.object(helper.controls,'snapshot',return_value=original), \
                 patch.object(helper.select,'select',return_value=([1],[],[])), \
                 patch.object(helper.hw,'line',return_value='{"op":"selftest"}'), \
                 patch.object(helper.controls,'set_bounds',side_effect=OSError('partial write')), \
                 patch.object(helper.controls,'restore',return_value=result) as restore:
                with self.assertRaises(OSError): helper.helper(session)
                restore.assert_called_once_with(original)
            self.assertTrue(s.c.read(session/'speed_control/restoration.json')['restored'])

    def helper_case(self,stop_after_first=False,cleanup_failure=False):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); original=before(); plan=ctl.plan(original)
            manifest=dict(controls_before=original,control_plan=plan,resource_baseline={},minimal_image='image',minimal_server_sha256='sha')
            s.c.save(session/'owner.json',dict(uid=1000))
            s.c.save(session/'feasibility.json',dict(feasibility_passed=not stop_after_first))
            specs=s.matrix()[:8] if stop_after_first else s.matrix()
            for spec in specs:
                d=session/'trials'/spec['trial']; d.mkdir(parents=True)
                s.c.save(d/'pilot_config.json',spec)
                s.c.save(d/'initial.json',dict(process_identity=dict(pid=1),cgroup='/sys/fs/cgroup/system.slice/docker-owned.scope',
                    initial_limits={},container_server_sha256='sha'))
                s.c.save(d/'container.json',dict(inspect=dict(Id='owned',HostConfig={},Image='image')))
            ops=['selftest','fixtures']
            for _ in specs: ops+=['condition','attach','enable','disable','detach']
            ops+=['finish']; current=copy.deepcopy(original)
            def set_bounds(value): current.clear(); current.update(copy.deepcopy(value))
            def restore(value):
                set_bounds(value)
                return dict(restored=True,errors=[],observed=copy.deepcopy(value))
            class FakeCounter:
                def __init__(self,d,g,e): self.directory=d; self.state='disabled'
                def control(self,op): self.state='enabled' if op=='enable' else 'disabled'; return {}
                def close(self):
                    if cleanup_failure: raise RuntimeError('perf cleanup failure')
            with patch.dict(helper.os.environ,{'SUDO_UID':'1000','SUDO_GID':'1000'}), \
                 patch.object(helper.os,'geteuid',return_value=0),patch.object(helper.os,'sched_setaffinity'), \
                 patch.object(helper.signal,'signal'),patch.object(helper.screen,'verify',return_value=manifest), \
                 patch.object(helper.c,'same_process',return_value=True),patch.object(helper.os,'chown'), \
                 patch.object(helper.controls,'snapshot',side_effect=lambda:copy.deepcopy(current)), \
                 patch.object(helper.controls,'set_bounds',side_effect=set_bounds), \
                 patch.object(helper.controls,'restore',side_effect=restore) as recovery, \
                 patch.object(helper.select,'select',return_value=([1],[],[])), \
                 patch.object(helper.hw,'line',side_effect=['{"op":"'+op+'"}' for op in ops]), \
                 patch.object(helper.hw,'fixture',side_effect=lambda d,m,e:d.mkdir()), \
                 patch.object(helper.screen.pc,'validate_fixtures',return_value=dict(passed=True)), \
                 patch.object(helper.c,'validate_resources'), \
                 patch.object(helper.bridge,'cgroup',return_value=Path('/sys/fs/cgroup/system.slice/docker-owned.scope')), \
                 patch.object(helper.hw,'Counter',FakeCounter),patch('builtins.print'):
                if cleanup_failure:
                    with self.assertRaises(RuntimeError): helper.helper(session)
                else: helper.helper(session)
                self.assertEqual(current,original)
                self.assertTrue(s.c.read(session/'speed_control/restoration.json')['restored'])
                self.assertGreaterEqual(recovery.call_count,2)

    def test_helper_restores_normal_completion_and_early_stop(self):
        self.helper_case(); self.helper_case(stop_after_first=True)

    def test_perf_cleanup_failure_still_restores_controls(self):
        self.helper_case(cleanup_failure=True)

    def test_speed_samples_must_cover_native_work_without_gaps(self):
        native=dict(start_monotonic_ns=2_000_000_000,stop_monotonic_ns=5_000_000_000)
        good=[dict(monotonic_ns=i*1_000_000_000) for i in range(1,7)]
        s.verify_speed_coverage(good,native)
        for rows in [[],good[2:],good[:-2],[dict(monotonic_ns=1_000_000_000),dict(monotonic_ns=6_000_000_000)]]:
            with self.assertRaises(ValueError): s.verify_speed_coverage(rows,native)

    def test_aligned_counter_metric_and_boundary_rejection(self):
        native=dict(start_monotonic_ns=20,stop_monotonic_ns=80,cpu_start_ns=0,cpu_stop_ns=1000000000,jobs=100)
        bounds={k:dict(lower=v,upper=v,midpoint=v) for k,v in [('usage_usec',1000000),('user_usec',900000)]}
        counts=dict(instructions=10000,cycles=20000,cycles_per_instruction=2)
        receipt=dict(cgroup='/sys/fs/cgroup/owned',controls=[{},dict(after_ns=10),dict(before_ns=90)])
        def read(p): return {'pilot_config.json':dict(counters=True),'perf_receipt.json':receipt,
                             'initial.json':dict(cgroup='/sys/fs/cgroup/owned')}[p.name]
        with patch.object(s.pc,'validate_counter',return_value=(counts,bounds)),patch.object(s.c,'read',side_effect=read):
            r=s.counter_metrics(Path('/tmp/test'),native)
            self.assertAlmostEqual(r['metrics']['cycles_per_user_cpu_sec'],20000/.9)
            receipt['controls'][1]['after_ns']=21
            with self.assertRaises(ValueError): s.counter_metrics(Path('/tmp/test'),native)

if __name__=='__main__': unittest.main()
