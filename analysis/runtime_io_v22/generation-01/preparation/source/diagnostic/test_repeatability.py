import csv
import math
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import build_repeatability as build
import repeatability_analysis as analysis
import repeatability_study as study
import run
from test_completion import fixture


def images():
    return dict(images=dict(legacy_a='original', legacy_b='original', exact_rebuild='rebuilt'))


def rows():
    return [dict(rep=b, recorder_arm=a, timely_500_fraction=.7, timely_1000_fraction=.95,
        failure_fraction=.01, cpu_usec_per_completed_work=4000, p99_e2e_ms=1000)
        for b in range(1, 5) for a in analysis.ARMS]


class RepeatabilityTests(unittest.TestCase):
    def test_no_service_metadata_all_outcomes_and_missing_markers(self):
        for arm in analysis.ARMS:
            result = analysis.classify(*fixture('legacy'), arm)
            self.assertEqual(result['offered'], 4)
            self.assertEqual(result['deadlines']['500']['failure'], 3)
            self.assertEqual(result['deadlines']['500']['late_success_work_before'], 1)
            self.assertTrue(all(r['publish_start_lower_ns'] is None for r in result['requests']))
        for field, value in (('marker_protocol', 'unexpected'), ('completion_events', [{'id': 0}]),
                ('runtime_capture', True), ('worker_yield', True)):
            c, s = fixture('legacy'); s[field] = value
            with self.assertRaises(ValueError): analysis.classify(c, s, 'legacy_a')

    def test_fixed_matrix_same_image_and_balanced_relative_order(self):
        plan = study.matrix(images())
        self.assertEqual(len(plan), 12)
        excluded = {'run_id', 'rep', 'recorder_arm', 'service_image'}
        self.assertEqual(len({tuple((k, v) for k, v in r.items() if k not in excluded) for r in plan}), 1)
        for a in analysis.ARMS:
            for b in analysis.ARMS:
                if a != b: self.assertEqual(sum(o.index(a) < o.index(b) for o in study.ORDERS), 2)
        bad = images(); bad['images']['legacy_b'] = 'different'
        with self.assertRaisesRegex(ValueError, 'same image'): study.matrix(bad)

    def test_aa_failure_prevents_rebuild_attribution_even_with_zero_rebuild_delta(self):
        data = rows(); data[1]['timely_500_fraction'] -= .02
        result = analysis.compare(data)
        self.assertEqual(result['decision'], 'same_image_variability_requires_review')
        self.assertFalse(result['rebuild_comparison_interpretable'])
        self.assertFalse(result['eligible_for_controls'])

    def test_rebuild_failure_with_stable_aa_and_guardrail_failure(self):
        for key, value in (('timely_500_fraction', .68), ('cpu_usec_per_completed_work', 4500),
                ('p99_e2e_ms', None), ('p99_e2e_ms', math.nan)):
            data = rows(); data[2][key] = value
            result = analysis.compare(data)
            self.assertTrue(result['same_image_within_screen'])
            self.assertFalse(result['rebuild_within_screen'])
            self.assertEqual(result['decision'], 'exact_source_rebuild_difference_requires_review')

    def test_passing_pilot_does_not_qualify_recorder_or_prove_equivalence(self):
        result = analysis.compare(rows())
        self.assertTrue(result['same_image_within_screen'])
        self.assertTrue(result['rebuild_within_screen'])
        self.assertFalse(result['eligible_for_persistent_recording'])
        self.assertFalse(result['eligible_for_controls'])
        self.assertEqual(result['contrasts']['same_image']['block_summary']['cpu_ratio']['sample_sd'], 0)
        for data in (rows()[:-1], rows() + [rows()[0]]):
            with self.assertRaises(ValueError): analysis.compare(data)

    def test_missing_aa_cpu_fails_screen(self):
        data = rows(); data[0]['cpu_usec_per_completed_work'] = None
        result = analysis.compare(data)
        self.assertFalse(result['same_image_within_screen'])
        self.assertIsNone(result['contrasts']['same_image']['block_summary']['cpu_ratio'])

    def test_prepare_is_verbatim_original_dockerfile_and_go_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'prepared'; build.prepare(target)
            self.assertEqual(build.stock.prepared_hashes(target / 'service'),
                build.stock.prepared_hashes(build.stock.DEFAULT / 'prepared/service'))
            self.assertNotIn('marker_protocol', (target / 'service/main.go').read_text())

    def test_launch_quiet_host_and_stop_pid_identity(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(study.pipeline, 'is_running', return_value=False), \
                patch.object(run, 'require_quiet_host', side_effect=ValueError('desktop present')), patch.object(study.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'desktop'): study.launch(Path(tmp))
            spawn.assert_not_called()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); run.put(p / 'launch.json', dict(pid=10, start_tick='old'))
            run.put(p / 'workflow-status.json', dict(worker_pid=11))
            with patch.object(study.pipeline, 'is_running', return_value=True), patch.object(study.pipeline, 'process_signature', return_value='new'), patch.object(study.os, 'kill') as kill:
                with self.assertRaisesRegex(ValueError, 'PID changed'): study.stop(p)
                kill.assert_not_called()

    def test_environment_sealed_then_tamper_refuses_before_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); (p / 'attempts').mkdir()
            power = dict(policies={}, platform_profile='balanced', external_power={'AC': '1'}, desktop_profile='balanced')
            samples = [dict(elapsed_sec=t, temperatures={'test': 44.0}, power_settings=run.comparable_power(power)) for t in range(0, 661, 5)]
            def prepare(session):
                run.put(session / 'environment.json', dict(policy=run.POLICY, power_settings=power, baseline_c={'test': 44.0}))
                run.put(session / 'initial-settling.json', dict(policy=run.POLICY, accepted=True, samples=samples))
            with patch.object(run.old, 'prepare_environment', side_effect=prepare): study.prepare_environment(p)
            study.verify_environment(p, required=True)
            run.put(p / 'environment.json', dict(baseline_c={'test': 60.0}))
            with patch.object(run.old, 'prepare_environment') as resume:
                with self.assertRaisesRegex(ValueError, 'environment changed'): study.prepare_environment(p)
                resume.assert_not_called()

    def test_resume_retains_original_baseline_and_progress_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            power = dict(policies={}, platform_profile='balanced', external_power={'AC': '1'}, desktop_profile='balanced')
            with patch.object(run.old, 'power_settings', return_value=power), patch.object(run.old, 'settle', return_value=dict(sensors={'test': dict(mean_c=44.0)})) as settle:
                run.old.prepare_environment(p); run.old.prepare_environment(p)
                self.assertEqual(settle.call_args.args[1], {'test': 44.0})
            snap = study.snapshot(p)
            self.assertEqual((snap['total'], snap['remaining']), (12, 12))

    def test_real_verified_build_and_frozen_bundle_tamper(self):
        # Mandatory prepared evidence: no skips masquerading as verification.
        value = run.read(build.DEFAULT / 'build.json')
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / 'bundle'; shutil.copytree(build.DEFAULT, bundle)
            with patch.object(run, 'image_id', side_effect=lambda x: x), patch.object(run, 'capture', return_value='{"research.runtime.variant":"stock"}'):
                self.assertEqual(build.verify(bundle), value)
                (bundle / 'binary_audit/legacy.build_id.txt').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'verification files changed'): build.verify(bundle)
            session = Path(tmp) / 'session'
            with patch.object(run, 'require_quiet_host'), patch.object(study.stock_study, 'time_offsets'), \
                    patch.object(run.old, 'check_topology', return_value={'fixture': True}), patch.object(run, 'capture', return_value='fixture'), patch.object(run, 'power_settings', return_value={}):
                study.create(session, value)
            study.verify_session(session, current=False)
            (session / 'repeatability_build/binary_audit/legacy.build_id.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'bundle changed'): study.verify_session(session, current=False)

    def test_real_fixtures_export_all_requests_and_seal_completion(self):
        value = run.read(build.DEFAULT / 'build.json')
        fixtures = {a: build.DEFAULT / f'fixture_{a}_g1' for a in analysis.ARMS}
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); session = directory / 'session'; session.mkdir()
            run.put(session / 'environment_seal.json', dict(fixture=True))
            run.put(session / 'matrix.json', study.matrix(value))
            run.put(session / 'repeatability_build/binary_audit/audit.json', run.read(build.DEFAULT / 'binary_audit/audit.json'))
            def validated(p, c):
                return analysis.classify(run.read(fixtures[c['recorder_arm']] / 'loadgen.json'), run.read(fixtures[c['recorder_arm']] / 'server_metrics.json'), c['recorder_arm'])
            def trial_row(order, c, p):
                row = rows()[0].copy(); row.update(order=order, run_id=c['run_id'], rep=c['rep'], recorder_arm=c['recorder_arm'])
                return row, {}
            for c in study.matrix(value):
                p = session / 'attempts' / c['run_id'] / '001'; p.mkdir(parents=True)
                for name in ('loadgen.json', 'server_metrics.json'): shutil.copy2(fixtures[c['recorder_arm']] / name, p / name)
                run.put(p / 'complete.json', dict(fixture=True))
            with patch.object(study, 'verify_session', return_value={}), patch.object(study, 'validate_attempt', side_effect=validated), patch.object(study.stock_analysis, 'trial_row', side_effect=trial_row):
                study.analyze_results(directory); study.verify_completion(directory)
                out = session / 'analysis'
                with (out / 'requests.csv').open() as stream:
                    offered = [r for r in csv.DictReader(stream) if r['deadline_ms'] == '500']
                self.assertEqual(len(offered), 72)
                self.assertFalse(run.read(out / 'repeatability_screen.json')['eligible_for_controls'])
                (out / 'report.md').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'analysis changed'): study.verify_completion(directory)


if __name__ == '__main__': unittest.main()
