# Packaged versus common-file executable loading

Four matched four-arm blocks at GOMAXPROCS=1, four workers, 50 ms / 100 ms quota, zero burst credits. All offered requests remain in the 500 ms primary and 1,000 ms guardrail denominators.

| Block | Arm | Timely 500 ms | Timely 1,000 ms | Failures | Late successes: work before 500 ms | CPU/job us | Queue p99 ms | Post-work p99 ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | legacy_packaged | 72.118% | 100.000% | 0.000% | 522 | 3668.56 | 513.35 | 161.73 |
| 1 | rebuilt_packaged | 74.003% | 100.000% | 0.000% | 544 | 3645.62 | 501.40 | 159.81 |
| 1 | rebuilt_shared | 73.797% | 100.000% | 0.000% | 553 | 3646.03 | 500.49 | 160.84 |
| 1 | legacy_shared | 73.267% | 100.000% | 0.000% | 584 | 3647.13 | 501.98 | 161.32 |
| 2 | rebuilt_packaged | 75.195% | 100.000% | 0.000% | 565 | 3649.53 | 491.70 | 161.13 |
| 2 | legacy_shared | 75.386% | 100.000% | 0.000% | 585 | 3647.58 | 484.08 | 160.82 |
| 2 | legacy_packaged | 73.149% | 100.000% | 0.000% | 551 | 3662.81 | 506.45 | 160.98 |
| 2 | rebuilt_shared | 74.680% | 100.000% | 0.000% | 598 | 3647.36 | 487.33 | 160.68 |
| 3 | legacy_shared | 74.650% | 100.000% | 0.000% | 620 | 3647.30 | 489.15 | 160.80 |
| 3 | rebuilt_shared | 73.885% | 100.000% | 0.000% | 570 | 3647.30 | 501.62 | 161.21 |
| 3 | rebuilt_packaged | 74.547% | 100.000% | 0.000% | 610 | 3647.75 | 488.49 | 161.27 |
| 3 | legacy_packaged | 72.280% | 100.000% | 0.000% | 554 | 3664.90 | 509.83 | 160.79 |
| 4 | rebuilt_shared | 74.753% | 100.000% | 0.000% | 586 | 3647.72 | 490.25 | 160.71 |
| 4 | legacy_packaged | 73.178% | 100.000% | 0.000% | 571 | 3662.79 | 503.45 | 160.79 |
| 4 | legacy_shared | 73.458% | 100.000% | 0.000% | 606 | 3649.35 | 495.41 | 161.27 |
| 4 | rebuilt_packaged | 74.636% | 100.000% | 0.000% | 585 | 3643.05 | 486.41 | 160.24 |

## Declared paired contrasts

| Contrast | Block | Timely 500 ms delta, pp | Timely 1,000 ms delta, pp | CPU/job change | Successful p99 change | Within practical margins |
|---|---:|---:|---:|---:|---:|---|
| legacy_packaged → rebuilt_packaged | 1 | +1.88 | +0.00 | -0.63% | -3.19% | False |
| legacy_packaged → rebuilt_packaged | 2 | +2.05 | +0.00 | -0.36% | -2.23% | False |
| legacy_packaged → rebuilt_packaged | 3 | +2.27 | +0.00 | -0.47% | -3.18% | False |
| legacy_packaged → rebuilt_packaged | 4 | +1.46 | +0.00 | -0.54% | -2.06% | False |
| legacy_shared → rebuilt_shared | 1 | +0.53 | +0.00 | -0.03% | +0.32% | True |
| legacy_shared → rebuilt_shared | 2 | -0.71 | +0.00 | -0.01% | +0.11% | True |
| legacy_shared → rebuilt_shared | 3 | -0.77 | +0.00 | +0.00% | +1.49% | True |
| legacy_shared → rebuilt_shared | 4 | +1.30 | +0.00 | -0.04% | -0.42% | False |
| legacy_packaged → legacy_shared | 1 | +1.15 | +0.00 | -0.58% | -2.97% | False |
| legacy_packaged → legacy_shared | 2 | +2.24 | +0.00 | -0.42% | -2.52% | False |
| legacy_packaged → legacy_shared | 3 | +2.37 | +0.00 | -0.48% | -3.71% | False |
| legacy_packaged → legacy_shared | 4 | +0.28 | +0.00 | -0.37% | -1.27% | True |
| rebuilt_packaged → rebuilt_shared | 1 | -0.21 | +0.00 | +0.01% | +0.55% | True |
| rebuilt_packaged → rebuilt_shared | 2 | -0.52 | +0.00 | -0.06% | -0.19% | True |
| rebuilt_packaged → rebuilt_shared | 3 | -0.66 | +0.00 | -0.01% | +0.94% | True |
| rebuilt_packaged → rebuilt_shared | 4 | +0.12 | +0.00 | +0.13% | +0.39% | True |

## Loading interaction

Shared-image contrast minus packaged-image contrast; CPU and p99 are ratios of ratios.

| Block | 500 ms interaction, pp | 1,000 ms interaction, pp | CPU ratio-of-ratios change | p99 ratio-of-ratios change |
|---|---:|---:|---:|---:|
| 1 | -1.35 | +0.00 | +0.60% | +3.63% |
| 2 | -2.75 | +0.00 | +0.36% | +2.39% |
| 3 | -3.03 | +0.00 | +0.47% | +4.83% |
| 4 | -0.16 | +0.00 | +0.50% | +1.68% |

Loading discovery decision: **shared_file_did_not_establish_neutrality**.

loading_screen.json retains paired deltas, block median/range and standard deviation, and the loading interaction. Four discovery blocks cannot establish statistical equivalence. Both retained images use their packaged executable and the exact common read-only file. Every arm has the same startup executable-provenance check before warmup. Actual mounts and process executable hashes are verified; shared arms also match the common device/inode identity. A missing packaged gap prevents claiming shared loading removed it. No publication timestamps are added. No filesystem/cache/scheduler cause or next-stage qualification follows automatically.

requests.csv retains failed, cancelled, late and drained outcomes, missing worker/handler events, clock bounds, and existing computation/handler deadline-crossing classes. Publication and mutex-boundary fields remain explicitly unobserved. Handler execution is not a runnable-readiness timestamp. Wall intervals include scheduling and off-CPU delays. Host/cgroup samples and CPU counters remain sealed, but do not identify instantaneous remaining quota or request-level throttle intervals. Further runtime/kernel observation requires a separate qualification.

[Frozen protocol](../source/docs/runtime_io_v17_loading_protocol.md)
