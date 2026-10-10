# V11 findings: which work got turns ahead of delayed HTTP

All eight sealed trials revalidate. Derived attribution was rebuilt from the raw recorder arrays and matches the sealed analysis. No performance measurement or scheduling correction was added.

## What this establishes

Ready HTTP goroutines wait seconds in the runtime-tracing-off workload while workers, other HTTP goroutines and HTTP background readers keep getting turns. The longest retained matched example is request 470 in block 4: 4.416610 seconds, 2,407 dispatches ahead, including 592 worker, 1,221 HTTP, 593 background-reader and one runtime-background dispatch. Of those turns, 1,768 came from runnext, 629 from regular local FIFO and 10 from the periodic global-fairness branch. None of the selections during this wait captured a pending flag or used forceFair.

Across all observed captures, runnext supplies 29,094 of 43,886 selections (66.29%). The pending-preemption ordinary correction supplies 181 forceFair selections (0.412%), all from the global queue. These are capture counts including control requests and drain, not workload-only rates.

Those 181 forced selections choose 99 worker, 66 HTTP, 12 runtime-background and 4 HTTP background-reader goroutines. It sometimes selects the delayed HTTP G, but that is not a guarantee of a prompt turn. For request 1554, it eventually selects the delayed G after 3.406082 seconds. Three other forced HTTP selections precede it, all near the end of the wait.

## Per-observed-trial evidence

| Block | Selections | Forced global choices | Matched pre-handler waits | Waits ≥1s | Waits ≥1s without another forced choice | Ready-wait p99 ms |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 10,912 | 8 | 763 | 159 | 37 | 3924.900 |
| 2 | 11,010 | 43 | 780 | 152 | 7 | 4018.310 |
| 3 | 10,952 | 66 | 863 | 104 | 10 | 3220.334 |
| 4 | 11,012 | 64 | 872 | 109 | 17 | 3115.319 |

Total matched waits: 3,278; 524 last at least one second, and 327 last at least two seconds. This is the explicitly linked network-ready cohort, not all client requests. Some wait windows overlap; their work-ahead counts must not be added.

## Recorder perturbation

The predeclared descriptive screens pass. Ratios of arm medians: server CPU/job +0.30%, client CPU/request +0.65%, successful p99 +4.86%, throughput +0.11%. Maximum rejection-plus-timeout rates are 2.43% observed and 2.56% control, and client trace coverage is 100%. This supports using the observed evidence with its stated limits; four pairs do not prove zero perturbation or statistical equivalence. Both arms use the same candidate, so this run does not compare the correction against stock Go.

## Interpretation and next question

The tested correction can help a selected G, but relying on a pending-preemption flag leaves long intervals in which it is inactive. Periodic global checks also occur during the longest wait and still fail to provide that particular G a prompt turn. The dominance of runnext is directly recorded; how a specific waiting G moves between global and local queues remains unrecorded. The next focused question is that queue residence/migration and whether a bounded dispatch or wait-age fairness rule can prevent these gaps without depending solely on the flag. This is a hypothesis for the next step, not a demonstrated fix.

Dispatch and runnable timestamps are observation sites, not continuous CPU execution. The source of a preemption signal is unavailable. Existing CPU-quota effects are retained; the experiment does not isolate kernel scheduling from every part of the delay.

## Small counting correction in this derived review

The sealed report defines "forced selections ahead" using the interval before the delayed G dispatches. That interval can include the delayed G’s own final selection. This review excludes its own final selection when describing other work selected ahead. Among the displayed examples, request 1554 therefore has three other forced choices (sealed count four), and request 1559 has zero (sealed count one). Exact corrections for every matched wait are in review.json. The timestamps and selections are unchanged, and the sealed report remains intact.
