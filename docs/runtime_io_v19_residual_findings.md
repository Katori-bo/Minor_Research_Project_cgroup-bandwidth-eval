# V19 residual delay: offline review

2026-10-05. Independent V19 completion verification passed before this analysis.
No new benchmark, Docker action or instrumentation was used. The original
discovery verdict remains `useful_worker_control_without_gap_signal`; the
post-computation screen was not relaxed. These additional analyses are exploratory.

## Where the latency change occurs

Means across the six trials per arm; the four-worker column averages both
identical controls. All 6,793 offers in every trial were successful, so these
stage populations do not omit client failures.

| Mean interval, ms | Four workers | One worker |
|---|---:|---:|
| Scheduled offer to handler entry, upper clock bound | 87.24 | 19.64 |
| Admission to computation start | 150.19 | 215.54 |
| Main computation wall time | 19.24 | 6.07 |
| Computation completion to handler resume | 38.91 | 17.30 |
| End-to-end client latency | 295.74 | 258.65 |

Queue wait grows with one worker. Its increase largely offsets the reduction
before handler entry. Most of the net latency reduction lies in computation wall
time and completion-to-resume. These are descriptive stage distributions, not
individual causal recovery estimates. The offer-to-entry column is a clock upper
bound; do not sum clock upper bounds as exact durations.

## A publication upper bound from existing program order

The exact retained build has one worker loop which calls `runJob` and then takes
the next job. `runJob` records completion and then sends the result on the
request's buffered reply channel before returning. With exactly one worker,
starting its next job therefore proves that the preceding reply send has already
returned. The next start timestamp is an upper bound on previous result
publication. It is not an observed publication timestamp.

The review checks the prepared source hash against the original build manifest,
the original image identity against V19 preparation, conserved request/job
records, single-worker nonoverlapping computation intervals, and the saved client
clock bounds. It applies the inference only to one-worker trials.

All **1,182** computation-before/handler-after 500 ms crossings in those trials
have a subsequent worker start certainly before the deadline. Thus each result
was already available before 500 ms. Handler resume occurs substantially later:
the median of the six within-trial medians of the conservative
publication-to-resume lower bound is **54.32 ms**.

This excludes delayed publication as the whole explanation of this subset's
remaining wait. It does not establish when the handler became runnable, whether
CPU quota was available, an OS/Go runqueue location, or a scheduler defect.
Uninformative next-start bounds and final jobs remain unknown, not zero. Applying
this inference to interleaved four-worker jobs would be invalid.

The [sealed summary](../analysis/runtime_io_v19_residual_review/20261005/summary.json)
contains all trial and stage results. The
[per-request bounds](../analysis/runtime_io_v19_residual_review/20261005/publication_bounds.json)
retain supporting IDs and timestamps. The copied original prepared source and
replay script are sealed with them. Seven synthetic inference checks cover the
bound, deadline uncertainty, absent/uninformative bounds and invalid worker
sequences.

## Implication for the next experiment

The useful next question is why execution after an available result is delayed,
and whether temporal CPU supply and worker continuation contribute. Another
four-versus-one confirmation would establish reproducibility rather than answer
that question. The [V20 proposal](runtime_io_v20_execution_delay_plan.md) holds
worker count at one and tests the existing post-publication yield flag and one
shorter quota period as a small factorial mechanism probe.
