# Dynamic quota-update replay: bounded assessment

Date: 8 October 2026. This completes the gate proposed in the [discovery comparison](runtime_io_novelty_discovery_round_20261008.md).

## Verdict

**Stop custom-method development and fresh collection for this candidate at the present gate.** The replay establishes conditional timing and accounting effects, but no additional capability beyond ordinary quota replay, replenishment controls and resource accounting. It establishes no actual published-controller ranking change or new empirical finding. A synthetic material effect alone does not meet the frozen proceed rule.

This is a decision about the present candidate and evidence, not proof that no future research on dynamic quota updates can contribute. The strongest remaining possibility would require a consequential finding in an actual deployment or evaluated controller, under a declared resource contract, that remains after the adequate ordinary controls. That finding is not supplied by this check. More repetitions of the current fixed-quota service would not establish it.

The empirical paper and supporting material remain unchanged. Earlier screens and the FIFO route remain closed; static fixed-average-allowance period selection remains on hold. Collection remains stopped.

## What was frozen and executed

The design was saved and sealed before numerical results. The replay fixes a 100ms quota period, zero burst credits, a five-ms local runtime slice, one physical CPU and one FIFO worker. It tracks global and local runtime separately; writes can refill the global pool and discard local balances, while periodic replenishment retains local runtime. The timer stays active. Initial global runtime equals the initial quota and local runtime is zero.

The resource window is half-open [0,4s). Eight hundred synthetic jobs arrive every five ms, each requiring five ms of CPU, so demand is continuously runnable throughout that window. Deadline targets are 100, 300 and 500ms relative to each arrival. Deadline evaluation continues through 4.5s; no new offered jobs enter after 4s. This is a deliberately CPU-demanding synthetic trace, not an overloaded live service or a replay of the manuscript's measurements.

First replenishment boundaries range from 1 through 100ms in one-ms steps. These are 100 sensitivity points, not a probability distribution and not a proof covering every continuous phase. At an exact tie, periodic replenishment precedes newly requested immediate writes; a boundary control receiving its request after that callback waits until the next callback. That declared order affects the aligned-phase case. Timer jitter, runtime debt, idle timer shutdown/slack returns, hierarchy and multi-CPU scheduling are outside the model.

Five fixed proposal sequences cover unchanged-limit suppression, genuine one-second alternation, small one-second changes, a scale-down/rollback grant and a nonbinding single-CPU control. Four actuation arms compare period-then-quota writes, quota-only writes, boundary-deferred setters and a recommendation applied natively before replenishment. The native boundary arm imitates the inspected Kscaler application point, not Kscaler's complete estimator or controller.

Ordinary scalar bisection also matches each boundary arm to the immediate arm's nominal allocation integral and separately to its saturated CPU consumption. It requires 16–18 offline replay evaluations per matching target. This is a retrospective calibrated comparator with known simulated state; it is not a low-information deployment policy or a claim of fewer measurements.

Finally, the pinned `CaptainScaler` class was extracted unchanged by AST and executed against simulated CPU/throttle feedback for all 100 phases. Its actual outer-loop actuation predicates and setter were separately executed using in-memory file sinks. Tower, distributed services, the Kubernetes runtime, real cgroup files and the Linux kernel were never executed.

Artifacts: [frozen plan](../analysis/runtime_io_quota_update_replay/20261008/design/plan.json), [numerical assessment](../analysis/runtime_io_quota_update_replay/20261008/assessment.json), [full results](../analysis/runtime_io_quota_update_replay/20261008/results.json), [reference event ledgers](../analysis/runtime_io_quota_update_replay/20261008/reference_ledgers.json), and [verification](../analysis/runtime_io_quota_update_replay/20261008/verification.json).

## Results against adequate controls

### 1. Skipping an unchanged period does not create a new capability

With zero burst, nonnegative global runtime and no execution between writes, the global balance after period-then-quota writes is the new quota. A quota-only write produces the same balance. Both clear local runtime. All 500 fixed-sequence phase cases have identical CPU use, completion vectors and deadline misses across these two immediate arms. All 100 native-policy feedback cases also have identical decisions and completion vectors across these arms.

The unchanged-limit control makes no effective setter calls and produces no additional CPU. The nonbinding control produces no CPU or deadline difference across the declared arms. These controls prevent attributing a duplicate-write bypass to the actual inspected limit-change guard.

Interwrite delays were a sensitivity check, not measured runtime timings. Across three genuine-change sequences and 100 phases each, delays of 10us and 100us add 30us and 300us of consumed CPU over four seconds respectively, with no deadline change. At 1ms, the consumption difference ranges from −12ms to +3ms and deadline differences range from −1 to +0.125 percentage points. Timing, lost local runtime and shifted refill opportunities can interact; two writes do not simply grant two quotas.

### 2. Approximately equal nominal allocation can supply different CPU

