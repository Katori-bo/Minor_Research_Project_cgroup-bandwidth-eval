# Extension after the completed capacity-calibration paper

Date: 9 October 2026. Status: researched shortlist, completed retrospective
feasibility audit, and proposed next experiment. No new service experiment,
installation, controller or manuscript revision has been launched.

The user's new objective is to pursue a concrete extension after finishing v1.
The recommended research question is:

> When does an accurate average-capacity estimate cease to be sufficient for
> deadline prediction under a fixed fractional CPU quota, and which additional
> timing information restores useful predictions?

This is a candidate empirical and causal extension. Neither originality nor a
new estimation method has been established. A good extension may validate a
consequential boundary of an established approximation without inventing an
algorithm.

## Connection to v1

V1 compares independently calibrated capacity inputs inside one constant-rate
FIFO model. Its successful result is restricted to a 500 ms deadline, uniform
request sizes within each trial, and a 100 ms quota period. It does not test
whether an accurate scalar capacity is sufficient at other time resolutions.

V2 would hold the capacity-calibration question fixed and test the model's next
assumption: replacing intermittently available CPU service with continuous
average processing speed. The practical decision is whether a declared arrival
schedule can meet a declared deadline-miss budget with the configured resource
contract. Predictions, causal explanation and a deployment recommendation are
separate claims, requiring separate evidence.

## Ranked avenues

| Priority | Question | Specific added result worth seeking | Strong ordinary alternative | Present assessment |
|---|---|---|---|---|
| 1 | When is average speed insufficient for short deadlines? | A reproducible, decision-relevant boundary; controlled evidence separating periodic CPU timing from runtime/HTTP delay; fresh validation of an adequate correction | Periodic-budget replay, conditional supply bounds, and a separately calibrated response-delay term | Best immediate lead: the retained data show deadline sensitivity, while mechanisms and practical utility remain open |
| 2 | Can identical request mixtures and aggregate capacity produce materially different deadline outcomes when expensive requests cluster? | A validated boundary for class/order information under the quota, beyond ordinary variable-service queueing | Per-class service-demand FIFO replay with the exact class sequence; mixture-aware queueing | Concrete alternative; generic service variability and head-of-line blocking are established and cannot carry novelty |
| 3 | What causes the whole-run/busy accounting mismatch and nonlinear load curve? | A reproducible causal decomposition that predicts the response to an intervention | Ordinary profiling, load-dependent demand inference, controlled CPU-performance and runtime-work measurements | Valuable if a discriminating measurement can be qualified; previous attribution and execution-state screens did not establish it |
| 4 | Does the validated boundary transfer to an independent service? | A scoped real-service replication of a specific surviving boundary or mechanism | Workload-specific recalibration and direct measurement of the practical decision | Useful confirmation after a lead survives; changing the benchmark alone is not the central contribution |

Quota-period selection remains a separately held candidate. This proposal keeps
quota and period fixed and does not restart the closed FIFO theorem, cheaper
calibration, passive-forecast guard, profiler, attribution-method or quota-update
campaigns. Their negative assessments remain relevant. The former Memcached
proposal was not adopted and is not silently made the new testbed here.

## First completed step: retrospective deadline audit

The new [audit](../analysis/runtime_io_v2_extension/20261009-deadline-discovery/report.md)
uses all sixteen saved V28 validation trials and the original, unchanged five
capacity estimates. It replays the original finite FIFO contract and recomputes
all-offer outcomes at an exploratory grid of deadlines. Successful responses
must finish within the deadline measured from scheduled offer; failed or missing
offers count as misses. No capacity is refitted.

| Deadline | Whole-run MAE pp | Busy MAE pp | Quadratic MAE pp | Busy maximum error pp |
|---|---:|---:|---:|---:|
| 25 ms | 5.517 | 4.060 | 4.296 | 6.396 |
| 50 ms | 4.831 | 2.255 | 2.682 | 4.062 |
| 100 ms | 5.201 | 0.902 | 1.296 | 2.333 |
| 200 ms | 9.432 | 1.045 | 1.797 | 2.190 |
| 500 ms | 13.494 | 0.453 | 1.169 | 1.714 |
| 1000 ms | 1.897 | 0.000 | 0.000 | 0.000 |

At 25 ms, busy forecasts overpredict misses in all sixteen trials. Their mean
absolute errors in the four blocks are 3.401, 4.342, 4.068 and 4.432 pp.
Both busy and quadratic estimates lose short-deadline accuracy; choosing a
different scalar estimate alone does not eliminate the observed sensitivity.

