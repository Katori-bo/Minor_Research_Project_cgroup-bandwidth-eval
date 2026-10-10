# Four-trial low-load qualification proposal

7 October 2026. Next bounded pilot for the
[contribution plan](runtime_io_contribution_and_experiment_plan.md).
This is an offline specification, not a sealed executable generation.

Implementation update: this proposal is now implemented in the separately
[frozen V26 protocol](runtime_io_v26_protocol.md), with a
[verified offline bundle](runtime_io_v26_preparation_verification.md) and
[external launch guide](runtime_io_v26_execution.md). Actual runtime checks and
all four pilot recordings remain unrun. The text below preserves the proposal.

The purpose is to establish two usable low-load conditions. It does not test
deadline equivalence, CPU-cost causality, a new predictor or broad generality.

## Fixed treatment and records

Retain the existing service/server/client/gate and native collector binaries;
44,000 SHA iterations, one worker, `GOMAXPROCS=1`, yield off, queue 128,
quota/period 50,000/100,000 microseconds, zero burst credits, service CPUs 2/4
and controller CPUs 0/1. Keep existing power, settling, clock and identity
checks. Do not rebuild application or collector binaries or change host policy.

Four sampler-on trials have the fixed order `15, 30, 30, 15` jobs/s. Each uses
its own service lifecycle, a 20-second steady warmup at its assigned rate,
full drain, reset, and a 30-second steady measurement followed by full drain.
Use the exact retained steady scheduler, and store the complete generated offer
vectors before running; do not infer offered counts from rounded rates.

The qualification window is fixed at seconds `[5,25]` after the first scheduled
measurement offer. It excludes initial startup and final drain. No preceding
high-load segment is permitted. Retain raw counter read brackets, server/client
events, host/server anchors, environment/identity receipts and owned cleanup.
The native capture includes warmup through final drain and retains its
110-second limit. Warmup and measurement together take 50 seconds; a capture
overrun is a technical failure, not permission to extend the limit live.

## Separate recording quality from state qualification

Recording quality requires raw replay, cohort conservation, complete clock
joins, valid monotonic counters and the retained 20 ms cadence, 50 ms gap,
60 ms endpoint enclosure and <=4% relative CPU/completion bound width.
The busy-delivery width rule has no busy phase to evaluate here; report that
as inapplicable, not passed. There must be no dropped client offers or admission
rejections. Deadline values are descriptive only.

For state qualification, throughout the clock-expanded fixed window require
waiting-queue maximum <=1 and the upper bound on `nr_throttled` increments
equal to zero. Require positive guaranteed completion count. Both trials at
each rate must meet these conditions. Counter uncertainty is not a statistical
confidence interval. Passing demonstrates only these recorded windows, not
guaranteed low-load behavior in future mixed schedules.

A valid record that fails a state condition stays valid and counts as an
unqualified trial. Finish the four planned slots to report the full outcome;
do not replace it. Missing/corrupt/unbounded records are technical failures.
Allow at most one total technical retry of the same slot with every attempt
retained; a second technical failure stops the pilot as incomplete.

## Preparation, execution and stop

Before collection, create a new dedicated generation with exact schedules,
source/binary hashes and design rules sealed. Build the report and independent
replay path offline; exercise successful-state, failed-state and technical-failure
fixtures. Functional checks belong to preparation and are not pilot evidence.
Existing historical studies must still replay without changed rules or sources.

Use the retained external quiet-machine launcher pattern: fully quit the
desktop app, obtain the existing fresh observer inventory, and keep the laptop
plugged in and idle. The pilot needs a new launcher; do not invoke V25 or the
blocked V24 scientific launcher as a substitute.

Set preparation <=10 minutes, collection <=45 minutes including initial
10-minute idle and per-trial settling, an active-trial watchdog <=360 seconds,
cleanup grace <=120 seconds, and independent analysis <=10 minutes after the
collection watchdog is disarmed. Preserve any attempted session; do not resume
an attempted collection or automatically extend a bound.

The report must list all four trials, recording quality, queue maxima,
throttling bounds, completion/CPU bounds, owned cleanup and technical retries.
Declare `both_low_rates_qualified`, `low_state_qualification_failed` or
`pilot_incomplete` separately from measurement validity. Stop after independent
replay regardless of outcome. This pilot schedules no mixture experiment.
