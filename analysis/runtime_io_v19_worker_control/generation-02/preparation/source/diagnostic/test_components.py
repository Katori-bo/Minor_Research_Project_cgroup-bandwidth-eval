import collections
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run
import monitor_host
import component_analysis
import inspect_trace_writer


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

    def test_quiet_message_is_compact_and_identifies_codex(self):
        with patch.object(run.sp, 'run') as call:
            call.return_value.returncode = 0
            call.return_value.stdout = '123\n456\n'
            call.return_value.stderr = ''
            with self.assertRaisesRegex(RuntimeError, r'ChatGPT/Codex.*2 matching processes') as caught:
                run.require_quiet_host()
            self.assertNotIn('123', str(caught.exception))
            call.assert_called_once_with(['pgrep', '-x', 'ChatGPT'], capture_output=True, text=True)

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

    def test_trace_storage_requires_full_persistence(self):
        config = dict(runtime_trace=True, trace_storage='memory')
        status = dict(runtime_trace_storage='memory', runtime_trace_bytes=100,
                      runtime_trace_persisted_bytes=100, runtime_trace_persistence_complete=True)
        run.validate_trace_storage(status, config)
        for key, value in [('runtime_trace_storage', 'file'),
                           ('runtime_trace_persisted_bytes', 99),
                           ('runtime_trace_persistence_complete', False)]:
            bad = dict(status, **{key: value})
            with self.assertRaises(ValueError): run.validate_trace_storage(bad, config)
        with self.assertRaises(ValueError): run.validate_trace_storage({}, config)
        # Historical evidence is accepted only without the new frozen setting.
        run.validate_trace_storage({}, dict(runtime_trace=True))

    def test_old_session_only_allows_read_only_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            plan = [{k: v for k,v in c.items() if k not in ('trace_storage', 'worker_yield')} for c in run.component_matrix()]
            run.put(directory/'matrix.json', plan)
            run.put(directory/'metadata.json', dict(schema=7, components=True, pilot=True,
                matrix_sha256=run.sha(directory/'matrix.json'),
                source_calibration_sha256=run.sha(run.ORIGINAL/'calibration.json')))
            run.verify_session(directory, check_current=False)
            with self.assertRaises(RuntimeError): run.verify_session(directory)

    def test_writer_review_counts_only_writer_syscalls_and_retains_unfinished(self):
        lines = [
            'M=1 P=0 G=7 StateTransition Time=100 GoID=7 Running->Syscall Reason=""\n',
            'TransitionStack=\n', '\tmain.(*cappedWriter).Write @ 0x123\n',
            'M=1 P=0 G=8 StateTransition Time=200 GoID=8 Running->Syscall Reason=""\n',
            'M=1 P=0 G=7 StateTransition Time=300 GoID=7 Syscall->Running Reason=""\n',
            'M=1 P=0 G=7 StateTransition Time=400 GoID=7 Running->Syscall Reason=""\n',
            'TransitionStack=\n', '\tmain.(*cappedWriter).Write @ 0x123\n']
        result = inspect_trace_writer.summarize(lines)
        self.assertEqual(result['writer_syscall_entries'], 2)
        self.assertEqual(result['completed_syscall_spans'], 1)
        self.assertEqual(result['missing_syscall_exit_count'], 1)
        self.assertEqual(result['summed_writer_syscall_ms'], .0002)


if __name__ == '__main__': unittest.main()
