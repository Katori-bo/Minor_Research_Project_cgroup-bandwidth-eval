# Paper scope: connect the completed findings to a conditional cost investigation

**Short empirical note, with a bounded extension — 2026-10-07:** The user
requests a simple draft and modest novelty/generality assessment. V22 now has
verified prospective support. Use the [short draft](runtime_io_short_working_draft.md)
and [targeted scope review](runtime_io_novelty_generality_review.md). The lead
note compares two capacity estimates for all-offer deadline failure under fixed
quota; earlier yielding/stage results motivate the question. V23 is implemented
and prepared to test two work sizes and further burst timescales, with its
research trials unrun. This broadens parameter-range evidence if successful;
it does not introduce a new algorithm or an independent workload. No full paper
or assured novelty/publication claim is intended at this stage.

**V22 implementation/preparation passed — 2026-10-07:** The
[prepared implementation](runtime_io_v22_preparation_verification.md) retains the
frozen question and original binaries. Software/functional checks passed;
fresh observer review, quiet-host qualification, calibration and prospective
validation remain unrun. Preparation is not scientific support for transfer or
novelty. The existing candidate contribution and attribution limits stand.

**Prospective question frozen — 2026-10-07:** The
[V22 revision-1 design](runtime_io_v22_frozen_question.md) fixes calibration,
baselines, validation order and prediction/error decisions. It tests queue-account
transfer with yielding off, not the yielding interaction or a new scheduler.
Implementation/preparation now passed as recorded above; performance validation
remains pending. The candidate empirical contribution and closest-work limits below stand.

**Closest-work comparison — 2026-10-07:** Use the
[contribution matrix](runtime_io_contribution_matrix.md) for the assessed scope.
The lead candidate is a quantified empirical diagnostic case study of the
conditional translation from stage improvement to all-offer deadline outcomes,
with a proposed prospective test of the queue account. Yielding limitations and
capacity/queue modelling have close precedents. No novel scheduler/model,
identified Go defect or general transfer boundary is established. Yield-off V22
alone would validate only the queue component, not a yielding interaction.

**Evidence consolidation — 2026-10-07:** Use the
[claims register](runtime_io_evidence_map.md) for current permitted wording.
The strong yielding stage response recurs, while its 500 ms benefit varies by
session: original V20 had no demonstrated gain; the faithful repeat had a modest
100 ms gain. Prospective capacity transfer and novelty remain unestablished.
The closest-work/contribution matrix is now linked above.

**Current scope update — 2026-10-07:** The period-cost cause search is closed as
unresolved, with all evidence retained. The next proposed study is the
[V22 prospective capacity/queue validation](runtime_io_v22_prospective_queue_plan.md).
Use that document for the post-restart steps and candidate contribution. The
earlier structure below remains useful, but a conditional cost mechanism section
has not been established and is not a prerequisite for reporting the other work.

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
