# Deadline Resolution and Traffic State in Capacity-Based Forecasts Under a Fractional CPU Quota

Working extension draft, updated 10 October 2026. This manuscript separates completed
prospective evidence from subsequent exploratory model development. V1 and all
frozen study sources remain preserved. V31 now supplies fresh prospective
confirmation of the empirical-latency comparison in its declared low-queue
domain. A subsequent NGINX complete-response study did not meet its declared
accuracy criterion. Related-work coverage is targeted rather than an exhaustive
novelty review; scientific originality remains unestablished.

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
points of error, but fails on burst traffic. A separately calibrated prospective
confirmation at new steady rates 5/11/19 requests/s yields 1.844 points of
10 ms error for this empirical reference and 67.340 for the periodic model,
with all eighteen trials inside the declared unthrottled, low-queue domain.
A subsequent stock-NGINX study uses a different complete-response endpoint,
including waiting. Its independently calibrated CDF has 5.981 points of
primary error and does not meet the declared conditional upper-interval
criterion of <=5 points. Together these results provide a reproducible,
scoped empirical account of predictive adequacy and transfer limits. They
establish no new estimator, causal phase explanation or universal correction.

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

There are five distinct evidence stages:

1. The retained V1 and V29 studies establish scoped capacity and long-deadline
   evidence with independently calibrated inputs.
2. V30 prospectively confirms a particular 25 ms prediction/decision contrast
   on fresh traffic patterns, after the ordinary timing approximation was
   developed using V29 discovery data.
3. The new empirical latency-CDF comparison is retrospective development
   prompted by V30's 10 ms failure. Its parameters use calibration records,
   but its method was chosen after validation outcomes; it is not another
   prospective result.
4. V31 prospectively confirms the predeclared paired calibration CDF at 10 ms
   using fresh calibration and eighteen trials at new steady rates. The V30
   exploratory evidence remains discovery; V31 has its own sealed predictions,
   technical qualification, domain checks and confirmation gates.
5. A separate stock-NGINX campaign tests a newly scoped complete-response CDF
   forecast and does not meet its primary accuracy criterion. It shares the
   physical host but not V31's internal-queue estimand or model comparison.

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
modeling. V31 below tests prospective accuracy within a declared low-queue
domain. An advance scope-selection rule for deployment still requires testing.

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

## 9. Prospective low-queue 10 ms confirmation

V31 retains V30's service, quota, request work, binaries, controls and clock
joins, while independently repeating all sixteen calibration trials. Four
fresh low-rate calibration cohorts supply 676 successful queue<=100 us timing
samples (113/225/225/113). The paired CDF preserves worker/residual dependence;
all methods and per-offer probabilities across eleven declared deadlines are
sealed before the first validation trial. No V30 outcomes or historical
software-fixture parameters enter the V31 fit.

Eighteen trials use steady rates 5, 11 and 19 requests/s, six blocks in the
retained counterbalanced orders, 20 s warmup and 60 s measurement. There are
12600 measurement offers. The scientific domain is zero recorded measurement
throttled periods and at least 99% of all offered requests with an observed
worker queue interval <=100 us. Domain exits must remain adverse results,
without replacement. These are operational limits checked on observations,
not proof of exclusive CPU service or an advance classifier of traffic state.

All eighteen trials are technically qualified and inside this domain. All
offers complete successfully; the smallest trial low-queue fraction is 99.825%.
All 34 scientific trials complete without a technical retry. Full completion
replay and separate calculations from raw client/server records reproduce
calibration pairing, all-offer outcomes, domain fractions and block contrasts.

| Validation profile | Rate requests/s | Mean observed 10 ms miss % | Paired-CDF forecast % | Paired-CDF MAE pp |
|---|---:|---:|---:|---:|
| A | 5 | 68.611 | 67.160 | 1.891 |
| B | 11 | 68.106 | 67.160 | 1.212 |
| C | 19 | 65.746 | 67.160 | 2.430 |

The primary equal-profile/block mean absolute error is 1.844 pp for the paired
CDF and 67.340 pp for periodic+delay. All six blocks improve. Mean paired
improvement is 65.495 pp, with the declared six-block 95% t interval
[63.925,67.065] pp (df=5, multiplier 2.571). Every frozen confirmation gate
passes, including the <=3 pp mean block CDF error and >=5 pp lower improvement
endpoint. Maximum individual CDF trial error is 5.055 pp; the mean accuracy
gate is not an individual-trial error guarantee.

