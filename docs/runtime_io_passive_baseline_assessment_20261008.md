# Passive burst forecasting: applicability, adequacy and decision

8 October 2026. Completed bounded offline follow-up to the
[novelty screen](runtime_io_passive_forecast_novelty_screen_20261008.md).

**Verdict: stop custom-method development and new collection at the present
novelty gate.** Passive demand inference, estimator selection, prediction intervals
and abstention already have substantial prior art. Our saved records do not
establish an additional reliable quota-forecast capability. This is neither a
proof that the practical question is solved nor a finding that no novel solution
is possible. It is a decision about what the evidence currently justifies.

The useful unresolved target is deciding when permissible history supports a
burst forecast, with meaningful coverage of nonzero misses. A method that always
refuses, answers only easy zero-miss cases, or reports tight parameter intervals
without checking future error would not establish that capability.

Collection remains stopped. The version-5 empirical manuscript, supporting
material, original forecasts and scientific outcomes are preserved. Quota-period
selection remains on hold; the FIFO theorem route remains closed.

## Decision problem and information boundary

Input: known future offered-arrival schedule, deadline 500 ms, same service and
request class, one worker, waiting queue 128, quota 50 ms/100 ms, initial queue,
affinity, and permitted observations collected before the decision. Output:
offered-cohort deadline-miss percentage, including failed offers, or an explicit
insufficient-evidence decision. The 3-percentage-point error reference comes from
the existing scoped comparison, not a production SLA.

Two contracts must remain distinct:

- **Cold start:** no historical burst/overload labels or offline loaded profiles.
  Use natural traffic or permissible low-load observations. Naturally occurring
  busy windows, if present, are permissible and an ordinary direct baseline.
- **Trained deployment:** historical paired histories and future outcomes may
  train/calibrate a method. Charge their acquisition cost and state-transfer
  assumptions. Avoiding overload during deployment does not imply that training
  never used overload.

Current passive inputs are twelve controlled idle/steady calibration trials in
two blocks: 0/15/30/60/90/120 offered requests/s. Ten contain work; strict-low
inputs are the four work-bearing 15/30 trials plus two idle trials. No retained
input trial throttled or missed a 500 ms deadline; waiting queue peaked at one.
The 90/120 observations are broader nonbacklogged observations, not strict low
load or natural production traffic. Deliberate mixed/backlogged calibration is
excluded from these new predictors. All sixteen saved burst outcomes are already
known: this assessment is retrospective, with no inherited prospective status.

## Published methods against this problem

| Method | Assumptions and measurements | Output and quota applicability | What was assessed |
|---|---|---|---|
| Perez et al.: BL, RPS/ERPS and MLPS | Shared CPUs, active-worker counts and CPU-related response times; ML adds a stochastic service model | Mean request demand. Single-worker continuous-server specialization reduces to mean worker execution time. Quota throttling and unsanitized off-CPU time require an additional mapping. | Evaluated the single-worker elapsed-time specialization with both unit-availability and conditional quota-scaled mappings. No full multithread implementation or CPU-demand correctness claim. |
| Incerto et al.: moving-horizon estimation (MHE) | Known network structure/routing/multiplicities; queue histories; exponential-service/fluid model | Service rates from inferred flows and occupied-server exposure. Does not itself model Linux budget replenishment. | Evaluated an explicit open, single-queue event/exposure adaptation with observed arrivals and empty/drained endpoints, exact exposure and a 10 ms grid. No full network QP reproduction. |
| SARDE | Monitoring streams, estimator library, window/step tuning and selection; internal cross-validation proxies or training errors | Demand estimates and estimator choice. Calibration fit quality is not future burst-error certification. | Implemented ordinary two-block selection between existing CPU linear/quadratic fits. This is a comparator inspired by established selection, not SARDE's learned selector or full pipeline. |
| DEC | Benchmark mixtures and replication, with a workload/resource transfer model | Demand estimates with confidence. Benchmark acquisition must be charged; not a label-free cold-start substitute. | Applicability comparison from the previously inspected 2010 primary thesis; journal revision and algorithm not reproduced. |
| Residual conformal prediction and selective risk control | Separate outcome-labeled calibration examples; exchangeability/i.i.d. or explicit shift treatment, depending on guarantee | Prediction sets or separately controlled selected-case risk. Neither follows from a coefficient confidence interval. | Checked block-level sample-count feasibility; computed descriptive residuals. No new guard fitted or guarantee claimed. |
| MPORA | Offline program state/allocation profiles, fitted prediction and held-out calibration | Uncertainty-aware deadline allocation. Its profile cost and transfer assumptions belong to trained deployment. | Applicability comparison only; saved single-state V28 data cannot reproduce its profiling or state-conditioned system. |

