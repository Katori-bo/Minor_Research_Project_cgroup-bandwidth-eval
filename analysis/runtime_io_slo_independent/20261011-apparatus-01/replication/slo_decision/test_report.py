import copy
from pathlib import Path
import unittest
import evaluation as e
import collectors as a
import report as r

ROOT=Path(__file__).resolve().parents[2]
PLAN=a.read(ROOT/'analysis/runtime_io_slo_independent/20261011-v1-frozen/plan.json')


def complete():
    cells=e.warmup_predictions([1]*39+[2],[1]*25,
        e.calibration_predictions([1]*39+[2],PLAN['fixed_deadlines_ns']['Go']))
    for cell in cells:
        cell['methods']={name:dict(forecast=f,score=e.score(f,[1]*93+[2]*7,cell['deadline_ns']))
                         for name,f in cell['methods'].items()}
    return dict(status='primary_domain',cells=cells)


class ReportOracles(unittest.TestCase):
    def test_all_unavailable_retains_72_slots_and_undefined_risk(self):
        value=r.report(PLAN,{})
        self.assertEqual(len(value['windows']),72)
        self.assertTrue(all(t['rates']['false_assurance_per_meets'] is None for t in value['tables']))
        self.assertFalse(value['independent_hardware_event_observed'])

    def test_complete_adverse_separate_from_primary_and_full_denominator(self):
        cid='slo_v1_host02_Go';first=complete();adverse=copy.deepcopy(first)
        adverse['status']='applicability_exit';adverse['domain_exits']=['dispatch_gate']
        value=r.report(PLAN,{cid:{'v31_b1_A':first,'v31_b1_B':adverse}})
        self.assertEqual(len(value['primary_event_windows']),1)
        self.assertTrue(value['independent_hardware_event_observed'])
        cells=[t for t in value['tables'] if t['campaign_id']==cid and t['label']=='q/39/40'
               and t['method']=='reference' and t['procedure']=='point']
        self.assertEqual([t['counts']['false_assurance'] for t in cells],[2,1])
        self.assertEqual([t['rates']['assurance_coverage_all_planned'] for t in cells],[2/18,1/18])

    def test_dkw_abstention_is_not_unavailable_or_safe_assurance(self):
        cid='slo_v1_host01_Go'
        value=r.report(PLAN,{cid:{'v31_b1_A':complete()}})
        table=next(t for t in value['tables'] if t['campaign_id']==cid and t['view']=='primary_domain'
            and t['label']=='q/39/40' and t['method']=='reference' and t['procedure']=='dkw')
        self.assertEqual(table['counts']['inconclusive'],1)
        self.assertEqual(table['rates']['answer_coverage_all_planned'],0)
        self.assertIsNone(table['rates']['false_assurance_per_meets'])

    def test_foreign_partial_or_missing_method_rejected(self):
        with self.assertRaises(ValueError):r.report(PLAN,{'foreign':{}})
        value=complete();value['status']='unavailable'
        with self.assertRaises(ValueError):r.report(PLAN,{'slo_v1_host01_Go':{'v31_b1_A':value}})
        value=complete();del value['cells'][0]['methods']['recent25']
        with self.assertRaises(ValueError):r.report(PLAN,{'slo_v1_host01_Go':{'v31_b1_A':value}})


if __name__=='__main__':unittest.main()
