# V27 revision-2 preparation verification

7 October 2026. Generation-01 stopped during the first functional preparation
case. Its client lacked `clock_anchors` and `client_test_start_ns`; all 999
offers completed, but timing replay could not qualify the record. Both owned
containers/cgroups were removed, with no watchdog intervention or cleanup
error. The recorded cgroup paths are absent. No measurement trial or lifetime
started. The [failure review](../analysis/runtime_io_v27_failure_review/20261007/report.json)
preserves the error, source diagnosis, outcome counts and cleanup receipts.

The defect was introduced when the new client copied base source without the
clock instrumentation transformation used by the retained client build.
Synthetic raw fixtures injected clocks, so the first verification did not
exercise the compiled binary's output contract.

The [separate repair protocol](runtime_io_v27r2_protocol.md) restores that
instrumentation and the verified prepared clock helper. The [revision-02
client receipt](../analysis/runtime_io_v27_client_build/revision-02/manifest.json)
records unit/race/vet success and Go 1.26.1 compilation with CGO_ENABLED=0.
All eight binary schedule exports still match the frozen vectors. Real compiled
client output from short localhost HTTP stub cases passes clock mapping and
complete request-stage replay: nine steady and twelve bursty requests, six
anchors each, without injected report fields. Stub clocks/requests are software
fixtures; no quota or SHA workload is involved. The original failed binary's
actual 999-offer report is rejected for missing clocks by the repaired replay.

All 31 repair checks passed. The [sealed preparation review](../analysis/runtime_io_v27r2_preparation_review/20261007/report.json)
also records the combined regression result and integrity verification. The
[generation-02 bundle](../analysis/runtime_io_v27/generation-02/bundle/manifest.json)
freezes 226 source/dependency files, including all 209 original V27 files
unchanged. Original failed-generation bundle/preparation seals are bound into
the new design and manifest. Scientific trial configurations exactly match the
original matrix; schedules, windows, practical screens and statistical rules
are unchanged. Service, gate and native collector binaries are retained.

The sandbox blocked localhost listener creation during the initial software
build attempt. That incomplete attempt is preserved separately as
`analysis/runtime_io_v27_client_build/revision-02-sandbox-blocked`.
The authorized software build then passed with the localhost fixtures enabled.
No Docker, sudo, quota measurement or host-policy change was performed during
this repair. Combined regressions include the retained native regular-file
software fixture.

Runtime preparation and composition measurements remain **0/16** in
generation-02. Actual resource/clock qualification and all functional cases
must run externally with the desktop app quit. Use the
[new combined launch command](runtime_io_v27r2_execution.md); preserve and do
not resume generation-01. Passing software checks is not scientific support
for load composition or a guarantee of runtime qualification. The launcher
stops after the bounded sixteen-trial report.