Importantly, mean observed misses at 25 ms are 75.508%. These historical
schedules are already far from a plausible low-miss operating target. The
audit does not establish that a forecast error changes an actual deployment
decision. The 1000 ms endpoint is uninformative here because every offer is
timely. Accuracy is not a monotone function of deadline across this grid.

Original 500 ms forecasts and outcomes reproduce. The consumed trial seals,
original analysis seal and frozen design hashes pass. The manuscript and
consumed historical files retain their hashes. The audit records input and
output hashes and refuses to replace an existing report directory.

These are retrospective discovery results, selected after V28 outcomes were
known. They establish no new prospective comparison, causal mechanism, phase
measurement, superiority threshold or statistical significance. V1's 3 pp
criterion is not automatically an acceptance rule for V2.

## Primary-source comparison and novelty boundary

The closest capabilities already rule out several broad novelty claims:

- [Linux bandwidth-control documentation](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html)
  describes periodic CPU budgets, throttling, allocation slices and retained
  local runtime. A quota is a ceiling, not a promise of timely CPU delivery.
  A deterministic on/off server is therefore an explicit approximation, not
  an exact description of every CFS configuration.
- [Cucinotta et al., Strong Temporal Isolation Among Containers](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf),
  Section 4.2, derives response approximations and timing bounds under a
  hierarchical reservation scheduler. Periodic service and its approximation
  by average capacity are established. Its guaranteed-reservation premises
  must be distinguished from our ordinary bandwidth ceiling; this distinction
  alone does not establish novelty or prior-method failure.
