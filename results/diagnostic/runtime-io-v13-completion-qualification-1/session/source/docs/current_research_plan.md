# Current research plan: deadline failures after worker computation

Updated 2026-10-03 after the V12 audit and the discussion narrowing the research question.

**Status:** Step 0 and the Step 1 test implementation are prepared and functionally verified. The [V13 protocol](runtime_io_v13_completion_protocol.md) provides the launch procedure for 12 observer-qualification trials; performance collection has not started. Start future work from this document. Update the status and decision log after each stage.

## 1. Research question and scope

The broader question remains:

> Under a fixed CPU quota, how do execution parallelism and burst history determine whether requests meet their deadlines, and which effects depend on the runtime?

Our first, scoped question is:

> Under a fixed fractional CPU quota, does reducing execution parallelism move deadline failures from waiting for computation to waiting for an already-computed result to reach the HTTP handler, and what causes that delay?

This is a testable question, not an established causal conclusion. Go is the first case study. Burst history will help test the explanation after measurement and existing controls are qualified. Comparison with another runtime is a later stage needed for broader claims.

The working hypothesis is that CPU workers can start more computation while completed results await publication or handler execution. That competition may worsen tight-deadline success even when reducing parallelism improves extreme latency. Competing explanations include ordinary quota pauses, effective service capacity, event-recording contention, response/network costs and observer effects.

The initial resource contract is unchanged quota **and period**. Changing period while keeping quota/period fixed preserves average CPU allowance but changes temporal CPU availability; report it as a separate factor. Raising/removing the quota or enabling burst credits is a separate resource-contract comparison.

## 2. Evidence we already have

Retain the sealed [V12 session report](../results/diagnostic/runtime-io-v12-bursty-parallelism-1/session/analysis/report.md), the [offline tradeoff audit](../analysis/runtime_io_v12_tradeoff_review/report.md), and the [gap audit and deadline analysis](../analysis/runtime_io_v12_tradeoff_review/gap_audit_and_completion_deadlines.md).

V12 has four paired GOMAXPROCS=2/1 comparisons under 0.5 CPU: `cpu.max=50000 100000`, configured burst credits=0, four CPU workers, queue capacity=128 and the same offered workload. The pinned toolchain is Go 1.26.1. Reducing GOMAXPROCS improved the extreme tail and failures, while overall successful-request p50 worsened in all four pairs. CPU cost per completed job also changed, so a scheduling-only explanation is premature.

The new **exploratory 500 ms deadline** analysis gives these pooled counts across four trials per arm:

| Outcome | GOMAXPROCS=2 | GOMAXPROCS=1 |
|---|---:|---:|
| All offered requests | 27,172 | 27,172 |
| Deadline misses, including unsuccessful requests | 7,899 | 9,298 |
| Misses whose main worker computation certainly finished by the deadline | 147 | 2,003 |
| Of that class, HTTP handler resume certainly occurred after the deadline | 144 | 1,994 |
| Misses with at least 50 ms between computation completion and the deadline | 71 | 903 |

For GOMAXPROCS=1, that class is about **21.5% of 500 ms misses**, or **7.37% of all offered requests**. Its count increases in all four pairs. These are descriptive pooled counts; individual requests are not independent experimental replications.

Important limits:

- The completion marker follows the main SHA loop but precedes event storage and reply publication. It does not mean all service work is finished or that the result is ready for the handler.
- Handler resume measures handler execution, not when its goroutine first became runnable. Completion-to-resume is not automatically scheduler waiting.
- Clock mappings retain lower/upper bounds and ambiguous cases. Aggregate `cpu.stat` is not a measurement of instantaneous remaining quota or a causal attribution for each request.
- These misses are opportunities to investigate, not a prediction that a policy can recover 2,003 responses. An intervention changes CPU use and later queue history.
- The 100/500/1,000 ms targets were chosen after V12. Confirmation targets must be declared before collecting confirmation data.

Earlier V8–V11 probes remain useful supporting evidence. Patched runtime/observer runs do not establish the mechanism of the stock, untraced V12 service. See the [earlier research map](runtime_io_prior_art_review.md) and the V12 review links above.

## 3. Staged work and decision points

### Step 0 — specify and freeze the next question

