# V23 prospective prediction validation

**Decision: primary_transfer_pass**

One host/boot/service/hash algorithm; two work sizes and burst cycles; no universal transfer or new estimator.

| Trial | Observed misses % | Predicted misses % | Error pp | Primary pass |
|---|---:|---:|---:|---|
| b1_small_A | 0.000 | 0.000 | 0.000 | True |
| b1_small_B | 22.659 | 22.762 | 0.103 | True |
| b1_large_B | 16.608 | 17.256 | 0.648 | True |
| b1_large_A | 0.000 | 0.000 | 0.000 | True |
| b2_small_B | 23.587 | 22.762 | -0.824 | True |
| b2_large_A | 0.000 | 0.000 | 0.000 | True |
| b2_small_A | 0.000 | 0.000 | 0.000 | True |
| b2_large_B | 16.549 | 17.256 | 0.707 | True |
| b3_large_A | 0.000 | 0.000 | 0.000 | True |
| b3_large_B | 15.931 | 17.256 | 1.325 | True |
| b3_small_B | 22.276 | 22.762 | 0.486 | True |
| b3_small_A | 0.000 | 0.000 | 0.000 | True |
| b4_large_B | 15.430 | 17.256 | 1.826 | True |
| b4_small_A | 0.000 | 0.000 | 0.000 | True |
| b4_large_A | 0.000 | 0.000 | 0.000 | True |
| b4_small_B | 21.702 | 22.762 | 1.060 | True |

Queue/rejection/recovery support: True
Per-size primary results: {'small': {'complete': True, 'primary_pass': True, 'baseline_advantage': True}, 'large': {'complete': True, 'primary_pass': True, 'baseline_advantage': True}}
Baseline advantage: True

Per-trial stage, rare-tail, queue trajectory and clock-uncertainty diagnostics are retained in report.json.
