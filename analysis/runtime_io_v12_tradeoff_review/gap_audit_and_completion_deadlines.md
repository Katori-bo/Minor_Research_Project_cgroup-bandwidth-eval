# Verified gap candidates and a new V12 deadline analysis

**Execution roadmap:** the [current research plan](../../docs/current_research_plan.md)
records the agreed scope, staged tasks, decision points and progress tracker.
Use it as the starting point for future implementation and measurement work.

Reviewed 2026-10-03. This note evaluates the supplied ChatGPT literature scan, extends the [research direction](research_direction.md), and adds an offline analysis of the sealed V12 evidence. No performance trials or service changes were made. The broad research subject remains CPU quotas, concurrency and deadline outcomes; Go is the first case study.

**Recommended candidate:** explain deadline misses that occur after a request's worker computation has already finished, and test whether protecting result handoff/response execution improves timely successful service under an unchanged fractional CPU quota. Use workload history and replenishment timing as controlled factors. This is a narrower, evidence-backed candidate than claiming novelty for the combination of quota period, parallelism and burst history.

It is a candidate gap, not a certified absence of prior work or a demonstrated new mechanism. Generic prioritization, latency-aware admission, CPU pacing and deadline scheduling all have prior implementations.

## 1. What is useful in the supplied scan

Keep its emphasis on fixed quota/period ratio, recent demand, end-to-end deadlines and separation of kernel/runtime effects. The idle→burst versus busy→burst experiment is particularly useful if it distinguishes the state left behind by the preceding load. Its newer references also broaden the related-work map.

The assertion that a real, defensible gap has already been established is stronger than its evidence. Failing to locate a paper that includes every proposed factor does not demonstrate an unexplained mechanism or an unmet service requirement. A joint characterization can be a research contribution, but needs a consequential finding that existing explanations or evaluations do not already provide.

### Verification of its additional references

