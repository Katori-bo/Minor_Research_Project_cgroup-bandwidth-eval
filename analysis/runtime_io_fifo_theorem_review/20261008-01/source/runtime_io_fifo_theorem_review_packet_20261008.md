# Originality review request: admission-only analysis of a finite FIFO trace

8 October 2026. Prepared for an independent researcher; **no independent
expert response has been received**. This packet requests an assessment, not
an endorsement. Collection remains stopped.

## Question for the reviewer

Is the admission-only reduction below a known result, a routine corollary of
FCFS recurrences and symbolic path analysis, or a sufficiently substantive
new theorem? If it is routine, we would prefer to close this research route
before doing further experiments. Correctness alone is not our novelty claim.

Our current assessment is that **a routine specialization is the leading
explanation**. We have not identified a published exact match in the selected
passages reviewed, but we have not established firstness. The prototype also
failed its predeclared practical speedup gate.

## Model and objective

There are N ≥ 1 fixed, ordered rational offer times a₁ ≤ … ≤ aₙ, initially
an empty work-conserving single FIFO server, and B ≥ 1 total slots, including
the job in service. Every admitted job takes the **same constant** service
time s ∈ [L,H], with rational 0 < L ≤ H. The uncertainty is one persistent
scalar parameter, not an independently chosen time for each job.

An offer finding B unfinished admitted jobs is rejected (tail-drop). A
completion at an offer time departs first. Simultaneous offers are processed
in input order. Every job has relative deadline D ≥ 0: completion equality
is timely. Late jobs continue to completion; deadlines cause no cancellation,
priority change or other feedback. The objective is the minimum and maximum
over all real s in [L,H] of

\[
K(s)=\#\{\text{rejected offers}\}+\#\{\text{admitted late jobs}\},
\qquad F(s)=K(s)/N.
\]

## Candidate theorem

**Admission-only partition theorem.** Under this model, each realizable
binary admission vector has a single interval of service-time valuations.
These nonempty intervals partition [L,H]. They are right-closed: the first
is [L,h] (possibly [L,L]), and subsequent intervals are (ℓ,h]. On each
interval, K is a nondecreasing step function. Therefore exact global extrema
and rational attaining witnesses can be found by branching only on admission
decisions, retaining completion formulas symbolically, and evaluating deadline
thresholds after the admission history is fixed. Neither idle decisions nor
deadline decisions need to split the search states.

The following formulas make the claim reproducible. For a fixed admitted
subsequence with offer indices p₁ < … < pₘ, write bⱼ = aₚⱼ. Its kth
completion time is

\[
C_k(s)=\max_{1\le j\le k}\{b_j+(k-j+1)s\}. \tag{1}
\]

At the next offer aᵢ, m < B implies admission. If m ≥ B, set

\[
c_i=\min_{1\le j\le m-B+1}
\frac{a_i-b_j}{m-j-B+2}. \tag{2}
\]

The offer is admitted exactly when s ≤ cᵢ and rejected exactly when s > cᵢ.
For accepted job k, set

\[
d_k=\min_{1\le j\le k}\frac{b_k+D-b_j}{k-j+1}. \tag{3}
\]

Job k is late exactly when s > dₖ. Consequently a history with m admissions
has, on its interval I,

\[
K_I(s)=N-m+\sum_{k=1}^m\mathbf{1}\{s>d_k\}. \tag{4}
\]

For I with low endpoint ℓ and closed high endpoint h, its maximum is K_I(h).
Its minimum is N−m plus the number of dₖ < ℓ, adding the number of dₖ = ℓ
when the left endpoint is open. For a closed left endpoint, ℓ attains that
minimum. Otherwise, take the midpoint between ℓ and the smallest dₖ > ℓ
inside I, or h if there is none. This is a rational attaining witness;
evaluating an excluded endpoint itself would be incorrect.

**Structural corollary, also submitted for originality assessment.** Define

\[
E_B=\left\{\frac{a_i-a_p}{q}:1\le p<i\le N,
\ 1\le q\le i-p-B+1\right\}.
\]

Pairs with a nonpositive upper bound contribute nothing. Every admission
boundary belongs to Eᵦ. With M = max(N−B,0), the number R of admission
intervals satisfies

\[
R\le 1+|E_B\cap[L,H)|\le 1+\frac{M(M+1)(M+2)}6. \tag{5}
\]

Thus only polynomially many admission vectors can be realizable along this
one-dimensional interval, despite the 2ᴺ possible binary vectors in general.
K is left-continuous at every s ∈ (L,H]. This is a consequence of the stated
tie conventions, not global monotonicity. These refinements do not establish
an improved worst-case algorithm over the earlier breakpoint reference.

## Proof

1. **Completions.** For admitted jobs, C₀ = 0 and
   Cₖ = max(bₖ,Cₖ₋₁)+s. Nonnegative b₁ and positive s give (1) by induction.
   This is the standard FCFS recurrence applied to the admitted subsequence;
   it is not claimed as a new recurrence.

2. **Capacity.** A reachable prefix never has more than B unfinished jobs.
   When m ≥ B, it is full at aᵢ exactly when its (m−B+1)th admitted job has
   not completed: Cₘ₋ᵦ₊₁(s) > aᵢ. Substituting (1), this is an OR of
   inequalities s > (aᵢ−bⱼ)/(m−j−B+2), giving (2). Equivalently fullness
   is Cₘ(s)−(B−1)s > aᵢ. The extra terms in this latter envelope, from
   j > m−B+1, have nonpositive coefficients after subtraction and are ≤ aᵢ
   because bⱼ ≤ aᵢ. They cannot change the test. The reachability condition
   is important; this is not a statement about arbitrary overloaded histories.

