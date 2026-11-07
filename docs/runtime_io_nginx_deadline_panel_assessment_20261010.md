# Completed NGINX deadline-panel assessment

10 October 2026. Fresh prospective generation 01; previous sealed studies remain unchanged.

**The complete campaign verifies. Neither policy meets the frozen multi-deadline accuracy gate,
although matching policy substantially improves on pooled calibration.**

Status: `deadline_panel_accuracy_not_supported`. Qualification took 4.65 minutes;
science took 35.67 minutes. All 10,530 offered responses succeeded:
1,030 qualification offers, 1,600 calibration measurements plus 100 warmup offers, and
7,200 validation measurements plus 600 warmup offers. All six qualification services,
four fresh calibration services and 24 validation services completed. Normal and independent
dead-owner policy restoration fixtures, source seals, request accounting, owned cleanup and
advance global/per-service forecast barriers pass canonical raw replay. Independent arithmetic
also verifies the primary block scores and decisions. No cohort or cutoff was replaced.

## Frozen primary decision

For each policy/block, average absolute miss-probability errors across 4/s and 8/s at each
of the five cutoffs, then take the maximum cutoff error. The mean of six such block scores
is the primary score, in percentage points (pp). Each matched-policy 97.5% conditional
interval must have upper endpoint <=5 pp. Matching has the same full acquisition as the controls.

| Policy | Matched score (pp) | Conditional 97.5% interval (pp) | Accuracy supported | Pooled score (pp) |
|---|---:|---:|---|---:|
| P0 | 6.611 | [1.831, 11.391] | No | 44.111 |
| P1 | 4.889 | [2.620, 7.158] | No | 38.222 |

P1 has a point score below 5 pp but its upper interval bound exceeds 5 pp. Failure to
support accuracy does not prove population error above 5 pp. The P0 interval also includes
values below the margin. Two policy intervals use Bonferroni family coverage >=95% only
conditional on independent approximately normal block scores. There are six chronological
blocks; independence and normality are unverified. Shared calibration is conditioned upon
and its uncertainty is not propagated. This tests average block adequacy at this panel,
not every individual cohort/rate or every finite deadline.

## Policy-matching advantage and ordinary controls

The pooled-minus-matched primary scores give a secondary descriptive advantage:

- P0: 37.500 pp, conditional descriptive 95% interval [33.703, 41.297] pp.
- P1: 33.333 pp, conditional descriptive 95% interval [30.405, 36.262] pp.

Both meet the predeclared secondary >=2 pp mean and positive lower-bound flag. This
does not replace the failed absolute-accuracy gates or establish a new estimator.

| Policy | Reference | Worst-cutoff block mean (pp) | Upper conditional interval (pp) | Panel-average MAE (pp) |
|---|---|---:|---:|---:|
| P0 | matched | 6.611 | 11.391 | 3.483 |
| P0 | pooled | 44.111 | 44.287 | 26.817 |
| P0 | baseline | 6.611 | 11.391 | 3.483 |
| P0 | warmup | 14.278 | 20.186 | 8.628 |
| P0 | matched_update | 6.515 | 11.261 | 3.490 |
| P0 | pooled_update | 43.542 | 43.709 | 26.512 |
| P1 | matched | 4.889 | 7.158 | 3.067 |
| P1 | pooled | 38.222 | 40.111 | 19.085 |
| P1 | baseline | 78.472 | 80.361 | 40.483 |
| P1 | warmup | 11.556 | 17.228 | 7.344 |
| P1 | matched_update | 4.886 | 7.166 | 3.091 |
| P1 | pooled_update | 37.644 | 39.534 | 18.778 |

Only matched is the primary accuracy method. The controls remain descriptive; no winner
is selected after validation. P0 baseline equals matched by construction. Warmup-only
scores are worse; the weighted matched update gives similar point scores and no upper
bound <=5 pp in either policy. The 25-offer warmup does not establish an advance reliability
signal. All controls are charged the acquired 1,600 calibration offers and same warmup.

## Deadline scope

Cutoffs were frozen from 800 fresh calibration measurements per policy using lower-order
ranks 79, 199, 399, 599, 719, without validation outcomes. Every cutoff was finite.

| Policy | Quantile | Deadline (ms) | Matched mean error (pp) |
|---|---|---:|---:|
| P0 | 1/10 | 17.433213 | 0.500 |
| P0 | 1/4 | 20.683338 | 3.250 |
| P0 | 1/2 | 21.041565 | 4.972 |
| P0 | 3/4 | 21.341755 | 5.389 |
| P0 | 9/10 | 21.562926 | 3.306 |
| P1 | 1/10 | 16.133618 | 1.778 |
| P1 | 1/4 | 16.383808 | 2.806 |
| P1 | 1/2 | 16.664488 | 4.194 |
| P1 | 3/4 | 16.946228 | 4.139 |
| P1 | 9/10 | 17.170689 | 2.417 |

Panel-average MAE is 3.483 pp for P0 and 3.067 pp for P1. Averaging cutoffs would
hide the hardest cutoff; those values are descriptive and do not change the primary gates.
There are 11 cohort/cutoff errors above 5 pp out of 60 in each policy. Maximum individual
errors are 19.667 pp (P0) and 11.000 pp (P1). These are 120 correlated errors, not 120
independent statistical replicates; inference uses six block units per policy.

At the additional historical 20.565395 ms deadline, matched MAE is 3.181 pp for P0 and
0 pp for P1. P1 calibration and validation each have zero misses there: that endpoint is
saturated and does not demonstrate accuracy near the calibration CDF transition.

- Descriptive P0 example: cohort 1 at 8/s, cutoff 3/4 (21.341755 ms), predicts 25.000% misses versus 44.667% observed; error 19.667 pp. Historical-cutoff error: 6.458 pp.
- Descriptive P1 example: cohort 15 at 4/s, cutoff 3/4 (16.946228 ms), predicts 25.000% misses versus 36.000% observed; error 11.000 pp. Historical-cutoff error: 0.000 pp.

These examples are selected after validation to illustrate the complete frozen result;
they are not new chosen endpoints, acceptance tests or pre-validation rules.

## Retained observations and interpretation

Validation cohort 1 (P0, 8/s, block 1) records one throttled period and 4,703 us aggregate
measurement throttling. It is retained. No other qualification/calibration/validation
observation flags or failed offers occur. The aggregate counter cannot assign throttling
to a particular request or explain the forecast error. Matching EPP readback does not fix
physical frequency. The current-host policy snapshot matched the prepared baseline when
this review was saved, through a read-only check; historical boundary/restoration records
are separately verified. No settings were changed during assessment.

The prospectively declared panel confirms an empirical scope limitation: accurate forecasts
at one historical cutoff, including a saturated cutoff, do not establish the frozen
multi-deadline accuracy criterion. Matching policy helps substantially here but does not
qualify that criterion. No causal explanation, latent-distribution shift test, uniform
CDF bound, novel estimator or useful advance reliability selector is established.
This is fresh evidence after known development results, on the same host, not independent
host replication. Numeric differences from earlier panels are not causal treatment effects.

Close this bounded experiment and preserve its complete result for manuscript integration.
Do not automatically repeat, relax the margin, drop the throttled cohort or tune a selector
on these outcomes and call it confirmed. Before more collection, any new reliability signal
needs a concrete mechanism, measurement feasibility and equal-cost ordinary comparator.
Worker-wait remains held; the friend-owned independent V31 replication remains pending.
The open manuscript is unchanged by this review.

Replay this assessment with `python3 -B analysis/review_nginx_deadline_panel.py --verify`.
