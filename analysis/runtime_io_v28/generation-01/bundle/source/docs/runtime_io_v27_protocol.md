# V27: controlled load-composition screen

7 October 2026. Freeze this protocol, offer vectors, source snapshots and binary
receipts before runtime preparation. V26 independently established both steady
low rates; its report and all earlier evidence remain unchanged.

The question is whether increasing low-load jobs changes whole-run CPU/job
while busy capacity stays within a practical margin, with high-load work fixed.
This is a bounded composition screen for one service. It does not identify the
runtime mechanism, establish a new estimator, or resolve deadline comparability.

## Treatments and fixed windows

Use four consecutive blocks, each with all four cells: 15 or 30 low jobs/s,
native sampler off or on. Sixteen trials have separate service lifecycles.
The frozen seeded Williams order balances every cell across the four positions
and both rate orders within each sampler condition. Exact order is in the
sealed design, with seed 2707102026; no adaptive ordering or replacement.

Retain the service image/server, gate, native collector, 44,000-iteration work,
one worker, GOMAXPROCS=1, yield off, queue 128, quota 50 ms per 100 ms, zero
burst credit, service CPUs 2/4 and controller/client CPUs 0/1. Retain resource,
power, thermal settling, ownership and observer-inventory controls.

The separate V27 client adds an explicit low-phase duration and an offline
schedule export. It copies the diagnostic client's request, HTTP tracing,
concurrency, timeout and outcome accounting logic. The source diff, compiler,
unit/race/vet output, binary hash and exact-schedule export comparisons are
retained. The historical client binary is unchanged. Both treatments and
sampler arms use the same new client binary. A successful build is not runtime
qualification; external functional cases check actual offers and outcomes.

Warm up at the assigned steady low rate for 20 seconds, drain and reset.
Measurement is four identical 15-second cycles: 10 seconds low at 15 or 30
jobs/s, then 5 seconds high at 169.8 jobs/s. Offer for 60 seconds and fully drain.
Each high phase has 849 offers, with identical high timestamps across conditions.
The 15-rate cohort has 600 low + 3,396 high = 3,996 offers; the 30-rate cohort
has 1,200 low + 3,396 high = 4,596. Warmup has 300 or 600 offers.

For cycle k=0..3, fixed low windows are [3,8]+15k and busy windows are
[11.5,14.5]+15k. No post-hoc window search. Expand queue windows by clock
uncertainty. Every on trial requires low queue maximum <=1, positive guaranteed
completions and upper bounded nr_throttled increments zero. Missing throttle
counters cannot qualify. Every trial, including off trials, requires guaranteed
positive waiting queue throughout all busy windows. On busy delivered-CPU
bounds must lie within [0.48,0.52]. Low windows must requalify in this mixed
schedule; V26 steady qualification is only a prerequisite.

Whole-run CPU/job is the retained aggregate container usage delta from the
measurement-start observation through full drain, divided by completed worker
jobs. This includes edge/runtime/service work under that operational definition.
Busy capacity uses completions in fixed busy windows, with clock bounds.
Phase CPU/completion uses monotonic native counters without interpolation.
These are aggregate metrics, not individual-job CPU demand or SHA attribution.

## Recording quality, unsuccessful outcomes and repetition

Replay exact offers and all outcomes, warmup/drain/reset, raw native decoding,
clock anchors, resource/thread identities, cleanup and source/binary identities.
Require no client drops or missed arrivals and p99 dispatch lag <=2 ms.
Retain <=50 ms measurement counter gaps, <=60 ms boundary enclosure,
<=4% phase CPU/completion bound width, and <=0.02 absolute busy-delivery bound
width. Native capture remains 20 ms cadence, 110-second bound and existing
storage limits, starting before warmup and covering full measurement drain.
At least 80 one-second host-monitor records are required for the 20+60 seconds
of traffic and associated lifecycle. Off trials contain no native records.

Admission rejections, HTTP/timeouts or unsuccessful offers in either warmup
or measurement are valid recorded outcomes; they make the scientific cohort
ineligible and must not be replaced as technical failures. State ineligibility,
large treatment differences and deadline misses likewise do not trigger retry.
Continue all slots and report those failures. Functional success cases require
successful offers; cancellation cases must exercise retained cancellation logic.

