import math
from pathlib import Path
import tempfile
import unittest

import runtime_gc_probe as probe


def rows(period_default=1.05, period_off=1.00, gc_ratio=.96):
    result=[]
    for spec in probe.matrix():
        costs={'A':3600, 'B':3600*gc_ratio, 'C':3600*period_default, 'D':3600*gc_ratio*period_off}
        result.append(dict(spec,cpu_usec_per_completed_work=costs[spec['arm']],
            busy_capacity=140, busy_cpu_cores=.5,timely_500_fraction=.8,failure_fraction=0))
    return result


class RuntimeGCProbeTests(unittest.TestCase):
    def test_only_gogc_added_to_performance_argv(self):
        stock=['docker','create','--name','x','-e','GOMAXPROCS=1','-p','127.0.0.1::8080','image','--server']
        spec=probe.matrix()[1]
        actual=probe.runtime_argv(stock,spec)
        self.assertEqual(actual,stock[:6]+['-e','GOGC=off']+stock[6:])
        self.assertNotIn('GODEBUG=gctrace=1',actual)
        self.assertNotIn('GOGC=off',stock)

    def test_balanced_matrix_and_legacy_workload(self):
        matrix=probe.matrix()
        self.assertEqual(len(matrix),16)
        for arm in probe.FACTORS:
            self.assertEqual(sorted((s['order']-1)%4 for s in matrix if s['arm']==arm),[0,1,2,3])
        for spec in matrix:
            config=probe.legacy_config(spec)
            self.assertFalse(config['worker_yield'])
            self.assertEqual(config['period_us'],1000*spec['period_ms'])
            self.assertEqual(config['quota_us']/config['period_us'],.5)
            self.assertEqual(config['workers'],1)

    def test_general_gc_cpu_saving_is_not_period_explanation(self):
        result=probe.compare(rows(period_default=1.05,period_off=1.05,gc_ratio=.8))
        self.assertEqual(result['decision'],'no_large_gc_period_interaction_in_tested_conditions')
        self.assertAlmostEqual(result['cpu_interaction']['mean'],0)
        self.assertFalse(result['historical_cause_established'])

    def test_period_interaction_detected_in_either_direction(self):
        for default,off in [(1.05,1),(1,1.05)]:
            result=probe.compare(rows(default,off))
            self.assertEqual(result['decision'],'gc_period_interaction_detected')
            self.assertAlmostEqual(result['cpu_interaction']['mean'],off/default-1)

    def test_wide_interval_is_inconclusive(self):
        data=rows(1,1)
        for r in data:
            if r['arm']=='D': r['cpu_usec_per_completed_work']*=1.1 if r['block']%2 else .9
        self.assertEqual(probe.compare(data)['decision'],'gc_period_interaction_inconclusive')

    def test_complete_unique_blocks_required(self):
        data=rows()
        with self.assertRaises(ValueError): probe.compare(data[:-1])
        data[-1]=data[0]
        with self.assertRaises(ValueError): probe.compare(data)

    def test_positive_finite_costs_required(self):
        for cost in (0,-1,float('nan')):
            data=rows(); data[0]['cpu_usec_per_completed_work']=cost
            with self.assertRaises(ValueError): probe.compare(data)

    def test_cannot_escape_generation_parent(self):
        with self.assertRaises(ValueError): probe.owned_directory('/tmp/unrelated')

    def test_extra_runtime_environment_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); spec=probe.matrix()[0]
            env=['GOMAXPROCS=1','WORKERS=1','QUEUE_SIZE=128','INSTRUMENT=1','WORKER_YIELD=0',
                'GOGC=100','PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
            probe.c.save(path/'container.json',{'inspect':{'Config':{'Env':env}}})
            probe.validate_runtime_environment(path,spec)
            probe.c.save(path/'container.json',{'inspect':{'Config':{'Env':env+['GOMEMLIMIT=32MiB']}}})
            with self.assertRaises(ValueError): probe.validate_runtime_environment(path,spec)


if __name__=='__main__': unittest.main()
