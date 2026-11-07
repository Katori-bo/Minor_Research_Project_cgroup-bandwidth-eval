# Warmup precision and collection cost

11 October 2026. Offline audit of all 78 NGINX warmup/reference pairs; no target outcomes used for precision.

| Campaign | Median warmup 95% interval width (us) | Median transformed probability-range width (pp) | Width >5 pp |
|---|---:|---:|---:|
| NGINX original | 564.638 | 57.094 | 18/18 |
| NGINX power | 523.626 | 54.062 | 24/24 |
| NGINX rate | 538.177 | 61.688 | 12/12 |
| NGINX panel | 525.452 | 58.438 | 24/24 |

These are conditional IID order-statistic illustrations. The transformed range is median-correction interval geometry, not a future miss-probability or error confidence interval.

| Reference group | Largest symmetric empirical location radius for <=5 pp (us) |
|---|---:|
| NGINX original/original | 56.624 |
| NGINX power/P1 | 45.438 |
| NGINX power/P0 | 52.210 |
| NGINX rate/P0 | 49.218 |
| NGINX panel/P0 | 47.708 |
| NGINX panel/P1 | 43.496 |

Radii are calibration sensitivity quantities, not justified bounds on future shifts.

The one-window IID DKWM CDF halfwidth at n=25 is 27.162 pp.
A sufficient 95% uniform-CDF halfwidth <=5 pp uses 738 offers, not a minimum necessary sample size or a power estimate.

| Fixed calibration offers | Equal-alpha paired-bound floor (pp) | Sufficient warmup offers for paired <=5 pp |
|---|---:|---:|
| 800 | 5.233 | Unavailable under this bound |
| 1600 | 3.701 | 12975 |

The paired illustration applies one-sample DKWM bounds with alpha=.025 each and the triangle/union bound. It permits different window distributions, estimates contemporaneous distributions only, and gives no future transfer certificate.
A floor above the margin is a limitation of this conservative allocation, not proof that every estimator or interval needs more calibration.

| Warmup offers per target | Extra offered requests | Extra nominal minutes | Projected science minutes | Fits optimistic service at 4/s / 8/s |
|---|---:|---:|---:|---|
| 25 | 0 | 0.000 | 35.673 | yes / yes |
| 50 | 600 | 1.875 | 37.548 | yes / yes |
| 100 | 1800 | 5.625 | 41.298 | yes / yes |
| 149 | 2976 | 9.300 | 44.973 | yes / yes |
| 200 | 4200 | 13.125 | 48.798 | no / yes |
| 400 | 9000 | 28.125 | 63.798 | no / yes |
| 597 | 13728 | 42.900 | 78.573 | no / yes |
| 738 | 17112 | 53.475 | 89.148 | no / no |
| 800 | 18600 | 58.125 | 93.798 | no / no |
| 1600 | 37800 | 118.125 | 153.798 | no / no |

Projections add nominal warmup schedules to the observed science lifetime, assuming all other behavior is unchanged. They exclude new design/qualification/preflight and do not certify campaign reserve or cleanup checks.
Ignoring startup and drain, the strict 120-second service ceiling plus 8-second reserve permits at most 149 warmup offers at 4/s and 597 at 8/s with 300 target offers. Those are optimistic maxima, not approved counts.

**Decision: hold longer-warmup hardware collection.** More precise warmup measurements would still need a demonstrated relation to the later window. Existing failed forecasts, protocol limits and no-retry rules remain unchanged.
Worker-wait remains held, friend-owned V31 pending, manuscript unchanged.
