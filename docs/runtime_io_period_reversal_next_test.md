# How to investigate the period reversal

Proposed 2026-10-06; no new benchmark launched and no desktop settings changed.
This is a staged investigation, not a prepared or sealed performance protocol.

## Question and current evidence

Why did the 20 ms period change from more CPU per job and lower capacity in
original V20 to less CPU per job and higher capacity in both later sessions?
The faithful repeat makes pilot-specific collection changes unnecessary for the
new direction. Verified results and limits are in
[repeat findings](runtime_io_v20_repeat_findings.md).

Desktop activity is the strongest currently measured candidate condition,
not an established cause: combined Plasma/KWin CPU changed from about 0.7%
to 19.6-19.8% of one core. Temperature covaries with this change. The same
processes, service binaries, offered schedule, CPU limits and recorded power
settings were present. These are three sessions, not independent randomized
tests of desktop activity. Historical execution-weighted clocks and hardware
work counts are absent; a new experiment cannot recover them retrospectively.

Read-only configuration inspection found a static image wallpaper with forced
animation disabled. The installed custom Skyline pager has no polling timer;
its shell command is triggered on click and its color animation on state changes.
Blur is enabled. These facts do not diagnose or exclude a rendering problem,
and current configuration is not a historical configuration snapshot.

## Stage 1: find a controllable condition without the service workload

Close the research app before measuring. Keep AC, profile, displays and other
applications fixed; record the visible desktop/window state. Use the existing
host sampler for interval process CPU, per-core utilization, temperature and
power settings. Record configuration before any manual, reversible adjustment.

Start with a two-minute stationary baseline. Investigate one desktop component
or visible-state change at a time, allowing a minute to settle and measuring
for two minutes. Restore the original setting and measure again. Limit this
initial search to about twenty minutes; do not kill the compositor, restart
the desktop, reboot or change power profile as part of this first screen.
Those actions alter too many conditions together.

A practical provisional gate for an activity manipulation is combined
Plasma/KWin mean CPU <=2% in the quiet condition and >=10% in the active
condition, reproduced after restoration. These thresholds target a large
portion of the recorded historical separation; they are feasibility criteria,
not a causal or statistical result. Save full samples and note other processes
that change. If the gate fails, do not launch a desktop-activity benchmark.
Inspect rendering/event activity separately or select another measurable
candidate. A profile name or a visually quiet desktop is not an activity measure.

## Stage 2: one bounded comparison if Stage 1 passes

Prepare and seal a separate protocol once the exact intervention is known.
Keep the original image, executable, arrivals, 44,000 SHA iterations, one
worker, GOMAXPROCS=1, CPU placement and 0.5 CPU ceiling fixed. Yield stays off;
hardware counters stay off for this reproduction test. The four cells are:

| Cell | Desktop condition | Quota period / quota |
|---|---|---|
| A | Measured quiet | 100 / 50 ms |
| B | Measured quiet | 20 / 10 ms |
| C | Measured active | 100 / 50 ms |
| D | Measured active | 20 / 10 ms |

Use four blocks with balanced orders ABCD, BADC, CDAB, DCBA. Retain warmup,
arrivals, drain, resource checks and independent raw replay. Verify the actual
desktop activity in every cell, not only before launch. Predeclare settle and
thermal acceptance rules; record temperature, power policy and other activity.
Do not assert a pure CPU-contention mechanism if these also change. Allow about
1-2 hours, with longer duration or an aborted block possible under settle rules;
the final prepared runner must provide its own timing estimate and restore the
desktop condition on failure or completion.

Primary contrast: the paired 20-versus-100 CPU/job ratio in quiet conditions
versus the same ratio in active conditions, assessed within each block. Report
each contrast and the interaction, not only a pooled average. Capacity uses
the same fixed backlogged windows as prior reviews; 500 ms success and queue
waiting are consequential outcomes. Predeclare a practical interaction margin
and uncertainty rule before collection. With four blocks an inconclusive
interval is possible; retain it rather than adding blocks until a sign appears.

Interpretation:

- If the original penalty returns in quiet conditions and reverses in active
  conditions consistently, the controlled desktop intervention affects the
  period contrast. This supports a conditional effect, but does not isolate
  frequency, cache, runtime work or thermal mediation.
- If the contrast changes without reproducing the original penalty, the
  intervention matters but does not fully explain the historical reversal.
- If activity separates but the period contrast does not meaningfully change,
  this particular intervention is insufficient. It does not exclude every
  host-state interaction or establish what happened historically.
- If activity does not separate during benchmark cells, or estimates are too
  uncertain, the experiment does not distinguish the candidate explanation.

## Stage 3: explain a reproducible change, if one is found

The existing perf pilot's counter fixtures passed, but its observer-equivalence
screen failed. Do not use it as a qualified causal observer or silently relax
its margins. First qualify a reduced collector under the reproduced conditions,
or use a separately qualified fixed-work control with explicit scope limits.
An isolated SHA control can test computational efficiency; it cannot by itself
attribute whole-service runtime/network work.

| Competing explanation | Needed evidence |
|---|---|
| More software work per job | Instructions/job plus a work breakdown locating the increase |
| Same work executes less efficiently | Stable instructions/job, but changed cycles/instruction or execution-weighted cycles per CPU second |
| Less CPU is actually delivered while work waits | Busy-window cgroup CPU seconds per wall second, backlog, and scheduling/throttling evidence if attribution is needed |

These causes may coexist. Process-wide instructions include HTTP/runtime work;
instantaneous MHz samples do not establish active-worker execution speed.
Only add a trace or profiler when its overhead and coverage are qualified for
the effect being measured. If qualification fails, retain the causal limit.

## Connection to the earlier research

Queue buildup remains the explanation for many misses given observed service
capacity. A better estimate of why capacity changes would explain the input to
that queue account; it does not replace the existing arrival/queue/yielding
results. Apply the existing capacity-based queue predictor to held-out blocks
of a new study and report its errors rather than fitting all blocks and calling
the result a prediction. Compare the eventual mechanism and scope with closest
primary prior work only after a supported effect is available. No novelty claim
or commitment to a paper pivot follows from this proposed plan.
