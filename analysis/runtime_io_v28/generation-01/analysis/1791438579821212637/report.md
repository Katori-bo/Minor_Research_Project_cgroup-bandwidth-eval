# V28 prospective estimator comparison

**Decision: predictive_advantage_inconclusive**

One service, one host and quota. Shared constant-rate FIFO model. Four validation blocks; t intervals assume independent approximately normal block errors. Quadratic baseline is a declared polynomial benchmark, not a reproduction of a published load-dependent algorithm.

| Method | Capacity rps | Deadline MAE pp | Accuracy screen |
|---|---:|---:|---|
| whole | 139.66892145293704 | 13.494419642857144 | False |
| busy | 149.41666666666666 | 0.4527529761904774 | True |
| idle_corrected | 139.74279052857142 | 13.47061011904762 | False |
| regression | 125.95250364668553 | 31.31436011904762 | False |
| quadratic | 148.46275808875967 | 1.1685267857142863 | False |

All failures, state qualifications, block intervals, calibration inputs and per-offer forecasts remain in sealed JSON.
No further experiment starts automatically. A positive decision does not establish novelty or workload/quota transfer.
