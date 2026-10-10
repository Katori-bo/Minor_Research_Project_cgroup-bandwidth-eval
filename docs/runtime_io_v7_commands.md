# Runtime/I/O v7: memory trace sink confirmation

## What changed and why

The v6 component study completed 16 valid trials but did not qualify full
collection. Runtime-only rejected 3.97–4.55% versus baseline 0–0.57%. Combined
rejected 4.33–4.55%. Successful p99 decreased while typical latency and server
queue/processing tails increased. Tracing changes the observed workload.

Inspection of all four retained combined traces places the dominant summed
post-handler Waiting-state overlap in Go HTTP cleanup:
`finishRequest -> abortPendingRead -> sync.(*Cond).Wait`. The sums are
37.68/82.38/50.45/57.80 goroutine-seconds, overlapping across requests; they are
not wall time or CPU consumption. Recorder waits are smaller and variable,
including 0.775 summed seconds in block 1. The responsible scheduling mechanism
remains unresolved. Evidence is in the v6 session's
`analysis/combined_b1_wait_stacks.json` through `combined_b4_wait_stacks.json`.

Runtime-only block 1 has 170 trace-file write syscall entries totaling 1.589 ms
of completed syscall state time, maximum 0.087 ms. Evidence:
`diagnostic/verification/runtime_io_v6_writer_review.json`. This does not prove
disk blocking caused the delay. Revision 7 tests whether removing these syscall
transitions helps, while keeping the complete trace.

The new image is `quota-diagnostic-service:6`, schema 8. Runtime capture defaults
to a fixed 64 MiB memory buffer. After capture stops and the writer drains,
the trace is written, synced and closed; the runner includes that persistence
in final cgroup CPU accounting. Overflow, incomplete persistence, trace parse
errors and missing lifecycle evidence fail validation. Abrupt termination can
lose buffered trace data and leaves an incomplete attempt. `TRACE_STORAGE=file`
remains available at service level for a separately planned comparison; the
confirmation pilot freezes memory mode.

This is a candidate intervention, not a proven fix. No user load, queue size,
worker count, quota, Go version or acceptance threshold was relaxed.

## Build and checks

The workflow launcher below rebuilds, seals the build, and runs Go and Python
tests automatically on its first launch. To run preparation separately:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

## Run only the fresh six-trial pilot

Save work and fully quit both ChatGPT and the Codex desktop app before collection.
On this machine Codex runs an executable named `ChatGPT`, so the same quiet-host
check also detects its helper processes. Use an external terminal.
Keep the laptop plugged in, on Balanced, lid open, awake and otherwise idle.
Keep any optional Baloo suspension consistent with the previous measurements.
The launcher does not kill other applications. The foreground command below
prints progress directly; keep its terminal open and prevent automatic sleep.
The background `start` alternative requests sleep inhibition when available.
Its built-in thermal settling includes
an initial ten minutes and at least a minute before each trial, plus the trials,
drain and analysis; allow additional time if temperatures need to settle.

Use this unused directory for the new revision. If it already contains this
revision's interrupted workflow, the same command resumes it with the unchanged
source/build. Do not point it at a v5/v6 session.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/run_all.sh foreground --directory results/diagnostic/runtime-io-v7-memory-1
```

Each settling period prints its temperatures at the first sample (about 0 s),
the first sample at or after 60 s, and every further minute if cooling continues.
Trial lines include run ID and attempt number. The 60-second reading is printed
before a stable period returns. The initial ten-minute idle period prints at
the same cadence. Sampling remains every five seconds; no gate was changed.

If an app is still present, launch prints one short ChatGPT/Codex message and
does not start the workflow. The old `pgrep -a` guard printed all Electron helper
arguments, explaining the long message. To check quietly yourself, use
`pgrep -x ChatGPT` (PIDs only) or `pgrep -q -x ChatGPT` (no output).

To run in the background instead, replace `foreground` with `start`. That mode
retains a separate launch log; the status command prints its path. Temperature
output is in that log and can be followed with `tail -f` on the printed path.
Check progress from a second external terminal while keeping the desktop apps closed:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/run_all.sh status --directory results/diagnostic/runtime-io-v7-memory-1
```

Do not rebuild or edit source/protocol after a session has started. After an
interruption, inspect status/failure and the printed log first; rerun the same
launch command with unchanged source/build to resume. A failed pilot gate is a
completed measurement outcome requiring review, not an interruption to retry
until it passes.

## Read results

Once status reports complete or a pilot-analysis gate failure, inspect:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -m json.tool results/diagnostic/runtime-io-v7-memory-1/pilot/analysis/validation.json
python3 -m json.tool results/diagnostic/runtime-io-v7-memory-1/pilot/analysis/pilot_gate.json
cat results/diagnostic/runtime-io-v7-memory-1/pilot/analysis/report.md
```

If it stops earlier, these files may not exist; use the workflow status and
foreground terminal output or the printed background launch log. A valid run is
distinct from a passed performance gate.
The gate requires all six trials valid, complete tracing, at least 99% usable
client timing, all three overhead ratios at most 1.10 and no rejection/timeout
increase beyond the unchanged 0.1 percentage-point tolerance. A smaller successful
p99 with more rejections still fails.

The workflow stops after the pilot. Review the gate, failures and matched
timelines before choosing any larger collection. A pass does not establish a
causal file-writer explanation; a fail motivates inspecting the runtime scheduler
and HTTP background-read path rather than loosening the workload or thresholds.

## Reproduce retained trace inspection (no workload)

ChatGPT may be open for these read-only analyses. Docker must be accessible:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
for block in 1 2 3 4; do
  python3 diagnostic/inspect_wait_stacks.py \
    "results/diagnostic/runtime-io-v6-components-1/attempts/component_b${block}_combined/001" \
    --output "results/diagnostic/runtime-io-v6-components-1/analysis/combined_b${block}_wait_stacks.json"
done
python3 diagnostic/inspect_trace_writer.py \
  results/diagnostic/runtime-io-v6-components-1/attempts/component_b1_runtime/001 \
  --output diagnostic/verification/runtime_io_v6_writer_review.json
```

New functional verification is recorded in `runtime_io_v7_verification.md`.
