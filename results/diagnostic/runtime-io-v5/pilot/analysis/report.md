# Diagnostic trial results

Pilot observations are diagnostic only.

| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 resume-to-write ms | p99 write-call ms | p99 write-to-exit ms | p99 signed e2e-minus-handler ms | Trace coverage | Rejections | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| trace_overhead_1 | 2122.832 | 0.012 | 982.809 | 187.267 | 195.746 | 0.019 | 0.009 | 0.002 | 1645.172 | 1.000 | 3.885% | 0.000% |
| trace_overhead_2 | 4109.596 | 0.022 | 811.234 | 95.050 | 105.398 | 0.019 | 0.008 | 0.009 | 4043.686 | 1.000 | 0.000% | 0.044% |
| trace_overhead_3 | 3822.021 | 0.027 | 606.643 | 97.266 | 108.726 | 0.024 | 0.008 | 0.006 | 3720.257 | 1.000 | 0.000% | 0.000% |
| trace_overhead_4 | 2625.739 | 0.012 | 988.955 | 184.213 | 195.507 | 0.019 | 0.009 | 0.003 | 2526.331 | 1.000 | 4.371% | 0.000% |
| trace_p100000_w1_on | 814.958 | 0.014 | 804.497 | 56.403 | 0.708 | 0.013 | 0.007 | 0.000 | 42.965 | 1.000 | 0.000% | 0.000% |
| trace_p100000_w1_off | 757.896 | 0.022 | 747.147 | 55.753 | 0.676 | 0.013 | 0.006 | 0.001 | 42.316 | 1.000 | 0.000% | 0.000% |

Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.

The handler exit marker is recorded after event storage and before unlocking/returning. The signed e2e-minus-handler value subtracts durations for the same request, not absolute clocks. It may be negative if client completion overlaps server cleanup; negative values and write errors are retained as outcomes. Neither a write return nor the exit marker proves delivery.

| Run | Server write errors | Negative signed differences | Slowest 1% mean signed difference / e2e |
|---|---:|---:|---:|
| trace_overhead_1 | 0 | 0 | 80.022% |
| trace_overhead_2 | 0 | 0 | 99.596% |
| trace_overhead_3 | 0 | 0 | 95.363% |
| trace_overhead_4 | 0 | 0 | 92.088% |
| trace_p100000_w1_on | 0 | 0 | 2.492% |
| trace_p100000_w1_off | 0 | 0 | 0.754% |

## Runtime and connection evidence

| Run | Runtime trace | Bytes | I/O events | Dropped | Matched slow/typical | Slow with socket write |
|---|---|---:|---:|---:|---:|---:|
| trace_overhead_1 | complete | 867965 | 18777 | 0 | 22/22 | 22 |
| trace_overhead_2 | disabled | NA | NA | NA | NA | NA |
| trace_overhead_3 | disabled | NA | NA | NA | NA | NA |
| trace_overhead_4 | complete | 853433 | 18825 | 0 | 22/22 | 22 |
| trace_p100000_w1_on | complete | 881705 | 18637 | 0 | 23/23 | 23 |
| trace_p100000_w1_off | disabled | NA | NA | NA | NA | NA |

Per-request runnable, Go Running, synchronization/network wait and socket-write evidence is in each accepted attempt’s `trace_requests.json` and `trace_report.md`. Go Running can include OS descheduling or quota throttling and is not measured CPU execution. Runtime and service timestamps are aligned only through two bracketed clock logs; mapping uncertainty is reported there. Socket reads are retained at connection level because a read may contain partial or multiple HTTP requests. A successful socket Write does not prove delivery to the client. Client timing is compared through durations only.
