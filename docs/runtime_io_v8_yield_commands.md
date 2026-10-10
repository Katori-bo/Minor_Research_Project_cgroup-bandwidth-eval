# Runtime/I/O v8: worker yielding and tracing comparison

This is the next mechanistic test after the completed failed v7 pilot. It asks
whether giving ready HTTP goroutines a scheduling opportunity between CPU jobs
reduces the observed cleanup stalls and runtime tracing's rejection penalty.

Four modes, each repeated four times in balanced order:

| Mode | Runtime tracing | Yield after each completed worker job | Custom connection recording |
|---|---|---|---|
| plain | Off | Off | On |
| trace | On | Off | On |
| yield | Off | On | On |
| yield_trace | On | On | On |

The new image is `quota-diagnostic-service:7`, schema 9, pinned Go 1.26.1. The
yield treatment calls `runtime.Gosched()` after completion and reply publication,
before taking the next job. It does not yield inside hashing. Default is off.
Health, metrics and trace status report the requested setting; mismatch fails
validation. Ordinary qualification configurations retain yielding off.

All cells retain four workers, GOMAXPROCS=2, 50,000/100,000 microsecond quota,
queue capacity 128, fixed original calibrated job and burst load, memory trace
storage, base timing, client settings and affinities. Each trial has 10 seconds
warmup and 20 seconds measurement. Failed requests remain in rejection/timeout
denominators. This study produces no passing pilot gate and cannot launch a full
collection.

## Preparation

Preparation builds and seals the image, runs Go and Python tests, and checks real
HTTP fixtures. Those checks do not measure performance under quota. The fixture
directory must be fresh; retained evidence is not overwritten.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/build.sh
python3 -m unittest discover -s diagnostic -p 'test_*.py'
python3 diagnostic/verify_yield_fixtures.py \
  --directory diagnostic/verification/runtime-io-v8-yield \
  --output diagnostic/verification/runtime_io_v8_yield_validation.json
```

These preparation steps have already been performed for the provided launch
command; see `runtime_io_v8_yield_verification.md`. Do not rebuild or edit
sources/protocol after collection starts. The runner verifies the build and
freezes all sources at session creation; unchanged interrupted sessions resume.

## Start from an external terminal

Save work first. The complete block below sends TERM to the processes named
`ChatGPT`; on this host that includes ChatGPT and the Codex desktop application.
It waits up to 30 seconds and refuses collection if they remain. The study
launcher itself never kills applications. Keep the laptop plugged in, on
Balanced, with the lid open, awake and otherwise idle. Keep any prior Baloo
suspension consistent. Keep this foreground terminal open.

```bash
(
  cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency || exit 1

  pkill -TERM -x ChatGPT || true
  for attempt in {1..30}; do
    if ! pgrep -q -x ChatGPT; then
      break
    fi
    sleep 1
  done
  if pgrep -q -x ChatGPT; then
    echo 'ChatGPT/Codex is still running. Fully quit it; the study was not started.' >&2
    exit 1
  fi

  bash diagnostic/run_yield_study.sh new \
    --session results/diagnostic/runtime-io-v8-yield-1
)
```

If you already fully quit the desktop applications, the collection command alone
is sufficient. The session directory above is separate from the v7 workflow;
its attempts will not be overwritten. `new` refuses an existing directory.

Allow roughly 50–75 minutes based on the last six-trial pilot, with extra time
if cooling takes longer. The absolute minimum includes ten minutes initial idle,
at least one minute settling per trial, eight minutes warmup/measurement across
16 trials, plus container setup, draining and analysis. The unchanged thermal
policy can wait considerably longer before failing. Temperature progress prints
the first sample (about 0 seconds), the first sample at/after 60 seconds, and each
later minute during settling, with the run ID and attempt for trial settling.

After the 16 trials, the launcher analyzes rejection, timeout, throughput, CPU
and latency, parses the eight retained runtime traces for exact cleanup-reader
joins, and prints `STUDY COMPLETE` with the report path. It retains the shared
experiment lock through analysis. A completed study is distinct from a passed
performance qualification.

## Progress, interruption and results

From a second external terminal, once session creation has occurred:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 -m json.tool results/diagnostic/runtime-io-v8-yield-1/status.json
```

`status.json` is created after the first trial completes; initial settling prints
in the foreground terminal before then. Collection status may say complete while
the launcher finishes trace analysis. Wait for `STUDY COMPLETE` before reviewing
the final report. Keep desktop applications closed during measurements.

If collection is interrupted, inspect the terminal and its retained failure
evidence, then resume with unchanged source/build after quitting desktop apps:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/run_yield_study.sh resume \
  --session results/diagnostic/runtime-io-v8-yield-1
```

Valid completed attempts are skipped; interrupted/invalid attempts are retained
and receive a new numbered attempt. A stale owned Docker container causes a
refusal with its ID; inspect it before removing it. Do not rebuild on resume.

After completion:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
cat results/diagnostic/runtime-io-v8-yield-1/analysis/report.md
python3 -m json.tool results/diagnostic/runtime-io-v8-yield-1/analysis/validation.json
```

`trials.csv` retains every trial. `contrasts.csv` compares trace penalties with
and without yielding, yield effects with tracing off/on, and their difference
within each balanced block. The eight `*_http_cleanup.json` files retain exact
reader associations and corrected generation-census handling. Helper state for
trace-off cells is unavailable, not zero.

A reduced rejection penalty together with shorter helper waits would support
the scheduling hypothesis. Reduced successful p99 alone is insufficient. Any
throughput or CPU cost of yielding must be evaluated. Four blocks are descriptive
evidence, not a definitive causal verdict or permission to relax pilot gates.
