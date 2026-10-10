# Imgproxy bounded feasibility qualification

Status: preparation and functional checks; no scientific calibration or validation.
This implements the feasibility stage of the application-transfer candidate.
The completed V30/V31 evidence is not changed.

Pinned application: imgproxy v4.0.17, upstream commit
`2c89e4ebff3384caf6752db2ec861b4ef5fe675c`; Go 1.27.1; native libvips 8.18.7.
The checksum-verified toolchain and module cache are project-local. Stock source
is preserved separately from the instrumented copy and its generated patch.
Packaging uses the exact native shared-library dependency closure in separate
scratch images. Optional libvips foreign-format modules are excluded. The pilot
tests PNG-to-JPEG functionality; it does not qualify those excluded codecs.

Fixed input is upstream `testdata/dct2/original.png`, 600x600 RGB. The operation
fits it to 300x300 and encodes JPEG at quality 80. Input bytes and all build/runtime
artifacts are hashed. No timing result was used to select this operation. Local
input avoids an external download server. ETag/Last-Modified use is disabled;
the upstream service also disables its libvips operation cache. Output identity
and decoded dimensions are checked against the unmodified service.

The instrumented copy preserves acquisition, image processing, response writing,
cleanup and worker-release order. A 1024-event bounded in-memory collector records
monotonic duration boundaries and request IDs. Queue and process durations are
also returned in headers, allowing an independent client/raw-record join.
The original application retains the worker through response writing and cleanup.
Worker hold time is therefore distinct from image-processing time. Collector
export occurs only after traffic drains; overflow or missing records fail.

Functional checks allow at most six created services across preserved attempts.
Each passing arm has one decoded-image check plus eight spaced offers. Functional
timings taken with Codex open are not evidence qualifying instrumentation cost.

The external pilot has six pairs, alternating stock-observed and observed-stock
orders: twelve services total, with no retries or replacement. Each service has
25 warmup offers at 5 req/s followed by 200 measurement offers at the same rate.
Offer spacing is exactly 200,000,000 ns; client completion includes the entire
response body. Ten seconds of settling precedes each service. Service CPU quota
is 25 ms per 100 ms, zero recorded configured burst, cpuset 2,4, GOMAXPROCS 1,
one application worker, queue 128. Pilot memory/PID safety limits are 512 MiB and
128, explicitly differing from the omitted V31 overrides. Collector/client are
on CPUs 0,1; native codec-thread behavior still requires review.

The hard active-service bound is 120 seconds with an independent owner-death and
timeout cleanup watchdog. Overall budget is 1200 seconds including a 120-second
cleanup reserve. Docker commands and client drains have finite deadlines.
Owned cleanup checks a nonce label and removes the inspected immutable ID only.
The launcher refuses root/noninteractive execution, requires Codex/ChatGPT closed,
verifies the sealed bundle, and obtains a read-only privileged leftover-observer
inventory. It changes no tracing or CPU-frequency settings. Run summaries retain
failures and reject overwriting/resuming an attempted pilot.

Predeclared observer-cost endpoints are service-cgroup CPU microseconds per offer
and median client offered-to-full-body latency. Each of six pairs supplies one
relative observed/stock change. For each endpoint, the 95% t upper bound
`mean + 2.571 * sample_sd / sqrt(6)` must be <=5%. This is a practical engineering
margin, not a precision or power justification for the later scientific claim.
Every offer must succeed with matching body hash and request ID; dispatch p99
must be <=2 ms and maximum <=10 ms. Each instrumented measurement cohort must
have >=99% queue<=100 us and zero recorded measurement throttled periods in
either arm. Any failed gate or domain exit is retained and terminates qualification.
CPU counters bracket only measurement, before event export.

Native libvips/codec threads make a one-worker setting insufficient to establish
serial CPU execution. Thread snapshots and aggregate CPU/worker-wall ratios are
descriptive checks, not proofs of absence of concurrent native execution. Even
if observer-cost qualification passes, `ready_for_scientific_collection` remains
false pending concurrency/model review and a sealed prospective transfer protocol.
There are no eighteen-trial forecasts or validation results in this pilot.

Entry points:
- `python3 -B diagnostic/imgproxy_qualify.py functional`: preparation-only checks.
- `python3 -B diagnostic/imgproxy_qualify.py seal`: freeze qualified preparation.
- `bash diagnostic/start_imgproxy_qualification.sh`: external overhead pilot.
- `python3 -B diagnostic/imgproxy_qualify.py verify`: verify the preparation seal.
- `python3 -B diagnostic/imgproxy_qualify.py replay`: reconstruct a completed pilot
  from raw offered requests, server events and actual CPU counters.

Evidence: `analysis/runtime_io_imgproxy_feasibility/generation-01/`.
Official upstream: https://github.com/imgproxy/imgproxy/tree/2c89e4ebff3384caf6752db2ec861b4ef5fe675c
