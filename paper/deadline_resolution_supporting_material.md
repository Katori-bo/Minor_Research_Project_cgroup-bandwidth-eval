# Supporting material: deadline forecasting under a fractional CPU quota

Revised 11 October 2026. Companion to the [completed extension manuscript](deadline_resolution_extension.md)
and [offline reproduction guide](deadline_resolution_reproducibility.md).
This document consolidates existing records and the retrospective response-CDF
control from the manuscript review, completed fresh power/rate/panel studies,
saved-data reliability screens and qualification/precision holds. Integration adds no performance measurements,
prospective endpoint selection or causal result.

## S1. Primary claims and limits

| Claim | Evidence | Scope and adverse evidence |
|---|---|---|
| Periodic+delay improves the primary 25 ms comparison | V30, 16 fresh calibration trials and 18 validation trials; MAE 2.341 pp versus fluid busy 73.599 pp | Mean/profile-weighted criterion; burst-only MAE 7.024 pp, maximum trial error 12.097 pp; secondary 50–150 ms errors favor fluid busy |
| The paired empirical reference improves the primary 10 ms comparison | V31, 16 fresh calibration trials and 18 validation trials; MAE 1.844 pp versus periodic+delay 67.340 pp | Same Go service and host, observed low-queue domain; maximum trial error 5.055 pp; convolution is better at secondary 9 ms |
| The low-rate empirical reference does not model overload | V30 exploratory timing comparison; 25 ms burst error 79.203 pp | Retrospective method selection; retained adverse scope evidence, not a separate prospective test |
| Complete-response CDF transfer is not supported by its declared accuracy gate | NGINX, 4 fresh calibration cohorts and 18 validation cohorts; MAE 5.981481 pp, conditional interval [1.320988,10.641975] pp | Upper endpoint exceeds required 5 pp; internal queue unmeasured, different calibration/completion/domain contract, same physical host; does not refute V31 |
| Ordinary complete-response calibration gives nearly the same V31 error | Retrospective control: same 676 calibration offers, original 10 ms deadline; forecast 67.455621%, MAE 1.802499 pp, maximum trial error 5.350358 pp | Selected after outcomes; 0.041938 pp mean difference establishes neither superiority nor equivalence; no instrumentation-removal qualification |
| Saved NGINX timing varies across cohorts near the response transition | Persistent block-2 excursion and client milestone diagnosis | Post-hoc description; no identified server stage, scheduler defect, CPU-demand change or quota phase |
| Assigned-policy matching helps but does not meet the accuracy target | Fresh power confirmation: 4 calibration and 24 validation cohorts; matched MAE 15.708 pp versus pooled 24.729 pp; improvement 9.021 pp, interval [1.746,16.296] | Accuracy upper bound 18.721 pp exceeds 5 pp; pooling deliberately mixes policies; zero-miss P1 is a saturated endpoint |
| Target-rate calibration is accurate without demonstrated extra advantage | Fresh fixed-P0 rate study: 6 calibration and 12 validation cohorts; matched MAE 1.194 pp, ordinary 5/s 1.972 pp | Gain 0.778 pp, interval [-0.375,1.931], fails frozen advantage criteria; both accurate, without equivalence or causal repair claim |
| Current checks supply no validated advance reliability signal | Retrospective calibration/warmup screens and fresh ordinary warmup comparisons | No fitted guard is confirmed; differing decision times and acquisition budgets remain explicit |
| Accurate historical-cutoff prediction does not establish panel accuracy | Fresh five-cutoff panel: P0/P1 scores 6.611/4.889 pp, conditional upper bounds 11.391/7.158 pp | Both frozen gates fail; P1's old cutoff has zero misses; six blocks per policy, shared calibration uncertainty excluded |
| Further local observer collection lacks a justified qualification path | Completed worker-wait equivalence is inconclusive; longer-warmup and execution-rate planning stay held | New clock observer was not implemented/measured; predictive usefulness and clock-to-response mapping remain untested |

V30/V31 gates apply to mean accuracy and declared paired improvements. NGINX
uses an upper-interval accuracy gate without the Go comparator. Its failed
criterion is not proof that population mean error exceeds five points. The
calibration budgets, endpoints and statistical contracts differ, so the studies
do not provide a common model ranking or a calibration-cost comparison.

## S2. Protocols and complete evidence

