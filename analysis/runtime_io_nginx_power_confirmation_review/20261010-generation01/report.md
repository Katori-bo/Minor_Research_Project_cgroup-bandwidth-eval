# Completed NGINX policy-matching confirmation

10 October 2026. The original pilot and fresh confirmation remain sealed and unchanged.

**Policy matching improved the pooled comparison but failed the frozen absolute-accuracy criterion.**

The new qualification passed, and all four calibration and twenty-four validation cohorts
completed: 8,800 measurement offers and 700 warmup offers. The scientific campaign
lasted 35.79 minutes. Full raw replay, source/evidence seals,
global and pre-measurement warmup forecast barriers, owned cleanup and policy restoration verify.
A separate current-host readback matched the prepared policy baseline when this review was created.

The repeated “Selection seal verifies; service implementation/qualification remain pending”
line is an inherited selection-validator message in `gzip_candidate_prepare.py`.
It is not the fresh confirmation’s status: the fresh qualification and complete campaign verify.

## Frozen primary result

Primary deadline: 20.565395 ms. Errors concern all-offer deadline-miss probabilities,
in percentage points (pp), rather than response-time error or percent relative improvement.

| Forecast | Mean absolute error (pp) | Conditional 95% interval (pp) | Maximum error (pp) | Cohorts >5 pp |
|---|---:|---:|---:|---:|
| Pooled calibration | 24.729 | [20.377, 29.082] | 44.583 | 18/24 |
| Policy-matched calibration | 15.708 | [12.695, 18.721] | 43.167 | 11/24 |
| P0-only calibration | 55.458 | [52.445, 58.471] | 79.500 | 23/24 |
| 25-offer target-rate warmup | 4.778 | [0.582, 8.974] | 25.000 | 7/24 |
| Matched + warmup samples | 15.250 | [12.286, 18.214] | 41.970 | 11/24 |
| Pooled + warmup samples | 24.350 | [20.036, 28.664] | 43.903 | 18/24 |

Matched improvement over pooled calibration is 9.021 pp, with conditional
95% interval [1.746, 16.296] pp. This meets the frozen mean improvement >=2 pp
and positive interval-lower-bound conditions. It does not establish a >=2 pp lower confidence bound.

Matched mean error is 15.708 pp and its conditional upper bound is 18.721 pp,
above the required <=5 pp. Therefore the combined acceptance result is negative.
Warmup is more accurate on average in this campaign, but its upper bound is 8.974 pp
and its maximum error is 25 pp. It has a later decision time and additional acquisition
budget; it does not rescue the primary matched-calibration claim or establish a reliable rule.

Intervals condition on the frozen calibration and assume adequate independence among
six consecutive block means. They do not propagate calibration uncertainty or provide
a guarantee for each future cohort. All blocks and both policies remain included.

## What failed to transfer

P0 (powersave / balance_performance) calibration predicted 79.5% misses. Its two
calibration cohorts gave 81% and 78%; agreement between them did not ensure transfer.
P0 validation averaged 48.889% misses, ranging from 36.333% to 84.333% across its
twelve cohorts. Its policy-specific MAE was about 31 pp. P1 (powersave / performance)
had zero recorded deadline misses in calibration and all twelve validation cohorts;
this finite sample does not certify a zero future miss probability.

Neither calibration nor validation recorded throttling, unsuccessful offers, overlap
or dispatch-gate observations. Allowing throttling enabled a complete prospective
contract, but no recorded throttle event explains this confirmation’s prediction failure.

The successful P0 mean response changed from 20.507 ms in calibration to 20.190 ms
in validation, a decrease of about 0.317 ms. A large share of validation responses
(61.94%) lay within 0.5 ms of the fixed deadline. This is descriptive evidence that
small timing-distribution changes can produce large miss-probability changes at this
deadline; it does not identify the physical cause. Calibration was at 5/s and validation
at 4/s or 8/s, in later fresh instances. Rate, chronology, distribution shape and
unmeasured physical state remain possible explanations. Matching EPP does not measure
fixed frequency, thermals, idle state or exclusive access to shared CPU resources.

The assigned-policy contrast in validation is strong, but an effect of policy and
accurate within-policy forecast transfer are different questions. The randomized
contrast still requires no interference/carryover assumptions; it cannot explain
the historical unobserved NGINX excursion. Pooled calibration deliberately combines
different assigned policies, so its defeat does not establish superiority over an
established state-aware prediction method.

At the fixed secondary 10 ms deadline every measured response missed; at 25 and
50 ms every measured response met the deadline. Zero global-CDF errors there are
trivial endpoint saturation in this sample, not grounds to replace the failed primary deadline.

## Paper contribution and next decision

A defensible empirical statement is: **under this single-host NGINX workload,
matching the assigned EPP policy reduced mean deadline-probability error relative
to pooled calibration, but did not suffice for the frozen accuracy target.**

This strengthens the empirical account of where inexpensive calibration transfers
and where it fails. It does not establish a novel estimator, a general reliability
diagnostic, physical frequency causation or conference-level novelty by itself.
Keep the independent V31 replication separate. Treat the stopped pilot as exploratory
and this fresh confirmation as the complete prospective outcome; do not combine
them into a favorable acceptance test. Close this bounded collection branch and
integrate the result into the empirical paper without further automatic runs,
deadline changes or a diagnostic fitted to these validation outcomes.
