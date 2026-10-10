# V13: post-computation measurement qualification

Prepared 2026-10-03 for Steps 0–1 of [current_research_plan.md](current_research_plan.md).
This is an executable discovery protocol. Functional fixtures qualify correctness; performance observer qualification remains pending until the separate quiet-host collection completes.

## Objective and declared outcomes

Determine whether dynamic shared event recording materially changes the observed post-computation deadline loss, and whether the additional boundary observer is sufficiently stable for the next scoped comparison. No scheduling policy, yielding, admission change or worker/parallelism treatment is introduced here.

The primary target is **500 ms from scheduled arrival to successful client completion**, selected from V12's exploratory effect. This is a study deadline, not a production SLO. Denominator: every offered ID, including rejection, timeout, transport error, late success and client/server drain. The 1,000 ms timely-success fraction, total failure fraction, successful p99 and CPU per completed job are guardrails. Save in-window and cohort/drain throughput separately. Work finishing after client cancellation remains in server counts.

A practical observer screen uses absolute paired changes no larger than **0.01** in timely fraction at either deadline, **0.001** in failure fraction, **5%** in CPU/job and **10%** in successful p99, in each of four matched blocks. These are deliberately conservative discovery margins, not powered equivalence tests. Record every paired delta and block median/range. A missing denominator or guardrail fails the screen. A difference outside the screen is evidence requiring review, not a technical failure eligible for rerun.

## Small matched design

Four independent trial blocks, three arms per block (**12 trials**):

| Arm | Worker/handler/entry event storage | Publication observer |
|---|---|---|
| legacy | Exact retained V12 service image and client | Absent |
| locked | Existing shared-mutex slice appends | Fixed ID slots for boundaries |
| bounded | Preallocated ID slots under the existing service mutex | Same fixed ID slots for boundaries |

The bounded arm removes growing slice appends and their allocation costs from worker/handler/entry storage; it retains the admission, counter and handler-exit mutex. It does not remove all contention. Both new arms allocate 32,768 fixed slots before warmup. Request ID zero is valid; reuse or capacity overflow is an explicit recording error that invalidates the attempt. Slots clear only after complete drain on reset; buffers never wrap. Export scans and copies occur after workload drain, outside server workload CPU accounting.

Both new arms finalize the worker completion counter after publication and its marker commit so drain cannot race an incomplete boundary. This moves bookkeeping relative to V12, and adds a post-publication mutex. **Legacy versus locked qualifies this combined observer**, not solely clock-call cost. Do not treat a difference as proof of legacy event-lock causation. Locked versus bounded holds that observer and bookkeeping constant. New variants use the retained, digest-pinned stock Go 1.26.1 compiler; no runtime patch or runtime trace is enabled.

Order is fixed before collection: legacy/locked/bounded; bounded/locked/legacy; locked/legacy/bounded; bounded/legacy/locked. This counterbalances legacy-versus-locked twice in each order and distributes other positions as closely as four blocks allow. Four is not divisible by three; order balance is incomplete and no randomization claim is made.

All arms retain V12's GOMAXPROCS=1, four workers, queue=128, 44,000 SHA iterations/job, deterministic bursty anchor=113.21 requests/s, low/high=56.605/169.815, alternating five-second halves of a ten-second cycle, 20 s warmup, 60 s arrivals, five-second client timeout and full drain. Use the same client binary and exact ID/scheduled-offset vector within each block; the analyzer checks vector identity. Quota and period remain **cpu.max=50000 100000**, burst=0, with the existing CPU affinity and unconstrained ancestor requirement. The runner verifies actual values, clock namespaces, power settings, monitor evidence and temperature criteria.

The separate proposed 16-trial GOMAXPROCS × worker comparison remains gated on this report and review. Passing this discovery screen only qualifies preparation for that comparison.

## Boundary map and ambiguities

| Marker | Meaning |
|---|---|
| completion_ns | Main SHA loop finished, before result recording/publication |
| record_start_ns | Worker about to acquire service mutex for event storage |
| record_lock_ns | Worker executing after mutex acquisition |
| record_end_ns | Worker executing after event storage and mutex unlock |
| publish_start_ns | Worker executing immediately before buffered result send |
| publish_end_ns | Worker executing immediately after that send returns |
| resume_ns | Handler executing after receive/select; **not** first runnable time |
| write_end_ns | ResponseWriter.Write returned; **not** socket flush or client receipt |
| handler_exit_ns | Existing final storage marker, before mutex unlock/function return |
| client completion | Existing full client response outcome, including drain |

The result becomes available somewhere within `[publish_start_ns, publish_end_ns]`. The handler may execute before the sender samples publish_end_ns. Preserve publication-to-resume as `[max(0, resume−publish_end), resume−publish_start]`; do not reject that legitimate overlap. A publication/deadline overlap is ambiguous. No handler record after cancellation is unobserved receipt/execution, not proven failure to become runnable.

