# Follow-up validation status — 2026-09-26

**Historical preparation report.** The later `results/followup/all-in-one-v2/` workflow finished on 2026-09-28 at 01:41 IST: eight validated pilot trials, a passed pilot gate, 50 validated full trials and completed analysis. See `results/followup/all-in-one-v2/COMPLETED.md`. Statements below about collection still being required describe the 2026-09-26 preparation state.

**Ready for the diagnostic pilot; full collection is not yet validated.** No live follow-up trials have been collected. The earlier three-trial pilot execution request was rejected at the permission step. The subsequent review corrected the implementation and protocol before any data collection; the current diagnostic pilot has eight trials.

## Review corrections

- Drain warmup jobs and HTTP handlers before resetting measurement state. Client timeouts no longer imply the server is finished.
- Publish completion counters together with stored timing events; protect reset against unfinished work. Retain service-local admission/start/completion timestamps and work completed after cancellation.
- Verify raw accounting, timing headers, cgroup limits, runtime, temperature/power evidence, and file hashes before reusing a completed trial. A `failure.json` attempt is never accepted, and a missing completion marker is incomplete.
- Bind built sources to image/binary hashes, include imported original runner/environment/monitor dependencies in session provenance, freeze collection order, and share the original experiment lock.
- Separate responses completed inside the offered window from arrival-cohort throughput and throughput including drain. Component summaries include all completed server jobs as well as successful-client subsets.
- Raise only Study A's steady rate to 176.41/s to test execution concurrency with sustained runnable work. Preserve Study B's original 113.21/s. Add a pilot saturation check for both A arms.
- Expand pilot coverage to both periods, both runtime settings, and a small on/off/off/on overhead comparison. Full collection now requires a passed pilot and matching evidence/source hashes.

## Verified

- **23 Python regression tests passed**, including corrupt evidence, raw-accounting recomputation, power drift, interrupted attempts, drain boundaries, exact interaction/ratio calculations, separate A/B analysis, missing observations and constant-temperature diagnostics.
- **Seven Go tests passed** during Docker builds: four service tests and three load-generator tests. They exercise queue overflow, queued work after client cancellation, completion snapshots, reset, timing headers, instrumentation off, SHA work, quantiles and arrival schedules.
- Both Go 1.26.1 binaries/images rebuilt successfully. Built source/binary manifest hashes match the reviewed files. Python compilation and shell syntax checks passed.
- CPU topology matches the required server/client separation. External power was connected at review time; actual desktop-profile and thermal acceptance remain enforced when the runner starts.
- The completed study's original source/binary hashes still match its metadata. Existing unrelated `.gitignore` and `tools/wrk2/README.md` edits were preserved; their pre-existing trailing-blank-line warnings are unrelated to this change.
- Full matrix has 50 unique trials: 10 A and 40 B. Pilot has eight separate diagnostic trials. No full experiment was launched.

## Still required

Run the live pilot and its analyzer using `followup/README.md`. It must validate quota/runtime/affinity, full HTTP timing and accounting, host monitoring, environmental acceptance, Study A saturation and the coarse overhead screen. Tests and successful compilation do not substitute for those observations. Pilot p99s are diagnostic only.

The overhead comparison has only two trials per instrumentation state. Its 10% screen is a predefined reason to investigate, not a precise uncertainty bound or proof of zero overhead. The paper's missing exact configuration details and different workload/runtime remain limitations of the adapted replication. Inspect any failed gate and record a protocol amendment before collecting full data.

## One-command workflow validation

Added eight workflow tests, bringing the Python suite to 23 passing tests. They cover the complete stage sequence and completion report, stopping before full collection on a pilot-analysis failure, resuming without rebuilding or overwriting evidence, rejecting incomplete session directories, recording failures, avoiding duplicate launches, nonzero stage exit handling, and sharing the coordinator lock with child runners while excluding another experiment. These tests use synthetic stages and temporary fixtures; the live pilot and full research collection remain unrun.
