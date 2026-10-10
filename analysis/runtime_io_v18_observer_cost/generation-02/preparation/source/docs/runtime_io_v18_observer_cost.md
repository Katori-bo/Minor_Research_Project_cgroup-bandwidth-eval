# V18 kernel observer cost pilot

This separate study asks whether kernel tracing changes the latency being measured.
It uses six matched pairs in the fixed order off/on, on/off, repeated three times.
The practical screen describes observer cost; it does not explain late responses.
Six pairs do not establish statistical equivalence.

## Commands and readiness

Run from the repository root under the original user identity. Choose a new generation
directory whenever implementation, collector, inputs, kernel, boot, or topology changes.
The runner never rebuilds the service or client. It copies the sealed retained gate,
original client and original packaged executable, checks the actual image executable,
and references the five already-passed bridge controls without rerunning them.

```bash
STUDY="$PWD/analysis/runtime_io_v18_observer_cost/generation-01"
python3 diagnostic/kernel_observer_cost.py prepare --directory "$STUDY"
python3 diagnostic/kernel_observer_cost.py verify-preparation --directory "$STUDY"
```

Preparation runs the deterministic protocol/parser/supervisor tests and freezes their
logs, sources, image inspection, binaries, full matrix, and capture limits. It does not
collect performance observations. The launcher remains gated until qualification passes.

Fully quit Codex/ChatGPT, then use an **external interactive terminal**:

```bash
./diagnostic/start_kernel_observer_cost.sh qualify "$STUDY"
```

Qualification performs two separate full-duration rehearsals, off then on, through
FIFO startup, warmup, reset, measurement, full drain, service exit, observer END and
detach. These are preparation evidence, never part of the six-pair pilot. It verifies
offered arrivals, client capacity, raw replay, host conditions, resource configuration,
clock bounds and cleanup. No twelve-trial batch follows automatically.

After reviewing qualification, launch the pilot explicitly from the external terminal:

```bash
./diagnostic/start_kernel_observer_cost.sh start "$STUDY"
# Explicit recovery after an interruption (same generation and baseline only):
./diagnostic/start_kernel_observer_cost.sh resume "$STUDY"
```

`qualify`, `start`, and `resume` in the Python CLI validate prerequisites and print
the external launcher command. The shell launcher authenticates sudo once locally.
It starts a bounded root supervisor under sleep inhibition. The supervisor forks
the worker, restores the original user's groups, UID, GID, home and user identity,
and connects it through an inherited socket pair. Neither credentials nor passwords
are passed to Codex or stored in evidence. Privilege does not depend on a sudo keepalive.

```bash
python3 diagnostic/kernel_observer_cost.py status --directory "$STUDY"
python3 diagnostic/kernel_observer_cost.py watch --directory "$STUDY"
python3 diagnostic/kernel_observer_cost.py stop --directory "$STUDY"
python3 diagnostic/kernel_observer_cost.py analyze --directory "$STUDY"
python3 diagnostic/kernel_observer_cost.py verify-completion --directory "$STUDY"
# Separate offline verification entry point:
python3 diagnostic/verify_kernel_observer_cost.py "$STUDY"
```

Do not open Codex during measurement. Progress in the external terminal shows order,
stage, temperatures and log location; `watch` shows the temperature baseline and
completed counts. `stop` verifies the original worker's UID and /proc start time
before signaling it. The root owner then cleans up its own container and probes.

## Frozen experiment and common overhead

Every trial uses the same original image, its `/server`, and retained load generator.
GOMAXPROCS=1, workers=4, queue=128, iterations=44000, service CPUs 2/4,
cpu.max=50000/100000, cpu.max.burst=0. Historical memory/PID limits remain
unlimited; the bridge fixture's memory=256m and pids=128 are not imported.
Warmup is 20 seconds; measurement is 60 seconds. Bursty traffic has mean 113.21 rps,
low/high 56.605/169.815 rps, a ten-second cycle, concurrency 512 and a five-second timeout.
All 6,793 measurement offers (including errors and cancellations) are retained;
the full relative arrival vector is verified against the retained client's integrated
rate formula and compared exactly within every completed pair.

Both arms use the same qualification mount and single-thread FIFO gate, original
service instrumentation, clock requests, host monitor and one-second thread snapshots.
Only the on arm attaches probes before gate release. The off arm has explicitly
unobserved kernel events and quota intervals, never inferred zero events.
Collector, supervisor, worker, client, monitor and progress run on CPUs 0/1.
Inventory, executable hashes and raw replay occur outside measurement.

