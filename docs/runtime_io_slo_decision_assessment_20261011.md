# Calibration accuracy and SLO decision failure

11 October 2026. Offline development audit of saved campaigns. No experiment started, manuscript edited, host state changed, or independent replication claimed.

Calibration can appear accurate and still give false assurance when its signed underprediction exceeds the remaining margin to the SLO boundary. A second failure occurs when a sampling interval for the calibration population is treated as assurance about a future window whose distribution may differ. The saved campaigns exhibit both patterns at newly selected calibration-only deadlines. They do not show incorrect ordinary-reference decisions at the historical frozen endpoints under this audit's illustrative 5% budget.

## Decision contract

The illustrative SLO permits at most 5% of all scheduled offers to fail or complete after deadline D in a complete target window. Completion exactly at D is timely; a miss fraction exactly 5% meets the budget. Failed offers remain in the denominator and count as misses. This is an empirical window decision, not a claim about an unknown future population.

Write b for the miss budget, p-hat for the forecast, and p-window for the observed target fraction. False assurance occurs when p-hat <= b < p-window. Equivalently, signed underprediction p-window - p-hat exceeds forecast slack b - p-hat. A 5-percentage-point error allowance cannot preserve decisions when slack is smaller than 5 points. Low mean error also does not bound errors in individual windows.

The audit includes all 96 target cohorts in five local campaigns, retains historical endpoints and the fresh panel's original cutoffs, and adds the same calibration-only nearest-rank grid: q90, q95, q97.5, q99, q99.5. Predictions for all cohorts were constructed before the audit loaded target raw offers. Historical outcomes were already known: this ordering makes the computation reproducible, not independently confirmatory. V30 uses a different model contract and is excluded; friend-owned independent V31 remains pending.

## Observed failures

At q95, the ordinary reference predicts compliance by construction. The following are errors against observed target windows, not estimates of an independent population false-assurance rate.

| Campaign | Cohorts / predicts meets | Observed false assurances | False assurances with absolute error <=5 pp | Mean absolute error (pp) | False assurances with conditional family target lower bound >5% |
|---|---:|---:|---:|---:|---:|
| Go V31 | 18 / 18 | 6 | 6 | 0.921 | 0 |
| NGINX original | 18 / 18 | 1 | 0 | 4.741 | 1 |
| NGINX power | 24 / 24 | 4 | 0 | 10.111 | 4 |
| NGINX rate | 12 / 12 | 0 | 0 | 2.278 | 0 |
| NGINX fresh panel | 24 / 24 | 14 | 12 | 2.375 | 2 |

The fresh panel's 2.375 pp mean error is descriptive at this new q95 question; it does not reverse that campaign's failed original worst-cutoff accuracy gates. Calibration self-fit is not independent validation of forecast accuracy. Cohorts share calibrations and deadline labels; do not pool these counts into an independent statistical claim.

Two concrete examples:

- Fresh NGINX panel cohort 2, P1, q95 D=17.286004 ms: forecast 5%, observed 7%. Error is only 2 pp, yet the point decision flips. The family-corrected target lower bound is 2.532%, so this individual window does not establish population noncompliance under that conditional model.
- Original NGINX cohort 4, q99 D=21.608002 ms: forecast 1%; ordinary 95% DKW upper bound 4.395%; target 113/300 misses = 37.667%. Even the calibration sampling-band decision says meets. The conditional family target interval is [26.966%, 49.268%]. This is a large response-window mismatch. It does not refute DKW, identify its physical cause, or establish a failure of richer drift-aware methods.

At q95 all 96 ordinary-reference DKW decisions are inconclusive. Their zero false assurances come with zero assurance coverage. Recent-25 and weighted updates sometimes reduce observed false assurances but also reject compliant windows; the full report provides both sides and acquisition costs. No universal winning method is established. At the retained historical Go 10/11/12 ms and NGINX historical endpoints, ordinary-reference point decisions all match observed windows under this budget.

## Uncertainty and interpretation

