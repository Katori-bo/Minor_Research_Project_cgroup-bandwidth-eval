# Runtime/I/O v8 yield study verification — 2026-10-02

Preparation is complete. No performance session or quota workload was launched.
The planned fresh directory is `results/diagnostic/runtime-io-v8-yield-1`.

- Built and sealed `quota-diagnostic-service:7` under schema 9, pinned Go 1.26.1.
  Service image ID:
  `sha256:e70ca5b9070342ea1ed7b0f787fa76a73fe37f4a8e0fb1e1150ae4a66b057f2f`.
  Load-generator image/source is unchanged. Build manifest:
  `diagnostic/bin/build.json`.
- Go service tests passed during the build and a separate fresh fixture export.
  Yield off/on completes identical hashes and replies, drains the worker, and
  reports its setting. The environment accepts only empty/default, `0` and `1`;
  an ambiguous value fails. The service calls `runtime.Gosched()` after reply
  publication, without modifying the hash loop or adding a scheduling counter.
- Real HTTP fixtures retain ID zero, a queue rejection, a client timeout with
  eventual worker completion, connection reuse and final trace flushing in
  yielding combined and yielding custom-only modes. Combined traces were parsed
  and analyzed with the pinned Go tool. Missing/incorrect yielding metadata fails
  validation. Existing default combined memory/file and reduced runtime/custom
  fixtures also validated. Raw exports:
  `diagnostic/verification/runtime-io-v8-yield/`. Hashed verification:
  `diagnostic/verification/runtime_io_v8_yield_validation.json`.
- All 44 Python tests passed. New tests verify balanced 16-trial factorial order,
  all four cells per block, fixed workload/custom recording, strict treatment
  evidence, correct interaction signs and missing-value handling, incomplete or
  duplicate block refusal, schema-8 read-only compatibility, report generation,
  eight traced cleanup analyses and inability to unlock full collection.
  Earlier exact cleanup stack/census handling tests remain covered.
- All six retained v7 pilot attempts and all 16 retained v6 component attempts
  revalidated with no issues after the schema-9 compatibility change. Their
  completion files, raw data and source snapshots remain intact.
- Python compilation, shell syntax and runner help checks passed. The launcher
  shares the experiment lock through collection and analysis, validates build
  and frozen provenance, and retains the existing compact quiet-host guard.
  Temperature sampling and output at the first/minute samples are unchanged.

The next action is the external-terminal launch in
[runtime_io_v8_yield_commands.md](runtime_io_v8_yield_commands.md). Functional
checks establish readiness to test, not that yielding improves scheduling or
that runtime tracing is suitable. The 16-trial study writes no passing pilot
gate, cannot launch full collection, and leaves the qualification thresholds
unchanged.
