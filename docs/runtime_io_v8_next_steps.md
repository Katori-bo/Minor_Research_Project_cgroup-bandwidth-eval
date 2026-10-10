# Investigation map after the v8 yielding study

Date: 2026-10-02. Planning from retained evidence; no new measurement launched.

## What we are trying to explain

Why does worker yielding remove most HTTP cleanup scheduling stalls while the
128-job queue still fills and rejection stays near 4%? Why do the non-yielding,
tracing-off cells sometimes reject less despite much worse successful latency?

Working hypothesis: non-yielding workers delay HTTP progress, spreading the
effective admissions of offered bursts. Yielding restores HTTP progress and
exposes the bounded queue to the burst sooner. This would explain a transfer of
waiting into the work queue, but the complete mechanism remains unproved.

## Landmarks already established

- All 16 trials completed and the saved validation reports no issues.
- In the traced comparison, the median of trial p99 cleanup waits falls from
  447.298 ms to 0.076192 ms with yielding. Some long outliers remain.
- Yielding cells reject 3.753–4.327% across the two tracing modes; all reach the
  queue capacity. Their 742 rejections belong to requests scheduled during the
  high-rate half of the client burst cycle.
- With tracing, median trial successful p99 falls from 2,556.092 to 1,002.283 ms,
  while median trial successful p50 rises from 177.852 to 415.437 ms. Median
  trial p50 queue wait rises from 0.007425 to 353.863 ms.
- CPU per completed job differs by less than 1% between mode medians. This makes
  a large increase in CPU cost alone an incomplete explanation.

The burst labels are client scheduling labels, not server arrival timestamps.
These observations establish a scheduling effect and queue saturation; they do
not establish the exact runtime internals or a qualified instrumentation fix.

## Route 1: reconstruct the queue using existing data

This is the immediate next action, before any new performance run.

1. Build one request ledger per trial from `server_metrics.json`,
   `trace_status.json` and `loadgen.json`. Join by request ID, retaining ID zero.
   Include admitted and rejected requests, eventual worker completions and
   connection reuse. Audit duplicates, missing joins and counter reconciliation.
2. Plot server-local cumulative handler entries, admissions, worker starts,
   completions and rejections. Add short-window rates at 10, 50 and 100 ms;
   preserve individual repetitions and balanced within-block comparisons.
3. Estimate admitted-but-not-started work and active work separately. Track
   when the queue approaches capacity, when rejection begins, and when it drains.
4. Compare all four modes for admission clustering, work-start gaps, completion
   gaps, queue waiting and work-completion-to-handler-resume waiting. For the
   eight traced cells, inspect reader scheduling around the same server windows.

Timestamp limits matter: `admission_ns` is sampled before the channel send,
`worker_start_ns` after dequeue, and custom admission/rejection marks after the
admission decision and mutex unlock. Sampled depth is not continuous occupancy.
The timestamp-based queue estimate can therefore include handoff gaps and cannot
be called exact instantaneous channel length. Report ordering uncertainty and
compare estimates against sampled depths and aggregate counters. Do not silently
clamp a contradiction into the range 0–128.

Connection reads have unknown HTTP framing and cannot automatically be treated
as one request each. Successful handler timing excludes rejected requests, so
use the custom lifecycle events to keep rejections in the ledger.

Deliverables: request ledger, four-mode server timelines, per-burst summaries,
source hashes and a reconciliation report. Keep derived outputs separate from
sealed trial evidence.

## Route 2: distinguish burst capacity from delayed admission

Use the ledger to test the working hypothesis, rather than fitting a story to
the successful-response percentiles.

| Question | Evidence that supports it | Evidence that weakens it |
|---|---|---|
| Did HTTP stalls spread admission? | Non-yielding admission is less concentrated or extends later, while yielding moves comparable work into the queue sooner. | Admission shapes are comparable despite different cleanup stalls and rejection. |
| Does the burst exceed effective service capacity? | Queue growth follows admissions exceeding work starts/completions, with rejection near saturation and recovery afterward. | Rejection occurs without credible saturation, or completion capacity is sufficient throughout the relevant windows. |
| Does yielding reduce effective worker capacity? | Busy-window completion rate falls or between-job gaps grow consistently within blocks, with comparable CPU per job. | Busy-window capacity is similar and arrival timing accounts for the difference. |
| Is there a residual tracing-specific problem? | Trace-on retains worse waiting, capacity or rejection within a yield setting after accounting for these patterns. | Tracing modes behave similarly within yield settings. |

