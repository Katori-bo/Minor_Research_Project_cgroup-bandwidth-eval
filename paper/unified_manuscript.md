# From CPU Capacity to SLO Decisions: An Empirical Study of Deadline Forecasting Under Linux CPU Quotas

Evidence cutoff: 11 October 2026. Unified empirical manuscript. All completed
performance studies use one physical host; independent-host confirmation is
pending and excluded. Historical manuscripts and scientific contracts remain
unchanged. Supporting material contains the detailed investigation history.

## Abstract

When do calibrated performance forecasts support reliable deadline and service
level objective (SLO) decisions under Linux CPU quotas? We investigate this
question through a factorial latency study, prospective capacity and deadline
comparisons, ordinary calibration-transfer controls, and fresh decision
evaluations of a Go service and stock NGINX on one host. At a 500 ms deadline,
whole-run CPU/job substitution yields 13.494 percentage points of mean absolute
miss-fraction error, compared with 0.453 for backlogged throughput and 1.169
for a nonlinear CPU-based benchmark; the busy-versus-nonlinear advantage remains
inconclusive under its frozen minimum-effect criterion. Separate Go campaigns
show that periodic service improves a 25 ms comparison, while an empirical
timing reference improves a 10 ms comparison within a declared low-queue
domain. NGINX transfer controls include improvement without sufficient accuracy,
accuracy without supported incremental advantage, and failed five-deadline
panel gates. In fresh decision evaluations, the ordinary reference gives five
wrong primary-deadline assurances among eighteen Go windows and six among
eighteen NGINX windows. One Go window reproduces the fixed positive-slack
false-assurance event with error at most five points; NGINX does not reproduce
that narrow event. Sampling-only uncertainty procedures provide zero assurance
coverage at these primary deadlines. The contribution is quantitative evidence
linking calibration scope, deadline resolution, transfer, decision error and
acquisition cost for selected established procedures. It supplies neither a
new estimator nor a universal reliability rule or independent hardware confirmation.

## 1. Research question and contribution

A CPU allowance, an estimated processing rate, a deadline-miss forecast and an
SLO decision describe different properties. Their relationship matters when
an inexpensive calibration is used to assure compliance for later traffic.
We ask: **when do calibrated performance forecasts support reliable deadline
and SLO decisions for the tested CPU-quota-limited services?**

Our investigation follows four questions: whether an aggregate CPU estimate
represents backlogged capacity; whether average capacity preserves timing at
short deadlines; whether an empirical calibration transfers to later windows;
and whether the resulting numerical error permits useful compliance decisions.
Each question has its own experimental contract. The studies collectively
provide a case study, rather than one pooled test of a universal hypothesis.

The empirical contribution is the measured relationship among those four
questions, with credible ordinary controls and adverse outcomes retained.
Nonlinear CPU calibration recovers most of the accuracy lost by a simple
whole-run substitution. A favorable mean error at one deadline does not
establish adequacy at another. Matching nominal operating conditions sometimes
improves transfer, but can leave substantial error or offer no required advantage
over ordinary calibration. Finally, a forecast within a five-point error
allowance can still make a wrong decision when its slack below the miss budget
is smaller than its error. That arithmetic is elementary; the fresh finite-window
observations and remedy tradeoffs are the empirical result.

CPU-dependent demand estimation, periodic service, empirical tail profiling,
forecast classification and uncertainty-aware resource decisions all have prior
work. Section 6 identifies what each precedent already establishes. We make
no first-result claim, published-method superiority claim, causal explanation
of transfer failures, or assertion of a new predictor. Reproducibility improves
the credibility of the observations; it does not establish originality.

## 2. Apparatus, endpoints and evidence design

### 2.1 Services and resource contracts

The recorded physical host is an AMD Ryzen 5 5600H laptop with twelve logical
CPUs and approximately 16 GB RAM. The original matrix records Linux
7.2.6-arch2-1; later studies record 7.2.8-arch1-2 and stock Go 1.26.1. Versions,
boots, images, binaries and configurations remain campaign-specific. Service
work uses logical CPUs 2 and 4; client/control work uses 0 and 1. Recorded
topology separates service and control physical cores but does not reserve
them exclusively. Power and thermal checks reduce some variation without
establishing fixed frequency, stationarity or freedom from interference.

