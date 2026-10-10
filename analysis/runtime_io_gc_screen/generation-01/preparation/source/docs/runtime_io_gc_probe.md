# Same-binary software/runtime diagnostic

2026-10-06. This is a targeted software hypothesis test, not a claimed bug fix.
No original V20 or pilot source, sealed protocol, image or result is modified.

The service allocates per-request objects and grows event slices. Its reset
clears those slices but does not recreate the process or explicitly collect
garbage. Automatic GC is therefore a plausible source of CPU work whose timing
can interact with quota replenishment and scheduling. Identical code does not
exclude this effect. There is no measured GC breakdown for historical V20.

Change exactly one software policy: GOGC=100 versus GOGC=off, at each of the
100/50 and 20/10 ms period/quota pairs. Go documents GOGC and the default memory
limit in [runtime documentation](https://pkg.go.dev/runtime@go1.26.1).
Use the retained Go 1.26.1 service executable without rebuilding, one worker,
GOMAXPROCS=1, yield off, unchanged instrumentation, CPU placement and arrivals.
No hardware counters, profiler or GC log is enabled in performance trials.
This choice tests allocation/automatic-GC policy, not every Go scheduling or
language-implementation hypothesis. Do not interpret a negative result as
proof that Go is uninvolved.

## Audit before running

`runtime_software_audit.py` compares the complete saved environment in all
48 original/pilot/repeat trials, checks retained source hashes, then adds
independent Python SHA reference vectors and concurrent request/snapshot/drained
reset checks to an isolated source copy. It runs vet and the race detector
with the retained Go 1.26.1 toolchain, offline. The race build is a correctness
check and is never a performance arm. [Go's race-detector documentation](https://go.dev/doc/articles/race_detector)
explains that it detects exercised races; passing does not prove no bug exists.

## Capped performance protocol

Four balanced blocks, sixteen fresh-container trials:

| Arm | Period/quota | Automatic collection |
|---|---|---|
| A | 100/50 ms | Default, GOGC=100 |
| B | 100/50 ms | Disabled, GOGC=off |
| C | 20/10 ms | Default, GOGC=100 |
| D | 20/10 ms | Disabled, GOGC=off |

Orders ABCD, BADC, CDAB, DCBA. Each trial retains the original 20 s warmup,
drain/reset, 60 s arrivals, full final drain, resource/identity checks and host
sampler. Collection waits for the existing ten-minute initial idle and per-trial
thermal settling. No automatic power-profile setter. Expect about 1-2 hours;
failed settling can take longer or stop collection. No automatic repeats,
resumption of interrupted blocks or favorable-result selection.

Preparation uses four short, two-second functional controls. GC logging and
128 additional metrics reads are enabled only there to demonstrate that the
actual executable collects with GOGC=100 and does not with GOGC=off. Those
fixtures have no performance interpretation and finish before initial idle.

The inherited service startup is adapted only by adding literal environment
entries inside a scoped single-threaded startup adapter. The complete inspected
environment is checked, including absence of an unexpected GOMEMLIMIT/GODEBUG.
Ownership, binary hashes, CPU limits, watchdog and cleanup stay enforced.
Off arms retain objects longer: a 768 MiB sampled per-service memory guard stops
the run and preserves failure evidence. Original unlimited cgroup memory settings
remain; the guard is not a performance tuning limit. The active watchdog remains
360 seconds and only owned containers are removed. This guard is sampled, not
an instantaneous hard memory ceiling.

## Prediction and interpretation

Primary outcome is an interaction, not the average saving from disabling GC:

    (CPU/job at 20 off / CPU/job at 100 off)
    ------------------------------------------------ - 1
    (CPU/job at 20 default / CPU/job at 100 default)

Compute within each block, with log-ratio aggregation and an exploratory t
interval across four blocks. A signal requires at least 2% absolute interaction
and an interval excluding zero. An interval entirely inside +/-2% supports no
large interaction under these tested conditions; otherwise it is inconclusive.
Report all block values, not only a decision label. Separately report whether
default GC reproduces the original positive CPU/job penalty (>=2%, interval
above zero). Do not equate failing this reproduction gate with a broken run.

Supporting outcomes: certainly-backlogged capacity and actual CPU delivered per
wall second, 500 ms success, queue waiting, failures and memory peak. CPU/job
remains whole-service CPU and includes rejected-request and administrative work.
The busy estimator retains clock bounds and requires six seconds of certainly
backlogged coverage. Failure to meet coverage makes that result unqualified;
the run stops and retains evidence rather than silently selecting another window.

If GC off changes the period contrast, allocation/GC policy contributes in this
session. It also changes object lifetime, cache and page behavior, so the result
alone does not locate CPU in GC or prove a collector defect. If GC off reduces
both periods equally, that is ordinary GC cost, not an explanation of reversal.
If the original default-GC penalty is absent, the historical cause remains
unresolved even if an interaction is detected. Persistent host state, runtime
scheduling and execution efficiency remain competing or interacting causes.
Hardware observers still need qualification before mechanistic attribution.

## External launch after preparation

Run from a normal-user external terminal. Save work before quitting the research
app. The following closes only your user's exact ChatGPT/Codex/codex processes;
it does not restart the desktop or modify power policy. No further background
apps are closed for this test, so its software contrast is interpretable.

```bash
(
  set -e
  cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
  python3 diagnostic/runtime_gc_probe.py verify-preparation
  pkill -TERM -u "$(id -u)" -x '(ChatGPT|Codex|codex)' || true
  for attempt in {1..30}; do
    if ! pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
      break
    fi
    sleep 1
  done
  if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
    echo 'Fully quit the app before launching.'
    exit 1
  fi
  bash diagnostic/start_runtime_gc_probe.sh
)
```

This test is independent of the proposed desktop-activity comparison. Keep the
desktop condition unchanged within this run and examine saved host activity for
drift. Do not change GC and desktop activity together in the same first test.
