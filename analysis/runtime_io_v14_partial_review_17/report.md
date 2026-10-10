# V14 exploratory review of 17 completed trials

Frozen session and individual attempt seals checked. This is a partial review, not the final eight-block qualification. Blocks 1–2 are complete; block 3 lacks V13. All available within-block offered schedules match. No collection is started and no sealed session files are changed.

| Block | Arm | Timely 500 ms | Timely 1,000 ms | CPU/job µs | Successful p99 ms | Late successes: work before 500 ms |
|---|---|---:|---:|---:|---:|---:|
| 1 | legacy | 66.38% | 100.00% | 3661.21 | 866.13 | 512 |
| 1 | clocks | 53.75% | 95.02% | 3783.93 | 1100.78 | 372 |
| 1 | v13 | 57.69% | 98.45% | 3739.36 | 1024.59 | 397 |
| 1 | passive | 54.06% | 94.66% | 3786.96 | 1101.21 | 393 |
| 1 | mutex_late | 53.14% | 94.26% | 3788.85 | 1116.61 | 392 |
| 1 | mutex_early | 54.51% | 95.23% | 3779.31 | 1096.04 | 362 |
| 2 | clocks | 53.97% | 95.44% | 3776.71 | 1100.62 | 368 |
| 2 | passive | 54.57% | 95.66% | 3783.40 | 1090.40 | 389 |
| 2 | legacy | 67.39% | 100.00% | 3659.86 | 859.41 | 503 |
| 2 | mutex_early | 53.60% | 94.95% | 3778.91 | 1103.34 | 383 |
| 2 | v13 | 57.82% | 99.04% | 3726.43 | 998.41 | 437 |
| 2 | mutex_late | 53.45% | 94.48% | 3789.58 | 1109.32 | 383 |
| 3 | passive | 54.79% | 95.92% | 3774.07 | 1089.70 | 374 |
| 3 | mutex_early | 55.04% | 95.78% | 3780.98 | 1084.40 | 370 |
| 3 | clocks | 53.58% | 95.13% | 3778.58 | 1101.07 | 376 |
| 3 | mutex_late | 53.76% | 94.73% | 3789.92 | 1109.95 | 386 |
| 3 | legacy | 68.35% | 100.00% | 3653.72 | 842.42 | 520 |

## Declared contrasts, available matched pairs

Values are change from the first arm to the second. Percentage points differ from percent change. Block 3 pairs are additional exploratory context; primary interim comparisons use the two complete blocks.

| Contrast | Block | Complete block | Timely 500 ms change, pp | CPU/job change | p99 change | Within original practical margins |
|---|---:|---|---:|---:|---:|---|
| legacy → clocks | 1 | True | -12.63 | +3.35% | +27.09% | False |
| legacy → clocks | 2 | True | -13.43 | +3.19% | +28.07% | False |
| legacy → clocks | 3 | False | -14.77 | +3.42% | +30.70% | False |
| clocks → passive | 1 | True | +0.31 | +0.08% | +0.04% | True |
| clocks → passive | 2 | True | +0.60 | +0.18% | -0.93% | True |
| clocks → passive | 3 | False | +1.21 | -0.12% | -1.03% | False |
| passive → mutex_early | 1 | True | +0.46 | -0.20% | -0.47% | True |
| passive → mutex_early | 2 | True | -0.97 | -0.12% | +1.19% | True |
| passive → mutex_early | 3 | False | +0.25 | +0.18% | -0.49% | True |
| mutex_early → mutex_late | 1 | True | -1.37 | +0.25% | +1.88% | False |
| mutex_early → mutex_late | 2 | True | -0.15 | +0.28% | +0.54% | True |
| mutex_early → mutex_late | 3 | False | -1.28 | +0.24% | +2.36% | False |
| mutex_late → v13 | 1 | True | +4.55 | -1.31% | -8.24% | False |
| mutex_late → v13 | 2 | True | +4.37 | -1.67% | -10.00% | False |
| legacy → passive | 1 | True | -12.32 | +3.43% | +27.14% | False |
| legacy → passive | 2 | True | -12.82 | +3.38% | +26.88% | False |
| legacy → passive | 3 | False | -13.56 | +3.29% | +29.35% | False |
| legacy → v13 | 1 | True | -8.69 | +2.13% | +18.30% | False |
| legacy → v13 | 2 | True | -9.57 | +1.82% | +16.17% | False |

