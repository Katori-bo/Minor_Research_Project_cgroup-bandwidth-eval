"""Contract oracles for the saved-data stage discrepancy screen."""
import unittest

import screen_stage_transfer_signal as s


class StageContracts(unittest.TestCase):
    def test_telescoping(self):
        data = s.stages([dict(ScheduledNs=10, DispatchNs=12, HeadersNs=17, BodyDoneNs=23)],
                        [dict(success=True, e2e_ns=13)])
        self.assertEqual(data, dict(dispatch=[2], headers=[5], body=[6]))

    def test_failed_stage_not_fabricated(self):
        self.assertEqual(s.stages([{}], [dict(success=False)]),
                         dict(dispatch=[None], headers=[None], body=[None]))

    def test_stage_order_rejected(self):
        with self.assertRaises(ValueError):
            s.stages([dict(ScheduledNs=0, DispatchNs=4, HeadersNs=3, BodyDoneNs=8)],
                     [dict(success=True, e2e_ns=8)])

    def test_stable_identical_stages(self):
        ref = [50] * 20 + [150] * 20
        warm = [50] * 12 + [150] * 13
        a = {j: ref[:] for j in s.STAGES}
        b = {j: warm[:] for j in s.STAGES}
        # This intentionally differing median is not a stable location profile.
        result = s.features(ref, warm, a, b, 100)
        self.assertFalse(result['accepts']['stage_projected'])
        stable = s.features([100] * 40, [100] * 25,
                           {j: [30] * 40 for j in s.STAGES},
                           {j: [30] * 25 for j in s.STAGES}, 100)
        self.assertTrue(stable['accepts']['stage_projected'])
        self.assertEqual(stable['predictions_pct']['reference'], 0)

    def test_cancellation_can_change_stages_without_total_shift(self):
        ref, warm = [100] * 40, [100] * 25
        a = dict(dispatch=[20] * 40, headers=[30] * 40, body=[50] * 40)
        b = dict(dispatch=[20] * 25, headers=[40] * 25, body=[40] * 25)
        result = s.features(ref, warm, a, b, 100)
        self.assertEqual(result['scores_pp']['full_median_temporal'], 0)
        self.assertEqual(result['scores_pp']['stage_projected'], 100)
        self.assertFalse(result['accepts']['stage_projected'])

    def test_failures_remain_misses_and_force_abstention(self):
        ref, warm = [100] * 40, [100] * 24 + [None]
        result = s.features(ref, warm, {j: ref[:] for j in s.STAGES},
                            {j: warm[:] for j in s.STAGES}, 100)
        self.assertFalse(result['accepts']['stage_projected'])
        self.assertTrue(result['accepts']['always'])
        self.assertEqual(result['scores_pp']['deadline_disagreement'], 4)


if __name__ == '__main__':
    unittest.main()
