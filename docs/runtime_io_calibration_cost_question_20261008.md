# Calibration-cost novelty screen: question and comparison contract

8 October 2026. The user authorized beginning this screen before completing
the empirical manuscript. Paper completion is not a scientific dependency.
This document fixes the scope of a literature and offline adequacy assessment;
it is not a fresh experimental protocol or a novelty claim. Collection remains
stopped. Quota-period selection remains on hold and the FIFO theorem lead
remains closed.

## One candidate capability

> For a declared arrival schedule in the existing fixed-quota, single-worker
> service, can we forecast the all-offer 500 ms deadline-miss fraction to useful
> accuracy at materially lower calibration cost than the cheapest adequate
> established alternative?

Begin with the service and CPU contract already recorded: small SHA jobs,
one worker, GOMAXPROCS=1, yield off, 128 waiting places, 50 ms quota per
100 ms, zero burst credit. Choose neither quota nor period. Retain the existing
FIFO forecast as a common baseline so that a capacity-input comparison does
not quietly become a new scheduling or simulation project.

The candidate method may choose calibration loads, repeat measurements or stop
collecting calibration when its declared criterion is satisfied. Its first
output is a miss-fraction forecast for each supplied schedule, accompanied by
the measurements used, assumptions, qualification status and incurred cost.
Its next measurement decision, if any, must use only information then available.
No algorithm or stopping criterion is asserted to be new at this stage.

An accuracy reference of 3 percentage points per case is inherited as a useful
screening yardstick from V28; it is not a new guarantee. Compare errors on
nonzero-miss cases as well as the whole declared set. A method that refuses
to forecast must report that refusal, with decision coverage alongside accuracy.
Counting only favorable answered cases would not establish adequacy. A future
study needs its own frozen evaluation and meaningful cost advantage criterion.

A caller-supplied allowable miss fraction could later turn forecasts into
accept/reject/insufficient-evidence decisions. That is not the initial novelty
claim. Such decisions require validated uncertainty and model-error treatment;
parameter confidence alone does not establish future deadline compliance.

## Available and unavailable information

Before any hypothetical fresh validation, permit the declared arrival vector,
resource configuration, queue policy and completed calibration observations.
These may include aggregate consumed CPU, wall duration, completion counts,
queue eligibility, throttling counters and request timings. CPU seconds and
wall seconds retain their recorded meanings. A bandwidth ceiling is not a
guaranteed CPU supply rate.

Do not give a selector later validation outcomes, the final full-budget capacity,
an oracle's best calibration subset or free measurements that another method
would need to acquire. Prior workload/host traces are possible inputs only
with their acquisition cost and transfer assumptions explicitly declared.

Existing V28 records support retrospective subset and availability checks.
V28 outcomes are already known; a newly selected rule cannot inherit that
study's prospective status. Blocked calibration splits may diagnose sensitivity,
but do not manufacture untouched scientific confirmation.

Whole-run CPU totals support changing which complete trials enter a fit; they
do not automatically support arbitrary shorter CPU measurement windows. Any
window-based analysis must first demonstrate the corresponding saved counter
and clock coverage. Overlapping windows are not independent repetitions.

## Cost, measured in appropriate units

Report the cost vector rather than collapsing unlike expenses into run count:

- End-to-end calibration wall time, including setup, warmup, drains, state
  qualification and any failed attempts needed to obtain the answer.
- Measurement duration, requests generated and CPU consumed.
- Deliberately induced backlog, late/failed calibration offers and measurement
  interference where recorded. Backlogged throughput is not free observation.
- Estimator computation and tuning time; external trace training, if used.

V28's direct estimates use four mixed trials, each with 20 s warmup and 60 s
measurement: 320 nominal scheduled seconds. Regression uses twelve idle/steady
trials with 20 s warmup and 30 s measurement: 600 nominal scheduled seconds.
Those totals omit drains and other overhead and are not measured total costs.
All methods originally had access to one shared sixteen-trial dataset; V28
did not run independent minimum-cost collection procedures. The nominal ratio
600/320 = 1.875 therefore proves neither a twofold saving nor optimality.
See the unchanged [V28 protocol](runtime_io_v28_protocol.md).

## Adequate alternatives to examine first

| Alternative | Necessary assessment |
|---|---|
| One qualified backlogged trial, then ordinary repeats if needed | Determine whether existing direct-throughput calibration already supplies the desired accuracy cheaply. |
| Reduced quadratic utilization–throughput fit | Allow fewer rates/repeats, sensible load placement and calibration-only admissibility checks; twelve observations are not a theoretical requirement. |
| Cost-aware experimental design for the same fit | Assess whether established information-based design supplies the measurement choice without a new method. |
| Applicable published demand estimation | Check response/utilization units and scheduling assumptions; compare a faithful method or clearly justified adaptation. |
| Standard adaptive estimator/window selection | Check whether existing tuning and selection already supply any proposed stopping or diagnostic rule. |
| Full V28 fits and whole/idle/linear inputs | Retain as historical references; beating weak inputs is insufficient if a cheap adequate alternative exists. |

In noiseless algebra, a quadratic with unknown intercept has three coefficients
and can be identified from three distinct throughput values with full-rank
design. A known zero intercept reduces this to two coefficients. This is an
identifiability observation, not evidence of adequate extrapolation, repeatability
or deadline accuracy. The intercept cannot be fixed to zero solely because
the favorable full-data V28 fit chose it.

## Necessary next result and stopping rule

The [first literature comparison](runtime_io_calibration_cost_novelty_screen_20261008.md)
tests whether the claimed capability is already supplied. Before a custom
prototype, identify a specific nonroutine capability beyond ordinary direct
measurement, reduced regression and cost-aware experimental design.

Stop the generic novelty claim if it is merely fewer samples, adaptive windows,
automatic estimator selection, or a new endpoint for otherwise standard steps.
Stop investment in a custom selector if the cheapest adequate simple alternative
already meets the decision need. Method inapplicability or absence of an exact
title match is not evidence of a gap.

Continue only with a claim-versus-method difference, a feasible measurement
contract and a fair way to test it. A tiny offline prototype is conditional on
that surviving difference; fresh validation comes after offline feasibility,
with separately frozen rules and a bounded measurement budget. No collection
or scientific fitting is authorized or launched by this document.

The [version-5 empirical manuscript](runtime_io_short_working_draft_v5.md)
remains an independent completed-evidence record. Final writing can resume
after the screen; neither a positive nor a negative screen rewrites its results.