The ordinary two-sided 95% DKW bands describe calibration sampling uncertainty conditional on independent samples from a common CDF. They do not protect transfer to a changed population. The target intervals are exact Clopper-Pearson 95% intervals, plus Bonferroni 95% family intervals across all 732 finite labelled target cells. Independent Bernoulli offers within a target window and calibration/target independence are unverified. Overlapping labelled cells need no independence for the union-bound correction, but dependence within a window can invalidate the binomial premise. The intervals are conditional sensitivity calculations, not certified operational risk.

The sealed campaign summary has a cosmetic default-label limitation: absent policy metadata appears as `Go` in `q95_policy_subgroups`, including original NGINX. Use each row's campaign and explicit config metadata for subgroup interpretation. The campaign table and decisions are unaffected. Supplemental group counts retain missing policy as unrecorded and group rates by the original interval in nanoseconds.

## Evaluation that would expose this failure prospectively

1. Freeze the operational SLI, deadline, miss budget, response boundary, failure handling, decision time and allowed information before seeing new outcomes. If multiple deadlines are needed, freeze the whole calibration-only selection rule and report every selected cutoff, including unavailable ones.
2. Score chronologically held-out complete windows. Use an untouched independent host or campaign for confirmation; old windows are development evidence. Preserve policy, rate, chronological blocks, throttle observations and failed offers. An independent V31 result answers its own frozen contract unless it also prospectively registers this decision question.
3. Report false assurances, unnecessary rejections, inconclusive decisions and assurance coverage together, with signed error, forecast slack and observed budget excess. Report conditional target uncertainty separately from empirical labels. Do not let average error or abstention alone count as success.
4. Compare the ordinary reference, recent-25 control, weighted update and declared policy/rate controls at their actual decision times and full acquired cost. Evaluate uncertainty-based abstention at matched coverage or a frozen minimum useful coverage. Charge full warmup, calibration, qualification and observer costs.
5. Distinguish sampling protection from transfer protection. Freeze an explicit drift allowance or empirically justified applicability test if claiming future assurance. Examine failure across rates, policies and temporal blocks; an IID-only interval is insufficient. Plan independent window replication to resolve the decision-risk target; request-level binomial arithmetic alone is not a replication plan.

This specifies an evaluation, not authorization to restart held hardware collection. No qualified low-cost observer or useful future-population certificate has been established here.

## Contribution decision

The defensible candidate contribution is a scoped empirical account of when small tail-forecast error fails to preserve SLO decisions under calibration transfer, together with reproducible evaluation of error, margin, coverage and cost. A stronger method contribution would require a justified transfer-aware decision rule with useful coverage and independent confirmation. Neither is established by this development audit.

Generic SLO decision-making, empirical-CDF sampling bounds and robustness under perturbations already have primary-source precedent. In particular, [Saxena et al., NSDI 2026](https://www.usenix.org/system/files/nsdi26-saxena.pdf) describe Galileo/PERC tail-performance robustness certificates and controller guidance. This targeted inspection does not establish a systematic literature gap or reproduce that richer contract. See the [source register](runtime_io_slo_decision_sources_20261011.json) for inspection limits. Sampling assumptions are supported by [Reeve's DKW treatment](https://arxiv.org/html/2403.16651v1); target interval arithmetic follows [NIST's exact binomial treatment](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

Recommendation: retain this as a development result and a candidate decision-focused paper extension. Keep the observer hardware hold. Wait for independent V31 under its existing contract; freeze any additional decision evaluation before new outcomes. Do not claim a new safe controller, established cause, universal predictor failure, or confirmed novel method.

## Evidence and verification

- Frozen [protocol](runtime_io_slo_decision_protocol_20261011.md).
- [Complete computed report](../analysis/runtime_io_slo_decision/20261011/report.md), [machine results](../analysis/runtime_io_slo_decision/20261011/screen.json), and [core seal](../analysis/runtime_io_slo_decision/20261011/seal.json).
- `python3 -B -m unittest discover -s analysis -p test_slo_decisions.py -v`: ten numerical checks pass.
- `python3 -B analysis/audit_slo_decisions.py --verify`: sealed replay passes for all 96 cohorts, calibration-only decisions, uncertainty arithmetic and protected current files.
- `python3 -B analysis/verify_empirical_consolidation.py`: previous consolidation and historical replay chain pass; the manuscript remains at its pre-audit hashes.
- Supplemental assessment groups and a separate assessment seal preserve the original frozen core seal.
