# V22: frozen question and prospective decision rules

Design revision 1, 2026-10-07. Step 3 of the research synthesis, following the
[evidence map](runtime_io_evidence_map.md) and
[contribution matrix](runtime_io_contribution_matrix.md). This document fixes the
scientific design before implementation. It is not an implemented launcher, a
completed preparation seal or collected performance evidence.

The [machine-readable design](../analysis/runtime_io_v22_design/20261007/design.json),
exact arrival vectors and [design review](../analysis/runtime_io_v22_design/20261007/review.json)
accompany this revision. The [design seal](../analysis/runtime_io_v22_design/20261007/seal.json)
records their hashes. Later executable preparation must include this design and
freeze the runner, analysis, environment and assets before collection. Any
necessary design amendment gets a new retained revision before performance
collection; validation results cannot change these rules.

## One question

> Under the retained half-CPU contract in this stock-Go service, can busy capacity
> measured from two independent burst calibration trials predict all-offer
> 500 ms deadline-failure rates for fresh bursty and evenly spaced arrivals,
> and their paired difference, within 3 percentage points in every block?

In plain language: measure how fast the kitchen actually works, write down the
expected number of late orders, then test those predictions with fresh orders
arriving in two different patterns. The predictions must be written first.

The hypothesis is that an independently calibrated, constant-capacity finite
FIFO account transfers adequately for this specified aggregate objective.
It is falsified at the chosen practical margin if a technically valid validation
trial or paired contrast exceeds the primary tolerance. Invalid inputs,
inadequate calibration or incomplete collection make the test inconclusive.

This tests the queue component of the candidate contribution. Yielding remains
off throughout; V22 cannot establish when yielding helps, a scheduler defect,
the historical period-cost cause, or a general CPU-quota law. Even arrivals
helping a queue is an expected direction, not the novelty claim.

## Fixed service and arrivals

Retain the original Go 1.26.1 image/server, load generator and release gate from
[V20 generation 03 preparation](../analysis/runtime_io_v20_execution_delay/generation-03/preparation/manifest.json).
Their exact identities are in design.json. Use one worker, GOMAXPROCS=1,
44,000 SHA iterations/job, queue128, WORKER_YIELD=0, service CPUs2/4,
controller/client CPUs0/1, cpu.max=`50000 100000`, cpu.max.burst=0 and the
historical memory/PID defaults. Verify actual image, executed binaries, limits,
ancestors, namespace clocks and runtime health. Do not rebuild the service or
change GC, quota period, boost, power policy, tracing or markers.

| Label | Measurement arrivals | Exact cohort |
|---|---|---|
| A: burst | Retained canonical vector, alternating 5 s low/high at nominal 56.605/169.815 offers/s | 6,793 offers in [0,60 s) |
| B: even | Offset for ID i is round-half-up(i × 60,000,000,000 / 6,793) ns, i=0..6792 | 6,793 offers in [0,60 s) |

Both mean rates are exactly 6793/60 offers/s for this finite cohort. The retained
client supports `steady` and `bursty`; B uses the decimal rate
`113.21666666666667`. Source-level arithmetic reproduces the exact B vector,
including termination at ID6793. Runtime output must still match the frozen
vector for every ID during preparation/qualification. No new client is needed
unless that check disproves feasibility; any replacement requires a new design
revision rather than silent substitution.

All trials use the **same canonical 20 s burst warmup**, full warmup drain,
empty-state metrics reset, then their assigned measurement vector and full
drain. Warmup is not changed with the treatment. Client concurrency512,
HTTP timeout5 s and tracing/accounting remain retained. Identical offers do not
promise identical completions: all errors, rejections, late responses and work
after cancellation stay recorded.

## Order, preparation and collection bounds

The measurement order is fixed:

1. New-boot technical qualification: q_A, q_B, one full trial of each pattern.
2. Calibration: cal_1, cal_2, both canonical A.
3. Produce and seal predictions from calibration only. Validate the seal before
   allowing the first validation trial to start.
4. Validation pairs: block1 A/B; block2 B/A; block3 B/A; block4 A/B.

There are eight validation trials and four independent paired blocks.
Qualification and calibration are not validation replications and are never
pooled with them or older sessions. Predictions must not fit qualification
results, validation arrivals as actually dispatched, or validation stage data.

Preparation must check exact schedules, raw joins, model edge cases, workload
and asset identities, resource preflight, functional/cancellation handling,
ownership cleanup and prediction-gate enforcement. Synthetic checks are not
performance confirmation. The post-restart snapshot is not qualification.

