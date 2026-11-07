# Deadline sensitivity and advance-warning screen

10 October 2026. Known-outcome development; all 78 cohorts retained, no new traffic or paper edit.

| Campaign | Flag | Accepted | Accepted errors >5 pp | Rejected errors <=5 pp | Max accepted error (pp) |
|---|---|---:|---:|---:|---:|
| NGINX original | calibration_agreement | 0/18 | 0 | 6 | unavailable |
| NGINX original | sensitivity_100us | 0/18 | 0 | 6 | unavailable |
| NGINX original | warmup_cdf | 2/18 | 1 | 5 | 9.000 |
| NGINX original | median_shift | 9/18 | 6 | 3 | 9.667 |
| NGINX original | always | 18/18 | 12 | 0 | 59.667 |
| NGINX original | agreement_and_shift | 0/18 | 0 | 6 | unavailable |
| NGINX power | calibration_agreement | 24/24 | 24 | 0 | 60.667 |
| NGINX power | sensitivity_100us | 0/24 | 0 | 0 | unavailable |
| NGINX power | warmup_cdf | 0/24 | 0 | 0 | unavailable |
| NGINX power | median_shift | 1/24 | 1 | 0 | 9.000 |
| NGINX power | always | 24/24 | 24 | 0 | 60.667 |
| NGINX power | agreement_and_shift | 1/24 | 1 | 0 | 9.000 |
| NGINX rate | calibration_agreement | 12/12 | 5 | 0 | 10.667 |
| NGINX rate | sensitivity_100us | 0/12 | 0 | 7 | unavailable |
| NGINX rate | warmup_cdf | 0/12 | 0 | 7 | unavailable |
| NGINX rate | median_shift | 3/12 | 1 | 5 | 5.667 |
| NGINX rate | always | 12/12 | 5 | 0 | 10.667 |
| NGINX rate | agreement_and_shift | 3/12 | 1 | 5 | 5.667 |
| NGINX panel | calibration_agreement | 24/24 | 9 | 0 | 19.667 |
| NGINX panel | sensitivity_100us | 0/24 | 0 | 15 | unavailable |
| NGINX panel | warmup_cdf | 0/24 | 0 | 15 | unavailable |
| NGINX panel | median_shift | 10/24 | 3 | 8 | 19.667 |
| NGINX panel | always | 24/24 | 9 | 0 | 19.667 |
| NGINX panel | agreement_and_shift | 10/24 | 3 | 8 | 19.667 |

Errors above 5 pp here are cohort maxima over the panel, an exploratory label, not a new primary acceptance test.

| Campaign | Forecast | Panel MAE (pp) | Mean cohort maximum (pp) | Cohorts >5 pp |
|---|---|---:|---:|---:|
| NGINX original | reference | 5.437 | 9.315 | 12/18 |
| NGINX original | warmup | 7.452 | 13.537 | 18/18 |
| NGINX original | weighted_update | 5.418 | 9.292 | 12/18 |
| NGINX original | location_shift | 7.200 | 11.211 | 13/18 |
| NGINX power | reference | 18.514 | 31.486 | 24/24 |
| NGINX power | warmup | 6.553 | 13.583 | 21/24 |
| NGINX power | weighted_update | 18.031 | 30.648 | 24/24 |
| NGINX power | location_shift | 4.930 | 10.161 | 18/24 |
| NGINX rate | reference | 2.617 | 5.083 | 5/12 |
| NGINX rate | warmup | 8.106 | 14.556 | 12/12 |
| NGINX rate | weighted_update | 2.533 | 4.894 | 4/12 |
| NGINX rate | location_shift | 6.466 | 11.962 | 12/12 |
| NGINX rate | rate_matched | 2.618 | 5.472 | 6/12 |
| NGINX panel | reference | 3.275 | 6.167 | 9/24 |
| NGINX panel | warmup | 7.986 | 14.264 | 23/24 |
| NGINX panel | weighted_update | 3.291 | 6.153 | 10/24 |
| NGINX panel | location_shift | 6.709 | 11.307 | 21/24 |

All methods receive the full acquired calibration and existing 25-offer warmup. Location correction is an ordinary median-shift model, not a new measured state signal.

## Descriptive rankings by campaign

| Campaign | Feature | AUC | Larger/smaller errors |
|---|---|---:|---:|
| NGINX original | calibration_agreement | 0.500 | 12/6 |
| NGINX original | sensitivity_100us | 0.500 | 12/6 |
| NGINX original | warmup_cdf | 0.535 | 12/6 |
| NGINX original | median_shift | 0.556 | 12/6 |
| NGINX power | calibration_agreement | unavailable | 24/0 |
| NGINX power | sensitivity_100us | unavailable | 24/0 |
| NGINX power | warmup_cdf | unavailable | 24/0 |
| NGINX power | median_shift | unavailable | 24/0 |
| NGINX rate | calibration_agreement | 0.500 | 5/7 |
| NGINX rate | sensitivity_100us | 0.500 | 5/7 |
| NGINX rate | warmup_cdf | 0.714 | 5/7 |
| NGINX rate | median_shift | 0.629 | 5/7 |
| NGINX panel | calibration_agreement | 0.456 | 9/15 |
| NGINX panel | sensitivity_100us | 0.456 | 9/15 |
| NGINX panel | warmup_cdf | 0.448 | 9/15 |
| NGINX panel | median_shift | 0.626 | 9/15 |

No significance or predictive guarantee follows from AUC. Policy/rate/block breakdowns and every cohort are in screen.json; no favorable pooled campaign is selected.

## Calibration and fixed sensitivity

| Campaign / reference | Max cohort disagreement (pp) | Max 100 us sensitivity (pp) |
|---|---:|---:|
| NGINX original / original | 6.250 | 8.375 |
| NGINX power / P1 | 1.750 | 10.000 |
| NGINX power / P0 | 3.000 | 10.875 |
| NGINX rate / P0 | 2.500 | 9.375 |
| NGINX panel / P0 | 1.250 | 9.000 |
| NGINX panel / P1 | 1.500 | 11.250 |

Fixed sensitivity is not a justified bound on future drift. Calibration agreement is constant within a reference group; neither can select later time windows within that group.
Failures retain their mass at infinity. Location quantities refuse if inputs contain failures. Duplicate cutoff labels and all chronological blocks remain included.
This screen changes no scientific acceptance decision, establishes no causal shift mechanism, and qualifies no live observer. Any fitted rule or changed threshold would be development requiring fresh evaluation.
