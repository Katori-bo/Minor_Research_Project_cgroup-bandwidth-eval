# Recent target-rate timing: observable gate result

10 October 2026. Completed bounded follow-up to the
[initial reliability assessment](runtime_io_forecast_reliability_assessment_20261010.md).
The [separate warmup analysis plan](runtime_io_recent_timing_observable_protocol_20261010.md)
was fixed before new scoring, after original outcomes were known. Original
experiments and the earlier reliability package remain preserved.

## Verdict

**Recent target-rate response timing is an available pre-measurement observable,
but this screen does not justify a new reliability method.** Direct warmup
profiling worsens average forecast accuracy in both campaigns. Ordinary pooled
updating gives a modest Go maximum-error improvement, while leaving NGINX's
large error intact. The disagreement warning is neither a consistently useful
selector nor an identified explanation of future timing changes.

Hold custom development and new collection at this gate. This is a scoped
negative feasibility result, not proof that all state-informed methods fail or
that no novel contribution is possible. Do not tune a blend, warning threshold
or warmup window until these known campaigns give a desired result.

## What was available before the decision

The Go runner synchronously completes 20 s of warmup, drains/resets the service,
then collects measurement. The NGINX runner synchronously completes 25 warmup
offers, checks drain/process state and captures the starting counters before
measurement. All warmup records were sealed and are reused only for this
retrospective analysis; they do not acquire prospective predictor status.

The changed decision time is **after that trial's target-rate warmup, before its
measurement window**. It differs from the original campaign-wide forecast
sealed before any validation service. Future measurement responses, queue checks
and CPU increments do not enter the new predictions or warning flags.

Other candidate observables have material gaps:

| Observable | Availability and limitation |
|---|---|
| Complete warmup responses at target rate | Present in both; includes complete endpoint variability and sampling noise |
| Warmup dispatch/header/body milestones | Present; client elapsed stages do not isolate server CPU, queue or scheduling |
| Pre-measurement resource/identity checks | Present and stable; no changing timing-state distinction follows |
| Comparable CPU-frequency/thermal state | Go has power/settling/monitor records; NGINX lacks matched timelines, so no common guard can be scored |
| NGINX isolated warmup CPU demand | Unavailable: cumulative measurement-before counters include startup/control; no matched pre-warmup baseline |
| Future measurement CPU and timing excursion | Observed afterward; using these to issue an advance warning would leak outcomes |

NGINX's server queue and per-request CPU/scheduler intervals remain unobserved.
Splitting a known complete response into client milestones is diagnostic; it
does not provide a new predictive input beyond their sum by itself.

## Ordinary forecasting comparisons

All eighteen validation cohorts per campaign are retained at the original
10 ms Go and 20.565395 ms NGINX deadlines. Errors are percentage points of
all-offer miss fraction, equally weighted within the six profile/block groups.
All compared warmup offers succeeded. A 5 pp per-cohort reference is exploratory
and does not replace V31's original 3 pp aggregate gate.

| Predictor | Go mean error | Go maximum | Go errors >5 pp | NGINX mean error | NGINX maximum | NGINX errors >5 pp |
|---|---:|---:|---:|---:|---:|---:|
| Original complete-response CDF | 1.802 | 5.350 | 1/18 | 5.981 | 38.333 | 7/18 |
| Last 25 warmup offers | 5.037 | 14.825 | 9/18 | 9.463 | 52.333 | 10/18 |
| Entire original warmup | 2.589 | 7.121 | 2/18 | 9.463 | 52.333 | 10/18 |
| Old samples pooled with full warmup | 1.878 | 4.936 | 0/18 | 5.971 | 38.549 | 7/18 |
| Equal-weight old/full-warmup probabilities | 2.084 | 5.219 | 1/18 | 6.833 | 45.333 | 9/18 |

No predictor improves mean error in every block of either campaign. The pooled
Go update removes the one observed >5 pp error but slightly worsens average
error. That is an ordinary sample-weighted update on known outcomes, not a
new estimator, a future maximum-error guarantee or evidence of superiority.
NGINX's pooled mean difference of about 0.010 pp does not establish a meaningful
advantage, and its maximum error grows slightly.

## Warning accuracy and answer coverage

For each warmup reference, issue a warning when its miss probability differs
from the old reference by >5 pp. Retain the old prediction for unflagged cases.
A false warning here means an observed old-forecast error <=5 pp; it is a
descriptive label, not a statistical claim that the warning was irrational.

| Warmup discrepancy check | Go coverage | Go accepted errors >5 pp | Go false warnings | NGINX coverage | NGINX accepted errors >5 pp | NGINX false warnings |
|---|---:|---:|---:|---:|---:|---:|
| Last 25 offers | 11/18 (61.1%) | 0/11 | 6/7 | 6/18 (33.3%) | 3/6 | 8/12 |
| Full warmup | 16/18 (88.9%) | 1/16 | 2/2 | 6/18 (33.3%) | 3/6 | 8/12 |