The Go HTTP service performs 44,000 or 88,000 SHA iterations per request, with
a waiting queue of 128 jobs. Later forecasting studies use one worker,
`GOMAXPROCS=1` and yielding disabled. The original worker experiment instead
uses one, two or four workers with `GOMAXPROCS=2`. Capacity comparisons include
50 ms CPU per 100 ms; tight-deadline and NGINX studies use 25 ms per 100 ms.
Burst credit is zero. Linux bandwidth control supplies a ceiling with
replenishment and allocation details, not a guaranteed continuously available
processor [1]. NGINX serves a retained 1 MiB body using gzip compression;
complete encoded-body reception and decoded-content integrity are checked.

Arrivals follow fixed open-loop schedules, independently of prior completion.
Warmup, measurement and drain are distinguished. The Go outcome includes
scheduled-offer-to-body-consumption-and-close time. NGINX timestamps complete
encoded-body receipt before close, decode and hash validation; integrity
failures count as unsuccessful offers. These endpoint differences prevent a
controlled application-effect interpretation of cross-service results.

### 2.2 Outcomes, chronology and statistical units

The original matrix measures each run's nearest-rank p99 among successful
requests and separately retains rejections and timeouts. Later deadline
studies count **all scheduled offers**: an unsuccessful offer, or a successful
offer whose completion duration exceeds deadline D, is a miss. Equality is
timely. Missing requests retain their denominator position. Partial or corrupt
decision windows remain unavailable rather than acquiring an imputed label.
Successful-request p99 and all-offer miss fractions are never pooled.

Deadline error is `100 * abs(forecast miss fraction - observed miss fraction)`
in percentage points (pp). Capacity comparisons use equal-trial means; later
campaigns use their frozen equal-profile/block means. Those scores differ
from pooling requests. Panel scores additionally take the worst cutoff within
the declared block construction. Their scale does not make them interchangeable.

Protocols, calibration and forecasts precede target outcomes in the prospective
comparisons. Methods discovered using earlier outcomes receive fresh confirmation
only under a later frozen contract. Screens designed after outcomes remain
development analyses even when their inputs were recorded before measurement.
The fresh decision studies were motivated by known historical results; their
new references and target forecasts were frozen before their own outcomes.
Local registration times and hashes are reproducibility records, rather than
independent timestamp attestations.

The capacity advantage interval uses four blocks. Tight-deadline and single-cutoff
transfer intervals use six blocks, normally `mean +/- 2.571 * SD / sqrt(6)`.
The panel uses two policy-specific conditional 97.5% intervals. These intervals
condition on frozen calibration and assume sufficiently independent, approximately
normal block summaries; sequential blocks do not establish those assumptions.
They do not propagate all calibration uncertainty. Requests, software checks
and multiple deadline labels are not additional host replications.

### 2.3 Procedures and acceptance criteria

Whole-run calibration divides CPU allowance by mean per-run cgroup CPU/completed
job. Busy calibration measures completion throughput in fixed, eligible
backlogged windows. Idle correction subtracts an independently measured
zero-request CPU rate. Linear and quadratic benchmarks fit utilization against
completion throughput and solve for capacity at the allowance. Every V28
capacity estimate supplies the same finite constant-service FIFO model.
Regression uses twelve idle/steady observations, while direct estimates use
four mixed runs; this is not an equal-cost comparison. The quadratic root
extrapolates to 1.269 times maximum measured throughput.

The periodic approximation replaces continuous speed by a single replenishing
global budget, using effective demand inferred from busy capacity and a
calibrated response-delay distribution. It averages 100 shared phases at
1 ms spacing with full initial credit. This is a phase assumption, not a
measured kernel phase, and omits CPU-local runtime and competing service threads.
The Go empirical timing reference uses calibration `R = complete response -
observed queue wait`. Target outcomes retain queue wait. A complete-response
CDF is an important ordinary control. NGINX uses complete-response CDFs, with
policy/rate matching evaluated under separate campaigns.

