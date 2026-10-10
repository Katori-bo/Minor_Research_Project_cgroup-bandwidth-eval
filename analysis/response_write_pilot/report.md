# Response-write pilot interpretation

The resumed pilot completed at 23:53 IST on September 30, 2026. All six accepted attempts were revalidated from raw evidence and their completion hashes matched the saved gate. The earlier thermal failure remains preserved as attempt 001 of the first trial; attempt 002 succeeded.

## Observed outcomes

| Trial | Workers | Timing enabled | Successful-request p99 | Rejections | Timeouts |
|---|---:|---|---:|---:|---:|
| pilot_overhead_1 | 4 | True | 3916.8 ms | 0.000% | 0.000% |
| pilot_overhead_2 | 4 | False | 4218.2 ms | 0.000% | 0.000% |
| pilot_overhead_3 | 4 | False | 4220.7 ms | 0.000% | 0.044% |
| pilot_overhead_4 | 4 | True | 1934.2 ms | 5.519% | 0.000% |
| pilot_p100000_w1_on | 1 | True | 894.7 ms | 0.662% | 0.000% |
| pilot_p100000_w1_off | 1 | False | 889.3 ms | 0.618% | 0.000% |

All trials use a 100 ms quota period and 0.5 CPU, with 20-second measurements. These are pilot observations, not five-repetition research estimates.

## Matching the slowest requests

| Instrumented trial | Slowest 1% count | Mean end-to-end | Mean handler span | Mean signed difference | Mean new response stages |
|---|---:|---:|---:|---:|---:|
| pilot_overhead_1 | 23 | 4015.36 ms | 345.68 ms | 3669.68 ms | 0.0117 ms |
| pilot_overhead_4 | 22 | 2219.74 ms | 118.60 ms | 2101.14 ms | 0.0135 ms |
| pilot_p100000_w1_on | 23 | 899.44 ms | 897.01 ms | 2.43 ms | 0.0139 ms |

Each row uses the same request IDs for all durations. The new response stages are handler resume through the exit marker, including the actual Write call. The signed difference is end-to-end duration minus the observed handler span; it does not locate a unique unmeasured stage, and no absolute clocks or independently calculated quantiles were subtracted.

For the slowest requests in the two instrumented four-worker trials, mean per-request signed difference/end-to-end is 91.42% and 94.74%. The new stages are too small on those requests to account for the seconds of waiting. With one worker, the corresponding share is 0.264%; its measured handler span accounts for nearly all the slow-request time. Client traces still place the long delay after request write and before the first response byte.

## Exceptions and limitations

The second instrumented four-worker trial rejected 125 of 2,265 requests (5.519%). Its lower successful-request p99 cannot be interpreted as a performance improvement without accounting for those failures and changed admitted load. The other instrumented four-worker trial rejected none. One uninstrumented four-worker request timed out.

The saved one-sided overhead screen passed: service CPU ratio 1.002245, client CPU ratio 1.000397, and successful-request p99 ratio 0.693332. It checks for increases above 10%; it does not establish equivalence or absence of instrumentation effects. The large rejection difference and only two on/two off observations require caution.

In `pilot_overhead_4`, request 725 spent 1201.068 ms between handler resume and Write start, while the Write call itself took 0.001893 ms. 154 other worker completions occurred during that server-local interval. This was not a continuous whole-server pause and was not among that trial's slowest 1%. It motivates investigating individual goroutine scheduling or blocking, but does not establish a cause.

All instrumented successful requests had usable client traces, no negative signed differences and no recorded server Write errors.

## Next decision

The pilot produced usable data and narrowed the measured response path, but did not explain the dominant long wait. The protocol's criterion for expanding the matrix is therefore not satisfied. The next diagnostic should correlate server receive/handler entry and final flush/socket activity, with a bounded runtime trace to test runnable versus blocked goroutine delays. Define request/connection matching and clock alignment before collection, and check tracing overhead and rejection rates again. Do not infer a transport, kernel-throttling or Go-scheduler cause from this pilot alone.
