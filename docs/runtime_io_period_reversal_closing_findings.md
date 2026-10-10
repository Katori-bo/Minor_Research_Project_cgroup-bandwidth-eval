# Closing findings: the historical period reversal remains unresolved

Final authorized comparison completed on 2026-10-06. All eight performance
cells, hardware fixtures, preparation/report seals and saved derivations were
independently replayed and verified. No additional performance run is proposed.

## Completed counter comparison

The final test retained the exact minimal SHA binary/image, Go1.26.1,
44,000 iterations/job, GOGC=100, GOMAXPROCS=1, CPUs2/4, 0.5 CPU and zero quota
burst. Eight fresh containers followed ABCD/DCBA, with 20-second warmup and
30-second measurement. Longer settling passed in every cell: the initial mean
reference was 58.885°C, and pre-trial accepted means were 58.81–59.48°C.

| Block | Hardware counting | CPU/job, 20 vs 100 ms | Instructions/job | Cycles/instruction | Effective user cycle-rate |
|---|---|---:|---:|---:|---:|
| 1 | Disabled | -0.625% | Unmeasured | Unmeasured | Unmeasured |
| 1 | Enabled | -0.577% | +0.000798% | +0.193% | +0.705% |
| 2 | Disabled | -0.527% | Unmeasured | Unmeasured | Unmeasured |
| 2 | Enabled | -1.045% | +0.000473% | +0.020% | +0.991% |

Average CPU delivery remained about 0.500–0.502 core. Counted work was about
26.709 million user instructions/job. All four matched counter-enabled/disabled
comparisons passed the 1% CPU/job, capacity and delivery margins; the largest
CPU/job observer contrast was 0.678%. Counter coverage, known-work fixtures,
native/cgroup alignment and cleanup passed. Qualification is specific to this
minimal workload/session, not retroactive qualification of the full-service pilot.

The reported decision `close_unresolved_period_effect_not_consistent` means
neither period contrast reproduced a >=2% same-direction effect in both blocks
under the predeclared screen. Both counter-disabled blocks actually agreed in
direction: a small improvement with the shorter period. The decision is not a
failed collection, opposite signs between blocks, or proof of equivalence.

## What the sequence establishes

Original V20 retained a verified shorter-period CPU/job penalty. The later cost
pilot and faithful V20 repeat retained the opposite direction. The seven-cell
minimal screen subsequently showed a 14.19% and 11.58% shorter-period penalty
in its two minimal opposite-order pairs, at average CPU supply near 0.5 core;
its final full-service 100 ms cell was missing. The completed closing comparison
now shows a small shorter-period improvement with essentially unchanged user
instruction counts and unchanged average CPU supply.

HTTP handling and application queues are unnecessary for the minimal penalty
observed in the earlier screen. The final counter-enabled cells show no sizable
additional instruction work in their current, near-null-effect state. They do
not establish what instructions or execution-weighted clocks did during the
earlier penalty, because counters were absent then. The historical penalty must
not be dismissed as invalid merely because it did not recur here.

This is not a controlled experiment isolating the change between sessions.
Measurement duration changed from 60 to 30 seconds, initial idle from 10 to
20 minutes, and matched helper/null-perf infrastructure and whole-session host
sampling were added. Recorded CPU settings and the minimal binary remained
fixed, but these collection/workload-timing differences and unmeasured host
conditions prevent attributing the reversal to any one factor. A snapshot of
temperature or process presence is not a historical causal explanation.

## Closing interpretation for the paper

The period-to-cost relationship is conditional in the retained observations,
rather than a stable universal shorter-period penalty. The exact mechanism
behind the historical sign reversal remains unresolved. Aggregate CPU supply
does not account for the earlier minimal penalty by itself; current user-work
counts cannot retrospectively distinguish increased runtime work from slower
execution in that earlier state. No frequency, cache, migration, GC, compiler,
tool-installation or desktop-activity cause is established. Novelty is not
established by observing both directions.

Retain the arrival/queue/yielding findings and their limits. Describe the original
penalty, faithful opposite-direction repeat and minimal controls as separate
verified conditional observations. Use the existing prior-work synthesis as
context, without citing either direction as proof of this mechanism. Close this
diagnostic branch as authorized; do not launch another experiment automatically.

Evidence:

- [Completed closing report](../analysis/runtime_io_minimal_counter_closing/generation-03/analysis/1791298178262469654/report.md)
- [Earlier seven-cell minimal report](../analysis/runtime_io_minimal_computation_screen/generation-02/partial_analysis/1791292967721661400/report.md)
- [Failed short-wait closing attempt](../analysis/runtime_io_minimal_counter_closing/generation-02/closing_analysis/1791295409385777239/report.md)
- [Repeat findings](runtime_io_v20_repeat_findings.md)
- [Prior-work synthesis](runtime_io_period_literature_synthesis.md)
