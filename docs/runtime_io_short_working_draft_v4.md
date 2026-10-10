# Whole-Run CPU Accounting and Busy Capacity Under a Fractional CPU Quota

### A prospective case study with idle correction and nonlinear regression controls

Short working draft, 8 October 2026. Consolidates completed V22–V28 evidence;
V24 collection failures remain historical failures. Version 3 is preserved.
The contribution is scoped empirical evidence; publication-level novelty is
not established by this draft or the accompanying prior-method assessment.

## Abstract

We examine whether whole-run CPU per completed job represents busy capacity
for a quota-limited service. Predictions frozen before fresh validation show
that substituting nominal CPU allowance divided by whole-run CPU/job into a
shared FIFO model substantially overpredicts 500 ms deadline misses. Earlier
validation covers two work sizes and two burst timescales. A subsequent
sampler-off comparison uses independent calibration for five capacity inputs.
Across sixteen validation trials, busy calibration yields a mean absolute miss
error of 0.453 percentage points, versus 13.494 for whole-run accounting,
13.471 after direct live-idle correction, 31.314 for linear regression, and
1.169 for a declared quadratic utilization–throughput benchmark. Busy passes
every predefined accuracy check, but its advantage over the quadratic does
not meet the frozen minimum-effect screen. Separate composition controls show
directional CPU/job changes with stable busy capacity, while their minimum
effect screen also remains inconclusive. Load-dependent demand estimation is
established prior work. These results support a reproducible forecasting case,
not a new estimator, identified mechanism, or general superiority claim.

## 1. Question and contribution

The question is whether a whole-cohort CPU cost can stand in for capacity
while work is queued. Whole-run accounting includes changing load and final
drain; busy capacity counts completions in fixed backlogged windows. Their
agreement is an empirical question, and a modest capacity difference can
produce a large miss-fraction difference near sustained overload.

The paper combines prospective deadline forecasts, bounded phase accounting,
qualified low-load measurements, a controlled composition comparison, and
fresh calibration against CPU-based alternatives. The main finding is that
the declared whole-run substitution underestimates busy capacity and materially
overpredicts misses in this service. Direct zero-request CPU correction barely
changes that result. A nonlinear CPU-based benchmark predicts nearly the same
capacity, substantially narrowing the possible contribution.

We do not claim that practitioners universally use the tested substitution,
that CPU measurements are generally inadequate, or that busy calibration is a
new method. The practical lesson concerns the measurement scope and forecast
consequences of this particular substitution under the tested conditions.

## 2. Measurements and designs

The containerized Go service has one worker, `GOMAXPROCS=1`, a waiting queue
of 128 jobs, and yielding disabled. CPU allowance is 50 ms per 100 ms, with
zero burst credit. The service uses CPUs 2 and 4; the client/controller uses
CPUs 0 and 1. Host power, resource limits, application identities, schedules,
kernel and boot identities are retained and checked. Work is repeated SHA
computation: 44,000 iterations per small job and 88,000 per large job. All
studies use one host and application; work-size transfer is not independent
application transfer.

Let `q = 0.5` CPU-seconds per wall-second. With cgroup CPU use `C`, completed
jobs `N`, and enclosing measurement-through-drain duration `T`, define:

```text
c_whole = C / N
mu_whole = q / mean(c_whole)                  jobs per wall-second
mu_busy = mean(completions / window duration) jobs per wall-second
```

The means use the declared independent calibration trials. Busy eligibility
uses waiting-queue observations throughout clock-expanded fixed windows.
V22/V23 require more than five waiting jobs in six three-second windows;
later designs require a guaranteed positive waiting queue in their separately
frozen windows. Definitions and thresholds are not retroactively harmonized.
Native phase-counter brackets bound CPU and completion counts without
interpolation. Accounting bounds are distinct from statistical intervals.

All prospective capacity inputs feed the same initially empty constant-service
FIFO model, with one active job and 128 waiting slots, using exact offered
timestamps. It omits entry delays, runtime/HTTP effects and quota pulses.
The deadline starts at the scheduled offer, and unsuccessful offers count as
misses in the full offered cohort. Calibration and predictions seal before
validation; validation outcomes never fit a method. The comparison tests
capacity inputs within this forecasting model.

