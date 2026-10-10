import unittest
import inspect_http_cleanup as cleanup
import trace_analysis as trace


class CleanupTests(unittest.TestCase):
    def evidence(self):
        parsed = dict(event_count=7, first_ns=0, transitions={
            '10': [(0, 'Undetermined', 'Running', ''),
                   (10, 'Running', 'Waiting', 'sync'),
                   (15, 'Waiting', 'Waiting', ''),
                   (30, 'Waiting', 'Runnable', '')],
            '20': [(5, 'NotExist', 'Runnable', ''),
                   (20, 'Runnable', 'Runnable', ''),
                   (29, 'Runnable', 'Running', '')]})
        request = dict(id=1, outcome='success', conn=1, last_socket_write_end_ns=9,
                       intervals={'handler_exit_to_connection_done':
                                  dict(goroutine=10, start_ns=8, end_ns=35)})
        requests = dict(clock_mapping=dict(offset_low_ns=0, offset_high_ns=0,
                                            uncertainty_ns=0), all_requests=[request])
        server = dict(events=[dict(completion_ns=t) for t in (12, 25, 40)])
        index = dict(waits=[(10, 10)], wakes={(10, 30): 20}, creates={20: (10, 5)})
        return parsed, requests, server, index

    def test_wait_crosses_census_and_joins_exact_child(self):
        result = cleanup.join(*self.evidence())
        row = result['all_request_rows'][0]
        self.assertEqual(row['wait_ns'], 20)
        self.assertEqual(row['generation_snapshots_crossed'], 1)
        self.assertEqual(row['reader_states'], {'runnable_ns': 19, 'go_running_ns': 1})
        self.assertEqual(row['other_jobs_completed'], 2)
        self.assertTrue(row['reader_never_ran_before_cleanup_wait'])
        self.assertTrue(row['final_socket_write_before_wait'])

    def test_network_reason_survives_empty_census(self):
        parsed = dict(event_count=3, first_ns=0, transitions={
            '1': [(0, 'Undetermined', 'Waiting', 'network'),
                  (10, 'Waiting', 'Waiting', ''),
                  (20, 'Waiting', 'Runnable', '')]})
        series = cleanup.snapshot_series(parsed)[1]
        self.assertEqual(trace.state_durations(series, 0, 20), {'network_wait_ns': 20})

    def test_wrong_parent_fails_and_missing_waker_is_counted(self):
        evidence = self.evidence()
        evidence[-1]['creates'][20] = (99, 5)
        with self.assertRaisesRegex(ValueError, 'creator/ordering mismatch'):
            cleanup.join(*evidence)
        evidence = self.evidence()
        evidence[-1]['wakes'].clear()
        result = cleanup.join(*evidence)
        self.assertEqual(result['requests_matched'], 0)
        self.assertEqual(result['unmatched'], {'no_background_read_broadcast_stack': 1})

    def test_stack_index_distinguishes_child_creator_and_broadcaster(self):
        raw = '''M=1 P=0 G=10 StateTransition Time=5 Resource=Goroutine(20) Reason="" GoID=20 NotExist->Runnable Reason=""
TransitionStack=
 net/http.(*connReader).backgroundRead @ 0x1
Stack=
 net/http.(*connReader).startBackgroundRead @ 0x2
M=1 P=0 G=10 StateTransition Time=10 GoID=10 Running->Waiting Reason="sync"
TransitionStack=
 sync.(*Cond).Wait @ 0x3
 net/http.(*connReader).abortPendingRead @ 0x4
M=1 P=0 G=-1 StateTransition Time=15 GoID=10 Waiting->Waiting Reason=""
M=1 P=0 G=20 StateTransition Time=30 GoID=10 Waiting->Runnable Reason=""
Stack=
 sync.(*Cond).Broadcast @ 0x5
 net/http.(*connReader).backgroundRead @ 0x6
'''
        index = cleanup.index_events(raw.splitlines(keepends=True))
        self.assertEqual(index, dict(waits=[(10, 10)], wakes={(10, 30): 20},
                                     creates={20: (10, 5)}))


if __name__ == '__main__':
    unittest.main()
