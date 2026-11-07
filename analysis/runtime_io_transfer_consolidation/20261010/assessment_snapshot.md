# Deadline-forecast transfer: consolidated evidence and contribution decision

10 October 2026. Offline consolidation after the completed rate-transfer study.
No new performance collection, predictor fitting or competing artifact execution.
Earlier protocols, raw records, assessments and finalized manuscripts remain
unchanged. This assessment supersedes preparation-era next-step statements;
it does not alter any experiment's gate or provenance.

## Decision

**Proceed with a scoped empirical paper; hold new collection and custom-method
development.** The evidence supports specific prospective forecast comparisons,
an adverse transfer result, a helpful but insufficient policy control, and a
fresh accurate-transfer episode without demonstrated rate-matching advantage.
It establishes no new estimator, advance reliability diagnostic, identified
physical cause or superiority over published methods. Conference-level
originality remains unestablished; the targeted literature check cannot certify
venue suitability or acceptance. A second host would improve scope, not create
algorithmic novelty.

The useful research question is: **what do selected, inexpensive approximation
and calibration procedures predict at a fixed deadline in a declared CPU-quota
setting, and which observed controls fail to assure transfer?** The paper should
answer that question with both favorable and adverse evidence. It should not
claim to characterize every condition in which empirical calibration works.

## Evidence ledger

All errors are absolute all-offer deadline-miss probability errors in percentage
points (pp). Campaigns have different endpoints, comparator information,
traffic contracts and gates. This table is a ledger, not a pooled model ranking.

| Study | Deadline (ms) | Reference MAE (pp) | Comparator MAE (pp) | Frozen result |
|---|---:|---:|---:|---|
| Go V30 | 25 | Periodic + delay: 2.341 | Fluid busy FIFO: 73.599 | Prospective gates passed |
| Go V31 | 10 | Queue-adjusted CDF: 1.844 | Periodic + delay: 67.340 | Prospective gates passed in observed domain |
| NGINX original | 20.565395 | Complete-response CDF: 5.981 | No head-to-head comparator | Prospective accuracy gate not supported |
| NGINX power confirmation | 20.565395 | Policy-matched CDF: 15.708 | Pooled policies: 24.729 | Improvement passed; accuracy failed |
| NGINX rate transfer | 20.565395 | Rate-matched CDF: 1.194 | Fixed 5/s CDF: 1.972 | Accuracy passed; advantage not supported |

The V31 complete-response control has MAE **1.802499 pp**, close to the
prospective queue-adjusted reference's 1.844437 pp. Its selection was
retrospective, despite using only calibration samples for its probabilities.
The primary paired-stage sum is exactly E-Q; stage decomposition is unnecessary
for that sum. The control weakens decomposition novelty, without inheriting
prospective status or establishing that observers can be removed safely.

Original NGINX accuracy has conditional 95% interval [1.321, 10.642] pp, failing
the required upper bound <=5 pp. This does not prove its population mean is
above 5 pp. The power confirmation improves over pooling by 9.021 pp,
interval [1.746, 16.296] pp, but matched accuracy's upper bound is 18.721 pp.
Its zero-miss P1 endpoint makes part of the aggregate comparison easy; the
failure under P0 remains visible and must not be hidden by aggregation.

In the rate study, matched accuracy's upper bound is 1.581 pp and ordinary
5/s accuracy's upper bound is 2.907 pp; both pass. The gain is 0.778 pp,
interval [-0.375, 1.931] pp, failing the frozen >=2 pp mean gain and positive
lower-bound requirements. This does not prove equivalence. Observed primary
miss probabilities span 78.667–84.000%; accurate prediction is distinct from
good deadline compliance. The two throttled cohorts are included as required.

The stopped power pilot remains an outcome-stopped exploratory prefix, not a
six-block confirmation. Its favorable partial error cannot be combined with
the complete confirmation to manufacture an acceptance result. V30's empirical
CDF burst failure and other deadline-grid contrasts also remain exploratory.

## What the ordinary controls resolved

