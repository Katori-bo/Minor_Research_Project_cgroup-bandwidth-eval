# Exact-image repeatability and exact-source rebuild pilot

Four matched three-arm blocks at GOMAXPROCS=1, four workers, 50 ms / 100 ms quota, zero burst credits. All offered requests remain in the 500 ms primary and 1,000 ms guardrail denominators.

| Block | Arm | Timely 500 ms | Timely 1,000 ms | Failures | Late successes: work before 500 ms | CPU/job us | Queue p99 ms | Post-work p99 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | legacy_a | 72.589% | 100.000% | 0.000% | 579 | 3653.97 | 508.20 | 161.53 |
| 1 | legacy_b | 72.074% | 100.000% | 0.000% | 573 | 3657.79 | 508.34 | 161.06 |
| 1 | exact_rebuild | 75.018% | 100.000% | 0.000% | 585 | 3640.87 | 479.53 | 160.88 |
| 2 | exact_rebuild | 76.064% | 100.000% | 0.000% | 589 | 3642.52 | 473.07 | 160.29 |
| 2 | legacy_b | 72.884% | 100.000% | 0.000% | 567 | 3656.52 | 506.21 | 160.34 |
| 2 | legacy_a | 72.972% | 100.000% | 0.000% | 579 | 3661.24 | 504.80 | 161.69 |
| 3 | legacy_b | 73.620% | 100.000% | 0.000% | 574 | 3659.99 | 499.79 | 161.64 |
| 3 | exact_rebuild | 75.710% | 100.000% | 0.000% | 590 | 3644.37 | 476.38 | 160.19 |
| 3 | legacy_a | 74.179% | 100.000% | 0.000% | 599 | 3654.66 | 496.07 | 161.31 |
| 4 | legacy_a | 72.987% | 100.000% | 0.000% | 587 | 3656.39 | 506.67 | 160.83 |
| 4 | exact_rebuild | 76.446% | 100.000% | 0.000% | 617 | 3646.48 | 468.06 | 161.70 |
| 4 | legacy_b | 72.531% | 99.985% | 0.000% | 597 | 3662.32 | 505.09 | 161.47 |

## Declared paired contrasts

| Contrast | Block | Timely 500 ms delta, pp | Timely 1,000 ms delta, pp | CPU/job change | Successful p99 change | Within practical margins |
|---|---:|---:|---:|---:|---:|---|
| legacy_a → legacy_b | 1 | -0.52 | +0.00 | +0.10% | +0.70% | True |
| legacy_a → legacy_b | 2 | -0.09 | +0.00 | -0.13% | +0.52% | True |
| legacy_a → legacy_b | 3 | -0.56 | +0.00 | +0.15% | +0.66% | True |
| legacy_a → legacy_b | 4 | -0.46 | -0.01 | +0.16% | -0.49% | True |
| legacy_a → exact_rebuild | 1 | +2.43 | +0.00 | -0.36% | -2.72% | False |
| legacy_a → exact_rebuild | 2 | +3.09 | +0.00 | -0.51% | -3.22% | False |
| legacy_a → exact_rebuild | 3 | +1.53 | +0.00 | -0.28% | -1.82% | False |
| legacy_a → exact_rebuild | 4 | +3.46 | +0.00 | -0.27% | -4.80% | False |
| legacy_b → exact_rebuild | 1 | +2.94 | +0.00 | -0.46% | -3.39% | False |
| legacy_b → exact_rebuild | 2 | +3.18 | +0.00 | -0.38% | -3.72% | False |
| legacy_b → exact_rebuild | 3 | +2.09 | +0.00 | -0.43% | -2.46% | False |
| legacy_b → exact_rebuild | 4 | +3.92 | +0.01 | -0.43% | -4.33% | False |

Baseline discovery decision: **exact_source_rebuild_difference_requires_review**.

repeatability_screen.json retains paired deltas, block median/range and sample standard deviation. Four discovery blocks cannot establish statistical equivalence. Two labels use the exact same original image; the third uses the exact-source/no-extra-metadata rebuild. Every trial starts a fresh container with the same control-plane calls. These are runner labels, never service metadata. A/A variability gates interpretation of both rebuild comparisons. No publication timestamps are added. No further experiment is launched automatically.

requests.csv retains failed, cancelled, late and drained outcomes, missing worker/handler events, clock bounds, and existing computation/handler deadline-crossing classes. Publication and mutex-boundary fields remain explicitly unobserved. Handler execution is not a runnable-readiness timestamp. Wall intervals include scheduling and off-CPU delays. Host/cgroup samples and CPU counters remain sealed, but do not identify instantaneous remaining quota or request-level throttle intervals. Further runtime/kernel observation requires a separate qualification.

[Frozen protocol](../source/docs/runtime_io_v16_repeatability_protocol.md)
