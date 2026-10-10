# V15: inline marker progression on the retained worker path

Prepared 2026-10-04 after the [17-trial V14 exploratory review](../analysis/runtime_io_v14_partial_review_17/report.md). V14 remains an incomplete, stopped batch. Its retained candidate pairs exceed the frozen all-pairs screen; completing it cannot yield a pass. Do not replace its source, results or baseline. V15 is a separate Step 1 experiment, not the worker/parallelism comparison.

## Question and static audit

V14 legacy→clocks combines five clock calls with a replacement worker path and a local order check. Its two complete blocks lose 12.63–13.43 percentage points of 500 ms timely success. V15 asks whether clock calls inserted directly into the original job function reproduce that penalty, and how it changes as calls are added.

[Actual-binary V14 audit](../analysis/runtime_io_v14_compiler_audit/compiler_audit/audit.json) finds matching normalized `main.work` instructions in legacy/V13/V14, including the SHA loop, but different surrounding worker paths. Normalization removes source lines and instruction addresses; it does not prove identical alignment, cache behavior, scheduling or CPU demand. V15 additionally records disassembly, compiler escape/inlining diagnostics and binary hashes. The build must confirm retained one/two/five `time.Since` calls and identical normalized SHA-work instructions. Zero-call job/worker instruction comparisons are reported separately.

## Six arms, four matched blocks: 24 trials

| Arm | Change relative to retained V12 |
|---|---|
| legacy | Exact original service image |
| rebuilt_zero | Rebuilt original worker/job path, zero new marker calls; metadata added to health/metrics |
| before_one | One clock call immediately before buffered result send |
| bracket_two | Same pre-send call plus one immediately after send |
| boundary_five | Three additional calls before event lock, after acquisition, and after unlock; two send-boundary calls retained |
| v14_clocks | Exact retained V14 clocks image, including its replacement worker path and local order check |

New variants are generated from the original stock entry-recording service by anchored source insertions into its original `runJob`. No replacement worker loop/helper, per-job mode dispatch, new locks, ID validation, buffers, event fields or counter repositioning. For all new variants, event save→completed/abandoned counters→unlock→buffered send remains intact. Marker results are discarded, not exported. The one/two/five variants cache the origin before the original event lock so post-send calls cannot race a drained reset. This local origin load, marker placement, generated-code/frame changes and calls are part of each declared treatment; pure instruction-level clock cost is not claimed.

This is a **clock-cost discovery screen**, not qualification of a full publication recorder: it exports no persistent publication brackets. Existing worker completion/handler execution and bounded external clock mapping remain available. No newly measured runnable readiness or per-request throttling is claimed.

Let arm indices be the table order. First order = [0,1,5,2,4,3], second order = first with indices rotated by one. Block orders are first, reversed first, second, reversed second: four distinct orders. Every arm pair appears twice in each relative order. These deterministic four blocks do not fully balance all six positions or immediate carryover. Keep this limitation explicit; do not describe order as randomized.

## Declared comparisons and decision

1. legacy→rebuilt_zero: build/metadata/layout control.
2. rebuilt_zero→before_one: cached origin and one pre-publication clock call.
3. before_one→bracket_two: one post-publication clock call and associated generated code.
4. bracket_two→boundary_five: three event-boundary calls and associated generated code.
5. boundary_five→v14_clocks: remaining V14 worker-path/order-check bundle, not a pure helper-call effect.
6. legacy→boundary_five: practical cost screen for the five inline marker calls.

Primary: successful completion within 500 ms of scheduled arrival / **all offered IDs**. Guardrails: 1,000 ms timely fraction, failure fraction, actual CPU/job and successful p99. Report each paired delta, block median/range, queue/processing/post-work stages, in-window/cohort/drain throughput, and all cancelled/rejected/failed/late outcomes. Marginal stage percentiles cannot be summed as request accounting. Independent trial blocks, not requests, are the replication unit.

Retain the existing practical margins unchanged: absolute timely delta ≤1 percentage point at both deadlines, failure delta ≤0.1 point, CPU/job ±5%, successful p99 ±10%, for every pair in a contrast. Missing guardrails fail the screen. A pass is a discovery result requiring manual review, not statistical equivalence. Any pass still requires **persistent-recording qualification** before detailed publication-based claims or Step 2. No automatic intervention or controls study. A failed rebuild control weakens attribution to added calls; a large five-inline→V14 difference motivates further worker-path isolation. No post-result relaxation, rerunning valid trials to obtain a pass, or selected-arm promotion.

