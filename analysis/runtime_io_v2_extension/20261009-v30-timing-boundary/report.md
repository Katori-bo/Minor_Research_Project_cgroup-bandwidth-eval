# V30 timing-boundary investigation

**Retrospective discovery after V30 outcomes; no fresh collection or new confirmation.** All fitted timing values come from the original four low-rate calibration trials. This does not make the new comparison prospective, because its method was chosen after validation results.

## The 10 ms discrepancy

The four calibration cohorts already show the steady-response timing that the CPU-derived demand misses:

| Quantity | Value ms |
|---|---:|
| Effective CPU demand from busy capacity | 7.160 |
| Recorded calibration worker-wall median | 8.855 |
| Calibration non-queue response residual mean | 1.397 |
| Paired queue-free calibration latency median | 10.228 |
| Paired queue-free latency 95th percentile | 10.902 |

The paired calibration CDF predicts **67.751%** misses at 10 ms; the frozen periodic model predicts **0.296%** for either steady profile. Observed steady misses are about 67%. Over all 12 steady trials, the empirical CDF has **1.079 pp** mean absolute error. This ordinary baseline explains much of the discrepancy without a new CPU-budget parameter.

| Steady comparator | 10 ms MAE pp | 11 ms MAE pp (exploratory) | 25 ms MAE pp |
|---|---:|---:|---:|
| joint_calibration_cdf | 1.079 | 1.534 | 0.000 |
| independent_worker_response_convolution | 6.778 | 0.594 | 0.000 |
| median_worker_plus_response | 9.822 | 0.638 | 0.000 |
| effective_cpu_demand_plus_response | 66.953 | 1.573 | 0.000 |
| V30_frozen_periodic_plus_delay | 66.953 | not frozen | 0.000 |

Retaining paired worker/response samples matters at this threshold: independent convolution predicts 60.471% misses instead of 67.751%. This is an empirical dependence/shape observation, not a proof of a causal interaction or a new distributional method. Calibration requests are not independent experiment replicates; there are four calibration trials and six validation blocks.

## Stage and resource evidence

| Profile | 10 ms misses | Computation certainly after | Computation certainly within, client missed | Clock ambiguous | Recorded throttled-period range |
|---|---:|---:|---:|---:|---:|
| A | 973 | 554 | 211 | 208 | 0–0 |
| B | 4337 | 2323 | 1368 | 646 | 0–0 |
| C | 7644 | 7289 | 214 | 141 | 351–381 |

All A/B trials have zero recorded throttled periods. Their queue-wait medians are about 0.009 ms. Therefore quota throttling is not needed to observe the 10 ms failure. CPU wall time, CPU accounting and HTTP/dispatch/runtime delay must remain distinct. Clock ambiguity is material at 10 ms and is retained rather than assigned to a cause.

Median calibration worker-wall time combined with busy capacity would require 30.917 ms of worker availability per 100 ms, above the configured 25 ms CPU quota. The previously rejected identification of worker wall time as transferable CPU on-time remains inadmissible. We do not fix it by clipping the budget or selecting faster samples.

## Scope and next test

The empirical CDF predicts zero 25 ms misses for bursts too, while profile C actually misses about 79%; its burst error is 79.203 pp. It is a low-queue timing reference, not a replacement for queue/budget modeling. The surviving lead is a boundary involving both traffic state and deadline resolution.

A suitable next confirmation would predeclare this ordinary paired calibration-CDF baseline and test fresh steady rates near the 10–11 ms response transition, with the original frozen models retained. At 11 ms its discovery forecast is 3.254% misses, near the declared 5% operating target. New calibration, rates, primary endpoint, blocks, decisions and technical qualification must be frozen before collection. No runnable next-generation collector is implied by this report.