V28 requires per-trial deadline error at most 3 pp and capacity error at most
5%. Busy advantage requires every block to improve and the conditional 95%
lower bound to reach 1 pp. V30 and V31 require mean error at most 3 pp,
all-block improvement and an improvement lower bound at least 5 pp, alongside
their frozen domain and decision checks. NGINX single-cutoff and panel accuracy
require the declared error-interval upper bound at most 5 pp. The fresh policy
and rate controls separately require mean gain at least 2 pp and its interval
lower bound above zero. Failed gates are retained without interpreting them
as population impossibility. These are engineering references, not universal SLOs.

## 3. Capacity and deadline adequacy

### 3.1 Period, concurrency and arrivals provide the foundation

The original randomized matrix crosses four periods (10, 50, 100 and 250 ms)
at 0.5 CPU and an unlimited comparison, three worker counts, two loads and
two arrival patterns, with five repetitions: 300 trials. It acquires 1,618,350
scheduled requests: 1,595,274 successes, 23,059 queue rejections and seventeen
timeouts. High-burst mean run p99 spans approximately 479–4303 ms across capped
conditions, compared with approximately 6.46 ms unlimited. Increasing period
reduces high-burst p99 most clearly with one or two workers; the relationship
is not monotonic across all worker counts. The unlimited case has greater
bandwidth and is not another 0.5-CPU allocation. The finding motivates joint
measurement of period, workers, load and arrivals; it supplies no universally
optimal period. Complete factorial tables and exploratory corrected contrasts
are retained in supporting material S1.

### 3.2 Credible nonlinear calibration limits the capacity claim

The final prospective capacity comparison (artifact V28) has sixteen fresh
calibration and sixteen validation trials at a 500 ms deadline. All 108,084
measurement offers and 21,600 warmup offers succeed. Forecasts freeze before
validation; native sampler collection is off.

| Capacity input | Capacity requests/s | Deadline MAE (pp) | Deadline checks /16 | Capacity checks /16 |
|---|---:|---:|---:|---:|
| Whole-run CPU/job | 139.669 | 13.494 | 0 | 0 |
| Idle-corrected CPU/job | 139.743 | 13.471 | 0 | 0 |
| Busy throughput | 149.417 | 0.453 | 16 | 16 |
| Linear CPU fit | 125.953 | 31.314 | 0 | 0 |
| Quadratic CPU fit | 148.463 | 1.169 | 13 | 16 |

Busy improves on quadratic by 0.716 pp, with conditional 95% interval
[0.086, 1.346]. All blocks improve, but the lower bound fails the frozen
1 pp advantage requirement. The verdict remains inconclusive; equivalence
is also unestablished. Dedicated idle correction barely changes the substitution.
Earlier prospective work spans two work sizes and two burst timescales. Four
V29 conditions crossing 25%/50% CPU and both sizes give busy-model 500 ms MAEs
of 0.479, 1.359, 0.672 and 1.295 pp. These are within-service extensions,
not independent hardware replication. Composition remains inconclusive under
its separate minimum-effect screen.

The result concerns the tested aggregate substitution. Load-dependent demand
estimation is established [2,3], and the nonlinear control recovers most of
the lost accuracy. Neither busy calibration's general superiority over CPU
methods nor a physical cause of the aggregate discrepancy follows.

### 3.3 Short deadlines change which approximation is adequate

Separate fresh campaigns test a 25/100 ms quota with 88,000-iteration jobs.
Each has sixteen calibration and eighteen validation trials in six blocks.

| Campaign and endpoint | Tested reference MAE (pp) | Comparator MAE (pp) | Frozen result |
|---|---:|---:|---|
| Go, 25 ms (V30) | Periodic + delay: 2.341 | Constant-rate busy FIFO: 73.599 | Gates pass |
| Go, 10 ms (V31) | Queue-adjusted CDF: 1.844 | Periodic + delay: 67.340 | Gates pass within observed low-queue domain |

