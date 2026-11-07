import unittest

import worker_wait_features as w


def snap(at, cpu, wait, start_ticks=70):
    identity = dict(pid=31, start_ticks=start_ticks, parent=30, exe_sha256='hash')
    return dict(identity=identity, identity_before=identity.copy(), identity_after=identity.copy(),
                read_started_ns=at, read_finished_ns=at + 1,
                counters=dict(running_ns=cpu, runnable_wait_ns=wait, timeslices=cpu // 10))


class CounterContracts(unittest.TestCase):
    def test_parser_units_and_framing(self):
        self.assertEqual(w.parse_schedstat('21021510 3287 2\n'),
                         dict(running_ns=21021510, runnable_wait_ns=3287, timeslices=2))
        for invalid in ('0 0', '1 2 3 4', '-1 0 0', '1.5 0 0', 'True 1 2'):
            with self.assertRaises(ValueError):
                w.parse_schedstat(invalid)

    def test_worker_selection_does_not_sort_pids(self):
        scan = dict(main_pid=30, vanished_during_scan=False, processes=[
            dict(pid=12, parent=30, start_ticks=70, tids=[12], affinity=[2], exe_sha256='hash'),
            dict(pid=30, parent=9, start_ticks=60, tids=[30], affinity=[2], exe_sha256='hash')])
        self.assertEqual(w.select_worker(scan, 'hash')['pid'], 12)
        scan['processes'][0]['parent'] = 29
        with self.assertRaises(ValueError):
            w.select_worker(scan, 'hash')

    def test_cumulative_values_need_matching_baseline(self):
        r = w.interval(snap(0, 1000, 500), snap(10000, 1500, 550), 25, True)
        self.assertEqual(r['running_ns_per_offer'], 20)
        self.assertEqual(r['runnable_wait_ns_per_offer'], 2)
        self.assertFalse(r['per_request_attribution'])

    def test_identity_restart_and_read_race(self):
        with self.assertRaises(ValueError):
            w.interval(snap(0, 100, 10), snap(100, 150, 20, 71), 25, True)
        bad = snap(100, 150, 20)
        bad['identity_after']['start_ticks'] += 1
        with self.assertRaises(ValueError):
            w.interval(snap(0, 100, 10), bad, 25, True)

    def test_unqualified_and_inactive_are_unavailable(self):
        with self.assertRaises(ValueError):
            w.interval(snap(0, 100, 10), snap(100, 150, 20), 25, False)
        with self.assertRaises(ValueError):
            w.interval(snap(0, 100, 10), snap(100, 100, 10), 25, True)

    def test_reversal_and_read_order_rejected(self):
        with self.assertRaises(ValueError):
            w.interval(snap(0, 100, 10), snap(100, 150, 9), 25, True)
        bad = snap(100, 150, 20)
        bad['read_finished_ns'] = -1
        with self.assertRaises(ValueError):
            w.interval(snap(0, 100, 10), bad, 25, True)

    def test_weighted_reference_is_per_offer(self):
        a = w.interval(snap(0, 100, 10), snap(100, 150, 20), 5, True)
        b = w.interval(snap(0, 100, 10), snap(100, 300, 50), 10, True)
        ref = w.reference([a, b])
        self.assertAlmostEqual(ref['running_ns_per_offer'], 250 / 15)
        self.assertAlmostEqual(ref['runnable_wait_ns_per_offer'], 50 / 15)

    def test_separate_cpu_and_wait_drift(self):
        base = w.reference([w.interval(snap(0, 100, 10), snap(1000, 600, 60), 25, True)])
        probe = w.interval(snap(0, 100, 10), snap(1000, 600, 110), 25, True)
        f = w.drift(probe, base)
        self.assertEqual(f['cpu_change_ns_per_offer'], 0)
        self.assertEqual(f['wait_change_ns_per_offer'], 2)
        self.assertFalse(f['future_outcomes_used'])

    def test_failure_mass_and_strict_deadline(self):
        result = w.miss_fraction([dict(success=True, e2e_ns=10), dict(success=False, e2e_ns=None),
                                  dict(success=True, e2e_ns=11)], 10)
        self.assertEqual(str(result), '2/3')


if __name__ == '__main__':
    unittest.main()
