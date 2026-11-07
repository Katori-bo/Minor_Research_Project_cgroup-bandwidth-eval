"""Synthetic tests: authentication gates, immutable scope and full NGINX runner."""
import copy
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
import common as c
import nginx_completion as amendment
import supervisor as s
import worker
import report
import collectors as a
import nginx_backend
import nginx_prediction_common as nc
import nginx_prediction_model as model
import assemble_returns


class Completion(unittest.TestCase):
    def setUp(self):
        self.plan=c.read(ROOT/'scientific/plan.json');self.package=c.verify_package(ROOT)

    def test_science_inherited_and_only_nginx(self):
        old=c.read(ROOT/'prior_supplement_scientific/plan.json')
        for key in old:
            if key not in self.plan['amendment']['changed_plan_fields']+['amendment']:
                self.assertEqual(old[key],self.plan[key],key)
        self.assertEqual(self.plan['NGINX'],old['NGINX'])
        self.assertEqual(self.plan['barrier'],old['barrier'])
        self.assertEqual(self.plan['budget']['nginx'],old['budget']['nginx'])
        self.assertEqual(self.package['host']['order'],['NGINX'])
        self.assertEqual(len(self.plan['campaigns']),1)
        self.assertEqual(self.plan['budget']['total_cap_sec'],2700)

    def test_prior_returns_and_known_outcomes_preserved(self):
        ledger=amendment.original_ledger(ROOT)
        rows=ledger['prior_supplement_allocations']
        self.assertEqual([x['completed_target_windows'] for x in rows],[18,0])
        self.assertEqual(sum(x['declared_offers'] for x in rows[0]['acquired_raw_offers']),29932)
        self.assertEqual(rows[1]['acquired_raw_offers'],[])
        self.assertEqual(ledger['combined_attempt_ledger_slots'],126)
        self.assertFalse(ledger['primary_results_pooled'])

    def test_prelaunch_read_only_and_refuses_go(self):
        before=list((ROOT/'runs').rglob('*'))
        amendment.prelaunch(ROOT,'NGINX',True,True)
        with self.assertRaisesRegex(ValueError,'NGINX-only'):amendment.prelaunch(ROOT,'Go',True,True)
        with self.assertRaisesRegex(ValueError,'amendment-accepted'):amendment.prelaunch(ROOT,'NGINX',False,True)
        self.assertEqual(before,list((ROOT/'runs').rglob('*')))

    def test_admission_without_precheck_cannot_consume_campaign(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);c.write(root/'scientific/plan.json',self.plan)
            c.write(root/'runtime_seal.json',dict(synthetic=True))
            receipt=dict(accepted=True,plan_sha256=c.sha(root/'scientific/plan.json'),
                         package_seal_sha256=c.sha(root/'runtime_seal.json'))
            c.write(root/'runs/host01/amendment_acceptance.json',receipt)
            with patch.object(c,'verify_package',return_value=self.package):
                with self.assertRaisesRegex(ValueError,'privileged precheck'):s.admit(root,'NGINX',True)
                with self.assertRaisesRegex(ValueError,'NGINX-only'):s.admit(root,'Go',True)
            self.assertFalse((root/'runs/host01/NGINX').exists())

    def readiness_fixture(self,root,age=0,boot='boot'):
        c.write(root/'runtime_seal.json',dict(synthetic=True));c.write(root/'scientific/plan.json',self.plan)
        audit=root/'runs/host01/audits/NGINX_precheck.json';c.write(audit,dict(synthetic=True))
        value=dict(package_seal_sha256=c.sha(root/'runtime_seal.json'),plan_sha256=c.sha(root/'scientific/plan.json'),
                   boot_id=boot,finished_ns=100*10**9-age,audit_sha256=c.sha(audit),
                   review=dict(performance_eligible=True))
        c.write(root/'runs/host01/auth_precheck/success.json',value);return value

    def test_freshness_boot_and_mutation_are_admission_guards(self):
        import leftover_observer_review as review
        for mode in ('good','stale','boot','mutated','failed'):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);value=self.readiness_fixture(root,age=61*10**9 if mode=='stale' else 0,
                                                          boot='wrong' if mode=='boot' else 'boot')
                if mode=='mutated':(root/'runs/host01/audits/NGINX_precheck.json').write_text('{}')
                if mode=='failed':c.write(root/'runs/host01/auth_precheck/failure.json',{})
                with patch.object(amendment.time,'monotonic_ns',return_value=100*10**9),\
                     patch.object(c,'identity',return_value=dict(boot_id='boot')),\
                     patch.object(review,'review',return_value=value['review']):
                    if mode=='good':self.assertEqual(amendment.readiness(root),value)
                    else:
                        with self.assertRaises(ValueError):amendment.readiness(root)

    def test_noninteractive_privileged_command_fails_promptly(self):
        argv=amendment.audit_command(ROOT,ROOT/'runs/host01/audits/synthetic.json')
        self.assertEqual(argv[:2],['sudo','-n'])
        self.assertIn("['sudo','-n',sys.executable",(ROOT/'runtime/supervisor.py').read_text())

    def test_missing_amendment_real_cli_creates_no_state(self):
        before=list((ROOT/'runs').rglob('*'))
        for args in (['runtime/setup.py','setup'],['runtime/nginx_completion.py','precheck'],
                     ['runtime/supervisor.py','run','--application','NGINX','--allocation-confirmed']):
            result=subprocess.run([sys.executable,'-B',str(ROOT/args[0])]+args[1:],
                                  cwd='/tmp',capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0);self.assertIn('amendment-accepted',result.stderr)
        self.assertEqual(before,list((ROOT/'runs').rglob('*')))

    def test_report_has_18_slots_and_undefined_risk_without_outcomes(self):
        value=report.report(self.plan,{})
        self.assertEqual((value['planned_windows'],len(value['windows'])),(18,18))
        self.assertFalse(value['independent_hardware_event_observed'])
        self.assertTrue(all(x['rates']['false_assurance_per_meets'] is None for x in value['tables']))


