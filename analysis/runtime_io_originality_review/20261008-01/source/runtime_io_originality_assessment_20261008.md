# Originality assessment before further experiments

8 October 2026. Focused primary-source screen after V22–V28 and retrospective
diagnostic development. This is a research decision record, not a systematic
review or a certification of originality. No new scientific collection,
published-method reproduction, or validation refit was performed.

## Decision

**Keep the experimental gate closed. The generic diagnostic is not yet a
defensible stronger contribution. One narrower algorithmic candidate merits
an offline feasibility check, with substantial prior-art risk.**

The broader ideas—load-dependent demand, selecting estimators, tuning monitoring
windows, measuring transient service, propagating parameter uncertainty, and
using prediction uncertainty for deadlines—already have clear precedents.
Success in a fresh guard experiment would establish usefulness in the tested
setting; it would not by itself resolve originality.

The best candidate found in this screen is **efficient, sound bounds on the
all-offer deadline-miss fraction across uncertain service capacity when a
finite FIFO queue can reject requests**. This closes an explicit limitation of
our prototype. Its potential contribution must be an additional algorithm,
theorem, or demonstrated efficiency/precision advantage over existing methods.
The counterexample below, a new metric name, or a Linux application alone does
not meet that requirement. No candidate has confirmed novelty at this point.

## What the closest methods already cover

The distinctions in the final column describe the passages reviewed. They do
not prove that the authors' methods cannot be extended to our problem. The
[source ledger](../analysis/runtime_io_originality_review/20261008-01/sources.json)
records access limitations, exact sections and next comparisons.

