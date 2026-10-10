# Reviewer-style assessment and research decision

8 October 2026. This is a substantive assistant review of correctness,
originality and significance, not independent journal peer review. It
supersedes the earlier recommendation that an external response was needed
before we could decide whether to invest further. The earlier sealed review
packet and evidence remain unchanged.

## Verdict

**The current admission-only theorem and implementation do not establish
sufficient novelty to anchor the stronger methods/theory paper we want. I
recommend closing this candidate as the present lead for that contribution.**

The mathematical argument appears sound under its stated assumptions. Its
main steps are short consequences of standard FCFS completion formulas and
one-dimensional linear inequalities. The prototype has neither an improved
established worst-case bound nor the convincing practical advantage sought
in Step 4. This is enough for a negative investment decision; another
person's approval is not required to make it.

I have **not proved that an identical theorem is already published**. The
classification is: likely routine specialization, and insufficient demonstrated
contribution. That differs from claiming a complete literature proof of
firstness or non-firstness. An external expert remains an optional way to
challenge this assessment, rather than a prerequisite for our decision.

## Correctness assessment

I re-examined the [complete model, theorem and proof](runtime_io_fifo_theorem_review_packet_20261008.md),
including the indexing, capacity guard and equality conventions. No apparent
mathematical error was found in the claimed reduction.

The capacity argument needs the history to be reachable: with at most B
unfinished jobs, a prefix with m admissions is full exactly when its
(m−B+1)th admitted job remains unfinished. Substituting its FCFS completion
formula gives a single service-time threshold. Prefixes with m < B always
have capacity. This handles departures at the arrival instant correctly.

A fixed admission vector fixes every threshold. Its feasible parameter
values are an intersection of closed upper half-lines and strict lower
half-lines with [L,H]. Hence it occupies one right-closed interval. The
right-closed topology follows from completion-first ties; it is not an
additional behavioral assumption.

For an admitted job, lateness is a strict threshold in s because all
completion-envelope coefficients are positive. Rejections are constant
within a fixed history, and late jobs never alter system policy. The
combined count is therefore monotone within that history. The minimum
witness construction correctly handles an excluded left endpoint, while
the included right endpoint attains the regional maximum.

These conclusions do not imply global monotonicity, independently uncertain
per-job service times, cancellation semantics or a CPU-quota guarantee.
The prior 7,806 structural checks are supporting evidence; this review did
not rerun them or treat finite tests as a universal proof.

## Originality assessment: the direct derivation is the main objection

The most damaging comparison is not another paper with the exact same title
or metric. It is how little additional reasoning is needed to derive our
claim from an existing recurrence.