Keep the retained thermal policy: initial idle at least600 s; temperature
samples every5 s; stable windows at least60 s; each sensor range at most2 C,
absolute slope at most1 C/min and mean within3 C of the same-boot baseline;
settling timeout1200 s. Freeze recorded power settings and sensor inventory.
Refresh observer ownership/inventory without adding a new observer. Verify the
desktop app is absent during external-terminal performance collection; retain
host-monitor coverage and resource/power checks throughout each trial.

Bound the complete external collection session, including qualification,
calibration, prediction freezing, settling and validation, to90 minutes; cleanup
has a separate120 s grace. Retain the existing client subprocess allowance of
duration+30 s and service drain limit100 s. Exceeding a bound stops collection
and preserves partial evidence. Twelve planned warmup/arrival windows contain
16 minutes of workload, excluding drains, setup and cooling; total elapsed time
must not be advertised as16 minutes.

## Calibration and frozen baselines

For each calibration trial j, use exactly the six half-open windows
[6.5+10k,9.5+10k) s, k=0..5, relative to measurement start:18 s total.
Their locations are fixed, not selected using deadlines or attractive rates.

Require logical admitted-but-not-started backlog **greater than5 throughout
every window**, including all possible window placements under the clock
bracket. If this saturation check fails, do not select another window or fit
from validation: calibration is inadequate and collection stops before validation.
Missing joins or nonconserved event identities are technical failures.

Let C_j be completion counts in those windows at the clock-bracket midpoint.
Set mu_j=C_j/18 jobs/s and the point capacity mu=(C_1+C_2)/36.
Both capacities must be finite and positive. Require
abs(mu_1−mu_2)/mean(mu_1,mu_2) <=0.05. A larger disagreement stops validation
as unstable calibration, retaining both valid trials; it does not trigger a
search for a preferred replacement.

Also count C_j_low/C_j_high conservatively: events certainly within the fixed
window union versus events possibly within it under the clock bracket. Freeze
the capacity sensitivity range
[0.95 × min(C_j_low/18), 1.05 × max(C_j_high/18)]. The5% padding is a declared
engineering sensitivity assumption, not a confidence interval or estimated
population variability. The agreement rule and padding are practical choices
with only two calibration trials; disclose that limitation.

Freeze two baseline versions of the **same** initially empty FIFO simulator:

- M_busy: constant service time1/mu from the fixed busy windows.
- M_cpu: constant service time1/mu_cpu, where mu_cpu=0.5/mean(c_1,c_2) and
  c_j is post-reset-through-drain cgroup usage seconds divided by completed jobs
  in calibration j. Warmup/startup CPU is excluded. Zero completed jobs makes
  this parameter unassessable; do not borrow a value from validation.

For each exact scheduled offer, remove completed jobs, admit if fewer than129
jobs remain in the system, otherwise reject. One job may be active and128 may
wait. Admit at the scheduled timestamp, start at max(arrival, previous admitted
completion), and complete after the fixed service time. Completions at an
arrival timestamp occur before that admission. Predicted client response equals
model completion; entry, HTTP/handler delay, cancellation and pulsed quota
supply are explicit omissions. Predicted rejection counts as a deadline miss.
Neither model is a new algorithm.

Seal per-ID predictions for point M_busy/M_cpu, predicted summaries and sensitivity
summaries using101 equally spaced capacities across the frozen range plus the point
capacity. The sampled range is sensitivity evidence, not a guaranteed continuous
bound. Seal calibration references/hashes, both capacities, vectors, scientific
design, implemented sources, decision thresholds, prediction hashes and creation
time **before validation**. Do not use the old session's fitted capacity.

## Outcomes and decisions

For each trial, observed miss fraction = 1 − successful responses within500 ms
of scheduled offer /6793. Errors/rejections count as misses. The clock is the
client's own clock; do not reset the deadline to actual dispatch. A predicted
miss is rejection or predicted completion more than500 ms after scheduled offer.

| Decision | Frozen requirement |
|---|---|
| Primary trial accuracy | Absolute M_busy miss-fraction error <=3 pp in **each of eight trials** |
| Primary contrast accuracy | For each block, absolute error of predicted minus observed (miss_B−miss_A) <=3 pp in **each of four blocks** |
| Supporting queue peak | Absolute difference between predicted and observed maximum logical queue <=10 jobs in every trial, including drain |
| Supporting rejection accuracy | Absolute rejected-offer fraction error <=0.5 pp in every trial |
| Supporting ordinary recovery | Absolute error of mean recovery <=250 ms in every A validation trial, with clock uncertainty accounted for |
| Anticipated even-arm check | If the frozen sensitivity lower capacity exceeds6793/60: every B trial has >=99% all-offer500 ms success, zero rejection and peak queue<=10 |

