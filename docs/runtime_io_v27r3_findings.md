# V27 generation-03: complete comparison, composition screen inconclusive

Verified 8 October 2026 against the [sealed original report](../analysis/runtime_io_v27/generation-03/analysis/1791429220799564493/report.json).
Full independent completion replay passed. A separate
[sealed result review](../analysis/runtime_io_v27r3_result_review/20261008/report.json)
also recalculates whole-run costs from raw measurement CPU endpoints and
completion counts, all paired block contrasts, bounded intervals and observer
interactions. The original report and all frozen rules remain unchanged.

All 16 planned trials were accepted with no technical retries. All 68,736
measurement offers and 7,200 warmup offers completed successfully. Every trial
retained 81 host-monitor records and passed the required coverage, quiet and
power checks. Owned cleanup passed without watchdog intervention; all recorded
cgroup paths are absent. Collection took 3,531.181 seconds (58.85 minutes),
within its 5,400-second bound. Collection is stopped.

The comparison changes low arrivals from 15 to 30 jobs/s while preserving high
arrivals, high-job counts/timestamps, workload and resource controls. Contrasts
are 100 × (low30 / low15 − 1), paired within each of four blocks per sampler arm.

| Native sampler | Whole CPU/job change % | Model-based 95% interval % | Busy capacity change % | Model-based 95% interval % |
|---|---:|---:|---:|---:|
| Off | +3.194 | [2.720, 3.669] | +0.042 | [−0.475, 0.559] |
| On | +3.419 | [2.989, 3.849] | +0.000 | [−0.662, 0.662] |

Whole-run CPU/job increased in all eight paired block comparisons. Low15
trials measured 3.512–3.533 ms/job, versus 3.616–3.646 ms/job at low30. Busy
capacity remained approximately 150 jobs/s (individual accounting bounds
149.167–150.333 jobs/s). Both busy-capacity contrast intervals and every block's
capacity bounds met the frozen ±2% stability screen.

All required states qualified: busy queues stayed positive in all 16 trials;
sampler-on low windows had at most one waiting job and zero bounded throttled
periods. Sampler-on busy delivery bounds lay inside [0.48, 0.52] CPU. The
sampler-on fixed-window CPU/completion bounds were 4.437–4.628 ms in low windows
and 3.297–3.396 ms in busy windows across trials. These are phase accounting
ratios, not direct per-job CPU attribution or proof of a runtime mechanism.

The observer-interaction checks passed: on-minus-off composition contrasts had
95% intervals [−0.186, 0.636] percentage points for whole cost and
[−1.032, 0.948] percentage points for busy capacity, both inside ±2 points.
This qualifies the specified contrast comparison; deadline sampler neutrality
remains unestablished.

The sole failed scientific support criterion was the minimum cost effect.
The frozen rule requires each cost interval's lower bound to be at least 3%.
The unrounded bounds are 2.719502% off and 2.988995% on, so both fail. Both
intervals cross 3%; the result neither establishes the target minimum nor
establishes an effect below that target. The original decision remains
`composition_inconclusive`. Do not round the on bound to 3%, lower the rule,
pool observer arms to replace their separate checks, or collect again until
the screen passes. The intervals assume independent approximately normal
block contrasts, with only four blocks and three degrees of freedom.

This adds controlled evidence of composition sensitivity in whole-run CPU/job
alongside bounded busy-capacity stability in this service and schedule. The
complete ≥3% support screen, a causal explanation, estimator superiority and
novelty remain unestablished. No new deadline forecast was prospectively
validated here. Earlier V22/V23/V25/V26 evidence and the working draft remain
unchanged; the prior sampler limitation is narrowed only for these two contrast
metrics. The next contribution question is whether a busy-state estimator
improves independent prediction against a fair utilization–throughput
comparator. Define that evaluation before deciding on further collection;
no follow-on workload or new generation was launched during this review.
