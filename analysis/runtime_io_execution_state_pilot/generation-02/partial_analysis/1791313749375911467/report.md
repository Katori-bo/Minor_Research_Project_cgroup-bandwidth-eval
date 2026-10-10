# Partial execution-state pilot review

incomplete_pilot_feasibility_demonstrated_no_large_interaction_in_complete_block

Twelve completed measurements pass independent raw replay. The thirteenth failed before workload startup; three were unrun.

One complete interaction block; reverse block has only constrained cells. The historical large penalty was not reproduced. No equivalence, exclusion of all execution-state mechanisms, or historical causal attribution. Whole-session host JSON was truncated after monitor SIGKILL; trial-local sealed control/power coverage remains verified. Cycles/user CPU second is not direct clock measurement; one counted reverse cell has a materially changed user/system CPU split.

| Block | Condition | Counters | CPU/job, 20 vs 100 ms | Capacity | Instructions/job | CPI | Effective user cycle rate |
|---|---|---|---:|---:|---:|---:|---:|
| 1 | automatic | False | -0.1962% | +0.0878% | unmeasured | unmeasured | unmeasured |
| 1 | automatic | True | -0.6747% | +0.6292% | +0.0008% | +0.3834% | +1.2927% |
| 1 | constrained | False | -1.0107% | +1.0414% | unmeasured | unmeasured | unmeasured |
| 1 | constrained | True | -0.5181% | +0.3885% | +0.0009% | +0.1290% | +0.6146% |
| 2 | constrained | False | -1.3148% | +1.2871% | unmeasured | unmeasured | unmeasured |
| 2 | constrained | True | -1.5454% | +1.5537% | +0.0008% | +0.0504% | +7.1880% |

The first-block speed intervention reduced the effective user cycle-rate proxy by 23.63% at 100 ms and 24.14% at 20 ms. All four first-block observer checks and the two available reverse-block checks passed the 1% practical margins.

First-block CPU/job interaction: -0.8161% counters off, +0.1576% counters on. Neither meets the predeclared 2% practical signal.

The final thermal window was steady: mean 56.933 C, range 0.125 C, slope -0.0987 C/min. It was 5.788 C below the automatic-mode baseline 62.721 C, outside the +/-3 C band. Increasing the timeout alone does not guarantee returning to that band.

Original controls were restored. The failed cell created no container or cgroup.

Caution: b2_F recorded 5.463% system CPU, versus approximately 0.23–0.46% in other counted cells. Its +7.188% cycles/user CPU-second period contrast is sensitive to this changed denominator; it must not be labeled a direct frequency increase under fixed clocks. Instructions and CPI remain nearly unchanged.

The whole-session sampler exited -9 and its JSON ends inside a record. The parsed prefix has 4,931 complete records ending just after the final settling began, so it cannot establish background activity during the subsequent temperature drop.

Recommendation: retain this as an informative incomplete pilot. Measurement feasibility is supported in the completed block, but the tested speed intervention did not reproduce the old period penalty. No automatic rerun or filling missing cells across sessions. A formal two-block interaction claim would require a new complete controlled comparison after addressing baseline drift; this is not necessary just to decide that the current pilot provides no promising large interaction signal.
