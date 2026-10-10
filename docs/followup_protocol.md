# CPU quota follow-up protocol

Revision 2, 2026-09-26, reviewed before any follow-up data collection. This is a local prespecified protocol, not an externally registered study. The completed `20260921-202841` session remains read-only; new sessions use `results/followup/`.

## Verified starting point

The completed study has 300 trials, 60 configurations and five repetitions: periods 10, 50, 100 and 250 ms at quota/period = 0.5, plus unlimited; one/two/four application workers; moderate/high steady/bursty arrivals. GOMAXPROCS is explicitly 2. Its calibration fixed 44,000 sequential SHA-256 iterations, sustainable capacity 133.19/s, unstable capacity 135.70/s, and high rate 113.21/s. Mean successful-request trial p99s under high bursty traffic were 828.76 versus 4302.71 ms for one versus four workers at 100 ms, and 478.78 versus 1157.63 ms at 250 ms. These are observations, not established mechanisms.

## Reference and replication boundary

Jeffery, Jensen and Mortier, [arXiv:2407.11582v1](https://arxiv.org/abs/2407.11582), Sections 2 and 3.1 and Figure 5, describe a worker queue running naive fib(30), uniform open-loop arrivals, and worker-start to computation-finish latency. Queue waiting is excluded from Figure 5 latency. Experiments ran for five seconds with five repeats on Linux 6.2.0 and a dual-socket Intel Xeon Silver 4112, 16 logical CPUs. Figure 5 compares manual execution concurrency with Go's historical automatic concurrency at quota allocations of 1, 2, 4, 8, 16 and 32 CPUs. It shows processing-latency distributions, not a labelled p99. Throughput is summarized across repeats. Exact Figure 5 quota period, arrival rate, warmup, Go version, worker-pool mapping and source-level control method are unavailable from the paper text.

No author experiment artifact is linked in the supplied PDF; the referenced `automaxprocs` repository is a third-party library. The author publication-page search did not identify a Figure 5 artifact. We cannot claim close reproduction. Study A is a selected **adapted replication** of the execution-concurrency comparison, using SHA-256, HTTP, this host, a fractional budget, and explicit GOMAXPROCS. It does not implement the dynamic neighbour-aware pool.

Modern Go behaviour must not be inferred from the 2024 paper. [Go 1.25](https://go.dev/doc/go1.25) introduced cgroup-aware defaults. [Runtime documentation](https://go.dev/src/runtime/debug.go) describes a usual minimum of two execution slots when affinity exposes at least two CPUs, and compatibility defaults that disable container-aware updates for module language version 1.24 and earlier. Our compiler is Go 1.26.1 and the module directive is `go 1.24`; both arms set GOMAXPROCS explicitly. Record compiler/runtime version, environment, affinity-visible CPU count, and actual GOMAXPROCS at start and end. Neither arm is labelled a measured automatic-runtime arm.

## Study A: selected adapted replication

Two configurations, five repetitions each: 100 ms period / 50 ms quota, four application workers, GOMAXPROCS 1 versus 2, steady **176.41 requests/s**, and 44,000 SHA-256 iterations. The rate is 1.3 times the original unstable capacity, selected before collection to maintain runnable work. The earlier draft used 113.21/s, which could leave too little simultaneous work to test excess execution concurrency; revision 2 corrects that issue. Pilot checks require observed aggregate CPU usage between 0.45 and 0.55 CPU in both arms. If either arm is not saturated, stop and document a protocol amendment before full collection; do not silently change the rate.

Four application workers remain fixed while runtime execution parallelism changes. Since a 0.5-CPU budget has no exact positive integer thread match, GOMAXPROCS=1 is the closest controlled arm. This tests a specific concurrency effect on this workload, not reproduction of the paper's full quota sweep. Report elapsed processing for **all completed server jobs**, including work whose client has timed out, and server/client throughput separately.

## Study B: period and worker extension

Eight primary configurations: periods 100/250 ms × application workers one/four × steady/bursty high traffic. Quota is exactly half the period. GOMAXPROCS remains 2. Five repetitions per configuration give 40 trials. Keep the original 44,000 iterations and 113.21/s rate, independently of Study A. No new unlimited controls are in this focused matrix. Existing unlimited results provide historical context only, because they used different instrumentation and collection times.

## Traffic, ordering and boundaries

All 50 full trials have 20-second warmup and 60-second measurement. One seeded shuffle (`20260926`) fixes collection order across both studies; the matrix hash is saved. Steady requests are evenly spaced. Study B bursty traffic starts low and alternates 5 seconds at 56.605/s with 5 seconds at 169.815/s, with equal mean 113.21/s and complete 10-second cycles.

Client affinity is CPUs 0,1; service affinity is 2,4, with topology checked. The load generator has 512 HTTP workers and a 5-second request timeout. The bounded application queue holds 128 waiting jobs. Queue-full requests receive HTTP 503. A client timeout is a distinct outcome; queued/running server work continues. After warmup, wait until every admitted job and HTTP handler finishes, save warmup client/server metrics, then reset service records. Wait up to 30 seconds for server drain at each boundary. A drain failure preserves the attempt and partial metrics; it is not accepted as a completed trial.

## Measurements

For each completed job, record request ID and monotonic offsets from a service-local epoch: admission immediately before the nonblocking enqueue attempt, worker start and computation completion. Queue wait is start minus admission; elapsed processing is completion minus start. Elapsed processing includes preemption/throttling and is **not CPU execution time**. Server duration headers must match completion records exactly. Full instrumentation records whether the client context was already cancelled at completion. Client timeout and cancellation can occur at different points; preserve both client outcomes and server observations, including their ID join.

The client records scheduled arrival, dispatch lag, full-response end-to-end latency, completion offset and timeout classification on its own monotonic clock. No server timestamp is subtracted from a client timestamp. Throughput within the offered window counts only successful responses completed by its end. Also report the successful arrival-cohort count divided by offered duration and the rate including client drain, with distinct names. These differ when work finishes after arrivals stop.

Record queue depth sampled immediately before admission and its maximum across those samples (not a continuous queue maximum); client rejections/timeouts/other errors; actual runtime settings; host temperature/frequency/power traces; and cgroup CPU usage/throttling counters. Retain a cgroup snapshot at client drain and a final snapshot after server drain so continued work is accounted for. The aggregate cgroup interval includes client/server drain and lightweight health polling, excludes serialization of the final event log, and is labelled with its elapsed duration. Cgroup CPU usage is aggregate, not per-request execution time. Scheduler tracing is deferred until a concrete unresolved mechanism question requires it.

## Environment and acceptance

Reuse `scripts/environment_controls.py` unchanged: external power and Balanced profile; initial idle at least 600 seconds; before each trial a 60-second temperature window with range ≤2 C, absolute slope ≤1 C/min, and mean within 3 C of the session baseline. Stop after 1200 additional seconds without stability. Use no ancestor CPU cap, zero `cpu.max.burst`, exact own quota, correct effective affinity and actual runtime settings. Do not change temperature or power settings automatically.

Require unchanged power settings, at least 70% of expected monitor samples, readable temperature/cgroup data, no missed arrivals or client drops, and client dispatch-lag p99 ≤2 ms. Service 503s, timeouts and other application/transport errors are outcomes; exclude only failed technical acceptance checks. A large latency or absence of the expected treatment effect is never grounds for exclusion. Under-load temperature is retained as evidence, not adjusted away automatically.

## Integrity, interruption and retry

Use the original runner's exclusive lock to prevent concurrent experiments. Build manifests bind service/client sources and tests to image IDs and the load-generator binary. Session provenance hashes include imported environment/monitor scripts, protocol, analysis, frozen matrix and original calibration. Explicitly reject stale builds or changed source on resume.

Each trial gets a new numbered attempt directory. Exceptions and handled interrupts write `failure.json`; the next resume retries in a new directory. A completion marker is written only after validation and cleanup and hashes every attempt file. Resume recalculates counts, timing, quotas, environment checks and file hashes; it does not trust a saved empty flag list. A failed attempt is never accepted. Do not overwrite evidence. SIGKILL or power loss may leave an owned Docker container; the runner detects it and requires inspection/removal of the named owned container before resume. Normal Ctrl-C/SIGTERM cleans up child processes and the owned container.

## Small pilot and collection gate

Revision 2 pilot has **eight diagnostic trials**, each with 10-second warmup and 20-second measurement, in a separate session. Four p100/w4/G2 burst trials use instrumentation on/off/off/on, providing two observations per instrumentation state. Off disables server timing calls, event recording and timing headers but retains common counters and workload. Other pilot trials cover p100/w1, p250/w4, and both Study A runtime settings at the saturated rate.

Validate accounting and component timing, both quota periods, both runtime settings, strict environment checks and drain. Go/Python regression tests separately exercise continued work after cancellation, snapshot/reset races, corrupted evidence, and interrupted/retried attempts. The live pilot does not have to produce timeouts naturally. Compare median server CPU microseconds per completed job for instrumentation on versus off; a ratio above 1.10 triggers review. This is a coarse overhead screen with two observations per arm, not a precise overhead estimate. Also require Study A saturation in both arms. Pilot analysis writes `pilot_gate.json`; full collection requires `--pilot-session` and revalidates the accepted evidence and hashes. Failed gates require investigation/amendment, never relaxed checks.

## Run count and duration

Full collection remains **50 trials**, with at least 50 × (60 s settling + 20 s warmup + 60 s measurement) = 116.7 minutes, plus 10-minute initial idle, drain/startup and extra cooling. Plan about 2.5–4 hours when settling is prompt; unstable temperature can extend this substantially or abort a run. The eight-trial pilot takes at least 22 minutes plus startup, drain and extra cooling; allow roughly 25–35 minutes on a quiet host.

## Unattended execution wrapper

The one-command `followup/run_all.sh` wrapper sequences the existing checks and studies without changing the matrix or acceptance criteria. It runs in the background, requests temporary systemd sleep/idle inhibition, holds the shared experiment lock throughout build/tests/collection/analysis, and automatically enters full collection only after the saved pilot passes all checks. Pilot and full data use separate subdirectories of `results/followup/all-in-one/`. It writes `COMPLETED.md` only after final analysis validates all 50 full trials. Failures stop the workflow and retain stage logs and trial attempts; a later explicit rerun resumes existing sessions without rebuilding their frozen binaries. No follow-up data had been collected when this wrapper was added.
