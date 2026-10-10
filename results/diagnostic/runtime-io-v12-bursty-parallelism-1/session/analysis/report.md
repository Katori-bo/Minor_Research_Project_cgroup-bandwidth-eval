# Existing parallelism remedy under bursty half-CPU load

Eight stock-Go trials; four paired GOMAXPROCS=1/2 contrasts. Four application workers and nominal CPU budget remain fixed. No runtime tracing, queue observer, scheduler patch or worker yielding.

| Block | GOMAXPROCS | Long entry fraction lower–upper | Missing entries | Success p99 ms | Success/s in window | Failure fraction | CPU/job us |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 | 4.446%–4.446% | 0 | 2449.205 | 107.767 | 2.620% | 3909.019 |
| 1 | 1 | 0.000%–0.000% | 0 | 882.304 | 111.117 | 0.000% | 3662.804 |
| 2 | 1 | 0.000%–0.000% | 0 | 873.167 | 111.250 | 0.000% | 3660.827 |
| 2 | 2 | 13.352%–13.352% | 0 | 4131.525 | 109.617 | 0.662% | 3902.561 |
| 3 | 1 | 0.000%–0.000% | 0 | 887.260 | 111.250 | 0.000% | 3669.116 |
| 3 | 2 | 9.966%–9.966% | 0 | 4124.467 | 109.233 | 1.325% | 3901.750 |
| 4 | 2 | 11.615%–11.615% | 0 | 4025.703 | 109.650 | 0.942% | 3895.037 |
| 4 | 1 | 0.000%–0.000% | 0 | 878.516 | 111.250 | 0.000% | 3663.617 |

Diagnostic interpretation: **existing_remedy_passes_diagnostic_screen**.

remedy_screen.json retains every predeclared criterion, four pair results and ratios of trial medians. Passing is a practical diagnostic screen, not a significance test, production SLO or novelty claim.

Entry delays retain successes, rejections and cancellations. Missing entries are unknown and widen the upper bound; they are never assigned zero delay. entry_delays.json contains every offered ID, interval bounds and one/five-second horizons. Clock round trips occur before arrivals and after client drain; monotonic offset brackets are intersected, never replaced by a midpoint.

Successful E2E percentiles remain conditional on success. The throughput column counts successes completed within the measurement window; cohort and drain throughput are separate in trials.csv. Server CPU accounting includes workload/drain and clock-control requests, but excludes final metrics export. Different CPU/job costs can change capacity and cannot be attributed entirely to fairness.

Scheduled-to-entry includes client dispatch lag. Dispatch-to-entry begins at the client request worker, not an exact wire-send or network-ready event. This stock comparison cannot identify ready-queue residence, runnext starvation or continuous CPU execution.

If the existing remedy suffices, report a known remedy validated in this case. If delay migrates into queueing/failures, inspect that tradeoff. If long entry delays remain, localize the residual with a separately controlled queue-history observer. If baseline symptom or coverage checks fail, repair the named measurement problem. No further experiment is automatically launched.

[Frozen research comparison](../source/docs/runtime_io_prior_art_review.md)
[Frozen protocol](../source/docs/runtime_io_v12_parallelism_commands.md)
