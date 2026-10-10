# Deadline Resolution and Traffic State in Capacity-Based Forecasts Under a Fractional CPU Quota

Working extension draft, 9 October 2026. This manuscript separates completed
prospective evidence from subsequent exploratory model development. V1 and all
frozen study sources remain preserved. The new empirical-latency comparison
requires fresh confirmation; related-work coverage is targeted rather than an
exhaustive novelty review.

## Abstract

An accurate average-capacity estimate need not yield accurate deadline
predictions when it is interpreted as a continuous processing speed. We study
this distinction in one Go HTTP service under fractional CPU quotas. A
four-condition robustness study provides independently calibrated evidence at
a 500 ms deadline. A subsequent prospective study holds the 25 ms/100 ms CPU
contract fixed, doubles the original request work, and freezes all predictions
before eighteen trials of previously unused steady and burst traffic. At a
25 ms deadline, average absolute miss-fraction error is 73.599 percentage
points for busy-capacity constant-rate FIFO and 2.341 for an ordinary
uniform-phase periodic-budget approximation with calibrated response delay.
The latter correctly classifies all eighteen trials against a 5% miss budget.
Its errors at 10 ms and medium deadlines expose a narrower validity region.
Post-study exploration finds that a paired empirical latency distribution from
low-rate calibration records predicts the steady 10 ms endpoint with 1.079
points of error, but fails on burst traffic. The contribution is a reproducible
empirical boundary and prospective operating-condition evidence, rather than a
new queueing algorithm, causal phase explanation or universal correction.

## 1. Question and contribution

We ask: **what measured timing information is sufficient to predict deadline
misses under a fractional CPU quota, across deadline resolutions and traffic
states?**

The completed capacity-calibration paper compared independently measured
capacity inputs within a common finite FIFO model. This extension tests the
next assumption: whether replacing intermittently available service with its
average processing rate preserves a useful deadline forecast. It also asks
what happens when a deadline approaches the measured response-time
distribution itself.

There are three distinct evidence levels:

1. The retained V1 and V29 studies establish scoped capacity and long-deadline
   evidence with independently calibrated inputs.
2. V30 prospectively confirms a particular 25 ms prediction/decision contrast
   on fresh traffic patterns, after the ordinary timing approximation was
   developed using V29 discovery data.
3. The new empirical latency-CDF comparison is retrospective development
   prompted by V30's 10 ms failure. Its parameters use calibration records,
   but its method was chosen after validation outcomes; it is not another
   prospective result.

This separation prevents a successful exploratory remedy from acquiring
confirmation status merely because its parameters came from calibration.

## 2. Model and prior-method boundary

The constant-rate FIFO uses calibrated throughput C, assigning each admitted
job service time 1/C. The periodic-budget approximation consumes an effective
demand d = (Q/P)/C while credit is available, and replenishes its global budget
Q at each period boundary P. Both model one job in service and up to 128 waiting
jobs; modeled rejection counts as a deadline miss.

