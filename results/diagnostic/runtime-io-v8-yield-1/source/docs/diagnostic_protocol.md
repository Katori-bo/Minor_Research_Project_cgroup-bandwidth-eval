# Focused response-timing diagnostic protocol

## Revision 8: worker-yield scheduling comparison, 2026-10-02

Schema 9 and `quota-diagnostic-service:7` add an explicit `WORKER_YIELD=0|1`
option, disabled by default. When enabled, workers call `runtime.Gosched()` once
after each job's work, completion recording and reply publication, before
receiving the next job. No yield occurs inside the hash loop. Health, metrics
and trace status record the treatment, which is frozen in every new trial's
configuration and validated at startup and completion. Invalid settings fail.

The separate `--yield-study` collection is a four-cell factorial: runtime tracing
off/on crossed with worker yielding off/on, four balanced Williams blocks,
16 trials. Custom recording stays ON in every cell so traced requests retain
exact HTTP cleanup-reader association. All other settings match the four-worker
20-second pilot workload: GOMAXPROCS=2, quota=50,000 microseconds per 100,000
microseconds, queue capacity 128, 10-second warmup, pinned original calibration,
burst schedule, client settings, affinities and environmental acceptance.
The memory trace sink remains fixed. Yielding CPU and scheduling overhead are
part of the measured treatment, not removed from accounting.

This experiment tests the v7 cleanup hypothesis; it is not an instrumentation
qualification pilot. It writes study validation, trials, within-block factorial
contrasts, and exact cleanup-reader joins for the eight tracing-on trials.
It cannot write a passing pilot gate or unlock a full collection. All ordinary
new pilot/full configurations keep yielding disabled. Qualification thresholds
and workload remain unchanged. Do not resume the completed failed v7 session.

Schema-7 and schema-8 evidence remains supported for read-only analysis and
revalidation; those sessions cannot resume under schema 9. Sealed attempt
schemas must match their session metadata. Historical matrices omit only the
fields introduced after their recorded schema. Current sources/build must match
their frozen provenance before an interrupted schema-9 collection can resume.

See `runtime_io_v8_yield_commands.md` for the new study and
`runtime_io_v7_cleanup_review.md` for the retained evidence motivating it.

## Revision 7: bounded memory trace sink candidate, 2026-10-02

Schema 8 and `quota-diagnostic-service:6` change only the runtime trace sink for
the next confirmation pilot. Its frozen `trace_storage=memory` configuration
selects `TRACE_STORAGE=memory`. A fixed 64 MiB byte buffer is allocated before
`trace.Start`, outside the workload CPU accounting window. The runtime writer
copies into this buffer without growing it or writing to the trace file during
capture. This adds up to 64 MiB of memory; it does not remove runtime tracing's
scheduler/event overhead or guarantee reduced perturbation. The existing
`TRACE_STORAGE=file` sink remains available for separately documented comparisons.

After final responses drain, the stop clock anchor is recorded and `trace.Stop`
drains the runtime writer. The buffered bytes are then written, synced and closed
before the runner samples final cgroup counters. Final persistence CPU and elapsed
time remain included. The 64 MiB capture bound, zero-overflow requirement, runtime
parse/clock/scheduler validation and all request/lifecycle checks remain intact.
Captured and persisted byte counts must agree; failed persistence invalidates the
attempt. An abrupt process/container exit can lose the in-memory trace; partial
status may report captured bytes while the file is empty. Such an attempt cannot
pass or supply complete scheduler evidence.

The 16 validated v6 component trials associate runtime capture with rejection in
all four repetitions; runtime-only is sufficient to reproduce the disturbance.
All four combined traces locate most summed post-handler Waiting-state overlap
in HTTP `finishRequest -> abortPendingRead -> sync.(*Cond).Wait`. Recorder mutex
overlap is smaller and variable. Runtime-only block 1 has 170 trace writer syscall
entries totaling 1.589 ms of completed syscall state time (maximum 0.087 ms).
These short recorded syscalls do not explain the seconds-long tail or establish
a file-I/O bottleneck. Memory storage is a controlled candidate intervention to
remove those syscall transitions, not an established correction. See
`runtime_io_v7_commands.md` for retained evidence and verification.

