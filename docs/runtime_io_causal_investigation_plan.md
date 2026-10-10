# Causal investigation: separate queue service from CPU-quota effects

Prepared 2026-10-03. This is a staged research plan, not a built recorder or a launched performance study. It replaces the earlier suggestion to collect queue histories as an end in itself: queue histories must select a causal intervention, and the intervention must have a declared interpretation before collection.

## Prior-art amendment: immediate next step changed

Preparation update: the stock comparison is now [built and functionally verified](runtime_io_v12_parallelism_verification.md). Use the [executable protocol and commands](runtime_io_v12_parallelism_commands.md). No quota collection has started; later queue-history stages remain conditional.

The [prior-work and existing-remedy review](runtime_io_prior_art_review.md), completed later on 2026-10-03, supersedes the immediate ordering below. **Do the bounded stock-Go parallelism comparison before Stage A.** Queue-history development and the scheduler/period factorial are conditional on an unresolved symptom after that comparison.

The completed 50-trial follow-up already includes five steady-overload trials per `GOMAXPROCS=1/2` setting at the same half-CPU quota. Median successful p99 fell from 2,429.97 to 1,181.66 ms, successful throughput rose from 134.40 to 152.33/s, rejection fell from 22.54% to 12.21%, and CPU/job fell by 11.9%. Throttling remained present in roughly 99.84% of periods. This is historical evidence for an existing configuration remedy; it is not a new fairness-only result. The frozen follow-up matrix has no bursty one-processor cell. [Recomputed summary and provenance](../analysis/runtime_io_prior_art_review/existing_followup_summary.json).

Prepare eight trials of **stock** Go 1.26.1, four pairs AB/BA/BA/AB, where A uses two processors and B one. Retain four application workers, work size, queue capacity, 100 ms period/0.5-CPU quota, zero burst allowance, original burst pattern and affinity. Keep yielding, scheduler patches and runtime observers off; retain identical application/client stage instrumentation. Use 20 s warmup and 60 s measurement to observe six burst cycles. Validate the stock build, clock bounds and complete outcome accounting before collection. The detailed outcomes, diagnostic screen and interpretation are in the review; no runner or runtime treatment was prepared in this planning turn.

The primary question at this point is remedy sufficiency: does a known configuration choice substantially reduce long handler-entry delays without losing useful throughput or worsening failures? This comparison cannot directly identify ready-queue residence. CPU-cost/capacity changes must be reported rather than attributed entirely to fairness.

If tuning is sufficient, report it as validation of an existing remedy and reconsider the remaining contribution. If it moves delay into queueing/admission, investigate that measured tradeoff. If valid stock measurements retain long pre-handler delays, proceed to Stage A for the residual condition; declare whether that condition uses one or two processors and carry it consistently into subsequent interventions. Avoid quietly applying the original two-processor factorial to a different residual condition.

The 24-trial cost below describes the conditional original localization/factorial path. It is no longer the unconditional next collection. The new eight-trial comparison needs at least 18.7 minutes for 60 s settling + 20 s warmup + 60 s measurement per trial, plus initial idle, startup, drains and analysis; scheduling a 45–90 minute quiet window is a planning allowance, not a measured run-time promise. Preparation remains separate.

## Target and scope

Explain the seconds-long **network-ready-to-first-selection delay** before some HTTP handler entries in the four-worker, bursty, half-CPU workload. A useful result either identifies a queue-service mechanism with a controlled intervention, or rules out a specific explanation for this symptom. Explaining every end-to-end delay and the entire original 300-trial matrix is a later task.

We should distinguish a cause, an amplifier and a mitigation. A quota can amplify poor queue service; an intervention can improve scheduling while worsening admission failures; neither fact alone establishes an acceptable solution.

## 1. Evidence ledger: what has already been learned

| Evidence | Supported conclusion | Limit |
|---|---|---|
| V8: network-woken HTTP goroutines wait 2.21–2.90 s while 298–384 jobs complete | Some long pre-handler delay is runnable work awaiting execution, with other work making progress | Selected extreme traced examples, not a complete CPU-time partition |
| V8: worker yielding reduces selected ready waits to roughly 86–88 ms; trace-off handler-entry tails also fall sharply | Scheduling opportunity is responsive to an intervention in this workload | Yielding changes scheduling/admission; application queue waits and rejection grow |
| Audited V9: pending-preemption patch does not eliminate long waits and fails the failure-rate screen | That patch is insufficient as a solution | Does not exclude runtime scheduling as a cause |
| V11: tracing off, 66.29% of selections use runnext; 181 forced choices out of 43,886 selections | Preferred handoffs are common; the tested correction acts rarely | V11 uses the same candidate in both arms, not stock versus patched |
| New offline decomposition: all 524 linked waits >=1 s have final-selection-to-dispatch <=31.94 microseconds | Seconds between final selection and runtime dispatch do not explain this linked cohort | OS/quota delays before selection or after dispatch remain possible |

