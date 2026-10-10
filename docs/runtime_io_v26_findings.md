# V26 findings: both steady low-load rates qualified

Verified 2026-10-07. V26 completed all four planned trials: two at 15 jobs/s
and two at 30 jobs/s, using small jobs and the native sampler. Independent
completion replay passed. The frozen decision is `both_low_rates_qualified`.

## What qualified

Every fixed window from 5 to 25 seconds after the first scheduled offer met
the operational low-load definition: at most one waiting job, positive
guaranteed completions, and zero throttled periods within the counter bounds.

| Trial | CPU time per completion (ms) | Maximum waiting queue | Throttled periods | 500 ms deadline misses |
|---|---:|---:|---:|---:|
| low15_r1 | 4.5189–4.5458 | 1 | 0 | 0 |
| low30_r1 | 4.5616–4.5773 | 1 | 0 | 0 |
| low30_r2 | 4.5462–4.5618 | 1 | 0 | 0 |
| low15_r2 | 4.5734–4.6041 | 1 | 0 | 0 |

CPU-time intervals are accounting bounds, not statistical confidence
intervals. Each 15 jobs/s window contained exactly 300 completions; each
30 jobs/s window contained exactly 600. Delivered CPU was approximately
0.068 CPU at 15 jobs/s and 0.137 CPU at 30 jobs/s.

Across the complete measurement cohorts, all 2,700 offered jobs completed
successfully, with zero 500 ms deadline misses. All four recordings passed
the quality budgets. There were 10,233 native readings, no skipped sampler
deadlines, and a maximum wall-clock read bracket of 0.057227 ms. The largest
relative CPU/completion bound width was 0.6714%, below the 4% limit.
There were no technical retries or watchdog interventions. All owned
containers and cgroups were removed successfully. Collection took 19.22
minutes and is complete.

## Scientific interpretation

This resolves the low-state qualification prerequisite that V25 did not meet.
For this service, quota and sampler-on configuration, we now have repeated
steady windows with a small queue and no measured quota throttling.

The measured low-load CPU cost remains about 4.5–4.6 ms per completion.
Earlier V25 small-job busy windows were about 3.3–3.4 ms per completion.
That cross-study contrast is an exploratory lead: V26 contains no busy arm,
so it cannot establish a controlled low-versus-busy difference or its cause.
The two V26 rates look similar descriptively, but two repetitions per rate
do not establish rate independence or statistical equivalence.

V26 also contains no sampler-off arm. It does not resolve sampler neutrality,
the earlier deadline comparability issue, generality, or publication novelty.
The original V25 low-state failures remain unchanged.

## Next question

The proposed next step is a controlled load-composition comparison: keep
high-load work fixed, vary the low-load portion, and test whether whole-run
CPU/job changes while busy capacity remains stable. A successful result
would support a practical warning about using whole-run averages for busy
capacity prediction. Its mechanism and novelty would still need assessment
against prior work and independent calibration baselines.

Low windows in a mixed schedule must qualify again; this steady pilot does
not guarantee that a preceding burst has drained. The next protocol and
analysis need to be frozen before any collection. No new experiment was
launched while reviewing these results.

## Evidence

- [Original sealed analysis](../analysis/runtime_io_v26/generation-01/analysis/1791394434069058442/report.md)
- [Original machine-readable report](../analysis/runtime_io_v26/generation-01/analysis/1791394434069058442/report.json)
- [Sealed independent result review](../analysis/runtime_io_v26_result_review/20261007/report.json)
- [Frozen V26 protocol](runtime_io_v26_protocol.md)
- [Contribution and experiment plan](runtime_io_contribution_and_experiment_plan.md)
