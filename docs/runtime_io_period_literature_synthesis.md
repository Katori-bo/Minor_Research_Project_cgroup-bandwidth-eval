# Interpreting the quota-period reversal against prior work

Reviewed 2026-10-06. This is a literature and saved-evidence review. No new
performance run, preparation, source change or host-setting intervention was made.

## Judgment

The later result matches the simple latency-smoothing expectation more closely.
The original result has a published throughput-loss precedent. Neither comparison
identifies our CPU/job mechanism, and neither licenses discarding a verified run.
Use the later result as the working baseline for the currently observed conditions;
retain original V20 as a verified, not subsequently reproduced period-cost penalty
whose cause is unresolved. Do not assert that the penalty is universal or faulty.

The relevant distinction is original V20 generation-03 versus later sessions,
not simply V20 versus V21: the faithful V20 generation-04 repeat also produced
the later direction under the restored original runner.

## What the closest sources establish

| Primary source | Relevant finding | Boundary for this investigation |
|---|---|---|
| [Linux bandwidth-control documentation](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html) | Smaller periods offer more consistent latency while limiting burst capacity. Quota controls CPU time. | Equal quota/period ratios do not promise equal completed work or CPU/job. The bandwidth allocation slice is a separate parameter from the quota period. |
| [Ugedal and Kumar, SBAC-PAD 2022](https://rakeshk.folk.ntnu.no/pubs/SBACPAD22.pdf) | Shorter periods lost performance in CPU-bound tests through bandwidth-accounting effects; the paper also studies allocation-lock overhead. | Its throttling evaluation used Linux 5.12, fixed-frequency Intel cores and exclusive CPUs. Our fractional-quota Go service on an AMD laptop differs materially. Wall-time loss does not explain our user-CPU increment by itself. |
| [Go's container-aware GOMAXPROCS explanation](https://go.dev/blog/container-aware-gomaxprocs) | Quota is a CPU-time ceiling; runtime activity can trigger throttling. Explicit GOMAXPROCS overrides container-aware defaults. | Our fixed GOMAXPROCS=1 prevents the default CPU-count change from explaining the reversal. Runtime scheduling and cleanup can still consume CPU. |
| [Shetty et al., SoCC 2025](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf) | CPU limits can create request queues and harm tail latency, including through microbursts. | This supports the queue account, not a universal ordering between 100 and 20 ms or a diagnosis of our reversal. |
| [AMD pstate documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html) | Active EPP mode supplies a preference; hardware adjusts execution frequency using workload and operating conditions. | Matching policy names does not establish matching active-worker performance. This is a mechanism candidate, not evidence that frequency caused our result. |

[Jeffery, Jensen and Mortier's 2024 thread-management study](https://arxiv.org/html/2407.11582v1)
is also relevant to quota and neighbouring load, but its automatic Go CPU-count
problem differs from our explicit single-P configuration. Its uniform-arrival
study sets application queue latency aside; it does not resolve our burst queue
or CPU-period reversal. Historical statements that Go ignores cgroups should
not be applied unchanged to our Go 1.26.1 configuration.

## What our records establish

Yield off; pilot counters off. CPU/job measures the entire service per completed
computation, not just SHA work. Capacity below uses the same fixed 18-second
busy-window estimator for the first three sessions.

| Session | CPU/job, 100 / 20 ms | Busy capacity, 100 / 20 ms | 500 ms success, 100 / 20 ms |
|---|---:|---:|---:|
| Original V20 | 3.630 / 3.833 ms | 151.04 / 138.67 jobs/s | 82.14 / 54.86% |
| Cost pilot | 3.643 / 3.591 ms | 148.10 / 151.19 jobs/s | 73.43 / 83.58% |
| Faithful V20 repeat | 3.644 / 3.596 ms | 148.03 / 151.04 jobs/s | 73.10 / 82.29% |

The GC screen also gives the later direction under both default cleanup and
cleanup disabled. Its two blocks do not give a large consistent CPU interaction.
These later sessions share a boot and similar recorded operating activity; they
are repeated observations, not independent hardware/boot generalization.

The original penalty and later improvements each persist across their blocks.
Independent raw replay, matching retained executables, workload and recorded
resource contracts, and the original-runner repeat weigh against a simple
analysis error or pilot-helper-only cause. Software tests found no defect in
the exercised paths. These checks cannot prove that every possible bug is absent.

About 99% of original V20's CPU/job increment is user CPU. Merely waiting off
CPU cannot itself consume this extra user CPU. A pure kernel-lock-overhead story
therefore leaves a major observation unexplained. Extra service/runtime work,
slower execution of the same instructions, or workload-cohort/measurement effects
remain alternatives. Original V20 includes rejected-offer overhead, so the
whole-service numerator must not be described as a direct per-SHA measurement.

The burst rate is 169.815 jobs/s. A constant-capacity approximation over five
seconds gives about 94 queued jobs at 151 jobs/s and 156 at 139 jobs/s, before
finite-buffer effects. The queue has 128 slots. This illustrates how a modest
capacity loss can cross a buffer/deadline boundary and create a large latency
change. It is not an exact replay or an explanation of capacity itself. The
original held-out queue model remains the stronger quantitative queue evidence.

## Ranked explanations and discriminating evidence

| Candidate | Current assessment | Evidence needed to distinguish it |
|---|---|---|
| Quota timing interacts with execution state: active frequency, cache/SMT effects or runtime scheduling | Leading class of hypotheses; exact mechanism unknown. Same binaries and settings can run differently in different measured operating states. | In a session reproducing the penalty: qualified instructions, cycles, active-worker performance and CPU delivery, with controlled workload and observer overhead. |
| Extra runtime/software work under frequent pauses | Possible; user-CPU evidence fits. GC screen lowers the priority of a large automatic-cleanup effect in current conditions. | A reproducible CPU/job penalty accompanied by additional instructions and a runtime/work breakdown. Disabling GC without the penalty cannot exclude its historical role. |
| Reduced delivered CPU from scheduling/accounting | Published precedent, but incomplete explanation for extra user CPU/job. Later busy windows receive approximately 0.5 CPU. | Time-aligned delivered CPU and runnable/throttle intervals during the actual penalty. Later counters cannot diagnose the earlier session retrospectively. |
| Different executable, arrival schedule, pilot measurement window or helper | Known versions of these explanations are weakened by identity/replay checks and the original-runner repeat. | A specific violated invariant or reproducible defect, rather than disagreement with expected behavior. |
| Heat alone or elapsed uptime alone | Unsupported as a causal account. Later sessions are hotter yet improve at 20 ms; all compared sessions share a boot. | A controlled intervention and a measured mechanism. A reboot changes many variables simultaneously. |

Desktop processes were present throughout, but combined Plasma/KWin activity
was about 0.7% of one core originally and about 19-20% later. Presence is not
constant activity. This is a session-level association, not proof that desktop
activity caused the reversal. Original frequency snapshots do not show a simple
lower-MHz explanation for 20 ms; they are not execution-weighted measurements.

## Decision for the research direction

Literature agreement is a plausibility check, not a validity test. Discard or
correct original V20 only if a concrete defect explains it. Otherwise retain
both outcomes and bound the claims to the observed sessions.

We can move forward with the verified queue and stage-specific yielding findings
while recording the cost penalty as not reproduced. A causal period-cost paper
still requires reproducing the penalty under conditions that permit measurement
of competing causes. Do not automatically run the full GC study or spend an
unbounded sequence of runs trying to recover one historical state.

If this mechanism remains central, the next protocol should first define and
verify one operating-state intervention and qualify measurement overhead. Its
question is whether the period contrast changes under that intervention. No such
protocol is prepared here. A fresh boot alone can test sensitivity to a reset,
but cannot name the responsible state. Mere direction-of-effect agreement with
prior work is not novelty; a demonstrated mechanism or predictive boundary would
be needed for that contribution.

Saved evidence: [original backlog findings](runtime_io_v20_backlog_findings.md),
[pilot review](runtime_io_period_cost_pilot_findings.md),
[faithful repeat review](runtime_io_v20_repeat_findings.md),
[GC screen review](runtime_io_gc_screen_findings.md), and
[software audit](runtime_io_software_audit_findings.md).