| Study | Purpose and retained design |
|---|---|
| V22 | Two calibration runs; eight fresh validation trials comparing bursty/even small-job arrivals; four paired contrasts. |
| V23 | Fresh calibration per work size; sixteen validation trials in four balanced blocks crossing two sizes and 3/12 s burst cycles; eight paired contrasts. |
| V25 | Sixteen diagnostic runs: four sampler-off and four sampler-on per size, repeated controls and bounded phase accounting. |
| V26 | Four sampler-on steady runs at 15/30/30/15 jobs/s; fixed low-load windows qualify queue and throttling conditions. |
| V27 generation-03 | Sixteen runs in four balanced blocks crossing low rates 15/30 and sampler off/on, with identical high arrivals at 169.8 jobs/s. |
| V28 | Sixteen calibration slots, a forecast freeze, then sixteen sampler-off validation slots in four balanced blocks crossing low rates 15/30 and 6/12 s cycles, with high arrivals at 180 jobs/s. |

V27 changes low-phase arrivals while holding high-phase offers fixed. Each
60 s measurement has four 15 s cycles, comprising 10 s low and 5 s high.
The high-phase cohort contains 3,396 offers; low cohorts contain 600 or 1,200.
Busy windows are fixed at 11.5–14.5 s in each cycle. Sampler-on low windows
at 3–8 s qualify separately. The frozen composition screen requires both
95% cost-increase interval lower bounds to reach 3%, busy-capacity intervals
within ±2%, and sampler-interaction intervals within ±2 percentage points.

V28 uses four mixed calibrations for whole and busy estimates and twelve
idle/steady observations for regression: two balanced blocks at zero requests
and steady offered rates 15/30/60/90/120. Dedicated live-idle observations
measure background rate `b_idle`. The declared correction is:

```text
mu_idle = (q - b_idle) / mean((C - b_idle*T) / N)
U = C / T; X = N / T
linear:    U(X) = b + d*X
quadratic: U(X) = b + d*X + e*X^2
regression capacity: admissible root of U(X) = q
```

Regressions use equal-run CPU-utilization residuals, a nonnegative intercept,
a positive initial slope, bounded extrapolation and the declared monotonicity
checks. Quadratic fitting compares a finite candidate family including free
and zero intercept and the linear boundary; it is not a reproduction of a
published queueing-constrained estimator. Live-idle CPU includes the retained
control environment, and loaded-background additivity is an assumption.

V28 validation runs last 60 s, with low/high phases occupying two-thirds and
one-third of each cycle. The frozen accuracy tolerances are at most 3
percentage points of miss error and 5% capacity error in every trial. Capacity
error is assessed against the measured busy-capacity bounds. The stronger
advantage screen requires every block's improvement to be positive and the
four-block 95% interval lower bound to reach 1 percentage point. All sixteen
trials, including zero-miss cases, contribute. Intervals assume independent,
approximately normal block contrasts; there are four blocks, not thousands
of independent statistical replicates.

## 3. Results

### 3.1 Earlier prospective validation

V22's busy estimate was 152.47 jobs/s. It predicted 10.38% burst misses
against 10.97–11.92% observed; whole-run accounting predicted 44.05%. Even
arrivals had zero 500 ms misses despite approximately 14.8% higher whole-run
CPU/job. All twelve primary trial/contrast checks passed, with maximum error
1.55 percentage points.

| V23 job size | Burst cycle | Mean observed misses | Busy forecast | Whole-run forecast |
|---|---:|---:|---:|---:|
| Small | 3 s | 0.00% | 0.00% | 0.00% |
| Small | 12 s | 22.56% | 22.76% | 49.23% |
| Large | 3 s | 0.00% | 0.00% | 0.00% |
| Large | 12 s | 16.13% | 17.26% | 46.85% |

Each row summarizes four fresh trials. All sixteen trial checks and eight
paired-contrast checks passed; maximum error was 1.83 percentage points.
All 81,504 validation offers succeeded, with no responses exceeding one second.
These are late successful responses. Zero short-cycle misses does not imply
exact latency prediction or satisfaction of tighter deadlines.

### 3.2 Accounting evidence and sampler limitations

V25 completed sixteen diagnostic trials with no retry. Its eight native
recordings passed quality checks: 33,260 readings, no skipped slots, maximum
acquisition wall time 0.274 ms. All eight busy phases qualified; delivered CPU
bounds were approximately 0.4933–0.5067 CPU.

| V25 size | Whole-run capacity | Measured busy capacity | Underprediction |
|---|---:|---:|---:|
| Small | 138.82 jobs/s | 149.42 jobs/s | 7.09% |
| Large | 70.53 jobs/s | 75.06 jobs/s | 6.03% |

