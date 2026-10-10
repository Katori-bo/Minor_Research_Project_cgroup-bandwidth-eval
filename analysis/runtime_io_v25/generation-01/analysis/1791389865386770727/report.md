# V25 repeated-control diagnostic

**Decision: control_design_screen_complete**

Four trials per condition/size are a bounded diagnostic. Observed repeat differences are not a confidence interval or a universal noise bound. Balanced descriptive contrasts do not establish equivalence or causality. Qualification data are not confirmatory scientific data.

Recording quality, control variation and workload states are separate. No equivalence or scientific confirmation is established.

| Trial | Sampler | Busy capacity jobs/s | Whole CPU/job ms | Misses % | Busy state | Low state |
|---|---|---:|---:|---:|---|---|
| b1_small_off_r1 | False | 148.778 | 3.6071 | 24.382 | unmeasured | unmeasured |
| b1_small_off_r2 | False | 149.389 | 3.6042 | 24.382 | unmeasured | unmeasured |
| b1_large_on_r1 | True | 75.056 | 7.0885 | 19.994 | True | False |
| b1_large_on_r2 | True | 74.889 | 7.0912 | 21.673 | True | False |
| b2_large_off_r1 | False | 74.833 | 7.0942 | 21.555 | unmeasured | unmeasured |
| b2_large_off_r2 | False | 74.611 | 7.1135 | 24.676 | unmeasured | unmeasured |
| b2_small_on_r1 | True | 149.500 | 3.6033 | 22.747 | True | False |
| b2_small_on_r2 | True | 149.167 | 3.6026 | 23.115 | True | False |
| b3_small_on_r1 | True | 149.444 | 3.6011 | 22.674 | True | False |
| b3_small_on_r2 | True | 149.556 | 3.5999 | 22.055 | True | False |
| b3_large_off_r1 | False | 75.278 | 7.0883 | 20.671 | unmeasured | unmeasured |
| b3_large_off_r2 | False | 75.111 | 7.0873 | 19.405 | unmeasured | unmeasured |
| b4_large_on_r1 | True | 75.278 | 7.0826 | 19.405 | True | False |
| b4_large_on_r2 | True | 75.000 | 7.0944 | 20.878 | True | False |
| b4_small_off_r1 | False | 148.722 | 3.6065 | 24.190 | unmeasured | unmeasured |
| b4_small_off_r2 | False | 149.278 | 3.6027 | 23.749 | unmeasured | unmeasured |

## small: controls and repeat variation

| Metric | Off mean | On mean | Off range | On range |
|---|---:|---:|---|---|
| busy_capacity_rps | 149.0417 | 149.4167 | 148.7222–149.3889 | 149.1667–149.5556 |
| whole_cpu_usec_per_job | 3605.1357 | 3601.7478 | 3602.7191–3607.1279 | 3599.9357–3603.3105 |
| miss_pct | 24.1755 | 22.6480 | 23.7485–24.3816 | 22.0554–23.1154 |

| Metric | Mean on-minus-off difference | Largest repeat difference | Both order contrasts exceed repeats with same sign |
|---|---:|---:|---|
| capacity_pct | 0.2516 | 0.4108 | False |
| cost_pct | -0.0940 | 0.1050 | False |
| miss_pp | -1.5275 | 0.6184 | True |

Eligible sampler-on phase trials: 0/4. Reference margins are descriptive; repeat differences are not uncertainty bounds.

## large: controls and repeat variation

| Metric | Off mean | On mean | Off range | On range |
|---|---:|---:|---|---|
| busy_capacity_rps | 74.9583 | 75.0556 | 74.6111–75.2778 | 74.8889–75.2778 |
| whole_cpu_usec_per_job | 7095.8134 | 7089.1725 | 7087.3065–7113.4629 | 7082.5754–7094.3866 |
| miss_pct | 21.5769 | 20.4873 | 19.4052–24.6761 | 19.4052–21.6726 |

| Metric | Mean on-minus-off difference | Largest repeat difference | Both order contrasts exceed repeats with same sign |
|---|---:|---:|---|
| capacity_pct | 0.1297 | 0.3690 | False |
| cost_pct | -0.0936 | 0.2718 | False |
| miss_pp | -1.0895 | 3.1213 | False |

Eligible sampler-on phase trials: 0/4. Reference margins are descriptive; repeat differences are not uncertainty bounds.
