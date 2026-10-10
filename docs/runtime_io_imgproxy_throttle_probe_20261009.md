# Separate imgproxy throttle-localization probe

The original twelve-service qualification stopped on p2_observed after one
measurement throttle. Keep its source, sealed bundle, raw data and failure intact.
The offline review is
`analysis/runtime_io_imgproxy_feasibility_review/20261009-generation01/report.md`.
This new engineering question is whether budget-counter updates occur during
idle background activity or the fixed offered workload, and which request
windows overlap those updates. This probe never passes the original qualification.

No image, operation, rate, quota, worker, GC or memory-free interval is tuned.
Reuse the frozen observed image and lifecycle safeguards. Resource limits remain
25 ms per 100 ms, burst zero, CPUs 2,4, GOMAXPROCS 1, worker 1, queue 128,
memory 512 MiB and pids 128. The source's default memory freeing every 10 seconds
is a candidate explanation, not an established cause; it remains enabled.

One preparation-only functional service verifies four offered image responses,
raw timing joins, actual packaged executable and client clock anchors. One separate
forensic service then has 40 seconds idle, 25 warmup offers at 5 req/s, and 200
measurement offers at 5 req/s. There are no retries or replacements. Ten seconds
of settling precedes startup. The inherited independent owner-death/service
watchdog has a 120-second active deadline; all subprocesses have bounded drains
and owned cleanup. Overall normal-path budget is 300 seconds with 120 reserved
for cleanup (privilege authentication occurs before execution).

The forensic client is a separate copy of the frozen Go client, adding two Linux
CLOCK_MONOTONIC reads bracketing its relative time origin. Request-body timing and
hash semantics are preserved. A Python counter sampler on the supervisor/client
CPUs 0,1 reads cpu.stat every nominal 4 ms with before/after monotonic bounds.
Its buffer is capped at 32,000 samples. Sampling errors, missing records and
output/clock inconsistencies make the diagnostic unavailable; evidence remains.

After traffic drains, retain CPU counters, the full timeline, and all 225 server
records before checking joins or classifying throttling. This addresses the
original collector's reporting limitation without changing that frozen collector.
Idle and measurement counter differences are reported separately. For every
positive nr_throttled update, report the interval between neighboring observations
and its possible or bounded overlap with request windows. Counter updates do not
provide scheduler throttle start/end timestamps; their localization is not a
causal attribution. Monitored timings are diagnostic and cannot qualify observer
overhead, establish absence of native parallelism, or confirm forecast transfer.
Zero observed throttles would not erase the original exit or prove none recur.

Requires an external normal-user terminal with Codex/ChatGPT closed and a fresh
read-only root observer inventory. It changes no host tracing controls. The
launcher and unique run directory reject resuming or overwriting the diagnostic.

Evidence: `analysis/runtime_io_imgproxy_throttle_probe/generation-01/`.
Launch: `bash diagnostic/start_imgproxy_throttle_probe.sh`.