- [V30 frozen execution design](../analysis/runtime_io_v30/generation-01/bundle/scientific_design/runtime_io_v30_confirmation_protocol_20261009.md).
- [V31 design in the qualified bundle](../analysis/runtime_io_v31/generation-01/bundle/manifest.json), including executable scientific rules; the [candidate protocol](../docs/runtime_io_v31_candidate_protocol_20261009.md) retains its historical proposal wording and is not the final completion record.
- [NGINX frozen prospective protocol](../docs/runtime_io_nginx_prediction_protocol_20261009.md) and [generation protocol](../analysis/runtime_io_nginx_prediction/generation-01/protocol.json).
- [Fresh power confirmation protocol](../docs/runtime_io_nginx_power_confirmation_protocol_20261010.md), [complete raw comparison](../analysis/runtime_io_nginx_power_confirmation/generation-01/campaign/comparison.json) and [sealed assessment](../analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.md).
- [Fresh rate-transfer protocol](../docs/runtime_io_nginx_rate_transfer_protocol_20261010.md), [complete raw comparison](../analysis/runtime_io_nginx_rate_transfer/generation-01/campaign/comparison.json) and [sealed assessment](../analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.md).
- [Focused primary-source comparison](../docs/runtime_io_deadline_boundary_prior_work_review_20261010.md), [original source/access register](../analysis/runtime_io_deadline_boundary_prior_work_review/20261010/sources.json), [transfer capability assessment](../docs/runtime_io_transfer_consolidation_20261010.md) and [updated source/access register](../docs/runtime_io_transfer_consolidation_sources_20261010.json).

Frozen bundles, calibration records, prediction seals, trial records and final
analyses remain under their original generation paths. The manuscript's V30,
V31 and NGINX labels identify distinct prospective contracts, not pooled repeats.
Warmup is excluded from the original global timing fits and validation outcomes;
the separately declared later-decision warmup/update references use it explicitly.
Any technical or
applicability exit retains its original classification and cannot be replaced
by favorable observations from another candidate.

## S3. Stopped application qualifications

| Candidate/attempt | Retained outcome | Interpretation |
|---|---|---|
| Original imgproxy pilot | Measurement nr_throttled increased in a recorded cohort; six-pair qualification unavailable | Domain exit before scientific calibration/validation; not a prediction counterexample |
| First one-CPU imgproxy runner | Pre-measurement live-thread affinity/cgroup check aborted | Apparatus failure; no valid prediction study |
| Corrected one-CPU imgproxy, generation 02 | Final stock cohort had a measurement throttle increment; joint qualification failed | All 12 cohorts retained; no forecast-validation campaign began |
| GNU gzip service wrapper | Pair-4 observed arm had 197/200 queue waits <=100 us, below required 99% | Seven cohorts retained; qualification unavailable; no fresh predictive test |
| Stock NGINX measurement qualification, generation 02 | Three full-response stock cohorts qualified | Measurement suitability only; these timings are excluded from the later scientific fit |
| Stock NGINX prospective generation 01 | All scientific measurement gates passed, but prediction accuracy criterion did not | Completed adverse scientific result, distinct from the earlier qualification exits |
| NGINX power-policy pilot | Validation cohort 12 recorded throttling; only 12/24 planned cohorts collected | Outcome-stopped exploratory prefix, not the six-block acceptance test; retained separately from fresh confirmation |

Detailed records: [original imgproxy failure](../analysis/runtime_io_imgproxy_feasibility_review/20261009-generation01/report.md),
[one-CPU apparatus abort](../analysis/runtime_io_imgproxy_one_cpu_abort_review/20261009-generation01/report.md),
[corrected one-CPU failure](../analysis/runtime_io_imgproxy_one_cpu_failure_review/20261009-generation02/report.md),
[gzip queue-domain exit](../analysis/runtime_io_gzip_failure_review/20261009-generation01/report.md),
and [NGINX suitability review](../analysis/runtime_io_nginx_qualification_review/20261009-generation02/report.md).
The [unchanged-workload imgproxy forensic probe](../analysis/runtime_io_imgproxy_throttle_probe_review)
did not restore qualification. Candidate selection changed software and
measurement scope; it did not produce independent physical-host replication.

## S4. Interpretation of recorded timing

V31's validation endpoint is complete scheduled-to-client-completion latency,
including queue waiting. Only its predictor calibration uses $R=E-Q$.
The worker/residual identity $W+(E-Q-W)=E-Q$ means that the primary CDF does
not require that stage split. All 676 client calibration offers also meet the
original queue selection. The retrospective full-response control therefore
uses exactly the same offers, with no new trimming or chosen endpoint.
Its fit uses calibration records only, but its method was selected after
validation: it is not an additional prospective comparison.

