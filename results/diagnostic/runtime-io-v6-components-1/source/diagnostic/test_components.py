import collections
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run
import monitor_host
import component_analysis


class ComponentTests(unittest.TestCase):
    def test_balanced_modes_and_fixed_workload(self):
        rows = run.component_matrix()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({r['run_id'] for r in rows}), 16)
        for position in range(4):
            self.assertEqual({r['component_mode'] for r in rows[position::4]}, set(component_analysis.MODES))
        pairs = collections.Counter((rows[b+i]['component_mode'], rows[b+i+1]['component_mode'])
                                    for b in range(0,16,4) for i in range(3))
        self.assertEqual(len(pairs), 12)
        self.assertEqual(set(pairs.values()), {1})
        fixed = ('workers','gomaxprocs','period_us','quota_us','rate','burst_low','burst_high',
                 'iterations','duration_sec','warmup_sec','instrument','client_trace')
        self.assertEqual(len({tuple(r[k] for k in fixed) for r in rows}), 1)
        self.assertEqual({(r['runtime_trace'], r['custom_recording']) for r in rows},
                         {(False,False),(True,False),(False,True),(True,True)})

    def test_quiet_preflight_fails_closed(self):
        for code in (0, 2):
            with patch.object(run.sp, 'run') as call:
                call.return_value.returncode = code
                call.return_value.stdout = '123 ChatGPT'
                call.return_value.stderr = 'failure'
                with self.assertRaises(RuntimeError): run.require_quiet_host()
        with patch.object(run.sp, 'run') as call:
            call.return_value.returncode = 1
            run.require_quiet_host()

    def test_process_deltas_ignore_new_and_reused_pids(self):
        before = {(1,10):dict(cpu_ticks=100), (2,20):dict(cpu_ticks=100)}
        after = {(1,10):dict(pid=1,cpu_ticks=150), (2,21):dict(pid=2,cpu_ticks=300),
                 (3,30):dict(pid=3,cpu_ticks=80)}
        rows = monitor_host.process_deltas(before,after,2,100)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['cpu_pct_one_core'],25)

    def test_proc_stat_with_spaces_and_parentheses(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'42';p.mkdir()
            fields = ['0']*37
            fields[0],fields[11],fields[12],fields[19],fields[36] = 'R','120','30','1234','7'
            (p/'stat').write_text('42 (name (with) spaces) '+' '.join(fields))
            row = monitor_host.process_snapshot(tmp)[(42,1234)]
            self.assertEqual((row['comm'],row['cpu_ticks'],row['last_cpu']),('name (with) spaces',150,7))

    def test_component_session_cannot_unlock_full(self):
        with patch.object(run,'verify_session',return_value=dict(components=True,pilot=True)), \
             patch.object(run,'read',return_value=dict(passed=True)):
            with self.assertRaises(RuntimeError): run.require_pilot(Path('/tmp/component'))

    def test_reduced_validation_rejects_mode_mismatch(self):
        status = dict(complete=True,active=False,pending_responses=0,start_error='',stop_error='',
                      trace_write_error='',io_events_dropped=0,runtime_trace_overflow=False,
                      runtime_capture=True,custom_recording=True)
        with patch.object(run,'read',return_value=status):
            with self.assertRaises(ValueError):
                run.validate_reduced_trace(Path('/tmp'),dict(runtime_trace=False,custom_recording=True),{}, {})


if __name__ == '__main__': unittest.main()
