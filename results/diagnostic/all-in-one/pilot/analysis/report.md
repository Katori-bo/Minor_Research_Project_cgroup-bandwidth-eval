# Diagnostic trial results

Pilot observations are diagnostic only.

| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 outside server ms | Trace coverage | Rejection fraction | Timeout fraction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pilot_overhead_1 | 3535.914 | 0.019 | 0.017 | 80.006 | 0.014 | 3527.986 | 1.000 | 0.000 | 0.000 |
| pilot_overhead_2 | 4128.918 | NA | NA | NA | NA | NA | NA | 0.025 | 0.000 |
| pilot_overhead_3 | 4134.439 | NA | NA | NA | NA | NA | NA | 0.025 | 0.000 |
| pilot_overhead_4 | 4037.124 | 0.019 | 0.017 | 80.160 | 0.013 | 4033.084 | 1.000 | 0.000 | 0.000 |
| pilot_p100000_w1 | 871.416 | 0.021 | 862.962 | 55.932 | 0.708 | 43.771 | 1.000 | 0.004 | 0.000 |
| pilot_p250000_w4 | 919.149 | 0.018 | 519.133 | 222.930 | 228.197 | 630.199 | 1.000 | 0.000 | 0.000 |
| pilot_p250000_w1 | 583.291 | 0.020 | 523.846 | 131.279 | 0.620 | 111.168 | 1.000 | 0.000 | 0.000 |

Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.
