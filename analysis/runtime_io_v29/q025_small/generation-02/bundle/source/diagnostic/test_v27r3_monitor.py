"""Actual-process cadence, endpoint validation and bounded failure regression."""
from contextlib import ExitStack
import signal
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import v27r3_common as c
import v27r3_monitor_control as control
import v27r3_study as runner


def fixture(directory):
    records=[dict(chatgpt_present=False, process_cpu_deltas=[], power_settings={},
                  record_before_ns=1_000_000_000+i*1_000_000_000,
                  record_after_ns=1_030_000_000+i*1_000_000_000) for i in range(80)]
    def status(n):
        return dict(pid=123,count=n,first_before_ns=records[0]['record_before_ns'],
            first_after_ns=records[0]['record_after_ns'],last_before_ns=records[n-1]['record_before_ns'],
            last_after_ns=records[n-1]['record_after_ns'])
    c.save(directory/'monitor_process.json',dict(pid=123))
    c.save(directory/'monitor_readiness.json',dict(wait_started_ns=0,received_ns=1_040_000_000,
        minimum_records=1,required_after_ns=0,bound_sec=5,status=status(1)))
    c.save(directory/'monitor_completion.json',dict(wait_started_ns=79_000_000_000,received_ns=80_040_000_000,
        minimum_records=80,required_after_ns=79_000_000_000,bound_sec=30,status=status(80)))
    return records,dict(power_settings={}),dict(startup=dict(before_ns=2_000_000_000),
                                               final=dict(after_ns=79_000_000_000))


