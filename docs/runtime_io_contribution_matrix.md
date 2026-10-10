# Closest work and contribution matrix

**Post-V22 update — 2026-10-07:** The matrix below records the pre-V22 review.
Prospective queue transfer and the declared nominal-baseline comparison now
passed in [V22](runtime_io_v22_findings.md). The current narrow candidate is the
[short capacity-estimate note](runtime_io_short_working_draft.md), with a
[focused novelty/generality assessment](runtime_io_novelty_generality_review.md)
and prepared V23 work-size/timescale extension. Busy calibration and burst
modelling remain established methods; V22 passing does not certify novelty.
The follow-up review also examines Casale et al.'s2009 controlled stress-testing
work. V23 performance remains unrun. Interpret the “missing/unproved” entries
below as the earlier review state, superseded where explicitly updated here.

Reviewed 2026-10-07. Step 2 of the research synthesis, following the
[evidence map](runtime_io_evidence_map.md). This is a targeted primary-source
review, not a systematic review or certification of novelty. The
[source/search register](../analysis/runtime_io_contribution_review/20261007/sources.json)
records versions, reviewed sections and retrieval limits; the
[review receipt](../analysis/runtime_io_contribution_review/20261007/review.json)
records local checks. No new benchmark, tracer or host-setting change was run.

## Decision

The strongest current candidate is a **scoped empirical diagnostic contribution**:
quantify how a very large improvement in the measured post-computation interval
translates into small or inconsistent all-offer deadline gains under an unchanged
fractional CPU contract, and assess how much a measured-capacity queue account
explains and fails to explain. The yielding stage response recurs; prospective
prediction transfer and a distinctive advance over closest work remain unproved.

Do not claim discovery of CPU-limit latency, burst-induced queues, quota-aware
parallelism, yielding, deadline-oriented scheduling, or capacity-based latency
prediction. Those ideas have substantial precedents below. A new Go version,
host or workload is scope information, not sufficient novelty.

The next study should validate a specific prediction and expose its limits.
An even-arrival comparison alone is useful validation, but its expected direction
is familiar queueing behavior. It cannot by itself establish a new model, a
scheduler mechanism, or a general boundary for when yielding helps.

## Comparison against the supported claims

Claim identifiers C01–C11 refer to the evidence map. The final column is our
assessment/inference from the reviewed material, not a statement made by its
authors. Different evaluation metrics and resource contracts prevent numerical
head-to-head comparisons without a matched implementation.

