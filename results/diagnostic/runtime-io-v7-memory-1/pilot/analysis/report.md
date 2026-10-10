# Diagnostic trial results

Pilot observations are diagnostic only.

| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 resume-to-write ms | p99 write-call ms | p99 write-to-exit ms | p99 signed e2e-minus-handler ms | Trace coverage | Rejections | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| trace_overhead_1 | 1517.168 | 0.013 | 984.868 | 183.583 | 193.566 | 0.017 | 0.008 | 0.001 | 1434.511 | 1.000 | 3.753% | 0.000% |
| trace_overhead_2 | 3914.659 | 0.028 | 906.482 | 99.452 | 107.000 | 0.019 | 0.009 | 0.005 | 3842.930 | 1.000 | 1.678% | 0.000% |
| trace_overhead_3 | 4032.112 | 0.020 | 323.720 | 80.423 | 101.786 | 0.019 | 0.008 | 0.007 | 4022.280 | 1.000 | 0.000% | 0.000% |
| trace_overhead_4 | 2043.707 | 0.012 | 985.015 | 184.357 | 196.701 | 0.018 | 0.008 | 0.001 | 1923.776 | 1.000 | 3.444% | 0.000% |
| trace_p100000_w1_on | 833.010 | 0.014 | 817.890 | 56.255 | 0.722 | 0.011 | 0.007 | 0.001 | 43.237 | 1.000 | 0.000% | 0.000% |
| trace_p100000_w1_off | 767.465 | 0.021 | 758.583 | 55.783 | 0.708 | 0.013 | 0.006 | 0.007 | 42.737 | 1.000 | 0.000% | 0.000% |

Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.

The handler exit marker is recorded after event storage and before unlocking/returning. The signed e2e-minus-handler value subtracts durations for the same request, not absolute clocks. It may be negative if client completion overlaps server cleanup; negative values and write errors are retained as outcomes. Neither a write return nor the exit marker proves delivery.

| Run | Server write errors | Negative signed differences | Slowest 1% mean signed difference / e2e |
|---|---:|---:|---:|
| trace_overhead_1 | 0 | 0 | 88.201% |
| trace_overhead_2 | 0 | 0 | 98.140% |
| trace_overhead_3 | 0 | 0 | 94.457% |
| trace_overhead_4 | 0 | 0 | 81.209% |
| trace_p100000_w1_on | 0 | 0 | 1.361% |
| trace_p100000_w1_off | 0 | 0 | 0.505% |

## Runtime and connection evidence

| Run | Runtime trace | Bytes | I/O events | Dropped | Matched slow/typical | Slow with socket write |
|---|---|---:|---:|---:|---:|---:|
| trace_overhead_1 | complete | 809201 | 18773 | 0 | 22/22 | 22 |
| trace_overhead_2 | disabled | NA | NA | NA | NA | NA |
| trace_overhead_3 | disabled | NA | NA | NA | NA | NA |
| trace_overhead_4 | complete | 804645 | 18777 | 0 | 22/22 | 22 |
| trace_p100000_w1_on | complete | 865603 | 18645 | 0 | 23/23 | 23 |
| trace_p100000_w1_off | disabled | NA | NA | NA | NA | NA |

Per-request runnable, Go Running, synchronization/network wait and socket-write evidence is in each accepted attempt’s `trace_requests.json` and `trace_report.md`. Go Running can include OS descheduling or quota throttling and is not measured CPU execution. Runtime and service timestamps are aligned only through two bracketed clock logs; mapping uncertainty is reported there. Socket reads are retained at connection level because a read may contain partial or multiple HTTP requests. A successful socket Write does not prove delivery to the client. Client timing is compared through durations only.

Runtime traces use a fixed 64 MiB memory buffer allocated before capture. After trace.Stop drains the writer, file persistence, Sync and Close remain inside the final cgroup CPU accounting window. Buffer overflow or persistence failure invalidates the attempt. This is a candidate instrumentation intervention; functional validation does not establish reduced performance perturbation.