Go worker-wall time is elapsed time, not isolated request CPU demand. A
non-queue residual includes client/runtime/transport effects. The periodic
model's effective demand comes from quota fraction divided by busy throughput,
not an independently observed SHA execution cost. Uniform shared quota phase
is assumed; it was not measured. Aggregate service CPU/job includes work that
cannot be assigned to individual request stages.

NGINX completion is encoded-body receipt before decoding/hash verification.
Internal queue is unmeasured. Headers-to-body time includes compression,
delivery and scheduling on both sides. Zero recorded throttle increments and
nonoverlapping client responses do not establish exclusive CPU service,
unchanging CPU cost or an observed server queue. The saved diagnosis cannot
assign its timing excursion to a unique mechanism.

## S5. Finalization scope

The first finalization and reviewer-assessment packages remain historical,
sealed records of the earlier manuscript. The earlier corrected documents are
preserved in the [review-correction audit](../analysis/runtime_io_deadline_extension_revision/20261010-review-corrections/report.json).
The live integrated documents are checked by the
[11 October consolidation package](../analysis/runtime_io_empirical_consolidation/20261011/).
The [10 October integration](../analysis/runtime_io_deadline_transfer_integration/20261010/)
also remains a historical sealed version.
The new checker runs the prior revision checker against its immutable manuscript
snapshots through a temporary logical workspace, preserving its source and
scientific evidence. Old document hashes intentionally identify earlier versions.

Methods provenance: kernel identities are in each campaign's
`observer_review/audit.json`; Go runtime identities are in the retained
`server_metrics.json` files and client-build manifests. Calibration schedules
are in each bundle's `scientific_design/design.json`. Busy/steady eligibility
and fixed windows are inherited from the sealed V29 `q025_large/design.json`
through the bundled study code. The deterministic 32-byte SHA-256 chain is
in `diagnostic/service/main.go`. The CPU model/RAM description comes from the
earlier [host record](paper_draft.md), which records an older kernel;
that historical kernel is not substituted for V30/V31's recorded kernel.
The revision audit checks these sources and records their hashes.

The finalization package preserves a manuscript snapshot, the source register,
figure coordinates, document hashes and the offline audit. The summary figure
contains three separately labeled studies; it has no common superiority gate.
Its interval is the declared conditional NGINX interval, not an unconditional
confidence statement or a pairing interval across applications.

Scientific novelty remains unestablished. The targeted review finds the core
methods established, with a material full-PDF access gap for RTSS 2019 and no
matched competing implementation run. Authors, affiliations, acknowledgments,
target venue and public artifact location have not been supplied. Manuscript
completion does not mean a submission or external artifact release occurred.

## S6. Follow-up information, populations and cost

Both completed controls preserve the original 20.565395 ms primary deadline,
stock binaries, corpus and quota. Their all-offer population allows throttling
through qualification, calibration, warmup and validation, unlike the stopped
pilot's zero-throttling gate. Corrupt complete output and invalid identity or
accounting remain technical stops; ordinary unsuccessful offers are misses.
No failed or throttled outcome is removed to improve a score.

The power confirmation acquires 1,600 calibration offers (800 per policy),
7,200 validation and 700 warmup offers. Matched and pooled procedures share
the acquisition but have different effective per-policy sample counts. The
rate study acquires 2,400 calibration (800 each at 4/5/8/s), 3,600 validation
and 450 warmup offers. One known-rate reference and the 5/s reference each
use 800, but covering both target rates needs 1,600 versus 800 for shared 5/s.
Qualification adds its own acquisition and never enters the scientific fit.
Warmup/update references use later information and additional samples.

Power matched gain passes but accuracy fails; rate matched accuracy passes but
gain fails. Neither outcome establishes equivalence, a general method ranking,
fixed physical frequency or the historical failure's cause. Rate cohorts 5 and
9 retain aggregate throttling of 6,600 and 9,133 us respectively. Their counters
do not assign events to responses. Keep both completed studies and the stopped
prefix separate in the paper's inference.

## S7. Reliability screens and independent-host status

The [initial reliability screen](../docs/runtime_io_forecast_reliability_assessment_20261010.md)
and [recent-timing screen](../docs/runtime_io_recent_timing_observable_assessment_20261010.md)
are exploratory saved-data analyses. Their known outcomes cannot validate a
newly fitted guard. Complete-response cohort dispersion, deadline sensitivity
and short warmup disagreement have not yielded a useful confirmed advance
rule. The fresh studies' predeclared ordinary warmup comparators do not turn
those earlier screens into prospective evidence.

