# V24 sampler revision 2: preserve the question, repair collection timing

Prepared 2026-10-07, before generation-02 measurement. This is an instrumentation
revision of the [original V24 question](runtime_io_v24_frozen_question.md).
Generation-01 remains incomplete and is retained without replacing samples,
changing acceptance, or resuming collection. Its sources remain unchanged.

## Failure and selected repair

The first small probe-off trial passed. Both attempts of the first small
probe-on slot each contained one read longer than the frozen 2 ms bracket:
3.408707 ms and 3.326864 ms at sample index3015, approximately61 seconds into
the recording. The sole technical retry was exhausted. All owned cleanup
receipts passed. Four short runtime preparation cases passed but each had only
103–152 readings; they did not exercise a full recording's retained allocations.
See the separately sealed failure review at
`analysis/runtime_io_v24_failure_review/20261007/report.json`.

An offline allocation replay using the original parser and a synthetic regular
file produced a generation-1 Python garbage collection lasting2.958 ms, enclosed
by a3.008 ms read. Its sample index differed from the saved failure. Garbage
collection is therefore a plausible cause; the original trace cannot attribute
the specific pauses. Revision2 removes this source of pauses prospectively,
without claiming that ordinary OS scheduling or file-read delays cannot occur.

The new sampler suspends automatic cyclic garbage collection only inside its
existing110-second capture bound. It retains acyclic dictionaries containing
integer counters; reference counting remains active. It restores the previous
GC state after closing the timed recording, including on an exception. JSON
serialization happens after that restoration. There is no service-runtime GC
change, root operation, priority change, realtime scheduling or host tuning.

Schema2 records the sampler revision, prior/restored GC state, and per-generation
collection counts before and after capture. The independent verifier requires
GC disabled at the capture endpoint, unchanged collection counts, and restored
prior state. It still rejects any read over2 ms. New filenames `v24r2_*` retain
the original revision1 modules and their hashes for independent historical replay.

## Scientific contract retained

The original design seal, service image, server/client/gate binaries, source
work sizes, traffic offsets, job counts, quota/period, affinities, warmup/drain,
12-slot order, settling, cleanup and retry limits are unchanged. The original
counter20 ms interval and110-second bound, maximum2 ms reads,50 ms gaps and60 ms
boundary enclosures remain unchanged. CPU accounting still uses conservative
counter/time/completion bounds without interpolation or sample deletion.

All six off/on pairs must pass the original observer-comparability screen.
All six probe-on trials at both sizes must meet the original phase-state,
5% cost separation and[0.48,0.52] busy CPU-delivery rules. The new metadata makes
sampler behavior auditable; it does not convert the failed generation into
scientific evidence or automatically establish the state-mixing explanation.

## Software evidence and next launch

The repair requires a complete110-second recording on a synthetic regular file
with the real sampler executable and20 ms sleeps, pinned to the normal sampler
CPUs0/1. Every read must pass the unchanged bracket checks, all adjacent gaps
must be<=50 ms, and the recording must contain at least5000 samples. A retained
6000-record allocation test additionally checks that no GC scan occurs. Unit
checks cover restoration on success/error, metadata tampering, unchanged timing
rejection and the original scientific decisions. The full recording and its
source hashes are independently replayed and sealed; preparation and launch
refuse a missing, failed or source-mismatched software receipt.

This software evidence uses no real cgroup, Docker service, sudo or workload.
The completed recording retained5441 readings over110.0165 seconds. Maximum
read width was0.642202 ms, p99 was0.317750 ms, and maximum adjacent gap was
21.461897 ms. No GC collections occurred during capture. All29 revision2 unit
checks and94 combined V22/V23/V24/revision2 checks passed. The sealed recording
is at `analysis/runtime_io_v24_sampler_repair/20261007`; this is software
readiness evidence only.

It cannot qualify real cgroup-read latency or prove harmless sampler overhead.
The next external launch repeats actual image/resource and four functional
checks, obtains a fresh observer ownership review and performs the entire new
12-trial schedule. It does not reuse generation-01's accepted slot or receipts.
Any remaining timing failure stays a technical failure under the same bound.

See the [new external launch guide](runtime_io_v24r2_execution.md).
