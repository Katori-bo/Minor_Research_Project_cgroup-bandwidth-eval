# Combined paper assessment after the prospective decision evaluations

11 October 2026. Internal assessment of the complete available body of work,
not independent peer review. No existing manuscript, protocol, raw outcome or
historical seal was changed. No native collection or submission accompanies
this assessment.

## Verdict and proposed contribution

The combined work has sufficient empirical substance to justify preparing one
full conference submission aimed at empirical performance engineering. It is
stronger as a unified case study than as a collection of individual model
improvements. Scientific originality and acceptance remain unestablished.

Suggested title:

**From CPU Capacity to SLO Decisions: An Empirical Study of Deadline Forecasting
Under Linux CPU Quotas**

Suggested question:

**When do calibrated performance forecasts support reliable deadline and SLO
decisions for CPU-quota-limited services?**

The defensible contribution is a prospective empirical evaluation of the
successes and limitations of selected existing calibration and forecasting
procedures, connecting capacity measurement, deadline resolution, transfer,
and operational decision error. It includes credible ordinary controls,
unsuccessful remedies, fresh decision evaluations and an auditable artifact.
It does not establish a new estimator, physical cause, universal operating
boundary, competitive controller or first recognition of prediction fragility.

## Evidence included in this judgment

| Evidence layer | Result that belongs in the combined paper | Required boundary |
| --- | --- | --- |
| Original 300-trial period/concurrency study | Nominal CPU fraction alone does not characterize the observed tails; quota period, workers, load and arrivals interact | One host/Go workload; successful-request run p99 and failures remain separate; exploratory contrasts are labelled |
| Prospective capacity studies, especially V28 | Whole-run substitution has 13.494 pp deadline MAE; busy calibration 0.453; quadratic CPU-based calibration 1.169 | Shared finite FIFO and 500 ms endpoint; busy versus quadratic fails the frozen minimum-effect advantage screen |
| V29/V30/V31 deadline studies | Long-deadline adequacy does not establish short-deadline adequacy; periodic approximation succeeds at 25 ms and a fresh empirical CDF succeeds at 10 ms in its declared low-queue domain | Different frozen comparators/endpoints and domains; no universal model switch; complete-response retrospective control limits stage-decomposition novelty |
| NGINX transfer and ordinary controls | Policy matching improves some errors but is insufficient; accurate rate-matched transfer has no required incremental advantage over ordinary calibration; the deadline panel fails its frozen gates | Separate chronological campaigns, no demonstrated cause or universal matching failure; failed gates are not population impossibility results |
| Prospective Go decision supplement | One fixed primary positive-slack, <=5 pp error event; reference makes 5 wrong primary-deadline assurances among 18 targets | New same-host evidence; known historical outcomes informed study choice; no independent hardware claim |
| Prospective NGINX-only completion | All 18 targets complete; reference makes 6 wrong primary-deadline assurances, with errors >5 pp; narrow primary event occurs zero times | Explicit non-reproduction of the small-error primary event; no replacement endpoint or pooling with Go |
| Artifact and study lineage | Advance calibration/forecast barriers, all-offer accounting, raw/resource replay, costs and retained partial/unavailable attempts | Reproducibility strengthens evidence quality but supplies no estimator novelty or independent attestation |

The original experiment's successful-request p99 must not be pooled with later
all-offer deadline-miss probabilities. Calibration histories, method selection,
scientific gates and host count remain distinct. The 300 trials, request counts
and correlated deadline labels are not additional hardware replications.

## Literature and venue fit

The broad robustness question already has substantial precedent.
[Galileo/PERC, NSDI 2026](https://www.usenix.org/system/files/nsdi26-saxena.pdf)
examines environmental variability and integrates statistical tail bounds with
controllers. [SuanMing, ICPE 2021](https://research.spec.org/icpe_proceedings/2021/proceedings/p165.pdf)
already evaluates regression forecasts alongside performance-degradation
classifications. Neither was run here. Our simple empirical references and
sampling-only DKW illustrations do not reproduce their complete methods.

The surviving contribution candidate is the specific measured behavior of
inexpensive calibration procedures under ordinary Linux quota contracts,
including where numerical accuracy ceases to support useful decisions and how
ordinary remedies trade wrong assurances against rejections, coverage and
acquisition cost. A different workload label or a longer related-work table
does not establish that this insight is new. The targeted comparison in
runtime_io_slo_contribution_review_20261011.md remains the starting point;
its status must be updated for the now-completed same-host decision tests.

My venue-fit judgment is that an empirical/case-study track is a credible
primary target. The current [ICPE 2027 tracks call](https://icpe2027.spec.org/tracks-and-submissions/)
explicitly includes Empirical / Experience / Reproduction / Case Study papers
within its research track. This establishes an appropriate contribution type,
not satisfaction of its originality/evaluation requirements or acceptance.
No submission deadline or external publication action is selected here.

## How to make one paper

Keep the original studies and extension available as immutable evidence
sources. Create a new integrated manuscript with a single question and these
main sections:

1. Motivation and contribution: distinguish capacity accuracy, deadline
   accuracy and operational decision reliability; state the empirical scope.
2. Apparatus and evidence design: quota contracts, open-loop offers, endpoints,
   calibration/forecast chronology, domains, statistical units and costs.
3. Capacity and deadline adequacy: a compact original-period foundation,
   capacity comparator table and the prospective long/tight deadline contrasts.
4. Transfer limits: NGINX's adverse and successful episodes, with policy/rate
   and deadline-panel controls and explicit original gates.
5. Prospective decision reliability: separate Go/NGINX results, all methods,
   wrong assurances, unnecessary rejections, abstention/coverage and costs;
   explicitly retain NGINX's negative narrow-primary result.
6. Related-work comparison, practical implications and validity limits.

Put the full original matrix, secondary cutoff tables, candidate-search
history, observer qualification detail and failed attempt ledger in supporting
material. Moving them out of the main narrative does not delete data or change
their outcomes. Do not concatenate the three manuscripts or make the paper
follow the historical experiment identifiers.

## Remaining review risks and priority

The decisive gaps are a clearly differentiated empirical lesson, external
scope and convincing practical relevance. Most favorable contrasts involve
simple comparators with known limitations; their large improvements do not
establish superiority over state-of-the-art predictors. The 5% miss budget
and calibration-quantile deadlines are explicitly standardized stress tests,
not externally supplied production SLOs. Good case-study evidence can still
be submitted at that scope, but broad deployment claims would require more.

For a stronger submission, complete the already pending independent-host work
under its own contract, and distinguish confirmation of V31 from confirmation
of the newer decision endpoint. Replication can strengthen generality; it
cannot by itself establish novelty. No additional local predictor or favorable
repeat is required merely to justify writing this paper. The next editorial
step is a new unified manuscript; the next scientific step is precise novelty
positioning and the planned independent evidence, with observer collection held.
