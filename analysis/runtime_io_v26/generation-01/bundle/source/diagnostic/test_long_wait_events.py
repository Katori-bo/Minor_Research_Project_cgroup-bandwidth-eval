import unittest

import inspect_long_wait_events as inspection


def event(g,old,new,stamp,reason='',p=0,stack=''):
    return dict(target_g=g,old=old,new=new,time_ns=stamp,reason=reason,
                p=p,m=1,Stack=stack,line=stamp)


class LongWaitEventTests(unittest.TestCase):
    def test_raw_actor_and_target_are_distinct_and_stacks_preserved(self):
        row = inspection.decode([
            'M=7 P=-1 G=-1 StateTransition Time=100 GoID=42 Waiting->Runnable Reason=""\n',
            'Stack=\n', '\truntime.injectglist @ 0x123\n'],10)
        self.assertEqual((row['m'],row['p'],row['actor_g'],row['target_g']),(7,-1,-1,42))
        self.assertIn('runtime.injectglist',row['Stack'])
        self.assertEqual(row['line'],10)

    def test_same_state_snapshots_do_not_reset_wakeup_and_late_runs_count(self):
        rows=[event(42,'Running','Waiting',10,'network'),
              event(42,'Waiting','Waiting',20),
              event(42,'Waiting','Runnable',30,p=-1),
              event(42,'Runnable','Runnable',40),
              event(42,'Runnable','Running',100)]
        matched,unresolved = inspection.wakeup_latencies(rows,25,60,set(),{42},set())
        self.assertEqual(matched[0]['category'],'no_P_network_to_http')
        self.assertEqual(matched[0]['latency_ns'],70)
        self.assertFalse(unresolved)

    def test_half_open_wake_cohort_and_preemption_are_separate(self):
        rows=[event(42,'Running','Waiting',5,'network'),
              event(42,'Waiting','Runnable',10,p=-1),
              event(42,'Runnable','Running',15),
              event(42,'Running','Runnable',20,'preempted'),
              event(42,'Runnable','Running',25),
              event(42,'Running','Waiting',30,'network'),
              event(42,'Waiting','Runnable',40,p=-1),
              event(42,'Runnable','Running',50)]
        matched,_ = inspection.wakeup_latencies(rows,10,40,set(),{42},set())
        self.assertEqual(len(matched),1)
        self.assertEqual(matched[0]['latency_ns'],5)

    def test_worker_identity_is_supplied_instead_of_hardcoded(self):
        row=event(900,'Waiting','Runnable',10,stack='runtime.selectnbsend\nmain.(*service).workHandler')
        self.assertEqual(inspection.classify_wakeup(row,'chan receive',{900},{0},set()),
                         'handler_admission_to_worker')
        row=event(0,'Waiting','Runnable',10,stack='runtime.chansend1\nmain.(*service).runJob')
        self.assertEqual(inspection.classify_wakeup(row,'select',{900},{0},set()),'worker_reply_to_http')

    def test_unresolved_wake_is_reported_not_treated_as_zero_latency(self):
        rows=[event(42,'Running','Waiting',5,'network'),event(42,'Waiting','Runnable',10,p=-1)]
        matched,unresolved=inspection.wakeup_latencies(rows,0,20,set(),{42},set())
        self.assertFalse(matched)
        self.assertEqual(unresolved[0]['target_g'],42)

    def test_maintenance_context_keeps_delayed_sync_and_missing_context(self):
        start=event(90,'Runnable','Running',100)
        start.update(kind='StateTransition',actor_g=-1,Stack='')
        preempt=event(7,'Running','Runnable',150,'preempted')
        preempt.update(kind='StateTransition',actor_g=7)
        sync=dict(kind='Sync',time_ns=100000150,actor_g=-1,Stack='')
        metric=dict(kind='Metric',time_ns=100000160,actor_g=90,
                    Stack='runtime.traceAdvance')
        rows=inspection.trace_maintenance_context([start,preempt,sync,metric],[preempt])
        self.assertEqual(rows[0]['sync_delta_us'],100000)
        self.assertEqual(rows[0]['advancer_start_to_preemption_us'],.05)
        missing=inspection.trace_maintenance_context([preempt],[preempt])[0]
        self.assertIsNone(missing['following_sync'])
        self.assertIsNone(missing['preceding_advancer_start'])


if __name__=='__main__':
    unittest.main()
