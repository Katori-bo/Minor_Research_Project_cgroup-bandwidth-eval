# Recovered request metrics — scheduler analysis unresolved

All 16 saved attempts pass the existing sealed-input, workload, environment and request-accounting checks. Their raw files were hashed before and after recovery and are unchanged. The original workflow remains failed.

This is a partial report. Scheduler cleanup joins fail in two stock/tracing-on trials. Scheduler wait estimates are omitted for every cell pending investigation. No collection was rerun, no acceptance threshold changed, and no completed-study or qualification gate was created.

| Mode | Rejection range | Timeout range | Total errors including timeouts | Median successful req/s | Median successful p99 ms | Median CPU µs/job |
|---|---:|---:|---:|---:|---:|---:|
| stock_off | 0.000%–1.678% | 0.000%–0.044% | 2 | 111.53 | 4061.028 | 3974.3 |
| stock_on | 1.678%–3.797% | 0.000%–0.000% | 0 | 109.30 | 2464.763 | 3994.7 |
| patched_off | 1.722%–2.208% | 0.044%–0.177% | 8 | 110.82 | 4227.035 | 4026.9 |
| patched_on | 3.974%–4.194% | 0.000%–0.000% | 0 | 108.50 | 2482.282 | 4047.1 |

| Comparison | CPU/job ratio | Client CPU/request ratio | Successful p99 ratio | Throughput ratio | Request-metric screens |
|---|---:|---:|---:|---:|---|
| patch_trace_off | 1.0132 | 0.9844 | 1.0409 | 0.9937 | FAIL |
| patch_trace_on | 1.0131 | 1.0086 | 1.0071 | 0.9927 | FAIL |
| tracing_stock | 1.0051 | 0.9668 | 0.6069 | 0.9800 | FAIL |
| tracing_patched | 1.0050 | 0.9906 | 0.5872 | 0.9790 | FAIL |

Original descriptive limits: CPU/job, client CPU/request and successful p99 ratios ≤1.10; maximum rejection-plus-timeout difference ≤0.001; client trace coverage ≥99%. Four balanced blocks are descriptive and do not replace the six-trial qualification pilot. Errors include timeouts; do not count them twice. Successful p99 excludes rejected and failed requests.

## Scheduler evidence mismatch

- fairness_b1_stock_on: cleanup wake follows final connection boundary; request 1528; decoded wake overshoots the mapped boundary by 906.945 ms versus clock-map uncertainty 697 ns.
- fairness_b2_stock_on: cleanup wake follows final connection boundary; request 1575; decoded wake overshoots the mapped boundary by 2214.914 ms versus clock-map uncertainty 604 ns.

The large mismatch cannot be explained by the saved clock-map uncertainty. The decoded stream contains sequences of events spaced by only a few nanoseconds near these mismatches. Timestamp adjustment by the Go decoder is a candidate explanation, not an established cause. The [Go trace reader](https://go.dev/src/internal/trace/reader.go) enforces increasing event timestamps; raw wire events and the exact pinned reader must be checked before using these scheduler durations.

Next: diagnose the decoded scheduler timestamps against raw wire events and service-local boundaries. Keep the original failed validation visible. Decide on any new measurement only after that audit.

## Raw wire follow-up

The pinned decoder was also run in wire mode on both failing captures. The first raw GoUnblock after each cleanup wait occurs **before** the service-local final boundary: 4.488 µs before for request 1528, and 3.780 µs before for request 1575. The decoded wake timestamps are respectively 906.950 ms and 2214.918 ms later than those raw events. This locates the discrepancy between the wire and decoded timelines, rather than in the client outcome records. [Exact raw events, generation/sequence and decoder hash](wire_audit.json).

The scheduler join must be rebuilt or its timing qualified against the raw events. Do not add a seconds-long tolerance or mark the original analysis as passed.