**Prepared.** The [V13 protocol](runtime_io_v13_completion_protocol.md) freezes the initial objective, 500 ms primary deadline, 1,000 ms guardrail, observer margins, matched arrival anchor, order and acceptance/rerun rules. The [completion study runner](../diagnostic/completion_study.py), [isolated builder](../diagnostic/build_completion.py) and [analysis](../diagnostic/completion_analysis.py) are implemented. Review the following requirements against its resulting evidence before advancing.

1. Choose the primary deadline and practical effect margin using V12 as discovery evidence. Record why that deadline matters; do not label it a production SLO without evidence. Declare a looser-deadline/tail and failure guardrail.
2. Define the primary outcome as timely successful responses divided by **all offered requests**, timed from scheduled arrival. Retain rejections, timeouts, late responses, drain completions and work after cancellation.
3. List the competing hypotheses and the observation or intervention that would distinguish each. Identify which markers are absent and which kernel/runtime evidence is feasible.
4. Fix arrival schedules, work, resource settings, run order, warmup, measurement, drain and environment criteria. Use independent blocks and balanced/randomized order; keep the same offered schedule within each matched comparison.
5. Specify observer qualification, uncertainty handling, technical acceptance and rerun rules before inspecting new results. Preserve failed attempts. Freeze protocol, source, binaries/images, schedules and analysis hashes in a new session.

**Deliverable:** an executable protocol and verification record, with its paths added here. This roadmap is not that protocol. Run-count proposals and runtime estimates remain provisional until runner preparation and pilot timing.

**Decision:** build only the measurement needed to distinguish a named ambiguity. Do not default to another complete runtime queue recorder or a large factorial sweep.

### Step 1 — qualify the post-computation measurement

Use a small, matched cohort based on the stock V12 service. Keep policy changes out of the observer qualification comparison.

1. Identify the boundaries: main computation ends → event storage → result publication → handler readiness → handler execution → response completion at client. Record publication start/end and exact meanings; concurrent receive/publication must retain timing ambiguity.
2. Compare existing event storage with disabled heavy storage or bounded per-worker buffers. Keep equivalent external request accounting so a faster recorder cannot hide failures.
3. Check record conservation, missing events, buffer overflow, request IDs, cancellation, clock brackets and CPU/latency overhead. Where runnable state is needed, use qualified runtime/kernel evidence rather than renaming the handler timestamp.
4. Capture enough quota and execution evidence to test whether the gap occurs during actual throttling, off-CPU time or runnable competition. State what remains unobservable; cumulative throttled time cannot simply be subtracted from per-request wall time.

**Deliverable:** a boundary map, observer-cost report and matched outcome comparison, including unobserved external outcomes.

**Decision:** if recording or publication contention explains most of the effect, resolve and remeasure it first. If necessary readiness/execution evidence cannot be qualified, limit the question to the measured service interval; do not claim a runtime scheduler defect.

### Step 2 — compare existing controls independently

After Step 1, prepare the proposed **16-trial discovery comparison**:

| Factor | Proposed levels |
|---|---|
| Runtime execution parallelism | GOMAXPROCS=1, 2 |
| CPU-worker concurrency | 1, 4 |
| Independent blocks | 4 |
| Initial quota/period | 50 ms / 100 ms, unchanged |
| Workload | V12 work and fixed offered-arrival anchor |

Worker concurrency and GOMAXPROCS are separate controls. Four workers do not imply four simultaneously executing Go threads. Four blocks are a starting discovery design, not guaranteed confirmation power.

1. Compare timely-success fraction, full outcome counts and latency distributions, including low/high phases and recovery.
2. Classify deadline crossings into before admission, queue/processing, publication/handoff and response delivery using only qualified boundaries. Keep ambiguous records explicit.
3. Report actual CPU consumption and CPU/job alongside wall-time stages. Measure configuration capacity separately if required to test a capacity explanation. Capacity-normalized loads are auxiliary experiments because they change offered arrivals.
4. Select the strongest available static baseline for the chosen objective. If worker=2 or another setting is needed to tune it, use a declared tuning batch; do not call the initial four cells exhaustive optimization.
5. Test whether a stated queueing/periodic-service explanation adequately accounts for the results. Specify its dispatch assumptions; a FIFO model is not the Go scheduler.

