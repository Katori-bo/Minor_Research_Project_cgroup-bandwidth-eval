# V31 candidate: fresh confirmation of the low-queue timing boundary

Status: concrete scientific proposal after the completed V30 discovery audit.
This is not yet a sealed execution design or a runnable/qualified collector.
No new measurements have started. V30 and the new empirical comparison are
discovery evidence for this proposal; neither supplies V31 outcomes.

## Question and scope

Can an ordinary paired empirical response-time distribution, measured during
independent low-rate calibration, forecast the 10 ms miss fraction on fresh
steady traffic more accurately than the retained CPU-derived periodic model?
The claim is confined to the declared low-queue, unthrottled regime on this
service/host. It is not a new estimator, overload predictor or phase-causal test.

Retain the V30 resource/request contract: quota 25000 us / period 100000 us,
configured burst zero, 88000 SHA iterations, worker 1, GOMAXPROCS 1, queue 128,
server CPUs 2 and 4, client/control CPUs 0 and 1, client concurrency 512 and
timeout 5 s. Use unchanged qualified service/client/gate binaries, raw stage
records, power/thermal controls, clock joins and 1 Hz host monitor. No tracing
collector or host setting change is proposed.

## Fresh parameters and frozen models

Collect the original sixteen V30 calibration slots afresh. Keep their resource,
clock/cohort and <=5% busy-capacity-range qualification. The four low-reference
15/30 steady trials (actual 3.75/7.5 requests/s) supply successful requests with
queue <=100 us. Preserve the distribution of R=e2e-queue with paired worker
and residual timing. Negative stage residuals or absent eligible samples make
the baseline unavailable; do not clip or replace them. Calibration trial
counts, accepted sample counts and sensitivity across the four cohorts remain
visible. Hundreds of requests are not hundreds of experiment replicates.

Primary models: paired calibration CDF versus retained uniform-phase
periodic-budget FIFO with calibrated independent response delay. Freeze the
100 sampled phases/full initial credit before outcomes. Secondary comparators:
fluid busy, fluid quadratic, independent worker/residual empirical convolution,
median worker plus empirical response residual, and fixed-zero-phase replay
as an explicit unobserved-phase scenario. No post-outcome selection of phase,
quantile, calibration cohort, deadline or model switch.

Seal every per-offer probability for every declared validation profile and
deadline after fresh calibration and before the first validation offer.
This generation must have its own namespace and sources; do not modify V30.

## New validation traffic and replication

| Profile | Traffic | Offers in 60 s |
|---|---|---:|
| A | Steady 5 requests/s | 300 |
| B | Steady 11 requests/s | 660 |
| C | Steady 19 requests/s | 1140 |

These rates were not V30 validation profiles. They are fixed from discovery
before new measurements, rather than adjusted after fresh calibration. Use
20 s warmup at the same rate, retained settling, reset and drain. Six blocks
retain orders ABC, BCA, CAB, ACB, CBA, BAC: eighteen validation trials and
12600 measurement offers. Qualification/export must compare actual binary
schedules with an independent rational oracle.

Keep all offered outcomes. A technically valid trial that exits the claimed
domain is an adverse scientific result, not grounds for a replacement. Proposed
domain checks are zero recorded measurement throttled periods and at least
99% of offered requests having an observed worker queue interval <=100 us.
Unobserved worker intervals do not count as domain successes. The domain
checks are proposed operational limits, not proofs that external scheduling
or all CPU delays are absent. They must be finalized and frozen before launch.

## Primary endpoint and decisions

Primary accuracy deadline: 10 ms. All-offer misses include errors, rejections,
dropped and missing offers. Average trial absolute miss-fraction errors equally
across the three profiles in each block; the six block errors are the replication
units. Pair CDF and periodic errors within blocks. Proposed confirmation gates:

- All eighteen trials are technically qualified and remain inside the declared
  scientific domain; domain exits are reported without excluding trials.
- Mean of six block CDF errors <=3 pp.
- Improvement over periodic is positive in every block; the lower endpoint of
  the declared 95% block t interval (df=5, multiplier 2.571) is >=5 pp.
- The CDF predicts the observed <=5%/>5% miss-budget decision in every trial
  at each of the declared 10 and 12 ms endpoints; every block has a profile
  meeting the target at 12 ms. Decisions and accuracy are reported separately.

Targets are engineering choices, not inherited application requirements. Six
blocks are a feasibility budget, not an independently established power result.
If any gate fails, retain negative/inconclusive or domain-exit status; do not
add blocks or move the deadline until a result passes.

Secondary deadlines: 9/9.5/10.5/11/12/20/25/50/100/500 ms. The 11 ms diagnostic
is near the discovered calibration 95th percentile and the 5% miss budget.
It is deliberately not substituted for a primary endpoint after observing
fresh outcomes. Report all methods and per-profile errors, including any
counterexample near 10.5 ms. Sensitivity to pairing, calibration cohorts,
request-level variability and response/worker dependence is descriptive unless
a separate inferential contrast is prespecified.

## Implementation and lifetime gate

Reuse six functional cases covering idle, high calibration steady load, mixed
calibration burst, new steady rates and cancellation, plus one unreleased
resource preflight. Maximum 41 released containers: six functional, 34 scientific,
one ordinary technical retry; maximum 42 created including preflight. Owned
cleanup must verify every attempt. Signal interruption and any lifetime timeout
are terminal. Scientific domain exits, unfavorable errors or wrong decisions
are not retryable. Automatic resume and overwrite are prohibited.

Candidate bounds retain V30: preparation 600 s, fresh terminal-authenticated
read-only observer inventory 300 s, measurement 9000 s including settling and
forecast freeze, analysis 900 s, active service 360 s, total campaign 12600 s
with 120 s cleanup reserve. Collect in an external normal-user terminal with
Codex/ChatGPT absent, after runtime qualification. Anticipated duration is about
two hours, not a guarantee under adverse settling.

Before an execution command is supplied: implement the separate collector and
verifier; qualify calibration-only CDF fitting and all offered schedules; check
raw outcomes, lifecycle bounds and terminal authentication; seal the final
design and source/binary snapshots. This proposal does not authorize calling
already-seen V30 outcomes a fresh V31 validation.