[Bandi, Bertsimas and Youssef, §2, Eq. (2)](https://www.mit.edu/~dbertsim/papers/Robust%20Optimization/Robust%20Queueing%20Theory.pdf)
give an FCFS system-time expression attributed to Lindley. Adding the admitted
arrival time and setting every service time equal to s yields our completion
envelope. The following reduction is **my inference from that formula and
our queue contract**, not a theorem attributed wholesale to their paper:

1. Use the earliest of the last B admitted completions to test fullness.
2. Rearrange its affine terms into a scalar admission threshold.
3. Intersect the threshold conditions of a fixed admission vector to get its
   service-time interval.
4. Rearrange each deadline comparison into a strict service threshold; count
   them after the admission sequence is fixed.

Thus the admission-only reduction is a useful specialization, but the current
proof introduces no substantial additional mathematical machinery. Finding
no exact wording match would not remove this objection.

Symbolic execution paths and their compatible timing-parameter regions also
precede this work: see
[Cimatti, Palopoli and Ramadian, §4.2 and Fig. 3](https://www.researchgate.net/publication/221298325_Symbolic_Computation_of_Schedulability_Regions_Using_Parametric_Timed_Automata).
Their objective is schedulability, not our combined count. That distinction
is real, but the use of parameter regions itself cannot carry our novelty.

## Claim-by-claim decision

| Proposed claim | Review finding | Contribution status |
|---|---|---|
| Max-plus FIFO completion envelope | Direct specialization of the standard FCFS formula. | Established building block. |
| Exact admission threshold | Follows by applying that formula to the earliest of the last B jobs. | Correct, but routine-looking algebra. |
| One interval per admission vector | Intersection of one-dimensional threshold inequalities. | Straightforward structural consequence. |
| Deferred deadline counting | Deadlines are passive observers; positive slopes give monotonicity on a fixed history. | Useful reduction, insufficient substantive originality demonstrated. |
| Capacity-dependent polynomial region bound | Bound the integer denominator and count the possible arrival-difference roots. | A narrow lemma worth retaining; no improved worst-case result or tightness result established. |
| Faster exact analyzer | Confirmation favors our solver on 7/24 cases, with no twofold wins. | Practical-advantage claim fails the declared gate. |
| Stronger explanation or guarantee for the runtime paper | No validated bridge from a shared constant service parameter to the measured runtime system. | Applicability claim unsupported. |

Our earlier exact breakpoint reference already has a polynomial universal
root family and an O(N⁴) arithmetic bound. **That reference is our own
baseline, not published prior art.** It does, however, defeat an internal
argument that the new partition bound alone turns an otherwise necessarily
exponential task into a tractable one. The current admission implementation's
coarse O(N⁵) bound establishes no better asymptotic result. These are upper
bounds excluding rational bit costs, not matching complexity lower bounds.

## Why this is not currently a stronger paper contribution

The exact loss-plus-late objective and explicit witnesses are useful. A short
technical note, teaching example or reproducible tool might benefit from
them. We have not established their suitability for any particular venue,
and that would not answer the user's request for a substantially stronger
research contribution.

A methods/theory argument presently lacks both a nonroutine result and a
demonstrated algorithmic advantage. An applied argument lacks validation
that this restricted service model contributes a useful new capability in
the original CPU-quota setting. Correctness cannot substitute for these
missing contributions.

This judgment does not depend on locating an exact published twin. Nor does
failure to meet a speedup threshold prove the theorem cannot have theoretical
value. It is the combination of the short derivation, narrow scope and absent
demonstrated advantage that makes further investment unjustified on current
evidence.

## Additional literature check and limits

I repeated targeted searches for parametric finite-buffer analysis, FIFO
admission monotonicity, piecewise-affine queue analysis, symbolic deadlines
and parametric discrete-event simulation. Most new results concern
stochastic loss, policy optimization or unrelated simulation; none was used
as evidence of an identical theorem. Broad generic capabilities were not
misrepresented as reproduced algorithms.

The university's record identifies a 17-page
[CESNET technical report from 2005](https://www.fit.vut.cz/research/result/c57593/.cs)
and links its author PDF. The PDF and old CESNET HTML remained inaccessible
through the browsing tool. This resolves the location of that report, not
the full-text access gap. The short CHARME paper and longer report are still
distinguished. Earlier source-access and forward-citation limitations remain.

This is a focused contribution review, not an exhaustive citation audit.
No source absence is treated as proof of originality. Full firstness remains
unresolved; **the decision not to build the stronger paper around this
candidate does not need a claim of exhaustive firstness resolution**.

## What happens to the research now

Retain the exact solvers, counterexamples, proof and negative comparisons as
research assets. Keep the speedup angle shelved and do not advertise the
admission-only theorem as the new centerpiece of the empirical paper.

For the stronger-paper objective, this candidate is closed on present
evidence. Reopening it requires a specific nonroutine result, an established
algorithmic advantage or a validated new application capability. Merely
adding benchmark repetitions or searching for a missing exact citation
does not supply that result. No new campaign is authorized or launched here.

The original empirical draft still documents the accounting/forecasting
case. Its scientific value and any suitable empirical contribution should
be assessed on its own evidence; this negative theorem verdict does not
erase it. Independent human review can still be useful later, but it is
optional for this decision. No review request has been sent.
