"""Meaningful failure cases for timing joins, paired gates and ownership cleanup."""
import copy
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import imgproxy_qualify as q


def fixtures():
    record=dict(ID='test-0',ExecuteStartNs=1,QueueStartNs=2,QueueDoneNs=12,
        ProcessStartNs=15,ProcessDoneNs=35,ResponseStartNs=36,ResponseDoneNs=40,
        ReleaseBeforeNs=41,ReleaseAfterNs=42,ExecuteDoneNs=43,Success=True)
    server=dict(Schema='imgproxy-qualification-v1',Overflow=0,GOMAXPROCS=1,
        Capacity=1024,GoVersion='go1.27.1',Records=[record])
    row=dict(ID='test-0',EchoID='test-0',ScheduledNs=0,DispatchNs=5,HeadersNs=46,
        BodyDoneNs=50,Status=200,Error='',BodySHA256='good',BodyBytes=100,
        ContentType='image/jpeg',QueueNs=10,ProcessNs=20,TimingError='')
    client=dict(Schema='imgproxy-client-v1',Count=1,IntervalNs=200000000,Rows=[row])
    return client,server


class TimingTests(unittest.TestCase):
    def test_complete_body_and_raw_header_join(self):
        client,server=fixtures()
        self.assertEqual(q.join_records(client,server)['total_process_ns'],20)
        self.assertEqual(q.validate_client(client,'test',1,'good')['median_e2e_ns'],50)

    def test_reject_duplicate_and_overflow(self):
        for bad in ('duplicate','overflow'):
            client,server=fixtures()
            if bad=='duplicate': server['Records'].append(copy.deepcopy(server['Records'][0]))
            else: server['Overflow']=1
            with self.subTest(bad=bad),self.assertRaises(ValueError): q.join_records(client,server)

    def test_reject_negative_residual_and_reversed_stage(self):
        client,server=fixtures(); client['Rows'][0]['BodyDoneNs']=34
        with self.assertRaises(ValueError): q.join_records(client,server)
        client,server=fixtures(); server['Records'][0]['ProcessDoneNs']=14
        with self.assertRaises(ValueError): q.join_records(client,server)

    def test_reject_header_disagreement(self):
        client,server=fixtures(); client['Rows'][0]['QueueNs']=9
        with self.assertRaises(ValueError): q.join_records(client,server)

    def test_reject_wrong_output_id_and_offer_time(self):
        for key,bad in [('BodySHA256','bad'),('EchoID','wrong'),('ScheduledNs',1),('Error','timeout')]:
            client,_=fixtures(); client['Rows'][0][key]=bad
            with self.subTest(key=key),self.assertRaises(ValueError): q.validate_client(client,'test',1,'good')


class PairedGateTests(unittest.TestCase):
    def rows(self,changes):
        return [dict(pair=i,arm=arm,cpu_per_offer_usec=100*(1+change),median_e2e_ns=1000*(1+change))
            for i,delta in enumerate(changes,1) for arm,change in [('stock',0),('observed',delta)]]

    def test_stable_small_overhead_passes(self):
        effects=q.effects_from(self.rows([.01]*6))
        self.assertTrue(all(r['upper_le_5pct'] for r in effects.values()))

    def test_small_mean_with_large_uncertainty_fails(self):
        effects=q.effects_from(self.rows([-.10,.10,-.10,.10,-.10,.10]))
        self.assertFalse(effects['cpu_per_offer_usec']['upper_le_5pct'])

    def test_missing_pair_or_zero_endpoint_rejected(self):
        rows=self.rows([.01]*6)
        with self.assertRaises(ValueError): q.effects_from(rows[:-1])
        rows[0]['cpu_per_offer_usec']=0
        with self.assertRaises(ValueError): q.effects_from(rows)


class OwnershipTests(unittest.TestCase):
    def test_wrong_nonce_never_removes(self):
        response=subprocess.CompletedProcess([],0,'[{"Config":{"Labels":{"'+q.LABEL+'":"other"}}}]','')
        with patch.object(q.subprocess,'run',return_value=response),patch.object(q,'cmd') as mutate:
            with self.assertRaises(ValueError): q.remove_owned('name','ours')
            mutate.assert_not_called()

    def test_cleanup_uses_immutable_id(self):
        with patch.object(q,'inspect_owned',side_effect=[{'Id':'immutable'},None]),patch.object(q,'cmd') as mutate:
            q.remove_owned('reusable-name','ours')
            mutate.assert_called_once_with(['docker','rm','-f','immutable'])

    def test_owner_death_stops_owned_client_and_removes_service(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            q.save(p/'ownership.json',dict(owner={'pid':123,'start_ticks':1},container='owned',nonce='nonce',deadline_monotonic=1e30))
            q.save(p/'client-ownership.json',dict(pid=456,start_ticks=2))
            with patch.object(q,'same_owner',side_effect=[False,True,False]),patch.object(q,'remove_owned') as remove,patch.object(q.os,'killpg') as stop:
                q.watchdog(p)
                remove.assert_called_once_with('owned','nonce')
                stop.assert_called_once_with(456,q.signal.SIGKILL)
            self.assertEqual(q.read(p/'watchdog-cleanup.json'),dict(invalidated=True,errors=[]))


if __name__=='__main__': unittest.main()