| Question | Answer supported by this evidence | Remaining limit |
|---|---|---|
| Does effective average throughput alone preserve short-deadline predictions? | The declared fluid substitution fails badly in V30; periodic + delay meets its primary gate | Its per-job floor already exceeds 25 ms. The large contrast is not a new timing law or a refutation of all fluid approximations |
| Is stage pairing necessary for the V31 10 ms result? | The ordinary complete-response control gives nearly the same average accuracy | Descriptive comparison; no equivalence, observer-removal or cost-saving qualification |
| Do clean calibration/throttle checks assure transfer? | Original NGINX and the fresh power confirmation fail their accuracy gates despite zero recorded scientific throttling | They do not isolate the internal queue, scheduler or physical cause |
| Does matching assigned EPP suffice in the tested confirmation? | It improves over mixing policies, but the accuracy requirement still fails | Defeating an intentionally mixed reference is weaker than defeating a state-aware published predictor |
| Does adding full target-rate calibration show useful extra benefit? | Matched transfer is accurate, but ordinary 5/s transfer is also accurate; the required advantage is not supported | No equivalence claim and no cross-campaign causal repair claim |
| Is short recent warmup a reliable replacement? | It does not consistently improve the original Go/NGINX screens and fails the power/rate accuracy upper-bound gates | Screens were retrospective; later warmup decisions have a different budget and information time |
| Can existing checks warn us before bad transfer? | The saved stability, sampling and warmup checks have not produced a validated useful rule | No identified additional capability; not proof that every state-aware method fails |

The earlier power P0 reference and the new 5/s P0 reference both happen to
predict 79.5% primary misses, from different fresh samples. Their later response
populations differ substantially. A matching forecast probability or assigned
setting alone therefore supplies no demonstrated transfer certificate.
This is descriptive evidence across episodes, not a controlled experiment
identifying why they differ. Rate, chronology, service instances, physical
state and distribution shape were not independently isolated across campaigns.

## Closest prior capabilities and fair comparison contracts

The implication column is our assessment. It does not claim these unexecuted
methods fail our workload. Primary passages were rechecked on 10 October;
locators, queries and access limitations are in the [source register](runtime_io_transfer_consolidation_sources_20261010.json).