At 25 ms, the continuous-speed comparator assigns each job 28.640 ms and
therefore predicts all misses even without queueing. The large contrast partly
reflects this imposed floor; it is not a competitive published tail model.
Periodic+delay correctly classifies all eighteen trials against the 5% miss
budget, with conditional improvement interval [68.900, 73.615] pp. However,
its burst-only MAE is 7.024 pp and maximum trial error is 12.097 pp. Mean-gate
success does not imply uniform accuracy or fine discrimination near the budget.
Secondary cutoff comparisons and the nonmonotone discovery switch remain S2.

The 10 ms empirical reference was developed after V30 outcomes and confirmed
only in V31's fresh study at 5, 11 and 19 offers/s. All eighteen targets satisfy
the declared domain: zero recorded measurement throttling and at least 99%
of offers with observed worker-queue wait at most 100 us. The improvement
interval is [63.925, 67.065] pp. An ordinary complete-response CDF, selected
as a retrospective control, has almost identical 1.802 pp MAE. Queue subtraction
and stage decomposition are therefore not demonstrated necessities. The CDF
has no overload mechanism: it predicts zero misses at 25 ms on the earlier
burst profile, where observed mean misses are 79.203%. Domain checks made on
target observations do not establish an advance model-selection rule.

## 4. Calibration transfer and ordinary controls

The NGINX studies use the same host and quota as the tight Go studies, but
different workload, completion checks, calibration inputs and domains. The
first three campaigns retain the original 20.565395 ms cutoff; the fourth
uses fresh policy-specific calibration-only deadline panels. Their chronology
and failed attempts are preserved; later accurate transfer does not identify
or repair the cause of an earlier failure.

| NGINX campaign | Main error score (pp) | Ordinary comparator (pp) | Original gate outcome |
|---|---:|---:|---|
| Original response-CDF transfer | 5.981 | No head-to-head primary comparator | Accuracy unsupported |
| Assigned-policy matching | 15.708 | Pooled policies: 24.729 | Gain supported; accuracy unsupported |
| Fixed-policy rate matching | 1.194 | Shared 5/s reference: 1.972 | Accuracy supported; extra advantage unsupported |
| Fresh panel, policy P0 | 6.611 | Pooled panel: 44.111 | Accuracy unsupported |
| Fresh panel, policy P1 | 4.889 | Pooled panel: 38.222 | Accuracy unsupported |

The original error interval is [1.321, 10.642] pp. The policy-matched accuracy
interval is [12.695, 18.721] pp despite improved performance against pooling.
Pooled policies intentionally mix assignments; this easy comparator does not
establish published-method superiority. In the later rate study, matched and
ordinary references both pass accuracy. The 0.778 pp gain interval
[-0.375, 1.931] fails the required incremental advantage. Two small measurement
throttling observations remain included under its all-offer contract.

The fresh panel's policy-specific conditional 97.5% intervals are
[1.831, 11.391] pp for P0 and [2.620, 7.158] for P1. Both fail the upper-bound
criterion; P1's mean below five does not pass its uncertainty gate. At the older
deadline, P1 forecasts and observes zero misses, while its panel cohort/cutoff
error reaches 11 pp. One P0 panel cohort records a throttled period and remains
included. Good performance at a saturated cutoff supplies little evidence
about more discriminating cutoffs.

Later saved-data guards and updates are development screens. A continuous
probe lowers an older power-study average, yet an agreeing probe still precedes
31.5 pp error. A median correction improves one history and worsens others.
Neither becomes a prospectively validated reliable-transfer selector. A
worker-wait observer fails behavioral-equivalence qualification through wide
intervals; it is neither demonstrated harmful nor qualified. Longer-warmup
precision geometry exceeds the declared budget, and execution-rate collection
remains an unmeasured proposal. Their full costs and limits are S4–S5.

