# Bursty stock-Go parallelism comparison

Prepared 2026-10-03 after the [prior-work review](runtime_io_prior_art_review.md). This tests a known configuration remedy in the missing bursty case. It does not claim a new scheduler mechanism or fix.

## Question and fixed design

Does changing stock Go 1.26.1 from GOMAXPROCS=2 to 1 reduce long handler-entry delay while preserving useful throughput and admission outcomes at the same half-CPU budget?

Eight trials, four pairs, order **2/1, 1/2, 1/2, 2/1**. Both use the same stock service image, four application workers, a 128-slot channel queue, 44,000 SHA iterations, `cpu.max=50000 100000`, `cpu.max.burst=0`, server affinity 2,4 and client/monitor affinity 0,1. Mean offered rate is 113.21 requests/s, five-second low/high phases at 56.605/169.815 requests/s. Arrival offsets use the retained deterministic integrated-rate inversion, identical in both arms. Warmup is 20 seconds and measurement 60 seconds (six complete burst cycles). Timeout is five seconds and client concurrency 512. There is no recalibration.

Runtime tracing, custom network recording, decision/queue observers, scheduler patches and worker yielding are off. Application/HTTP-client stage instrumentation is on in both arms. The stock compiler is the retained Go 1.26.1 image ID; the build neither patches its runtime nor changes earlier images/builds.

## Entry coverage and clock boundaries

The isolated service retains an additional entry/exit/admission record for every valid work request, including rejected and cancelled handlers. Entries are captured at the existing handler-entry timing site and exported only after draining. Successful-response handler/worker timing records remain available separately. Additional entry records use the existing handler-exit lock; they add application observation cost in both arms, so stock refers to the runtime rather than an uninstrumented application.

The isolated client samples `/clock` three times before offered arrivals and three after client drain, on a separate control connection. Each server-origin timestamp is bracketed by client-origin monotonic timestamps. Intersect offset intervals with a unit slope; disagreement, reset-generation changes or uncertainty over one millisecond fail technical validation. No wall-clock midpoint is substituted. Ordinary Linux host/container monotonic clocks must share an unshifted time namespace; the runner verifies host/container time-namespace offsets are zero. Clock-control costs occur outside offered arrivals but inside server CPU accounting; client workload CPU excludes them. The anchor brackets and original timestamps remain sealed.

For every offered request, retain its outcome and scheduled/dispatch-to-entry bounds. Client dispatch is the request worker's start, not an exact wire-send event. An absent entry is unknown rather than zero latency or proven non-entry; it widens possible-entry and possible-long-wait bounds. Report certain/possible entry by one/five seconds and counts of unknown entries. Rejected/cancelled entries remain in denominators. A client-side drop or incomplete offered-ID accounting fails the existing collection checks instead of disappearing from the analysis.

Report successful E2E p99, success throughput completed inside the measurement window, cohort/drain throughput, rejection, timeout/error fractions, queue waits for successful and all completed jobs, post-client completions, CPU/job, usage and throttled-period fraction. Do not add stage percentiles. Exact network-ready-to-selection time is unavailable in this stock comparison.

## Predeclared diagnostic screen and next action

Baseline symptom: each of the four two-processor trials must have certainly long (>=1 s scheduled-to-entry) observations. Successful client-trace coverage must be >=99% in every trial. Failure of those conditions makes the diagnostic comparison inconclusive.

For a conservative pass, each one-processor trial's **possible** long-entry fraction must be lower than its paired two-processor trial's **certain** long-entry fraction. The ratio of median possible one-processor fraction to median certain two-processor fraction must be <=0.5. Median successful E2E p99 must also fall by >=50%, median total failure fraction may rise by at most 0.001, and median in-window successful throughput may fall by at most 5%. Missing entries count in the conservative upper bound. These refine the review's screen by making its clock/coverage requirement explicit; they are descriptive criteria with four pairs, not statistical significance or SLO certification.

If tuning passes, report an existing remedy validated for this case. CPU/job changes identify a capacity change, so improvement cannot be attributed entirely to fairness. If delay moves into application queueing/failures, examine that tradeoff. If long delays remain with valid coverage, localize the residual with a separately controlled queue-history observer before choosing any scheduler intervention. No further performance collection is automatically launched.

## Build and functional verification

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/build_parallelism.py build
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
python3 diagnostic/parallelism_study.py verify-build
```

Build outputs are isolated at `analysis/runtime_io_v12_parallelism_build`. Build-time Go tests include failed/cancelled entry capture and clock/reset cases. Two short real-HTTP fixtures verify both processor settings, request ID zero, entry linkage and clock brackets. These fixtures use no CPU quota and are functional checks, not research results. A completed build refuses replacement; verification is read-only. A failed unsealed build must be inspected and preserved before preparing a new build.

## Launch after quitting the desktop app

Save work and fully quit ChatGPT/Codex. Launch from an external terminal with the laptop plugged in, Balanced power profile and lid open. The existing quiet-host guard, thermal settling, shared experiment lock, monitor/quality checks and child/ancestor quota checks remain enforced.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/parallelism_study.py start
```

Wait for **Started in background with sleep inhibition** before closing the terminal. Allow **45–90 minutes**, longer if cooling or an interrupted attempt requires more settling. Arithmetic minimum is 18.7 minutes for eight times (60 s settling + 20 s warmup + 60 s measurement), plus the ten-minute initial idle, startup, drains and analysis. Building is separate.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/parallelism_study.py status
```

For a live display refreshing every five seconds, use another external terminal:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/parallelism_study.py watch
```

It shows completed/total trials and percentage, current trial/attempt, elapsed time, cooling/warmup/measurement phase, current sensor temperatures and the accepted initial baseline. Phase labels use saved collection files, so combined labels such as measurement/client drain reflect that boundary uncertainty. The counter updates immediately after each validated trial, including before resume settling. Current temperatures are live host readings, not reconstructed measurement samples. The separate display is pinned to the client/monitor CPUs and starts no workload. Ctrl+C closes only the display; the background experiment continues. The existing per-minute settling messages and new `DONE n/8` temperature summaries remain in the launch log. The display exits automatically on completion, failure or interruption.

Default results: `results/diagnostic/runtime-io-v12-bursty-parallelism-1/session/analysis/report.md`, `trials.csv`, `entry_delays.json`, `remedy_screen.json`, `validation.json`. Technical completion and passing the remedy screen are separate. The source bundle preserves this protocol, the prior-work review and the audited steady-comparison summary, together with the stock build and original calibration.

On interruption, preserve all attempts/logs and rerun the same start command after quitting the app. Changed sources/builds/protocol, duplicate valid attempts, leftover owned containers or altered sealed evidence cause refusal. Completed analysis is hash-checked and not silently overwritten. There is no pilot-to-full qualification gate or automatic larger study.
