# Runtime/I/O v7 verification — 2026-10-02

Implementation and functional verification only. No v7 performance pilot or full
collection was launched. Memory buffering remains a candidate instrumentation
intervention; its effect on the v6 rejection problem is unverified.

- Built and sealed `quota-diagnostic-service:6` under schema 8 with pinned
  Go 1.26.1. The load-generator source/image is unchanged.
- All 32 Python tests passed. New checks reject incorrect storage mode, missing
  persistence metadata, unequal captured/persisted byte counts, and incomplete
  persistence. Schema-7 sessions may be analyzed read-only but cannot resume.
- The pinned Go service tests passed during the build and a separate real-HTTP
  fixture export. New tests verify zero trace-file bytes during memory capture,
  byte-for-byte persistence, a sticky capture overflow bound, writes rejected
  after finish, and failure status when final persistence fails. Pending-response
  stop protection remains covered.
- Combined memory and file fixtures both retain two successes (including ID
  zero), one queue rejection, and one client timeout with eventual worker
  completion, plus connection reuse and final lifecycle evidence. Runtime-only
  and custom-only fixtures pass their respective reduced-evidence checks.
  Corrupt clock anchors and missing rejection records are still rejected.
  Evidence: `diagnostic/verification/runtime_io_v7_validation.json` and the raw
  fixtures under `diagnostic/verification/runtime-io-v7/`.
- The runtime-only memory fixture's raw pinned Go trace reports zero
  `cappedWriter.Write` syscall entries, consistent with deferring file writes
  until after `trace.Stop`. Evidence:
  `diagnostic/verification/runtime_io_v7_writer_review.json`. This fixture is not
  quota-limited performance evidence.
- All 16 retained v6 component attempts were revalidated against their seals and
  evidence with zero issues. Their raw attempts/source snapshots remain intact.
  All four combined wait-stack reports and the runtime-only block-1 trace-writer
  report were added outside sealed attempts.
- Python compilation, shell syntax and launcher help checks passed.

The new pilot freezes memory storage and keeps all workload/environment,
failure-rate and overhead gates. Allocation of the fixed 64 MiB buffer occurs
before capture; deferred file persistence, Sync and Close remain inside the final
cgroup accounting window. Abrupt termination can lose unpersisted trace data;
an incomplete attempt cannot pass. A passed future pilot would screen suitability
without proving the causal reason for the v6 disturbance.

Run instructions: [runtime_io_v7_commands.md](runtime_io_v7_commands.md).

## Temperature progress and compact launch refusal

The settling loop now prints actual temperatures on its first sample and the
first sample at/after each minute, before accepting a stable period. Diagnostic
trial lines identify the run and attempt. Sampling and thermal thresholds are
unchanged. Launch now checks for ChatGPT/Codex before starting the workflow and
prints a compact refusal instead of a process command-line dump. The matching
process name remains `ChatGPT`; on this host it includes the Codex desktop app.
No applications are killed and the quiet-host check remains enforced.

All 34 Python tests pass, including the stable-at-60-seconds output boundary and
compact process-count message. No new pilot session exists or was launched.
