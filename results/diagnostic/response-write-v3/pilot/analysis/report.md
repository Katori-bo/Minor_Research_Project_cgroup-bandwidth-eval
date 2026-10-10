# Diagnostic trial results

Pilot observations are diagnostic only.

| Run | p99 end-to-end ms | p99 pre-admission ms | p99 queue ms | p99 processing ms | p99 post-work ms | p99 resume-to-write ms | p99 write-call ms | p99 write-to-exit ms | p99 signed e2e-minus-handler ms | Trace coverage | Rejections | Timeouts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| pilot_overhead_1 | 3916.796 | 0.019 | 705.697 | 93.650 | 104.828 | 0.018 | 0.021 | 0.008 | 3751.255 | 1.000 | 0.000% | 0.000% |
| pilot_overhead_2 | 4218.229 | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0.000% | 0.000% |
| pilot_overhead_3 | 4220.720 | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0.000% | 0.044% |
| pilot_overhead_4 | 1934.198 | 0.020 | 990.578 | 114.468 | 176.793 | 0.026 | 0.024 | 0.008 | 1918.310 | 1.000 | 5.519% | 0.000% |
| pilot_p100000_w1_on | 894.668 | 0.023 | 887.832 | 55.825 | 0.708 | 0.015 | 0.019 | 0.001 | 43.255 | 1.000 | 0.662% | 0.000% |
| pilot_p100000_w1_off | 889.276 | NA | NA | NA | NA | NA | NA | NA | NA | NA | 0.618% | 0.000% |

Each p99 is calculated separately from its per-request distribution. Never add or subtract the displayed p99 values to claim a request-level explanation.

The handler exit marker is recorded after event storage and before unlocking/returning. The signed e2e-minus-handler value subtracts durations for the same request, not absolute clocks. It may be negative if client completion overlaps server cleanup; negative values and write errors are retained as outcomes. Neither a write return nor the exit marker proves delivery.

| Run | Server write errors | Negative signed differences | Slowest 1% mean signed difference / e2e |
|---|---:|---:|---:|
| pilot_overhead_1 | 0 | 0 | 91.415% |
| pilot_overhead_2 | 0 | 0 | NA |
| pilot_overhead_3 | 0 | 0 | NA |
| pilot_overhead_4 | 0 | 0 | 94.738% |
| pilot_p100000_w1_on | 0 | 0 | 0.264% |
| pilot_p100000_w1_off | 0 | 0 | NA |