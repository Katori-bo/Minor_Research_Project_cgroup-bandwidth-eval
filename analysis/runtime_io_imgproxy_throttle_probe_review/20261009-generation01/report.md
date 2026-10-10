# Imgproxy forensic probe: verified, cause unresolved

The separate probe completed in 97.839 seconds. Both input
seals and the complete run evidence seal verify. Runtime, image, executable,
resource and ownership identities verify. All 225 offers (25 warmup, 200
measurement) have successful matching image bodies, valid clock brackets and
paired raw server events. Owned cleanup completed without errors.

The 40-second idle window and original 5 req/s measurement window each recorded
zero new throttled periods and zero additional throttled time. All 20,418
counter samples retain nr_throttled=1 and throttled_usec=24,125 from before the
idle window. Thus the service had a pre-idle throttle; this probe did not observe
a new throttle during monitoring. The largest counter sample gap was 7.714 ms.
The cumulative counters also cover gaps between samples.

Measurement median end-to-end latency was 17.392 ms. All 200 measurement queue
waits were <=100 us. Whole-cgroup measured CPU consumption was 16.786 ms per
offer. These are descriptive forensic observations, not a new cost qualification.

The original p2_observed measurement throttle and stopped pilot remain verified
and unchanged. The probe has a different service-age schedule (40 seconds idle)
and an added sampler whose overhead is not qualified. It is not a replacement
trial. The absence of a new throttle does not identify the old throttle's cause,
demonstrate that it was fixed, or establish which background/native work caused it.

There is still no complete six-pair observer-cost qualification, effective native
concurrency qualification, or fresh calibration/held-out imgproxy forecast test.
The current 25 ms/100 ms candidate remains unqualified. Stop this candidate's
scientific collection at this gate; do not rerun the pilot until it passes or
weaken the zero-throttle rule after observing the failure. Any revised candidate
requires a separately justified, prospective engineering protocol before its
new measurements. V31's confirmed result remains unchanged. This probe supports
no new mechanism, application-transfer, or novelty claim.