The fresh six-trial pilot keeps on/off/off/on four-worker trials and the
one-worker on/off pair, the original workload/quota/queue/GOMAXPROCS/affinities,
environmental acceptance, 10% CPU/client CPU/p99 screens, and 0.1 percentage-point
failure-rate screen unchanged. Collection stops after pilot analysis. A pass is
an instrumentation suitability screen, not proof that trace-file writes caused
the v6 rejections; comparisons across sessions are descriptive. A failure must
be reviewed before further collection. Default workflow directory:
`results/diagnostic/runtime-io-v7-memory-1`.

Existing schema-7 sessions support read-only revalidation with the current
analyzer but cannot be resumed or qualify a schema-8 full run. Raw attempts and
frozen source snapshots are preserved. No live v7 performance result is claimed
by implementation/functional verification alone.

## Revision 6: tracing component isolation, 2026-10-02

Schema 7 and `quota-diagnostic-service:5` add independent `TRACE_RUNTIME` and
`TRACE_CUSTOM` switches behind `TRACE_DIAGNOSTIC=1`. Both default to enabled
for the existing combined trace path. Base request/worker metrics and client
callbacks stay enabled across all component modes; "custom" means the additional
v5 task/connection/I/O instrumentation, including the tracked socket wrapper.
Runtime-only uses the original TCP listener without that wrapper. It retains
only start/stop clock logs and runtime scheduler capture, not custom request logs.
Custom-only retains the wrapper, lifecycle records and annotation call sites;
runtime annotation APIs are inactive without runtime capture.

The separate `--components` protocol is a 16-trial balanced four-mode study.
Blocks: baseline/runtime/combined/custom; runtime/custom/baseline/combined;
custom/combined/runtime/baseline; combined/baseline/custom/runtime. Each mode
appears in each position once and every ordered adjacent pair appears once
within blocks. All trials use the existing four-worker 100 ms period, 50 ms
quota, GOMAXPROCS=2, 128-slot queue, 113.21 RPS burst pattern, 44,000 iterations,
20 s measurement and 10 s warmup. No recalibration or workload relaxation.

All modes retain client outcomes, base worker/handler metrics, CPU counters,
thermal/affinity/power checks and sealed artifacts. Combined mode retains full
v5 lifecycle/scheduler validation. Runtime-only requires a nonempty bounded
capture, valid scheduler chains and consistent clock anchors, but has no
request association or guarantee of recording the final post-handler flush.
Custom-only checks recorded lifecycle/outcome/worker associations, drained final
responses and zero overflow, but has no scheduler evidence or runtime clock map.
Neither reduced mode claims the complete evidence coverage of combined mode.

Component analysis writes per-trial metrics and within-block differences. It
never writes a passing pilot gate and cannot qualify a full collection. The
existing six-trial pilot and its CPU/client CPU/p99/failure-rate thresholds are
unchanged. Its new default session is `runtime-io-v6`; performance suitability
remains unproven until a fresh pilot passes after any chosen correction.

Host monitoring adds /proc process tick deltas keyed by PID and start time,
monotonic interval lengths, one-core-normalized CPU percentages and last-CPU
samples, alongside existing per-core utilization. New/exited/unreadable processes
may lack deltas; last CPU does not attribute the whole interval to a core.
Component runs and v6 pilot trials refuse a running ChatGPT process before
measurement and reject samples observing it during measurement. This is a
specific quiet-host check, not proof that every competing process is absent.
Baloo remains observable and optional to suspend; no automatic process killing.

Old frozen sessions and source snapshots are unchanged and cannot be resumed
with schema 7. See `runtime_io_v6_commands.md` for collection and inspection.

## Revision 5: corrected boundary and outcome validation, 2026-10-01

This revision supersedes revision 4's request analysis and uses schema 6,
`quota-diagnostic-service:4`, and a fresh `results/diagnostic/runtime-io-v5`
session. Existing raw data and frozen sessions remain unchanged. The six-trial
ordering, workload, environmental controls, 10% overhead screen and 0.1 percentage
point failure-rate screen in revision 4 remain unchanged. Collection still stops
after pilot analysis.

