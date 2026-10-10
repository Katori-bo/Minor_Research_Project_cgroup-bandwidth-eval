from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_trace_timestamps as audit
import build_pending_probe as build
import pending_probe as probe
import run
import trace_analysis as trace


class TimestampTests(unittest.TestCase):
    def test_restore_original_times_sort_and_remove_census_without_changing_stack(self):
        blocks=[['M=1 P=0 G=1 StateTransition Time=100 GoID=1 Undetermined->Waiting Reason="network"\n'],
                ['M=2 P=-1 G=-1 StateTransition Time=101 GoID=1 Waiting->Waiting Reason=""\n'],
                ['M=2 P=-1 G=-1 StateTransition Time=102 GoID=1 Waiting->Runnable Reason=""\n','Stack=\n',' target @ 0x1\n'],
                ['M=1 P=0 G=1 StateTransition Time=103 GoID=1 Runnable->Running Reason=""\n']]
        ledger=['RESEARCH_TIME raw=10 decoded=100 kind=StateTransition',
                'RESEARCH_TIME raw=12 decoded=101 kind=StateTransition',
                'RESEARCH_TIME raw=20 decoded=102 kind=StateTransition',
                'RESEARCH_TIME raw=30 decoded=103 kind=StateTransition']
        result,changes,dropped=audit.restore(blocks,ledger)
        self.assertEqual([r[0] for r in result],[10,20,30])
        self.assertEqual(dropped,{'same_state_census':1})
        self.assertEqual(len(changes),4)
        self.assertEqual(result[1][2][1:],blocks[2][1:])
        parsed=trace.parse_lines(line for row in result for line in row[2])
        trace.scheduler_series(parsed)
        self.assertEqual(parsed['transitions']['1'][-1][0],30)

    def test_missing_or_misaligned_audit_event_fails(self):
        block=[['M=1 P=0 G=1 StateTransition Time=20 GoID=1 Waiting->Runnable Reason=""\n']]
        for ledger in ([],['RESEARCH_TIME raw=10 decoded=21 kind=StateTransition'],
                       ['RESEARCH_TIME raw=10 decoded=20 kind=Log']):
            with self.assertRaises(ValueError):audit.restore(block,ledger)


class ProbeTests(unittest.TestCase):
    def test_only_observer_changes_between_balanced_arms(self):
        rows=probe.matrix(dict(images=dict(control='sha256:control',observed='sha256:observed')))
        self.assertEqual(len(rows),8)
        self.assertEqual(len({r['run_id'] for r in rows}),8)
        base=run.pilot_matrix()[0]
        changed={'run_id','rep','runtime_trace'}
        for r in rows:
            self.assertTrue(all(r[k]==v for k,v in base.items() if k not in changed))
            self.assertFalse(r['runtime_trace']);self.assertFalse(r['worker_yield']);self.assertTrue(r['custom_recording'])
        for block in range(1,5):self.assertEqual({r['probe_mode'] for r in rows if r['rep']==block},{'control','observed'})
        self.assertEqual([r['probe_mode'] for r in rows[::2]],['control','observed','observed','control'])

    def test_runtime_policy_is_identical_except_observer_constant(self):
        source=(run.ROOT/'analysis/runtime_io_v9_candidate/prepared/proc.go').read_text()
        control=build.runtime_source(source,False)
        observed=build.runtime_source(source,True)
        self.assertEqual(control.replace('const researchObservePending = false','const researchObservePending = true'),observed)
        self.assertIn('preemptRequested := pp.preempt',observed)
        self.assertIn('forceFair := preemptRequested',observed)

    def test_wrong_source_refused(self):
        with self.assertRaises(ValueError):build.runtime_source('unexpected source',True)

    def test_counter_mode_schema_and_disabled_zero_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);server=dict(scheduler_observation_enabled=False,
                scheduler_counters={n:0 for n in build.NAMES},
                scheduler_counter_window='reset_to_snapshot_including_control_and_drain')
            run.put(p/'server_metrics.json',server)
            probe.validate_counters(p,dict(probe_mode='control'))
            with self.assertRaisesRegex(ValueError,'mode'):probe.validate_counters(p,dict(probe_mode='observed'))
            server['scheduler_counters']['pending_seen']=1;run.put(p/'server_metrics.json',server)
            with self.assertRaisesRegex(ValueError,'disabled'):probe.validate_counters(p,dict(probe_mode='control'))
            server['scheduler_observation_enabled']=True;server['scheduler_counters']['pending_seen']=-1
            run.put(p/'server_metrics.json',server)
            with self.assertRaisesRegex(ValueError,'schema'):probe.validate_counters(p,dict(probe_mode='observed'))

    def test_quiet_host_guard_prevents_launch(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(probe.pipeline,'is_running',return_value=False), \
             patch.object(run,'require_quiet_host',side_effect=RuntimeError('desktop app present')), \
             patch.object(probe.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(RuntimeError,'desktop'):probe.launch(Path(tmp))
            spawn.assert_not_called()

    def test_probe_cannot_be_used_as_standard_qualification_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);rows=probe.matrix(dict(images=dict(control='x',observed='y')))
            run.put(p/'matrix.json',rows)
            run.put(p/'metadata.json',dict(schema=run.SCHEMA,pending_probe=True,pilot=False,matrix_sha256=run.sha(p/'matrix.json')))
            with self.assertRaisesRegex(RuntimeError,'matrix'):run.require_pilot(p)

    def test_frozen_probe_bundle_validates_and_rejects_tampering_without_measurements(self):
        value=run.read(build.DEFAULT/'build.json')
        with tempfile.TemporaryDirectory() as tmp,patch.object(run,'require_quiet_host'), \
             patch.object(run.old,'check_topology',return_value={'fixture':True}), \
             patch.object(run,'capture',return_value='fixture'), \
             patch.object(run,'power_settings',return_value={'fixture':True}):
            p=Path(tmp)/'session';probe.create(p,value)
            self.assertTrue(probe.verify_session(p)['pending_probe'])
            frozen=p/'probe_build/control_runtime/proc.go'
            frozen.write_text(frozen.read_text()+'\n// altered\n')
            with self.assertRaisesRegex(ValueError,'frozen probe source'):probe.verify_session(p)


if __name__=='__main__':unittest.main()
