from collections import Counter
from copy import deepcopy
import csv
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import build_loading as build
import loading_analysis as analysis
import loading_identity as identity
import loading_study as study
import run
from test_completion import fixture


def value():
    return dict(images=dict(legacy_packaged='original', legacy_shared='original',
        rebuilt_packaged='rebuilt', rebuilt_shared='rebuilt'), server_sha256='server', probe_sha256='probe')


def rows(packaged=.03, shared=0):
    levels=dict(legacy_packaged=.70, rebuilt_packaged=.70+packaged,
        legacy_shared=.72, rebuilt_shared=.72+shared)
    return [dict(rep=b, recorder_arm=a, timely_500_fraction=levels[a], timely_1000_fraction=.99,
        failure_fraction=0, cpu_usec_per_completed_work=4000, p99_e2e_ms=1000)
        for b in range(1, 5) for a in analysis.ARMS]


def evidence(mode='shared'):
    server=dict(sha256='server', device=1, inode=22, size=10, mode=33261, uid=1000, gid=1000)
    probe=dict(sha256='probe', device=1, inode=33, size=10, mode=33261, uid=1000, gid=1000)
    mounts=[dict(Type='bind', Source='/frozen', Destination='/qualification', RW=False, Propagation='rprivate')]
    if mode=='shared':mounts.append(dict(Type='bind', Source='/frozen/shared.server', Destination='/server', RW=False, Propagation='rprivate'))
    return dict(loading_mode=mode, image_id='image', expected_image_id='image', mounts=mounts,
        probe=dict(target_executable=server.copy(), probe_executable=probe.copy(), target_link='/server'),
        host_shared_identity=server, host_probe_identity=probe, collection='startup_before_warmup')