| Closest source / reviewed focus | What is already supplied | Our evidence and possible addition | Assessment / remaining requirement |
|---|---|---|---|
| P01 [Go container-aware GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs), 2025, and [Gosched API](https://pkg.go.dev/runtime#Gosched) | Go distinguishes execution parallelism from time-based CPU limits; quota-aware defaults and voluntary yielding already exist. | C01–C04 evaluate explicit settings in pinned Go 1.26.1, including the stage response and all-offer deadline outcome. | Configuration and Gosched are existing mechanisms. Our experiment does not discover a primitive or establish an optimal default. |
| P02 [Uber automaxprocs README](https://github.com/uber-go/automaxprocs), engineering benchmark | Its two-CPU-quota table already shows lower GOMAXPROCS improving p99 while worsening p50 and reducing throughput. | C01 adds scheduled-offer 500 ms accounting and measured post-computation crossings for our workload. | The broad tail/median/throughput tradeoff is prior art. The README's protocol/toolchain are insufficient for a matched quantitative comparison. |
| P03 Jeffery, Jensen, Mortier, [Reducing Tail Latencies Through Environment- and Neighbour-aware Thread Management](https://arxiv.org/html/2407.11582v1), 2024 preprint, §§2–5 | Quota-aware thread tuning and neighbour-friendly pools address worker latency/throughput tradeoffs. Their uniform open-loop experiments initially include application queue delay, then exclude it from later latency analysis as overload. | C03–C08 keep application waiting, client deadlines and unsuccessful offers central, alongside the yielding intervention. | Potential distinction is the joint diagnostic evidence, not ignorance of queues in prior work. The paper predates Go's 2025 default change. |
| P04 Shetty et al., [CPU-Limits kill Performance: Time to rethink Resource Control](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf), SoCC 2025, especially §3.2 | CPU limits can create queues and severe latency through microbursts despite low average utilization. The paper argues for removing limits in latency-sensitive applications. | C05–C08 quantify backlog and model errors while retaining a strict quota and zero burst credits. | Retaining limits changes the question; it does not make burst-induced queueing new. We have no evidence of outperforming their resource-control alternatives. |
| P05 Li et al., [Work Stealing for Interactive Services to Meet Target Latency](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/06/paper-1.pdf), PPoPP 2016 | Tail-control adapts admission and parallelism using request progress, load and a latency target; evaluation uses TBB workloads. | C01/C04 demonstrate why successful p99 and the chosen all-offer deadline fraction can move differently. | Optimizing deadline attainment rather than a percentile is established. No new admission or work-stealing policy is implemented here. |
| P06 Muller, Westrick, Acar, [Fairness in Responsive Parallelism](https://cs.nyu.edu/~shw8119/19/icfp-fairness.pdf), ICFP 2019, abstract/introduction | Priority-aware scheduling has formal execution/response bounds, fairness tradeoffs and an evaluated Standard ML implementation. | C02/C03 expose a measured publication-to-execution opportunity in a stock Go service. | Generic fairness/responsiveness is established. Their formal guarantees do not automatically apply to our quota-constrained Go path; ours proves no fairness theorem. |
| P07 [hnes/cpuworker](https://github.com/hnes/cpuworker), prototype README | A CPU-work scheduler demonstration seeks to protect interactive HTTP work; the documented setup uses multiple execution threads and a separate CPU-worker limit. | C03/C04 isolate one existing yield flag with one worker/GOMAXPROCS=1 under half a CPU. | Workload/resource differences delimit comparison. README/demo inspection is not an internal algorithm audit or proof that our technique is distinct. |
| P08 Wang et al., [Autothrottle](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf), NSDI 2024, §§1–3 | End-to-end SLO-aware CPU allocation combines service throttling feedback with application-level control. Resource proxies must be interpreted against the application objective. | C03–C05 examine a stage-local improvement against client deadlines inside a fixed contract. | The general need to connect a proxy to end-to-end outcomes is known. A local intervention case study differs from allocation control but establishes no controller advance. |
| P09 Mi et al., [Sizing multi-tier systems with temporal dependence: benchmarks and analytic models](https://link.springer.com/content/pdf/10.1007/s13174-010-0012-9.pdf), JISA 2010, §§2–4 | Burst-aware queueing models use measured service behavior, variability and temporal dependence; a reproducible burst generator and TPC-W validation are provided. Busy-period measurements help estimate the service process. | C06–C08 use exact finite offer vectors, finite admission and an empirically fitted constant busy capacity; rare-tail failures remain visible. | Neither burst-aware modelling nor busy-period calibration is new. A constant-capacity FIFO account is a baseline, not a new modelling method. Its applicability limits need prospective evidence. |
| P10 Cucinotta et al., [Strong Temporal Isolation Among Containers in OpenStack for NFV Services](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), TCC 2023, §4.2 and §6 | Reservation-based container isolation is linked to service-time and M/M/1 response predictions, then evaluated with NFV workloads. | C07/C08 test a simpler measured-capacity account under ordinary bandwidth limits, with non-Poisson scheduled bursts, finite queues and all-offer deadline loss. | Fractional CPU-to-latency modelling is established. A guaranteed reservation and a bandwidth ceiling are different contracts; their assumptions cannot be silently imported into ours. |
| P11 Khan et al., [PerfSim](https://www.es.mdu.se/pdf_publications/6526.pdf), TCC 2023 (early online 2021), §§3.1.4, 6 | A profiled microservice-chain simulator approximates CFS/container CPU allocation, endpoint work and network effects; evaluation reports average-latency prediction across deployment scenarios. | C07/C08 retain explicit deadline/rejection accounting and identify aggregate-success versus rare-tail prediction limits for a serial service. | Container performance simulation is prior art. Different emphasis is not proof that PerfSim cannot express our case; no matched comparison has been run. |
| P12 Ugedal, Kumar, [Mitigating Unnecessary Throttling in Linux CFS Bandwidth Control](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf), SBAC-PAD 2022 | Bandwidth-accounting and synchronization behavior can cause unnecessary throttling and short-period performance loss; mechanisms and changes are evaluated on their system. | C09/C10 retain our opposite period directions and unsuccessful attribution attempts. | An unresolved historical reversal is context, not a new accounting mechanism. Our measurements do not identify their mechanism as the cause. |
| P13 Hall et al., [Harvesting Spare CPU Resources in Container Systems](https://www.usenix.org/system/files/nsdi26-hall.pdf), NSDI 2026, §§4–5 | Rapid CPU harvesting, affinity management and interference controls protect primary services while using spare resources, including bursty demand. | C03–C08 retain the original fractional limit rather than assigning extra CPU during demand. | Resource-contract difference matters for interpretation. We have no new harvesting algorithm or comparative efficiency result. |
| P14 Li, Zhang, Wang, [SchedBlame](https://arxiv.org/html/2609.02052v1), September 2026 preprint, demand decomposition and §9 | An eBPF design attributes container CPU contention and decomposes demand/waiting. Its reported evaluation is explicitly preliminary cost evidence, with accuracy experiments still proposed. | C02 and observer qualification expose what our markers cannot determine. | No new tracing contribution: exact Go handler readiness and per-request quota causality remain unknown. Do not treat this preprint's planned accuracy evaluation as completed. |
| P15 [Go issue #73964](https://github.com/golang/go/issues/73964), issue report, current body/status | A runnable-order/timer starvation case and possible scheduler changes are reported in Go. | C02/C03 show delayed handler execution and a yield response in a different HTTP workload. | A related report motivates hypotheses but does not prove our path has the same mechanism or a runtime defect. Issue status is mutable. |
| P16 [Linux bandwidth-control documentation](https://docs.kernel.org/scheduler/sched-bwc.html), current documentation | Quota/period, CPU-local runtime slices, throttling counters and burst-credit mechanisms are established. | The V20/V22 contract disables burst credits; changing period preserves only the average quota ratio. | No new quota law. Documentation is background, not evidence of instantaneous budget during any particular request. Its listed control files are cgroup v1; our recorded interface is v2. |
| P17 [argos-edge v1.3.41.1 release notes](https://cmos486.github.io/argos-edge/release-notes/v1.3.41.1/), September 2026 engineering report, export/pacing comparison | The author reports that keyset export plus Gosched improved export time but still failed an interactive p99 target under a retained one-CPU limit; paced export and competing work are discussed. | C03–C05 provide paired block comparisons, internal stage bounds and all-offer deadline outcomes under a different service contract. | This is a close practical precedent against a broad “yielding is insufficient” novelty claim. The release notes are author-reported evidence, not an independently reproduced controlled experiment. |

Two additional 2026 sources were screened at abstract/introduction level, not
fully assessed: P18 [Unfair by design: eBPF-based scheduling of mixed database
workloads](https://arxiv.org/html/2605.02377v1), a May preprint presenting
application-hinted priority protection in PostgreSQL; and P19
[Eunomia: Preemption-based and QoS-aware Core Allocation in Oversubscribed
Cloud](https://past.date-conference.com/proceedings-archive/2026/DATA/1135.pdf),
DATE 2026, presenting QoS-aware preemption/core allocation for colocated VMs.
They reinforce that protecting interactive work is an active, established area.
No claim about their exact coverage of our measurement is made from that screen.

## Contribution candidates and their present status

| Candidate | Existing evidence | What is missing | Decision |
|---|---|---|---|
| Quantified stage-to-deadline mismatch under fixed quota | C03: strong stage response in original/repeat. C04: original −0.088 pp versus repeat +1.638 pp at 500 ms/100 ms period. C05: 95.57% of original yield-on successful misses crossed the deadline while queued. | Independent validation of where this account transfers; stronger measurement if asserting a runnable-state cause. P17 already reports a related practical yielding limitation. | Lead empirical candidate; describe conditional outcomes, not “yielding never helps.” |
| Prediction transfer and error boundary | C07 withheld-block aggregate errors; C08 nominal CPU/job model failure and missed rare tails. | Frozen predictions for new arrival patterns, baseline comparisons and stage/tail errors. No validated boundary currently exists. | Supporting candidate for V22; existing queueing methods remain baselines. |
| CPU-accounting versus busy-service diagnostics | C08 shows a large failure of one whole-trial CPU/job substitution. | Prospective baseline reproduction and decomposition of workload-phase overhead; other workloads if generalizing. | Retain as a scoped diagnostic finding, not a universal rejection of utilization-based modelling. |
| New scheduler/controller or Go defect | None established; Gosched is an existing API. | A new policy plus matched evaluation, or qualified readiness/quota evidence isolating a defect. | Do not claim. |
| Explanation of historical period reversal | C09/C10 show both directions and preserved negative diagnostics. | The historical cause remains unidentified. | Closed as unresolved; not the novelty target. |

Our synthesis/inference is that these observations can make a useful case study
without yet establishing a new general mechanism. Neither the amount of data
collected nor the lack of an exact match in this targeted search establishes
novelty, paper acceptance, or suitability for a particular venue.

## Implications for the prospective study

Use [V22](runtime_io_v22_prospective_queue_plan.md) to test the queue component,
with independent new-boot calibration and frozen predictions. Its first-stage
design keeps yielding **off**: it therefore does not prospectively test the
yielding interaction or the complete proposed stage-to-deadline contribution.
Keep that distinction in the eventual paper.

Before implementation, Step 3 should freeze one falsifiable question and these
comparison requirements:

1. **Baseline:** constant-capacity FIFO with finite admission and exact arrivals.
   Compare measured busy capacity with the existing nominal-quota/whole-trial
   CPU-job substitution, estimated only from calibration. Report both, including
   failed predictions. Do not call the FIFO model a new algorithm.
2. **Separation:** calibration supplies capacity/uncertainty; validation supplies
   no fitted parameters. Seal predictions, thresholds, reset/dispatch checks and
   technical-failure rules before validation. Retain disagreements rather than
   refitting them away.
3. **Outcomes:** all-offer 500 ms success, rejection, queue peak and recovery;
   additionally retain stage errors and >1 s outcomes. Passing aggregate errors
   cannot erase the rare-tail failure already seen in C08.
4. **Decision:** burst-versus-even tests transfer to a new timing pattern.
   A named shorter/longer-burst extension may test a predicted onset of deadline
   or buffer failure if first-stage results justify it. That onset calculation
   is ordinary queueing; the possible addition is demonstrated applicability and
   error limits, not its formula. No extension is automatically launched here.
5. **Scope:** if only the familiar direction reproduces, write a transparent
   replication/case study. If predictions fail, report the failure and localize
   it before proposing another measurement. Any future joint yielding-boundary
   claim needs a separate matched yield comparison, not inference from yield-off
   V22 alone.

A defensible working contribution statement is:

> We characterize a stock-Go HTTP service under a retained fractional CPU limit:
> a large measured post-computation improvement has conditional deadline benefit,
> and a measured-capacity queue account explains much of the recorded loss while
> failing on specified outcomes. We then test its transfer to new arrival timing
> with predictions frozen before validation.

The first sentence is a scoped description of existing evidence. The second is
proposed work, not a completed result. “First,” “novel model,” “scheduler defect,”
“validated general boundary,” and “no prior work” are not permitted claims now.

## Review coverage and limits

Primary papers, author/institution-hosted versions, official documentation and
author-maintained engineering reports support the matrix. Searches covered
quota/thread control, response fairness, burst modelling, container simulation,
deadline control, tracing and recent 2026 developments. Reviewed portions are
listed per source; reading selected sections is not a complete algorithm audit.
No competing artifact was executed and no new raw-trial replay was performed.

The argos-edge direct page initially failed retrieval; a later domain-filtered
search returned the substantive release-note text and table, enabling the
limited engineering comparison above. A separate lead, *Model-Driven System
Capacity Planning Under Workload Burstiness* (TC 2010), was not retrieved in full
and is not assigned full-text findings; P09 supplies a retrieved related primary
paper. Search misses, retrieval failures and screened abstracts are not evidence
that an exact preceding contribution does not exist.

This matrix supersedes the narrower three-source novelty discussion in V22.
The earlier [prior-art review](runtime_io_prior_art_review.md) and
[period synthesis](runtime_io_period_literature_synthesis.md) remain historical
context, with their original dates and claim limits.
