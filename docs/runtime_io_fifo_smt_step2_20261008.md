# Step 2: independent SMT baseline and bounded offline comparison

8 October 2026. Synthetic algorithm verification only. No service experiment
or scientific collection was launched. Existing paper drafts and sealed evidence
are preserved.

## Outcome

The [SMT baseline](../analysis/finite_fifo_deadline_smt.py) independently computes
the exact minimum and maximum rejected-plus-late counts under the Step 1 model.
It supplies exact rational service-time witnesses, each offer's admission and
completion outcome, and UNSAT checks excluding a strictly better extremum.
It uses pinned Z3 4.15.4.0; it is **our generic encoding**, not a reproduction
of a published timed-automata or scheduling algorithm.

All 203 synthetic cross-method problems passed. A fixed 16-case comparison
found matching extrema in every completed run. The reachable symbolic checker
was faster than the conservative reference on all these cases and faster than
this SMT baseline wherever both completed. It also produced fewer cells than
the reference on all these cases. These are bounded observations, not a
general performance guarantee.

**Step 2 is complete. Novelty is not established.** This supports investigating
an efficient specialized exact analyzer, but standard symbolic branching is
already prior methodology. Faster execution than this one encoding does not
establish a new algorithm or superiority over the literature.

## Model and independent encoding

The model is exactly the [Step 1 contract](runtime_io_fifo_reference_step1_20261008.md):
a known finite rational arrival trace; one initially empty work-conserving FIFO
server; B positions including the executing offer; deterministic tail-drop;
one common service time `s` anywhere in the closed real interval `[L,H]`;
one relative deadline D. Equal-time offers use input order. Completion at
arrival releases capacity before admission; completion at the deadline is
timely. Late jobs stay until completion. The denominator is every offered
request, including rejected requests.

Let `A_i` denote admission, `C_i` completion, and `R_i` the last admitted
completion through offer i. Rejected offers have sentinel `C_i = 0`; the
sentinel is always guarded by `A_i`. Put `R_-1 = 0` and encode:

```text
O_i = sum over j<i of If(A_j and C_j > a_i, 1, 0)
A_i <=> O_i < B
C_i = If(A_i, max(a_i, R_(i-1)) + s, 0)
R_i = If(A_i, C_i, R_(i-1))
late_i <=> A_i and C_i > a_i + D
K = sum over i of If(not A_i or late_i, 1, 0)
L <= s <= H
```

The implementation writes `max` with a conditional. All timing constraints
are linear; Booleans select branches, and integer indicator sums count jobs.
There are `N*(N-1)/2` occupancy terms and O(N) other row constraints. This is
an encoding-size bound, not a polynomial solver-runtime bound. The baseline
imports only validated `Problem` and the refusal exception from the reference;
it imports neither its simulation nor its breakpoint generator. In particular,
it does not use reference outcomes to initialize or accelerate optimization.

Binary search asks whether `K <= k` is feasible for the minimum, and whether
`K >= k` is feasible for the maximum. These threshold predicates are monotone
in k even when failures are nonmonotone in s. A feasible optimum has a rational
witness. Separate checks of `K < minimum` and `K > maximum` must be UNSAT.
Solver results `unknown`, including timeouts, cause refusal and return no
certified extrema. They never become UNSAT or an approximate exact answer.

