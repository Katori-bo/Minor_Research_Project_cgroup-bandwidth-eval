# Pre-restart system record and remaining reversal questions

Saved 2026-10-07 before the user's planned restart. No power/CPU settings were
changed, no app was stopped, and no performance experiment was launched.

## Saved record

Use the [final pre-restart snapshot](../analysis/runtime_io_system_state_snapshots/1791343349016869707-pre-restart.json),
its [SHA-256 receipt](../analysis/runtime_io_system_state_snapshots/1791343349016869707-pre-restart.sha256),
and [exact collector source](../analysis/runtime_io_system_state_snapshots/1791343349016869707-pre-restart.collector.py).
Earlier capture attempts are also retained; the final record is the reference
for the command below. The first sandboxed capture explicitly records unavailable
system-bus/Docker queries; subsequent captures used unrestricted read access.

The final capture began at 2026-10-07 03:22:22 UTC (08:52:22 IST). Boot ID:
`4dd475b5-ebf2-4155-be33-81effdc05269`; recorded uptime approximately 74.97 hours.
Kernel: `7.2.8-arch1-2`. CPU driver/mode: `amd-pstate-epp` / active. Desktop and
platform profiles: balanced. CPUs2/4 use powersave with balance_performance EPP,
boost enabled and bounds 1,108,930–4,280,985 kHz. This is the automatic state,
not the pilot's constrained state.

Boost clarification, checked 2026-10-07: boost permits execution above the CPU's
nominal frequency; enabling it is permission, not evidence that the worker
actually ran at a particular boosted speed. The original V20 generation03,
cost-pilot generation02 and faithful V20 generation04 environment records retain
the same 1,108,930–4,280,985 kHz policy bounds, but do not record the boost flag.
Their selected saved environment/host/preparation records therefore cannot
directly establish its value during those historical measurements. The later
execution-state pilot and continuation explicitly record boost=1; their controls
leave boost unchanged and manipulate only frequency bounds. There is no recorded
off-to-on transition explaining the original reversal. A change in actual boost
behavior remains an unproved execution-state possibility. The constrained pilot
is not a dedicated boost-enabled/disabled crossover.

Definition reference: [Linux 7.2 AMD P-state boost and active-mode documentation](https://www.kernel.org/doc/html/v7.2/admin-guide/pm/amd-pstate.html).

The snapshot retains CPU topology, CPPC capability fields, microcode and BIOS
identification, CPU/idle/boost controls, selected scheduler/perf/VM controls,
GPU power-control state, cgroup-root controls, installed package versions,
enabled/running services, Docker version/driver/images/running containers,
repository revision/change listing and diagnostic/script source hashes.
Five-second samples retain process names/CPU/RSS, temperatures, instantaneous
frequency readings, idle counters, external-power status, load, memory, pressure
and aggregate CPU/interrupt records. General command arguments, process
environments and general user configuration contents are not collected.

All final command inventories and configuration reads succeeded; fixed controls
matched at the end of capture. Hash verification and comparisons distinguishing
unchanged records, transient-only changes, a changed CPU bound and an unavailable
profile read passed. These are snapshot/comparison checks, not performance tests.

The app was open during capture. This is an evidence snapshot, not a quiet
thermal baseline or a reproduction of the earlier performance sessions. The
short activity sample is descriptive. Root-only BPF/tracing/descriptor ownership
was not freshly audited; the earlier root inventory remains a separately dated
snapshot, not proof of current or post-restart absence.

## After restarting

Capture before changing the power profile, installing updates or intentionally
altering CPU settings, if practical. Ordinary reboot/login activity is expected
to differ and is recorded as context. Run:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/system_state_snapshot.py capture --label post-restart \
  --compare-before analysis/runtime_io_system_state_snapshots/1791343349016869707-pre-restart.json
```

This takes approximately 5–20 seconds, writes new timestamped snapshot/hash and
comparison files, and prints their paths. It never restores or writes settings.
Run it in the normal external terminal with system-bus/Docker access. If a read
fails, its coverage gap is retained rather than treated as proof of no change.
The matching app-open state is useful for descriptive comparison, but neither
capture establishes benchmark readiness. Keep the same collector source for
pre/post comparison; its archived copy is available above.

A post-restart performance result requires a newly prepared boot-valid protocol
and current observer evidence. Do not resume old preparations assuming boot-bound
checks still apply. The command above performs no benchmark and no reboot.

If later results change, compare configuration/version differences first, then
activity/thermal context and the new trial records. Reboot changes several
conditions together; a changed sign does not identify uptime itself or a specific
service as the cause. Unchanged recorded settings also do not prove identical
execution conditions.

## What remains for the reversal

| Open question | What is missing / what would distinguish it |
|---|---|
| What changed in effective execution while the large penalty occurred? | Qualified instruction/cycle measurements during a reproducible penalty, paired with delivered CPU. Current near-null counters cannot reconstruct the older uncounted state. |
| Did extra runtime work, stalls/cache effects, or execution-weighted clock behavior matter? | Separation of additional instructions from cost per instruction and execution rate in the penalty state. Requested speed bounds and instantaneous frequency samples alone do not identify historical worker clocks. |
| Did temporal CPU delivery matter despite similar average delivery? | An aligned scheduling/quota timeline during the effect. Average 0.5-core delivery cannot explain individual runnable delays or rule out different supply timing. Existing aggregate records are not that timeline. |
| Did collection/setup or preceding workload change execution state? | A controlled original-versus-added collection-context comparison if a substantial effect returns. Faithful V20 repeat already shows pilot-only collection is unnecessary for the later direction; the full-service observer's failed margin limits its counters. |
| Does reboot-reset state change the result? | Comparable new observations after reboot, then a targeted intervention if a useful difference appears. No controlled fresh-boot performance comparison has been run. The saved pre/post records are descriptive evidence, not a causal reboot experiment. |
| Why did one constrained counted cell report unusual system CPU? | That cell's anomaly remains unresolved; later automatic-state cells are not a replication of its conditions. |

The background-app crossover was cancelled and never run. GC and software audits
narrow particular explanations under tested conditions, without excluding them
historically. The evenly spread arrival proposal is also unrun; it addresses
backlog formation and would not by itself explain the CPU/job sign reversal.

No finite checklist can certify that every possible cause has been excluded.
The main missing evidence is measurement **while the sizable penalty exists**.
Until there is a promising new signal, retain this branch as unresolved and
prioritize the existing capacity/queue account and paper synthesis. This record
does not automatically authorize another sweep or performance batch.

See the [investigation catalogue](runtime_io_investigation_catalogue.md) and
[latest continuation findings](runtime_io_execution_state_continuation_findings.md)
for the full retained sequence and cross-session limits.
