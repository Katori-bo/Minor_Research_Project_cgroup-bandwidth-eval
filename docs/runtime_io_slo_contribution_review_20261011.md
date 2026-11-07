# SLO decision reliability: contribution review

11 October 2026. Targeted primary-source comparison and read-only inspection of
sealed development results. No new performance data, predictor, observer,
manuscript revision, external registration or V31 contract change.

## Decision

Continue the **empirical contribution route**, with a narrower claim:

> Under the recorded Linux CPU quotas, we quantify how the tested calibration
> procedures translate forecast errors into incorrect SLO assurances, unnecessary
> rejections and unavailable answers, retaining acquisition costs and adverse
> transfer outcomes. Existing campaigns establish development evidence for the
> decision question; independent decision confirmation remains outstanding.

The broad question remains useful: **When does calibrated tail-latency prediction
provide useful SLO decision reliability under CPU quotas?** The current evidence
answers it through scoped examples, not a complete operating boundary or a rule
for recognizing trustworthy forecasts in advance.

**Originality gate: provisional, not passed.** The inspected papers establish
nearly all the conceptual ingredients. The surviving candidate is the specific
measured error–decision–coverage–cost relationship for these procedures and quota
conditions. An exact benchmark mismatch does not establish novelty. Strong
publication suitability cannot yet be concluded.

## Closest papers, claim by claim

The differences and verdicts below are our interpretation. These published
systems were not executed or shown to fail our workload. Section locators and
access limits are in the [source register](runtime_io_slo_contribution_sources_20261011.json).

