# Step 2: pending-preemption fairness candidate

Date: 2026-10-02. An isolated source correction has been prepared and
functionally checked. Its performance and causal explanation remain unqualified.

## What we learned

The saved events and pinned Go 1.26.1 source support a specific scheduling
hypothesis: ready work can lose turns to repeated local handoffs, and a pending
preemption can be cleared when a goroutine parks before it is interrupted.
Trace maintenance can supply additional interruptions, changing that behavior.
The runtime's queue positions and preemption flags are absent from our traces,
so this is not proof that this flag-loss path caused each observed long wait.

This is closely related to a reported Go runtime problem. A Go maintainer's
[issue #73964](https://github.com/golang/go/issues/73964) describes short-running
goroutines repeatedly receiving `runnext` preference while preemption requests
may go unserved as the goroutine parks. Its example uses short sleeps; ours
involves HTTP and channel handoffs under CPU quota. The issue proposes honoring
pending preemption at a scheduling boundary or periodically bypassing `runnext`.
The analogy strengthens the hypothesis, but does not establish identical causes.

For the paper, the contribution should concern how quota period, worker
concurrency and bursts interact with this behavior, including delay/admission/
rejection tradeoffs and a tested intervention. Do not claim discovery of an
otherwise unknown Go starvation mechanism. V8 still examines one quota/worker
configuration, so a result here does not explain the entire original matrix.

## Additional direct evidence from all eight saved traces

The new inspector matches a strict sequence: a goroutine wakes another while
running on a P, then parks or yields, and the target is the next recorded
goroutine dispatched on that same P. The wake must occur inside the preceding
running segment. Census snapshots do not restart a segment. This is observed
ordering, not proof of the `runnext` slot or inherited scheduler tick.

| Non-yielded block | All dispatches in selected long wait | Matched worker-reply handoffs | Dispatches following no-P wakeups |
|---|---:|---:|---:|
| 1 | 1404 | 289 | 39 |
| 2 | 1688 | 357 | 42 |
| 3 | 1329 | 274 | 16 |
| 4 | 1543 | 337 | 19 |

Hundreds of direct worker-to-HTTP handoffs continue while the selected
network-ready HTTP goroutine waits. These dispatch-window counts have a
different membership rule from step 1's wake-window cohorts; do not subtract
them to infer missing or queued requests. Matches are a conservative subset,
not an exhaustive reconstruction of channel activity or queue choices.

All eight decoded inputs match the hashes from the validated step 1 review.
[Handoff evidence](../analysis/runtime_io_v9_candidate/handoffs/summary.json)
retains source event excerpts, and
[its provenance](../analysis/runtime_io_v9_candidate/handoffs/source_hashes.json)
connects back to the sealed trials.

## The precise source decision

In the pinned source:

1. `preemptone` sets the running goroutine's preemption request and, when async
   preemption is enabled, the P's `preempt` flag (`proc.go`, lines 6867–6891).
2. At scheduler entry, `schedule` clears `pp.preempt` before calling
   `findRunnable` (lines 4154–4164).
3. `findRunnable` normally checks global work every 61 scheduling ticks before
   considering the local queue (line 3443). Local `runnext` work has preference
   and inherits a time slice (`runqget`, line 7598).
4. `execute` clears the selected goroutine's `preempt` flag and advances the
   scheduler tick only for a fresh time slice (lines 3347–3350).

Together, these decisions permit a pending interruption to be discarded at a
natural scheduling boundary without deliberately serving older ready work.
Whether that occurs often enough to explain our long waits is the causal
question the candidate tests. The source also has normal fairness and sysmon
preemption mechanisms; the problem is not absence of those mechanisms.

Source: [exact retained proc.go](../analysis/runtime_io_v8_long_waits/go_source/runtime/proc.go).

## The candidate correction

`pending-preemption-fairness-v1` changes the scheduler only when a pending
P-level preemption is seen at scheduler entry:

- Preserve the flag's value before the existing clear.
- At the next ordinary work-selection point, check global runnable work even
  if the 61-tick check is not due.
- If no global work is selected, prefer the oldest regular local-queue entry
  over the `runnext` slot for this turn.
- If only `runnext` exists, run it with a fresh time slice; do not strand it.
- Keep the normal `runnext` policy for other selections and retain trace-reader,
  GC and safe-point priorities. This does not impose a hard latency bound.

The candidate adds no sleep or per-job yield. It changes no SHA iterations,
worker count, GOMAXPROCS, CPU budget, queue capacity, offered load or admission
rule. The existing per-job yield option remains off for the proposed comparison.

This targets a runtime fairness decision. It is a different intervention from
moving trace output into memory or yielding after every job. It may still expose
the burst to the bounded queue earlier, increasing rejection. That would count
against a solution claim even if HTTP readiness waits improve.

The [reviewable patch](../analysis/runtime_io_v9_candidate/prepared/runtime_fairness.patch)
and [manifest](../analysis/runtime_io_v9_candidate/prepared/manifest.json) were
generated from exact source hashes from the retained compiler image. The
[generator](../diagnostic/runtime_fairness/prepare.py) rejects different source
content and existing output directories. It modifies only derived copies.
No installed runtime, production image, build seal or sealed trial was changed.

## Functional verification

- Seven targeted runtime tests passed: queue ordering, queue stealing, empty
  queue behavior, preemption, GC preemption, syscall preemption, and the new
  fairness-policy test.
- The new runtime test checks normal preference, fairness preference, FIFO
  order, ring wraparound, fresh versus inherited time slices, no duplicated/lost
  entries, and a sole `runnext` goroutine making progress.
- All 18 service tests passed on both stock and patched Go: identical SHA work,
  reply publication, timeout accounting, HTTP connection reuse and final flush,
  runtime/custom recording modes, trace persistence, and yield settings.
- All 61 Python diagnostic tests passed, including adversarial handoff matching.

The first service test invocation failed trace-start fixtures because the
read-only container had no writable `/runtime.trace`. A dedicated writable test
file resolved that setup problem; both final stock and patched service runs
passed. The initial log is retained rather than rewritten.

[Verification record](../analysis/runtime_io_v9_candidate/verification.json).
These are correctness checks; their timings are not research measurements.
The full Go runtime suite and race-enabled suite have not been run. The patch
requires additional review and performance testing before any solution claim.

## Step 3 comparison to prepare next

Use a new frozen session comparing stock/patched runtime crossed with runtime
tracing off/on, with four balanced blocks as in v8. Keep the original calibrated
work, four workers, GOMAXPROCS=2, 50,000/100,000 µs quota, 128-slot queue, client
burst pattern, duration, affinity and environmental controls. Keep worker
yielding off in every cell. No workload tuning or recalibration.

Two questions must stay separate:

1. **Correction effect:** patched versus stock under the same tracing setting.
   Does it shorten network-ready waits and HTTP cleanup stalls, and what happens
   to rejection, timeout/error counts, throughput, queue waiting and CPU/job?
2. **Tracing perturbation:** trace on versus off within each runtime. Does
   tracing still change the delay/admission/rejection pattern?

A scheduling improvement in both tracing settings would support a broader
runtime interaction. An improvement confined to trace-on would suggest a
tracing-dependent interaction. No improvement would weaken this particular
pending-preemption correction; it would not invalidate the observed ready waits.
An improvement accompanied by worse failures or throughput is a tradeoff,
not an accepted solution.

Retain the existing numeric acceptance rules: on/off service CPU/job, client
CPU/request and successful p99 ratios at most 1.10, complete evidence and at
least 99% client trace coverage, and the maximum trace-on rejection-plus-timeout
fraction no more than 0.001 above the maximum trace-off fraction. Report
throughput and all outcomes alongside those screens. A balanced mechanism study
does not itself produce the existing six-trial qualification gate.

Keep the original stock/tracing-off reference visible when assessing the
solution; a patched baseline cannot silently replace the original behavior.
Any later research collection using this runtime would be an explicit treatment,
not an unmodified replication of the original matrix.

Before launch, the runner still needs separate stock/candidate image identities,
patch provenance and version checks; the images and launch protocol must be
prepared and verified. The patch has not been integrated into the performance
runner in this step. Collection must retain the external-terminal quiet-host,
thermal and provenance controls. No quota performance run was launched here.