def raw(cfg,plan,warmup=False):
    count=cfg['warmup_count'] if warmup else cfg['count'];prefix='warmup' if warmup else 'measurement'
    interval=cfg['interval_ns']
    return dict(Schema='nginx-client-v1',Count=count,IntervalNs=interval,Rows=[dict(
        ID=f'{prefix}-{i}',EchoID=f'{prefix}-{i}',ScheduledNs=i*interval,DispatchNs=i*interval+10,
        HeadersNs=i*interval+20,BodyDoneNs=i*interval+50,Error='',DecodeError='',Status=200,
        ContentEncoding='gzip',ContentType='application/x-ndjson',DecodedBytes=1048576,
        DecodedSHA256=plan['NGINX']['input_sha256'],BodyBytes=100) for i in range(count)])


class NginxRunner(unittest.TestCase):
    def run_fixture(self,mode):
        plan=c.read(ROOT/'scientific/plan.json');package=c.verify_package(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);c.write(root/'scientific/plan.json',plan);c.write(root/'runtime_seal.json',{})
            directory=root/'runs/host01/NGINX';directory.mkdir(parents=True)
            alloc=s.allocation(plan,'host01','NGINX');c.write(directory/'allocation.json',alloc)
            c.write(directory/'lifetime.json',dict(started_ns=time.monotonic_ns(),boot_id=c.identity(os.getpid())['boot_id']))
            c.write(directory/'workers/collect.json',c.identity(os.getpid()));events=[];test=self
            class Backend:
                def __init__(self,root,directory):
                    self.directory=directory;self.reader=a.OfferReader('NGINX',dict(model=model))
                def configs(self,role):return nc.configs('pilot' if role=='qualification' else role)
                def begin(self,hook):self.hook=hook
                def case(self,cfg):return self.directory/'cases'/(cfg['role']+'_'+str(cfg['index']))
                def collect(self,cfg):
                    case=self.case(cfg);case.mkdir(parents=True);events.append(cfg['role'])
                    if cfg['role']=='validation':
                        self.hook.before_trial(case,cfg);c.write(case/'warmup.json',raw(cfg,plan,True))
                        self.hook.warmup_ready(case,cfg)
                        def create():
                            test.assertFalse((case/'measurement.json').exists())
                            c.write(case/'measurement.json',raw(cfg,plan))
                            return type('Child',(),dict(pid=991))()
                        self.hook.spawn(case,cfg,'measurement',create)
                    else:
                        c.write(case/'warmup.json',raw(cfg,plan,True));c.write(case/'measurement.json',raw(cfg,plan))
                    return dict(config=cfg,domain_exits=['synthetic_exit'] if mode=='adverse' and cfg['role']=='validation' else [])
                def reference(self,cohorts,plan):
                    test.assertEqual(len(cohorts),4)
                    if mode=='calibration_failure':raise ValueError('synthetic calibration failure')
                    return [50]*1600
                def target_values(self,case,cfg):return self.reader
            with patch.object(worker,'ROOT',root),patch.object(c,'verify_package',return_value=package),\
                 patch.object(c,'check_host',return_value={}),patch.object(os,'sched_setaffinity'),\
                 patch.object(signal,'signal'),patch.object(nginx_backend,'Backend',Backend):
                if mode=='complete':worker.run(directory,'collect')
                else:
                    with self.assertRaises(ValueError):worker.run(directory,'collect')
            return c.read(directory/'campaign_report.json'),events,c.read(directory/'acquisition_cost.json')

    def test_full_three_four_eighteen_runner_and_all_offers(self):
        result,events,cost=self.run_fixture('complete')
        self.assertEqual(events.count('pilot'),3);self.assertEqual(events.count('calibration'),4)
        self.assertEqual(events.count('validation'),18)
        self.assertTrue(all(x['status']=='primary_domain' for x in result['windows']))
        self.assertEqual(sum(x['declared_offers'] for x in cost['raw_acquisitions']),7925)
        self.assertFalse(result['independent_hardware_event_observed'])

    def test_calibration_failure_never_releases_target(self):
        result,events,_=self.run_fixture('calibration_failure')
        self.assertNotIn('validation',events);self.assertTrue(all(x['status']=='unavailable' for x in result['windows']))

    def test_adverse_first_target_is_retained_without_replacement(self):
        result,events,_=self.run_fixture('adverse')
        self.assertEqual(events.count('validation'),1)
        self.assertEqual([x['status'] for x in result['windows'][:2]],['applicability_exit','unavailable'])


