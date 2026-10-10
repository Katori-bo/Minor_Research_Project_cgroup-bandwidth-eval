# Fourth novelty screen: request CPU, shared CPU and CPU delivery

8 October 2026. Authorized bounded offline screen. No new collection.

**Verdict: stop custom-method development and collection for this candidate.**
The accounting discrepancy remains a useful empirical observation, but this
screen did not identify a new way to diagnose its cause or choose a remedy with
less information than established attribution methods. This is a research
allocation decision, not proof that no future contribution is possible.

## Precise decision problem

For the retained single-worker Go service under a fixed fractional CPU quota,
distinguish three possible contributors to a slowdown: more CPU consumed by
request work, more shared/runtime CPU, and less CPU execution while work is
runnable. Return an actionable diagnosis or insufficient evidence. A useful
method would need to distinguish cases requiring different changes, with a
declared error/cost advantage over ordinary profiling and scheduler accounting.
Component attribution alone does not establish that changing that component
will improve deadlines; that requires a causal argument or intervention.

Define ownership first. Request-triggered GC or HTTP processing could be charged
to a request or classified separately. The categories must be disjoint and use
the same convention across alternatives. Fixed SHA iteration counts establish
fixed configured computation, not fixed CPU nanoseconds, cycles or frequency.

## Comparison with existing capabilities

| Method | Required observations and assumptions | Output | Relevance and limitation |
|---|---|---|---|
| Linux cgroup counters | Aligned usage/user/system deltas, quota configuration, relevant hierarchy and runnable-state evidence | Consumed CPU and bandwidth-throttling accounting | Already separates aggregate CPU consumption from wall time. Does not identify which request or runtime component consumed it. Usage below the ceiling alone does not identify unavailable supply. |
| Ordinary CPU profiling with request/class labels | CPU samples, stacks and correctly applied ownership labels; enough samples and coverage | Statistical CPU shares by stack/label | Directly addresses useful-work versus runtime/shared-work attribution. Existing worker pools must apply labels while processing work; label inheritance at goroutine creation is insufficient by itself. Short-request and rare-event estimates need suitable precision checks. |
| Go runtime metrics | Supported metrics from the particular runtime, aligned captures | Estimated GC, scavenging and user CPU classes; runtime scheduling diagnostics | Useful category signals, but CPU-class estimates are explicitly not directly comparable to system CPU counters. Subtracting them from cgroup usage as exact residual CPU is unjustified. |
| CockroachDB fine-grained attribution RFC | Modified Go runtime, scoped counters, propagation across cooperating goroutines/RPCs and selected code paths | Request/tenant/range running-state accounting | Shows that scoped attribution is established engineering work. Its running-state clock explicitly includes OS descheduling; it is not exact on-CPU time under quota stalls. RFC/prototype evidence does not establish accuracy or overhead for our service. |
| Coarse resource-demand estimation | CPU utilization and class throughputs; informative variation and specified background/model assumptions | Estimated mean CPU demand per request class | Established regression/noise-handling methods already target low-overhead inference. Generic fitting, confidence intervals and refusing an unidentifiable fit are insufficient novelty. |
| Scheduling-aware demand inference | Response times and thread-pool/queue measurements; cleaned external waits and a specified scheduling/resource model | Mean class demands/service rates | Perez et al. model multithreaded processor sharing. Fixed periodic quota and unobserved runtime work require an explicit mapping; their full algorithm was not reproduced or refuted here. |
| Scheduler tracing and contention attribution | Runnable/run transitions, cgroup identity, throttling and scheduler state | Time executing, waiting and potentially competing cgroups | Already addresses delivery-side diagnosis. SchedBlame is close recent work, but its attribution-accuracy and detection-quality evaluations are planned rather than completed. It does not identify request CPU within our Go service. |

