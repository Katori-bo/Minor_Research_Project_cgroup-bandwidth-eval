# Completed v8 worker-yield study findings — 2026-10-02

All 16 trials completed and independently revalidated with no issues. There
were no client timeouts, client errors or server response-write errors. All eight
cleanup analyses reference the retained runtime trace and completion-file hashes.
This is a completed mechanistic study, not a qualification pilot; no passing
pilot gate or permission for full collection is produced.

## Finding: yielding strongly reduces the HTTP scheduling stalls

Within all four balanced blocks, yielding after a completed worker job greatly
reduces the observed HTTP cleanup wait for its background reader. The median
of the four trial p99 cleanup waits falls from 447.298 ms without yielding to
0.076192 ms with yielding. The median count of observed waits at least 1 ms falls
from 912 to 17.5 per trial. Trial p99 ranges are 381.302–902.348 ms without yield
and 0.033216–0.166592 ms with yield.

Successful requests' median trial p99 handler post-work delay also falls from
242.800 ms to 4.523 ms in the traced comparison. Those consistent changes support
the scheduling-opportunity hypothesis for the HTTP cleanup and response stalls.
They do not identify the exact Go trace/scheduler internals responsible for the
initial perturbation, or demonstrate that all observed delays have disappeared.
Yielded traces still have occasional maximum cleanup waits of 8.7–79.1 ms.

The original service is changed by the yielding treatment. This is evidence
about a mechanism, not proof of a transparent instrumentation fix.

## Finding: cleanup improvement does not fix rejection or all latency

Values below summarize four repetitions. Rejection ranges include all offered
requests; latency columns describe successful responses only. Latency values
are medians of per-trial percentiles, not pooled request percentiles.

| Runtime tracing | Worker yield | Rejection range | Median trial p50 end-to-end | Median trial p99 end-to-end | Median successful requests/s |
|---|---|---:|---:|---:|---:|
| Off | Off | 0–3.444% | 165.581 ms | 3,846.351 ms | 111.35 |
| On | Off | 3.311–4.150% | 177.852 ms | 2,556.092 ms | 109.40 |
| Off | On | 3.974–4.327% | 414.042 ms | 1,003.642 ms | 108.525 |
| On | On | 3.753–4.238% | 415.437 ms | 1,002.283 ms | 108.65 |

With yielding, runtime tracing off/on behaves similarly, but both modes reject
about 4% of offered requests. Yielding has not improved rejection relative to
the original traced cells, and it worsens rejection relative to the tracing-off,
non-yielding cells in every block. The tracing penalty in rejection becomes
smaller in all four within-block interactions because the yield-only cells
also reject more; that cannot be called an overall failure-rate improvement.

In the traced comparison, successful response p99 improves from about 2.56 s to
1.00 s, while successful response p50 worsens from about 178 to 415 ms. Successful
request rate decreases slightly. CPU per completed job differs by less than 1%
between the mode medians, which supports investigating scheduling and admission
timing rather than a large increase in CPU cost alone.

## Finding: remaining rejection is concentrated in the offered bursts

All eight yielding trials reach the 128-job queue capacity. Their 742 rejected
requests (377 yield-only and 365 yield-plus-trace) were all scheduled during the
high-rate half of the burst cycle. Across all four repetitions of a mode, 6,792
requests were scheduled during high-rate halves and 2,268 during low-rate halves.
The high-rate offered load is 169.815 requests/s; the low rate is 56.605/s.

Without yielding, the plain cells reject 151 high-phase and three low-phase
requests; the traced cells reject 322 high-phase and one low-phase request.
Phase classification uses each client's ScheduledOffsetNs modulo the frozen
10-second cycle (low first five seconds, high next five). It does not align
absolute client and server clocks or assert when a delayed request reached
the server.

Successful requests' median trial p50 queue wait in traced cells increases from
0.007425 ms without yield to 353.863 ms with yield, while post-work and HTTP
cleanup delays shrink. These observations are consistent with waiting being
redistributed into the bounded work queue as HTTP scheduling becomes more
responsive. They do not alone prove the complete rejection mechanism.

## Next step

Use the existing admission, worker-start/completion, rejection and connection
events to reconstruct server-local queue behavior during the offered bursts.
Test whether delayed admission/connection handling in the non-yielding cells
spreads the burst and accounts for their lower rejection, while yielded cells
expose the CPU-limited queue sooner. Estimate busy-window completion capacity
from observed worker/cgroup evidence rather than successful-throughput averages.
Keep client/server clock alignment limits explicit.

Do this retained-data analysis before scheduling another performance run.
Treat yielding as a mechanism probe; a future instrumentation candidate still
requires a separately planned fresh qualification comparison. Preserve the
original workload, failure-rate tolerance and overhead gates.

Sources: `results/diagnostic/runtime-io-v8-yield-1/analysis/report.md`,
`trials.csv`, `contrasts.csv`, the eight `*_http_cleanup.json` outputs, and the
sealed attempts' `loadgen.json`, `server_metrics.json` and `trace_status.json`.
No new workload was launched for this review.
