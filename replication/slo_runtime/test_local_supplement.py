"""Offline amendment, fresh-entrypoint and separate-denominator checks."""
import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
import common as c
import local_supplement as amendment
import supervisor
import assemble_returns
import evaluation as e
import report


class Supplement(unittest.TestCase):
    def setUp(self):
        self.plan=c.read(ROOT/'scientific/plan.json')
        self.package=c.verify_package(ROOT)

    def test_scientific_rules_are_exactly_inherited(self):
        old=c.read(ROOT/'original_scientific/plan.json')
        changed=set(self.plan['amendment']['changed_plan_fields'])
        self.assertEqual(set(self.plan)-{'amendment'},set(old))
        for key in old:
            if key not in changed:
                with self.subTest(field=key):self.assertEqual(self.plan[key],old[key])
        self.assertEqual({x['host'] for x in self.plan['campaigns']},{'host01'})
        self.assertEqual(sum(x['planned_windows'] for x in self.plan['campaigns']),36)
        self.assertEqual(self.plan['budget']['total_cap_sec'],15300)
        self.assertTrue(all(x['scientific_attempt_limit']==1 for x in self.plan['campaigns']))

    def test_original_attempts_costs_and_seals_survive(self):
        ledger=amendment.original_ledger(ROOT)
        rows={row['application']:row for row in ledger['original_allocations']}
        self.assertEqual(sum(x['declared_offers'] for x in rows['Go']['acquired_raw_offers']),510)
        self.assertEqual(rows['NGINX']['acquired_raw_offers'],[])
        self.assertEqual(rows['Go']['summary']['elapsed_sec'],46.675556012)
        self.assertEqual(rows['NGINX']['summary']['elapsed_sec'],187.520880128)
        self.assertEqual(ledger['combined_attempt_ledger_slots'],108)
        self.assertFalse(ledger['supplement_replaces_original_slots'])

    def test_missing_acknowledgment_creates_no_state(self):
        before={str(x) for x in (ROOT/'runs').rglob('*')}
        with self.assertRaisesRegex(ValueError,'amendment-accepted'):amendment.accept(ROOT,False)
        with self.assertRaisesRegex(ValueError,'amendment acceptance'):supervisor.admit(ROOT,'Go',True)
        self.assertEqual(before,{str(x) for x in (ROOT/'runs').rglob('*')})

    def test_real_setup_and_launch_cli_require_acknowledgment(self):
        before={str(x) for x in (ROOT/'runs').rglob('*')}
        with tempfile.TemporaryDirectory() as temp:
            for arguments in (['runtime/setup.py','setup'],
                              ['runtime/supervisor.py','run','--application','Go','--allocation-confirmed'],
                              ['runtime/prelaunch_local_supplement.py','--application','Go']):
                result=subprocess.run([sys.executable,'-B',str(ROOT/arguments[0])]+arguments[1:],
                    cwd=temp,capture_output=True,text=True,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('amendment-accepted',result.stderr)
        self.assertEqual(before,{str(x) for x in (ROOT/'runs').rglob('*')})

    def test_prelaunch_is_read_only_and_nginx_requires_go_setup(self):
        before={str(x) for x in (ROOT/'runs').rglob('*')}
        amendment.prelaunch(ROOT,'Go',True,True)
        with self.assertRaisesRegex(ValueError,'first run Go'):amendment.prelaunch(ROOT,'NGINX',True,True)
        self.assertEqual(before,{str(x) for x in (ROOT/'runs').rglob('*')})

    def test_acknowledgment_is_exact_and_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);c.write(root/'scientific/plan.json',self.plan)
            c.write(root/'runtime_seal.json',dict(synthetic=True))
            with patch.object(c,'verify_package',return_value=self.package),\
                 patch.object(amendment,'original_ledger',return_value=dict(synthetic=True)):
                amendment.accept(root,True)
                path=root/'runs/host01/amendment_acceptance.json';first=path.read_bytes()
                amendment.accept(root,True);self.assertEqual(path.read_bytes(),first)
                value=c.read(path);value['additional_campaign_cap_sec']=0
                path.write_text(__import__('json').dumps(value))
                with self.assertRaisesRegex(ValueError,'acceptance differs'):amendment.accept(root,True)

    def test_supplement_report_has_36_unavailable_slots_and_null_risk(self):
        value=report.report(self.plan,{})
        self.assertEqual((value['planned_windows'],len(value['windows'])),(36,36))
        self.assertTrue(all(x['rates']['false_assurance_per_meets'] is None for x in value['tables']))
        self.assertFalse(value['independent_hardware_event_observed'])

    def test_denominator_mismatch_is_rejected(self):
        bad=copy.deepcopy(self.plan);bad['planned_target_windows']=72
        with self.assertRaisesRegex(ValueError,'planned window denominator'):report.report(bad,{})

    def test_local_primary_event_never_claims_independent_hardware(self):
        cells=e.warmup_predictions([1]*39+[2],[1]*25,
            e.calibration_predictions([1]*39+[2],self.plan['fixed_deadlines_ns']['Go']))
        for cell in cells:
            cell['methods']={name:dict(forecast=f,score=e.score(f,[1]*93+[2]*7,cell['deadline_ns']))
                for name,f in cell['methods'].items()}
        cid=next(x['id'] for x in self.plan['campaigns'] if x['application']=='Go')
        value=report.report(self.plan,{cid:{'v31_b1_A':dict(status='primary_domain',cells=cells)}})
        self.assertEqual(len(value['primary_event_windows']),1)
        self.assertFalse(value['independent_hardware_event_observed'])

    def test_one_host_closed_report_keeps_original_attempts_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);meta=copy.deepcopy(self.package);meta.pop('local_supplement')
            c.write(root/'runtime_package.json',meta);c.write(root/'scientific/plan.json',self.plan)
            c.write(root/'runtime_seal.json',dict(synthetic=True))
            with patch.object(c,'verify_package',side_effect=lambda p:c.read(Path(p)/'runtime_package.json')):
                for app in meta['host']['order']:
                    supervisor.close_unavailable(root,app,'OFFLINE SYNTHETIC FIXTURE',True)
                result=assemble_returns.assemble([root])
            self.assertEqual(result['allocated_cap_sec'],15300)
            self.assertEqual(len(result['windows']),36)
            self.assertEqual(result['primary_verdict'],'unavailable')
            self.assertFalse(result['independent_hardware_event_observed'])


if __name__=='__main__':unittest.main()
