# Worker-wait qualification result: operational boundaries pass, overhead inconclusive

10 October 2026. Read-only review of the single completed, frozen generation-01
qualification. This is measurement qualification, not a predictor experiment or
an independent method comparison. No original source, protocol, raw record,
acceptance margin or manuscript is changed by this review.

## Verified acquisition and boundary result

The canonical `python3 -B diagnostic/nginx_worker_wait_study.py replay` succeeds:
preparation/source and raw evidence seals, process identity, fixed-policy and
scheduler readbacks, counter/event chronology, all-offer accounting, paired
comparison and final receipt agree. Both boundary services and all 24 overhead
services completed. All 7,890 offered responses succeeded. Boundary collection
took 41.526 seconds and overhead collection 1,752.786 seconds (29.213 minutes).

Both boundary probes satisfy the frozen operational checks. Worker CPU per offer
was 18.711 ms at 4/s and 18.571 ms at 8/s; runnable-wait per offer was 8.780 us and
26.985 us respectively. Worker/cgroup CPU residuals were 1.400 and 0.920 us per
offer, below the 100 us allowance. Both idle checks record zero additional CPU,
wait and scheduling-count increments. Both witness positive runnable waiting.
These observations establish the declared local boundary checks, not absolute
wait accuracy, request-level waiting attribution or a reliability signal.

Two overhead cohorts retain measurement throttling: cohort 7 (off, 8/s, block 2)
records one period / 11,603 us; cohort 15 (on, 8/s, block 4) records one period /
1,057 us. Neither is removed, replaced or reinterpreted as a technical failure.
No cohort has a technical qualification exit.

## Why overall qualification remains inconclusive

On-minus-off paired comparisons have six pairs per rate. The frozen rule requires
all six conditional intervals wholly inside their engineering margins; every
interval fails that containment check:

| Rate | Metric | Mean on-minus-off | Conditional interval | Allowed margin | Equivalence |
|---|---|---:|---:|---:|---|
| 4/s | Target miss rate (pp) | +0.278 | [-2.522, 3.077] | +/-2 | Not supported |
| 4/s | Target mean latency (us) | -21.809 | [-134.771, 91.153] | +/-100 | Not supported |
| 4/s | Warmup mean latency (us) | +15.751 | [-328.940, 360.442] | +/-100 | Not supported |
| 8/s | Target miss rate (pp) | -0.833 | [-4.833, 3.166] | +/-2 | Not supported |
| 8/s | Target mean latency (us) | -28.856 | [-157.989, 100.276] | +/-100 | Not supported |
| 8/s | Warmup mean latency (us) | -67.336 | [-404.026, 269.354] | +/-100 | Not supported |

The intervals are the prespecified 99.5% Student-t intervals (multiplier 4.774,
df5), with family coverage >=97% conditional on approximately independent normal
paired differences. This single history does not validate those assumptions.
Both pooled endpoints are informative (80.861% and 82.028% misses), so endpoint
saturation is not the failing gate. Every interval contains zero and every point
estimate lies inside its margin. That does not establish equivalence, and the
result does not demonstrate a harmful observer effect either.

Observer operations in overhead on-arms take 0.908–1.462 ms total per warmup,
below the 20 ms timing cap. This measures the two snapshots, snapshot serialization
and provisional calculation/write, not a per-request additive latency effect.
Small operation wall time cannot replace the behavioral equivalence comparison.
Shared initial status/quiet/selection controls are present in both arms and charged
separately; this run does not qualify their absolute cost versus older campaigns.

## Decision and next gate

The recorded status is `observer_overhead_qualification_inconclusive` and
`qualified=false`. Close this bounded qualification run with its complete result.
Hold predictive discovery using this observer. Do not label the worker-wait
hypothesis ineffective: its advance predictive usefulness was never tested.
Do not widen margins, drop noisy or throttled pairs, reinterpret zero-crossing as
success, overwrite/resume generation-01, or automatically repeat until it passes.

If the worker-wait route is revisited, the next useful work is a bounded offline
precision-and-cost design review. Use this run only as development evidence to
assess whether a separately frozen qualification can plausibly resolve the same
engineering tolerances within a useful collection budget, and whether any
boundary/observer change is independently justified. Variance planning from six
pairs is uncertain; adding offers to the target does not automatically resolve
25-offer warmup variability. A redesigned observer would need fresh workload
qualification. No redesigned protocol or new collection is selected here.

Only after adequate measurement qualification should a separate discovery study
ask whether matched CPU/runnable-wait drift predicts subsequent transfer error.
Any eventual reliability method must beat an ordinary state-conditioned comparator
with the same measurements, warmup budget, boundary costs and decision time, then
receive a fresh declared confirmation. These qualification outcomes cannot serve
as that independent confirmation. The empirical manuscript remains unchanged;
friend-owned independent V31 remains pending and separate.

## Evidence and replay

* [Frozen protocol](../../../docs/runtime_io_worker_wait_qualification_protocol_20261010.md)
* [Raw comparison](../../runtime_io_nginx_worker_wait_qualification/generation-01/qualification/comparison.json)
* [Final receipt](../../runtime_io_nginx_worker_wait_qualification/generation-01/qualification/summary.json)
* [Review data](review.json)

```bash
python3 -B diagnostic/nginx_worker_wait_study.py replay
```
