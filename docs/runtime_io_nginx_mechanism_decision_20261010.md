# Next research decision: explain calibration transfer before inventing a guard

10 October 2026. Planning and read-only capability review after the two saved-data
reliability screens. No scientific trial, privileged capture or power-setting
change was performed. This does not revise any original protocol or result.

## Decision

**A bounded server power-policy study is technically plausible and could strengthen
the empirical explanation. Its standalone novelty is weak.** Prepare it as a
conditional supporting study, not as a new reliability algorithm or a guaranteed
conference contribution. Keep the existing empirical paper and independent V31
replication as the main path. Do not reopen the closed profiler, FIFO theorem or
quota-period selection routes.

The concrete question is: **Does matching a known server power policy during
calibration and validation materially improve complete-response deadline forecasts
across the tested low offered rates?** The policy is observable before prediction;
the future response labels are not. A positive answer would establish a scoped
calibration condition under an intervention. It would not explain the historical
NGINX excursion by itself, nor create a novel state-conditioned estimator.

The [candidate study contract](runtime_io_nginx_power_policy_candidate_20261010.md)
specifies the two settings, crossed rates, ordinary comparisons, budget and
failure outcomes. It is a design proposal, not a frozen executable collection
bundle. There is no qualified launcher for it yet.

## Evidence that motivates this particular question

The [preserved NGINX diagnosis](../analysis/runtime_io_nginx_prediction_diagnosis/20261010-generation01/report.md)
finds fewer deadline misses at 8/s than 4/s in all six balanced blocks, a mean
within-block difference of -5.222 pp. This observational association is compatible
with an idle/power effect, but also with cadence, client activity and unrecorded
host interference. It is not causal evidence for a power explanation.

The largest excursion was mostly visible after headers: 1.122 ms of the 1.276 ms
extra mean response duration. Identical encoded bytes and response hashes rule
out a changed output size; they do not prove identical executed instructions.
Whole-cohort CPU/offer does not uniquely explain the excursion. Client milestones
cannot distinguish streaming compression, server/client scheduling or delivery.

The [recent-timing screen](runtime_io_recent_timing_observable_assessment_20261010.md)
already tested direct warmup profiling, pooling and discrepancy warnings. Those
ordinary approaches did not resolve NGINX's error. That motivates a controlled
calibration condition, rather than another tuned warmup rule.

## Competing explanations and what the candidate can identify

| Explanation | Discriminating observation | What this study can conclude |
|---|---|---|
| Server power policy affects execution/wakeup and its rate dependence | Randomized crossed policy/rate contrast, verified setting readbacks, unchanged application/resources | A causal effect of the assigned policy under the study conditions; not a pure frequency or C-state mechanism |
| Client allocation, GC or scheduling changes body completion | Client timeline / qualified server-side boundaries, or a separately controlled client | Existing client dispatch/header/body records only localize timing; this candidate cannot isolate client GC |
| Server scheduling or shared-core/package contention | Qualified scheduling/occupancy evidence and a targeted intervention | CPU affinity and zero quota-throttle counters do not establish exclusive CPU service; unresolved here |
| Compression executes different work | Worker-scoped instructions and qualified profiles with controlled work/output | Same response bytes are insufficient; aggregate cgroup CPU is not instruction evidence |
| Network/body-read timing varies | Matched ingress/egress/socket boundaries and observer qualification | Client headers-to-body is not a network-only interval; unresolved here |
| Small timing shifts cross a steep CDF | Frozen calibration CDF evaluated at the unchanged deadline | This arithmetic is already established; it amplifies an effect but does not identify its cause |

Failure to observe a policy effect does not refute all power, idle-state,
scheduling or client explanations. Success under a manipulated setting does not
prove that this setting changed during the original unobserved excursion.

## Closest primary work and the novelty boundary

Sources inspected 10 October 2026; no competing implementation ran.

