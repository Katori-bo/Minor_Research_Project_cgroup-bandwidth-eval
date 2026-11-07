# Search for an advance transfer signal: response-stage screen

10 October 2026. Completed offline development analysis, after all historical
outcomes were known. No new traffic, host changes, observer or manuscript edits.

**No useful advance signal emerged from this additional screen.** Separating
the existing response milestones does not improve the practical selector over
the ordinary complete-response check. This result concerns the specified rule
and saved campaigns, not every possible stage model.

## Concrete hypothesis and fair test

Opposing changes in dispatch, header and body intervals could hide a changed
condition in their total. The candidate measures each stage's warmup median
displacement from calibration, converts it to probability change through the
original response CDF, and checks early/late warmup stage displacement. Its
score is the largest of those changes. The fixed <=5 pp rule retains the
original forecast only when all terms are small and all reference/probe offers
succeeded. This assumes an additive timing shift; a persistence relation is
unestablished. Client stages do not isolate server CPU execution or queueing.

The [protocol](runtime_io_stage_signal_protocol_20261010.md) was fixed before
calculating new stage scores, with historical outcomes already known. All
methods receive identical calibration records, client milestones, 25 warmup
offers and decision time. Ordinary comparators include complete-response median
translation with the same chronological check, deadline disagreement and ECDF
distance. Maximum stage ECDF distance is a direct distribution-check comparator.
No check is a statistical risk certificate or a new-estimator claim.

## Result

| Campaign | Stage guard answers | Whole-response guard answers | Stage false warnings | Stage accepted errors >5 pp |
|---|---:|---:|---:|---:|
| Original NGINX | 1/18 | 1/18 | 10 | 0 |
| Power confirmation | 12/24 | 12/24 | 1 | 0 |
| Rate transfer | 2/12 | 4/12 | 10 | 0 |

Stage and whole-response guards make identical decisions in original NGINX
and power. Power answers are exclusively P1, with zero measured misses; neither
guard answers any of the twelve P0 transition cases. Stage coverage is 16.7%
in the accurate rate campaign, refusing ten accurate forecasts. Its two answers
differ from the four whole-response answers; it is not a nested filter. Both
ECDF guards answer zero cohorts at the unchanged 5 pp descriptive cutoff.

This candidate fails the existing usefulness screen in every campaign: >=50%
overall and transition-region coverage, with no accepted error >5 pp, including
a separate P0 power assessment. Zero incorrect assurances at these coverages
does not establish useful reliability. No threshold was retuned.

Original adverse cohort 4 has reference 50% and future 88.333% misses. Stage
score 6.875 pp and whole-response score 7.8125 pp both warn; catching this known
case adds no demonstrated capability.

Power cohort 23 has reference 79.5%, warmup 44% and full-window 69% misses.
Both warmup guards warn. The separate continuous-probe screen forecast 48%
from its first 100 offers and observed 79.5% in the next 200. Those are different
decision boundaries: a warmup warning does not rescue the later agreeing-probe
failure. No stages from that future measurement entered this advance score.

## Availability and cost audit

| Observable | Before measurement? | Supported interpretation |
|---|---|---|
| Calibration and 25 warmup client milestones | Yes | Current client interval distributions |
| Isolated warmup cgroup CPU increment | Yes in power/rate; missing matched original baseline | Aggregate CPU duration; earlier CPU screen failed |
| EPP/governor/min/max readbacks | Yes in newer campaigns | Configured policy, not realized execution speed |
| Sibling-before cumulative CPU3 proc-stat snapshot | Yes | Historical cumulative count; no isolated warmup utilization increment |
| Sibling after-minus-before increment | No | Future measurement interval; inadmissible input |
| Matched worker runnable-wait or effective-frequency timeline | Not preserved in these NGINX records | Cannot reconstruct an advance score |

Original NGINX lacks a distinct warmup/measurement monotonic stamp. Preserved
source collects warmup synchronously, checks drain and then starts measurement.
Power/rate preserve warmup acquisition end <= ordinary warmup forecast seal <=
measurement start. The new guard was never executed live. Replay checks these
boundaries, sealed calibration reconstruction and original outcome accounting.

