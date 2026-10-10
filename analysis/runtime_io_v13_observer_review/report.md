# V13 observer qualification review — 2026-10-03

**Technical completion verified; observer qualification failed.** Original session, sources and reports remain sealed. These derived files live outside the result session.

| Four-trial arm totals | Offered | Timely at 500 ms | Failures | Late successful response, work certainly before 500 ms |
|---|---:|---:|---:|---:|
| legacy | 27,172 | 18,431 (67.831%) | 0 | 2,021 |
| locked | 27,172 | 16,242 (59.775%) | 0 | 1,715 |
| bounded | 27,172 | 16,222 (59.701%) | 0 | 1,687 |

Legacy→locked loses 5.76–10.88 percentage points of primary timely success in every block (median loss 7.79 points). CPU/job rises 1.71–2.58%; successful p99 rises 13.19–21.38%. CPU alone passes its 5% margin, but deadline success fails the 1-point margin and p99 fails the 10% margin in every pair. Zero rejection/timeout/error outcomes does not mean zero deadline misses.

Locked→bounded passes all declared practical screens in these four pairs. Its 500 ms timely-success change ranges from −0.90 to +0.65 percentage points, without a consistent benefit. This does not prove equivalence or show that all application locks are harmless: both arms retain locks and the same new observer.

## What the new boundaries show, within the affected observer

In all eight marked trials, completion→publication-start p99 is about 1.1–1.3 microseconds; publication-bracket p99 is about 1.6–2.3 microseconds. Recorded pre-publication lock-wait p99 is 0.11 microseconds. Publication→handler-execution lower-bound p99 remains about 161–164 ms. One bounded request has a roughly 91 ms pre-publication interval; three marked requests have publication brackets over 50 ms. Those exceptions remain explicit rather than silently treating publication as instantaneous.

This weakens dynamic event append as the dominant delay explanation in the marked service and localizes most measured post-computation delay after publication. Because the observer changes external outcomes, these timings cannot establish the exact mechanism of the legacy service. Wall intervals do not separate quota pauses from runnable competition. Fewer marked work-before misses also does not mean a remedy: overall deadline success worsened, so misses can migrate to earlier stages.

## Implementation ambiguity to isolate next

The new worker path adds timestamp calls, large fixed slot allocation, ID checks/slot bookkeeping and a second mutex acquisition after the result send; it moves completion/abandonment counters from before publication to after marker storage. Legacy→locked tests this combined change. The second lock and changed bookkeeping are concrete causal candidates, not established causes. I added these to make drain/export conservation explicit; the qualification experiment now shows their combined measurement cost is too large for the declared objective.

Next prepare an isolated observer ablation: keep legacy counters/send order and HTTP behavior, then distinguish timestamp cost from record commit/second-lock cost and slot layout. Design safe record finalization/export/reset without changing result handoff; retain cancellation and race/conservation checks. Freeze a new protocol/build and requalify against legacy before using fine-grained marked timings or launching the independent-control matrix. Do not rebuild or rewrite this completed V13 session, rerun valid trials to obtain a pass, or attribute the effect solely to clock calls.

## Temperature and technical validity

Every accepted trial passed the frozen settling/power/quiet-host and resource checks; accepted settling-window temperature means span roughly 56.94–60.13°C. The recorded k10temp collection samples span 66.125–75.875°C; review.json retains all actual monitor temperature ranges separately. The terminal’s 88.9°C reading was a live host reading after completion; it does not describe all collection samples or by itself invalidate the sealed trials. The protocol does not measure hardware thermal throttling directly, so passing its checks is not proof of thermal equivalence or absence of all host effects.

[Sealed report](../../results/diagnostic/runtime-io-v13-completion-qualification-1/session/analysis/report.md)
[Detailed derived evidence](review.json)
