# Pending-preemption observation probe

Eight validated trials of the same candidate runtime, with observation disabled/enabled. Runtime tracing and worker yielding were off. The original workload and limits were fixed.

| Block | Arm | Pending flags seen | Ordinary fairness reached | Global work selected | Regular local selected | Sole runnext selected | Successful p99 ms | Rejection | Timeout |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | control | 0 | 0 | 0 | 0 | 0 | 2114.402 | 4.106% | 0.000% |
| 1 | observed | 173 | 161 | 158 | 1 | 2 | 3825.003 | 2.296% | 0.000% |
| 2 | observed | 104 | 94 | 90 | 1 | 3 | 4021.204 | 0.618% | 0.000% |
| 2 | control | 0 | 0 | 0 | 0 | 0 | 3928.802 | 1.943% | 0.000% |
| 3 | observed | 109 | 97 | 94 | 0 | 3 | 4114.628 | 2.163% | 0.000% |
| 3 | control | 0 | 0 | 0 | 0 | 0 | 4030.097 | 1.678% | 0.000% |
| 4 | control | 0 | 0 | 0 | 0 | 0 | 3999.456 | 3.974% | 0.044% |
| 4 | observed | 108 | 98 | 95 | 1 | 2 | 4111.501 | 0.486% | 0.088% |

## Observer perturbation screen

Original descriptive numeric screens: PASS. Median throughput ratio: 1.0164. See observer_screens.json for CPU, client cost, p99, failures and coverage checks.

The purpose is to measure whether the previously tested policy executes, not test a new correction. Counters cover reset through the final snapshot, including control requests and drain. They are aggregate atomic samples, not a per-request queue history or proof of which ready HTTP request was selected.

Nonzero ordinary/global/local counts establish that those paths execute in the observer arm. Zero or rare pending signals would show that this workload hardly exercises the proposed correction. A path executing while delays remain would weaken its sufficiency, not exonerate the runtime. If the observer changes outcomes beyond the original screens, its timing cannot be substituted for the unobserved control.

No solution claim, qualification gate or larger collection is created.
