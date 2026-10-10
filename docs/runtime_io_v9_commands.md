# Overnight stock/patched runtime comparison — 2026-10-02

2026-10-03: the 16 measurements completed, but the original analysis stopped
on decoded scheduler timestamps. A separate
[audited original-time reanalysis](../analysis/runtime_io_v9_investigation_20261003_final/report.md)
now validates all 16 trials. The original failed workflow is retained. Do not
rerun this collection to repair analysis. The
[next focused counter probe](runtime_io_v10_pending_probe_commands.md) is ready.

This is step 3: test the pending-preemption fairness candidate against stock
Go 1.26.1. The patch is a hypothesis under test. Functional checks do not
establish a performance improvement or finish the paper.

The sealed images are already built. The launcher runs 16 trials in four
balanced blocks: stock/patched runtime crossed with runtime tracing off/on.
Worker yielding is OFF and custom recording is ON throughout. The workload,
44,000 hash iterations, 50,000/100,000 µs quota, four workers, GOMAXPROCS=2,
128-entry queue, original burst schedule, 10-second warmup, 20-second
measurement, CPU affinities, memory trace sink and host acceptance rules stay
fixed. No larger collection starts automatically.

## Tonight

Save your work. Use an **external terminal**; the block below closes the
ChatGPT/Codex desktop app, which the measurement protocol requires. Keep the
laptop plugged in, on the same Balanced power profile, with the lid open.
Close other CPU-heavy applications and leave the machine idle.

```bash
(
  cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency || exit 1
  pkill -TERM -x ChatGPT || true
  for attempt in {1..30}; do
    if ! pgrep -q -x ChatGPT; then break; fi
    sleep 1
  done
  if pgrep -q -x ChatGPT; then
    echo 'Fully quit ChatGPT/Codex, then rerun this block.' >&2
    exit 1
  fi
  bash diagnostic/run_fairness_study.sh start
)
```

Wait for **Started in background with sleep inhibition** before closing the
terminal. The detached launcher blocks automatic idle/sleep and saves a unique
log for each launch. Keep the lid open: lid closure can override inhibitors.
There is an initial ten-minute idle interval and at least one minute of
settling before each trial, plus draining, cooling and analysis. Allow roughly
45–90 minutes, longer if thermal settling requires it.

## Tomorrow

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/run_fairness_study.sh status
```

The status prints the current stage, trial count, launch log and completion
report. Results are saved under:

```text
results/diagnostic/runtime-io-v9-fairness-1/COMPLETED.md
results/diagnostic/runtime-io-v9-fairness-1/session/analysis/report.md
results/diagnostic/runtime-io-v9-fairness-1/session/analysis/trials.csv
results/diagnostic/runtime-io-v9-fairness-1/session/analysis/contrasts.csv
results/diagnostic/runtime-io-v9-fairness-1/session/analysis/screens.json
results/diagnostic/runtime-io-v9-fairness-1/session/analysis/validation.json
```

The report compares successful p99 delay, rejection, timeouts, other errors,
throughput, server CPU/job and client CPU/request. It applies the original
numeric screens (ratios ≤1.10, maximum rejection-plus-timeout difference
≤0.001, usable client trace coverage ≥99%) descriptively to four repetitions
per cell. It does not substitute for the existing six-trial qualification
pilot, create a passing gate or authorize full collection. Trace-on scheduler
waits are contextual; tracing-off waits are unavailable rather than zero.

**Completed means the experiment validated; it does not mean the correction
passed.** A performance-screen failure remains in the completed report for
review. A technical/environmental failure stops the workflow and preserves
all numbered attempts and logs without silently changing acceptance rules.

If interrupted, close the desktop app again and rerun the tonight block.
Resume verifies frozen sources, workload, image identities and decoder, skips
valid trials, and preserves failed attempts. A changed build or leftover
owned container causes refusal; inspect the printed reason before continuing.
