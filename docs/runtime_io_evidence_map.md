# Research evidence map and claims register

**Verified V22 follow-up — 2026-10-07:** The original consolidation below is
retained as its dated snapshot. New claims are supported by the
[V22 findings](runtime_io_v22_findings.md) and independently sealed
[result review](../analysis/runtime_io_v22_result_review/20261007/report.json):

| Claim | New evidence | Scope |
|---|---|---|
| C12: prospective busy-capacity transfer | All8 validation trial and4 paired contrast errors passed the frozen3 pp limit; maximum1.55 pp. Supporting queue/rejection/recovery and even screen passed. | One host/boot/service/44k work size; yielding off. Exact stage/tail prediction is not implied. |
| C13: prospective nominal CPU/job substitution failure | This declared baseline predicted44.05% burst misses, versus10.97–11.92%; busy-capacity prediction10.38%. Its advantage passed the frozen supporting comparison. | Specific loaded cgroup CPU/job substitution, not every CPU-demand model. Cause of the estimator difference is not isolated. |
| C14: arrival-pattern CPU/job tradeoff | Even-pattern CPU/job was approximately14.8% above burst-pattern CPU/job in paired blocks, despite much lower response latency. | Descriptive matched observation; per-job CPU and the overhead mechanism are unmeasured. |

The [short draft](runtime_io_short_working_draft.md) narrows the empirical target.
[V23](runtime_io_v23_frozen_question.md) is prepared for two work sizes and new
burst timescales; its qualification/calibration/validation remain unrun. Work-size
generality, an independent algorithm/workload and novelty are not established by
its software checks. The original Step1 review receipt is not rewritten.

Consolidated 2026-10-07, after the post-restart comparison and the decision to
close the historical period-reversal investigation. This is Step 1 of the
research synthesis: assemble what the existing evidence permits us to say before
assessing the contribution against closest work.

The strongest current account is that execution controls change where requests
wait, while measured busy service capacity and burst arrivals explain much of
the original 500 ms deadline loss. Strong improvement in one measured stage does
not guarantee a comparable improvement in timely responses. Whether this account
predicts a new arrival pattern remains an untested question.

This consolidation checks dated findings against saved analysis summaries and
reports. It does not freshly replay every raw trial or certify novelty. The
[review receipt](../analysis/runtime_io_evidence_map/20261007/review.json) records
the inspected files, hashes, selected arithmetic and local-link checks. Original
protocols, reports, failed attempts and decision thresholds remain preserved.

## Scope and measurement rules

- The central V20 evidence concerns stock Go 1.26.1, a fixed SHA workload of
  44,000 iterations/job, one worker/GOMAXPROCS=1, a 128-slot queue, CPUs 2/4,
  0.5 CPU allowance and zero quota burst credits on the recorded AMD/Linux host.
  Earlier V12 varies GOMAXPROCS with four workers; V19 varies workers. These are
  different treatments and must not be merged into one comparison.
- A fixed quota **and period** is the unchanged CPU contract. Comparing 100 and
  20 ms at the same quota/period ratio changes temporal CPU availability despite
  preserving average allowance.
- Deadline success means a successful response within the deadline from its
  scheduled offer, divided by **all offers**. Rejections/errors count as misses;
  successful p99 is conditional on success. Late and drained outcomes remain
  included. The 500 ms target was exploratory in V12 and declared for V20; it is
  not an independently established production SLO.
- Main-computation completion precedes event storage and reply publication.
  Handler resume records execution, not first runnable readiness. Their interval
  is not a direct measurement of scheduler waiting. Program order supplies a
  publication bound in specified single-worker cases, not an exact timestamp.
- Independent blocks are the replication units. Request/cycle counts are
  descriptive. Means of trial quantiles are not pooled quantiles, and separately
  computed stage percentiles cannot be added to explain E2E percentiles.

## Supported claims

“Supported” below means supported within the named recorded conditions; it does
not imply universal behavior or an identified kernel/runtime mechanism. Sources
E01–E11 are linked in the evidence index below.

