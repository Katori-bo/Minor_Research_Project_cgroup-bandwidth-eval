# Inline clock-call progression on the legacy worker path

Four matched six-arm blocks at GOMAXPROCS=1, four workers, 50 ms / 100 ms quota, zero burst credits. All offered requests remain in the 500 ms primary and 1,000 ms guardrail denominators.

| Block | Arm | Timely 500 ms | Timely 1,000 ms | Failures | Late successes: work before 500 ms | CPU/job us | Queue p99 ms | Post-work p99 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | legacy | 75.004% | 100.000% | 0.000% | 593 | 3656.30 | 488.97 | 161.85 |
| 1 | rebuilt_zero | 68.909% | 99.985% | 0.000% | 531 | 3686.43 | 534.55 | 161.53 |
| 1 | v14_clocks | 60.238% | 99.691% | 0.000% | 472 | 3755.08 | 689.07 | 161.15 |
| 1 | before_one | 60.224% | 99.661% | 0.000% | 437 | 3749.92 | 693.77 | 160.36 |
| 1 | boundary_five | 61.460% | 99.706% | 0.000% | 455 | 3749.83 | 684.51 | 160.87 |
| 1 | bracket_two | 61.814% | 99.853% | 0.000% | 456 | 3749.59 | 668.67 | 160.65 |
| 2 | bracket_two | 61.298% | 99.823% | 0.000% | 445 | 3752.26 | 672.54 | 162.48 |
| 2 | boundary_five | 61.652% | 99.735% | 0.000% | 428 | 3749.28 | 684.06 | 162.11 |
| 2 | before_one | 60.680% | 99.588% | 0.000% | 415 | 3750.89 | 695.54 | 161.75 |
| 2 | v14_clocks | 60.710% | 99.558% | 0.000% | 437 | 3756.96 | 696.53 | 161.61 |
| 2 | rebuilt_zero | 67.820% | 100.000% | 0.000% | 502 | 3686.19 | 569.11 | 161.17 |
| 2 | legacy | 74.562% | 100.000% | 0.000% | 599 | 3653.87 | 494.25 | 162.21 |
| 3 | rebuilt_zero | 69.689% | 100.000% | 0.000% | 518 | 3680.85 | 532.61 | 161.08 |
| 3 | before_one | 60.047% | 99.617% | 0.000% | 420 | 3748.07 | 695.19 | 160.09 |
| 3 | legacy | 73.311% | 100.000% | 0.000% | 595 | 3655.86 | 501.24 | 160.37 |
| 3 | bracket_two | 62.020% | 99.750% | 0.000% | 429 | 3756.19 | 676.83 | 161.44 |
| 3 | v14_clocks | 60.209% | 99.617% | 0.000% | 441 | 3751.24 | 695.23 | 161.76 |
| 3 | boundary_five | 60.018% | 99.617% | 0.000% | 446 | 3751.94 | 690.14 | 161.94 |
| 4 | boundary_five | 60.636% | 99.603% | 0.000% | 439 | 3753.26 | 694.46 | 161.24 |
| 4 | v14_clocks | 59.635% | 99.647% | 0.000% | 437 | 3757.90 | 695.47 | 161.68 |
| 4 | bracket_two | 60.768% | 99.691% | 0.000% | 447 | 3749.65 | 686.44 | 160.36 |
| 4 | legacy | 74.194% | 100.000% | 0.000% | 554 | 3656.61 | 502.49 | 161.81 |
| 4 | before_one | 60.077% | 99.661% | 0.000% | 436 | 3748.99 | 699.23 | 162.01 |
| 4 | rebuilt_zero | 66.775% | 100.000% | 0.000% | 523 | 3694.08 | 582.72 | 161.95 |

## Declared paired contrasts

| Contrast | Block | Timely 500 ms delta, pp | Timely 1,000 ms delta, pp | CPU/job change | Successful p99 change | Within practical margins |
|---|---:|---:|---:|---:|---:|---|
| legacy → rebuilt_zero | 1 | -6.09 | -0.01 | +0.82% | +8.13% | False |
| legacy → rebuilt_zero | 2 | -6.74 | +0.00 | +0.88% | +9.30% | False |
| legacy → rebuilt_zero | 3 | -3.62 | +0.00 | +0.68% | +6.56% | False |
| legacy → rebuilt_zero | 4 | -7.42 | +0.00 | +1.02% | +10.16% | False |
| rebuilt_zero → before_one | 1 | -8.69 | -0.32 | +1.72% | +15.74% | False |
| rebuilt_zero → before_one | 2 | -7.14 | -0.41 | +1.76% | +14.05% | False |
| rebuilt_zero → before_one | 3 | -9.64 | -0.38 | +1.83% | +17.10% | False |
| rebuilt_zero → before_one | 4 | -6.70 | -0.34 | +1.49% | +12.04% | False |
| before_one → bracket_two | 1 | +1.59 | +0.19 | -0.01% | -2.13% | False |
| before_one → bracket_two | 2 | +0.62 | +0.24 | +0.04% | -1.40% | True |
| before_one → bracket_two | 3 | +1.97 | +0.13 | +0.22% | -1.73% | False |
| before_one → bracket_two | 4 | +0.69 | +0.03 | +0.02% | -0.88% | True |
| bracket_two → boundary_five | 1 | -0.35 | -0.15 | +0.01% | +0.67% | True |
| bracket_two → boundary_five | 2 | +0.35 | -0.09 | -0.08% | +0.61% | True |
| bracket_two → boundary_five | 3 | -2.00 | -0.13 | -0.11% | +1.17% | False |
| bracket_two → boundary_five | 4 | -0.13 | -0.09 | +0.10% | +1.02% | True |
| boundary_five → v14_clocks | 1 | -1.22 | -0.01 | +0.14% | +1.55% | False |
| boundary_five → v14_clocks | 2 | -0.94 | -0.18 | +0.20% | +1.67% | True |
| boundary_five → v14_clocks | 3 | +0.19 | +0.00 | -0.02% | -0.31% | True |
| boundary_five → v14_clocks | 4 | -1.00 | +0.04 | +0.12% | -0.20% | False |
| legacy → boundary_five | 1 | -13.54 | -0.29 | +2.56% | +23.31% | False |
| legacy → boundary_five | 2 | -12.91 | -0.26 | +2.61% | +23.67% | False |
| legacy → boundary_five | 3 | -13.29 | -0.38 | +2.63% | +24.06% | False |
| legacy → boundary_five | 4 | -13.56 | -0.40 | +2.64% | +23.58% | False |

Practical marker decision: **inline_marker_effect_requires_review**.

observer_screen.json retains paired deltas and their block median/range; four discovery blocks cannot establish statistical equivalence. The six declared contrasts check rebuilding, one/two/five clock placement and the V14 worker-path/order-check bundle. No publication timestamps are exported in this screen. No intervention or larger batch is launched by passing this screen.

requests.csv retains failed, cancelled, late and drained outcomes, missing worker/handler events, clock bounds, and existing computation/handler deadline-crossing classes. Publication and mutex-boundary fields remain explicitly unobserved. Handler execution is not a runnable-readiness timestamp. Wall intervals include scheduling and off-CPU delays. Host/cgroup samples and CPU counters remain sealed, but do not identify instantaneous remaining quota or request-level throttle intervals. Further runtime/kernel observation requires a separate qualification.

[Frozen protocol](../source/docs/runtime_io_v15_marker_protocol.md)