The user's friend owns the pending V31 independent-host replication. No returned
host result is included. On arrival inspect the actual qualified package,
fresh calibration, global forecast barriers, all eighteen trials, comparators,
domain/partial outcomes and cleanup. Preserve host-specific results; do not
pool offers as independent hardware replications. A further contribution needs
a concrete additional claim, compatible comparator and independent evaluation
contract before collection or custom-method development resumes.

## S8. Fresh deadline-panel evidence and costs

The [completed assessment](../docs/runtime_io_nginx_deadline_panel_assessment_20261010.md)
and [sealed raw-review package](../analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01/)
retain all 24 validation cohorts and five calibration-only cutoffs per policy.
Ranks 79/199/399/599/719 from 800 offers each freeze the panel before validation.
The six-block statistic takes the maximum cutoff error after averaging across
rates; it is distinct from single-deadline MAE and panel-average error.
P0 score 6.611 pp, interval [1.831, 11.391], and P1 score 4.889 pp,
[2.620, 7.158], both fail the upper <=5 pp gate. Intervals are conditional
97.5% per policy, with >=95% family coverage only under the stated block model;
shared calibration uncertainty is excluded. P1's zero error at the old saturated
cutoff does not imply panel accuracy. The retained P0/8/s cohort 1 has one
throttled period / 4,703 us; aggregate accounting cannot identify its cause.

The full acquisition is 10,530 offers: 1,030 qualification, 1,600 calibration
measurement, 100 calibration warmup, 7,200 validation and 600 validation warmup.
Qualification takes 279.086 s and science 2,140.385 s. Matching, pooling,
P0-only and warmup/update controls are charged the complete acquired data;
updates decide later. All source/forecast barriers, outcomes, cleanup and
normal/dead-owner policy restoration verify. These are fresh instances on the
same host, distinct from the pending friend's V31 replication.

## S9. Later development screens and measurement holds

| Evidence | Retained scope and result |
|---|---|
| [Timing/CPU screens](../docs/runtime_io_prevalidation_signals_assessment_20261010.md) | Warmup timing and aggregate CPU agreement do not supply confirmed transfer reliability; later information/cost is explicit |
| [Continuous persistence](../docs/runtime_io_continuous_persistence_assessment_20261010.md) | All 54 cohorts, first-100/next-200 boundary; average power improvement and 31.5 pp accepted-error case both retained |
| [Client stages](../docs/runtime_io_stage_signal_assessment_20261010.md) | All 54 cohorts; inadequate coverage and no useful advantage over whole-response checks |
| [Deadline scope](../docs/runtime_io_deadline_scope_assessment_20261010.md) | Retrospective 54-cohort panels motivate the independently frozen fresh study; their original primary gates stay unchanged |
| [Deadline sensitivity](../docs/runtime_io_deadline_sensitivity_assessment_20261010.md) | All 78 cohorts; no confirmed selector or robust median correction, with known outcomes and correlated cutoff cells |
| [Worker-wait qualification](../docs/runtime_io_worker_wait_qualification_assessment_20261010.md) | All 7,890 offers; operational checks pass, all six behavioral intervals fail containment; qualified=false, usefulness untested |
| [Worker-wait precision/cost](../docs/runtime_io_worker_wait_precision_cost_assessment_20261010.md) | Conditional planning from six pairs per rate; unchanged small repeats remain unjustified |
| [Warmup precision/cost](../docs/runtime_io_warmup_precision_cost_assessment_20261011.md) | All 78 pairs; IID rank/DKWM geometry, long-warmup budget and lifetime violations; no future-error guarantee |
| [Execution-rate audit](../docs/runtime_io_execution_rate_candidate_20261011.md) | Read-only capability review; no counter accuracy, attribution or future usefulness measured |
| [Bounded execution-rate design](../docs/runtime_io_execution_rate_qualification_design_20261011.md) | No-go: eight-pair budget, historical noise scenarios far outside 20 us allowance, unverified clock-to-response mapping |

The development screens were chosen with historical outcomes known. Pre-target
feature timestamps do not make them prospective confirmation. The observer
qualification is separate from predictive testing; an inconclusive equivalence
result proves neither harm nor uselessness. Planning bounds are not minimum
sample sizes, observed new-observer behavior or power. Hold longer-warmup,
worker-wait and execution-rate collection. A further candidate needs justified
measurement precision/cost and a state-to-future relation, then equal-information
ordinary comparison and fresh evidence. No hardware experiment begins with this
revision, and V31 replication remains pending and excluded.

The new audit preserves the four prior manuscript files, all existing tables
and 2,559 protected paths, while replaying historical checkers with their original
manuscript versions. Old seals continue to identify those versions. Use the
current checker in the reproduction guide; no historical seal is rewritten.
