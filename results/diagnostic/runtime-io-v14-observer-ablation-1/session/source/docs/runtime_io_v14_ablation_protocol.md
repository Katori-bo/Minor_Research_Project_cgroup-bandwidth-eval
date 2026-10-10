# V14 observer ablation: overnight discovery protocol

Prepared 2026-10-04 following the sealed [V13 observer review](../analysis/runtime_io_v13_observer_review/report.md). This batch remains within Step 1 of the [current research plan](current_research_plan.md). Do not launch a worker/parallelism or policy comparison automatically from its results.

## Question and design

V13's combined observer reduced 500 ms timely-success fraction by 5.76–10.88 percentage points in every block. Which observer changes contribute to that difference, and does a passive worker buffer qualify against the original service?

Use **eight matched blocks × six arms = 48 trials**. The first six blocks use a six-treatment Williams order, balancing treatment positions and immediate predecessor/successor combinations within those blocks. The last two use one original order and its reverse. Every pair appears four times in each relative order across eight blocks. These are deterministic declared orders, not randomized orders or proof of independent host state. Between-trial settling and the original workload/reset remain mandatory.

| Arm | Additional clocks/recording | Counter position | Extra service mutex after send |
|---|---|---|---|
| legacy | Exact retained V12 service image | Before send | None |
| clocks | Five boundary clock calls; values consumed locally, no record buffers | Before send | None |
| passive | Same five calls, fixed single-writer buffer per worker | Before send | None |
| mutex_early | Same passive buffer and calls | Before send | Protects record commit |
| mutex_late | Same buffer and calls | After send/record commit | Protects record and counters |
| v13 | Exact retained V13 locked image, large ID-indexed storage/ID checks | After send/record commit | Protects record and counters |

The four new arms retain legacy SHA work, growing legacy event/handler/entry slices, response body/headers, buffered channel publication, cancellation behavior, queue/admission locks and worker/queue settings. For clocks/passive/mutex_early the event-save → completion/abandonment counters → unlock → buffered-send order is unchanged. The new worker function/control path is shared across these four arms. The clocks arm additionally contains a local clock-order check; this small branch is part of its measured clock/path bundle. No exact original-machine-instruction identity is claimed.

Passive storage allocates **16,384 boundaries per worker**, with no wrap. Each worker is its buffer's sole writer. An atomic committed-prefix count publishes immutable records for live metrics. It adds stores and an atomic publication after result send, so it still needs qualification. The fixed buffer allocation and commit are tested together in clocks→passive; this protocol does not separately identify their individual costs. V13's remaining bundle differs in layout, ID validation and worker/service path; mutex_late→v13 is **not** a pure memory-layout experiment.

## Declared contrasts and decisions

1. legacy→clocks: added clock calls and shared new worker path.
2. clocks→passive: fixed buffers plus record commit.
3. passive→mutex_early: extra mutex around post-publication commit.
4. mutex_early→mutex_late: move completion/abandonment counters.
5. mutex_late→v13: remaining V13 storage/validation/path bundle.
6. legacy→passive: candidate observer qualification.
7. legacy→v13: replication of the combined observer effect.

Primary outcome: successful client completion within **500 ms of scheduled arrival / all offered IDs**. Keep **1,000 ms timely fraction**, total failure fraction, successful p99, actual CPU/job and in-window/cohort/drain throughput. All rejected, timed-out, late, missing-server and cancelled-work outcomes remain explicit. Retain bound-aware post-computation and publication crossing classes only where those markers are observed; legacy and clocks have no detailed publication records.

Retain V13's conservative practical margins: absolute paired timely-fraction change ≤0.01 at both deadlines; failure-fraction change ≤0.001; CPU/job ratio within ±5%; successful p99 ratio within ±10%, in **all eight** candidate-versus-legacy pairs. Missing guardrails fail the screen. Report every contrast's eight paired deltas and block median/range. Screens are diagnostic, not powered equivalence tests, and dependent contrasts are not independent discoveries. A failed practical screen is a valid result, not a rerun criterion. Passing legacy→passive permits manual review of whether it is useful for subsequent controls; it does not automatically declare a mechanism or launch another batch. If the clocks/path bundle alone is consequential, further isolate that bundle before attributing the effect solely to clock calls.

## Fixed workload/resource contract

All 48 trials retain GOMAXPROCS=1, four CPU workers, queue capacity=128, Go 1.26.1 stock runtime, 44,000 SHA iterations/job, 113.21 requests/s deterministic burst anchor, low/high rates 56.605/169.815, five-second low/high phases, 20 s warmup and **60 s offered arrivals**, five-second client timeout and full drain. Exactly the same retained client binary is used for every arm. The analyzer checks identical ID/scheduled-offset vectors within every block. Code/binary and matrix hashes freeze the schedule-generating implementation and parameters before collection.

