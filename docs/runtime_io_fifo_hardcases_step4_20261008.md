# Step 4: harder rejecting traces and contribution decision

8 October 2026. Offline synthetic analysis only. Collection stays stopped.

## Decision

**Step 4 is complete. The current solver does not pass the practical-advantage
gate, and a stronger novelty claim remains unsupported.** Both our admission
solver and the earlier reachable symbolic method solve all 24 harder cases
exactly. In the confirmation batch our solver is faster on seven cases and
slower on seventeen, with no twofold wins. Its largest median speed advantage
is about 1.31×. Fewer regions do not produce a convincing runtime improvement.

This is a decision about this prototype and this bounded comparison. It does
not prove that every possible theorem or algorithm for the problem is already
known. It does show that we should not promote this implementation as an
efficient new analyzer or restart service experiments on its strength.

My recommendation is to **shelve the current speedup angle** and retain the
proof, exact reference and counterexamples as research assets. A theoretical
contribution would need a knowledgeable review of the precise admission-only
result's originality and significance. A routine implementation optimization
or another favorable benchmark would not settle that question.

## Cases frozen before timing

The [new driver](../analysis/compare_finite_fifo_step4.py) preserves all earlier
solver files. Its [protocol](../analysis/runtime_io_fifo_hardcases_step4/20261008-01/protocol.json)
was written before selecting inputs. Three generators—jittered gaps,
clusters, and mixed gaps—are crossed with sizes 8, 16, 32 and 64 and two
configurations:

| Configuration | Total slots B | Relative deadline D | Shared service interval |
|---|---:|---:|---:|
| Small buffer | 2 | 5/4 | [9/20, 23/20] |
| Larger buffer | 5 | 21/10 | [11/20, 27/20] |

For each of the 24 strata, generate 50 seeded traces and select the first
whose existing shortcut returns `undetermined` and whose five probe replays
include at least one rejected offer. Neither exact extrema, symbolic region
counts nor solver timings influence selection. All 1,200 candidates and every
selection decision are retained in the
[selection log](../analysis/runtime_io_fifo_hardcases_step4/20261008-01/selection.json).
There are 1,060 eligible pool candidates; all strata supply a case.

This deliberately studies a subset where the shortcut cannot certify the
answer. It does not estimate how common those inputs are in real workloads.
The model retains all Step 1 event conventions and the single common constant
service parameter; it does not represent independent per-request uncertainty,
periodic CPU quota supply, cancellation or multiple servers.

## Frozen comparison and timing correction

Candidate, reachable and compact SMT receive three fresh-process repetitions
per case: 216 runs, in one predeclared shuffled order. Candidate permits 512
offers, 10,000 states and 50,000,000 charged terms. Reachable permits 10,000
states and 10,000,000 transitions. SMT permits 512 offers, 750 ms per check and
2,000 ms total checking. Every worker has a six-second hard timeout.

The engineering threshold was fixed before timing: no fewer candidate
completions than reachable, at least twofold median improvement on at least
two-thirds of the paired cases and at least half within each family, with at
least twelve paired cases. This is an exploratory decision threshold, not a
publication criterion or an originality test.

A verification unittest process overlapped part of the first timing batch.
That batch is retained rather than silently discarded. After those tests
finished, we repeated the complete frozen cases, order, methods and budgets
in a [confirmation package](../analysis/runtime_io_fifo_hardcases_step4/20261008-02-confirmation/comparison.json).
Its protocol, selection and design bytes are identical to the first batch.
No solver optimization, new selection or budget adjustment occurred. We use
the confirmation batch for the timing table below. The desktop host remains
uncontrolled, so this is still not publication-level performance evidence.

| Result per batch | Original | Confirmation |
|---|---:|---:|
| Candidate exact runs | 72/72 | 72/72 |
| Reachable exact runs | 72/72 | 72/72 |
| Compact SMT exact runs | 45/72 | 45/72 |
| Candidate faster paired cases | 6/24 | 7/24 |
| Candidate at least twice as fast | 0/24 | 0/24 |
| Practical gate | Failed | Failed |

Across both batches there are 432 runs, 378 exact completions and 54
incomplete SMT results. Every completed count agrees, within and across
batches, and every reported witness is independently queue-verified. SMT
unknown/time results reflect these budgets; they do not prove that SMT or the
published formal methods cannot solve the cases.

Timings include method execution, result construction and witnesses, excluding
imports, startup, JSON and independent witness replay. Outputs differ:
candidate returns admission-region extrema, reachable returns constant-outcome
cells, and SMT returns global extrema with witnesses. Reported worker RSS
includes imports and verification; no solver-memory claim is made.

## Harder cases still favor the adequate comparator

The 64-offer confirmation medians show the result directly:

| Family / buffer | Candidate ms / regions | Reachable ms / cells |
|---|---:|---:|
| Jittered / small | 281.80 / 669 | 154.43 / 942 |
| Jittered / larger | 211.44 / 689 | 105.85 / 721 |
| Clustered / small | 16.07 / 26 | 8.85 / 39 |
| Clustered / larger | 158.40 / 465 | 122.47 / 769 |
| Mixed gaps / small | 42.34 / 57 | 22.04 / 91 |
| Mixed gaps / larger | 91.43 / 270 | 119.67 / 607 |

Candidate uses fewer regions in all 24 paired cases, but the reachable method
is faster on five of these six larger cases. Even rejecting traces beyond
the shortcut's certificates do not establish a useful general speedup.
Defeating our budgeted SMT encoding alone would miss the stronger comparator.