These descriptive values use four sampler-on runs per size. Whole-run cost
exceeded busy-window cost in all eight recordings. One conservative lower
bound was 4.997%, below the 5% screen; seven of eight met it. Matching CPU,
counts and duration is an accounting identity, not independent validation.

Deadline sampler comparability remains unresolved. Small-job off/on means
were 24.18%/22.65%, with opposite-order differences of −1.45/−1.60 percentage
points against a largest consecutive repeat difference of 0.62. Large-job
means were 21.58%/20.49%, with opposite-order differences of −2.28/+0.10 and
largest repeat difference 3.12. Neither causal sampler effects nor equivalence
are established. None of V25's eight intended low phases qualified: seven
had waiting-queue maxima above one and all eight had positive throttling upper
bounds. Later qualification does not change those outcomes.

### 3.3 Qualified low load and composition sensitivity

V26 qualified all four low windows: waiting queue at most one, bounded
throttled-period count zero, positive completions. All 2,700 measurement offers
succeeded with zero 500 ms misses; 10,233 native readings passed quality
checks. This establishes the measurement condition for steady sampler-on
traffic, without a busy arm or sampler-off comparison.

V27 generation-03 completed sixteen accepted runs without retries. All 68,736
measurement offers succeeded and all required mixed states qualified.
Doubling low arrivals from 15 to 30 jobs/s increased whole-run cost in every
one of the eight paired comparisons:

| Native sampler | Mean CPU/job increase | Model-based 95% interval |
|---|---:|---:|
| Off | 3.194% | [2.720%, 3.669%] |
| On | 3.419% | [2.989%, 3.849%] |

Busy capacity remained 149.167–150.333 jobs/s. Both busy-stability and
sampler-interaction screens passed. Both cost interval lower bounds fall
below the frozen 3% minimum; retain `composition_inconclusive`. The evidence
supports a directional composition effect in this service, without establishing
the required minimum magnitude. Cost/capacity interaction checks do not prove
deadline sampler neutrality or isolate why CPU/job changes.

### 3.4 Fresh comparison with idle and regression controls

V28 completed all 32 slots without retries; all 108,084 measurement offers
and 21,600 warmup offers succeeded. States, host controls and owned cleanup
passed. Every scientific run used the native sampler off. Forecasts sealed
13.912 s before the first validation attempt. Observed validation busy-capacity
bounds spanned 148.667–150.500 jobs/s.

| Frozen capacity input | Capacity jobs/s | Deadline MAE pp | Maximum deadline error pp | Maximum capacity error % | Deadline checks /16 | Capacity checks /16 |
|---|---:|---:|---:|---:|---:|---:|
| Whole-run CPU/job | 139.669 | 13.494 | 16.905 | 7.197 | 0 | 0 |
| Idle-corrected CPU/job | 139.743 | 13.471 | 16.810 | 7.148 | 0 | 0 |
| Busy capacity | 149.417 | 0.453 | 1.714 | 0.720 | 16 | 16 |
| Linear utilization–throughput regression | 125.953 | 31.314 | 37.929 | 16.311 | 0 | 0 |
| Quadratic utilization–throughput benchmark | 148.463 | 1.169 | 3.619 | 1.354 | 13 | 16 |

Busy meets every accuracy tolerance. Quadratic meets all capacity tolerances
and fails three deadline tolerances. The other inputs substantially overpredict
misses and fail every accuracy check. These outcomes describe the declared
fits and shared FIFO model, rather than the accuracy of CPU-based methods
in general.

Busy reduces quadratic's deadline error by a mean 0.716 percentage points,
with model-based 95% interval [0.086, 1.346]. All four block improvements are
positive, but the lower endpoint fails the required 1-point minimum. Retain
`predictive_advantage_inconclusive`. The interval includes 1 point, so it
also does not establish that the true improvement is below that target.
Advantages over whole, idle-corrected and linear inputs pass their frozen
screens. Both busy and quadratic predict zero misses in all eight 6 s trials.
The eight 12 s trials have descriptive MAEs of 0.906 and 2.337 points,
respectively; this subset does not replace the frozen all-trial comparison.

The two live-idle captures consume 7.668/8.056 ms CPU over approximately
30.11 s each. Mean idle rate is 0.000261092 CPU, or 0.0261% of one CPU.
The additive correction reduces mixed CPU/job by only 0.105% and increases
estimated capacity by 0.0739 jobs/s. That correction cannot repair the observed
gap. Loaded overhead remains unidentified. Steady calibration costs are
approximately 4.50–4.53 ms/job at 15/30 jobs/s and 3.679–3.691 at 120; all
ten steady runs have zero throttled periods and queue peak one. These are
cohort costs, not isolated SHA demand or a measured runtime mechanism.

