# Software audit and the next controlled change

2026-10-06. The original V20 and its repeat completed operationally; their
shorter-period performance results differ. Calling one run a failure and the
other a success obscures the question. The original penalty is a retained
observation, not evidence that collection crashed or the code changed.

## What was checked

The audit's [final report](../analysis/runtime_io_software_audit/audit-01/container_followup/report.json)
checks the complete saved service environment for all 48 original V20, cost
pilot and faithful-repeat trials. Every entry matches except the deliberately
varied WORKER_YIELD value. GODEBUG is empty throughout; no GOGC, GOMEMLIMIT,
CPU-feature override or other environment difference was found. Image identity
and recorded Go version match. Earlier audits also established identical
workload, packaged binary and shared source hashes and replayed CPU/deadline
arithmetic from raw records.

The retained prepared Go source was copied into a separate audit directory.
Production sources were not edited. Go vet passed. All 22 top-level tests ran
twice with the race detector using Go 1.26.1 and passed, with no race warning.
Added checks cover concurrent requests, cancellation, queue accounting,
snapshots, fully drained resets, yielding, GOMAXPROCS=1/2 and independent Python
SHA vectors for 1, 10 and 44,000 iterations. The original tests also cover HTTP
response behavior and tracing.

The first host execution's full race suite failed its trace-start tests: those
tests expect to create `/runtime.trace`, which a normal user cannot create at
the host root. This is preserved in the initial audit report and logs. The
same source, with no trace-code change, passed the complete suite when executed
as a statically linked race test binary inside an isolated offline container
supporting that path. V20 disables runtime/custom tracing. This audit harness
failure is not an explanation of its period reversal.

Passing is limited to exercised paths. See [Go's race detector](https://go.dev/doc/articles/race_detector).
It does not prove absence of bugs, exclude ordinary runtime effects, or observe
historical GC/scheduler activity. No programming-language defect has been found.

## Why identical code can behave differently

The SHA loop and request count may be unchanged while the amount and timing of
runtime maintenance, goroutine execution and physical CPU delivery differ.
The worker allocates reply channels and records; the handler allocates/encodes
responses and grows event slices. Reset clears event slices and changes the
clock origin after a checked drain, but does not create a new process or force
GC. Allocation/automatic-GC policy is therefore a specific testable software
hypothesis, not a demonstrated cause. No comparable GC decomposition exists
for the original run. Runtime scheduling and hardware execution conditions
remain separate or interacting possibilities.

## Ready diagnostic, still unrun

The [GC probe protocol and external launch commands](runtime_io_gc_probe.md)
are prepared in `analysis/runtime_io_gc_probe/generation-01`. It retains the
original executable and compares default automatic memory cleanup with cleanup
disabled, at both CPU periods. No performance profiler, hardware counters or
GC logging is added. Desktop/power conditions stay unchanged within the test.

Nine targeted Python tests passed. Four two-second actual-service functional
controls passed raw replay, environment/hash/resource checks and cleanup. Both
default-GC controls recorded one GC cycle during the functional workload and
additional metrics-read stress; both GC-off controls recorded zero. Functional
memory peaks were 8.9-12.4 MiB. The manipulation is therefore operationally
verified, but it has no performance result yet. All sixteen performance trials
remain unrun. Preparation is sealed with the 115 retained sources and six new
files; original preparation and results remain unchanged.

The primary prediction is that disabling cleanup changes the *20-versus-100 ms
CPU/job contrast*, not merely that removing cleanup saves CPU generally. The
protocol separates that interaction from a general GC saving and reports
whether the original default-GC penalty returns. Four balanced blocks cap the
run; there is no retry-until-positive rule. Expected duration is roughly one to
two hours, depending on settling.

If the contrast changes, GC/allocation policy contributes under the tested
conditions; object lifetime/cache effects still prevent attributing the entire
change directly to collector CPU. If it does not change, that narrows this
hypothesis under the tested conditions, without ruling out other runtime
effects. If the original penalty is absent again, the historical cause remains
unresolved regardless of a detected interaction. No novelty or paper-pivot
claim follows automatically.
