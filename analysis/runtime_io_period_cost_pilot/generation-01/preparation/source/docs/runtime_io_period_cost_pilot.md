# CPU-period cost feasibility pilot

2026-10-05. Executable preparation protocol for a new, separate pilot. V20 and
earlier sealed evidence remain historical. No V21, scheduler remedy or broader
period sweep is authorized by a passing feasibility result.

## Purpose

Determine whether aggregate measurement can reproduce and distinguish the
shorter-period CPU-cost/capacity difference without materially perturbing the
original service. This is a gate before a causal study, not that study itself.

The [paper scope](runtime_io_paper_scope.md) preserves the delayed-handler and
queueing findings whether or not this pilot supports further investigation.

## Resource and workload contract

Use the exact packaged V20 original executable and retained load generator;
no Go rebuild, pprof endpoint, worker CPU clock or runtime trace is added.
One worker, GOMAXPROCS=1, 44,000 SHA iterations, queue 128, CPUs2/4, client and
collector on CPUs0/1. The 60-second workload has 6,793 offers with alternating
five-second low/high rates 56.605/169.815 per second, following 20 seconds of
warmup and full drain/reset. Retain rejected offers and computation after client
cancellation. Preserve historical memory/PID defaults and unconstrained CPU
ancestors; verify actual CPU settings and zero configured burst allowance.

| Cell | Quota / period | Counters |
|---|---|---|
| 100_off | 50 / 100 ms | Null perf collector |
| 100_on | 50 / 100 ms | User cycles and retired instructions |
| 20_off | 10 / 20 ms | Null perf collector |
| 20_on | 10 / 20 ms | User cycles and retired instructions |

Both off/on arms have the same external control/helper processes. Off uses
`perf stat -n`; on uses a grouped `cycles:u,instructions:u` event set, restricted
to the actual service cgroup and CPUs2/4. Do not collect other PMU events in this
pilot. Output retains counts per CPU and event runtime/coverage. Start disabled;
acknowledged enable/disable operations bracket the entire measured cohort/drain.
User and system CPU-stat reads on both sides of each acknowledgement bound
alignment uncertainty. Root access is restricted operationally to a bounded
helper whose IPC accepts operations, never caller-specified commands or paths.
No sudoers, perf permissions, governors or root tracing controls are changed.

## Order and bounds

Four independent exploratory blocks, sixteen trials total:

1. 100_off, 100_on, 20_off, 20_on
2. 100_on, 100_off, 20_on, 20_off
3. 20_off, 20_on, 100_off, 100_on
4. 20_on, 20_off, 100_on, 100_off

Each cell occupies each within-block position once. Off/on ordering reverses;
each cell pair precedes the other in two blocks. Requests and burst cycles are
not independent replicates. Preserve trial-level results and block contrasts.

Before any service trial, four privileged functional fixtures execute equal
fixed work on both CPUs: three computation repeats and the same computation
plus one second of sleep. They use dedicated owned uncapped cgroups and a
barrier. Each CPU must show positive instructions, all counter coverage must
be at least 99.5%, instruction max/min spread across the four cases at most
1%, and sleep must add at least 0.75 seconds beyond the additional running CPU
time. A failed fixture stops collection; it does not trigger a service run.

Use the existing ten-minute initial idle and per-trial thermal/power settling
criteria. The helper has a three-hour ceiling, a 300-second active-capture
timeout and a bounded idle timeout. Normal service ownership has its retained
360-second watchdog. Interruptions stop the pilot and retain evidence. There
is no resume or automatic rerun command; review the failed attempt before
preparing any additional collection. Passing results do not expand the pilot.

The minimum service arithmetic is 16 × (60 settling + 20 warmup + 60 arrivals)
= 37 minutes 20 seconds, plus ten-minute initial idle, fixtures, startup, drain,
cooling and analysis. Allow roughly 1–2 hours provisionally; actual timing is
not calibrated. Long cooling can hit the three-hour bound and stop the pilot.

## Frozen decision rules

