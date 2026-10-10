# Next novelty discovery round: dynamic CPU-quota updates

Date: 8 October 2026. Scope: primary-source comparison and pinned actuator-source inspection. No workload, controller, profiler or custom kernel was executed.

## Decision

**Proceed to one bounded offline actuator/replay check. Novelty remains unestablished.** Prioritize a possible causal empirical contribution before designing another predictor or controller:

> When CPU limits genuinely change, can quota-update timing materially alter deadline/cost comparisons, and does the difference survive ordinary controls under an explicit resource-budget contract?

The source audit rejects the tempting simpler claim that the inspected autoscalers blindly rewrite unchanged quotas. It also rejects treating documented quota refills as a new discovery. The surviving lead concerns real changes, their application time, and which resource contract a comparison actually measures. A new algorithm is optional; a reproducible, consequential new causal finding could be the contribution.

This screen does not reopen static quota-period selection. The empirical manuscript remains the record of established results. Paper completion is not a prerequisite for this bounded search, but searching does not strengthen its existing claims automatically. Collection remains stopped pending the offline gate.

## What has already been screened

| Route | Present status | Reason to avoid repeating it |
| --- | --- | --- |
| Reduced calibration cost | Closed at its present gate | Ordinary busy calibration already suffices on retained cases. |
| Passive/low-load burst forecasting with insufficient-evidence recognition | Closed at its present gate | Established estimation/uncertainty methods and ordinary nonlinear calibration leave no demonstrated additional capability. |
| Fixed-quota optimization-benefit profiling, Coz/BCOZ | Closed | Source/reporting checks and ordinary quota replay do not establish a distinct useful capability. |
| Request/shared CPU attribution | Closed at its present gate | Missing attribution is not itself a new method; ordinary profiling and demand inference are close comparators. |
| Earlier FIFO theorem route | Closed | Existing paper retains what was established; do not restart the theorem search. |
| Fixed-average-allowance period selection | On hold | A held question is not a completed unsuccessful novelty test. |

There are four recent completed novelty screens, or five explored routes when the earlier FIFO route is included. Initial and follow-up gates for one question are not separate novelty avenues.

## Comparison with other fresh directions

| Candidate | Closest established capability | Initial decision |
| --- | --- | --- |
| Latency-aware burst-credit management | CEDULE and MRburst profile credit-based cloud resources and manage latency/depletion tradeoffs; their cloud credit semantics differ from Linux quota bursts. | Deprioritize broad credit-management novelty. A Linux mapping alone would not establish an advance. |
| Pool CPU budgets across cooperating containers | Kubernetes documents Pod-level resource budgets and sharing idle resources, subject to feature availability. | Deprioritize generic budget pooling. Do not assume every deployment supports the feature. |
| Load-dependent CPU cost from idle/warm-up effects | Approximate Mean Value Analysis for Multi-core explicitly treats frequency/idle effects in service demand. Our earlier execution-state continuation did not reproduce the old large period penalty. | Deprioritize generic mechanism rediscovery; current evidence does not justify another frequency campaign. |
| Budget semantics of genuine dynamic quota changes | Kernel update/refill semantics, Autothrottle actuation, Kscaler replenishment-time adaptation, and AQuoSA consistency rules. | Select one bounded replay gate. Scope must survive these controls. |

