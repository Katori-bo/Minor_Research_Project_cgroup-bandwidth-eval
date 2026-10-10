# Step 1: exact finite-FIFO deadline reference

8 October 2026. Offline implementation and model verification. No new service
measurement, scientific validation forecast, threshold tuning, or published
competitor reproduction. Existing drafts and V22–V28 evidence are preserved.

## Outcome and limits

The [reference solver](../analysis/finite_fifo_deadline_reference.py) now handles
general finite rational arrival traces and computes exact minimum and maximum
rejected-or-late fractions over a closed interval of one shared service time.
It returns every partition cell, separate rejected/late counts, exact failure
fractions, all cells attaining each extremum, and full replay witnesses.

The [independent checker](../analysis/finite_fifo_deadline_symbolic_check.py)
branches directly on reachable admission and deadline decisions. It shares only
the input type/validation and budget exception with the reference. It imports
neither its fixed-parameter simulator nor its global breakpoint generator. It
is a small standard symbolic-analysis implementation, **not an SMT baseline**
and not a reproduction of a published tool.

This completes the reference-implementation milestone. Correctness is supported
by the argument below and differential checks; it is not a machine-checked
formal proof or an independently reviewed theorem. Novelty and an efficiency
advantage remain unestablished. This is a baseline to improve or compare, not
the claimed new algorithm for a paper.

## Exact contract

There are N > 0 offers at fixed timestamps `a_0 <= ... <= a_(N-1)`. Timestamps
are nonnegative rationals, with equal-time offers processed in input order. A
single initially empty, work-conserving server executes identical jobs with
one shared constant service time `s` in `[L,H]`, where `0 < L <= H`. Every
offer has the same relative deadline `D >= 0`.

The system holds at most B > 0 jobs **including the running job**. At an
arrival instant, completions at or before that instant first release their
positions. Reject the new offer if all B positions remain occupied; otherwise
admit it in FIFO order. Rejection consumes no service. Admitted jobs continue
to completion after missing their deadlines; there is no abandonment,
cancellation, eviction, retry, or preemption. Completion at `a_i+D` is timely.
Completions after the final arrival are included.

For each admitted offer, its completion is

```text
c_i(s) = max(a_i, completion_of_previous_admitted_offer(s)) + s.
```

Rejected offers do not replace the previous admitted completion. The objective
is `F(s) = (rejected(s) + late(s))/N`, using the same offered denominator N
at every parameter value. An admitted late offer is counted once. A rejected
offer is counted once and has no completion time. The requested extrema are
`min F(s)` and `max F(s)` over the entire real interval `[L,H]`.

All supplied times use one declared unit. Integer values and exact strings
such as `"0.95"` or `"19/20"` are accepted. Python Fractions are also accepted
by the API. Floats and Boolean values are refused to prevent a rounded input
from silently shifting an equality boundary. `time_unit` is a label; the
program performs no unit conversion.

## Correctness argument

**Lemma 1: affine completions on a fixed execution branch.** For any admitted
offer i, its completion on that branch has the form `a_j + k*s`, where j is an
offer that started its current busy period, `j <= i`, and
`1 <= k <= i-j+1`.

Initially, the first admitted offer completes at its arrival plus s. If the
next admitted offer arrives after the previous admitted completion, it starts
a new busy period and has the form `a_i+s`. Otherwise it completes one service
time after that previous completion, increasing k by one. Rejections neither
advance completion nor increase k. There can be no more admitted jobs than
offers between j and i. This proves the stated form by induction.

**Lemma 2: all decision changes lie in a finite candidate set.** A completion
can change its ordering relative to arrival i only at
`s = (a_i-a_j)/k`. An admitted completion can change its deadline classification
only at `s = (a_i+D-a_j)/k`. The idle/busy choice in the recurrence uses the
same completion-versus-arrival comparisons. Occupancy and admission depend
only on which admitted completions have departed and the fixed capacity B.

Generate both root families for every `0 <= j <= i < N` and
`1 <= k <= i-j+1`; retain values in `[L,H]` and add L and H. The set is a
conservative superset of actual decision boundaries: many generated forms
never occur on an execution. Duplicate values are removed exactly.

**Lemma 3: outcomes are constant inside each open cell.** Sort the candidate
set. Between two adjacent candidates, no possible comparison root exists.
Induct on offers. Previous admission decisions and completion expressions are
fixed on the cell by the induction hypothesis. Their ordering relative to the
current arrival cannot change inside it. Therefore the departed jobs, queue
occupancy, admission decision, and resulting completion expression are fixed
on that cell. Its timely/late classification cannot change either, because all
possible deadline roots were included. This establishes a constant admission
pattern and constant rejected/late counts throughout each open cell.

**Theorem: partition replay yields exact extrema.** Partition `[L,H]` into a
singleton for every candidate and an open interval between every adjacent
pair. These cells are disjoint, nonempty and cover the whole closed interval.
Replay each singleton exactly, applying the stated equality conventions.
Replay each open cell at its rational midpoint; Lemma 3 makes its counts valid
for every real parameter in that cell, including irrational values. Taking the
smallest and largest cell counts gives the exact extrema. Each extremum has a
concrete rational witness. A zero-width service interval has one singleton.

