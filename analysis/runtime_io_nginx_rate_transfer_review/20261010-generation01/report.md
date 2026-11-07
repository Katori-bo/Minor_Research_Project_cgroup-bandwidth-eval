# Completed NGINX rate-transfer assessment

10 October 2026. All frozen studies and their evidence remain unchanged.

**Rate-matched calibration met the accuracy target; its required advantage over ordinary 5/s calibration was not supported. Both references were accurate in this campaign.**

Qualification, six fresh calibration cohorts and all twelve validation cohorts replay successfully.
The scientific campaign took 23.96 minutes and retained
6,000 measured offers plus 450 warmup offers. All scientific responses succeeded.
Source/evidence seals, advance forecast barriers, owned cleanup and read-only fixed-P0 checks verify.
A separate current-host policy readback matched the prepared baseline when this assessment was saved.

## Frozen primary comparison

Deadline: 20.565395 ms. Errors are absolute deadline-miss probability errors in percentage points (pp).

| Reference | Mean error (pp) | Conditional 95% interval (pp) | Maximum error (pp) | Cohorts >5 pp |
|---|---:|---:|---:|---:|
| Rate-matched calibration | 1.194 | [0.808, 1.581] | 2.333 | 0/12 |
| Ordinary 5/s calibration | 1.972 | [1.037, 2.907] | 4.500 | 0/12 |
| Pooled 4/5/8 calibration | 1.361 | [1.091, 1.632] | 3.208 | 0/12 |
| 25-offer target-rate warmup | 7.528 | [4.629, 10.426] | 13.667 | 7/12 |
| Matched + warmup | 1.149 | [0.841, 1.457] | 2.182 | 0/12 |
| 5/s + warmup | 2.073 | [1.055, 3.091] | 4.485 | 0/12 |
| Pooled + warmup | 1.371 | [1.074, 1.669] | 3.216 | 0/12 |

Matched improvement over 5/s calibration is 0.778 pp, conditional 95% interval [-0.375, 1.931] pp.
It fails both the frozen >=2 pp mean-improvement condition and the positive interval-lower-bound condition.
This does not prove equivalence or absence of any rate-matching benefit. The rate-matched, 5/s and pooled
references each have an accuracy upper bound <=5 pp; all their individual cohort errors are <=5 pp.

Intervals use six consecutive block means and condition on frozen calibration. Adequate block independence
is assumed; calibration uncertainty and between-campaign variation are not propagated. These are not
per-cohort guarantees. Warmup and updated references have later decision times and different acquisition budgets.

## Population and applicability

Observed primary miss probabilities ranged from 78.667% to 84.000%. Accurate forecasts here mean
accurately predicting that most offers miss the deadline; they do not mean the service meets the deadline.
The primary endpoint was not saturated. Rate-specific calibration predicted 81.000% at 4/s,
79.500% at 5/s and 81.875% at 8/s.

Validation cohort 5 (8/s, block 3) recorded one throttled period and 6,600 us aggregate throttling;
cohort 9 (8/s, block 5) recorded one throttled period and 9,133 us. Both were retained as prescribed
by the all-offer contract. These aggregate counters do not assign a throttle event to a specific response.
No other scientific observation flags or unsuccessful offers were recorded.

At the predeclared secondary 10 ms endpoint all measured offers missed; at 50 ms all met the deadline.
Those zero-error endpoints are saturated. At 25 ms matched and 5/s MAE were 0.027778 pp;
this secondary endpoint does not replace the primary comparison.

## What this changes in the research argument

The preceding power-policy confirmation failed its absolute-accuracy target. In this fresh campaign,
the ordinary 5/s fixed-P0 reference also transferred accurately, so the earlier failure cannot be
attributed to rate mismatch or declared repaired by rate matching. Chronology, fresh instances and
unmeasured physical state differ across campaigns. Matching an EPP setting does not fix physical frequency.
The campaigns are separate empirical episodes, not randomized trials of why the historical failure occurred.

The defensible claim is accurate empirical-CDF transfer in this episode, without demonstrated incremental
advantage from matching the offered rate. This result establishes neither a novel estimator nor a general
reliability diagnostic. Preserve the preceding failure alongside this success in the empirical paper.
Close this bounded collection branch; do not automatically repeat, change deadlines or fit a rule to
these validation outcomes. The friend-owned independent V31 replication remains pending.

Reproduce this assessment with `python3 -B analysis/review_nginx_rate_transfer.py --verify`.