**Deliverable:** an independent-control comparison and a documented baseline, with uncertainty calculated across trial blocks.

**Decision:** if a known worker cap meets the objective and guardrails, report that result. A controller needs a remaining requirement or failure case. If ordinary capacity and quota timing explain the effect, pursue validation of that explanation rather than an unsupported new mechanism.

### Step 3 — one targeted handoff intervention, only if needed

Proceed only if qualified post-computation losses remain consequential against tuned existing controls.

1. Test one bounded intervention that delays starting new CPU work while a completed result awaits handler handoff. Define the acknowledgment boundary explicitly; handoff acknowledgment does not mean client receipt.
2. Use blocking signaling, bound outstanding results and handle canceled requests/shutdown. Do not spin or introduce an unbounded waiting path.
3. Compare with tuned static worker limits and relevant yielding/pacing/admission controls. Measure overhead, throughput, rejection cost, looser-deadline success and tail behavior under the same quota and period.
4. Explain which competing causes the intervention distinguishes. A gain by itself does not prove the scheduler mechanism: it may change processing order, capacity or quota consumption.

**Deliverable:** a mechanism-specific counterfactual and baseline comparison, with a declared benefit/guardrail criterion.

**Decision:** if it has no useful advantage over the strongest known baseline, stop this remedy route. Completion prioritization and adaptive admission have prior art; implementation in Go is not sufficient novelty.

### Step 4 — use burst history to challenge the explanation

After the measurement and controls are qualified, compare an identical test burst after idle and busy preconditioning.

1. Keep the test-burst arrivals and work identical and preserve the initial zero-burst-credit contract.
2. Separate history that leaves queued/in-progress work from a comparison where application backlog is cleared. Record residual work and connection/runtime state; waiting for backlog to clear can itself change quota state.
3. Measure or explicitly manipulate replenishment phase when feasible. Wall-clock modulo the configured period does not establish the cgroup's actual phase or remaining budget.
4. If budget/phase cannot be qualified independently, report a workload-preconditioning effect and its confounds. Do not attribute it uniquely to quota memory.
5. Add shorter periods or positive burst credits only as separately declared factors. Predict outcomes before these challenge runs.

**Deliverable:** a history test that supports or rejects the explanation, rather than another parameter sweep.

**Decision:** if existing backlog and periodic CPU supply explain the history effect, report that. Investigate an additional runtime contribution only if the qualified evidence requires it.

### Step 5 — confirm scope, usefulness and possible contribution

1. Freeze the explanation/control and confirmation objectives before new data. Determine repetitions from a precision pilot using independent blocks, not the number of requests.
2. Challenge it with irregular bursts, variable-cost/allocation-heavy work and a realistic Go endpoint. Keep tuning and held-out conditions distinct.
3. Introduce a controlled native-thread HTTP comparison or a second runtime with equivalent CPU demand, arrivals and queue/admission semantics. Document differences; native code alone cannot isolate a Go scheduler effect.
4. Use request-level kernel/runtime evidence to support attribution. Similar results across two implementations support robustness in those cases, not universality. Wider machine/kernel validation is needed for wider claims.
5. Revisit the closest papers and artifacts for the actual result. State what existing mechanisms explain, what remains, and how the contribution differs.

**Deliverable:** a confirmation report and a contribution statement sized to the evidence.

Possible outcomes are an established-explanation validation, a causal characterization with a useful failure boundary, or a policy improvement beyond known controls. None is guaranteed in advance. A feasible contribution must explain something consequential beyond “CPU limits hurt tails” or “less parallelism helps.”

## 4. How this replaces earlier next-step proposals

- The [earlier research direction](../analysis/runtime_io_v12_tradeoff_review/research_direction.md) remains background. Its 48-trial period/arrival-pattern matrix is **deferred** until a qualified mechanism and claim justify it.
- The [older runtime queue-history proposal](runtime_io_v12_queue_history_plan.md) is historical, not the default next batch. Reopen it only if selective runtime queue evidence is necessary to resolve a named uncertainty after observer qualification.
- Existing result sessions, seals, frozen source snapshots and their reports remain historical evidence. Write new derived evidence outside sealed sessions and new measurements to a distinct session directory.
- Do not infer that V12 proves a scheduler bug, that all 2,003 misses are recoverable, or that generic result prioritization is a new algorithm.