Periodic CPU supply and average-speed approximations are established ideas.
[Linux bandwidth-control documentation](https://docs.kernel.org/scheduler/sched-bwc.html)
describes quota ceilings, replenishment, allocation slices and retained
CPU-local runtime. Our single global-budget abstraction omits those local
details, competing service threads and execution-cost variation.
[Cucinotta et al.](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf)
study hierarchical real-time reservations, with guarantees and modeling
premises that differ from this ordinary bandwidth-limited benchmark. Our
experiment is not a reproduction or refutation of their full method.

The main periodic forecast averages 100 shared phases at 1 ms spacing, with
full initial credit. This is an assumed phase prior; kernel replenishment phase
was neither observed nor aligned. A response-delay distribution is fitted
from four low-rate calibration trials using e2e minus queue minus worker-wall
time, restricted to successful calibration requests with queue wait <=100 us.
It is appended independently of modeled service. Neither effective demand nor
the residual is an isolated measurement of SHA CPU demand.

## 3. Evidence sequence and experimental contract

V29 comprises four conditions of the same service and host: CPU allowance
25%/50% crossed with two SHA iteration counts. Each complete condition uses
sixteen calibration and sixteen validation trials. Three complete conditions
come from the overnight generation; the final condition comes from an
independently recalibrated rerun. The interrupted final-condition record is
preserved as supplementary evidence and is not pooled into the full matrix.
Conditions ran sequentially, so cross-condition differences are confounded
with time. Request-size changes do not constitute independent application
transfer.

V30 uses Q=25 ms, P=100 ms, zero configured burst credit, 88000 SHA iterations,
one worker, GOMAXPROCS=1, queue size 128 and server CPUs 2 and 4. Client/control
work uses CPUs 0 and 1. Client concurrency is 512 and timeout is 5 s. Six
functional cases and an unreleased resource preflight qualify the retained
binaries before scientific collection. Fresh observer inventory, clocks,
power/thermal settling, ownership and the 1 Hz host monitor are retained.

Sixteen fresh calibration trials precede a forecast seal. Eighteen validation
trials use six blocks in order ABC, BCA, CAB, ACB, CBA, BAC. Each profile occurs
in each position twice. Measurement is 60 s after a 20 s warmup, with reset and
bounded drain between trials.

| Profile | Traffic | Offers per trial |
|---|---|---:|
| A | Steady 4 requests/s | 240 |
| B | Steady 18 requests/s | 1080 |
| C | Repeated 1 s at 4 requests/s, then 1 s at 42 requests/s | 1380 |

There are 16200 validation offers. The endpoint measures scheduled offer to
successful client completion; failed or missing offers count as misses.
Empty queues are legitimate validation behavior. Six blocks, rather than
requests, are the replication units. Counterbalancing does not prove their
independence.

The primary deadline is 25 ms and the experimental miss budget is 5%. Frozen
confirmation gates require all eighteen qualified trials, <=3 pp mean block
MAE for periodic+delay, positive improvement in every block and >=5 pp at the
lower endpoint of the declared 95% block-based t interval, correct miss-budget
classification for every trial, and at least one profile meeting the target in
every block. The interval uses df=5 and multiplier 2.571, assuming approximately
independent normal block contrasts. These are declared engineering targets;
the trial count is a feasibility budget rather than a demonstrated power
calculation.

## 4. Retained capacity and long-deadline evidence

| V29 condition | Busy capacity requests/s | Busy-model 500 ms MAE pp |
|---|---:|---:|
| 50% CPU, 44000 iterations | 153.792 | 0.479 |
| 25% CPU, 44000 iterations | 69.625 | 1.359 |
| 50% CPU, 88000 iterations | 77.646 | 0.672 |
| 25% CPU, 88000 iterations | 34.854 | 1.295 |

The frozen busy-comparator gates pass in all four complete V29 conditions.
This extends within-service robustness evidence but neither establishes
causal cross-condition effects nor overturns V1's inconclusive minimum-effect
comparison against its quadratic benchmark. Each study retains its own
calibration, traffic and gates.

## 5. Prospective 25 ms result

V30's fresh busy estimate is 34.917 requests/s. The constant-rate substitution
therefore assigns every job 28.640 ms of service and predicts 100% misses at
25 ms even without a queue. Actual steady requests frequently finish sooner
than that imposed floor.

| Traffic | Observed mean miss fraction | Periodic+delay forecast | Periodic+delay MAE pp |
|---|---:|---:|---:|
| Steady 4 requests/s | 0.000% | 0.000% | 0.000 |
| Steady 18 requests/s | 0.000% | 0.000% | 0.000 |
| Bursty profile C | 79.203% | 72.179% | 7.024 |

The primary equal-profile/block MAE is 73.599 pp for fluid busy and 2.341 pp
for periodic+delay. Every block improves; mean paired improvement is 71.258 pp
with declared interval [68.900,73.615] pp. All eighteen observed <=5%/>5%
decisions match the periodic forecast. All 34 scientific trials complete
without a technical retry; independent completion replay passes.

The primary accuracy gate applies to the mean. Two blocks exceed 3 pp and the
maximum individual error is 12.097 pp. Burst-only MAE is 7.024 pp; weighting
by offered requests instead of profiles gives 3.590 pp. Thus the result is
useful classification of widely separated operating conditions, not evidence
of <=3 pp error on every traffic pattern or a precise boundary near 5% misses.
Zero observed misses in steady trials do not guarantee zero future misses.

## 6. Deadline-resolution limits

| Deadline ms | Fluid busy MAE pp | Periodic+delay MAE pp |
|---:|---:|---:|
| 10 | 24.394 | 49.622 |
| 20 | 73.080 | 2.318 |
| 25 (primary) | 73.599 | 2.341 |
| 35 | 4.018 | 3.306 |
| 50 | 2.947 | 4.122 |
| 75 | 1.385 | 6.181 |
| 100 | 0.918 | 8.173 |
| 150 | 2.738 | 9.691 |
| 500 | 0.000 | 0.000 |

The periodic approximation improves 20–25 ms forecasts, but fails at 10 ms and
is less accurate than fluid busy at 50–150 ms. The 500 ms endpoint has no misses
and supplies no comparative discrimination in V30. Secondary endpoints carry
no new superiority-significance claim.

The fixed zero-phase/full-credit diagnostic has 0.902 pp MAE at 25 ms, below the
main model's 2.341 pp. This was a prespecified scenario, not measured phase;
promoting it after outcomes would require a new selection/confirmation
contract. Periodic without response delay has 2.729 pp MAE, so this experiment
does not demonstrate that delay calibration is necessary. The discovery
model-switch rule creates nonmonotone miss curves in six trials. It is not one
coherent latency distribution and cannot be presented as a general correction.

## 7. Exploratory explanation of the 10 ms failure

All twelve steady validation trials record zero throttled periods. Median queue
wait is about 0.009 ms. Nevertheless, about 67% of their requests miss 10 ms.
This failure appears without recorded quota throttling or substantial queues.

The model infers 7.160 ms effective CPU demand from busy throughput. The four
low-rate calibration cohorts instead have 8.855 ms median worker-wall time,
1.397 ms mean non-queue residual and 10.228 ms median paired queue-free
latency. The deadline lies near that distribution's center; an error of one or
two milliseconds materially changes the predicted miss fraction.

For each selected calibration request define R = e2e - queue, retaining the
original pairing between worker and remaining response time. The ordinary
empirical estimate is the fraction of R samples greater than the deadline.
There are 676 samples across four independently collected calibration trials.
No validation residual, phase or threshold is fitted. The choice to examine
this model is post-V30 and therefore exploratory.

At 10 ms this calibration CDF predicts 67.751% misses, close to the observed
steady means of 67.569% and 66.929%. Across the twelve steady validation trials,
its MAE is 1.079 pp, versus 66.953 pp for frozen periodic+delay on that same
steady subset. Independently combining the worker and residual marginals gives
6.778 pp error; using median worker time with the residual distribution gives
9.822 pp. These contrasts show that the recorded timing distribution and
pairing can matter near this threshold. They do not establish that the paired
CDF dominates at other deadlines: at exploratory 11 ms the independent
convolution is more accurate, and paired-CDF error rises to 4.169 pp at 10.5 ms.

The calibration CDF supplies no overload mechanism. At 25 ms it predicts zero
burst misses, producing 79.203 pp burst error. It is an ordinary reference for
the observed low-queue regime, not a universal alternative to periodic/FIFO
modeling. A predictive scope rule still requires independent testing.

## 8. Stage, accounting and mechanism boundaries

At 10 ms the steady profiles produce 5310 misses. Computation is certainly
after the deadline for 2877, certainly within it despite a client miss for
1579, and clock-boundary ambiguous for 854. At 25 ms, all 6558 misses occur in
profile C: 6529 have computation certainly after the deadline, 22 certainly
within it despite a client miss, and seven are ambiguous. These are
descriptive counts, not a causal decomposition of CPU budget, frequency,
descheduling, dispatch or HTTP effects.

Treating the calibration worker-wall median as transferable CPU on-time while
retaining busy capacity would require 30.917 ms of worker availability per
100 ms, above the configured 25 ms CPU quota. The earlier rejected two-rate
identification therefore remains inadmissible. Neither clipping its budget nor
selecting faster calibration samples is justified. Aggregate CPU/job includes
the whole service; worker-wall time includes elapsed scheduling effects. A
measurement or intervention contract must distinguish these before a causal
claim is made.

## 9. Interpretation and remaining confirmation

The evidence supports a scoped hierarchy of useful information. Average busy
capacity supports retained long-deadline forecasts; ordinary periodic service
repairs a confirmed 25 ms operating-condition contrast; near the 10 ms response
transition, the effective-demand approximation misses measured job-level
timing that a simple empirical calibration reference captures in discovery.
Traffic state matters alongside deadline resolution. This is not a theorem
that one particular ratio D/P determines the correct model.

A proposed V31 study would freeze the empirical reference and ordinary
comparators before fresh calibration and new steady-rate trials. It would test
10 ms accuracy prospectively, retain the 10–11 ms transition as a diagnostic,
and check observed operating decisions at declared 10/12 ms endpoints. Its
runtime and collector implementation remain pending. Independent service/host
transfer and qualified mechanism measurements are subsequent scope extensions,
not evidence already supplied by this manuscript.

## 10. Reproducibility and evidence map

| Result or claim | Local evidence | Status |
|---|---|---|
| V1 capacity comparison | `paper/capacity_calibration_empirical.md` and V28 sealed reports | Completed prospective study |
| Four V29 conditions | `analysis/runtime_io_v29_result_review/20261009-complete-matrix/report.json` | Combined independently verified complete records |
| Model development before V30 | `analysis/runtime_io_v2_extension/20261009-v29-ordinary-models/report.json` | V29 discovery |
| V30 primary confirmation | `analysis/runtime_io_v30/generation-01/analysis/1791534266682067738/report.json` | Fresh prospective validation |
| V30 audit and limits | `analysis/runtime_io_v30_result_review/20261009-generation01/report.json` | Independent completion replay and descriptive audit |
| Empirical timing reference | `analysis/runtime_io_v2_extension/20261009-v30-timing-boundary/report.json` | Post-V30 discovery; not confirmed |

Per-offer forecasts, raw client/server stages, input hashes, immutable source
snapshots and result seals remain available. Five new numerical checks verify
empirical boundary counting, convolution, calibration leakage rejection and
stage-count conservation. They complement the retained independent periodic
slot-oracle tests and full completion replay; software checks are not empirical
replicates.