## 4. Closest prior methods and contribution boundary

Load-dependent demand is established. Kumar, Zhang and Tantawi jointly infer
load-dependent service-demand and overhead functions from utilization and
mean response time using queueing relations and constrained optimization.
[Enhanced Inferencing, VALUETOOLS 2009](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799), §§2–3.
Zhang, Li and Zhou model demand as a polynomial of CPU utilization, combining
utilization-law constraints with soft mean-response bounds.
[Estimate Load-dependent Service Demand for Modern CPU, 2013](https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639), load-dependent estimation section, Eqs. 1–5.
V28 fits utilization directly as a function of throughput using CPU residuals;
neither published algorithm was reproduced or evaluated. Its quadratic curve
therefore supplies a useful nonlinear benchmark, not a result against those
algorithms. Their applicability requires explicit CPU units, scheduling and
response-time mappings; a fractional quota cannot simply be treated as a
continuously available processor in a queueing formula.

The Spinner et al. survey treats estimation assumptions and model mismatch
as central comparison issues; its author-hosted abstract documents evaluation
across load and monitoring conditions.
[Evaluating Approaches to Resource Demand Estimation, 2015](https://se.informatik.uni-wuerzburg.de/en/tools/librede/), 2015 publication entry.
Busy-period and burst-aware sizing also have precedents in
[Mi et al., JISA 2010](https://link.springer.com/article/10.1007/s13174-010-0012-9).
Aggregate utilization accounting is established in
[Casale et al., Middleware 2009](https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf), §3.1.
Reservation models use different isolated-demand and scheduling assumptions:
[Cucinotta et al., IEEE TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), §4.2.
Application periodicity and Linux bandwidth interfaces are adjacent prior art:
[Sampat et al., APSys 2025](https://tianyin.github.io/pub/kscaler.pdf), §§2–3.
Our observed substitution failure does not refute these models or establish a
kernel defect.

The defensible addition is a reproducible prospective case linking measurement
scope to deadline forecast error, together with adverse controls and a strong
nonlinear benchmark. A first-discovery claim, a new estimator and superiority
over applicable load-dependent methods remain unestablished. The targeted
[prior-method assessment](runtime_io_load_dependent_baseline_assessment_20261008.md)
explains this boundary; it is not an exhaustive novelty review.

## 5. Limits, failures and reproducibility

Generality is limited to two SHA sizes, the tested deterministic schedules,
one host and one quota. Other applications, quotas, mixed sizes, stochastic
traffic and hosts are untested. Aggregate CPU includes runtime, HTTP and
kernel work; phase boundaries can contain in-flight work. Counter/clock bounds
do not prove zero accounting lag. Frequency, cache and scheduling mechanisms
were not isolated. Good capacity-input predictions do not independently
validate the FIFO model for other deadlines or traffic distributions.

Earlier V24 generations stopped under their frozen timing/qualification rules.
V27 generation-01 failed because client clock anchors were absent;
generation-02 exhausted its retry with 79 monitor records against a minimum
80. Generation-03 used a separately frozen bounded monitor-lifetime repair.
Failed recordings remain failed. V23's report completed before its watchdog
interrupted final replay; subsequent verification passed without new collection.
Neither technical repairs nor software tests add scientific effects.

Saved artifacts retain exact offers, raw events, clock/counter brackets,
configuration and binary identities, forecast seals and cleanup receipts.
Separate result reviews provide the evidence for the tables:

- [V22 review](../analysis/runtime_io_v22_result_review/20261007/report.json) and [V23 review](../analysis/runtime_io_v23_result_review/20261007/report.json).
- [V25 review](../analysis/runtime_io_v25_result_review/20261007/report.json) and [V26 review](../analysis/runtime_io_v26_result_review/20261007/report.json).
- [V27 generation-03 review](../analysis/runtime_io_v27r3_result_review/20261008/report.json) and [V28 review](../analysis/runtime_io_v28_result_review/20261008/report.json).
- [V28 frozen protocol](runtime_io_v28_protocol.md) and [consolidation audit](../analysis/runtime_io_paper_consolidation_review/20261008/report.json).

Collection is stopped. This draft can proceed as a scoped empirical note;
stronger algorithmic or general claims require additional justified evidence,
not repetition until an existing threshold passes.
