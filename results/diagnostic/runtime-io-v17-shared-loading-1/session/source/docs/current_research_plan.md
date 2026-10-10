# Current research plan: deadline failures after worker computation

Updated 2026-10-04 after V15 review and preparation of the V16 repeatability/rebuild pilot.

**Status:** V16 completed all 12 trials and its frozen evidence verified. Original-image A/A is within every declared discovery margin; the byte-identical exact-source rebuild improves 500 ms success by 1.53–3.92 points against the original labels, so behavioral neutrality still fails. The [V16 offline review](../analysis/runtime_io_v16_repeatability_review/report.md) confirms matching launch/resource/runtime/power/workload settings and finds no causal configuration mismatch. Stay in Step 1. The separate [V17 loading protocol](runtime_io_v17_loading_protocol.md) and [verified preparation](runtime_io_v17_preparation_verification.md) now cross both images with packaged/common-file loading in four matched blocks (16 trials). All shared conditions execute the exact same sealed backing file; identical startup provenance checks apply to every arm. Next collect V17 in a separate quiet window and interpret packaged-gap reproduction before the shared-file/within-image contrasts and loading interaction. Collection remains unstarted at 0/16. V15's nonmonotonic marker effects remain unresolved; V14 stays retired/incomplete. Start future work from this document. Update the status and decision log after each stage.

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
| Step 1: observer/boundary qualification | V16 complete and audited; V17 packaged/shared loading prepared, collection pending (0/16) | Packaged-gap reproduction and common-file/within-image loading contrasts, then scoped qualification review |
| Step 2: independent controls | Pending | Qualified baseline comparison |
| Step 3: handoff intervention | Conditional | Residual problem and baseline limitation |
| Step 4: history challenge | Pending after qualification | Predicted outcomes and controlled state comparisons |
| Step 5: confirmation/runtime comparison | Later | Locked explanation and precision plan |

For future sessions:

1. Read this plan, the gap audit and the latest decision log entry before changing the runner.
2. Continue **Step 1** from the [completed V15 review](../analysis/runtime_io_v15_marker_review/report.md). Do not rerun completed valid trials to obtain a pass. The zero-call rebuild control fails despite matching normalized worker/job/SHA-work instructions, and added clock-count effects are not monotonic. The [completed V16 review and offline audit](../analysis/runtime_io_v16_repeatability_review/report.md) verifies all 12 trials: original-image A/A is within discovery margins, while exact-source rebuilding reproduces executable bytes/configuration but improves timely success outside the neutrality margin. Launch/resource/runtime/power/workload checks match; no causal hidden-state difference is identified. The [V17 protocol](runtime_io_v17_loading_protocol.md) now declares the named common-file/loading control, four image/loading conditions, balanced order, startup provenance and stopping/interpretation rules. [Preparation verified](runtime_io_v17_preparation_verification.md), performance unstarted. Next collect from its external-terminal launcher; packaged-gap reproduction must precede claims about removal of the gap. A common backing file remains a discovery control, not an established remedy. Do not pool V14's warmer and V15's cooler sessions as matched trials. Qualify persistent records only after a trustworthy control is established, before the proposed independent worker/parallelism comparison. No automatic promotion or scheduling intervention.
3. Preparation can proceed during normal desktop use. Performance measurements need a separate quiet window and the validated host/thermal protocol. Preserve temperature and progress monitoring, with consistent monitor cost across arms.
4. After each stage, update the tracker and append: date; protocol/session/report paths; accepted findings and uncertainty; rejected explanations; decision; next task. If scope changes, write the reason here so old proposals do not silently become current again.

### Decision log

**2026-10-03 — scope agreed.** Retain the broader fixed-quota/parallelism/history/runtime question. First investigate deadline misses after main computation, motivated by V12's 500 ms classification. Measurement qualification and known-control comparison come before a new remedy or broad matrix. Novelty remains a candidate, subject to causal evidence and renewed comparison with closest work. Next task: prepare Step 0 and the observer qualification design.

