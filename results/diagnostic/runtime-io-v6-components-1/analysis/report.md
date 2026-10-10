# Tracing component comparison

Diagnostic evidence only. This is not a passed pilot and cannot unlock full collection.

Base server/client timing stays enabled in every mode. Runtime-only has no request-level scheduler association or final-flush guarantee. Custom-only has no scheduler evidence. Only combined mode receives full lifecycle analysis.

| Mode | Rejection range | Error range (includes timeouts) | Median successful p99 ms | Median CPU µs/completed work |
|---|---:|---:|---:|---:|
| baseline | 0.000%–0.574% | 0.000%–0.000% | 4071.160 | 4017.7 |
| runtime | 3.974%–4.547% | 0.000%–0.000% | 2342.473 | 4049.6 |
| custom | 0.574%–4.283% | 0.000%–0.000% | 3872.338 | 4043.3 |
| combined | 4.327%–4.547% | 0.000%–0.000% | 1656.185 | 4058.1 |

Inspect per-trial results and within-block differences in contrasts.csv; four repeats are descriptive, not a causal verdict. Lower successful-request latency with more failures is not an improvement.

Host monitor retains per-core utilization and process interval CPU deltas. Deltas exclude processes missing at either endpoint; last_cpu is a sample, not interval core attribution.

Choose any optimization only after reviewing scheduler waits and component differences, then validate it in a fresh six-trial pilot with the unchanged gates.