3. **Regions and completeness.** For any fixed binary vector, its admitted
   subsequences at each prefix are fixed, so every cᵢ is a constant rational
   number. Intersect [L,H] with s ≤ cᵢ for each admission and s > cᵢ for
   each rejection. The intersection is empty or one interval. Its upper
   bounds are closed and its additional lower bounds strict. Different
   vectors are disjoint, and every s has exactly one deterministic execution.
   Successively making these admission splits therefore covers the interval
   completely, including equality points. No idle-mode branch is required
   because (1) keeps all maxima without choosing their active terms.

4. **Deadlines and extrema.** In (1) every coefficient k−j+1 is positive.
   Cₖ > bₖ+D is equivalent to s > dₖ, proving (3) and (4). Because lateness
   never changes admission or service, these tests may be deferred. Equation
   (4) is monotone on a history interval and gives the extrema and witnesses
   above. Global extrema are the smallest and largest regional values. A
   region's maximum need not be the global maximum at H; changing admission
   histories can change K in either direction.

5. **Boundary bound and left continuity.** A minimum in (2) is attained at
   some bⱼ = aₚ. Its positive integer denominator q = m−j−B+2 is at most
   i−p−B+1, since m−j+1 ≤ i−p. Each boundary is consequently in Eᵦ.
   Distinct cuts along a real interval create at most one additional interval
   each, including a possible singleton at L. Summing the expression counts
   over i−p gives M(M+1)(M+2)/6. Right-closed intervals and strict lateness
   thresholds give the same admission vector and K immediately to the left
   of any s > L, proving left continuity.

## Closest known building blocks and the residual question

| Source and inspected passage | Already established | Question left for this theorem |
|---|---|---|
| [Bandi, Bertsimas & Youssef, Robust Queueing Theory (2015)](https://www.mit.edu/~dbertsim/papers/Robust%20Optimization/Robust%20Queueing%20Theory.pdf), §2, Eq. (2) | FCFS system-time expression in cumulative interarrival and service times, attributed to Lindley. | Adding the arrival time and setting every admitted service to s gives (1) directly. Does the finite-loss extension (2)–(5) warrant anything beyond a corollary? |
| [Baccelli et al., Synchronization and Linearity (1992)](https://www.rocq.inria.fr/metalau/cohen/documents/BCOQ-book.pdf), §7.2.1, Eq. (7.3), Remark 7.1 | Max-plus event recurrence associated with a single-server infinite-buffer FIFO queue. | Our known offered trace undergoes tail-drop, so the accepted input depends on s. Max-plus treatment itself is established. |
| [Cimatti, Palopoli & Ramadian (2008)](https://doi.org/10.1109/RTSS.2008.36), §4.2 and Fig. 3, [author-uploaded text](https://www.researchgate.net/publication/221298325_Symbolic_Computation_of_Schedulability_Regions_Using_Parametric_Timed_Automata) | Extracting parameter regions from symbolic execution/error traces; schedulability regions rather than this count objective. | Is projecting to admission histories and postponing this passive monotone observer a routine abstraction? |
| [Matoušek, Tools for Parametric Verification (2004)](https://www.jucs.org/jucs_10_10/tools_for_parametric_verification/Matousek_P.pdf), §§2.3–2.4, 5.1–5.2 | Parametric symbolic configurations, integer counters, FIFO channels and loss-recovery parameter synthesis. | Its reviewed objective is recovery in a PGM model, not exact rejected-plus-late extrema for our model. Counting losses or synthesizing parameter regions is nevertheless established. |

These differences describe inspected passages; they do not establish that no
published result elsewhere implies this theorem. The
[desk assessment](runtime_io_fifo_theorem_originality_assessment_20261008.md)
and source ledger retain the access and citation-audit limits.

## What our implementation and evidence establish

The frozen [admission solver](../analysis/finite_fifo_deadline_admission.py)
implements these calculations, with ordinary envelope pruning. Its existing
checks include independent exact enumeration, reachable symbolic execution
and SMT checks. The new structural checks address (5), interval topology
and equality behavior; finite checks support debugging, not a proof or an
originality verdict.

In the [Step 4 confirmation](runtime_io_fifo_hardcases_step4_20261008.md),
both admission and reachable solvers complete all 24 selected cases. Admission
is faster on seven and slower on seventeen, with no twofold wins. The current
coarse bound is O(N²R) arithmetic operations, hence O(N⁵), versus the exact
reference's O(N⁴); rational bit costs are excluded. No asymptotic advantage,
convincing practical advantage or validated runtime-system applicability is
established. Published analyzers have not been reproduced or timed.

## Requested response and research decision

Please assess these three questions:

1. Is the theorem correct under the full contract, especially the capacity
   guard, interval boundaries and open-endpoint minimum?
2. Is it an existing result or a routine corollary? A citation or a short
   reduction would be particularly helpful. Please distinguish the basic
   recurrence from the admission-only partition and capacity-dependent bound.
3. If some part is original, is it substantive enough for a modest theoretical
   paper? What concrete missing result would change your assessment?

Please classify the assessment as **known/routine**, **potentially original
but insufficient**, **potentially substantial with specified missing work**,
or **unable to assess**. These are informal triage categories, not a request
for publication approval. An unanswered request does not count as a positive
review. We keep the speedup route shelved and collection stopped pending a
substantive response.
