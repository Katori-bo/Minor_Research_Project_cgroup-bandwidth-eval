# V30 prospective deadline-resolution confirmation specification

Status: sealed scientific specification and compiled offered schedules.
Collector/analysis implementation and runtime qualification are pending.
No new service measurement has started. This is a prediction/decision study,
not a phase-causal experiment, and is not a claim of a novel algorithm.

## Scope and controls

Retain the q025_large condition: quota 25000 us per 100000 us, burst credit zero,
88000 SHA iterations, one worker, GOMAXPROCS=1, queue 128, server CPUs 2 and 4,
client/control CPUs 0 and 1, concurrency 512 and client timeout 5 s. Use the same
qualified service/client/gate binaries. Record their immutable hashes, topology,
resource ownership, clocks, power policy, temperatures and CPU accounting.
Use normal-user external orchestration and a fresh read-only observer audit;
Codex/ChatGPT must be absent during measurement. No kernel phase is assumed
observable, aligned or controlled by container startup or gate release.

Collect the retained sixteen independent calibration trials anew, in their
sealed order and with warmup/reset/drain semantics. Require complete conserved
cohorts, qualified resource/clock state and calibration busy-capacity range
<=5%. Fit original capacity estimators and the empirical non-queue delay
distribution using calibration only. Delay samples use the four reference
15/30 low-rate trials with queue wait <=100 us; negative residuals invalidate
that baseline rather than being silently clipped. Freeze all per-offer forecasts
for every validation profile before any validation offer is dispatched.

No parameters, phase, delay distribution or model-switch threshold can be fitted
to validation outcomes. Failure to qualify calibration stops validation. Preserve
unavailable alternatives. The prior interrupted V29 run and both complete V29
generations are discovery evidence and enter neither V30 parameter estimation
nor its validation outcomes.

## Unseen validation profiles

Each measurement lasts 60 s, after a 20 s warmup at the profile's low/steady
rate, with retained settling, reset and bounded drain.

| ID | Offered traffic | Measurement offers |
|---|---|---:|
| A | Steady 4 rps | 240 |
| B | Steady 18 rps | 1080 |
| C | 2 s cycle: 1 s at 4 rps, 1 s at 42 rps | 1380 |

Rates are fixed from discovery-scale reasoning near 0.1/0.5/1.2 times 35 rps;
they are not tuned after fresh calibration. Integer phase counts avoid ambiguous
fractional per-cycle offers. These schedules were not V29 validation traffic.

Six blocks use all six profile permutations, in this fixed order:
ABC, BCA, CAB, ACB, CBA, BAC. Each profile occupies each position twice and every
ordered adjacency occurs twice. Eighteen validation trials produce 16200
measurement offers. The block, rather than each request, is the replication
unit. Resetting between trials does not prove statistical independence; report
block order and possible drift.

## Models and prediction contract

Primary comparison: independently calibrated busy-capacity constant-rate FIFO
against the ideal periodic-budget FIFO, averaged uniformly over 100 sampled
phases at 1 ms spacing, with full initial credit and the independently calibrated
non-queue delay distribution. Effective demand is `(quota/period)/busy_capacity`.
All-offer denominators include failed, rejected, dropped and missing offers.
The phase prior, initial credit, single-budget abstraction and independent-delay
assumption are explicit approximations, not observations or CPU guarantees.

Secondary comparators retain fluid quadratic, fluid busy plus delay, periodic
uniform phase without delay, and fixed zero-phase/full-credit replay as a
scenario diagnostic. Report sampled ranges over empty/full starting credit and
calibration capacity extremes; these are not continuous/hard bounds. Never
choose an oracle phase from held-out outcomes.

A provisional model-selection rule uses periodic+delay for D/P <=0.25 and the
original busy-capacity fluid model for larger ratios. It was selected from V29
discovery and is an ordinary heuristic. Primary 25 ms predictions equal the
periodic model; secondary unseen deadlines test the threshold rather than
establishing a general theorem.

## Primary endpoint and gates

Primary deadline: **25 ms**, measured from scheduled offer to successful client
completion. Benchmark SLO: **at most 5% misses**. This is an engineering target
for the experiment, not an asserted application requirement.

For each block, average absolute miss-fraction error equally across its three
profiles. Pair that block's errors between the two primary models. Report six
block contrasts, their mean and a two-sided 95% t interval using df=5 and a
conservative multiplier 2.571. The interval assumes approximately independent,
normal block contrasts and does not supply a universal guarantee.

Confirmation requires all of the following, specified before fresh outcomes:

- All eighteen trials meet data/clock/resource/cohort qualification. Validation
  does not require nonempty queues: empty queues are deliberate in profiles A/B.
- Periodic+delay mean absolute error, equally weighted across the six blocks,
  is <=3 percentage points. This is a new engineering accuracy target for this
  test, not an automatic transfer of V1's criterion.
- Every block's improvement over fluid busy is positive, and the 95% interval's
  lower endpoint is >=5 percentage points, the declared minimum useful effect.
- The primary periodic forecast classifies each trial consistently with its
  observed <=5%/>5% miss-budget decision, and at least one profile meets the
  benchmark SLO in every block. If all profiles fail, accuracy alone does not
  establish a useful operating choice.

Otherwise retain the outcome as negative/inconclusive or technically incomplete;
do not collect extra blocks until it passes. Six blocks are a fixed feasibility
budget, not a demonstrated power calculation for the new profiles. Report
errors and decisions separately and do not infer a phase cause from a win.

Secondary deadlines: 10/20/35/50/75/100/150/500 ms, covering new intermediate
resolutions and the original long-deadline endpoint. Report all methods, signed
errors, maximum errors, sampled-range coverage and width, and request-stage
decomposition with clock bounds. No secondary accuracy/superiority claim or
multiple testing significance rule is introduced here.

## Lifecycle and implementation gate

Use six bounded functional/runtime qualification cases including the new 2 s
profile. Preserve old binaries; qualify their exact compiled schedules against
an independent rational timestamp oracle. Record raw offers, client failures,
server stages, startup assets, CPU usage/throttling endpoints, warmup/drain and
the retained 1 Hz host monitor. No unqualified tracing collector is added.

One ordinary technical retry is permitted for the generation after verified
owned cleanup. Deliberate SIGTERM/interrupt/deadline expiry is terminal and may
never start a retry. Scientific adverse outcomes are not retryable. Freeze a
maximum of 41 active-container attempts: six qualifications, 34 scientific
trials and one technical retry. No overwriting or automatic resume.

Bound preparation to 600 s, observer authentication/inventory to 300 s,
measurement to 9000 s, analysis to 900 s and active containers to 360 s. Use a
12600 s (3.5 hour) total bound with a final 120 s cleanup reserve. The extra two
validation trials and additional offline forecasts justify a newly declared
lifetime; no accuracy or state criterion is relaxed. Expect roughly two hours
if the host settles normally. Qualification and bounds must be implemented and
reviewed before a runnable launcher is supplied.

Publication scope remains this service/host and these held-out patterns. A
predictive boundary and an ordinary adequate model can be a useful empirical
extension. New estimator, phase mechanism, universal superiority and transfer
require separate evidence.