AC/Balanced power, quiet host, the historical 600-second initial idle, stable
60-second thermal window, baseline temperature tolerance and full drain are retained.
Power/topology/kernel/boot identity and the qualification temperature baseline must
remain unchanged on resume. Completed valid trials are retained even if their effects
miss the screen. Invalid partial attempts remain sealed; only explicit resume creates
new attempts. Interruptions and interrupted pairs appear in the report.

## Root supervisor and cleanup

Only argument-free `create`, `release`, `observe`, `end`, and `finish` requests are
accepted. The supervisor derives the next arm and resource paths from the frozen
matrix, verifies attempt ownership/configuration, rejects extra fields and ordering
violations, and never accepts command strings, paths or PIDs through IPC. Docker
commands operate on the unique owned container identity. The experiment lock spans
settling, collection and cleanup. Disconnects, worker death, observer diagnostics,
early exits and timeouts invalidate the attempt and retain partial evidence.

The active-trial watchdog is 360 seconds, collector ceiling 300 seconds, and the
supervisor has bounded idle, IPC and overall lifetimes. Cleanup includes final service
exit, collector END, owned BPF program detach, owned container/cgroup disappearance
and unchanged root tracefs controls. A failed cleanup stays explicitly unverified;
`supervisor_exit.json` records whether ownership was safely released. Inspect failed
cleanup before resuming; no global tracing reset, arbitrary process kill or stale
resource removal is performed.

## Events, clocks and offline evidence

The separate collector preserves the bridge's probe set and event semantics with
1,024 map keys and 64 perf-buffer pages. stdout/stderr are actively drained; their
combined raw limit is 1 GiB per trial. An overflowing chunk is retained separately,
recorded as a violation, and invalidates collection. Evidence is never silently
truncated. At least 20 GiB free is required before launch and every active trial.

Replay rejects diagnostics, loss/count mismatches, malformed records, wrong CPU or
cgroup identity, map errors, unmatched thread/scheduler lifecycles and open quota
pairs. Wakeup origin CPUs are retained: IRQ/network wakeups can originate outside
the service cpuset; the target CPU and captured target TID must remain in scope,
as in the verified bridge. Throttle attempts remain separate from successful transitions. Per-CPU quota
intervals preserve overlapping uncertainty bounds without becoming a summed service
pause. A valid pilot capture can contain zero throttle transitions. Counters and events
are exported for their actual observation windows; bandwidth-period counters and
per-CPU transitions do not share a one-to-one count interpretation.

After warmup fully drains, reset establishes the measurement clock generation.
Three kernel/server anchors precede measurement and three follow full drain in both
arms; the client's own six anchors compose the mapping. One measurement generation,
zero time namespace offsets, kernel/server uncertainty at most 1 ms and composed
kernel/client uncertainty at most 2 ms are mandatory. Recorded request boundary
bounds must lie inside the on-arm capture. Publication and runnable readiness remain
unobserved, and failed/missing records retain explicit missingness.

Each trial seals raw outputs, identities, snapshots, namespace offsets, anchors,
counter brackets, environment, cleanup, classifications and completion metadata.
The independent offline command recomputes from raw trial files and checks frozen
inputs, per-arm configuration, paired arrival vectors, exported results and practical
screen. It can verify completed effects outside the margins; finite complete evidence
and a passing practical screen are distinct conclusions.

## Exports and screen

Analysis creates a new sealed report generation (earlier reports remain unchanged):
`requests.csv`, `trials.csv`, `pairs.csv`, `report.json`, and `report.md`.
Timely success uses all offered requests as denominator at 500 ms and 1,000 ms.
Failure fraction includes every unsuccessful client outcome. Successful-response p99
uses the nearest-rank formula and includes late/drained successes. CPU per completed
computation uses cgroup usage after reset through measurement plus full service drain;
warmup and final service exit are outside that bracket. Clock/control requests inside
the counter window are included equally in both arms.

Every pair must have absolute timely-success differences at most .01, failure
difference at most .001, on/off CPU per computation in [.95,1.05], and on/off
successful p99 in [.90,1.10], with complete evidence and finite comparisons.
The report retains all six paired effects and describes medians, minima, maxima
and sample standard deviations. Decisions are `incomplete_evidence`,
`effects_outside_margins`, or `within_margins_requires_review`.
Passing never establishes equivalence or authorizes causal attribution/intervention.
After observer cost review, a separate analysis can examine whether quota intervals
and service execution overlap recorded computation-to-handler delays.
