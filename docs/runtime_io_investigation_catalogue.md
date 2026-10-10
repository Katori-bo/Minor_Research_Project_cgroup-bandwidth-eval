# Investigation catalogue and resumption record

Updated 2026-10-07 after V22 completion/review, the short working draft and V23 preparation. This is the current
entry point for returning to the investigation. Earlier protocols and findings
are dated records: their proposed next steps may have since been completed,
superseded or cancelled. Preservation here means saved locally in this repository;
this catalogue does not certify an independent backup.

## Current position

The [evidence map and claims register](runtime_io_evidence_map.md) consolidates
supported findings, negative/measurement evidence and unresolved questions.
The historical reversal branch is closed as unresolved. The pre/post boot
configuration comparison is complete. V22 generation-02 completed qualification,
calibration and all8 validation trials; independent raw replay passed all12
primary checks and supporting comparisons. See the [verified findings](runtime_io_v22_findings.md). The
[closest-work/contribution matrix](runtime_io_contribution_matrix.md) is complete
as a targeted review. Its lead candidate is a scoped stage-to-deadline diagnostic
case study; novelty remains unestablished, while V22's scoped prospective transfer
now passed. Step 3 is now
recorded in the [frozen V22 question/design](runtime_io_v22_frozen_question.md).
Step 4 implementation and generation-02 preparation passed: 32 tests, an actual
resource preflight and four short functional/cancellation checks. See the
[verification record](runtime_io_v22_preparation_verification.md) and
[external launch guide](runtime_io_v22_execution.md). A fresh root inventory needs
local sudo authentication and was checked by the launcher before V22 collection.
Its yield-off design tests the queue account, not the yielding interaction.

The current [short draft](runtime_io_short_working_draft.md) focuses on the
capacity-estimate comparison. The [novelty/generality review](runtime_io_novelty_generality_review.md)
defines its modest scope. V23 generation-01 preparation passed46 regressions,
one actual resource preflight and eight short functional/cancellation checks;
owned resources were removed. Its two-size/two-timescale performance extension
remains unrun. Use the [V23 launch guide](runtime_io_v23_execution.md) after fully
quitting the app, with fresh observer review and the90-minute session limit.

The original shorter-period CPU/job penalty and later opposite-direction results
are retained observations. Their historical cause remains unresolved. The
execution-state pilot demonstrated measurement/control feasibility, but did not
consistently reproduce a large period interaction. Its remaining four cells were
completed in a separate session with a fresh baseline. All sixteen intended
labels are available across two sessions, not as an uninterrupted study.

The queue/backlog account predicts much of the original deadline loss from
measured service capacity. It does not explain why capacity itself changes.
No programming-language defect, historical CPU-speed cause, collection-overhead
cause or novelty claim has been established. The recommended next work is the
existing queueing analysis and paper synthesis; no new performance run is
authorized by this catalogue.

## Completed analyses and performance comparisons

