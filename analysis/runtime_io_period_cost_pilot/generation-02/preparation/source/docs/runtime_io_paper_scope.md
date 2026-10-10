# Paper scope: connect the completed findings to a conditional cost investigation

2026-10-05. Working structure, not a novelty claim or a completed manuscript.

Working title:

**From CPU Quotas to Deadline Misses: Service Capacity, Queueing, and Execution
Order in a Go HTTP Service**

One coherent question links the work: under a fixed average CPU allowance, what
determines timely successful responses, and which measured delays can actually
be improved without losing service capacity?

The causal account to test is resource timing and execution cost → effective
service capacity and execution order → queue history → all-offer deadline success.
Different arrows have different evidential status; do not present the entire
chain as already established.

1. **Completed empirical characterization.** Report the quota/parallelism/burst
   comparisons and their workload/runtime/host scope. Distinguish average allowance
   from an unchanged quota-and-period contract. Count all offers and retain drains,
   rejections, cancellations and observer failures.
2. **Completed delayed-handler intervention.** Reducing execution parallelism left
   consequential post-computation delays in earlier observations. V20's yield
   intervention almost eliminated that measured interval at 100 ms, without a
   demonstrated gain at the chosen 500 ms objective. This is a bounded negative
   intervention result, not an unexplained loose end or proof of equivalence.
3. **Existing queueing explanation.** Reconstruct admission, worker starts, burst
   buildup and recovery. Report separately fitted capacity predictions and their
   errors, retrospective analysis choices, omitted timing effects and rare-tail
   failures. This explains the bulk of losses conditional on observed capacity,
   not capacity from the CPU quota itself.
4. **Conditional efficiency extension.** V20 observed increased aggregate CPU/job
   and lower busy capacity at 20 ms. Add a mechanism section only if measurement
   qualification and a targeted causal experiment distinguish the cause. A
   passing feasibility pilot alone does not fill this section.
5. **Synthesis and limits.** Explain which symptoms were consequential, which
   intervention merely moved waiting, and what an established queue/resource
   account predicts. Bound transfer to other arrival patterns, workloads, hosts,
   kernels and runtimes by actual validation.

The earlier result stands whether the cost pivot succeeds or fails. A shorter
period hurting throughput, or even arrivals helping a queue, is not inherently
novel. A defensible contribution could be a new validated boundary or predictive
account, a causally established interaction, or a useful scoped empirical/negative
result; strength and venue suitability need a separate closest-work comparison.
Time invested is a reason to preserve evidence, not evidence of novelty.

See [V20 findings](runtime_io_v20_findings.md),
[the backlog account](runtime_io_v20_backlog_findings.md),
[the prior-work map](runtime_io_prior_art_review.md), and
[the bounded feasibility pilot](runtime_io_period_cost_pilot.md).