The CDF predicts the <=5%/>5% decision correctly in all eighteen trials at both
10 and 12 ms. All trials fail the miss budget at 10 ms; all have zero observed
misses at 12 ms. This confirms decisions well separated from the miss-budget
boundary. It does not establish precision near 5% or a rate-selection method.
At 12 ms the periodic forecast also has zero error; that endpoint adds no
comparative accuracy discrimination. Zero observed misses do not guarantee
zero future misses.

| Deadline ms | Paired-CDF MAE pp | Independent worker/residual convolution MAE pp | Periodic+delay MAE pp |
|---:|---:|---:|---:|
| 9 | 1.940 | 1.180 | 69.519 |
| 9.5 | 1.738 | 2.811 | 77.478 |
| 10 (primary) | 1.844 | 7.585 | 67.340 |
| 10.5 | 3.852 | 4.645 | 24.838 |
| 11 | 0.607 | 0.628 | 2.243 |
| 12 | 0.000 | 0.113 | 0.000 |

At the primary endpoint, median worker plus empirical response residual has
8.104 pp error; fluid busy and fluid quadratic each have 32.512 pp error.
The fixed-zero-phase/no-added-delay diagnostic has 67.488 pp error. These
secondary comparator contrasts are descriptive. Pairing's advantage at 10 ms
does not extend to every endpoint: the independent convolution is better at
9 ms, and paired-CDF error rises to 3.852 pp at 10.5 ms. The 3 pp primary gate
was never a gate across the deadline grid. Both CDF and periodic forecasts
have zero error at 12/20/25/50/100/500 ms in this study.

Cohort-only CDF 10 ms predictions range from 57.522% to 69.912%. Leaving each
calibration cohort out gives 1.974–2.268 pp validation error. This sensitivity
is descriptive and does not alter the frozen pooled fit. Four calibration
trials and six validation blocks remain the experiment-level evidence; the
676 samples and 12600 offers are not additional independent replicates.

There are 8429 observed 10 ms misses: 4813 with computation certainly after
the deadline, 2264 certainly within despite the client miss, and 1352
clock-boundary ambiguous. At 11 ms, the corresponding counts are 279 misses,
12 certainly after, 233 certainly within and 34 ambiguous. These counts
conserve all misses and retain timing uncertainty, without causal attribution
to CPU demand, quota phase, descheduling or HTTP delay.

## 10. Interpretation and remaining scope

The evidence documents scoped differences in predictive adequacy. Average busy
capacity supports retained long-deadline forecasts; ordinary periodic service
repairs a confirmed 25 ms operating-condition contrast; near the 10 ms response
transition, the effective-demand approximation misses measured job-level
timing that a simple empirical calibration reference captures in discovery
and V31 prospectively confirms within its declared low-queue domain.
Traffic state matters alongside deadline resolution. This is not a theorem
that one particular ratio D/P determines the correct model.

V31 establishes a scoped fresh confirmation; V30's empirical-CDF burst failure
remains negative evidence outside that scope. The observed domain checks do
not constitute an advance rule for choosing a model before traffic runs.
The subsequent stock-NGINX complete-response study did not meet its declared
accuracy criterion (Section 12). This supplies negative evidence for that newly
scoped application-transfer question; it does not test the same queue-adjusted
paired-stage comparator. Independent host transfer and qualified mechanism
measurements remain subsequent scope extensions. Further within-service sweeps
would not supply that missing hardware evidence. Consolidating both the scoped
confirmation and the transfer limit yields an empirical contribution candidate.
The targeted prior-work review in Section 13 finds the underlying methods
established; it does not certify originality of the precise empirical result.

## 11. Reproducibility and evidence map