The pinned Go 1.26.1 source calls `ConnState(Active)` after `readRequest` returns
when bytes were consumed, including error returns. For a subsequently matched
work handler this brackets the interval from parsing completion to handler entry.
`ConnState(Idle)` follows `finishRequest`; `ConnState(Closed)` follows connection
close/final flushing. Those boundaries run on the connection goroutine. The
analyzer verifies their runtime goroutine identity and ordering against handler,
task, and underlying write events. It reports handler-exit-to-first-write, each
socket write, and handler-exit-to-connection-done intervals, including goroutine
states and other jobs completed during each interval. Client delivery is still
not established by any server write or lifecycle callback.

Before handler entry, accept or the previous Idle marker supplies a **connection
context window**, not a request arrival timestamp. It can include connection
creation, idle time, read-ahead, request reading and parsing. An observed goroutine
creation permits the preceding portion to be labeled not-yet-created. Reads remain
unassociated with request IDs because reads can split or combine HTTP messages
and background reads can run on another goroutine. Buffered/pipelined requests
may have no separate Active callback; that parsing boundary is explicitly
unavailable. No socket read is treated as a full request. A control request on a
reused connection clears the previous work association at Idle/Closed; request ID
zero is valid and separate from an unknown association.

`go_running_ns` means **Go runtime Running state**, not measured time executing
on a CPU. The OS may deschedule or throttle the thread while Go still records it
as Running. Runnable, network waiting, other synchronization/waiting, and syscall
state durations are reported separately. Unknown scheduler coverage invalidates
an observed interval; it cannot silently become a mechanism claim. Runtime
scheduler transition chains, initial states, task begin/end, worker task identity,
connection log matching, clock mapping and capture coverage are validated. The
two bracketed clock anchors must agree within an interval no wider than 1 ms.
Durations use their own clocks; no client/server absolute timestamp subtraction
is introduced. The interval tables overlap and must not be summed.

Every client outcome is retained in `trace_requests.json`. Observed successful,
rejected, timed-out and other failed requests must have matching handler entry,
exit, admission/rejection and final connection boundaries. Every admitted job
must have worker evidence even if its client timed out. A failed request never
observed at the server is explicitly unobserved and has no inferred server state.
A client success or completed rejection cannot use that exception. Application
and socket write errors remain outcomes. Missing evidence, duplicate events,
broken order/association, unknown required scheduler state, incomplete runtime
trace or capture overflow fails the attempt. Validation recomputes request analysis
from the retained scheduler and I/O evidence rather than accepting a summary flag.

The runner drains workers, handlers **and pending final responses** before
stopping the trace. The stop endpoint rejects pending responses. Idle/background
reads spanning the capture endpoints may be absent; their framing and arrival
association remain unresolved, and they are not used to prove completeness of a
request byte timeline. Storage retains the existing 64 MiB runtime trace and
30,000 I/O event caps; overflow invalidates the attempt and subsequent runtime
chunks are discarded. Parser output is streamed; compact scheduler evidence is
retained as `trace_scheduler.json` and covered by the attempt seal.

Matched slow and typical successes appear in `trace_report.md`; complete outcomes,
per-interval state durations, other-job counts and sampled IDs, connection reuse,
read context and write errors remain in `trace_requests.json`. The largest
connection context window cannot be called a request delay without establishing
arrival framing. A Go Running interval cannot alone distinguish CPU execution
from OS throttling. A missing request-arrival boundary or client-delivery boundary
must be named explicitly. No intervention or cause is selected automatically.

Build and tests are allowed before the quiet window. See
[verification](runtime_io_v5_verification.md) for functional verification and
remaining limits. From the project root, launch only when the measurement window
is quiet:

```bash
bash diagnostic/run_all.sh --directory results/diagnostic/runtime-io-v5
bash diagnostic/run_all.sh status --directory results/diagnostic/runtime-io-v5
```

## Revision 4: bounded runtime and server I/O pilot, 2026-10-01

The completed six-trial response-write pilot is preserved in
`results/diagnostic/response-write-v3/pilot`. Its matched-request review is
`analysis/response_write_pilot/report.md`. Four-worker slow requests spent
91–95% of elapsed time outside the observed handler span. The final application
Write took microseconds, but the application Write return did not establish
delivery. One trial rejected 125 requests; its lower successful-request p99
does not establish an improvement. Request 725 paused 1.2 seconds between
handler resume and Write start while other jobs completed. The new pilot asks
where the remaining gap lies and what each affected server goroutine was doing.