| Primary work | Established capability and evaluation | What our evidence may add; limit |
|---|---|---|
| [Galileo/PERC, NSDI 2026](https://www.usenix.org/system/files/nsdi26-saxena.pdf), §§4–7, Appendix E | Bounds worst-case tail latency over environmental perturbations; evaluates empirical bound coverage, tightness, controller SLO violations, resources and overhead. Uses recent response data and active perturbations. | A finite-window classification audit of inexpensive CDF transfer, including failed ordinary remedies. Robustness, coverage and operational consequence are already present; our DKW comparison does not reproduce PERC. |
| [SuanMing, ICPE 2021](https://research.spec.org/icpe_proceedings/2021/proceedings/p165.pdf), §§2.7, 3.1.4–3.2.2 | Converts performance forecasts into threshold classifications; reports regression error alongside TP/FP/TN/FN, accuracy, F1, forecast-horizon effects and overhead. Uses tracing, historical labels and ongoing updates. | Miss-fraction decisions for all scheduled offers under quotas, with explicit forecast slack and abstention. **Reporting decision errors alongside forecast error is not a new evaluation idea.** Its target is not our complete-window 5% miss fraction. |
| [Sinan, ASPLOS 2021](https://people.csail.mit.edu/delimitrou/papers/2021.asplos.sinan.pdf), §3, especially §§3.1–3.2 | Separates immediate latency prediction from longer-horizon QoS-violation prediction, using resource and latency history to select allocations. Documents limitations of longer-horizon point prediction. | Evidence about the much simpler frozen calibration procedures at their actual decision times. We cannot claim first recognition that prediction accuracy and useful QoS decisions differ, or superiority to Sinan. |
| [CEDULE, ICAC 2018](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf), §§II.B–C, III.E | Sparse CPU-limit/load profiles and quantile regression support SLO-constrained resource decisions; profiling cost is explicit. | Policy/rate matching was insufficient or lacked the required extra advantage in specific fresh campaigns. This does not establish that CEDULE's conditioned predictor fails; quantile error and probability error are different metrics. |
| [RScale, UCC 2020](https://www.cs.utsa.edu/~plama/papers/UCC20.pdf), §§III.B–D, equation (6) | GP tail prediction uses application/container/VM metrics. Resource selection constrains posterior mean plus a multiple of standard deviation; a sliding dataset updates the model. | Quantified behavior of tested sampling-only bounds and ordinary response updates. Uncertainty-aware SLO decisions and adaptive state conditioning are prior art. Our saved data do not reproduce its inputs or posterior model. |
| [MPORA, ECRTS 2026](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html), §§5.2, 6.1–6.3 | Execution-state/allocation profiles, split residual calibration and weighted conformal bounds support deadline allocation. Discusses temporal coupling and coverage loss under distribution shift. | Client-completion calibration-transfer observations under an ordinary CPU ceiling. Neither drift-aware uncertainty nor its tradeoff with conservatism is new; MPORA has a different endpoint and richer acquisition contract. |
| [CPU-Limits kill Performance, SoCC 2025](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf), §3.2 | Demonstrates CPU-limit delays from microbursts despite similar average utilization and proposes alternative resource control. | Specific predictive and decision behavior, including recorded unthrottled transfer failures. Low-utilization quota latency is background. Our data do not identify that paper's mechanism as the cause of NGINX transfer errors. |
| [Conformal Prediction Beyond Exchangeability](https://arxiv.org/html/2202.13415v4), §§2, 3, 4.5 | Weighted predictive inference; coverage-gap bounds depend on distribution differences, with conditions on weight choice. | Sampling-band transfer failure in the tested campaigns. It neither refutes this richer inference nor establishes impossibility of useful future assurance. A calibration CDF band is not a residual-calibrated predictive set. |
| [SLO-Scaler, August 2026 preprint](https://arxiv.org/pdf/2608.18390), §§III–VI | Bayesian-LSTM uncertainty guides bottleneck-aware scaling; reports violations, resources and ablations. Requires four hours of baseline data; notes uncertainty may be understated in nonstationary environments. | A different, small-calibration empirical contract. It is a preprint and not an executed comparator. Uncertainty-gated scaling and the limitations of approximate uncertainty are not new. |
| [SLO-Aware uncertainty calibration, EDPACS 2026](https://www.tandfonline.com/doi/abs/10.1080/07366981.2026.2663080), publisher abstract only | Describes risk-weighted workload forecasting, mean/quantile/Monte Carlo decision mappings, and simulated SLO/resource outcomes. | A close decision-cost lead that further weakens a broad novelty claim. Full text was unavailable in this review; the complete assumptions and validation contract remain unresolved. |

A newly found [LLM routing study](https://arxiv.org/abs/2609.16206) also describes
hardware calibration and operational serving outcomes. Only its author abstract
was checked; it is a cross-domain lead, not evidence about CPU-quota transfer.

The earlier [deadline comparison](runtime_io_deadline_boundary_prior_work_review_20261010.md)
retains periodic-server and simulator precedents. This review does not supersede
those modeling caveats or imply a comprehensive search of every relevant paper.
Searches covered named nearest neighbors and combinations of calibration,
tail prediction, quotas, SLO decision error, uncertainty and operational cost.

## What remains empirically substantive

The [sealed SLO report](../analysis/runtime_io_slo_decision/20261011/report.md)
contains five local histories, 96 target windows and 732 finite labelled cells.
They share one host and calibrations; labels and requests are not independent
replications. V30's different contract remains outside this response-CDF audit.

1. **Positive slack does not rescue a fixed 5 pp error allowance.** In the saved
   NGINX panel at calibration q97.5, the reference predicts 2.5% misses, leaving
   2.5 pp slack below the illustrative 5% budget. Eight of 24 windows exceed
   that budget; all eight forecast errors are <=5 pp. MAE is 1.778 pp. This
   extracts existing sealed results, not a newly validated subgroup or endpoint.
   It is stronger evidence than relying solely on q95's zero-slack construction.
2. **A sampling-band assurance can fail badly during transfer.** Original NGINX
   cohort 4 at calibration q99 predicts 1%; its ordinary 95% DKW upper bound is
   4.395%; the target has 113/300 misses (37.667%). This is a response-window
   mismatch, not a counterexample to DKW's assumptions or an identified cause.
3. **Some apparent safety gains merely remove useful answers.** At q95 all 96
   ordinary-reference DKW decisions are inconclusive. A forecast at the budget
   with a positive sampling radius naturally lacks clearance to assure
   compliance. The count cannot by itself establish novel uncertainty failure.
   Recent updates also incur unnecessary rejections; all confusion counts and
   decision times matter.
4. **Historical decisions provide a necessary counterexample to overclaiming.**
   The ordinary reference makes no wrong decisions at retained historical Go
   10/11/12 ms or NGINX historical endpoints under this audit's 5% budget. Many
   are far from the boundary. Good historical decisions and new boundary failures
   must both remain visible.

Boundary flips are labels for finite observed windows. Conditional binomial
target intervals do not establish offer independence or population noncompliance.
The 8/24 result must not become a general false-assurance-rate estimate.

## What would make this a stronger contribution

| Gate | Current position | Required evidence |
|---|---|---|
| Distinct empirical question | Plausible, narrow | Show that these measured transfer/decision/cost results add insight beyond the nearest papers, rather than just a new workload label |
| Prospective decision validity | Missing | Fresh outcomes under a separately frozen decision protocol; all endpoints and failed/domain cases retained |
| Practical relevance | Incomplete | Externally supplied fixed SLOs or a clearly labelled standardized stress test; report positive and zero margins separately |
| Useful remedy evaluation | Development only | Joint assurance errors, unnecessary rejections, coverage and full cost; no success from abstaining everywhere |
| Breadth | One local host | Independent host/campaign evidence; successful V31 alone does not confirm NGINX or the new deadlines |
| Mechanism or new method | Absent | Not necessary for a scoped empirical paper, but neither can be claimed |

The [bounded evaluation draft](runtime_io_slo_independent_evaluation_draft_20261011.md)
turns the prospective gate into a concrete specification. It is **not a finalized
preregistration or a launchable protocol**. Apparatus portability, operational
deadline selection and timing cost must be resolved before freezing collection.

Continue V31 only under its already prepared separate handoff. The current
Intel package explicitly predeclares a complete-response CDF secondary control;
its original primary forecast/decision gates remain unchanged. Newly selected
q95/q97.5/q99 analyses of returned data would be supplementary development unless
registered before relevant outcomes and protected by a verifiable information
boundary. We have no evidence that such an extension was registered. Do not
modify that package or describe a future favorable result as confirming this audit.

**Next priority:** finish the independent decision design's feasibility and
information boundary, then freeze it before collecting any outcomes. If the
nearest-work comparison cannot support a useful distinct empirical insight,
retain the existing paper as a case study rather than inventing a predictor.
Observer hardware collection stays held.

## Verification

The prior SLO sealed replay passes for all 96 cohorts, interval arithmetic and
protected current files. The positive-slack counts above are checked directly
against that sealed JSON. A companion review receipt hashes this review, draft,
source register and consumed local evidence. No raw data, historical seals,
manuscript, launcher or acceptance gate is edited.