**2026-10-03 — V13 implemented.** Prepared [protocol](runtime_io_v13_completion_protocol.md), isolated locked/bounded service variants with publication brackets, all-offered deadline analysis, four matched three-arm blocks, frozen-source/attempt/output verification, interruption/resume, quiet-host checks and temperature/progress display. Build: `analysis/runtime_io_v13_completion_build`; [functional verification](../analysis/runtime_io_v13_completion_build/functional_verification.json). Both new stock-Go builds passed Go tests; six unquotaed real-HTTP fixtures passed across all three arms at GOMAXPROCS=1/2. Python regression and offline export/seal checks passed; see [preparation record](runtime_io_v13_preparation_verification.md). Functional results establish implementation correctness only. New markers and completion-counter bookkeeping are an observer change, qualified by legacy→locked; locked→bounded tests dynamic shared storage while retaining the mutex. No exact runnable-readiness or request-level throttle evidence is claimed. Next task: quit the desktop app, collect V13 in the validated quiet window, inspect its matched observer report, then decide whether Step 2 is justified.

**2026-10-03 — V13 completed and reviewed.** All 12 trials completed and the original frozen-source, raw-attempt and analysis seals verified. [Sealed report](../results/diagnostic/runtime-io-v13-completion-qualification-1/session/analysis/report.md); [derived observer review](../analysis/runtime_io_v13_observer_review/report.md). Legacy→locked loses 5.76–10.88 percentage points of 500 ms timely success across four blocks (median loss 7.79), increases CPU/job by 1.71–2.58%, and worsens successful p99 by 13.19–21.38%. Locked→bounded passes the four practical screens with no consistent timely benefit. The legacy arm reproduces 2,021 late successful responses whose main work certainly finished by 500 ms. Marked recording/publication p99 intervals are microseconds while publication→handler execution lower-bound p99 is about 161–164 ms, but those intervals belong to the materially affected observer. Reject qualification of that combined observer; do not claim dynamic append is the main cause or attribute legacy delays solely to runtime scheduling. Next task: isolate timestamp, post-publication second-lock/bookkeeping and slot-layout costs in a new observer ablation while preserving legacy handoff/counter order; design safe drain/export/reset evidence and requalify before Step 2. Existing valid trials are retained; no new benchmark was launched by this review.

**2026-10-04 — V14 overnight ablation prepared.** Implemented four isolated new stock-Go arms (clocks-only, passive worker buffers, passive buffers with post-publication mutex and original counters, then moved counters) beside exact V12/V13 reference images. Eight six-arm blocks give 48 trials with all pairs balanced four times in each relative order; the first six orders balance position and immediate carryover. Resource settings, legacy event storage/HTTP behavior and offered arrival anchor remain fixed. Passive recording uses immutable single-writer prefixes with atomic publication and a separate control-plane drain/reset check. All normal Go/race checks and twelve unquotaed real-HTTP fixtures passed; 131 Python diagnostic checks passed, including export/seal, overflow/pending validation, order balance and quiet-host refusal. [Protocol/launch](runtime_io_v14_ablation_protocol.md); [preparation record](runtime_io_v14_preparation_verification.md); build `analysis/runtime_io_v14_ablation_verified_build`; new results target `results/diagnostic/runtime-io-v14-observer-ablation-1`. The first unsealed preparation attempt is preserved separately after host trace tests could not write `/runtime.trace`; only the host race-check fixture output path was redirected, with source adjustment/hashes recorded, and the full race suite then passed. No performance batch was launched during preparation. Next task: save work, run the external-terminal overnight launcher in the validated quiet window, then review the seven predeclared contrasts before Step 2.

## 6. Supporting files