class MonitorTests(unittest.TestCase):
    def test_real_child_progress_and_shutdown_saved_record_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            argv=[sys.executable,'-B',str(c.ROOT/'diagnostic/v27r3_monitor_fixture.py'),'.005','.003',
                  '--output',str(directory/'monitor.json'),'--progress',str(directory/'monitor_progress.json')]
            monitor=control.HostMonitor(directory,lambda:None)
            try:
                monitor.start('/unused-software-fixture',argv)
                start=time.monotonic_ns();end=time.monotonic_ns()
                monitor.finish(end)
            finally:monitor.stop()
            records=c.read(directory/'monitor.json')
            control.validate(directory,records,dict(power_settings={}),
                             dict(startup=dict(before_ns=start),final=dict(after_ns=end)))
            self.assertGreaterEqual(len(records),80)
            self.assertFalse(any(x['process_cpu_deltas'] for x in records))

    def test_count_threshold_unchanged_and_79_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);rows,env,obs=fixture(d)
            self.assertEqual(c.design()['host_monitor_min_records'],80)
            control.validate(d,rows,env,obs)
            with self.assertRaisesRegex(ValueError,'79 records; required 80'):control.validate(d,rows[:79],env,obs)

    def test_quiet_and_power_failures_have_separate_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);rows,env,obs=fixture(d)
            rows[40]['chatgpt_present']=True
            with self.assertRaisesRegex(ValueError,'quiet failure'):control.validate(d,rows,env,obs)
            rows[40]['chatgpt_present']=False
            rows[40]['process_cpu_deltas']=[dict(comm='Codex')]
            with self.assertRaisesRegex(ValueError,'quiet failure'):control.validate(d,rows,env,obs)
            rows[40]['process_cpu_deltas']=[];rows[40]['power_settings']={'changed':True}
            with self.assertRaisesRegex(ValueError,'power failure'):control.validate(d,rows,env,obs)

    def test_count_cannot_replace_endpoint_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);rows,env,obs=fixture(d)
            obs['final']['after_ns']=81_000_000_000
            with self.assertRaisesRegex(ValueError,'endpoint coverage'):control.validate(d,rows,env,obs)
            obs['final']['after_ns']=79_000_000_000;obs['startup']['before_ns']=1_000_000_000
            with self.assertRaisesRegex(ValueError,'endpoint coverage'):control.validate(d,rows,env,obs)

    def test_receipts_cannot_invent_records_or_change_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);rows,env,obs=fixture(d)
            receipt=c.read(d/'monitor_completion.json');receipt['status']['count']=81
            c.save(d/'monitor_completion.json',receipt)
            with self.assertRaisesRegex(ValueError,'receipt differs'):control.validate(d,rows,env,obs)
            fixture(d);receipt=c.read(d/'monitor_completion.json');receipt['status']['pid']=124
            c.save(d/'monitor_completion.json',receipt)
            with self.assertRaisesRegex(ValueError,'receipt differs'):control.validate(d,rows,env,obs)
            fixture(d);receipt=c.read(d/'monitor_completion.json');receipt['status']['last_after_ns']+=1
            c.save(d/'monitor_completion.json',receipt)
            with self.assertRaisesRegex(ValueError,'does not match'):control.validate(d,rows,env,obs)

    def test_record_clock_order_and_bounded_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);rows,env,obs=fixture(d);rows[40]['record_before_ns']=1
            with self.assertRaisesRegex(ValueError,'order/clock'):control.validate(d,rows,env,obs)
            rows,env,obs=fixture(d);receipt=c.read(d/'monitor_completion.json')
            receipt['received_ns']+=31_000_000_000;c.save(d/'monitor_completion.json',receipt)
            with self.assertRaisesRegex(ValueError,'receipt differs'):control.validate(d,rows,env,obs)

    def test_missing_progress_timeout_and_early_exit_are_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor=control.HostMonitor(Path(tmp),lambda:None)
            monitor.process=types.SimpleNamespace(pid=123,poll=lambda:None)
            with self.assertRaisesRegex(TimeoutError,'0 records; required 80'):monitor.wait(80,1,0,'receipt.json')
            monitor.process=types.SimpleNamespace(pid=123,poll=lambda:1)
            with self.assertRaisesRegex(ValueError,'exited before'):monitor.wait(80,1,30,'receipt.json')

    def test_stale_count_and_wrong_process_cannot_complete_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp);rows,env,obs=fixture(d);receipt=c.read(d/'monitor_completion.json')
            status=receipt['status'];status['count']=79;c.save(d/'monitor_progress.json',status)
            monitor=control.HostMonitor(d,lambda:None)
            monitor.process=types.SimpleNamespace(pid=123,poll=lambda:None)
            with self.assertRaisesRegex(TimeoutError,'79 records; required 80'):monitor.wait(80,1,0,'receipt.json')
            status['count']=80;status['pid']=456;c.save(d/'monitor_progress.json',status)
            with self.assertRaisesRegex(ValueError,'identity/count'):monitor.wait(80,1,30,'receipt.json')

    def test_production_lifecycle_stops_counter_before_extended_monitor_wait(self):
        events=[]
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);directory=session/'trial'
            c.save(session/'environment.json',dict(power_settings={},baseline_c={}))
            cfg=c.matrix()[0]
            class Service:
                group=Path('/sys/fs/cgroup/software-fixture')
                base='http://software-fixture'
                def __init__(self,*args):pass
                def create(self):events.append('create')
                def release(self):events.append('release')
                def guard(self):pass
                def observe(self):return dict(before_ns=time.monotonic_ns(),after_ns=time.monotonic_ns())
                def close(self,*args):events.append('close')
            class Monitor:
                def __init__(self,*args):pass
                def start(self,*args):events.append('monitor_ready')
                def finish(self,*args):events.append('monitor_finish')
                def stop(self):events.append('monitor_stop')
            counter=types.SimpleNamespace(pid=123,returncode=0,stdout=types.SimpleNamespace(fileno=lambda:0,close=lambda:None))
            def load(d,s,seconds,name,*args):events.append(name);c.save(d/(name+'.json'),{})
            def decode(raw,out,save):save(out,dict(samples=[{}]));events.append('counter_decoded')
            contexts=[patch.object(runner,'Service',Service),patch.object(runner,'HostMonitor',Monitor),
                 patch.object(runner,'require_quiet_host'),patch.object(runner,'update'),
                 patch.object(runner,'bounded_settle'),patch.object(c,'capacity'),
                 patch.object(runner,'power_settings',return_value={}),patch.object(runner,'load',load),
                 patch.object(runner,'drain',return_value={}),patch.object(runner,'reset',return_value={}),
                 patch.object(runner.bridge,'anchors',return_value=[]),patch.object(c,'validate_client'),
                 patch.object(c,'technical_client'),patch.object(c,'process_identity',return_value=dict(pid=123)),
                 patch.object(runner.subprocess,'Popen',return_value=counter),
                 patch.object(runner.select,'select',return_value=([counter.stdout],[],[])),
                 patch.object(runner.os,'read',return_value=b'READY\n'),
                 patch.object(runner.fixtures,'stop',side_effect=lambda *args:events.append('counter_stopped')),
                 patch.object(runner.native,'decode_file',side_effect=decode),
                 patch.object(runner.analysis,'replay',return_value={}),
                 patch.object(runner.verify,'counter_input'),patch.object(runner.model,'trial',return_value={})]
            with ExitStack() as stack:
                for context in contexts:stack.enter_context(context)
                runner.collect(session,directory,cfg,'run')
            self.assertLess(events.index('monitor_ready'),events.index('release'))
            self.assertLess(events.index('counter_stopped'),events.index('monitor_finish'))
            self.assertLess(events.index('counter_decoded'),events.index('monitor_finish'))
            self.assertLess(events.index('monitor_finish'),events.index('close'))
            self.assertTrue(c.read(directory/'complete.json')['valid'])


if __name__=='__main__':unittest.main()