Primary transfer passes only if all12 primary checks pass; pooled agreement
cannot rescue a failing block. Queue-account support additionally needs every
queue/rejection/recovery check. The even-arm check is a separate prediction
screen, not substituted for primary accuracy. If the sensitivity lower capacity
is at/below the mean arrival rate, retain the overload/uncertain predictions and
test primary accuracy, but mark the intended safely-below-capacity even comparison
as unestablished. Do not force the anticipated99% outcome.

Three pp corresponds to about204 offers per trial; ten jobs are7.8% of queue128;
250 ms is half the selected deadline;0.5 pp rejection is about34 offers. These
are practical accuracy screens inherited/narrowed from exploratory V20, not
statistical equivalence, a production SLO, or universal acceptable error.

Logical queue is reconstructed from admission/start events, with simultaneous
changes combined; peak does not need a client-clock origin. Ordinary A recovery
uses switches at10,20,30,40,50 s: the last return to Q<=5 after a switch with no
later Q>5 before the next high phase. If Q never exceeds5, recovery is0. If it
remains above5 to the next high phase, recovery is right-censored at5 s and
cannot pass an ordinary-recovery check. Final recovery after60 s is a separate
drain outcome, because no low-phase arrivals follow it. This intentionally
separates the final drain from the older six-switch retrospective mean.

Compute admissible recovery ranges under the shared clock bracket using event
boundaries, not independent timestamp shifts. The supporting error passes only
if its worst absolute admissible value is <=250 ms; unresolved ambiguity cannot
pass. Predicted B has no burst recovery metric. Report queue trajectory on the
fixed100 ms grid, stage residuals/coverage, successful p99, all-offer1 s misses,
successful responses after1 s, cancellations, CPU/job and delivered CPU as
diagnostics without changing the primary rule. Missing stage timings remain
unknown. Aggregate success never implies exact-stage or rare-tail accuracy.

Evaluate M_cpu using the same outcomes. For the supporting baseline comparison,
each block's score is the mean of its two absolute trial miss errors. A declared
M_busy advantage requires a smaller score in all four blocks and at least1 pp
lower mean score across blocks. Both models passing without that advantage is
reported as no demonstrated practical advantage over this baseline. Neither
baseline ranking nor a positive A-to-B effect alone establishes novelty.

Report every block, mean/median/range and signed errors; summaries across requests
are descriptive, not independent replications. With four blocks, do not add a
request bootstrap, significance gate, optional stopping or equivalence claim.
Even if a valid early result fails a scientific criterion, finish the bounded
fixed validation schedule unless a technical/time bound requires stopping.

## Technical acceptance, retries and interpretation

Each warmup and measurement requires exact IDs/offsets and counter conservation,
zero client drops, zero missed arrivals and dispatch-lag p99<=2 ms. Retain the
inherited direct clock-bracket width<=1 ms and host/server anchor checks, verified
empty reset/full drain, unchanged resources/power, adequate monitor coverage,
raw replay and ownership/cleanup receipts. Retain the1 s monitor sampling and
minimum80 recorded samples covering warmup/measurement, with the inherited
per-sample quiet/power checks. Service rejections, timeouts or bad
deadline performance are valid adverse outcomes when accounting is conserved;
they are not technical failures or reasons to rerun.

Allow **one total technical retry** across all planned slots, preserving the
failed attempt and a concrete technical reason. Verify cleanup and repeat normal
settling; retry only the failed slot without replacing accepted trials or changing
order, assets, model or settings. Never retry valid unstable calibration or a
valid prediction failure. A second technical failure, reboot, source/asset or
protocol change stops the generation. Interrupted evidence is retained; incomplete
validation cannot receive the complete primary-pass label.

Decision precedence: incomplete/invalid evidence; inadequate/unstable calibration;
otherwise primary transfer failure/pass; then supporting queue-account and
even-arm/baseline labels. A primary failure is a useful scoped counterexample to
this capacity-transfer assumption, not proof of a scheduler bug. Post-validation
refits may be labeled exploratory diagnostics only, never frozen prediction
success. A primary pass supports this service/host/boot/pattern pair, not a general
boundary. Yielding-boundary claims require their own future matched comparison.

Step 4 is implementation and sealed preparation against this design. No optional
burst-duration extension, performance collection or renewed period-reversal
investigation is launched by completion of Step 3.