- [Completed V13 observer review and next measurement decision](../analysis/runtime_io_v13_observer_review/report.md)
- [V14 overnight observer-ablation protocol and launch](runtime_io_v14_ablation_protocol.md)
- [V14 preparation verification](runtime_io_v14_preparation_verification.md)
- [V13 executable protocol and launch commands](runtime_io_v13_completion_protocol.md)
- [V13 preparation verification](runtime_io_v13_preparation_verification.md)
- [V12 tradeoff audit](../analysis/runtime_io_v12_tradeoff_review/report.md)
- [Verified literature/gap audit and new deadline evidence](../analysis/runtime_io_v12_tradeoff_review/gap_audit_and_completion_deadlines.md)
- [Prior-work tradeoff comparison](../analysis/runtime_io_v12_tradeoff_review/prior_work_comparison.md)
- [Deadline classification script](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work.py), [machine-readable results](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work.json), [request-level evidence](../analysis/runtime_io_v12_tradeoff_review/deadline_after_work_requests.csv)
- [Earlier research map](runtime_io_prior_art_review.md)

The gap audit records source verification and retrieval limits for Go's quota-aware defaults, thread management, TailClipper, deadline scheduling, concurrency limits and other close approaches. Use that evidence before claiming a method is new.

**2026-10-04 — V14 stopped and next design agreed.** The user stopped V14 at 17/48 and selected a new isolated batch after [partial review](../analysis/runtime_io_v14_partial_review_17/report.md). All 17 completed raw attempts and frozen evidence validate; block 3 V13 attempt 001 failed cooling before performance measurement, ending at 44.25°C against the 58.95°C baseline. Legacy→clocks loses 12.63/13.43 points in the complete blocks, while extra-lock changes are smaller/mixed; CPU/job rises about 3.2–3.4% and queued backlog grows. Passive cannot pass the unchanged all-pairs rule with retained pairs. Preserve this incomplete exploratory batch and do not relax its margins or baseline. [Static binary audit](../analysis/runtime_io_v14_compiler_audit/compiler_audit/audit.json) finds matching normalized SHA-work instructions in legacy/V13/V14 but different surrounding paths; it does not prove equal timing. Next: prepare the [V15 protocol](runtime_io_v15_marker_protocol.md) on the original worker/job path, with a zero-call rebuild control, incremental calls, exact V14 clocks reference and a separate measured/frozen baseline.

**2026-10-04 — V15 prepared and verified.** Implemented the [inline-marker progression protocol](runtime_io_v15_marker_protocol.md), separate builder/runner/analyzer and external-terminal launcher. Four new original-path images (zero/one/two/five calls) join exact legacy and V14 clocks references for four matched six-arm blocks, 24 trials. Actual-binary audit confirms the intended call counts, matching normalized SHA-work instructions and a zero-call job/worker instruction match to legacy. Full normal Go and all four race suites, twelve real HTTP fixtures, shell syntax and 144 Python checks passed; see the [preparation verification](runtime_io_v15_preparation_verification.md). The verified build is `analysis/runtime_io_v15_marker_verified_build`; first unsealed preparation is preserved after a missing Python HTTP import stopped fixtures, corrected before the verified build. The new session measures and seals its own accepted idle baseline, checks it before resume, and has a verified-identity graceful stop command. Performance remains unstarted at 0/24. Next: launch `bash diagnostic/start_marker_batch.sh` from an external terminal in a quiet AC/Balanced window, inspect the six declared contrasts and rebuild control, then design/qualify persistent records only if justified. A passing discarded-clock screen cannot qualify a full recorder or automatically launch Step 2.

**2026-10-04 — V15 completed and reviewed.** All 24 trials completed, with no invalid attempts or failures; original frozen-source, complete build-bundle, environment, attempt and analysis seals verified. [Sealed report](../results/diagnostic/runtime-io-v15-inline-markers-1/session/analysis/report.md); [derived review](../analysis/runtime_io_v15_marker_review/report.md). Fresh idle baseline 42.04°C; accepted trial means 41.78–43.97°C and collection k10temp samples 53.75–62.25°C pass the declared checks without proving thermal equivalence. Legacy→five inline clocks loses 12.91–13.56 percentage points of 500 ms success, CPU/job +2.56–2.64%, successful p99 +23.31–24.06%. The zero-call rebuild also loses 3.62–7.42 points (paired median 6.42), while two calls improve timely success over one by 0.62–1.97 points; added three calls have smaller/mixed effects. The remaining V14 worker-path bundle is much smaller than the main deficit, but not within every practical pair. Queue p99 grows from median 498 ms in legacy to 675–695 ms in marked arms; post-work p99 stays about 161–162 ms. Legacy retains 2,341 successful late-after-work responses. Reject observer qualification and a pure per-clock-cost explanation. Static normalized instruction identity did not establish a behaviorally neutral rebuild control. Next: exact-image A/A repeatability and an exact-source/no-extra-metadata rebuild, with full binary/control-plane audit, then persistent-recorder qualification if justified. No new performance batch was launched by this review; V14 remains retired/incomplete and its warmer baseline is not pooled with V15.


