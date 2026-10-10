# What the earlier drafts contribute to the completed paper

9 October 2026. Read-only manuscript/evidence assessment. The current manuscript
and frozen scientific outcomes are unchanged; this note proposes editorial reuse.

## Where the project landed

The completed scientific manuscript is **Capacity Calibration and Deadline
Forecasts Under a Fractional CPU Quota** in
`paper/capacity_calibration_empirical.md`. It asks how independently calibrated
capacity inputs forecast all-offer 500 ms deadline misses within a shared FIFO
model. Whole-run CPU/job substantially overpredicts misses; direct idle
correction barely helps; busy calibration is accurate; a nonlinear CPU-based
benchmark comes close. The frozen minimum advantage over that nonlinear
benchmark remains inconclusive. No new estimator, isolated scheduler mechanism
or universally superior calibration method is established.

## Draft and evidence lineage

| Record | Actual question/result | How to use it now |
|---|---|---|
| `paper/archive/paper_draft_legacy.md` | Short exploratory pilot; header explicitly says its claims require replacement | Preserve history; do not copy its numeric claims, software settings or broad operational recommendations into the current paper |
| `paper/paper_draft.md` | Reviewed 300-trial period/concurrency/arrival matrix; successful-response p99 and failures reported separately | Contextual evidence that equal configured CPU fractions can have different response distributions; keep its endpoint and configuration scope explicit |
| V20 original and repeat findings | Yielding sharply reduces completion-to-handler delay; net deadline improvement is negligible or conditional; period ordering changes across sessions | Motivation for measuring end-to-end outcomes and retaining conditional/negative results; no universal yield or period remedy |
| Earlier capacity drafts and V22/V23 | Prospective capacity-to-deadline evidence, including tested request sizes and burst timescales | Already carried into the current manuscript with their independently frozen definitions |
| V25/V26/V27 controls | Accounting mismatch, qualified low-load states, observer limitations and composition evidence | Already retained in supporting material; preserve the inconclusive composition threshold and observer limitations |
| Final V28 comparison | Strong nonlinear comparator narrows busy calibration's advantage | This controls the current paper's central conclusion; earlier language implying general CPU-estimator failure cannot override it |
| FIFO theorem/other closed screens | Correct scoped assets or unsuccessful contribution gates | Retain as research records; do not recast them as established novel foundations of the empirical manuscript |

## Tail latency remains relevant

Tail latency describes the slow end of the response-time distribution. The old
paper's p99 is a nearest-rank percentile among successful requests: approximately
99% of those successful responses finish within that time. Its table reports
means of run-level p99 values, not a pooled percentile.

The current paper asks how many of **all offered requests** fail a declared
deadline. Rejections and unsuccessful offers count as misses. This endpoint
prevents a rapid rejection from silently improving the apparent successful-
response distribution. Percentile latency and deadline misses answer related
questions, with different cohorts and summaries.

The reviewed original matrix has 300 trials, 1,618,350 offers, 23,059 rejections
and 17 timeouts. It records strong period/concurrency/arrival interactions and
explicitly withholds a universal optimum. Its legacy claim that longer periods
eliminate quota-induced tail latency is not supported by the completed matrix.
Those older observations cannot be pooled into V28 because configurations,
runtime parallelism, dates and endpoints differ.

## Recommended reuse

1. Use one short introduction paragraph to connect the earlier response-time
   problem to the present capacity-calibration question.
2. Keep the completed matrix, yielding observations, reversals and observer
   qualifications as separate linked supporting evidence. Supporting Material
   S5 already carries the original matrix and yielding/period history.
3. Retain successful-response p50/p95/p99 alongside all-offer deadline outcomes
   when interpreting the next dataset; always show failures and cohort counts.
4. Use the earlier conditional stage findings to justify recording request
   stages for V29. Do not infer a cause from aggregate throttle counts or
   computation wall time.

Proposed introduction wording, for a later editorial revision:

> Earlier experiments in this project found that successful-request p99 depended
> on quota period, worker concurrency and arrival pattern at a fixed configured
> CPU allowance. They also recorded rejections and timeouts, motivating joint
> reporting of response times and unsuccessful offers. Here we examine how
> capacity calibration affects forecasts of all-offer deadline misses. The earlier
> experiments provide separate context because their configurations and endpoint
> differ from the present prospective comparison.

The previous records can improve motivation, limitations and supporting context.
They do not add a new prospective comparison or establish the current paper's
novelty simply by being merged into its text. Preserve verified evidence, reuse
it in its proper role, and retire superseded claims.

Source records: `paper/paper_draft.md`, `paper/archive/paper_draft_legacy.md`,
`paper/README.md`, `paper/capacity_calibration_empirical.md`,
`paper/capacity_calibration_supporting_material.md`,
`docs/runtime_io_v20_findings.md`, `docs/runtime_io_v20_repeat_findings.md`,
and `docs/runtime_io_period_reversal_closing_findings.md`.
