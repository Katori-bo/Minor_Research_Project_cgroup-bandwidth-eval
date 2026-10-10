# Response-write implementation audit — 2026-09-30

Scope: the revision-3 changes to `diagnostic/service`, collection validation, analysis, the existing-data audit, pilot launcher, and protocol. This audit included fixes; it was not a new performance collection.

## Findings and corrections

| Priority | Finding | Correction and evidence |
|---|---|---|
| P1 | The former `return_ns` timestamp was taken before acquiring the final bookkeeping lock. Contention there could be omitted from the very response boundary under investigation. | Replaced it with `handler_exit_ns`, recorded after lock acquisition and event storage. It is explicitly a final observed marker, preceding unlock and actual return. A regression test holds that lock and checks that the marker follows its release. |
| P1 | Validation assumed client end-to-end time must contain the entire post-write handler span. Client completion can overlap cleanup, so this could reject legitimate observations. | Preserve the signed `e2e_minus_handler_span` result, including negative values; retain write errors as outcomes. Validate server-local ordering and ID matches independently. Tests cover overlap, write failure, missing/mismatched IDs and timestamp ordering. |
| P2 | The reported write interval included formatting and digest-to-string conversion before the actual `ResponseWriter.Write` call. | A narrow `io.Writer` wrapper now times the actual Write call while preserving the existing `fmt.Fprintf` response generation. A real HTTP test checks identical on/off response bodies and complete events after drain. |
| P2 | The existing-data audit trusted derived trial summaries and contained hard-coded explanatory values. Its summaries could remain stale despite checking raw attempt hashes. | Recompute trial quantiles, outcomes and throttling from sealed raw inputs; validate the frozen matrix and timing identities; generate narrative values and a source-hash manifest. All 20 recomputed trial summaries agree with the original summaries. |
| P2 | The recommended pilot command bypassed the background launcher and sleep inhibition, while the launcher would automatically continue into full collection. | The documented launcher now defaults to pilot collection plus analysis, with persistent logs, resume behavior and sleep inhibition. It writes `PILOT_COMPLETED.md`; full collection requires explicit `--full`. A pipeline test checks both paths. |
| P2 | Three-decimal fraction formatting hid rare timeouts as `0.000`. | New timing reports display rejection and timeout percentages with three decimal places. |

## Verification

- Ten Python regression tests pass. Coverage includes request-ID joins before computing residual quantiles, instrumentation off, signed overlap, outcome accounting, changed raw evidence and the pilot/full boundary.
- Seven service Go tests pass in the Docker build, including final-lock contention, write failures and a real HTTP response on/off comparison. The unchanged load-generator build reused its previously tested Docker layer.
- The service image was rebuilt as `quota-diagnostic-service:2` and its schema-4 build manifest regenerated.
- Python compilation and launcher help checks pass.
- The existing-data audit regenerated its report, CSVs, source hashes and plot.
- All 504 files in the original completed pilot/full workflow remain byte-for-byte unchanged, verified against hashes taken before this audit.
- Repository-wide `git diff --check` reports pre-existing trailing blank lines in `.gitignore` and `tools/wrk2/README.md`; those unrelated edits were not changed by this audit.

## Remaining limits

The six-trial performance pilot has not been collected. Actual overhead, environmental acceptance, long-wait reproduction and explanatory value therefore remain unverified. Two on and two off four-worker trials provide only a coarse overhead screen; the one-worker pair provides a descriptive comparison.

The exit marker and Write completion do not establish when the client received bytes. Even after measuring the new stages, a large signed difference could combine pre-handler delivery, final HTTP flushing, transport, dispatch and client completion. Choosing between those mechanisms may require a targeted runtime or kernel trace with verified correlation and clock alignment.

The completed experiment's findings are unchanged. The corrected implementation is prepared for the focused pilot, with the launch instructions in `diagnostic/README.md`.
