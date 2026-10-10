#!/usr/bin/env python3
"""Prepare/build a bounded scheduler decision recorder on the retained policy."""
import argparse
from pathlib import Path
import shutil
import subprocess

import build_pending_probe as base
import run

DEFAULT = run.ROOT/'analysis/runtime_io_v11_decision_probe_final_build'
IMAGE = base.IMAGE
REASONS = ('trace_reader', 'gc_worker', 'fair_global', 'local', 'global_batch',
           'netpoll_nonblocking', 'steal_or_timer', 'gc_idle', 'before_idle',
           'global_recheck', 'global_after_release', 'gc_after_release', 'netpoll_blocking')

RECORDER = r'''
// Research-only append-only capture. Hooks neither allocate nor acquire locks.
// Each slot has one writer; release publication precedes snapshot reads.
const researchDecisionCapacity = 262144
type researchDecisionSlot struct {
    published atomic.Uint32
    event ResearchSchedulerEvent
}
type ResearchSchedulerEvent struct {
    Sequence uint64 `json:"sequence"`
    Time int64 `json:"time_ns"`
    Kind uint8 `json:"kind"` // 1 wake, 2 selection, 3 dispatch, 4 handler, 5 worker
    G uint64 `json:"g"`
    Actor uint64 `json:"actor_g"`
    M int64 `json:"m"`
    P int32 `json:"p"`
    Source uint8 `json:"source"`
    Pending bool `json:"pending"` // captured at schedule entry
    Fair bool `json:"fair"` // current ordinary forceFair decision
    Inherit bool `json:"inherit"`
    Network bool `json:"network"` // waitreason at Waiting->Runnable
    Schedtick uint32 `json:"schedtick"`
    Request uint64 `json:"request"` // valid only for kinds 4/5, including zero
    StartPC uint64 `json:"start_pc"`
    Function string `json:"function"` // resolved only in the stopped snapshot
}
var researchDecisionSlots [researchDecisionCapacity]researchDecisionSlot
var researchDecisionNext atomic.Uint64
var researchDecisionActive atomic.Bool
var researchDecisionWriters atomic.Int32
var researchDecisionEpoch atomic.Uint64
var researchDecisionLifecycle atomic.Uint32
var researchDecisionStop atomic.Int64

//go:nosplit
func researchDecisionRecord(kind uint8, gp *g, source uint8, pending, fair, inherit bool, request uint64) {
    if !researchObserveDecisions || !researchDecisionActive.Load() { return }
    epoch := researchDecisionEpoch.Load()
    researchDecisionWriters.Add(1)
    if !researchDecisionActive.Load() || epoch != researchDecisionEpoch.Load() { researchDecisionWriters.Add(-1); return }
    index := researchDecisionNext.Add(1)-1
    if index < researchDecisionCapacity {
        slot := &researchDecisionSlots[index]
        mp := getg().m
        e := &slot.event
        e.Sequence = index+1
        e.Time = nanotime()
        e.Kind, e.G, e.Source = kind, gp.goid, source
        e.StartPC = uint64(gp.startpc)
        e.Pending, e.Fair, e.Inherit, e.Request = pending, fair, inherit, request
        e.Network = kind == 1 && gp.waitreason == waitReasonIOWait
        e.M, e.P = mp.id, -1
        if mp.curg != nil { e.Actor = mp.curg.goid }
        if mp.p != 0 {
            pp := mp.p.ptr()
            e.P, e.Schedtick = pp.id, pp.schedtick
            if kind == 2 && source == 4 { e.Source = pp.researchLastLocalPick }
        }
        slot.published.Store(1)
    }
    researchDecisionWriters.Add(-1)
}

func ResearchSchedulerObservationEnabled() bool { return researchObserveDecisions }
func ResearchSchedulerNanoTime() int64 { return nanotime() }
// Lifecycle calls are outside the workload; generation checks exclude stale
// writers across captures. Each service allows only one start after its reset.
func ResearchSchedulerStart() bool {
    if !researchDecisionLifecycle.CompareAndSwap(0, 1) { return false }
    defer researchDecisionLifecycle.Store(0)
    if researchDecisionActive.Load() { return false }
    researchDecisionEpoch.Add(1)
    researchDecisionStop.Store(0)
    researchDecisionNext.Store(0)
    for i := range researchDecisionSlots { researchDecisionSlots[i].published.Store(0) }
    if researchObserveDecisions { researchDecisionActive.Store(true) }
    return true
}
func ResearchSchedulerStop() {
    for !researchDecisionLifecycle.CompareAndSwap(0, 1) { Gosched() }
    defer researchDecisionLifecycle.Store(0)
    researchDecisionActive.Store(false)
    researchDecisionEpoch.Add(1)
    // A late entrant that saw the old active value rechecks before writing.
    // Wait for writers that passed the recheck before publishing completion.
    for researchDecisionWriters.Load() != 0 { Gosched() }
    researchDecisionStop.Store(nanotime())
}
func ResearchSchedulerMark(kind uint8, request uint64) {
    if researchObserveDecisions { researchDecisionRecord(kind, getg(), 0, false, false, false, request) }
}
func ResearchSchedulerSnapshot() (events []ResearchSchedulerEvent, reserved uint64, stopped int64) {
    stopped = researchDecisionStop.Load()
    if stopped == 0 { return nil, researchDecisionNext.Load(), 0 }
    reserved = researchDecisionNext.Load()
    count := reserved
    if count > researchDecisionCapacity { count = researchDecisionCapacity }
    events = make([]ResearchSchedulerEvent, 0, count)
    for i := uint64(0); i < count; i++ {
        slot := &researchDecisionSlots[i]
        if slot.published.Load() != 0 {
            event := slot.event
            if event.StartPC != 0 { event.Function = funcname(findfunc(uintptr(event.StartPC))) }
            events = append(events, event)
        }
    }
    return
}
'''