| Result or claim | Local evidence | Status |
|---|---|---|
| V1 capacity comparison | `paper/capacity_calibration_empirical.md` and V28 sealed reports | Completed prospective study |
| Four V29 conditions | `analysis/runtime_io_v29_result_review/20261009-complete-matrix/report.json` | Combined independently verified complete records |
| Model development before V30 | `analysis/runtime_io_v2_extension/20261009-v29-ordinary-models/report.json` | V29 discovery |
| V30 primary confirmation | `analysis/runtime_io_v30/generation-01/analysis/1791534266682067738/report.json` | Fresh prospective validation |
| V30 audit and limits | `analysis/runtime_io_v30_result_review/20261009-generation01/report.json` | Independent completion replay and descriptive audit |
| Empirical timing reference | `analysis/runtime_io_v2_extension/20261009-v30-timing-boundary/report.json` | Post-V30 discovery; not confirmed |
| V31 runner preparation | `analysis/runtime_io_v31_preparation_review/20261009-generation01/report.json` | Offline qualification; runtime gates subsequently passed |
| V31 primary confirmation | `analysis/runtime_io_v31/generation-01/analysis/1791544686930410674/report.json` | Fresh prospective low-queue 10 ms confirmation |
| V31 completion and scope audit | `analysis/runtime_io_v31_result_review/20261009-generation01/report.json` | Independent completion replay, raw-outcome/block checks and descriptive audit |
| Stock NGINX measurement suitability | `analysis/runtime_io_nginx_qualification_review/20261009-generation02/report.json` | Qualified full-response measurement; internal queue unobserved |
| NGINX complete-response transfer | `analysis/runtime_io_nginx_prediction_result_review/20261009-generation01/report.json` | Completed prospective campaign; primary accuracy criterion not supported |
| NGINX saved-evidence diagnosis | `analysis/runtime_io_nginx_prediction_diagnosis/20261010-generation01/report.json` | Post-hoc timing decomposition and stationarity limits; cause unresolved |
| Focused prior-work review | `docs/runtime_io_deadline_boundary_prior_work_review_20261010.md` and its dated source register | Targeted primary-source comparison; novelty remains unestablished |

Per-offer forecasts, raw client/server stages, input hashes, immutable source
snapshots and result seals remain available. Five new numerical checks verify
empirical boundary counting, convolution, calibration leakage rejection and
stage-count conservation. They complement the retained independent periodic
slot-oracle tests and full completion replay; software checks are not empirical
replicates.

## 12. Subsequent NGINX application-transfer limit

A separately sealed prospective study tests stock NGINX 1.30.5 dynamic gzip
compression of a fixed 1 MiB corpus on the same physical host. The application,
native runtime, single event-loop worker, CPU-2 affinity and 25 ms/100 ms quota
are pinned, with zero configured burst. Unlike V31, internal queue wait is
unobserved: the predictor uses complete scheduled-offer-to-body-receipt latency,
including all waiting. No queue subtraction or paired-stage periodic/residual
comparator is imported. This is a new application-transfer question, not an
exact replication of V31's model comparison.

Three fresh new-rate qualification cohorts precede four 400-offer calibration
cohorts at 5 requests/s. The lower pooled calibration median, 20,565,395 ns,
defines the primary deadline. The empirical CDF predicts 50% misses at that
deadline. The calibration, deadline, CDF and forecasts are sealed before the
eighteen 300-offer held-out cohorts at 4, approximately 6 and 8 requests/s,
ordered in six balanced blocks. Qualification observations are excluded from
the scientific fit and validation. All 1,600 calibration and 5,400 validation
offers are correct; measurement throttle increments are zero in every cohort.
Dispatch, runtime identity, process/thread stability, request accounting,
observer inventory, owned cleanup and full raw replay pass. The campaign
completes without a technical or applicability exit in 29 minutes 2.660 seconds.

| Validation rate requests/s | Mean observed primary miss % | Frozen forecast % | MAE pp |
|---:|---:|---:|---:|
| 4 | 48.833 | 50.000 | 1.389 |
| approximately 6 | 52.611 | 50.000 | 10.167 |
| 8 | 43.611 | 50.000 | 6.389 |

Primary mean block absolute error is 5.981481 pp. The declared conditional,
model-based six-block 95% t interval is [1.320988, 10.641975] pp; the required
upper endpoint is <=5 pp. The accuracy criterion is not supported. The interval
conditions on the finite frozen forecast and assumes approximately independent
normal block means. It does not propagate calibration uncertainty or establish
that unknown population mean error exceeds five points.

All six 8-requests/s cohorts have 41.000–46.667% misses, below the 50% forecast.
The approximately-6-requests/s cohort in block 2 has 88.333% misses, giving
38.333 pp error, and remains included. Its median full-response time is
21.438653 ms, with median dispatch lag 0.541647 ms and median dispatch-to-full-
body interval 20.857623 ms. That latter interval includes server waiting,
compression and delivery and is not an identified processing stage. Saved
records do not establish a scheduler, quota-phase or internal-queue cause.

Fresh calibration cohort miss fractions at the pooled deadline are 44.500%,
56.250%, 48.500% and 50.750%; medians span 20.510439–20.621183 ms. This
observed cohort variation limits a stationarity claim near the steep response
transition. Predeclared cohort-probability sensitivity MAEs are 5.296–11.463 pp,
reported descriptively without changing the pooled forecast. At the fixed
secondary 10 ms deadline all validation offers miss; at 25 and 50 ms there
are zero observed misses. These secondary matches do not replace the failed
primary endpoint or guarantee zero future misses.

