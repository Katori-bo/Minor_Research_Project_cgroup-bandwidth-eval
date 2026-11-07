# Deadline-specific versus distribution-wide transfer: offline experiment

10 October 2026. User authorized more experimentation before another manuscript
update. This bounded retrospective experiment uses saved data; all historical
outcomes are already known. The calculation is specified before computing its
new summaries, which does not make it independent or prospectively collected.

Question: does small empirical forecasting error at the historical primary
deadline coincide with close calibration-to-validation response CDFs, or can
the agreement be specific to that deadline?

Retain all 54 validation cohorts from original NGINX, power confirmation and
rate transfer, including failures and throttling. Use all original calibration
offers. No worker counters, new hardware observer, future selector or fitting.

Methods: original pooled reference for original NGINX; pooled, assigned-policy
matched and original P0 baseline for power; pooled, target-rate matched and
ordinary 5/s reference for rate. They reproduce the original primary-deadline
forecasts. Their original full acquisition costs remain charged; this replay
claims no reduced profiling expense or equally sized selected reference pools.

Report, for every cohort/method:

1. Absolute all-offer miss-fraction error at the unchanged 20.565395 ms deadline.
2. The exact maximum empirical CDF difference over every finite nonnegative
   deadline, computed at the union of calibration/target successful completion
   times. This is a descriptive supremum, not a newly chosen operating deadline.
3. Errors at calibration-only lower order-statistic quantiles 10%, 25%, 50%,
   75% and 90%, index floor(q*(n-1)). Power uses the assigned-policy calibration
   panel; rate uses the ordinary 5/s panel; original uses its original pool.
   All methods in each cohort share that panel. Duplicated deadlines remain
   labelled duplicates; an infinite failure-mass quantile is unavailable.

Failures are misses at every finite deadline. Equality completes on time.
Finite successful outcomes and total offered counts define the sub-CDF, preserving
failure mass rather than normalizing on successes. No target contributes to a
panel cutoff or an advance input. Targets enter only subsequent scoring and the
diagnostic location of the empirical supremum.

Summarize each campaign, each power policy and each rate, with every individual
cohort and six chronological block summaries retained. Count primary error <=5 pp
alongside empirical CDF discrepancy >5 pp to illustrate scope, not to replace
historical acceptance gates or declare latent-distribution transfer failure.
Report descriptive paired gains across blocks; no hypothesis tests or new
accuracy/advantage decisions. The CDF supremum includes finite-sample variation;
shared references, temporal dependence and one host prevent an independent
population or causal interpretation. No simultaneous confidence guarantee.

Stop after this single specification, source tests and saved calculation replay.
Do not tune deadlines, search predictor windows, launch traffic, change margins,
reuse this data as fresh confirmation, or update the open manuscript. A useful
finding would refine the scope of the empirical paper. Any fresh experiment
would need its own question, comparator, timing/cost and qualification contract.
