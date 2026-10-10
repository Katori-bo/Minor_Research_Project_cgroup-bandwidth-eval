"""Prepare a separate, pinned imgproxy feasibility build; never edit V31 inputs."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'analysis/runtime_io_imgproxy_feasibility/generation-01'
SOFTWARE = BASE / 'software'
UPSTREAM = SOFTWARE / 'upstream/imgproxy-imgproxy-2c89e4e'
PATCHED = SOFTWARE / 'observed-source'


def sha(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f'upstream patch anchor changed: {path}: {old!r}')
    path.write_text(text.replace(old, new))


def instrument():
    shutil.copytree(UPSTREAM, PATCHED)
    request = PATCHED / 'handlers/processing/request.go'
    methods = PATCHED / 'handlers/processing/request_methods.go'
    replace(request, '\t"net/http"', '\t"net/http"\n\t"time"')
    replace(request, '\tHandlerContext\n', '\tHandlerContext\n\tqualification QualificationRecord\n')
    replace(request, 'func (r *request) execute() *server.Error {', '''func (r *request) execute() *server.Error {
    if qualificationEnabled {
        r.qualification.ID = r.reqID
        r.qualification.ExecuteStartNs = qualificationNow()
        defer func() {
            r.qualification.ExecuteDoneNs = qualificationNow()
            qualificationAppend(r.qualification)
        }()
    }''')
    replace(request, '\tdefer releaseWorker()', '''    if qualificationEnabled {
        defer func() {
            r.qualification.ReleaseBeforeNs = qualificationNow()
            releaseWorker()
            r.qualification.ReleaseAfterNs = qualificationNow()
        }()
    } else {
        defer releaseWorker()
    }''')
    replace(request, '\tresult, err := r.processImage(originData)', '''    if qualificationEnabled { r.qualification.ProcessStartNs = qualificationNow() }
    result, err := r.processImage(originData)
    if qualificationEnabled { r.qualification.ProcessDoneNs = qualificationNow() }''')
    replace(request, '\treturn r.respondWithImage(statusCode, result.OutData)', '''    if qualificationEnabled {
        r.qualification.ResponseStartNs = qualificationNow()
        r.rw.Header().Set("X-Qualification-Queue-Ns", fmtQualification(r.qualification.QueueDoneNs-r.qualification.QueueStartNs))
        r.rw.Header().Set("X-Qualification-Process-Ns", fmtQualification(r.qualification.ProcessDoneNs-r.qualification.ProcessStartNs))
    }
    responseErr := r.respondWithImage(statusCode, result.OutData)
    if qualificationEnabled {
        r.qualification.ResponseDoneNs = qualificationNow()
        r.qualification.Success = responseErr == nil && statusCode == http.StatusOK
    }
    return responseErr''')
    # Keep the time import explicitly attached to the duration formatting helper.
    replace(request, '\t"time"', '')
    replace(methods, '\tfn, err := r.Workers().Acquire(ctx)', '''    if qualificationEnabled { r.qualification.QueueStartNs = qualificationNow() }
    fn, err := r.Workers().Acquire(ctx)
    if qualificationEnabled { r.qualification.QueueDoneNs = qualificationNow() }''')
    (PATCHED / 'handlers/processing/qualification.go').write_text('''package processing

import (
    "encoding/json"
    "net/http"
    "os"
    "runtime"
    "strconv"
    "sync"
    "time"

    "github.com/imgproxy/imgproxy/v4/server"
)

const qualificationCapacity = 1024
var qualificationEnabled = os.Getenv("IMGPROXY_QUALIFICATION") == "1"
var qualificationOrigin = time.Now()
var qualificationMu sync.Mutex
var qualificationRecords = make([]QualificationRecord, 0, qualificationCapacity)
var qualificationOverflow uint64

type QualificationRecord struct {
    ID string
    ExecuteStartNs, ExecuteDoneNs int64
    QueueStartNs, QueueDoneNs int64
    ProcessStartNs, ProcessDoneNs int64
    ResponseStartNs, ResponseDoneNs int64
    ReleaseBeforeNs, ReleaseAfterNs int64
    Success bool
}

func qualificationNow() int64 { return time.Since(qualificationOrigin).Nanoseconds() }
func fmtQualification(ns int64) string { return strconv.FormatInt(ns, 10) }

func qualificationAppend(record QualificationRecord) {
    qualificationMu.Lock()
    defer qualificationMu.Unlock()
    if len(qualificationRecords) == qualificationCapacity { qualificationOverflow++; return }
    qualificationRecords = append(qualificationRecords, record)
}

// Collection is bounded and never drained/reset during traffic. Export after drain.
func (h *Handler) QualificationRecords(id string, rw server.ResponseWriter, req *http.Request) *server.Error {
    if !qualificationEnabled { rw.WriteHeader(http.StatusNotFound); return nil }
    qualificationMu.Lock()
    records := append([]QualificationRecord(nil), qualificationRecords...)
    overflow := qualificationOverflow
    qualificationMu.Unlock()
    rw.Header().Set("Content-Type", "application/json")
    json.NewEncoder(rw).Encode(struct {
        Schema string
        GoVersion string
        GOMAXPROCS int
        Capacity int
        Overflow uint64
        Records []QualificationRecord
    }{"imgproxy-qualification-v1", runtime.Version(), runtime.GOMAXPROCS(0), qualificationCapacity, overflow, records})
    return nil
}
''')
    replace(PATCHED / 'imgproxy.go', '\tr.GET(healthPath, i.handlers.Health.Execute).Silent()',
            '\tr.GET(healthPath, i.handlers.Health.Execute).Silent()\n\tr.GET("/qualification/events", i.handlers.Processing.QualificationRecords).Silent()')
    gofmt = SOFTWARE / 'toolchain/go/bin/gofmt'
    changed = ['handlers/processing/request.go', 'handlers/processing/request_methods.go',
               'handlers/processing/qualification.go', 'imgproxy.go']
    subprocess.run([str(gofmt), '-w', *[str(PATCHED/n) for n in changed]], check=True)
    patch = ''.join(''.join(difflib.unified_diff(
        (UPSTREAM/n).read_text().splitlines(True) if (UPSTREAM/n).exists() else [],
        (PATCHED/n).read_text().splitlines(True), fromfile='a/'+n, tofile='b/'+n)) for n in changed)
    (SOFTWARE/'qualification.patch').write_text(patch)
    print('instrumented source prepared; upstream unchanged')


def build():
    env = dict(os.environ, GOTOOLCHAIN='local', GOENV='off', CGO_ENABLED='1',
               GOPROXY='off', GOSUMDB='off', GOMAXPROCS='4',
               GOMODCACHE=str(SOFTWARE/'modcache'), GOCACHE='/tmp/imgproxy-build-cache')
    go = SOFTWARE / 'toolchain/go/bin/go'
    with (SOFTWARE/'build-observed.log').open('x') as log:
        subprocess.run([str(go), 'build', '-p', '4', '-trimpath', '-o',
                        str(SOFTWARE/'imgproxy-observed'), './cli'], cwd=PATCHED,
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=600)
    with (SOFTWARE/'worker-tests.log').open('x') as log:
        subprocess.run([str(go), 'test', '-p', '4', '-count=1', './workers'], cwd=PATCHED,
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    subprocess.run(['gcc', '-O2', '-static', str(ROOT/'diagnostic/kernel_start_gate.c'),
                    '-o', str(SOFTWARE/'gate')], check=True, timeout=60)
    print('observed build and upstream worker tests passed')


def package():
    runtime = SOFTWARE/'runtime'; runtime.mkdir(exist_ok=True)
    # Package the exact native dynamic dependency closure in a scratch image.
    # JPEG/PNG are built into this libvips; optional foreign-format modules are excluded.
    ldd = subprocess.check_output(['ldd', str(SOFTWARE/'imgproxy-stock')], text=True)
    (SOFTWARE/'ldd-stock.txt').write_text(ldd)
    paths = sorted(set(re.findall(r'(?<!\S)(/[^\s()]+)', ldd)))
    for item in paths:
        target = runtime/item.lstrip('/'); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
    loader = runtime/'lib64/ld-linux-x86-64.so.2'; loader.parent.mkdir(exist_ok=True)
    shutil.copy2('/usr/lib64/ld-linux-x86-64.so.2', loader)
    (runtime/'input').mkdir(exist_ok=True)
    shutil.copyfile(UPSTREAM/'testdata/dct2/original.png', runtime/'input/source.png')
    shutil.copy2(SOFTWARE/'gate', runtime/'gate')
    for arm in ('stock', 'observed'):
        shutil.copy2(SOFTWARE/('imgproxy-'+arm), runtime/'server')
        with tarfile.open(SOFTWARE/('runtime-'+arm+'.tar'), 'w', dereference=True) as tar:
            for child in sorted(runtime.iterdir()): tar.add(child, arcname=child.name)
    files = {str(p.relative_to(runtime)): sha(p) for p in runtime.rglob('*') if p.is_file() and p.name != 'server'}
    manifest = dict(upstream_commit='2c89e4ebff3384caf6752db2ec861b4ef5fe675c',
        upstream_version='v4.0.17', go_version='go1.27.1',
        vips_version=subprocess.check_output(['pkg-config','--modversion','vips'], text=True).strip(),
        archive_sha256=sha(SOFTWARE/'imgproxy-v4.0.17.tar.gz'),
        patch_sha256=sha(SOFTWARE/'qualification.patch'),
        binaries={a:sha(SOFTWARE/('imgproxy-'+a)) for a in ('stock','observed')},
        runtime_files_sha256=files, runtime_tars_sha256={a:sha(SOFTWARE/('runtime-'+a+'.tar')) for a in ('stock','observed')},
        workload=dict(input='upstream testdata/dct2/original.png', input_sha256=sha(runtime/'input/source.png'),
            input_dimensions=[600,600], output_dimensions=[300,300], output_format='jpeg', quality=80,
            path='/insecure/rs:fit:300:300:0/q:80/plain/local:///source.png@jpg'),
        note='Host-library scratch packaging; optional foreign-format modules excluded; verify JPEG/PNG functionality before timing.')
    (SOFTWARE/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('runtime archives and manifest prepared')


if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=('instrument','build','package'))
    globals()[p.parse_args().phase]()