The Go last-25 check has a promising-looking descriptive error/coverage pair,
but NGINX fails the proposed 50% usefulness reference and half its accepted
cohorts exceed 5 pp error. Neither result validates a learned guard or selective
risk certificate. Requests/cohorts on these two known campaigns do not establish
independent forecasting episodes or representative future condition sampling.
The full Go warmup check misses its sole >5 pp original error and flags two
cohorts whose original errors were within tolerance.

## The persistent NGINX excursion remains unresolved

In block 2's approximately-6 requests/s cohort, the warmup miss fraction is
36%, the old reference is 50%, and the later measurement has 88.333% misses.
Direct warmup prediction therefore has 52.333 pp error. The discrepancy guard
does warn because 36% differs from 50% by 14 pp; it catches this large error,
but does not predict the direction or magnitude of the later change and issues
many other warnings. Do not describe it as failing to flag this particular case.

The initial 30 measured offers have 56.667% misses and the remaining 270 have
91.852%, as the preserved exploratory diagnosis already records. This contrast
locates a change between shorter early observations and later responses; it
does not identify a change-point law or causal mechanism. Three other cohorts
with original error >5 pp are unflagged by the warmup discrepancy rule.

The finding supports a narrower practical limitation: **recent target-rate
response observations did not ensure accurate later tight-deadline forecasts
under the tested conditions**. It does not show what a richer state-aware method
would predict or that longer/matched profiles necessarily fail.

## Observation budget and statistical interpretation

NGINX has 25 warmup offers, approximately 3-6 s at its target rates. Go has
100/220/380 offers over 20 s. The last-25 Go calculation uses the tail of that
full existing warmup, so acquiring it still costs the whole warmup; it is not
a newly qualified 25-offer-only collector. Matching the number analyzed does
not match elapsed time, CPU demand or observer cost.

Under hypothetical iid same-distribution requests, the 95% uniform CDF sampling
half-width is 27.162 pp for 25 observations, 13.581 for 100, 9.156 for 220 and
6.967 for 380. These are assumption illustrations, not valid future-drift or
finite-cohort prediction certificates. A small warmup mismatch can be ordinary
sampling noise; more samples at an uninformative state do not bound later shifts.

## Closest adaptive methods

| Primary source and inspection | Capability / required observations | Implication |
|---|---|---|
| [RScale, UCC 2020](https://www.cs.utsa.edu/~plama/papers/UCC20.pdf), Sections III and profiling/overhead passages | Adaptive Gaussian-process tail prediction using application/container/VM metrics and observed response labels | Adaptive state-conditioned uncertainty already exists. Direct warmup CDF is a deliberately simple ordinary comparison, not a reproduction of RScale. |
| [ReTail, HPCA 2022](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf), Sections IV and V-D; drift evaluation VII-G | Request/application features, labelled service times, fixed-frequency isolated feature profiling and online prediction-error monitoring/retraining | Generic state/feature-aware latency prediction and reacting to drift have direct precedent. Our NGINX record does not expose equivalent features or server service-time labels. |
| [Adaptive Conformal Inference](https://arxiv.org/html/2106.00170v1), Section 2 | Sequential feedback from observed prediction errors; updated uncertainty parameter | A live feedback comparator uses outcomes after prediction. It must be evaluated under a separately specified online contract, not credited as an advance certificate for a single future cohort. |

Source inspection occurred 10 October 2026. No competing implementation ran.
The comparison supports an applicability assessment; it neither establishes a
literature gap nor refutes those methods. No novelty follows just from using
pre-outcome hardware features instead of recent responses.

## Research decision and remaining prerequisite

The source/data inventory identifies one executable offline observable and
tests it against ordinary recent profiling, updating and warning checks. Its
result does not meet the prerequisite for a new method. The next stronger
question would need an explicit relationship between pre-outcome measured
state and a bounded/predictable change in future response times, with acquisition
cost and a matched ordinary state model. Current records cannot establish that
relationship. Naming missing frequency/queue/scheduler measurements is not
enough to authorize a collection campaign or demonstrate novelty.

Retain these results as exploratory supporting evidence for the empirical
paper. The separately planned friend-host V31 replication can strengthen its
scope; this follow-up does not modify that package or turn his results into
fresh validation of a newly chosen guard. Hold custom reliability development
unless the concrete state-to-future relationship and independent evaluation
contract can be supplied. The empirical paper remains the justified output.

## Reproduction and preservation

[Implementation](../analysis/screen_recent_timing_observable.py) and
[numerical results](../analysis/runtime_io_recent_timing_observable/20261010/screen.json)
are separate from the prior reliability screen and original campaigns.

```bash
python3 -B analysis/screen_recent_timing_observable.py --verify
python3 -B analysis/screen_forecast_reliability.py --verify
```

Verification recomputes the new screen, checks consumed raw warmup/measurement
files against original seals, reconciles the unchanged original forecasts,
checks strict deadline and unsuccessful-offer accounting and verifies input/
output hashes. This is saved-data software verification, not new scientific
collection, a full campaign replay or prospective guard confirmation.
