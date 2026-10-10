# Stopped imgproxy qualification: verified domain exit

The engineering pilot stopped after 168.719 seconds: one complete stock/observed
pair followed by p2_observed. All 600 measurement offers succeeded with matching
full-response image hashes. Cleanup is verified for all three owned services.
The preparation seal, runtime/image/resource identities, original sources,
actual measurement-counter differences and observer inventory all verify.

The failed trial's nr_throttled increased from 2 to 3 during measurement. Thus
the increase is not just its two pre-measurement startup/warmup throttles.
throttled_usec increased by 38,456 us. All 200 observed queue waits were <=100 us
(maximum 38.632 us). Its median end-to-end latency was 18.297 ms, with maximum
58.177 ms at measurement-125; that request reported 56.091 ms processing and
1.453 us queue wait. A slow request and a throttle increment are consistent with
a quota stall, but without a time-resolved trace their association is not proven.

Average measured CPU use was approximately 0.086 CPU, below the configured
0.25-CPU average allowance. An average allowance does not guarantee every
100-ms budget interval stays unthrottled. Application background work, native
thread behavior, and budget allocation remain candidate explanations. The
upstream default performs memory freeing every 10 s, including Go FreeOSMemory
and glibc malloc_trim; no recorded event establishes that it caused this stall.

There is only one complete pair. No six-pair confidence interval or observer-cost
qualification can be claimed. There is no calibration/held-out transfer result
and no new causal or novelty claim. The V31 result remains separate.

Reporting limitation: the frozen runner checked the domain before exporting
the failed trial's bounded server buffer. Client timing headers and CPU counters
remain, but that buffer cannot be recovered after owned cleanup. Keep this
limitation; do not rewrite the frozen collector or replace the failed trial.

Next: one separately declared forensic diagnostic with idle and fixed-load
windows, monotonic client anchors, a bounded CPU-counter timeline, and server
event export before classification. Keep the application, rate, worker setting
and quota unchanged. Its aim is localization, not passing the original pilot.
