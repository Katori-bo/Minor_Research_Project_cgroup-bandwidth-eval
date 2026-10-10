# Diagnostic trial results

Pilot observations are diagnostic only.

| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 outside server ms | Trace coverage | Rejection fraction | Timeout fraction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pilot_overhead_1 | 4334.599 | 0.016 | 23.960 | 79.880 | 81.402 | 4329.058 | 1.000 | 0.000 | 0.000 |
| pilot_overhead_2 | 4217.594 | NA | NA | NA | NA | NA | NA | 0.000 | 0.000 |
| pilot_overhead_3 | 4146.813 | NA | NA | NA | NA | NA | NA | 0.000 | 0.000 |
| pilot_overhead_4 | 4330.133 | 0.020 | 0.015 | 80.273 | 0.013 | 4323.241 | 1.000 | 0.000 | 0.000 |
| pilot_p100000_w1 | 875.063 | 0.023 | 861.734 | 55.891 | 0.655 | 42.851 | 1.000 | 0.002 | 0.000 |
| pilot_p250000_w4 | 1469.010 | 0.016 | 523.593 | 222.942 | 226.823 | 1055.176 | 1.000 | 0.000 | 0.000 |
| pilot_p250000_w1 | 576.263 | 0.021 | 520.811 | 131.428 | 0.604 | 110.286 | 1.000 | 0.000 | 0.000 |

Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.
