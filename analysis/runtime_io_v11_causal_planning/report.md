# V11 interval decomposition for causal planning

Offline analysis of the reviewed, hash-checked raw captures. No workload was launched.

## What can be eliminated for the linked long-wait cohort

Of 3,278 matched pre-handler network-ready waits, 524 last at least one second. The largest final-selection-to-dispatch interval among these long waits is 0.031940 ms. At least 99.997543% of each long wait occurs before the final selection observation. This narrows the explanation: seconds spent between the final selection hook and the dispatch hook do not explain this cohort.

| Trial | Matched waits | Waits >=1s | Selection-to-dispatch p99, all (ms) | Selection-to-dispatch maximum, long (ms) | Dispatch-to-handler-marker maximum, long (ms) |
|---|---:|---:|---:|---:|---:|
| decisions_b1_observed | 763 | 159 | 0.003797 | 0.001503 | 0.141636 |
| decisions_b2_observed | 780 | 152 | 0.003927 | 0.031940 | 0.099985 |
| decisions_b3_observed | 863 | 104 | 0.004158 | 0.000792 | 0.030948 |
| decisions_b4_observed | 872 | 109 | 0.003366 | 0.000741 | 0.029075 |

## Scheduling opportunities during each trial's longest linked wait

| Trial / request | P | Other selections | Inherited selections | Tick progress between first/last choice | Periodic global choices | Forced choices |
|---|---:|---:|---:|---:|---:|---:|
| decisions_b1_observed / 413 | 0 | 1138 | 841 | 297 | 5 | 0 |
| decisions_b1_observed / 413 | 1 | 1062 | 791 | 270 | 4 | 0 |
| decisions_b2_observed / 443 | 0 | 1217 | 896 | 321 | 6 | 0 |
| decisions_b2_observed / 443 | 1 | 1094 | 808 | 286 | 4 | 1 |
| decisions_b3_observed / 1554 | 0 | 942 | 698 | 243 | 4 | 3 |
| decisions_b3_observed / 1554 | 1 | 854 | 633 | 220 | 4 | 0 |
| decisions_b4_observed / 470 | 0 | 1251 | 921 | 330 | 5 | 0 |
| decisions_b4_observed / 470 | 1 | 1156 | 847 | 309 | 5 | 0 |

## Limits

Wake hooks observe a state transition and can precede queue publication. Final selection hooks observe a findRunnable return and can follow queue removal. Consequently wake-to-selection includes scheduling, admission/publication, OS descheduling and quota effects; it is not exact queue residence. Dispatch is a runtime state observation before machine-code execution. A small selection-to-dispatch interval does not exclude OS throttling before selection or after dispatch. The handler marker can follow another CPU pause.

Per-P tick progress covers the first through last other selections, not the entire wait; periodic global counts record successful choices, not unsuccessful checks. Queue location is still unknown. Cohort members can overlap and are not independent experimental repetitions. No causal CPU-time partition or source of a preemption signal is inferred.
