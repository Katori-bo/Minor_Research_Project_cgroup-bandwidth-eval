# Passive burst-deadline forecasting: novelty, feasibility and data screen

8 October 2026. The user authorized screening this candidate and is open to
additional useful data. This comparison uses primary literature and existing
records. No scientific collection or custom prediction/abstention algorithm
was launched. The empirical paper, closed FIFO theorem route and held
quota-period selection route remain unchanged.

## Verdict

**Reject the broad novelty claim of passive forecasting with uncertainty or an
option to abstain. Proceed only to a bounded offline comparison of a specific
quota-forecast reliability capability; novelty is not established. New data are
not needed to begin that comparison.**

There is a practical question worth screening: can a forecaster distinguish
useful predictions from unreliable extrapolation under an ordinary fractional
CPU quota, while avoiding deliberate saturation and answering a meaningful
fraction of future burst cases? The inspected literature establishes its
building blocks. The saved records show a reliability problem but do not show
that an adequate established approach cannot solve it.

The immediate missing item is a specified capability and fair published-method
mapping, rather than another campaign. No custom prototype is justified yet.
If standard passive estimators with standard uncertainty/model-support checks
meet the need, stop this method route. If all supportable policies refuse almost
everything, that also fails the useful-capability test.

## Operational decision and working assumptions

Given a history ending before the decision and a declared future offered-arrival
schedule, forecast the fraction of all offers that exceed 500 ms, including
unsuccessful offers. Return either a forecast with explicitly scoped uncertainty
or an insufficient-evidence answer. Retain the known request class, one worker,
128 waiting places and 50 ms/100 ms quota with zero burst credit for the first
screen. No period or resource configuration is selected.

The working use case is a live service observed through normal traffic and
possibly bounded low-load probes. This is a research scenario, not evidence
that a production user requires it. If isolated replica calibration is acceptable,
ordinary direct busy calibration remains an adequate competitor. If natural
traffic already has eligible busy windows, its direct throughput estimate is a
permitted passive alternative; do not manufacture a gap by discarding it.

Separate two information contracts:

- **Cold start:** no prior saturation/burst labels for this workload/resource
  state. Transferring demand and CPU supply beyond observed load requires stated
  assumptions; confidence is not supplied by the quota ratio alone.
- **Previously trained deployment:** historical workload/host profiles and
  independently measured forecast errors are allowed, with acquisition cost and
  transfer assumptions charged to every method. No deliberate deployment-time
  overload is different from having never observed overload anywhere.

The strict low-load subset is 0/15/30 jobs/s. The broader nonbacklogged subset
also includes 60/90/120. All twelve existing idle/steady observations happened
to have zero throttling, zero request deadline misses and at most one waiting
job. Calling 120 jobs/s "low load" without qualification would be misleading.
These were controlled synthetic calibration runs, not production traffic traces.
Zero past misses do not guarantee that new probes will be harmless.

No later burst outcome, busy capacity, best subset chosen by deadline score or
hidden prior profile may enter a cold-start forecast or refusal rule. Fixed
arrival schedules here avoid adding a traffic-prediction problem. Initial backlog
and clock/accounting scope must remain declared. Existing outcomes are already
known, so every new computation below is retrospective.

## Comparison with primary prior work

The implication column is our inference; a different output metric or scheduler
does not establish an unmet capability. See the
[source register](../analysis/runtime_io_passive_novelty_screen/20261008/sources.json)
for inspected sections and unresolved leads.

