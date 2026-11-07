# Pre-validation transfer signals: completed feasibility assessment

10 October 2026. New offline development screens after manuscript integration. Historical outcomes were known. No new performance collection, host-setting changes, predictor fitting or manuscript revisions.

**Two concrete signals were tested. Neither distinguishes reliable transfer at the required coverage and error tolerance.** The mathematical signal and fair comparators are now explicit; their observed failure is retained. This narrows the search without proving that no useful advance signal can exist.

## Timing-shift signal

Estimate delta = median(last 25 warmup responses) - median(reference), then predict p_shift = 1 - F_reference(D-delta). The score is the maximum of |p_shift-p_reference| and the difference between shifted predictions from the early and late twelve warmup offers. The middle offer is excluded only from the half comparison. Accept the original forecast when the score is <=5 percentage points and there are no failed reference/warmup offers.

A persistent population location shift produces exactly this CDF displacement. The difficult assumption is that shape and shift persist into the future window. Median translation is ordinary distribution modelling; [NIST’s quantile comparison](https://www.itl.nist.gov/div898/handbook/eda/section3/eda33o.htm) explains how location and shape differences appear. The temporal check sees within-warmup changes but cannot certify subsequent stability.

| Campaign | Answers | Coverage | Transition coverage* | Bad forecasts accepted | False warnings |
|---|---:|---:|---:|---:|---:|
| Go V31 | 4/18 | 22.2% | 22.2% | 0 | 13 |
| NGINX | 1/18 | 5.6% | 5.6% | 0 | 10 |
| NGINX power | 12/24 | 50.0% | 0.0% | 0 | 1 |
| NGINX rate | 4/12 | 33.3% | 33.3% | 0 | 8 |

*Transition cases have observed miss fractions between 10% and 90%. A bad forecast has later absolute probability error >5 pp. These are descriptive labels, not inputs to the rule.

Power-study answers comprise only the twelve P1 cohorts with zero observed misses. It answers none of the twelve P0 transition cases. In the accurately transferring rate campaign it rejects eight of twelve forecasts. Removing the temporal check retains four bad forecasts among nine accepted original NGINX cases; shift-only also retains Go’s 5.35 pp error. The ablations do not rescue the candidate.

## Fair ordinary comparators

Every recent-data method receives the identical reference, the same 25 warmup offers and the same post-warmup decision time. Compare direct recent empirical CDF, sample-weighted update, ordinary median translation, deadline disagreement, chronological deadline disagreement and ECDF sup distance. The median translation forecast is itself an ordinary comparator; no new-estimator claim is made.

| Campaign | Original CDF MAE | Recent 25 MAE | Weighted update MAE | Median translation MAE |
|---|---:|---:|---:|---:|
| Go V31 | 1.802 | 5.037 | 1.779 | 3.284 |
| NGINX | 5.981 | 9.463 | 5.971 | 9.219 |
| NGINX power | 15.708 | 4.778 | 15.250 | 5.227 |
| NGINX rate | 1.972 | 7.528 | 2.073 | 6.969 |

Errors are percentage points of all-offer deadline-miss probability. Keep campaigns separate; their endpoints and acquisition contracts differ. Translation worsens Go and original NGINX. In the power study it improves the original reference but does worse than direct warmup profiling. In the rate study, adapting the already accurate reference worsens it.

Ordinary warmup/reference disagreement catches all eleven bad power-study forecasts but answers only one of twelve transition cases. The full ECDF-distance <=5 pp check accepts no cohorts. Its cutoff is the same descriptive probability tolerance, not a calibrated hypothesis test or a future-risk certificate; [NIST defines the ECDF-distance statistic](https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/ks2samp.htm). No threshold is selected after inspecting these results.

The original NGINX excursion is especially informative: warmup gives 36% misses, median translation predicts 42.8125%, the original reference predicts 50%, and the subsequent cohort has 88.3333% misses. The new rule warns, but ordinary disagreement warns too. Correcting toward the warmup actually increases error. Catching that single known excursion therefore supplies neither comparator advantage nor a demonstrated persistence model.

## Isolated warmup CPU-demand signal

The newer NGINX studies preserve cgroup CPU snapshots isolated around warmup. Compare CPU microseconds per offer with the two corresponding calibration warmups, translate their difference into an additive timing shift, and warn when the resulting CDF probability change exceeds 5 pp. The reference is policy-matched for power and ordinary fixed-5/s for rate. This design was frozen after the timing screen and counter inventory; historical outcomes were already known.

This is ordinary CPU-conditioned prediction. It assumes aggregate CPU-duration changes translate into response time and persist after warmup. [Kernel cpu.stat documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu) defines accounting over cgroup processes; these counters do not isolate per-request CPU, physical frequency or scheduler/client delay.

| Campaign | Answers | Transition coverage | Bad forecasts accepted | Maximum accepted error | False warnings |
|---|---:|---:|---:|---:|---:|
| NGINX power | 16/24 | 33.3% | 3 | 39.500 pp | 0 |
| NGINX rate | 0/12 | 0.0% | 0 | — | 12 |

The three bad accepted P0 power cases have warmup CPU changes approximately -0.65%, -0.64% and -0.69%. Their reference predicts 79.5% misses while later misses are 44.33%, 44.33% and 40%. Near-agreement in CPU demand does not assure transfer.

Rate-study warmup CPU demand is about 1.26–1.99% below the reference warmups, causing all twelve accurate forecasts to be refused. CPU-conditioned forecast MAE is 17.122 pp versus 1.972 pp for the original reference. Later measurement CPU per offer exceeds warmup by 310.8 us on average. That later discrepancy is diagnostic evidence only and never enters an advance prediction. The additive mapping is inadequate here; this does not identify a physical cause. Original NGINX lacks the corresponding isolated warmup baseline, so its excursion receives no invented CPU score.

## Cost and information contract

Decision time is after completed warmup and drain, before measurement. It is later than the original global forecast. At 4/s the 25 offers occupy about 6 seconds of scheduled span; at 8/s about 3 seconds, plus drain, control and setup. Two CPU snapshots add observer cost not independently qualified for deployment. Consuming saved samples is not evidence of a cost saving.

Go acquired 9022 calibration measurement offers and 3600 calibration warmup offers across sixteen trials including two idle controls. The analyzed complete-response pool is 676 offers. The shift-screen JSON field calibration_total_offers counts the pool analyzed and must not be read as the full Go acquisition budget. The separate cost audit supplies those full counts. Go validation warmups acquired 4,200 offers, of which this equal-budget screen consumes 450.

Original NGINX acquired 1,600 calibration measurement offers; power acquired 1,600; rate acquired 2,400. Each selected power-policy or fixed-5/s pool has 800. Retain all acquired pools in the cost ledger. CPU-reference estimation also consumes 50 calibration warmup offers per selected reference. Qualification, settling, startup and instrumentation are additional. A 25-offer-only collector has not been qualified.

A richer state-informed comparator must receive the same new measurements and acquisition budget. [ReTail](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf) uses richer request/frequency information and online prediction-error feedback. It was not executed or denied its inputs, and no superiority claim is made.

## Decision and remaining question

**No new confirmation experiment is justified by these candidates.** The missing relation is whether a cheaply measured pre-validation state predicts persistence or change over the subsequent response window. The screens show why merely detecting a current timing or CPU shift is insufficient: small summaries can agree before bad transfer, and short probes can disagree before accurate transfer.

A future candidate needs an explicit advance state-to-future relation that can distinguish CPU service changes, off-CPU/downstream delay, or a change after warmup. Adding a list of frequency, thermal or queue counters alone does not satisfy that requirement. Alternatively, a longer contiguous probe would need a justified sample/time budget and an equal-cost recent-profile comparator; longer warmup cannot be assumed to cure these results. Keep the empirical manuscript and friend-host V31 replication separate.

The 72 timing evaluations share campaign references, chronology and one physical host. They are development evidence, not 72 independent reliability episodes. Thresholds, windows and deadlines were not tuned. No causal mechanism, novelty, statistical risk guarantee or general impossibility result is established.

## Verification

Both screens reproduce from consumed raw seals, with strict deadline/failure accounting, raw calibration reconstruction, synthetic translation and failure/throttle oracles, original-result reconciliation and warmup information barriers. Existing reliability, recent-timing, power-confirmation and rate-transfer verifiers also pass. Original evidence and manuscripts remain unchanged.

```bash
python3 -B analysis/screen_prevalidation_shift.py --verify
python3 -B analysis/screen_prevalidation_cpu.py --verify
```

[Timing protocol](runtime_io_prevalidation_shift_protocol_20261010.md), [timing results](../analysis/runtime_io_prevalidation_shift/20261010/screen.json), [CPU design](../analysis/runtime_io_prevalidation_cpu/20261010/design.json), [CPU results](../analysis/runtime_io_prevalidation_cpu/20261010/screen.json), [cost audit](../analysis/runtime_io_prevalidation_shift/20261010/cost_audit.json).
