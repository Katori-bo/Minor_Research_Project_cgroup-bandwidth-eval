# CPU-period cost pilot: verified findings

Reviewed 2026-10-06. Generation-02 completed all sixteen trials. The frozen
decision remains **effect_not_reproduced**. No additional collection or protocol
change was performed for this review.

The shorter period's earlier CPU penalty did not merely become too uncertain to
detect: its direction reversed in every counter-off block. This limits the
cross-session repeatability of the earlier observation and stops the proposed
cost-mechanism investigation at its first research gate.

Follow-up: the [launch/code audit](runtime_io_period_reversal_audit.md) treats
host conditions and pilot setup differences as competing candidates. Neither
has been established as the cause. A separate original-runner V20 repeat is
prepared in generation-04; no repeat performance trial has been launched.

## Verification and reproducibility

The offline reviewer checks the preparation, fixture, report and trial seals,
replays all sixteen pilot trials from raw records, compares saved derivations,
and recomputes the frozen decision. Four known-work counter fixtures passed.
All 108,688 offers completed; there were no rejections or other failures and
all met the 1,000 ms target. The sixteen prior V20 trial seals were also checked.

The reviewer separately joins raw client/server records for the eight pilot
counter-off trials and eight V20 yield-off trials to apply the same fixed busy
window in both sessions. These cross-session comparisons are descriptive.

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 analysis/review_period_cost_pilot.py
```

See [review data](../analysis/runtime_io_period_cost_pilot_review/20261006/report.json)
and the [frozen pilot report](../analysis/runtime_io_period_cost_pilot/generation-02/analysis/1791227322172383591/report.json).
The original Markdown report omits the counter-off period contrasts; the JSON
contains them under `unobserved_period_effect`.

## The counter-off result

Both cells use the original executable, one worker, GOMAXPROCS=1, yield off,
the same burst arrivals and 0.5 CPU allowance. Only period/quota change.
Values below are means of four equal-offer trials; p99 is a mean of trial p99s.

| Quantity | 100 ms | 20 ms |
|---|---:|---:|
| Aggregate CPU per completed computation | 3.643 ms | 3.591 ms |
| Certainly backlogged completion capacity | 148.11 jobs/s | 151.33 jobs/s |
| Offers completed within 500 ms | 73.43% | 83.58% |
| Mean successful E2E p99 | 746.0 ms | 635.4 ms |
| Backlogged CPU consumption | 0.49982 cores | 0.50010 cores |
| Mean application queue waiting | 257.2 ms | 226.9 ms |

The frozen paired-block analysis gives a 20-versus-100 ms CPU/job change of
**-1.44%**, exploratory 95% interval **[-2.02%, -0.84%]**; busy capacity changes
by **+2.17% [1.04%, 3.31%]**. Thus the gate requiring a CPU increase of at least
2% and a capacity loss fails. The gate's label does not mean collection failed.

The 500 ms success difference is descriptively +10.15 percentage points. The
same small improvement in capacity can have a much larger deadline effect when
the 169.815 jobs/s burst rate exceeds either capacity. This is consistent with
the queue account; a new held-out predictive queue model was not tested here.

## Measurement feasibility

Counters are technically usable: scope, events, coverage, fixtures and raw
validation passed. The observer screen nevertheless fails. Turning counters on
is associated with CPU/job increases of 1.13% [0.81%, 1.45%] at 100 ms and 1.42%
[0.81%, 2.03%] at 20 ms. Neither interval fits the frozen +/-1% margin. Deadline
stability also fails; at 20 ms, capacity and p99 equivalence checks fail too.
These comparisons do not isolate pure counting overhead from host variability.

With counters on, instructions/job change by only -0.0049%; cycles/instruction
change by +0.184%. Effective cycles/user-CPU changes by +0.64% [-0.25%, 1.54%]
and backlogged CPU consumption by +0.048% [-0.139%, 0.236%]. Precision passes the
pilot's aggregate screen, but no decomposition signal meets its 2% threshold.
This does not identify extra software work, slower execution or reduced CPU
delivery as the cause of the V20 penalty: that penalty is absent here, and V20
has no comparable hardware counters. Whole-service counts are not per-SHA costs.

## What differs from V20

Kernel, boot ID, topology, executable/image hashes, offered-arrival vector and
recorded power configuration match. A different build, reboot, arrival schedule
or selected power profile therefore does not explain this particular reversal.
Host operating conditions still differ substantially:

| Recorded host quantity | V20 | Cost pilot |
|---|---:|---:|
| Initial idle temperature baseline | 48.5 C | 57.1 C |
| Mean recorded temperature during monitoring | 61.6 C | 69.5 C |
| Plasma shell CPU, percent of one core | 0.20% | 12.06% |
| KWin CPU, percent of one core | 0.50% | 7.52% |

Temperature and process CPU summaries use all 80 saved warmup/arrival monitor
samples per trial, pooled across sixteen trials. Process CPU is interval CPU
time divided by monitored elapsed time, not a screenshot of lifetime `%CPU`.
ChatGPT presence is false in every saved sample in both sessions. Quiet-app
checks do not guarantee low desktop activity. Higher temperature and desktop
activity are candidate explanatory variables, not demonstrated causes or proof
of thermal throttling. Snapshot MHz values cannot establish worker clock speed.

Applying V20's identical fixed busy window (seconds 6.5-9.5 of each ten-second
cycle) to yield-off/counter-off trials gives:

| Session | 100 ms capacity | 20 ms capacity |
|---|---:|---:|
| V20 | 151.04 jobs/s | 138.67 jobs/s |
| Cost pilot | 148.10 jobs/s | 151.19 jobs/s |

The reversal therefore survives use of the same capacity estimator. V20's
CPU/job values were 3.630/3.833 ms, versus 3.643/3.591 ms here. It is mostly
the 20 ms cell that changes across sessions, while the 100 ms deadline outcome
also worsens. Counters-off still includes the pilot's external control/helper
and resource sampling, so host state is not the only cross-session difference.

## Research decision

Pause the proposed explanation of a reproducible shorter-period CPU penalty.
The remaining question is which conditions make the period contrast change
direction. Audit/control desktop activity, thermal starting state and pilot
harness differences before interpreting another mechanism measurement. If a
further experiment is justified, predeclare one bounded, counter-off comparison
under matched host conditions, with explicit host-activity acceptance criteria;
do not rerun until a desired sign appears. Qualify the observer separately before
using counted results to explain a reproduced cost penalty.

The earlier yielding intervention and queue reconstruction remain evidence
about V20. This cost pilot does not repeat yield-on cells, so it cannot overturn
that intervention comparison. The queue account explains deadline loss given
observed capacity; it does not predict capacity independently from the nominal
quota. The paper must report the new non-reproduction and narrow the claim
that a shorter period necessarily raises CPU/job or lowers throughput. No causal
mechanism, research novelty or publication contribution is established here.