## 5. Prospective SLO decision reliability

### 5.1 Frozen question, ordinary comparisons and information barrier

We use an illustrative fixed miss budget of 5%. The primary deadline is the
fresh calibration q97.5, selected by the frozen nearest-rank rule; secondary
quantiles and historical fixed deadlines are retained separately. The primary
event requires the ordinary reference to predict below the budget with
strictly positive slack, the target window to exceed the budget, and absolute
forecast error to be at most 5 pp. Calibration-quantile deadlines and this
budget are standardized stress tests, not externally supplied production SLOs.

Three point procedures share available information: the frozen complete-response
reference, the recent 25 warmup offers, and a sample-size-weighted update.
Calibration seals precede target warmups; validated warmup/drain, durable
forecast and permit precede target child creation. Barrier delay and preparation
are charged to the actual acquisition ledger. This does not demonstrate
behavioral equivalence with historical collectors.

Ordinary two-sided 95% DKW procedures classify as meets only when the sampling
upper bound is at most the budget, exceeds only when the lower bound is greater,
and otherwise abstain. With IID sampling the radius is
`sqrt(log(2/0.05)/(2*n))`; independence/stationarity are not established for
these windows. The bands describe sampling uncertainty for their reference
distribution and do not bound unmodeled transfer to a future window. The
weighted procedure's registered construction remains an ordinary comparison,
not a new uncertainty estimator. All procedures retain unsuccessful-offer mass.

### 5.2 Separate fresh Go and NGINX results

The local Go supplement completes eighteen primary-domain windows. At the
10,497,189 ns primary deadline, its 676-offer reference predicts 16/676 misses
(2.3669%). Window `v31_b3_A` at 5/s has 19/300 misses (6.3333%), a 3.9665 pp
error. It reproduces the positive-slack small-error event in one window.
Four additional wrong assurances have errors above the narrow event allowance.

The separate NGINX completion study also completes eighteen primary-domain
windows. Its 21,330,991 ns cutoff gives a 40/1600 (2.5%) reference forecast.
Six windows exceed the budget, with errors 23.1667–58.5 pp. Thus the narrow
primary event occurs **zero times**: `not_reproduced_in_available_windows`.
Larger forecast-transfer failures are observed, but cannot substitute for
that negative primary result. Go and NGINX are not pooled into one primary test.

| Service / point procedure | Meets /18 | Wrong assurances | Unnecessary rejections | Observed compliant |
|---|---:|---:|---:|---:|
| Go / reference | 18 | 5 | 0 | 13 |
| Go / recent 25 | 15 | 4 | 2 | 13 |
| Go / weighted update | 18 | 5 | 0 | 13 |
| NGINX / reference | 18 | 6 | 0 | 12 |
| NGINX / recent 25 | 12 | 2 | 2 | 12 |
| NGINX / weighted update | 18 | 6 | 0 | 12 |

Every point procedure answers all eighteen completed windows. Recent-only
updating trades fewer observed wrong assurances for some unnecessary rejections;
it is not a selected winner or a general guarantee. Wrong-assurance-per-assurance
denominators are the meets counts, while unnecessary-rejection denominators are
the observed-compliant counts. Counts describe these episodes, not population rates.

All three Go DKW procedures abstain in every primary-deadline window. NGINX
reference and weighted DKW likewise abstain in all eighteen; recent-25 DKW
abstains in fifteen and rejects three, including one unnecessary rejection.
Every DKW procedure has zero meets assurances and zero assurance coverage.
Its false-assurance-per-assurance denominator is therefore undefined. Zero
answers cannot demonstrate useful safety or zero risk. Full joint tables for
all endpoints, views and planned denominators are retained in S6.

### 5.3 Availability, acquisition cost and independent confirmation

Go acquires 29,932 declared offers across functional, calibration, warmup and
target phases and takes 9,652.677 s (about 2 h 41 min). Only 676 selected
calibration offers feed its reference; they do not replace the acquisition
cost of the enclosing study. The completed NGINX campaign acquires 7,925 offers
and takes 1,755.700 s (29 min 16 s). Its separately recorded image setup and
readiness costs are 0.470 and 75.524 s. Preparatory acquisitions already in a
campaign ledger are not added again.

