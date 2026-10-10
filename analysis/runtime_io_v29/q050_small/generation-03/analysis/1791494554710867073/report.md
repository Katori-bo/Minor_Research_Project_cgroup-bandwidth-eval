# V29 prospective estimator comparison

**Decision: busy_advantage_over_declared_comparators**

One service, one host and quota. Shared constant-rate FIFO model. Four validation blocks; t intervals assume independent approximately normal block errors. Quadratic baseline is a declared polynomial benchmark, not a reproduction of a published load-dependent algorithm.

| Method | Capacity rps | Deadline MAE pp | Accuracy screen |
|---|---:|---:|---|
| whole | 141.3686626805711 | 15.658668154761903 | False |
| busy | 153.79166666666669 | 0.4786086309523807 | True |
| idle_corrected | 141.45879971732643 | 15.44438244047619 | False |
| regression | 120.74686590268301 | 41.208519345238095 | False |
| quadratic | 132.30505866731517 | 29.436197916666664 | False |

All failures, state qualifications, block intervals, calibration inputs and per-offer forecasts remain in sealed JSON.
No further experiment starts automatically. A positive decision does not establish novelty or workload/quota transfer.