### Trace boundaries and interpretation

The pinned Go 1.26.1 `net/http` HTTP/1.x server calls `conn.readRequest`, runs
the handler on the connection goroutine, then calls `response.finishRequest`.
`finishRequest` flushes its buffered writer and connection writer after the
handler returns. `conn.finalFlush` also flushes on connection teardown. The
client's `WroteRequest` and `GotFirstResponseByte` callbacks remain client-local.
The server records connection accept, underlying `net.Conn.Read`/`Write` start
and end, handler entry and exit, and existing worker/handler stages. The same
connection ID is retained on keep-alive reuse. Writes carry the current
HTTP/1 request ID; the sequential HTTP/1 handler loop supports that association
for this plain-HTTP workload. A single read can contain part of one request or
multiple requests, so reads remain connection-level evidence and cannot prove
a particular request arrived at a specific read boundary. A socket Write
return proves only that the local `net.Conn` accepted bytes, not peer receipt.

The switch `TRACE_DIAGNOSTIC=1` exposes `/trace/start`, `/trace/stop` and
`/trace/status`. It records runtime tasks for each request, worker and handler
regions, plus runtime scheduler state transitions. Go 1.26.1 parsed trace
states distinguish executing (`Running`), waiting to run (`Runnable`),
`Waiting` with network reason, other waits, and syscall time. An unknown state
is reported as unknown. Two trace clock logs bracketed by service-local
monotonic reads map runtime and service timestamps with an explicit interval;
the parser rejects inconsistent or wide mappings. Client and server absolute
timestamps are never subtracted. Request-level comparisons use client
durations and server/runtime durations separately.

The runtime trace file is capped at 64 MiB and server I/O events at 30,000.
Overflow, missing associations, inconsistent event order or clock mapping,
invalid trace parse, or missing successful-request evidence fails an attempt.
The failed attempt and any partial trace are retained. Each accepted attempt
records source hashes, pinned runtime version, trace start/stop offsets, event
and file sizes, completeness, and all outcomes. Disabled trials produce no
trace file or trace status.

### Frozen focused pilot

Use 100 ms period, 50 ms quota, `GOMAXPROCS=2`, the existing affinity and power
gates, bursty 113.21 requests/s mean, 44,000 SHA iterations, 128 queue slots,
and 5-second low/high phases. Each trial has a 10-second warmup and 20-second
measurement. The order is four-worker trace on/off/off/on, then one-worker
trace on/off. Handler timing and client HTTP tracing remain enabled in all six,
isolating the added runtime/I/O mode. Trace starts after warmup and reset and
stops after the client and service drain. Collection stops after this pilot's
analysis; pilot observations are not research estimates.

The overhead screen compares the median of the two four-worker on trials with
the two off trials. Service CPU microseconds per completed job, client CPU
microseconds per scheduled request, and successful-request p99 must each have
an on/off ratio at most 1.10. All attempts must validate; on trials must have
complete runtime traces, event association and at least 99% usable client
traces. The maximum on-trial rejection plus timeout fraction may exceed the
maximum off-trial fraction by no more than 0.1 percentage point. Report raw
rejection, timeout and throughput counts even if this screen passes. A lower
successful-request p99 with more failures is insufficient to claim a speedup.

Select the slowest 1% and equal-count typical successful requests by matching
request IDs. For each, report handler and worker goroutine state durations,
server stage times, connection ID/reuse, socket writes after handler exit,
write errors, clock uncertainty and unresolved read/delivery boundaries. If a
dominant interval is observable, propose one controlled intervention with a
specific predicted change. Otherwise name the missing boundary. No kernel
trace or full matrix is authorized by this pilot protocol.

## Revision 3: response-write pilot, 2026-09-30

