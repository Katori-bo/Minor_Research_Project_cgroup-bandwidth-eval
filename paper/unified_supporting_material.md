# Supporting material: From CPU Capacity to SLO Decisions

11 October 2026. This index moves extensive investigation detail out of the
[unified manuscript](unified_manuscript.md) by reference. It preserves the
original files, endpoints, failed gates, raw data and seals. A concise narrative
does not replace any historical record. All observed performance evidence is
same-host; independent Intel evidence remains pending.

## S1. Original period/concurrency study

The [original manuscript](paper_draft.md) retains all 300 trials, matrix tables,
successful-request p99, rejection/timeout accounting, chronological collection
segments, exploratory contrasts and sensitivity models. Its raw session is
[20260921-202841](../results/sessions/20260921-202841/).
The matrix contains sixty cells and five trials per cell, not 300 hosts.
The [legacy draft](archive/paper_draft_legacy.md) remains historical.

Core retained findings: nominal fraction does not determine tails; period,
concurrency, arrivals and load interact; unlimited has a different bandwidth;
the high-burst period relation is not uniformly monotone; success-conditional
p99 excludes 23,059 rejections and seventeen timeouts, which remain separate.

## S2. Capacity and deadline contracts

The [capacity manuscript](capacity_calibration_empirical.md),
[support](capacity_calibration_supporting_material.md) and
[reproduction guide](capacity_calibration_reproducibility.md) retain equations,
calibration windows, roots/extrapolation, full error tables and V22/V23
work-size/burst comparisons. The [V28 result audit](../analysis/runtime_io_v28_result_review/20261008/report.json)
replays CPU endpoints, offer outcomes, window brackets and the independent FIFO
recurrence. Its busy-versus-quadratic verdict remains inconclusive; the
composition screen remains inconclusive. Calibration budgets are unequal.

The [deadline manuscript](deadline_resolution_extension.md),
[support](deadline_resolution_supporting_material.md) and
[reproduction guide](deadline_resolution_reproducibility.md) retain V29's four
conditions, V30's full secondary cutoff grid, phase scenarios, burst failure,
stage counts and rejected timing-identification attempt. V31's primary CDF
subtracts calibration queue wait but never subtracts target wait. Its ordinary
complete-response control remains retrospective. Observation-based applicability
does not establish an advance scope selector.

| Core result | Authoritative local record |
|---|---|
| V28 five-capacity comparison | [Result audit](../analysis/runtime_io_v28_result_review/20261008/report.json) |
| V30/V31 and original NGINX primary values | [Finalization coordinates](../analysis/runtime_io_deadline_extension_finalization/20261010/figure_data.json) and their full campaign bundles below |
| V30 frozen/complete campaign | [Generation 01](../analysis/runtime_io_v30/generation-01/) |
| V31 frozen/complete campaign | [Generation 01](../analysis/runtime_io_v31/generation-01/) |
| Current integrated historical checks | [Consolidation](../analysis/runtime_io_empirical_consolidation/20261011/) |

## S3. Transfer controls and adverse attempts

The original NGINX result, subsequent stopped power-policy pilot, completed
policy confirmation, rate-matched study and fresh panel are separate episodes.
All-offer failures and recorded throttling remain included according to each
contract; a later success does not replace an earlier negative result.

- [Power confirmation report](../analysis/runtime_io_nginx_power_confirmation_review/20261010-generation01/report.md): matching gain passes, absolute accuracy fails; zero-miss P1 lowers pooled error and does not qualify P0 reliability.
- [Rate-transfer report](../analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.md): both matched and ordinary calibration pass accuracy; required extra advantage fails; two throttling observations remain included.
- [Fresh panel report](../analysis/runtime_io_nginx_deadline_panel_review/20261010-generation01/report.md): both conditional policy upper bounds fail; all 10,530 qualification/scientific/warmup offers remain retained.
- [Transfer consolidation](../docs/runtime_io_transfer_consolidation_20261010.md) and [contribution note](deadline_transfer_contribution_note.md): interpretation, chronology and matched-information limits.
- [NGINX qualification](../docs/runtime_io_gzip_candidate_qualification_plan_20261009.md), [imgproxy first qualification](../docs/runtime_io_imgproxy_qualification_20261009.md) and [second qualification](../docs/runtime_io_imgproxy_one_cpu_qualification_v2_20261009.md): retained adverse application-screen records, not extra successful transfer confirmations.