This completed experiment adds a negative boundary result to the extension:
zero recorded measurement throttling and successful apparatus checks were
insufficient to ensure the declared accuracy of a rate-invariant complete-
response empirical forecast in this NGINX campaign. It does not invalidate
V31's confirmation within its different observed low-queue domain. Neither
new-algorithm novelty, causal mechanism nor independent-host reproduction is
established. Preserve the primary result and inspect saved evidence before
any separately justified prospective follow-up; no trial removal, deadline
substitution, gate relaxation or replacement collection is part of this result.

A subsequent exploratory diagnosis uses only these sealed records. The
block-2 excursion's first 30 offers have 56.667% misses; its remaining 270
have 91.852%, showing persistence within the measurement window. Relative
to the other five same-rate cohorts, mean full response increases by 1.275873
ms: dispatch lag changes by -0.035438 ms, dispatch-to-headers by +0.189690 ms,
and headers-to-full-body by +1.121621 ms. About 87.9% of the extra mean duration
therefore occurs after headers. These are observed client milestone intervals,
not identified server stages. Encoded response bytes/hashes are identical
across all 7,300 campaign measurement offers, and client response windows do
not overlap. Aggregate CPU per offer does not uniquely identify the excursion:
two other same-rate cohorts have comparable or higher average CPU use without
its large miss fraction.

At diagnostic deadlines 100 us below and above the frozen primary deadline,
the pooled calibration miss fractions are 57.750% and 41.625%. This steep
region makes small duration shifts consequential; these post-hoc offsets do
not replace the primary endpoint. Internal request-stage CPU/queue timings,
scheduler traces, client GC timing, frequency/thermal timelines and exact
quota phase were not recorded, so finer causal attribution remains unavailable.
The separate diagnosis report and per-request milestone CSV retain all offers
and explicitly distinguish these exploratory observations from confirmation.

## 13. Focused related work and contribution positioning

Periodic-server response-distribution modeling predates this extension.
[Li, Lu and Gill (RTSS 2019)](https://www.cse.wustl.edu/~cdgill/publications/rtss19.pdf)
analyze Poisson arrivals with deterministic demand under a deferrable server
and evaluate synthetic and Redis services on Xen. These premises differ from
our finite schedules and ordinary Linux bandwidth ceiling. Our periodic model
is a simplified baseline, not their implemented analysis. This review inspected
indexed primary passages; direct full-PDF retrieval was unavailable.

The average-speed approximation in
[Cucinotta et al. (TCC 2023)](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf)
explicitly assumes a reservation period small relative to request processing
time, under HCBS temporal isolation. Its evaluation uses a 2 ms period. Our
100 ms ceiling and short requests do not reproduce this regime, and failure
of our constant-rate comparator does not refute their method.

Empirical profiling for tail prediction is also established.
[CEDULE (ICAC 2018)](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf)
fits quantile models using CPU-limit/load profiles for burstable-cloud
scheduling. Its richer conditioning and quantile metrics differ from our
fixed empirical miss-probability reference. We have neither implemented a
matched comparison nor demonstrated superiority to that method.

[Mi et al. (JISA 2010)](https://link.springer.com/content/pdf/10.1007/s13174-010-0012-9.pdf)
study temporal dependence and limitations of average models, fitting richer
service models from busy-period observations. The broad importance of
burstiness and dependence is therefore background, not our discovery.
Likewise, [Jeffery et al. (2024 preprint)](https://arxiv.org/html/2407.11582v1)
already distinguish queue and worker latency in quota-aware thread management;
stage instrumentation itself supplies no algorithmic novelty.

The possible incremental contribution is the measured, prospectively tested
contrast across selected deadlines and traffic conditions, accompanied by
adverse transfer evidence. It is restricted to the declared comparators and
observed domains. Pairing does not dominate every deadline, a steep CDF is
not a new mechanism, and NGINX tests a different full-response question.
No universal deadline/period boundary, advance applicability selector,
independent-hardware replication or state-of-the-art superiority follows.
The focused review records ten primary sources and its access/coverage gaps
in `docs/runtime_io_deadline_boundary_prior_work_review_20261010.md`.
Finding no exact match in selected passages is insufficient to claim a first
result; scientific novelty remains a candidate requiring further assessment.
