#!/usr/bin/env python3
"""Prepare a conditional local amendment package; never run Docker or traffic."""
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

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PROTOCOL=ROOT/'docs/runtime_io_slo_local_supplement_protocol_20261011.md'


def once(source,old,new):
    c.require(source.count(old)==1,'ambiguous supplement adaptation: '+old)
    return source.replace(old,new)


def seal(base,name):
    c.write(base/name,dict(files_sha256={str(p.relative_to(base)):c.sha(p)
        for p in sorted(base.rglob('*')) if p.is_file() and p!=base/name and
        'runs' not in p.relative_to(base).parts}),exclusive=False)


def build(parent,output):
    started=time.monotonic_ns();parent=parent.resolve();output=output.resolve()
    c.require(not output.exists(),'preserve existing supplement; no overwrite')
    c.require(parent.parent==output.parent and parent!=output,'keep original parent beside supplement')
    old=c.verify_package(parent);original=c.read(parent/'scientific/plan.json')
    c.require(old['host']['id']=='host01' and set(old['consumed_allocations'])=={'Go','NGINX'},
              'both original local allocations must be closed and preserved')
    attempts={}
    for app in old['host']['order']:
        origin=c.campaign_origin(parent,app);directory=origin/'runs/host01'/app
        c.require(not (directory/'calibration_provenance.json').exists(),'unexpected original calibration; re-review amendment')
        c.require(not list((directory/'decisions').glob('*_score.json')),'unexpected original targets; re-review amendment')
        attempts[app]=copy.deepcopy(old['consumed_allocations'][app])
        setup=origin/'runs/host01/setup/setup.json'
        c.require(setup.exists(),'original setup record missing')
        attempts[app]['setup_sha256']=c.sha(setup)
    shutil.copytree(parent,output,ignore=shutil.ignore_patterns('runs','__pycache__'))
    (output/'runtime_seal.json').unlink()
    (output/'scientific').rename(output/'original_scientific')
    shutil.copytree(output/'original_scientific',output/'scientific')
    (output/'scientific/seal.json').unlink()
    plan=copy.deepcopy(original)
    changed=['id','registered_utc','registration','role','host_preference','hosts','campaigns',
             'planned_target_windows','independent_hardware_hosts','primary','budget','eligibility']
    plan.update(id='slo-local-supplement-01',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        registration='conditional local pre-target sealed amendment; human execution acknowledgment required',
        role='separate fresh same-host evaluation after known apparatus failures; not independent hardware evidence',
        host_preference='host01 AMD; explicit amendment acceptance and allocation confirmation required',
        hosts=[copy.deepcopy(old['host'])],
        campaigns=[dict(id='slo_local_supplement01_host01_'+app,host='host01',application=app,
            planned_windows=18,scientific_attempt_limit=1,previous_v31_return_used=False)
            for app in ('Go','NGINX')],planned_target_windows=36,independent_hardware_hosts=1,
        eligibility='protocol.md plus unchanged v1 integrity/eligibility rules in original_scientific/protocol.md')
    plan['primary']['finite_window_hardware_recurrence']='supplemental host01 event is fresh same-host recurrence only'
    plan['budget']['total_cap_sec']=15300
    plan['amendment']=dict(parent_study_id=original['id'],parent_plan_sha256=c.sha(parent/'scientific/plan.json'),
        parent_planned_windows=72,changed_plan_fields=changed,supplemental_planned_windows=36,
        combined_attempt_ledger_slots=108,additional_campaign_cap_sec=15300,combined_planned_cap_sec=45900,
        known_original_preparation_offers=510,known_original_nginx_client_offers=0,
        known_original_calibration_or_target_outcomes=False,original_closed_attempts=attempts,
        original_results_replaced=False,primary_results_pooled=False,
        execution_acknowledgment_required=True,execution_approved_by_preparation=False)
    c.write(output/'scientific/plan.json',plan,exclusive=False)
    shutil.copy2(PROTOCOL,output/'scientific/protocol.md')
    c.write(output/'scientific/input_sha256.json',dict(parent_package_seal_sha256=c.sha(parent/'runtime_seal.json'),
        parent_plan_sha256=c.sha(parent/'scientific/plan.json'),amendment_protocol_sha256=c.sha(PROTOCOL)),exclusive=False)
    changes=[]
    def adapt(name,source):
        path=output/name;previous=path.read_text();ast.parse(source)
        path.write_text(source)
        changes.append(''.join(difflib.unified_diff(previous.splitlines(True),source.splitlines(True),
            fromfile='v6/'+name,tofile='supplement/'+name)))
    for name in ('local_supplement.py','test_local_supplement.py','prelaunch_local_supplement.py'):
        shutil.copy2(HERE/name,output/'runtime'/name)
    shutil.copy2(HERE/'start_local_supplement.sh',output/'start_local_supplement.sh')
    source=(output/'runtime/setup.py').read_text()
    source=once(source,'def setup(root):','def setup(root,amendment_accepted=False):\n    from local_supplement import accept\n    accept(root,amendment_accepted)')
    source=once(source,"args=p.parse_args()","p.add_argument('--amendment-accepted',action='store_true');args=p.parse_args()")
    source=once(source,'else:setup(ROOT)','else:setup(ROOT,args.amendment_accepted)')
    adapt('runtime/setup.py',source)
    source=(output/'runtime/supervisor.py').read_text()
    source=once(source,'def run(root,app,allocation_confirmed=False):',
        'def run(root,app,allocation_confirmed=False,amendment_accepted=False):\n    from local_supplement import accept\n    accept(root,amendment_accepted)')
    source=once(source,'def close_unavailable(root,app,reason,allocation_confirmed=False):',
        'def close_unavailable(root,app,reason,allocation_confirmed=False,amendment_accepted=False):\n    from local_supplement import accept\n    accept(root,amendment_accepted)')
    guard="""    if 'local_supplement' in package:
        receipt=Path(root)/'runs'/host/'amendment_acceptance.json'
        c.require(receipt.exists(),'amendment acceptance must precede campaign admission')
        accepted=c.read(receipt)
        c.require(accepted.get('accepted') is True and accepted.get('plan_sha256')==c.sha(Path(root)/'scientific/plan.json')
                  and accepted.get('package_seal_sha256')==c.sha(Path(root)/'runtime_seal.json'),
                  'amendment acceptance identity differs')
"""
    source=once(source,"    value=allocation(plan,host,app)\n",guard+"    value=allocation(plan,host,app)\n")
    source=once(source,"p.add_argument('--allocation-confirmed',action='store_true');args=p.parse_args()",
        "p.add_argument('--allocation-confirmed',action='store_true');p.add_argument('--amendment-accepted',action='store_true');args=p.parse_args()")
    source=once(source,'close_unavailable(root,args.application,args.reason,args.allocation_confirmed)',
        'close_unavailable(root,args.application,args.reason,args.allocation_confirmed,args.amendment_accepted)')
    source=once(source,'else:run(root,args.application,args.allocation_confirmed)',
        'else:run(root,args.application,args.allocation_confirmed,args.amendment_accepted)')
    adapt('runtime/supervisor.py',source)
    source=(output/'slo/report.py').read_text()
    source=once(source,'    return dict(planned_windows=72,windows=all_windows,tables=output,',
        "    e.require(len(all_windows)==plan['planned_target_windows'],'planned window denominator differs')\n    return dict(planned_windows=plan['planned_target_windows'],windows=all_windows,tables=output,")
    adapt('slo/report.py',source)
    source=(output/'runtime/assemble_returns.py').read_text()
    source=once(source,"r.require(len(roots)==2,'the two frozen host packages are required')",
        "r.require(len(roots) in (1,2),'declared study host package count required')")
    source=once(source,"r.require(set(hosts)=={'host01','host02'} and bound==30600 and len(closed)==4,'fixed study allocation inventory differs')",
        "r.require(set(hosts)=={x['host'] for x in plan['campaigns']} and bound==plan['budget']['total_cap_sec'] and len(closed)==len(plan['campaigns']),'fixed study allocation inventory differs')")
    source=once(source,'\n    return result\n',"""
    result['study_id']=plan['id']
    result['primary_results_pooled_with_parent']=False
    if plan.get('amendment'):
        result['interpretation']='fresh same-host supplemental evaluation; no independent hardware claim'
        for root in map(Path,roots):
            if r.verify_package(root).get('local_supplement'):
                from local_supplement import original_ledger
                result['preserved_original_attempt_ledger']=original_ledger(root)
    return result
""")
    adapt('runtime/assemble_returns.py',source)
    source=(output/'runtime/test_runtime.py').read_text()
    source=once(source,"self.plan=r.read(ROOT/'scientific/plan.json')","self.plan=r.read(ROOT/'original_scientific/plan.json')")
    source=once(source,"self.package.pop('consumed_allocations',None)","self.package.pop('local_supplement',None)\n        self.package.pop('consumed_allocations',None)")
    source=once(source,"r.read(ROOT/'scientific/plan.json')['hosts'] if x['id']=='host02'",
        "r.read(ROOT/'original_scientific/plan.json')['hosts'] if x['id']=='host02'")
    adapt('runtime/test_runtime.py',source)
    package=copy.deepcopy(old);package['consumed_allocations']={}
    package.update(scientific_plan_sha256=c.sha(output/'scientific/plan.json'),all_outcomes_unrun=True,
        local_supplement=dict(relative_parent_package='../'+parent.name,parent_package_seal_sha256=c.sha(parent/'runtime_seal.json'),
            parent_scientific_plan_sha256=old['scientific_plan_sha256'],original_closed_attempts=attempts,
            amendment_acceptance_required=True,original_results_replaced=False),
        collection_authorized=False,runtime_qualified=False,new_campaigns_unrun=True)
    seal(output/'scientific','seal.json')
    package['scientific_seal_sha256']=c.sha(output/'scientific/seal.json')
    c.write(output/'runtime_package.json',package,exclusive=False)
    (output/'supplement_adaptations.patch').write_text(''.join(changes))
    (output/'README.md').write_text("# Separate AMD local SLO supplement 01\n\nRead scientific/protocol.md before execution. Explicit --amendment-accepted\nis required for setup and each campaign. New order: Go then NGINX.\nSetup once before Go; do not repeat setup before NGINX. Original v1 attempts\nremain closed. Keep sibling original v3, v4 and v6 packages and all runs evidence.\nNo collection has been started by preparation.\n\nOffline verification:\n\n```bash\npython3 -B runtime/setup.py verify-package\npython3 -B -m unittest discover -s runtime -p 'test*.py' -v\n```\n\nAfter both supplemental allocations are closed, assemble this one package\nwith runtime/assemble_returns.py --host-package /absolute/path/to/this-package\n--output /absolute/path/to/new-supplement-report.json. The report has 36 slots\nand retains the original attempt costs in a separate ledger.\n")
    c.write(output/'supplement_build_receipt.json',dict(registered_utc=plan['registered_utc'],
        source_builder_sha256=c.sha(Path(__file__)),parent_package_seal_sha256=c.sha(parent/'runtime_seal.json'),
        protocol_sha256=c.sha(PROTOCOL),engineering_elapsed_sec=(time.monotonic_ns()-started)/1e9,
        source_changes=changed,no_docker_commands=True,no_traffic=True,no_hardware_probes=True,
        execution_acknowledgment_required=True,inherited_compiled_exports=69))
    syntax=subprocess.run(['bash','-n',str(output/'start_local_supplement.sh')],capture_output=True,text=True)
    c.require(syntax.returncode==0,syntax.stderr)
    seal(output,'runtime_seal.json')
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','runtime','-p','test*.py','-v'],
        cwd=output,capture_output=True,text=True,timeout=90)
    (output/'supplement_tests.stdout').write_text(tests.stdout)
    (output/'supplement_tests.stderr').write_text(tests.stderr)
    c.require(tests.returncode==0,'supplement checks failed; preserve rejected package:\n'+tests.stderr)
    seal(output,'runtime_seal.json');c.verify_package(output)
    check=subprocess.run([sys.executable,'-B',str(output/'runtime/setup.py'),'verify-package'],
        cwd=output,capture_output=True,text=True,timeout=20)
    c.require(check.returncode==0,check.stderr)
    print(dict(package=str(output),plan_sha256=c.sha(output/'scientific/plan.json'),
        runtime_seal_sha256=c.sha(output/'runtime_seal.json'),no_collection_started=True,
        execution_requires_amendment_accepted=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent',type=Path,default=ROOT/'handoff/slo-host01-20261011-runtime-v6')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.parent,args.output)
