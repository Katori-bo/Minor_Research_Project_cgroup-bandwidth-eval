# V23 findings: work size and burst duration

Reviewed 2026-10-07. Generation-01 completed all four qualification, four
calibration and sixteen validation trials. Independent raw replay and
calibration-only forecast recomputation returned `primary_transfer_pass`.
All sixteen trial checks and eight paired-contrast checks passed their frozen
3 percentage point limit. Both work sizes passed separately.

## Why the terminal showed an interruption

The 90-minute watchdog interrupted the final independent verification inside
`analyze`, after the last trial had completed and after the analysis report had
been written and sealed. The last completed slot preceded the interruption by
39.537 seconds. The foreground process therefore left a traceback and a stale
`drain` progress status rather than printing the successful final message.

The retained session is still marked interrupted. A separate read-only
`verify-completion` invocation now exited successfully, verifying the saved
report against raw data and recomputing predictions from calibration only.
No measurement was repeated, no bound extended and no frozen source, raw trial,
prediction or original report changed. All 24 trial cleanup receipts record
removed containers/cgroups, no cleanup errors and no trial watchdog intervention.

## What changed the outcome

Every trial measured 60 seconds. Within each work size, the two traffic patterns
had identical offered job counts, low/high rates and average rates. A used a
3-second cycle (1.5 seconds low, 1.5 high); B used a 12-second cycle (6 seconds
low, 6 high). Thus the treatment changes the duration of a sustained high rate.
Small jobs performed 44,000 SHA iterations; large jobs performed 88,000, with
half the offer rates. These are two sizes of the same computation.

| Job size | Burst cycle | Observed 500 ms misses, four trials | Busy-capacity forecast | CPU/job forecast |
|---|---:|---:|---:|---:|
| Small | 3 s | 0% in every trial | 0% | 0% |
| Small | 12 s | 21.70–23.59% (mean 22.56%) | 22.76% | 49.23% |
| Large | 3 s | 0% in every trial | 0% | 0% |
| Large | 12 s | 15.43–16.61% (mean 16.13%) | 17.26% | 46.85% |

The longest trial/contrast error was 1.826 percentage points. Supporting queue,
rejection and recovery checks also passed: maximum peak-queue error was two jobs
and maximum clock-bounded recovery error was 81.83 ms. Across 81,504 validation
offers, every request succeeded, with zero rejections and zero responses longer
than one second. The 500 ms misses therefore describe late successful responses.
Zero 500 ms misses in the short cycles does not imply zero waiting or that
tighter deadlines were met.

## What the capacity comparison says

Each size received its own two fresh calibration trials using the fixed
10-second pattern. Predictions for both sizes were sealed before validation.
Busy-capacity estimates were 152.167 and 76.889 jobs/s for small and large jobs;
the nominal half-CPU divided by whole-cohort CPU/job estimates were 139.273 and
71.233 jobs/s. Calibration disagreement was approximately 0.22% and 0.14%.

The busy estimate outperformed the declared CPU/job substitution in all eight
size/block comparisons, satisfying the frozen baseline-advantage rule at both
sizes. Both models predicted zero 500 ms misses for the short cycles, so their
deadline distinction comes from the long cycles. The comparison does not test
every possible CPU-demand model or establish why the two capacity estimates
differ. Per-job CPU time was not measured.

## Meaning and next research question

A checkout counter provides an analogy: the same number of customers can arrive
in short rushes or sustained rushes. Short rushes end before the queue becomes
large enough to cause a 500 ms deadline failure; sustained rushes let the queue
grow. Measuring how fast the counter actually serves a waiting line predicted
the tested outcome more accurately than the declared CPU/job substitution.

V23 extends V22's prospective evidence across two job sizes and two burst
durations on this host and service. Busy-period modelling and burst queues have
prior art; this result alone does not establish a new estimator or algorithm.
For a stronger small contribution, the next step is to investigate the cause
of the estimator mismatch and define a useful diagnostic or correction with
an appropriate baseline. Further repetitions alone would strengthen evidence
without creating that contribution.

Evidence: [sealed original report](../analysis/runtime_io_v23/generation-01/analysis/1791359968410941280/report.json),
[new verification receipt](../analysis/runtime_io_v23_result_review/20261007/report.json),
[frozen protocol](runtime_io_v23_frozen_question.md),
[prior-art scope review](runtime_io_novelty_generality_review.md).
