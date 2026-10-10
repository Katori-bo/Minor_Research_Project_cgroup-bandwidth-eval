#!/usr/bin/env python3
"""Build isolated recorder qualification variants; never alter the V12 build."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

import build_parallelism as stock
import run

DEFAULT = run.ROOT / 'analysis/runtime_io_v13_completion_build'
EXTRAS = ('completion_service.go', 'completion_service_test.go')


def service_source(source):
    source = stock.service_source(source)
    replace = stock.replace
    source = replace(source, '\tentries []entryEvent',
        '\trecorderMode string\n\tcompletionSlots []completionSlot\n\trecordErrors int\n\tentries []entryEvent')
    source = replace(source, 'func (s *service) runJob(j job, finishRegion func()) {',
        'func (s *service) runJob(j job, finishRegion func()) {\n'
        '\tif s.recorderMode != "" { s.completionRunJob(j, finishRegion); return }')
    source = replace(source, '\ts.active++',
        '\tif s.recorderMode != "" {\n'
        '\t\tif id >= uint64(len(s.completionSlots)) || s.completionSlots[id].seen {\n'
        '\t\t\ts.recordErrors++; s.mu.Unlock(); http.Error(w, "record ID invalid", 400); return\n'
        '\t\t}\n\t\ts.completionSlots[id].seen = true\n\t}\n\ts.active++')
    source = replace(source, '\t\t\ts.handlerEvents = append(s.handlerEvents, *timing)',
        '\t\t\tif s.recorderMode == "bounded" { s.completionSlots[id].handler = *timing; '
        's.completionSlots[id].handlerReady = true } else { s.handlerEvents = append(s.handlerEvents, *timing) }')
    source = replace(source,
        '\t\t\ts.entries = append(s.entries, entryEvent{ID:id, EntryNS:handlerEntry.Sub(s.origin).Nanoseconds(), '
        'ExitNS:time.Since(s.origin).Nanoseconds(), Admitted:accepted})',
        '\t\t\te := entryEvent{ID:id, EntryNS:handlerEntry.Sub(s.origin).Nanoseconds(), '
        'ExitNS:time.Since(s.origin).Nanoseconds(), Admitted:accepted}\n'
        '\t\t\tif s.recorderMode == "bounded" { s.completionSlots[id].entry = e; '
        's.completionSlots[id].entryReady = true } else { s.entries = append(s.entries, e) }')
    source = replace(source, '\t\t\ts.handlerEvents[len(s.handlerEvents)-1].HandlerExitNS = time.Since(s.origin).Nanoseconds()',
        '\t\t\tif s.recorderMode == "bounded" { s.completionSlots[id].handler.HandlerExitNS = '
        'time.Since(s.origin).Nanoseconds() } else { s.handlerEvents[len(s.handlerEvents)-1].HandlerExitNS = '
        'time.Since(s.origin).Nanoseconds() }')
    source = replace(source, '\treturn snapshot',
        '\tif s.recorderMode != "" { s.completionSnapshot(snapshot, includeEvents) }\n\treturn snapshot')
    source = replace(source, '\ts.entries = nil',
        '\ts.entries = nil\n\tif s.recorderMode != "" { '
        'clear(s.completionSlots); s.recordErrors = 0 }')
    return replace(source, '\ts.workerYield = booleanEnv',
        '\ts.configureCompletion(defaultCompletionRecorder)\n\ts.workerYield = booleanEnv')


def dependencies():
    return sorted(set(stock.dependencies() + [Path(__file__)] + [run.HERE/n for n in EXTRAS]))


def prepare(directory):
    stock.prepare(directory)
    service = directory/'service'
    (service/'main.go').write_text(service_source((run.HERE/'service/main.go').read_text()))
    for name in EXTRAS: shutil.copy2(run.HERE/name, service/name)
    (service/'completion_default.go').write_text('package main\nvar defaultCompletionRecorder = "locked"\n')
    for name in ('service', 'loadgen'):
        path = directory/name/'Dockerfile'
        text = path.read_text().replace('research.study="bursty-parallelism-v1"', 'research.study="completion-qualification-v1"')
        if name == 'service':
            text = text.replace('ARG COMPILER_IMAGE\n', 'ARG COMPILER_IMAGE\n')
            text = text.replace('WORKDIR /src\n', 'ARG RECORDER=locked\nWORKDIR /src\n')
            text = text.replace('go build -trimpath', 'go build -ldflags="-X main.defaultCompletionRecorder=${RECORDER}" -trimpath')
        path.write_text(text)


def verify(directory=DEFAULT, fixtures=True):
    value = run.read(directory/'build.json')
    if value['sources'] != run.hashes(dependencies()): raise ValueError('completion build sources changed')
    if stock.prepared_hashes(directory/'prepared') != value['prepared_sha256']: raise ValueError('prepared sources changed')
    if run.sha(directory/'loadgen') != value['loadgen_sha256']: raise ValueError('client changed')
    if value['compiler_image_id'] != stock.COMPILER or run.image_id(stock.COMPILER) != stock.COMPILER:
        raise ValueError('pinned compiler unavailable')
    for image in value['images'].values():
        if run.image_id(image) != image: raise ValueError('image unavailable')
        labels = json.loads(run.capture(['docker','image','inspect','--format','{{json .Config.Labels}}',image]))
        if labels.get('research.runtime.variant') != 'stock': raise ValueError('non-stock image')
    if fixtures:
        check = run.read(directory/'functional_verification.json')
        if not check['passed'] or check['performance_run'] or check['build_sha256'] != run.sha(directory/'build.json'):
            raise ValueError('functional seal changed')
        if check['analyzer_sha256'] != run.sha(run.HERE/'completion_analysis.py'): raise ValueError('analyzer changed')
        if {(r['arm'],r['gomaxprocs']) for r in check['records']} != {(a,g) for a in ('legacy','locked','bounded') for g in (1,2)}:
            raise ValueError('six fixture cells required')
        for name,digest in check['files_sha256'].items():
            if run.sha(directory/name) != digest: raise ValueError('functional fixture changed')
    return value


def functional(directory, value):
    import completion_analysis as analysis
    records=[]
    for arm in ('legacy','locked','bounded'):
        for g in (1,2):
            out=directory/f'fixture_{arm}_g{g}';out.mkdir()
            container=run.capture(['docker','create','-e',f'GOMAXPROCS={g}','-e','WORKERS=4','-e','INSTRUMENT=1',
                '-p','127.0.0.1::8080',value['images'][arm]])
            try:
                run.capture(['docker','start',container])
                port=run.capture(['docker','port',container,'8080/tcp']).split(':')[-1]
                base=f'http://127.0.0.1:{port}'
                def get(endpoint):
                    with urllib.request.urlopen(base+'/'+endpoint,timeout=10) as r: return json.load(r)
                for _ in range(50):
                    try: health=get('health');break
                    except OSError: time.sleep(.1)
                else: raise ValueError('fixture health timeout')
                with (out/'client.log').open('w') as log:
                    subprocess.run([str(directory/'loadgen'),'-url',base+'/work?iterations=10','-duration','300ms',
                        '-rate','20','-concurrency','2','-output',str(out/'loadgen.json')],
                        stdout=log,stderr=subprocess.STDOUT,check=True,timeout=20)
                # HTTP body receipt can precede the deferred handler record.
                for _ in range(100):
                    server=get('metrics')
                    if server['active_handlers']==0 and server['completed']==server['admitted']: break
                    time.sleep(.01)
                run.put(out/'server_metrics.json',server)
                result=analysis.classify(run.read(out/'loadgen.json'),server,arm)
                if health['go_version']!='go1.26.1' or health['gomaxprocs']!=g or result['offered']!=6 or result['missing_entry_count']:
                    raise ValueError('functional fixture mismatch')
                records.append(dict(arm=arm,gomaxprocs=g,requests=6,clock_uncertainty_ns=result['mapping']['uncertainty_ns']))
            finally: run.capture(['docker','rm','-f',container])
    files={str(p.relative_to(directory)):run.sha(p) for p in sorted(directory.glob('fixture_*/*')) if p.is_file()}
    run.put(directory/'functional_verification.json',dict(passed=True,performance_run=False,records=records,
        build_sha256=run.sha(directory/'build.json'),analyzer_sha256=run.sha(run.HERE/'completion_analysis.py'),files_sha256=files))


def build(directory):
    if directory.exists(): raise ValueError('build exists; verify it or use a new directory')
    legacy=stock.verify()
    directory.mkdir(parents=True);prepare(directory/'prepared')
    images={'legacy':legacy['images']['service']}
    for arm in ('locked','bounded'):
        tag='quota-completion-'+arm+':13'
        with (directory/(arm+'_build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--build-arg','COMPILER_IMAGE='+stock.COMPILER,
                '--build-arg','RECORDER='+arm,'-t',tag,str(directory/'prepared/service')],
                stdout=log,stderr=subprocess.STDOUT,check=True)
        images[arm]=run.image_id(tag)
    shutil.copy2(stock.DEFAULT/'loadgen',directory/'loadgen')
    value=dict(schema=1,at=run.now(),compiler_image_id=stock.COMPILER,images=images,
        sources=run.hashes(dependencies()),prepared_sha256=stock.prepared_hashes(directory/'prepared'),
        loadgen_sha256=run.sha(directory/'loadgen'),legacy_build_sha256=run.sha(stock.DEFAULT/'build.json'))
    run.put(directory/'build.json',value);functional(directory,value);verify(directory)
    print('Completion builds and six real-HTTP functional fixtures verified:',directory,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('build','verify'))
    p.add_argument('--directory',type=Path,default=DEFAULT);a=p.parse_args()
    if a.command=='build':
        with run.acquire_experiment_lock(): build(a.directory.resolve())
    else: verify(a.directory.resolve());print('Build verified; no performance measurements launched.')
