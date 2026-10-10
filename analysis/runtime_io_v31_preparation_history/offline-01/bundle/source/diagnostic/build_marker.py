#!/usr/bin/env python3
"""V15: insert clock calls into the retained worker path, without new recording."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request

import build_parallelism as stock
import build_ablation as prior
import run

DEFAULT = run.ROOT / 'analysis/runtime_io_v15_marker_verified_build'
COUNTS = dict(rebuilt_zero=0, before_one=1, bracket_two=2, boundary_five=5)
ARMS = ('legacy',) + tuple(COUNTS) + ('v14_clocks',)


def service_source(original, arm):
    source = stock.service_source(original)
    if arm not in COUNTS:
        raise ValueError('unknown marker arm')
    if COUNTS[arm]:
        source = stock.replace(source, '\t// Completion becomes visible only after the corresponding event is saved.',
            '\tmarkerOrigin := s.origin // Cache before send; reset may follow handler exit.\n'
            + ('\t_ = time.Since(markerOrigin).Nanoseconds()\n' if COUNTS[arm] == 5 else '')
            + '\t// Completion becomes visible only after the corresponding event is saved.')
        if COUNTS[arm] == 5:
            source = stock.replace(source, '\ts.mu.Lock()\n\tif s.instrument {\n\t\ts.events = append',
                '\ts.mu.Lock()\n\t_ = time.Since(markerOrigin).Nanoseconds()\n\tif s.instrument {\n\t\ts.events = append')
        source = stock.replace(source, '\tj.reply <- answer // Buffered: timed-out clients never strand a worker.',
            ('\t_ = time.Since(markerOrigin).Nanoseconds()\n' if COUNTS[arm] == 5 else '')
            + '\t_ = time.Since(markerOrigin).Nanoseconds()\n'
            + '\tj.reply <- answer // Buffered: timed-out clients never strand a worker.'
            + ('\n\t_ = time.Since(markerOrigin).Nanoseconds()' if COUNTS[arm] >= 2 else ''))
    return stock.replace(source, '\treturn snapshot',
        '\tsnapshot["marker_protocol"] = "inline-clock-screen-v1"\n'
        f'\tsnapshot["marker_arm"] = "{arm}"\n'
        f'\tsnapshot["marker_clock_calls"] = {COUNTS[arm]}\n\treturn snapshot')


def dependencies():
    return sorted(set(stock.dependencies() + prior.dependencies() + [Path(__file__),
        run.HERE/'marker_analysis.py', run.HERE/'marker_service_test.go']))


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    for arm in COUNTS:
        stock.prepare(directory/arm)
        service = directory/arm/'service'
        (service/'main.go').write_text(service_source((run.HERE/'service/main.go').read_text(), arm))
        shutil.copy2(run.HERE/'marker_service_test.go', service/'marker_service_test.go')
        (service/'Dockerfile').write_text('ARG COMPILER_IMAGE\nFROM ${COMPILER_IMAGE} AS build\nWORKDIR /src\n'
            'COPY go.mod *.go ./\nRUN go version && go test -count=1 -v ./...\n'
            'RUN CGO_ENABLED=0 go build -trimpath -gcflags="research-service=-m=2" -o /server .\n'
            'FROM scratch\nLABEL research.runtime.variant="stock" research.study="inline-clock-screen-v1"\n'
            'COPY --from=build /server /server\nENTRYPOINT ["/server"]\n')


def normalized_assembly(raw):
    lines = []
    for line in raw.splitlines():
        fields = line.split(None, 3)
        if len(fields) == 4 and fields[1].startswith('0x'):
            lines.append(re.sub(r'(?<!\$)\b0x[0-9a-f]{5,}\b', 'ADDR', fields[3].strip()))
    return '\n'.join(lines)


def compiler_audit(directory, images):
    """Read actual shipped binaries; no timed requests or CPU benchmarks."""
    out = directory/'compiler_audit'; out.mkdir()
    records = {}
    patterns = {'work': '^main.work$', 'worker': r'^main\.\(\*service\)\.worker$',
                'runJob': r'^main\.\(\*service\)\.runJob$',
                'ablationRunJob': r'^main\.\(\*service\)\.ablationRunJob$'}
    for arm, image in images.items():
        binary = out/(arm+'.server')
        container = run.capture(['docker','create',image])
        try:
            run.capture(['docker','cp',container+':/server',str(binary)])
        finally:
            run.capture(['docker','rm',container])
        record = dict(image=image, binary_sha256=run.sha(binary), functions={})
        for name, pattern in patterns.items():
            raw = run.capture(['docker','run','--rm','--network','none','-v',str(out)+':/audit:ro',
                stock.COMPILER, 'go','tool','objdump','-s',pattern,'/audit/'+binary.name])
            (out/(arm+'.'+name+'.txt')).write_text(raw)
            normalized = normalized_assembly(raw)
            path = out/(arm+'.'+name+'.normalized.txt'); path.write_text(normalized)
            record['functions'][name] = dict(normalized_sha256=run.sha(path),
                instruction_lines=len(normalized.splitlines()),
                time_since_calls=normalized.count('CALL time.Since(SB)'),
                calls=re.findall(r'CALL ([^\n]+)', normalized))
        records[arm] = record
    for arm, count in COUNTS.items():
        if arm not in records:
            continue
        if records[arm]['functions']['runJob']['time_since_calls'] != count:
            raise ValueError('compiler did not retain expected marker calls: '+arm)
        if records[arm]['functions']['work']['normalized_sha256'] != records['legacy']['functions']['work']['normalized_sha256']:
            raise ValueError('SHA-work machine code changed: '+arm)
    checks = dict(work_code_matches_legacy={a:r['functions']['work']['normalized_sha256'] ==
        records['legacy']['functions']['work']['normalized_sha256'] for a,r in records.items()},
        zero_runJob_matches_legacy=(records['rebuilt_zero']['functions']['runJob']['normalized_sha256'] ==
            records['legacy']['functions']['runJob']['normalized_sha256']) if 'rebuilt_zero' in records else None,
        zero_worker_matches_legacy=(records['rebuilt_zero']['functions']['worker']['normalized_sha256'] ==
            records['legacy']['functions']['worker']['normalized_sha256']) if 'rebuilt_zero' in records else None)
    run.put(out/'audit.json',dict(passed=True, compiler_image_id=stock.COMPILER, records=records, checks=checks,
        limitation='Normalized instructions omit code addresses and source lines. Static identity does not prove identical timing, cache alignment, scheduling or host state.'))
    return checks


def race_checks(directory, value):
    gcc = shutil.which('gcc')
    if not gcc:
        raise ValueError('installed GCC required')
    records = []
    with tempfile.TemporaryDirectory(prefix='quota-marker-race-') as tmp:
        sdk = Path(tmp)/'go'; container = run.capture(['docker','create',stock.COMPILER])
        try:
            run.capture(['docker','cp',container+':/usr/local/go',str(sdk)])
        finally:
            run.capture(['docker','rm',container])
        env = dict(os.environ, GOROOT=str(sdk), GOCACHE=str(Path(tmp)/'cache'), GOPATH=str(Path(tmp)/'gopath'),
            GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off', CGO_ENABLED='1', CC=gcc)
        for arm in COUNTS:
            source = Path(tmp)/arm; shutil.copytree(directory/'prepared'/arm/'service', source)
            trace_file = source/'trace_diag.go'; original = 'const tracePath = "/runtime.trace"'
            replacement = 'const tracePath = '+json.dumps(str(Path(tmp)/(arm+'.trace')))
            trace_file.write_text(stock.replace(trace_file.read_text(), original, replacement))
            logfile = directory/(arm+'_race.log')
            with logfile.open('w') as log:
                subprocess.run([str(sdk/'bin/go'),'test','-race','-count=1','-v','./...'],cwd=source,
                    env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
            records.append(dict(arm=arm, log=logfile.name, log_sha256=run.sha(logfile),
                production_source_sha256=stock.prepared_hashes(directory/'prepared'/arm/'service'),
                tested_source_sha256=stock.prepared_hashes(source),
                fixture_adjustment=dict(file='trace_diag.go',original=original,replacement=replacement)))
    run.put(directory/'race_verification.json', dict(passed=True, compiler_image_id=stock.COMPILER,
        prepared_sha256=value['prepared_sha256'], records=records))


def functional(directory,value):
    import marker_analysis as analysis
    records=[]
    for arm in ARMS:
        for g in (1,2):
            out=directory/f'fixture_{arm}_g{g}';out.mkdir()
            container=run.capture(['docker','create','-e',f'GOMAXPROCS={g}','-e','WORKERS=4','-e','INSTRUMENT=1',
                '-p','127.0.0.1::8080',value['images'][arm]])
            try:
                run.capture(['docker','start',container]);port=run.capture(['docker','port',container,'8080/tcp']).split(':')[-1]
                base=f'http://127.0.0.1:{port}'
                def get(endpoint):
                    with urllib.request.urlopen(base+'/'+endpoint,timeout=10) as r:return json.load(r)
                for _ in range(50):
                    try: health=get('health');break
                    except OSError:time.sleep(.1)
                else:raise ValueError('fixture health timeout')
                with (out/'client.log').open('w') as log:
                    subprocess.run([str(directory/'loadgen'),'-url',base+'/work?iterations=10','-duration','300ms',
                        '-rate','20','-concurrency','2','-output',str(out/'loadgen.json')],
                        stdout=log,stderr=subprocess.STDOUT,check=True,timeout=20)
                for _ in range(100):
                    server=get('metrics')
                    if server['active_handlers']==0 and server['completed']==server['admitted'] and not server.get('observer_pending_records',0):break
                    time.sleep(.01)
                else:raise ValueError('functional observer drain timeout')
                run.put(out/'server_metrics.json',server)
                result=analysis.classify(run.read(out/'loadgen.json'),server,arm)
                if health['go_version']!='go1.26.1' or health['gomaxprocs']!=g or result['offered']!=6 or result['missing_entry_count']:
                    raise ValueError('functional fixture mismatch')
                records.append(dict(arm=arm,gomaxprocs=g,requests=6,clock_uncertainty_ns=result['mapping']['uncertainty_ns']))
            finally:run.capture(['docker','rm','-f',container])
    files={str(p.relative_to(directory)):run.sha(p) for p in sorted(directory.glob('fixture_*/*')) if p.is_file()}
    run.put(directory/'functional_verification.json',dict(passed=True,performance_run=False,records=records,
        build_sha256=run.sha(directory/'build.json'),analyzer_sha256=run.sha(run.HERE/'marker_analysis.py'),files_sha256=files))


def verify(directory=DEFAULT, fixtures=True):
    value = run.read(directory/'build.json')
    if value['sources'] != run.hashes(dependencies()) or value['prepared_sha256'] != stock.prepared_hashes(directory/'prepared'):
        raise ValueError('marker sources changed')
    if value['loadgen_sha256'] != run.sha(directory/'loadgen') or value['compiler_image_id'] != stock.COMPILER:
        raise ValueError('marker compiler/client changed')
    if run.image_id(stock.COMPILER) != stock.COMPILER or set(value['images']) != set(ARMS):
        raise ValueError('missing compiler or arms')
    for image in value['images'].values():
        if run.image_id(image) != image:
            raise ValueError('image unavailable')
        labels = json.loads(run.capture(['docker','image','inspect','--format','{{json .Config.Labels}}',image]))
        if labels.get('research.runtime.variant') != 'stock':
            raise ValueError('runtime not stock')
    if fixtures:
        check = run.read(directory/'functional_verification.json')
        if not check['passed'] or check['performance_run'] or check['build_sha256'] != run.sha(directory/'build.json') or check['analyzer_sha256'] != run.sha(run.HERE/'marker_analysis.py'):
            raise ValueError('functional seal mismatch')
        if {(r['arm'],r['gomaxprocs']) for r in check['records']} != {(a,g) for a in ARMS for g in (1,2)} or len(check['records']) != 12:
            raise ValueError('twelve fixture cells required')
        seal = run.read(directory/'verification.json')
        actual = {str(p.relative_to(directory)):run.sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.name != 'verification.json'}
        if not seal['passed'] or seal['files_sha256'] != actual:
            raise ValueError('build verification files changed')
        race = run.read(directory/'race_verification.json')
        if not race['passed'] or race['prepared_sha256'] != value['prepared_sha256'] or {r['arm'] for r in race['records']} != set(COUNTS):
            raise ValueError('race checks missing')
        if not run.read(directory/'compiler_audit/audit.json')['passed']:
            raise ValueError('compiler audit missing')
    return value


def build(directory):
    if directory.exists():
        raise ValueError('preserve existing build; use verify or another directory')
    legacy, previous = stock.verify(), prior.verify()
    directory.mkdir(parents=True)
    prepare(directory/'prepared')
    images = dict(legacy=legacy['images']['service'], v14_clocks=previous['images']['clocks'])
    for arm in COUNTS:
        with (directory/(arm+'_build.log')).open('w') as log:
            tag = 'quota-inline-marker-'+arm.replace('_','-')+':15'
            subprocess.run(['docker','build','--network','none','--build-arg','COMPILER_IMAGE='+stock.COMPILER,
                '-t',tag,str(directory/'prepared'/arm/'service')], stdout=log,stderr=subprocess.STDOUT,check=True)
        images[arm] = run.image_id(tag); print('Built',arm,flush=True)
    shutil.copy2(stock.DEFAULT/'loadgen',directory/'loadgen')
    value = dict(schema=1,at=run.now(),compiler_image_id=stock.COMPILER,images=images,
        sources=run.hashes(dependencies()),prepared_sha256=stock.prepared_hashes(directory/'prepared'),
        loadgen_sha256=run.sha(directory/'loadgen'),legacy_build_sha256=run.sha(stock.DEFAULT/'build.json'),
        v14_build_sha256=run.sha(prior.DEFAULT/'build.json'))
    run.put(directory/'build.json',value)
    print('Actual binary compiler audit:',compiler_audit(directory, images),flush=True)
    race_checks(directory,value); print('All four race suites passed.',flush=True)
    functional(directory,value)
    files = {str(p.relative_to(directory)):run.sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    run.put(directory/'verification.json',dict(passed=True,files_sha256=files))
    verify(directory); print('V15 build and twelve HTTP fixtures verified; performance collection not started.',flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('build','verify','audit-v14'))
    p.add_argument('--directory',type=Path,default=DEFAULT); a=p.parse_args()
    if a.command == 'audit-v14':
        out = run.ROOT/'analysis/runtime_io_v14_compiler_audit'
        if out.exists(): raise ValueError('preserve existing audit')
        v = prior.verify(); out.mkdir()
        print(compiler_audit(out,dict(legacy=v['images']['legacy'],v14_clocks=v['images']['clocks'],v13=v['images']['v13'])))
    elif a.command == 'build':
        with run.acquire_experiment_lock(): build(a.directory.resolve())
    else:
        verify(a.directory.resolve()); print('V15 build verified.')
