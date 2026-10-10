Current follow-up: [v11 scheduler-choice attribution and paired recorder commands](../docs/runtime_io_v11_decision_probe_commands.md).
The v10 pending-counter probe completed. The v11 offline report attributes work
dispatched during 24 audited HTTP waits; separately built recorder images are
functionally verified for the next quiet eight-trial study. No v11 quota
measurement has been launched. The v9/v10 evidence remains preserved.

Historical follow-up: [v9 overnight stock/patched runtime commands](../docs/runtime_io_v9_commands.md).
The v8 worker-yield study is complete. Retained traces and pinned scheduler
source motivate an isolated pending-preemption fairness candidate; see the
[candidate evidence](../docs/runtime_io_v9_candidate.md). Revision 9 crosses
stock/patched Go with runtime tracing in a balanced 16-trial study. It preserves
the original workload and numeric screens and reports failures and throughput
alongside delays and CPU cost. It cannot qualify a pilot or unlock full
collection. Older commands below are historical.

# Focused timing diagnostic

## Revision 5: boundary and outcome validation

The current diagnostic fixes request ID zero, reports connection context before
handler entry and final flushing after handler exit, and retains every client
outcome. `Go Running` is reported as a runtime state and does not prove continuous
CPU execution. Missing scheduler or request evidence fails validation. See the
[current protocol](../docs/diagnostic_protocol.md) and
[verification](../docs/runtime_io_v5_verification.md).

Build and verify from this project root:

```bash
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

Launch during a quiet measurement window, plugged in on Balanced with the lid
open and other active applications closed:

```bash
bash diagnostic/run_all.sh --directory results/diagnostic/runtime-io-v5
bash diagnostic/run_all.sh status --directory results/diagnostic/runtime-io-v5
```

The six-trial pilot stops after analysis. Each accepted traced attempt includes
`trace_report.md`, `trace_requests.json`, `trace_scheduler.json`, `trace_status.json`
and `runtime.trace`, with source hashes and a completion seal. Failed attempts
retain partial evidence. No performance collection has been run for this revision.

The instructions below document previous revisions; use revision 5 for new work.

## Revision 4: runtime and server I/O pilot

The completed response-write pilot remains frozen under
`results/diagnostic/response-write-v3/pilot`; see
`analysis/response_write_pilot/report.md`. Revision 4 records bounded Go
runtime and underlying TCP I/O events, with request and connection IDs. See
the [protocol](../docs/diagnostic_protocol.md) for boundaries and acceptance.

Build and verify while the laptop is in normal use:

```bash
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

During a quiet measurement window, plugged in on Balanced with the lid open
and other active applications closed, launch only the six-trial pilot:

```bash
bash diagnostic/run_all.sh --directory results/diagnostic/runtime-io-v4
bash diagnostic/run_all.sh status --directory results/diagnostic/runtime-io-v4
```

The launcher is resumable and stops after pilot analysis. Accepted attempts
contain `runtime.trace`, `trace_status.json`, `trace_requests.json`, client and
server JSON, source hashes and a completion seal. Failed attempts retain
partial evidence. `trace_requests.json` contains matched slow and typical
request goroutine states and socket-write evidence. Review the pilot report
and failure counts before selecting any intervention or larger collection.

## Revision 3: next focused pilot

The completed revision-2 audit is [analysis/completed_report.md](analysis/completed_report.md), with [request-level CSV](analysis/completed_request_audit.csv), [recomputed trial summaries](analysis/completed_trials.csv), [source hashes](analysis/completed_source_hashes.json), and [p99 plot](analysis/completed_p99.png). It calculates summaries directly from sealed raw requests. Regenerate it with `MPLCONFIGDIR=/tmp/mpl-response-audit venv/bin/python diagnostic/analysis/completed.py`.

Revision 3 records response Write start/end and a handler exit marker after the final bookkeeping lock. Its six-trial pilot targets 100 ms/four workers and 100 ms/one worker; see [protocol](../docs/diagnostic_protocol.md). Neither the Write return nor the exit marker proves client delivery. The final per-request end-to-end-minus-handler difference is signed and can be negative when client completion overlaps server cleanup. From the project root, build and run checks first:

