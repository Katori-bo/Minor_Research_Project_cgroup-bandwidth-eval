# V27 revision 2: restore the client clock contract

7 October 2026. This is a software repair for the unchanged
[V27 composition protocol](runtime_io_v27_protocol.md), prepared as
`analysis/runtime_io_v27/generation-02`. Generation-01's failed runtime
preparation and all source/build/record seals remain preserved.

## Recorded failure

The V27 revision-01 client was copied from the base diagnostic client, omitting
`build_parallelism.client_source` instrumentation and `parallelism_clock.go`.
Its first 15-second functional case completed 999/999 offers successfully, then
raw replay failed with missing `clock_anchors`; `client_test_start_ns` was also
absent. Preflight and functional containers/cgroups were removed successfully.
No measurement lifetime or composition trial was started. See the
[sealed failure review](../analysis/runtime_io_v27_failure_review/20261007/report.json).
Synthetic raw fixtures supplied clocks and did not exercise actual client JSON.

## Software repair and verification

Separate V27r2 Python/client sources retain the original frozen files. Restore
the exact clock instrumentation transformation used to build the retained V12
client, plus its verified prepared clock helper and tests. The repaired client
records three start and three stop brackets, server clock generations and its
monotonic test origin. Clock requests occur before arrivals and after client
drain, as in V22/V23/V25/V26. Do not reconstruct missing clocks in old recordings
or accept absent fields. Add an explicit report-contract error on absent clocks.

Keep the unequal-cycle scheduler, HTTP request/tracing logic and offer vectors.
Build with retained Go 1.26.1 and CGO_ENABLED=0. Freeze source snapshots, diff,
compiler/binary hashes, unit/race/vet output, all eight binary schedule exports
and compiled-client JSON integration receipts. The latter run the real binary
against a local HTTP software stub for short steady/bursty cases, then pass its
unaltered JSON through clock mapping and the complete per-request stage join.
The stub performs no SHA work and uses no Docker, quota or native sampling.
It is a software contract check, not runtime or scientific qualification.
The same integration check must reject revision-01 output with missing clocks.

Check six distinct brackets, matching clock generation, bracketing before
offers/after drain, clock-uncertainty budget, exact offers, HTTP outcomes,
per-request stage identities and readiness for raw replay. Synthetic missing-
clock checks alone cannot replace testing output from the compiled binary.
Retain all existing decision/uncertainty/lifecycle tests and failed-run seals.

## Unchanged science and external execution

Copy the original trial order, rates, windows, thresholds, uncertainty analysis,
functional schedules, service/gate/native binaries, resource/host controls,
retry limits and stopping rules exactly. Add only software-revision and failed-
generation provenance to the new design. No data from generation-01's functional
case enter the composition analysis. Generation-02 uses the same repaired
client binary in every treatment/observer arm.

Runtime resources and all four functional cases must qualify again externally,
with the desktop app fully quit. Successful offline JSON checks do not qualify
actual container timing or the scientific workload. Preparation <=600 s;
collection <=5,400 s; active trial <=360 s; cleanup grace <=120 s; independent
post-collection analysis <=600 s. Stop after the sixteen-trial report regardless
of its result. No automatic next generation, calibration or deadline validation.
Use the [revision-2 execution guide](runtime_io_v27r2_execution.md).
