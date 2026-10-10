#!/usr/bin/env python3
"""Audit retained service environment and run correctness checks, not performance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import execution_delay_common as c

ROOT = c.ROOT
COMPILER = 'sha256:2389ebfa5b7f43eeafbd6be0c3700cc46690ef842ad962f6c5bd6be49ed82039'
PARENT = ROOT/'analysis/runtime_io_software_audit'


def historical_environment():
    sessions = [ROOT/'analysis/runtime_io_v20_execution_delay'/g for g in ('generation-03', 'generation-04')]
    sessions.append(ROOT/'analysis/runtime_io_period_cost_pilot/generation-02')
    records = []
    for session in sessions:
        paths = sorted((session/'trials').glob('*/attempt-*')) if 'execution_delay' in str(session) else sorted((session/'trials').glob('*'))
        if len(paths) != 16: raise ValueError('sixteen trials required per session')
        for path in paths:
            c.verify_seal(path)
            container = c.read(path/'container.json')['inspect']
            env = container['Config']['Env']
            keys = [v.split('=', 1)[0] for v in env]
            if len(set(keys)) != len(keys): raise ValueError('duplicate environment key')
            health = c.read(path/'identity.json')['health']
            records.append(dict(trial=str(path.relative_to(ROOT)), environment=sorted(env),
                image=container['Image'], go_version=health['go_version'], godebug=health['godebug']))
    # Yield is an intentional factor; every other environment entry must agree.
    normalized = [tuple(v for v in r['environment'] if not v.startswith('WORKER_YIELD=')) for r in records]
    return dict(trials=records, full_environment_matches_except_yield=len(set(normalized)) == 1,
        images_match=len({r['image'] for r in records}) == 1,
        go_versions_match=len({r['go_version'] for r in records}) == 1,
        godebug_values=sorted({r['godebug'] for r in records}))


def audit(directory):
    if directory.parent != PARENT or directory.exists() or directory.is_symlink():
        raise ValueError('use a new direct software-audit directory')
    directory.mkdir(parents=True)
    evidence = historical_environment()
    c.save(directory/'historical_environment.json', evidence)
    source = ROOT/'analysis/runtime_io_v12_parallelism_build/prepared/service'
    build = c.read(ROOT/'analysis/runtime_io_v12_parallelism_build/build.json')
    for p in source.iterdir():
        if p.is_file() and c.digest(p) != build['prepared_sha256']['service/'+p.name]:
            raise ValueError('retained prepared source differs')
    prepared = directory/'service'
    shutil.copytree(source, prepared)
    shutil.copy2(ROOT/'diagnostic/runtime_software_audit_test.go', prepared/'runtime_software_audit_test.go')
    vectors = {}
    for n in (1, 10, 44000):
        value = bytes(range(32))
        for _ in range(n): value = hashlib.sha256(value).digest()
        vectors[n] = value.hex()
    (prepared/'audit_vectors_test.go').write_text('package main\nvar auditDigestVectors = map[int]string{\n'+
        ''.join(f'{n}: "{v}",\n' for n,v in vectors.items())+'}\n')
    c.save(directory/'independent_vectors.json', vectors)
    # The retained Alpine compiler defaults to CGO=0. Extract its exact Go
    # toolchain and use the host gcc for the race detector, offline.
    compiler = directory/'toolchain'
    name = 'quota-software-audit-'+uuid.uuid4().hex
    subprocess.run(['docker','create','--name',name,'--network','none',COMPILER], check=True, stdout=subprocess.DEVNULL)
    try:
        subprocess.run(['docker','cp',name+':/usr/local/go',str(compiler)], check=True)
    finally:
        subprocess.run(['docker','rm',name], check=True, stdout=subprocess.DEVNULL)
    go = compiler/'bin/go'
    env = dict(os.environ, GOROOT=str(compiler), GOCACHE=str(directory/'cache'),
        GOPATH=str(directory/'gopath'), GOPROXY='off', GOSUMDB='off', GOTOOLCHAIN='local',
        GOENV='off', CGO_ENABLED='1', CC='/usr/bin/gcc', GOMAXPROCS='2')
    receipts = []
    for label, args in [('toolchain',['version']), ('vet',['vet','./...'])]:
        argv = [str(go)]+args
        with (directory/(label+'.stdout')).open('x') as out, (directory/(label+'.stderr')).open('x') as err:
            value = subprocess.run(argv, cwd=prepared, env=env, stdout=out, stderr=err, timeout=240,
                preexec_fn=lambda: os.sched_setaffinity(0, {0,1}))
        receipts.append(dict(label=label, argv=argv, returncode=value.returncode))
        print(label+': '+('passed' if value.returncode == 0 else 'FAILED'), flush=True)
    report = dict(performance_run=False, historical_environment_checks={k:v for k,v in evidence.items() if k != 'trials'},
        receipts=receipts, passed=False, pending=['container_race_check'], compiler_image=COMPILER,
        vectors=vectors, audit_source_sha256=c.digest(Path(__file__)),
        service_source_sha256={p.name:c.digest(p) for p in prepared.iterdir() if p.is_file()},
        limitation='Race detection covers exercised paths. Passing does not prove absence of bugs, runtime effects or a causal explanation of the historical reversal.')
    c.save(directory/'report.json', report)
    print('Audit report: '+str(directory/'report.json'), flush=True)
    return finish_in_container(directory)


def finish_in_container(directory):
    """Preserve an earlier host check; run every test with its expected trace path."""
    previous = c.read(directory/'report.json')
    for name,sha in previous['service_source_sha256'].items():
        if c.digest(directory/'service'/name) != sha: raise ValueError('audited source copy changed')
    evidence = previous['historical_environment_checks']
    if not all(evidence[k] for k in ('full_environment_matches_except_yield','images_match','go_versions_match')):
        raise ValueError('historical environment mismatch needs investigation')
    out = directory/'container_followup'
    if out.exists(): raise ValueError('preserve existing follow-up')
    out.mkdir()
    toolchain = directory/'toolchain'
    env = dict(os.environ, GOROOT=str(toolchain), GOCACHE=str(directory/'cache'),
        GOPROXY='off', GOSUMDB='off', GOTOOLCHAIN='local', GOENV='off', CGO_ENABLED='1',
        CC='/usr/bin/gcc', GOMAXPROCS='2')
    binary = out/'service.race.test'
    receipts=[]
    # Static linking permits the host-gcc race build to execute in the retained
    # Alpine container. Tests use numeric loopback addresses, not name lookup.
    commands = [('compile_race', [str(toolchain/'bin/go'),'test','-race','-c',
        '-ldflags','-linkmode=external -extldflags=-static','-o',str(binary)]),
        ('container_race',['docker','run','--rm','--pull=never','--network','none',
            '--cpuset-cpus','0,1','-e','GOMAXPROCS=2','-v',str(out)+':/audit:ro',
            COMPILER,'/audit/service.race.test','-test.count=2','-test.timeout=120s','-test.v'])]
    for label,argv in commands:
        with (out/(label+'.stdout')).open('x') as stdout, (out/(label+'.stderr')).open('x') as stderr:
            value = subprocess.run(argv,cwd=directory/'service',env=env,stdout=stdout,stderr=stderr,
                timeout=240,preexec_fn=lambda:os.sched_setaffinity(0,{0,1}))
        receipts.append(dict(label=label,argv=argv,returncode=value.returncode))
        print(label+': '+('passed' if value.returncode==0 else 'FAILED'),flush=True)
        if value.returncode: break
    required=[r for r in previous['receipts'] if r['label'] in ('toolchain','vet')]
    report=dict(passed=len(required)==2 and all(r['returncode']==0 for r in required+receipts)
            and len(receipts)==2, performance_run=False,
        prior_report_sha256=c.digest(directory/'report.json'), receipts=receipts,
        historical_environment_checks=evidence,
        source_sha256=previous['service_source_sha256'], vectors=previous['vectors'],
        race_binary_sha256=c.digest(binary) if binary.exists() else None,
        audit_source_sha256=c.digest(Path(__file__)),
        host_trace_test_failure_preserved=any(r['label']=='race' and r['returncode']!=0 for r in previous['receipts']),
        limitation='Every retained test plus added correctness/concurrency checks is run with the race detector in a container supporting /runtime.trace. Passing only covers exercised paths and does not exclude runtime effects or identify the period-reversal cause.')
    c.save(out/'report.json',report); c.seal(out)
    c.save(directory/'latest_report.json',dict(path='container_followup/report.json',seal=c.digest(out/'seal.json')))
    print('Final audit report: '+str(out/'report.json'),flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=PARENT/('audit-'+str(time.time_ns())))
    parser.add_argument('--finish-in-container', action='store_true')
    args = parser.parse_args()
    report = finish_in_container(args.directory.absolute()) if args.finish_in_container else audit(args.directory.absolute())
    raise SystemExit(0 if report['passed'] else 1)