```bash
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

During a quiet measurement window, with the laptop plugged in, Balanced, lid open and active applications closed, collect **only the pilot** in a new directory:

```bash
bash diagnostic/run_all.sh --directory results/diagnostic/response-write-v3
bash diagnostic/run_all.sh status --directory results/diagnostic/response-write-v3
```

The launcher runs in the background, requests sleep inhibition when available, and preserves logs and status. Re-run the same start command to resume an interrupted pilot. It stops after pilot analysis and writes `PILOT_COMPLETED.md`; it does not automatically start full collection.

The pilot passes only if all six attempts validate, instrumented requests have at least 99% usable client traces, and the three four-worker overhead ratios are each at most 1.10. If it passes, inspect the per-request server and client intervals before choosing whether to add runtime/kernel tracing or collect a larger matrix. Only after that review, `--full` explicitly enables the larger collection. Expected pilot outputs are `pilot/analysis/report.md`, `trials.csv`, `validation.json`, `pilot_gate.json`, and the raw numbered attempts under `pilot/attempts/`. Interpret write errors and negative signed differences as retained outcomes, not automatic technical failures.

## Revision 2 archived instructions

The commands below describe the earlier collection and are retained for provenance. The current source has revision-3 timing and uses a new pilot directory.

The completed follow-up data audit is [analysis/existing_report.md](analysis/existing_report.md), with one row per trial in [analysis/existing_trials.csv](analysis/existing_trials.csv), source hashes in `analysis/existing_source_hashes.json`, and a figure in `analysis/existing_bursty_p99.png`. Recompute these read-only outputs with:

```bash
MPLCONFIGDIR=/tmp/mpl-diagnostic venv/bin/python diagnostic/analysis/existing.py
```

The collection protocol is [../docs/diagnostic_protocol.md](../docs/diagnostic_protocol.md). This code is prepared for a **later quiet measurement window**. It is a separate study under `results/diagnostic/`; existing datasets are never overwritten. The seven-trial pilot screens server CPU cost, client tracing CPU cost, and end-to-end p99 change before the 20-trial batch starts.

## Before the unattended run

Save work and close active applications. Plug in the laptop, set Balanced, keep the lid open, and disable automatic suspend in normal desktop settings if the temporary inhibitor is unavailable. The launcher requests systemd idle/sleep inhibition and reports whether it obtained it. The thermal settling gate requires at least ten minutes at the start and at least one minute before every trial. Initial pilot collection has seven short measurements. Full collection has 20 research measurements. Allow roughly 2–4 hours including cooling and drain; actual time can be longer.

Builds and regression checks can run while the laptop is in use:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

Start the complete batch only in the quiet window:

```bash
bash diagnostic/run_all.sh --directory results/diagnostic/all-in-one
```

After successful background startup, the terminal may close. To check status or resume after a stop, run:

```bash
bash diagnostic/run_all.sh status --directory results/diagnostic/all-in-one
bash diagnostic/run_all.sh --directory results/diagnostic/all-in-one
```

The second command resumes the same frozen pilot/full sessions. A completed workflow writes `results/diagnostic/all-in-one/COMPLETED.md`, including links to `full/analysis/report.md`, `trials.csv`, `estimates.json`, `attempt_audit.csv`, and the pilot gate. Every launch has its own log under `logs/`. Failure files and numbered attempts are retained. A stopped pilot gate or technical acceptance failure requires investigation; do not silently relax the protocol. Changed code requires a new session directory and fresh build. The shared experiment lock prevents overlapping the original or follow-up runners.

After the power-source recording fix, the existing `all-in-one` pilot and full sessions remain frozen to their original source hashes. Preserve them as evidence. Start a new collection with a new directory, for example `results/diagnostic/all-in-one-power-fix`; the launcher will build and collect a fresh pilot and full session. The fix ignores only offline USB power inputs; it still records AC disconnection and an active USB input.

## How to interpret the output

Compare request-level timing records for the same ID. `X-Pre-Admission-Ns` measures handler entry to admission; `X-Post-Work-Wait-Ns` measures SHA completion to handler resume. Client HTTP-trace offsets time connection acquisition, request write, first byte, headers and full body. The remaining duration outside these server stages also includes network and response writing, so a large residual still needs inspection. Cgroup throttling counters are aggregate evidence and cannot explain the delay of a particular request by themselves. A mitigation should be chosen only after the diagnostic analysis identifies a specific stage.
