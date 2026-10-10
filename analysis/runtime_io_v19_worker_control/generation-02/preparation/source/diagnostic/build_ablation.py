#!/usr/bin/env python3
"""Isolated stock-Go observer ablation, retaining exact V12/V13 reference images."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import urllib.request

import build_parallelism as stock
import build_completion as v13
import run

DEFAULT=run.ROOT/'analysis/runtime_io_v14_ablation_verified_build'
MODES=('clocks','passive','mutex_early','mutex_late')
ARMS=('legacy',)+MODES+('v13',)


def service_source(original):
    source=stock.service_source(original);replace=stock.replace
    source=replace(source,'\tentries []entryEvent','\tablation *ablationRecorder\n\tentries []entryEvent')
    source=replace(source,'func (s *service) worker() {',
        'func (s *service) worker() {\n\tif s.ablation!=nil { s.ablationWorker();return }')
    source=replace(source,'\treturn snapshot',
        '\tif s.ablation!=nil { s.ablationSnapshot(snapshot,includeEvents) }\n\treturn snapshot')
    source=replace(source,'if s.admitted != s.completed || s.active != 0 || len(s.queue) != 0 {',
        'if s.admitted != s.completed || s.active != 0 || len(s.queue) != 0 || '
        '(s.ablation!=nil && s.ablationPending()!=0) {')
    source=replace(source,'\ts.entries = nil',
        '\ts.entries = nil\n\tif s.ablation!=nil { s.resetAblation() }')
    return replace(source,'\ts.workerYield = booleanEnv',
        '\ts.configureAblation(defaultAblationMode)\n\ts.workerYield = booleanEnv')


def dependencies():
    return sorted(set(stock.dependencies()+v13.dependencies()+[Path(__file__)]+
        [run.HERE/n for n in ('ablation_service.go','ablation_service_test.go','ablation_analysis.py')]))


def prepare(directory):
    stock.prepare(directory)
    service=directory/'service'
    (service/'main.go').write_text(service_source((run.HERE/'service/main.go').read_text()))
    for name in ('ablation_service.go','ablation_service_test.go'): shutil.copy2(run.HERE/name,service/name)
    (service/'Dockerfile').write_text('ARG COMPILER_IMAGE\nFROM ${COMPILER_IMAGE} AS build\nWORKDIR /src\n'
        'COPY go.mod *.go ./\nRUN go version && go test -count=1 -v ./...\n'
        'ARG MODE=passive\nRUN CGO_ENABLED=0 go build -trimpath -ldflags="-X main.defaultAblationMode=${MODE}" -o /server .\n'
        'FROM scratch\nLABEL research.runtime.variant="stock" research.study="observer-ablation-v1"\n'
        'COPY --from=build /server /server\nENTRYPOINT ["/server"]\n')


def verify(directory=DEFAULT,fixtures=True):
    value=run.read(directory/'build.json')
    if value['sources']!=run.hashes(dependencies()): raise ValueError('ablation build sources changed')
    if value['prepared_sha256']!=stock.prepared_hashes(directory/'prepared'): raise ValueError('prepared source changed')
    if run.sha(directory/'loadgen')!=value['loadgen_sha256']: raise ValueError('client changed')
    if value['compiler_image_id']!=stock.COMPILER or run.image_id(stock.COMPILER)!=stock.COMPILER:
        raise ValueError('pinned compiler unavailable')
    if set(value['images'])!=set(ARMS): raise ValueError('six images required')
    for image in value['images'].values():
        if run.image_id(image)!=image: raise ValueError('image unavailable')
        labels=json.loads(run.capture(['docker','image','inspect','--format','{{json .Config.Labels}}',image]))
        if labels.get('research.runtime.variant')!='stock': raise ValueError('runtime is not stock')
    if fixtures:
        check=run.read(directory/'functional_verification.json')
        if not check['passed'] or check['performance_run'] or check['build_sha256']!=run.sha(directory/'build.json'):
            raise ValueError('functional seal changed')
        if check['analyzer_sha256']!=run.sha(run.HERE/'ablation_analysis.py'): raise ValueError('functional analyzer changed')
        if len(check['records'])!=12 or {(r['arm'],r['gomaxprocs']) for r in check['records']}!={(a,g) for a in ARMS for g in (1,2)}:
            raise ValueError('twelve HTTP fixture cells required')
        for name,digest in check['files_sha256'].items():
            if run.sha(directory/name)!=digest: raise ValueError('fixture changed')
        race=run.read(directory/'race_verification.json')
        if not race['passed'] or race['compiler_image_id']!=stock.COMPILER or race['prepared_sha256']!=value['prepared_sha256']:
            raise ValueError('race verification differs from prepared source')
        if run.sha(directory/'race_tests.log')!=race['log_sha256']:raise ValueError('race log changed')
    return value


def functional(directory,value):
    import ablation_analysis as analysis
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
        build_sha256=run.sha(directory/'build.json'),analyzer_sha256=run.sha(run.HERE/'ablation_analysis.py'),files_sha256=files))


def build(directory):
    if directory.exists():raise ValueError('build directory exists; verify or preserve and use a new directory')
    legacy=stock.verify();previous=v13.verify()
    directory.mkdir(parents=True);prepare(directory/'prepared')
    images=dict(legacy=legacy['images']['service'],v13=previous['images']['locked'])
    for mode in MODES:
        tag='quota-observer-ablation-'+mode.replace('_','-')+':14'
        with (directory/(mode+'_build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--build-arg','COMPILER_IMAGE='+stock.COMPILER,
                '--build-arg','MODE='+mode,'-t',tag,str(directory/'prepared/service')],
                stdout=log,stderr=subprocess.STDOUT,check=True)
        images[mode]=run.image_id(tag)
        print('Built',mode,flush=True)
    shutil.copy2(stock.DEFAULT/'loadgen',directory/'loadgen')
    value=dict(schema=1,at=run.now(),compiler_image_id=stock.COMPILER,images=images,
        sources=run.hashes(dependencies()),prepared_sha256=stock.prepared_hashes(directory/'prepared'),
        loadgen_sha256=run.sha(directory/'loadgen'),legacy_build_sha256=run.sha(stock.DEFAULT/'build.json'),
        v13_build_sha256=run.sha(v13.DEFAULT/'build.json'))
    run.put(directory/'build.json',value);race_checks(directory,value);functional(directory,value);verify(directory)
    print('Six ablation images and twelve functional HTTP fixtures verified:',directory,flush=True)


def race_checks(directory,value):
    # Use the retained compiler SDK and installed host GCC; no package install
    # or download. All caches are temporary. This verifies simultaneous live
    # metrics/export, buffer publication, cancellation and reset generations.
    import os
    gcc=shutil.which('gcc')
    if not gcc:raise ValueError('installed GCC required for recorder race checks')
    with tempfile.TemporaryDirectory(prefix='quota-ablation-race-') as tmp:
        sdk=Path(tmp)/'go';container=run.capture(['docker','create',stock.COMPILER])
        try:run.capture(['docker','cp',container+':/usr/local/go',str(sdk)])
        finally:run.capture(['docker','rm',container])
        env=dict(os.environ,GOROOT=str(sdk),GOCACHE=str(Path(tmp)/'cache'),GOPATH=str(Path(tmp)/'gopath'),
            GOTOOLCHAIN='local',GOPROXY='off',GOSUMDB='off',CGO_ENABLED='1',CC=gcc)
        race_source=Path(tmp)/'service'
        shutil.copytree(directory/'prepared/service',race_source)
        # Container fixtures use /runtime.trace. On the host, redirect only
        # that fixture output path into this owned temporary directory.
        trace_file=race_source/'trace_diag.go'
        original='const tracePath = "/runtime.trace"'
        replacement='const tracePath = '+json.dumps(str(Path(tmp)/'runtime.trace'))
        trace_file.write_text(stock.replace(trace_file.read_text(),original,replacement))
        with (directory/'race_tests.log').open('w') as log:
            subprocess.run([str(sdk/'bin/go'),'test','-race','-count=1','-v','./...'],cwd=race_source,
                env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
        run.put(directory/'race_verification.json',dict(passed=True,compiler_image_id=stock.COMPILER,
            prepared_sha256=value['prepared_sha256'],go_binary_sha256=run.sha(sdk/'bin/go'),
            source_adjustment=dict(file='trace_diag.go',original=original,replacement=replacement),
            race_source_sha256=stock.prepared_hashes(race_source),
            gcc_version=run.capture([gcc,'--version']),log_sha256=run.sha(directory/'race_tests.log')))
    print('Concurrent recorder race checks passed.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('build','verify'))
    p.add_argument('--directory',type=Path,default=DEFAULT);a=p.parse_args()
    if a.command=='build':
        with run.acquire_experiment_lock():build(a.directory.resolve())
    else:verify(a.directory.resolve());print('Ablation build verified; no performance trial launched.')