if __name__=='__main__':unittest.main()

class PrecheckFailure(unittest.TestCase):
    def test_failed_actual_inventory_preserves_precheck_without_admission(self):
        import v31_common as go
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(amendment,'accept'),patch.object(amendment.sys.stdin,'isatty',return_value=True),\
                 patch.object(go,'require_desktop_absent'),patch.object(c,'check_host'),\
                 patch.object(c,'sha',return_value='sealed'),\
                 patch.object(amendment.subprocess,'run',side_effect=[None,subprocess.CalledProcessError(1,['sudo','-n'])]):
                with self.assertRaises(subprocess.CalledProcessError):amendment.precheck(root,True,True)
            self.assertTrue((root/'runs/host01/auth_precheck/failure.json').exists())
            self.assertFalse((root/'runs/host01/auth_precheck/success.json').exists())
            self.assertFalse((root/'runs/host01/NGINX').exists())

    def test_failed_authentication_never_invokes_inventory(self):
        import v31_common as go
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(amendment,'accept'),patch.object(amendment.sys.stdin,'isatty',return_value=True),\
                 patch.object(go,'require_desktop_absent'),patch.object(c,'check_host'),\
                 patch.object(c,'sha',return_value='sealed'),\
                 patch.object(amendment.subprocess,'run',side_effect=subprocess.TimeoutExpired(['sudo','-v'],300)) as run:
                with self.assertRaises(subprocess.TimeoutExpired):amendment.precheck(root,True,True)
            self.assertEqual(run.call_count,1)
            self.assertTrue((root/'runs/host01/auth_precheck/failure.json').exists())
            self.assertFalse((root/'runs/host01/NGINX').exists())

    def test_successful_precheck_uses_dedicated_new_audit_route(self):
        import v31_common as go
        import leftover_observer_review as review
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);boot=c.identity(os.getpid())['boot_id']
            def run(argv,**kwargs):
                if argv[:2]==['sudo','-n']:
                    self.assertEqual(Path(argv[-1]),root/'runs/host01/audits/NGINX_precheck.json')
                    c.write(Path(argv[-1]),dict(synthetic=True))
            with patch.object(amendment,'accept'),patch.object(amendment.sys.stdin,'isatty',return_value=True),\
                 patch.object(go,'require_desktop_absent'),patch.object(c,'check_host'),\
                 patch.object(c,'sha',return_value='sealed'),patch.object(amendment.subprocess,'run',side_effect=run),\
                 patch.object(review,'review',return_value=dict(performance_eligible=True,boot_id=boot)):
                amendment.precheck(root,True,True)
            value=c.read(root/'runs/host01/auth_precheck/success.json')
            self.assertTrue(value['no_traffic']);self.assertFalse(value['campaign_admitted'])
            self.assertFalse((root/'runs/host01/NGINX').exists())
            # The precheck is single use, even after success.
            with patch.object(amendment,'accept'),patch.object(amendment.sys.stdin,'isatty',return_value=True),\
                 patch.object(go,'require_desktop_absent'),patch.object(c,'check_host'):
                with self.assertRaises(FileExistsError):amendment.precheck(root,True,True)


