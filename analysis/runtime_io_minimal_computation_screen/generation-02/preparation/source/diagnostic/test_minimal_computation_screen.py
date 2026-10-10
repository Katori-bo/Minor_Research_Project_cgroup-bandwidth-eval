import copy
import unittest
from pathlib import Path
import minimal_computation_screen as s
import leftover_observer_audit as a
import leftover_observer_review as review


class ScreenTests(unittest.TestCase):
    def rows(self,full=.005,mini=.005):
        return [dict(spec,cpu_usec_per_completed_work=3000*(1+(full if spec['kind']=='full' else mini))
                     if spec['period_ms']==20 else 3000,capacity=150,cpu_cores=.5,failure_fraction=0)
                for spec in s.matrix()]

    def test_stop_when_neither_signal(self):
        result=s.compare(self.rows())
        self.assertEqual(result['decision'],'bounded_screen_did_not_narrow_cause')
        self.assertFalse(result['automatic_followup_authorized'])
        self.assertFalse(result['historical_cause_established'])

    def test_compute_control_signal(self):
        self.assertEqual(s.compare(self.rows(.055,.04))['decision'],
                         'period_cost_signal_also_present_in_minimal_control')

    def test_service_only_signal(self):
        self.assertEqual(s.compare(self.rows(.055,.005))['decision'],
                         'full_service_period_signal_not_matched_by_minimal_control')

    def test_order_reversal_not_consistent(self):
        rows=self.rows(.055,.04)
        next(r for r in rows if r['trial']=='b4_B')['cpu_usec_per_completed_work']=2900
        self.assertFalse(s.compare(rows)['large_consistent_signals']['full'])

    def test_missing_duplicate_zero_rejected(self):
        for rows in [self.rows()[:-1], self.rows()[:-1]+[self.rows()[0]]]:
            with self.assertRaises(ValueError): s.compare(rows)
        rows=self.rows(); rows[0]['cpu_usec_per_completed_work']=0
        with self.assertRaises(ValueError): s.compare(rows)

    def test_exact_retained_computation(self):
        self.assertEqual(s.work_source((s.ROOT/'diagnostic/minimal_sha.go').read_text()),
                         s.work_source(s.SOURCE.read_text()))

    def test_native_cpu_scope_and_count_validation(self):
        rows=[dict(event='started',go_version='go1.26.1',gomaxprocs=1)]
        for event,start in [('warmup_done',1_000_000_000),('measurement_done',4_000_000_000)]:
            rows.append(dict(event=event,go_version='go1.26.1',gomaxprocs=1,jobs=100,digest='abc',
                iterations=44000,duration_ms=2000,start_monotonic_ns=start,stop_monotonic_ns=start+2_000_000_000,
                cpu_start_ns=1_000_000_000,cpu_stop_ns=2_000_000_000))
        obs={'measurement_start':dict(after_ns=3_999_000_000,cpu_stat=dict(usage_usec=1_000_000)),
             'measurement_stop':dict(before_ns=6_001_000_000,cpu_stat=dict(usage_usec=2_000_000))}
        result=s.minimal_summary(rows,obs,'abc')
        self.assertEqual(result['cpu_usec_per_completed_work'],10000)
        bad=copy.deepcopy(obs); bad['measurement_stop']['cpu_stat']['usage_usec']=2_100_000
        with self.assertRaises(ValueError): s.minimal_summary(rows,bad,'abc')
        bad=copy.deepcopy(rows); bad[-1]['digest']='wrong'
        with self.assertRaises(ValueError): s.minimal_summary(bad,obs,'abc')
        bad=copy.deepcopy(rows); bad[-1]['jobs']=0
        with self.assertRaises(ValueError): s.minimal_summary(bad,obs,'abc')


class AuditTests(unittest.TestCase):
    def clean(self):
        fields={k:dict(ok=True,text=v) for k,v in
                [('current_tracer','nop'),('tracing_on','1'),('events/enable','0'),
                 ('kprobe_events',''),('uprobe_events',''),('dynamic_events','')]}
        return dict(processes=dict(scan_complete=True,permission_denied_pids=[],
                observer_candidates=[],perf_fd_owners=[]),
            tracefs=dict(root_readable=True,instance_error=None,
                states=[dict(path='/sys/kernel/tracing',controls=fields,enabled_events=[],event_read_errors=[])]),
            bpf={k:dict(returncode=0,items=[]) for k in ('prog','link','map')})

    def test_nop_tracing_flag_is_not_active_observer(self):
        self.assertTrue(a.assess(self.clean())['clear_snapshot'])

    def test_protected_missing_is_not_clean(self):
        value=self.clean(); value['bpf']['prog']['returncode']=1
        self.assertFalse(a.assess(value)['clear_snapshot'])
        self.assertEqual(a.assess(value)['status'],'audit_incomplete')

    def test_events_and_attachments_require_review(self):
        value=self.clean(); value['tracefs']['states'][0]['enabled_events']=['sched/sched_switch']
        self.assertFalse(a.assess(value)['clear_snapshot'])
        value=self.clean(); value['bpf']['prog']['items']=[dict(id=1,type='cgroup_device')]
        self.assertFalse(a.assess(value)['clear_snapshot'])


class OwnershipReviewTests(unittest.TestCase):
    def data(self):
        value=AuditTests().clean()
        value['processes']['rows']=[dict(pid=1,comm='systemd',uid=0)]
        value['bpf']['prog']['items']=[dict(id=24,type='lsm',name='restrict_filesystems',
            pids=[dict(pid=1,comm='systemd')],map_ids=[10],orphaned=False)]
        value['bpf']['map']['items']=[dict(id=10,type='hash_of_maps',name='cgroup_hash',pids=[dict(pid=1,comm='systemd')])]
        value['bpf']['link']['items']=[dict(id=1,type='tracing',prog_type='lsm',attach_type='lsm_mac',
            prog_id=24,pids=[dict(pid=1,comm='systemd')])]
        return value

    def test_verified_systemd_policy_classified(self):
        self.assertTrue(review.classify(self.data())['performance_eligible'])

    def test_name_without_verified_owner_not_exempt(self):
        value=self.data(); value['bpf']['prog']['items'][0]['pids']=[]
        with self.assertRaises(ValueError): review.classify(value)

    def test_new_observer_or_unknown_map_not_exempt(self):
        value=self.data(); value['bpf']['prog']['items'].append(dict(id=100,type='kprobe',orphaned=False))
        with self.assertRaises(ValueError): review.classify(value)
        value=self.data(); value['bpf']['map']['items'].append(dict(id=200,type='ringbuf',name='events'))
        with self.assertRaises(ValueError): review.classify(value)

    def test_missing_inventory_not_exempt(self):
        value=self.data(); value['bpf']['map']['returncode']=1
        with self.assertRaises(ValueError): review.classify(value)


if __name__=='__main__': unittest.main()
