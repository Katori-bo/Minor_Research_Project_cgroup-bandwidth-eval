# Stock bursty parallelism preparation verified

Verified 2026-10-03. No quota measurements were launched and the eight-trial study has not started.

The [runner](../diagnostic/parallelism_study.py), [analysis](../diagnostic/parallelism_analysis.py) and [protocol/commands](runtime_io_v12_parallelism_commands.md) implement the candidate question selected in the [prior-work review](runtime_io_prior_art_review.md). Both arms use the same stock Go 1.26.1 service image; only explicit GOMAXPROCS changes. Four application workers and the half-CPU quota remain fixed.

## Verification evidence

- All **108 Python diagnostic tests passed**, including interval ambiguity, absent/rejected/cancelled entries, request ID zero, clock drift/reset/width, conservative remedy screens, a zero-success trial, immutable source/build/matrix/fixture checks, shifted time namespaces and quiet-host refusal. The added progress-display tests cover trial counts, phases, live/baseline temperatures, interrupted processes and closing the display without stopping the experiment.
- **20 service and six load-generator Go tests passed** in the isolated build, including new all-outcome entry and clock checks. The final identical image build reused those successful Docker layers. Original execution logs remain in the preserved initial preparation directory: [service](../analysis/runtime_io_v12_parallelism_build_initial/service_build.log), [client](../analysis/runtime_io_v12_parallelism_build_initial/loadgen_build.log).
- Two real HTTP fixtures, one at each processor setting, each retained all six offered requests including ID zero. They used ten hash iterations/request, a 300 ms arrival window and **no CPU quota**, so they are functional checks rather than experimental results.
- Final fixture clock uncertainty was **115,567 ns** for one processor and **109,846 ns** for two processors, below the declared one-millisecond technical limit. No midpoint clock estimate replaces these brackets.
- The retained compiler image, stock service/client image IDs, source/prepared-file hashes, client binary and functional evidence were verified through Docker. [Build manifest](../analysis/runtime_io_v12_parallelism_build/build.json), [functional verification](../analysis/runtime_io_v12_parallelism_build/functional_verification.json).
- The original diagnostic service/client sources and images were not replaced. Initial preparation was preserved when finalizing an analysis edge case; final outputs use the separate `runtime_io_v12_parallelism_build` directory.

## Interpretation boundaries

This build measures scheduled/dispatch-to-handler-entry delay and full service outcomes. It does not record exact network-ready time, queue residence, scheduler choices or continuous CPU execution. All-outcome entry storage adds application instrumentation in both arms. Stock describes the runtime, not an observation-free application.

Unknown entries remain unknown and widen conservative bounds. Successful latency remains conditional on success, and throughput completed inside the measurement window is separate from cohort/drain throughput. CPU cost can change effective capacity even under the same nominal quota. The final report therefore tests whether an existing remedy suffices and selects a next action; it cannot independently establish a new fairness mechanism or novelty.

Allow 45–90 minutes for the external-terminal collection, including initial idle and settling. Use the [launch instructions](runtime_io_v12_parallelism_commands.md); the workflow retains all attempts, stops after eight trials plus analysis and starts no further experiment.

The `watch` command refreshes progress and temperatures every five seconds in a separate read-only process pinned to the client/monitor CPUs. The collector updates the count immediately after each validated trial and retains completion/temperature summaries in its launch log. No service/client binary, workload parameter, thermal acceptance policy or analysis screen changed for this display update.