| Closest work | Established capability / required information | Consequence for this paper |
|---|---|---|
| [Li, Lu and Gill, RTSS 2019](https://www.cse.wustl.edu/~lu/papers/rtss19.pdf), P2 | Stationary response-distribution analysis with Poisson arrivals, deterministic demand and a highest-priority deferrable server; Xen evaluation | Periodic-server tail prediction is established. Finite deterministic traffic and a Linux bandwidth ceiling do not reproduce its premises. Indexed primary passages only; full PDF retrieval still fails |
| [Cucinotta et al., TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), P3 | HCBS reservation analysis; average-speed approximation requires period small relative to processing time; evaluation uses 2 ms periods | Our 100 ms quota ceiling with short requests tests a different contract. V30 cannot be presented as a counterexample to their stated approximation |
| [CEDULE, ICAC 2018](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf), P4 | Sparse CPU-limit/load profiling and quantile-regression tail forecasts for credit-aware scheduling; profiling cost is explicit | Load-conditioned calibration and held-out profiling are established. A fixed-deadline miss-probability error is not their quantile error; we have no matched implementation comparison |
| [Tales of the Tail, SoCC 2014](https://syslab.cs.washington.edu/papers/latency-socc14.pdf), P5 | Measures hardware/OS/application sources of tail latency, including NGINX and low-load power effects | Power mechanisms affecting tails are established. Our later calibration-transfer outcomes add scoped observations, not an identified new power mechanism |
| [ReTail, HPCA 2022](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf), P6 | Request-feature and frequency-conditioned latency prediction with active DVFS, latency monitoring and drift-triggered retraining | State-aware prediction and adaptation are established. Our campaign-wide fixed forecast lacks its inputs and feedback. Matching EPP is not matching physical frequency or reproducing its controller |
| [MPORA, ECRTS 2026](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html), P7 | Progress/state/allocation models with weighted conformal uncertainty and cache/memory resource control; shifted coverage depends on distribution dissimilarity | Uncertainty-aware deadline allocation is established. It uses richer execution profiles and a different task endpoint; no direct HTTP probability-error comparison or distribution-free transfer guarantee follows |

The [Linux bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html)
explains quota/period accounting and latency tradeoffs (P1). The
[AMD driver documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html)
explains that active EPP guides autonomous hardware decisions (P8). A quota
ceiling is not a guaranteed isolated reservation, and a matching EPP preference
does not fix instantaneous frequency, thermals or shared-resource interference.
The richer uncertainty literature and its assumptions remain in the earlier
[reliability capability audit](runtime_io_forecast_reliability_prior_work_20261010.md).

There is no valid state-of-the-art ranking here. We should not deny a published
method its required inputs, replace its scheduler or invent a probability
output from one predicted quantile and then attribute failure to that method.
Any adaptation would be a separately named baseline with its own validation.

## Contribution assessment

| Proposed contribution | Verdict | Defensible scope |
|---|---|---|
| New empirical-CDF estimator or stage-pairing algorithm | Unsupported | CDF estimation and E-Q accounting are ordinary |
| Discovery that quota periodicity or power policy affects latency | Prior art | Background established by the closest models, measurements and documentation |
| Prospective comparison of selected approximations at declared deadlines | Supported, modest empirical contribution candidate | Keep exact inputs, traffic, outcomes and weak-comparator limitations visible |
| Prospective calibration-transfer audit with unsuccessful controls preserved | Supported, scoped empirical contribution candidate | Matching policy was insufficient in one completed campaign; rate matching showed no required extra advantage in another |
| General operating boundary or advance trustworthy-forecast selector | Unsupported | No validated signal predicts which future episode will transfer |
| Physical explanation of the historical NGINX excursion | Unresolved | Client stages and aggregate counters do not identify per-request CPU/scheduling causes |
| Reproducible evidence and integrity-preserving evaluation process | Supported artifact strength | Reproducibility improves credibility; seals and fresh data are not scientific novelty by themselves |
| Independent-host generality or production SLO control | Pending / unsupported | Friend's V31 not received; high miss fractions and trivial decision labels do not establish useful control near the 5% budget |

The value beyond a list of error numbers is exposing which inference is safe:
the tested approximation can pass one endpoint and miss another; an ordinary
profile can match a richer timing reference; and measured control agreement
does not establish future response stationarity. These are quantified examples
of known concerns, not a new universal theory. The combined prospective and
adverse record is a plausible empirical case-study contribution, but its
originality and breadth remain the main submission risk. Freshness of evidence
and the absence of an exact match in this targeted search do not settle that risk.

## Information, cost and statistics to retain

Each target-rate reference uses 800 calibration offers. Covering both 4/s and
8/s requires 1,600, versus 800 for the shared 5/s reference; pooling uses 2,400.
The complete rate study acquired all three pools plus qualification and warmup.
Those total costs must not be reported as only the predictor's selected samples.
Similarly V31's 676 retained timing samples came from a larger sixteen-trial
calibration apparatus. No client-only deployment or acquisition-cost saving
was qualified. Updated references spend additional samples and decide later.

Six block summaries, not requests, support each primary block-based comparison.
They are sequential; independence and normality are assumptions. The NGINX
intervals condition on frozen references, excluding calibration uncertainty.
Campaigns differ in contracts, and all physical-host evidence here is from
the same machine. Do not combine cohort or offer counts into a larger independent
replication count. Passing an aggregate accuracy gate is not a per-cohort bound;
not supporting superiority is not proving equivalence. Zero-error saturated
secondary endpoints cannot replace the frozen primary endpoint.

## Decision before another experiment

1. **Use the current empirical result now.** A [contribution note for manuscript integration](../paper/deadline_transfer_contribution_note.md)
   supplies the question, contribution wording and limitations. Integrate the
   two follow-ups with both success and failure visible; preserve historical
   manuscript/audit snapshots. This consolidation does not rewrite the sealed
   manuscript or certify submission readiness.
2. **Keep the friend's V31 replication separate and pending.** On return verify
   qualification, fresh calibration, forecast barriers, all eighteen trials,
   the prospectively declared ordinary comparator, domain exits and cleanup.
   Report hosts separately, including adverse outcomes. Do not assume his
   current package contains an uninspected comparator or use his outcomes to
   train a new guard and then count them as confirmation.
3. **Reopen collection only for a concrete stronger claim.** A reliability
   method needs a pre-outcome observable tied to future shift, an ordinary
   profile/uncertainty comparator with the same information and acquisition
   budget, and independent forecasting episodes. A causal claim needs a
   measurement or intervention that distinguishes the proposed mechanism.
   A published-method comparison needs compatible inputs, scheduler and output
   before a matched evaluation can be frozen. None of these prerequisites is
   supplied by the current result, so no new experiment is selected here.

A same-settings repeat could eventually estimate recurrence, but without a
declared recurrence target and episode budget it would merely add another
episode. A new warmup window, endpoint, frequency sweep or larger predictor
chosen to improve these known outcomes would be development, not independent
confirmation. Earlier closed/hold branches stay closed/on hold.

## Verification and evidence

The additive package at `analysis/runtime_io_transfer_consolidation/20261010/`
contains source-derived numeric rows, an input hash inventory, six read-only
saved-evidence verification receipts, this assessment snapshot, the contribution
note snapshot and source-register metadata. The manuscript revision audit
checks preserved earlier evidence; the power and rate verifiers replay their
full raw campaigns. The reliability screens remain saved-data exploratory
checks. None is an independent scientific replication or originality certificate.

```bash
python3 -B analysis/consolidate_transfer_evidence.py --verify
```

Individual primary results remain in the [V30 review](../analysis/runtime_io_v30_result_review/20261009-generation01/report.json),
[V31 review](../analysis/runtime_io_v31_result_review/20261009-generation01/report.json),
[original NGINX review](../analysis/runtime_io_nginx_prediction_result_review/20261009-generation01/report.json),
[power confirmation review](../analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.md)
and [rate-transfer review](../analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.md).
