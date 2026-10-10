# Next research decision after closing the admission-only lead

**User decision — 8 October 2026:** Put the quota-period selection candidate
on hold. The proposed comparison, prototype and fresh experiments are not
active next steps. Collection remains stopped. Preserve the existing paper
and completed evidence; assess the current empirical contribution on its own
merits. The bounded plan below is retained as a proposal for possible later
reconsideration, not an active work instruction.

8 October 2026. This is a proposed direction and a bounded offline assessment,
not a novelty claim or a frozen experimental protocol. Collection stays
stopped. Existing drafts, solver packages and scientific outcomes are unchanged.

## Recommendation

Preserve the empirical draft as the record of completed work. Close the
admission-only theorem as the current lead for a stronger contribution, per
the [reviewer verdict](runtime_io_fifo_reviewer_verdict_20261008.md).

For the user's stronger-paper objective, the next candidate to screen is a
concrete systems decision tied to the original problem:

> For a declared burst schedule and deadline target, can we choose a CPU
> quota period that improves deadline outcomes while keeping the configured
> average CPU allowance fixed?

For example, 50 ms quota / 100 ms period and 10 ms quota / 20 ms period both
configure 0.5 CPU. Equal configured allowance does not imply equal delivered
CPU, overhead, isolation or deadline outcomes. The study would need to account
for these differences rather than treating the ratio as sufficient fairness.
Periods above or below these examples are not recommendations to change the
running system. No configuration changes are made here.

This is a candidate problem, **not a claim that deadline-aware period selection
is new**. Broad quota-period control and deadline-aware resource management
already exist. We have not established a remaining substantial contribution.

## Why this candidate rather than more work on the closed theorem

The current paper already concerns Linux CPU quotas and bursty requests. A
quota-period decision connects directly to that setting. The rejected theorem
instead treats a constant-rate idealization, with no demonstrated new
advantage or validated link to quota timing.

We should first assess this systems question on paper. The existing data use
one quota setting; they cannot establish cross-period benefits. Another
regression, guard threshold, favorable solver benchmark or extra workload
would not repair that evidential gap or establish originality.

## Closest methods to compare before implementing anything

| Source | Inspected result | Implication for the candidate |
|---|---|---|
| [Sampat et al., Kscaler, APSys 2025](https://tianyin.github.io/pub/kscaler.pdf), §§3, 5 | Kernel observations of run/idle behavior drive joint quota-period adaptation. Application SLOs are identified as future work in the reviewed paper. | Joint adaptation and periodicity awareness are already covered. An author's future-work item is not evidence that the wider problem remains unsolved. |
| [Wang et al., Autothrottle, NSDI 2024](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf), §§3.2, 4 | SLO-targeted CPU quota management using throttle and usage observations; the implementation observes 100 ms CFS periods. | SLO awareness and CPU control are established. A fixed-budget period selector would have to add a specific capability beyond a fair adaptation of this approach. |
| [Struhár et al., Hierarchical Resource Orchestration Framework for Real-Time Containers, 2023](https://www.es.mdu.se/pdf_publications/6658.pdf), §§4.1, 5 | Offline server design selects quota and period for schedulability; runtime resource adaptation uses a hierarchical real-time scheduler. | Deadline-aware quota-period design already exists under reservation premises. We must compare its premises and result with unmodified CFS bandwidth ceilings, not dismiss it because the application differs. |
| [Cucinotta et al., Strong Temporal Isolation Among Containers in OpenStack for NFV Services, 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), §4.2 | Reservation-based response analysis and temporal isolation. | Known response/supply bounds may already suffice under applicable assumptions. A ceiling cannot automatically be treated as guaranteed supply. |

A targeted search also found a 2026 real-time-container adaptation chapter and
adjacent deadline-aware CPU allocation work. These are additional leads, not
audited exact matches. This preliminary screen is not an exhaustive citation
review or a justification to begin experiments.

## The immediate deliverable

Prepare one explicit comparison answering:

1. **Decision and information:** Are we choosing a fixed period before a run,
   adapting online, or declaring that no period meets the target? What arrival,
   work-cost and quota-phase information is available before that decision?
   Start with one worker and a small declared set of admissible periods; do
   not quietly expand into a general cloud orchestrator.
2. **Existing solution:** Can the closest periodic-resource result, quota-period
   method, or a simple calibrated sweep already make this decision adequately?
   Identify the equations, required observations and assumptions, including
   whether CPU delivery is guaranteed or only limited.
3. **Actual addition:** What precise useful capability would our method add?
   Possible dimensions to investigate are less calibration, better justified
   predictions under phase uncertainty, or a materially different feasible
   decision. These are alternatives to assess, not achieved results or a
   requirement to claim all three.

Use the existing records only to assess what information we possess and what
would need measurement. Retrospective exploration must remain labelled as
such. The deliverable is a claim-versus-method comparison and a proceed/stop
verdict, not a simulator, new controller or additional performance campaign.

## Conditions to continue or stop

Continue only if we can state a specific contribution beyond the existing
methods, explain why it is nonroutine, and give a feasible plan for testing
it against the strongest adequate baseline. A Linux application, new deadline
metric or exact wording difference is insufficient.

Stop this candidate if a standard bound or straightforward adaptation supplies
the needed result with adequate effort. Also stop if the supposed benefit
reduces to selecting the shortest allowed period without a meaningful cost or
constraint. A calibrated period sweep and fixed default/short periods are
essential simple alternatives; a sophisticated selector must justify its
additional complexity or save an identifiable measurement cost.

If a genuine gap survives, build a tiny offline feasibility prototype first.
Only after it demonstrates the claimed additional capability should we prepare
fresh calibration and validation. New measurements need their own frozen
design, fairness criteria and bounded budget. Existing V28 outcomes cannot
become prospective evidence for a newly selected rule.

If this candidate also closes, do not start another automatic campaign. The
honest options are to finish the scoped empirical paper or deliberately choose
a new research question with a broader change of scope. No sequence of small
variants can guarantee strong novelty.
