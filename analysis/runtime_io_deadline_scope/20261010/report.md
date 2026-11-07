# Deadline scope: retrospective distribution-transfer experiment

10 October 2026. Complete saved records; known development outcomes, no new traffic or independent confirmation.

| Campaign / method | Cohorts | Primary MAE (pp) | Mean empirical CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |
|---|---:|---:|---:|---:|---:|---:|
| NGINX original / original | 18 | 5.981 | 10.721 | 61.812 | 9/11 | 5.437 |
| NGINX power / pooled | 24 | 24.729 | 45.984 | 54.854 | 6/6 | 22.719 |
| NGINX power / matched | 24 | 15.708 | 34.031 | 63.083 | 13/13 | 18.514 |
| NGINX power / baseline | 24 | 55.458 | 66.288 | 89.000 | 1/1 | 33.510 |
| NGINX rate / pooled | 12 | 1.361 | 6.306 | 10.500 | 7/12 | 2.253 |
| NGINX rate / matched | 12 | 1.194 | 7.931 | 13.375 | 11/12 | 2.618 |
| NGINX rate / baseline | 12 | 1.972 | 6.538 | 11.208 | 9/12 | 2.617 |

Primary is the unchanged 20.565395 ms cutoff. The count denominator is the number of cohorts with primary error <=5 pp, not all cohorts. This is a scope diagnostic; the historical primary acceptance decisions remain unchanged.

Panel deadlines are calibration-only 10/25/50/75/90% lower order statistics, with one common panel per cohort/method comparison. Power panels use the assigned-policy reference, rate panels the ordinary5/s reference. CDF maxima inspect all finite cutoffs; attaining locations are retrospective diagnostics, never newly selected operational deadlines. Failure mass is retained.

## Policy and rate subgroups

### NGINX power / P0

| Method | Primary MAE (pp) | Mean CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |
|---|---:|---:|---:|---:|---:|
| pooled | 9.708 | 45.128 | 54.854 | 6/6 | 17.150 |
| matched | 31.417 | 44.170 | 50.583 | 1/1 | 22.656 |
| baseline | 31.417 | 44.170 | 50.583 | 1/1 | 22.656 |

### NGINX power / P1

| Method | Primary MAE (pp) | Mean CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |
|---|---:|---:|---:|---:|---:|
| pooled | 39.750 | 46.839 | 50.583 | 0/0 | 28.289 |
| matched | 0.000 | 23.892 | 63.083 | 12/12 | 14.372 |
| baseline | 79.500 | 88.406 | 89.000 | 0/0 | 44.364 |

### NGINX rate / 4

| Method | Primary MAE (pp) | Mean CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |
|---|---:|---:|---:|---:|---:|
| pooled | 1.083 | 7.181 | 10.500 | 4/6 | 2.753 |
| matched | 1.222 | 8.097 | 12.167 | 6/6 | 3.000 |
| baseline | 1.056 | 7.507 | 11.208 | 6/6 | 3.156 |

### NGINX rate / 8

| Method | Primary MAE (pp) | Mean CDF maximum (pp) | Worst CDF maximum (pp) | Primary <=5 but CDF >5 | Panel MAE (pp) |
|---|---:|---:|---:|---:|---:|
| pooled | 1.639 | 5.431 | 10.375 | 3/6 | 1.753 |
| matched | 1.167 | 7.764 | 13.375 | 5/6 | 2.236 |
| baseline | 2.889 | 5.569 | 9.708 | 3/6 | 2.078 |

## Descriptive block gains

Positive means smaller error for matching. No new significance or advantage decision is made; these six blocks share one host and calibration references.

NGINX power, matched versus pooled: mean primary gain 9.021 pp; mean CDF-maximum gain 11.952 pp; mean panel gain 4.206 pp.

NGINX rate, matched versus baseline: mean primary gain 0.778 pp; mean CDF-maximum gain -1.392 pp; mean panel gain -0.001 pp.

## Limits and disposition

These are discrepancies between two finite empirical distributions, including sampling noise. They do not identify latent-distribution error, causality or future reliability. Calibration quantiles are exploratory questions selected after historical outcomes were known. Every cohort and throttling observation is retained; no new deadline, threshold or model was tuned. Full original acquisition, warmup, qualification, settling and startup costs remain charged.

The scientific result is a more precise assessment of deadline-specific versus distribution-wide empirical agreement. Any stronger all-deadline prediction claim requires a separately declared fresh evaluation. No live experiment or manuscript update is selected by this screen; worker-wait collection remains held and the friend-owned V31 remains pending.

Complete per-cohort cutoffs, forecasts, empirical suprema, observations and six-block summaries are in screen.json. The frozen specification and verification receipts preserve the analysis.
