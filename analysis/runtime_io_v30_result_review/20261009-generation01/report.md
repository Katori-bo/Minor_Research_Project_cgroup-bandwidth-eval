# V30 verified findings — 9 October 2026

**The fresh 25 ms prediction/decision test passed its frozen gates.** Independent completion replay returned success; raw records, assets, clocks, monitor coverage, calibration, forecast chronology and result derivation reproduce. All 34 scientific trials completed without a technical retry. Campaign duration: 115.44 minutes.

## What the experiment showed

Average busy capacity was 34.917 requests/s. The constant-rate FIFO turns that into a 28.640 ms service time and therefore predicts every request misses 25 ms, including isolated requests. Real lightly loaded requests often receive CPU faster than that average rate suggests. The periodic model distinguishes the successful steady workloads from the failing burst workload. This is predictive evidence; it does not isolate a kernel-phase cause.

| Traffic profile | Validation offers | Observed 25 ms misses | Timing-model predicted misses | Timing-model MAE pp |
|---|---:|---:|---:|---:|
| Steady 4 rps | 1440 | 0.000% | 0.000% | 0.000 |
| Steady 18 rps | 6480 | 0.000% | 0.000% | 0.000 |
| 1 s at 4 rps, then 1 s at 42 rps | 8280 | 79.203% | 72.179% | 7.024 |

There were zero observed 25 ms misses across all six repeats of each steady profile. Burst misses ranged from 75.870% to 84.275%. The primary timing forecast agreed with the observed <=5%/>5% decision for all 18 trials. This supports classification of these widely separated operating conditions; it does not locate a precise rate boundary near 5% misses.

## Primary evidence and weighting

Fluid busy MAE: **73.599 pp**. Uniform-phase periodic+calibrated-delay MAE: **2.341 pp**, with equal weighting of the three profiles within each of six blocks. Every block improved; mean paired improvement was **71.258 pp**, with the declared block-based 95% t interval **[68.900, 73.615] pp**. Its assumptions remain approximately independent normal block contrasts.

The <=3 pp gate applies to the mean of block errors. It does not require every trial or block to stay below 3 pp: two blocks exceeded 3 pp, and the maximum trial error was **12.097 pp**. Burst-only MAE was **7.024 pp**. Weighting by offered requests instead gives **3.590 pp**; that is a secondary diagnostic, not the prespecified primary endpoint. The zero errors in the two steady profiles reduce the primary mean. No claim of <=3 pp error for every traffic pattern is justified.

## Boundary and adverse findings

| Deadline ms | Fluid busy MAE pp | Periodic + delay MAE pp |
|---:|---:|---:|
| 10 | 24.394 | 49.622 |
| 20 | 73.080 | 2.318 |
| 25 | 73.599 | 2.341 |
| 35 | 4.018 | 3.306 |
| 50 | 2.947 | 4.122 |
| 75 | 1.385 | 6.181 |
| 100 | 0.918 | 8.173 |
| 150 | 2.738 | 9.691 |
| 500 | 0.000 | 0.000 |

The periodic model also helps at 20 ms, but fails badly at 10 ms (49.622 pp overall MAE). Its predicted 10 ms miss fraction is only 0.296% for either steady profile, whereas observed pooled misses are 67.569% and 66.929%. Observed worker-processing medians are about 8.8 ms and client completion medians about 10.2 ms; the effective CPU demand inferred from average capacity is only about 7.16 ms. This descriptive mismatch motivates checking the demand/timing abstraction; it is not proof of a frequency, scheduling or phase cause.

At 50–150 ms, fluid busy is more accurate than periodic+delay. All methods have zero error at 500 ms because these validation offers all meet that deadline; this endpoint is uninformative for comparative superiority here. Six discovery-switch forecasts are nonmonotone when switching models above 25 ms, so that heuristic is not one coherent latency distribution. The sampled no-added-delay envelope covers 15/18 trials at 25 ms and 0/18 at 10 ms; it is not a guaranteed bound.

The fixed zero-phase/full-credit diagnostic has lower 25 ms MAE (0.902 pp) than the uniform-phase primary model. Phase was neither observed nor fitted to outcomes, so do not promote that scenario after seeing the results or claim the primary model beats every alternative. The calibrated-delay improvement over periodic-without-delay is modest (2.729 to 2.341 pp); this study does not establish that delay calibration is necessary.

Of 6558 misses at 25 ms, computation was certainly after the deadline for 6529, certainly within it despite a client miss for 22, and clock-boundary ambiguous for seven. These counts are descriptive stage decomposition.

## Paper claim and next work

A defensible claim is: **For this service and host, independently calibrated average capacity can misclassify a short-deadline operating condition. A frozen ordinary periodic-service approximation recovered the 25 ms operating decisions on new traffic patterns, while its errors at 10 ms and medium deadlines expose limits of the approximation.**

V1 and the four-context V29 study establish capacity/long-deadline evidence. V30 adds fresh short-deadline prediction and decision evidence. Preserve the full chain; do not rewrite earlier discovery as prospective validation. The result establishes neither a novel algorithm, a causal replenishment-phase explanation, universal deadline accuracy nor transfer to other applications or hosts.

Before further collection, consolidate these results into the extension narrative and investigate the 10 ms abstraction mismatch using retained calibration/stage records. Any changed demand model, phase assumption or model-switch threshold must be developed on existing discovery evidence and tested in a newly frozen held-out experiment. No additional collection launches automatically.
