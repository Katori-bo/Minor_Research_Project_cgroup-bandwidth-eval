#!/usr/bin/env python3
"""Offline freeze and client build; no Docker, service, sampler or host changes."""
import difflib
import json
import os
import random
import shutil
import subprocess
from pathlib import Path
import v27r2_common as c
import v26_verify


def main():
    if c.CLIENT_BUILD.exists():
        raise ValueError('preserve existing build; no overwrite')
    prerequisite=v26_verify.verify_completion(c.PREVIOUS)
    if prerequisite['decision']!='both_low_rates_qualified':raise ValueError('V26 prerequisite failed')
    design=c.read(c.ROOT/'analysis/runtime_io_v27_design/20261007/design.json')
    design.update(software_revision=2,
                  failed_generation_bundle_seal=c.digest(c.FAILED/'bundle/seal.json'),
                  failed_generation_preparation_seal=c.digest(c.FAILED/'preparation/seal.json'))
    if c.DESIGN.exists():
        if c.read(c.DESIGN/'design.json')!=design:raise ValueError('existing design differs; no overwrite')
    else:
        c.DESIGN.mkdir(parents=True)
        c.save(c.DESIGN/'design.json',design)
        for rate in (15,30):
            cfg=c.config(dict(id='vector',block=1,collection_order=1,low_rate=rate,counter_probe=True))
            for label,config in [('measurement',cfg),('warmup',c.warmup_config(cfg))]:
                c.save(c.DESIGN/f'rate{rate}_{label}_offsets_ns.json',c.generated_schedule(config))
        hashes={str((c.DESIGN/name).relative_to(c.ROOT)):h for name,h in c.files(c.DESIGN).items()}
        hashes['docs/runtime_io_v27r2_protocol.md']=c.digest(c.ROOT/'docs/runtime_io_v27r2_protocol.md')
        c.save(c.DESIGN/'seal.json',dict(files_sha256=hashes))
    c.design()
    out=c.CLIENT_BUILD;out.mkdir(parents=True);source=c.ROOT/'diagnostic/v27r2_loadgen'
    shutil.copytree(source,out/'source')
    # Current source lineage is recorded explicitly; this is a new client binary.
    diff=[]
    for name in ('main.go','main_test.go'):
        diff.extend(difflib.unified_diff((c.ROOT/'diagnostic/loadgen'/name).read_text().splitlines(True),
                    (source/name).read_text().splitlines(True),fromfile='diagnostic/loadgen/'+name,tofile='diagnostic/v27r2_loadgen/'+name))
    (out/'source.diff').write_text(''.join(diff))
    go=c.ROOT/'analysis/runtime_io_software_audit/audit-01/toolchain/bin/go'
    env=dict(os.environ,GOTOOLCHAIN='local',GOPROXY='off',GOSUMDB='off',GOCACHE='/tmp/v27r2-go-cache',GOMODCACHE='/tmp/v27r2-go-modcache')
    version=subprocess.run([str(go),'version'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
    checks={}
    for name,argv in [('test',[str(go),'test','-count=1','-v','./...']),('vet',[str(go),'vet','./...']),
                      ('race',[str(go),'test','-race','-count=1','./...']),
                      ('build',[str(go),'build','-trimpath','-o',str(out/'loadgen'),'.'])]:
        print('V27r2 client '+name,flush=True)
        build_env=dict(env,CGO_ENABLED='0') if name=='build' else env
        result=subprocess.run(argv,cwd=source,env=build_env,capture_output=True,text=True,timeout=240)
        (out/(name+'.stdout')).write_text(result.stdout);(out/(name+'.stderr')).write_text(result.stderr)
        if result.returncode:raise ValueError('client '+name+' failed: '+result.stderr)
        checks[name]=dict(argv=argv,exit_code=result.returncode)
    exports=out/'schedule_exports';exports.mkdir()
    for cfg in [c.matrix()[next(i for i,x in enumerate(c.matrix()) if x['low_rate']==r)] for r in (15,30)]:
        for label,config in [('measurement',cfg),('warmup',c.warmup_config(cfg))]:
            path=exports/f'rate{cfg["low_rate"]}_{label}.json'
            argv=[str(out/'loadgen'),'-duration',str(config['duration_sec'])+'s','-pattern',config['traffic_pattern'],
                  '-rate',str(config['rate']),'-burst-low',str(config['burst_low']),'-burst-high',str(config['burst_high']),
                  '-burst-period','15s','-burst-low-duration','10s','-schedule-output',str(path)]
            subprocess.run(argv,env=env,check=True,capture_output=True,timeout=10)
            if c.read(path)!=c.schedule(config):raise ValueError('compiled client schedule differs from frozen vector')
    for cfg in c.functional_configs():
        path=exports/(cfg['trial']+'.json')
        argv=[str(out/'loadgen'),'-duration',str(cfg['duration_sec'])+'s','-pattern',cfg['traffic_pattern'],
              '-rate',str(cfg['rate']),'-burst-low',str(cfg['burst_low']),'-burst-high',str(cfg['burst_high']),
              '-burst-period','15s','-burst-low-duration','10s','-schedule-output',str(path)]
        subprocess.run(argv,env=env,check=True,capture_output=True,timeout=10)
        if c.read(path)!=c.schedule(cfg):raise ValueError('compiled functional schedule differs')
    import v27r2_client_fixture
    fixtures=[v27r2_client_fixture.run_fixture(out/'loadgen',out/('compiled_report_'+pattern),pattern) for pattern in ('steady','bursty')]
    c.save(out/'manifest.json',dict(schema=1,sources={p.name:c.digest(p) for p in source.iterdir() if p.suffix in ('.go','.mod')},
        binary_sha256=c.digest(out/'loadgen'),compiler=str(go),compiler_sha256=c.digest(go),compiler_version=version,
        environment_overrides={k:env[k] for k in ('GOTOOLCHAIN','GOPROXY','GOSUMDB','GOCACHE','GOMODCACHE')},checks=checks,
        test_passed=True,vet_passed=True,race_passed=True,all_frozen_vectors_match_binary=True,
        compiled_client_report_replay_passed=all(f['compiled_client_report_replay_passed'] for f in fixtures),
        clock_instrumentation_source='retained build_parallelism.client_source plus V12 prepared parallelism_clock.go',
        build_cgo_enabled='0',
        original_client_source_hashes={name:c.digest(c.ROOT/'diagnostic/loadgen'/name) for name in ('main.go','main_test.go','go.mod')},
        historical_client_binary_sha256=c.read(c.ORIGINAL/'manifest.json')['loadgen_sha256'],
        runtime_qualified=False,performance_run=False,prerequisite_decision=prerequisite['decision']))
    c.seal(out);c.verify_client_build()
    print('V27r2 design and unequal-cycle client frozen; runtime trials remain unrun.',flush=True)


if __name__=='__main__':main()