| Primary source | Inspected capability | Consequence for our claim |
|---|---|---|
| [Li et al., Tales of the Tail, SoCC 2014](https://syslab.cs.washington.edu/papers/latency-socc14.pdf), Sections 3.3.1 and 4.6 | Fine-grained server measurements; low-utilization power/idle effects, including NGINX | Neither low-load latency reversal nor a benefit from power-policy control is a new mechanism claim |
| [ReTail, HPCA 2022](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf), Sections IV, V-D and VII-G | Frequency-conditioned request prediction; feature selection and online error-triggered retraining | State-conditioned CDFs here are deliberately ordinary controls; generic state-aware prediction and drift response have precedent |
| [Waiting at the front door, IMC 2026 accepted version](https://arxiv.org/html/2606.02057v1), Sections 4, 6.3 and 8 | Host-stack latency monitoring; NGINX workloads; observer-effect measurements; ingress-only limitation | Building another broad latency tracer is not justified. The tool does not directly measure the whole streaming server-to-client body interval |
| [Linux AMD pstate documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html), operation modes and EPP | Active mode uses hardware-autonomous control influenced by an energy/performance preference | A preference change is a policy intervention; it is not a verified fixed-frequency experiment |

This focused comparison establishes substantial prior overlap. It does not
establish that no paper studies our exact configuration, or establish a first
result for CPU-quota calibration transfer.

## Current capability findings

The [read-only inventory](../analysis/runtime_io_nginx_mechanism_plan/20261010/capability_inventory.json)
records CPU 2 on `amd-pstate-epp` active mode, `powersave` governor and
`balance_performance` EPP. `performance` is an advertised EPP choice. Its policy
lists CPU 2 alone, but CPUs 2 and 3 are SMT siblings: neither policy scope nor
affinity isolates shared execution units, package power or temperature.

Perf, trace-cmd, bpftrace and bpftool are installed. Their presence does not
qualify scope, permissions or overhead. `perf_event_paranoid=2` and unprivileged
BPF is restricted. Avoid adding these observers to the primary pilot; they are
unnecessary for estimating an assigned-policy effect. Any later mechanism
attribution through counters/tracing needs its own functional and observer gate.
The existing [counter feasibility review](runtime_io_period_cost_feasibility.md)
already records these limitations and an unsuccessful observer precision screen.

The stock NGINX build lives in the preserved research bundle, rather than PATH.
Reusing its exact binary/client is preferable to rebuilding; reuse must be
verified against its source/runtime seals in a separate new generation. The
read-only inventory alone does not establish runtime launch readiness.

## Contribution contract for the paper

| Possible contribution | Supported now? | Evidence needed for a stronger statement |
|---|---|---|
| Prospective comparison of inexpensive calibration representations at specified deadlines/resources | Yes, within original Go/NGINX contracts and their different endpoints | Independent replication strengthens scope; simple response-CDF comparator should be declared prospectively |
| Empirical boundary: fine-deadline response-CDF transfer can work in one tested application and miss its criterion in another | Yes, scoped to these campaigns | More independent forecasting episodes and controlled confounds before generalizing |
| Recent target-rate warmup alone was insufficient in these saved records | Yes, exploratory | A separately frozen prospective comparison before presenting it as confirmed |
| Matching server power policy improves calibration transfer across offered rates | No | Candidate qualified, sealed and run with all ordinary comparisons and every outcome retained |
| A new advance reliability diagnostic | No | A distinct capability beyond ordinary state-conditioned calibration, an observable state-to-future link, fair comparators and independent confirmation |

A successful policy study would strengthen an empirical contribution about
calibration conditions. It would not automatically justify a methods-paper
title. If state-matched ordinary calibration solves the controlled problem,
report that result and stop custom-method development for that problem.

## Worth pursuing and stopping rules

Preparation of a small policy-control fixture and a new-generation dry-run
contract is worth doing if we want the empirical explanation. A full campaign
is conditional on qualification; the proposed ceiling is 28 scientific cohorts,
9,500 total scientific-run offers including warmup, and 45 minutes elapsed.
Qualification is separate and capped. These are feasibility limits, not power
calculations or assurance that the study will resolve the question.

Stop this branch if restoration/scope cannot be made reliable, the two assigned
settings cannot be verified, the original low-overlap/non-throttled domain fails,
or the campaign cannot distinguish a useful forecasting difference. Keep null,
domain-exit and inconclusive results. Do not replace EPP with governor/boost/
C-state/period changes after seeing outcomes, or expand collection until a
desired pattern appears.

The immediate technical deliverable for a later execution turn is a separately
named policy-control and qualification package with restoration journals,
ownership/watchdog handling, source seals and a dry-run schedule. No approval is
being requested for a hypothetical campaign here. Host-setting writes and
privileged launches must use the normal host permission mechanism when an
actual qualified action is ready.
