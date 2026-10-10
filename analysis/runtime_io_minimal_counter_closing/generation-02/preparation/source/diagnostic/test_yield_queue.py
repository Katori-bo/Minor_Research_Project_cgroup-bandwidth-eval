import unittest

import inspect_yield_queue as queue
import inspect_prehandler_ready as ready


class QueueReconstructionTests(unittest.TestCase):
    def test_clock_brackets_include_dispatch_lag_and_first_byte_is_dispatch_relative(self):
        requests = {
            0: dict(ScheduledOffsetNs=100, DispatchLagNs=20, FirstByteOffsetNs=40),
            1: dict(ScheduledOffsetNs=200, DispatchLagNs=30, FirstByteOffsetNs=50),
        }
        entries = {0: dict(start_ns=1130), 1: dict(start_ns=1260)}
        clock = queue.causal_clock_bounds(requests, entries)
        # [970,1010] intersect [980,1030]. Known actual offset 1000 is included.
        self.assertEqual((clock['offset_low_ns'],clock['offset_high_ns']), (980,1010))
        self.assertEqual(clock['lower_bound_request'],1)
        self.assertEqual(clock['upper_bound_request'],0)
        self.assertEqual(queue.delay_bounds(1130,100,clock),(20,50))

    def test_incompatible_clocks_refuse_instead_of_fitting(self):
        requests = {0:dict(ScheduledOffsetNs=0,DispatchLagNs=0,FirstByteOffsetNs=10),
                    1:dict(ScheduledOffsetNs=0,DispatchLagNs=0,FirstByteOffsetNs=10)}
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            queue.causal_clock_bounds(requests,{0:dict(start_ns=100),1:dict(start_ns=200)})

    def test_duplicate_zero_id_is_not_silently_lost(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):
            queue.unique([{'id':0},{'id':0}], 'id', 'job')
        self.assertIn(0,queue.unique([{'id':0}], 'id', 'job'))

    def test_queue_sweep_and_processing_are_separate_conserved_counts(self):
        jobs = {0:dict(admission_ns=1,worker_start_ns=2,completion_ns=6),
                1:dict(admission_ns=3,worker_start_ns=7,completion_ns=8)}
        times,q,active = queue.sweep(jobs)
        self.assertEqual(queue.value_at(times,q,4),1)
        self.assertEqual(queue.value_at(times,active,4),1)
        self.assertEqual(queue.value_at(times,q,7,before=True),1)
        self.assertEqual(queue.value_at(times,q,7),0)
        self.assertEqual((q[-1],active[-1]),(0,0))
        self.assertEqual(queue.extrema(times,q,3,7),(1,1))
        self.assertEqual(queue.extrema(times,q,3,8),(0,1))

    def test_handoff_estimate_above_channel_capacity_is_preserved(self):
        jobs = {i:dict(admission_ns=1,worker_start_ns=2,completion_ns=3) for i in range(129)}
        _,q,_ = queue.sweep(jobs)
        self.assertEqual(max(q),129)

    def test_half_open_bins_do_not_double_count_boundary_events(self):
        self.assertEqual(queue.count_between([0,10,10,20],0,10),1)
        self.assertEqual(queue.count_between([0,10,10,20],10,20),2)
        self.assertEqual(queue.percentile([1,2,3,4],50),2)

    def test_runnable_snapshots_merge_and_intervals_clip_at_both_ends(self):
        rows=[(0,'Waiting','network'),(10,'Runnable',''),(20,'Runnable',''),
              (30,'Running',''),(40,'Runnable',''),(60,'Running','')]
        self.assertEqual(ready.runnable_spans(rows,15,50),[(15,30),(40,50)])

    def test_empty_and_uncreated_intervals_are_not_runnable(self):
        rows=[(0,'NotExist',''),(20,'Runnable',''),(30,'Running','')]
        self.assertEqual(ready.runnable_spans(rows,0,10),[])
        self.assertEqual(ready.runnable_spans(rows,30,20),[])


if __name__=='__main__':
    unittest.main()
