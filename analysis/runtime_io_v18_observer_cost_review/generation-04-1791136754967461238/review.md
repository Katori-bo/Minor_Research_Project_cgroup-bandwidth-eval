# V18 observer cost review

All twelve trials have complete verified evidence. Five of six pairs fail only the 500 ms timely-success margin. Neither p99 nor service CPU per computation exceeds its practical margin. Effects on 500 ms success move in both directions; the pilot does not distinguish tracing cost from ordinary paired variability.

| Pair | Tracing on minus off: 500 ms timely success (percentage points) | Service CPU change | Successful-response p99 change |
|---|---:|---:|---:|
| 1 | -1.21 | +0.088% | +2.10% |
| 2 | +2.21 | +0.118% | -1.84% |
| 3 | -2.74 | +0.110% | +3.97% |
| 4 | -1.47 | +0.101% | +1.65% |
| 5 | +1.09 | +0.107% | +0.30% |
| 6 | +0.53 | +0.220% | -0.56% |

Across all 81,516 offered requests, every response succeeded within 1,000 ms. Successful-response p99 ranges from 734.5 to 768.4 ms.

Without kernel tracing, 3,518 of 9,729 requests missing 500 ms certainly completed computation before that deadline and resumed their handler afterward. The bounds account conservatively for clock uncertainty. This confirms that post-computation delay is present in the tracing-off arm. Publication and runnable readiness remain unobserved.

Computation-to-handler delay exceeds 50 ms for 15,928/40,758 tracing-off requests and 16,058/40,758 tracing-on requests.

The observer is not qualified by the prespecified practical screen. Six pairs do not establish statistical equivalence. These timing facts do not establish that quota caused individual delays. Review 500 ms sensitivity and control-arm variability before deciding whether another observer qualification experiment is warranted. The completed pilot should remain retained rather than rerun to obtain a passing outcome.
