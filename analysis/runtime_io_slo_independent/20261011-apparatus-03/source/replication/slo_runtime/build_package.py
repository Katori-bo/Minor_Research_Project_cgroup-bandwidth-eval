#!/usr/bin/env python3
"""Build standalone host-specific SLO packages, without Docker or traffic."""
import argparse
import ast
import copy
import datetime
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import common as r

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
GO=ROOT/'handoff/v31-host02-intel-20261011'
FROZEN=ROOT/'analysis/runtime_io_slo_independent/20261011-v1-frozen'
PREVIOUS=ROOT/'analysis/runtime_io_slo_independent/20261011-apparatus-01'
NGINX=ROOT/'analysis/runtime_io_nginx_feasibility/generation-02/software'


def functions(source,names):
    tree=ast.parse(source);tree.body=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    r.require({n.name for n in tree.body}==set(names),'missing retained functions')
    return ast.unparse(tree)+'\n'


def replace_function(source,name,replacement):
    matches=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name]
    r.require(len(matches)==1,'ambiguous function adaptation: '+name)
    n=matches[0];lines=source.splitlines(keepends=True)
    return ''.join(lines[:n.lineno-1])+replacement.rstrip()+'\n'+''.join(lines[n.end_lineno:])


def once(source,old,new):
    r.require(source.count(old)==1,'ambiguous apparatus adaptation: '+old);return source.replace(old,new)


def seal(directory,filename='seal.json'):
    r.write(directory/filename,dict(files_sha256={str(p.relative_to(directory)):r.sha(p)
        for p in sorted(directory.rglob('*')) if p.is_file() and p!=directory/filename}),exclusive=False)


