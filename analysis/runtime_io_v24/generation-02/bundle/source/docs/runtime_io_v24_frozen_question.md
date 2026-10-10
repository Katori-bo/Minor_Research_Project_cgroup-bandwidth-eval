# V24: test whether whole-cohort CPU/job mixes different service states

Revision 1, 2026-10-07. This mechanism experiment follows V22/V23. It is fixed
before any V24 collection. The unattended preparation is entirely offline;
runtime resource/functional qualification remains mandatory at the next launch.

## Question and competing explanations

Does whole-cohort cgroup CPU/completion overstate CPU/completion in continuously
backlogged windows, while actual CPU delivery in those busy windows stays near
the declared 0.5 CPU? If so, combining busy throughput with whole-cohort CPU/job
mixes different operating states. The alternatives include substantially
different actual busy CPU delivery, insufficient state separation, sampling
perturbation, measurement uncertainty or failure to reproduce the cost shift.

V23's four calibration trials provide an exploratory lead. Linear interpolation
of old one-second monitor labels suggests busy CPU/completion of approximately
3.29 ms (small) and 6.49 ms (large), versus whole-cohort 3.59/7.02 ms and
low-phase 4.80/9.03 ms. Busy delivery appears near 0.5 CPU. The old monitor lacks
actual read timestamps and has rounded epoch labels, so these are approximate
selection evidence, not confirmatory phase measurements. Preserve the separate
capacity-mismatch review. No per-job CPU attribution or scheduler cause follows.

## Retained contract and fixed order

Use the exact original V20 generation-03 server/loadgen/gate and image,
Go 1.26.1, one worker/GOMAXPROCS=1, queue128, yield off, service CPUs2/4,
client/controller0/1, cpu.max=50000 100000, cpu.max.burst=0 and original
memory/PID defaults. No rebuild, profiling, runtime trace, BPF or host setting
change. The existing iterations URL parameter selects 44k/88k SHA work.

Both sizes use canonical 10-second cycles with five seconds low/five high.
Small offers 56.6/169.8 jobs/s, 6,792 jobs in 60 seconds. Large offers
28.3/84.9 jobs/s, 3,396 jobs. Both schedule 298,848,000 SHA iterations.
Each trial has the same size-specific 20-second warmup, full drain, empty reset,
60-second measurement and full drain. Retain concurrency512/timeout5 seconds.

The treatment is a new counter sampler off/on. The existing one-second host
monitor stays present in both. Twelve trials form three blocks, each with
small off/on and large off/on pairs:

1. small off, small on, large on, large off;
2. large off, large on, small on, small off;
3. small on, small off, large off, large on.

All three repetitions at each size are required. No data pooling can rescue a
failed size or observer pair. This is a mechanism experiment, not a new
prospective forecast-validation batch; V22/V23 remain the prediction evidence.

## New bounded counter measurement

The normal-user sampler runs on CPUs0/1 and reads only the owned service's
existing cpu.stat every20 ms. Each read has host CLOCK_MONOTONIC before/after
timestamps. It starts before warmup and stops after full measurement drain,
with an independent110-second process bound. Record its own CPU time and
command/identity. It issues no target HTTP requests and changes no counters.

Fixed measurement windows, repeated for k=0..5, are:

- busy: [6.5+10k,9.5+10k) seconds;
- low: [1+10k,4+10k) seconds.

Each phase totals18 seconds. Busy windows require admitted-not-started queue>5
throughout every clock-admissible placement; low windows require queue<=5.
Low means lightly backlogged, not a claim that no computation occurs.

Join the retained client/server/host anchors under the existing unit-slope,
same-host clock assumption. At each uncertain boundary, take the last counter
read guaranteed before the earliest possible boundary and first read guaranteed
after the latest possible boundary. Monotonic counter values enclose the true
value; subtract opposite bounds for each interval and sum all six intervals.
No interpolation is permitted. Bound completion counts across the same shared
server-origin interval. CPU/completion bounds divide usage bounds by opposite
count bounds. Include quota-period/throttling, user/system counters as diagnostics.