| Investigation / question | Retained outcome and limit | Entry point |
|---|---|---|
| V22 scientific design, Step 3 | Question, calibration-only models, exact vectors, validation order, criteria and bounds frozen in revision1. Unchanged by implementation or result review. | [Frozen question/protocol](runtime_io_v22_frozen_question.md); [design and checks](../analysis/runtime_io_v22_design/20261007) |
| V22 implementation/preparation, Step 4 | Generation-02 sealed;32 tests, actual resource preflight and four short functional/cancellation cases passed. Subsequent collection completed as recorded below. | [Preparation verification](runtime_io_v22_preparation_verification.md); [execution guide](runtime_io_v22_execution.md); [review receipt](../analysis/runtime_io_v22_preparation_review/20261007/report.json) |
| V22 completed prospective validation | All12 primary checks passed; supporting queue/rejection/recovery, even screen and baseline advantage passed. One work size/host/service, yielding off. | [Findings](runtime_io_v22_findings.md); [result review](../analysis/runtime_io_v22_result_review/20261007/report.json) |
| Short draft and V23 generality extension | Modest capacity-estimate comparison target. V23 revision1 frozen and generation-01 prepared;46 tests, resource preflight and eight short HTTP/cancellation checks passed. Research collection unrun. | [Short draft](runtime_io_short_working_draft.md); [scope review](runtime_io_novelty_generality_review.md); [V23 design](runtime_io_v23_frozen_question.md); [preparation review](../analysis/runtime_io_v23_preparation_review/20261007/report.json) |
| Original V20: yielding and quota period | Sixteen trials complete. Yielding removes most post-computation handler delay, while queue waiting dominates residual misses. Short period increases whole-service CPU/job about 5.6% in the yield-off comparison. | [V20 findings](runtime_io_v20_findings.md); [original report](../analysis/runtime_io_v20_execution_delay/generation-03/analysis/1791215103576116652/report.md) |
| Arrival, admission, queue and recovery reconstruction | Raw request joins and held-out capacity-based queue predictions support burst overload as the main account of deadline misses, conditional on observed capacity. | [Backlog findings and replay instructions](runtime_io_v20_backlog_findings.md); [review results](../analysis/runtime_io_v20_backlog_review/20261005/report.json) |
| CPU-cost pilot, sometimes called V21 | Sixteen trials complete; shorter-period penalty absent. Full-service hardware observer fails its 1% qualification margin. Pilot collection context differs from V20. | [Pilot findings](runtime_io_period_cost_pilot_findings.md); [report](../analysis/runtime_io_period_cost_pilot/generation-02/analysis/1791227322172383591/report.md) |
| Original/pilot protocol and raw-arithmetic audit | Shared sources, binaries, workload and resource contract checked; no recorded mismatch explains the reversal. Added helper/timing and historical operating state remain limitations. | [Reversal audit](runtime_io_period_reversal_audit.md); [reproducible review](../analysis/review_period_reversal.py) |
| Faithful V20 repeat | Original runner, sixteen trials, no pilot helper/counters. Shorter period improves CPU/job about 1.3%. Pilot-only collection is unnecessary for that later direction. | [Repeat findings](runtime_io_v20_repeat_findings.md); [report](../analysis/runtime_io_v20_execution_delay/generation-04/analysis/1791263686578222719/report.md) |
| Software / Go audit | Environment, hashes, vet, race checks and exercised workload paths reviewed. No explanatory defect found; passing checks are not proof that every bug or runtime effect is absent. Initial host trace-path failure and container follow-up both retained. | [Software findings](runtime_io_software_audit_findings.md); [initial audit](../analysis/runtime_io_software_audit/audit-01/report.json); [container follow-up](../analysis/runtime_io_software_audit/audit-01/container_followup/report.json) |
| Tool installation and collection context | Tools were installed before original V20. Installation itself does not separate the sessions; active use and persistent effects remain distinct questions. | [Tools audit](runtime_io_period_tools_audit.md) |
| Short default-GC versus GC-off screen | Eight trials complete. No large, consistent CPU-period interaction; original penalty absent. Does not retrospectively exclude GC in the original session. | [GC findings](runtime_io_gc_screen_findings.md); [report](../analysis/runtime_io_gc_screen/generation-01/analysis/1791269097990204124/report.md) |
| Leftover-observer inventory and ownership review | No unexplained experimental observer in the reviewed snapshot. BPF flags were attributed/reviewed, not deleted. Snapshot cannot prove historical absence. | [Ownership findings](runtime_io_leftover_observer_findings.md); [root inventory](../analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.json); [review](../analysis/runtime_io_leftover_observer_audit/audit-20261006-root-01.review.json) |
| Minimal SHA versus full service | Seven of eight cells completed before the whole-screen timeout. Minimal comparisons show approximately 11–14% short-period CPU penalties; HTTP and application queues are unnecessary for those observed penalties. Hardware counters were absent. | [Protocol](runtime_io_minimal_computation_screen.md); [partial report](../analysis/runtime_io_minimal_computation_screen/generation-02/partial_analysis/1791292967721661400/report.md) |
| Minimal counter closing comparison | Eight trials complete after longer settling. Small short-period improvements; nearly unchanged instructions/job; current observer checks pass. Current counters cannot diagnose earlier uncounted penalties. | [Closing findings](runtime_io_period_reversal_closing_findings.md); [report](../analysis/runtime_io_minimal_counter_closing/generation-03/analysis/1791298178262469654/report.md) |
| Automatic versus constrained execution state | Twelve cells completed; first-block feasibility gate passed. Slower measured execution raised CPU/job with essentially fixed instruction work, but no large complete-block period interaction. A constrained counted cell has an unresolved system-CPU anomaly. | [Partial findings](runtime_io_execution_state_partial_findings.md); [partial report](../analysis/runtime_io_execution_state_pilot/generation-02/partial_analysis/1791313749375911467/report.md) |
| Remaining automatic-state cells with fresh baseline | Four cells complete. Short-period CPU/job improves 0.65% uncounted and 0.39% counted; observer checks pass. Combined second-block interaction is cross-session descriptive evidence. | [Latest findings](runtime_io_execution_state_continuation_findings.md); [report](../analysis/runtime_io_execution_state_continuation/generation-01/analysis/1791342475330161615/report.md) |
| Prior-work and paper-scope reviews | Targeted closest-work matrix complete. Broad quota/burst/yield/modelling claims have precedents; quantified diagnostic case study is a candidate, not certified novelty. Historical opposite directions remain valid scoped observations. | [Contribution matrix](runtime_io_contribution_matrix.md); [source/search register](../analysis/runtime_io_contribution_review/20261007/sources.json); [period literature synthesis](runtime_io_period_literature_synthesis.md); [prior-art review](runtime_io_prior_art_review.md); [paper scope](runtime_io_paper_scope.md) |
| Pre/post-restart system evidence | Different boot IDs; three compared fields changed, with no attempted-read/command coverage gaps. Descriptive configuration/activity record, not a causal reboot experiment or benchmark baseline. | [Snapshot context and open questions](runtime_io_restart_snapshot_and_open_questions.md); [current comparison](../analysis/runtime_io_system_state_snapshots/1791345410664662815-comparison.json); [evidence map C11](runtime_io_evidence_map.md) |