def runtime_source(text, enabled):
    replace = base.replace_once
    text = replace(text, 'func findRunnable(preemptRequested bool)',
        'const researchObserveDecisions = '+str(enabled).lower()+'\n'+RECORDER+'\nfunc findRunnable(preemptRequested bool)')
    # Annotate every return from findRunnable without changing its values.
    start=text.index('func findRunnable(preemptRequested bool)')
    end=text.index('\nfunc ', start+5)
    function=text[start:end]
    function=replace(function, '\tmp := getg().m\n', '\tmp := getg().m\n\tresearchPending := preemptRequested\n')
    lines=function.splitlines(); sites=[]
    for i,line in enumerate(lines):
        if line.strip().startswith('return gp,'):
            sites.append(i)
    if len(sites) != len(REASONS):
        raise ValueError('findRunnable return sites changed')
    for ordinal,i in reversed(list(enumerate(sites))):
        indent=lines[i][:len(lines[i])-len(lines[i].lstrip())]
        inherited='inheritTime' if 'inheritTime' in lines[i] else 'false'
        fair='false' if ordinal < 2 else 'forceFair'
        lines.insert(i, indent+f'researchDecisionRecord(2, gp, {ordinal+1}, researchPending, {fair}, {inherited}, 0)')
    text=text[:start]+'\n'.join(lines)+'\n'+text[end:]
    text=replace(text, '\tif gp.bubble != nil {\n\t\tsystemstack(func() {\n\t\t\tgp.bubble.changegstatus',
        '\tif oldval == _Gwaiting && newval == _Grunnable { researchDecisionRecord(1, gp, 0, false, false, false, 0) }\n\n\tif gp.bubble != nil {\n\t\tsystemstack(func() {\n\t\t\tgp.bubble.changegstatus')
    text=replace(text, '\tcasgstatus(gp, _Grunnable, _Grunning)\n\tgp.waitsince',
        '\tcasgstatus(gp, _Grunnable, _Grunning)\n\tresearchDecisionRecord(3, gp, 0, false, false, inheritTime, 0)\n\tgp.waitsince')
    text=replace(text, '\tif preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\treturn next.ptr(), true',
        '\tif preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\tif researchObserveDecisions { pp.researchLastLocalPick = 14 }\n\t\treturn next.ptr(), true')
    text=replace(text, '\t\t\tif !preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\t\t\treturn next.ptr(), false',
        '\t\t\tif !preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\t\t\tif researchObserveDecisions { pp.researchLastLocalPick = 16 }\n\t\t\t\treturn next.ptr(), false')
    text=replace(text, '\t\tif atomic.CasRel(&pp.runqhead, h, h+1) { // cas-release, commits consume\n\t\t\treturn gp, false',
        '\t\tif atomic.CasRel(&pp.runqhead, h, h+1) { // cas-release, commits consume\n\t\t\tif researchObserveDecisions { pp.researchLastLocalPick = 15 }\n\t\t\treturn gp, false')
    return text


