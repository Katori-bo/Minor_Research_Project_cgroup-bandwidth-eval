# V27 revision-3 repair verification

8 October 2026. Generation-03 is frozen and independently verified offline;
actual runtime preparation and all sixteen scientific trials remain unrun.
The [sealed review](../analysis/runtime_io_v27r3_preparation_review/20261008/report.json)
records bundle, design, software-check and reused client-build identities.

The real child-process software fixture used the production monitor loop with
synthetic reads, a one-second sleep and31ms per-read overhead for an80-second
simulated traffic lifetime. It had78 records at drain and80 after bounded
completion, averaging1.031279 seconds per record. Saved records and lifecycle
receipts independently passed count and endpoint coverage checks. No real host
monitor reads, service workload, Docker, quota or native sampling were used.

All40 revision-3 tests and180 inherited V22/V23/V24r3/V25/V26/V27/V27r2 checks
passed. These include exact offers, all-outcome clock/stage joins, bounded
inference, retry/no-resume behavior, count79 rejection, quiet/power separation,
endpoint/progress/PID tampering, missing/stale progress and early exit. A
production collection orchestration fixture confirmed native counter shutdown
and decoding precede the extended host-monitor wait. Shell syntax passed;
bundle verification rejects changed comparison and monitor-receipt identities.

All226 inherited source files and both failed generations' bundles, preparations,
attempts, seals, diagnosis and partial report remain unchanged. The241-file new
bundle includes separate revision-3 sources and protocol. All scientific
configuration and offer vectors match revision2. Reuse the sealed revision-02
client; no new build or software HTTP fixture was needed.

The repair adds readiness before service release and a bounded host-monitor
completion wait after drain, with an unchanged minimum80. Native capture and
all scientific thresholds and lifetime/retry limits remain unchanged. The new
host-monitor progress writes add a shared observer cost; these checks establish
software behavior, not runtime timing, scientific effect or novelty.

Run only generation-03 using the [external execution guide](runtime_io_v27r3_execution.md),
with the desktop app fully quit. It requalifies actual resources and all four
functional cases before measurement. Preserve failures; do not resume an
attempted generation. Collection stops after its report regardless of result.
