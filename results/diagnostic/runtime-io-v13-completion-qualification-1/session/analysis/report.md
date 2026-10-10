# Completion-boundary observer qualification

Four matched three-arm blocks at GOMAXPROCS=1, four workers, 50 ms / 100 ms quota, zero burst credits. All offered requests remain in the 500 ms primary and 1,000 ms guardrail denominators.

| Block | Recorder | Timely 500 ms | Timely 1,000 ms | Failures | Late successes: work before 500 ms | CPU/job us |
|---|---|---:|---:|---:|---:|---:|
| 1 | legacy | 64.228% | 100.000% | 0.000% | 506 | 3667.75 |
| 1 | locked | 58.472% | 98.822% | 0.000% | 431 | 3730.33 |
| 1 | bounded | 57.574% | 98.734% | 0.000% | 427 | 3734.70 |
| 2 | bounded | 60.268% | 99.426% | 0.000% | 429 | 3708.94 |
| 2 | locked | 60.194% | 99.558% | 0.000% | 441 | 3711.56 |
| 2 | legacy | 68.939% | 100.000% | 0.000% | 470 | 3635.24 |
| 3 | locked | 61.328% | 99.647% | 0.000% | 424 | 3707.04 |
| 3 | legacy | 68.173% | 100.000% | 0.000% | 519 | 3642.88 |
| 3 | bounded | 61.210% | 99.617% | 0.000% | 424 | 3701.37 |
| 4 | bounded | 59.753% | 99.499% | 0.000% | 407 | 3708.05 |
| 4 | legacy | 69.984% | 100.000% | 0.000% | 526 | 3636.03 |
| 4 | locked | 59.105% | 99.161% | 0.000% | 419 | 3729.97 |

Practical observer decision: **marker_effect_requires_review**.

observer_screen.json retains paired deltas and their block median/range; four blocks cannot establish statistical equivalence. Legacy-to-locked checks the combined marker/bookkeeping observer. Locked-to-bounded checks dynamic shared event storage. No intervention or larger batch is launched by passing this screen.

requests.csv retains failed, cancelled, late and drained outcomes, missing worker/handler events, clock bounds, publication/deadline overlap and publication-to-resume bounds. Sender completion can follow handler resume. Handler execution is not a runnable-readiness timestamp. Recorded mutex intervals include scheduling and off-CPU delays. Host/cgroup samples and CPU counters remain sealed, but do not identify instantaneous remaining quota or request-level throttle intervals. Further runtime/kernel observation requires a separate qualification.

[Frozen protocol](../source/docs/runtime_io_v13_completion_protocol.md)
