# Recent target-rate timing: observable and ordinary-baseline gate

10 October 2026. Bounded follow-up authorized by the user's "go ahead" after
the initial reliability assessment. This plan precedes new warmup scoring;
original outcomes and NGINX's adverse warmup example are already known. Every
new result is retrospective discovery. Original forecasts/gates remain intact.

## Decision and hypothesis

Candidate observable: full client-response durations in the same fresh service
at its declared target rate immediately before measurement. These responses
were collected as warmup and originally excluded from scientific prediction.

Operational hypothesis: a recent target-rate response profile may reflect
current timing state better than an earlier reference-rate profile. Assess
whether it improves forecasts or whether disagreement supplies a useful warning.
This is ordinary local profiling, not an assumed new method or identified cause.

The decision occurs **after the target-rate warmup completes, before that
cohort's measurement starts**. This explicitly relaxes the old campaign-level
calibration-only contract. It is not a prediction made before all validation
traffic. Warmup offers, elapsed time and any errors must be charged; they are
real traffic, not free metadata. A guard using measured-window responses is
outside this contract. Original qualification/pilot measurements remain excluded.

## Observable feasibility inventory

- Complete-response warmup durations, schedule/rate and success records are
  present for both Go and NGINX. The runner source executes warmup synchronously
  before reset/drain/control checks and measurement.
- Dispatch, header and complete-body timing milestones are present. They can
  localize elapsed time but do not measure server queue/CPU/runnable time in
  NGINX. A new decomposition cannot add information to the sum by itself.
- Go retains settling/power settings and a host monitor; NGINX lacks comparable
  frequency/thermal/scheduling timelines. We cannot score a common hardware-state
  selector from absent values or use measurements after the decision.
- Aggregate NGINX measurement CPU counters are future information. The
  measurement-before cumulative counter includes startup/warmup/control costs;
  no matched pre-warmup counter isolates warmup CPU demand. Do not construct an
  isolated per-request pre-outcome CPU metric from that number.
- Quota/resource identities are constant checks rather than observed changing
  timing state. Prior aggregate CPU observations did not uniquely identify the
  NGINX excursion's cause.

## Fixed saved-data comparisons

Use all eighteen Go V31 and eighteen NGINX cohorts at their original fixed
primary deadlines. Use complete-response outcomes including unsuccessful offers.
Keep the same 5 pp exploratory error reference; original gates are unchanged.

For each cohort use these predictors without tuning:

1. The old complete-response calibration CDF, unchanged.
2. The empirical miss fraction of the last 25 warmup offers (a common offer
   count, not equal elapsed-time or CPU cost). NGINX has exactly 25 warmup offers;
   Go has 100/220/380 offers over 20 s, depending on rate.
3. The empirical miss fraction of the entire original warmup cohort. Report
   Go's longer observation budget explicitly; NGINX predictors 2 and 3 coincide.
4. Pool the old calibration samples with the entire warmup pool (ordinary
   sample-weighted update). Retain failure mass as deadline misses; no trimming.
5. An equal-weight average of the old and whole-warmup miss fractions, with the
   1/2 weight fixed here as a descriptive ordinary shrinkage comparison.

For each predictor report equal-profile/block MAE, maximum error, each profile
and block, and the number of cohort errors >5 pp. Paired block improvements
are descriptive; no t-test, risk certificate or prospective success gate.

For both last-25 and full-warmup profiles, flag a warning if its predicted
miss fraction differs from the original calibration forecast by >5 pp. The
unflagged/accepted predictor remains the original forecast. Report warning
counts, accepted answer coverage, accepted errors >5 pp and false warnings
(flagged cohorts where original forecast error <=5 pp). No flag threshold is
selected from future accuracy; a warning is not a proof of future error.

Also report request-iid sampling half-widths for the observed warmup sizes as
assumption illustrations only. Disagreement can be sampling noise; iid precision
does not bound state drift or finite future-cohort error. Short warmup and future
measurement can diverge after the decision.

## Prior-method and continue/stop gate

Inspect RScale's adaptive profile/state inputs, online conformity feedback,
and a direct low-cost tail-state method (ReTail if a primary paper is available).
The candidate must beat ordinary recent profiling at matched information/cost,
not merely beat a stale CDF. A new timing feature or tuning a blend is insufficient.

Continue custom development only with a pre-outcome observable that plausibly
constrains future behavior and demonstrates a nonroutine capability beyond
these ordinary comparisons, plus a credible fresh evaluation plan. If recent
profiling itself solves the practical question, retain it as an ordinary remedy.
If even recent profiling fails because timing changes after warmup, preserve
that failure and hold development: a late change cannot be diagnosed from
future-free inputs without additional assumptions/observations.

No new experiment, prototype fitting, deadline replacement, trial removal,
instrumentation deployment or changes to the friend's replication are authorized
by this offline plan. It ends with a specific proceed/stop verdict and the
remaining evidence contract, not another broad collection proposal.
