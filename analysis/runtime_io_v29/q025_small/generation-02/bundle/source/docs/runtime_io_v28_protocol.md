# V28: independent calibration and prospective estimator comparison

8 October 2026. Separate generation; the V27 composition decision and all
historical thresholds remain unchanged. No scientific measurement is run in the
desktop chat. This protocol tests a predictive contribution gate on the existing
small SHA service, not novelty, a runtime mechanism or application generality.

Use the retained stock server and clock-repaired client binaries: 44,000 SHA
iterations, one worker, GOMAXPROCS=1, yield off, 128 waiting positions, quota
50,000/100,000 us, zero CPU burst, service CPUs2/4 and control CPUs0/1. All
calibration and validation use the native sampler **off**. Endpoint cgroup CPU
and throttling counters, request events, client clocks, host/server anchors and
the ordinary approximately1Hz host/ownership controls remain enabled. The idle
measurement therefore estimates a live service with this control polling, not
an entirely unobserved background process or machine idle time.

## Fixed collection budget and separation

There are32 scientific slots:16 calibration, then16 validation. Two calibration
blocks each contain live idle, steady15/30/60/90/120 jobs/s and two mixed trials.
The eight conditions have a seeded initial order and reverse order in block2.
Each trial has20s warmup at its low rate (idle receives no jobs), full drain,
metrics reset, measurement and full drain. Idle/steady measurement lasts30s.
Mixed measurement lasts60s with four15s cycles:10s at15 or30 and5s at169.8.
Whole cost includes measurement startup/terminal control overhead and full drain,
as in the retained substitution. Warmup cost is excluded.

After the16 calibration inputs, replay and seal the calibration review, fitted
parameters, every validation summary and every per-offer forecast. Refuse to
create or recreate forecasts after any validation attempt. Validate the seal and
its raw calibration references before each validation slot. No historical CPU
measurements, validation outcomes, hand-tuned parameter or favorable rerun enters
the fit. The historical result is a provenance prerequisite only.

Validation crosses low15/30 with period6/12s, four balanced Williams blocks.
Every trial is60s: low phase occupies2/3 of each cycle, high is180 jobs/s.
Thus the high cohort contains3600 offers in all trials, with600 or1200 low offers.
The schedules change both the calibration burst timescale and high arrival rate.
Source/design seals retain exact nanosecond vectors and their compiled binary
exports. Seed2808102026 is declared before collection. No performance pilot
selects these schedules.

## Calibration qualification and estimator contracts

Record every technical and scientific failure separately. Calibration requires
all offers and warmup offers successful, each declared state eligible, and the
four mixed busy-capacity point estimates' max/min range at most5%.

Live idle receives zero work throughout warmup and measurement; health and final
metrics must show no admitted/completed/rejected work, active handlers or queue.
Use dedicated idle receipts and six host/server clock anchors; never fabricate a
zero-rate client report or divide idle CPU by zero jobs.

For steady data, completions in fixed [3,10), [10,17), [17,24) windows must bracket
the offered rate within±5%. Entire-run queue peak must be≤1 at15/30 and≤5 at
60/90/120. Low15/30 additionally require zero throttled periods in the full
accounting interval. Higher rates may throttle: retain and report that count;
reject a growing/large queue or failed steady throughput qualification. Busy
capacity counts completions in [11.5,14.5)+15k, k=0..3, with positive waiting
queue throughout every clock-expanded window. Clock uncertainty bounds count
endpoints conservatively. An unqualified state is a scientific result and gets
no technical retry; stop before validation and retain a calibration-failed report.

All estimators receive the shared16-trial dataset and declared appropriate fit
inputs. The regression range extends to120 jobs/s; report remaining extrapolation
and residuals rather than claiming saturation was measured by regression.

| Method | Frozen capacity input |
|---|---|
| whole | q / mean(CPU seconds / completed jobs), over four mixed trials |
| idle_corrected | (q-b) / mean((CPU seconds-b*T)/completed jobs), same mixed trials; b=mean CPU/wall rate of two idle trials |
| busy | mean completion throughput in fixed backlogged windows, four mixed trials |
| regression | Fit U=b+dX by equal-run least squares to the12 idle/steady points, constrain b≥0,d>0; capacity (q-b)/d |
| quadratic | Fit U=b+dX+eX² to the same12 points, b≥0,d>0, monotonic to its admissible positive capacity root U=q |

