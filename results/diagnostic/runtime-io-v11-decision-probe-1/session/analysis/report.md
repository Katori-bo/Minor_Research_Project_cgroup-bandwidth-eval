# Scheduler choices ahead of delayed HTTP handlers

Eight validated trials with the same candidate policy. Runtime tracing and worker yielding were off. Only the bounded decision recorder differed. Counts cover capture start through drained stop, including control and drain.

| Block | Arm | Events | Matched pre-handler waits | Ready-wait p99 ms | Successful p99 ms | Rejection | Timeout |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | control | 0 | unavailable | unavailable | 3340.622 | 2.561% | 0.000% |
| 1 | observed | 34630 | 763 | 3924.900 | 3904.851 | 0.000% | 0.000% |
| 2 | observed | 34863 | 780 | 4018.310 | 4114.125 | 0.000% | 0.177% |
| 2 | control | 0 | unavailable | unavailable | 4338.915 | 0.044% | 0.221% |
| 3 | observed | 34664 | 863 | 3220.334 | 3637.509 | 2.384% | 0.044% |
| 3 | control | 0 | unavailable | unavailable | 2733.273 | 2.119% | 0.088% |
| 4 | control | 0 | unavailable | unavailable | 4136.381 | 0.000% | 0.044% |
| 4 | observed | 34812 | 872 | 3115.319 | 3935.584 | 2.075% | 0.000% |

Original descriptive observer screens: PASS. Inspect observer_screens.json for CPU/job, client CPU/request, successful p99, failure and coverage checks. Throughput and all failures remain in trials.csv. Four pairs are descriptive.

| Trial | Request | HTTP G | Ready wait ms | Dispatches ahead | Forced selections ahead | Final source |
|---|---:|---:|---:|---:|---:|---|
| decisions_b1_observed | 413 | 1673 | 4202.865 | 2200 | 0 | fair_global |
| decisions_b1_observed | 1624 | 2367 | 4016.453 | 2196 | 3 | regular_local |
| decisions_b1_observed | 1625 | 2364 | 4012.387 | 2191 | 3 | regular_local |
| decisions_b2_observed | 443 | 1693 | 4318.038 | 2311 | 1 | global_batch |
| decisions_b2_observed | 444 | 1643 | 4314.595 | 2300 | 1 | fair_global |
| decisions_b2_observed | 1610 | 2398 | 4101.155 | 2218 | 4 | regular_local |
| decisions_b3_observed | 1554 | 2387 | 3406.082 | 1796 | 4 | fair_global |
| decisions_b3_observed | 1559 | 1938 | 3405.325 | 1791 | 1 | fair_global |
| decisions_b3_observed | 1575 | 2225 | 3320.342 | 1827 | 6 | regular_local |
| decisions_b4_observed | 470 | 1696 | 4416.610 | 2407 | 0 | global_batch |
| decisions_b4_observed | 504 | 1768 | 4219.920 | 2314 | 0 | regular_local |
| decisions_b4_observed | 471 | 1731 | 4210.561 | 2271 | 0 | fair_global |

scheduler_attribution.json preserves selected G identities, sources and pending/fairness flags, plus per-request dispatch counts by role/source. Only network wakes whose first running segment reaches a handler marker are associated. Earlier connection cleanup must finish before the wake; ambiguous reuse is retained separately. Control waits are unavailable, not zero.

Recorder timestamps describe observation sites, not continuous CPU execution or exact queue residence. A selection may be diverted before execute; unmatched dispatches have no source claim. The origin of a preemption signal is unavailable. Equal boundary timestamps are reported as ambiguous. The longest examples overlap and their counts must not be added.

If the recorder fails the original perturbation screens, its timings cannot replace the control. Activation with delays does not establish sufficiency. No new correction, solution claim, qualification gate or larger collection is created.
