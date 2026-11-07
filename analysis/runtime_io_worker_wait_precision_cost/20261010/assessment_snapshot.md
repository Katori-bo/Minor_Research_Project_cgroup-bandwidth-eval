# Worker-wait offline precision/cost assessment

10 October 2026. All six observed pairs at both rates remain development inputs.
The prior qualification stays inconclusive; no live run, predictor, manuscript
change or acceptance-rule revision follows this assessment.

**Decision: hold collection with the unchanged observer.** Warmup paired mean
latency SD (173–177 us) dominates the +/-100 us equivalence gate. Increasing only
the 300-offer target window would leave this warmup gate unresolved. Modest
one-hour or two-hour fresh-run illustrations still miss warmup width containment
even under a zero-effect assumption and unchanged pilot noise.

| Fresh-run illustration | Pairs at 4/s / 8/s | Offers | Projected collection time |
|---|---:|---:|---:|
| Zero effect, width-only geometry, balanced | 30 / 30 | 39,090 | 2.45 h |
| Zero effect, conservative model bound, balanced | 102 / 102 | 132,690 | 8.29 h |
| Pilot means persist, conservative model bound, unequal | 139 / 804 | 613,040 | 30.78 h |

Width geometry substitutes assumed mean/SD into the interval and is not power.
The conservative bound gives a sufficient >=80% model-based chance of passing
all six interval gates, assuming IID normal paired differences within each metric
and the stated population moments. It is not a minimum required sample size,
estimated actual power or overall hardware qualification success probability.
No independence across metrics is required for its union bound. Future t critical
values preserve 99.5% interval coverage; the original sealed six-pair decision
is unchanged. Technical/boundary/endpoint gates are outside this probability.

Hours charge fresh complete services, verification gaps and fresh boundary
probes. Preflight, inter-session rest, new preparation, predictive discovery and
confirmation are excluded; linear scaling and stable future noise are not
verified. The observed six pairs are not pooled or subtracted. Neither unequal
allocation nor the 80% planning example constitutes a selected protocol.

The SD estimate itself is weak: each individual normal-model 95% interval spans
0.624–2.453 times its pilot SD. Even a hypothetical 25% reduction in SD leaves
the conservative zero-effect unequal illustration at 4.90 hours. Zero effect
and persistence of the pilot means are scenarios, not causal findings.

The [sealed detailed assessment](../analysis/runtime_io_worker_wait_precision_cost/20261010/report.md)
preserves formulas, all metrics, budget and SD-sensitivity grids, source/input
hashes, six numerical checks and replay. The
[planning program](../analysis/worker_wait_precision_cost.py) performs no workload
collection. Primary formula references are linked in the detailed assessment.

Revisit only with an independently justified way to reduce variability or
disturbance while retaining useful inputs and boundaries, or an explicitly
justified larger research budget. Any redesigned observer needs separately
declared fresh qualification and an equal-information/equal-cost ordinary
comparator in subsequent predictive work. No such design or collection is
selected here. Predictive usefulness remains untested; friend-owned V31 remains
pending and separate.

```bash
python3 -B analysis/worker_wait_precision_cost.py --verify analysis/runtime_io_worker_wait_precision_cost/20261010/planning.json
```