## Fixed workload and host contract

Retain Go 1.26.1 compiler image `sha256:2389ebfa5b7f43eeafbd6be0c3700cc46690ef842ad962f6c5bd6be49ed82039`, stock runtime, exact retained V12 client binary, GOMAXPROCS=1, four workers, queue128, 44,000 SHA iterations/job, 50 ms quota/100 ms period, zero burst credits, uncapped ancestors and retained server/client affinities. Arrivals: deterministic V12 burst schedule at 113.21/s anchor, 56.605/169.815 low/high, five-second halves, 20 s warmup, 60 s offered arrivals, five-second timeout and full work/client/handler drain. All arms in each block must have identical offered ID/scheduled-offset vectors.

**V15 establishes its own baseline after at least ten minutes of quiet idle and a stable 60-second window.** It does not copy V14's 58.95°C baseline or demand exactly 60°C. The accepted mean becomes this session's frozen baseline. Every trial and resume must meet the unchanged ±3°C tolerance, ≤2°C range, ≤1°C/min absolute slope and existing timeout policy. Resuming never silently rebaselines. If idle state changes materially again, preserve this session and explicitly prepare another; do not relax the gate. AC power, Balanced profile, lid open, quiet-host and monitor acceptance remain required. Hardware thermal equivalence is not proven by these checks.

## Implementation verification and evidence

Build: `analysis/runtime_io_v15_marker_verified_build`, separate from V12/V13/V14. Four new images run original and added Go tests; all four undergo the full race suite, including concurrent reset after handoff and live snapshots. Host race-test copies only redirect inherited `/runtime.trace` output into temporary files; production images keep the original path, and the change/tested hashes are recorded. Twelve unquotaed real HTTP fixtures cover six arms × GOMAXPROCS1/2, six requests each; these establish behavior and clock joins, not performance. Build networking and compiler module downloads are disabled. The first unsealed preparation directory, `analysis/runtime_io_v15_marker_build`, is preserved after a missing Python HTTP import stopped fixture preparation; that runner import was corrected before creating the verified bundle.

Source, prepared variants, binary/image, compiler audit, fixtures, race logs and build bundle are frozen at collection creation. Raw attempt hashes, time-namespace offsets, actual cgroup limits, clock generations/≤1 ms uncertainty, conservation, quiet-host/power/thermal and outcome checks determine technical acceptance. Invalid attempts remain preserved; no automatic retries. Original source drift invalidates resume; completed frozen evidence is verifiable independently of later source edits. Final report and all analysis outputs are sealed. `attempt_audit.json` retains every attempt and rejection reason.

## Launch and operation

Save work, then run from a normal external terminal:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_marker_batch.sh
```

The script closes ChatGPT/Codex, waits for shutdown, starts the detached sleep-inhibited finite 24-trial study and displays five-second progress, current/accepted temperatures, phase, completed/24, remaining, elapsed and log path. Ctrl+C closes the display while the worker continues. At completion, automatic analysis is sealed and the script prints the report. Keep AC power, Balanced profile and lid open; leave the desktop app closed during collection.

Planning estimate: approximately **1.5–3 hours**, depending on cooling. Arithmetic floor is 24×(60 s settling+20 s warmup+60 s arrivals)+600 s initial idle = 66 minutes, excluding startup, drains, extended cooling and analysis. The finite trial count determines completion, not an elapsed-time target. Cooling may stop the run; this is not a guarantee.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/marker_study.py status
python3 diagnostic/marker_study.py watch
```

Rerunning the launcher resumes only valid remaining trials under the same frozen baseline/build. A running study is not duplicated. Results: `results/diagnostic/runtime-io-v15-inline-markers-1/session/analysis/report.md`, `trials.csv`, `requests.csv`, `observer_screen.json`, `validation.json`, `attempt_audit.json`, root `completion.json`. No performance measurement is launched by preparation.

The initial environment and idle samples are hashed in `environment_seal.json` before the first trial. Resume verifies this seal before cooling, and final completion binds its hash. For a graceful stop that preserves trials, use `python3 diagnostic/marker_study.py stop` from the project directory. It checks the recorded launch identity and worker command before sending TERM; it does not treat closing the display as a stop.
