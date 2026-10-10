# V13 preparation verification — 2026-10-03

**Status: implementation and functional verification complete; performance observer qualification pending.**

The [executable protocol](runtime_io_v13_completion_protocol.md) and [current research plan](current_research_plan.md) define the next decision. Preparation was performed with the desktop app open; no quota-controlled performance study was launched.

## Implemented artifacts

- [Isolated builder](../diagnostic/build_completion.py): retains V12 service/client as the legacy arm and builds two stock-Go recorder variants without changing legacy service sources or sealed sessions.
- [Service boundaries and buffers](../diagnostic/completion_service.go): record mutex acquisition/storage and publication brackets, with bounded ID storage, overflow/duplicate errors, cancellation conservation and reset/drain synchronization.
- [All-offered analysis](../diagnostic/completion_analysis.py): retains both declared deadlines, external failure/late outcomes, clock ambiguity, publication/receiver overlap and missing server evidence. Screens paired trial blocks rather than treating requests as independent repetitions.
- [Study runner](../diagnostic/completion_study.py): four matched three-arm blocks, same client and schedule checks, frozen hashes, full inherited resource/environment validation, preserved attempts, explicit resume, sleep inhibition and read-only progress/temperature display.
- [Regression checks](../diagnostic/test_completion.py) and [Go checks](../diagnostic/completion_service_test.go).

## Checks completed

Both new images built with the retained digest-pinned Go 1.26.1 compiler and networking disabled during Docker build. Their build-time service Go tests passed, including the added cancellation/rejection, record conservation, boundary ordering, reset and invalid-ID cases. Logs: [locked](../analysis/runtime_io_v13_completion_build/locked_build.log), [bounded](../analysis/runtime_io_v13_completion_build/bounded_build.log). The exact legacy build verified before reuse.

Six short **unquotaed functional HTTP fixtures** passed: legacy/locked/bounded × GOMAXPROCS=1/2, six offered requests per fixture, valid request zero, full entry/worker/handler linkage and clock uncertainty below 1 ms. Sealed evidence: [functional_verification.json](../analysis/runtime_io_v13_completion_build/functional_verification.json), [build.json](../analysis/runtime_io_v13_completion_build/build.json). These are implementation fixtures, not evidence of deadline improvement under a CPU quota.

The diagnostic Python regression suite passed. The new tests cover missing/cancelled/rejected outcomes, deadline/clock ambiguity, concurrent sender/receiver timestamp overlap, malformed/missing/duplicate markers, buffer errors, stable CSV fields, separate observer/recorder screens, fixed matched matrix, isolated source preparation, quiet-host refusal before spawn, frozen evidence tampering and 12-trial progress reporting. An offline end-to-end export test used the functional HTTP fixtures and synthetic CPU counters in a temporary directory to verify report/CSV export and completion-seal refusal after tampering; it cannot support a performance conclusion.

The prepared build verified after all functional checks. The V13 study plan resolves to 12 uniquely identified trials with GOMAXPROCS=1, four workers and unchanged quota/period/workload; only recorder arm/image and block/order differ. Quiet-host safeguards remain enabled.

## Remaining evidence

Run the [quiet-window collection](runtime_io_v13_completion_protocol.md#quiet-window-launch-and-progress), then inspect the matched report and practical observer screen. Marker/bookkeeping and recorder costs have not yet been measured under quota. Exact runnable readiness, instantaneous quota balance and per-request kernel throttle/off-CPU intervals remain unqualified. A passing discovery screen permits preparation of Step 2; it does not prove equivalence, a scheduler defect, policy benefit or novelty.
