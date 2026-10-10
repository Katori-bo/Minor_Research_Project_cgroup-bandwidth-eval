# V29 prospective estimator comparison

**Decision: busy_advantage_over_declared_comparators**

One service, one host and quota. Shared constant-rate FIFO model. Four validation blocks; t intervals assume independent approximately normal block errors. Quadratic baseline is a declared polynomial benchmark, not a reproduction of a published load-dependent algorithm.

| Method | Capacity rps | Deadline MAE pp | Accuracy screen |
|---|---:|---:|---|
| whole | 65.61125774929118 | 10.360863095238095 | False |
| busy | 69.625 | 1.359374999999999 | True |
| idle_corrected | 65.68241438680907 | 10.267113095238095 | False |
| regression | 57.37792783147556 | 26.159970238095237 | False |
| quadratic | 59.13390389837025 | 23.301339285714285 | False |

All failures, state qualifications, block intervals, calibration inputs and per-offer forecasts remain in sealed JSON.
No further experiment starts automatically. A positive decision does not establish novelty or workload/quota transfer.