Estimate busy-window capacity from worker completions and available cgroup CPU
and throttling evidence. Use CPU budget divided by CPU/job only as a labeled
sanity check. Successful requests per second over the entire trial is not a
busy-window service-capacity estimate. Worker processing wall time and Go
Running state are not CPU execution time.

Analyze client offered-phase membership separately from server-local windows.
Do not overlay their relative clocks without a defensible alignment and stated
uncertainty. Where cross-clock latency is unavailable, use each request's own
client durations and server durations, or report the limitation. Do not infer
exact quota-boundary timing from aggregate cgroup statistics.

Deliverable: a verdict for each hypothesis—supported, weakened or unresolved—
with all four block comparisons, exceptions and remaining evidence gaps.

## Route 3: choose the smallest follow-up that separates explanations

- If admission spreading explains the rejection difference, document where the
  waiting moved and assess end-to-end outcomes and failures together. Lower
  rejection achieved through longer hidden waiting is not sufficient success.
- If yielding loses busy-window capacity, localize between-job scheduling gaps
  and CPU availability before proposing a scheduling change.
- If a residual trace-specific stall remains, inspect its exact reader/worker
  stacks and scheduling transitions. Propose a targeted change only when that
  evidence identifies the component and expected effect.
- If retained event timing cannot distinguish the mechanisms, specify a new,
  separately versioned diagnostic that fills that particular gap. Define its
  hypothesis, distinguishing outcomes, instrumentation cost, completeness checks
  and stopping rule before preparing launch commands.

A new measurement should be chosen from this decision, not from a broad parameter
sweep. Any measurement follows the documented external-terminal quiet-host,
thermal and provenance controls. Retained-data analysis can happen now.

## Route 4: qualify a candidate only after the mechanism is understood

A candidate must preserve response correctness, request lifecycle accounting,
trace completeness and the original qualification workload. Run a fresh,
separately planned qualification comparison with the original failure-rate and
overhead gates. Report rejection, timeouts, errors, successful latency,
throughput and CPU cost together. Full collection remains gated on that result.

Keep yielding classified as a mechanism probe: it changes service scheduling.
Do not enlarge the queue, lower the offered load, change the worker count or
relax acceptance thresholds to relabel the failed qualification as passed.
Such changes, if later desired, require a separate workload/design question.

## Source trail

- [Completed findings](runtime_io_v8_yield_findings.md)
- [Study report](../results/diagnostic/runtime-io-v8-yield-1/analysis/report.md)
- [Trial summaries](../results/diagnostic/runtime-io-v8-yield-1/analysis/trials.csv)
- [Within-block contrasts](../results/diagnostic/runtime-io-v8-yield-1/analysis/contrasts.csv)
- [Saved validation](../results/diagnostic/runtime-io-v8-yield-1/analysis/validation.json)
- [Service timestamp definitions](../diagnostic/service/main.go)
- [Connection event definitions](../diagnostic/service/trace_diag.go)

## Progress — 2026-10-02

Routes 1 and 2 are now complete: all 16 trials and 36,240 requests were reviewed,
the ledger and timelines were produced, and admission spreading is supported.
The longest pre-handler Runnable spans were also inspected. See
[the new discoveries and narrowed next question](runtime_io_v8_queue_findings.md).
The exact runtime cause and a qualified instrumentation candidate remain open.

Step 1 of the agreed three-step investigation is complete. The eight saved
runtime traces show network-read wakeups waiting for execution while worker
channel handoffs and completions continue. Pinned runtime source makes local
`runnext` preference versus global network-ready work a specific hypothesis;
trace generation maintenance is associated with the sparse recorded worker
preemptions. See [the raw long-wait inspection](runtime_io_v8_long_wait_findings.md)
for the direct evidence, source reasoning and unresolved causal details. No
correction was implemented and no new performance run was launched.

Step 2 now has a concrete experimental candidate: preserve a pending P-level
preemption at scheduler entry and use it to prefer older ready work at the next
ordinary selection. An isolated Go 1.26.1 patch passes targeted runtime and
stock/patched service correctness checks. Its causal hypothesis and performance
remain unqualified. See [the candidate and next comparison](runtime_io_v9_candidate.md).
Step 3 must prepare separate image/provenance support before a new controlled
performance session; the workload and acceptance rules remain unchanged.