def prepare(output):
    if output.exists(): raise ValueError('use a fresh decision build directory')
    source=run.ROOT/'analysis/runtime_io_v9_candidate/prepared'
    manifest=run.read(source/'manifest.json')
    for name,digest in manifest['patched_sha256'].items():
        if run.sha(source/name)!=digest: raise ValueError('retained policy changed')
    runtime2=run.ROOT/'analysis/runtime_io_v8_long_waits/go_source/runtime/runtime2.go'
    # Pin the source captured alongside proc.go (also checked against compiler in build).
    output.mkdir(parents=True)
    shutil.copytree(run.HERE/'service',output/'service',ignore=shutil.ignore_patterns('*.trace'))
    main=output/'service/main.go'; text=main.read_text(); replace=base.replace_once
    text=replace(text, '\t\t\t\tconn.request.Store(&id)', '\t\t\t\truntime.ResearchSchedulerMark(4, id)\n\t\t\t\tconn.request.Store(&id)')
    text=replace(text, 'func (s *service) runJob(j job, finishRegion func()) {',
        'func (s *service) runJob(j job, finishRegion func()) {\n\truntime.ResearchSchedulerMark(5, j.id)')
    text=replace(text, '\treturn snapshot\n}', '''
    snapshot["scheduler_observation_enabled"] = runtime.ResearchSchedulerObservationEnabled()
    if includeEvents {
        events, reserved, stopped := runtime.ResearchSchedulerSnapshot()
        snapshot["scheduler_capture"] = map[string]any{
            "events": events, "reserved": reserved, "stopped_ns": stopped,
            "capacity": 262144, "window": "trace_start_to_drained_trace_stop", "schema": 1,
        }
    }
    return snapshot
}''')
    main.write_text(text)
    diag=output/'service/trace_diag.go'; text=diag.read_text()
    text=replace(text, '"runtime/trace"', '"runtime/trace"\n"runtime"')
    text=replace(text, 'type diagnostic struct {', 'type diagnostic struct {\n\tschedulerAnchors []schedulerClockAnchor')
    text=replace(text, 'type clockAnchor struct {', '''type schedulerClockAnchor struct {
    Label string `json:"label"`
    BeforeNS int64 `json:"before_ns"`
    RuntimeNS int64 `json:"runtime_ns"`
    AfterNS int64 `json:"after_ns"`
}

type clockAnchor struct {''')
    text=replace(text, '\tbefore := time.Since(d.s.origin).Nanoseconds()\n\ttrace.Log',
        '\tbeforeScheduler := time.Since(d.s.origin).Nanoseconds()\n\tstampScheduler := runtime.ResearchSchedulerNanoTime()\n\tafterScheduler := time.Since(d.s.origin).Nanoseconds()\n\td.schedulerAnchors = append(d.schedulerAnchors, schedulerClockAnchor{label, beforeScheduler, stampScheduler, afterScheduler})\n\tbefore := time.Since(d.s.origin).Nanoseconds()\n\ttrace.Log')
    text=replace(text, '\td.anchors = nil', '\td.anchors = nil\n\td.schedulerAnchors = nil')
    text=replace(text, '"runtime_capture": d.captureRuntime, "custom_recording": d.recordCustom,',
        '"scheduler_clock_anchors": d.schedulerAnchors,\n\t\t"runtime_capture": d.captureRuntime, "custom_recording": d.recordCustom,')
    text=replace(text, '\td.active.Store(true)\n\td.anchor("start")',
        '\tif !runtime.ResearchSchedulerStart() { d.mu.Unlock(); http.Error(w, "scheduler capture already used", 409); return }\n\td.active.Store(true)\n\td.anchor("start")')
    text=replace(text, '\td.stoppedNS = time.Since(d.s.origin).Nanoseconds()',
        '\truntime.ResearchSchedulerStop()\n\td.stoppedNS = time.Since(d.s.origin).Nanoseconds()')
    diag.write_text(text)
    for mode in ('control','observed'):
        target=output/(mode+'_runtime');target.mkdir()
        for name in manifest['patched_sha256']: shutil.copy2(source/name,target/name)
        (target/'proc.go').write_text(runtime_source((source/'proc.go').read_text(),mode=='observed'))
        (target/'runtime2.go').write_text(replace(runtime2.read_text(),'type p struct {',
            'type p struct {\n\tresearchLastLocalPick uint8'))
        exported=target/'export_test.go'; testtext=exported.read_text()
        testtext=replace(testtext, 'if gp != &gs[index] || inherit != (preferNext && index == 2) {', '''
                if researchObserveDecisions {
                    want := uint8(15)
                    if index == 2 { if preferNext { want = 14 } else { want = 16 } }
                    if pp.researchLastLocalPick != want { throw("research local selection source mismatch") }
                }
                if gp != &gs[index] || inherit != (preferNext && index == 2) {''')
        exported.write_text(testtext)
    (output/'service/scheduler_recorder_test.go').write_text(r'''
package main
import (
    "reflect"
    "runtime"
    "testing"
)
func TestSchedulerRecorderLifecycle(t *testing.T) {
    for _, request := range []uint64{0, 42} {
        if !runtime.ResearchSchedulerStart() { t.Fatal("start refused") }
        runtime.ResearchSchedulerMark(4, request)
        runtime.Gosched()
        runtime.ResearchSchedulerStop()
        events, reserved, stopped := runtime.ResearchSchedulerSnapshot()
        if stopped <= 0 || reserved != uint64(len(events)) { t.Fatal("incomplete published capture") }
        marks := 0
        for i, e := range events {
            if e.Sequence != uint64(i+1) || e.Time > stopped { t.Fatal("invalid sequence/time") }
            if e.Kind == 4 { if e.Request != request { t.Fatal("stale capture marker") }; marks++ }
        }
        if runtime.ResearchSchedulerObservationEnabled() {
            if marks != 1 { t.Fatal("missing identity marker, including request zero") }
        } else if len(events) != 0 { t.Fatal("disabled recorder wrote events") }
        runtime.Gosched()
        again, next, stop := runtime.ResearchSchedulerSnapshot()
        if !reflect.DeepEqual(events, again) || reserved != next || stopped != stop { t.Fatal("stopped capture mutated") }
    }
}
func TestSchedulerRecorderOverflow(t *testing.T) {
    if !runtime.ResearchSchedulerStart() { t.Fatal("start refused") }
    for i := uint64(0); i <= 262144; i++ { runtime.ResearchSchedulerMark(4, i) }
    runtime.ResearchSchedulerStop()
    events, reserved, _ := runtime.ResearchSchedulerSnapshot()
    if runtime.ResearchSchedulerObservationEnabled() {
        if len(events) != 262144 || reserved <= 262144 { t.Fatal("overflow was not explicitly retained") }
    } else if reserved != 0 || len(events) != 0 { t.Fatal("disabled overflow recorder wrote events") }
}
''')
    docker=['ARG COMPILER_IMAGE']
    for mode in ('control','observed'):
        docker += [f'FROM ${{COMPILER_IMAGE}} AS {mode}-build',
            'ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off',
            f'COPY {mode}_runtime/ /usr/local/go/src/runtime/', 'WORKDIR /src', 'COPY service/ ./',
            "RUN go test -v runtime -run '^(TestResearchPendingPreemptFairQueue|TestSchedLocalQueue|TestSchedLocalQueueSteal|TestSchedLocalQueueEmpty|TestPreemption|TestPreemptionGC|TestPreemptionAfterSyscall)$' -count=1 -timeout=180s && go test -v -count=1 ./... && go build -trimpath -o /server ."]
    for mode in ('control','observed'):
        docker += [f'FROM scratch AS {mode}',f'LABEL research.runtime.variant="decision-probe-{mode}"',
            f'COPY --from={mode}-build /server /server','ENTRYPOINT ["/server"]']
    (output/'Dockerfile').write_text('\n'.join(docker)+'\n')
    run.put(output/'prepared.json',dict(compiler_image=IMAGE,base_candidate=manifest,
        runtime2_sha256=run.sha(runtime2),generator_sha256=run.sha(Path(__file__)),eligible_for_full=False,
        sources={str(p.relative_to(output)):run.sha(p) for p in output.rglob('*') if p.is_file()}))


