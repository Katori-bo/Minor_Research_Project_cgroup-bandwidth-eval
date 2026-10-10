# V25: bounded repeated-control diagnostic

Freeze this protocol, schedules and source receipts before fresh runtime
preparation or collection. This study answers a design question, not the V24
scientific hypothesis. Earlier generations keep their original failed outcomes.
Prior V24 results motivated this design; none is a new V25 replicate.

## Question and scope

How large are differences between repeated, identical trials compared with
sampler off/on differences? Do the fixed windows establish the workload states
needed to interpret phase CPU/completion?

Reuse the exact V24 revision-3 native collector binary, C source, raw decoder,
build receipt and completed 110-second software receipt. No new collector,
tracing, realtime scheduling, application instrumentation or host settings.
Retain the image/server/client/gate, 44k/88k jobs, scaled arrival schedules,
50000/100000 CPU quota, one worker, yield off, 128-job queue, affinities,
20-second warmup/reset/drain, 60-second measurement and 10-second burst cycle.
Keep the same clock joining and six fixed busy/low windows.

## Sixteen diagnostic trials

Each group has two consecutive trials of the same size and sampler condition.
O means sampler off and N means sampler on. The frozen order is:

| Block | First group | Second group |
|---|---|---|
| 1 | small O, O | large N, N |
| 2 | large O, O | small N, N |
| 3 | small N, N | large O, O |
| 4 | large N, N | small O, O |

Each size has four off and four on trials. Each condition has two consecutive
repeat pairs. Compare group means across blocks 1/2 and 3/4: each size has one
off-then-on contrast and one on-then-off contrast. Each size/condition appears
once as the first group and once as the second group of a block. This balances
simple order effects; it does not control every thermal, frequency or quota
phase difference. Initial/per-trial settling and existing host monitoring stay
in place. No outcome-dependent reordering, extra repetition or rerun-until-pass.

Repetition and interleaving are established benchmark practices. The Go
benchstat documentation recommends larger samples for statistical comparisons;
this intentionally small four-per-condition screen provides descriptive
diagnostics, not an equivalence test or confidence interval.
[benchstat documentation](https://pkg.go.dev/golang.org/x/perf/cmd/benchstat).
[Google Benchmark repetition/interleaving guidance](https://github.com/google/benchmark/blob/main/docs/user_guide.md).

## Recording quality is independent of outcomes

Continue verifying raw counters, monotonic clocks, source/binary ownership,
dispatch, environment, full cohort conservation and cleanup. Keep the existing
20 ms cadence, 50 ms measurement-gap rule, 60 ms boundary enclosure rule,
4% maximum relative CPU/completion bound width and 0.02 CPU maximum busy
delivery bound width. All readings remain recorded; slow reads are diagnostic.
These are bounds on observed counters and alignment, not statistical intervals
or guarantees of zero kernel accounting lag.

Missing/corrupt records or failure to bound a measurement is a technical failure.
There is one total technical retry of the same slot. A valid record with a
different miss rate or an ineligible workload phase is retained as a diagnostic
trial; it does not consume a retry or stop the collection. The recorder is not
redesigned merely because a control comparison varies.

## Workload states are reported separately

For the single-worker busy phase, require a strictly positive waiting queue
throughout every clock-expanded fixed window. A waiting job is direct backlog
evidence. Do not import the earlier recovery diagnostic's greater-than-five
margin into this definition. Still report the old margin for transparency.

For the lightly loaded phase, require queue maximum at most one in every
expanded window, and an upper bound of zero on throttled periods over those
windows. This operational definition allows one briefly waiting arrival while
excluding deeper backlog and observed quota exhaustion. It does not prove an
idle CPU at every instant or identify isolated per-job SHA CPU demand.
Missing throttling counters make the low-state check unavailable/false; they
are not assumed zero. Neither state condition changes recording validity.

These new state definitions apply only to V25 diagnostics. They do not accept
generation-03 retrospectively or establish the original V24 scientific claim.
Report CPU/completion as aggregate container accounting, including runtime,
HTTP and kernel work, and retain in-flight completion-boundary limitations.

## Fixed report and stopping rule

Use trials, not individual requests, as repetitions. At each size report:

- Four off and four on values: mean, sample standard deviation and range for
  busy completions/s, whole-container CPU/completion and 500 ms deadline misses.
- Four consecutive same-condition pair differences and two order-balanced
  off/on group-mean differences, retaining their signs and trial references.
- The overall mean off/on difference. Compare it descriptively with the
  earlier reference margins (2% capacity, 2% cost, 1 percentage point misses).
- For each metric, whether both order contrasts have the same sign and exceed
  the largest observed same-condition repeat difference. This is a heuristic
  comparison with observed repeats, not a significance test or noise bound.
- Each on trial's recording quality, native timing/cost and busy/low state
  eligibility. Retain all valid trial values even when a state is ineligible.

After all sixteen valid recordings and independent replay, the decision is
`control_design_screen_complete`, irrespective of comparison/state outcomes.
Always report equivalence and scientific confirmation as not established.
An incomplete collection is explicitly incomplete. Stop after the report.
No automatic confirmatory collection, revised thresholds or extra trials.
Review whether observer differences dominate observed repeat variation and
whether the intended states are reproducible before choosing another study.

## Execution and preservation

Use a fresh dedicated V25 generation. Preparation remains bounded to 10 minutes,
including real image/resource checks and four functional cases. Collection has
a 90-minute bound including the retained initial 10-minute idle and per-trial
settling, 120-second cleanup grace and separate 10-minute analysis bound.
The active-trial watchdog remains 360 seconds. Disarm the collection watchdog
before replay. Never resume an attempted collection. Preserve every attempt.

The external normal-user terminal must have the desktop app fully quit. A fresh
read-only observer inventory uses local sudo authentication. Keep the laptop
plugged in and idle. Offline preparation invokes no Docker, sudo or live
workload. The old full V24 study remains blocked; V25 does not call its launcher.
