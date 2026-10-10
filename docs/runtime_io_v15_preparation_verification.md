# V15 preparation verification — 2026-10-04

**Ready for external-terminal collection; performance trials not started (0/24).**

[Protocol and launch](runtime_io_v15_marker_protocol.md). Verified build: `analysis/runtime_io_v15_marker_verified_build`. Results target: `results/diagnostic/runtime-io-v15-inline-markers-1`. V14 remains stopped, with its original 17 valid trials and failed cooling attempt preserved; V15 creates a separate accepted temperature baseline at launch.

## What changed and why

The four new variants retain the original V12 worker loop and `runJob`, original locks, counter position, buffered reply and HTTP outcome accounting. Build-time source insertion adds zero, one, two or five discarded clock calls; a cached origin protects the post-send sample from reset. No persistent marker storage is introduced. Exact V12 and V14 clocks images provide references. Four distinct declared orders, paired with their reverses, give 24 trials and two relative-order appearances per arm pair. Position and immediate carryover are not fully balanced across four blocks.

The separate runner retains the original quiet-host, cgroup/affinity, arrival schedule, full drain and evidence acceptance rules. It measures an idle baseline after at least ten minutes and a stable window, seals environment/idle evidence before the first trial, and verifies the seal on resume and completion. It never copies V14's warmer baseline or silently replaces a baseline. It adds a graceful `stop` command that verifies process identity before sending TERM. The launcher closes the desktop app, starts the detached sleep-inhibited batch, displays progress/temperatures/remaining trials, and prints the sealed report.

## Verification evidence

- All normal Go service tests passed for each of four new images.
- Full `go test -race -count=1 -v ./...` passed for all four variants, including concurrent snapshots, repeated drained resets after handoff, cancelled work and queue rejection. Race logs and the temporary host trace-output adjustment are sealed in [race verification](../analysis/runtime_io_v15_marker_verified_build/race_verification.json).
- [Actual-binary compiler audit](../analysis/runtime_io_v15_marker_verified_build/compiler_audit/audit.json) confirms zero/one/two/five retained `time.Since` calls in the original job function and matching normalized SHA-work instructions across all six images. The zero-call rebuild's worker and job instructions also match legacy after address normalization. Actual binaries, hashes, raw/normalized disassembly and compiler escape/inlining logs are retained.
- [Twelve real HTTP fixtures](../analysis/runtime_io_v15_marker_verified_build/functional_verification.json) passed across all six arms at GOMAXPROCS1/2, with six requests each, outcome conservation, runtime/mode/count and bounded-clock checks. These unquotaed fixtures establish implementation behavior, not performance evidence.
- **144 Python diagnostic tests passed, with no skips.** New checks cover missing publication markers, all-offered failures, schema drift, source insertion/counter/send order, distinct balanced relative orders, screen refusal to promote a recorder, fresh/sealed baseline and resume tampering, quiet-host launch refusal, stop PID reuse refusal, progress/remaining counts, actual build-bundle/frozen-session tampering, and real-fixture analysis/export/completion seal tampering. Offline export uses synthetic CPU fields and cannot qualify performance.
- `bash -n diagnostic/start_marker_batch.sh` passed. The 24-cell plan and not-started status were inspected; no background performance worker was launched.

The first unsealed preparation folder, `analysis/runtime_io_v15_marker_build`, is preserved: its images, compiler audit and race suites passed, but a missing Python HTTP import stopped functional preparation. The import was corrected and the separate verified bundle was built and checked from the corrected code.

## Limits and next decision

Static code identity does not establish equal timing, alignment, cache effects or host state. Cached-origin loads, marker placement and associated generated code are part of the treatment. V14 clocks still differs in worker-path and order-check behavior. Four discovery blocks and practical margins do not prove equivalence. All arms deliberately lack stored publication brackets; even a low-cost result needs persistent-recorder qualification before fine-grained publication claims or worker/parallelism controls. Read the six declared contrasts before selecting the next measurement change. No automatic controls or intervention study is enabled.