Sources: [CEDULE](https://www2.cs.uh.edu/~fyan/Paper/Feng-ICAC18.pdf), [MRburst](https://www2.cs.uh.edu/~fyan/Paper/Feng-Middleware19.pdf), [Kubernetes resource management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), and [Approximate Mean Value Analysis for Multi-core](https://www.cas.mcmaster.ca/~downd/SPECTS2015.pdf). This is a scoped search, not an exhaustive originality certification.

## What the source audit actually found

Seven public source files were downloaded without building or executing them. Their URLs, byte counts and SHA-256 hashes are recorded in `source_inventory.json` in the discovery artifact. Git remote references resolved the revisions below. Web-rendered line numbers differed from downloaded files; references here use downloaded-file line numbers.

**Linux v6.12:** the tag resolves to commit `adc218676eef25575469234709c2d87185ca223a`. In `kernel/sched/core.c`, `tg_set_cfs_bandwidth` applies bandwidth values, refills global runtime, clears per-CPU runtime balances and unthrottles constrained queues. No same-value early return appears in this inspected setter. The refill in `fair.c` adds quota and caps the global balance at quota plus burst. A write can therefore affect runtime availability in addition to the configured ratio. Whether it increases usable runtime depends on current balances, execution, hierarchy and timer state. This is source interpretation, not a test of our installed kernel. The behavior is documented; it is not a novelty claim. [Kernel documentation](https://docs.kernel.org/scheduler/sched-bwc.html), [versioned setter source](https://raw.githubusercontent.com/torvalds/linux/adc218676eef25575469234709c2d87185ca223a/kernel/sched/core.c), [versioned refill source](https://raw.githubusercontent.com/torvalds/linux/adc218676eef25575469234709c2d87185ca223a/kernel/sched/fair.c).

**Autothrottle artifact:** revision `d237d7f3d765ee9ab67bcf4aeb626164a87c6bfa`. In downloaded `worker-daemon.py`, lines 255–264 coalesce very small limit differences and call the setter only when the retained limit changes. Lines 54–63 write the period and then quota on that call, including the unchanged default period. Regular Captain decisions use a one-second interval; rollback can occur on the faster observation loop. Thus a blind repeated-identical-limit example does not reproduce this artifact. Genuine changes still reach bandwidth setters; the effects of the two writes cannot simply be added because runtime caps, local clearing and intervening execution matter. This artifact uses cgroup v1; our manuscript uses v2. [Pinned worker source](https://raw.githubusercontent.com/microsoft/autothrottle/d237d7f3d765ee9ab67bcf4aeb626164a87c6bfa/worker-daemon.py).

The [Autothrottle paper](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf) intentionally grants additional CPU during rollback. It reports CPU allocation and also CPU usage. Its declared allocation-cost objective is legitimate; this screen does not establish that its evaluation is wrong. Refill opportunity, allocated capacity and consumed CPU are distinct quantities.

**Kscaler artifact:** `catcloud-6.12.0` resolves to `1acfe8458c9bcba383975fdb5e3bfeda9d722e35`; `master` resolves to `43566d6445c1d1a1d1c22c6e374f808d3582b4c7`. The inspected `core.c` and `fair.c` files have identical contents across those two revisions. Automatic recommendation application in `fair.c` lines 6661–6664 changes quota/period within `do_sched_cfs_period_timer`; the ordinary refill follows at line 6751. Throttle-correction changes also occur in that callback. This path is already replenishment-driven, rather than a userspace repeated-write path. Other external writes and timer/hierarchy details require separate treatment. [Pinned automatic path](https://raw.githubusercontent.com/xlab-uiuc/Kscaler/1acfe8458c9bcba383975fdb5e3bfeda9d722e35/kernel/sched/fair.c).

The [Kscaler paper](https://tianyin.github.io/pub/kscaler.pdf) uses scheduler runtime/idle/throttle histories, adjusts quota and period, and reports performance and allocation cost. Its evaluation identifies kernel 6.3.0. The available 6.12 artifact is not certified as the exact evaluated revision. A difference between actuator paths does not establish a comparison bias or refute its reported gains.

**AQuoSA:** Section 3.2 explicitly addresses consistency during adaptive reservation changes. New budgets take effect at recharge; global bandwidth accounting distinguishes increases and decreases and applies admission rules. It assumes a reservation scheduler and periodic soft-real-time tasks, rather than directly providing Linux CFS ceiling semantics for our service. It nevertheless blocks broad claims that safe dynamic budget updates or deferring changes to replenishment are new ideas. [AQuoSA](https://retis.santannapisa.it/~tommaso/publications/SPE-2008.pdf).

## Adequate alternatives and the surviving gap

First compare ordinary controls:

1. Preserve existing identical-limit suppression; avoid rewriting an unchanged period when quota alone changes.
2. Apply the same intended allocation changes at validated replenishment boundaries. A wall-clock sleep is not evidence that the kernel boundary was reached, and userspace deferral changes reaction time.
3. Report the time integral of nominal allocated capacity, measured CPU consumption, update-induced runtime opportunity and deadline outcomes separately. Consumption alone does not certify a cap or isolation contract.
4. Compare with known adaptive-reservation accounting. Do not invent a new debt mechanism before testing those rules and their actual applicability.

The possible empirical gap is a consequential ranking change that follows from application timing in a real actuator, under a clearly stated comparison contract. The possible method gap is a useful improvement over these controls with comparable measurements and budgets. Neither is demonstrated today.

Equal average allocation is not automatically an equal hard budget over every window. Define the contract before comparing: aligned-period ceiling, sliding-window bound, long-run allocation cost, consumed CPU cost, or an explicitly permitted emergency grant. Dynamic autoscaling intentionally changes allocation. Calling every newly granted unit an unfair surplus would be incorrect.

## Next bounded gate

Freeze a replay design before seeing its outcomes. Keep period fixed for the userspace-change arm so this does not become the held period-selection question. Use the inspected genuine-change and rollback paths, their actual cadence, and explicit initial global/local runtime and timer states. Include identical-limit suppression as a negative control and the replenishment-driven Kscaler path as a separate comparator. Replenishment phase must be an input or uncertainty range; do not choose one favorable phase and call it typical.

Compare original actuation, unchanged-period suppression, validated boundary application, and an ordinary reservation/accounting reference. Model both the recorded actuator sequence and, if claims concern controller performance, feedback after the alternative actuation. Holding decisions fixed supports an actuator-level causal comparison, not a full controller ranking.

For this screening gate, predeclare a materiality reference of at least 5% change in the chosen CPU resource measure or 3 percentage points in all-offer deadline misses. These are proposed screening thresholds, not a power calculation or established scientific importance. Show sensitivity across the declared phase range; any ranking claim must survive matched resource contracts and cannot count an intentional emergency grant as free CPU. A synthetic result remains a hypothesis for runtime validation.

**Stop** if the effect is only documented refill behavior, a path the actual code suppresses, negligible at actual cadence, fully explained by an ordinary control without a consequential new empirical finding, or dependent on an unmatched contract. Do not build another custom controller in those cases.

**Proceed to a minimal runtime validation** only if source-faithful replay predicts a material causal effect tied to genuine actuation and a concrete additional finding or capability remains after the adequate controls. The first runtime check would validate the actuator model, not launch a broad campaign. Freeze its decision rule before measurement.

## Data required if that gate survives

The current manuscript's fixed-quota records do not supply dynamic update traces. More repetitions of those records cannot settle this hypothesis. The minimal new evidence would be:

- Exact kernel/controller/runtime revisions, cgroup version, parent limits, burst setting, CPU placement and effective actuator path.
- Bracketed monotonic timestamps of requested/applied quota and period writes, including errors, coalescing and order; runtime phase/balance evidence sufficient to validate the model.
- Aligned CPU usage and deadline records for identical offered work under the original and ordinary control arms, including rejected/unfinished work and measurement overhead.
- A declared allocation/emergency-budget contract and separate consumption accounting. Add co-tenant outcomes only if making an isolation or packing claim.

No dynamic traces were collected today. No kernel was installed, no published controller was run, and no prototype capability was established. Earlier evidence, the manuscript and supporting material retain their hashes. The discovery artifact records source provenance and preservation checks separately from the prior sealed screens.
