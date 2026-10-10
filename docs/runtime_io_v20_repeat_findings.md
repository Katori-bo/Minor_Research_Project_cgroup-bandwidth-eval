# Faithful V20 repeat: verified findings

Reviewed 2026-10-06. Generation-04 completed four qualification rehearsals and
all sixteen trials with no interrupted blocks. Independent raw completion
verification passed. Its frozen decision is
**mixed_execution_opportunity_and_temporal_supply_signals**.

The central result is that **the original shorter-period penalty did not return
when the original runner and four-cell design were restored**. The repeat agrees
with the cost pilot's direction: 20 ms uses less CPU per completed computation,
provides higher busy completion capacity and improves 500 ms success. The pilot
helper, its counter-aligned measurement window and its additional reset-to-load
delay are therefore not necessary for this direction. This does not prove every
pilot-specific effect is zero.

## Verification

The [offline reviewer](../analysis/review_v20_repeat.py) verifies completion for
both V20 generations and replays the cost pilot. It checks all 48 trial records,
the sealed repeat protocol, original/repeat source and binary identity, workload,
matrix, CPU/memory/PID limits, kernel/boot/topology, exact offered schedule and
power settings. It applies the same fixed busy window to all three sessions.
All recorded contracts match. Results, per-cell summaries, contrasts, host
summaries and source seals are saved in
[review data](../analysis/runtime_io_v20_repeat_review/20261006/report.json).

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 analysis/review_v20_repeat.py
```

All 108,688 repeat offers completed, with no rejections/errors; every offer met
the 1,000 ms target. Each trial's 20 s warmup completed all 2,265 offered jobs.
The original report, thresholds and previous results remain unchanged.

## Repeat cells

Means across four equal-offer trials per arm. P99 is the mean of trial p99s,
not a pooled p99. CPU/job includes the entire service. Capacity uses the same
18 seconds per trial as the original backlog audit: seconds 6.5-9.5 in each
ten-second cycle. It is supplementary to the frozen V20 primary outcome.

| Arm | 500 ms success | CPU/completed computation | Busy capacity | Successful E2E p99 | Mean completion-to-handler interval |
|---|---:|---:|---:|---:|---:|
| A: 100 ms, yield off | 73.10% | 3.644 ms | 148.03 jobs/s | 749.4 ms | 18.595 ms |
| B: 100 ms, yield on | 74.74% | 3.648 ms | 147.68 jobs/s | 737.6 ms | 0.0886 ms |
| C: 20 ms, yield off | 82.29% | 3.596 ms | 151.04 jobs/s | 642.0 ms | 10.573 ms |
| D: 20 ms, yield on | 82.31% | 3.601 ms | 150.42 jobs/s | 650.2 ms | 0.0474 ms |

All B/C/D guardrails against A passed in every block.

Period without yield, C-A: 500 ms success improves in every block, mean
**+9.18 percentage points**, exploratory block 95% interval **[4.47, 13.90] pp**.
Mean paired CPU ratio is -1.30%, interval [-1.83%, -0.78%]. Completion-to-handler
mean falls approximately 43.1%. With yield, D-B success rises +7.57 pp
[5.59, 9.55] and CPU ratio falls approximately 1.29%.

Yielding at 100 ms, B-A: the mean completion-to-handler interval falls about
99.5%, replicating its strong stage-specific response. 500 ms success increases
in all four blocks, mean +1.64 pp [0.03, 3.25]. This is a modest exploratory
deadline benefit in this session; the original result was -0.09 pp [-1.00, 0.82].
At 20 ms, D-C deadline change is effectively zero on average (+0.026 pp), has
both signs and a wide interval [-6.08, 6.13] pp, despite another approximately
99.5% interval reduction. A strong stage response is not a guaranteed net
deadline benefit.

The decision label describes both factors meeting the frozen descriptive
screens. It does not observe remaining quota, handler runnable readiness or a
scheduler defect. The small yielded intervals also make a relative period
reduction of approximately 44% correspond to only approximately 41 microseconds
in absolute mean time. Do not confuse that supporting effect with the much
larger absolute queue and deadline differences.

## Comparison across sessions

Yield off only; pilot counters off. Identical fixed capacity estimator:

| Session | 100/20 ms CPU per completed computation | 100/20 ms capacity | 100/20 ms 500 ms success |
|---|---:|---:|---:|
| Original V20, generation-03 | 3.630 / 3.833 ms | 151.04 / 138.67 jobs/s | 82.14% / 54.86% |
| Cost pilot, generation-02 | 3.643 / 3.591 ms | 148.10 / 151.19 jobs/s | 73.43% / 83.58% |
| Faithful V20 repeat, generation-04 | 3.644 / 3.596 ms | 148.03 / 151.04 jobs/s | 73.10% / 82.29% |

Thus this is no longer an isolated improvement seen only in the new pilot.
Two later sessions, with different collection paths, agree. This is evidence
against a pilot-helper-only explanation and against treating the original
shorter-period penalty as universal. It is not confirmation of a generally
better 20 ms setting: the opposite earlier session remains in the evidence.

The nominal CPU allowance, workload, binaries and recorded power settings match,
but actual recorded host activity follows the session split:

| Recorded condition | Original V20 | Cost pilot | V20 repeat |
|---|---:|---:|---:|
| Accepted idle baseline | 48.5 C | 57.1 C | 59.4 C |
| Mean monitored temperature | 61.6 C | 69.5 C | 70.4 C |
| Plasma shell CPU, percent of one core | 0.20% | 12.05% | 12.25% |
| KWin CPU, percent of one core | 0.50% | 7.52% | 7.55% |

All host summaries use all 80 saved warmup/arrival samples per trial, pooled
across sixteen trials. CPU values use interval CPU deltas rather than lifetime
process percentages. ChatGPT is absent in every saved monitor sample. The same
desktop processes were present in all sessions, but their activity changed.

That association strengthens the case for investigating a persistent operating
state or an interaction with quota timing; it is not proof that desktop activity
or heat caused the change. Active-worker frequency/cycles and the original
runtime work breakdown remain unobserved. A simple hotter-means-slower explanation
does not account for the improved 20 ms cell in the hotter later sessions.

The repeat launch omitted the explicit `powerprofilesctl set balanced` command.
Reissuing that command at each launch is not necessary for the new direction.
A persistent effect of an earlier setting is not excluded simply by omitting
the later command; pre-command state and full daemon/GPU action history were
not recorded. No attribution to that command is established.

## What remains and the next useful question

The burst rate, 169.815 jobs/s, exceeds observed busy capacity in all sessions,
while the whole-minute average remains lower. The queue account is still useful
given measured capacity: the repeat's 20 ms queue waiting averages 232.7 ms versus
258.1 ms at 100 ms. A new held-out queue prediction was not performed for this
review. The unresolved causal question is what changes execution cost/capacity
and the period contrast between sessions.

Before choosing another run, identify the source of increased desktop activity
and define one reversible, measured intervention or a verified execution-state
control. A later paired comparison must keep the benchmark contract fixed,
verify that its target actually changed, record power/thermal differences and
retain all blocks. Merely repeating the same current session or changing a
profile name would not isolate a cause. No new performance experiment was
launched by this review.

The original queue reconstruction and strong yielding response remain useful.
The paper needs conditional claims about deadline benefit and quota period;
neither a shorter-period remedy nor a cost penalty transfers universally from
the current data. Causal mechanism, novelty and generalization remain unresolved.
