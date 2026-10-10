# V18 bounded kernel fixtures

Prepared 2026-10-04 after installation and sealed capability review. This verifies
the external observer's basic event meanings and cleanup, not its performance cost
on the original service. The twelve-trial observer-cost batch remains unprepared.

## Verified installation and host capabilities

The [capability review](../analysis/runtime_io_v18_kernel_capability_review/20261004T123651Z/report.md)
verifies the installation seal, exact nine newly installed packages, unchanged
existing package versions and matching current/sealed BTF. All scheduler events
needed for these fixtures exist. The apparent trace-cmd failure was its version
command returning 255 with a valid banner; the corrected check retains that exit
code and recognizes only this specific version response. No historical seal changed.

There is no CPU-bandwidth throttle tracepoint in this inventory. The throttle-named
kyber and vmscan events describe other subsystems and are excluded. Running-kernel
BTF listings expose `throttle_cfs_rq(struct cfs_rq *)` and
`unthrottle_cfs_rq(struct cfs_rq *)`. Matching kernel-image disassembly is retained
in the review; actual fentry/fexit attachment subsequently passed in the repaired
capture reviewed below.

## Three positive/negative controls

| Fixture | CPU allowance | Known workload |
|---|---|---|
| sleep | Uncapped | 0.6 seconds sleep |
| cpu | Uncapped | 0.6 seconds CPU work |
| quota | 50,000 us / 100,000 us, burst=0 | 1.8 seconds CPU work |

Each creates one new uniquely named child cgroup under `/sys/fs/cgroup`; it edits
only that child's resource files. Existing CPU-controller activation is required;
the runner does not enable controllers or change parent limits. Work is restricted
to CPU2, pids.max=16 and memory.max=256 MiB. A short companion thread exercises
fork/wakeup/exit accounting. Collector processes use CPUs0,1. These are functional
fixtures under normal desktop use, not a thermal-controlled performance comparison.

The worker starts blocked on an input barrier. It moves into the fresh unthrottled
cgroup before attachment. Once the observer reports BEGIN, the supervisor identifies
its BPF program IDs through its own file descriptors and releases the worker.
Workload and observer source snapshots, hashes, identities, actual settings,
raw events, diagnostics, CPU counters and validation remain in the new output.

## Event semantics and acceptance

Scheduler switch records reconstruct thread scheduled residency, including kernel
and interrupt time. They are not exact instruction-execution time or Go goroutine
state. Thread IDs and all companion thread creation/exits must conserve. Retain
worker process CPU time and CLOCK_MONOTONIC timestamps independently.

Function entry/exit bracket quota-state transitions on a particular CPU runqueue:

- Throttle entry alone is an attempt. Require a true return **and** throttled=1 at
  exit to open an interval; false return/state=0 does not open one.
- Require prior throttled=1 at unthrottle entry and throttled=0 at exit to close it.
  A return without this state transition is not a successful unthrottle.
- Keep onset/end lower and upper bounds. Pair by exact cgroup/CPU/runqueue identity;
  reject unmatched, duplicate or ambiguous state transitions. Do not add overlapping
  per-CPU intervals into a process-wide pause.

