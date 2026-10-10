# Completed V29 robustness matrix

The final q025_large condition completed in 110.21 minutes including qualification and analysis. Its full retained verifier replayed the raw request records, CPU bounds, calibration, frozen forecasts and result provenance successfully. The three earlier complete contexts had already passed the same verifier, and all 12522 preservation hashes remain unchanged.

The primary matrix contains **128 scientific trials**: 64 calibration and 64 validation, totaling **243,190 offered measurement requests**. Warmup and functional offers are excluded. The interrupted q025_large generation-03 dataset remains separate and is not pooled.

## Primary 500 ms deadline

| CPU budget | Request size | Generation | Busy MAE pp | Whole CPU MAE pp | Linear MAE pp | Quadratic MAE pp | Busy maximum error pp |
|---|---|---|---:|---:|---:|---:|---:|
| 50% | Small | generation-03 | 0.479 | 15.659 | 41.209 | 29.436 | 1.738 |
| 25% | Small | generation-03 | 1.359 | 10.361 | 26.160 | 23.301 | 2.857 |
| 50% | Large | generation-03 | 0.672 | 11.093 | 40.817 | 29.994 | 2.333 |
| 25% | Large | generation-04 | 1.295 | 8.985 | 25.086 | 23.568 | 2.667 |

Busy calibration passes the declared 3 pp deadline-error and 5% capacity-error criteria in all four complete contexts. Each complete context also passes the declared block-based advantage criterion over the linear and quadratic comparators. These are the retained benchmarks, not reproductions of external published algorithms. The much worse quadratic result here, compared with V1, is reported unchanged rather than assumed to be a universal property.

## Prespecified secondary deadline diagnostics

Busy MAE in percentage points, averaged over the 16 validation trials in each context:

| Context | 25 ms | 50 ms | 100 ms | 200 ms | 500 ms | 1000 ms |
|---|---:|---:|---:|---:|---:|---:|
| q050_small | 3.451 | 1.517 | 1.020 | 0.880 | 0.479 | 0.000 |
| q025_small | 3.158 | 2.329 | 0.648 | 1.653 | 1.359 | 0.554 |
| q050_large | 5.176 | 3.093 | 0.952 | 1.280 | 0.672 | 0.000 |
| q025_large | 20.624 | 2.979 | 0.555 | 0.763 | 1.295 | 0.753 |

The clearest extension lead is **q025_large at 25 ms**. Its calibrated busy capacity is 34.854 rps. The constant-rate FIFO model assigns each job approximately 28.691 ms of service and therefore predicts 100% of offers miss a 25 ms deadline. Actual miss fractions average 79.376% across the 16 trials (range 72.500–84.952%), giving 20.624 pp MAE. Approximately 20.624% meet the deadline on average across trials; this is a mean of trial percentages, not a pooled offer percentage. At 500 ms, the same calibrated model has just 1.295 pp MAE.

This is evidence of a time-resolution limit in the average-capacity model. It does not by itself isolate quota phase or prove a new algorithm. The six-deadline grid was declared as secondary diagnostics; do not promote the short-deadline observation into a newly invented confirmatory criterion.

## Scope and next step

The completed collection supports robustness across the tested CPU budgets, request costs and burst patterns in one service on one host. Context order and time are confounded, including the separate final follow-up. It does not establish causal quota/work-size effects, transfer to another service or host, universal superiority, or estimator novelty. V1 manuscript and all earlier records remain unchanged.

Next, compare an ordinary quota-aware timing baseline with the retained constant-rate model, freeze any choices using discovery data, and test on explicitly held-out timing conditions. Use the request-level timestamps to investigate the short-deadline discrepancy before claiming a causal mechanism. Further bulk collection is not needed to finish this four-condition matrix.

The machine-readable report includes source report paths, comparator intervals, accounting and scope. No new performance experiment was launched during review.