## Exact analysis does matter; that is not the novelty claim

The five-point probe misses a true extremum on four selected cases: two
minima and two maxima. On the other twenty cases its sample extrema happen
to match, but the shortcut still cannot certify them from its independent
global bounds. An unresolved certificate is not an incorrect result.

For `mixed_gaps_16_small_buffer`, the probe finds a maximum of 13 failures.
Exact analysis finds 14, attained at service time **16/15**, inside the
interval. For `clustered_16_larger_buffer`, the probe finds a minimum of four
failures, while the exact minimum is three, attained at **89/160**.
Both examples are checked by complete breakpoint enumeration in addition to
the two symbolic solvers. Their full inputs, exact partitions, candidate
regions and shortcut results are retained in the
[example package](../analysis/runtime_io_fifo_hardcases_step4/20261008-01/examples/missed_maximum_reference.json).

These examples demonstrate why a grid is not a complete algorithm. They do
not establish that handling continuous uncertainty is new: the reachable
method already solves these cases exactly.

## Focused originality assessment

The [source ledger](../analysis/runtime_io_fifo_hardcases_step4/20261008-01/sources.json)
records primary texts, inspected passages, access limits and the specific
remaining question. We followed selected relevant reference/extension links;
this is not a complete backward/forward citation audit through the scope date.
No published analyzer has been reproduced or timed.

| Primary source | Existing result relevant to our claim | Difference still requiring assessment |
|---|---|---|
| [Bouakaz et al., 2017](https://doi.org/10.1145/3007898), author manuscript §§2, 4 | Symbolic performance formulas and enabling-pattern reasoning for parametric dataflow. | Its finite buffers constrain producer firing; our fixed offers are tail-dropped. Execution-pattern reduction itself is established. |
| [Nxumalo et al., 2021](https://doi.org/10.1007/978-3-030-84629-9_4), author manuscript §§4–6; [2023 extension](https://link.springer.com/article/10.1007/s10009-022-00693-9), abstract/preview | FIFO/EDF queue abstraction and iterative timed-automata schedulability; extension separates clock operations and uses counter abstraction. | All-task schedulability differs from exact finite-trace combined loss/late extrema; general FIFO state reduction is already known. |
| [Gupta, 2023](https://pure.tudelft.nl/ws/portalfiles/portal/141947587/TU_dissertation_Gupta.pdf), selected §§2.4, 3.4 and Chapter 5 | Piecewise-affine theory, choice-dependent max-plus hybrid models and parametric event-time systems. | A ready-made algorithm for our objective was not identified in these passages. Broad max-plus/parameter modelling claims are unavailable. |
| [Mufid et al., 2022](https://www.cs.ox.ac.uk/people/alessandro.abate/publications/MAA22.pdf), abstract and model | Interval max-plus uncertainty and SMT reachability in linear real arithmetic. | Event-varying matrix uncertainty differs from our persistent shared service parameter and tail-drop admission. Our Z3 baseline is not their reproduced method. |
| [Espindola-Winck et al., 2025](https://perso-laris.univ-angers.fr/~hardouin/JDEDS_2025_SMTvsMaxplus.pdf), introduction and conclusion | Concise fixed-point max-plus computation compared with disjunctive SMT for uncertain state estimation. | Its measurement-compatible state estimates differ from our global combined failure counts; replacing disjunctions by specialized algebra is not a new general idea. |

The earlier Step 3 assessments of max-plus FIFO recurrence, hull pacing,
timing observers, quantitative automata, lossy FIFO verification and
parametric schedulability remain relevant and unchanged.

The only narrowly plausible candidate remains **exact admission-only
partitioning for finite FIFO all-offer loss/deadline extrema, using conditional
monotonicity to avoid deadline and idle splits**. We have a derivation and
correct implementation. We do not have an improved worst-case bound,
convincing practical advantage, verified firstness or an independently
reviewed originality argument. No exact published match identified in selected
passages is not evidence of absence.

Thus the efficiency route fails this gate; the narrow theorem's originality
remains unresolved. Adding the solver to the empirical paper also requires a
validated connection between the service-interval model and the measured
runtime system. That connection has not been supplied by this offline work.

## Verification, preservation and reproduction

The [audit](../analysis/runtime_io_fifo_hardcases_step4/20261008-01/audit.json)
regenerates all 1,200 pool inputs, checks shortcut/rejection selection and
first-eligible decisions, source hashes, identical frozen designs and all
432 logged jobs. All six selected eight-offer cases agree with complete
breakpoint reference analysis; the two additional sixteen-offer examples
agree too. The existing eight admission tests and two shortcut tests pass.

All 1,911 protected scientific files, the v4 draft and load-dependent
assessment, the twelve Step 3 source files and all five earlier evidence
seals verify unchanged. New evidence packages are sealed separately. No
scientific experiment, workload collection or calibration refit was launched.

From the repository root, using an isolated environment with the pinned Z3
requirements, reproduce to a new directory:

```bash
python3 analysis/compare_finite_fifo_step4.py --prepare /tmp/new-fifo-step4
python3 analysis/compare_finite_fifo_step4.py --run /tmp/new-fifo-step4
```

The driver refuses existing output files and verifies frozen solver hashes
before timing. Read the report together with the raw runs; retain incomplete
results and the declared selection scope when interpreting performance.