- [Shin and Lee's author/institution record](https://pure.kaist.ac.kr/en/publications/periodic-resource-model-for-compositional-real-time-guarantees/)
  documents established periodic-resource models and schedulability analysis.
  Full-text retrieval from the Penn repository returned 403 in this screen;
  a second author-hosted full-text URL was inaccessible. Exact supply-bound
  coefficients have not been audited here and should not be reconstructed
  from an abstract or search excerpt.
- [Kscaler](https://tianyin.github.io/pub/kscaler.pdf) already adapts quota and
  period from kernel observations. It is relevant background if the project
  later returns to period selection; it is not a fixed-quota deadline-forecast
  algorithm reproduced by this proposal.
- [Shetty et al., CPU-Limits kill Performance](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf)
  studies CPU-limit effects and resource-management alternatives. Merely
  showing that limits affect latency or microbursts would not add the needed
  result.
- [Kumar, Zhang and Tantawi](https://eudl.eu/doi/10.4108/ICST.VALUETOOLS2009.7799)
  and [Zhang, Li and Zhou](https://scialert.net/abstract/?doi=itj.2013.632.639)
  already address load-dependent demand estimation. The causal-cost avenue
  must add a verified mechanism or consequence beyond generic load dependence.

This is a targeted screen, not an exhaustive originality review. Our inference
is that a measured, practically useful approximation boundary is worth testing.
We have not established that no published work already supplies that boundary.

## Recommended sequence for avenue 1

### A. Establish whether ordinary models already explain the lead

Complete this offline comparison before preparing a fresh performance launcher.
Use calibration records for parameters; do not fit a correction to the sixteen
validation outcomes and call the result prospective. Compare:

1. The original busy-capacity constant-rate FIFO model.
2. The original quadratic-capacity constant-rate model.
3. Constant-rate FIFO with a separately calibrated non-queue response-delay
   component, using a declared scope and no validation residual fitting.
4. Ordinary periodic-budget FIFO replay, with a declared effective CPU demand,
   fixed quota/period, budget state and clock-phase information contract.
5. The same periodic replay with unknown phase: report the range over admissible
   shared phases and initial balances, including how informative that range is.
6. Applicable established timing/supply bounds, after their source equations and
   premises are verified. Without an enforceable lower CPU-service guarantee,
   do not claim a hard finite deadline bound from a bandwidth ceiling alone.

Effective demand derived from quota divided by busy throughput is a fitted
whole-service parameter, not a measurement of isolated SHA CPU work. Calibrated
runtime overhead and idle behavior may require their own terms. Replay must
state unused-budget retention, timer activity and when phase is knowable.
The most favorable phase chosen from validation outcomes is an oracle
diagnostic, not a deployable predictor.

**Gate:** Continue if the retained error pattern survives credible capacity
uncertainty and has a specific explanation to distinguish. If an ordinary
delay term explains it adequately, investigate that scoped boundary rather than
asserting a CPU-phase cause. If ordinary periodic replay suffices, it remains
the reference solution; any custom predictor needs a further useful capability.

### B. Qualify one discriminating experimental intervention

Primary contrast: the same exact offered schedule and uniform request work,
released at different offsets relative to a verified quota replenishment phase.
Keep the configured 50 ms / 100 ms quota and zero burst credit fixed. This
tests timing at equal configured allowance and comparable measured capacity.

Two competing explanations:

| Explanation | Discriminating expectation |
|---|---|
| Averaging intermittent CPU supply loses relevant timing | With stable measured capacity, deadline outcomes vary with qualified phase; an independently specified periodic model explains the contrast |
| Runtime/HTTP/client delay or unstable execution cost dominates | Phase alone fails to explain the contrast; a separately measured delay/cost component accounts for it or the capacity-stability condition fails |

A timestamp relative to container startup or timestamp modulo 100 ms is not
evidence of kernel replenishment phase. Existing per-CPU throttle events are
not automatically group-wide CPU-off intervals. Phase observations must be
joined with clock bounds, accounting semantics and collector-cost evidence.
The earlier observer qualification failures cannot be ignored.

For a simple fresh test contract, consider one allowed physical CPU, one worker
and GOMAXPROCS=1, with client/control work on separate CPUs. This is a changed
affinity contract from V28 and must be recorded. Affinity does not imply
exclusive CPU service. Choose it only after topology and recorder feasibility
are checked; do not modify the host during this planning step.

If phase cannot be observed or controlled with sufficiently small, qualified
cost, stop the phase-causal experiment. An unknown-phase forecasting comparison
is a possible separately justified study, not a substitute causal result.

### C. Freeze a small discovery pilot near a meaningful target

Provisional structural cap: eight qualification attempts, four independent
calibration trials and twelve discovery trials (four phase offsets by three
balanced blocks). This is a 24-attempt preparation/discovery ceiling, not a
power calculation, confirmed configuration or collection authorization from
this document. Technical failures consume the bound; there is no retry-until-pass.

Candidate offsets are 0/25/50/75 ms relative to verified replenishment. Freeze
the exact workload, warm-up/reset/drain semantics, first-cycle budget state,
arrival timestamps, offsets, order and exclusions before launch. Later phases
must remain observable, or phase drift must be included in the analysis.

Keep one request size initially. Derive the offered rate and finite burst
schedule from independent calibration and a declared rule. Aim for a useful
deadline/miss-budget boundary, rather than the historical 75% miss workload.
The application target, acceptable forecast error and minimum useful effect
must be stated before outcomes. Do not search schedules until a preferred
method wins. A deadline grid is a diagnostic; predeclare one primary deadline
and decision, with other deadlines secondary.

Record every scheduled offer, actual dispatch, completion/error/timeout,
request stage timing, capacity bounds, delivered CPU, throttle observations,
phase uncertainty and client saturation evidence. Compare all-offer outcomes,
not only successful-response percentiles. Use independent block contrasts,
not request counts as the replication count. Report calibration effort and
collector cost for each method.

**Discovery verdict:** Continue only for a material, repeatable contrast with
qualified timing and a credible ordinary comparator. If capacity or delivered
CPU differs, retain that result but do not call it a phase-only causal effect.
If the error changes no useful decision, the finding can remain a scoped
approximation result; it does not justify a new decision method.

### D. Confirm the surviving claim independently

Use the pilot variability to select a feasible confirmation budget and assess
statistical power at the declared useful effect. Seal the hypothesis, methods
and forecasts before fresh outcomes. Confirmation must use new trials and
arrival schedules that did not choose the correction. If uncertainty remains
too large at the feasible budget, report an inconclusive result.

Transfer to a second service or host only after this gate, and only to match
the scope of the intended claim. A positive one-host SHA result remains a
bounded result. A controlled boundary plus faithful adequate baselines and
fresh confirmation could support a stronger empirical paper even if the best
remedy is already known.

## Concrete intended output

Working title: **When Average Capacity Is Enough for Deadline Prediction Under
a Fractional CPU Quota**.

The desired paper would answer: what information is sufficient at which time
resolution; what explains an observed failure; whether established timing
models repair it; and whether the repair changes a useful operating decision.
These are intended questions, not results already obtained.

The immediate next technical deliverable is the calibration-only ordinary-model
comparison in step A, with a proceed/stop verdict and an explicit measurement
contract for any surviving experiment. V1 stays the completed paper; the new
deadline audit is extension discovery evidence and is not appended as if it
were part of V1's frozen validation.