| Source and reviewed scope | Established overlap | Remaining question and implication |
|---|---|---|
| [Kumar et al., Enhanced Inferencing, VALUETOOLS 2009](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799), §§2–3 | Workload-dependent demand and overhead fitted jointly from utilization and mean-response observations. | Our CPU-only quadratic benchmark does not reproduce this inference. Rediscovering load dependence is not a contribution. |
| [Zhang et al., 2013](https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639), load-dependent estimation, Eqs. 1–5; retained prior assessment | Polynomial demand in utilization, utilization-law constraints and soft mean-response bounds. | Exact image coefficients remain incompletely verified. Applicability needs declared units and scheduling assumptions, not a claim of published-method failure. |
| [Grohmann et al., SARDE, 2021](https://doi.org/10.1145/3463369), author preprint §§5.2–5.3, 6.3, 9.1 | Continuous estimator tuning/selection, including measurement-window and aggregation-interval tuning. Internal validation combines utilization error with MVA mean-response error. | A deadline-fraction decision differs from that evaluated objective. Replacing its loss function alone would be a weak originality claim; its selection framework is a serious conceptual baseline. |
| [Becker and Fidler, 2015](https://arxiv.org/html/1506.04657), §§II–III, especially III-D | Non-stationary service curves, transient delay/backlog bounds, and two-phase minimal probing with an accuracy assessment. | “Choose a suitable timescale” or “use minimal probing” is already covered. Any extension must address a specific broken assumption, such as loss-dependent admission or load-dependent service, and beat a justified adaptation. |
| [Lopatatzidis et al., Robust queueing theory, 2016](https://users.ugent.be/~jdbock/documents/SL-2016-QUES-paper.pdf), abstract/introduction and model description | Finite-capacity, discrete-time queue predictions under imprecise arrival/departure probabilities. | Their probabilistic queue differs from our fixed finite offer trace, but bounding uncertain queue performance is established. |
| [van Dijk and Miyazawa, 2004](https://www.rs.tus.ac.jp/miyazawa/pdf-file/EB-NESQ.pdf), abstract/introduction | Perturbation error bounds for nonexponential finite/infinite-buffer queues, including throughput and stationary queue measures. | A finite-trace deadline-fraction algorithm has a different output. That distinction does not make uncertainty propagation original. |
| [Matoušek, Smrčka and Vojnar, 2005](https://dl.ifip.org/db/conf/charme/charme2005/MatousekSV05.pdf), §§3–4 | Timed-automata models of lossy/delayed FIFO queues and parametric analysis involving queue size, request rate and reading time. | This is direct prior art against “the first parameter-aware finite-buffer analysis.” A specialized solver needs a concrete advantage over general symbolic verification. |
| [André, 2017](https://lipn.univ-paris13.fr/~andre/documents/a-unified-formalism-for-monoprocessor-schedulability-analysis-under-uncertainty.pdf), §§3–5 | Robust single-processor schedulability with uncertain timing parameters; scheduler/queue encoding and parameter synthesis using IMITATOR. | The presented safety analysis enters an error state on a miss/overflow. Counting all offered misses requires an observer extension; its simplicity may defeat a novelty claim. No solver comparison was run. |
| [MPORA, ECRTS 2026](https://drops.dagstuhl.de/storage/00lipics/lipics-vol375-ecrts2026/html/LIPIcs.ECRTS.2026.17/LIPIcs.ECRTS.2026.17.html), indexed primary abstract/introduction | Learned execution predictions, receding-horizon allocation and weighted conformal prediction for uncertainty-aware deadline constraints. | This blocks a broad claim that uncertainty-aware deadline decisions are new. It is a different execution/allocation model, not a tested competitor here. Full live fetches timed out in this screen. |
| [Sampat et al., Kscaler, 2025](https://tianyin.github.io/pub/kscaler.pdf), §§3–4 | Runtime/idle observations and joint quota/period autoscaling; explicitly identifies incorporating application SLOs as future work. | A possible systems direction is deadline-sensitive period choice at a fixed CPU budget. The paper's future-work item is not proof that the wider field has left it unsolved. |
| [Wang et al., Autothrottle, NSDI 2024](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf), §§2–3 | SLO-targeted CPU allocation using application feedback and per-service throttle targets. | “SLO-aware CPU control” is already covered. A period-planning proposal must distinguish its controllable variables, foresight, budget and model, and compare fairly. |
| [Shin and Lee, RTSS 2003](https://pure.kaist.ac.kr/en/publications/periodic-resource-model-for-compositional-real-time-guarantees/), author institution abstract; [Cucinotta et al., TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), §4.2 | Periodic-resource timing guarantees and container reservation-based response analysis. | A quota ceiling is not a guaranteed reservation. Equal average CPU with different timing effects is not a new principle; transferring reservation bounds requires justified supply premises. |

Searches also covered deterministic finite-buffer deadline prediction,
nonmonotonic service-rate/deadline outcomes, and parametric timing synthesis.
These found relevant queue and formal-method precedents. No exact match in a
search result is insufficient evidence of an unoccupied research problem.
Forward/backward citation review and an implementation-level comparison remain
necessary for the shortlisted algorithmic claim.

## A concrete mathematical boundary

Our guard currently uses endpoint capacities only after proving that every
reference capacity admits the same offers. It abstains if that proof fails.
That restriction is necessary: counting rejection as failure does not restore
deadline monotonicity when faster service changes which jobs are admitted.

Consider an initially empty, single-server FIFO with two total positions,
identical constant service times, and offers at **0, 0, 0.95, 1.95 seconds**.
Every offer has a **1.1 second** relative deadline. A new offer is rejected
only when full; admitted late jobs continue to completion. Completion at the
deadline is timely; departures at an arrival instant are processed first.

| Capacity (jobs/s) | Completions by offer, seconds | Rejections | Timely offers | All-offer misses |
|---|---|---:|---:|---:|
| 1 | 1, 2, rejected, 3 | 1 | 2/4 | 50% |
| 10/9 | 0.9, 1.8, 2.7, 3.6 | 0 | 1/4 | 75% |
| 2 | 0.5, 1, 1.5, 2.45 | 0 | 4/4 | 0% |

Checking only capacities 1 and 2 yields a miss range of 0–50%. The interior
capacity 10/9 produces 75%. The faster server admits the third job; that late
job then delays the fourth. At the slower rate the third offer was rejected
and the fourth was timely. This is a synthetic counterexample to an inference
rule, not a measured phenomenon in our Linux service or a claimed discovery.
Deadline abandonment, eviction, another denominator, or a different admission
policy would define another problem.

The [exact rational check](../analysis/runtime_io_originality_review/20261008-01/check_rejection_boundary.py)
matches independently written completion traces and the existing FIFO
simulator. It also enumerates every possible critical service time for this
four-offer example, including the boundary points, recovering the full
model-family miss range **0–75%**. Results are in the
[report](../analysis/runtime_io_originality_review/20261008-01/rejection_boundary_report.json).

There is already a straightforward exact reference construction. For N fixed
offers and one common service time s, any admitted completion has the form
`arrival_j + k*s`, with `1 <= k <= N`. Admission, idle/busy and deadline
comparisons change only at

```text
s = (arrival_i - arrival_j)/k
s = (arrival_i + deadline - arrival_j)/k.
```

Enumerate the values in the allowed service interval; replay at each value and
once inside every intervening open interval. Induction on offers shows that
the admission pattern and deadline labels stay constant in each open interval.
Point cells preserve equality conventions. There are at most O(N³) candidate
values and O(N⁴) replay work, excluding rational-arithmetic bit costs. This is
a proof sketch for a basic reference procedure, not an efficient new solver.
It also shows why a grid may miss a narrow bad region. No large-trace benchmark
was run, and the four-offer calculation is not evidence of scalability.

The constant-rate family is an idealized model. Periodic quota stalls,
load-dependent job cost and network/runtime delay can violate its premises.
Even exact optimization over this family cannot certify a real forecast unless
the learned family and separately assessed discrepancy have justified coverage.
This is the second unresolved problem, after solver originality.

## Candidate ranking and conditions for a stronger paper

| Candidate | Specific possible addition | Present verdict |
|---|---|---|
| 1. Efficient finite-FIFO uncertainty bounds through rejection | Exact or provably sound all-offer deadline-fraction bounds over a continuous capacity interval, with witnesses for interior extrema, at practical trace lengths. | Best inexpensive offline lead. The problem is concrete; novelty is unconfirmed and general symbolic methods are strong prior art. |
| 2. Deadline-sensitive quota-period planning at fixed CPU budget | Choose a period for a known burst schedule and deadline objective without simply increasing CPU allocation; quantify when period changes suffice. | Conditional systems pivot. Kscaler supplies an explicit motivation, but resource timing and SLO control already exist. Requires further method audit and eventually new measurements. |
| 3. Separate job-cost changes from CPU-delivery changes | A valid identification procedure that distinguishes mechanisms producing similar aggregate CPU/job observations. | Potentially stronger explanation, but no identified mechanism or new identification method. Expensive causal work; do not start it based on current correlations. |
| Generic guard, conformal wrapper, new workload, another regression | Selection or validation of known machinery in another setting. | Useful research activity but insufficient by itself for the stronger method contribution requested. |

For candidate 1 the provisional claim, **only if achieved**, would be:

> We provide a sound, computationally practical method for bounding all-offer
> deadline loss under service uncertainty in a rejecting finite FIFO, accounting
> for interior admission changes that endpoint forecasts can miss.

This wording describes a target; it must not be added as an achieved result to
the current draft. To make it original, identify the actual extra theorem,
algorithm or quantified advantage relative to an equivalent prior formulation.
“No paper uses our exact combination of words” is not such an advantage.

## The next gate is offline, not another campaign

1. Write the same finite-horizon, tail-drop, no-abandonment problem in the closest
   parametric framework, including an all-offer miss-count observer. Inspect
   its algorithm/artifact and citation neighborhood. If an existing method
   already gives our desired result at practical cost, stop this novelty route
   unless a specific additional contribution is identified.
2. Specify a candidate solver and its correctness/complexity difference from
   the critical-point reference and the equivalent general method. Test ties,
   rejection, interior extrema and narrow parameter cells with exact synthetic
   checks. Do not tune a third diagnostic threshold on V28.
3. Use short, predetermined offline traces to assess practicality before trying
   full trace lengths. Stop on uncontrolled state growth. Model-family bounds
   must be separated from how capacity and model discrepancy are learned:
   an empirical calibration min/max is still not a future coverage guarantee.
4. Open the experimental gate only if a precise originality argument and a
   useful computational result survive. Then freeze independent calibration,
   comparators, error/coverage objectives and a bounded fresh validation design.

Always-busy calibration remains a required practical comparator for any final
guard. Its V28 forecasts were already accurate, while the timing-envelope
prototype accepted only four of sixteen forecasts and unnecessarily flagged
twelve accurate busy predictions. Adding a solver cannot erase that cost or
establish useful real-world coverage. Existing-data development remains
retrospective; it cannot become fresh validation.

The current empirical draft remains a valid record of its scoped findings.
This review does not strengthen its existing estimator novelty claim. It
changes the next step: examine a precise algorithmic gap cheaply, and decline
another collection campaign until that gap is defensible. Historical drafts,
V22–V28 outcomes, both inconclusive screens and evidence seals are unchanged.
