"""Counter scope/lifecycle, conservative decisions and retained-record replay."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import execution_delay_common as old
import period_cost as pc
import period_cost_perf as hardware


def counters():
    return [dict(cpu='CPU'+str(cpu), event=event, **{'counter-value':'1000000',
        'event-runtime':1000000, 'pcnt-running':100})
        for cpu in (2,4) for event in ('cycles:u','instructions:u')]


def rows():
    result = []
    for spec in pc.matrix():
        short = spec['period_ms'] == 20
        r = dict(spec, cpu_usec_per_completed_work=3800 if short else 3600,
            busy_capacity=139 if short else 150, timely_500_fraction=.55 if short else .82,
            timely_1000_fraction=.97 if short else 1, failure_fraction=.023 if short else 0,
            p99_e2e_ms=950 if short else 650, rejected_fraction=.023 if short else 0,
            busy_cpu_cores=.5, instructions_per_job=1060000 if short else 1000000,
            cycles_per_instruction=1, effective_cycles_per_user_sec=3000000000)
        result.append(r)
    return result


class ScopeTests(unittest.TestCase):
    def test_balanced_matrix_exact_legacy_binary_contract(self):
        self.assertEqual(len(pc.matrix()),16)
        for position in range(4):
            self.assertEqual(len({order[position] for order in pc.ORDERS}),4)
        for spec in pc.matrix():
            config = pc.legacy_config(spec)
            old.validate_config(config)
            self.assertFalse(config['worker_yield'])
            self.assertEqual(config['workers'],1)
            self.assertEqual(config['quota_us']/config['period_us'],.5)
            self.assertEqual(old.schedule(config),old.arrivals())

    def test_both_events_both_cpus_and_coverage_required(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/'perf'
            def parse(values):
                p.write_text('\n'.join(json.dumps(v) for v in values))
                return pc.parse_perf(p)
            self.assertEqual(parse(counters())['instructions'],2000000)
            for mutation in ('missing','duplicate','wrong_cpu','low_coverage','unsupported','nan'):
                values = counters()
                if mutation == 'missing': values.pop()
                elif mutation == 'duplicate': values.append(values[0])
                elif mutation == 'wrong_cpu': values[0]['cpu']='CPU0'
                elif mutation == 'low_coverage': values[0]['pcnt-running']=90
                elif mutation == 'unsupported': values[0]['counter-value']='<not supported>'
                else: values[0]['counter-value']='nan'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): parse(values)

    def test_off_does_not_accept_hardware_results(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'perf'; p.write_text('')
            self.assertIsNone(pc.parse_perf(p,False))
            p.write_text(json.dumps(counters()[0]))
            with self.assertRaises(ValueError): pc.parse_perf(p,False)

    def test_real_null_perf_handshake_and_graceful_flush(self):
        # No hardware events, privilege, service or performance workload.
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); c=hardware.Counter(d,Path('/sys/fs/cgroup'),False)
            try:
                c.control('enable'); c.control('disable')
            finally: c.close()
            receipt=old.read(d/'perf_receipt.json')
            self.assertEqual(receipt['returncode'],0)
            self.assertEqual([v['op'] for v in receipt['controls']],['disable','enable','disable'])
            self.assertIsNone(pc.parse_perf(d/'perf.jsonl',False))
            self.assertEqual(receipt['argv'][-2:],['--','/usr/bin/cat'])

    def test_control_state_prevents_duplicate_enable(self):
        with tempfile.TemporaryDirectory() as t:
            c=hardware.Counter(Path(t),Path('/sys/fs/cgroup'),False)
            try:
                c.control('enable')
                with self.assertRaisesRegex(ValueError,'already enabled'): c.control('enable')
                c.control('disable')
            finally: c.close()

    def test_failed_exit_and_large_alignment_do_not_pass(self):
        def sample(op,a,b,t):
            return dict(op=op,before_ns=t,after_ns=t+1,
                cpu_before=dict(usage_usec=a,user_usec=a,system_usec=0),
                cpu_after=dict(usage_usec=b,user_usec=b,system_usec=0))
        receipt=dict(returncode=0,controls=[sample('disable',0,0,1),
                    sample('enable',0,1,10),sample('disable',100000,100001,10000000)])
        self.assertLess(pc.counter_bounds(receipt)['relative_alignment_width'],.005)
        receipt['returncode']=1
        with self.assertRaises(ValueError): pc.counter_bounds(receipt)
        receipt['returncode']=0; receipt['controls'][-1]['cpu_after']['usage_usec']=200000
        with self.assertRaisesRegex(ValueError,'alignment'): pc.counter_bounds(receipt)

    def test_sealed_dependency_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d=Path(t); (d/'raw').write_text('original'); old.seal(d)
            (d/'raw').write_text('changed')
            with self.assertRaises(ValueError): old.verify_seal(d)

    def test_external_session_path_rejected(self):
        with self.assertRaises(ValueError): pc.owned_directory('/tmp/arbitrary')


class DecisionTests(unittest.TestCase):
    def test_detectable_change_does_not_claim_cause_or_novelty(self):
        report=pc.compare(rows())
        self.assertEqual(report['decision'],'measurement_feasible_targeted_control_needed')
        self.assertFalse(report['causal_mechanism_established'])
        self.assertFalse(report['novelty_established'])
        self.assertTrue(report['rejection_work_present'])

    def test_observer_bias_blocks_advance(self):
        values=rows()
        for r in values:
            if r['counters']: r['cpu_usec_per_completed_work'] *= 1.02
        self.assertEqual(pc.compare(values)['decision'],'observer_or_precision_inconclusive')

    def test_deadline_instability_blocks_advance_even_if_cpu_stable(self):
        values=rows()
        for r in values:
            if r['counters']: r['timely_500_fraction'] += .02
        self.assertFalse(pc.compare(values)['observer_screen_passed'])

    def test_missing_or_duplicate_trial_never_imputed(self):
        values=rows()
        for v in (values[:-1], values[:-1]+[values[0]]):
            with self.assertRaises(ValueError): pc.compare(v)

    def test_period_effect_absent_is_not_feasible_success(self):
        values=rows()
        for r in values: r['cpu_usec_per_completed_work']=3600; r['busy_capacity']=150
        self.assertEqual(pc.compare(values)['decision'],'effect_not_reproduced')

    def test_mixed_block_variation_is_not_evidence_of_observer_effect(self):
        values=rows()
        for r in values:
            if r['counters']: r['cpu_usec_per_completed_work'] *= [1.03,.97,1.03,.97][r['block']-1]
        result=pc.compare(values)
        self.assertEqual(result['decision'],'observer_or_precision_inconclusive')
        self.assertAlmostEqual(result['observer']['100']['cpu']['mean'],-.00045,places=4)

    def test_quiet_guard_and_no_resume_are_in_runner(self):
        source=Path(pc.__file__).read_text()
        self.assertIn('run.require_quiet_host()',source)
        self.assertIn('no automatic resume/rerun',source)
        self.assertNotIn("choices=('prepare','verify-preparation','run','resume'",source)

    def test_retained_v20_records_join_without_modification(self):
        spec=pc.matrix()[0]
        d=next((pc.BASE/'trials/b1_A').glob('attempt-*'))
        old.verify_seal(d)
        result=pc.legacy_analysis.replay(d)
        self.assertEqual(result['summary']['offered'],6793)
        self.assertEqual(result['summary']['completed_computations'],6793)


if __name__ == '__main__': unittest.main()
