# Research direction after V12: explain and predict the limits of known remedies

**Current scope:** follow the [current research plan](../../docs/current_research_plan.md),
agreed after the additional deadline analysis. Measurement qualification and a
comparison of independent worker/runtime controls now come first. The 48-trial
matrix below is an earlier proposal, deferred pending those decisions.

Prepared 2026-10-03. This is a literature-grounded proposal, not a registered experiment protocol or a claim of established novelty. It extends the [V12 offline audit](report.md), [focused tradeoff comparison](prior_work_comparison.md), and [earlier research map](../../docs/runtime_io_prior_art_review.md). No performance trial, service change, or controller implementation was performed for this note.

**Recommendation:** seek a transferable explanation and validated decision rule for choosing parallelism under a fixed fractional CPU quota and changing demand. Investigate a new control policy only if existing controls leave a reproducible, consequential limitation. More runs increase evidence; they increase novelty only if they answer a question beyond the known tradeoff.

## 1. The candidate question

> For a Go HTTP service whose CPU quota cannot be raised or removed, what determines which execution-parallelism setting delivers more successful responses before a specified deadline as demand changes? Can observable workload and backlog information predict that choice on workloads not used to construct the rule?

The practical output would be an explanation and a tested configuration rule. A new scheduler is optional. The reviewed sources establish many ingredients of this problem, but do not supply a validated answer for our combined service, resource constraint, burst history and full-outcome accounting. That is a **candidate coverage gap**, not proof that no paper answers it.

The motivation is specific. With the same half-CPU quota, V12's median trial fraction of all offered requests successfully completed within 500 ms is 73.75% with GOMAXPROCS=2 and 65.71% with 1. At one second it is 82.52% versus 99.99%. These deadlines were selected after the experiment and are exploratory. The result supports investigating a deadline-dependent choice; it does not establish one universal crossover threshold or a production SLO.

The audit also localizes costs. Overall successful p50 worsens in all four pairs, but low-phase p50 improves slightly in all four and high-phase p50 worsens in only three. In each arm's median-rank cohort, application-queue and worker-completion-to-handler-resume means increase with one processor. CPU/job decreases too. Consequently, a scheduler-only explanation is premature: effective capacity, quota timing, network handling and return-path scheduling can change together.

## 2. What the closest sources already cover

