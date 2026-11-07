# NGINX rate transfer: result for the next manuscript revision

10 October 2026. Additive result note; finalized manuscripts, frozen protocols
and earlier evidence retain their historical scope. Independent V31 replication
is pending with the user's friend and is not included.

## Proposed results paragraph

A fresh prospective comparison tested whether matching the offered traffic rate,
under fixed P0 (powersave governor, balance_performance EPP), improves calibration
transfer to later service instances. Stock NGINX served the same 1 MiB gzip
workload on one worker under a 25 ms quota per 100 ms period. Six fresh 400-offer
calibration cohorts supplied two references each at 4, 5 and 8 requests/s.
Six validation blocks each included one 300-offer cohort at 4/s and one at 8/s,
with randomized order. Forecasts were frozen before validation; the primary
complete-response deadline remained 20.565395 ms. Qualification and all twelve
validation cohorts completed. The all-offer population retained throttling;
all 6,000 scientific measurement and 450 warmup responses succeeded. Two 8/s
validation cohorts recorded throttling and remained in every comparison.

| Ordinary forecast | Mean absolute miss-probability error (pp) | Conditional 95% interval (pp) | Maximum error (pp) |
|---|---:|---:|---:|
| Rate-matched calibration | 1.194 | [0.808, 1.581] | 2.333 |
| Fixed 5/s calibration | 1.972 | [1.037, 2.907] | 4.500 |
| Pooled 4/5/8 calibration | 1.361 | [1.091, 1.632] | 3.208 |
| 25-offer target-rate warmup | 7.528 | [4.629, 10.426] | 13.667 |

Rate-matched calibration met the frozen accuracy-upper-bound criterion of
<=5 pp. Its improvement over ordinary 5/s calibration was 0.778 pp, conditional
95% interval [-0.375, 1.931] pp, failing the required >=2 pp mean improvement
and positive interval-lower-bound conditions. Ordinary 5/s and pooled calibration
also met the accuracy target; all twelve errors for each were <=5 pp. Observed
deadline-miss probabilities ranged from 78.667% to 84.000%, so accurate forecasts
should not be confused with satisfactory deadline performance.

## Interpretation and limits

This campaign demonstrates accurate empirical-CDF transfer in one fixed-policy
episode without supported incremental advantage from rate matching. It does
not prove equivalence between the references. Six block means supply conditional
t intervals, assuming adequate independence and excluding calibration uncertainty.
Each rate-specific reference uses 800 calibration offers. Covering both target
rates requires 1,600, while the shared 5/s reference uses 800 and the pooled
reference uses 2,400. The full campaign acquires all three pools. Warmup and
updated references use later information and have different acquisition budgets.

The preceding power-policy confirmation failed its within-policy accuracy
target. Because the ordinary 5/s reference also succeeded in this new episode,
the earlier failure cannot be declared caused by rate mismatch or repaired by
rate matching. Time, fresh instances and unmeasured physical state vary across
campaigns; they do not form a randomized causal comparison of the repair.
EPP matching does not establish fixed physical frequency. Preserve both episodes
as separate results, without pooling their requests as independent replications.

No novel estimator, validated advance reliability diagnostic or general transfer
guarantee is established. The bounded rate-matching branch is complete; the
result belongs in the empirical account alongside adverse evidence.

## Evidence

- [Sealed assessment](../analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.md).
- [Original comparison](../analysis/runtime_io_nginx_rate_transfer/generation-01/campaign/comparison.json).
- [Frozen protocol](../docs/runtime_io_nginx_rate_transfer_protocol_20261010.md).
- Reproduce with `python3 -B analysis/review_nginx_rate_transfer.py --verify`.
