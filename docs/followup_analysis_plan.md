# Prespecified follow-up analysis plan

Revision 2, 2026-09-26, before any follow-up collection. Trials are the replication units; pilot data are reported separately and never pooled with full trials. Raw data remain unchanged. `analysis/trials.csv` and `analysis/report.md` show every repetition, including severe observations.

## Trial outcomes

Use nearest-rank p50/p95/p99/maximum of successful client end-to-end latency, successful-request queue waiting and elapsed processing. Also report queue/processing summaries for **all completed server jobs**, including jobs whose client failed, to expose outcome-selection effects. Preserve raw client requests and server events as the within-trial distributions; request counts do not increase the number of independent repetitions. Off-instrumentation pilot timings are unavailable, not zero.

Report successful responses per offered second completed inside the measurement window; successful arrival-cohort count divided by offered duration; successful throughput including client drain; completed server jobs divided by server-drain elapsed time; rejection fraction, timeout fraction and other-error fraction of scheduled requests; aggregate CPU usage; throttled-period fraction and throttled microseconds; sampled queue-depth maximum; server completions after client departure; and dispatched requests not observed by the server. Keep these denominators and populations distinct.

## Study B comparisons

For steady and bursty separately, estimate the change in the worker-count effect between periods:

`(mean trial p99 at 100 ms, four workers − mean at 100 ms, one worker) − (mean at 250 ms, four workers − mean at 250 ms, one worker)`.

Report the difference in milliseconds and the ratio of geometric-mean worker effects (100 ms versus 250 ms). Use 10,000 bootstrap resamples of trials within each of the four cells, five trials per cell, fixed seed 761, and 95% percentile intervals. Never bootstrap individual requests as experimental repeats. This is a new-data check of a contrast selected from the completed study, not a claim of discovery from a previously unseen hypothesis. If a trial has zero successful requests, its successful p99 is undefined and the affected contrast is reported unavailable; do not silently drop that trial.

Show queue and processing distributions via each trial's component quantiles and retained request records. Do not add component p99 values to obtain end-to-end p99.

## Study A comparisons

Compare GOMAXPROCS 2 versus 1 on all-completed-server-job processing p99 and server throughput including drain. Also report successful client throughput and failure fractions. Show each repetition and bootstrap the difference of arm means with trials as units. The paper's fib latency excludes queue wait; our all-completed processing duration is the closest timing definition available. SHA-256 versus fib(30), HTTP transport, 0.5-CPU budget, four goroutines, this machine/runtime, 176.41/s arrival rate, and 60-second measurement make this an adapted replication. Figure 5 is not labelled as p99, so do not numerically equate our p99 to a figure value. Compare qualitative processing-latency and throughput directions, supported by our repeated observations.

## Mechanism checks

An interaction mainly in queue wait, sampled depth and rejections supports queue accumulation. An interaction mainly in elapsed processing with increased throttling supports execution delay from quota enforcement or scheduling. Similar server components with changed client p99 weakens both and motivates examination of transport, client scheduling and success selection. Multiple explanations can coexist. Trial-level cgroup counters cannot identify the exact scheduling cause of a particular request; no confirmed mechanism or universal latency formula is claimed.

## Validation, order and environment

The analyzer checks one accepted attempt per planned trial, file checksums, source/configuration, runtime/quota/affinity, accounting, event/header timing agreement, thermal windows, power and monitor coverage. Report every failed/incomplete/corrupt attempt in `attempt_audit.csv`. Do not remove application errors or severe latency values as technical failures.

Inspect every trial's collection index, start timestamp and starting temperature. Compute descriptive correlations of within-treatment centered log p99 with order and temperature; conditioning by treatment avoids treating a shuffled sequence of different configurations as one homogeneous series. Constant/missing series produce null diagnostics. Interpret associations cautiously with five repetitions per cell. Retain under-load environmental traces for review and do not adjust away a treatment-caused temperature difference by default.

## Pilot gate

Validate all eight pilot trials. Report the median instrumented/uninstrumented CPU microseconds per completed job ratio from the on/off/off/on sequence. A ratio >1.10 triggers investigation; two observations per arm provide only a coarse screen. Require aggregate CPU usage between 0.45 and 0.55 CPU in both Study A pilot arms, plus observed component timing for instrumented trials. Passing does not establish the research hypothesis. The full runner checks the saved pilot gate and exact completion hashes before permitting full collection.
