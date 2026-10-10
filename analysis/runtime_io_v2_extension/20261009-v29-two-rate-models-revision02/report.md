# Two-rate periodic worker baseline

All results are retrospective discovery. Median low-rate worker processing wall time and independent busy throughput define effective worker availability. This is a calibrated wall-service approximation, not isolated CPU-demand measurement or a kernel supply guarantee. No validation residual or phase is fitted.

| Context | Worker time ms | Effective budget ms | Model | 25 ms MAE pp | 50 ms MAE pp | 100 ms MAE pp | 500 ms MAE pp |
|---|---:|---:|---|---:|---:|---:|---:|
| q050_small | 4.513 | 69.400 | unavailable: B exceeds Q | — | — | — | — |
| q025_small | 4.497 | 31.312 | unavailable: B exceeds Q | — | — | — | — |
| q050_large | 8.807 | 68.385 | unavailable: B exceeds Q | — | — | — | — |
| q025_large | 8.832 | 30.783 | unavailable: B exceeds Q | — | — | — | — |

The effective budget B=P*busy_capacity*worker_time preserves the calibrated long-run capacity and must not exceed the configured quota. It represents worker wall-service availability; runtime and other service CPU demands are not separately measured. Unknown phase is averaged uniformly, not observed or selected as an oracle. Independent response delay is appended from the same four low-rate calibration trials. These choices were examined after V29 outcomes and require fresh confirmation.
