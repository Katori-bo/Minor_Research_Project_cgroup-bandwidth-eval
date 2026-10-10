# Completed continuation: small current period effects, historical cause unresolved

Reviewed 2026-10-07. No new performance experiment or settings change.
The four-cell continuation completed successfully. Its report seal, all four
raw replays and saved derivations, twelve older raw replays, contrast arithmetic,
hardware fixtures, CPU-control receipts, fresh thermal baseline and finalized
host log were verified again. All sixteen intended cell labels are now represented
across two sessions; this is not the original uninterrupted sixteen-cell study.

Evidence: [continuation report](../analysis/runtime_io_execution_state_continuation/generation-01/analysis/1791342475330161615/report.md),
[partial pilot findings](runtime_io_execution_state_partial_findings.md).

## Result

| Automatic-speed observation | 100 ms | 20 ms | Short-period change |
|---|---:|---:|---:|
| CPU/job, counters off | 3.296 ms | 3.274 ms | -0.645% |
| CPU/job, counters on | 3.300 ms | 3.288 ms | -0.385% |
| Capacity, counters off | 151.806 jobs/s | 152.735 jobs/s | +0.612% |

Instructions/job changed +0.000733%, CPI -0.0636%, effective user cycle-rate
+0.2641%, and delivered CPU stayed around 0.5001–0.5008 core. Both matched
counter-observer screens pass the 1% practical margins; CPU/job contrasts from
enabling counting are +0.136% at100 ms and +0.398% at20 ms. These are practical
checks, not statistical equivalence or proof of zero observer overhead.

The label `continuation_no_consistent_large_period_signal` means neither
counted/uncounted CPU/job contrast reaches the predeclared 2% practical signal.
Both observations show small improvements in the same direction; it does not
mean opposite signs, invalid data, a failed collection, or proof of no effect.
The older +5.6% full-service penalty and +11–14% minimal penalty were not
reproduced here. They remain historical verified observations whose cause has
not been identified.

The whole speed pilot showed that requested CPU performance bounds can create
substantially different measured execution conditions (roughly24% lower
execution-rate proxy and30% more CPU/job in the complete first block), with
nearly identical instruction work. This demonstrates measurement/control
feasibility for that workload/session. It supplies no supported large period
interaction or historical clock explanation.

## Additional observations and limits

Fresh automatic baseline was61.221 C, compared with62.721 C in the interrupted
session. It was not the56.933 C at which the old run stopped. The continuation
therefore did not test whether that particular cooler state changes the period
contrast, and this is not a controlled temperature intervention.

The new host log finalized successfully with1,969 records; CPU settings stayed
comparable and no named ChatGPT/Codex process was recorded. The new collector
streams the original host sample fields instead of buffering the entire session.
This removes the prior finalization failure in this run but remains an explicit
collection-context difference between sessions.

The new counted cells attribute0.192% (20 ms) and0.251% (100 ms) of total CPU to
system CPU. The prior constrained20 ms cell's5.463% split did not recur in these
new **automatic-speed** cells. This does not identify or exclude the cause of
that anomalous split. Cycles/user CPU-second remains an effective metric rather
than direct measured worker frequency.

Descriptive combined speed-period interactions are -0.816%/+0.158% (first block,
counting off/on), and -0.674%/-1.164% for the second block labels. All are below2%
magnitude. The latter combines older constrained cells with new automatic cells,
so it cannot support a replicated controlled interaction claim. No universal
period ordering, exclusion of every execution-state mechanism, historical causal
attribution or novelty follows from these data.

## Research decision

This is useful negative evidence and completed follow-through, not a mechanistic
breakthrough. The tested speed-control route has not supplied a promising
explanation of the reversal. Do not broaden the experiment search merely because
that cause is still unknown.

Proceed with the existing arrival/admission/queue/yielding and capacity-based
prediction account, retaining the original penalty, faithful opposite-direction
repeat, minimal controls and continuation as separately qualified observations.
Treat processing capacity as measured input until its period dependence has a
supported mechanism. Keep a historical-state and collection-context limit in the
paper; assess contribution against prior work without claiming that seeing both
signs or generic clock-dependent throughput is novel. No further performance run
is proposed or automatically authorized by this review.
