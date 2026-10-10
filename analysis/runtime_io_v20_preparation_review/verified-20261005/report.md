# V20 implementation and preparation verification

Verified 2026-10-05. **Generation-03 preparation passed. Quiet-machine qualification and discovery have not started: 0/4 rehearsals and 0/16 trials.** Preparation checks and synthetic software fixtures are not performance findings.

V20 holds one worker and GOMAXPROCS=1, then independently varies the existing post-publication yield control and the CPU quota period. The four cells are yield off/on at 50 ms quota per 100 ms period and yield off/on at 10 ms quota per 20 ms period. All retain the same average 0.5 CPU allowance. Shortening the period changes temporal CPU availability; it is a declared resource factor. The original packaged service, load generator, FIFO start gate and marker meanings are preserved without rebuilding or tracing.

The runner executes four full-duration operational rehearsals, then sixteen discovery trials in four balanced blocks. It checks warmup and measurement dispatch capacity, actual resource settings, environment stability, clocks, raw outcome conservation, watchdogs and owned cleanup. Analysis exports requests, trials, phases, paired contrasts and interaction estimates, reports and PNG/SVG figures. Independent verification replays raw evidence and compares the saved analysis and CSV exports.

## Actual preparation evidence

- All 36 tests passed, including accounting, publication bounds, contrast/guardrail decisions, resource drift, ownership, interruption and tamper rejection.
- All four Docker resource preflights verified the actual executable, yield state, CPU quota/period, historical memory/PID settings and cleanup.
- Normal controls A, B, C and D each retained 114 offers and completed all 114 successfully.
- Cancellation controls A and D each retained 453 offers: 452 timeouts and one rejection. Each recorded 429 completed computations. Missing handler records were retained: 414 in A and 443 in D. Whole-cohort gap means remained unknown rather than substituting zero or selecting only observed completions.
- Every preparation container and cgroup was removed; cleanup receipts reported no errors or watchdog intervention.
- The preparation freezes 115 source files, including all 105 unchanged V19 sources, the exact service image and binary assets. Preparation seal SHA-256: `75067bc80894755049932ed27e236698e3877294141dfe69ce098209bc913a40`.

The sealed preparation is [generation-03/preparation](../analysis/runtime_io_v20_execution_delay/generation-03/preparation/manifest.json). The implemented protocol is [runtime_io_v20_execution_delay.md](runtime_io_v20_execution_delay.md).

## Corrections before measurement

Two failed preparation generations remain preserved. Generation-01 exposed the existing service's strict `WORKER_YIELD=0/1` parser; generation-02 exposed a copied assumption that startup throttling must always be zero. Docker startup can consume more than a 10 ms quota before the gated service begins. V20 retains startup counters but uses separately bracketed counters after warmup/reset for measurement. These corrections preceded quiet qualification or discovery and did not relax performance thresholds. Separate sealed cleanup audits verify absence of all owned objects, including the early startup failure recovered from an exact ownership-nonce Docker creation event.

## Additional software verification

Copied actual functional evidence replayed exactly. Resealed changes to a raw latency, whole-cohort primary result, yield environment or CPU period were rejected. Extra unsealed files and executable modifications were rejected. A copied full-duration V19 trial passed V20's warmup and measurement parser with 6,793 offers; this is parser verification, not new V20 data.

A separately marked synthetic fixture exercised all four qualification cells, sixteen trial cells, analysis, plots and independent completion verification. Deliberately altered and resealed trial CSV content was rejected by raw replay. The fixture reused historical timing data and provides no experimental conclusion. Synthetic plot layouts were visually inspected. V19's original independent completion verifier still passed with `useful_worker_control_without_gap_signal`.

Check receipts and synthetic plot QA are saved in [the sealed preparation review](../analysis/runtime_io_v20_preparation_review/verified-20261005/report.json).

## Next run

Fully quit Codex/ChatGPT, then run from an external terminal as the normal user:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_execution_delay.sh run \
  "$PWD/analysis/runtime_io_v20_execution_delay/generation-03"
```

No sudo is required. Allow roughly 75–100 minutes, with additional time if cooling takes longer. The launcher first requires four successful rehearsals, then runs sixteen trials and automatically analyzes and independently verifies completion. Keep the desktop app closed throughout measurement. Use this generation, not either failed preparation.

```bash
python3 diagnostic/execution_delay_study.py verify-completion \
  --directory "$PWD/analysis/runtime_io_v20_execution_delay/generation-03"
```

V20 can distinguish sensitivity to execution opportunity, temporal CPU supply and their interaction. The measured completion-to-handler interval and conservative publication bounds still do not directly observe runnable time, instantaneous remaining quota or a scheduler defect.
