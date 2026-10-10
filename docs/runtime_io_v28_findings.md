# V28: prospective accuracy passes; minimum advantage remains inconclusive

Verified8 October2026 against the
[original sealed report](../analysis/runtime_io_v28/generation-01/analysis/1791438579821212637/report.json).
Full completion replay passed. A separate
[sealed result audit](../analysis/runtime_io_v28_result_review/20261008/report.json)
recomputed raw CPU endpoint ratios, client-clock intersections and busy completion
counts, the five calibration estimates (including analytic regression equations),
every deadline forecast with a separate FIFO recurrence, prediction errors and
four-block intervals. The original decision remains
`predictive_advantage_inconclusive`; the protocol and source/design seals are
unchanged. Collection is stopped.

All32 scientific slots completed:16 calibration and16 validation, with no
technical failures or retries. All108,084 measurement offers and21,600 warmup
offers succeeded. Calibration and validation states qualified, owned cleanup
passed without watchdog intervention, and all recorded cgroup paths are absent.
Host-monitor coverage, quiet and power checks passed: short captures50–51
records and long captures80–81. Scientific runs used the native sampler off.
Collection took99.757 minutes within its120-minute bound. All fits and per-offer
forecasts were sealed before validation; the freeze marker preceded the first
validation attempt by13.912 seconds.

All estimates used fresh calibration and one shared constant-rate FIFO model.
Regression had the declared12 idle/steady observations through120 offered
jobs/s; its accounting-window maximum throughput was117.029 jobs/s. Whole and
busy calibration used four mixed trials. No validation input fitted a method.
The observed validation busy-capacity bounds spanned148.667–150.500 jobs/s.

| Method | Frozen capacity jobs/s | Mean absolute500ms miss error pp | Maximum miss error pp | Maximum capacity error % | Deadline checks passed /16 | Capacity checks passed /16 |
|---|---:|---:|---:|---:|---:|---:|
| Whole-run CPU/job |139.669|13.494|16.905|7.197|0|0|
| Idle-corrected CPU/job |139.743|13.471|16.810|7.148|0|0|
| Busy capacity |149.417|0.453|1.714|0.720|16|16|
| Linear utilization–throughput regression |125.953|31.314|37.929|16.311|0|0|
| Declared quadratic utilization–throughput benchmark |148.463|1.169|3.619|1.354|13|16|

Accuracy thresholds were≤3pp deadline error and≤5% capacity error in every
validation trial. Busy passed all32 checks. Quadratic passed every capacity
check but exceeded the deadline tolerance in three trials: block2 low15/period12
(3.619pp), block4 low15/period12 (3.381pp), block4 low30/period12 (3.458pp).
The other methods failed both thresholds in every validation trial.

## Why the complete advantage decision is inconclusive

Busy's error reduction versus quadratic averaged0.716pp over the16 trials.
All four block improvements were positive:0.914,0.914,0.122,0.914pp.
The model-based95% interval was[0.086,1.346]pp. The frozen support rule requires
its lower endpoint to be≥1pp; this fails, and the observed mean itself is below
the target. The interval includes1pp, so the experiment does not establish that
the true improvement is smaller than1pp either. These intervals assume
independent approximately normal block contrasts, with only four blocks/df3.

| Comparator | Mean busy improvement pp | Model-based95% interval pp | Frozen minimum advantage screen |
|---|---:|---:|---|
| Whole-run |13.042|[12.412,13.672]|Pass|
| Idle-corrected |13.018|[12.388,13.648]|Pass|
| Linear regression |30.862|[30.232,31.491]|Pass|
| Quadratic benchmark |0.716|[0.086,1.346]|Fail|

Both busy and quadratic correctly predicted zero misses in all eight6s-period
trials. All16 trials belong to the frozen advantage calculation. Among the
eight12s-period trials, observed misses ranged29.167–35.952%; busy's deadline
MAE was0.906pp and quadratic's2.337pp. That descriptive subset must not replace
the primary all-trial screen or be used to claim a prospective subset advantage.

## What the direct idle measurement resolved

Two zero-request live-service measurements consumed7.668 and8.056ms of CPU over
approximately30.11s each. Their mean CPU rate was0.000261092 CPU, or0.0261% of
one CPU. The declared additive idle correction reduced mixed whole cost by only
0.105% and increased the capacity estimate by0.0739 jobs/s. Its deadline MAE
changed from13.494 to13.471pp. Measured zero-request CPU is too small for this
correction to repair the observed gap. This does not establish the amount or
cause of overhead under load; background additivity/comparability is an
assumption of the correction.

The steady calibration data also recorded approximately4.50–4.53ms CPU/job at
15/30 jobs/s and3.679–3.691ms at120 jobs/s; all ten steady trials had zero
throttled periods and queue peak1. This is cohort CPU accounting, not isolated
per-job SHA demand or a frequency/cache/runtime mechanism. A fitted linear
intercept is not a direct background-CPU measurement.

## Contribution implication and next work

This extends the prospective evidence: busy calibration predicts fresh6/12s
burst schedules and high180 arrivals accurately, while the declared whole-run,
idle-corrected and constant-demand linear substitutions substantially overpredict
misses. Direct live-idle correction is now tested. A nonlinear benchmark already
recovers nearly the same capacity and much of the prediction accuracy, limiting
the stronger estimator-superiority argument.

The quadratic is the predeclared polynomial benchmark, not a reproduction of a
published load-dependent estimator. Advantage over all relevant prior methods,
a novel selection diagnostic, a causal mechanism and workload/quota transfer
remain unestablished. Keep the successful busy accuracy result and the failed
minimum-advantage screen together. Preserve V27's earlier inconclusive decision.

Do not repeat V28 to obtain a passing threshold or launch a transfer workload
automatically. The next useful work is offline: update the scoped paper with
V26–V28 and assess the closest applicable load-dependent method against the
declared quadratic contract. A stronger contribution needs a distinct practical
benefit or failure boundary before another bounded experiment is justified.
The historical short draft remains unchanged pending that revision.
