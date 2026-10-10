# Runtime/I/O v6 component experiments

Historical revision. The 16-trial component session is complete. Current build
and pilot commands are in [runtime_io_v7_commands.md](runtime_io_v7_commands.md).
Use the current analyzer for read-only v6 analysis, but do not resume a v6 session
with revision 7 source/build.

Implemented 2026-10-02. The v5 rejection problem is not yet proven fixed. This
revision isolates its cause before any performance optimization or full matrix.
The service image is `quota-diagnostic-service:5`, schema 7. Both v5 sessions
remain unchanged. Never reuse their directories with this revision.

## What runs

16 trials: four balanced repetitions each of baseline, runtime-only,
custom-recording-only and combined. Every trial retains base server/client timing
and uses four workers, GOMAXPROCS=2, 50 ms CPU quota per 100 ms, queue capacity 128,
the original 113.21 RPS burst pattern, 44,000 iterations, 10 s warmup and 20 s
measurement. Thermal settling and analysis add time beyond those durations.

Baseline disables the additional runtime/I/O diagnostic. Runtime-only records
scheduler events without custom request/I/O records or a tracked TCP wrapper.
Custom-only enables the v5 wrapper and request/I/O instrumentation without runtime
capture. Combined enables both. The wrapper and annotation call sites are part
of the custom component; this is not yet a separate test of each custom subpart.

Combined mode retains full lifecycle validation. Runtime-only cannot associate
scheduler states to individual requests or guarantee capture through the final
HTTP flush; custom-only cannot report scheduler states. These limitations are
intentional and appear in the report. Component results cannot unlock full runs.

## Prepare

The image was built and sealed during implementation. If code has changed since
then, rebuild **before starting a new session**:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py' -v
```

Use an external terminal. Exit ChatGPT fully before collection. This command
must print nothing (exit code 1 means no matching process):

```bash
pgrep -a -x ChatGPT
```

Keep the machine awake, plugged in, and otherwise idle. If you choose to suspend
Baloo, do so consistently across the entire study and record it. No script kills
background processes or changes your indexing preferences. Per-core utilization
and per-process interval CPU deltas are retained in every `monitor.json`.

## Collect the component study

Use a fresh directory. This runs in the foreground and then validates/analyzes
all 16 trials. Keep the terminal open and the computer awake.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/run_components.sh new --session results/diagnostic/runtime-io-v6-components-1
```

Alternatively, if `systemd-inhibit` is available and permitted on your desktop,
wrap that same command to inhibit idle sleep for its duration:

```bash
systemd-inhibit --what=idle:sleep --mode=block --why="CPU quota component study" \
  bash diagnostic/run_components.sh new --session results/diagnostic/runtime-io-v6-components-1
```

Choose one launch command, not both. ChatGPT presence causes preflight refusal;
if it reappears in monitor samples, the attempt fails validation. Sampling cannot
prove that no very short-lived process ran between observations.

After an interruption, inspect the saved failure/status first and resume with
unchanged code/build. Valid attempts are retained; new attempts get new numbers.
An orphaned experiment container is reported and must be inspected before removal.

```bash
python3 -m json.tool results/diagnostic/runtime-io-v6-components-1/status.json
bash diagnostic/run_components.sh resume --session results/diagnostic/runtime-io-v6-components-1
```

Analysis-only (no workload; ChatGPT may be open):

```bash
bash diagnostic/run_components.sh analyze --session results/diagnostic/runtime-io-v6-components-1
```

Read `analysis/report.md`, `trials.csv`, `contrasts.csv`, `validation.json` and
`attempt_audit.csv` inside the new session. Contrasts subtract the same block's
baseline. Error fraction includes timeouts; it is not added again to timeout
fraction. Successful-request p99 must be considered alongside all failure rates.
CPU per completed work retains the existing accounting window, including drain
and trace stopping. Four repeats are descriptive evidence, not proof of causality.

## Inspect a combined trace's HTTP cleanup waits

The saved v5 quiet trial's post-handler waits were traced to
`net/http.(*response).finishRequest → net/http.(*connReader).abortPendingRead →
sync.(*Cond).Wait`. This identifies the waiting HTTP cleanup path, not why the
background read was slow to finish. It does not establish a custom recorder lock
bottleneck. Reproducible evidence is in
`diagnostic/verification/runtime_io_v5_wait_stacks.json`.

For a new combined attempt, write the report outside the sealed attempt:

```bash
python3 diagnostic/inspect_wait_stacks.py \
  results/diagnostic/runtime-io-v6-components-1/attempts/component_b1_combined/001 \
  --output results/diagnostic/runtime-io-v6-components-1/analysis/combined_b1_wait_stacks.json
```

## After reviewing the component results

Choose a correction supported by the component differences and stack evidence.
Do not enlarge the queue, change load/workers, or relax thresholds to obtain a
pass. If only the combined mode fails, investigate the interaction; if custom or
runtime alone fails, investigate that component first. Overlapping results or
host contention may require further controlled comparisons.

After a correction, document a new revision, rebuild, exit ChatGPT and run a new
six-trial pilot directory. The existing thresholds remain unchanged. For example,
choose an unused directory appropriate to that revision:

```bash
bash diagnostic/run_all.sh foreground --directory results/diagnostic/runtime-io-v6-confirmation-1
```

Do not run this confirmation pilot yet merely to repeat the existing failure.
No `--full` command is part of this component experiment.