Evaluating only open cells would discard equality cases. Evaluating only the
two interval endpoints would discard interior admission changes. A numerical
grid supplies neither completeness guarantee.

**Independent checker's argument.** Its state stores a service-time interval,
affine pending completions, and accumulated rejected/late counts. Each linear
comparison splits that interval into the portions satisfying `<=` and `>`;
these are disjoint and cover the original interval. A departure removes the
first pending completion; a full queue rejects the offer; otherwise the new
completion is derived from the last pending completion or from the current
arrival if empty. Deadline splitting then counts the accepted job once without
removing it. Induction on these transitions preserves the exact deterministic
execution and covers every valuation. There are finitely many offers and
decisions, so exhaustive branching terminates in principle. Operational limits
can refuse the run instead of returning incomplete bounds.

## Complexity and resource refusal

The number of generated root expressions, before filtering and deduplication,
is exactly `N*(N+1)*(N+2)/3`. Thus there are at most O(N³) candidate values and
cells. A fixed-parameter replay uses O(N) queue operations, so full analysis
uses O(N⁴) arithmetic operations, with candidate sorting contributing
O(N³ log N). Rational-arithmetic bit costs are excluded from those counts.

The reference stores O(N³) candidates/cell summaries and O(N) witness records;
it does not store an N-offer trace for every cell. It intentionally retains
irrelevant boundaries and does not merge adjacent equal-outcome cells. These
are reference properties, not claims that every trace requires that much work.

Default resource limits are 100,000 root expressions, 20,000 fixed-parameter
replays, and 200,000 offer evaluations, including two full witness replays.
Expression counts are checked before generation; replay budgets are checked
before cell evaluation. Exceeding a limit raises `BudgetExceeded` and produces
no extrema. Python callers can explicitly supply different positive limits.
The CLI uses the defaults. These are operation-count limits, not a hard
wall-clock timeout or memory guarantee for arbitrarily large rational inputs.

The tiny symbolic checker additionally caps live states and transitions.
Neither implementation has been established as suitable for the thousands of
offers in our service trials. Default budget refusal is not a mathematical
counterexample or a negative research result.

## Verification completed

The new [test suite](../analysis/test_finite_fifo_deadline_reference.py) passed
all **14 tests**. It includes:

- 672 exhaustive small problems: all ordered traces of 1–4 arrivals from
  `{0,1,2,3}`, every capacity from 1 to N, and deadlines 0, 1/2 and 1 over
  service interval `[1/4,3/2]`.
- 200 reproducible rational problems with 1–8 offers, varied capacities,
  deadlines, rational denominators and service intervals, including singletons.
- Nine directed reference/checker comparisons covering both counterexamples,
  completion/arrival and deadline equality, singleton-only extrema, continued
  late execution, terminal drain, zero deadlines, unit/origin invariance and
  rejection-free monotonicity.
- Input refusal, exact fractions and witnesses, resource-limit refusal,
  CLI output and refusal to overwrite an existing output file.

For each of the 881 compared problems, tests form the union of both solvers'
partition boundaries. They check every boundary and three rational points in
each resulting open interval. Both partitions must assign each checked value
to exactly one cell, and rejected/late counts must agree. This checks for a
symbolic boundary missing from the reference rather than sampling only the
reference's midpoints. It does not replace the whole-interval proof above.

The historical four-offer example has exact failure range **0–75%** over
service interval `[0.5,1]`; its endpoints give only **0–50%**. The user's
review example has exact range **50–75%** over `[1,1.2]`; both endpoints give
75%. Both examples are synthetic mathematics, not service measurements.

The [packaged results](../analysis/runtime_io_fifo_reference/20261008-01/review_report.json)
record verification provenance, examples, preserved evidence checks and hashes.
Synthetic test problems are not statistical validation trials, and their
counts are not real-world coverage evidence.

## Usage

Save a JSON input with exact times, for example:

```json
{
  "arrivals": ["0", "0", "0.95", "1.95"],
  "system_slots": 2,
  "relative_deadline": "1.1",
  "service_interval": ["0.5", "1"],
  "time_unit": "seconds"
}
```

From the repository root, run:

```bash
python3 analysis/finite_fifo_deadline_reference.py input.json --output new-result.json
python3 -m unittest discover -s analysis -p test_finite_fifo_deadline_reference.py -v
```

The output path must be new; omitting `--output` prints JSON. No third-party
dependencies are needed. In Python, construct `Problem(...)` and call `solve`;
`replay` supplies fixed-parameter checks and `Limits` controls refusal budgets.

## What remains before pursuing novelty

The next method gate is a faithful independent SMT encoding and a justified
comparison with relevant prior symbolic procedures, followed by an explicit
algorithmic improvement if one is found. We have not supplied that baseline,
proved an improvement, benchmarked large traces, closed the citation audit, or
established novelty. Merely rewriting the symbolic checker as a fast solver
does not establish originality.

One common s is essential to the stated polynomial partition argument. This
milestone does not cover independently uncertain per-job service times,
periodic CPU supply, multiserver execution, abandonment, mixed job costs or
stochastic arrivals. Exact answers within this model do not certify the real
Linux service. Collection remains stopped.
