# V25 results: valid records, a scoped estimator mismatch, unresolved controls

2026-10-07. Generation-01 completed all sixteen diagnostic trials. Independent
completion replay passed; every raw-derived phase/report value, source/binary
receipt, environment/observer identity and bounded collection receipt verified.
No technical retry was used. All owned containers/cgroups were cleaned up.
Collection took 56.01 minutes including initial/per-trial settling.
The [sealed review](../analysis/runtime_io_v25_result_review/20261007/report.json)
binds the evidence. The original report is at
`analysis/runtime_io_v25/generation-01/analysis/1791389865386770727/report.json`.

## Recording quality

The eight sampler-on trials produced 33,260 readings with no skipped sampling
slots. Maximum acquisition wall time was 0.274273 ms. All eight passed the
frozen measurement uncertainty budgets. The collector worked reliably in these
trials; this is not a guarantee for every future run.

## Repeated controls

| Job size | Off mean misses | On mean misses | On-minus-off | Largest consecutive same-condition miss difference |
|---|---:|---:|---:|---:|
| Small | 24.1755% | 22.6480% | -1.5275 percentage points | 0.6184 percentage points |
| Large | 21.5769% | 20.4873% | -1.0895 percentage points | 3.1213 percentage points |

Small-job miss contrasts were -1.4502 and -1.6048 percentage points under the
two order directions. Both exceeded the largest observed same-condition
difference and had the same sign. We cannot dismiss this as ordinary repeat
variation, but four runs per condition do not establish a causal sampler effect
or statistical equivalence. Balanced order does not remove all host-state effects.

Large-job miss contrasts were -2.2821 and +0.1031 percentage points. Their
opposite signs, and a 3.1213-point off/off repeat difference, leave the sampler
comparison unresolved. The previous single-pair failure therefore was not
sufficient to attribute the deadline difference to the collector.

Average busy-capacity differences were only +0.2516% (small) and +0.1297%
(large). Whole CPU/job differences were -0.0940% and -0.0936%. These are within
the earlier 2% reference margins descriptively. They do not demonstrate that
deadline behavior is equivalent or that all sampler effects are negligible.

## What the phase measurements show

All eight on trials met the positive-queue busy definition. Their delivered
CPU bounds stayed within approximately 0.4933–0.5067 CPU, near the declared
0.5 CPU allocation. Whole-cohort CPU/completion consistently exceeded
busy-window CPU/completion:

| Job size | Envelope of whole/busy CPU-cost bounds | Approximate excess |
|---|---:|---:|
| Small | 1.06033–1.09140 | 6.0–9.1% |
| Large | 1.04997–1.07879 | 5.0–7.9% |

These are envelopes of per-trial accounting/clock bounds, not confidence
intervals. One large trial's conservative lower bound was 4.9971%, just below
the earlier 5% scientific threshold; seven of eight lower bounds exceeded it.
No original scientific pass is inferred.

For the on-trial condition means, nominal CPU divided by whole-cohort CPU/job
predicts 138.82 small jobs/s versus 149.42 measured busy jobs/s (7.09% lower),
and 70.53 large jobs/s versus 75.06 measured busy jobs/s (6.03% lower). These
are descriptive capacity calculations, not a new deadline-model validation.

None of the eight planned low phases met the frozen V25 low-state definition.
Seven had queue maxima above one; six had strictly positive lower bounds on
throttled periods; all eight had positive upper bounds. The lower-arrival-rate
phase was not a verified uniformly unthrottled, shallow-queue baseline.
This does not invalidate its aggregate CPU measurement, but it prevents a
clean interpretation as the intended low state. Do not move the windows or
relax the frozen rule to turn these data into a confirmatory pass.

## Contribution and next step

V22/V23 remain the evidence for the tested forecast comparison and limited
transfer across work sizes/burst patterns. V25 adds repeated descriptive
evidence that whole-cohort CPU/job and saturated-window CPU/job differ, alongside
documented measurement and observer limits. It does not prove that a pure
low/busy state mixture causes the mismatch, establish deadline observer
equivalence, or establish novelty against the literature.

Stop automatic collection and use this review to scope the modest draft. A
defensible empirical claim is that whole-cohort CPU/job underpredicts measured
busy capacity under the retained workloads, while busy CPU delivery remains
near nominal. Keep the state explanation exploratory and the observer deadline
difference explicit. No further experiment is scheduled or launched by this
review. Any additional collection should serve a specific indispensable claim.
