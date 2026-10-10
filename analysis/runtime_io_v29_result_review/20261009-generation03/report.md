# V29 overnight collection review

The seven-hour campaign bound stopped the fourth context. The collected dataset
contains **123 verified scientific trials out of 128 planned**, with all 64
calibration trials and 59 of 64 validation trials. Completed request records,
forecasts, historical evidence and interrupted attempts remain unchanged.

| CPU budget | Request size | Calibration | Validation | Status | Busy forecast MAE at 500 ms (percentage points) |
|---|---|---:|---:|---|---:|
| 50% | Small | 16/16 | 16/16 | Fully replayed, complete | 0.479 |
| 25% | Small | 16/16 | 16/16 | Fully replayed, complete | 1.359 |
| 50% | Large | 16/16 | 16/16 | Fully replayed, complete | 0.672 |
| 25% | Large | 16/16 | 11/16 | Individually verified, partial | 0.865 (descriptive only) |

The three complete contexts pass the declared busy-capacity accuracy screen and
advantage screen against the declared comparators. The partial context cannot
pass the complete comparison screen. Its calibration and forecasts were sealed
before validation, and each of its 27 accepted trials passed independent raw
replay. Two interrupted attempts for one missing slot are excluded; the second
lacks a completion seal. Existing complete-context reports were independently
verified with the retained `verify-completion` command, each returning exit 0.

There is sufficient evidence to begin extension analysis now. Completing the
full four-condition matrix requires the combined low-budget/large-request cell.
Recommend a separate complete run of **only q025_large**, with fresh calibration
and frozen forecasts, roughly two hours including qualification and analysis.
The first three collections took 105–109 minutes each before analysis. Preserve
the old partial context separately; completing its final five slots later would
cross the collection lifetime and leave its fourth balanced block interrupted.
Do not rerun the full overnight campaign or overwrite attempted generations.

Before another package is frozen, fix deliberate-interruption handling: the
study treated SIGTERM as a retryable technical exception and started another
attempt in the cleanup reserve. Neither interrupted attempt is scientific data.
The last attempt's watchdog cleanup record reports owner exit with no errors.

The six-deadline diagnostics are available. In complete contexts, busy forecast
MAE at 25 ms is approximately 3.45, 3.16 and 5.18 percentage points; the 500 ms
accuracy result does not establish equal short-deadline accuracy. These support
investigating the proposed deadline-resolution extension. This remains one
service and one host with sequential contexts confounded by time; no universal
generality or new estimator is established.

No new performance collection was launched during this review.
