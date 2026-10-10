# Runtime/I/O v6 verification — 2026-10-02

Implementation and functional verification only. No component experiment,
confirmation pilot or full matrix was launched.

- Schema 7, new service image `quota-diagnostic-service:5`, build manifest sealed.
  Current Go source hashes match the manifest. Load generator image unchanged.
- 29 Python configuration/analysis tests passed, including balanced trial order,
  fixed workload, quiet-host refusal, PID-reuse-safe CPU deltas, mode mismatch
  rejection and prevention of component studies qualifying full collection.
- Pinned Go 1.26.1 service tests passed, including combined, runtime-only and
  custom-only real-HTTP fixtures. Each fixture exercises success including ID
  zero, actual queue rejection, timeout with eventual worker completion, and
  connection reuse. Runtime-only records no custom I/O events; custom-only
  opens no runtime writer. Existing pending-response stop protection passes.
- Exported combined fixture passed full request/scheduler analysis. Runtime-only
  passed scheduler chain/clock/capture-boundary checks. Custom-only passed
  lifecycle ordering, socket-write and outcome/worker association checks.
  Corrupt runtime clock anchors and missing custom rejection records were
  rejected. Evidence: `diagnostic/verification/runtime_io_v6_validation.json`.
- Host monitor smoke test captured three samples with process CPU deltas,
  monotonic interval lengths, and per-core utilization including CPUs 2 and 4.
- Python compilation, launcher help and shell syntax checks passed.

Read-only stack inspection of the retained v5 quiet trial identified about
54.11 summed goroutine-seconds of post-handler waiting in HTTP
`finishRequest → abortPendingRead → sync.(*Cond).Wait`. Recorder mutex stacks
accounted for approximately 0.0034 summed seconds in those same intervals.
These sums overlap across requests and are not wall-clock runtime or CPU cost.
They locate a wait path, not the cause of delayed background-read completion.
See `diagnostic/verification/runtime_io_v5_wait_stacks.json` for trace hash,
clock uncertainty, exact stacks and scope.

The unchanged failure-rate gate still applies to a future confirmation pilot.
Component mode comparisons have narrower evidence coverage and cannot authorize
full collection. Run instructions: [runtime_io_v6_commands.md](runtime_io_v6_commands.md).
