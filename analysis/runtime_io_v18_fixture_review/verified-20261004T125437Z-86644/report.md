# V18 bounded fixture review

Decision: **single_cpu_fixture_observation_qualified**.

Reviewed capture: `/home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/analysis/runtime_io_v18_kernel_fixtures/20261004T125437Z-86644`. All sealed file hashes and frozen source hashes
match. Replaying the frozen analyzer against each raw capture reproduces its
saved validation and the collection summary. All three observers/workers exited
successfully; their recorded owned-probe detach and temporary-cgroup removal
checks passed. Root tracing controls match before/after.

| Fixture | Received events | Process CPU ms | Closed quota intervals | nr_throttled |
|---|---:|---:|---:|---:|
| sleep | 19 | 1.035 | 0 | 0 |
| cpu | 43 | 599.265 | 0 | 0 |
| quota | 292 | 947.061 | 18 | 18 |

The quota fixture recorded 190 throttle attempts, but only 18 successful, closed
quota-state intervals. Their duration midpoint median is 49.461342 ms,
range 45.431497–50.456269 ms. The widest duration bracket is
21.19 microseconds.
These bounds describe function-transition brackets, not total request clock error.
The kernel counter records 18 throttled periods in this single-CPU fixture; this
agreement is a cross-check and is not a general equality for multi-CPU operation.
Sleep and uncapped CPU controls have no quota intervals. Emitted/received event
counts agree and observer diagnostics are empty in all three captures.

The result verifies detection of known scheduler/quota events on CPU2. It does
not explain any HTTP deadline miss, resolve rebuild/clock effects, or qualify
observer overhead. Per-CPU quota state is not a whole-service stop. Publication
and Go handler runnable-readiness remain unobserved. The first failed capture
remains invalid and unchanged.

Next gate: a bounded original-service compatibility check on CPUs2,4, including
existing/new thread coverage, initial state, exact leaf cgroup and uncapped
ancestors, and mapping to retained service/client clock bounds. Then freeze and
collect six matched tracing-off/on pairs in a separate quiet window. Only after
that cost screen can kernel overlap be interpreted as service contribution evidence.
No performance batch was launched by this review.
