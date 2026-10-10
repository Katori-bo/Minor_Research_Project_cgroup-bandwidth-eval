# Interrupted minimal-computation screen: partial findings

Seven of eight cells completed and independently replayed from sealed raw records. The formal eight-cell decision is unavailable; the second-block full-service 100 ms cell never started its workload. Original evidence and preparation remain unchanged.

The 45-minute whole-screen alarm expired during final pre-trial settling. Initial baseline was 49.519°C; the last 60-second window averaged 60.683°C, outside the ±3°C baseline tolerance. Its range (0.5°C) and slope (+0.460°C/min) passed stability thresholds, but its temperature level did not. The last settling wait lasted about 772 seconds. Earlier completed cells settled in 85–145 seconds. Power settings remained unchanged throughout the failed wait. The log identifies a warmer idle condition, not its cause; it does not record process attribution during settling. This is not evidence that thermal throttling caused the period effect.

All seven completed trial cleanup receipts report no errors and removal of their containers and cgroups. The final cell has null container/cgroup identities because it was interrupted before creating them.

| Block | Workload | CPU/job, 20 vs 100 ms | Capacity change | CPU delivery change |
|---|---|---:|---:|---:|
| 1 | full | +4.80% | -7.17% | -0.007% |
| 1 | minimal | +14.19% | -12.41% | +0.016% |
| 4 | minimal | +11.58% | -10.36% | +0.019% |

The minimal control shows a substantial CPU/job increase in both opposite-order blocks. Native process CPU and cgroup CPU agree within 0.001% for these cells, while average CPU delivery stays around 0.5 core. The first full-service pair also shows the original penalty direction, with 500 ms success falling from 83.50% to 56.26%. The second full-service comparison remains missing.

This narrows the investigation: HTTP handling and application queueing are not necessary for a shorter-period CPU/job penalty in this session. Reduced average CPU delivery is not supported by the completed minimal pairs. It does not distinguish extra runtime/software work from slower execution of the same instructions, prove a frequency/cache/preemption mechanism, or establish the historical reversal cause. Continuously backlogged minimal work and bursty full-service work have different workload shapes and power behavior. Two short blocks do not establish generality.

Do not bypass the thermal criterion, raise the time ceiling, fill the missing cell in this one-shot generation, or launch another run automatically. Retain this as partial evidence. A fresh complete run would be a separately authorized attempt, not a continuation that completes this paired design.
