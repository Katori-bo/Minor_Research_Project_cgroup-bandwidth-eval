# V18 bounded two-CPU and original-service compatibility gate

This is a functional qualification, following the [verified primitive fixtures](../analysis/runtime_io_v18_fixture_review/verified-20261004T125437Z-86644/report.md).
It does not qualify observer cost, estimate repeatable service latency, or launch
the proposed twelve-trial performance pilot. Preparation can occur during normal
desktop use. Root recording is launched externally with local sudo authentication.

## Fixed scope

Five bounded cases: one known two-process quota workload, followed by original
service GOMAXPROCS=1/2 with uncapped and 50,000 us/100,000 us CPU allowance.
All use CPUs2,4; collectors/client use CPUs0,1. Burst credits are zero. The known
workload pins one child to each service CPU and burns for 1.8 seconds of wall time,
then joins and idles. Require positive quota intervals on each CPU and at least
one certainly overlapping pair, retaining intervals separately.

Service cases use the exact original retained image and its packaged `/server`;
the original server and client hashes are checked against the retained V16 build
seal. No service rebuild or inline marker is introduced. Service workers=4,
queue default=128, INSTRUMENT=1 and the original Go 1.26.1 metadata/records remain.
Uncapped HTTP cases offer 227 requests over two seconds at a steady 113.21 requests/s.
The revised capped cases offer 453 requests over two seconds at 226.42 requests/s,
44,000 SHA iterations, concurrency=64, timeout=5 seconds and client tracing enabled.
These are functional coverage settings, not the bursty sixty-second cost protocol.
The capped fixture's rate was doubled after the first root G1 capture used only
962,067 us of CPU and recorded no throttled periods or quota-state intervals.
Its positive-control failure remains a failure: having a CPU limit alone is not
proof of quota exhaustion. Capped and uncapped functional cells now use different
loads, so their response distributions are not a performance contrast.
Non-recording HTTP preflights retain before/after kernel CPU counters and require
positive throttled-period counts for capped fixtures before another root capture.
Each service cgroup has memory.max=256 MiB and pids.max=128; the native control has
pids.max=32. Every observed ancestor must be uncapped or the gate stops.

## Initial state and thread identity

A small statically linked C launcher starts single-threaded, emits READY, then
blocks opening a per-case FIFO before executing Go. A self-issued SIGSTOP is
unsuitable for container namespace PID 1, as the startup preflight showed.
The known native workload uses SIGSTOP outside the container. The supervisor verifies that sole blocked
host TID, exact cgroup membership/affinity, zero prior throttled periods, effective
CPU restrictions and zero time-namespace offsets. It seeds that host PID in the
observer, waits for BEGIN and records its owned BPF IDs, then releases the FIFO
with one verified byte (or resumes the native workload).
The launcher executes the original `/server`; its code does not remain resident
in the service. A read-only `/qualification` mount holds the launcher and FIFO;
`/server` is not bind mounted. Its actual executable hash and link are checked.

This startup barrier/mount is declared setup, not evidence that this setup is
performance-neutral relative to V12. If used in the later cost pilot, both off/on
arms must share it and the same before-warmup checks. No additional request path
bookkeeping is introduced. The collector tracks all forked descendants, wakeups,
switches and exits from the known initial target. Live `/proc` thread snapshots
are checked against the captured fork/exit lifecycle with enumeration-time bounds.
Unknown identities, missing final switches or open lifecycles stop qualification.
Thread identity still does not establish Go goroutine runnable readiness.

## Clock joins and coverage

Kernel records explicitly use nsecs(monotonic), native controls CLOCK_MONOTONIC
and the Python supervisor time.monotonic_ns. The retained server/client
runtime.nanotime1 and time.now disassembly is saved during preparation and checked for the
Linux clock ID 1 path through vdsoClockgettimeSym and the syscall fallback.
Host/service time-namespace offsets must be zero; the client inherits the host's
zero offsets. No reset is made during a case.

Three host-to-existing-`/clock` round trips occur before load and three after drain.
Intersect their kernel-minus-server intervals: require agreement and width <=1 ms.
Retain the original six client/server anchors and their <=1 ms mapping. Compose
the two offset intervals conservatively, requiring <=2 ms kernel/client uncertainty.
The unit-slope/common CLOCK_MONOTONIC assumption is explicit. Keep direct kernel
bounds for existing computation completion and handler execution, all offered
outcomes and deadline-crossing classes. No publication timestamp is added.

Require every clock bracket and observed request boundary certainly inside the
capture, full workload drain, no observer diagnostics/loss/count mismatch and
closed per-CPU quota pairs. Positive capped cases must actually exercise throttling;
uncapped cases must have none. No handler-readiness inference or HTTP-delay cause
is accepted at this stage. Overlapping per-CPU quota states are never summed into
whole-service lost time. Ancestor restrictions matter because the
[kernel bandwidth hierarchy](https://docs.kernel.org/scheduler/sched-bwc.html#hierarchical-considerations)
can throttle a child independently of its own quota.
Service CPU counters end after drain and before container stop, which may remove
its runtime cgroup. They cross-check active work; they do not include the final
exit tail and are not required to equal the count of captured per-CPU intervals.

## Bounds and cleanup

Scheduler tracepoints and four typed quota-function probes match the primitive
fixture semantics. Map capacity=1024, perf buffer pages=64 per CPU, probe cap=12.
No stacks, uprobes, unsafe helpers, pinned maps or global tracing edits. Probes fire
on global events before filtering; their service overhead remains unqualified.
Each observer self-exits after 25 seconds and the supervisor has attach/work/drain/
shutdown limits and a 360-second overall watchdog. An early collector exit fails
coverage. The known worker owns a separate process group; cleanup stops its child
work too. Docker cleanup targets only newly created UUID-named containers. Owned
BPF IDs must disappear after detach. Only an empty owned native cgroup is removed.
Recorded root tracing controls must match before/after. Preserve failures and seals;
do not rerun a valid capture merely to improve its result.

## Reviewed checkpoint and continuation

Capture `20261004T135227Z-94326` has three valid cases: known two-CPU quota work
and both uncapped service cases. The G1 capped case failed the positive control;
G2 capped was not run. All attempted cases report clean detach/cgroup cleanup and
unchanged root tracing controls. The old capture and frozen source remain sealed.

Revised assets retain a reference to that checkpoint's full seal. Before collection,
the runner rechecks every old sealed file and frozen source, requires unchanged
collector/analyzer/native-gate/original-image/client semantics, and replays all
three successful controls against their validations and summary. Only the runner,
launcher, tests and declared fixture protocol can differ. Original image, server, client,
gate and kernel identities must match the newly prepared inputs. The earlier
failed case is checked but never imported as a successful positive control.

A continuation records explicit case origins and collects **only the two capped
HTTP cases** under the revised load. Retained controls are not new measurements or
independent replications. Both source generations remain attributable, and the
references are rechecked after collection. A stale seal, changed measurement
semantics or failed old cleanup stops continuation. The strict positive-control,
loss, thread, clock and cleanup gates remain unchanged.

## Launch after preparation

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_kernel_service_bridge.sh
```

Run as the normal user in an external interactive terminal. Enter sudo credentials
only there. Allow roughly two to five minutes; normal desktop activity is allowed
for this functional gate. It writes a new timestamped directory under
`analysis/runtime_io_v18_service_bridge/` and prints its summary path. Return its
output for raw/seal review. A successful gate does not launch the quiet-window
tracing-off/on cost pilot. That final implementation/protocol remains pending.