All methods consume 25 warmup offers, roughly 3–6 seconds of scheduled span
at 8–4/s plus completion/control time. Acquired calibration measured offers
were 1,600 original, 1,600 power and 2,400 rate, plus warmups, qualification and
startup. A selected 800-offer reference does not erase other acquired pools.
Deployment overhead is unqualified. Three histories on one host are not 54
independent reliability episodes.

Kernel CPU accounting covers aggregate cgroup processes. Per-process scheduler
statistics separately describe running time and runnable-wait time; runnable
waiting is not every form of off-CPU delay.
[CPU accounting](https://docs.kernel.org/admin-guide/cgroup-v2.html#cpu),
[scheduler statistics](https://docs.kernel.org/scheduler/sched-stats.html#proc-pid-schedstat).

AMD active EPP supplies a hardware preference; actual frequency also responds
to workload and physical conditions. scaling_cur_freq can represent a requested
state rather than exact realized frequency. Policy readbacks therefore cannot
stand in for execution measurements.
[AMD driver](https://docs.kernel.org/admin-guide/pm/amd-pstate.html#active-mode),
[CPUFreq interface](https://docs.kernel.org/admin-guide/pm/cpufreq.html#policy-interface-in-sysfs).

## Concrete next hypothesis and missing prerequisite

The next candidate worth a measurement-feasibility audit is **worker runnable-wait
drift conditional on CPU execution demand**. For a fixed warmup window, record
worker CPU-running increment C and runnable-wait increment R, each divided by
scheduled offers n. Compare (C/n, R/n) with identically acquired calibration
warmups and retain early/late increments. Require exact worker identity and
matched boundaries; unavailable counters must remain unavailable.

The narrow hypothesis: similar CPU duration with increased runnable waiting
could expose scheduling delay missed by zero quota throttling and aggregate
CPU agreement. Increased CPU duration with stable waiting points instead to
an execution-side change, without identifying its cause. Neither guarantees
persistence: new contention can start after the decision. This feature pair
is a candidate measurement, not a validated scalar signal.

These matched worker counters are missing from the adverse NGINX records.
R cannot be obtained by subtracting cgroup CPU duration from client response
time: the scopes and boundaries differ. Effective frequency/instruction sensing
would be a separately charged mechanism measurement if execution duration
remained ambiguous; it is not automatically bundled into this counter proposal.

Next audit preserved collector source and worker schedstat availability/accounting
semantics, then specify observer-overhead qualification if usable. No collector
or launcher is prepared here. A separately declared discovery study would then
test whether this feature pair predicts subsequent changes. A confirmation run
still needs a demonstrated relation and an independently frozen rule.

Grant the fair comparator the same (C/n, R/n), response history, decision time
and acquisition budget: ordinary state-conditioned prediction plus recent CDF
and ordinary uncertainty checks. Denying its inputs would manufacture an
advantage. State-aware prediction is established. ReTail explicitly evaluates
feature availability and uses isolated frequency-controlled profiling; adding
a scheduler counter alone is not a novelty claim.
[ReTail](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf), sections IV.B–D.

Any fitted mapping needs separate development histories and untouched
confirmation histories, with campaign-level splits and retained failures.
Known suffixes or friend-host results used for development cannot also confirm
the guard. The friend's independent V31 remains pending and separate.

## Verification and decision

Close this bounded stage screen and preserve its negative result alongside
earlier timing, CPU and continuous-persistence screens. Six stage contract
oracles pass. All 54 outcomes, raw seals, calibration reconstruction, chronology,
ordinary comparator reconciliation and exact recomputation verify. The three
earlier screen verifiers and current manuscript-integration verifier also pass.
No new method, causal explanation or fresh experiment is established.

```bash
python3 -B analysis/screen_stage_transfer_signal.py --verify
python3 -B -m unittest discover -s analysis -p test_stage_transfer_signal.py -v
```

[Numerical results](../analysis/runtime_io_stage_signal/20261010/screen.json),
[earlier timing/CPU assessment](runtime_io_prevalidation_signals_assessment_20261010.md),
[continuous-probe result](runtime_io_continuous_persistence_assessment_20261010.md).
