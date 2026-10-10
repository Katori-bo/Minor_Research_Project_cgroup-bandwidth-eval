# Tools, collection and the period reversal

Read-only audit and proposed next comparisons, 2026-10-06. No package was
installed/removed, no setting changed and no benchmark launched. The proposed
comparisons below are not prepared run protocols.

## New timeline evidence

The local `/var/log/pacman.log` records the tool transaction on
2026-10-04 at 17:51:58-59 +05:30. It installed perf, trace-cmd, bpftrace, bpf,
bcc, clang and dependencies. The log ends with that transaction; it does not
record a later package transaction between the following preparations:

| Preparation | Manifest timestamp, +05:30 |
|---|---|
| Original V20 generation-03 | 2026-10-05 19:21:54 |
| Cost pilot generation-02 | 2026-10-05 23:27:56 |
| Faithful V20 generation-04 | 2026-10-06 09:18:10 |

Thus these tools were already installed before original V20. Their installation
is not a treatment separating the compared sessions. This does not exclude a
later invocation, persistent attachment or operating-state consequence.
The manifest times identify preparations; they are not trial start times.

## Collector evidence

The pilot launches a privileged helper and per-trial perf/cat processes even
in counter-off cells. Its off mode uses `perf stat -n`, which starts no counters
but still runs perf. See the [perf manual](https://man7.org/linux/man-pages/man1/perf-stat.1.html).
The pilot's existing on/off screen gives approximately 1.1-1.4% CPU/job increases
with counters on and fails its declared observer-equivalence margin. These are
associated differences, not a clean attribution of all variation to counting.

All sixteen saved pilot detach receipts report perf return code zero. The helper
closes/reaps per-trial processes, checks owner identity and has bounded lifetime;
the finish path returns after the final detachment. These receipts establish
recorded per-trial termination, not a complete system-wide attachment inventory.

The faithful V20 repeat launches neither that helper nor perf counters and still
has the later period direction. Pilot-specific collection is therefore not
necessary for the later result. The original warmup/pilot difference also exists
before per-trial counter attachment. A complete account must fit both clues.
Historical collector cleanup evidence cannot replace a live inventory of other
processes, tracefs instances, enabled events/probes and pinned/attached BPF objects.

## Efficient investigation rather than component-by-component searching

First audit persistent collection state and settings without the benchmark.
Record the package timeline, tool/daemon processes, tracefs instances, events,
probes and BPF attachments, and relevant settings. Attribute ownership before
changing anything. A stopped frontend process alone does not establish that
every tracing attachment is gone. Do not uninstall tools as a first intervention:
the installed state was shared, and removal changes more than active collection.

If an unexplained active collector exists, target that verified attachment first.
Otherwise, a bounded grouped crossover can directly test the broader collection
explanation under the same current host session:

| Cell | CPU period | Collection context |
|---|---|---|
| A | 100 ms | Original V20 collection only |
| B | 20 ms | Original V20 collection only |
| C | 100 ms | Same base plus the defined added collector/helper context |
| D | 20 ms | Same base plus the defined added collector/helper context |

The exact added bundle and preceding fixtures/timing must be specified before
running. Turning off hardware events while leaving the helper is not the lean
condition. Both paths need the same outcome measurement and resource/workload
contract; verify process termination and persistent state on transitions.
Use two balanced blocks as a short screen, retaining opposite orders and all
results. Eight 20-second warmup/60-second measurement cells contain about eleven
minutes of workload, with initial idle, settling, drain and checks additional.
No total runtime is promised before preparing the actual protocol.

The primary question is whether the 20-versus-100 CPU/job contrast changes with
the collection bundle. A consistent substantial interaction makes the bundle
worth splitting into smaller groups. No interaction narrows current direct
collection effects; it cannot exclude a persistent historical side effect.
Two blocks can remain inconclusive and should not be extended until a desired
sign appears. The existing original-runner repeat makes this a lower-priority
test unless the state audit reveals new collector evidence.

An orthogonal fixed-SHA control can test the CPU-execution explanation using the
same work function, periods and placement with HTTP/runtime workload reduced.
If the period-sensitive efficiency change appears there too, request handling
is not required for that effect. If it appears only in the full service, inspect
the service/runtime path next. A negative control does not exclude a mechanism
that specifically requires the service's workload; lower-power and scheduling
behavior can differ in the control.

Only after finding a reproducible effect should qualified hardware counters
separate additional instructions, slower execution and lower CPU delivery.
Existing counter fixtures pass, but observer equivalence does not; do not treat
the present collector as harmless. Sampling/profiling should be added only when
its overhead is qualified for the signal being investigated.

The efficient strategy is to isolate a responsible class with grouped,
reversible comparisons and then split that class. It is not exhaustive toggling,
and no single retrospective test can prove an unrecorded historical cause.

Related saved reviews: [reversal audit](runtime_io_period_reversal_audit.md),
[faithful repeat](runtime_io_v20_repeat_findings.md), and
[literature synthesis](runtime_io_period_literature_synthesis.md).