The solver API and rational representation follow the primary
[Z3Py guide](https://ericpony.github.io/z3py-tutorial/guide-examples.htm).
The guide establishes tool capabilities, not originality of this queue model.

## Correctness argument

Fix any real s in `[L,H]`. Induct on the ordered offers. Initially the system
is empty and its last completion is zero. A previously admitted job occupies
a position exactly when its completion exceeds the current arrival. Thus
`O_i` is precisely the number of occupied positions after equal-time
departures; the admission equivalence gives exactly the queue policy.

An admitted job starts at the later of its arrival and the previous admitted
completion, so the encoded `C_i` is its FIFO completion. Rejection leaves
`R_i` unchanged, and no deadline condition removes a job from occupancy.
Consequently the induction continues with the exact execution history.
The late predicate uses strict deadline comparison and the failure indicator
counts each rejected or admitted-late offer once. Summing gives the intended
all-offer count K, including terminal completions after the last arrival.

Conversely the recurrence constructs a satisfying assignment for every
allowed service time. The encoding therefore admits precisely the queue
executions under this model. Searching bounded integer counts, obtaining an
attaining assignment, and excluding every strict improvement establishes the
extrema over the whole real interval. This argument is not a machine-checked
proof. The recorded UNSAT results trust Z3; no independently checked proof
objects are supplied.

## Verification

The [new suite](../analysis/test_finite_fifo_deadline_smt.py) passed all six
tests in 8.056 seconds. It compares:

- 90 exhaustive problems: sorted traces of 1–3 offers on `{0,1,2}`, every
  capacity 1 through N, deadlines 0 and 1, and service interval `[1/4,3/2]`.
- 100 seeded rational problems with 1–8 offers, varied capacities, exact
  timing fractions and singleton intervals; seed `810202602`.
- 12 directed cases: both interior counterexamples, singleton-only extrema,
  equal-time departures/admission, deadline equality, rejections not consuming
  service, continued late execution, terminal drain and small rational units.
- One additional scaled/shifted problem checking time-unit and origin invariance.

For each problem, both extrema agree with the reference and the complete SMT
witness offer list matches independent exact replay. For all cells in 12
directed and 20 seeded problems, further SMT queries establish that each cell
is feasible and that **no real service-time value in it** can disagree with
the reference's rejected/late counts. This is stronger than checking only
sampled values, while still depending on the correctness of both encodings.

The suite additionally verifies resource/unknown refusal, export and reload
of SMT-LIB constraints, CLI results and refusal to overwrite existing files.
It does not reproduce a published competitor. The Step 1 tests and sealed
sources remain unchanged.

The packaged examples independently recover exact ranges 0–75% for the
interior-maximum example, 50–75% for the interior-minimum example and 0–50%
for the boundary-only minimum. Inputs, witnesses and base SMT-LIB encodings
are in the [examples directory](../analysis/runtime_io_fifo_smt_baseline/20261008-01/examples).

## Bounded runtime comparison

The [comparison driver](../analysis/compare_finite_fifo_solvers.py) wrote its
[design](../analysis/runtime_io_fifo_smt_baseline/20261008-01/design.json)
before any timed comparison. Four synthetic trace families—regular arrivals,
four-offer bursts, seeded irregular rational gaps and repeated interior
counterexamples—each have sizes 4, 8, 16 and 32. Every case/method pair runs
three times, in a fixed shuffled order, serially in fresh processes: 144 runs.

The methods are the conservative Step 1 breakpoint reference, its reachable
symbolic checker, and the independent SMT baseline. The timed call includes
encoding/analysis and witness extraction where supplied; imports, process
startup, JSON serialization and subsequent witness replay are excluded.
The outputs differ: the reference returns a conservative partition and
witnesses; the checker returns its reachable partition; SMT returns extrema
and witnesses. This is useful for choosing a method, not a comparison of
identical output workloads. CPU times and absolute fresh-worker peak RSS are
also retained. RSS includes imports and post-timing verification, so it does
not isolate solver memory.

For this bounded pilot only, SMT has a 500 ms limit per check and a 2,000 ms
total check budget; workers have a six-second hard limit. The other methods
use their existing operation budgets. Of 144 runs, 138 completed exactly and
six SMT runs were incomplete. All completed extrema agree, and every reported
extremum witness is replay-verified. No worker hit the hard timeout.

The 32-offer cases illustrate the difference. Times below are median method
milliseconds over three completed runs; the SMT incomplete entries have no
completed median.

| Trace | Reference time / cells | Reachable time / cells | SMT time |
|---|---:|---:|---:|
| Regular | 66.29 ms / 497 | 17.60 ms / 196 | Incomplete at 500 ms/check |
| Bursts | 45.02 ms / 273 | 2.14 ms / 12 | 1,034.14 ms |
| Irregular | 343.84 ms / 4,095 | 31.12 ms / 287 | Incomplete at 500 ms/check |
| Repeated interior | 39.29 ms / 183 | 1.95 ms / 7 | 1,436.87 ms |

The [raw runs and summary](../analysis/runtime_io_fifo_smt_baseline/20261008-01/comparison.json)
retain results and all limitations. Timings are from an uncontrolled desktop
host, with small synthetic inputs and only three repeats; they support no
publication-level statistical performance claim. Peak memory is not used as
evidence of a memory advantage.

### Time-limit sensitivity

The two incomplete cases were subsequently checked once each with the default
2,000 ms/check, 10,000 ms total budget, then once each with 5,000 ms/check,
30,000 ms total. This is a separately declared post-pilot diagnostic, not
replacement runs in the frozen comparison. The
[sensitivity driver](../analysis/check_finite_fifo_smt_time_limits.py) and
[results](../analysis/runtime_io_fifo_smt_baseline/20261008-01/sensitivity.json)
are retained.

**Both cases completed exactly under both larger budgets.** Under the default
limits regular arrivals took 1.760 seconds and irregular arrivals took 2.362
seconds; their bounds and witnesses agree with the reference. The pilot's
incompleteness reflects its time limit, not an inability of SMT to solve these
32-offer models. We have not demonstrated a solver scalability barrier.

## Novelty decision and the next gate

The evidence supports a modest practical observation: exploring only reachable
decision regions can avoid much unnecessary conservative partitioning and can
outperform this generic SMT encoding on the supplied traces. The reachable
checker already does this through ordinary symbolic branching. Treat it as
another baseline, not as a newly discovered principle.

A stronger paper would require an explicit contribution beyond those baselines.
The next offline gate should identify and justify a concrete FIFO-specific
reduction, incremental calculation or provable structural bound, then test it
against **both** the existing reachable method and improved relevant generic
encodings at larger predeclared sizes. Comparison only against the deliberately
conservative reference would be insufficient. Any proposed reduction must
preserve equality points, all-offer counting and admission-dependent interior
extrema. A forward-citation and closest-method audit must still establish
whether that particular reduction is already published.

Continue only if a specific improvement survives that comparison, or a new
structural theorem itself supplies a defensible contribution. No new runtime
collection is needed for this gate. Large trace scalability, independent
workloads, calibration uncertainty coverage, CPU quota behavior and a closed
originality audit remain unestablished. The common constant service-time model
does not cover independently varying job costs or periodic CPU supply.

## Reproduction and preserved evidence

The dependency is pinned in
[finite_fifo_smt_requirements.txt](../analysis/finite_fifo_smt_requirements.txt).
The executed interpreter is the bundled Python 3.12.14 inside a temporary
isolated environment `/tmp/fifo-step2-venv`; no scientific or global Python
environment was changed. That temporary environment is not a durable artifact.
Create a fresh environment and install the requirements when rerunning.

From the repository root, after activating that environment:

```bash
python3 -m pip install -r analysis/finite_fifo_smt_requirements.txt
python3 -m unittest discover -s analysis -p test_finite_fifo_deadline_smt.py -v
python3 analysis/finite_fifo_deadline_smt.py input.json --output new-result.json --smt2 new-model.smt2
python3 analysis/compare_finite_fifo_solvers.py --prepare /tmp/new-fifo-comparison
python3 analysis/compare_finite_fifo_solvers.py --run /tmp/new-fifo-comparison
python3 analysis/check_finite_fifo_smt_time_limits.py /tmp/new-fifo-comparison
```

Use new output paths; existing files are refused. The exported base SMT-LIB
file supplies constraints, not a standalone proof of the extrema: append the
recorded optimum attainment or strict-improvement assertion to reproduce the
corresponding query. Default solver limits cap query time only; they are not
hard bounds on encoding, rational input size or total CLI runtime. The
comparison runner additionally imposes a wall-clock worker limit.

The [sealed review package](../analysis/runtime_io_fifo_smt_baseline/20261008-01/review_report.json)
records sources, environment, test provenance and results. Hash verification
confirmed all 1,911 protected scientific files, the prior guard/originality/
Step 1 seals, the v4 draft and the load-dependent assessment are unchanged.
No experiment, calibration fit or data collection was launched.
