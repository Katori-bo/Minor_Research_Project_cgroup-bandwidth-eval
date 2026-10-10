# V26: four-trial steady low-load qualification

7 October 2026. Freeze this design, exact offer vectors and source/binary receipts
before runtime preparation or collection. This implements the
[low-load pilot proposal](runtime_io_low_load_qualification_plan.md).
Earlier studies retain their original windows, rules and outcomes.

The sole question is whether two lower steady arrival rates establish a bounded
shallow-queue, unthrottled window. V26 does not test busy capacity, deadline
equivalence, a causal mechanism, estimator superiority or publication novelty.

## Fixed trials and state window

| Order | Trial | Steady jobs/s | Repeat |
|---:|---|---:|---:|
| 1 | low15_r1 | 15 | 1 |
| 2 | low30_r1 | 30 | 1 |
| 3 | low30_r2 | 30 | 2 |
| 4 | low15_r2 | 15 | 2 |

All four have the native sampler on. Retain the exact V25 application, client,
gate and native collector binaries. Use 44,000-iteration jobs, one worker,
`GOMAXPROCS=1`, yield off, queue 128, quota 50 ms per 100 ms, no burst credit,
service CPUs 2/4 and client/controller CPUs 0/1. Preserve the resource defaults,
power settings and existing host/ownership checks.

Each trial has its own service lifecycle. Warm up for 20 seconds at the assigned
steady rate, fully drain, reset service metrics, offer for 30 seconds, then fully
drain again. No high-load segment precedes the measurement. The retained
steady scheduler rounds `index / rate × 1e9` to the nearest nanosecond and
excludes timestamps at or beyond the duration. Frozen measurement vectors
contain 450/900 offers at 15/30 jobs/s; warmup vectors contain 300/600.

The sole state window is `[5,25]` seconds after the first scheduled measurement
offer, expanded by clock uncertainty for queue and counter-bound calculations.
Require guaranteed positive completion count, waiting-queue maximum <=1 and
the upper bound on `nr_throttled` increments equal to zero. A missing throttle
counter makes state eligibility false; it is not assumed zero. Both recordings
at each rate must qualify. Do not shift windows or adjust thresholds afterward.

## Recording quality and adverse outcomes

Record and replay exact offer/outcome conservation, native raw reads/decoding,
CPU/resource observations, thread identities, clock anchors, warmup/drain/reset,
source/binary identities and owned cleanup. Require no dropped or missed offers,
no admission rejections or other unsuccessful offers in warmup/measurement,
and the retained <=2 ms client p99 dispatch-lag screen.

The native collector retains 20 ms cadence, a 110-second capture bound and its
existing storage limits. It starts before warmup and must cover full measurement
drain; early exit or capture overrun is a technical failure. Check monotonic
reads, <=50 ms measurement gaps, <=60 ms endpoint enclosures and <=4% relative
CPU/completion bound width. Report busy-delivery checks as inapplicable because
there is no busy phase. Raw replay requires at least 45 one-second host-monitor
records during the 20-second warmup plus 30-second measurement and associated
lifecycle; the old 80-record requirement belonged to the longer V25 trial.

CPU/completion is aggregate container accounting, not isolated SHA demand.
Counter/clock intervals are accounting bounds, not statistical confidence
intervals. Deadline misses remain descriptive and cannot qualify the sampler.

An otherwise valid record with an ineligible state counts as a completed pilot
trial. Continue through all four slots, then report `low_state_qualification_failed`.
Never replace a valid failed-state recording. A technical failure permits one
total retry of that same slot. Preserve both attempts; a second technical
failure stops collection as incomplete. Cleanup/watchdog failures stop without
retry. No generation may resume once measurement was attempted.

## Preparation, report and bounds

Offline preparation snapshots new V26 sources and all unchanged inherited
sources, exact schedules, retained binaries and native build/software receipts.
Run state-success, state-failure, clock/gap/uncertainty, raw conservation,
report-tamper and lifecycle/retry fixtures. These are software checks only.

External runtime preparation separately checks the actual image/resource
contract without releasing the preflight gate, then runs four short functional
cases: steady success at each rate and cancellation at each configuration.
All owned preparation resources must be removed. Do not infer scientific
qualification from functional cases.

Use the retained external normal-user launcher and fresh read-only root observer
inventory. Fully quit the desktop app, keep external power connected and leave
the host idle. No code changes power profile, CPU settings or other host policy.
Preparation <=600 seconds, collection <=2700 seconds including initial
600-second idle and per-trial settling, active trial <=360 seconds, cleanup
grace <=120 seconds and post-collection analysis <=600 seconds. Disarm the
collection watchdog before independent analysis.

The report lists every valid trial, state/quality outcomes, completion and CPU
bounds, queue maxima, throttling bounds, acquisition diagnostics, descriptive
misses, source/trial seals, cleanup receipts and technical failures. Incomplete
sessions can be analyzed from retained records; they cannot qualify either
rate pair. Independent replay must reproduce the saved report exactly.

The only decisions are `both_low_rates_qualified`,
`low_state_qualification_failed` and `pilot_incomplete`. Stop after reporting
and independent replay regardless of result. No mixture study, regression
calibration or deadline validation is automatically launched.
