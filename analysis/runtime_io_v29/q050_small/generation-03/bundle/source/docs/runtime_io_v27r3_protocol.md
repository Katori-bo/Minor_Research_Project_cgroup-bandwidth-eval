# V27 revision 3: bound monitor readiness and completion

8 October 2026. Separate generation-03 repairs the monitor lifecycle after
generation-02 exhausted its technical retry with 79 records against the frozen
80-record minimum. All original sources, failed attempts, partial reports and
seals remain preserved. See the [diagnosis](runtime_io_v27r2_failure_findings.md).

The [original scientific protocol](runtime_io_v27_protocol.md) is unchanged:
four balanced blocks, sixteen trials, identical high-arrival work, low15 versus
low30, sampler off/on, warmup20 seconds, measurement60 seconds, full drain,
the original windows, state/cohort criteria, effect thresholds and inference.
Reuse the sealed revision-02 client, service/gate/native binaries and exact
schedule vectors. No failed generation's measurements enter this comparison.

Copy the retained host monitor into a separate revision-3 source. Keep its
one-second sleep, reads, process attribution, power checks and saved JSON.
Add monotonic brackets around each full record and an atomic completed-record
progress sidecar with PID, count and endpoint brackets. The same host monitor
runs in both native sampler arms. Its progress writes are an added observer
cost shared by the arms, not a demonstration of deadline sampler neutrality.

Require a completed first record before releasing the service gate, bounded
by five seconds. After full measurement drain and final resource observation,
stop and decode the native sampler first, preserving its 110-second limit.
Keep the service/cgroup and host monitor alive until there are at least 80
actual records and a record whose read starts after the final observation.
Bound that extra completion wait by 30 seconds. Never fabricate records, lower
the count minimum or extend native capture to obtain host-monitor headroom.
Existing active-trial360, preparation600, collection5400, cleanup120 and
independent post-collection analysis600-second bounds remain unchanged.

Independent replay retains the original quiet and power checks, identifies
their failures separately, verifies record order, first/last coverage, process
identity, progress-to-record agreement and bounded lifecycle receipts.
The first completed record must precede the startup observation, and the last
record must start after the final observation. Functional preparation remains
without the host monitor. Runtime resources and all four functional cases
must qualify again externally.

Software verification uses the actual monitor loop and child-process shutdown
with synthetic read functions, one-second sleeps plus31ms per-record read cost,
and an 80-second simulated traffic lifetime. It must require additional waiting
and independently replay at least80 saved records with both endpoint brackets.
Also check count79 rejection, endpoint/identity/progress tampering, early exit,
missing/stale progress timeouts, quiet/power failures, and counter shutdown
before the extended host-monitor wait. This fixture runs no scientific workload,
Docker, quota changes, native sampler or real host-monitor reads.

One total technical retry is retained; a second technical failure stops the
new generation. Cleanup/watchdog failures stop it. No resume of an attempted
generation, replacement of scientifically valid failed states, or repeat until
favorable. Stop after the sixteen-trial report, whatever the result. Offline
verification does not qualify runtime timing, scientific effects or novelty.
Use the [revision-3 external execution guide](runtime_io_v27r3_execution.md).