## 5. Progress tracker and resumption instructions

| Work item | Current status | Required evidence before advancing |
|---|---|---|
| V12 full-outcome/tradeoff audit | Complete | Linked audit and original seals |
| Exploratory post-computation deadline classification | Complete | Script, JSON, request CSV and clock bounds |
| Scoped question and staged roadmap | Complete | This document |
| Step 0: protocol and implementation preparation | Complete for V13 discovery | V13 protocol, isolated builds, Go/Python checks and six real-HTTP fixtures |
| Step 1: observer/boundary qualification | Implemented; performance collection pending | V13 matched cost/outcome report; readiness/kernel attribution remains unqualified |
| Step 2: independent controls | Pending | Qualified baseline comparison |
| Step 3: handoff intervention | Conditional | Residual problem and baseline limitation |
| Step 4: history challenge | Pending after qualification | Predicted outcomes and controlled state comparisons |
| Step 5: confirmation/runtime comparison | Later | Locked explanation and precision plan |

For future sessions:

1. Read this plan, the gap audit and the latest decision log entry before changing the runner.
2. Continue **Step 1** with the [V13 quiet-window launch](runtime_io_v13_completion_protocol.md). The implementation and functional checks are complete; no performance benchmark has started. Review the observer screen before preparing the 16-trial independent-control comparison.
3. Preparation can proceed during normal desktop use. Performance measurements need a separate quiet window and the validated host/thermal protocol. Preserve temperature and progress monitoring, with consistent monitor cost across arms.
4. After each stage, update the tracker and append: date; protocol/session/report paths; accepted findings and uncertainty; rejected explanations; decision; next task. If scope changes, write the reason here so old proposals do not silently become current again.

### Decision log

**2026-10-03 — scope agreed.** Retain the broader fixed-quota/parallelism/history/runtime question. First investigate deadline misses after main computation, motivated by V12's 500 ms classification. Measurement qualification and known-control comparison come before a new remedy or broad matrix. Novelty remains a candidate, subject to causal evidence and renewed comparison with closest work. Next task: prepare Step 0 and the observer qualification design.

**2026-10-03 — V13 implemented.** Prepared [protocol](runtime_io_v13_completion_protocol.md), isolated locked/bounded service variants with publication brackets, all-offered deadline analysis, four matched three-arm blocks, frozen-source/attempt/output verification, interruption/resume, quiet-host checks and temperature/progress display. Build: `analysis/runtime_io_v13_completion_build`; [functional verification](../analysis/runtime_io_v13_completion_build/functional_verification.json). Both new stock-Go builds passed Go tests; six unquotaed real-HTTP fixtures passed across all three arms at GOMAXPROCS=1/2. Python regression and offline export/seal checks passed; see [preparation record](runtime_io_v13_preparation_verification.md). Functional results establish implementation correctness only. New markers and completion-counter bookkeeping are an observer change, qualified by legacy→locked; locked→bounded tests dynamic shared storage while retaining the mutex. No exact runnable-readiness or request-level throttle evidence is claimed. Next task: quit the desktop app, collect V13 in the validated quiet window, inspect its matched observer report, then decide whether Step 2 is justified.

## 6. Supporting files

- [V13 executable protocol and launch commands](runtime_io_v13_completion_protocol.md)
- [V13 preparation verification](runtime_io_v13_preparation_verification.md)
- [V12 tradeoff audit](../analysis/runtime_io_v12_tradeoff_review/report.md)
- [Verified literature/gap audit and new deadline evidence](../analysis/runtime_io_v12_tradeoff_review/gap_audit_and_completion_deadlines.md)
- [Prior-work tradeoff comparison](../analysis/runtime_io_v12_tradeoff_review/prior_work_comparison.md)
- [Deadline classification script](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work.py), [machine-readable results](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work.json), [request-level evidence](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work_requests.csv)
- [Earlier research map](runtime_io_prior_art_review.md)

The gap audit records source verification and retrieval limits for Go's quota-aware defaults, thread management, TailClipper, deadline scheduling, concurrency limits and other close approaches. Use that evidence before claiming a method is new.