class Launcher(unittest.TestCase):
    def fixture(self,mode):
        import pty
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);binpath=root/'bin';binpath.mkdir()
            script=root/'start_nginx_completion.sh';script.write_bytes((ROOT/'start_nginx_completion.sh').read_bytes())
            fake='''#!/usr/bin/env python3
import os, sys
from pathlib import Path
name=Path(sys.argv[0]).name
with open(os.environ['COMPLETION_TEST_LOG'],'a') as f:f.write(name+' '+repr(sys.argv[1:])+'\\n')
mode=os.environ['COMPLETION_TEST_MODE']
if name=='systemd-inhibit':os.execvp('bash',sys.argv[3:])
if name=='python3':
    args=sys.argv[1:]
    if 'runtime/nginx_completion.py' in args and mode=='precheck_failure':sys.exit(3)
    if 'runtime/supervisor.py' in args:
        p=Path('runs/host01/NGINX/return_seal.json');p.parent.mkdir(parents=True);p.write_text('{}')
        if mode=='campaign_failure':sys.exit(4)
sys.exit(0)
'''
            # Invoke the test interpreter by absolute path to avoid recursion in fake python3.
            fake=fake.replace('#!/usr/bin/env python3','#!'+sys.executable)
            for name in ('python3','systemd-inhibit','pkill','sleep'):
                path=binpath/name;path.write_text(fake);path.chmod(0o755)
            master,slave=pty.openpty()
            try:
                result=subprocess.run(['bash',str(script),'--amendment-accepted','--allocation-confirmed'],
                    stdin=slave,capture_output=True,text=True,timeout=10,
                    env=dict(os.environ,PATH=str(binpath)+':'+os.environ['PATH'],
                             COMPLETION_TEST_LOG=str(root/'log'),COMPLETION_TEST_MODE=mode))
            finally:os.close(master);os.close(slave)
            return result,(root/'log').read_text().splitlines()

    def test_complete_one_command_auth_gate_then_campaign_and_report(self):
        result,lines=self.fixture('complete');self.assertEqual(result.returncode,0,result.stderr)
        python=[x for x in lines if x.startswith('python3')]
        self.assertEqual(len(python),5)
        for index,name in enumerate(('prelaunch_local_supplement','setup','nginx_completion','supervisor','assemble_returns')):
            self.assertIn(name,python[index])
        self.assertFalse(any('--application Go' in line for line in lines))

    def test_failed_precheck_prevents_campaign_and_assembly(self):
        result,lines=self.fixture('precheck_failure');self.assertEqual(result.returncode,3)
        self.assertFalse(any('runtime/supervisor.py' in x and x.startswith('python3') for x in lines))
        self.assertFalse(any('runtime/assemble_returns.py' in x and x.startswith('python3') for x in lines))

    def test_closed_campaign_failure_still_assembles_and_returns_failure(self):
        result,lines=self.fixture('campaign_failure');self.assertEqual(result.returncode,4)
        self.assertTrue(any('runtime/assemble_returns.py' in x and x.startswith('python3') for x in lines))
