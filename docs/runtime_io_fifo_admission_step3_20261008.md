# Step 3: admission-only reduction, verification and contribution decision

8 October 2026. Offline mathematics and synthetic algorithm comparison.
Scientific collection remains stopped. The existing empirical paper is unchanged.

## Decision

**The correctness milestone passed; the stronger-contribution gate did not.**
We implemented a precise admission-only reduction, supplied a correctness
argument and verified it against independent queue simulation and SMT. It
reduces the number of explored regions, but is slower than the existing
reachable method on several rejecting traces. More decisively, a simple
certified witness shortcut solves all 20 benchmark cases. Those cases therefore
cannot establish a need for our full symbolic analyzer to obtain extrema.

This is useful research progress, but it is not evidence of publication-ready
novelty. Do not add an achieved novelty claim to the paper, and do not launch
another service experiment on the strength of these results. The proposed
reduction remains a candidate; its originality and a useful advantage on
harder inputs are unresolved.

## The specific reduction implemented

The [candidate](../analysis/finite_fifo_deadline_admission.py) partitions the
service interval only when an admission decision changes. It does not split
at idle/busy boundaries, individual departures or deadline crossings.

On a fixed admission history, completion times are maxima of affine functions
of the common service time. Those functions are increasing. Hence the failure
count is nondecreasing **within a fixed admission region**, although it can
decrease when the admission pattern changes. The method computes each region's
minimum and maximum directly from deadline thresholds and then combines the
regional extrema. Open interval boundaries receive exact rational witnesses.

It uses standard max-plus completion formulas and a standard upper envelope
to discard globally dominated affine functions. An ablation retains all lines.
This is a concrete difference from the existing reachable implementation,
which branches on departures and deadline labels and stores pending jobs.
It is not a discovery of max-plus algebra, convex hulls or symbolic branching.

Inputs and event conventions are exactly the
[Step 1 contract](runtime_io_fifo_reference_step1_20261008.md). Capacity B
includes the running job; completion at arrival releases a position before
admission; completion at the deadline is timely; ties use offer order;
rejected jobs consume no service; late admitted jobs finish. There is one
shared constant service time in a closed rational interval `[L,H]`, with
`0 < L <= H`. The all-offer denominator is N.

## Correctness argument

Number admitted jobs on a fixed history from zero, with arrival timestamps
`t_0,...,t_(m-1)`. These are a subsequence of the offered trace. Let `T_m(s)`
be the last admitted completion after m admissions, with `T_0(s)=0`.

**Lemma 1: scalar capacity guard.** At offered arrival a the system is full
exactly when

```text
T_m(s) - (B-1)*s > a.
```

If empty, `T_m <= a` and the guard is false. Otherwise q pending equal-size
jobs have residual work `W=r+(q-1)*s`, where the running job's residual
`0 < r <= s`. All pending completions are s apart: while the queue is
nonempty every admitted job joins the current busy period. Thus
`q=ceil(W/s)` and, as capacity is never exceeded, q=B exactly when
`W>(B-1)*s`. Also `W=T_m-a` while nonempty. This proves the guard and its
strict inequality at equal-time departures. Rejection leaves T unchanged.

This is a deterministic workload representation, not an originality claim.
The [compact SMT comparator](../analysis/finite_fifo_deadline_compact_smt.py)
receives the same scalar guard; it therefore improves the earlier O(N²)
occupancy encoding to O(N) guards/row constraints rather than withholding
this simplification from a generic competitor.

**Lemma 2: completion envelope.** Inducting on the standard FIFO recurrence
`T_(m+1)=max(a,T_m)+s` gives

```text
T_m(s) = max over 0 <= j < m of [t_j + (m-j)*s]
       = m*s + max over 0 <= j < m of [t_j - j*s].
```

The first admission satisfies this formula because timestamps are nonnegative.
The next admission adds s to existing lines and contributes its own arrival
plus s. The formula retains idle/busy changes as an envelope; they need no
separate execution branch.

