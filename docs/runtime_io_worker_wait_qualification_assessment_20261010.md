# Worker-wait qualification completed: overhead inconclusive

10 October 2026. The single external-terminal generation-01 run completed and
its canonical raw replay succeeds. Both operational boundary probes and all 24
randomized overhead services completed; all 7,890 offers succeeded. Two throttled
overhead cohorts remain included. The frozen result is
`observer_overhead_qualification_inconclusive`, with `qualified=false`.

The local worker-identity, counter chronology, cgroup CPU residual and idle
carryover checks pass, including positive runnable-wait increments in both
boundary probes. These checks do not establish absolute wait accuracy or
predictive reliability. Incremental observer operations take 0.908–1.462 ms per
warmup in overhead on-arms, below the 20 ms cap; behavioral equivalence remains
a separate requirement.

| Rate | Target miss-rate mean change (on minus off) | Conditional interval | Frozen allowance |
|---|---:|---:|---:|
| 4/s | +0.278 pp | [-2.522, 3.077] pp | +/-2 pp |
| 8/s | -0.833 pp | [-4.833, 3.166] pp | +/-2 pp |

All six frozen intervals, including target and warmup mean latency at each rate,
extend beyond their margins. Every point estimate lies inside its margin and
every interval contains zero, which establishes neither equivalence nor harm.
Endpoints are non-saturated. Intervals retain the protocol's conditional normal
paired-difference assumptions; this one host history does not verify them.

Close this bounded qualification run and hold predictive discovery with this
observer. Its predictive usefulness remains untested. A possible revisit first
requires a bounded offline precision/cost design review and, if justified, a
separately frozen fresh qualification. No larger repeat, relaxed margin, outcome
exclusion, classifier fit or predictive campaign is selected. More target offers
alone would not resolve warmup variability. Future method evaluation must give
the ordinary state-conditioned comparator equal measurements and total cost.

The [sealed review](../analysis/runtime_io_nginx_worker_wait_qualification_review/20261010-generation01/report.md)
contains all six comparisons, boundary values, retained throttling and the
verification receipt. The [raw comparison](../analysis/runtime_io_nginx_worker_wait_qualification/generation-01/qualification/comparison.json)
and [frozen protocol](runtime_io_worker_wait_qualification_protocol_20261010.md)
remain unchanged. No manuscript edit follows this qualification-only result;
friend-owned independent V31 remains pending and separate.

Read-only replay:

```bash
python3 -B diagnostic/nginx_worker_wait_study.py replay
```
