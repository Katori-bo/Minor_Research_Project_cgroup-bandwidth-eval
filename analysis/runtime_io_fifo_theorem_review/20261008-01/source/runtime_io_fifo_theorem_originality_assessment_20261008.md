# Desk assessment of the admission-only theorem

8 October 2026. Literature scope through this date. **Speedup route shelved;
independent expert assessment pending.** No collection, calibration refit or
performance campaign was launched for this review.

## Current verdict

The result appears correct under its deliberately narrow model, but we have
not established a strong theoretical contribution. My current judgment is
that it is **likely a routine specialization of known FCFS and symbolic
parameter-analysis machinery**. This is an assessment of the derivation, not
evidence that a paper with the identical theorem has already been found.

The [review packet](runtime_io_fifo_theorem_review_packet_20261008.md) states
exactly what remains to be assessed: realizable admission vectors occupy
intervals; the all-offer failure count is monotone within each interval;
admission boundaries belong to a finite capacity-dependent root family; and
only admission splits are needed for exact extrema. It includes a proof and
asks an expert to distinguish correctness, firstness and research significance.

## Why the originality risk is high

The completion formula is directly derivable from a published FCFS expression.
In [Bandi et al., §2, Eq. (2)](https://www.mit.edu/~dbertsim/papers/Robust%20Optimization/Robust%20Queueing%20Theory.pdf),
add the kth admitted arrival to system time and make all service times equal
to s. This gives our maximum of affine completion terms. **This reduction is
our inference**, not a claim that their paper states the full tail-drop theorem.

Once the accepted sequence is fixed, positive coefficients make deadline
counts monotone. The capacity test uses the earliest of the last B admitted
completions. Its linear inequalities give a scalar threshold. A fixed history
then gives an intersection of half-lines, hence an interval. These steps are
short algebraic consequences of the recurrence and queue policy. A new
application or a newly written proof of them would not, by itself, establish
a substantial new theorem.

There is also longstanding formal-methods precedent for associating parameter
regions with symbolic paths:
[Cimatti et al., §4.2](https://doi.org/10.1109/RTSS.2008.36).
[Matoušek (2004), §§2.3–2.4 and 5.2](https://www.jucs.org/jucs_10_10/tools_for_parametric_verification/Matousek_P.pdf)
uses parametric symbolic analysis with counters and FIFO channels for loss
recovery. Neither inspected objective is our exact combined count, but these
sources rule out broad novelty claims about symbolic uncertainty, path regions
or counting losses.

The potentially useful specialization is avoiding idle and deadline branching
while preserving exact counts. We have not established that this abstraction
requires a new idea beyond combining those building blocks. An expert should
assess that question directly, including whether equation (5)'s
capacity-dependent bound is merely a routine combinatorial corollary.

## What changed in this review

The theorem now explicitly includes the right-closed shape of admission
regions, rational witnesses for open-left intervals, and a bound of
1 + M(M+1)(M+2)/6 regions for M = max(N−B,0). These clarify the proof;
they are **not declared new research contributions**. They do not improve
the current coarse O(N⁵) solver bound over the reference's O(N⁴).

The [structural check](../analysis/check_finite_fifo_theorem_review.py)
enumerated 7,806 small rational problems: N = 1…5, sorted offers from
{0, 1/2, 1, 3/2, 2}, B = 1…N+1, three deadlines and two service intervals
(including a singleton). It checked 10,266 admission regions and 28,921
reference boundaries. All extrema agreed with complete breakpoint replay;
interval shape, admission-boundary membership, the region bound and left
continuity passed. These checks are finite supporting evidence, not a
replacement for the proof, and were not timed as performance evidence.

All solver implementations are unchanged. The
[Step 4 decision](runtime_io_fifo_hardcases_step4_20261008.md) remains binding
for this prototype: no convincing practical advantage was demonstrated.

## Scope of the literature assessment

This was a targeted desk review, not an exhaustive literature or citation
audit. We inspected the FCFS formula, the max-plus book's FIFO example,
Cimatti's parameter-region algorithm and Matoušek's 2004 primary text.
The [source ledger](../analysis/runtime_io_fifo_theorem_review/20261008-01/sources.json)
records passage locations, access status, differences and search queries.
Earlier Step 3 and Step 4 assessments of dataflow, max-plus uncertainty,
FIFO abstraction and schedulability remain relevant, with their original
access limits preserved.

The 2005 lossy-FIFO seed's publisher PDF could not be retrieved in this review.
Indexed excerpts from a longer technical report were available, but that
version must not be conflated with the short conference paper. Its loss
abstraction also must not be assumed identical to tail-drop. We do not use
these access gaps as evidence of originality. Selected citation links were
followed; complete forward-citation coverage, including Google Scholar's
“Cited by” results, remains unverified. Search-engine crawl dates were not
treated as publication dates.

## Decision before more work

The ready-to-send
[review request](../analysis/runtime_io_fifo_theorem_review/20261008-01/review_request.txt)
asks a queueing, discrete-event/max-plus or parametric-verification researcher
for a concrete assessment of the enclosed theorem. It has **not been sent**.
The same assistant helped derive the theorem and prepared this desk review;
this is not an independent peer review.

If the response is **known/routine**, close this route as a stronger-paper
novelty lead. If it is **potentially original but insufficient**, ask for the
specific missing contribution before committing more work. If the expert
identifies a **substantial, precise gap**, assess that proposed result and its
feasibility before a new campaign. A citation gap, unanswered request or
positive correctness check does not clear this gate.

The model's constant common service parameter also needs a validated bridge
to the measured CPU-quota/runtime system before becoming a guarantee in that
paper. This review supplies no such bridge. Historical paper drafts and
scientific evidence remain unchanged; this theorem belongs in the review
packet until its contribution is justified.
