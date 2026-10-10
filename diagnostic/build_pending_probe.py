#!/usr/bin/env python3
"""Build a paired observation probe without changing the retained candidate."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import build_fairness
import run

IMAGE=build_fairness.prepare.IMAGE
NAMES=('pending_seen','trace_reader_before_ordinary','gc_worker_before_ordinary',
       'ordinary_fairness_reached','global_selected','regular_local_selected','sole_runnext_selected')
DEFAULT=run.ROOT/'analysis/runtime_io_v10_pending_probe_verified_build'


def replace_once(text,old,new):
    if text.count(old)!=1:raise ValueError('expected exactly one source site: '+old[:70])
    return text.replace(old,new,1)


def runtime_source(text,enabled):
    text=replace_once(text,'func findRunnable(preemptRequested bool)',
        'const researchObservePending = '+str(enabled).lower()+'''\n\nvar researchPendingCounts [7]atomic.Uint64

// ResearchPendingPreemptionStats returns cumulative diagnostic counts. This
// experimental API is present only in the separately built observation probe.
func ResearchPendingPreemptionStats() (result [7]uint64) {
    if !researchObservePending { return }
    for i := range result { result[i] = researchPendingCounts[i].Load() }
    return
}

func ResearchPendingPreemptionObservationEnabled() bool { return researchObservePending }

func findRunnable(preemptRequested bool)''')
    text=replace_once(text,'preemptRequested := pp.preempt\n\tpp.preempt = false',
        'preemptRequested := pp.preempt\n\tif researchObservePending && preemptRequested { researchPendingCounts[0].Add(1) }\n\tpp.preempt = false')
    text=replace_once(text,'return gp, false, true\n\t\t}\n\t}\n\n\t// Try to schedule a GC worker.',
        'if researchObservePending && preemptRequested { researchPendingCounts[1].Add(1) }\n\t\t\treturn gp, false, true\n\t\t}\n\t}\n\n\t// Try to schedule a GC worker.')
    text=replace_once(text,'gp, tnow := gcController.findRunnableGCWorker(pp, now)\n\t\tif gp != nil {',
        'gp, tnow := gcController.findRunnableGCWorker(pp, now)\n\t\tif gp != nil {\n\t\t\tif researchObservePending && preemptRequested { researchPendingCounts[2].Add(1) }')
    text=replace_once(text,'forceFair := preemptRequested\n\tpreemptRequested = false',
        'forceFair := preemptRequested\n\tif researchObservePending && forceFair { researchPendingCounts[3].Add(1) }\n\tpreemptRequested = false')
    text=replace_once(text,'if (forceFair || pp.schedtick%61 == 0) && !sched.runq.empty() {\n\t\tlock(&sched.lock)\n\t\tgp := globrunqget()\n\t\tunlock(&sched.lock)\n\t\tif gp != nil {',
        'if (forceFair || pp.schedtick%61 == 0) && !sched.runq.empty() {\n\t\tlock(&sched.lock)\n\t\tgp := globrunqget()\n\t\tunlock(&sched.lock)\n\t\tif gp != nil {\n\t\t\tif researchObservePending && forceFair { researchPendingCounts[4].Add(1) }')
    text=replace_once(text,'if !preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\t\t\treturn next.ptr(), false',
        'if !preferNext && next != 0 && pp.runnext.cas(next, 0) {\n\t\t\t\tif researchObservePending { researchPendingCounts[6].Add(1) }\n\t\t\t\treturn next.ptr(), false')
    # Match only the regular local FIFO return inside runqgetPolicy.
    before, function=text.split('func runqgetPolicy(pp *p, preferNext bool)',1)
    function=replace_once(function,'if atomic.CasRel(&pp.runqhead, h, h+1) { // cas-release, commits consume\n\t\t\treturn gp, false',
        'if atomic.CasRel(&pp.runqhead, h, h+1) { // cas-release, commits consume\n\t\t\tif researchObservePending && !preferNext { researchPendingCounts[5].Add(1) }\n\t\t\treturn gp, false')
    return before+'func runqgetPolicy(pp *p, preferNext bool)'+function


def prepare(output):
    if output.exists():raise ValueError('use a fresh probe build directory')
    source=run.ROOT/'analysis/runtime_io_v9_candidate/prepared'
    record=run.read(source/'manifest.json')
    for name,digest in record['patched_sha256'].items():
        if run.sha(source/name)!=digest:raise ValueError('retained candidate changed')
    output.mkdir(parents=True)
    shutil.copytree(run.HERE/'service',output/'service',ignore=shutil.ignore_patterns('*.trace'))
    main=output/'service/main.go';text=main.read_text()
    text=replace_once(text,'type service struct {','type service struct {\n\tschedulerBaseline [7]uint64')
    text=replace_once(text,'\tif s.diag != nil {\n\t\tsnapshot["runtime_trace_storage"]', '''
    snapshot["scheduler_observation_enabled"] = runtime.ResearchPendingPreemptionObservationEnabled()
    raw := runtime.ResearchPendingPreemptionStats()
    names := []string{"'''+ '","'.join(NAMES)+'''"}
    counters := make(map[string]uint64, len(raw))
    for i, value := range raw { counters[names[i]] = value - s.schedulerBaseline[i] }
    snapshot["scheduler_counters"] = counters
    snapshot["scheduler_counter_window"] = "reset_to_snapshot_including_control_and_drain"
    if s.diag != nil {
        snapshot["runtime_trace_storage"]''')
    text=replace_once(text,'\ts.origin = time.Now()\n\tif s.diag != nil {',
        '\ts.origin = time.Now()\n\ts.schedulerBaseline = runtime.ResearchPendingPreemptionStats()\n\tif s.diag != nil {')
    main.write_text(text)
    for mode in ('control','observed'):
        runtime=output/(mode+'_runtime');runtime.mkdir()
        for name in record['patched_sha256']:shutil.copy2(source/name,runtime/name)
        (runtime/'proc.go').write_text(runtime_source((source/'proc.go').read_text(),mode=='observed'))
        with (runtime/'export_test.go').open('a') as stream:stream.write('''
func ResearchProbeQueueCounters() (before, after [7]uint64) {
    before = ResearchPendingPreemptionStats()
    RunResearchFairQueueTest()
    after = ResearchPendingPreemptionStats()
    return
}
''')
        with (runtime/'proc_test.go').open('a') as stream:stream.write('''
func TestResearchProbeCounters(t *testing.T) {
    before, after := runtime.ResearchProbeQueueCounters()
    if runtime.ResearchPendingPreemptionObservationEnabled() {
        if after[5]-before[5] < 4 || after[6]-before[6] < 2 { t.Fatal("probe missed actual FIFO/fallback decisions") }
    } else if before != [7]uint64{} || after != [7]uint64{} { t.Fatal("disabled observer counted events") }
}
''')
    docker=['ARG COMPILER_IMAGE']
    for mode in ('control','observed'):
        docker += [f'FROM ${{COMPILER_IMAGE}} AS {mode}-build',
            'ENV CGO_ENABLED=0 GOTOOLCHAIN=local GOENV=off',
            f'COPY {mode}_runtime/proc.go /usr/local/go/src/runtime/proc.go',
            f'COPY {mode}_runtime/export_test.go /usr/local/go/src/runtime/export_test.go',
            f'COPY {mode}_runtime/proc_test.go /usr/local/go/src/runtime/proc_test.go',
            'WORKDIR /src','COPY service/ ./',
            "RUN go test -v runtime -run '^(TestResearchProbeCounters|TestResearchPendingPreemptFairQueue|TestSchedLocalQueue|TestSchedLocalQueueSteal|TestSchedLocalQueueEmpty|TestPreemption|TestPreemptionGC|TestPreemptionAfterSyscall)$' -count=1 -timeout=180s && go test -v -count=1 ./... && go build -trimpath -o /server ."]
    for mode in ('control','observed'):
        docker += [f'FROM scratch AS {mode}',f'LABEL research.runtime.variant="pending-probe-{mode}"',
                   f'COPY --from={mode}-build /server /server','ENTRYPOINT ["/server"]']
    (output/'Dockerfile').write_text('\n'.join(docker)+'\n')
    run.put(output/'prepared.json',dict(compiler_image=IMAGE,base_candidate=record,counter_names=NAMES,
        generator_sha256=run.sha(Path(__file__)),eligible_for_full=False,
        sources={str(p.relative_to(output)):run.sha(p) for p in output.rglob('*') if p.is_file()}))
    return output


def build(output):
    if run.image_id('golang:1.26.1-alpine')!=IMAGE:raise ValueError('retained compiler differs')
    base=run.verify_build()
    prepared=run.read(output/'prepared.json')
    for name,digest in prepared['sources'].items():
        if run.sha(output/name)!=digest:raise ValueError('probe source changed')
    images={}
    for mode in ('control','observed'):
        tag='quota-diagnostic-pending-'+mode+':10'
        with (output/(mode+'_build.log')).open('w') as log:
            subprocess.run(['docker','build','--network','none','--build-arg',
                            'COMPILER_IMAGE='+IMAGE,'--target',mode,'-t',tag,str(output)],
                           stdout=log,stderr=subprocess.STDOUT,check=True)
        images[mode]=run.image_id(tag)
    run.put(output/'build.json',dict(prepared=prepared,images=images,base_build=base,
        producer_sha256=run.sha(Path(__file__)),eligible_for_full=False,performance_run=False))
    print('PROBE BUILD COMPLETE:',output/'build.json',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','build'))
    parser.add_argument('--directory',type=Path,default=DEFAULT)
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.directory.resolve())
    else:build(args.directory.resolve())
