# Retrospective deadline-resolution audit

Unchanged V28 calibrations; 16 retained validation trials. No new collection or fitting.
Alternate deadlines were selected after the original results; these are discovery diagnostics.

| Deadline ms | Whole MAE pp | Busy MAE pp | Quadratic MAE pp | Busy maximum error pp |
|---:|---:|---:|---:|---:|
| 25 | 5.517 | 4.060 | 4.296 | 6.396 |
| 50 | 4.831 | 2.255 | 2.682 | 4.062 |
| 100 | 5.201 | 0.902 | 1.296 | 2.333 |
| 200 | 9.432 | 1.045 | 1.797 | 2.190 |
| 500 | 13.494 | 0.453 | 1.169 | 1.714 |
| 1000 | 1.897 | 0.000 | 0.000 | 0.000 |

All original 500 ms forecasts/outcomes reproduce. Consumed trial seals and design hashes pass.
The manuscript and consumed historical inputs retain their hashes.

This audit does not identify an error mechanism, establish novelty, or validate a new forecast.
See report.json for all five methods, per-trial errors and limitations.
