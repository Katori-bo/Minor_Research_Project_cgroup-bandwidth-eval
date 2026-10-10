# Focused prior-work review of the deadline-resolution extension

Date: 2026-10-10. Scope: the empirical contribution now supported by V30,
V31 and the completed NGINX campaign, rather than earlier proposed methods.
Status: targeted primary-source review completed; scientific novelty remains
unestablished. No experiment or competing implementation was run for this review.

## Assessment

The broad ideas are established: CPU bandwidth limits affect latency; periodic
CPU availability differs from continuous average speed; latency profiles can
support prediction; temporal dependence and traffic shape can defeat simple
average models. The paired empirical CDF is an ordinary estimator, not a new
algorithm. A steep CDF converts small timing changes into large miss-probability
changes by definition, so that observation alone is not a novel mechanism.

The strongest defensible contribution is a **scoped empirical case study of
predictive adequacy across deadlines and observed traffic states under one
fixed Linux CPU quota**, with separately calibrated prospective confirmations
and a preserved adverse application-transfer result. That is a candidate
incremental contribution, not an established first result or general law.
The reviewed passages do not report our exact combination of service, endpoints,
comparators and prospective evidence. This is a statement about this review's
coverage, not proof that an equivalent study does not exist elsewhere.

Suggested contribution sentence:

> On one Linux host under a fixed fractional CPU quota, we prospectively
> document a 25 ms forecast contrast and a separately confirmed 10 ms low-queue
> calibration result, while preserving burst-traffic failure and an unsupported
> complete-response transfer criterion in stock NGINX. These experiments delimit
> the adequacy of the tested approximations; they introduce no new estimator or
> universal model-selection rule.

An empirical contribution can be worthwhile without a new algorithm. The
targeted review does not establish whether this particular contribution is
sufficient for a given journal or conference.

## Evidence being compared with prior work

| Record | Result | Exact scope |
|---|---|---|
| V30, fresh calibration and 18 held-out trials | At the primary 25 ms endpoint, constant-rate busy FIFO MAE 73.599 pp; ordinary periodic+delay MAE 2.341 pp; all declared 5% miss-budget decisions agree | One Go SHA HTTP service, Q=25 ms/P=100 ms, steady and specified burst traffic; aggregate accuracy gate, not a bound on every profile |
| V30 timing exploration | A low-rate paired empirical CDF fits the steady 10 ms result but fails on burst traffic | Method chosen after V30 outcomes; discovery only |
| V31, fresh calibration and 18 trials at new rates | Primary 10 ms paired-CDF MAE 1.844 pp versus periodic+delay 67.340 pp | Same host/service, 5/11/19 requests/s; zero recorded measurement throttling and >=99% observed queue waits <=100 us; scope checked after observation |
| NGINX, fresh calibration and 18 held-out cohorts | At 20.565395 ms, full-response CDF MAE 5.981481 pp; conditional 95% interval [1.320988,10.641975] pp does not satisfy the required upper bound <=5 pp | Stock NGINX gzip, same host, new complete-response estimand including waiting; internal queue unmeasured; not a replication of the V31 comparator |
| NGINX saved-evidence diagnosis | Persistent timing excursion mainly after response headers; cohort variation near a steep response transition | Exploratory client milestones; mechanism unresolved; no trial removal or endpoint replacement |

All errors are absolute miss-fraction errors in percentage points (pp). They
are not directly comparable to published relative quantile errors, average
response-time errors, throughput gains or worst-case bounds. Request counts
are not independent experiment replicates. V31 has six validation blocks;
the NGINX interval conditions on the frozen calibration and does not propagate
calibration uncertainty. Its failed gate does not establish that population
mean error is necessarily greater than five points.

## Closest primary work and what it rules out

Sources below were accessed on 2026-10-10. Section locators, access limitations
and the recorded query set are retained in the companion source register.
Descriptions compare scope and premises, not unexecuted implementations.