Counter reads must have width<=2 ms; adjacent measurement read gaps<=50 ms;
each pair enclosing a boundary must span<=60 ms. Counter keys must match and
all values remain nonnegative/monotonic. Inadequate coverage is a technical
failure. Phase-state ineligibility is retained as a scientific failure, without
choosing different windows. This is aggregate phase CPU per completion, not
an isolated job's SHA CPU demand: HTTP, scheduler, GC and kernel work remain
included. Boundary work can straddle windows; three-second repeated intervals
and retained uncertainty constrain but do not eliminate that accounting issue.

## Frozen decision rules

First screen measurement perturbation in every six size/block off/on pairs:
absolute busy-capacity difference<=2% of off capacity, whole CPU/job
difference<=2% of off CPU/job, and all-offer500 ms miss difference<=1 pp.
These are engineering comparability screens, not statistical equivalence tests
or proof of zero overhead. Failure yields `observer_effect_unresolved`.

Then require all six probe-on trials to have eligible busy/low phases and:

1. the lower bound of whole-cohort CPU/job divided by busy CPU/completion>=1.05;
2. the lower bound of low CPU/completion divided by busy CPU/completion>=1.05;
3. the entire busy delivered-CPU interval inside [0.48,0.52].

All checks at both sizes plus the observer screen yield
`phase_cost_explanation_supported`. Complete evidence without these requirements
yields `phase_cost_explanation_not_fully_demonstrated`, retaining every failing
check and narrower result. Partial schedules yield `incomplete`. No result is
declared novel automatically. The5% cost and CPU-delivery margins are selected
after exploratory V23 review and frozen before V24, not tuned after collection.

Matched-window CPU capacity 0.5/(busy usage/completions) is an accounting
diagnostic. If measured busy delivery equals0.5, it equals busy completions/time
algebraically. Do not advertise this identity as a new independent predictor
or a validated correction algorithm. A successful result identifies a scoped
state-mixing failure mode; it does not isolate spinning, GC, frequency, HTTP or
a kernel bug. An intervention on one such mechanism would be a later test.

## Runtime qualification and bounds

Offline preparation snapshots sources/design/binaries and runs synthetic
software checks only. It deliberately does not inspect Docker or run workloads.
The next external launch first verifies the bundle, creates an unreleased
resource preflight, then four short functional/cancellation cases covering both
sizes with the new sampler. These are deferred; failure blocks measurements.
After that preparation, require a fresh read-only root observer inventory and
ownership review. Its local sudo authentication occurs only when the user runs
the prepared command. Workload collection runs as the normal user.

Retain topology/power/thermal controls, initial600-second idle, per-trial settling
>=60 seconds, stable60-second windows, temperature range<=2 C, slope<=1 C/min,
baseline tolerance3 C, timeout1200 seconds, exact client IDs/offsets,
zero drops/missed arrivals, dispatch p99<=2 ms, client/server clock<=1 ms,
host/client composed clock<=2 ms, at least80 host-monitor samples and scoped
container/process/cgroup cleanup. Fully quit Codex/ChatGPT for runtime preparation
and collection. Boot/source/setting changes stop measurement.

Bound workload collection to60 minutes including initial settling and12 trials,
with120 seconds cleanup grace. Bound runtime preparation separately to10 minutes
with120 seconds cleanup grace. Each active trial retains a360-second watchdog.
Permit at most one technical retry across the twelve measurement slots; preserve
failed attempts, never replace an accepted or adverse trial. No automatic resume
after interruption. Offline analysis runs after the measurement watchdog is
disarmed and cleanup is complete, with its own10-minute subprocess bound. A
measurement time-limit interruption still leaves an incomplete result; it does
not earn an extension or alter the original bound.

Expected quiet collection is approximately50–55 minutes from V23 slot timings;
runtime qualification and final verification add several minutes. Thermal or
technical delays can exhaust the bound. Preserve incomplete evidence.
