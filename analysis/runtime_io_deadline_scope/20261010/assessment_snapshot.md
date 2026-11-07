# More experimentation before the next paper update: deadline scope

10 October 2026. The user authorized additional experimentation. One bounded
offline experiment is complete on all 54 saved NGINX validation cohorts. The
[specification](runtime_io_deadline_scope_protocol_20261010.md) defines exact
empirical CDF discrepancies and common calibration-defined deadline panels.
All historical outcomes were already known; this remains exploratory development,
not independent confirmation. No paper edit or new traffic follows this replay.

## New descriptive result

| Reference / population | Error at original deadline: MAE (pp) | Mean empirical CDF maximum (pp) | Calibration-defined panel MAE (pp) |
|---|---:|---:|---:|
| Original NGINX reference | 5.981 | 10.721 | 5.437 |
| Power matched, all policies | 15.708 | 34.031 | 18.514 |
| Power matched, P1 alone | 0.000 | 23.892 | 14.372 |
| Rate matched | 1.194 | 7.931 | 2.618 |
| Rate ordinary 5/s | 1.972 | 6.538 | 2.617 |

The clearest example is P1 power cohort 21: its matched reference forecasts zero
misses at 20.565395 ms and the cohort indeed has zero. At the reference's median
deadline, 16.823523 ms, it predicts 50% misses versus 96% observed: 46 pp error.
At the calibration 75% lower-order-statistic cutoff, 17.101607 ms, it predicts 25%
versus 85.667%: 60.667 pp error. Those cutoffs use calibration alone. The largest
empirical discrepancy is 63.083 pp at a diagnostic, outcome-derived location;
that location is not promoted to an operational deadline.

Every one of the twelve P1 cohorts agrees at the original zero-miss deadline,
while the matched-policy empirical CDF discrepancy averages 23.892 pp. Thus the
existing zero-miss result does not characterize agreement throughout the latency
distribution. The finite records demonstrate the distinction without identifying
its physical cause or establishing future failure.

Rate matching remains accurate at the original endpoint. Its calibration-panel
MAE is essentially identical to the ordinary 5/s reference (2.618 versus 2.617 pp),
and its mean empirical CDF maximum is descriptively higher (7.931 versus 6.538 pp).
This is neither a new significance decision nor evidence that rate matching
causes worse latent-distribution prediction. Pooled references, policy subgroups,
rate subgroups, all per-cohort outcomes and six-block paired descriptive gains
are retained in the [complete results](../analysis/runtime_io_deadline_scope/20261010/report.md).

## Sampling limitation

The empirical CDF maximum includes sampling variation and maximization over
cutoffs. A 5 pp empirical discrepancy is a descriptive scale, not a calibrated
all-deadline uncertainty threshold. For context, under IID samples from the same
population, applying the one-sample DKW bound to each sample with failure .025
and using the triangle/union bounds gives a conservative per-comparison 95%
same-distribution bound of

`100 * [sqrt(log(80)/(2*n_cal)) + sqrt(log(80)/(2*n_target))]`.

For 800 and 300 offers this is 13.779 pp. This illustrates why the rate-study
empirical discrepancies alone should not be labelled population drift. The
bound is not applied as a test here: independence/stationarity are unestablished,
and it supplies no family guarantee across all cohorts/methods. The one-sample
inequality is given in the primary
[Wei–Dudley paper](https://arxiv.org/abs/1107.5356). The bound here is our separate
triangle/union-bound derivation, not its stronger two-sample theorem.

## Next experimental direction

This result supports a specific fresh question: **does matched-policy calibration
forecast a declared panel of tighter deadlines accurately, including P1 cases
that appear successful at the current zero-miss endpoint?** Use fresh calibration
to determine panel deadlines before validation and retain the historical cutoff
as an additional reference. Ordinary matched-policy CDF prediction is the method
under test; pooled and same-input ordinary controls remain comparators. Adding
deadline points does not consume extra requests or require the unqualified worker
observer, but full fresh acquisition still costs time.

A new study needs a separately frozen forecast barrier, all-offer endpoint,
per-policy/deadline scoring and finite-sample-aware acceptance/cost contract.
Do not use empirical supremum <=5 pp as an automatic accuracy gate, promote the
retrospective worst cutoff to the new primary deadline, or count this replay as
confirmation. No runnable fresh package or live collection is selected by this
assessment. The potential addition is a prospective empirical scope result;
there is no established new reliability method or novelty claim.

## Verification and disposition

All original primary forecasts and error summaries reconcile. All 54 cohorts,
16,200 target offers and 5,600 calibration offers are retained; all of those
responses succeeded. Both rate-study throttled cohorts remain included. Six
tests check strict deadline equality, failure mass, tied support points, exact
suprema against exhaustive integer cutoffs, calibration-only panel inputs and
primary agreement with a large curve discrepancy. Saved analysis replay passes.

The earlier worker-wait collection remains held; its inconclusive qualification
and offline cost audit are unchanged. The manuscript and friend-owned V31 remain
unchanged and separate. Close this bounded offline experiment with its complete
result. No broad search or automatic traffic run follows.

```bash
python3 -B analysis/screen_deadline_scope.py --verify
```
