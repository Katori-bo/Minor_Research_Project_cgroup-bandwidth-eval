# V29 prospective estimator comparison

**Decision: busy_advantage_over_declared_comparators**

One service, one host and quota. Shared constant-rate FIFO model. Four validation blocks; t intervals assume independent approximately normal block errors. Quadratic baseline is a declared polynomial benchmark, not a reproduction of a published load-dependent algorithm.

| Method | Capacity rps | Deadline MAE pp | Accuracy screen |
|---|---:|---:|---|
| whole | 33.372004418433605 | 8.985119047619047 | False |
| busy | 34.85416666666667 | 1.294642857142859 | True |
| idle_corrected | 33.41050023696146 | 8.985119047619047 | False |
| regression | 29.467316008654628 | 25.086309523809522 | False |
| quadratic | 29.810073101551133 | 23.56845238095238 | False |

All failures, state qualifications, block intervals, calibration inputs and per-offer forecasts remain in sealed JSON.
No further experiment starts automatically. A positive decision does not establish novelty or workload/quota transfer.
