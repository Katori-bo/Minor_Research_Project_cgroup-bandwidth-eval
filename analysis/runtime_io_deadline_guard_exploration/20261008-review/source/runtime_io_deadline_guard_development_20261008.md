# Developing a deadline-specific reliability diagnostic

8 October 2026. The user has selected the diagnostic route toward a stronger
paper. Offline development has started. No new scientific measurement has been
launched. This document and its new outputs do not revise V22–V28, their frozen
thresholds, unsuccessful studies, or the current paper's evidential claims.

## Research target

Answer: **Under what arrival schedules and deadlines is a CPU-derived capacity
estimate sufficiently reliable, and when should the forecast be withheld or
recalibrated?** The output should tell someone which forecasts to trust within
a declared error tolerance, with useful coverage and an honest uncertainty
assessment. Another small improvement in average prediction error is not the
target.

A candidate contribution is a validated characterization of the calibration
granularity and uncertainty needed for deadline forecasting under a fractional
quota. A new diagnostic is possible, but has not been established. A conditional
FIFO inequality, estimator disagreement, and empirical min/max ranges are not
individually novel. A publishable difference from closest work remains a gate.

## Closest work found during this development

| Primary source | What is already established | What our proposed study would have to add |
|---|---|---|
| [Kumar et al., Enhanced Inferencing, 2009](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799) | Workload-dependent demand and overhead inference using utilization and response measurements. | Reliability of a particular all-offer deadline forecast under a quota, not rediscovery of load dependence. |
| [Grohmann et al., SARDE, 2021](https://doi.org/10.1145/3463369) | Continuous tuning and selection of an ensemble of demand estimators in changing environments; publisher abstract reviewed. [Author project](https://gitlab2.informatik.uni-wuerzburg.de/descartes/librede-rrde). | A deadline-specific accept/withhold criterion, if it proves useful beyond estimator selection. We have not audited or reproduced its full algorithm. |
| [Lopatatzidis et al., Robust queueing theory, 2016](https://users.ugent.be/~jdbock/documents/SL-2016-QUES-paper.pdf) | Finite-capacity queue predictions with uncertain arrival/departure parameters and performance bounds; abstract and introduction reviewed. | A practically validated link between measurement granularity and forecasting reliability in this service. Propagating uncertainty through a queue is established. |
| [Sampat et al., Kscaler, APSys 2025](https://tianyin.github.io/pub/kscaler.pdf) | CPU quota/period semantics and application runtime/idle periodicity in autoscaling; author-hosted abstract/source reviewed. | Deadline error and calibration requirements, not a new discovery of quota timescale effects. |

These are targeted comparisons, not an exhaustive novelty search. None is an
implemented performance competitor in the new development. Do not claim that
published estimators or selection algorithms lose to the prototype.

## First prototype and the conditional inequality

For exact scheduled offsets, use the same one-worker FIFO convention as V28:
129 positions including the active job, initially empty, rejected offers counted
as deadline misses. Let `F(mu)` be the modeled all-offer miss percentage at
capacity `mu`, and `m_hat = F(mu_hat)` the candidate estimator's forecast.

For a reference range `[mu_lo, mu_hi]`, first simulate the infinite FIFO at
`mu_lo`. If its peak occupancy exceeds 129, abstain. Otherwise every reference
capacity accepts every offer, and the recurrence

```text
completion_i(mu) = max(arrival_i, completion_(i-1)(mu)) + 1/mu
```

is monotone. Thus `F(mu_hi) <= F(mu) <= F(mu_lo)` over the entire reference
range. The candidate point forecast itself may reject; no monotonicity claim
about its rejecting admission pattern is needed. If real/model discrepancy is
at most `B` percentage points, a conditional error bound is

```text
max(|m_hat - F(mu_hi)|, |m_hat - F(mu_lo)|) + B.
```

Accept conditionally only if this is at most the retained 3 pp tolerance.
Reference overflow or missing qualification produces an insufficient-evidence
outcome. All new FIFO computations use exact rational service times and integer
nanosecond offers; equality at the deadline is timely.

This is a mathematical statement about specified premises. A measured range or
the maximum of two calibration residuals does not establish those premises for
new traffic. The implementation explicitly reports no real-world guarantee.

## Retrospective development results and adverse findings

The source cohort is sealed V28. Every outcome was known before this rule was
conceived. Splitting its calibration into two anchor trials in block 1 and two
discrepancy trials in block 2 prevents direct validation fitting in the code,
but cannot turn this development into prospective evidence.

**Initial scalar prototype.** Reference range 149.4167–149.5000 jobs/s;
held-out maximum model discrepancy 1.5015 pp. On the nonlinear benchmark it
accepted eight accurate short-cycle forecasts and flagged eight long-cycle
forecasts, including all three above the 3 pp error tolerance. Five warnings
were unnecessary by that observed tolerance. Whole/idle/linear were flagged in
all sixteen trials; busy was accepted in all sixteen.

This result has a serious qualification problem: the anchor range contained
the measured validation busy bounds in only **1/16 trials**. Its apparent
success cannot validate the capacity premise. Retain this failed premise check.

**Duration-matched accounting exploration.** Using raw block-1 calibration
events, replay fixed subwindows inside the already-qualified busy intervals.
Starts are spaced 0.25 s apart; durations are 1, 1.8, and 3 s, chosen after
seeing V28's measurement definitions. Preserve conservative clock brackets.

| Window duration | Observed calibration rate envelope | Correlated subwindows |
|---|---:|---:|
| 1 s | 148.0000–152.0000 jobs/s | 72 |
| 1.8 s | 148.3333–151.1111 jobs/s | 40 |
| 3 s | 148.6667–150.3333 jobs/s | 8 |

The matching 1/1.8 s envelopes contain all sixteen validation aggregate busy
bounds. This concerns aggregate validation windows, not every validation
subwindow or statistical future coverage. Overlapping windows are correlated;
72 windows are not 72 independent experiments. The conclusion is that the
original average hid variation relevant to a shorter measurement scale.

Widening the reference range while retaining the global scalar residual maximum
raises that margin to 11.5616/7.6827 pp. The scalar guard then rejects every
forecast, including accurate busy forecasts. It has no useful coverage in this
replay. Do not widen the range and claim only its favorable coverage result.

**One timing-envelope alternative.** Use the duration-matched reference ranges.
From the separate block-2 calibration request records, bound observed latency
outside the fast/slow FIFO latency envelopes. Calibrated early/late shifts are
64.511/76.457 ms for the 1 s range and 70.316/84.838 ms for the 1.8 s range.
Propagate these shifts through per-offer deadline classifications rather than
adding one global percentage-point penalty. The forecast interval is

```text
lower misses = count(fast_model_latency - early_shift > deadline) / offers
upper misses = count(slow_model_latency + late_shift > deadline) / offers
```

It conditionally accepts a point prediction only when its worst distance from
this miss interval is at most 3 pp. Reference overflow still causes abstention.
No forecast error, shift, or tolerance is fitted from validation records.

| Candidate capacity input | Accepted forecasts | Inaccurate accepted | Flagged forecasts | Accurate but flagged |
|---|---:|---:|---:|---:|
| Whole-run CPU/job | 0 | 0 | 16 | 0 |
| Idle-corrected CPU/job | 0 | 0 | 16 | 0 |
| Linear regression | 0 | 0 | 16 | 0 |
| Busy capacity | 4 | 0 | 12 | 12 |
| Nonlinear benchmark | 4 | 0 | 12 | 9 |

Its miss envelope contains all sixteen observed validation miss fractions.
The price is substantial over-warning. Compared with accepting the nonlinear
benchmark whenever capacity error is under 5%, this avoids the three observed
false reassurances, but also withholds nine accurate forecasts. Compared with
always withholding, it preserves four useful forecasts. These are retrospective
tradeoffs, not established superiority or future reliability.

Only four distinct validation schedules and four blocks underlie these tables.
The five methods share the same sixteen trials; they do not create eighty
independent observations. The current guard requires busy probes and adds
calibration; no cheaper-measurement claim is supported. Always using the busy
point estimator was accurate in V28 and remains a strong practical alternative.
The guard would need to provide useful reliability information or a demonstrated
calibration-reuse advantage, not merely relabel its forecasts.

## Required next stage before a stronger paper

The present candidate is a development artifact. It is **not ready for a
scientific novelty claim or a new measurement launch**. Proceed in this order:

1. Audit the full closest diagnostic/selection methods and choose applicable
   baselines. Resolve the load-dependent method's units and scheduling mapping.
   A declared adaptation may be compared, but must not be called the published
   algorithm without a faithful implementation. Keep the current nonlinear
   benchmark and the always-busy strategy as strong controls.
2. Settle the timing-envelope rule and its scope. Explicitly specify capacity
   window duration, clock bounds, independently calibrated timing shifts,
   calibration budget, abstention, and how quota stalls enter its assumptions.
   Keep the 3 pp operational tolerance. Do not choose a margin using validation
   errors or promise statistical coverage from observed extrema.
3. Implement and verify a separate fresh validation package with all guard
   decisions and all comparator forecasts sealed before the first validation
   offer. Synthetic checks and existing-data development are permitted; no
   performance pilot may select favorable conditions.
4. Evaluate benign and sensitive schedules, then an independently implemented
   workload or a new quota. Report erroneous accepted forecasts, acceptance
   coverage, unnecessary warnings, envelope coverage, all failures and total
   calibration cost. Do not present detection alone as practical success.

There should be no third threshold variant on V28 to obtain a favorable table.
The two scalar/timing variants and their adverse results above remain visible.
Further source-driven changes belong to a new version, with disclosed reasons.

## Concrete validation design to prepare

This is a **draft design, not a frozen or launchable protocol**. For an initial
fresh retained-service gate, use 16 calibration slots and 24 validation slots.
The calibration sequence follows the broad V28 idle/steady/mixed budget with
separate capacity-anchor and timing-discrepancy blocks; exact rates, ordering,
monitor qualification and window grids must be sealed in the new design.

For validation, cross low arrival rates `0.1*mu_ref` and `0.2*mu_ref` with cycle
lengths 2/6/12 s, low phase two-thirds and high phase one-third, and
`high=1.2*mu_ref`. `mu_ref` is derived by a declared formula from fresh anchor
calibration, never the historical numeric capacity. Generate exact timestamp
vectors mechanically, with four balanced blocks and no performance-driven
schedule selection. Include both benign short bursts and long bursts; V28's
all-inaccurate whole-cost cases alone cannot evaluate unnecessary warnings.

Primary operational gates should require zero erroneous accepted forecasts
across the fresh accepted set, nontrivial acceptance (proposed at least one-third
of available estimator/schedule decisions), and disclosure of every reference
or timing-envelope miss. These are finite-sample adequacy screens, not a claim
that future failure probability is zero. Assess paired comparisons at the block
level; individual requests are not independent replicates. Methods on the same
trial are correlated. Report per-method and per-schedule results even if a
combined gate passes. If a baseline gives the same or better safety/coverage
tradeoff, the new diagnostic's advantage is unestablished.

The existing exact-image and operational qualification must be preserved.
Technical retry budget should remain one total, with no scientific retry for
an unfavorable result. Stop on failed cleanup, watchdog intervention, failed
measurement qualification or an exhausted retry. Choose and freeze a bounded
external-runtime budget after the implementation audit; do not extend it to
obtain a positive result.

An independent JSON decode/transform/encode worker, or another justified
non-SHA workload, is a candidate transfer arm. Its implementation, demand scope,
fixed payload, image identity and load scaling need qualification before any
launch. A second SHA iteration count is not independent application transfer.
Fresh evidence from the first gate cannot be used to tune a rule and then be
reused as its independent transfer evidence. Any transfer design must be sealed
before its outcomes and retain failures. Neither a larger campaign nor a new
workload alone guarantees novelty.

## Artifacts and verification

- [Conditional guard](../analysis/deadline_capacity_guard.py) and
  [soundness/leakage tests](../analysis/test_deadline_capacity_guard.py).
- [Initial exploratory replay](../analysis/explore_deadline_capacity_guard.py)
  and [sealed result](../analysis/runtime_io_deadline_guard_exploration/20261008-01/report.json).
- [Duration-matched raw-event replay](../analysis/explore_busy_window_transfer.py)
  and [sealed result](../analysis/runtime_io_deadline_guard_exploration/20261008-window-transfer/report.json).
- [Timing-envelope alternative and scalar comparison](../analysis/explore_deadline_timing_envelope.py)
  and [sealed result](../analysis/runtime_io_deadline_guard_exploration/20261008-timing-envelope/report.json).

Nine software tests pass, including randomized checks of interval soundness,
exact deadline ties, queue overflow, rejecting point estimates, malformed inputs,
and refusal of validation data or reused blocks in calibration. Two timing
tests additionally check trace accounting and per-offer envelope containment.
These checks
validate software behavior, not the scientific reliability assumptions.

The new replays verify original seals and input digests and write to new paths.
Their exact FIFO deadline forecasts agree with the historical V28 forecasts.
Raw counter/window bounds were independently checked with direct completion
brackets. All development is retrospective. No scientific effect is added by
the tests or replays. The revised paper remains the honest record of completed
science until new evidence supports changing its contribution.

Current operating constraint: the retained measurement pipeline excludes a
running desktop app and uses an external interactive terminal; see
[V28 execution](runtime_io_v28_execution.md). The future study needs its own
prepared command and verified package. Running an old V28 command would repeat
an old study, not validate this diagnostic.
