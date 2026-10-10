# Contribution and next experiment

7 October 2026. Design proposal and completed offline review. Collection remains
stopped. This document does not freeze or launch a new experiment generation.
The [working draft v3](runtime_io_short_working_draft_v3.md), V22/V23 forecasts,
V25 state failures and all original sources/reports remain unchanged.

Implementation update: [V26 completed and both steady low rates qualified](runtime_io_v26_findings.md).
The composition stage is separately frozen and prepared as
[V27](runtime_io_v27_protocol.md), with [passing offline verification](runtime_io_v27_preparation_verification.md).
Its runtime preparation and sixteen trials remain unrun; use the
[external execution guide](runtime_io_v27_execution.md). The comparator and
forecast stages remain proposals. The planning text below records the staged
proposal; V27's separate frozen protocol governs its collection and analysis.

## What we are trying to add

The current result is a prospective failure of one declared capacity-input
substitution in one service. The candidate advance is a tested diagnostic:
identify when aggregate CPU/job changes with load composition, compare that
diagnostic with an established demand estimator, and determine whether it
improves fresh deadline forecasts. Busy calibration and CPU/completion
accounting are existing techniques. A successful experiment does not itself
establish publication novelty or a new estimator.

The immediate question is narrower:

> With the high-load segments unchanged, does increasing the number of
> genuinely low-load jobs change whole-run CPU/job while busy capacity remains
> approximately stable?

This tests load composition. It does not isolate a specific runtime, frequency,
cache or kernel mechanism. A changed low arrival rate can itself change CPU
cost, so a positive result cannot prove a universal two-state mixture model.

## Completed saved-data review

The [new exploratory report](../analysis/runtime_io_v25_contribution_leads/20261007/report.md)
was generated only after independent V25 completion replay passed. It uses the
original windows and bounded native counters without interpolation.

| Lead across four on trials per size | Small | Large |
|---|---:|---:|
| Minimum conservative lower bound on lower-arrival minus busy user CPU/completion | 0.770 ms | 1.564 ms |
| Maximum conservative system-CPU share of the total phase-cost difference | 25.5% | 14.5% |
| Maximum pre-offer plus post-arrival CPU / whole-run reference excess | 26.1% | 28.2% |

System CPU alone cannot explain the measured phase-cost difference within these
bounds. Even assigning all edge CPU to overhead is insufficient to explain the
excess over `completed_jobs × busy_window_CPU/completion`. The latter is a
conditional accounting comparison, not job-level attribution. Aggregate user
CPU includes application and runtime work; it does not identify SHA cost or
frequency. None of the original low phases qualified. These results narrow
the next test without turning V25 into confirmation.

## Fair comparator and novelty check

[Spinner, Casale, Brosig and Kounev, *Evaluating Approaches to Resource Demand
Estimation*, Performance Evaluation 2015](https://doi.org/10.1016/j.peva.2015.07.005)
is closer prior work than a generic CPU-interface discussion. Its author
preprint, §§2.3.2–2.3.3, describes demand-law and regression estimators;
§3.2 discusses load-dependent demand, and §§4.3.6–4.3.7 examine background
work and processing delays. Those broad measurement problems are established.

For a future forecast comparison, retain the declared whole-run substitution
and busy capacity, and add a nonnegative utilization/throughput regression.
Our specified single-class variant is `CPU_delivery = b + d × completions/s`,
fitted on separate idle and qualified steady-load calibration runs. Its capacity
estimate is `(0.5 - b) / d`; invalid/nonpositive estimates remain failures.
The fitted intercept is a modeling assumption, not evidence of a particular
background process. Check calibration residuals and retain model mismatch.

Do not fit this comparator on saturated windows: that would largely reconstruct
the busy estimate being compared. All estimators must use independent
calibration; validation cannot choose fitting windows or supply parameters.
Calling `U/X` another comparator adds nothing if it uses the same whole-run
counters: it is algebraically the same CPU/job value.

The [IBM capacity-planning guidance](https://www.ibm.com/docs/en/ims/15.5.0?topic=design-performing-capacity-planning)
provides practical precedent for extrapolating CPU usage against transaction
rate, but concerns IMS. We have not established that practitioners routinely
use our exact loaded-container substitution for quota-limited Go services.
Keep that motivation scoped unless direct evidence is found.

## Next collection: qualify the low-load condition first

Prepare only the [four-trial low-load pilot](runtime_io_low_load_qualification_plan.md).
Start with 44,000-iteration jobs; the larger size is deferred because another
parameter repetition would not resolve this design question. Two fixed rates,
15 and 30 jobs/s, receive two trials each. These rates are deliberately below
the historical failed 56.6 jobs/s low phase. Qualification must show shallow
queue and no bounded throttled periods, not merely low average CPU.

If either rate cannot qualify in both recordings, stop this proposed comparison.
Report whether the failure is state or measurement quality. Do not search
windows, relax the state definition, or automatically try another rate.
Any redesign requires a separately versioned proposal.

## Conditional experiment after qualification

The proposed treatment uses four identical 15-second cycles over 60 seconds:
10 seconds at either 15 or 30 jobs/s, then 5 seconds at the retained high rate
169.8 jobs/s. High-load duration, request work and offered high schedule are
identical. Low-job counts differ; total offered jobs legitimately differ.
Both conditions finish with full drain. The intended low windows are
`[3,8] + 15k` and busy windows `[11.5,14.5] + 15k`, for `k = 0..3`.

Propose four blocks, each containing the two low rates with sampler off/on:
16 trials total. Freeze a seeded order that balances treatment and observer
positions before collection. Retain existing service, quota, affinities and
host controls. State checks apply to on recordings; off trials provide a
separate check of whole-run cost and busy-throughput treatment contrasts.
Report sampler effects on those contrasts, not just condition grand means.

The provisional practical screens are a >=3% whole-cost treatment difference
with consistent paired direction and <=2% busy-capacity difference. These are
design targets, not established uncertainty limits or hypothesis-test thresholds.
Use trials/blocks as repetitions. Before freezing this stage, specify the
analysis, uncertainty and sample-size rationale; four blocks alone cannot
certify equivalence. If the bounded design cannot resolve these targets, report
inconclusive and stop rather than interpreting nonsignificance as stability.

## Decision and stopping rules

| Outcome | Consequence |
|---|---|
| Pilot does not establish both low rates | Stop; low/busy composition test remains unsupported. |
| Whole cost changes, busy capacity also changes materially | Report failure of the proposed stable-busy account. |
| Whole cost does not change materially, or uncertainty is too wide | Report absent/inconclusive composition effect; retain current note. |
| Composition effect is reproducible with acceptable recording/state/control evidence | Prepare independent regression calibration and sampler-off deadline validation. |
| Established comparator matches busy calibration on fresh forecasts | Describe an established-method application and scoped measurement warning; do not claim estimator superiority. |
| Busy calibration improves fresh forecasts over the fair comparator | Test the specified diagnostic on an independent workload and another quota before broader claims. |

Future deadline validation must seal predictions before fresh offers and retain
the all-offer 500 ms outcome, finite-queue model and 3-percentage-point error
screen. Its counts, baseline-advantage rule and failure handling require a
separate frozen protocol. Sampler-on deadlines cannot substitute for off-arm
validation while V25 comparability remains unresolved. No calibration,
validation, larger-workload matrix, new quota or automatic follow-up is launched
by this plan.

Reproduce the completed offline lead review in a fresh output directory:

```bash
python3 analysis/review_v25_contribution_leads.py --output /tmp/v25-contribution-leads-review
```