def build(output,host_id):
    started=time.monotonic_ns();r.require(not output.exists(),'preserve existing package')
    for base,filename in [(GO,'package_seal.json'),(FROZEN,'seal.json'),(PREVIOUS,'apparatus_seal.json')]:
        for name,h in r.read(base/filename)['files_sha256'].items():r.require(r.sha(base/name)==h,'predecessor changed: '+str(base/name))
    plan=r.read(FROZEN/'plan.json');host=next(x for x in plan['hosts'] if x['id']==host_id)
    output.mkdir(parents=True)
    for folder in ('diagnostic','scripts','analysis'):
        shutil.copytree(GO/folder,output/folder)
    fairness=output/'diagnostic/runtime_fairness';fairness.mkdir(exist_ok=True)
    for path in (ROOT/'diagnostic/runtime_fairness').glob('*.py'):shutil.copy2(path,fairness/path.name)
    shutil.copytree(GO/'assets',output/'assets')
    # Historical functional fixtures are not acquisition inputs for this study.
    # Retained client software build receipts remain explicitly software provenance.
    fixtures=output/'assets/software_fixtures'
    if fixtures.exists():shutil.rmtree(fixtures)
    shutil.copytree(FROZEN,output/'scientific')
    runtime=output/'runtime';runtime.mkdir()
    for path in HERE.glob('*.py'):
        if path.name!='build_package.py':shutil.copy2(path,runtime/path.name)
    slo=output/'slo';slo.mkdir()
    for name in ('collectors.py','evaluation.py','report.py'):shutil.copy2(PREVIOUS/'replication/slo_decision'/name,slo/name)
    shutil.copytree(PREVIOUS/'adapted',output/'adapted')
    assets=output/'assets/nginx';assets.mkdir()
    for name in ('runtime.tar','client','manifest.json','nginx-1.30.5.tar.gz'):
        shutil.copy2(NGINX/name,assets/name)
    changes={}
    def adapt(name,source):
        path=output/name;old=path.read_text() if path.exists() else ''
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
        ast.parse(source)
        changes[name]=''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='retained/'+name,tofile='portable/'+name))
    cpus=','.join(map(str,host['go_service_cpus']));cpu_list=repr(host['go_service_cpus']);cpu_set=repr(set(host['go_service_cpus']))
    common=(output/'diagnostic/v31_common.py').read_text()
    common=common.replace("PARENT = ROOT / 'runs/host02/study'",f"PARENT = ROOT / 'runs/{host_id}/Go'")
    common=common.replace("DESIGN = ROOT / 'assets/scientific_design'","DESIGN = ROOT / 'scientific/go'")
    common=common.replace('SERVER_CPUS = (2, 3)','SERVER_CPUS = '+repr(tuple(host['go_service_cpus'])))
    common=common.replace("'2,3'",repr(cpus))
    common=replace_function(common,'baseline',"def baseline():\n    import portable_platform\n    return portable_platform.baseline()")
    common=replace_function(common,'verify_package',"def verify_package():\n    import portable_platform\n    return portable_platform.verify_package()")
    common=replace_function(common,'design',"""def design():
    verify_seal(DESIGN)
    actual=read(DESIGN/'design.json')
    expected=read(ROOT/'scientific/retained_go_design.json')
    import portable_platform
    host=portable_platform.host()
    for cfg in expected['calibration_configs']+expected['validation_configs']:
        cfg['cpus']=host['go_service_cpus']
    if actual!=expected:raise ValueError('frozen Go contract changed beyond declared host CPU placement')
    return actual
""")
    common=replace_function(common,'source_hashes',"def source_hashes():\n    return {name:digest(ROOT/name) for name in read(ROOT/'runtime_package.json')['go_source_files']}")
    adapt('diagnostic/v31_common.py',common)
    platform_source="""from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
import common as r
def host():return r.read(ROOT/'runtime_package.json')['host']
def verify_package():return r.verify_package(ROOT)
def baseline():return r.baseline()
def check_topology():return r.placement(host(),r.topology(),__import__('os').sched_getaffinity(0))
def temperatures():return r.temperatures()
"""
    adapt('scripts/portable_platform.py',platform_source)
    adapt('scripts/host02_platform.py','from portable_platform import *\n')
    service=(output/'diagnostic/v31_service.py').read_text().replace("research.v31.host02.owner",'research.slo.'+host_id+'.Go.owner')
    service=service.replace('{2, 3}',cpu_set)
    needle='                start_new_session=True, preexec_fn=lambda: os.sched_setaffinity(0, {0, 1}))\n'
    service=once(service,needle,needle+"            c.save(self.directory/'watchdog_process.json',c.process_identity(self.watcher.pid))\n")
    adapt('diagnostic/v31_service.py',service)
    raw=(output/'diagnostic/v31_raw.py').read_text().replace('!= [2,3]','!= '+cpu_list)
    adapt('diagnostic/v31_raw.py',raw)
    bridge=(output/'diagnostic/kernel_service_bridge.py').read_text().replace('{2,3}',cpu_set).replace('affinity=[2,3]','affinity='+cpu_list)
    bridge=once(bridge,'def get(base, endpoint):','def _retained_get(base, endpoint):')
    bridge+='''\nHTTP_CALLS={}
def get(base,endpoint):
    key='GET '+endpoint
    HTTP_CALLS[key]=HTTP_CALLS.get(key,0)+1
    return _retained_get(base,endpoint)
'''
    adapt('diagnostic/kernel_service_bridge.py',bridge)
    verification=(output/'diagnostic/v31_verify.py').read_text().replace("m['host_id'] != 'host02'", "m['host_id'] != "+repr(host_id))
    adapt('diagnostic/v31_verify.py',verification)
    study=(output/'diagnostic/v31_study.py').read_text()
    study=once(study,'def reset(service):\n',"def reset(service):\n    bridge.HTTP_CALLS['POST reset']=bridge.HTTP_CALLS.get('POST reset',0)+1\n")
    # Keep the runtime preparation watchdog, while removing historical launchers.
    tree=ast.parse(study);main=next(n for n in tree.body if isinstance(n,ast.If) and ast.unparse(n.test)=="__name__ == '__main__'")
    lines=study.splitlines(True)
    routing="""if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['_watchdog'])
    parser.add_argument('--phase',required=True)
    parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args()
    session_watchdog(args.directory,args.phase)
"""
    adapt('diagnostic/v31_study.py',''.join(lines[:main.lineno-1])+routing)
    # Private read-only inventory evidence is under runs; reviewers still check
    # the same script identity, root provenance and complete ownership rules.
    observer=(output/'diagnostic/leftover_observer_review.py').read_text()
    observer=once(observer,"ROOT/'analysis/runtime_io_leftover_observer_audit'",f"ROOT/'runs/{host_id}/audits'")
    adapt('diagnostic/leftover_observer_review.py',observer)
    # Build a minimal NGINX helper module from the exact retained primitives.
    helpers="""import os,sys,subprocess,time,signal,urllib.request
from pathlib import Path
import kernel_service_bridge as bridge
import kernel_fixtures as fixtures
import common as r
require,sha,read,save=r.require,r.sha,r.read,lambda p,v:r.write(p,v,exclusive=False)
"""
    helpers+=functions((ROOT/'diagnostic/imgproxy_qualify.py').read_text(),
        ['cmd','same_owner','process_identity','desktop_absent','fetch','handle_signal'])
    helpers+="\nhelpers=sys.modules[__name__]\n"+functions((ROOT/'diagnostic/gzip_qualify.py').read_text(),['proc_identity','scan_group'])
    helpers=once(helpers,'def fetch(base, endpoint, headers=None):','def _retained_fetch(base, endpoint, headers=None):')
    helpers+='''\nHTTP_CALLS={}
def fetch(base,endpoint,headers=None):
    key='GET '+endpoint
    HTTP_CALLS[key]=HTTP_CALLS.get(key,0)+1
    return _retained_fetch(base,endpoint,headers)
'''
    adapt('diagnostic/nginx_helpers.py',helpers)
    ncommon=f"""from pathlib import Path
import os
from types import SimpleNamespace
import common as r
import nginx_helpers as h
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'runs/{host_id}/NGINX'
SOFTWARE=ROOT/'runs/{host_id}/setup/nginx'
prior=SimpleNamespace(helpers=h,scan_group=h.scan_group)
INPUT_SHA={plan['NGINX']['input_sha256']!r}
SOURCE_SHA={plan['NGINX']['source_archive_sha256']!r}
LIMITS={{'cpu.max':'25000 100000','cpu.max.burst':'0','cpuset.cpus.effective':'2','memory.max':'536870912','pids.max':'128'}}
PROTOCOL={{'application_user':f'{{os.getuid()}}:{{os.getgid()}}'}}
sha,read,require=r.sha,r.read,r.require
def save(path,value):r.write(path,value,exclusive=False)
def source_hashes():return {{name:r.sha(ROOT/name) for name in r.read(ROOT/'runtime_package.json')['go_source_files']}}
def inputs():
    r.verify_package(ROOT)
    setup=r.verify_setup(ROOT,ROOT/'runs/{host_id}/setup')
    manifest=r.read(SOFTWARE/'manifest.json')
    expected=r.read(ROOT/'assets/nginx/manifest.json')
    require(manifest==expected and sha(SOFTWARE/'client')==expected['client_sha256'],'NGINX retained runtime/client identity changed')
    require(read(SOFTWARE/'image.json')['id']==setup['nginx_image'],'NGINX fresh image binding changed')
"""
    adapt('diagnostic/nginx_common.py',ncommon)
    qualify=(ROOT/'diagnostic/nginx_qualify.py').read_text()
    body=functions(qualify,['inspect_owned','remove_owned','watchdog','parse_status','drained','Service','identity','evidence_seal'])
    body=body.replace("research.nginx.feasibility.owner",'research.slo.'+host_id+'.NGINX.owner')
    # Label is a module constant rather than a function AST node.
    qsource="""import argparse,json,os,re,signal,subprocess,sys,time,uuid
from pathlib import Path
import nginx_common as n
h=n.prior.helpers
LABEL="""+repr('research.slo.'+host_id+'.NGINX.owner')+'\n'+body
    needle='        self.watcher = subprocess.Popen('
    # Add identity after the full two-line retained watchdog call.
    qsource=once(qsource,'stdout=self.watch_log, stderr=subprocess.STDOUT, start_new_session=True)\n',
        'stdout=self.watch_log, stderr=subprocess.STDOUT, start_new_session=True)\n        n.save(self.directory / "watchdog_process.json", h.process_identity(self.watcher.pid))\n')
    qsource+="""\nif __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['watchdog']);parser.add_argument('--directory',type=Path,required=True)
    args=parser.parse_args();watchdog(args.directory)
"""
    adapt('diagnostic/nginx_qualify.py',qsource)
    prediction=(ROOT/'diagnostic/nginx_prediction_common.py').read_text()
    pbody=functions(prediction,['config','configs','verify_evidence'])
    psource="""import nginx_common as n
ROOT,BASE=n.ROOT,n.BASE
sha,read,save,require=n.sha,n.read,n.save,n.require
PROTOCOL=dict(calibration_interval_ns=200000000,calibration_offers=400,pilot_offers=100,preparation_offers=20,
 validation_intervals_ns=dict(A=250000000,B=166666667,C=125000000),validation_offers=300,
 block_orders=['ABC','BCA','CAB','ACB','CBA','BAC'])
def sources():return n.source_hashes()
"""+pbody
    adapt('diagnostic/nginx_prediction_common.py',psource)
    adapt('diagnostic/nginx_prediction_model.py',"import nginx_prediction_common as c\n"+functions((ROOT/'diagnostic/nginx_prediction_model.py').read_text(),['outcomes']))
    # Namespace module for the previously registered collector AST; no CLI.
    adapt('diagnostic/nginx_prediction_study.py',"""import json,math,os,signal,subprocess,sys,time,traceback
from pathlib import Path
import nginx_common as n
import nginx_qualify as q
import nginx_prediction_common as c
import nginx_prediction_model as model
h=q.h
""")
    godir=output/'scientific/go';godir.mkdir();science=r.read(FROZEN/'retained_go_design.json')
    for cfg in science['calibration_configs']+science['validation_configs']:cfg['cpus']=host['go_service_cpus']
    r.write(godir/'design.json',science);shutil.copytree(FROZEN/'schedules/go',godir/'schedules');seal(godir)
    # Keep only the transitive local source imports used by the new entrypoints.
    search=[output/p for p in ('runtime','diagnostic','scripts','analysis','slo','diagnostic/runtime_fairness')]
    seeds=[runtime/n for n in ('worker.py','supervisor.py','setup.py','assemble_returns.py','test_runtime.py') if (runtime/n).exists()]
    seeds+=[output/'diagnostic/v31_study.py',output/'diagnostic/v31_service.py',output/'diagnostic/v29_monitor.py',
            output/'diagnostic/leftover_observer_audit.py',output/'diagnostic/nginx_qualify.py']
    todo=list(seeds);keep=set();external=set()
    while todo:
        path=todo.pop()
        if path in keep:continue
        keep.add(path)
        for node in ast.walk(ast.parse(path.read_text())):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for name in names:
                top=name.split('.')[0];found=next((p/(top+'.py') for p in search if (p/(top+'.py')).exists()),None)
                if found:todo.append(found)
                elif top not in sys.stdlib_module_names:external.add(top)
    # Dynamic platform imports are declared seeds, not silently missed.
    keep.add(output/'scripts/portable_platform.py');keep.add(output/'scripts/host02_platform.py')
    for parent in search:
        for path in parent.glob('*.py'):
            if path not in keep:path.unlink()  # Only newly staged package files.
    source_files=sorted(str(p.relative_to(output)) for p in keep if p.relative_to(output).parts[0] in ('diagnostic','scripts','analysis'))
    r.write(output/'runtime_package.json',dict(schema=1,host=host,go_source_files=source_files,
        scientific_plan_sha256=r.sha(output/'scientific/plan.json'),scientific_seal_sha256=r.sha(FROZEN/'seal.json'),
        previous_apparatus_seal_sha256=r.sha(PREVIOUS/'apparatus_seal.json'),
        original_nginx_image=plan['NGINX']['immutable_original_image'],nginx_fresh_import_identity_declared=True,
        third_party_python_imports=sorted(external),runtime_qualified=False,collection_authorized=False,
        immutable_originals_preserved=True,all_outcomes_unrun=True))
    (output/'adaptations.patch').write_text(''.join(changes.values()))
    bundle=output/'assets/go_bundle';bundle.mkdir()
    for name in ('gate','loadgen','image.server','publication_source.go','publication_build.json','counter'):
        shutil.copy2(output/'assets/binaries'/name,bundle/name)
    shutil.copytree(output/'assets/client_build',bundle/'client_build')
    shutil.copytree(godir,bundle/'scientific_design')
    for name in source_files:
        target=bundle/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(output/name,target)
    # Export the compiled client schedules offline; no HTTP or workload.
    sys.path.insert(0,str(ROOT/'replication/slo_decision'))
    import freeze_design as vectors
    cfgs=science['calibration_configs']+science['validation_configs']
    selected=[next(x for x in cfgs if x['role']=='idle'),next(x for x in cfgs if x['role']=='steady' and x['reference_low_rate']==120),
        next(x for x in cfgs if x['role']=='mixed' and x['reference_low_rate']==30),
        next(x for x in cfgs if x['role']=='validation' and x['profile']=='A'),next(x for x in cfgs if x['role']=='validation' and x['profile']=='C')]
    functional=[dict(x,trial='functional_'+str(i),functional=True,duration_sec=x['burst_period_sec'] if x['traffic_pattern']=='bursty' else 2,warmup_sec=0) for i,x in enumerate(selected)]
    functional.append(dict(functional[1],trial='functional_cancel',timeout_sec=.001,duration_sec=2,traffic_pattern='steady',rate=56.6,burst_low=56.6,burst_high=56.6))
    exports={}
    for cfg in cfgs+[vectors.warmup_config(x) for x in cfgs if x['traffic_pattern']!='idle']+functional:
        if cfg['traffic_pattern']=='idle':continue
        key=cfg['trial']+('_warmup' if cfg['duration_sec']==20 else '_measurement')
        target=bundle/'compiled_vectors'/(key+'.json');target.parent.mkdir(exist_ok=True)
        argv=[str(bundle/'loadgen'),'-duration',str(cfg['duration_sec'])+'s','-rate',str(cfg['rate']),'-pattern',cfg['traffic_pattern'],
            '-burst-low',str(cfg['burst_low']),'-burst-high',str(cfg['burst_high']),'-burst-period',str(cfg['burst_period_sec'])+'s',
            '-burst-low-duration',str(cfg['burst_low_duration_sec'])+'s','-schedule-output',str(target)]
        subprocess.run(argv,check=True,capture_output=True,timeout=10)
        r.require(r.read(target)==vectors.go_vector(cfg),'compiled vector differs')
        exports[key]=dict(sha256=r.sha(target),count=len(r.read(target)),argv=argv)
    identity=r.read(output/'assets/retained_identity.json')
    r.write(bundle/'manifest.json',dict(identity,schema=31,host_id=host_id,matrix=cfgs,
        sources={name:r.sha(output/name) for name in source_files},design_seal=r.sha(godir/'seal.json'),
        client_build_seal=r.sha(bundle/'client_build/seal.json'),compiled_exports=exports,
        software_checks_passed=True,runtime_qualified=False,performance_run=False,resource_baseline=None,
        created=time.time(),software_check_scope='retained compiled vectors and package offline runtime tests'))
    seal(bundle)
    # Record the exact sources and engineering elapsed time before final sealing.
    r.write(output/'build_receipt.json',dict(registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        compiled_exports=len(exports),static_local_modules=len(keep),external_imports=sorted(external),
        engineering_elapsed_sec=(time.monotonic_ns()-started)/1e9,no_docker_commands=True,no_traffic=True))
    readme=HERE/'README.md'
    if readme.exists():shutil.copy2(readme,output/'README.md')
    seal(output,'runtime_seal.json')
    # Separate process: all imports and source paths resolve only inside output.
    check=subprocess.run([sys.executable,'-B',str(output/'runtime/setup.py'),'verify-package'],cwd=output,capture_output=True,text=True,timeout=60)
    r.require(check.returncode==0,check.stderr)
    tests=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s','runtime','-p','test_runtime.py','-v'],
        cwd=output,capture_output=True,text=True,timeout=60)
    (output/'offline_tests.stdout').write_text(tests.stdout);(output/'offline_tests.stderr').write_text(tests.stderr)
    r.require(tests.returncode==0,'portable offline checks failed:\n'+tests.stderr)
    seal(output,'runtime_seal.json');r.verify_package(output)
    print(json.dumps(dict(package=str(output),host=host_id,compiled_exports=len(exports),
        seal_sha256=r.sha(output/'runtime_seal.json'),runtime_qualified=False,collection_started=False),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--host',choices=['host01','host02'],required=True);args=p.parse_args();build(args.output.resolve(),args.host)
