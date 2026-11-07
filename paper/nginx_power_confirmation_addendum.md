# NGINX power-policy confirmation: result for the next manuscript revision

10 October 2026. Addendum to the completed empirical extension; the finalized
manuscript and its audit snapshots retain their historical scope. Independent
V31 hardware replication is pending with the user's friend and is not included.

## Proposed results paragraph

A separate prospective follow-up tested whether matching an assigned server
energy/performance preference improves complete-response deadline forecasts.
Stock NGINX served the unchanged 1 MiB gzip workload on one worker under a
25 ms quota per 100 ms period. Both treatments used the powersave governor:
P0 selected balance_performance EPP and P1 selected performance EPP. Four fresh
400-offer calibration cohorts at 5 requests/s supplied two references per
policy. Six randomized validation blocks each crossed both policies with
4 and 8 requests/s, using 300 measured offers per cohort. The primary deadline
remained 20.565395 ms; unsuccessful offers would count as misses in every
calibration, warmup and validation reference. Throttling was permitted and
retained under the new all-offer contract. Qualification and all 24 validation
cohorts completed, with no recorded scientific-phase throttling or unsuccessful
offers. Source/evidence seals, raw outcomes, advance forecast barriers, cleanup
and restoration replayed against the collector's saved results.

| Ordinary forecast | Mean absolute miss-probability error (pp) | Conditional 95% interval (pp) | Maximum error (pp) | Cohorts >5 pp |
|---|---:|---:|---:|---:|
| Pooled calibration | 24.729 | [20.377, 29.082] | 44.583 | 18/24 |
| Policy-matched calibration | 15.708 | [12.695, 18.721] | 43.167 | 11/24 |
| 25-offer target-rate warmup | 4.778 | [0.582, 8.974] | 25.000 | 7/24 |

Matching reduced mean error relative to pooling by 9.021 pp, with conditional
95% interval [1.746, 16.296] pp, meeting the frozen >=2 pp mean-improvement and
positive interval-lower-bound conditions. Its accuracy upper bound nevertheless
exceeded the required <=5 pp. The combined acceptance result was therefore
not supported. Under P0, calibration predicted 79.5% deadline misses, while
later validation averaged 48.889%; P1 predicted and observed zero misses in
the collected sample. The result demonstrates a scoped improvement over a
pooled reference without sufficient within-policy transfer accuracy.

## Interpretation and limits to retain

This follow-up was chosen after a separate pilot stopped at its zero-throttling
domain gate. The pilot remains exploratory and is not incorporated into the
fresh confirmation's acceptance test. The confirmation changed the target
population prospectively to all offers under the configured quota; it did not
change the workload, deadline, quota or assigned policies. No observed
throttling occurred in the fresh scientific campaign.

Six consecutive block means supply conditional t intervals; adequate block
independence is assumed and calibration uncertainty is not propagated. Warmup
methods have a later decision time and additional acquisition budget. Pooling
deliberately mixes different assigned policies and is not a reproduction of
the strongest published state-aware predictor. EPP readback establishes a
setting, not fixed physical frequency or isolation from shared resources.
Calibration at 5/s and validation at 4/s or 8/s also leave rate versus temporal
transfer unresolved. Finite-sample zero misses do not certify future zero risk.

The contribution is empirical: policy matching improved the tested ordinary
reference but was insufficient for the frozen accuracy target. It establishes
no novel estimator, validated reliability diagnostic, universal selection rule,
or causal explanation of the historical NGINX excursion.

## Evidence

- [Full sealed assessment](../analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.md).
- [Original machine-readable comparison](../analysis/runtime_io_nginx_power_confirmation/generation-01/campaign/comparison.json).
- [Prospectively frozen contract](../docs/runtime_io_nginx_power_confirmation_protocol_20261010.md).
- Reproduce with `python3 -B analysis/review_nginx_power_confirmation.py --verify`.
