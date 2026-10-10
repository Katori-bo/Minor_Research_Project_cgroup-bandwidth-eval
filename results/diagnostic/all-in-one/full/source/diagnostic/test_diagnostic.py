"""No workload is launched by these configuration and analysis checks."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import analyze
import run


class DiagnosticPlanTests(unittest.TestCase):
    def test_client_launch_preserves_flags_after_trace_toggle(self):
        for enabled in (True, False):
            config = dict(run.matrix()[0], client_trace=enabled)
            with TemporaryDirectory() as directory, patch.object(run.sp, 'Popen') as popen:
                popen.return_value.wait.return_value = 0
                popen.return_value.poll.return_value = 0
                output = Path(directory) / 'client.json'
                run.run_client(config, 1, output)
                args = popen.call_args.args[0]
                self.assertIn(f'-trace-client={str(enabled).lower()}', args)
                self.assertNotIn('-trace-client', args)
                self.assertEqual(args[args.index('-output') + 1], str(output))
                self.assertEqual(args[args.index('-burst-period') + 1], '10s')

    def test_frozen_matrix_and_pilot(self):
        rows = run.matrix()
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({r['run_id'] for r in rows}), 20)
        self.assertEqual(run.matrix(), rows)
        self.assertEqual({(r['period_us'], r['workers']) for r in rows},
                         {(100000, 1), (100000, 4), (250000, 1), (250000, 4)})
        for row in rows:
            self.assertEqual(row['quota_us'] * 2, row['period_us'])
            self.assertEqual((row['gomaxprocs'], row['pattern'], row['rate']), (2, 'bursty', 113.21))
            self.assertTrue(row['client_trace'])
            self.assertEqual((row['warmup_sec'], row['duration_sec'], row['timeout_sec']), (20, 60, 5))
        pilot = run.pilot_matrix()
        self.assertEqual(len(pilot), 7)
        self.assertEqual([r['instrument'] for r in pilot[:4]], [True, False, False, True])
        self.assertEqual([r['client_trace'] for r in pilot[:4]], [True, False, False, True])
        self.assertEqual({(r['period_us'], r['workers']) for r in pilot if r['instrument']},
                         {(100000, 1), (100000, 4), (250000, 1), (250000, 4)})

    def test_interaction_uses_trials_as_units(self):
        cells = {(100, 1): [1.0] * 5, (100, 4): [5.0] * 5,
                 (250, 1): [2.0] * 5, (250, 4): [4.0] * 5}
        self.assertEqual(analyze.interaction(cells), 2.0)
        self.assertEqual(analyze.boot(cells, analyze.interaction), [2.0, 2.0])

    def test_pilot_gate_rejects_missing_timing_and_excess_overhead(self):
        fields = dict(p99_e2e_ms=100., client_cpu_usec_per_scheduled=10.,
                      trace_coverage=1., p99_pre_admission_ms=.01, p99_post_work_ms=.01,
                      p99_request_to_first_byte_ms=1., p99_first_byte_to_body_done_ms=.01)
        rows = [dict(run_id=f'pilot_overhead_{i}', period_ms=100., workers=4,
                     instrument=on, cpu_usec_per_completed_work=100 if on else 100,
                     **fields) for i, on in enumerate((True, False, False, True), 1)]
        rows += [dict(run_id=f'pilot_p{p}_w{w}', period_ms=float(p), workers=w,
                      instrument=True, cpu_usec_per_completed_work=100, **fields)
                 for p, w in ((100, 1), (250, 4), (250, 1))]
        self.assertTrue(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['cpu_usec_per_completed_work'] = 130
        rows[3]['cpu_usec_per_completed_work'] = 130
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['cpu_usec_per_completed_work'] = 100
        rows[3]['cpu_usec_per_completed_work'] = 100
        rows[0]['client_cpu_usec_per_scheduled'] = 13
        rows[3]['client_cpu_usec_per_scheduled'] = 13
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['client_cpu_usec_per_scheduled'] = 10
        rows[3]['client_cpu_usec_per_scheduled'] = 10
        rows[0]['p99_e2e_ms'] = 130
        rows[3]['p99_e2e_ms'] = 130
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])
        rows[0]['p99_e2e_ms'] = 100
        rows[3]['p99_e2e_ms'] = 100
        rows[4]['p99_post_work_ms'] = None
        self.assertFalse(analyze.pilot_gate(rows, {})['passed'])


if __name__ == '__main__':
    unittest.main()