## Incomplete, repaired, superseded and unrun attempts

Trial directories can exist even when measurement never began. Use sealed
completion/replay status and reports rather than counting directories as trials.

| Attempt | Actual disposition | Preserved location |
|---|---|---|
| V20 generations 01 and 02 | Preparation/cleanup records; no performance trial directories. Generation 03 is the original completed study. | [V20 generations](../analysis/runtime_io_v20_execution_delay) |
| CPU-cost pilot generation 01 | Preparation only; performance results are in generation 02. | [Pilot generations](../analysis/runtime_io_period_cost_pilot) |
| Longer GC probe generation 01 | Prepared, no performance trials. Replaced for screening by the completed shorter GC study; do not describe the longer probe as executed. | [Probe protocol](runtime_io_gc_probe.md); [preparation](../analysis/runtime_io_gc_probe/generation-01/preparation) |
| Minimal computation generation 01 | Preparation only; observer ownership gate reviewed before generation 02. | [Minimal generations](../analysis/runtime_io_minimal_computation_screen) |
| Minimal computation generation 02 final cell | Whole-screen 45-minute ceiling reached during settling; seven completed cells retained separately. | [Interruption](../analysis/runtime_io_minimal_computation_screen/generation-02/interruption.json); partial report above |
| Minimal closing generation 01 | Preparation only. | [Closing generations](../analysis/runtime_io_minimal_counter_closing) |
| Minimal closing generation 02 | First-cell settling failed under the shorter timeout; no completed performance comparison. Later generation 03 completed. | [Failed-attempt report](../analysis/runtime_io_minimal_counter_closing/generation-02/closing_analysis/1791295409385777239/report.md) |
| Background ChatGPT/app crossover | Prepared, then cancelled by the user before performance collection because original records showed the app absent. Not experimental evidence against an app effect. | [Protocol](runtime_io_v20_background_app.md); [preparation](../analysis/runtime_io_v20_background_app/generation-01/preparation) |
| Execution-state pilot generation 01 | First measurement reached replay, which failed on an undefined environment variable. Original attempt retained; repair/regression review does not promote it into a completed valid trial. | [Repair review](../analysis/runtime_io_execution_state_pilot/generation-01/validation_repair_review/1791307508181918908/report.md); [interruption](../analysis/runtime_io_execution_state_pilot/generation-01/interruption.json) |
| Execution-state pilot generation 02 interruption | Twelve completed cells retained. Failed next cell was thermally steady but below the old baseline band. Whole-session host log was truncated during failure cleanup; sealed per-trial evidence has separate coverage. | [Interruption](../analysis/runtime_io_execution_state_pilot/generation-02/interruption.json); [host-monitor failure](../analysis/runtime_io_execution_state_pilot/generation-02/host_monitor_failure.json); partial findings above |
| Desktop activity, fresh-boot, collection-bundle, evenly spread arrivals and other suggested comparisons | Discussed/proposed avenues, not automatically completed experiments. Consult dated proposals and actual generation evidence before claiming an intervention was run. | [Earlier reversal proposal](runtime_io_period_reversal_next_test.md); [tools proposals](runtime_io_period_tools_audit.md); [GC discussion](runtime_io_gc_screen_findings.md); [V20 next-step plan](runtime_io_v20_next_steps.md) |
| Worker-core boost enabled/disabled by quota period | Bounded design saved, then shelved when the user chose to close the reversal branch. No boost changes or performance trials. | [Boost-screen design](runtime_io_boost_screen_plan.md) |
| V22 prospective capacity/queue validation | Completed with independent calibration and frozen predictions; all primary/supporting screens passed as recorded above. V23 is the separate unrun extension. | [V22 findings](runtime_io_v22_findings.md); [historical plan](runtime_io_v22_prospective_queue_plan.md) |

