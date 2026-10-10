# Supporting material: deadline forecasting under a fractional CPU quota

10 October 2026. Companion to the [completed extension manuscript](deadline_resolution_extension.md)
and [offline reproduction guide](deadline_resolution_reproducibility.md).
This document consolidates existing records. It adds no performance measurements,
model fit, endpoint selection or causal result.

## S1. Primary claims and limits

| Claim | Evidence | Scope and adverse evidence |
|---|---|---|
| Periodic+delay improves the primary 25 ms comparison | V30, 16 fresh calibration trials and 18 validation trials; MAE 2.341 pp versus fluid busy 73.599 pp | Mean/profile-weighted criterion; burst-only MAE 7.024 pp, maximum trial error 12.097 pp; secondary 50–150 ms errors favor fluid busy |
| The paired empirical reference improves the primary 10 ms comparison | V31, 16 fresh calibration trials and 18 validation trials; MAE 1.844 pp versus periodic+delay 67.340 pp | Same Go service and host, observed low-queue domain; maximum trial error 5.055 pp; convolution is better at secondary 9 ms |
| The low-rate empirical reference does not model overload | V30 exploratory timing comparison; 25 ms burst error 79.203 pp | Retrospective method selection; retained adverse scope evidence, not a separate prospective test |
| Complete-response CDF transfer is not supported by its declared accuracy gate | NGINX, 4 fresh calibration cohorts and 18 validation cohorts; MAE 5.981481 pp, conditional interval [1.320988,10.641975] pp | Upper endpoint exceeds required 5 pp; internal queue unmeasured, new estimand, same physical host; does not refute V31 |
| Saved NGINX timing varies across cohorts near the response transition | Persistent block-2 excursion and client milestone diagnosis | Post-hoc description; no identified server stage, scheduler defect, CPU-demand change or quota phase |

V30/V31 gates apply to mean accuracy and declared paired improvements. NGINX
uses an upper-interval accuracy gate without the Go comparator. Its failed
criterion is not proof that population mean error exceeds five points. The
calibration budgets, endpoints and statistical contracts differ, so the studies
do not provide a common model ranking or a calibration-cost comparison.

## S2. Protocols and complete evidence

- [V30 frozen execution design](../analysis/runtime_io_v30/generation-01/bundle/scientific_design/runtime_io_v30_confirmation_protocol_20261009.md).
- [V31 design in the qualified bundle](../analysis/runtime_io_v31/generation-01/bundle/manifest.json), including executable scientific rules; the [candidate protocol](../docs/runtime_io_v31_candidate_protocol_20261009.md) retains its historical proposal wording and is not the final completion record.
- [NGINX frozen prospective protocol](../docs/runtime_io_nginx_prediction_protocol_20261009.md) and [generation protocol](../analysis/runtime_io_nginx_prediction/generation-01/protocol.json).
- [Focused primary-source comparison](../docs/runtime_io_deadline_boundary_prior_work_review_20261010.md) and [source/access register](../analysis/runtime_io_deadline_boundary_prior_work_review/20261010/sources.json).

Frozen bundles, calibration records, prediction seals, trial records and final
analyses remain under their original generation paths. The manuscript's V30,
V31 and NGINX labels identify distinct prospective contracts, not pooled repeats.
Warmup is excluded from scientific timing fits and outcomes. Any technical or
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

Detailed records: [original imgproxy failure](../analysis/runtime_io_imgproxy_feasibility_review/20261009-generation01/report.md),
[one-CPU apparatus abort](../analysis/runtime_io_imgproxy_one_cpu_abort_review/20261009-generation01/report.md),
[corrected one-CPU failure](../analysis/runtime_io_imgproxy_one_cpu_failure_review/20261009-generation02/report.md),
[gzip queue-domain exit](../analysis/runtime_io_gzip_failure_review/20261009-generation01/report.md),
and [NGINX suitability review](../analysis/runtime_io_nginx_qualification_review/20261009-generation02/report.md).
The [unchanged-workload imgproxy forensic probe](../analysis/runtime_io_imgproxy_throttle_probe_review)
did not restore qualification. Candidate selection changed software and
measurement scope; it did not produce independent physical-host replication.

## S4. Interpretation of recorded timing

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
