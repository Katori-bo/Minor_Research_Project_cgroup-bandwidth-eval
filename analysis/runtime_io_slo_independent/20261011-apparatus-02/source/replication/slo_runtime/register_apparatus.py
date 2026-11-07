#!/usr/bin/env python3
"""Register/replay the portable apparatus supplement without live host checks."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def inventory(base,omit):
    return {str(p.relative_to(base)):sha(p) for p in sorted(base.rglob('*')) if p.is_file() and p!=base/omit}
def require(value,message):
    if not value:raise ValueError(message)
def check_package(base):
    result=subprocess.run([sys.executable,'-B',str(base/'runtime/setup.py'),'verify-package'],
                          capture_output=True,text=True,timeout=60,cwd=base)
    require(result.returncode==0,result.stderr)
    package=read(base/'runtime_package.json')
    require(not package['runtime_qualified'] and not package['collection_authorized'],'unexpected hardware qualification')
    require('Ran 33 tests' in (base/'offline_tests.stderr').read_text() and
            (base/'offline_tests.stderr').read_text().rstrip().endswith('OK'),'portable offline checks did not pass')
    return package


def verify(output):
    seal=read(output/'apparatus_seal.json')
    require(inventory(output,'apparatus_seal.json')==seal['files_sha256'],'registered supplement changed')
    manifest=read(output/'apparatus.json')
    for name,h in manifest['repository_sources_sha256'].items():
        require(sha(ROOT/name)==h,'registered implementation changed: '+name)
    for name,h in manifest['predecessor_seals_sha256'].items():
        require(sha(ROOT/name)==h,'predecessor seal changed: '+name)
    for row in manifest['packages']:
        base=ROOT/row['path'];package=check_package(base)
        require(package['host']['id']==row['host'],'returned package host differs')
        require(sha(base/'runtime_seal.json')==row['seal_sha256'],'registered package seal changed')
        require(package['scientific_plan_sha256']==manifest['scientific_plan_sha256'],'scientific plan differs')
    print('Portable apparatus supplement verifies; hardware collection remains held.')


def register(output):
    require(not output.exists(),'preserve previous registration; no overwrite')
    predecessors=['analysis/runtime_io_slo_independent/20261011-v1-frozen/seal.json',
        'analysis/runtime_io_slo_independent/20261011-apparatus-01/apparatus_seal.json',
        'handoff/v31-host02-intel-20261011/package_seal.json']
    packages=[]
    for host in ('host01','host02'):
        base=ROOT/'handoff'/('slo-'+host+'-20261011-runtime-v2');value=check_package(base)
        packages.append(dict(host=host,path=str(base.relative_to(ROOT)),seal_sha256=sha(base/'runtime_seal.json'),
            scientific_plan_sha256=value['scientific_plan_sha256'],offline_checks=33,
            compiled_exports=read(base/'build_receipt.json')['compiled_exports']))
    require(len({x['scientific_plan_sha256'] for x in packages})==1,'host scientific plans differ')
    output.mkdir(parents=True)
    sources=list(HERE.glob('*.py'))+[HERE/'README.md',ROOT/'docs/runtime_io_slo_portable_runtime_20261011.md']
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(sources)}
    for path in sources:
        dest=output/'source'/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    for row in packages:
        base=ROOT/row['path'];dest=output/row['host'];dest.mkdir()
        for name in ('runtime_package.json','runtime_seal.json','build_receipt.json','offline_tests.stdout','offline_tests.stderr','adaptations.patch'):
            shutil.copy2(base/name,dest/name)
    save(output/'apparatus.json',dict(schema=2,registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        scope='portable runtime, single-attempt supervisor and returned-decision replay; offline engineering',
        scientific_plan_sha256=packages[0]['scientific_plan_sha256'],packages=packages,
        repository_sources_sha256=hashes,predecessor_seals_sha256={name:sha(ROOT/name) for name in predecessors},
        collector_adapters_unchanged=True,scientific_plan_unchanged=True,
        portable_dependency_closure_packaged=True,third_party_python_imports=[],
        external_campaign_supervisor_implemented=True,all_planned_windows=72,total_campaign_cap_sec=30600,
        hardware_collection_started=False,new_outcomes_acquired=False,collection_authorized=False,runtime_qualified=False,
        remaining=['explicit frozen host availability/allocation confirmation','external apparatus qualification before calibration/targets'],
        rejected_preparations_preserved=['handoff/slo-host01-20261011-v1','handoff/slo-host01-20261011-apparatus02']))
    save(output/'apparatus_seal.json',dict(files_sha256=inventory(output,'apparatus_seal.json')))
    verify(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['register','verify'])
    parser.add_argument('--output',type=Path,default=ROOT/'analysis/runtime_io_slo_independent/20261011-apparatus-02')
    args=parser.parse_args();(register if args.command=='register' else verify)(args.output.resolve())
