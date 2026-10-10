import unittest
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch
import imgproxy_throttle_probe as p


class AnchorAndOverlapTests(unittest.TestCase):
    def test_anchor_must_stay_inside_supervisor_bounds(self):
        p.validate_anchor({'MonotonicBeforeNs':10,'MonotonicAfterNs':11},9,12)
        with self.assertRaises(ValueError): p.validate_anchor({'MonotonicBeforeNs':8,'MonotonicAfterNs':11},9,12)
        with self.assertRaises(ValueError): p.validate_anchor({'MonotonicBeforeNs':12,'MonotonicAfterNs':11},9,13)

    def test_update_interval_is_not_asserted_to_be_a_throttle_interval(self):
        samples=[dict(before_ns=100,after_ns=101,cpu_stat={'nr_throttled':0,'throttled_usec':0}),
                 dict(before_ns=110,after_ns=111,cpu_stat={'nr_throttled':1,'throttled_usec':50})]
        client=dict(MonotonicBeforeNs=0,MonotonicAfterNs=1,
                    Rows=[dict(ID='inside',DispatchNs=80,BodyDoneNs=120),
                          dict(ID='partial',DispatchNs=105,BodyDoneNs=130),
                          dict(ID='outside',DispatchNs=200,BodyDoneNs=230)])
        changes=p.counter_changes(samples,{'measurement':client})
        overlap=changes[0]['request_window_overlaps']
        self.assertEqual(overlap,[{'phase':'measurement','id':'inside','relation':'update_interval_inside_request'},
                                 {'phase':'measurement','id':'partial','relation':'possible_overlap'}])
        self.assertEqual(changes[0]['update_interval_ns'],[100,111])

    def test_counter_regression_rejected(self):
        samples=[dict(before_ns=0,after_ns=1,cpu_stat={'nr_throttled':1,'throttled_usec':0}),
                 dict(before_ns=2,after_ns=3,cpu_stat={'nr_throttled':0,'throttled_usec':0})]
        with self.assertRaises(ValueError): p.counter_changes(samples,{})

    def test_sampler_failure_is_retained(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(p.q.fixtures,'stat',side_effect=OSError('missing counter')):
            sampler=p.Sampler(Path('/unused')); sampler.start(); sampler.thread.join(timeout=1)
            target=Path(directory)/'timeline.json'
            with self.assertRaises(ValueError): sampler.stop(target)
            self.assertEqual(p.q.read(target)['error'],'missing counter')

    def test_raw_export_precedes_record_count_classification(self):
        service=Mock()
        with tempfile.TemporaryDirectory() as directory,patch.object(p.q,'fetch',return_value=(b'{"Records":[{}],"Overflow":1}',{})):
            target=Path(directory)/'events.json'
            raw=p.export_preserved(service,target,1)
            self.assertEqual(p.q.read(target),raw)
            self.assertEqual(raw['Overflow'],1)


if __name__=='__main__': unittest.main()
