# Calibration-cost contribution: first literature and adequacy screen

8 October 2026. Read-only literature assessment and paper analysis under the
[decision contract](runtime_io_calibration_cost_question_20261008.md). Targeted
primary-source search, not exhaustive firstness certification. No scientific
fits, new workload runs or prospective forecasts. Source coverage and access
limits are in the [source register](../analysis/runtime_io_calibration_novelty_screen/20261008/sources.json).

## First verdict

**Reject the broad novelty claim that we introduce accurate performance
prediction using fewer measurements, adaptive calibration, estimator selection
or uncertainty-guided experiments. These are established ideas.**

The fixed-quota all-offer deadline application remains a possible setting for
a contribution, but no specific nonroutine extra capability has yet survived
comparison. Do not start a custom selector or a fresh campaign. The justified
next step is a bounded offline adequacy assessment of reduced nonlinear fits
and ordinary direct busy calibration, followed by a single proceed/stop
decision. If they suffice at comparable or lower cost, close this candidate.

Finishing the empirical paper first is not required. Its draft and evidence are
preserved independently, with collection stopped and period selection on hold.

## Claim-versus-method comparison

The last column is our inference from the inspected sources. A difference in
target metric or scheduler is a mapping question, not an established gap.

| Primary source and inspected material | Assumptions and required observations | Output and relevant capability | Consequence for this candidate |
|---|---|---|---|
| [Kumar, Zhang and Tantawi, Enhanced Inferencing, 2009](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799), §§2.3, 3.1–3.2 | Measurements at stationary workload regimes; arrival rates, mean response and CPU utilization; chosen queueing and demand/overhead families | Joint load-dependent parameter inference; discusses experiment count, noise and iterative model fitting | Load dependence and adjusting calibration effort are prior art. Our transient FIFO quota mapping needs assessment, not dismissal. |
| [Spinner et al., Evaluating Approaches to Resource Demand Estimation, 2015](https://se.informatik.uni-wuerzburg.de/staff/samuel-kounev/publications/?cHash=093a29953fb0ac74fd2f314fcdf9bc45&tx_extbibsonomycsl_publicationlist%5Baction%5D=download&tx_extbibsonomycsl_publicationlist%5Bcontroller%5D=Document&tx_extbibsonomycsl_publicationlist%5BfileName%5D=SpCaBrKo2015-PEVA-ResDemEstSurvey.pdf&tx_extbibsonomycsl_publicationlist%5BintraHash%5D=0373ae5cb4f2bbaedd9a5a2ba28a445c&tx_extbibsonomycsl_publicationlist%5BuserName%5D=samuel.kounev), §§2–3, 4.3.1–4.3.2 | Different estimators use utilization, throughput, response or queue observations under their model assumptions | Compares accuracy as sampling interval and sample count change, among other factors | An error-versus-observation-budget comparison by itself is familiar. Full text was retrieved in this screen, improving earlier abstract-only access. |
| [Grohmann et al., Self-Tuning Resource Demand Estimation, 2017](https://se.informatik.uni-wuerzburg.de/software-engineering-group/staff/nikolas-herbst/publications/?cHash=d9fa15b1b30a31ea2b3a27bae6b8c63f&tx_extbibsonomycsl_publicationlist%5Baction%5D=download&tx_extbibsonomycsl_publicationlist%5Bcontroller%5D=Document&tx_extbibsonomycsl_publicationlist%5BfileName%5D=GrHeSpKo2017-ICAC-RDE.pdf&tx_extbibsonomycsl_publicationlist%5BintraHash%5D=0d61fe2941695054d57cc3326805ce4e&tx_extbibsonomycsl_publicationlist%5BuserName%5D=nikolas.herbst), §§III–V | Training traces, observed performance metrics, cross-validation and tunable estimator parameters | Automatically tunes estimators using discrete optimization | Automatic tuning is covered. Estimator optimization effort differs from acquiring live workload calibration; their unresolved tradeoff is not proof of ours being new. |
| [Grohmann et al., SARDE, 2021](https://se.informatik.uni-wuerzburg.de/publications/?cHash=c7300d8a02e65b7dcd8870de230e3338&tx_extbibsonomycsl_publicationlist%5Baction%5D=download&tx_extbibsonomycsl_publicationlist%5Bcontroller%5D=Document&tx_extbibsonomycsl_publicationlist%5BfileName%5D=SARDE_TaaS2020.pdf&tx_extbibsonomycsl_publicationlist%5BintraHash%5D=fc3fb3694ee15b680f1466a5acc7bc64&tx_extbibsonomycsl_publicationlist%5BuserName%5D=se-group), §§5.1–5.4, 9–10 | Continuous application/system monitoring, estimator families and an internal cross-validation error proxy | Tunes aggregation/window parameters, selects estimators and returns adaptive demand estimates | A generic selection/window rule is already covered. Whether its internal error adequately tracks our all-offer deadline error remains untested; that alone does not demonstrate a new method. |
| [Venkataraman et al., Ernest, NSDI 2016](https://www.usenix.org/system/files/conference/nsdi16/nsdi16-paper-venkataraman.pdf), §§3.2–3.3 | Batch analytic job, small input runs, features/model family and candidate experiment costs | Cost-aware optimal experiment design for performance prediction | Choosing informative low-cost experiments is established. Adapting its linear-in-parameters design to quadratic CPU calibration is an adequate alternative to assess. |
| [Alipourfard et al., CherryPick, NSDI 2017](https://www.usenix.org/system/files/conference/nsdi17/nsdi17-alipourfard.pdf), §§3.3–3.6, 4 | Representative batch workload, candidate cloud configurations, measured runtime/cost, GP and noise assumptions | Sequential experiment selection and stopping for cost optimization subject to runtime constraints | Adaptive sampling under uncertainty is covered. It does not directly establish our fixed-quota forecasting accuracy, but a deadline objective alone does not make the adaptive machinery new. |
| [Perez, Casale and Pacheco-Sanchez, Estimating Computational Requirements in Multi-Threaded Applications](https://juanfperez.com/data/2015_02_des_TSE.pdf), abstract and introduction | Response-time and resource-queue observations; threading and queueing assumptions | Regression/likelihood demand estimates using observations other than CPU utilization | Fair alternatives cannot be restricted to CPU-only fits if another method can use equally accessible request/queue observations. Detailed quota applicability is unaudited. |
| [Mazkatli et al., CIPM, 2025](https://publikationen.bibliothek.kit.edu/1000182067/160513300), abstract, Ops-time calibration passages and §12 | Architecture/code models, monitoring and changes to modeled system parameters | Adaptive monitoring, selective recalibration and self-validation | Lower monitoring/calibration overhead is already an explicit goal; its architecture requirements and incremental-update setting differ from our initial calibration task. |
| [Hummel et al., GARMA, 2026](https://publikationen.bibliothek.kit.edu/1000191876/178599444), abstract, §V and validity limits | Early design artifacts, workload/runtime descriptions and an LLM workflow | CPU-demand ranges without a running calibration system; assessed against measured CPU demand | Low-measurement demand estimation is active research. CPU-demand intervals here are not validated all-offer latency/deadline guarantees. Rich design inputs prevent treating it as a free interchangeable baseline. |

Ernest's experiment-design objective uses parameter covariance and experiment
cost. Applying such a design to the feature vector `[1, X, X²]` is our proposed
baseline mapping, not a new result attributed to Ernest. It needs care because
offered rate is controlled while completion throughput X is observed, and
quota/throttling can change the relation. Ordinary nonlinear fitting and design
must receive a fair opportunity before a custom strategy is justified.

CherryPick's published erratum corrects a swapped comparison figure:
[NSDI 2017 erratum](https://www.usenix.org/system/files/conference/nsdi17/nsdi17_errata.pdf).
No comparative numerical advantage from that figure is used here.

## Simplest alternatives on paper

The current four-versus-twelve observation count does not survive as a novelty
argument. A direct throughput estimate can be obtained from one qualified busy
trial, with repeatability/error still needing assessment. A three-coefficient
quadratic is identifiable from three distinct noiseless points; two coefficients
remain if the intercept is genuinely known. These facts do not establish real
accuracy, but defeat an assumption that the adequate competitors inherently
need twelve trials.

With V28's scheduled durations, four mixed calibrations account for 320 s of
warmup plus measurement versus 600 s for twelve idle/steady observations.
That nominal 1.875 ratio excludes drains, qualification and acquisition
overhead. Counts, elapsed measurement time, estimator computation and disruption
are different costs. The original shared sixteen-slot procedure did not test
either method at its minimum adequate budget.

An uncertainty stopping rule based only on residuals at low load is also
insufficient without assumptions: good agreement below saturation does not
determine an unobserved capacity root or future miss error. Model form,
interference and transfer assumptions must be stated. This is a standard
identifiability/model-mismatch concern, not a theorem we claim to have discovered.

## Existing-record assessment that is feasible next

1. Inventory each saved calibration observation, available counters and
   clock bounds, elapsed lifecycle and induced queue/disruption. Charge shared
   setup once and per-run expenses appropriately; do not call discarded data
   free or infer unrecorded short CPU windows.
2. Declare ordinary direct busy estimates with one/two/four complete mixed
   trials, and reduced nonlinear fits with fewer rates/repeats. Choose designs
   from calibration information or standard design rules rather than selecting
   subsets by V28 deadline error. Allow all adequate methods the same input
   availability and expose different acquisition costs.
3. Assess stability across calibration blocks and retained cases. Score all
   declared cases, failed fits and refused answers, showing nonzero-miss cases
   separately. Existing validation is a known retrospective check, not fresh
   confirmation; all subset results must carry that label.
4. Ask whether any specific proposed strategy could add a nonroutine practical
   advantage beyond the cheapest adequate baseline. Produce one bounded verdict
   before implementing a custom method. No automatic fresh campaign follows.

This is an adequacy assessment using existing methods, not permission to label
a new optimizer as novel. A materially better calibration policy might still
be possible, but its extra capability is currently unspecified and unproved.
Completing the empirical manuscript remains worthwhile regardless of this
assessment's result.

## Coverage and unresolved leads

Searches cover demand estimation, sampling/window size, estimator selection,
confidence, experimental design, adaptive profiling and recent monitoring/
calibration work. Parts of primary full texts were inspected; algorithms and
artifacts were not executed. Source/search absences do not certify originality.

Zhang et al. 2013 remains relevant through the preserved
[prior-method assessment](runtime_io_load_dependent_baseline_assessment_20261008.md);
its equation-image verification gap remains. A 2025 CARE-D paper appeared in
publisher search excerpts as few-history execution-time calibration with
CPU-resource inputs. Its full page/PDF could not be retrieved through the
browser tool, so it is an unresolved lead and is not used to claim exact
coverage or defeat this candidate. DEC confidence estimation likewise remains
a bibliographic lead without a primary full-text audit. A source's future-work
item is not evidence that the wider problem remains open.

**Current status: necessary screening scope is specified and the first novelty
search is complete; novelty is not established. Proceed only with the bounded
adequate-baseline assessment, holding custom implementation and collection.**
