"""Workflow tests use synthetic stages; they never launch research workloads."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import pipeline
import run


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='quota-pipeline-test-')
        self.directory = Path(self.temp.name)
        self.called = []

    def tearDown(self):
        self.temp.cleanup()

    def stage(self, directory, name, command, lock):
        self.called.append((name, list(map(str, command))))
        if name.endswith('collection'):
            session = directory / ('pilot' if name.startswith('pilot') else 'full')
            session.mkdir(exist_ok=True)
            if not (session / 'metadata.json').exists():
                run.put(session / 'metadata.json', {})
            run.put(session / 'matrix.json', run.pilot_matrix() if name.startswith('pilot') else run.matrix())
        if name == 'pilot-analysis':
            run.put(directory / 'pilot/analysis/pilot_gate.json', {'passed': True})
        if name == 'full-analysis':
            run.put(directory / 'full/analysis/validation.json', {'passed': True})
            run.put(directory / 'full/analysis/estimates.json',
                    {pattern: {'interaction_ms': 1, 'interaction_ms_ci95': [-1, 3]} for pattern in ('steady', 'bursty')})

    def execute(self, stage=None):
        with patch.object(pipeline, 'stage_command', side_effect=stage or self.stage), \
             patch.object(run, 'verify_build'), patch.object(run, 'verify_session'), \
             patch.object(run, 'require_pilot'), contextlib.redirect_stdout(io.StringIO()):
            pipeline.execute(self.directory, Mock())

    def test_successful_pipeline_runs_every_stage_and_writes_completion(self):
        self.execute()
        self.assertEqual([stage for stage, _ in self.called], [
            'build-and-go-tests', 'python-regression-tests', 'pilot-collection',
            'pilot-analysis', 'full-collection', 'full-analysis'])
        full = next(command for stage, command in self.called if stage == 'full-collection')
        self.assertIn('--pilot-session', full)
        self.assertEqual(run.read(self.directory / 'workflow-status.json')['state'], 'complete')
        self.assertIn('50 validated trials', (self.directory / 'COMPLETED.md').read_text())
        self.assertTrue((self.directory / 'completion.json').exists())

    def test_failed_pilot_analysis_never_starts_full_collection(self):
        def failing_stage(directory, name, command, lock):
            if name == 'pilot-analysis':
                raise RuntimeError('overhead screen failed')
            self.stage(directory, name, command, lock)
        with self.assertRaisesRegex(RuntimeError, 'overhead screen'):
            self.execute(failing_stage)
        self.assertFalse((self.directory / 'full').exists())
        self.assertFalse((self.directory / 'COMPLETED.md').exists())
        self.assertNotIn('full-collection', [name for name, _ in self.called])

    def test_resume_does_not_rebuild_or_overwrite_existing_sessions(self):
        pilot, full = self.directory / 'pilot', self.directory / 'full'
        run.put(pilot / 'metadata.json', {})
        run.put(pilot / 'analysis/pilot_gate.json', {'passed': True})
        run.put(full / 'metadata.json', {'pilot_session': str(pilot),
                'pilot_gate_sha256': run.sha(pilot / 'analysis/pilot_gate.json')})
        evidence = full / 'existing-evidence.txt'
        evidence.write_text('retain me')
        self.execute()
        self.assertNotIn('build-and-go-tests', [name for name, _ in self.called])
        for name, command in self.called:
            if name.endswith('collection'):
                self.assertIn('resume', command)
                self.assertNotIn('new', command)
        self.assertEqual(evidence.read_text(), 'retain me')

    def test_empty_session_directory_is_not_reused_as_new(self):
        path = self.directory / 'pilot'
        path.mkdir()
        with self.assertRaisesRegex(RuntimeError, 'without session metadata'):
            pipeline.collection_command(path, pilot=True)

    def test_worker_records_failure_and_closes_lock(self):
        lock = Mock()
        with patch.object(run, 'acquire_experiment_lock', return_value=lock), \
             patch.object(pipeline, 'execute', side_effect=RuntimeError('pilot gate failed')), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = pipeline.run_worker(self.directory)
        self.assertEqual(code, 1)
        self.assertEqual(run.read(self.directory / 'workflow-status.json')['state'], 'failed')
        self.assertIn('pilot gate failed', run.read(self.directory / 'workflow-status.json')['error'])
        lock.close.assert_called_once()
        self.assertFalse((self.directory / 'COMPLETED.md').exists())

    def test_repeat_command_does_not_launch_duplicate_or_completed_job(self):
        with patch.object(pipeline, 'is_running', return_value=True), \
             patch.object(pipeline, 'print_status'), patch.object(pipeline.sp, 'Popen') as popen:
            self.assertEqual(pipeline.launch(self.directory), 0)
            popen.assert_not_called()
        run.put(self.directory / 'workflow-status.json', {'state': 'complete', 'stage': 'complete'})
        (self.directory / 'COMPLETED.md').write_text('done')
        with patch.object(pipeline, 'is_running', return_value=False), \
             patch.object(pipeline, 'print_status'), patch.object(pipeline.sp, 'Popen') as popen:
            self.assertEqual(pipeline.launch(self.directory), 0)
            popen.assert_not_called()

    def test_stage_failure_has_nonzero_status_and_no_success_event(self):
        with (self.directory / 'local.lock').open('a') as lock, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'code 7'):
                pipeline.stage_command(self.directory, 'test-failure',
                                       [sys.executable, '-c', 'raise SystemExit(7)'], lock)
        self.assertNotIn('stage_complete', (self.directory / 'workflow-events.jsonl').read_text())


class LockInheritanceTests(unittest.TestCase):
    def test_child_shares_coordinator_lock_while_unrelated_process_is_excluded(self):
        with tempfile.TemporaryDirectory(prefix='quota-lock-test-') as tmp, patch.dict(os.environ):
            os.environ.pop('CPU_QUOTA_EXPERIMENT_LOCK_FD', None)
            path = Path(tmp) / 'experiment.lock'
            with run.acquire_experiment_lock(path) as lock:
                env = dict(os.environ, CPU_QUOTA_EXPERIMENT_LOCK_FD=str(lock.fileno()))
                script = 'from pathlib import Path; import run,sys; lock=run.acquire_experiment_lock(Path(sys.argv[1]))'
                inherited = subprocess.run([sys.executable, '-c', script, str(path)], cwd=run.HERE,
                    env=env, pass_fds=(lock.fileno(),), capture_output=True, text=True)
                self.assertEqual(inherited.returncode, 0, inherited.stderr)
                outsider = subprocess.run([sys.executable, '-c', script, str(path)], cwd=run.HERE,
                    env=os.environ.copy(), capture_output=True, text=True)
                self.assertNotEqual(outsider.returncode, 0)
                self.assertIn('BlockingIOError', outsider.stderr)
            with run.acquire_experiment_lock(path):
                pass


if __name__ == '__main__':
    unittest.main()
