# V22 prospective prediction validation

**Decision: primary_transfer_pass**

One service/host/boot/pattern pair; constant FIFO baseline; yielding off; aggregate success does not establish stage/tail accuracy.

| Trial | Observed misses % | Predicted misses % | Error pp | Primary pass |
|---|---:|---:|---:|---|
| b1_A | 11.924 | 10.378 | -1.546 | True |
| b1_B | 0.000 | 0.000 | 0.000 | True |
| b2_B | 0.000 | 0.000 | 0.000 | True |
| b2_A | 11.880 | 10.378 | -1.502 | True |
| b3_B | 0.000 | 0.000 | 0.000 | True |
| b3_A | 11.703 | 10.378 | -1.325 | True |
| b4_A | 10.967 | 10.378 | -0.589 | True |
| b4_B | 0.000 | 0.000 | 0.000 | True |

Queue/rejection/recovery support: True
Even-arrival screen: True
Baseline advantage: True

Per-trial stage, rare-tail, queue trajectory and clock-uncertainty diagnostics are retained in report.json.