Two original local decision allocations failed before target collection and
retain 36 unavailable slots. The Go supplement's NGINX allocation failed at
authentication and retains eighteen more unavailable slots. Its later NGINX
completion is a separately frozen eighteen-slot study, not a replacement.
The original 72-slot plan, 36-slot supplement and eighteen-slot completion
give a 126-slot attempt ledger: 36 completed, 54 closed unavailable and 36
pending independent Intel slots. These totals describe availability and
provenance, not a pooled event denominator. Costs from stopped attempts remain
reported separately in S6.

No independent-host result has been received. Two distinct Intel contracts
are prepared: original V31 replication at 10 ms, and a fresh Go/NGINX decision
evaluation. Successful V31 would confirm only its registered forecast/domain
question, including its predeclared complete-response secondary control; it
would not confirm the new q97.5 decision endpoint or NGINX. Independent
decision evidence requires fresh pre-outcome references and barriers under
its own contract. No same-host repeat can supply that missing hardware scope.

## 6. Claim-specific comparison with prior work

Our interpretation of the closest precedents is summarized below. None of
their complete systems was executed here. Differences in workload or CPU
contract alone do not prove novelty; the surviving claim is a scoped empirical
case connecting measured adequacy to decisions and cost.

| Claim examined here | Established precedent | Additional evidence and retained limit |
|---|---|---|
| Calibration scope changes forecast accuracy | Enhanced Inferencing [2] and load-dependent demand estimation [3] | Fresh shared-FIFO comparison with an effective nonlinear control; no new demand estimator |
| Average speed loses short-deadline information | Periodic-server latency analysis [4]; reservation approximation [5] | Quantified 25 ms and 10 ms contrasts under a Linux ceiling; no new periodic theory or universal deadline/period boundary |
| Calibration transfer and SLO robustness matter | Galileo/PERC [6]; CEDULE [7] | Failed and successful ordinary policy/rate controls with original gates; no refutation of their richer models |
| Numerical forecasting and decision quality differ | SuanMing [8]; Sinan [9] | Fresh all-offer finite-window labels, positive slack, wrong assurances, rejections and unavailable cells; classification evaluation is established |
| Conservative answers need useful coverage | RScale [10]; MPORA [11]; nonexchangeable conformal inference [12] | Measured sampling-only/update tradeoffs and costs; no new predictive guarantee or impossibility theorem |

Galileo/PERC explicitly addresses environmental perturbations and controller
consequences, while SuanMing already reports regression and confusion metrics.
Sinan separates near-term latency prediction from longer-horizon QoS-violation
prediction. These precedents rule out broad claims to discover prediction
fragility or forecast/decision divergence [6,8,9]. Our result remains an
incremental empirical contribution candidate; originality and peer-review
acceptance are unestablished. The expanded claim register in S7 supplies
source locators, access limits and explicit nonclaims.

## 7. Implications and validity limits

For these procedures, calibration should be evaluated against the actual
deadline and decision margin. A capacity check tests a service-rate input;
a deadline check tests a response distribution at a cutoff; an SLO check tests
which side of a budget the future window occupies. Useful remedy evaluation
must jointly retain wrong assurances, unnecessary rejections, abstention,
availability and full acquisition cost. Improvements against an intentionally
mixed or structurally weak comparator warrant that restricted interpretation.

All observed scientific performance evidence comes from one laptop and two
services. SHA work-size changes, fresh containers, many requests and successful
software replays do not supply hardware independence. Traffic is deterministic
and limited; production distributions, rare-tail guarantees, mixed workloads
and externally chosen SLOs are untested. Queue-based domain checks are observed
conditions, rather than validated advance selectors. Blocks and windows share
calibration and a host; conditional intervals and descriptive decision counts
do not certify population risk.

