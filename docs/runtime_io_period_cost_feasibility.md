# Feasibility gate for investigating quota-period CPU cost

2026-10-05. Proposed investigation, not a frozen collection protocol. This note
records read-only capability checks and the decisions needed before committing
to a mechanism study. No new service performance trial, privileged capture,
power-setting change or package installation was performed for this review.

## The question and the current limit

At the same nominal 0.5 CPU allowance, V20's 20 ms period increased aggregate
cgroup CPU per completed computation and reduced busy-phase completion capacity.
The aggregate CPU numerator includes HTTP/runtime/recording and rejected-request
work. It is not a measurement of CPU consumed inside the SHA calculation.
See [the existing cost audit](runtime_io_v20_backlog_findings.md#audit-of-the-cpu-increase).

We need to separate three possibilities, allowing combinations:

| Possibility | First discriminating measurements | Remaining ambiguity |
|---|---|---|
| More software work per completed computation | User instructions per job, followed by a sampled function profile | Aggregate instruction changes can reflect HTTP/rejection/cohort differences, not necessarily extra SHA or scheduler work. |
| The same work takes more CPU time while running | User CPU/job, cycles/instruction and execution-weighted clock evidence | More cycles/instruction suggests execution stalls or changed work mix; lower clock suggests frequency effects. Counters alone do not prove either cause. |
| Less CPU time is delivered per wall second while work is waiting | Aligned cgroup usage deltas, backlog/completion records; qualified scheduler/quota observation if needed | A CPU cap is a ceiling, not a delivery guarantee. Low consumption without backlog is not evidence of insufficient CPU delivery. |

Extra off-CPU waiting alone does not explain increased CPU time per job. It can
explain part of the capacity loss. All three effects can coexist.

## Capability checks completed

- `/usr/bin/perf`, `/usr/bin/trace-cmd`, `/usr/bin/bpftrace` and
  `/usr/bin/bpftool` are installed.
- `perf list` lists instructions, cycles, task-clock, context switches, CPU
  migrations and MSR APERF/MPERF events. Listing is not proof that an event can
  be opened or counted correctly in the required container/cgroup scope.
- Installed `perf stat` supports cgroup filtering, CPU selection, machine-readable
  output and enable/disable control with acknowledgements. These permit a
  collector outside the service with measurement boundaries aligned to the load.
- `perf_event_paranoid=2` and `unprivileged_bpf_disabled=2`. Plan privileged
  cgroup-wide/kernel capture through the existing external-terminal workflow;
  do not change system security settings simply to avoid that workflow.
- CPU4 reports `amd-pstate-epp`, `powersave`, `balance_performance`. No verified
  fixed operating frequency is available from these checks. APERF/MPERF counts
  are CPU-wide and must not be attributed to the worker without accounting for
  other activity and execution placement.
- V20's retained source does not import `runtime/pprof` or expose a pprof endpoint.
  Prefer external `perf` on the exact executable first. Adding Go profiling
  requires a separately qualified build comparison, given historical rebuild
  differences.

The [V18 observer review](../analysis/runtime_io_v18_observer_cost_review/generation-04-1791136754967461238/review.md)
did not pass the practical deadline screen: five of six pairs exceeded the
500 ms success margin. CPU changes were small and timing changes had both signs;
the pilot did not distinguish tracing cost from ordinary paired variability.
That observer is not automatically qualified for a new cost study.

## A bounded route to a decision

1. **Validate counters on known fixtures.** Confirm actual cgroup-scoped counting,
   all service threads/CPUs, correct measurement windows and permission handling.
   Check that an equal-work fixture gives stable instruction counts and a sleeping
   fixture adds wall time rather than comparable CPU time/instructions. Reject
   unsupported, missing or heavily multiplexed counts. Run these as functional
   checks, not evidence about V20's mechanism.
2. **Prepare one capped quiet-host pilot.** A candidate ceiling is four balanced
   blocks of 100/20 ms period × counters off/on: sixteen service trials total.
   Keep the exact executable, workload, affinity, workers, GOMAXPROCS and average
   allowance fixed. Preserve every outcome and rejected offer. Initially collect
   only a small aggregate counter set; defer sampling/tracing. This count is a
   planning ceiling, not a powered design or permission to rerun until passing.
3. **Assess repeatability and observer effects before attribution.** Counter-off
   trials must reproduce a useful period contrast. Counter-on/off differences
   and block uncertainty must be appreciably smaller than the roughly 5–6% CPU
   effect. A proposed planning target is about 1% CPU/job and busy throughput;
   retain deadline/latency/failure guardrails too. Freeze actual margins and the
   analysis before collection. Four blocks may be insufficient to reach the
   target: failure to establish precision is an inconclusive feasibility result.
4. **Locate the measurable difference.** Separate whole-cohort cost from aligned
   backlogged-window CPU delivery and capacity. Count completed server work,
   rejected offers and unfinished boundary work consistently. If instruction
   cost rises, qualify a separate low-rate `perf record` profile to distinguish
   SHA from HTTP, runtime, GC and recording. Compare absolute sampled cost, not
   just profile percentages. If necessary, use one no-rejection workload control
   or a separate fixed-work calculation fixture; neither substitutes for the
   original service evidence. A goroutine can move between OS threads, so a
   thread CPU clock around its calculation is not automatically per-job CPU.
5. **Require a causal and literature distinction.** Choose one intervention from
   the measurements, state different predictions for the remaining explanations,
   and verify that the intervention actually changed its target. Changing a power
   governor does not establish fixed frequency. Require the explanation to
   predict a separate workload/block and compare it with the closest established
   account before claiming a contribution.

For aligned busy windows, use the accounting relation
`completion rate ≈ delivered CPU per wall second / CPU per completed job` only
with consistent scope and bounded unfinished-work effects. Do not substitute
whole-trial average CPU/job for saturated service cost; V20 already showed that
this substitution fails.

**Proceed** if valid, sufficiently precise measurements expose a reproducible
difference and a feasible intervention can distinguish its cause. **Narrow or
stop** if counters cannot be scoped, observer effects/variation obscure the
effect, work composition cannot be separated, or a known explanation accounts
for the result without a demonstrated additional insight. Do not automatically
expand the pilot or launch V21.

## Closest primary references

- [Linux perf tutorial](https://perfwiki.github.io/main/tutorial/): hardware event
  semantics, counting, sampling, access restrictions and multiplexing.
- [Go diagnostics](https://go.dev/doc/diagnostics): Linux perf support and the need
  to assess profiling overhead separately.
- [Linux CFS bandwidth documentation](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html):
  the quota contract and aggregate throttle accounting.
- [AMD pstate documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html):
  autonomous hardware performance control under EPP.
- [Ugedal and Kumar, SBAC-PAD 2022](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf):
  runtime-accounting-related unnecessary throttling, shorter-period performance
  losses and bandwidth-control overhead. Applicability to our current kernel and
  user-CPU increase remains to be established.
