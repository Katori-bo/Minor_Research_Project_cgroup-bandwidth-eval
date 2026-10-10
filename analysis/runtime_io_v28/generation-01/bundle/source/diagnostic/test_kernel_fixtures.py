import unittest

import kernel_fixture_analysis as analysis


class QuotaEvidenceTests(unittest.TestCase):
    def test_failed_throttle_attempt_is_not_a_pause(self):
        pauses,attempts=analysis.quota_intervals([['T',10,20,2,99,100,0,0]],99)
        self.assertEqual(attempts,1)
        self.assertEqual(pauses,[])

    def test_transition_brackets_are_retained_as_bounds(self):
        rows=[['T',10,20,2,99,100,1,1],['U',80,90,2,99,100,1,0]]
        pauses,_=analysis.quota_intervals(rows,99)
        self.assertEqual(pauses[0]['duration_lower_ns'],60)
        self.assertEqual(pauses[0]['duration_upper_ns'],80)

    def test_unsuccessful_unthrottle_does_not_close_pause(self):
        rows=[['T',10,20,2,99,100,1,1],['U',40,50,2,99,100,1,1]]
        with self.assertRaises(ValueError):analysis.quota_intervals(rows,99)

    def test_wrong_identity_duplicate_and_open_intervals_are_refused(self):
        t=['T',10,20,2,99,100,1,1];u=['U',80,90,2,99,100,1,0]
        for rows,cgid in (([t,u],88),([t],99),([u],99),([t,t,u],99)):
            with self.subTest(rows=rows,cgid=cgid),self.assertRaises(ValueError):
                analysis.quota_intervals(rows,cgid)

    def test_cross_cpu_intervals_are_not_combined(self):
        rows=[['T',10,20,2,99,100,1,1],['T',15,25,4,99,200,1,1],
              ['U',80,90,2,99,100,1,0],['U',90,100,4,99,200,1,0]]
        pauses,_=analysis.quota_intervals(rows,99)
        self.assertEqual([p['cpu'] for p in pauses],[2,4])

    def test_loss_count_and_diagnostics_fail(self):
        text='BEGIN 1 99\nW 10 0 123 2\nEND 20 1\n'
        self.assertEqual(len(analysis.records(text,'')[0]),1)
        with self.assertRaises(ValueError):analysis.records(text.replace('END 20 1','END 20 2'),'')
        for message in ('Lost 1 events','WARNING: failed helper','ERROR: attach failed'):
            with self.subTest(message=message),self.assertRaises(ValueError):analysis.records(text,message)

    def test_unknown_output_and_out_of_window_events_fail(self):
        for text in ('BEGIN 1 99\nunknown\nEND 20 0\n',
                     'BEGIN 1 99\nW 30 0 123 2\nEND 20 1\n'):
            with self.assertRaises(ValueError):analysis.records(text,'')


if __name__=='__main__':unittest.main()