Quota, runtime, scheduling, HTTP and execution-cost effects remain entangled.
Unthrottled failures do not identify a frequency cause, and assigned-policy
contrasts do not explain historical excursions. Observer equivalence,
distributional assumptions and counter-to-response mappings remain unresolved.
Known-outcome development screens cannot be promoted to confirmation. No
complete published competitor was reproduced under matched information,
endpoint, cost and applicability conditions.

These limitations restrict the paper to an auditable empirical study. They
do not require another local predictor search to report the completed findings.
Independent evidence is an explicitly outstanding confirmation item; the
present claims exclude it.

## 8. Reproducibility and conclusion

The [supporting material](unified_supporting_material.md) indexes the original
matrix, all core result records, adverse investigations, costs and attempt
ledger. The [reproduction guide](unified_reproducibility.md) distinguishes
document consistency, numerical decision replay, preserved historical checks
and full raw/resource replay. Scientific gates, raw outcomes and historical
seals are retained unchanged. Local artifacts and checksums do not constitute
an independent attestation or a public release.

The completed observations trace a scoped progression from capacity calibration
to deadline adequacy, transfer and SLO decisions. Nonlinear calibration narrows
the initial busy-throughput advantage; short-deadline results depend on the
chosen approximation and observed domain; nominal matching supplies mixed
transfer outcomes; and fresh decision tests show both an observed small-error
false assurance in Go and non-reproduction of that narrow event in NGINX.
Ordinary updates and sampling bands do not establish an affordable reliable
assurance rule in these episodes. The contribution is the measured progression
and its preserved limits, rather than a new estimator or general deployment rule.

## References

1. Linux Kernel Contributors. CFS Bandwidth Control. [Kernel documentation](https://docs.kernel.org/scheduler/sched-bwc.html).
2. D. Kumar, L. Zhang and A. Tantawi. Enhanced Inferencing: Estimation of a Workload Dependent Performance Model. VALUETOOLS 2009. [Primary paper](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799).
3. Z. Zhang, S. Li and J. Zhou. Estimate Load-dependent Service Demand for Modern CPU. Information Technology Journal, 2013. [Publisher full text](https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639).
4. H. Li, C. Lu and C. Gill. Predicting Latency Distributions of Aperiodic Time-Critical Services. RTSS 2019. [Author paper](https://www.cse.wustl.edu/~cdgill/publications/rtss19.pdf). Direct retrieval unavailable in this final pass; retained primary-source review limits apply.
5. T. Cucinotta et al. Strong Temporal Isolation Among Containers in OpenStack for NFV Services. IEEE TCC, 2023. [Author paper](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf).
6. D. Saxena et al. Towards Performance Robustness for Microservices. NSDI 2026. [Proceedings paper](https://www.usenix.org/system/files/nsdi26-saxena.pdf).
7. A. Ali et al. CEDULE: A Scheduling Framework for Burstable Performance in Cloud Computing. ICAC 2018. [Author paper](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf).
8. J. Grohmann et al. SuanMing: Explainable Prediction of Performance Degradations in Microservice Applications. ICPE 2021. [Proceedings paper](https://research.spec.org/icpe_proceedings/2021/proceedings/p165.pdf).
9. Y. Zhang et al. Sinan: ML-Based and QoS-Aware Resource Management for Cloud Microservices. ASPLOS 2021. [Author paper](https://people.csail.mit.edu/delimitrou/papers/2021.asplos.sinan.pdf).
10. P. Kang and P. Lama. Robust Resource Scaling of Containerized Microservices with Probabilistic Machine Learning (RScale). UCC 2020. [Author paper](https://www.cs.utsa.edu/~plama/papers/UCC20.pdf).
11. A. Eisenklam et al. Uncertainty-Aware Resource Allocation for Multi-Path Programs with In-Kernel Predictions. ECRTS 2026. [Proceedings full text](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html).
12. R. F. Barber et al. Conformal Prediction Beyond Exchangeability. [Author manuscript](https://arxiv.org/html/2202.13415v4).
