# Short-deadline forecast reliability: bounded discovery protocol

10 October 2026. Version 1. Authorized by the user to define and assess this
research path. This protocol is written before the new numerical screen, after
the original Go and NGINX outcomes and prior screens were already known. It is
an exploratory analysis plan, not prospective preregistration of unseen data.
No new performance collection, custom diagnostic training or manuscript change
is part of this stage.

## 1. The decision we want to support

A caller has a specified application/request class, Linux CPU quota, host,
future offered-arrival schedule, finite offer count and deadline. Calibration
ends before that future traffic begins. The caller wants a forecast of the
fraction of all offers that miss the deadline, with an explicit warning when
the available evidence does not support the desired accuracy.

Candidate research question:

> Can observations available before validation identify unreliable transfers
> of an empirical response-time forecast at a short deadline, while retaining
> useful forecasts at comparable measurement cost to ordinary alternatives?

This is a candidate practical use case, not an established production demand.
A warning about unsupported evidence is different from certification that an
accepted forecast is accurate. Forecast error and an SLO decision are also
different: 5 percentage points of probability error is not a 5% miss budget.

For the initial screen use a common **5 percentage point error tolerance**.
This is a declared research reference, chosen for comparison with the NGINX
study, not a replacement for V31's original 3 pp mean-error gate. Report both
per-cohort errors and equal-profile/block mean errors. Neither criterion implies
the other. No new gate is applied to the original experiments.

## 2. What would constitute a contribution

The generic ingredients already exist: empirical latency profiles, confidence
intervals, drift checks, abstention and uncertainty-aware resource decisions.
The earlier passive-burst screen stopped at its custom-method gate; this plan
does not reverse that verdict. It screens a later, narrower empirical-CDF
transfer question using short-deadline evidence unavailable in that old screen.

A method contribution would require a concrete additional capability, such as
lower error risk at matched answer coverage and cost, greater answer coverage
at matched risk and cost, or lower acquisition cost at matched risk/coverage.
Adding a feature, a threshold or a refusal message is insufficient.
An empirical contribution could instead explain a reproducible failure of
ordinary reliability checks under a clearly stated contract. No new mechanism,
first result, universal rule or published-method superiority is assumed.

## 3. Information contracts

**Calibration-only contract (this audit):** use complete successful client
response durations and cohort boundaries from the original four timing cohorts,
their rates/order, declared deadline, future schedule and recorded configuration.
Queue-adjusted V31 samples are retained as a separate diagnostic control.
Use neither future response durations nor future throttling/queue-domain checks
to make acceptance decisions. A host/application name must not be a learned
good/bad label. The Go and NGINX completion conventions remain different.

Calibration technical eligibility is inherited from verified evidence. Zero
calibration throttling is an input check; zero future throttling is an observed
outcome, not an advance predictor. Qualification/pilot/warmup timing samples
are excluded from prediction fits in this screen, matching the old contracts.
Their availability as extra profiling is a future charged alternative, not a
free hidden input.

**Trained deployment (future, separate):** labelled history-to-future episodes
may train and independently calibrate a guard. Charge profiling, instrumentation
and residual labels to every method. Split entire episodes/hosts temporally;
thousands of requests cannot replace independent forecasting episodes.

A universal calibration-only guarantee under arbitrary unobserved future drift
is not a coherent target: identical histories can precede different futures.
Any useful guarantee needs explicit stationarity, bounded-shift or labelled
deployment assumptions. An online rule using new responses has a different
information contract and must charge delay and failures before its warning.

## 4. Bounded existing-data screen

Use exactly two completed campaigns: Go V31 generation-01 and stock-NGINX
prediction generation-01. Retain all 18 validation cohorts in each. Each has
four relevant timing-calibration cohorts and six sequential validation blocks.
The two campaigns are case studies on one host, not independent draws from a
population of service/host conditions. Their primary deadlines are 10 ms and
20,565,395 ns respectively. These fixed endpoints remain primary for this audit.

Reconstruct complete-response calibration CDFs from raw client records; compare
the 10 ms Go point result with its retained retrospective control and the NGINX
point result with its original frozen forecast. Recompute all-offer validation
fractions directly. Reconcile against saved raw-result reviews and hash every
consumed input. Preserve original evidence and manuscript files.

Calculate the following ordinary baselines/checks, without training or choosing
thresholds using validation errors:

1. Always return the pooled complete-response CDF forecast.
2. Timing-rate support check: accept only future steady rates inside the range
   of the four timing cohorts. Other Go calibration slots are not silently
   added to that timing pool. This can be conservative; it is not a theorem
   that interpolation is reliable or extrapolation unreliable.
3. Cohort agreement: accept if every cohort probability at the fixed deadline
   is within 5 pp of the pooled probability. Retain the full cohort range too.
4. Four-cohort t half-width at 95%, df=3 and multiplier 3.182446305. Compute
   this around the equal-cohort mean; distinguish it from request-pooled
   probability. A width <=5 pp is a descriptive precision check, not a valid
   future-risk certificate. Equal-size/independence/stationarity assumptions
   do not become true because a number can be calculated.
