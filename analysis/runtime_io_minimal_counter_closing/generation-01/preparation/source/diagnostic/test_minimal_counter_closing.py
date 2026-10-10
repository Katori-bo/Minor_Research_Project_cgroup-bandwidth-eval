import copy
import unittest
from unittest.mock import patch
import minimal_counter_closing as s


def rows():
    result=[]
    for spec in s.matrix():
        short=spec['period_ms']==20
        cpu=3600 if short else 3200
        result.append(dict(spec,cpu_usec_per_completed_work=cpu,capacity=500000/cpu,
            cpu_cores=.5,instructions_per_job=1000,cycles_per_instruction=2,
            cycles_per_user_cpu_sec=2e9*(3200/cpu)))
    return result


class Closing(unittest.TestCase):
    def test_balanced_sequence(self):
        self.assertEqual([r['arm'] for r in s.matrix()],list('ABCDDCBA'))
        self.assertEqual([r['order'] for r in s.matrix()],list(range(1,9)))
        self.assertEqual(len({r['trial'] for r in s.matrix()}),8)

    def test_execution_rate_hint(self):
        r=s.compare(rows())
        self.assertTrue(r['observer_qualified'])
        self.assertIn('similar_user_instruction_count_with_changed_execution_cost',r['execution_hints'])
        self.assertIn('lower_effective_user_cycles_per_cpu_second',r['execution_hints'])
        self.assertFalse(r['historical_reversal_cause_established'])

    def test_counter_effect_rejects_interpretation(self):
        a=rows()
        for r in a:
            if r['counters']: r['cpu_usec_per_completed_work']*=1.015
        result=s.compare(a)
        self.assertFalse(result['observer_qualified'])
        self.assertEqual(result['execution_hints'],[])
        self.assertEqual(result['decision'],'close_unresolved_counter_observer_not_qualified')

    def test_no_period_effect_closes(self):
        a=rows()
        for r in a: r.update(cpu_usec_per_completed_work=3200,capacity=156.25)
        self.assertEqual(s.compare(a)['decision'],'close_unresolved_period_effect_not_consistent')

    def test_one_block_effect_is_insufficient(self):
        a=rows()
        for r in a:
            if r['block']==2: r.update(cpu_usec_per_completed_work=3200,capacity=156.25)
        self.assertFalse(s.compare(a)['reproduced_without_counters'])

    def test_more_work_hint(self):
        a=rows()
        for r in a:
            if r['period_ms']==20: r['instructions_per_job']=1125
        self.assertIn('more_user_instructions_per_job',s.compare(a)['execution_hints'])

    def test_missing_or_duplicate_trial_rejected(self):
        with self.assertRaises(ValueError): s.compare(rows()[:-1])
        a=rows(); a[-1]=copy.deepcopy(a[0])
        with self.assertRaises(ValueError): s.compare(a)

    def test_short_native_protocol(self):
        self.assertEqual(s.durations(s.matrix()[0])['MINIMAL_MEASURE_MS'],'30000')
        self.assertEqual(s.durations(s.matrix()[0],True)['MINIMAL_MEASURE_MS'],'2000')

    def test_nonfinite_or_zero_measurements_rejected(self):
        for value in (0,float('nan'),float('inf')):
            a=rows(); a[0]['cpu_usec_per_completed_work']=value
            with self.assertRaises(ValueError): s.compare(a)

    def counter_case(self):
        native=dict(start_monotonic_ns=20,stop_monotonic_ns=80,cpu_start_ns=0,
                    cpu_stop_ns=1000000000,jobs=100)
        bounds={k:dict(lower=v,upper=v,midpoint=v) for k,v in
                [('usage_usec',1000000),('user_usec',900000),('system_usec',100000)]}
        counts=dict(instructions=10000,cycles=20000,cycles_per_instruction=2)
        receipt=dict(cgroup='/sys/fs/cgroup/owned',controls=[{},dict(after_ns=10),dict(before_ns=90)])
        def read(p):
            return {'closing_config.json':dict(counters=True),'perf_receipt.json':receipt,
                    'initial.json':dict(cgroup='/sys/fs/cgroup/owned')}[p.name]
        return native,bounds,counts,receipt,read

    def test_cycle_rate_uses_aligned_user_cpu(self):
        from pathlib import Path
        native,bounds,counts,receipt,read=self.counter_case()
        with patch.object(s.pc,'validate_counter',return_value=(counts,bounds)),patch.object(s.c,'read',side_effect=read):
            result=s.counter_metrics(Path('/tmp/test'),native)
        self.assertAlmostEqual(result['metrics']['cycles_per_user_cpu_sec'],20000/.9)

    def test_native_work_must_be_inside_counter_window(self):
        from pathlib import Path
        native,bounds,counts,receipt,read=self.counter_case(); receipt['controls'][1]['after_ns']=21
        with patch.object(s.pc,'validate_counter',return_value=(counts,bounds)),patch.object(s.c,'read',side_effect=read):
            with self.assertRaises(ValueError): s.counter_metrics(Path('/tmp/test'),native)

    def test_excess_boundary_cpu_is_rejected(self):
        from pathlib import Path
        native,bounds,counts,receipt,read=self.counter_case(); bounds['usage_usec']['upper']=1006000
        with patch.object(s.pc,'validate_counter',return_value=(counts,bounds)),patch.object(s.c,'read',side_effect=read):
            with self.assertRaises(ValueError): s.counter_metrics(Path('/tmp/test'),native)


if __name__=='__main__': unittest.main()