**Lemma 3: one admission cut per history.** At the next offer a, subtract
`(B-1)*s` in Lemma 2. A line has slope `m-j-B+1`. Nonpositive slopes cannot
make the full-queue guard true for positive s, since `t_j <= a`. Therefore,
when m >= B, reject exactly when

```text
s > c,  where c = min over j with m-j-B+1 > 0
                    of (a-t_j)/(m-j-B+1).
```

For m < B the queue cannot be full. Splitting a current region into its
`s <= c` and `s > c` portions is exact, disjoint and complete. A branch keeps
one admitted subsequence and a rejection count. Inducting on offered arrivals
partitions the entire parameter interval into fixed-admission regions.

**Lemma 4: deadline thresholds do not affect future execution.** After the
next admission, let its completion be `T_(m+1)` and deadline `a+D`. All slopes
in its envelope are positive. It is timely exactly when

```text
s <= d, where d = min over 0 <= j <= m of
                  (a+D-t_j)/(m+1-j).
```

Here the newly admitted arrival has `t_m=a`. Store d without splitting the
region. A later offer cannot change this job's completion. Deadline labels
cannot alter admission because the model has no abandonment or cancellation.
Thus for each final region I, rejection count r is constant and

```text
K_I(s) = r + number of stored deadline thresholds d with d < s.
```

This is nondecreasing on I. It need not be constant on I; the output calls
these **regions with extrema**, not constant-outcome cells.

**Lemma 5: exact extrema and attainable witnesses.** Write I with bounds l,h
and explicit open/closed endpoints. Its minimum late count is the number of
thresholds below l, plus those equal to l when the left endpoint is open.
Its maximum late count is the number strictly below h, whether the right
endpoint is open or closed. A threshold equal to h is timely at h and cannot
be crossed inside the region.

For a closed left endpoint, l attains the minimum. Otherwise choose a rational
point between l and the first stored threshold strictly greater than l, or
between l and h if none intervenes. For a closed right endpoint, h attains
the maximum. Otherwise choose a point between h and the last stored threshold
strictly below h, using l if none intervenes. These witnesses attain the
counts; singleton regions are handled with their closed endpoint. Global
minimum/maximum are obtained by selecting among regional extrema.

**Envelope pruning.** Lines `t_j-j*s` arrive in strictly decreasing slope
order. Store the upper envelope with adjacent crossings strictly decreasing
in admitted ordinal. When inserting a line, remove the previous final line
while the new crossing is at or beyond the prior crossing; that line has no
interval where it exceeds the retained neighbors. This standard construction
preserves the maximum for all real s, including ties. Adding a common
multiple of s preserves dominance, so pruned lines cannot change capacity or
deadline predicates. There is no pruning based on a numerical grid.

Together these lemmas establish exact bounds under the model. They are written
proof arguments, not an independently reviewed or machine-checked formal
proof. SMT exclusions trust the solver, with no exported checked proof objects.

## Cost and refusal

Let R be the number of final admission regions, and Hmax the largest retained
envelope along a branch. At most N*R state visits occur; each has an envelope
copy/pruning and up to two scans costing O(Hmax). Final threshold scans cost
O(N*R). Thus arithmetic/tuple work is bounded by
`O(N*R*(Hmax+1))`, at worst `O(N²*R)`, excluding rational bit costs.
Persistent deadline chains and current envelopes use O(N*R) storage in a
conservative worst-case bound. Results store O(R) summaries and O(N) witnesses.

Admission cuts belong to the family `(a_i-a_j)/k`, with `j<i` and
`1 <= k <= i-j`. There are at most `N*(N-1)*(N+1)/6` such expressions before
deduplication/filtering, hence R=O(N³). The resulting coarse worst-case time
bound is O(N⁵). **This prototype does not improve the reference's O(N⁴)
worst-case bound.** Fewer explored regions are not a proof of faster runtime.

