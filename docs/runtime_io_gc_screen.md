# Faster GC / CPU-period screen

2026-10-06. Separate eight-trial prioritization screen. The prepared sixteen-trial
GC probe and its sealed sources are preserved. No performance collection is
launched during screen preparation.

Question: does default automatic memory cleanup versus GOGC=off change the
20-versus-100 ms CPU/job contrast? Removing cleanup may save CPU at both periods
without explaining their difference. A changed contrast still does not prove
a Go defect or identify the cause of the earlier V20 session.

## What is shortened and what is retained

Run two opposite-order blocks, ABCD and DCBA, rather than four blocks. A/B are
100 ms with default/off GC; C/D are 20 ms with default/off GC. Each arm appears
once in each block and its order against each other arm reverses. Two blocks do
not balance every cell over all four positions or establish four-block precision.

Retain the original 20 s warmup, full warmup drain/reset, 60 s measured arrivals
(six ten-second low/high cycles), final drain, SHA work, CPU allowance/placement,
worker count, yield off, instrumentation, hardware-counter/profiler absence and
resource/ownership/memory/watchdog checks. Fresh service container per trial.
No reboot, power-profile setter or additional app closures during this software
comparison. Retain the ten-minute initial idle and at least sixty-second stable
thermal window before each trial; silently removing these could change the
condition under investigation. Verify the prepared boot identity before launch.

The retained runtime configuration uses original block labels 1 and 4 for raw
replay compatibility. These blocks execute consecutively as screen orders 1-8;
`screen_execution.json` records actual order. No intermediate blocks are run.
The screen calls the qualified GC collector without changing its frozen source.
Its progress callback is scoped to each serial trial; the service workload and
analysis primitives remain unchanged. Screen source files and protocol are
sealed separately. GC functional controls and software audit are reused through
their verified preparation seal rather than rerun as benchmark evidence.

## Time budget

Nominal floor: 600 s initial idle + 8 x (60 s settling + 20 s warmup + 60 s
arrivals) = 1,720 s, about 29 minutes, plus startup/drain/check overhead. Plan
about 30-40 minutes when temperatures settle promptly. It is not a hard timeout:
thermal settling can add time or stop under the existing policy. The earlier
one-to-two-hour estimate allowed those waits. The service arrivals themselves
account for only eight minutes of this short run.

Shortening measured trials is deferred: it would change the amount of allocated
memory and the number of queue/GC cycles observed. Short trials need separate
duration qualification. The present screen gains speed through fewer blocks,
with an explicit loss of inferential strength.

## Decision rules

Compute the CPU period-ratio interaction separately in both blocks:

    (20 ms CPU/job with GC off / 100 ms CPU/job with GC off)
    ------------------------------------------------------- - 1
    (20 ms CPU/job with default GC / 100 ms CPU/job with default GC)

Flag `consistent_gc_period_signal_in_short_screen` only if both block
interactions have at least 2% magnitude in the same direction. This is a reason
to prioritize follow-up, not confirmation. Otherwise report
`short_screen_inconclusive`; do not label GC absent or the experiment broken.
Two-block t intervals (one degree of freedom) are descriptive and may be very
wide; no equivalence or hypothesis-exclusion decision is made from them.

Report default-GC period cost in both blocks, capacity, delivered busy CPU,
deadline success, queue waits, failures and memory peak. GC-off changes object
lifetime/cache/page behavior as well as collector work. An equal CPU saving at
both periods is not evidence explaining reversal. If the historical default-GC
penalty is absent, the screen cannot identify its historical cause. Retain every
result, interruption and raw record. No automatic rerun or full-study launch.

## External command

Save work before quitting the research app. Run this shorter command instead of
the sixteen-trial launch command; do not run both as an automatic sequence.

```bash
(
  set -e
  cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
  python3 diagnostic/runtime_gc_screen.py verify-preparation
  pkill -TERM -u "$(id -u)" -x '(ChatGPT|Codex|codex)' || true
  sleep 5
  if pgrep -u "$(id -u)" -x '(ChatGPT|Codex|codex)' >/dev/null; then
    echo 'Fully quit the app before launching.'
    exit 1
  fi
  bash diagnostic/start_runtime_gc_screen.sh
)
```

Progress prints `1/8` through `8/8`, followed by a report path. Bring back that
path. A missing/weak signal still provides data for choosing the next step, but
does not justify concluding that automatic cleanup cannot cause the earlier
behavior.