## Earlier research trail

The repository retains the work preceding V20. Start from the corresponding
dated protocol/findings and the actual result directories rather than the old
current-status paragraphs:

- [V5 review](runtime_io_v5_delay_review.md), [V6 verification](runtime_io_v6_verification.md), [V7 verification](runtime_io_v7_verification.md).
- V8 [yield findings](runtime_io_v8_yield_findings.md), [queue findings](runtime_io_v8_queue_findings.md), [long-wait findings](runtime_io_v8_long_wait_findings.md).
- [V9 candidate](runtime_io_v9_candidate.md), [V10 probe](runtime_io_v10_pending_probe_commands.md), [V11 brief](runtime_io_v11_literature_problem_brief.md).
- [V12 verification](runtime_io_v12_parallelism_verification.md), [tradeoff review](../analysis/runtime_io_v12_tradeoff_review/report.md), [deadline/gap audit](../analysis/runtime_io_v12_tradeoff_review/gap_audit_and_completion_deadlines.md).
- [V13 protocol](runtime_io_v13_completion_protocol.md), [V14 protocol](runtime_io_v14_ablation_protocol.md), [V15 verification](runtime_io_v15_preparation_verification.md), [V16 protocol](runtime_io_v16_repeatability_protocol.md), [V17 verification](runtime_io_v17_preparation_verification.md).
- V18 [kernel fixtures](runtime_io_v18_kernel_fixtures.md), [observer cost](runtime_io_v18_observer_cost.md), [service preparation](runtime_io_v18_service_preparation_verification.md).
- [V19 residual findings](runtime_io_v19_residual_findings.md) and [worker-control protocol](runtime_io_v19_worker_control.md).
- [Earlier diagnostic result sessions](../results/diagnostic) and [analysis tree](../analysis) retain raw evidence and reviews, including interrupted/retired branches. A protocol link alone is not a completion claim.

## Returning to this later

1. Read the latest continuation findings and this catalogue before following an
   older document's next-step instructions.
2. Choose the exact session/generation. Preserve its raw files, preparation,
   source snapshots, hashes/seals, trial derivations, host/control records and
   interruption receipts together. Do not overwrite earlier attempts.
3. Use the linked offline reviewer or that session's documented replay procedure
   before making a new inference. Recheck runtime prerequisites and boot-bound
   observer evidence before preparing any new performance collection.
4. A useful reopening should supply new evidence that distinguishes competing
   explanations, ideally measurements taken while the sizable penalty occurs.
   Later near-null counter measurements cannot retrospectively name its cause.

Outstanding questions: historical execution state; runtime/software work during
the penalty; cycle/stall behavior during that state; temporal versus average CPU
delivery; collection/workload-history effects; the isolated system-CPU anomaly.
These are unresolved possibilities, not established causes or a list of all
mechanisms conclusively excluded.