Defaults refuse beyond 2,048 offers, 10,000 live states or 10,000,000 charged
envelope/counter terms; no approximate extrema are returned as exact. These
are operation guards, not hard time or memory limits. The comparison uses
explicit limits recorded below, including a wall-clock worker limit.

## Verification completed

The [candidate tests](../analysis/test_finite_fifo_deadline_admission.py)
passed all eight tests in 4.585 seconds, comparing 837 synthetic problems:
672 exhaustive, 150 seeded rational, ten directed, four deadline-invariance
cases and one scaled/shifted case. Bounds match both the conservative
reference and the reachable checker. With/without-envelope pruning yields
identical admission regions. Full witness offer lists match queue replay.

Intersecting each candidate region with the reference's complete partition
checks its rejected count, fixed admission pattern and attainable regional
failure range. Forty-one problems also compare with compact SMT; 59
whole-region SMT queries using the older independent occupancy encoding
exclude any bound violation at any real service value in those regions.
Envelope checks compare pruned and unpruned maxima at pairwise intersections
and additional service values. Equality, singleton extrema, terminal drain,
continued late execution, unit/origin invariance, CLI no-overwrite and
resource/unknown refusal are covered.

## Predeclared larger comparison: mixed result

The [driver](../analysis/compare_finite_fifo_step3.py) wrote its
[design](../analysis/runtime_io_fifo_admission_step3/20261008-01/design.json)
before timing. Five synthetic families—regular, bursts, irregular, repeated
interior counterexample, and no-loss—have sizes 16, 64, 128 and 256. Each
case/method has three serial fresh-process repetitions in a fixed shuffled
order. Candidate, unpruned ablation, reachable and compact SMT run on every
case; a safe two-endpoint method runs on the four no-loss cases: **252 runs**.

Candidate limits in this comparison are 512 offers, 10,000 states and
50,000,000 charged terms. Reachable limits are 10,000 states and 10,000,000
transitions. Compact SMT permits 512 offers, 2,000 ms per check and 5,000 ms
total check time. Every worker has a 10-second hard limit. Outputs differ:
candidate/ablation return admission-region extrema and witnesses; reachable
returns constant-outcome cells; SMT/endpoints return extrema and witnesses.
Timings include the method call and output/witness construction; imports,
process startup, JSON and independent witness verification are excluded.

Of 252 runs, 180 completed exactly and 72 were incomplete. All completed
extrema agree and reported witnesses are queue-verified. Candidate completed
54/60, ablation 48/60, reachable 51/60, compact SMT 15/60 and safe endpoints
12/12. Candidate timed out on regular and irregular 256-offer traces. The
reachable method refused those cases at its state limit and timed out on
no-loss 256. These limits are operational effects, not impossibility results.
Compact SMT's unknown/time-budget results likewise establish no general
scalability barrier.

The 128-offer medians illustrate why the region reduction is insufficient:

| Family | Candidate time / regions | Reachable time / cells |
|---|---:|---:|
| Regular | 2,442.16 ms / 3,035 | 1,065.54 ms / 3,102 |
| Bursts | 30.99 ms / 32 | 17.69 ms / 36 |
| Irregular | 1,841.71 ms / 2,252 | 1,177.05 ms / 3,169 |
| Repeated interior | 6.15 ms / 2 | 7.89 ms / 7 |
| No-loss | 3.19 ms / 1 | 1,352.30 ms / 3,102 |

Among the 17 cases both completed, candidate is faster in eight and slower
in nine, despite fewer regions in each. Hull pruning improves the candidate
relative to its ablation, but that is a standard optimization. The no-loss
128 endpoint method takes only 1.12 ms and is already exact by monotonicity.

The [summary and raw runs](../analysis/runtime_io_fifo_admission_step3/20261008-01/comparison.json)
retain all outcomes. Three repetitions, small synthetic families and an
uncontrolled desktop host are insufficient for publication-level performance
claims. Absolute worker RSS includes imports and verification and is not
used to claim a solver-memory improvement.

