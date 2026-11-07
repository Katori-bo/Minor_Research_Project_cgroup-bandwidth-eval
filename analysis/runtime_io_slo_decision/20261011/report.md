# SLO decisions: fixed offline audit

11 October 2026. Known-outcome development; no new collection, manuscript change or independent confirmation.

The illustrative SLO is <=5% failed/late offers in a complete target window. Finite observed compliance is not a population certificate.

## Calibration 95th-percentile deadline: ordinary reference

| Campaign | Cohorts | Meets decisions | False assurances | False assurances with error <=5 pp | False assurances with conditional family lower >5% | MAE (pp) |
|---|---:|---:|---:|---:|---:|---:|
| Go V31 | 18 | 18 | 6 | 6 | 0 | 0.921 |
| NGINX original | 18 | 18 | 1 | 0 | 1 | 4.741 |
| NGINX power | 24 | 24 | 4 | 0 | 4 | 10.111 |
| NGINX rate | 12 | 12 | 0 | 0 | 0 | 2.278 |
| NGINX panel | 24 | 24 | 14 | 12 | 2 | 2.375 |

The 95th-percentile reference meets its own empirical 5% budget by construction. This is self-fit, not proof of accurate transfer. Nearest ranks, strict deadline exceedance and failure mass are fixed before scoring.

## All fixed deadline labels and information-matched controls