Perez et al. require CPU-related worker response measurements, separating
external/non-CPU delays; BL integrates reciprocal active-worker occupancy,
while RPS uses response/occupancy regression. With one active worker, their
continuous-server demand formula reduces to the elapsed service mean. Applying
that formula here is conditional because saved processing time is elapsed wall
time, not measured worker CPU. [Primary paper, §§3–6](https://juanfperez.com/data/2015_02_des_TSE.pdf).

MHE fits queue-network dynamics and estimates rates from flows divided by
occupied-server exposure. Our adaptation replaces inferred flows with observed
open-queue arrivals/completions, restores seconds explicitly, and handles one
server. This removes the need for a network optimizer for this restricted check;
it does not validate the stochastic/fluid assumptions or add quota-service
dynamics. [Primary paper, §§II–III](https://cse.lab.imtlucca.it/~mirco.tribastone/papers/mascots18.pdf).

SARDE tunes estimation parameters through internal cross-validation and learns
estimator selection from actual or proxy errors. Our block selector only tests
the simpler ordinary alternative; absence of a full learned library comparison
remains a limitation. [Primary preprint, §§5.2–5.4](https://se.informatik.uni-wuerzburg.de/publications/?cHash=c7300d8a02e65b7dcd8870de230e3338&tx_extbibsonomycsl_publicationlist%5Baction%5D=download&tx_extbibsonomycsl_publicationlist%5Bcontroller%5D=Document&tx_extbibsonomycsl_publicationlist%5BfileName%5D=SARDE_TaaS2020.pdf&tx_extbibsonomycsl_publicationlist%5BintraHash%5D=fc3fb3694ee15b680f1466a5acc7bc64&tx_extbibsonomycsl_publicationlist%5BuserName%5D=se-group).

DEC and MPORA remain training/profile comparators, as documented in the prior
screen. See the [DEC primary thesis](https://www.collectionscanada.gc.ca/obj/thesescanada/vol2/002/MR69450.PDF?is_thesis=1&oclc_number=806535411)
and [MPORA primary paper](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html).

Linux quota controls an upper CPU-time budget with replenishment and per-CPU
distribution. It is not a guarantee of continuous service at the configured
average fraction. Multiplying a wall-service estimate by 0.5 is an assumption
under test, not an established quota mapping.
[Kernel bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html).

## Offline comparisons actually performed

The separate [assessment design](../analysis/runtime_io_passive_baseline_assessment/20261008/design/plan.json)
was sealed before fitting/scoring this assessment, after the original outcomes
were known. It excludes mixed/busy and validation observations from parameter
estimation. It declares both quota mappings rather than selecting one from burst
errors. Every available estimate feeds the same retained constant-rate FIFO
approximation and exact saved offered schedule. This isolates capacity inputs;
it does not test a quota-aware service simulator or a whole published pipeline.

For one worker, `N / sum(processing_wall_time)` is the unscaled wall-service
estimate; the conditional quota mapping multiplies it by 0.5. Queue exposure
uses `N / integral(min(admitted_but_unfinished, 1) dt)`, covering admission-to-start
gaps as well as worker execution. Endpoints span first admission to final
completion, with empty/drained queue, avoiding unaccounted boundary jobs.

The ordinary load-dependent response adaptation regresses mean elapsed worker
time against throughput, `D(X) = a + bX`, and solves `X D(X) = 0.5`. This is an
affine wall-demand adaptation, not a reproduction of Kumar/Zhang or a novel
model. A positive demand, increasing required-CPU curve through the capacity
root, unique admissible root and root within twice maximum observed throughput
are required. Unavailable roots remain refusals.

The selector fits linear/quadratic CPU models on one calibration block and
scores utilization error on the other, reversing the split. It selects the
smaller summed calibration-only error, then refits that family on all twelve
calibration rows. Linear held-out SSE is 0.0058779054 versus quadratic
0.0015879518. It selects quadratic without burst labels.

| Scoped comparator | Capacity, jobs/s | Mean absolute miss error, pp | Maximum error, pp | Within 3 pp, all 16 | Within 3 pp, nonzero 8 |
|---|---:|---:|---:|---:|---:|
| Existing strict-low aggregate CPU demand law | 110.691 | 43.291 | 54.476 | 0 | 0 |
| Strict-low worker wall, quota-scaled | 116.900 | 39.280 | 49.024 | 0 | 0 |
| Broader worker wall, quota-scaled | 125.883 | 31.314 | 37.929 | 0 | 0 |
| Broader exact queue exposure, quota-scaled | 125.767 | 31.482 | 38.167 | 0 | 0 |
| Broader 10 ms queue exposure, quota-scaled | 133.212 | 23.085 | 26.333 | 0 | 0 |
| Broader affine wall-demand adaptation | 136.766 | 18.203 | 20.119 | 0 | 0 |
| Calibration-block selector → existing quadratic | 148.463 | 1.169 | 3.619 | 13 | 5 |

Unit-wall mappings, without quota correction, predict zero misses on all sixteen
schedules: they pass the eight observed-zero cases and fail all eight nonzero
cases (MAE 16.119 pp, maximum 35.952 pp). They have no observed nonzero-case
accuracy. The strict-low affine wall model refuses all sixteen under its bounded
extrapolation rule. The earlier strict-low quadratic likewise has zero answer
coverage; neither demonstrates a useful reliability classifier.

The numerical result is not evidence that BL, MLPS, MHE or SARDE are inferior
to a new method. We tested declared specializations/adaptations with uncertain
quota transfer, and the strongest current CPU comparator is an existing
nonlinear benchmark. General load-dependent inference remains established and
full closest-algorithm quota validation remains incomplete.

### Sampling sensitivity

The 10 ms adaptation cannot be used as the main evidence against transient
inference: processing intervals are only a few milliseconds. Independent
calibration-only checks found its zero-phase exposure error ranges from
−19.467% to −0.293% across the ten work-bearing trials. Shifting the grid by
5 ms changes the range to −11.034% to +10.322%. A 1 ms grid is much closer
(zero-phase −0.551% to +1.387%; half-step −1.817% to +0.566%). This is
quadrature/alias sensitivity on saved events, not quota-phase measurement or
observer qualification. Exact event exposure provides the appropriate comparison
here. No grid was chosen using future forecast performance.

## What ordinary uncertainty can and cannot provide here

Independent residual calibration is an established way to construct prediction
intervals. Split conformal uses the order statistic at
`ceil((n + 1) * 0.95)` for 95% marginal coverage. Four exchangeable calibration
blocks would require rank five, beyond the observed residuals; the usual
unbounded residual interval is vacuous, or it spans the full known target range
0–100%. Nineteen independent calibration episodes are the count minimum for
a finite empirical 95% residual quantile, not enough by itself for a narrow
interval, selective risk or transfer. Marginal coverage does not automatically
survive selection of only narrow/confident forecasts. Separate selective risk
control already exists. [Conformal tutorial, §1.1 and §5.5](https://arxiv.org/html/2107.07511v6).

V28 has four burst validation blocks, not thousands of independent forecasting
episodes. No exchangeability across future deployment states is established.
Using these known outcomes to develop a guard would require fresh error
calibration and testing. Descriptive quadratic block-maximum errors are
2.333, 3.619, 1.500 and 3.458 pp. Their largest value exceeds the 3 pp reference.
They neither certify future accuracy nor establish that state-dependent ordinary
uncertainty methods cannot do better.

For a fixed guard with zero bad accepted predictions among independent accepted
episodes, the one-sided 95% binomial upper risk is `1 - 0.05^(1/n)`.
With four episodes it is 52.713%; 59 zero-failure accepted episodes bring it
below 5%. These are count illustrations under stated sampling assumptions,
not a chosen campaign size or a guarantee for adaptive selection/state drift.

## Concrete capability contract and remaining gap

The [machine-readable contract](../analysis/runtime_io_passive_baseline_assessment/20261008/capability_contract.json)
specifies a candidate capability: at matched observation/training cost and
justified accepted-error risk, answer materially more useful burst cases than
ordinary nonlinear inference plus independently calibrated uncertainty/risk
control. Alternatively, reduce cost at matched risk and coverage. Include
nonzero misses and histories that genuinely do not support the extrapolation.
A new feature, application endpoint, interval wrapper or refusal label alone
does not establish this advantage.

For a future design, proposed criteria are error within 3 pp, answer coverage
at least 50% overall and 50% among observed-nonzero cases, and a justified
95%-confidence upper bound of 5% on bad accepted predictions. These are
provisional research criteria, not achieved results or user-approved production
targets. Accepted-case risk requires its own calibration/test treatment.

Cold-start evidence must independently justify the model/service bounds on
which any interval relies. Repeated low-load measurements alone estimate
variation at low load; they do not validate future loaded demand or unknown
resource supply. A trained deployment can learn empirical reliability from
past paired episodes, subject to disclosed transfer assumptions and cost.
Both contracts must allow ordinary comparators equal information.

The essential missing data, if a distinct mechanism/capability is formulated,
are independent pairs of permissible history and subsequent burst outcomes,
varying history support and relevant resource state. Existing data do not
provide a separated development/error-calibration/fresh-test dataset for that
guard. Additional worker CPU or quota timing would be conditional measurements
requiring a specific discriminator and observer qualification first.

## Proceed-or-stop disposition

1. **Stop the broad novelty claim:** passive forecasting with uncertainty or
   refusal is established. This comparison establishes no new method.
2. **Stop a custom prototype and fresh campaign now:** no distinct reliable
   capability has been demonstrated, and published quota mappings remain
   incompletely validated. Adaptation failures do not supply novelty.
3. **Retain the narrow question as an open candidate:** reopen only with a
   concrete mechanism explaining how permissible observations constrain loaded
   service or forecast error beyond the ordinary comparators. A trained,
   state-conditioned empirical guard may be feasible, but its generic form
   already has prior art and its useful quota-specific advantage is untested.

The empirical paper can be finished independently with its present scoped
contribution. No new data are necessary to report this verdict. If the candidate
is reopened, the paired-data requirement above should determine a bounded
protocol; do not collect a larger dataset first to search for a favorable claim.

## Verification and artifacts

[Assessment report](../analysis/runtime_io_passive_baseline_assessment/20261008/report.json),
[forecasts](../analysis/runtime_io_passive_baseline_assessment/20261008/forecasts/report.json),
[uncertainty check](../analysis/runtime_io_passive_baseline_assessment/20261008/uncertainty.json),
[grid sensitivity](../analysis/runtime_io_passive_baseline_assessment/20261008/grid_sensitivity.json),
and [independent verification](../analysis/runtime_io_passive_baseline_assessment/20261008/verification.json)
are separate from all prior evidence. The verifier checked ten raw event
integrals, fourteen demand fits, four block-selection folds, 224 forecast cases
using the retained simulator independently of the new forecast recurrence,
and seven conformal rank calculations. SHA-256 preservation checks passed for
1,911 protected scientific files and nineteen additional paper/screen files.
No scientific trial, new instrumentation, custom guard or full published
pipeline was executed.