## Stronger simple comparator discovered after the pilot

The [shortcut](../analysis/finite_fifo_deadline_shortcut.py) uses independently
valid bounds and a few exact replay witnesses. This was added after seeing the
pilot; it is a declared post-pilot diagnostic, not a retrospectively altered
predeclared comparison.

For each simultaneous arrival group of size g, at least `max(0,g-B)` offers
must be rejected: no positive-service job can depart between those tied
offers. Summing yields a global lower failure bound. If `L>D`, every offered
job fails (rejected or late), giving lower bound N instead.

If `H<=D`, the first offer is guaranteed timely. So is any offer preceded by
a gap at least `B*H`: at the previous arrival the residual work is at most
`B*s`, so the gap guarantees an empty system. Subtract these guaranteed
timely offers from N to obtain a global upper failure bound. If `H>D`, use
the universal upper bound N.

Replay at L, H and the three quarter points. **Return exact extrema only if
the observed minimum attains the proved lower bound and the observed maximum
attains the proved upper bound.** Otherwise return `undetermined`, with
sample extrema clearly distinguished from global bounds. These are
certificate conditions, not an assertion that a five-point grid is complete.
Where B>=N, rejection is impossible and two endpoints already give exact
extrema by the standard FIFO monotonicity argument.

The [shortcut suite](../analysis/test_finite_fifo_deadline_shortcut.py) passed
two tests in 0.138 seconds: 420 exhaustive small problems check every
certification and enclosure against the exact reference; a directed unresolved
control confirms that sampling alone never produces an exact result.

The [post-pilot diagnostic](../analysis/check_fifo_step3_shortcuts.py) evaluates
every original case plus that control, with three fresh-process repetitions:
63 runs. **The shortcut certifies all 20 original cases.** Eighteen have
completed independent method results, which agree; it also certifies the two
256-offer cases where all original methods refused or timed out. Original
case medians range from 0.207 to 5.663 ms. These timings are from a separate
batch and should not be treated as a paired statistical comparison.

For the control `[0,0,1/5,2/5]`, B=3, D=1, s in `[1/2,4/5]`, the shortcut
leaves the problem unresolved; exact analysis returns 2–3 failures out of four.
So the shortcut is not a general replacement for symbolic analysis. Its
success on our benchmark families does invalidate using those families as
evidence that a sophisticated analyzer is needed for their extrema. Results
and the control witness are in the
[diagnostic package](../analysis/runtime_io_fifo_admission_step3/20261008-01/shortcut_comparison.json).

## Focused originality screen

The [source ledger](../analysis/runtime_io_fifo_admission_step3/20261008-01/sources.json)
records primary sources, inspected passages, access failures and remaining
questions. The screen is through 8 October 2026 and is not an exhaustive
forward-citation audit. Some seed-source live fetches failed; their earlier
assessment is retained with that distinction.