| Campaign | Deadline label | Method | Point false assurance / meets | Point unnecessary rejection | IID-band false assurance / meets | IID-band inconclusive / cells |
|---|---|---|---:|---:|---:|---:|
| Go V31 | historical/10 | reference | 0/0 | 0 | 0/0 | 0/18 |
| Go V31 | historical/10 | recent25 | 0/0 | 0 | 0/0 | 0/18 |
| Go V31 | historical/10 | weighted_update | 0/0 | 0 | 0/0 | 0/18 |
| Go V31 | historical/11 | reference | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | historical/11 | recent25 | 0/16 | 2 | 0/0 | 18/18 |
| Go V31 | historical/11 | weighted_update | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | historical/12 | reference | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | historical/12 | recent25 | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | historical/12 | weighted_update | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/9/10 | reference | 0/0 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/9/10 | recent25 | 4/4 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/9/10 | weighted_update | 0/0 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/19/20 | reference | 6/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/19/20 | recent25 | 3/10 | 5 | 0/0 | 18/18 |
| Go V31 | slo_grid/19/20 | weighted_update | 5/14 | 3 | 0/0 | 18/18 |
| Go V31 | slo_grid/39/40 | reference | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/39/40 | recent25 | 0/14 | 4 | 0/0 | 18/18 |
| Go V31 | slo_grid/39/40 | weighted_update | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/99/100 | reference | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/99/100 | recent25 | 0/17 | 1 | 0/0 | 18/18 |
| Go V31 | slo_grid/99/100 | weighted_update | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/199/200 | reference | 0/18 | 0 | 0/0 | 18/18 |
| Go V31 | slo_grid/199/200 | recent25 | 0/17 | 1 | 0/0 | 18/18 |
| Go V31 | slo_grid/199/200 | weighted_update | 0/18 | 0 | 0/0 | 18/18 |
| NGINX original | historical | reference | 0/0 | 0 | 0/0 | 0/18 |
| NGINX original | historical | recent25 | 0/0 | 0 | 0/0 | 2/18 |
| NGINX original | historical | weighted_update | 0/0 | 0 | 0/0 | 0/18 |
| NGINX original | slo_grid/9/10 | reference | 0/0 | 2 | 0/0 | 0/18 |
| NGINX original | slo_grid/9/10 | recent25 | 8/9 | 1 | 0/0 | 18/18 |
| NGINX original | slo_grid/9/10 | weighted_update | 0/0 | 2 | 0/0 | 0/18 |
| NGINX original | slo_grid/19/20 | reference | 1/18 | 0 | 0/0 | 18/18 |
| NGINX original | slo_grid/19/20 | recent25 | 1/13 | 5 | 0/0 | 18/18 |
| NGINX original | slo_grid/19/20 | weighted_update | 1/13 | 5 | 0/0 | 18/18 |
| NGINX original | slo_grid/39/40 | reference | 1/18 | 0 | 0/0 | 18/18 |
| NGINX original | slo_grid/39/40 | recent25 | 1/15 | 3 | 0/0 | 18/18 |
| NGINX original | slo_grid/39/40 | weighted_update | 1/18 | 0 | 0/0 | 18/18 |
| NGINX original | slo_grid/99/100 | reference | 1/18 | 0 | 1/18 | 0/18 |
| NGINX original | slo_grid/99/100 | recent25 | 1/18 | 0 | 0/0 | 18/18 |
| NGINX original | slo_grid/99/100 | weighted_update | 1/18 | 0 | 1/18 | 0/18 |
| NGINX original | slo_grid/199/200 | reference | 1/18 | 0 | 1/18 | 0/18 |
| NGINX original | slo_grid/199/200 | recent25 | 1/18 | 0 | 0/0 | 18/18 |
| NGINX original | slo_grid/199/200 | weighted_update | 1/18 | 0 | 1/18 | 0/18 |
| NGINX power | historical | reference | 0/12 | 0 | 0/12 | 0/24 |
| NGINX power | historical | recent25 | 0/12 | 0 | 0/0 | 13/24 |
| NGINX power | historical | weighted_update | 0/12 | 0 | 0/12 | 0/24 |
| NGINX power | historical | pooled_policy | 0/0 | 12 | 0/0 | 0/24 |
| NGINX power | slo_grid/9/10 | reference | 0/0 | 19 | 0/0 | 0/24 |
| NGINX power | slo_grid/9/10 | recent25 | 1/18 | 2 | 0/0 | 21/24 |
| NGINX power | slo_grid/9/10 | weighted_update | 0/0 | 19 | 0/0 | 12/24 |
| NGINX power | slo_grid/9/10 | pooled_policy | 2/12 | 9 | 0/0 | 12/24 |
| NGINX power | slo_grid/19/20 | reference | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/19/20 | recent25 | 1/20 | 1 | 0/0 | 22/24 |
| NGINX power | slo_grid/19/20 | weighted_update | 1/20 | 1 | 0/0 | 24/24 |
| NGINX power | slo_grid/19/20 | pooled_policy | 2/12 | 10 | 0/0 | 12/24 |
| NGINX power | slo_grid/39/40 | reference | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/39/40 | recent25 | 1/21 | 0 | 0/0 | 22/24 |
| NGINX power | slo_grid/39/40 | weighted_update | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/39/40 | pooled_policy | 2/12 | 10 | 2/12 | 0/24 |
| NGINX power | slo_grid/99/100 | reference | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/99/100 | recent25 | 1/21 | 0 | 0/0 | 22/24 |
| NGINX power | slo_grid/99/100 | weighted_update | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/99/100 | pooled_policy | 2/12 | 10 | 2/12 | 0/24 |
| NGINX power | slo_grid/199/200 | reference | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/199/200 | recent25 | 1/21 | 0 | 0/0 | 22/24 |
| NGINX power | slo_grid/199/200 | weighted_update | 4/24 | 0 | 0/0 | 24/24 |
| NGINX power | slo_grid/199/200 | pooled_policy | 2/12 | 10 | 2/12 | 0/24 |
| NGINX rate | historical | reference | 0/0 | 0 | 0/0 | 0/12 |
| NGINX rate | historical | recent25 | 0/0 | 0 | 0/0 | 0/12 |
| NGINX rate | historical | weighted_update | 0/0 | 0 | 0/0 | 0/12 |
| NGINX rate | historical | rate_matched | 0/0 | 0 | 0/0 | 0/12 |
| NGINX rate | slo_grid/9/10 | reference | 0/0 | 1 | 0/0 | 0/12 |
| NGINX rate | slo_grid/9/10 | recent25 | 6/6 | 1 | 0/0 | 12/12 |
| NGINX rate | slo_grid/9/10 | weighted_update | 0/0 | 1 | 0/0 | 1/12 |
| NGINX rate | slo_grid/9/10 | rate_matched | 0/0 | 1 | 0/0 | 12/12 |
| NGINX rate | slo_grid/19/20 | reference | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/19/20 | recent25 | 0/8 | 4 | 0/0 | 12/12 |
| NGINX rate | slo_grid/19/20 | weighted_update | 0/8 | 4 | 0/0 | 12/12 |
| NGINX rate | slo_grid/19/20 | rate_matched | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/39/40 | reference | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/39/40 | recent25 | 0/11 | 1 | 0/0 | 12/12 |
| NGINX rate | slo_grid/39/40 | weighted_update | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/39/40 | rate_matched | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/99/100 | reference | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/99/100 | recent25 | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/99/100 | weighted_update | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/99/100 | rate_matched | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/199/200 | reference | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/199/200 | recent25 | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/199/200 | weighted_update | 0/12 | 0 | 0/0 | 12/12 |
| NGINX rate | slo_grid/199/200 | rate_matched | 0/12 | 0 | 0/0 | 12/12 |
| NGINX panel | historical | reference | 0/12 | 0 | 0/12 | 0/24 |
| NGINX panel | historical | recent25 | 0/12 | 0 | 0/0 | 12/24 |
| NGINX panel | historical | weighted_update | 0/12 | 0 | 0/12 | 0/24 |
| NGINX panel | historical | pooled_policy | 0/0 | 12 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/10 | reference | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/10 | recent25 | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/10 | weighted_update | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/10 | pooled_policy | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/4 | reference | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/4 | recent25 | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/4 | weighted_update | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/4 | pooled_policy | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/2 | reference | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/2 | recent25 | 0/0 | 0 | 0/0 | 3/24 |
| NGINX panel | original_panel/1/2 | weighted_update | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/1/2 | pooled_policy | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/3/4 | reference | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/3/4 | recent25 | 0/0 | 0 | 0/0 | 18/24 |
| NGINX panel | original_panel/3/4 | weighted_update | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/3/4 | pooled_policy | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/9/10 | reference | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | original_panel/9/10 | recent25 | 7/7 | 0 | 0/0 | 24/24 |
| NGINX panel | original_panel/9/10 | weighted_update | 0/0 | 0 | 0/0 | 3/24 |
| NGINX panel | original_panel/9/10 | pooled_policy | 12/12 | 0 | 0/0 | 12/24 |
| NGINX panel | slo_grid/9/10 | reference | 0/0 | 0 | 0/0 | 0/24 |
| NGINX panel | slo_grid/9/10 | recent25 | 7/7 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/9/10 | weighted_update | 0/0 | 0 | 0/0 | 3/24 |
| NGINX panel | slo_grid/9/10 | pooled_policy | 12/12 | 0 | 0/0 | 12/24 |
| NGINX panel | slo_grid/19/20 | reference | 14/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/19/20 | recent25 | 6/13 | 3 | 0/0 | 24/24 |
| NGINX panel | slo_grid/19/20 | weighted_update | 6/13 | 3 | 0/0 | 24/24 |
| NGINX panel | slo_grid/19/20 | pooled_policy | 5/12 | 3 | 0/0 | 12/24 |
| NGINX panel | slo_grid/39/40 | reference | 8/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/39/40 | recent25 | 6/19 | 3 | 0/0 | 24/24 |
| NGINX panel | slo_grid/39/40 | weighted_update | 8/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/39/40 | pooled_policy | 2/12 | 6 | 2/12 | 0/24 |
| NGINX panel | slo_grid/99/100 | reference | 0/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/99/100 | recent25 | 0/23 | 1 | 0/0 | 24/24 |
| NGINX panel | slo_grid/99/100 | weighted_update | 0/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/99/100 | pooled_policy | 0/12 | 12 | 0/12 | 0/24 |
| NGINX panel | slo_grid/199/200 | reference | 0/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/199/200 | recent25 | 0/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/199/200 | weighted_update | 0/24 | 0 | 0/0 | 24/24 |
| NGINX panel | slo_grid/199/200 | pooled_policy | 0/12 | 12 | 0/12 | 0/24 |

Zero meets decisions means no assurance coverage, not demonstrated safety. DKW bands are conditional common-population sampling illustrations; they do not cover future drift. Warmup controls decide later and consume the same last 25 offers. The acquired pools and full warmups remain charged.

## Target uncertainty and scope

All 96 cohorts and 732 finite labelled deadline cells are retained. Exact Clopper-Pearson target intervals are provided per cell and at Bonferroni family alpha .05. Within-target IID Bernoulli behavior and independence from calibration are unverified. Family correction needs no independence between labelled cells. These calculations do not identify physical drift or the historical cause.

Rows include all point/band confusion counts, signed error and budget slack, 95% and family target intervals, complete acquired-cost counts, policy subgroups, six-block 95th-percentile counts and retained observations. Deadline-specific counts share cohorts and calibration; no pooled independent-risk estimate or method ranking is made.

Historic Go 10/11/12 ms, NGINX historical and fresh original-panel forecasts reconcile with saved outcomes. New calibration-only deadline questions and decisions remain development despite the information boundary. V30 is outside this ordinary-CDF audit, and friend-owned V31 remains pending. The manuscript and prior scientific decisions are unchanged.

Read-only replay: `python3 -B analysis/audit_slo_decisions.py --verify`.