Six client/server monotonic round-trip anchors outside arrivals/drain retain lower/upper offset bounds. Generation change, disagreement, uncertainty over 1 ms or shifted time namespace invalidate the attempt. Deadline classification uses bounds, never their midpoint. Distinguish timely success, main work certainly after deadline, main work overlapping deadline, work before with resume before/after/ambiguous/unobserved, and work unobserved. Keep unsuccessful requests distinct from successful late delivery. Retain the 50 ms work-before margin as secondary evidence.

Record-lock wait, held interval and publication brackets are wall intervals containing possible preemption and quota pauses. The monitor and cgroup CPU samples qualify environment/resource use and supply aggregate usage/throttling evidence. They do **not** expose instantaneous remaining quota, per-request kernel off-CPU state or exact runtime readiness. V13 can qualify and localize service intervals, but cannot separate quota blocking from runnable competition. Any required runtime/kernel observer needs its own declared qualification; do not infer a scheduler defect from these markers.

## Competing explanations and decisions

- **Added measurement changes behavior:** legacy→locked exceeds practical margins. Review observer/bookkeeping changes; do not advance on the marked intervals alone.
- **Dynamic event storage is consequential:** locked→bounded changes deadline loss or CPU/job outside margins. Inspect recorded wait/storage intervals and paired external outcomes; repair/remeasure the recorder before the controls study. Removing appends is not an intervention on all locking.
- **Loss persists with qualified storage:** marker comparison passes and bounded recording retains substantial work-before/late delivery. Prepare independent worker/GOMAXPROCS controls next, reporting capacity as well as latency.
- **Ordinary quota/capacity or transport costs explain loss:** preserve as alternatives. Aggregate counters and client/write stages alone cannot establish individual causal attribution; test a named unresolved explanation only after this review.
- **No consequential residual or insufficient precision:** report that outcome. Do not force a new scheduling policy or novelty claim.

## Technical acceptance, sealing and reruns

Each attempt must pass the retained full-outcome, exact ID accounting, timing-header, response-write, actual image/configuration, cgroup, quiet-host, power/thermal and clock checks. Successful IDs must have entry, worker and handler evidence. Every admitted/completed job in marked arms must have exactly one ordered publication record. Recording errors must be zero. Missing external entries remain unknown and count in all offered denominators. Client drops or malformed/contradictory evidence fail existing checks; a genuine rejection/timeout is a study outcome, not a rerun reason.

Preserve all attempts and logs. A failed technical attempt stops collection; inspect its evidence before explicitly rerunning the same start command. Resume uses already-valid trials and new numbered attempts for invalid trials, refusing duplicate valid attempts or leftover owned containers. Sources, protocol, matrix, compiler/image IDs, client binary, prepared sources, functional fixtures and calibration are hashed and frozen in a distinct session. Current-source drift blocks collection resume; frozen-source/attempt/output drift blocks completion verification. Analysis of a sealed completion verifies rather than overwrites it.

## Build and functional verification

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -m unittest discover -s diagnostic -p 'test_completion.py' -v
python3 diagnostic/build_completion.py build
python3 diagnostic/completion_study.py verify-build
python3 diagnostic/completion_study.py plan
```

Build outputs: `analysis/runtime_io_v13_completion_build`. Retained V12 build must verify. Build-time Go checks cover cancellation, rejection, zero/duplicate/overflow IDs, reset, record conservation, ordering and existing service/client behavior. Six unquotaed real-HTTP fixtures cover all three arms at GOMAXPROCS=1/2 and both declared deadlines. These fixtures are functional verification, not research measurements. Existing build directories are never replaced; preserve a failed build and use `--directory` to prepare another. The study's `build.DEFAULT` must designate that reviewed build before collection; custom build paths are for repair/inspection, not silent substitution.

## Quiet-window launch and progress

Save work, fully quit the ChatGPT/Codex desktop app, and use an external terminal. Keep the laptop plugged in, Balanced power profile, lid open, and the established quiet-host/thermal settings. The retained guard refuses collection while the desktop app is present. Preparation and functional checks can run with the app open.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/completion_study.py start
python3 diagnostic/completion_study.py status
python3 diagnostic/completion_study.py watch
```

Wait for “Started in background with sleep inhibition” before closing the launch terminal. Budget **60–120 minutes**, allowing more for cooling/drains. The minimum collection arithmetic is 28 minutes for twelve × (60 s settling + 20 s warmup + 60 s arrivals), plus ten-minute initial idle, startup/drains and analysis. The progress display stays on client/monitor CPUs, shows validated trials/12, phase, elapsed time, live temperatures and accepted baseline. Ctrl+C closes only the display.

New results: `results/diagnostic/runtime-io-v13-completion-qualification-1/session/analysis/report.md`, `trials.csv`, `requests.csv`, `observer_screen.json`, `validation.json`; original V12 evidence is untouched. Completion seals are at the new result root. Inspect the report and update the research-plan decision log before advancing.