q=0.5. T uses outer measurement counter brackets; CPU is measured consumed CPU
time, not elapsed idle time. Both regression candidates with free/zero intercept
are assessed by calibration residuals; quadratic also includes the linear
boundary. This is a declared finite candidate fit, not a general optimizer of
all inequality-constrained polynomials. Scale X numerically. Require positive
demand, b<q, positive derivative over measured range and through the capacity
root, and capacity≤2*maximum calibration throughput. Preserve nonphysical or
unavailable fits as model mismatch; do not clip to historical/busy capacity.
Idle subtraction assumes an additive comparable background and is tested as a
baseline, not asserted as causal accounting.

Every available estimate feeds the identical retained deterministic constant-rate
FIFO simulation (one active plus128 waiting) at the exact scheduled offsets.
Report all-offer500ms misses, rejections and queue peaks. Failed offers count as
misses. Unequal-phase recovery diagnostics from the retained simulator are
omitted because their old half-cycle assumption does not apply. This comparison
isolates capacity inputs; it does not claim a new queueing model or stochastic
deadline distribution.

## Fresh validation and stopping decisions

Observed busy windows are [4.8,5.8)+6k, k=0..9, for period6, and
[10,11.8)+12k, k=0..4, for period12. Require positive waiting queue throughout
clock-expanded windows. Retain failed states and unsuccessful offers as outcomes.
Capacity accuracy uses the worst relative error against observed throughput
lower/upper accounting bounds. Deadline accuracy uses the sealed point-capacity
forecast against the all-offer miss fraction; this is not a confidence interval
over uncertain forecast parameters.

Declared accuracy: every validation slot has capacity error≤5% and500ms miss
error≤3 percentage points. Declared advantage: compute comparator absolute
deadline error minus busy absolute error, average four conditions within each
of four blocks. All four block improvements must be positive and the95% t
interval's lower endpoint must be≥1pp (df3, critical3.182446305284263).
The units are blocks, not individual jobs. Intervals assume independent,
approximately normal block contrasts; sequential host blocks and n=4 limit
inference. Record raw errors, mean errors and all intervals even on failure.

Decisions in order: incomplete collection; calibration qualification failure;
validation state/cohort failure; busy accuracy failure; unavailable established
comparator; either established comparator meets the accuracy screen; busy has
the declared advantage over both regression and quadratic; otherwise advantage
inconclusive. Comparator adequacy stops the superiority route even if busy has
a small numerical advantage. Do not reinterpret an unavailable comparator as
busy superiority. Other method comparisons remain descriptive/secondary.

Stop after this report. No rerun to pass a screen, automatic transfer experiment
or novelty declaration. If established methods suffice, consolidate the scoped
empirical paper. Only a distinct useful result justifies a separately frozen
workload/quota transfer gate.

## Closest-method assessment

Utilization–throughput resource-demand regression and background-load concerns
are established: [Spinner et al.,2015](https://doi.org/10.1016/j.peva.2015.07.005).
Load-dependent demand estimation is also established:
[Zhang et al.,2013](https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639)
uses utilization-dependent polynomial demand with queueing/response constraints.
Our quadratic U(X) benchmark is **not** a reproduction of that algorithm; its
response/queueing assumptions need separate applicability assessment for this
periodically throttled transient service. Consequently beating these declared
baselines is evidence for further work, not superiority over all prior methods.
Before a stronger novelty claim, reproduce an applicable closest load-dependent
method or document a technically justified inapplicability and compare a credible
alternative. Simple idle correction or composition sensitivity alone is not new.

## Operational bounds

Runtime preparation600s; collection7200s including initial600s minimum settling
and60s minimum per scientific slot (thermal bound1200s each remains inside the
global bound); active container360s; drain100s; monitor readiness5s and completion
30s; cleanup120s; separately bounded analysis600s after disarming measurement
watchdog. Host monitor minimum45 records for30s measurement and80 for60s, with
first sample before release and last after full drain, progress/record agreement
and quiet/power checks. Functional cases use separate preparation limits and no
scientific host-monitor screen. No native20ms counter process starts.

One total technical retry across32 slots; second technical failure stops. Any
cleanup/watchdog intervention or monitor cleanup failure stops immediately.
Attempted generations cannot resume or overwrite data. Repeated scientific
failures cannot consume retry allowance. Keep collection stopped until the user
launches the prepared command outside the desktop app. Rough operational
expectation90–110min plus preparation; the two-hour collection bound is a limit,
not an ETA or permission to extend collection.