The completed revision-2 session is `results/diagnostic/all-in-one-power-fix`. Its 20 full trials passed validation. The request-ID audit in `diagnostic/analysis/completed_report.md` shows that the slowest 1% of successful 100 ms/four-worker requests averaged 4.36 s end to end and 4.23 s outside the four recorded server stages. All 338 of those selected requests were scheduled during the high-rate half of a burst. Dispatch lag averaged 0.56 ms. The client had written each request and was still waiting for the first response byte. This locates a gap, not its cause.

The new server events record handler resume, actual `ResponseWriter.Write` start/end, byte count, write-call count, write error, and a final handler exit marker using one service-local monotonic origin. Formatting remains outside the measured Write call and inside resume-to-write. The exit marker is recorded after acquiring the final bookkeeping mutex and appending the event; it includes that lock wait. It precedes unlocking and actual function return, so it is a marker rather than a claim to measure the return itself. Event publication and the active-handler decrement share the mutex, so drained metrics cannot omit the marker. Write errors are retained as outcomes, including for unsuccessful client requests.

Client traces retain request write, first byte, and body completion. Request IDs join records; absolute client/server clocks must never be subtracted. Go `ResponseWriter.Write` may buffer output, and neither its completion nor the exit marker proves client delivery. Report `e2e_minus_handler_span` as a signed per-request duration difference, not a partition of latency. Client completion can overlap server cleanup, so negative values are retained and counted rather than rejected or clamped. A positive difference still combines pre-handler delivery, unmeasured cleanup/final flush, transport, dispatch and client completion; these stages cannot be separated by this instrument alone.

The focused pilot has six 20-second measurements with 10-second warmup: four 100 ms/four-worker trials with instrumentation on/off/off/on, then 100 ms/one-worker on/off. Both use the existing bursty rate, 44,000 SHA iterations, 0.5 CPU quota, `GOMAXPROCS=2`, original affinity and environmental gates. The four-worker on/off pairs screen the median ratio of service CPU per completed job, client CPU per scheduled request, and p99 end-to-end latency; all three must be at most 1.10. All six attempts must validate; on trials require at least 99% usable client traces and complete server timing. The one-worker pair is a mechanism comparison, not a precise overhead estimate. Pilot data are excluded from any later research estimate.

Interpret the pilot by joining request IDs and comparing the slowest 1% with typical requests. A large resume-to-write, write-call or write-to-exit interval locates elapsed time at that boundary, including possible descheduling. If the measured handler span is short while the client waits seconds, pre-handler delivery and net/http's flush or transport path remain unresolved. A runtime trace would ask whether runnable server goroutines wait to execute or block in network I/O; a transport trace would ask when request/response bytes reach the socket path. Define clock alignment and request/connection correlation before adding either trace. Aggregate cgroup throttling supports only a condition-level association. Do not choose a mitigation from this pilot alone.

Proceed to a larger matrix only after the pilot passes the unchanged technical/overhead gates, both instrumented four-worker trials reproduce the long first-byte wait, and matching request IDs show which new interval absorbs it. If it remains outside the observed handler span, prepare the targeted trace first. Failure to reproduce or an overhead-screen failure requires review; a passing overhead screen alone never establishes a cause. The launcher now defaults to pilot collection and analysis only, with sleep inhibition and persistent logs. Full collection requires an explicit `--full` invocation after review.

The new source and Docker image use schema 4 and `quota-diagnostic-service:2`. Existing revision-2 sessions and their sealed source copies remain untouched. Build and analyze before starting a new pilot directory; do not resume a revision-2 session with revision-3 code.

## Archived revision 2 specification

The following describes the already completed collection. Revision 3 above supersedes its pilot matrix, added timing boundaries and automatic full-collection behavior.

Revision 2, 2026-09-28. Written before diagnostic collection. This is a separate session from the completed 300-trial study and 50-trial follow-up. Its purpose is to locate the large client-observed delay remaining after subtracting server queue wait and elapsed SHA processing. No mitigation or mechanism is assumed in advance.

## Existing evidence and competing explanations

The completed follow-up shows that, at 100 ms quota period and four workers under bursty load, the mean trial p99 end-to-end latency is 4131.7 ms. The mean trial p99 of the **per-request** remainder is 4085.7 ms; among each trial's slowest 1% successful requests, the mean remainder share is 97.8%. These two p99 values do not necessarily select the same requests. The source audit is `diagnostic/analysis/existing_report.md` and its 50-trial CSV. All original attempt file hashes and request/event ID matches were checked.

