# Diagnostic trial results

Pilot observations are diagnostic only.

| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 resume-to-write ms | p99 write-call ms | p99 write-to-exit ms | p99 signed e2e-minus-handler ms | Trace coverage | Rejections | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| trace_overhead_1 | 1430.108 | 0.013 | 988.541 | 187.681 | 187.101 | 0.022 | 0.008 | 0.004 | 930.171 | 1.000 | 3.974% | 0.000% |
| trace_overhead_2 | 4130.488 | 0.027 | 600.124 | 94.373 | 102.482 | 0.018 | 0.009 | 0.001 | 4118.134 | 1.000 | 0.000% | 0.000% |
| trace_overhead_3 | 4231.328 | 0.027 | 696.464 | 91.989 | 101.842 | 0.019 | 0.009 | 0.008 | 4119.116 | 1.000 | 0.000% | 0.000% |
| trace_overhead_4 | 1810.766 | 0.013 | 986.430 | 184.085 | 192.812 | 0.022 | 0.008 | 0.002 | 1616.323 | 1.000 | 3.664% | 0.000% |
| trace_p100000_w1_on | 837.313 | 0.013 | 822.568 | 56.523 | 0.661 | 0.012 | 0.007 | 0.000 | 44.825 | 1.000 | 0.000% | 0.000% |
| trace_p100000_w1_off | 777.006 | 0.025 | 768.271 | 55.725 | 0.672 | 0.013 | 0.006 | 0.006 | 43.443 | 1.000 | 0.000% | 0.000% |

Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.

The handler exit marker is recorded after event storage and before unlocking/returning. The signed e2e-minus-handler value subtracts durations for the same request, not absolute clocks. It may be negative if client completion overlaps server cleanup; negative values and write errors are retained as outcomes. Neither a write return nor the exit marker proves delivery.

| Run | Server write errors | Negative signed differences | Slowest 1% mean signed difference / e2e |
|---|---:|---:|---:|
| trace_overhead_1 | 0 | 0 | 68.090% |
| trace_overhead_2 | 0 | 0 | 99.185% |
| trace_overhead_3 | 0 | 0 | 94.022% |
| trace_overhead_4 | 0 | 0 | 68.441% |
| trace_p100000_w1_on | 0 | 0 | 0.868% |
| trace_p100000_w1_off | 0 | 0 | 0.610% |

## Runtime and connection evidence

| Run | Runtime trace | Bytes | I/O events | Dropped | Matched slow/typical | Slow with socket write |
|---|---|---:|---:|---:|---:|---:|
| trace_overhead_1 | complete | 861946 | 18781 | 0 | 22/22 | 22 |
| trace_overhead_2 | disabled | NA | NA | NA | NA | NA |
| trace_overhead_3 | disabled | NA | NA | NA | NA | NA |
| trace_overhead_4 | complete | 855061 | 18777 | 0 | 22/22 | 22 |
| trace_p100000_w1_on | complete | 883547 | 18645 | 0 | 23/23 | 23 |
| trace_p100000_w1_off | disabled | NA | NA | NA | NA | NA |

Per-request runnable, Go Running, synchronization/network wait and socket-write evidence is in each accepted attempt’s `trace_requests.json` and `trace_report.md`. Go Running can include OS descheduling or quota throttling and is not measured CPU execution. Runtime and service timestamps are aligned only through two bracketed clock logs; mapping uncertainty is reported there. Socket reads are retained at connection level because a read may contain partial or multiple HTTP requests. A successful socket Write does not prove delivery to the client. Client timing is compared through durations only.