In the new decomposition, at least 99.9975% of each linked long ready wait precedes its final selection hook. Dispatch-to-handler-marker is at most 0.142 ms in that long-wait cohort. During the longest example, 2,407 other selections occur, but only 10 successful ordinary periodic global choices occur. Scheduler ticks advance hundreds of times, so the explanation cannot simply be “ticks never advance.” The unresolved question is whether the delayed goroutine is in the queue being serviced, how much work precedes it, and how often that queue gets a turn.

The decomposition was checked against raw selection/dispatch/handler events for all 3,278 matched waits; inputs and outputs were hash-checked. [Offline report](../analysis/runtime_io_v11_causal_planning/report.md), [validation](../analysis/runtime_io_v11_causal_planning/validation.json), [reproduction script](../analysis/runtime_io_v11_causal_planning/inspect.py).

Wake hooks can precede queue publication, and selection hooks can follow removal. These hooks delimit observations, not exact queue residence. Earlier decoder-adjusted trace timings must not replace the audited original timestamps.

## 2. Competing explanations and their distinguishing predictions

| Explanation | Prediction in a complete history | Test that can weaken it |
|---|---|---|
| Sparse service of global work | Long global residence; few successful global removals while local work runs; FIFO rank drains slowly or a later batch removes the target | Give global work an opportunity on every ordinary selection and verify that this opportunity actually serves the backlog |
| Preferred local handoffs delay regular local work | Target resides in a local regular queue while the owning P repeatedly selects runnext | Prefer regular local FIFO whenever it is nonempty, retaining runnext as fallback |
| Ordinary backlog rather than disproportionate bypass | Many older runnable entries ahead, and removal progress consistent with that backlog | Measure rank, removals and waiting turns; queue-service intervention should change opportunities, not merely add CPU capacity |
| Placement, batching or publication/transit delay | Target spends substantial time between publication/removal operations or migrates to a queue receiving few turns | Follow the transfer; a local/global preference test cannot resolve a publication gap by assumption |
| Quota-period effects amplify waiting | Same queue-service sequence is stretched by execution pauses; shorter periods reduce elapsed waits, potentially without reducing waiting turns | Shorten the period while preserving the nominal half-CPU budget |
| OS scheduling / execution-resource placement | A relevant P/M gets few execution opportunities, or substantial unexplained gaps persist despite timely queue service | Targeted kernel execution evidence and, if justified, a separate GOMAXPROCS=1 comparison |

These explanations can coexist. Many other dispatches exclude “the entire service was continuously frozen throughout the whole wait,” but do not exclude substantial intermittent quota throttling. Finite long waits do not establish unbounded starvation.

## 3. How existing work informs the tests

