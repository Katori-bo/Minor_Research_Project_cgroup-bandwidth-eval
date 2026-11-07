# Worker runnable-wait alongside CPU demand: concrete candidate

10 October 2026. User-selected candidate. Measurement design and offline tests
only; hardware qualification and discovery collection have not run. No claim of
useful prediction, causal identification or method novelty.

## Correction to the earlier feasibility inference

The earlier [capability note](runtime_io_worker_wait_feasibility_20261010.md)
inferred that sched_schedstats=0 made worker counters unavailable. That inference
was incorrect. Its raw readback was accurate; its conclusion confused additional
scheduler statistics with the per-task information exported by procfs. Preserve
the earlier sealed note as history; this correction supersedes its gate.

Kernel proc_pid_schedstat exports task CPU runtime, sched_info.run_delay and
sched_info.pcount. sched_info_on checks CONFIG_SCHED_INFO separately from the
sched_schedstats switch. The distinction is present in checked v6.12 and current
upstream definitions; upstream is not an exact source match for the running kernel.
[Procfs exporter](https://raw.githubusercontent.com/torvalds/linux/master/fs/proc/base.c),
[per-task availability](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/sched/stat.h),
[v6.12 definition](https://raw.githubusercontent.com/torvalds/linux/v6.12/include/linux/sched/stat.h).

A read-only current-session check found CONFIG_SCHED_INFO=y, CONFIG_SCHEDSTATS=y
and sched_schedstats=0. The audit process's schedstat tuple was 21021510 3287 2:
nonzero runtime/wait accounting with the switch unchanged. This demonstrates
accessibility, not NGINX interval accuracy, historical state, sampling overhead
or predictive usefulness. [Saved check](../analysis/runtime_io_worker_wait_candidate/20261010/capability.json).
No switch change is selected for this candidate.

## Exact observable and decision boundary

Keep stock single-worker NGINX, CPU2, Q25 ms/P100 ms, P0, fixed workload and
D=20.565395 ms. Identify the worker as the unique single-thread child of the
guarded master using host PID/TID, saved start ticks, parent, executable digest
and CPU affinity. Never choose by lowest/highest PID. Replacement, disappearance,
topology change or unreadable counters makes the feature unavailable.

Read /proc/WORKER/task/WORKER/schedstat immediately before launching the existing
25-offer warmup client and immediately after it completes, **before** the
health/status request that verifies drain. Check identity before and after
each read; record monotonic read start/end brackets. Use identical boundaries
for fresh calibration warmups and future probes. Client launch, drain, decoding
completion and polling remain part of this window. This is not per-request
attribution. Qualification must check carryover and unintended worker requests.

Let C and R be increments in the first and second counters, with n scheduled
offers including unsuccessful offers. The observable is x=(C/n,R/n), in ns per
offered request: worker CPU duration and runnable-wait duration. The third field
is retained as scheduling-count context. R is not all off-CPU time or server
queueing time; C is not instruction count.
[Definitions](https://docs.kernel.org/scheduler/sched-stats.html#proc-pid-schedstat).

Reference x_ref pools corresponding fresh **calibration warmup** increments
weighted by offered count. Do not compare this worker interval with an old
400-offer cgroup interval containing different control requests. Acquire the
ordinary response-CDF calibration separately. The signed features are
(delta_C,delta_R)=x_probe-x_ref.

Hypothesis: increased delta_R with similar delta_C could expose changed scheduling
conditions missed by aggregate CPU agreement and response-only summaries.
Increased delta_C with stable delta_R shows a different execution-side pattern,
without identifying frequency, cache or any physical cause. Small changes in both
do not assure future accuracy: new contention may begin after the decision.
Counters can omit pending intervals at a read boundary; their scope and quota
interaction must be qualified. Do not infer R by subtracting cgroup CPU time
from client response time, or treat C+R as an exact client-time decomposition.

The first qualification uses the **whole 25-offer window**, with two counter
snapshots. The current client emits JSON only at run end; a precise 12/13-offer
counter split lacks qualified online synchronization. Additional midpoint reads
need their own timing and overhead contract. A restart or two-client split must
not silently replace continuous warmup.

Decision time is after acquisition, integrity checks, drain and feature/forecast
sealing, before target offers. Every future outcome/counter increment is a label,
never an advance feature. No scalar score, CPU-similarity cutoff or guard has
been fitted or selected from the known historical outcomes.

## Fair comparator and potential contribution

All methods share fresh calibration, the same 25-offer probe, decision time,
counters and acquisition budget. Include:

1. Unchanged ordinary response CDF, recent CDF and sample-weighted update.
2. Ordinary response-only discrepancy/uncertainty checks.
3. CPU-only conditioning as an ablation.
4. Ordinary state-conditioned prediction/risk estimation with both C/n and R/n.

The fourth comparator must receive the proposed signal's inputs. Adding counters,
ordinary fitting or abstention is not a new method. The first potential
contribution is an empirical demonstration that worker scheduling information
improves advance transfer assessment at a measured cost. Stronger novelty needs
a distinct capability and a focused prior-work check.

Target the all-offer miss fraction in the following unchanged 300-offer window.
Report forecast error, accepted errors >5 pp, overall/transition-region coverage
and acquisition/observer cost. Keep failures as misses, throttling observations,
unavailable features and technical exits; no favorable replacement. Finite target
fractions are noisy labels, not population risk. The prior >=50% coverage and
<=5 pp accepted-error screen is a development criterion, not a risk guarantee.

## Qualification before discovery

The immediate external step would be **measurement qualification**, with its
execution package implemented and sealed before use. Required gates:

1. Guarded worker identity, readable counters and actual interval behavior under
   the workload with unchanged settings; cumulative self counters are insufficient.
2. Pre/post ordering, exclusion of health requests, drain, counter update behavior
   and boundary carryover; snapshots are not assumed atomic or fully flushed.
3. Randomized paired observer-on/off qualification with identical workload, rate,
   policy and existing guards. Count identity/read/timestamp/serialization costs
   and scheduling perturbation. Freeze the acceptable overhead margin, sample/time
   budget and exit handling before collection. Nonsignificance is not equivalence.
4. Existing quiet-desktop external-terminal, ownership, watchdog, source-seal,
   lifetime-budget and cleanup requirements. No perf/BPF observer or scheduler
   switch change is bundled into this candidate.

Qualification sample count and overhead allowance are not frozen here; the
apparatus is not runnable or qualified yet. If these gates fail, close the
measurement route without interpreting absent/zero counters as reliable state.
If they pass, declare a bounded **discovery** study before collecting. A useful
relation would then need untouched independent confirmation histories.

Split at campaign/boot/session boundaries, not offers or shared-reference cohorts.
Retain both stable and adverse cases; introduced contention/interventions must be
declared as different populations. Do not tune rates, deadlines or windows until
an attractive relation appears. The friend's pending V31 remains separate.

## Software status

[Offline feature module](../analysis/worker_wait_features.py) parses fields,
selects the worker, checks identity/order, computes increments/references/drift
and preserves strict all-offer deadline accounting. It contains no procfs reader,
collector, launcher, fitted predictor or guard cutoff. Accounting qualification
is an explicit required input, not inferred from sched_schedstats.

Nine synthetic tests cover framing/units, worker selection, matched baselines,
PID reuse/read races, unqualified/inactive data, reversal/order, weighted references,
separate CPU/wait drift and failure/deadline handling. Software checks do not
establish hardware semantics or observer cost. Historical evidence and the open
manuscript remain unchanged.

```bash
python3 -B -m unittest discover -s analysis -p test_worker_wait_features.py -v
```