| Primary source checked | Established result or technique | Consequence for our proposed contribution |
|---|---|---|
| [Uber automaxprocs](https://github.com/uber-go/automaxprocs#performance) | Its two-CPU-quota load-balancer table shows lower p50 but higher p99.9 with two processors than with one. Quota-aware sizing is implemented. | Neither setting one processor nor reproducing a median/tail tradeoff is a novel remedy. Its throughput falls with 2→1, unlike our slight increase. |
| [Go container-aware GOMAXPROCS](https://go.dev/blog/container-aware-gomaxprocs), [proposal #73193](https://github.com/golang/go/issues/73193), and [Go 1.26.1 source](https://raw.githubusercontent.com/golang/go/go1.26.1/src/runtime/debug.go) | Policy explicitly considers fractional rounding, burst parallelism and a minimum of two. Actual changes to GOMAXPROCS in the pinned source stop the world. | “Use quota-aware parallelism” and “bursts can favor higher parallelism” are established. Verify actual defaults and switching costs rather than presenting them as new ideas. |
| [Jeffery, Jensen and Mortier, 2024](https://arxiv.org/html/2407.11582v1), §§3–5 | Studies quota-aware sizing and separates worker queuing from computation. Its friendlypool dynamically changes active threads using recent CPU usage. The neighbor-adaptation section assumes quotas are absent. | Adaptive thread counts already exist. Our fixed-quota HTTP setting differs, but the difference needs a demonstrated consequence, not just a new parameter value. |
| [Work Stealing for Interactive Services to Meet Target Latency, PPoPP 2016](https://www.microsoft.com/en-us/research/publication/work-stealing-for-interactive-services-to-meet-target-latency/) | Tail-control uses progress, load and a latency target to adapt request parallelism and admission in TBB. | Deadline-aware adaptation is established. A Go implementation alone would not distinguish our contribution. |
| [Autothrottle, NSDI 2024](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf), §3 | Uses CPU usage and throttling feedback to adjust microservice CPU quotas, guided by application SLOs. | Throttle feedback and SLO control are established. Its actuator changes allocation; a fixed-quota study must evaluate what remains possible without that actuator. |
| [CPU-Limits kill Performance: Time to rethink Resource Control, SoCC 2025, author paper](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf), [arXiv text](https://arxiv.org/html/2510.10747v1), §3.2 | Examines DeathStarBench services and explains both individual throttling and queue amplification across requests. Advocates removing limits for latency-sensitive services. | “CPU limits hurt latency” and “brief bursts create longer queues” are established. Our scope must explain why the limit is retained and compare remedies within that constraint. |
| [Netflix concurrency-limits](https://github.com/Netflix/concurrency-limits) | Implements latency-based adaptive concurrency, including Vegas and Gradient2; simple enforcement rejects excess in-flight work. | Compare against available admission/concurrency controls. Count rejected requests as failures to deliver timely successful service, rather than hiding them behind success-only latency. |
| [Concord, SOSP 2023](https://marioskogias.github.io/docs/concord.pdf), §3 | Combines compiler-enforced cooperative preemption with bounded worker queues and dispatch techniques for microsecond-scale services. | Scheduling and preemption improvements have strong precedent. A generic “prioritize short work” or “yield more often” claim is insufficient. Its dedicated-core system is not a direct half-CPU Go comparison. |

The fixed-quota scope has a real operational example: Kubernetes namespaces can require container CPU limits through `limits.cpu` ResourceQuota policies. This is documented in the [official namespace quota walkthrough](https://kubernetes.io/docs/tasks/administer-cluster/manage-resources/quota-memory-cpu-namespace). It does **not** mean every Kubernetes service must have a limit or that this project already represents a production deployment. State the policy assumption explicitly; validate the phenomenon in a containerized service before claiming deployment relevance.

A separate mechanism lead comes from the [CogMI 2024 response-time-instability study](https://doi.org/10.1109/CogMI62246.2024.00024): its publisher abstract describes transient microservice bottlenecks propagating into queuing, drops and TCP retransmissions lasting seconds. We checked the abstract, not the full paper. Its multi-tier workload differs from ours, but it makes network behavior a concrete alternative to investigate. Scheduled-arrival-to-handler-entry is not a measurement of a network-ready goroutine's scheduler residence.

## 3. Three possible contributions, ranked

### A. A validated explanation and configuration rule — recommended first

Determine which combination of demand, outstanding work, quota period, effective service capacity and deadline predicts the advantage of one versus two processors. Compare three levels of explanation:

1. CPU-count/quota and mean-utilization rules.
2. A simple queueing model using measured service-time distributions and periodic CPU availability. Specify its dispatch and service assumptions; do not call a FIFO model the Go scheduler.
3. A model that additionally accounts for measured entry or result-delivery delay, only if the simpler explanation leaves systematic error.

Train and select models on discovery data, then lock them before new workload/machine tests. Report prediction error and lost timely completions relative to the best static setting in each held-out scenario. A winner comparison by scenario is valid; constructing an “oracle” by stitching request latencies or burst phases from separate executions is not, because switching changes queue history.

**Contribution condition:** a repeatable, useful predictive improvement over existing sizing rules and simple queueing explanations, with a physical explanation and external validation. A larger collection of percentile plots alone is descriptive replication. If a known model already explains the effect adequately, report that finding and do not invent a missing mechanism.

### B. A causal explanation of a remaining delay stage — conditional

If outcome prediction depends materially on entry or post-work waiting, determine which pathway causes it. Separate at least:

- Client dispatch, connection establishment, wire delivery/readiness and handler entry.
- Application-queue waiting from CPU execution opportunities.
- Worker completion, result publication, handler readiness, handler execution and response completion.

V12 does not contain all these markers. Its completion-to-resume interval can include event-lock and reply-publication time, not just runnable waiting. Earlier patched/traced runs cannot automatically establish the mechanism of stock V12.

Use a small, matched stock-service diagnostic cohort with targeted instrumentation and observer-off controls. Check connection/retransmission behavior before assuming all pre-entry delay is runtime scheduling. If a return-path effect remains, change worker concurrency independently of GOMAXPROCS and use one targeted intervention that changes that pathway. Preserve CPU limits and count changed processing cost. A change to quota period is a useful perturbation, but changes temporal CPU availability and does not independently prove a runtime queue policy.

**Contribution condition:** request-level linkage plus a counterfactual intervention that distinguishes competing explanations, followed by replication beyond this SHA workload. Measuring another long interval is insufficient. Predeclare one diagnostic batch and a decision after it; add probes only to resolve a named ambiguity that could change the conclusion.

### C. A policy that improves the remaining tradeoff — highest development risk

Only after A/B, test whether online worker admission or execution parallelism can increase timely successful completions while retaining a chosen tail/failure guardrail under the unchanged quota. Signals must be available at decision time, such as actual queue state and recent throttling; future arrival schedules and known benchmark phase labels are unavailable in deployment.

Compare against tuned static GOMAXPROCS, tuned worker concurrency and an existing adaptive admission approach. Include controller CPU overhead, switching pauses, GC behavior, oscillation and rejection cost. Model-based prediction can also support a static configuration recommendation rather than a controller.

**Contribution condition:** an identified limitation of existing approaches, a mechanism-specific design difference, and improvement on held-out workloads at the same stated resource contract. If tuned static controls perform equally well, the controller route has no demonstrated benefit. Adaptive concurrency by itself is already prior art.

## 4. Collect data in stages, with a decision after each

### Stage 0 — prepare measurement and hypotheses

Reuse the sealed V12 data and existing audit. Keep the original observations as discovery evidence. Specify the service objective before collecting confirmation data: timely **successful** completions divided by all offered requests, with failures, drains and work after cancellation retained. The 500 ms/one-second contrast is a useful exploratory motivation; select confirmation targets and practically meaningful effect margins explicitly rather than treating those targets as predeclared.

Estimate processing capacity separately for each configuration using independent rate sweeps and a declared stability criterion, not CPU/job alone. Check both observer cost and environmental variation. Preserve the original fixed offered-arrival comparison as the operational question. Comparisons at matched fractions of each arm's measured capacity are auxiliary: they change arrival rates and cannot substitute for the same-workload comparison.

Before running, review whether the runner supports all proposed arrival patterns and quota-period settings; seal a separate protocol, binaries, input schedule and analysis plan. This note is not that protocol.

### Stage 1 — a small boundary study

A proposed discovery batch has **48 trials**:

| Factor | Proposed levels |
|---|---|
| GOMAXPROCS | 1, 2 |
| Quota period | 20 ms, 100 ms; quota/period = 0.5 in both |
| Arrival pattern | Steady; 0.5 s low/0.5 s high; original 5 s low/5 s high |
| Replication | Four independent blocks per cell, balanced/randomized order |

Initially keep workers=4, queue=128, work and offered mean rate fixed at the V12 anchor. For burst patterns keep the same low/high rates and duty cycle so mean rate is unchanged. Preserve identical offered schedules within each parallelism pair. Quota period changes remain an explicit factor, with zero configured burst credits. Record effective ancestor limits and affinity. Vary/record timing offsets; validate later on nonperiodic arrivals so synchronized benchmark cycles do not determine the conclusion.

Use 20 s warmup and provisionally 120 s measurement, with full drain. Four blocks per cell are discovery replication, not guaranteed statistical power. This batch answers whether temporal demand and replenishment alter the deadline-dependent advantage at the same average CPU allowance. It does not establish a new scheduler mechanism or a universal CPU-budget rule.

**Decision:** if ordinary service capacity plus periodic availability predicts outcomes, focus on validating that explanation. If a known static control resolves the chosen service objective robustly, do not build an adaptive remedy without another demonstrated requirement. If large unexplained stage delays remain, use the bounded diagnostic cohort from B.

### Stage 2 — challenge the explanation and the available baselines

Select informative conditions from Stage 1, then lock predictions before collecting new data:

- Change CPU budget (e.g. 0.25, 0.75 and 1 CPU), offered load below/near measured capacity and burst amplitude. Use calibrated demand for budget comparisons to avoid making low-budget overload a trivial result. Retain fixed-arrival anchors too.
- Compare worker counts 1, 2 and 4 independently of GOMAXPROCS. Test the shorter quota period as an available control. Verify Go's actual default and a quota-floor policy; if they choose values already tested, do not count them as independent mechanisms.
- Add variable-cost and allocation/GC-heavy requests, then a realistic Go endpoint with CPU work and I/O. A second synthetic hash size alone is weak generalization.
- Reserve irregular bursts and another machine as held-out tests. Pin and report toolchain/kernel/container versions; a second Go version helps bound a runtime-specific claim.

Use a precision pilot to determine confirmation replication, based on independent trial blocks and a predeclared uncertainty target. Confirmation windows of 5–10 minutes can capture more demand transitions and rarer outcomes. Do not treat individual requests or cycles as independent replicates. Record temperature, frequency/CPU accounting when available, order/day effects and observer controls. Affinity alone is not exclusive CPU isolation.

Removing the quota, increasing allocation or adding burst credits can be useful context comparisons, but those change the resource contract. Report them separately from a remedy that preserves the original quota and period. A shorter period preserves the average allowance, not the timing contract.

### Stage 3 — optional policy and causal confirmation

Proceed only if Stage 2 leaves a practically relevant limitation. Freeze training/tuning conditions, test on new arrivals/workloads, compare the strongest tuned baselines and reproduce an ablation of the proposed mechanism. Rejecting more requests must not masquerade as a latency improvement. Declare the guardrail and acceptable tradeoffs before these runs.

## 5. What additional time buys

The 48-trial discovery proposal alone contains 96 minutes of measured traffic. With 20 s warmup and an assumed 60 s settling interval per trial, the arithmetic is 48 × (120+20+60) = **2 h 40 min**, plus initial idle, startup, drain and thermal settling. A provisional **3–6 hour session** is a planning range, not a runner estimate; calibration and instrumentation validation are additional. Longer settling or reruns can exceed it. The runner is not yet built/sealed for this study.

Confirmation and cross-workload/machine validation should be separate sessions with decisions between them. Additional research time is best spent on calibration, falsifying competing explanations and held-out prediction rather than launching a large grid before knowing what evidence it could change.

## 6. What we could honestly claim afterward

| Result | Defensible direction |
|---|---|
| Known controls and a simple established model explain the effect everywhere tested | Reproduction and practical validation; no demonstrated new mechanism or controller need. |
| A model predicts deadline-dependent configuration choices on new workloads better than existing rules | Candidate empirical/model contribution, subject to a renewed closest-work comparison. |
| A particular entry or return-path mechanism is causally isolated and matters across workloads | Candidate mechanism contribution, with its runtime/resource scope stated. |
| A mechanism-based policy beats tuned baselines under the same contract on held-out demand | Candidate systems contribution; novelty depends on its specific difference from adaptive scheduling/admission prior art. |

This review is targeted, not exhaustive. Sources include engineering evidence, official implementation/policy documentation, and original research; they are not all equivalent forms of evidence. Search covered CPU limits, fractional quotas, parallelism, adaptive concurrency, deadline scheduling and burst-driven delay, including recent 2025 work and searches for 2026 work. Before asserting a specific model or algorithm is novel, follow the citations of the closest matching paper and inspect its full evaluation/artifact for that exact claim. The next executable task is to prepare and seal Stage 0/1, after choosing the confirmation objective, rather than starting another performance trial from this proposal.
