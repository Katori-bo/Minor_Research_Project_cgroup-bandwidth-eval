# V29 prospective estimator comparison

**Decision: busy_advantage_over_declared_comparators**

One service, one host and quota. Shared constant-rate FIFO model. Four validation blocks; t intervals assume independent approximately normal block errors. Quadratic baseline is a declared polynomial benchmark, not a reproduction of a published load-dependent algorithm.

| Method | Capacity rps | Deadline MAE pp | Accuracy screen |
|---|---:|---:|---|
| whole | 72.55757752737262 | 11.093377976190476 | False |
| busy | 77.64583333333333 | 0.672247023809524 | True |
| idle_corrected | 72.60624530931993 | 11.093377976190476 | False |
| regression | 62.32878356017293 | 40.81659226190476 | False |
| quadratic | 67.03263931302013 | 29.993675595238095 | False |

All failures, state qualifications, block intervals, calibration inputs and per-offer forecasts remain in sealed JSON.
No further experiment starts automatically. A positive decision does not establish novelty or workload/quota transfer.