One total technical retry is allowed in the same slot with identical inputs.
Preserve both attempts. A second technical failure stops the generation as
incomplete. Cleanup/watchdog failures stop without retry. No automatic resume
once measurement is attempted. Never rerun until favorable.

## Frozen block analysis and practical screens

The unit of repetition is the independent trial/block, never jobs or cycles.
For each of the four blocks and each sampler condition, define the signed
percentage treatment contrast 100*(metric_low30/metric_low15 - 1). This is
computed separately for whole-run CPU/job and busy capacity. Positive cost
contrast is the preregistered direction; an opposite effect is reported, not
relabelled. Retain deterministic busy-capacity contrast bounds from completion
and clock bounds. Whole-cost values use the defined observation endpoints.

Report all four contrasts, sample SD, means and model-based 95% paired-t
intervals, with t(0.975,3)=3.182446305284263. For accounting-bounded inputs,
use mean endpoint bounds and the maximum sample SD over all sixteen vertices
of their four-dimensional interval box. Expand each mean endpoint by
`t*maximum_SD/sqrt(4)`. This encloses every paired-t interval consistent with
the bounds, rather than treating midpoint estimates as exact.

These intervals assume independent, approximately normal block contrasts.
Four blocks cannot check that assumption well or certify universal equivalence.
The run is a fixed diagnostic budget, not a powered general confirmation.
For point contrasts, half-width is 1.5912 times the observed block SD. To clear
a 3% cost threshold when the estimated increase is 4%, block SD would need to
be below about 0.63 percentage points. With zero estimated busy difference,
SD must be below about 1.26 points for an interval inside +/-2%, before extra
accounting uncertainty. These are resolution calculations, not expected power
or noise guarantees. V26 costs and historical busy costs motivate the direction
but are not plugged into the final treatment estimates.

A supportive screen requires all of the following:

- Complete, technically valid collection; all warmup/measurement cohorts successful.
- Every required mixed-state and nominal busy-delivery check passes.
- In each sampler arm, all four cost contrasts are positive and the 95% interval
  lower endpoint is >=3%.
- In each sampler arm, every bounded busy contrast and the 95% interval lie
  entirely within [-2%,+2%]. A small mean or nonsignificant difference is insufficient.
- For each metric, the block interaction `contrast_on - contrast_off` has its
  model-based 95% interval entirely within [-2,+2] percentage points.

Interactions check the treatment contrast's observer dependence. Off/on level
contrasts at each rate are also reported, but passing interactions does not
establish sampler neutrality for cost, throughput or deadline outcomes.
Deadline misses remain descriptive and cannot qualify the sampler.

Decision precedence: `composition_incomplete`, `cohort_outcomes_ineligible`,
`mixed_state_qualification_failed`, `composition_screen_supported`,
`busy_capacity_changed_materially` (a busy interval entirely outside +/-2%),
`composition_effect_below_target` (a cost interval upper endpoint below 3%),
`observer_interaction_unresolved`, otherwise `composition_inconclusive`.
All data and failed screens remain visible regardless of the top-level decision.
Independent replay must reproduce the complete report and inputs exactly.

## Runtime, bounds and stopping

Offline preparation independently verifies the V26 prerequisite, source/binary
receipts, design, schedule exports, adverse analysis fixtures and lifecycle rules.
External normal-user preparation checks actual resource/image identity behind
an unreleased gate, then runs a full 15-second unequal-cycle success case at
each low rate and a separate 2-second cancellation case at each configuration.
Use a fresh read-only root observer inventory after preparation.

Fully quit Codex/ChatGPT, connect external power and keep the host idle.
No code changes power profiles or host settings. Runtime preparation <=600 s;
collection <=5,400 s including initial 600 s idle and per-trial settling;
active trial <=360 s; cleanup grace <=120 s; separate analysis <=600 s.
Disarm the collection watchdog before post-collection replay.

Stop after reporting and independent replay, whatever the result. A supportive
screen justifies separately preparing independent regression calibration and
fresh sampler-off forecasts. This launcher does not collect those stages or
start another generation. Scientific mechanism, generality and novelty remain
unestablished even if every screen passes.