The following table compares immediate writes against the boundary-setter arm calibrated to the same nominal allocation integral. Extra CPU is relative to that boundary arm. Deadline advantage is boundary miss percentage minus immediate miss percentage, across all declared deadlines and phases.

| Fixed sequence | Extra CPU range | Phase points with at least 5% extra CPU | Deadline advantage range |
| --- | ---: | ---: | ---: |
| 40/60ms regular alternation | 0–6.617% | 36/100 | 0–2.125 pp |
| 49/51ms regular changes | 0–7.281% | 36/100 | 0–2.500 pp |
| 25ms scale-down, 75ms rollback grant | 0–4.622% | 0/100 | −0.500–1.250 pp |

The nominal matching error is at most 20us of CPU allocation integrated over four seconds, reflecting integer-us quota settings. This is approximate matching, not exact equality. Both boundary arms yield the same table on this particular workload; that does not establish general equivalence when local runtime survives a changed-quota boundary.

The 5% resource reference is met at some phases. None of these fixed comparisons reaches the frozen 3pp deadline reference. The effects depend on phase and are explained by the declared replenishment/reset ledger; they do not constitute a new mechanism or a verified effect in a real controller evaluation. The grid count is not an empirical frequency or confidence interval.

### 3. Matching consumed CPU changes the interpretation

The CPU-calibrated boundary arms meet the frozen 10us consumption tolerance on 495/500 fixed-sequence phase cases each. The five unmatched targets have errors of 12–18us from integer setting granularity and are excluded from consumption-matched deadline claims. Nominal-matched targets have a different quantization criterion; do not combine those failures with consumption-matching failures.

Across the eligible consumption-matched genuine-change cases, the immediate arm's deadline advantage ranges from −1.875 to +1.375pp. No eligible case reaches a 3pp absolute difference. A direction change is possible: an immediate arm that appears preferable under nominal allocation can have higher misses than the ordinary boundary arm at approximately equal consumed CPU. Both directions remain conditional properties of the synthetic actuation model, not a published-controller ranking result.

Matching consumption is one comparison contract. It does not certify equal instantaneous caps, isolation, or opportunity for a lightly loaded service; the continuously runnable demand here makes consumed CPU a usable opportunity measure within this declared single-CPU window. Initial/residual balances and local discards are reported separately, and the conservation identity is checked.

### 4. Native feedback can magnify the difference, with unequal budgets

Executing the pinned Captain scalar logic in the model yields up to a 9.75pp difference at the 500ms deadline between immediate and boundary actuation. The 100ms and 300ms deadline differences are zero in this trace. The arms receive different simulated throttle histories and can consequently choose different later quotas.

Over the resource window, immediate-minus-boundary consumed CPU ranges from +6 to +70ms; nominal allocation differences range from −159.14 to +94.5ms of CPU. These runs were not resource-matched. They demonstrate feedback sensitivity, not a fair controller-performance or efficiency ranking. The fixed-sequence controls do not remove that limitation. Matching full adaptive controllers remains untested; no result here refutes the Autothrottle or Kscaler evaluations.

## Why this does not pass the novelty gate

The strongest confirmed statement is that a nominal allocation integral alone need not capture available execution under dynamic writes. The update and unthrottling behavior is already documented, and safe reconfiguration has established reservation-based alternatives. [Linux bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html), [AQuoSA](https://retis.santannapisa.it/~tommaso/publications/SPE-2008.pdf).

Autothrottle's rollback intentionally grants additional CPU; its allocation and usage objectives must be interpreted as declared rather than treating an emergency grant as free. [Autothrottle](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf).

Ordinary budget replay and accounting explain every declared outcome. No new timing-uncertainty decision rule, cheaper measurement procedure, better matched-budget control or consequential actual-system finding is established. The largest deadline signal from native feedback has unequal resource histories. It cannot be promoted into the empirical finding required by the proceed rule.

The literature screen is scoped, and the available Kscaler revision is not certified as the exact paper-evaluation revision. Closing this gate should therefore be read as insufficient demonstrated contribution, not an exhaustive proof of non-originality or proof that timing never matters in deployments.

## Verification and preservation

Verification passed 60 independently implemented one-ms tick-reference vectors, 74,400 finite-state paired/single-write equivalence checks, and conservation/physical-capacity checks for 4,000 fixed-arm rows. It also checked 4,500 calls through the pinned worker's actual outer-loop predicates and 200 setter write pairs against the native scalar proposals, including quota rounding and write order. These checks validate the declared offline model and source mapping; they do not validate Linux runtime fidelity.

All 1,911 protected scientific paths and 278 additional preserved paths retain their hashes. The preceding discovery artifact and older sealed roots were preserved, including the previously reported unsealed calibration verifier cache. No existing seal was changed. A separate artifact contains this design, results, software and provenance.

No dynamic controller traces, interwrite-latency measurements or new service trials were collected. No custom controller was built. Reopening this candidate requires a concrete new causal claim or capability with a matched adequate comparator; collecting data merely to validate documented refills would not, by itself, establish novelty.