| ID | Claim and quantitative anchor | Evidence/status | Permitted interpretation and boundary |
|---|---|---|---|
| C01 | In the V12 bursty comparison, reducing GOMAXPROCS from 2 to 1 improved the extreme successful tail but worsened overall successful p50 in all four pairs. Median trial p99: 4,075.09 → 880.41 ms; median trial p50: 159.30 → 355.47 ms. Exploratory all-offer 500 ms misses: 7,899 → 9,298 of 27,172 per arm. | E01; paired descriptive characterization and post-hoc deadline analysis. | Tail improvement can coexist with worse tight-deadline outcomes. This is not a universal parallelism recommendation or a fairness-only effect; CPU/job also changed. |
| C02 | Computed results can be available before the deadline while handler execution occurs afterward. All 1,182 V19 single-worker computation-before/handler-after crossings had a subsequent worker start certainly before 500 ms; typical conservative publication-to-resume lower bound: 54.32 ms. | E02; exploratory inference from verified source/program order and bounded clocks. | Delayed publication cannot explain the whole wait in this subset. Exact handler readiness, available quota and runqueue residence remain unknown. |
| C03 | Post-publication yielding strongly reduces the measured completion-to-handler interval. Original V20 at 100 ms: mean 17.280 → 0.0579 ms, with 99.58–99.78% reduction across blocks. Repeat: 18.595 → 0.0886 ms. | E03/E05; controlled comparisons, four blocks per session. | The stage-specific response recurs across these sessions. It does not establish the scheduler mechanism or individual-request causal recovery. |
| C04 | Yielding's net 500 ms benefit is conditional. Original V20 at 100 ms: 82.14 → 82.05% success (−0.088 pp); repeat: 73.10 → 74.74% (+1.638 pp, positive in all four blocks). Repeat at 20 ms: approximately +0.026 pp with both signs across blocks. | E03/E05; original frozen screen failed useful signal; repeat block summaries are exploratory. | A strong stage response does not guarantee a net deadline gain. Do not say “yielding never helps”: the faithful repeat retained a modest 100 ms benefit. No-benefit in the original is not equivalence. |
| C05 | Queue waiting is the dominant location of original V20 successful deadline losses. With 100 ms/yield on, 4,661 of 4,877 successful misses crossed 500 ms after admission and before worker start (95.57%). Mean queue wait increased 217.724 → 232.802 ms when yielding was enabled. | E04; raw-linked retrospective stage reconstruction. | Directly localizes these losses to the application waiting interval. It does not identify why the worker fell behind or prove that the same requests exchanged waiting time between stages. |
| C06 | The original burst vector creates transient overload despite mean demand below measured busy capacity. High/low rates: 169.815/56.605 offers/s; mean 113.217. Original yield-off busy capacities: 151.04/138.67 jobs/s at 100/20 ms. All 96 recorded cycles began their high phase with zero logical queue; A peaks 88–102 jobs, C/D reach 128 and reject offers. | E04; within-session queue/history observation. | Backlog builds during high phases and clears during low phases in this vector. Logical queue is reconstructed admitted-but-not-started intervals, not an independent channel-occupancy trace. |
| C07 | Separately fitted busy capacity predicts the bulk of the original V20 queue/deadline outcomes in withheld blocks. Train blocks 1–2, evaluate 3–4: miss-rate error at most 1.782 pp; peak error 5 jobs; mean recovery error 81.8 ms. | E04; post-hoc prediction check, common capacity per period. | Supports a capacity-to-backlog-to-deadline account for this session. Outcomes were already known and tolerances selected retrospectively; this is not prospective validation or an explanation of capacity from quota. |
| C08 | Whole-trial CPU/job is a poor substitute for the busy capacity parameter in this model. The nominal CPU/job model predicts roughly 46–47% misses and 198–217 rejections for held-out 100 ms trials, versus about 17–18% observed misses and no rejections. The busy-capacity model also misses rare tails: b3_C/b4_C have 28/14 successful responses beyond 1 s, predicted zero. | E04; failed alternative and retained model limitations. | Distinguish workload-average CPU accounting from busy service behavior. Good aggregate prediction does not establish exact stage or rare-tail prediction. These failures are part of the evidence. |
| C09 | The recorded period-to-cost relationship changes between sessions. Original V20 yield off: 3.630 → 3.833 ms CPU/job and 82.14 → 54.86% 500 ms success at 100 → 20 ms. Faithful repeat: 3.644 → 3.596 ms and 73.10 → 82.29%. | E03/E05/E06; verified conditional observations with matching retained binaries and recorded contracts. | Neither universal shorter-period penalty nor universal shorter-period benefit is supported. The original runner repeat weakens a pilot-helper-only explanation; it does not isolate the historical cause. |
| C10 | HTTP handling and application queues were unnecessary for the earlier minimal SHA period penalty. Two minimal pairs showed 14.19% and 11.58% shorter-period CPU/job penalties. Later closing and automatic-state continuation comparisons had small improvements and near-unchanged instruction counts. | E07; seven-cell partial screen, separate completed closing/continuation comparisons. | Preserve both states. Later counters cannot retrospectively diagnose an earlier uncounted penalty; the partial screen is not a completed eight-cell factorial. |
| C11 | The reboot is recorded, with three differences in compared fields. Different boot IDs; root subtree controllers lost hugetlb/rdma/misc/dmem; BogoMIPS 6587.56 → 6587.82; one transient service appeared. Other service states matched after whitespace normalization. | E11; descriptive snapshot comparison, zero attempted-read/command coverage gaps. | This completes the pre/post configuration record. It is not a quiet performance baseline or causal reboot test; transient activity differed and root-only observer ownership was not freshly audited. |

