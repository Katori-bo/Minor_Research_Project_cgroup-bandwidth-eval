# Retained v7 HTTP cleanup investigation — 2026-10-02

The four-worker traces show an HTTP connection waiting for its background reader
to run. The reader is ready to run for almost the entire wait. This establishes
the immediate cleanup dependency, but does not establish why enabling runtime
tracing changes scheduling or how much this dependency contributes to rejection.

The memory-buffer intervention did not qualify the pilot: both four-worker
tracing trials exceeded the unchanged failure-rate gate. Their rejection rates
were 3.753% and 3.444%, versus 1.678% and 0% with runtime tracing off. All six
attempts completed and validated. The gate failure is a performance observation,
not a failed build, lost trace, or invalid attempt.

## Exact dependency from retained evidence

For each work request, the inspector joins three raw Go events:

1. The HTTP goroutine creates a `connReader.backgroundRead` goroutine through
   `startBackgroundRead`.
2. That HTTP goroutine enters `sync.Cond.Wait` in `abortPendingRead` during its
   recorded handler-exit-to-connection-done interval.
3. The exact child reader makes the HTTP goroutine runnable through
   `sync.Cond.Broadcast` in `backgroundRead`.

All 2,265 observed work-request cleanup waits match in each retained trace, with
no missing child or wake association. Two control-route waits per trace fall
outside the work-request windows and are excluded. These are observed cleanup
waits across all outcomes, not just successful requests.

| Retained trace | Workers | Cleanup waits ≥1 ms | Cleanup wait p99 | Maximum | Reader Runnable share of summed wait time | Long waits whose reader had never run before cleanup |
|---|---:|---:|---:|---:|---:|---:|
| trace_overhead_1 | 4 | 623 / 2,265 (27.5%) | 487.118 ms | 585.770 ms | 99.9878% | 616 / 623 |
| trace_overhead_4 | 4 | 743 / 2,265 (32.8%) | 581.985 ms | 675.730 ms | 99.9922% | 739 / 743 |
| trace_p100000_w1_on | 1 | 0 / 2,265 | 0.021 ms | 0.224 ms | 12.9023% | No long waits |

In `trace_overhead_1`, successful request 1604 waits 585.770 ms: handler G2341
waits for reader G3273, which has never run before the wait. During this interval,
71 worker completions are recorded. In `trace_overhead_4`, successful request 526
waits 675.730 ms: handler G1964 waits for reader G2027, also never previously run;
80 worker completions occur during the wait. The helpers eventually run and wake
the handlers after roughly 8 microseconds in Go Running in these two examples.

The final recorded socket write precedes the wait for all matched requests.
This is consistent with the pinned Go HTTP implementation, which flushes the
response before `abortPendingRead`, and finishes that cleanup before serving
the next request on the connection. A returned socket write does not prove
client delivery. These waits therefore establish delayed connection cleanup
and potential delay to reuse, not the same request's entire client latency.

Other jobs progressing means the server is not continuously unable to execute
throughout these long intervals. CPU quota throttling can still contribute.
Runnable means ready to run; it does not expose a goroutine's queue position.
The evidence points to uneven scheduling of background HTTP work under the
four-worker configuration. The one-worker contrast is descriptive; changing
worker count also changes contention and cannot by itself establish causation.

Pinned implementation references:
[Go 1.26.1 net/http server](https://github.com/golang/go/blob/go1.26.1/src/net/http/server.go)
(`startBackgroundRead`, `backgroundRead`, `abortPendingRead`, `finishRequest`,
`conn.serve`) and
[Go 1.26.1 scheduler](https://github.com/golang/go/blob/go1.26.1/src/runtime/proc.go).
No exact scheduler queue policy is inferred from the captured state transitions.

## Reproducibility and correction to census handling

New read-only inspector: `diagnostic/inspect_http_cleanup.py`. Its derived JSON
outputs are in `results/diagnostic/runtime-io-v7-memory-1/pilot/analysis/`:

- `trace_overhead_1_http_cleanup.json`
- `trace_overhead_4_http_cleanup.json`
- `trace_p100000_w1_on_http_cleanup.json`

Each output includes all joined requests, state durations, source trace and
completion-file hashes, and the parsed-dump hash. The pinned parsed dump must
reproduce the sealed scheduler evidence exactly before its stack joins are used.
The inspector revalidates retained attempts and refuses output inside them.

Go generation censuses may emit same-state `Waiting->Waiting` snapshots with an
empty reason. They do not end a wait. The new inspector follows each Cond wait
to an actual state change and preserves wait reasons across those snapshots.
The four-worker joins cross 117 and 124 such snapshots; the one-worker joins
cross none. Earlier simple wait-stack summaries could split waits at censuses,
and existing scheduler state summaries can lose the network reason at a census.
This report uses the corrected reader-state joins. No sealed attempt, original
analysis output, workload, or qualification gate was changed.

Duration sums overlap across goroutines; they are not elapsed pilot time or CPU
usage. Percentiles here describe cleanup Cond waits, not end-to-end latency.
The server/runtime clock mapping uses the retained bracketed anchors. No
absolute client/server timestamps are subtracted. There is no tracing-off
runtime scheduler capture, so this analysis cannot measure its helper waits.

Verification: all 38 Python tests passed, including exact stack association,
cross-census waits, wait-reason preservation, wrong-parent rejection, and missing
waker accounting. All three retained traces passed the inspector's evidence
checks. No performance workload was launched during this investigation.

## Next controlled comparison

The next mechanistic experiment should test whether giving ready HTTP goroutines
a scheduling opportunity between CPU jobs reduces these stalls. Prepare a
separate experimental service option that calls `runtime.Gosched()` once after
each completed worker job; keep its default disabled. This is a hypothesis test,
not an established fix or permission to treat the current tracing pilot as valid.

Compare four balanced modes: worker yield off/on crossed with runtime trace
off/on. Keep four workers, GOMAXPROCS, CPU quota/period, memory trace storage,
custom recording, job iterations, request rate/burst schedule, queue capacity,
duration, client behavior, and environment controls fixed. Record the treatment
in the configuration and health/status evidence, seal it in a fresh study,
and use balanced repeated blocks, as in the component experiment.

Evaluate rejection/timeout rates, throughput and latency in all four modes.
For traced modes, rerun the exact cleanup-reader joins and check both helper
Runnable time and handler post-work delay. A smaller tracing penalty together
with shorter helper waits would support the proposed scheduling mechanism.
Yielding that helps both modes equally, shifts delay elsewhere, or reduces
throughput would require a different interpretation. Preserve the original
failure-rate and overhead criteria for any eventual qualification pilot.

Do not resume or overwrite the completed v7 session. Its pilot failed, so its
full collection remains locked. Implement and functionally verify the separate
comparison before asking the user to quit the desktop and launch it externally.
