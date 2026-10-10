import copy
import json
import unittest
import kernel_bridge_analysis as analysis


def raw(rows):
    return 'BEGIN 1 50\n'+'\n'.join(' '.join(map(str,r)) for r in rows)+f'\nEND 1000 {len(rows)}\n'


def records():
    return [
        ['S',10,2,0,100,0,0,1], ['F',11,2,100,101], ['F',12,2,100,102],
        ['S',15,2,100,101,1,1,1], ['S',16,4,0,102,0,0,1],
        ['T',20,21,2,50,200,1,1], ['T',22,23,4,50,400,1,1],
        ['S',25,2,101,0,0,1,0], ['S',26,4,102,0,0,1,0],
        ['U',80,81,2,50,200,1,0], ['U',82,83,4,50,400,1,0],
        ['S',85,2,0,101,0,0,1], ['X',86,2,101], ['S',87,2,101,100,0,1,1],
        ['S',88,4,0,102,0,0,1], ['X',89,4,102], ['S',90,4,102,0,0,1,0],
        ['X',91,2,100], ['S',92,2,100,0,0,1,0]]


META=dict(pid=100,cgroup_id=50,capped=True,cpu_stat_delta=dict(nr_throttled=1))


class CoverageTests(unittest.TestCase):
    def test_two_cpu_states_remain_separate(self):
        result=analysis.coverage(raw(records()),'',META,[dict(before_ns=30,after_ns=40,tids=[100,101,102])])
        self.assertEqual(result['observed_cpus'],[2,4])
        self.assertEqual([v['cpu'] for v in result['quota_intervals']],[2,4])
        self.assertEqual(result['received_events'],19)
        self.assertFalse(result['service_request_attribution'])

    def test_unaccounted_snapshot_rejected(self):
        with self.assertRaisesRegex(ValueError,'/proc'):
            analysis.coverage(raw(records()),'',META,[dict(before_ns=30,after_ns=40,tids=[100,101,999])])

    def test_snapshot_racing_thread_exit_allows_bounds(self):
        analysis.coverage(raw(records()),'',META,[dict(before_ns=85,after_ns=90,tids=[100,101])])

    def test_missing_final_switch_rejected(self):
        with self.assertRaisesRegex(ValueError,'open'):
            analysis.coverage(raw(records()[:-1]),'',META,[])

    def test_unknown_fork_parent_rejected(self):
        rows=records();rows[1][3]=999
        with self.assertRaisesRegex(ValueError,'parent'):
            analysis.coverage(raw(rows),'',META,[])

    def test_cpu_escape_rejected(self):
        rows=records();rows[0][2]=3
        with self.assertRaisesRegex(ValueError,'CPUs'):
            analysis.coverage(raw(rows),'',META,[])

    def test_uncapped_quota_rejected(self):
        metadata=copy.deepcopy(META);metadata['capped']=False
        with self.assertRaisesRegex(ValueError,'uncapped'):
            analysis.coverage(raw(records()),'',metadata,[])

    def test_loss_diagnostics_rejected(self):
        with self.assertRaisesRegex(ValueError,'diagnostics'):
            analysis.coverage(raw(records()),'Lost 1 events',META,[])


class ClockTests(unittest.TestCase):
    def samples(self):
        return [dict(label=f'{phase}_{i}',before_ns=10000+i,after_ns=10010+i,
                     server_ns=1000+i,generation=0) for phase in ('start','stop') for i in range(3)]

    def mapping(self):
        return dict(server_minus_client_lower_ns=100,server_minus_client_upper_ns=110)

    def test_composed_bounds(self):
        result=analysis.clock_join(self.samples(),self.mapping(),0)
        self.assertEqual(result['kernel_minus_server_lower_ns'],9000)
        self.assertEqual(result['kernel_minus_server_upper_ns'],9010)
        self.assertEqual(result['kernel_minus_client_lower_ns'],9100)
        self.assertEqual(result['kernel_minus_client_upper_ns'],9120)

    def test_generation_reset_rejected(self):
        with self.assertRaisesRegex(ValueError,'generation'):
            analysis.clock_join(self.samples(),self.mapping(),1)

    def test_inconsistent_clock_mapping_rejected(self):
        samples=self.samples();samples[-1]['server_ns']+=100
        with self.assertRaisesRegex(ValueError,'disagree'):
            analysis.clock_join(samples,self.mapping(),0)

    def test_excessive_clock_error_rejected(self):
        samples=self.samples()
        for s in samples:s['after_ns']+=2_000_000
        with self.assertRaisesRegex(ValueError,'1 ms'):
            analysis.clock_join(samples,self.mapping(),0)


if __name__=='__main__':unittest.main()
