# V25 exploratory contribution leads

Original fixed low windows are lower-arrival windows, not qualified low states. User/system costs divide aggregate counters by phase completions, not per-job CPU. Edge accounting compares all pre-offer and post-arrival CPU with the excess over N times busy-window aggregate CPU/completion; it is a conditional reference calculation, not identification of a mechanism or attribution to individual jobs. Clock/counter bounds are not statistical confidence intervals. No state criteria, windows, thresholds or original reports were changed.

Independent V25 completion replay passed before these calculations.

| Size | Trials | Qualified low states | Minimum user-cost increase | Maximum system share of phase difference | Maximum edge CPU / reference excess |
|---|---:|---:|---:|---:|---:|
| small | 4 | 0 | 0.770 ms/completion | 25.5% | 26.1% |
| large | 4 | 0 | 1.564 ms/completion | 14.5% | 28.2% |

The aggregate user-CPU difference is positive in all eight recordings. System CPU alone cannot account for the entire measured phase-cost difference within these bounds. This does not identify SHA, runtime, HTTP or frequency effects.

Pre-offer plus post-arrival CPU is smaller than the reference excess in every recording. Under that reference accounting, attributing every edge CPU-second to overhead is still insufficient. This is not a job-level decomposition.

No new workload was run. All original phase/state outcomes remain unchanged.