| Source | What was verified | Implication and retrieval limit |
|---|---|---|
| [Huang et al., Adapt Burstable Containers to Variable CPU Resources](https://digitalcommons.kennesaw.edu/facpubs/6154/), DOI 10.1109/TC.2022.3174480 | University record and abstract describe an adaptive container scheduler, virtual blocking and busy-wait detection for concurrency under variable available CPUs. | A genuine close predecessor. Full text was not retrieved; its absence of a particular experiment cannot be certified from the abstract. |
| [Mind the Gap, SoCC 2021](https://research.adobe.com/publication/mind-the-gap-broken-promises-of-cpu-reservations-in-containerized-multi-tenant-clouds/) | Author-affiliated abstract identifies Forced Runqueue Sharing and Phantom CPU Time as causes of discrepancies between reserved and received CPU. | Generic Linux/container scheduling pathology already has causal research. This abstract does not establish either mechanism in V12. |
| [Thread-Per-Core Tail Latency, ANCS 2019](https://researchportal.helsinki.fi/en/publications/the-impact-of-thread-per-core-architecture-on-application-tail-la/) | University record verifies authors, title, venue and DOI. Linked manuscript retrieval failed. | Bibliographically real; detailed exclusions in the supplied scan were not independently verified. |
| [Harvesting Spare CPU Resources in Container Systems, NSDI 2026](https://www.usenix.org/system/files/nsdi26-hall.pdf), §§2–3 and 5.7 | HarvestContainers manages spare cores and interference, including networking interrupts, and evaluates cgroup shares/quotas as comparisons. | Real and relevant recent work. Its primary resource control differs from retaining a fixed fractional quota for the latency-sensitive service. It also warns against treating cross-runtime similarity as sufficient kernel attribution. |
| [ChaosRM, FGCS 2026](https://www.sciencedirect.com/science/article/abs/pii/S0167739X2600021X), DOI 10.1016/j.future.2026.108387 | Publisher abstract/introduction describe tri-zone CPU sharing, JVM instance states, and thread-queuing time as feedback. | Real; scheduling-delay feedback is established. Full paper was not inspected, so exact evaluation exclusions remain unverified. |
| [Jeffery et al., 2024](https://arxiv.org/html/2407.11582v1), §§2–5 | Original text includes quota-aware Go/Rust work, initial queue/computation accounting, and a later neighbor-aware pool under an explicit no-quota assumption. | Supports a specific scope distinction; neither adaptive thread counts nor measuring queue delay is new by itself. |

The [Autothrottle paper](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf), §3, does adjust quota using usage/throttle feedback under application SLO guidance. This remains an important comparator, but its actuator changes allocation. Direct retrieval of the supplied 2021 burst mailing-list message failed; the current [kernel bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html) verifies the burst feature, not the exact performance claims made about that patch evaluation.

### Close work missing from the supplied scan

- [KubeDeadline, ECRTS 2025](https://drops.dagstuhl.de/storage/00lipics/lipics-vol335-ecrts2025/html/LIPIcs.ECRTS.2025.3/LIPIcs.ECRTS.2025.3.html), §§2 and 6: uses hierarchical SCHED_DEADLINE reservations, budget/period analyses and deadline experiments. Deadline analysis of periodic CPU supply is not a newly discovered idea; its reservation semantics differ from ordinary fair-class quota enforcement.
- [TailClipper, SoCC 2024](https://lass.cs.umass.edu/papers/pdf/socc24_tailclipper.pdf), §§3–5: propagates request age and implements oldest-request-first/limited processor sharing through ghOSt across service components. Protecting existing requests and optimizing whole-service scheduling already have strong precedents. The inspected evaluation is not a controlled fractional-quota result-handoff study.
- [Latency-Aware Group Scheduling, 2025 preprint](https://arxiv.org/html/2508.15703v1), §§2 and 4: uses recent cgroup load to prioritize completion in dense serverless deployments; its scope disables bandwidth throttling to retain work conservation. Thus using workload history to improve completion is established, even though the quota contract differs.
- [CockroachDB engineer's account of CPU pacing](https://irfansharif.io/blog/rubbing-control-theory-on-scheduler-latencies/), §§3–4: uses Go scheduling-latency feedback, CPU tokens and cooperative suspension to protect foreground work from elastic CPU-heavy work; includes tests on cgroup-limited nodes. This is engineering evidence, not a matching paper experiment. A generic Go yield/pacing controller would duplicate an available technique.

These comparisons narrow the candidate. They do not support declaring that CPU-budget timing, history-aware control, deadline fractions or completion prioritization are original concepts.

## 2. Technical corrections needed before using the scan as a proposal

1. **History has several mechanisms.** Prior busy load may leave queued/in-progress work, consume current-period quota, affect runtime/GC/cache state, or change accumulated bandwidth when burst credits are enabled. V12 has `cpu.max.burst=0`; deliberately accumulated burst credits cannot explain it. CPU-local slice carryover is a separate kernel caveat. Idle/busy preconditioning alone does not isolate these mechanisms.
2. **Arrival phase requires measurement.** The experiment's wall-clock start is not a verified replenishment boundary. Aggregate `cpu.stat` does not directly expose an instantaneous remaining-budget field. Observer design must account for per-CPU allocation and ancestor limits. Qualify a kernel observer before claiming request-level quota state.
3. **The proposed latency sum can double count.** A queue-wait or processing wall interval may already contain throttling and descheduling. Keep disjoint timestamp stages; annotate overlapping kernel/runtime states within them. Do not add aggregate throttled time to those intervals.
4. **Worker count and execution parallelism are different controls.** Four workers under GOMAXPROCS=1 cannot execute four Go computations simultaneously. Hardware affinity also bounds actual execution. Vary the controls independently.
5. **Automatic Go sizing may duplicate a tested setting.** Under V12's two-CPU affinity and half-CPU quota, the [pinned Go 1.26.1 default calculation](https://raw.githubusercontent.com/golang/go/go1.26.1/src/runtime/debug.go) selects two. Explicit GOMAXPROCS disables automatic updates. A default arm is a useful behavior check, not a new parallelism mechanism if it selects two.
6. **Cross-runtime agreement is corroboration, not causal isolation.** Native workers still involve application design, the network stack and OS scheduling. Match meaningful work/load/resource conditions and intervene on the suspected mechanism. Do not attribute a shared effect solely to Linux because two implementations show it.
7. **Deadlines improve decision relevance, not novelty by themselves.** [Tail-control, PPoPP 2016](https://www.microsoft.com/en-us/research/publication/work-stealing-for-interactive-services-to-meet-target-latency/) already optimizes the number of requests meeting a latency target. Count rejections/timeouts as unsuccessful service and keep all offered requests in the denominator.

## 3. New evidence: some deadline misses occur after worker computation finishes

The new [offline script](deadline_after_work.py) reads all eight V12 trials. It verifies completion seals and confirms every original result-file hash remains unchanged. For each offered request it places the server's worker-completion marker into the client clock interval, without using a midpoint, and compares it with the deadline measured from scheduled arrival. All missed requests fall into mutually exclusive categories: not admitted, computation certainly late, clock-boundary ambiguous, or computation certainly completed by the deadline.

At the exploratory **500 ms** deadline:

| Pooled counts over four trials per arm | GOMAXPROCS=2 | GOMAXPROCS=1 |
|---|---:|---:|
| Offered requests | 27,172 | 27,172 |
| Timely successful responses | 19,273 | 17,874 |
| Misses, including failures | 7,899 | 9,298 |
| Misses with worker computation certainly finished by deadline | **147** | **2,003** |
| Of those, handler resume certainly after deadline | 144 | **1,994** |
| Computation finished at least 50 ms before deadline, but response still missed | 71 | **903** |

In the one-processor arm, the 2,003 requests are **7.37% of all offered requests** and **21.54% of all 500 ms misses**. These are pooled descriptive counts, not independent request-level replicates or medians of trial percentages. The per-trial work-before-deadline counts are 503, 509, 492 and 499; the corresponding two-processor counts are 49, 17, 71 and 10. The direction occurs in all four pairs. In the one-processor arm, 1,897 such requests were scheduled in high phases and 106 in low phases.

The JSON also retains the exploratory 100 ms/one-second results and several completion-margin thresholds. At one second, one processor has only three misses, all with worker computation before the deadline; two processors has 4,943 misses, 575 with computation before the deadline. This reinforces deadline dependence rather than establishing a universal return-path problem.

Validation includes an independent duration-prefix identity for all **53,967 successful requests**: entry bounds plus pre-admission, queue and processing wall spans match the directly mapped work-completion bounds exactly. Outputs are [deadline_after_work.json](deadline_after_work.json) and [request-level examples](deadline_after_work_requests.csv).

**Interpretation limit:** worker completion is stamped after the SHA loop, before taking the event-storage lock and publishing the reply. Handler resume is stamped when the handler executes, not when it becomes runnable. The interval therefore contains result storage/publication, runtime scheduling and possible quota/OS pauses. These counts establish a timing opportunity; they do not estimate preventable misses. Saving all 2,003 requests is not an achievable gain implied by this analysis, because remaining response work costs CPU and interventions change other requests' queue history.

## 4. The recommended focused question

> Under a fixed fractional CPU quota, does a known parallelism remedy create a consequential backlog of computed-but-undelivered responses, and can result-handoff-aware control improve deadline success beyond tuned worker/admission controls without increasing the quota?

This keeps the wider quota/concurrency subject while selecting a precise request-lifecycle question. Use Go first because the stage evidence already exists. A controlled native-thread HTTP implementation then checks transfer; a broader language survey is unnecessary at the discovery stage.

The working hypothesis is that workers can continue starting CPU jobs while completed results await publication or handler execution, causing some requests to miss a tighter deadline despite finishing their main computation in time. It competes with ordinary quota pauses, event-storage contention, response/network costs and observer effects. Our current analysis does not decide among them.

**Candidate gap statement:** In the sources inspected, we did not locate a controlled account of how quota-aware parallelism shifts deadline failures into the post-computation handoff/response interval under a retained fractional quota, or a comparison of handoff-aware control against tuned static worker concurrency for that failure class. This is the claim to test and continue reviewing, not a claim that post-computation delay or completion prioritization has never been studied.

## 5. A bounded sequence toward an undergraduate-scale contribution

1. **Validate the stage, including observer cost.** Add precise result-publication and handler-readiness evidence only in a small matched diagnostic cohort. First test whether event storage creates most of the interval. Use buffered/per-worker records or disabled heavy event storage as an observer control, with equivalent external outcome measurement. Avoid interpreting an instrumentation artifact as a runtime defect.
2. **Test available controls first.** A proposed discovery comparison is GOMAXPROCS {1,2} × CPU-worker concurrency {1,4}, with four independent blocks: **16 trials**, plus measurement qualification. Keep V12's quota, period, offered schedule and work fixed. This separates worker admission from runtime parallelism and identifies a stronger baseline. It is not yet an executable/sealed protocol.
3. **One targeted handoff intervention, if needed.** Test a bounded policy that delays starting new CPU work while a completed result awaits handler handoff. Preserve the quota and period. Use blocking signals rather than spinning, handle cancellation, and compare with equivalent fixed worker limits and simple yielding/pacing. This is a counterfactual probe of a known prioritization principle, not automatically a novel algorithm. Count all offered outcomes and costs.
4. **Use history as an experimental tool.** Repeat the identical test burst after idle and busy preconditioning. Separate tests with intentionally retained backlog from tests whose application backlog is cleared; independently measure replenishment phase/budget state. Keep burst credits off initially. If direct state measurement cannot be qualified, limit the claim to workload-preconditioning effects. Add positive burst credits only in a separate, explicitly changed resource-contract comparison.
5. **Confirm transfer and usefulness.** Lock the discovered explanation/control before irregular bursts, variable-cost/GC-heavy work, a realistic endpoint and the native-thread comparison. Use independent trial blocks and a precision-based confirmation plan. A second machine supports wider claims. The 500 ms target is exploratory here; predeclare any confirmation objective and guardrail before collecting that batch.

There are decisions after each batch. If observer cost explains the effect, resolve that before a service-mechanism claim. If a simple fixed worker cap resolves it, report its limitation/benefit and do not invent a controller need. If the targeted intervention has no advantage over the best available baseline, stop that remedy route. If a known periodic-service model explains the observations, treat history experiments as validation of that model.

## 6. What the project could contribute

A feasible minimum is a reproducible, causally supported characterization of **when worker completion is a misleading proxy for timely client success** under fractional quotas, including the conditions where existing parallelism remedies shift rather than eliminate deadline losses. It must add a concrete explanation or failure boundary beyond the reviewed precedents.

A stronger result would add a small handoff-aware application policy with measurable benefit over tuned static concurrency and known pacing/admission approaches under the same resource contract. A new Linux scheduler is not required. The method and policy remain candidates until validated and compared with the closest related implementations.

The broad quota/period/history interaction remains useful context. A large factorial matrix should follow a qualified mechanism and a specific claim; it should not be the default response to uncertainty about novelty. Search breadth does not certify absence: this review adds papers/implementations missing from the supplied scan, identifies partial retrieval limits, and preserves the distinction between newly computed project evidence and new knowledge for the research community.

To reproduce the added offline analysis from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 analysis/runtime_io_v12_tradeoff_review/deadline_after_work.py
```