**2026-10-04 — V16 prepared and verified.** User authorized the baseline diagnostic checkpoint. Prepared the [repeatability/rebuild protocol](runtime_io_v16_repeatability_protocol.md), isolated offline uncached exact-source builder, three-arm/four-block runner and external-terminal launcher; [verification](runtime_io_v16_preparation_verification.md). Both A/A labels reference the same retained V12 image. Exact-source rebuild reproduces full executable bytes, Go build ID and Docker image configuration; V15 metadata-zero remains a different binary. Original Go tests, six short HTTP fixtures and 60 Python checks passed without skips. All performance trials remain unstarted (0/12). A/A and rebuilding are collected within the same session to reduce session confounding, with A/A interpreted first; a failed A/A screen prevents rebuild attribution. Four blocks remain discovery/precision evidence, not equivalence. Next: collect V16 from the external-terminal launcher in a quiet AC/Balanced window, review repeatability and then decide the minimum justified recording/precision work. No automatic marker qualification, worker matrix or scheduler intervention.


**2026-10-04 — V16 completed; offline execution audit complete.** User completed the 12-trial batch in 47 minutes 34 seconds. Original frozen-source/build/environment/raw/analysis seals verified, all 12 accepted with no quality flags. [Sealed report](../results/diagnostic/runtime-io-v16-repeatability-1/session/analysis/report.md); [derived review/audit](../analysis/runtime_io_v16_repeatability_review/report.md). Original-image labels differ by 0.09–0.56 percentage points at 500 ms within all discovery margins. Exact-source rebuilt executable/configuration remain identical, yet both comparisons improve 500 ms success by 1.53–3.92 points outside neutrality margins. Actual launch arguments, cgroup limits, runtime/power settings and every scheduled arrival vector match. Load-temperature sample means span 59.98–60.85°C; sampled host observations do not identify a causal difference. Rebuilt runs have slightly lower aggregate CPU/job and queue p99, with similar post-work p99. Late responses whose computation finishes before 500 ms persist: A 2,344, B 2,311, rebuilt 2,381, each of 27,172 offered. Build byte reproducibility is established; behavioral neutrality/clock-cost attribution is unresolved. Next: a narrowly declared container-execution/loading control or explicit precision redesign; persistent markers and worker/scheduler interventions remain gated. This offline audit launched no performance study and changed no sealed session evidence.


**2026-10-04 — V17 shared-file loading prepared and verified.** User authorized the next container-execution control. Prepared [protocol](runtime_io_v17_loading_protocol.md), isolated assets/helper builder, four-cell/four-block runner and external-terminal launcher; [verification](runtime_io_v17_preparation_verification.md). The exact original and rebuilt images each execute their packaged binary or one common read-only host file, with unchanged executable bytes and V12 client. Every arm uses the same before-warmup process/mount provenance check, no new service code or request tracing. Eight real HTTP/loading fixtures verify the actual common device/inode and executable hash across both images; two helper Go tests and 73 Python checks passed without skips. Each arm occupies each position once; every within-block directed transition appears once. A packaged gap absent in this session prevents claiming the mount removed V16's effect. No pure filesystem/cache/scheduler attribution or automatic recorder/control promotion. Build/fixtures and assets are sealed; the session seals shared-file identity after its single copy. All performance trials remain unstarted (0/16). Next: save work and launch V17 from the external terminal in a quiet AC/Balanced window, inspect all four contrasts and interaction before deciding further work.
