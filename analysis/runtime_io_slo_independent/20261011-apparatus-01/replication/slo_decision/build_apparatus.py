#!/usr/bin/env python3
"""Seal and verify an offline collector integration supplement; never collect."""
import argparse
import ast
import datetime
import difflib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import collectors as a
import evaluation as e
import freeze_design as design

ROOT=Path(__file__).resolve().parents[2]
FROZEN=ROOT/'analysis/runtime_io_slo_independent/20261011-v1-frozen'
SOURCE=ROOT/'replication/slo_decision'
PREDECESSORS=['diagnostic/v31_study.py','diagnostic/v31_common.py',
    'diagnostic/nginx_prediction_study.py','diagnostic/nginx_prediction_common.py',
    'diagnostic/nginx_prediction_model.py','diagnostic/nginx_qualify.py']
CODE=['evaluation.py','freeze_design.py','collectors.py','report.py',
      'test_evaluation.py','test_collectors.py','test_report.py','build_apparatus.py']


def closure():
    """Conservative static local-module inventory, including function-local imports."""
    search=[ROOT/p for p in ('diagnostic','scripts','analysis')]
    todo=[ROOT/p for p in PREDECESSORS];seen=set();external=set()
    while todo:
        path=todo.pop()
        if path in seen:continue
        seen.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                top=name.split('.')[0]
                found=next((p/(top+'.py') for p in search if (p/(top+'.py')).exists()),None)
                if found:todo.append(found)
                elif top not in sys.stdlib_module_names:external.add(top)
    return sorted(seen),sorted(external)


def verify(directory):
    directory=Path(directory)
    seal=a.read(directory/'apparatus_seal.json')
    files={str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p.name!='apparatus_seal.json'}
    e.require(files==set(seal['files_sha256']), 'apparatus file set changed')
    for name,h in seal['files_sha256'].items():
        e.require(a.sha(directory/name)==h,'apparatus hash changed: '+name)
    design.verify(FROZEN)
    for name,h in a.read(directory/'source_inputs.json').items():
        e.require(a.sha(ROOT/name)==h,'registered source input changed: '+name)
    return seal


def build(directory):
    e.require(not directory.exists(),'preserve apparatus supplement; no overwrite')
    design.verify(FROZEN)
    # Verify the independent V31 handoff inventory before and after this work.
    package=ROOT/'handoff/v31-host02-intel-20261011'
    prior=a.read(package/'package_seal.json')['files_sha256']
    def check_prior():
        for name,h in prior.items():e.require(a.sha(package/name)==h,'pending V31 package changed: '+name)
    check_prior()
    directory.mkdir(parents=True)
    for name in CODE:
        target=directory/'replication/slo_decision'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE/name,target)
    # Tests compile the actual retained validators/collectors without importing
    # heavyweight plotting modules or reading historical performance outcomes.
    for name in PREDECESSORS:
        target=directory/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,target)
    frozen_target=directory/'analysis/runtime_io_slo_independent/20261011-v1-frozen'
    shutil.copytree(FROZEN,frozen_target)
    adaptations={}
    for app,name in [('Go','diagnostic/v31_study.py'),('NGINX','diagnostic/nginx_prediction_study.py')]:
        original=(ROOT/name).read_text();adapted=a.adapt_source(original,app)
        target=directory/'adapted'/('go_collector.py' if app=='Go' else 'nginx_collector.py')
        target.parent.mkdir(exist_ok=True);target.write_text(adapted)
        patch=''.join(difflib.unified_diff(original.splitlines(True),adapted.splitlines(True),
            fromfile='retained/'+name,tofile='isolated/'+target.name))
        target.with_suffix('.patch').write_text(patch)
        adaptations[app]=dict(source_sha256=a.sha(ROOT/name),adapted_sha256=a.sha(target),
            collection_functions_only=True,historical_launchers_included=False,
            hardware_runtime_qualified=False)
    deps,external=closure()
    inputs={str(p.relative_to(ROOT)):a.sha(p) for p in deps}
    inputs.update({str((SOURCE/n).relative_to(ROOT)):a.sha(SOURCE/n) for n in CODE})
    inputs[str((FROZEN/'seal.json').relative_to(ROOT))]=a.sha(FROZEN/'seal.json')
    inputs[str((package/'package_seal.json').relative_to(ROOT))]=a.sha(package/'package_seal.json')
    a.save(directory/'source_inputs.json',inputs)
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','replication/slo_decision',
        '-p','test_*.py','-v'],cwd=directory,capture_output=True,text=True,timeout=60)
    (directory/'tests.stdout').write_text(tests.stdout);(directory/'tests.stderr').write_text(tests.stderr)
    e.require(tests.returncode==0,'isolated apparatus tests failed; preserve rejected preparation')
    check_prior()
    a.save(directory/'apparatus.json',dict(schema=1,scientific_plan_sha256=a.sha(FROZEN/'plan.json'),
        scientific_seal_sha256=a.sha(FROZEN/'seal.json'),adaptations=adaptations,
        evaluator_unchanged=a.sha(SOURCE/'evaluation.py')==a.sha(FROZEN/'evaluation.py'),
        test_result='39 synthetic checks passed',static_backend_source_files=len(deps),
        static_backend_external_imports=external,
        runtime_backend_dependency_closure_packaged=False,
        retained_backend_historical_boot_paths_rebound=False,
        external_campaign_supervisor_ported=False,
        report_fixed_windows=72,hardware_collection_started=False,new_outcomes_acquired=False,
        launch_ready=False,collection_authorized=False,pending_v31_inventory_files=len(prior),
        pending_v31_package_unchanged=True,
        remaining=['isolated portable runtime backend and fresh-baseline qualification entry point',
            'dedicated external campaign supervisor with hard cap and owner-safe cleanup',
            'host availability confirmation and runtime apparatus qualification before calibration'],
        scope='registered collection-function integration and report layer; no runnable scientific launcher'))
    doc=ROOT/'docs/runtime_io_slo_collector_integration_20261011.md'
    if doc.exists():shutil.copy2(doc,directory/'integration.md')
    a.save(directory/'apparatus_seal.json',dict(registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        local_registration_only=True,launch_ready=False,
        files_sha256={str(p.relative_to(directory)):a.sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}))
    verify(directory)
    print(json.dumps(dict(output=str(directory),synthetic_checks=39,launch_ready=False,
                         seal_sha256=a.sha(directory/'apparatus_seal.json')),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['build','verify']);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.command=='build':build(args.output.resolve())
    else:verify(args.output.resolve());print('Registered adapter supplement verifies; collection remains held.')
