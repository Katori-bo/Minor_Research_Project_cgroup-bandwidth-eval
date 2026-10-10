"""Retained scientific checks plus final-context interruption regressions."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_v29 import FrozenTransferTests,CalibrationAndDeadlineTests,SupervisorTests
import v29r4_common as c
import v29r4_study as study
import v29r4_campaign as campaign


class FinalContextTests(unittest.TestCase):
    def test_only_final_context_and_fresh_directories(self):
        self.assertEqual(campaign.ORDER,('q025_large',))
        self.assertEqual(campaign.session_for('q025_large'),c.PARENT/'generation-04')
        for key in ('q050_small','q025_small','q050_large'):
            with self.assertRaises(ValueError):campaign.session_for(key)
        with self.assertRaises(ValueError):c.owned_directory(c.PARENT/'generation-03')
        with self.assertRaises(ValueError):campaign.validate_directory(campaign.PARENT/'generation-03')
        self.assertEqual(c.owned_directory(c.PARENT/'generation-04'),c.PARENT/'generation-04')

    def test_original_sources_and_scientific_design_preserved(self):
        old=c.read(c.PARENT/'generation-03/bundle/manifest.json')
        self.assertEqual(c.retained_v29.source_hashes(),old['sources'])
        self.assertEqual(c.matrix(),old['matrix'])
        self.assertEqual(c.digest(c.DESIGN/'seal.json'),old['design_seal'])

    def test_bound_includes_all_retained_stage_bounds(self):
        design=c.design()
        self.assertEqual(campaign.TOTAL_SEC,10800)
        needed=design['runtime_preparation_bound_sec']+300+design['measurement_bound_sec']+600+120
        self.assertGreater(campaign.TOTAL_SEC,needed)

    def test_final_audit_retains_terminal_authentication(self):
        with patch.object(campaign.sys.stdin,'isatty',return_value=True),patch.object(campaign,'invoke') as invoke:
            campaign.collect_observer_inventory(Path('/tmp/unused'),Path('/tmp/unused-audit'),12345)
        argv=invoke.call_args.args[1]
        self.assertEqual(argv[0],'sudo');self.assertNotIn('-n',argv)
        self.assertFalse(invoke.call_args.kwargs['new_session'])

    def test_interruption_never_retries_even_after_successful_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp)
            def interrupted(_session,directory,cfg,phase):
                directory.mkdir(parents=True)
                c.save(directory/'cleanup.json',dict(errors=[],watchdog_intervened=False))
                raise InterruptedError('bounded measurement interrupted')
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study.verify,'verify_preparation'),patch.object(study.verify,'verify_environment'),patch.object(study,'failures',return_value=[]),patch.object(study,'collect',side_effect=interrupted) as collect:
                with self.assertRaises(InterruptedError):study.collect_slot(session,c.matrix()[0])
            self.assertEqual(collect.call_count,1)
            self.assertEqual(len(list((session/'slots').glob('*/attempt-*'))),1)

    def test_expired_lifetime_prevents_first_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp)
            c.save(session/'measurement_lifetime.json',dict(deadline_monotonic=study.time.monotonic()-1))
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study,'collect') as collect:
                with self.assertRaises(TimeoutError):study.collect_slot(session,c.matrix()[0])
            collect.assert_not_called()
            self.assertFalse((session/'slots').exists())

    def test_lifetime_expiring_during_failure_prevents_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp)
            c.save(session/'measurement_lifetime.json',dict(deadline_monotonic=study.time.monotonic()+100))
            def expired(_session,directory,cfg,phase):
                directory.mkdir(parents=True)
                c.save(directory/'cleanup.json',dict(errors=[],watchdog_intervened=False))
                c.save(session/'measurement_lifetime.json',dict(deadline_monotonic=study.time.monotonic()-1))
                raise TimeoutError('measurement bound exhausted')
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study.verify,'verify_preparation'),patch.object(study.verify,'verify_environment'),patch.object(study,'failures',return_value=[]),patch.object(study,'collect',side_effect=expired) as collect:
                with self.assertRaises(TimeoutError):study.collect_slot(session,c.matrix()[0])
            self.assertEqual(collect.call_count,1)

    def test_ordinary_technical_failure_still_has_one_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            session=Path(temp);calls=[]
            c.save(session/'preparation/manifest.json',{})
            def recoverable(_session,directory,cfg,phase):
                directory.mkdir(parents=True);calls.append(directory)
                c.save(directory/'cleanup.json',dict(errors=[],watchdog_intervened=False))
                if len(calls)==1:raise RuntimeError('technical client failure')
            with patch.object(study.verify,'accepted',return_value=None),patch.object(study.verify,'verify_preparation'),patch.object(study.verify,'verify_environment'),patch.object(study.verify,'verify_trial'),patch.object(study,'failures',return_value=[]),patch.object(study,'collect',side_effect=recoverable):
                study.collect_slot(session,c.matrix()[0])
            self.assertEqual(len(calls),2)
            self.assertNotEqual(calls[0],calls[1])


if __name__=='__main__':unittest.main()