The Go runtime discussion [#73964](https://github.com/golang/go/issues/73964) proposes repeated runnext preference and preemption requests missed when short-running goroutines park as a starvation mechanism. It suggests both pending-preemption handling and periodic local-queue service. Our previous patch tested the former direction; its failure does not test the latter independently. The issue's sleep reproducer is not our HTTP workload.

[Jeffery, Jensen and Mortier, 2024](https://arxiv.org/html/2407.11582v1) study OS-thread overcommitment and quotas. This motivates a CPU-resource contrast, but their Go default-thread-count observations predate container-aware Go defaults. Our pinned Go 1.26.1 workload explicitly sets GOMAXPROCS=2, so an old default-detection defect is not established here. [The Go team's explanation](https://go.dev/blog/container-aware-gomaxprocs) distinguishes parallelism from aggregate CPU bandwidth.

[Fairness in Responsive Parallelism, 2019](https://cs.nyu.edu/~shw8119/19/icfp-fairness.pdf) and [Work Stealing for Interactive Services to Meet Target Latency, 2016](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/06/paper-1.pdf) motivate explicit service/fairness measurements instead of assuming throughput implies responsiveness. Their scheduling models and implementations differ from Go; their results are guidance, not proof for this workload.

[Linux cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html) defines cpu.max as aggregate bandwidth per period. [Bandwidth-control documentation](https://docs.kernel.org/scheduler/sched-bwc.html) also describes parent limits and CPU-local accounting. Record the ancestor limits and relevant kernel accounting settings; aggregate throttled time is not a per-request elapsed-time attribution.

## 4. Stage A: one bounded localization and observer study

Build a queue-history observer on **stock pinned Go 1.26.1**, with a separate compiled-out observer control. Both keep stock scheduling. Preserve the original calibrated workload, GOMAXPROCS=2, four workers, 128 queue slots, 44,000 SHA iterations, 113.21 requests/s bursts, service/client affinity and environmental controls. Runtime tracing and worker yielding stay off.

Use eight trials in four control/observed pairs, ordered AB/BA/BA/AB; 10 s warmup, 20 s measurement, plus unchanged settling and drain. This returns to the original runtime reference. V11's candidate-policy measurements remain historical evidence and must not be silently relabelled as stock measurements.

Record the minimum evidence needed to distinguish the table above:

- Wake, queue publication/removal/transfer, selection, dispatch and request identity.
- Global, regular local/P, runnext/P, and explicit direct-selection or transit states.
- Queue order/depth information sufficient to establish older work ahead and removals while the target waits; include initial unknown entries explicitly.
- Owning P and executing M, fresh/inherited slices, scheduler ticks, successful source choices and fairness opportunities including checks that find no eligible work.
- Transfers through injection, overflow, batching, runnext displacement, stealing and draining. Direct netpoll selection must remain a distinct path.

Use bounded nonallocating records and existing queue ownership/locking rules. No unsafe queue scans or extra blocking hot-path locks. Publication/removal may overlap across processors: operation identities and timing brackets must preserve partial order, rather than treating record reservation order as a global causal clock. Selective tracking is acceptable only if it preserves the target's entire path and the queue-order evidence needed for attribution; otherwise use a bounded complete capture.

Verify queue ordering, displacement, stealing, batching, wraparound, concurrent transfers, conservation, request zero, capture stop and overflow before collection. Unknown initial state or an omitted transfer cannot become an invented FIFO rank. Overflow or impossible histories fail mechanism validation.

Predeclare observer screens: server CPU/job and client CPU/offered request ratios <=1.10; successful client p99 median ratio in [1/1.10, 1.10]; failure-rate increase <=0.001 in absolute fraction; >=99% usable client traces; complete workload accounting. Also report the unconditional handler-entry delay with clock bounds and whether tracing-free long delays still reproduce. These are descriptive screens with four pairs, not equivalence tests. Screening must detect a recorder that hides the symptom as well as one that worsens it.

Deliver queue timelines for every reconstructable long wait and a fixed typical comparison cohort, with residence brackets, older entries, owning-P turns, queue-service opportunities and unknown time. Report linked and unlinked network wakes, buffered requests without a separate wake, all outcomes and coverage by outcome.

**Decision before Stage B:** Choose the probe from queue residence and service evidence, then freeze its source and predictions. Global residence motivates a global-service probe; local regular residence motivates FIFO-first local service. If both are material, use an explicitly combined alternating global/local probe and limit the claim to the combined mechanism. Dominant publication/transit or unresolved histories instead trigger a targeted transfer investigation; do not launch an unrelated fairness matrix.

## 5. Stage B: a controlled 2 x 2 causal comparison

For a queue-service explanation, compare the selected strong mechanism probe with stock Go, crossed with two quota periods:

| Cell | Scheduler | cpu.max | Nominal budget |
|---|---|---|---|
| A | Stock | 50000 100000 | 0.5 CPU |
| B | Selected queue-service probe | 50000 100000 | 0.5 CPU |
| C | Stock | 5000 10000 | 0.5 CPU |
| D | Same probe | 5000 10000 | 0.5 CPU |

Use the same observer in every cell, runtime tracing off, and the same application work and offered arrivals. Keep cpu.max.burst=0. Read back actual child/ancestor limits. Shorter periods preserve nominal bandwidth but may change realized utilization and accounting costs; measure those differences rather than assuming equal achieved capacity.

The probe is deliberately strong for diagnosis, not a proposed production patch:

- Global case: at the ordinary fairness point, try a global removal whenever global work exists, independent of pending preemption and schedtick modulo 61; otherwise follow stock local selection.
- Local case: prefer regular local FIFO when nonempty; if empty, retain the stock runnext fallback and inherited-slice behavior.
- Mixed case: alternate global and regular-local opportunities at ordinary selection points, with empty-queue fallbacks and runnext when neither has regular work. Do not implement global-first-only and claim it bounds local waiting.

Retain GC, safe-point and runtime correctness priorities. Verify that intended opportunities actually happen under load. A FIFO-first choice can change fresh-slice ticks and later global checks; the local probe therefore tests that policy pathway, not runnext priority independently of every tick/preemption effect. Record these changes.

Four balanced blocks, 16 trials: ABDC, BCAD, CDBA, DACB. Each cell appears once in each position. Freeze order, hashes, buffer capacity, analysis and numerical interpretation before launch. Stage A observations are not reused as Stage B causal replicates. No parameter sweep or adaptive extension during collection.

Primary mechanism measurements: per-trial linked pre-handler ready-wait p99, long-wait counts per 1,000 offered requests, queue residence and waiting turns/opportunities. Also report all HTTP network-wake distributions and linkage/coverage changes, so a treatment cannot appear better merely by changing cohort membership.

Required outcome measurements: all-offered handler-entry delay with existing clock bounds, successful E2E p50/p99, success throughput, rejection/timeouts/errors, application queue waits, CPU/job and achieved cgroup usage. These reveal delay migration and capacity tradeoffs. Never add independent percentiles into a synthetic latency partition.

Before launch, define a large-effect diagnostic screen: >=50% reduction in linked ready-wait p99 in each of the four paired 100 ms blocks, with corresponding reduction in waiting turns and the predicted queue residence. This is a practical mechanism screen, not a significance threshold. Weaker/mixed effects are reported as such; four trials per cell cannot establish precise population effects.

## 6. Interpretation and stopping rules

| Result | Permitted conclusion / next action |
|---|---|
| Queue probe shortens residence and waiting turns at the original quota | Evidence that the targeted scheduling pathway contributes; verify unconditional handler entry and failures before claiming overall improvement |
| Shorter period changes elapsed delay much more than waiting turns | Evidence for a period-dependent amplifier; exact throttle-time attribution still requires kernel evidence |
| Both interventions matter, or their effects differ across periods | Investigate an interaction between queue service and bandwidth enforcement, not a single exclusive cause |
| Intended probe engages but targeted residence/turn counts remain high | Weaken that specific queue-service explanation; inspect remaining placement/transit or earlier-priority paths |
| Ready waiting shrinks but application queue waits/rejections grow | Scheduling mechanism improved, but overload/admission tradeoff remains; not an accepted service fix |
| Neither factor has a clear effect | This study has not resolved the mechanism; do not equate a small sample's null result with absence of an effect |
| Observer changes/hides the symptom or histories are incomplete | Repair the measurement once with a named deficiency; do not interpret a mechanism from incomplete evidence |

Do not launch another generic delay-discovery batch after this. The report must update the evidence ledger with supported, weakened, eliminated-for-this-cohort and unresolved explanations. If the data are inconclusive, state why: failed manipulation, missing boundary, changing cohort, observer effect, insufficient precision or competing mechanisms.

A residual OS question gets a **separate small kernel study**, chosen from a specific unexplained interval. Check available tracepoints/tools on this host first. Correlate scheduler switch/wakeup events with service thread IDs, and actual bandwidth throttle/unthrottle events where supported, using bounded clock mapping, lost-event checks and an observer control. Switch traces alone cannot label every off-CPU interval as quota throttling. Per-CPU cgroup throttling intervals are not automatically disjoint process-wide pauses. One-second monitor samples and aggregate cpu.stat cannot supply this missing timeline retrospectively.

The prior-art amendment moves the GOMAXPROCS=1 contrast ahead of localization; keep worker count, work, arrivals and quota fixed, and record capacity changes. Removing the quota is only a contextual negative control: it grants additional CPU and cannot independently identify the cause of the original half-CPU delay.

If a mechanism is supported, the next deliverable is a minimal reproducer that retains its queue path and handoff behavior, plus one gentler candidate tested against the original failure/throughput criteria. Only then expand to other quota periods/workers or the original research matrix.

## 7. Cost and completion criteria

Conditional localization path after the prior-art amendment's configuration comparison: eight localization/observer trials, a review checkpoint, then 16 causal trials. These are two quiet external-terminal windows. Allow roughly **1.5–3 hours of collection in total** for this conditional path, with thermal settling, drains and retries able to extend it. With 60 s settling, 10 s warmup and 20 s measurement, the per-trial arithmetic minimum is 36 minutes for 24 trials; two 10-minute initial idle windows add 20 minutes before drains and analysis. Runtime preparation, correctness verification and recorder development are separate and cannot yet be estimated reliably.

This planning turn completes the offline interval decomposition and the protocol. It does not implement the queue observer, compile runtime treatments or start performance collection. Existing sealed trials, frozen sources and reports remain intact.

Success is a causal account with a verified pathway and counterfactual contrast, or a clearly scoped elimination such as the one already obtained for final-selection-to-dispatch delay. Another report that only confirms “HTTP waits seconds” is not the intended outcome.