## Measurement and negative evidence that constrain the claims

| Evidence | Retained result | How it limits interpretation |
|---|---|---|
| V15–V17 observer/build controls (E08) | Marker effects were nonmonotonic; rebuild controls changed deadline outcomes. Shared loading reduced the image gap but did not meet neutrality in every pair. | More detailed timestamps cannot automatically be treated as neutral observations of the original service. |
| V18 tracing cost pilot (E09) | Twelve complete trials; five of six pairs failed the 500 ms practical margin. CPU/job and p99 remained within their margins; deadline effects had both signs. | Technical completeness and known-work fixture success do not establish neutral observer cost or causal attribution of HTTP waits to quota. |
| Full-service hardware cost pilot (E06) | Hardware observer failed its 1% qualification margin. Later minimal observer checks passed in their own workload/session. | Minimal-workload qualification does not transfer retroactively to the full-service pilot or older uncounted states. |
| GC, software and ownership reviews (E10) | Current GC screen did not reproduce a large consistent period interaction; exercised software checks found no explanatory defect; dated ownership review found no unexplained experimental observer. | These narrow explanations in tested conditions. They do not prove all bugs, historical GC effects or historical observers absent. |
| Incomplete/cancelled branches (catalogue) | Minimal screen and speed pilot had retained partial sessions; background-app crossover was cancelled; boost crossover and V22 remain unrun. | Preparation is not collection, and cancelled/unrun proposals are not negative experimental results. |

## Hypotheses and unresolved questions

| ID | Statement | Current status | Evidence needed to advance it |
|---|---|---|---|
| H01 | Capacity calibrated in separate current-boot burst trials transfers to evenly spaced arrivals and predicts all-offer 500 ms outcomes. | Candidate next hypothesis; V22 proposed, unimplemented/unrun. | Freeze parameters, uncertainty and predictions before independent validation. A capacity shift with arrival pattern is a failed transfer assumption to report, not refit away. |
| H02 | The account predicts the burst-duration boundary for queue-driven deadline failure and buffer overflow. | Optional extension, untested. The balance calculation itself is ordinary queueing. | Validate new durations at identical total work and resource contract with independently frozen predictions. |
| U01 | Runtime runnable competition versus temporal quota supply explains the residual post-publication wait. | Unresolved mechanism. | Qualified aligned readiness/execution/quota evidence or a discriminating intervention. Handler resume and aggregate cpu.stat alone are insufficient. |
| U02 | A particular execution-state, runtime-work, thermal, clock, cache, desktop or collection-context change caused the historical period-cost reversal. | Closed as unresolved; retained context, no automatic reopening. | A reproducible substantial effect with measurements that distinguish causes. Later near-null counters and reboot snapshots cannot reconstruct the historical state. |
| U03 | Findings transfer across workloads, hardware, kernels or runtimes. | Unestablished. | Separate controlled replication supporting the intended breadth. Multiple sessions on one host do not supply that generalization. |
| U04 | The supported findings constitute a novel research contribution. | Unassessed by this evidence consolidation. | Closest-work/contribution matrix, followed by the validation needed for the surviving substantive distinction. |