## Interpretation and next exploration

The dominant interim separation is already present in legacy → clocks: in the two complete blocks, primary timely success loses 12.63 and 13.43 percentage points, CPU/job increases 3.35% and 3.19%, and successful p99 increases 27.09% and 28.07%. The corresponding pair from incomplete block 3 has the same direction. This implicates the combined clock-call/new-worker-path change, not clock calls in isolation.

Adding persistent per-worker recording changes timely success by +0.31 and +0.60 points in the complete blocks. Adding the post-send mutex changes it by +0.46 and −0.97 points. Those much smaller, mixed lock differences do not support the extra mutex as the dominant source of the roughly 13-point regression. Counter placement has a smaller adverse trend (−1.37 and −0.15 points in complete blocks; −1.28 in partial block 3), which deserves continued checking. None proves equivalence.

V13 versus legacy reproduces the earlier observer penalty: −8.69 and −9.57 points. The new passive recorder is worse than legacy by −12.32 and −12.82 points in complete blocks. The original all-pairs qualification rule already cannot pass with these retained pairs, regardless of the remaining trials. Finishing the declared batch would estimate consistency and the component contrasts; it must not be treated as a chance to obtain a passing observer.

Queue-delay p99 increases from 601/596 ms in legacy to 826/824 ms in clocks and 824/818 ms in passive. Post-computation p99 remains about 162–163 ms. The larger end-to-end penalty is therefore accompanied primarily by a larger queued backlog. These marginal percentiles cannot be added as per-request accounting. The modest CPU/job increase and larger backlog are consistent with small service-demand differences being amplified by a quota-limited burst; they do not establish its exact cause.

The original late-after-work phenomenon persists: legacy has 512 and 503 successful deadline misses whose main computation is certainly before 500 ms, plus 520 in partial block 3. All 393/389/374 corresponding passive successes have publication certainly before the deadline; their publication-to-handler lower-bound p99 is roughly 163 ms. This localizes delay in the affected observer, but does not distinguish runnable scheduling from quota unavailability. The lower late-after-work count in passive is not improvement: many more requests finish work after the deadline.

Next explore the common worker-path change with a static source/compiler audit and a separately frozen minimal ablation that keeps the legacy path and introduces marker calls incrementally. Do not alter this session’s source or margins. Complete remaining blocks only under comparable accepted environment conditions; require a qualified observer before the worker/parallelism comparison.

## Cooling and host context

The accepted initial baseline is 58.95°C. Completed-trial accepted cooling-window means span 56.32–59.43°C; collection k10temp samples span 65.75–75.13°C. Later failed cooling is distinct: block 3 V13 attempt 001 waited about 1,263 seconds and ended at 44.25°C, below the permitted baseline window. It never collected a performance trial. The gate requires a stable temperature mean within ±3°C of baseline, not exactly 60°C; a much cooler host can indeed fail it. If the host settles persistently near 44°C, prepare a separate session with a newly frozen baseline rather than overwrite this baseline or combine conditions without disclosing the change. All 17 completed trials pass their recorded acceptance checks, but those checks do not prove thermal equivalence.

Five queue-full HTTP 503 outcomes remain in the denominators: two in block 1 passive and three in block 1 mutex_late. There are no timeout/network failures in these completed trials.

## Integrity and limitations

17 valid completed attempts; 1 preserved incomplete/invalid attempts. The full qualification remains pending. Practical margins are unchanged: 1 pp deadline success, 0.1 pp failure, 5% CPU/job and 10% p99. Individual requests are not independent experiment repetitions.

Clock/path and allocation/store comparisons are bundles. V13 versus mutex_late is also a bundle. Handler execution timestamps do not establish runnable readiness; wall intervals do not isolate quota pauses. Accepted cooling and host samples do not directly measure hardware thermal throttling.

[Detailed data and attempt audit](review.json)