Technical evidence must pass raw client/server replay, clock brackets, binary
hashes, actual cgroup/CPU contract, thread snapshots, host monitor, collector
exit/status, counters on both CPUs and verified owned cleanup. Counter CPU-window
uncertainty must be at most 0.5%. No unsupported/missing counts are imputed.
At least six seconds of certainly backlogged sampled intervals must exist in
each trial. CPU samples retain host monotonic brackets and are joined to server
events using six clock anchors. Their completion counts retain boundary bounds.

Compute matched block log-ratios and exploratory Student-t intervals with df=3.
Four blocks are not guaranteed to demonstrate adequate precision.

- **Effect reproduced:** counters-off short-period CPU/job increases by at least
  2% on the geometric-mean contrast, its interval excludes zero, and short-period
  busy-capacity interval indicates a decrease.
- **Observer screen:** for each period, the entire estimated interval must fit
  within ±1% CPU/job and busy capacity, ±1 percentage point timely success at
  500/1,000 ms, ±0.1 point failure, and ±10% successful-response p99.
- **Counter separation:** relative-change interval halfwidths must be at most
  2 percentage points for instructions/job, cycles/instruction, effective
  cycles/user-CPU-second and CPU delivered per second in backlogged windows.
  A detectable aggregate signal has magnitude at least 2% and excludes zero.

Report one of:

| Decision | Meaning and next action |
|---|---|
| effect_not_reproduced | Stop the proposed mechanism study on this evidence; examine repeatability/context. |
| observer_or_precision_inconclusive | This pilot has not qualified observation. Do not attribute its differences or automatically repeat it. |
| aggregate_measurements_inconclusive | Instrumentation passed, but the aggregate contrasts did not distinguish a useful change. Narrow the question before another experiment. |
| measurement_feasible_targeted_control_needed | Measurements support designing one causal control. Work composition and novelty still require separate evidence. |

If counters or cleanup fail before completion, preserve the technical failure
and do not produce a causal/feasibility success decision from partial blocks.

## Interpretation limits

Instruction increases may reflect rejected-request, HTTP, recording or runtime
work. They are not automatically extra calculation work. Cycle/instruction
changes can reflect stalls or changed instruction mix. Cycles/user-CPU-second
is an aggregate effective clock proxy, not instantaneous worker frequency.
Backlogged CPU consumption is delivered time, not a guarantee of entitlement;
quota settings supply a ceiling. Effects can coexist. Pure off-CPU waiting
does not by itself explain increased running CPU time per completed job.

The accounting decomposition uses aligned cohort counters; whole-trial CPU/job
is not substituted for busy-phase service cost. A Go goroutine can migrate
between OS threads, so a thread clock around a calculation is not adopted here.

Even a passing pilot establishes neither an exclusive cause nor novelty.
Depending on its signal, a later separately qualified profile, no-rejection
control, execution-frequency intervention or resource-delivery measurement may
be needed. Verify a control actually changes its intended factor. Compare any
result against [Ugedal and Kumar, 2022](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf)
and the prior quota/queueing work before claiming a new contribution.

## Launch and inspect

Preparation is performed now as the normal user. Kernel fixtures and performance
collection must be launched externally with Codex/ChatGPT fully quit, on AC power
with the existing Balanced profile. Keep the external terminal open; Ctrl+C
requests cleanup. Authenticate sudo only in that terminal.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_period_cost.sh
```

The default prepared directory is
`analysis/runtime_io_period_cost_pilot/generation-01`.
The launcher verifies preparation and quiet-host status before requesting sudo.
It inhibits sleep and keeps the Python orchestrator and client under the normal
user. A persistent sudo helper prevents credential expiry during cooling.

Status, offline replay and reports:

```bash
python3 diagnostic/period_cost.py status
python3 diagnostic/period_cost.py analyze
```

Reports are saved in that generation's `analysis/<timestamp>/report.md`,
`report.json` and `trials.csv`; `latest_analysis.json` points to the newest sealed
report. Raw files, preparation, counter fixtures and each trial have hashes.
Offline analysis replays original records and rejects a changed saved derivation.

Primary tool references: [perf documentation](https://perfwiki.github.io/main/tutorial/),
[perf-stat source manual](https://raw.githubusercontent.com/torvalds/linux/master/tools/perf/Documentation/perf-stat.txt),
[Go diagnostics](https://go.dev/doc/diagnostics), and
[Linux bandwidth contract](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html).