## Wording for research synthesis

Supported now:

> In a stock-Go HTTP service under a strict fractional CPU quota, execution
> controls substantially altered measured request-stage delays. Yielding
> consistently reduced the post-computation interval, but its net 500 ms deadline
> benefit varied between sessions. A retrospective finite-buffer model calibrated
> from busy completion capacity accounted for much of the original burst-driven
> queue buildup and deadline loss, while retaining identifiable prediction errors.

Candidate addition after validation:

> Independently calibrated capacity predicts all-offer deadline outcomes across
> specified new arrival patterns, with measured limits on its transfer and tail
> accuracy.

Do not claim a new queueing law, guaranteed gains from yielding, a proven Go
scheduler defect, a universal quota-period recommendation, an explained historical
reversal, neutral instrumentation in all studies, or established novelty.

The next authorized planning step is the closest-work/contribution matrix using
C03–C08 as the central evidence. H01 is the proposed next empirical test, subject
to final protocol and new-boot preparation. The
[V22 design](runtime_io_v22_prospective_queue_plan.md) supplies its current scope.

## Evidence index

- **E01 — V12 parallelism:** [tradeoff audit](../analysis/runtime_io_v12_tradeoff_review/report.md),
  [deadline/marker interpretation](../analysis/runtime_io_v12_tradeoff_review/gap_audit_and_completion_deadlines.md),
  [deadline counts](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work.json).
- **E02 — V19 residual:** [findings and source proof](runtime_io_v19_residual_findings.md),
  [sealed summary](../analysis/runtime_io_v19_residual_review/20261005/summary.json).
- **E03 — Original V20:** [findings](runtime_io_v20_findings.md),
  [verified result summary](../analysis/runtime_io_v20_result_review/20261005/report.json),
  [original generation-03 report](../analysis/runtime_io_v20_execution_delay/generation-03/analysis/1791215103576116652/report.md).
- **E04 — Queue/model account:** [findings, definitions and failures](runtime_io_v20_backlog_findings.md),
  [raw-linked review](../analysis/runtime_io_v20_backlog_review/20261005/report.json),
  [reviewer](../analysis/review_v20_backlog.py).
- **E05 — Faithful V20 repeat:** [findings](runtime_io_v20_repeat_findings.md),
  [cross-session review](../analysis/runtime_io_v20_repeat_review/20261006/report.json),
  [generation-04 report](../analysis/runtime_io_v20_execution_delay/generation-04/analysis/1791263686578222719/report.md).
- **E06 — Cost/reversal context:** [cost pilot findings](runtime_io_period_cost_pilot_findings.md),
  [reversal audit](runtime_io_period_reversal_audit.md).
- **E07 — Minimal and closing controls:** [minimal partial report](../analysis/runtime_io_minimal_computation_screen/generation-02/partial_analysis/1791292967721661400/report.md),
  [closing findings](runtime_io_period_reversal_closing_findings.md),
  [execution-state continuation](runtime_io_execution_state_continuation_findings.md).
- **E08 — Instrumentation/build controls:** [marker review](../analysis/runtime_io_v15_marker_review/report.md),
  [repeatability review](../analysis/runtime_io_v16_repeatability_review/report.md),
  [shared-loading report](../results/diagnostic/runtime-io-v17-shared-loading-1/session/analysis/report.md).
- **E09 — Kernel observer limits:** [completed cost review](../analysis/runtime_io_v18_observer_cost_review/generation-04-1791136754967461238/review.md).
- **E10 — Diagnostic exclusions and limits:** [GC findings](runtime_io_gc_screen_findings.md),
  [software audit](runtime_io_software_audit_findings.md),
  [ownership findings](runtime_io_leftover_observer_findings.md).
- **E11 — Boot comparison:** [pre-restart snapshot](../analysis/runtime_io_system_state_snapshots/1791343349016869707-pre-restart.json),
  [post-restart snapshot](../analysis/runtime_io_system_state_snapshots/1791345410649559361-post-restart.json),
  [comparison](../analysis/runtime_io_system_state_snapshots/1791345410664662815-comparison.json),
  [collector](../diagnostic/system_state_snapshot.py).
- **Full investigation/attempt status:** [catalogue](runtime_io_investigation_catalogue.md).