| Method/source | Assumptions and required data | Output | Implication |
|---|---|---|---|
| [Spinner et al., resource-demand survey, 2015](https://se.informatik.uni-wuerzburg.de/staff/samuel-kounev/publications/?cHash=093a29953fb0ac74fd2f314fcdf9bc45&tx_extbibsonomycsl_publicationlist%5Baction%5D=download&tx_extbibsonomycsl_publicationlist%5Bcontroller%5D=Document&tx_extbibsonomycsl_publicationlist%5BfileName%5D=SpCaBrKo2015-PEVA-ResDemEstSurvey.pdf&tx_extbibsonomycsl_publicationlist%5BintraHash%5D=0373ae5cb4f2bbaedd9a5a2ba28a445c&tx_extbibsonomycsl_publicationlist%5BuserName%5D=samuel.kounev) | Coarse utilization/throughput or response/queue measurements; flow/model assumptions; response approximates demand only when waiting/other resources are negligible | Demand estimates and comparison across load, window size and model mismatch | Ordinary passive CPU and response-time baselines must receive a fair opportunity. |
| [Incerto, Napolitano and Tribastone, moving-horizon estimation, 2018](https://cse.lab.imtlucca.it/~mirco.tribastone/papers/mascots18.pdf) | Queue-length time series, known network/routing/multiplicities; single-class exponential-service queueing network and fluid approximation | Transient online demand estimates without measurement traffic | Passive transient estimation is established. Map our waiting-plus-active state and pulsed CPU service explicitly before claiming inadequacy. |
| [Perez, Casale and Pacheco-Sanchez, computational requirements](https://juanfperez.com/data/2015_02_des_TSE.pdf) | Arrival/departure/state or response/queue observations; declared thread-pool/multicore scheduling model | Demand inference, including event-based and reduced-information alternatives | Rich request timings are available here; a CPU-only benchmark is not the strongest possible passive competitor. |
| [Kalbasi, DEC thesis, 2010](https://www.collectionscanada.gc.ca/obj/thesescanada/vol2/002/MR69450.PDF?is_thesis=1&oclc_number=806535411) | Measured benchmark demands, replication and function/workload-mix decomposition | Aggregate demand and confidence estimates with validation | Confidence and warnings about misleading narrow regression intervals already exist. Benchmark acquisition is not free cold-start evidence. The 2012 journal revision was not fully retrieved. |
| [Grohmann et al., SARDE, 2021](https://se.informatik.uni-wuerzburg.de/publications/?cHash=c7300d8a02e65b7dcd8870de230e3338&tx_extbibsonomycsl_publicationlist%5Baction%5D=download&tx_extbibsonomycsl_publicationlist%5Bcontroller%5D=Document&tx_extbibsonomycsl_publicationlist%5BfileName%5D=SARDE_TaaS2020.pdf&tx_extbibsonomycsl_publicationlist%5BintraHash%5D=fc3fb3694ee15b680f1466a5acc7bc64&tx_extbibsonomycsl_publicationlist%5BuserName%5D=se-group) | Continuous monitoring streams, estimator families, training and internal cross-validation proxy | Adaptive demand estimation and estimator/window selection | Generic diagnostics and selection are covered; internal observed-regime error must be distinguished from future burst-deadline error. |
| [Shah et al., selective regression, 2021](https://arxiv.org/abs/2110.15403) | Learned regression/confidence model and selection rule | Abstention, with accuracy-versus-coverage tradeoff | Returning insufficient evidence is not a new contribution by itself. This is generic precedent, not a tested quota forecaster. |
| [MPORA, ECRTS 2026](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html) | Offline execution-state/allocation profiles, held-out error calibration; exchangeability or modeled shift assumptions | Runtime demand predictions and uncertainty-aware deadline allocation | Learned deadline uncertainty is already established. Its profiles are substantial inputs; its guarantees are marginal, not automatically conditional guarantees for our burst schedule. |
| [SafeOpt, ICML 2015](https://proceedings.mlr.press/v37/sui15.html) | Noisy function measurements and Gaussian-process regularity assumptions | Constraint-respecting sequential exploration | Adding "safe" adaptive probes does not alone supply novelty. The actual service must satisfy the assumed support/regularity conditions. Abstract-level inspection only. |

The [preserved load-dependent assessment](runtime_io_load_dependent_baseline_assessment_20261008.md)
also remains relevant. Neither Kumar/Zhang nor the response/transient methods
above have been faithfully implemented and tested here. The polynomial
benchmark does not stand for all of them.

## What the saved records actually demonstrate

The [offline report](../analysis/runtime_io_passive_novelty_screen/20261008/report.json)
uses only appropriate idle/steady inputs for its reference predictors.
All sixteen known validation cases are scored, including zero-miss cases and
refusals. The CPU demand-law estimate uses pooled CPU/completions at 15/30;
the wall proxy uses pooled worker processing duration. Both assume transfer to
loaded operation. Worker elapsed duration is not measured worker CPU time.

| Ordinary reference | Calibration input | Capacity jobs/s | Deadline MAE pp | Maximum error pp | Within 3 pp | Refusals |
|---|---|---:|---:|---:|---:|---:|
| Low-load CPU demand law | Four steady 15/30 observations | 110.691 | 43.291 | 54.476 | 0/16 | 0 |
| Low-load worker-wall proxy | Same four request-event traces | 116.900 | 39.280 | 49.024 | 0/16 | 0 |
| Linear utilization fit | Twelve nonbacklogged observations | 125.953 | 31.314 | 37.929 | 0/16 | 0 |
| Quadratic utilization fit | Same twelve observations | 148.463 | 1.169 | 3.619 | 13/16 | 0 |
| Existing quadratic admissibility policy | Six strict-low 0/15/30 observations | Unavailable | — | — | 0/16 | 16 |

Thus forecasting without deliberate saturation already has a strong near-adequate
reference in our own evidence. A three-case tolerance failure is not proof that
a new method is required; model-error calibration or another established
estimator may suffice. Conversely, the strict-low refusal is the existing
bounded-extrapolation rule, not a newly validated insufficiency detector.
It answers no cases and supplies no useful coverage by itself.

Separate quadratic fits on the two nonbacklogged calibration blocks give
148.369 and 148.558 jobs/s, only 0.189 jobs/s apart. Their case-wise prediction
envelope misses eight observed outcomes, with maximum distance outside of
3.381 pp. This is a descriptive sensitivity envelope, **not** a statistical
confidence/prediction interval. It shows why repetition agreement alone cannot
validate deadline accuracy outside observed load.

As an aggregate-identifiability illustration, a common monotone interpolation
through the six pooled utilization-throughput knots can be continued above the
largest measured throughput with positive slopes reaching quota at 1.10, 1.25
or 1.50 times that throughput. These calibration-only choices yield capacity
roots 128.669, 146.215 and 175.458 jobs/s. Under the shared FIFO forecast, their
miss fractions differ by more than 6 pp on every retained schedule. No one
point forecast can be within 3 pp of both endpoints under that admitted family.

This illustration concerns those aggregate features and that model family.
It neither establishes equivalence of full request/CPU traces nor describes
multiple measured real CPUs. It does not refute richer passive estimators,
prove a new theorem, or reopen the FIFO theorem route. Additional assumptions
or informative observations must restrict the extrapolation family. Merely
repeating identical low-rate aggregates does not measure its continuation.

The [kernel bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html)
describes quota replenishment, throttling and per-CPU runtime slices. Treating
the configured ratio as continuously guaranteed CPU supply would skip the
resource contract needed for deadline prediction. Actual CPU service,
loaded demand, quota timing and HTTP/runtime delay are distinct unknowns.

## Additional data: what is missing and when it matters

**No new data are necessary to finish this initial screen or begin the closest
baseline mapping.** We already have aggregate CPU, request clocks/events,
admission/worker/completion timing, low-load controls and known burst outcomes.
The [data gate](runtime_io_passive_forecast_data_gate_20261008.md) ranks future
measurements and gives the conditions for collecting them.

The most valuable future dataset would pair a permissible passive/low-load
history with a subsequently measured burst outcome, across informative history
regimes and cases near the caller's decision boundary. It would test whether a
frozen guard predicts reliability before observing the burst. Current records
have only two calibration blocks on one service/host/quota, controlled traffic
and a sparse future schedule grid. They cannot validate a learned refusal rule
or a conditional error-coverage claim selected now.

Per-request CPU attribution is absent. Fine quota/replenishment/runnable-service
traces are absent for V28; coarse roughly-one-second counters do not resolve a
100 ms period. These are conditional needs for particular models, not a reason
to repair or deploy intrusive instrumentation preemptively. Observer neutrality
would need its own qualification. Natural traffic histories, known workload
classes/state features and independent forecast-error labels are higher-priority
inputs for an empirical reliability policy.

Additional observations can test a contribution; they do not make its idea new.
The [verification](../analysis/runtime_io_passive_novelty_screen/20261008/verification.json)
checks fit equations, original forecasts and the conditional interpolation
example. All protected scientific evidence and seven additional paper/screen
documents remain unchanged. No new data or custom guard was collected/built.

## Next bounded gate

Compare a justified quota mapping of the closest response/event and transient
passive estimators, alongside the existing nonlinear fit and standard
uncertainty/support checks. Keep the two information contracts separate.
Specify one additional capability in terms of accepted-case error, answer
coverage (including nonzero-miss cases), calibration disruption and acquisition
cost. Parameter confidence alone is insufficient; no universal promise is made.

**Proceed with that offline applicability/adequacy gate; hold custom
implementation and collection until a nonroutine capability survives.**
If established methods suffice or assumptions force near-total refusal, stop.
The empirical paper remains independently finishable throughout.
