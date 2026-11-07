# Forecast reliability: primary-source capability and gap audit

10 October 2026. Targeted review for the
[bounded reliability protocol](runtime_io_forecast_reliability_protocol_20261010.md).
Ten primary sources and two additional leads were checked at the levels below.
This is not a systematic review or an execution of competing artifacts. The
implication column is our assessment of applicability, not a published claim
that those methods fail our benchmark.

## Capability matrix

| Source and inspection level | Inputs / assumptions / cost | Output | Implication for our candidate |
|---|---|---|---|
| [Linux bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html), background and caveats | Quota/period ceiling, replenishment and local runtime slices | Resource-control semantics | Quota is not continuously guaranteed CPU supply. Throttle counters do not establish latency-distribution stationarity. |
| [Li, Lu and Gill, RTSS 2019](https://www.cse.wustl.edu/~lu/papers/rtss19.pdf), indexed primary abstract/system-model passages; direct PDF fetch failed | Poisson arrivals, deterministic demand, deferrable-server parameters; Xen evaluation | Stationary response distribution and resource configuration | Periodic tail modeling is established. Our simplified Linux replay is not this implementation; scheduler/arrival differences cannot prove an unmet capability. |
| [CEDULE, ICAC 2018](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf), abstract, methodology and profiling-cost discussion | CPU-limit/load profiles and quantile regression; multiple profiling runs and credit-control premises | Tail forecasts supporting resource decisions | Profiling across loads and held-out prediction are established. Compare the cost of informative rate profiles before claiming a cheap warning adds capability. |
| [Shah et al., Selective Regression Under Fairness Criteria](https://arxiv.org/abs/2110.15403), primary abstract | Trained regression/confidence models and rejection; subgroup assumptions | Error-versus-answer-coverage behavior | Abstention is established and can worsen subgroup behavior. An overall accuracy gain while one application always loses coverage is inadequate evidence. |
| [Angelopoulos and Bates, conformal introduction](https://arxiv.org/html/2107.07511v6), algorithm, exchangeability and Appendix D rank proof | Separate residual calibration and exchangeability; additional labelled samples | Marginal prediction-set coverage | Sampling intervals and conditional accepted-forecast reliability differ. Four timing cohorts cannot be silently reclassified as independent future-error episodes. |
| [Barber et al., Conformal Prediction Beyond Exchangeability](https://arxiv.org/html/2202.13415v4), introduction, coverage-gap discussion and weight conditions | Weighted residual calibration; informative bounds on distribution differences needed for useful coverage statements | Robust predictive sets with quantified coverage loss | Drift-aware uncertainty is established. No observed bound on future drift is supplied by our calibration range. Their richer method has not been reproduced here. |
| [Gibbs and Candes, Adaptive Conformal Inference](https://arxiv.org/html/2106.00170v1), abstract and Section 2 update | Online observed prediction errors and sequential adaptation | Long-run coverage-frequency control | This uses feedback after outcomes. It is an appropriate online comparator if the contract changes, not an advance certificate for a single unseen cohort. |
| [MPORA, ECRTS 2026](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html), Sections 5.2 and 6.1-6.3 | Diverse offline state/allocation profiles, separate conformity scores, exchangeability or weighted shift treatment | Uncertainty-aware deadline/resource allocation | State-conditioned deadline uncertainty already exists. Differences from our client-response endpoint do not establish novelty; profile/state acquisition costs must be matched. |
| [Reeve, DKW-Massart proof](https://arxiv.org/html/2403.16651v1), iid statement and corollaries | Independent samples from one distribution | Empirical-to-population CDF deviation bounds | Ordinary sampling uncertainty can be small while transfer error is large. The bound is not a future-drift or finite future-cohort error guarantee. |
| [Kang and Lama, RScale, UCC 2020](https://www.cs.utsa.edu/~plama/papers/UCC20.pdf), abstract and Sections I/III opening | Adaptive Gaussian-process profiles, container metrics and VM hardware counters, observed performance | Tail-latency predictions and confidence-aware resource scaling | Adaptive state-conditioned latency uncertainty has direct systems precedent. We have no matched execution or evidence of a benefit beyond this class of approach. |

## Additional leads and unresolved checks

1. [Sinan, ASPLOS 2021](https://people.csail.mit.edu/delimitrou/papers/2021.asplos.sinan.pdf): primary abstract and introduction inspected. Dependency-aware learned tail prediction and QoS resource control are established. Its complete input/training/update and artifact contract has not been audited for our narrow advance-reliability task. It is not an uncertainty method shown to fail by this screen.
2. [SLO-Scaler, August 2026 preprint](https://arxiv.org/abs/2608.18390): primary abstract inspected. Proposes Bayesian-LSTM tail/SLO forecasts and confidence-based scaling. Treat as a close lead at preprint/abstract level, not verified performance or an executed comparator. Full uncertainty calibration and data-acquisition contract remains to inspect before any new method claim.

The existing [passive-baseline assessment](runtime_io_passive_baseline_assessment_20261008.md)
also covers demand inference, estimator selection and the scarcity of independent
residual labels. Its stopped custom-method verdict remains preserved. The
previous [extension prior-work review](runtime_io_deadline_boundary_prior_work_review_20261010.md)
covers the original model-comparison claims. This audit narrows the decision
contract; it does not relabel an old idea as new.

## Precise gap assessment

The possible practical gap is **useful advance reliability information from a
small client-response calibration budget under the specified Linux quota**.
That statement is a candidate contract, not a demonstrated literature gap.

We have not established that ordinary profile-based prediction plus independently
calibrated uncertainty, or adaptive state-conditioned approaches, cannot meet
this need. We lack comparable labelled history-to-future episodes and several
state observables. Denying those inputs to a competitor could manufacture a
gap; using them in our method would require charging the same acquisition cost.

The bounded saved-data screen establishes no additional capability. Its
conservative checks flag both campaigns, while naive sampling precision favors
NGINX because it has more samples. This is a limitation of the tested information
and checks, not a refutation of conformal inference, GP prediction, MPORA,
CEDULE or the field of latency modeling.

**Verdict: no established method gap at this gate.** Keep the empirical
reliability limitation as discovery evidence. Hold custom diagnostic development
and new collection until a concrete pre-outcome observable, an appropriate
ordinary comparator and a feasible independent validation contract are specified.
The absence of a close exact benchmark match does not establish originality.

## Coverage record

Searches combined tail-latency prediction, uncertainty, calibration, drift,
microservices and named prior sources, followed by primary-page/PDF checks.
Primary claims above rely on official documentation, authors' manuscripts,
arXiv author submissions and the ECRTS proceedings. Direct RTSS PDF retrieval
failed at two author paths; indexed primary passages limit that source's audit.
The selective-regression and SLO-Scaler inspections remain abstract-level.
No exhaustive citation graph, competing artifact execution or full statistical
theorem reproduction was performed. Access date is 10 October 2026.
