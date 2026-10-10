#!/usr/bin/env python3
"""Isolated stock-Go build with all-outcome entry records and client clock brackets."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

import run

DEFAULT = run.ROOT / 'analysis/runtime_io_v12_parallelism_build'
COMPILER = 'sha256:2389ebfa5b7f43eeafbd6be0c3700cc46690ef842ad962f6c5bd6be49ed82039'
EXTRAS = ('parallelism_service.go', 'parallelism_service_test.go',
          'parallelism_clock.go', 'parallelism_clock_test.go')


def replace(source, old, new):
    if source.count(old) != 1:
        raise ValueError('expected unique source anchor: ' + old[:80])
    return source.replace(old, new, 1)


def service_source(source):
    source = replace(source, '\thandlerEvents                                              []handlerEvent',
        '\tentries []entryEvent\n\tgeneration uint64\n\thandlerEvents                                              []handlerEvent')
    source = replace(source, '\tvar timing *handlerEvent\n\tn := 44000',
        '\tvar timing *handlerEvent\n\taccepted := false\n\tn := 44000')
    source = replace(source, '\t\ts.active--\n\t\t// Timestamp',
        '\t\tif s.instrument {\n\t\t\ts.entries = append(s.entries, entryEvent{ID:id, '
        'EntryNS:handlerEntry.Sub(s.origin).Nanoseconds(), ExitNS:time.Since(s.origin).Nanoseconds(), Admitted:accepted})\n'
        '\t\t}\n\t\ts.active--\n\t\t// Timestamp')
    source = replace(source, '\taccepted := false\n\tselect {', '\taccepted = false\n\tselect {')
    source = replace(source, '\t\tsnapshot["handler_events"] = append([]handlerEvent{}, s.handlerEvents...)',
        '\t\tsnapshot["handler_events"] = append([]handlerEvent{}, s.handlerEvents...)\n'
        '\t\tsnapshot["entry_events"] = append([]entryEvent{}, s.entries...)')
    source = replace(source, '\t\t"instrument":       s.instrument,',
        '\t\t"entry_protocol": "all-outcomes-v1",\n\t\t"clock_generation": s.generation,\n'
        '\t\t"runtime_variant": "stock",\n\t\t"instrument":       s.instrument,')
    source = replace(source, '\ts.handlerEvents = nil', '\ts.handlerEvents = nil\n\ts.entries = nil\n\ts.generation++')
    return replace(source, '\thttp.HandleFunc("/health", s.health)',
        '\thttp.HandleFunc("/health", s.health)\n\thttp.HandleFunc("/clock", s.clock)')


def client_source(source):
    source = replace(source, '\tElapsedIncludingDrainSec float64',
        '\tClockAnchors []clockAnchor `json:"clock_anchors"`\n'
        '\tClientTestStartNS int64 `json:"client_test_start_ns"`\n\tElapsedIncludingDrainSec float64')
    source = replace(source, '\tclientCPUStart := processCPUUsec()',
        '\tclockOrigin := time.Now()\n\tanchors, clockErr := clockSamples(clockOrigin, *targetURL, "start")\n'
        '\tif clockErr != nil { fmt.Fprintln(os.Stderr, clockErr); os.Exit(2) }\n'
        '\tclientCPUStart := processCPUUsec()')
    source = replace(source, '\ttestEndTime := testStartTime.Add(*duration)',
        '\tclientTestStartNS := testStartTime.Sub(clockOrigin).Nanoseconds()\n\ttestEndTime := testStartTime.Add(*duration)')
    source = replace(source, '\t// Aggregate metrics',
        '\tstopAnchors, clockErr := clockSamples(clockOrigin, *targetURL, "stop")\n'
        '\tif clockErr != nil { fmt.Fprintln(os.Stderr, clockErr); os.Exit(2) }\n'
        '\tanchors = append(anchors, stopAnchors...)\n\t// Aggregate metrics')
    return replace(source, '\t\tElapsedIncludingDrainSec: elapsedIncludingDrain,',
        '\t\tClockAnchors: anchors,\n\t\tClientTestStartNS: clientTestStartNS,\n'
        '\t\tElapsedIncludingDrainSec: elapsedIncludingDrain,')


def dependencies():
    return run.build_sources() + [Path(__file__)] + [run.HERE / n for n in EXTRAS]


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=False)
    for name in ('service', 'loadgen'):
        shutil.copytree(run.HERE / name, directory / name, ignore=shutil.ignore_patterns('*.trace'))
    (directory / 'service/main.go').write_text(service_source((run.HERE / 'service/main.go').read_text()))
    (directory / 'loadgen/main.go').write_text(client_source((run.HERE / 'loadgen/main.go').read_text()))
    for name in EXTRAS:
        target = 'service' if 'service' in name else 'loadgen'
        shutil.copy2(run.HERE / name, directory / target / name)
    for name, binary in (('service', 'server'), ('loadgen', 'loadgen')):
        (directory / name / 'Dockerfile').write_text(
            'ARG COMPILER_IMAGE\nFROM ${COMPILER_IMAGE} AS build\nWORKDIR /src\nCOPY go.mod *.go ./\n'
            'RUN go version && go test -count=1 -v ./... && CGO_ENABLED=0 go build -trimpath -o /'+binary+' .\n'
            'FROM scratch\nLABEL research.runtime.variant="stock" research.study="bursty-parallelism-v1"\n'
            'COPY --from=build /'+binary+' /'+binary+'\nENTRYPOINT ["/'+binary+'"]\n')


def prepared_hashes(directory):
    return {str(p.relative_to(directory)): run.sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def verify(directory=DEFAULT, fixtures=True):
    value = run.read(directory / 'build.json')
    if value['sources'] != run.hashes(dependencies()): raise ValueError('parallelism build sources changed')
    if value['prepared_sha256'] != prepared_hashes(directory / 'prepared'): raise ValueError('prepared source changed')
    if run.sha(directory / 'loadgen') != value['loadgen_sha256']: raise ValueError('client binary changed')
    if value['compiler_image_id'] != COMPILER or run.image_id(COMPILER) != COMPILER:
        raise ValueError('pinned stock compiler unavailable')
    for image in value['images'].values():
        if run.image_id(image) != image: raise ValueError('stock image unavailable')
        labels = json.loads(run.capture(['docker','image','inspect','--format','{{json .Config.Labels}}', image]))
        if labels.get('research.runtime.variant') != 'stock': raise ValueError('non-stock image')
    if fixtures:
        checks = run.read(directory / 'functional_verification.json')
        if not checks['passed'] or checks['performance_run'] or checks['build_sha256'] != run.sha(directory/'build.json'):
            raise ValueError('functional verification missing or changed')
        if checks['analyzer_sha256'] != run.sha(run.HERE/'parallelism_analysis.py'):
            raise ValueError('functional analyzer changed')
        if {r['gomaxprocs'] for r in checks['records']}!={1,2} or len(checks['records'])!=2:
            raise ValueError('both parallelism fixtures required')
        for name, digest in checks['files_sha256'].items():
            if run.sha(directory/name) != digest: raise ValueError('functional fixture changed')
    return value


def functional(directory, value):
    import parallelism_analysis as analysis
    records=[]
    for g in (1,2):
        out=directory/f'fixture_g{g}';out.mkdir()
        container=run.capture(['docker','create','-e',f'GOMAXPROCS={g}','-e','WORKERS=4','-e','INSTRUMENT=1',
            '-p','127.0.0.1::8080',value['images']['service']])
        try:
            run.capture(['docker','start',container])
            port=run.capture(['docker','port',container,'8080/tcp']).split(':')[-1]
            base=f'http://127.0.0.1:{port}'
            def get(endpoint):
                with urllib.request.urlopen(base+'/'+endpoint,timeout=10) as r: return json.load(r)
            for _ in range(50):
                try: health=get('health');break
                except OSError:time.sleep(.1)
            else:raise ValueError('fixture health timeout')
            with (out/'client.log').open('w') as log:
                subprocess.run([str(directory/'loadgen'),'-url',base+'/work?iterations=10',
                    '-duration','300ms','-rate','20','-concurrency','2','-output',str(out/'loadgen.json')],
                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=20)
            server=get('metrics');run.put(out/'server_metrics.json',server)
            result=analysis.entry_analysis(run.read(out/'loadgen.json'),server)
            if health['go_version']!='go1.26.1' or health['gomaxprocs']!=g or server['runtime_capture'] or server['custom_recording']:
                raise ValueError('non-stock or observed fixture')
            if result['entry_count'] != 6 or result['missing_entry_count'] or result['mapping']['uncertainty_ns']>1_000_000:
                raise ValueError('functional entry/clock fixture failed')
            records.append(dict(gomaxprocs=g,requests=6,clock_uncertainty_ns=result['mapping']['uncertainty_ns']))
        finally:
            subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,check=True)
    files={str(p.relative_to(directory)):run.sha(p) for p in sorted(directory.glob('fixture_g*/*')) if p.is_file()}
    run.put(directory/'functional_verification.json',dict(passed=True,performance_run=False,records=records,
        build_sha256=run.sha(directory/'build.json'),analyzer_sha256=run.sha(run.HERE/'parallelism_analysis.py'),files_sha256=files))


def build(directory):
    if directory.exists(): raise ValueError('build directory exists; use verify or a new directory')
    if run.image_id(COMPILER)!=COMPILER: raise ValueError('retained Go 1.26.1 compiler unavailable')
    directory.mkdir(parents=True);prepare(directory/'prepared')
    tags={'service':'quota-bursty-parallelism-service:12','client':'quota-bursty-parallelism-client:12'}
    for name,mode in (('service','service'),('loadgen','client')):
        with (directory/f'{name}_build.log').open('w') as log:
            subprocess.run(['docker','build','--network','none','--build-arg','COMPILER_IMAGE='+COMPILER,
                '-t',tags[mode],str(directory/'prepared'/name)],stdout=log,stderr=subprocess.STDOUT,check=True)
    container=run.capture(['docker','create',tags['client']])
    try:run.capture(['docker','cp',container+':/loadgen',str(directory/'loadgen')])
    finally:run.capture(['docker','rm',container])
    (directory/'loadgen').chmod(0o755)
    value=dict(schema=1,at=run.now(),compiler_image_id=COMPILER,runtime_variant='stock',
        images={mode:run.image_id(tag) for mode,tag in tags.items()},sources=run.hashes(dependencies()),
        prepared_sha256=prepared_hashes(directory/'prepared'),loadgen_sha256=run.sha(directory/'loadgen'))
    run.put(directory/'build.json',value);functional(directory,value);verify(directory)
    print('Stock parallelism build and functional fixtures verified:',directory)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('build','verify'))
    p.add_argument('--directory',type=Path,default=DEFAULT);a=p.parse_args()
    if a.command=='build':
        with run.acquire_experiment_lock():build(a.directory.resolve())
    else:verify(a.directory.resolve());print('Build verified; no performance trials launched.')