class LoadingTests(unittest.TestCase):
    def test_matrix_balances_position_relative_order_and_carryover(self):
        plan=study.matrix(value())
        self.assertEqual(len(plan),16)
        for a in analysis.ARMS:
            self.assertEqual(Counter(o.index(a) for o in study.ORDERS),Counter(range(4)))
            for b in analysis.ARMS:
                if a!=b:self.assertEqual(sum(o.index(a)<o.index(b) for o in study.ORDERS),2)
        transitions=Counter(pair for order in study.ORDERS for pair in zip(order,order[1:]))
        self.assertEqual(len(transitions),12);self.assertEqual(set(transitions.values()),{1})
        excluded={'run_id','rep','recorder_arm','service_image','loading_mode'}
        self.assertEqual(len({tuple((k,v) for k,v in r.items() if k not in excluded) for r in plan}),1)
        bad=value();bad['images']['legacy_shared']='different'
        with self.assertRaises(ValueError):study.matrix(bad)

    def test_shared_file_uses_same_readonly_path_and_packaged_has_no_server_mount(self):
        a=identity.mount_arguments(Path('/frozen'),'packaged')
        b=identity.mount_arguments(Path('/frozen'),'shared')
        self.assertEqual(b[:len(a)],a)
        self.assertNotIn('dst=/server',str(a))
        self.assertIn('src=/frozen/shared.server,dst=/server,readonly',b[-1])

    def test_running_executable_identity_and_mount_validation(self):
        for mode in ('shared','packaged'):
            identity.validate(evidence(mode),mode,Path('/frozen'),'server','probe')
        for mutation in ('writable','source','inode','server_hash','probe_hash','missing_mount','extra_mount'):
            e=evidence()
            if mutation=='writable':e['mounts'][0]['RW']=True
            elif mutation=='source':e['mounts'][1]['Source']='/other/server'
            elif mutation=='inode':e['probe']['target_executable']['inode']=999
            elif mutation=='server_hash':e['probe']['target_executable']['sha256']='wrong'
            elif mutation=='probe_hash':e['probe']['probe_executable']['sha256']='wrong'
            elif mutation=='missing_mount':e['mounts'].pop()
            else:e['mounts'].append(e['mounts'][0])
            with self.assertRaises(ValueError,msg=mutation):identity.validate(e,'shared',Path('/frozen'),'server','probe')

    def test_missing_packaged_gap_prevents_claim_of_removal(self):
        for gap in (0,-.03):
            result=analysis.compare(rows(packaged=gap))
            self.assertTrue(result['shared_image_within_screen'])
            self.assertFalse(result['packaged_v16_direction_reproduced'])
            self.assertEqual(result['decision'],'packaged_gap_not_reproduced_requires_review')

    def test_interaction_and_passing_shared_gap_do_not_qualify_recorder(self):
        result=analysis.compare(rows())
        self.assertEqual(result['decision'],'shared_file_gap_within_margins_requires_review')
        self.assertFalse(result['eligible_for_controls']);self.assertFalse(result['eligible_for_persistent_recording'])
        for pair in result['loading_interaction']['pairs']:
            self.assertAlmostEqual(pair['timely_fraction_delta'],-.03)
            self.assertEqual(pair['cpu_ratio'],1)

    def test_persisting_gap_and_failed_guardrails(self):
        result=analysis.compare(rows(shared=.02))
        self.assertEqual(result['decision'],'shared_file_did_not_establish_neutrality')
        for key,val in (('cpu_usec_per_completed_work',None),('p99_e2e_ms',float('nan'))):
            data=rows();data[3][key]=val
            self.assertFalse(analysis.compare(data)['shared_image_within_screen'])
        with self.assertRaises(ValueError):analysis.compare(rows()[:-1])

    def test_all_offered_outcomes_without_publication_or_runtime_observer(self):
        for arm in analysis.ARMS:
            result=analysis.classify(*fixture('legacy'),arm)
            self.assertEqual(result['deadlines']['500']['failure'],3)
            self.assertTrue(all(r['publish_start_lower_ns'] is None for r in result['requests']))
        c,s=fixture('legacy');s['runtime_capture']=True
        with self.assertRaises(ValueError):analysis.classify(c,s,analysis.ARMS[0])

    def test_wrapper_inserts_actual_mounts_records_startup_and_restores_globals(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);c=study.matrix(value(),Path('/frozen'))[0]
            originals=(run.capture,run.old.cgroup_path,run.drain)
            def inherited(s,config,number):
                args=['docker','create','--label',f'quota.diagnostic.session={s}',config['service_image']]
                self.assertEqual(run.capture(args),'container')
                self.assertIn('--mount',args)
                run.old.cgroup_path(123)
                self.assertTrue((s/'attempts'/config['run_id']/'001/file_loading.json').exists())
                raise ValueError('synthetic stop')
            with patch.object(run,'capture',return_value='container') as capture, patch.object(run.old,'cgroup_path',return_value='cgroup'), \
                    patch.object(identity,'collect',return_value=evidence('packaged')),patch.object(study.stock_study,'run_checked_attempt',side_effect=inherited):
                with self.assertRaisesRegex(ValueError,'synthetic stop'):study.run_loading_attempt(session,c,1)
                self.assertIs(run.capture,capture)
            self.assertEqual((run.capture,run.old.cgroup_path,run.drain),originals)

    def test_same_bytes_replacement_still_fails_current_identity_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp);assets=session/'loading_build/runtime_assets';assets.mkdir(parents=True)
            for n in ('shared.server','probe'):(assets/n).write_bytes(b'unchanged')
            run.put(session/'loading_assets_seal.json',{n:identity.identity(assets/n) for n in ('shared.server','probe')})
            meta=dict(loading_assets_seal_sha256=run.sha(session/'loading_assets_seal.json'))
            study.verify_assets(session,meta)
            replacement=assets/'replacement';replacement.write_bytes((assets/'shared.server').read_bytes())
            replacement.replace(assets/'shared.server')
            with self.assertRaisesRegex(ValueError,'identity changed'):study.verify_assets(session,meta)
            study.verify_assets(session,meta,current=False)

    def test_quiet_host_refuses_before_launch_and_progress_total(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(study.pipeline,'is_running',return_value=False), \
                patch.object(run,'require_quiet_host',side_effect=ValueError('desktop present')),patch.object(study.subprocess,'Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'desktop'):study.launch(Path(tmp))
            spawn.assert_not_called()
            snap=study.snapshot(Path(tmp));self.assertEqual((snap['total'],snap['remaining']),(16,16))

    def test_real_bundle_and_frozen_session_reject_probe_tamper(self):
        value=run.read(build.DEFAULT/'build.json')
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/'bundle';shutil.copytree(build.DEFAULT,bundle)
            with patch.object(run,'image_id',side_effect=lambda x:x):
                self.assertEqual(build.verify(bundle),value)
                (bundle/'runtime_assets/probe').write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'asset changed'):build.verify(bundle)
            session=Path(tmp)/'session'
            with patch.object(run,'require_quiet_host'),patch.object(study.stock_study,'time_offsets'), \
                    patch.object(run.old,'check_topology',return_value={}),patch.object(run,'capture',return_value='fixture'),patch.object(run,'power_settings',return_value={}):study.create(session,value)
            study.verify_session(session,current=False)
            (session/'loading_build/runtime_assets/probe').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'bundle changed'):study.verify_session(session,current=False)

    def test_real_startup_fixtures_match_common_inode_across_both_images(self):
        value=run.read(build.DEFAULT/'build.json');targets=[]
        for arm in analysis.ARMS:
            for g in (1,2):
                e=run.read(build.DEFAULT/f'fixture_{arm}_g{g}/file_loading.json')
                identity.validate(e,analysis.MODES[arm],build.DEFAULT/'runtime_assets',value['server_sha256'],value['probe_sha256'])
                if analysis.MODES[arm]=='shared':targets.append(e['probe']['target_executable'])
        self.assertTrue(all(t==targets[0] for t in targets))

    def test_real_http_fixtures_export_and_completed_analysis_tamper(self):
        value=run.read(build.DEFAULT/'build.json')
        fixtures={a:build.DEFAULT/f'fixture_{a}_g1' for a in analysis.ARMS}
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp);session=directory/'session';session.mkdir()
            run.put(session/'environment_seal.json',dict(fixture=True));run.put(session/'metadata.json',dict(build=value))
            run.put(session/'loading_assets_seal.json',dict(fixture=True))
            run.put(session/'matrix.json',study.matrix(value,session/'loading_build/runtime_assets'))
            def validated(p,c):return analysis.classify(run.read(fixtures[c['recorder_arm']]/'loadgen.json'),run.read(fixtures[c['recorder_arm']]/'server_metrics.json'),c['recorder_arm'])
            def trial_row(order,c,p):
                row=rows()[0].copy();row.update(order=order,run_id=c['run_id'],rep=c['rep'],recorder_arm=c['recorder_arm'])
                return row,{}
            for c in study.matrix(value,session/'loading_build/runtime_assets'):
                p=session/'attempts'/c['run_id']/'001';p.mkdir(parents=True)
                for name in ('loadgen.json','server_metrics.json'):shutil.copy2(fixtures[c['recorder_arm']]/name,p/name)
                run.put(p/'complete.json',dict(fixture=True))
            with patch.object(study,'verify_session',return_value={}),patch.object(study,'validate_attempt',side_effect=validated),patch.object(study.stock_analysis,'trial_row',side_effect=trial_row):
                study.analyze_results(directory);study.verify_completion(directory)
                out=session/'analysis'
                with (out/'requests.csv').open() as stream:
                    self.assertEqual(sum(r['deadline_ms']=='500' for r in csv.DictReader(stream)),96)
                self.assertFalse(run.read(out/'loading_screen.json')['eligible_for_controls'])
                (out/'report.md').write_text('changed')
                with self.assertRaisesRegex(ValueError,'analysis changed'):study.verify_completion(directory)


if __name__=='__main__':unittest.main()