Primary sources: [Linux cgroup v2 CPU interface](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu),
[Go profile labels](https://pkg.go.dev/runtime/pprof),
[Go runtime metric semantics](https://pkg.go.dev/runtime/metrics),
[CockroachDB RFC](https://github.com/cockroachdb/cockroach/blob/master/docs/RFCS/20220602_fine_grained_cpu_attribution.md),
[Pacifici et al., dynamic CPU-demand estimation](https://research.ibm.com/publications/dynamic-estimation-of-cpu-demand-of-web-traffic),
[Spinner et al., estimation survey](https://doi.org/10.1016/j.peva.2015.07.005),
[Perez et al., §§3–7](https://juanfperez.com/data/2015_02_des_TSE.pdf), and
[SchedBlame v1, §§3–9](https://arxiv.org/html/2609.02052v1).
The survey's author-hosted abstract verifies the established estimation scope;
its full PDF was not retrieved. The IBM abstract supports regression and noise
handling, not a complete algorithm audit. Current Go/Linux documentation may
describe interfaces absent from the recorded versions; this comparison does
not assume that every listed metric existed in our captures. No published
estimator or profiler was executed on the service in this screen.

## What the saved evidence can distinguish

The [numerical audit](../analysis/runtime_io_cpu_attribution_novelty_screen/20261008/evidence_audit.json)
recomputes envelopes and conditional accounting summaries from the retained
reports. These are bounds over clock/counter uncertainty, except the separately
labeled model-based block intervals. No historical decision was changed.

| Evidence | Supported constraint | Explanation still unresolved |
|---|---|---|
| V25: eight sampler-on busy trials have consumed-CPU bounds within an overall 0.493278–0.506713 CPU envelope at configured 0.5 CPU | A large sustained average consumption shortfall is not present in those qualified busy windows | Fine-scale supply timing, per-request attribution and time outside those windows are not determined |
| V25 conditional phase accounting: system CPU accounts for at most 25.50% of the low/busy cost difference for small jobs and 14.55% for large jobs | The system-CPU component alone cannot explain that reference difference | User CPU includes both application and runtime work. These were lower-arrival phases, with zero qualified low states |
| V25: all CPU before first offer and after final arrival is at most 26.11%/28.18% of small/large whole-run reference excess | Those outer edges alone cannot explain the conditional reference excess | In-window boundaries, shared work and attribution remain unresolved; the reference uses busy aggregate CPU/completion, not isolated SHA CPU |
| V27: sixteen accepted trials, all required states qualified; whole CPU/completion rises about 3.194% off and 3.419% on while busy-capacity stability passes | Changing composition changes the aggregate accounting ratio in these conditions | Both 95% lower limits remain below the frozen 3% minimum; the original decision remains composition_inconclusive. This does not isolate a CPU-cost mechanism |
| V27: eight sampler-on busy trials give an overall 0.493328–0.506793 CPU envelope | Again, no large average busy consumption deficit | Cost/capacity observer qualification does not establish deadline observer neutrality |
| V28: zero-request CPU rate 0.000261 CPU; idle correction changes inferred capacity 139.669→139.743 jobs/s and deadline MAE 13.494→13.471 percentage points | The declared constant additive idle correction does not repair the prediction gap | Idle CPU does not bound background/runtime activity induced by load |
| Retained state-detail review | Processing elapsed times and coarse frequency samples do not identify CPU demand | No per-job CPU, instructions/cycles, executed frequency or runtime-activity attribution is available in this evidence set |

See [V25 findings](runtime_io_v25_findings.md),
[conditional V25 leads](../analysis/runtime_io_v25_contribution_leads/20261007/report.md),
[V27 verified findings](runtime_io_v27r3_findings.md),
[V28 findings](runtime_io_v28_findings.md) and
[state-detail limitations](../analysis/runtime_io_capacity_state_details/20261007/report.json).
An application backlog alone does not prove that its worker remained OS-runnable.
Cgroup consumed CPU divided by wall time is not a guaranteed supply rate.
Linux bandwidth limits constrain consumption in time and do not compensate for
execution frequency. [Linux CPU controller](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu).

## Simplest offline checks and adequate alternatives

These [exact arithmetic checks](../analysis/runtime_io_cpu_attribution_novelty_screen/20261008/offline_checks.json)
are declared conditional examples, not measured executions or a theorem about
indistinguishable full Linux traces.

1. **Aggregate counters cannot assign ownership.** In a closed ten-second window
   with 1,000 completions and four CPU seconds, one allocation has four ms/request
   and no shared CPU; another has three ms/request and one shared CPU second.
   Both can have exactly 3.8 user and 0.2 system CPU seconds. Correct request/stack
   attribution distinguishes them. The existing aggregate totals do not.
2. **Ordinary additive inference works under its assumptions.** For
   `U = c*N + h*T`, ten-second captures with 100 and 1,000 completions consuming
   1.3 and 4.0 CPU seconds recover `c = 3 ms` and `h = 0.1 CPU` by two-equation
   arithmetic. No new estimator is needed for this declared model.
3. **More loads and an idle capture need not separate load-induced work.**
   `c = 3 ms`, shared CPU `0.01*T + 0.001*N`, and `c = 4 ms`, shared CPU
   `0.01*T` give equal totals at 0, 100, 500 and 1,000 completions. Idle correction
   identifies the constant term, not ownership of the proportional term. This
   ordinary confounding example does not refute richer published inference.
4. **Consumption and elapsed-time controls prevent misleading diagnoses.**
   Under continuous runnable CPU-only work, 0.5 CPU/5 ms and 0.4 CPU/4 ms both
   yield 100 jobs/s; aligned consumed CPU separates their total execution rates.
   Outside those assumptions, lower consumption can also mean blocked or absent
   work. Likewise 4 ms executing plus 6 ms off CPU and 10 ms executing both
   occupy 10 ms elapsed time; wall timers cannot serve as CPU attribution.

The ordinary measurement reference combines aligned total CPU with adequate
request/stack attribution and runnable/throttling evidence where delivery is in
question. Its sampling precision, coverage and overhead need validation; this
screen did not claim that it is free or universally exact. Go CPU-class totals
cannot simply be used as exact components of this accounting, and the RFC's
running-state clock needs an OS-descheduling correction before such use.
[Metric limitations](https://pkg.go.dev/runtime/metrics),
[RFC clock semantics](https://github.com/cockroachdb/cockroach/blob/master/docs/RFCS/20220602_fine_grained_cpu_attribution.md).

## Novelty gate and missing data

No concrete cheaper attribution mechanism, validated diagnosis rule or improved
remedy ranking emerged. Missing component labels are a data limitation, not an
additional capability. Combining existing counters, profiler labels and ordinary
regression would require another nonroutine idea to support method novelty.
An insufficient-evidence answer is appropriate here but is not itself new.

If the goal later becomes explaining the empirical paper, useful measurements
would be aligned request/stack CPU attribution, runtime activity, and worker
runnable/run/quota state in comparable low and busy windows. Attribution needs
observer checks, an ownership convention, and closed-cohort/boundary accounting.
Instructions/cycles and execution-associated frequency matter only if that
specific mechanism is under test. A remedy claim also needs a controlled change
with predicted and measured consequences. This is a future evidence requirement,
not authorization to start collection or a novelty claim.

Reopen this candidate only for a specified mechanism that predicts a distinction
adequate alternatives cannot make at the same measurement budget, with declared
accuracy, coverage and overhead targets. Otherwise retain the unexplained
accounting effect as a limitation of the focused empirical paper. The three
preceding novelty screens remain closed, quota-period selection stays on hold,
and FIFO theorem work stays closed. Do not start a fifth campaign by default.

## Reproduction and preservation

The [screen design](../analysis/runtime_io_cpu_attribution_novelty_screen/20261008/design/plan.json)
was saved before the arithmetic execution; source reading and historical result
inspection preceded it. This was a retrospective screen, not a preregistered
scientific test. The assessment script audits saved report fields and executes
only the declared accounting checks. A separate verifier checks the arithmetic,
saved decisions, input hashes and design seal.

All 1,911 protected scientific paths and 233 additional preserved paths retain
their hashes, including the current paper, supporting material and prior gate.
Earlier status-pointer contents are copied into provenance; only new status
prefaces were added. The previously recorded extra cache in an older screen was
left untouched, and no old artifact was resealed. The
[verification receipt](../analysis/runtime_io_cpu_attribution_novelty_screen/20261008/verification.json)
records the result. No workload, kernel, profiler or system setting was changed.
