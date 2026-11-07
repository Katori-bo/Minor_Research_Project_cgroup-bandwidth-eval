# Contribution wording after the completed transfer controls

10 October 2026. Proposed integration wording, separate from finalized
manuscripts and historical snapshots. No new algorithm or independently
received hardware replication is claimed.

## Paper question

How accurately do selected throughput-based, periodic-service and empirical
response-profile forecasts predict deadline-miss probabilities under a fixed
fractional Linux CPU quota, and what do prospective calibration-transfer
controls actually establish?

## Proposed contribution paragraph

We present a reproducible, single-host empirical evaluation of deadline
forecasts under a 25 ms per 100 ms CPU quota. Separately calibrated prospective
Go experiments support a 25 ms contrast between the tested average-rate and
periodic-service approximations, and a 10 ms empirical-CDF result in an observed
low-queue domain. A retrospectively selected ordinary complete-response CDF
achieves nearly the same Go mean error, limiting any claim that stage
decomposition supplies additional predictive capability. A prospective stock-NGINX
study fails its declared calibration-transfer accuracy criterion. Fresh follow-ups
show that matching assigned power policy improves a pooled comparison without
sufficient absolute accuracy, while rate-matched calibration transfers accurately
in a later campaign without demonstrating the required improvement over ordinary
5/s calibration. Together these results quantify the adequacy and transfer
limitations of the tested procedures, preserving both successes and adverse
outcomes. They introduce no new estimator or general reliability guarantee.

## Three contributions to organize the revision

1. Prospective, numerical comparisons of specified approximations at fixed
   deadlines and declared traffic/domain contracts, with the weak-comparator
   assumptions stated alongside the large gains.
2. A calibration-transfer audit retaining the adverse NGINX result and complete
   ordinary-control follow-ups: assigned-policy matching was insufficient in
   one campaign, and target-rate profiling did not establish extra advantage
   over a shared reference in another.
3. An auditable evidence artifact covering fresh calibration, advance forecast
   barriers, all-offer scoring, domain exits and preserved raw outcomes. This
   is reproducibility strength, not an algorithmic novelty claim.

## Limits that belong in the abstract/discussion

The experiments use one physical host; the friend's independent V31 result
remains pending. They do not execute a compatible published predictor under
a matched contract or identify the physical cause of the historical NGINX
excursion. Primary block-based intervals rely on sequential-block assumptions;
NGINX intervals exclude calibration uncertainty. Accurate probabilities can
describe poor deadline compliance. The combined record does not identify an
advance observable that distinguishes reliable from unreliable future transfer.

Periodic-server distribution analysis, load-conditioned profiling, power-aware
latency prediction and uncertainty-aware deadline allocation already exist.
The [consolidated assessment](../docs/runtime_io_transfer_consolidation_20261010.md)
compares their premises and capabilities directly, with primary citations.
The remaining submission risk is whether this scoped empirical evidence adds
enough insight and breadth beyond established concerns. An exact benchmark
difference or a new successful run does not establish originality.

Use the [power result note](nginx_power_confirmation_addendum.md) and
[rate-transfer result note](nginx_rate_transfer_addendum.md) for the detailed
follow-up numbers. Retain prospective versus retrospective labels, and do not
describe rate matching as a demonstrated repair of the prior failure.
