# Worker yielding and runtime tracing comparison

Mechanistic evidence only. This study cannot qualify a pilot or unlock full collection.

Custom connection recording, base timing and the workload stay enabled and fixed in every mode. Yielding calls runtime.Gosched once after each completed CPU job and reply publication. Runtime tracing is the second independent treatment.

| Mode | Rejection range | Timeout range | Median successful requests/s | Median successful p99 ms | Median CPU µs/completed work |
|---|---:|---:|---:|---:|---:|
| plain | 0.000%–3.444% | 0.000%–0.000% | 111.35 | 3846.351 | 3978.4 |
| trace | 3.311%–4.150% | 0.000%–0.000% | 109.40 | 2556.092 | 3995.2 |
| yield | 3.974%–4.327% | 0.000%–0.000% | 108.53 | 1003.642 | 3994.4 |
| yield_trace | 3.753%–4.238% | 0.000%–0.000% | 108.65 | 1002.283 | 4004.7 |

| Traced mode | Median cleanup wait p99 ms | Median waits ≥1 ms | Median reader Runnable share |
|---|---:|---:|---:|
| trace | 447.298 | 912.0 | 99.1234% |
| yield_trace | 0.076 | 17.5 | 89.5303% |

Within each balanced block, contrasts.csv reports the tracing penalty with and without yielding, the yield effect with tracing off/on, and their difference (interaction). Fractions are unitless; multiply by 100 for percentage points. Four blocks are descriptive, not a definitive causal estimate.

Lower rejection together with shorter helper waits and a smaller tracing penalty would support the scheduling hypothesis. Improved successful latency alone is insufficient, and throughput or CPU penalties must be assessed. Both tracing-off cells still have custom recording; this does not establish suitability for an uninstrumented service.

Trace-off helper scheduler state is unavailable, not zero. Cleanup wait counts include only observed Cond waits; each JSON retains excluded/missing associations. State-duration sums overlap and Go Running is not measured CPU execution.

No pilot_gate.json is written. The original qualification workload and acceptance thresholds are unchanged; any eventual candidate needs a separately planned fresh qualification pilot.
