# Audit of the V20 / CPU-cost pilot reversal

2026-10-06. Offline audit requested after the generation-02 pilot reversed the
earlier shorter-period result. **The cause remains unresolved.** Host conditions
are a candidate, not an established explanation. This audit preserves the
original results and decision rules.

The reproducible reviewer is [review_period_reversal.py](../analysis/review_period_reversal.py).
It verifies original V20 completion, replays all sixteen pilot trials, compares
all 115 shared frozen source files with each other and the loaded implementation,
and independently calculates CPU/job and 500 ms success directly from all 32
trials' raw counters and client records. It also compares actual client commands,
resource limits, resets, drain, warmup outcomes and clock-mapped startup timing.
Results and evidence hashes are in
[report.json](../analysis/runtime_io_period_reversal_review/20261006/report.json).
Both suites passed again: 36 V20 tests and 20 pilot tests. Launchers pass bash
syntax checking. Tests reduce the likelihood of specific implementation errors;
they do not prove that every possible experimental confound has been excluded.

## What the audit establishes

| Candidate discrepancy | Evidence | Status |
|---|---|---|
| Changed service/client/gate build | Frozen hashes and actual packaged-file verification match | No mismatch found |
| Changed inherited collection/analysis code | All 115 shared source hashes match | No mismatch found; the new pilot runner is an addition |
| Changed work or offered load | Actual argv, 44,000 iterations, 20 s warmup, 60 s arrivals, exact schedule and client conservation match | No mismatch found |
| Wrong worker count, yield, quota, affinity or limits | Actual container/health/cgroup records match A/C; one worker, GOMAXPROCS=1, yield off, CPUs 2/4, 0.5 CPU | No mismatch found |
| Warmup left in measured request totals | Reset health is zero and raw measurement records match the declared schedule | No mismatch found |
| Different CPU denominator or deadline arithmetic | Independent raw CPU-delta/completion division and raw client deadline counts agree in all 32 trials | Does not explain reversal |
| Different capacity estimator | Using V20's fixed busy windows in both datasets preserves the reversal | Does not explain reversal |
| Missed client arrivals | Zero in all trials; mean dispatch lag is about 0.55 ms in both sessions | No recorded dispatch-capacity failure |
| Counter attachment or changed CPU measurement window alone | Warmup differences already exist before per-trial attachment; legacy and counter-aligned pilot CPU/job are identical | Cannot be the sole explanation |
| Whole pilot collection context | Persistent helper, fixtures and altered timing exist even with counters off | Remains a candidate |
| Host activity, thermal state or unrecorded execution conditions | Host records differ; active-worker cycles/frequency are absent for V20 | Remains a candidate, without causal attribution |

CPU per completed computation is whole-service CPU, not CPU measured inside the
SHA function. Rejected-request work remains in V20's numerator and does not have
an invented completed computation. Its amount cannot be attributed from these
records alone.

## The pasted command

The new shutdown expression sends the same TERM signal as the old command. It
adds exact process names `Codex` and `codex`, omits the UID selector, and waits
until those names disappear rather than always waiting five seconds. It does
not write the service workload or CPU contract. A normal user's permission to
signal processes still applies. Saved monitors report ChatGPT absent in both
runs. Other process names and shutdown side effects were not comprehensively
recorded, so absence of every possible effect is not proven.

The substantive settings mutation is **`powerprofilesctl set balanced`**. The
installed 0.30 CLI writes `ActiveProfile` through the daemon's D-Bus API. The
saved resulting desktop/platform profile, governor, EPP, minimum/maximum CPU
frequencies and AC state match V20. Thus there is no recorded switch to a
different CPU profile during measurement. The pre-command state, profile-hold
history, daemon actions, GPU/display state and every possible persistent effect
of reapplying a profile were not saved. Do not conclude that this line caused
the reversal or that all its effects have been excluded.

Both runners wait at least ten minutes before collection, so the difference
between a five-second and up-to-thirty-second app-close wait is not a direct
explanation of sustained job efficiency. The full launch/setup context still
differs and merits a faithful original-runner repeat. That repeat checks the
profile without changing it.

## The pilot is not identical to the original runner

Both use the same Service class, warmup, reset, drain, host monitor and roughly
one-second thread/resource observations. Differences include:

- A persistent privileged helper plus four known-work fixtures before initial
  idle. Fixture counters close and fixture cgroups are removed, but this is an
  added setup path.
- `perf stat -n` and a blocked `cat` process in counter-off trials. No hardware
  events are collected there, but these processes and control operations exist.
- A longer reset-to-arrival interval: approximately 14-15 ms in V20 versus
  111-132 ms in the pilot, composed through the saved clock bridges. Counter-off
  pilot values are approximately 111/119 ms at 100/20 ms. This may change quota
  phase or startup timing; its causal effect is not measured.
- V20 includes four full-duration rehearsals and yield-on cells. The pilot
  substitutes counter-on cells and does not run those rehearsals. These create
  different preceding workloads even though each trial settles separately.
- V20 emits progress/temperature updates approximately every ten seconds during
  load. Pilot progress output differs. The pilot additionally saves returned
  resource samples; the shared per-second observation method itself is unchanged.

These differences are not proof that the pilot has a defect. They prevent treating
the old versus new session comparison as a randomized test of host conditions.

## An informative pre-measurement clue

The 20 ms warmup outcomes differ before the per-trial collector attaches:

| Warmup quantity, four-trial average | V20 C | Pilot 20 ms counters off |
|---|---:|---:|
| Offers | 2,265 | 2,265 |
| Completed computations | 2,216.75 | 2,265 |
| Rejections/errors | 48.25 | 0 |
| Startup-to-measurement CPU per warmup computation | 3.849 ms | 3.620 ms |

The last row includes the warmup and intervening control/administrative work;
it is not a separately aligned per-SHA counter measurement. Its direction and
the raw rejection difference show that a main-measurement-only analysis error
or attaching the per-trial collector cannot explain the entire difference.
The helper and overall pilot context already exist during warmup and are not
excluded by this observation.

V20 and the pilot used the same thermal acceptance policy, but that policy
derives a new baseline in each session rather than imposing one temperature
across sessions. Accepted idle baselines were 48.5 C and 57.1 C. Monitored
temperatures and desktop process CPU also differ, as recorded in the
[pilot findings](runtime_io_period_cost_pilot_findings.md). Using the same manual
procedure and passing the same controls therefore does not prove identical
hardware operating state. These differences still do not demonstrate causation.

## Next experiment

Analysis narrows the candidates but cannot assign a cause. The prepared
[faithful V20 repeat](runtime_io_v20_repeat_plan.md) restores the original runner,
four rehearsals, original sixteen-cell order, binary and launch procedure in a
new generation. It uses no perf helper, no hardware counters and no automatic
profile setter. All results, including another reversal, must be retained.

If the repeat restores the V20 penalty, compare its recorded conditions with
both earlier sessions before deciding between harness and host explanations.
If it retains the pilot's direction, the pilot-only collector is not necessary
for that direction; the earlier V20 penalty lacks cross-session repeatability.
Either outcome still requires a controlled intervention before causal attribution.
There is no automatic second run or return to another broad intervention sweep.