These points follow the [upstream bandwidth implementation](https://raw.githubusercontent.com/torvalds/linux/v7.2/kernel/sched/fair.c),
with running-kernel BTF/disassembly and fixtures retained to check this host.
Quota-state onset may precede deferred task throttling; it does not itself establish
that every thread stopped immediately. Scheduling and quota-state evidence must be
interpreted together. Hierarchical and multi-CPU qualification is still required
before observing the real service on CPUs2,4.

Require exactly one BEGIN/END, workload timestamps inside that lifecycle, exact
emitted/received record counts and no warning/error/lost/dropped diagnostics. No
unknown lines are silently discarded. Both uncapped fixtures require no successful
quota intervals and zero nr_throttled. The capped fixture requires at least three
closed intervals, at least three throttled periods and at least 300 ms process CPU
time. These aggregate checks are a cross-check, not request-level attribution or
an assertion that per-CPU event counts equal nr_throttled exactly.

The same named CLOCK_MONOTONIC domain is used for kernel and fixture timestamps.
This does not yet qualify mapping to the original Go service/client clock brackets.
Any invalid event, loss, identity, timing or cleanup check stops the fixtures.

## Scope, bounds and cleanup

The observer uses scheduler events plus four typed function probes. Hooks execute
when those events/functions fire globally, but retained events are filtered to the
fixture thread set and exact child cgroup. Future overhead qualification must assess
the resulting observer effects. No stacks, service uprobes, unsafe helpers or map
pinning are used. Map capacity=128, perf buffer pages=64 per CPU, probe cap=12.

Each capture self-exits after eight seconds. The supervisor also enforces attach,
worker and shutdown timeouts, plus a 150-second overall watchdog. On failure or
interruption it stops only its own subprocesses, verifies its owned BPF programs
detach, and removes only its empty cgroup. Nonempty groups or cleanup failures are
retained and reported for review; it never recursively deletes cgroups.

Root ftrace controls are saved before/after and must match. No root tracefs reset,
sysctl, security-policy, boot, persistent service or sudoers change occurs. Every
output includes attempts and a hash seal, even when possible validation fails.
Results under `analysis/runtime_io_v18_kernel_fixtures/` are new evidence; V12–V17
sessions are untouched.

## External-terminal command

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_kernel_fixtures.sh
```

Run as the normal user. Sudo authenticates in that terminal; its cached credential
does not carry to the assistant's noninteractive process. Allow roughly one or two
minutes for compilation and checks. Successful output names `summary.json` and
all three fixture validations. Return for review before preparing the real observer
off/on pilot. A pass does not automatically launch or qualify that pilot.

Preparation checks: fourteen Python guard/evidence tests, shell syntax, native
bpftrace syntax formatting and ordinary unquotaed sleep/CPU worker checks pass.
Actual root probe attachment and quota fixtures remain unrun at preparation.

## First attempt and filter repair

The first root attempt, `20261004T124634Z-86037`, attached the observer and
captured the sleep fixture, then failed strict diagnostic validation. Ordinary
absent-key value lookups in membership filters generated warnings under `-k`;
discarded map-delete return values also produced compiler warnings. It is retained
as an invalid attempt with its original source, diagnostics and seal. Cleanup
reported no errors, owned probes detached, the cgroup was removed and root trace
controls were unchanged. No quota workload or performance trial ran.

The repaired script uses explicit `has_key` membership predicates and checks
map-delete results. Missing required quota-entry state emits an error; errors and
lost events are still rejected. The API follows the installed
[bpftrace 0.27 map helpers](https://bpftrace.org/docs/release_027/stdlib).
A short native present-key/absent-key/delete test must pass without diagnostics
before the three workloads begin. A new invocation creates a new source snapshot
and evidence directory; it does not replace or reinterpret the failed attempt.
The repaired root capture subsequently passed and is reviewed below.

## Successful capture and offline verification

The user completed `20261004T125437Z-86644`. Its [derived review](../analysis/runtime_io_v18_fixture_review/verified-20261004T125437Z-86644/report.md)
verifies every sealed file/source hash and replays the frozen analyzer against
raw events, diagnostics and worker records, reproducing all saved validations.
The native map API guard and all three fixtures passed. Recorded owned-probe
detach and cgroup-removal checks passed; root tracing controls match before/after.

Sleep: 19 events, 1.035 ms process CPU and no quota intervals. Uncapped CPU:
43 events, 599.265 ms process CPU and no quota intervals. Quota: 292 events,
947.061 ms process CPU, 190 throttle attempts and 18 successful closed intervals;
nr_throttled=18. Interval duration midpoints have median 49.461342 ms and range
45.431498–50.456269 ms. The widest duration bracket is 21.19 microseconds;
this is not an end-to-end request timestamp error bound.

Decision: **single_cpu_fixture_observation_qualified**. Service thread/CPU coverage,
ancestry and clock mapping remain to be checked before the observer-cost pilot;
see the [next gate](runtime_io_v18_kernel_observation_plan.md#next-preparation-bounded-service-compatibility).
No HTTP mechanism or observer cost is established, and no performance batch ran.
The earlier failed capture remains invalid and unchanged. The fixture protocol
snapshot in each sealed capture remains its original version.
