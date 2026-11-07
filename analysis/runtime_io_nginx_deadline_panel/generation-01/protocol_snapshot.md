# Fresh NGINX calibration-defined deadline panel

Prepared 10 October 2026 after the known power, rate, worker-wait and offline
CDF-scope results. This is a prospective test of ordinary calibration transfer
across several cutoffs, not a new estimator or advance reliability diagnostic.
The historical data motivate this design but supply no calibration samples.
Do not change this document or the implementation after preparation sealing.

## Question and acquisition

Can an ordinary policy-matched response CDF predict deadline misses accurately
across five fresh calibration-defined deadlines, separately for P0 and P1?
The original sealed stock NGINX/native zlib 1 MiB gzip6 workload, single worker
CPU2, Q=25 ms / P=100 ms, client and endpoint conservation checks are reused.
Control tasks use CPU0/1. Both policies use powersave; only CPU2 EPP differs:
P0 balance_performance, P1 performance. A separate privileged lease checks full
policy snapshots and restores CPU2 EPP on completion, owner exit, control EOF
or its bounded deadline. Readback is not a fixed-frequency or thermal-reset
claim. No worker observer, perf/BPF collector or scheduler-switch change is used.

Qualification first runs normal and dead-owner restoration fixtures, four smoke
services (P0/P1 crossed with 4/s and 8/s, 25 warmup plus 20 measured offers),
and two calibration-lifetime services (P0/P1 at 5/s, 25 plus 400 offers).
These 1,030 offers are excluded from the scientific calibration and scores.
Qualification is bounded at 600 seconds, including fixtures and inventory.

Scientific collection uses four entirely fresh calibration services at 5/s,
two per policy, each with 25 warmup plus 400 measured offers. Order is selected
uniformly from the six distinct P0/P0/P1/P1 permutations before collection.
Each policy reference has 800 measured offers; the pooled reference has 1,600.
Six blocks each contain one randomly ordered service per P0/P1 x 4/s/8/s cell.
The 24 validation services each have 25 warmup plus 300 measured offers.
Scientific acquisition totals 8,800 measured offers and 9,500 including warmup;
combined qualification and science total 10,530 offers. Science is bounded at
2,700 seconds. Terminal/preflight time is additional. No qualification or science
attempt may be resumed, retried, overwritten or replaced.

Each policy settles for 10 seconds before service creation. Service lifetime is
120 seconds; an 8-second reserve is required against remaining nominal offered
schedule before warmup and before measurement. Root lease maximum is 150 seconds
(owner deadline 149 seconds). Each cohort reserves 150 seconds plus 120 seconds
of cleanup against the enclosing campaign ceiling. Longer calibration-lifetime
qualification tests the intended 400-at-5/s schedule under both policies; it is
not predictive evidence. Source, boot/topology, ownership, endpoint, restoration,
root observer inventory and immutable evidence checks remain mandatory.

## Cutoff and forecast barrier

For each policy, sort the successful calibration response times, with failed
or dropped offers represented as mass at infinity. Select quantiles 1/10, 1/4,
1/2, 3/4, 9/10 at zero-based rank floor(q*(800-1)). All five must be finite.
If any rank is in the failure mass, retain calibration and forecast evidence and
stop before validation; do not substitute a success-only cutoff. Duplicate times
retain their five quantile labels; these are not independent observations.
The historical 20.565395 ms cutoff is scored descriptively in addition.

Seal all policy panels, references and calibration-derived forecasts globally
before any validation. Each method uses the panel of the validation service's
assigned policy. A response at exactly the cutoff meets the deadline. Every
failed offer misses every finite cutoff; no successful-only renormalization.
Seal 25-offer warmup forecasts before that service's first validation offer.
Canonical replay verifies both time barriers, all raw outcomes and source hashes.

Ordinary controls are policy-matched CDF (main method), pooled CDF, P0 CDF,
warmup-only CDF, and offer-weighted matched-plus-warmup and pooled-plus-warmup
CDFs. Every method is charged the full acquired four calibration services and
receives the same known policy and 25-offer warmup. Selected pools differ; this
comparison makes no cost-saving claim for smaller reference pools. No queue
subtraction, learned selector or reliability refusal rule is introduced.

## Frozen scoring and decisions

For each policy p, block b and cutoff k, average the two absolute miss-probability
errors at 4/s and 8/s, in percentage points. The primary block score is the
maximum of those five averaged errors. Use all six block scores for each policy.
For the matched CDF, form mean +/- 3.164*s/sqrt(6), the rounded-up two-sided
97.5% Student-t interval with five degrees of freedom. Each policy's accuracy
gate is its upper endpoint <=5 pp. Two such intervals use Bonferroni family
coverage >=95% conditional on independent approximately normal block scores.
The result distinguishes both, partly, or neither policy supported.

This tests conditional average block adequacy at the five declared cutoffs,
not every individual cohort, each rate separately or every finite deadline.
Calibration is shared and conditioned upon; its uncertainty is not propagated.
Six chronological blocks do not establish independence or normality. Gate
failure means accuracy is not supported under this contract; it need not prove
population inaccuracy. No expected success probability or power is claimed.

Report every cohort/cutoff error, per-cutoff mean, panel-average error, maximum
individual error, count above 5 pp and historical-cutoff scores. Descriptive
intervals use 2.571*s/sqrt(6), ordinary two-sided 95% t intervals; they are not
simultaneous ten-cutoff guarantees or new acceptance gates. Pooled-minus-matched
primary block scores give a secondary descriptive gain interval; mean >=2 pp
and lower >0 flags descriptive advantage, separate from the accuracy verdict.
Other controls are descriptive. Do not select a winning cutoff or method after
seeing validation and present it as the original primary hypothesis.

Throttling, overlap, dispatch lag, ordinary non-200/transport failures and client
cap drops are retained annotations, not reasons to omit or replace a cohort.
Malformed timing, complete claimed-200 payload corruption/body-cap breach,
identity/source mismatch, conservation failure, budget or restoration errors
stop technically. Preserve the partial attempt; no automatic new generation.

## Interpretation and subsequent work

This study can strengthen or limit the empirical paper's deadline-specific
transfer claim. It cannot by itself establish a novel method, causal power
mechanism, population-wide CDF guarantee or independent host replication.
Worker-wait discovery remains held after inconclusive observer qualification
and unfavorable precision/cost planning. Friend-owned V31 replication remains
pending. After collection, replay and assess the complete frozen result before
any manuscript update or further experiment.
