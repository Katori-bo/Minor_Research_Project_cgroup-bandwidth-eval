#!/usr/bin/env python3
"""Seal a distinct NGINX-only amendment without native probes or client traffic."""
import argparse
import ast
import copy
import datetime
import difflib
from pathlib import Path
import shutil
import subprocess
import sys
import time
import common as c
from build_local_supplement import once,seal

ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent


def build(parent,output):
    started=time.monotonic_ns();parent=parent.resolve();output=output.resolve()
    c.require(not output.exists(),'preserve existing amendment package; no overwrite')
    c.require(parent.parent==output.parent and parent!=output,'keep prior packages beside completion')
    old=c.verify_package(parent);previous=c.read(parent/'scientific/plan.json')
    c.require(previous['id']=='slo-local-supplement-01','unexpected prior study')
    sys.path[:0]=[str(parent/p) for p in ('runtime','diagnostic','scripts','analysis','slo')]
    from assemble_returns import verify_return
    from local_supplement import original_ledger
    original_ledger(parent)
    returns={}
    for app in ('Go','NGINX'):
        directory=parent/'runs/host01'/app;verify_return(directory,parent)
        finish=c.read(directory/'supervisor_finished.json')
        c.require(finish['allocation_closed'],'prior allocation remains open')
        c.require(len(list((directory/'decisions').glob('*_score.json')))==(18 if app=='Go' else 0),
                  'prior outcome inventory changed')
        returns[app]=c.sha(directory/'return_seal.json')
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('runs','__pycache__'))
    (output/'runtime_seal.json').unlink();(output/'scientific').rename(output/'prior_supplement_scientific')
    shutil.copytree(output/'prior_supplement_scientific',output/'scientific');(output/'scientific/seal.json').unlink()
    for path in ('runtime/test_local_supplement.py','start_local_supplement.sh'):(output/path).unlink()
    known=output/'known_prior';known.mkdir()
    for source,target in (
        ('analysis/runtime_io_slo_independent/local-supplement01-return.json','return.json'),
        ('analysis/runtime_io_slo_independent/20261011-local-supplement01-raw-replay.json','raw_replay.json'),
        ('docs/runtime_io_slo_local_supplement_result_20261011.md','result.md')):
        shutil.copy2(ROOT/source,known/target)
    plan=copy.deepcopy(previous);host=copy.deepcopy(old['host']);host['order']=['NGINX']
    plan.update(id='slo-nginx-completion-01',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        registration='NGINX-only local amendment frozen before new outcomes; known Go outcomes disclosed',
        role='separate same-host NGINX evaluation after authentication failure',hosts=[host],
        host_preference='host01 AMD; NGINX-only; external human allocation confirmed',
        campaigns=[dict(id='slo_nginx_completion01_host01_NGINX',application='NGINX',host='host01',
                        planned_windows=18,scientific_attempt_limit=1,previous_v31_return_used=False)],
        planned_target_windows=18)
    plan['budget']['total_cap_sec']=2700
    plan['primary']['finite_window_hardware_recurrence']='NGINX completion on host01 is fresh same-host evidence only'
    plan['amendment']=dict(parent_study_id=previous['id'],parent_plan_sha256=c.sha(parent/'scientific/plan.json'),
        parent_planned_windows=36,supplemental_planned_windows=18,combined_attempt_ledger_slots=126,
        additional_campaign_cap_sec=2700,combined_planned_cap_sec=48600,
        changed_plan_fields=['id','registered_utc','registration','role','hosts','host_preference','campaigns',
                             'planned_target_windows','budget','primary'],
        known_Go_target_windows=18,known_Go_primary_events=1,known_NGINX_client_offers=0,
        known_Go_report_sha256=c.sha(known/'return.json'),original_results_replaced=False,
        primary_results_pooled=False,execution_acknowledgment_required=True)
    c.write(output/'scientific/plan.json',plan,exclusive=False)
    protocol=ROOT/'docs/runtime_io_slo_nginx_completion_protocol_20261011.md'
    shutil.copy2(protocol,output/'scientific/protocol.md')
    c.write(output/'scientific/input_sha256.json',dict(parent_package_seal_sha256=c.sha(parent/'runtime_seal.json'),
        parent_plan_sha256=c.sha(parent/'scientific/plan.json'),protocol_sha256=c.sha(protocol),
        known_prior_report_sha256=c.sha(known/'return.json'),known_prior_raw_replay_sha256=c.sha(known/'raw_replay.json')),
        exclusive=False)
    patches=[]
    def adapt(name,source):
        path=output/name;before=path.read_text();ast.parse(source);path.write_text(source)
        patches.append(''.join(difflib.unified_diff(before.splitlines(True),source.splitlines(True),
            fromfile='prior/'+name,tofile='completion/'+name)))
    shutil.copy2(HERE/'nginx_completion.py',output/'runtime/nginx_completion.py')
    (output/'runtime/local_supplement.py').write_text('"""NGINX-only amendment compatibility hooks."""\nfrom nginx_completion import accept, original_ledger, prelaunch\n')
    shutil.copy2(HERE/'start_nginx_completion.sh',output/'start_nginx_completion.sh')
    source=(output/'runtime/setup.py').read_text()
    start=source.index("        go=c.read(Path(root)/'assets/retained_identity.json')")
    end=source.index("        archive=Path(root)/'assets/nginx/runtime.tar'",start)
    source=source[:start]+source[end:]
    source=once(source,"package_seal_sha256=c.sha(Path(root)/'runtime_seal.json'),go_image=go['image'],",
                "package_seal_sha256=c.sha(Path(root)/'runtime_seal.json'),applications=['NGINX'],")
    adapt('runtime/setup.py',source)
    source=(output/'runtime/common.py').read_text()
    source=once(source,"for app,key in [('Go','go_image'),('NGINX','nginx_image')]:",
                "for app,key in [('Go','go_image'),('NGINX','nginx_image')]:\n        if app not in verify_package(root)['host']['order']:continue")
    adapt('runtime/common.py',source)
    source=(output/'runtime/supervisor.py').read_text()
    source=once(source,"    value=allocation(plan,host,app)\n", """    if package.get('nginx_completion'):
        c.require(app=='NGINX','NGINX-only amendment; Go cannot be repeated')
        from nginx_completion import readiness
        readiness(root)
    value=allocation(plan,host,app)
""")
    source=once(source,"invoke(directory,['sudo',sys.executable", "invoke(directory,['sudo','-n',sys.executable")
    source=once(source,"    host=package['host']['id'];lockpath=", "    if package.get('nginx_completion'):\n        subprocess.run(['sudo','-n','-v'],check=True,timeout=10)\n    host=package['host']['id'];lockpath=")
    adapt('runtime/supervisor.py',source)
    source=(output/'runtime/test_runtime.py').read_text()
    source=once(source,"self.package.pop('local_supplement',None)",
                "self.package['host']=next(h for h in self.plan['hosts'] if h['id']=='host01')\n        self.package.pop('nginx_completion',None)\n        self.package.pop('local_supplement',None)")
    source=once(source,"with patch.object(sys,'argv',argv[3:]):audit.main()", "with patch.object(sys,'argv',argv[4:]):audit.main()")
    source=source.replace("r.read(ROOT/'scientific/plan.json'),host,'Go'", "r.read(ROOT/'original_scientific/plan.json'),host,'Go'")
    source=once(source,"r.write(root/'scientific/plan.json',r.read(ROOT/'scientific/plan.json'))",
                "r.write(root/'scientific/plan.json',r.read(ROOT/'original_scientific/plan.json'))")
    source=once(source,"alloc=s.allocation(r.read(ROOT/'original_scientific/plan.json'),host,'Go')","alloc=s.allocation(r.read(ROOT/'original_scientific/plan.json'),host,'Go')\n            package['host']=alloc['host']")
    adapt('runtime/test_runtime.py',source)
    shutil.copy2(HERE/'test_nginx_completion.py',output/'runtime/test_nginx_completion.py')
    source=(ROOT/'replication/slo_decision/test_evaluation.py').read_text()
    source=source.replace('import evaluation as e',"import sys\nROOT=Path(__file__).resolve().parents[1]\nsys.path[:0]=[str(ROOT/'slo'),str(ROOT/'original_scientific')]\nimport evaluation as e")
    (output/'runtime/test_evaluator.py').write_text(source)
    package=copy.deepcopy(old);package.update(host=host,nginx_completion=True,
        local_supplement=dict(relative_parent_package='../'+parent.name,
            parent_package_seal_sha256=c.sha(parent/'runtime_seal.json'),
            parent_scientific_plan_sha256=c.sha(parent/'scientific/plan.json'),prior_returns=returns,
            prior_acceptance_sha256=c.sha(parent/'runs/host01/amendment_acceptance.json'),
            prior_setup_sha256=c.sha(parent/'runs/host01/setup/setup.json')),
        scientific_plan_sha256=c.sha(output/'scientific/plan.json'),new_campaigns_unrun=True,
        all_outcomes_unrun=True,collection_authorized=False,runtime_qualified=False)
    seal(output/'scientific','seal.json');package['scientific_seal_sha256']=c.sha(output/'scientific/seal.json')
    c.write(output/'runtime_package.json',package,exclusive=False)
    (output/'nginx_completion_adaptations.patch').write_text(''.join(patches))
    (output/'README.md').write_text('# NGINX-only local completion amendment 01\n\nRead scientific/protocol.md. All prior sibling packages must remain intact.\nNo traffic has started. From an external interactive terminal run:\n\n```bash\nbash start_nginx_completion.sh --amendment-accepted --allocation-confirmed\n```\n\nThe command closes Codex/background apps, imports only NGINX, asks for sudo,\nchecks the real privileged audit before admission, and runs one bounded campaign.\nIts final report is runs/host01/final_report.json. Never retry this package.\n')
    c.write(output/'nginx_completion_build_receipt.json',dict(registered_utc=plan['registered_utc'],
        builder_sha256=c.sha(Path(__file__)),protocol_sha256=c.sha(protocol),
        parent_package_seal_sha256=c.sha(parent/'runtime_seal.json'),engineering_elapsed_sec=(time.monotonic_ns()-started)/1e9,
        no_traffic=True,no_native_probes=True,inherited_compiled_exports=69))
    shell=subprocess.run(['bash','-n',str(output/'start_nginx_completion.sh')],capture_output=True,text=True)
    c.require(shell.returncode==0,shell.stderr);seal(output,'runtime_seal.json')
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','runtime','-p','test*.py','-v'],
        cwd=output,capture_output=True,text=True,timeout=90)
    (output/'nginx_completion_tests.stdout').write_text(tests.stdout)
    (output/'nginx_completion_tests.stderr').write_text(tests.stderr)
    c.require(tests.returncode==0,'offline verification failed; preserve rejected package:\n'+tests.stderr)
    seal(output,'runtime_seal.json');c.verify_package(output)
    print(dict(package=str(output),plan_sha256=c.sha(output/'scientific/plan.json'),
        runtime_seal_sha256=c.sha(output/'runtime_seal.json'),no_collection_started=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent',type=Path,default=ROOT/'handoff/slo-host01-20261011-local-supplement-03')
    p.add_argument('--output',type=Path,required=True);args=p.parse_args();build(args.parent,args.output)