Possible locations include client connection/request preparation, server handler work before admission, a handler waiting to resume after the SHA worker finishes, response writing and transport, and client response-body completion. These are hypotheses, not findings. The original service starts server timing immediately before enqueue and stops it immediately after the SHA computation. The client times through full body consumption.

## Frozen diagnostic matrix

The research matrix is 100/250 ms periods × one/four application workers × five repetitions, all at 0.5 CPU (`quota_us = period_us / 2`). Each trial uses `GOMAXPROCS=2`, original 44,000 SHA-256 iterations, original high rate 113.21/s, 5-second low/high burst phases at 0.5/1.5 times the mean, 20-second warmup and 60-second measurement. The four conditions have 20 trials in one random order seeded with 20260928. Pilot data are excluded from research estimates.

The diagnostic pilot has seven 20-second measurements with 10-second warmup: four 100 ms/four-worker overhead trials in on/off/off/on order, and one instrumented trial of each remaining condition. On/off switches both server timing and client HTTP tracing. The pilot must validate all attempts and observe server timing and at least 99% usable client traces among successful responses in each instrumented trial. Three median on/off ratios must each be no greater than 1.10: service cgroup CPU microseconds per completed job, load-generator process CPU microseconds per scheduled request, and client end-to-end p99 latency. Two observations per arm give a coarse perturbation screen, not proof of negligible overhead. A failed screen stops collection for review.

## New timing boundaries

Server: handler entry → admission, admission → worker start, worker start → SHA completion, and SHA completion → handler resume. These server durations use one monotonic clock. The existing worker events and new handler events retain request IDs and offsets from one service-local origin. Response headers duplicate durations and are checked against server events. The handler-resume timestamp precedes header formatting and response writing.

Client: dispatched request start → connection acquired, request written, first response byte, headers returned, and body fully consumed. `net/http/httptrace` records the first three boundaries; the client records the latter two. Trace callbacks use a separate synchronized recorder, frozen before a request result is published. Missing, repeated or late callbacks are classified in each raw request; an unusual callback order does not invalidate an otherwise sound trial. The analyzer reports trace coverage and leaves client trace quantiles unavailable below 99% usable successful requests. These offsets use one client-local clock. Never subtract an absolute server timestamp from a client timestamp. The per-request remainder after all four server durations still contains dispatch, transport, response writing and client completion. Even if it narrows substantially, the measurement does not by itself distinguish kernel throttling from Go scheduling; cgroup counters are aggregate corroborating evidence.

## Outcomes and analysis

Retain every request and server event. Report per-trial nearest-rank p50/p95/p99 of end-to-end and each measured duration, plus rejection and timeout fractions, throughput, cgroup throttling, sampled queue depth, and each repetition. Derive residual durations per successful request; never add or subtract independently computed quantiles. For the four-cell comparison, use the same interaction definition as the follow-up and bootstrap five independent trial values per cell with 10,000 resamples and fixed seed 761. Analyze residual, handler wait, client request-to-first-byte and end-to-end metrics separately. Any mechanistic claim requires matching the recorded stages and environmental/cgroup evidence. Failed application requests remain outcomes, not exclusions.

## Environment, integrity and operation

Reuse the follow-up's power, temperature, CPU topology, affinity, quota, zero `cpu.max.burst`, monitor coverage and generator-lag checks. Both clients and server use the same affinities as the completed follow-up. The launcher shares `.experiment.lock`; it builds and runs tests, then the pilot, then full collection only after the pilot passes. It uses systemd sleep inhibition when available. Sessions are under `results/diagnostic/`, with separate pilot/full raw attempts, numbered retries, logs, status and completion markers. Existing sessions cannot be rebuilt or have source/protocol changed on resume. No existing experiment evidence is overwritten.

Allow roughly 2–4 hours including settling, cooling and retries. The mathematical minimum for the 20 full trials is 20 × (60 s settling + 20 s warmup + 60 s measurement) = 46.7 minutes, plus initial idle, pilot and drains. Prepare while the laptop is in use; start the unattended performance batch only when it can remain plugged in, on Balanced, with its lid open and other active applications closed.