5. Request-iid DKW sampling half-width, 100*sqrt(log(40)/(2*n)), as an explicitly
   assumption-dependent illustration. It bounds same-distribution CDF sampling
   uncertainty under iid requests; it does not cover future drift or an observed
   finite future-cohort fraction. It is not an admissible safety certificate here.
6. Deadline sensitivity: tabulate pooled probabilities at D plus/minus 50, 100
   and 250 microseconds. For each offset report the larger one-sided deviation
   from the original probability. Use the 100 us, <=5 pp check as one fixed
   illustrative stress rule; display every offset without selecting a winner.
   A steep CDF is a mathematical sensitivity, not a newly identified cause.
   The offsets are stress scenarios, not measured upper bounds on future shift.
7. Chronological calibration checks: predict cohort j from cohorts before j.
   Go keeps 10 ms; NGINX recomputes the lower pooled median from the prefix only
   so the held-out cohort cannot choose that fold's endpoint. Report all three
   fold errors and a fixed max<=5 pp internal check. These folds have different
   NGINX deadlines and do not confirm the original validation endpoint.
8. Additional-calibration proxy: show the fixed-endpoint pooled forecast after
   each prefix of 1/2/3/4 calibration cohorts and its later validation errors.
   For NGINX this conditions on the final calibration-defined deadline. It is
   descriptive, not a simulation of choosing an early deadline or acquiring
   new informative-rate profiles. No preferred prefix is selected.

Report acceptance/answer coverage, accepted MAE, maximum accepted error and
accepted-cohort errors >5 pp. Give each campaign separately, including profile
and block breakdowns. A calibration-only flag shared by 18 cohorts is one
campaign-level decision, not 18 independent guard validations. Never claim risk
control from 36 dependent cohorts. No interval coverage is inferred from a
cohort envelope. Refusing everything fails usefulness; accepting only endpoints
with all/zero misses supplies weak evidence. Secondary deadline grids remain
context, not extra independent tasks or a source of a winning threshold.

## 5. Literature gate

Map primary sources for periodic-server prediction (Li et al.), profiling
(CEDULE), selective regression, conformal inference and nonexchangeable/online
uncertainty. Include recent uncertainty-aware deadline allocation (MPORA) and
microservice prediction leads. Record inputs, output, assumptions, acquisition
cost, actual inspection level and the precise implication for this contract.
An incompatible output/scheduler does not establish that a method would fail
here. Do not relabel a simplified adaptation as a reproduced published method.
Limit this initial review to ten primary sources plus two unresolved leads;
use a targeted review, not a claim of exhaustive literature coverage.

## 6. Continue / stop criteria

**Continue to a specific design only if all conditions hold:**

- An actual ordinary-comparator failure matters for the caller's decision.
- A named permissible observation plausibly constrains the missing future
  behavior; the explanation is more concrete than adding uncertainty or drift.
- Closest prior work does not already supply that capability under a fair,
  matched information/cost contract; unresolved artifact checks are explicit.
- An independent, affordable evaluation can separate the proposed benefit
  from ordinary cohort checks, standard uncertainty and extra calibration.

Failure of a baseline does not by itself justify a custom method. Cleanly
separating these two known campaigns does not establish a learnable rule.
If the data cannot distinguish competing explanations, record **insufficient
evidence**, name the missing observable, and stop custom development/collection
at this gate. If ordinary alternatives suffice, stop the method route and
retain the scoped empirical paper. Do not tune until Go passes and NGINX fails.

No fixed new trial count is justified by this audit. For planning only: an
independently fixed guard with zero failures in n independent accepted episodes
has one-sided 95% binomial upper risk 1-0.05**(1/n); 59 accepted episodes are
needed to get below 5%. Four error-calibration episodes cannot produce a finite
95% split-conformal residual quantile; 19 is a rank minimum, not a useful-width
or transfer guarantee. Timing cohorts are not automatically such episodes.

For a later pilot, provisional usefulness targets are >=50% answer coverage
overall and among transition-region cases (observed miss fraction 10%-90%),
with errors <=5 pp. These are feasibility targets, not a statistical validation
contract. Any claimed risk certificate needs its own sampling/power design and
stated assumptions. No campaign starts on this protocol alone.

## 7. Relationship to the friend's V31 replication

His independently recalibrated second-host run tests the existing V31 claim,
with the plain complete-response comparator included before validation if its
package is prepared accordingly. Freeze any new guard before his calibration
or validation outcomes are inspected if it is to be evaluated there. If his
records inform development, classify them as discovery and find separate fresh
evidence for confirmation. Do not alter his fixed deadline to make it informative
after seeing results; triviality/domain exit is a retained replication outcome.

## 8. Deliverables and stopping boundary

This stage produces this protocol, a reproducible saved-data screen, consumed
input hashes, a primary-source capability matrix and a continue/stop verdict
with one concrete next action. It does not change sealed results, promote the
plain CDF to prospective status, certify novelty, build a universal guard,
select a conference or run an experiment. Keep the original papers available
as independent completed empirical outcomes.