| Reviewed prior method | What it already establishes | Implication for our claim |
|---|---|---|
| [Baccelli et al., 1992, §7.2](https://www-rocq.inria.fr/metalau/cohen/documents/BCOQ-book.pdf) | Max-plus recurrence modeling for FIFO queueing/discrete-event systems. | Completion envelopes are established mathematics. |
| [Sivaraman et al., 2009, §§III–IV](https://www2.ee.unsw.edu.au/~vijay/pubs/jrnl/09ton.pdf) | Convex-hull algorithms for traffic pacing with deadline constraints; identical-delay updates and logarithmic tangent methods. | Convex-hull use in deadline/network problems is established. Their pacer changes release scheduling; it is not this fixed-offer, shared-service extremum problem. |
| [André, 2013, §§II–IV](https://www.loria.science/andre/documents/observer-patterns-for-real-time-systems.pdf) | Timing-property observer patterns and reachability reductions, including implementation in IMITATOR. | Adding a deadline observer is not a new research principle. |
| [Fränzle et al., ICALP 2018](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ICALP.2018.125) | Quantitative costs/rewards and Pareto reachability in priced timed automata. | Quantitative optimization is established; their continuous-rate observers and general model differ from this discrete failure counter. |
| [Chen, 2004](https://www.sciencedirect.com/science/article/abs/pii/S037722170300136X) | Parameter optimization for finite-capacity fuzzy stochastic queues. | Neither uncertain queue performance nor interval extrema are novel in general. This is a stochastic-rate rather than finite deterministic-trace model. |
| [Matoušek et al., 2005](https://dl.ifip.org/db/conf/charme/charme2005/MatousekSV05.pdf), earlier reviewed §§3–4 | Lossy/delayed FIFO timed-automata modeling and parameter-dependent verification. | Parameterized lossy FIFO analysis already exists; current live PDF fetch failed. |
| [Cimatti et al., 2008](https://doi.org/10.1109/RTSS.2008.36), earlier reviewed §§4–5 | Symbolic trace-compatible parameter regions and schedulability synthesis. | Region splitting and symbolic path analysis already exist. Current author-page fetch failed; prior assessment does not establish our reduction's originality. |
| [Arias et al., 2024](https://doi.org/10.1016/j.scico.2023.103074), publisher indexed abstract | Symbolic analysis/parameter synthesis with Maude and SMT, including state folding. | General exact symbolic machinery remains a serious baseline. Full live access failed in this screen; no published artifact was reproduced. |

None of the reviewed passages establishes this exact admission-only
rejected-plus-late extremum specialization as a published ready-made algorithm.
That is a limited observation, not proof that it is absent. The derivation uses
simple consequences of established queue recurrences, so originality risk is
substantial even with a correct implementation.

The precise candidate claim would be: **an exact admission-only analysis for
finite FIFO all-offer loss/deadline extrema, avoiding deadline and idle event
partitioning through conditional monotonicity.** At present we can substantiate
its implementation and model correctness, not firstness, an improved worst-case
bound or a broad practical advantage over adequate alternatives.

## What to do with this result

Retain the proof and prototypes as offline research assets. The next worthwhile
gate, if pursued, is a bounded set of previously unseen rejecting traces on
which the certified shortcut is unresolved, with capacity/deadline variation
and the existing reachable method as a required comparator. Define those cases
before optimizing on them. Then consider a specific state reduction or faster
query method only if the remaining cost is material; merely rewriting standard
hull routines is not an originality argument. A knowledgeable external review
of the admission-only theorem and its closest prior formulations would be
needed before publication claims.

We have not supplied such a hard-case advantage or closed that originality
audit. This step therefore does not justify another collection campaign or
promote the current draft into a stronger-novelty paper. It narrows the next
question and prevents an unjustified speedup claim based on easy examples.

## Reproduction and preservation

Use the existing pinned Z3 requirements and an isolated Python environment.
From the repository root:

```bash
python3 -m unittest discover -s analysis -p test_finite_fifo_deadline_admission.py -v
python3 -m unittest discover -s analysis -p test_finite_fifo_deadline_shortcut.py -v
python3 analysis/finite_fifo_deadline_admission.py input.json --output new-result.json
python3 analysis/compare_finite_fifo_step3.py --prepare /tmp/new-step3-comparison
python3 analysis/compare_finite_fifo_step3.py --run /tmp/new-step3-comparison
python3 analysis/check_fifo_step3_shortcuts.py --run /tmp/new-step3-comparison
```

Output paths must be new. The
[sealed review report](../analysis/runtime_io_fifo_admission_step3/20261008-01/review_report.json)
records source snapshots, test provenance, all completed/incomplete outcomes,
post-pilot additions and preservation checks. Existing Step 1/2 code and seals,
the empirical v4 draft, the load-dependent assessment and all 1,911 protected
scientific files remain unchanged. No experiment, data collection, threshold
tuning on V28 or calibration refit was launched.