## S4. Known-outcome development screens

The [investigation catalogue](../docs/runtime_io_investigation_catalogue.md)
and [evidence map](../docs/runtime_io_evidence_map.md) retain earlier observer,
GC, queue, execution-delay, accounting, loading and kernel investigations.
The [consolidation record](../docs/runtime_io_empirical_consolidation_20261011.md)
indexes the later fixed screens and protected history.

The later [reliability](../docs/runtime_io_forecast_reliability_assessment_20261010.md),
[pre-validation](../docs/runtime_io_prevalidation_signals_assessment_20261010.md),
[stage](../docs/runtime_io_stage_signal_assessment_20261010.md),
[continuous persistence](../docs/runtime_io_continuous_persistence_assessment_20261010.md),
[deadline scope](../docs/runtime_io_deadline_scope_assessment_20261010.md) and
[sensitivity](../docs/runtime_io_deadline_sensitivity_assessment_20261010.md)
screens were specified after outcomes were known. Favorable aggregate scores,
agreeing probe halves or small median drift never acquire prospective selector
status. Original acceptance gates and every cohort remain retained.

In particular, the agreeing continuous probe forecasts 48% misses but the
subsequent 200 offers have 79.5%, a 31.5 pp error. Median correction improves
older power-panel MAE from 18.514 to 4.930 pp but worsens original, rate and
fresh-panel histories. These diagnostics do not identify the historical cause
or a validated remedy.

## S5. Observer qualification and precision/cost

The [worker-wait qualification](../docs/runtime_io_worker_wait_qualification_assessment_20261010.md)
retains all 24 randomized overhead services and 7,890 successful offers.
Behavioral-equivalence intervals are too wide for their frozen margins:
`qualified=false`, with neither equivalence nor harm demonstrated. Predictive
usefulness was not tested. The [worker-wait cost assessment](../docs/runtime_io_worker_wait_precision_cost_assessment_20261010.md)
separates operation time from behavioral qualification.

The [warmup assessment](../docs/runtime_io_warmup_precision_cost_assessment_20261011.md)
retains all 78 calibration/warmup pairs. New-panel median interval span is
525.452 us versus empirical sensitivity radii 47.708/43.496 us. IID rank and
DKW calculations are conditional illustrations, not established future-error
coverage. The sufficient 738-offer single-window illustration adds 17,112
offers and 53.475 nominal minutes, exceeding the declared science/service caps.
It is not a minimum sample-size or power result.

The [execution-rate design](../docs/runtime_io_execution_rate_qualification_design_20261011.md)
is unimplemented and unmeasured. Substituting old observer variability yields
268.804/262.564 us halfwidths versus the proposed 20 us allowance. This planning
no-go does not establish actual new-counter variability or harm. No affordable,
qualified reliability measurement emerges from these candidates. Local observer,
longer-warmup and predictor-search branches remain closed to further collection
under the research closeout.

## S6. Decision tables, availability and costs

The [96-window development audit](../analysis/runtime_io_slo_decision/20261011/report.md)
retains all fixed endpoints and confusion/coverage tables from five historical
same-host histories. Its positive-slack boundary evidence is development, not
fresh decision confirmation. The earlier historical deadlines also include
correct decisions and remain visible.

Fresh studies have separate plans, denominators and locally registered seals:

