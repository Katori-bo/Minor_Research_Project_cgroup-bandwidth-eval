# Completed diagnostic: request-ID timing audit

Source: `/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/results/diagnostic/all-in-one-power-fix/full`. Every attempt seal and successful request/server ID was checked.
Pilot requests are excluded. Trial summaries are recomputed from sealed raw data. Residuals are calculated for each request before grouping. Slowest-1% means pool the selected requests across trials; p50/p99 columns average trial quantiles.

| Period | Workers | Mean trial p50 / p99 e2e | Slowest 1%: mean e2e / residual | Residual share | High-phase count | Mean dispatch lag |
|---:|---:|---:|---:|---:|---:|---:|
| 100 ms | 1 | 342.3 / 886.7 ms | 893.3 / 1.7 ms | 0.2% | 331/340 | 0.530 ms |
| 100 ms | 4 | 173.7 / 4261.5 ms | 4361.1 / 4231.2 ms | 97.1% | 338/338 | 0.563 ms |
| 250 ms | 1 | 190.3 / 598.7 ms | 618.6 / 85.5 ms | 13.8% | 340/340 | 0.554 ms |
| 250 ms | 4 | 192.6 / 1165.0 ms | 1338.6 / 866.9 ms | 60.2% | 339/340 | 0.556 ms |

| Period | Workers | Slowest 1% mean queue / processing / post-work | Mean trial rejection / timeout | Mean throttled period fraction |
|---:|---:|---:|---:|---:|
| 100 ms | 1 | 875.7 / 15.2 / 0.7 ms | 0.501% / 0.000% | 62.5% |
| 100 ms | 4 | 67.1 / 46.5 / 16.2 ms | 1.048% / 0.029% | 70.9% |
| 250 ms | 1 | 521.2 / 11.6 / 0.2 ms | 0.000% / 0.000% | 57.0% |
| 250 ms | 4 | 299.6 / 84.5 / 87.6 ms | 0.000% / 0.000% | 59.6% |

| Period | Workers | Typical / slow mean queue depth at admission | Typical / slow mean write-to-first-byte | All successful requests in high phase |
|---:|---:|---:|---:|---:|
| 100 ms | 1 | 47.4 / 125.2 | 341.52 / 892.72 ms | 74.9% |
| 100 ms | 4 | 0.1 / 7.0 | 171.05 / 4360.43 ms | 74.7% |
| 250 ms | 1 | 24.5 / 82.0 | 189.04 / 617.94 ms | 75.0% |
| 250 ms | 4 | 4.8 / 49.1 | 196.35 / 1337.97 ms | 75.0% |

Typical means the middle 40–60% of successful end-to-end latencies within each trial. Queue depth is an admission-time sample, not a continuous occupancy trace. High-phase counts should be read against the higher number of arrivals in that phase.

## Location of the delay

The slowest successful requests in the 100 ms/four-worker cell average 4.36 s end to end and 4.23 s outside the four measured server stages. Mean request-write offset is 0.042 ms; mean first-byte-to-body-completion is 0.039 ms. 338/338 selected requests were scheduled in the high-rate half of the burst.

This audit cannot locate the remaining interval relative to handler entry or response writing. Client and server offsets have different monotonic origins and are never subtracted. Aggregate cgroup throttling does not identify the cause of an individual request.

The trial CSV retains rejection and timeout fractions; they are not included in successful-request quantiles.