def build(output):
    if run.image_id('golang:1.26.1-alpine')!=IMAGE: raise ValueError('retained compiler differs')
    # Reject a mismatched runtime2.go rather than silently replacing unrelated runtime structure.
    check=run.capture(['docker','run','--rm','--network','none',IMAGE,'sha256sum','/usr/local/go/src/runtime/runtime2.go']).split()[0]
    prepared=run.read(output/'prepared.json')
    if check!=prepared['runtime2_sha256']: raise ValueError('runtime structure source differs from compiler')
    base_build=run.verify_build()
    for name,digest in prepared['sources'].items():
        if run.sha(output/name)!=digest: raise ValueError('prepared source changed')
    images={}
    for mode in ('control','observed'):
        tag='quota-diagnostic-decision-'+mode+':11'
        with (output/(mode+'_build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--build-arg','COMPILER_IMAGE='+IMAGE,
                '--target',mode,'-t',tag,str(output)],stdout=log,stderr=subprocess.STDOUT,check=True)
        images[mode]=run.image_id(tag)
    run.put(output/'build.json',dict(prepared=prepared,images=images,base_build=base_build,
        producer_sha256=run.sha(Path(__file__)),eligible_for_full=False,performance_run=False))
    print('DECISION BUILD COMPLETE:',output/'build.json',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','build'))
    parser.add_argument('--directory',type=Path,default=DEFAULT)
    args=parser.parse_args()
    if args.command=='prepare': prepare(args.directory.resolve())
    else: build(args.directory.resolve())