| Allocation | Planned windows | Completed primary-domain windows | Closed unavailable | Pending | Primary event |
|---|---:|---:|---:|---:|---|
| Original local Go | 18 | 0 | 18 | 0 | Unavailable |
| Original local NGINX | 18 | 0 | 18 | 0 | Unavailable |
| Original independent Intel Go | 18 | 0 | 0 | 18 | Pending |
| Original independent Intel NGINX | 18 | 0 | 0 | 18 | Pending |
| Local supplement Go | 18 | 18 | 0 | 0 | One fixed narrow event |
| Local supplement NGINX | 18 | 0 | 18 | 0 | Unavailable |
| NGINX completion supplement | 18 | 18 | 0 | 0 | Zero fixed narrow events |
| Attempt ledger total | 126 | 36 | 54 | 36 | No pooled primary endpoint |

The [Go supplemental report](../analysis/runtime_io_slo_independent/local-supplement01-return.json)
retains all quantile and fixed-deadline tables, complete-trusted and
primary-domain views, all methods/procedures, undefined denominators and
acquisition ledgers. Its [observed review](../analysis/runtime_io_slo_independent/20261011-local-supplement01-observed-review-01/)
preserves the used launcher and receipts. The [Go result interpretation](../docs/runtime_io_slo_local_supplement_result_20261011.md)
explicitly retains its NGINX authentication failure.

The [NGINX completion report](../analysis/runtime_io_slo_independent/20261011-nginx-completion01-observed-review-01/final_report.json)
and [raw replay](../analysis/runtime_io_slo_independent/20261011-nginx-completion01-raw-replay.json)
retain the zero-event primary verdict, six larger-error assurances and all
secondary labels. The [result interpretation](../docs/runtime_io_slo_nginx_completion_result_20261011.md)
explains acquisition, preparation/readiness and the retained predecessor failures.
Its fresh result never overwrites the earlier unavailable NGINX allocations.

The [generated complete decision tables](../analysis/runtime_io_unified_closeout/20261011/decision_tables.md)
reconcile every frozen label/view/method/procedure against both saved reports.
The [cost ledger](../analysis/runtime_io_unified_closeout/20261011/decision_costs.json)
records successful and failed allocations separately, including setup cost
records; preparation snapshots are subsets and never added twice. The original
local Go failure retains 510 acquired functional offers; the original NGINX
and supplemental authentication stops retain their actual zero raw acquisitions
and nonzero elapsed time. Partial data are not assigned a complete-window label.

## S7. Novelty comparison

The [new claim-specific register](../docs/unified_claim_novelty_comparison_20261011.md)
updates the historical contribution review for the completed Go and NGINX
decision results. Its closest primary-source comparisons are explicit about
existing capabilities, what was actually executed, differences in acquisition
and endpoint, and unestablished originality. Full published predictors,
controllers and conformal methods were not reproduced.

The [historical source register](../docs/runtime_io_slo_contribution_sources_20261011.json)
retains wider literature leads and original access limitations. The
[deadline prior-work review](../docs/runtime_io_deadline_boundary_prior_work_review_20261010.md)
and [load-dependent comparator assessment](../docs/runtime_io_load_dependent_baseline_assessment_20261008.md)
remain available. Publisher-abstract-only leads are not used to establish
full-method claims in the unified text.

## S8. Independent-host scope and editorial closeout

The [independent evidence status](../docs/unified_independent_evidence_status_20261011.md)
distinguishes the prepared V31 package from the separate decision study and
lists the exact return requirements. No run received at this cutoff supplies
independent evidence. Pending cells have not been silently closed as unavailable.
No favorable local repeat, altered cutoff or imported V31 result replaces them.

The [closeout record](../RESEARCH_FINAL.md) makes the new manuscript the current
editorial entry point while historical plans, manuscript files and seals remain
unchanged. Authorship, affiliation, venue formatting and external artifact
release are publication preparation, not additional scientific findings.
No submission or upload accompanies this closeout.