| Source | Relevant established contribution | Implication for our claim |
|---|---|---|
| S01: [Linux CFS bandwidth-control documentation](https://docs.kernel.org/scheduler/sched-bwc.html), background, caveats and examples | Quota/period ceilings, local runtime accounting and the latency/burst tradeoff of period selection are documented | Quota periodicity and quota-induced delay are background. Our single global-budget baseline omits Linux details. |
| S02: Li, Lu and Gill, [Predicting Latency Distributions of Aperiodic Time-Critical Services](https://www.cse.wustl.edu/~cdgill/publications/rtss19.pdf), RTSS 2019, abstract and Sections II–III | Derives stationary response distributions for Poisson arrivals and deterministic service under a deferrable server; synthetic and Redis evaluation on Xen | Periodic-server tail prediction predates our work. Its scheduler and arrival premises differ from our finite deterministic schedules under Linux bandwidth ceilings. Indexed primary passages were available; direct PDF retrieval failed, limiting the audit. |
| S03: Cucinotta et al., [Strong Temporal Isolation Among Containers in OpenStack for NFV Services](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), TCC 2023, Section 4.2 and evaluation setup | Models real-time HCBS containers; its average-speed approximation explicitly requires reservation period small relative to request processing time. Evaluation uses P=2 ms and modified Linux | A 100 ms ceiling with short requests does not reproduce those guarantees or assumptions. Our weak fluid baseline cannot refute this published method. |
| S04: Ali et al., [CEDULE: A Scheduling Framework for Burstable Performance in Cloud Computing](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf), ICAC 2018, Sections II–III | Uses latency profiling and quantile regression across CPU limit and load to support burstable-cloud scheduling, with held-out profiling cases | Empirical calibration for tail prediction and testing at new loads are established. Our fixed CDF is simpler; the credit-control setting and quantile endpoint differ. No state-of-the-art superiority claim follows. |
| S05: Mi et al., [Sizing multi-tier systems with temporal dependence: benchmarks and analytic models](https://link.springer.com/content/pdf/10.1007/s13174-010-0012-9.pdf), JISA 2010, Sections 3.2–3.3 | Shows limitations of average models under burstiness; uses completions over concatenated busy periods and dispersion to fit temporally dependent service models | Busy-time characterization and the importance of dependence are prior art. Our FIFO comparator does not implement their richer correlated model. |
| S06: Jeffery, Jensen and Mortier, [Reducing Tail Latencies Through Environment- and Neighbour-aware Thread Management](https://arxiv.org/html/2407.11582v1), 2024 preprint, Sections 2–5 | Separates enqueue, worker-start and finish timing and studies quota/environment-aware thread management; queue latency is excluded from later non-overload analysis | Stage timing and quota-aware thread policies are established. Our frozen miss-probability comparison has a different purpose; we have not demonstrated a better controller. |
| S07: Shetty et al., [CPU-Limits kill Performance: Time to rethink Resource Control](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf), SoCC 2025, especially Section 3.2 | Studies CPU-limit microbursts and latency despite low average utilization and proposes a different resource-control approach | Low average load does not imply harmless limits. Our unthrottled V31 result does not establish the same causal mechanism or outperform their controller. |
| S08: Gokan Khan et al., [PerfSim: A Performance Simulator for Cloud Native Microservice Chains](https://www.es.mdu.se/pdf_publications/6526.pdf), author manuscript, DOI 10.1109/TCC.2021.3135757, Sections 3.1.4 and 6 | Profile-based discrete-event modeling includes container CPU limits and validates response/execution-time measures across scenarios | Container-latency simulation is prior art. Their reported metrics do not directly answer our miss-probability endpoint, but that difference is not proof that their method would fail it. |
| S09: Ugedal and Kumar, [Mitigating Unnecessary Throttling in Linux CFS Bandwidth Control](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf), SBAC-PAD 2022, abstract and introduction | Identifies runtime-accounting and synchronization problems and proposes kernel changes | Known bandwidth-control mechanisms must not be relabeled as our discovery. Our records do not identify these causes. |
| S10: Samimi et al., [Enabling Containerisation of Distributed Applications with Real-Time Constraints](https://drops.dagstuhl.de/storage/00lipics/lipics-vol335-ecrts2025/html/LIPIcs.ECRTS.2025.3/LIPIcs.ECRTS.2025.3.html), ECRTS 2025, abstract and Section 2 | KubeDeadline integrates SCHED_DEADLINE reservations with Kubernetes/Ray for temporal isolation | A schedulable CPU reservation provides a different contract from our ordinary quota ceiling. No universal impossibility of deadline prediction follows from our results. |

The closest modeling precedent is S02; the closest profiling precedent among
these sources is S04. S03 is particularly important because it states the
small-period assumption that our average-rate comparison does not satisfy.
The correct positioning is an empirical evaluation of selected approximations
in the tested regime, not discovery that periodic supply or profiling matters.

## Claim-by-claim verdict

| Proposed claim | Verdict | Appropriate wording or missing evidence |
|---|---|---|
| CPU quotas can damage latency even when average utilization is low | Established background | Cite S01/S07; do not list as our novelty |
| Periodic CPU supply can produce response distributions unlike a continuous average rate | Established modeling idea | Cite S02/S03; our observations quantify one setting |
| Predicting tails from measured latency profiles | Established approach | Cite S04/S08; ordinary CDF adds no algorithmic novelty |
| Pairing measured worker/residual samples matters | Endpoint-specific empirical contrast | V31 supports a contrast at 10 ms; independent convolution is better at 9 ms. No general pairing theorem or causal dependence claim |
| The tested models have different accuracy across deadline and traffic conditions | Supported scoped empirical contribution candidate | V30 primary 25 ms and V31 primary 10 ms are separate prospective studies. Other deadline-grid comparisons remain descriptive |
| Zero recorded throttling ensures accurate empirical latency transfer | Not supported | NGINX completed measurement gates but did not meet its declared accuracy criterion. V31's internal-queue domain was not measured in NGINX |
| A steep CDF amplifies small timing changes | Mathematical property, not novelty by itself | Use to interpret errors; diagnostic offsets are post-hoc, not new validated deadlines |
| We identified quota phase, CPU demand or a scheduler defect as the cause | Not established | Assumed phase, elapsed stage times and aggregate CPU are insufficient; missing per-request execution/scheduling evidence |
| Our model beats published state-of-the-art methods | Not tested | No matched artifact execution; our simplified baselines differ from S02–S05/S08 |
| A universal model or validated advance selection rule | Not established | One host, limited workload contracts; observed domain checks do not predict applicability beforehand |
| Independent-hardware replication | Not performed | A new application on the same machine changes software, not physical host |
| New empirical evidence is automatically scientific novelty | Incorrect | Fresh evidence strengthens a claim; its difference from the full relevant literature still needs assessment |

## Practical decision

Consolidate the extension as a scoped empirical paper/note, with existing
methods described explicitly as baselines and references. Include both the
positive prospective comparisons and the failed NGINX criterion in the
abstract and conclusions. Retain the failed candidate qualifications in the
evidence history, without treating apparatus failures as scientific
counterexamples. Do not create a custom workload solely to obtain a positive
transfer result or retune the failed NGINX campaign.

The literature does not make a new algorithm the simplest next step. A
universal model would require much broader theory and evidence. A second-host
replication would strengthen generality, but is unavailable with the current
hardware and would not by itself prove originality. This review therefore
supports finishing the honest empirical account now; it does not authorize a
new experimental campaign or certify submission readiness.

If a future manuscript makes a stronger prediction-method claim, first select
a compatible published comparator, establish its assumptions and implement or
run it under a separately declared matched evaluation. If it makes a causal
claim, first collect measurements or interventions that identify the cause.
Those are separate research tasks, not requirements to invent novelty for the
current descriptive contribution.

## Coverage and limitations

This is a targeted review, not a systematic review. Searches combined CPU
quota/CFS, periodic reservation, response distributions, empirical calibration,
deadline misses and burstiness, followed by named-paper checks and selected
primary passages. Prior project contribution screens informed source selection;
this document supplements them for the later V30/V31/NGINX evidence and does
not rewrite their historical verdicts. Ten sources were compared, including
official documentation and a preprint. No complete citation graph, exhaustive
database coverage or competing-artifact audit was performed. S02 has a material
full-PDF access gap. Absence of an exact match in inspected passages is weak
evidence of originality; confidence is higher that the broad method ideas are
already established than that the precise empirical combination is new.

Evidence package:
`analysis/runtime_io_deadline_boundary_prior_work_review/20261010/` contains
this report snapshot, `sources.json`, `local_evidence.json` and a SHA256 seal.
The seal records file identity, not originality or independent replication.