Actual quota/period must be **cpu.max=50000 100000**, burst=0, retained server/client affinity and uncapped ancestors. Preserve power profile, plugged-in requirement, quiet-host/process checks, thermal settling and monitor cost. Initial/resume idle is at least **600 s** plus a stable temperature window; every trial requires its own stable window near the accepted baseline. No hardware thermal-equivalence claim is made from passing these host checks.

## Drain, live metrics and reset safety

Legacy completion counters can become visible before publication evidence is finalized. The three new recording arms therefore expose `observer_pending_records`, and the control runner waits for it to reach zero **after ordinary client/work/handler drain**, before exporting metrics or resetting. This control-plane check occurs outside offered arrivals; it does not delay handoff or add a hot-path mutex in passive. Health/export/reset retain the original service mutex for consistent legacy counters/events. Each exported buffer prefix is immutable and published by atomic count; resets require completed==admitted, empty queue, no active handlers and zero pending observer records, then clear prefix counts for the next generation. Worker ownership persists across reset. Clocks-only has no persistent records to drain and uses a cached origin for its final clock calls.

Overflow increments an explicit dropped-record counter without overwriting or blocking publication. Duplicate IDs are not newly rejected in the HTTP path; final record joining must reject duplicate/unknown IDs. These cases fail technical acceptance. Successful/cancelled jobs must conserve worker records in every recording arm. Reset, cancellation, simultaneous metrics reads and buffer publication require meaningful Go race checks before launch.

Bounded-clock mappings retain six external anchors, zero host/container time namespace offsets, generation identity, ≤1 ms uncertainty and interval bounds rather than midpoints. Publication is inside [publish_start, publish_end]; handler execution may precede sender-end sampling. Preserve overlap. Handler execution is not runnable readiness. Wall-clock lock/publication intervals include possible quota pauses and preemption; monitor/cgroup samples do not measure instantaneous remaining quota or per-request off-CPU attribution.

## Functional preparation and sealing

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -m unittest discover -s diagnostic -p 'test_ablation.py' -v
python3 diagnostic/build_ablation.py build
python3 diagnostic/ablation_study.py verify-build
python3 diagnostic/ablation_study.py plan
```

Preparation uses separate sources/images under `analysis/runtime_io_v14_ablation_verified_build`. V12/V13 builds verify before reference reuse. Four new images run stock-Go tests with build networking disabled. Race checks use the retained compiler SDK plus existing host GCC, with temporary caches and downloads disabled; no installation is needed. The host race-check source copy redirects only the inherited `/runtime.trace` fixture output to its owned temporary directory; this adjustment and the tested source hashes are recorded, and production images retain their original path. The initial unsealed build with a host fixture-path failure is preserved at `analysis/runtime_io_v14_ablation_build`. Twelve unquotaed HTTP fixtures cover six arms × GOMAXPROCS=1/2. They verify implementation behavior/clock joins, not performance under quota. Build, fixture, race log and compiler/prepared-source hashes are retained. Current source drift invalidates collection resume; frozen source, complete build-bundle, attempt and output drift invalidate verification. Completed V12/V13 data are untouched.

## Overnight launch

Save work and run this from a **normal external terminal**, plugged in, Balanced power profile, lid open:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_ablation_overnight.sh
```

The script sends TERM to the same ChatGPT desktop process checked by the existing guard, waits up to 30 s, starts the detached sleep-inhibited worker, then opens the five-second live display. The display shows initial/resume cooling, accepted baseline, current temperatures, trial/attempt, completed/48, percent, **trials remaining**, elapsed time and log path. Ctrl+C closes only the display. Completion automatically analyzes, seals and saves results; the launcher prints the report when its display returns after completion. Do not reopen the desktop app during collection.

Budget **roughly 3–6 hours**, depending on cooling and host behavior. Arithmetic floor: 48 × (60 s settling + 20 s warmup + 60 s arrivals) = **112 minutes**, plus ten-minute initial idle, startup/drains/export/analysis. The prior 12-trial run took 57 minutes, making around four hours a useful planning estimate for 48 trials, not a promise. Long cooling or technical failure can extend or stop the job. The study ends after its finite 48 trials; it is not a recurring automation or padded duration run.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/ablation_study.py status
python3 diagnostic/ablation_study.py watch
```

On failure/interruption, preserve attempts and logs. Inspect the reason before rerunning `start`; valid trials are retained and invalid attempts get new numbers. Both inherited raw checks and additional observer checks determine technical reuse. Sources/protocol/build drift, duplicate valid attempts or leftover owned containers cause refusal. No automatic retries seek a passing practical screen. Final results: `results/diagnostic/runtime-io-v14-observer-ablation-1/session/analysis/report.md`, `trials.csv`, `requests.csv`, `observer_screen.json`, `validation.json`, `attempt_audit.json` (including technical rejection reasons), and root `completion.json`. Review the contrast evidence and update the research decision log before Step 2.
