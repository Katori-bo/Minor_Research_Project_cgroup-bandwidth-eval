# Bounded post-restart boost/period screen: design, not a prepared launcher

**Status update — 2026-10-07:** The user subsequently chose to close the reversal
search and move forward. This boost comparison is shelved and remains unrun.
Use the [V22 prospective queue plan](runtime_io_v22_prospective_queue_plan.md)
for the current direction. The design below is preserved for later reference;
it is not a default post-restart action.

2026-10-07. The user requested a simple boost comparison and asked whether it
should follow the planned restart. Decision: capture post-restart configuration
first, then prepare a same-boot boost-by-period screen. No boost setting was
changed and no performance trial was launched. This document is a concrete
design; executable preparation, control validation and a sealed launcher remain
pending against the new boot. Do not use earlier boot-bound launchers for this.

## Why and what this can answer

Boost permission can affect CPU/job because CPU time is time scheduled, not a
fixed instruction budget. Faster execution can finish fixed work in fewer CPU
milliseconds. Hardware can vary actual execution rate even with boost enabled.
See [Linux 7.2 AMD P-state documentation](https://www.kernel.org/doc/html/v7.2/admin-guide/pm/amd-pstate.html).

Our historical V20/pilot/repeat environment records do not directly preserve the
boost flag. Their frequency bounds match. Recent speed-pilot and continuation
controls explicitly preserve boost=1; no documented off-to-on transition explains
the reversal. The earlier constrained-speed intervention reduced access to high
frequencies and produced a large overall cost change without a consistently large
period interaction. That lowers the priority of another speed hypothesis, but
does not substitute for a dedicated boost toggle.

Primary question: does disabling boost change the **20-versus-100 ms CPU/job
ratio**, rather than merely slowing both arms? This tests a current causal
interaction, not the unobserved historical boost state. A simple before/after
run at only one period cannot answer it. A result with the original penalty
absent cannot establish that boost caused that original penalty.

## Matrix and retained workload

| Cell | Worker-core boost permission | Quota period / quota |
|---|---|---|
| A | Enabled | 100 ms / 50 ms |
| B | Enabled | 20 ms / 10 ms |
| C | Disabled | 20 ms / 10 ms |
| D | Disabled | 100 ms / 50 ms |

Two blocks in order ABCD, then DCBA; eight fresh-container trials in one boot.
Use the retained full V20 service/client/gate image and workload: Go1.26.1,
44,000 SHA iterations/job, one worker, GOMAXPROCS=1, queue128, yield off,
CPUs2/4, average0.5 CPU allowance, quota burst0; 20-second warmup and
60-second burst schedule per trial. Retain original resource limits and
verified measurement/reset/drain semantics. No hardware perf counters, runtime
profile, added per-job telemetry or background-app intervention in this screen.

Control only worker cores and their SMT siblings (logical CPUs2/3/4/5) if
post-restart topology and per-policy control support match. Other CPUs stay at
their starting boost state. This avoids intentionally changing the load
generator/controller speed. It tests worker-core boost, not every global boost
consequence. Same parked fixed-scope helper infrastructure is present in both
conditions; host monitoring remains matched.

Preparation must verify the target boost knob semantics, record all original
flags and frequency bounds, exercise toggle/readback/restoration without a
performance benchmark, and reject unexpected policy scope. Disabling boost may
change the kernel-reported frequency ceiling; that expected consequence must be
recorded and validated rather than silently forced back to an inconsistent
ceiling. Verify governor/EPP/platform profile and external-power settings, quota,
affinity and untouched-policy controls separately. Observed boost=0 does not
guarantee a constant physical frequency.

Use a narrow privileged helper with fixed operations, owner/lifetime checks,
restoration on normal exit/error/owner death and an explicit recovery receipt.
Restore original boost flags and original writable frequency bounds, with
readback; do not assume turning boost back on alone restores every bound. Check
no owned container/cgroup/observer remains. No arbitrary sysfs command channel.

## Thermal acceptance and duration

Use fresh baseline evidence for each boost condition in this new boot, because
the intervention can change idle temperature. Derive and freeze both references
before performance blocks; retain the existing60-second stability window,
2 C range and1 C/min slope requirements, with3 C tolerance to that condition's
reference. Do not relax acceptance or redefine the reference in response to
desired trial outcomes. Record all transition/settling times. Any comparison
includes the boost intervention's frequency/thermal consequences; it is not an
isolated temperature experiment.

Eight warmup/measurement windows total about10 minutes40 seconds. Initial
baseline collection, transitions, settling, drains and validation dominate
elapsed time. Planning allowance approximately40–75 minutes, conditional on
settling; this is not a guaranteed completion time. Freeze a90-minute total
ceiling and retain partial evidence if reached. No automatic extension or
retry-until-positive rule. A shorter one-pair result may inform feasibility but
must not be presented as a replicated reversal explanation.

## Analysis and stopping rule

Replay each trial from raw counters/client/service records. CPU/job is
whole-service CPU divided by completed computations, with rejections retained
separately. Report CPU delivery in certainly-backlogged intervals, capacity,
deadline success, queue waiting and actual recorded controls as supporting
outcomes. Do not equate whole-service CPU/job with CPU inside the SHA function.

For each block compute R_on = CPU/job(20,on)/CPU/job(100,on), R_off similarly,
and interaction I = R_off/R_on - 1. A promising screen requires at least2%
magnitude in the same interaction direction in both opposite-order blocks,
valid raw replay, verified controls/cleanup and a meaningful boost manipulation.
This is a practical screen, not a powered equivalence test. Report both
individual period contrasts and the general on/off cost shift.

- Both periods slow similarly with boost disabled: demonstrates a general
  execution-rate effect, not a useful explanation of the period reversal.
- A consistent substantial interaction: worker-core boost permission affects
  period-dependent cost under this workload/session. Historical attribution
  still requires evidence linking this behavior to the original penalty.
- No sizable consistent interaction: no promising signal in this screen;
  do not extend automatically or claim all boost mechanisms excluded.
- A failed manipulation, control drift, settling failure or incomplete block:
  preserve evidence and report the limitation; do not treat it as a null result.

Do not combine today's pre-restart boost-on measurements with new boost-off
measurements as a causal comparison. Reboot changes several conditions together.
Capture the [post-restart system comparison](runtime_io_restart_snapshot_and_open_questions.md)
before preparing/running the screen. A new current observer audit/review is
needed; the old same-boot inventory is not a post-restart qualification.

## Interpretation boundary

We have investigated several leading avenues, not excluded all possible causes.
The historical reversal remains unresolved. Measurement while the large penalty
actually occurs, precise CPU-supply timing, workload/setup history and the isolated
system-CPU anomaly remain gaps. The proposed boost screen is one bounded,
specific intervention; a negative result is a reason to stop this route and
continue the queue/capacity paper account, not open an unrestricted search.
