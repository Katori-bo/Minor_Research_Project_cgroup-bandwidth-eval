# Offline worker-wait precision versus collection cost

10 October 2026. Development planning from the completed six-pair-per-rate
qualification. No traffic, host setting change, experiment launch, predictor fit
or manuscript edit. Generation-01 remains inconclusive under its original sealed
rule. This analysis is not a revised acceptance decision or a frozen new campaign.

## Decision

Hold further collection with the unchanged observer. There is no compelling
small extension within the earlier bounded collection envelope: even an optimistic
zero-effect width projection requires substantially more fresh pairs. The
conservative probability-based illustration is longer still, is sensitive to
uncertain pilot moments and cannot be run by extending the sealed 45-minute
collector. The main bottleneck is warmup mean-latency equivalence, not just target
miss-rate precision. More target offers alone would not resolve that bottleneck.

This does not show that runnable-wait lacks predictive value or that the observer
causes harm. Those claims remain untested. It shows why a larger unchanged
qualification should not be selected merely to seek a passing result. Revisit
only for a concrete, independently justified way to reduce warmup variability or
observer disturbance while preserving valid inputs and decision boundaries, or
for an explicit larger budget supported by the scientific value. Such a change
needs a new declared design and fresh qualification; no change is selected here.

## Inputs and bottleneck

All six observed on-minus-off pairs per rate are retained, including both
measurement-throttled cohorts. The following standard deviations measure paired
between-service variation; they are not identified causal observer effects.

| Rate | Metric | Pilot mean | Paired sample SD | Frozen absolute margin |
|---|---|---:|---:|---:|
| 4/s | Target misses (pp) | +0.278 | 1.436 | 2 |
| 4/s | Target mean latency (us) | -21.809 | 57.960 | 100 |
| 4/s | Warmup mean latency (us) | +15.751 | 176.857 | 100 |
| 8/s | Target misses (pp) | -0.833 | 2.052 | 2 |
| 8/s | Target mean latency (us) | -28.856 | 66.257 | 100 |
| 8/s | Warmup mean latency (us) | -67.336 | 172.752 | 100 |

Warmup paired SD is about 173–177 us against a 100 us margin. The 8/s pilot
warmup mean is -67.336 us, leaving only 32.664 us of geometric headroom if that
mean persists. It could instead be sampling noise or chronological state drift;
this analysis neither treats it as established bias nor centers it away to
qualify the run. Zero-effect and observed-mean cases are separate scenarios.

With only six independent normal pairs, each SD's individual 95% interval is
0.624–2.453 times its sample value. These are conditional, non-simultaneous
intervals, not evidence of normality or stable future noise. The formula and
its normality sensitivity are documented by
[NIST](https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/sdconfli.htm).
Mean/SD scenarios are not confidence guarantees about the next run.

## Two distinct planning questions

**Width-only geometry:** For a hypothetical fresh sample of n pairs per rate,
substitute the scenario SD and mean into
`abs(delta) + t(.9975,n-1) * sigma / sqrt(n) <= margin`.
This preserves the 99.5% interval coverage level and the original margins,
using the appropriate future degrees of freedom. It is not expected interval
width, power, or an actual qualification decision. The original six-pair frozen
4.774 multiplier and outcomes remain unchanged. The Student-t interval formula
is documented by [NIST](https://www.itl.nist.gov/div898/handbook/prc/section2/prc221.htm).

**Conservative model-based chance of passing all six interval gates:** To give
a sufficient bound of at least 80%, allocate failure epsilon=(1-.80)/6=1/30
per gate, half to two-sided sample-mean deviation and half to the upper sample-SD
tail. For each metric, require

```text
abs(delta) + [z(1-epsilon/4)
              + t(.9975,n-1) * sqrt(chi2(1-epsilon/2,n-1)/(n-1))]
             * sigma/sqrt(n) <= margin.
```

For independent identically normal pairs within each metric, the sample mean
has SD sigma/sqrt(n) and the scaled sample variance is chi-squared. On the two
bounded events, the whole t interval lies inside the margin. A union bound
across all six gates gives at least .80; independence across gates is unnecessary.
This is a deliberately conservative sufficient design, not the minimum necessary
sample size or a numerical estimate of actual power. 80% is a planning example,
not a changed acceptance criterion. It excludes technical failures, boundary
checks, endpoint saturation and phase/lifetime limits, so it is not an overall
qualification success probability. Pilot moments are assumed parameters, not
known population values.

## Fresh collection cost at observed noise

| Mean scenario | Calculation | Unequal pairs: 4/s / 8/s | Fresh offers | Unequal hours | Balanced pairs per rate | Balanced hours |
|---|---|---:|---:|---:|---:|---:|
| Zero effect | Width only | 30 / 28 | 37,790 | 2.39 | 30 | 2.45 |
| Zero effect | Conservative >=80% model bound | 102 / 98 | 130,090 | 8.17 | 102 | 8.29 |
| Observed pilot means | Width only | 40 / 225 | 172,340 | 8.68 | 225 | 18.27 |
| Observed pilot means | Conservative >=80% model bound | 139 / 804 | 613,040 | 30.78 | 804 | 65.25 |

The optimistic balanced width-only case is 30 pairs per rate, 39,090 offers,
about 2.45 hours. Under zero effect, the conservative balanced illustration is
102 pairs per rate, 132,690 offers, about 8.29 hours. Holding the pilot means,
unequal allocation still projects 30.78 hours / 613,040 offers under the
conservative bound, versus 65.25 hours if both rates use 804 pairs. None of these
is a selected experiment or a claim that so many pairs are strictly necessary.

One-hour and two-hour illustrations (12 and 24 balanced pairs, respectively)
still fail width containment for warmup at both rates even when centered at zero.
Thus a modest enlargement does not resolve the frozen six-metric requirement
under unchanged observed noise.

Costs use complete observed service lifetimes and group verification gaps, not
traffic time alone: about 186.62 s per fresh 4/s pair and 105.51 s per fresh 8/s
pair, plus the 41.526-second boundary phase. A pair is two fresh services with
25 warmup and 300 target offers each (650 offers); two new boundary services add
90 offers. The result file retains exact costs. Every row is entirely fresh
collection; the existing six pairs are development data and are not subtracted
from the budget or pooled into a new confirmation.

Linear hours are illustrations, not certified wall-time bounds. They omit
preflight/inventory, package preparation, inter-session rest, predictive
discovery and independent confirmation. Long runs or multiple sessions would
require a separately declared blocking, baseline and qualification design;
stationary independent normal noise over those hours is unestablished.
Unequal rate allocation is a cost illustration, not a rewritten schedule.

## Sensitivity to future paired noise

| Mean scenario | Future SD / pilot SD | Unequal pairs: 4/s / 8/s | Unequal hours | Balanced hours |
|---|---:|---:|---:|---:|
| Zero effect | 0.75 | 61 / 59 | 4.90 | 4.96 |
| Zero effect | 1 | 102 / 98 | 8.17 | 8.29 |
| Zero effect | 1.5 | 215 / 206 | 17.19 | 17.46 |
| Zero effect | 2 | 371 / 354 | 29.62 | 30.12 |
| Observed pilot means | 0.75 | 83 / 461 | 17.83 | 37.42 |
| Observed pilot means | 1 | 139 / 804 | 30.78 | 65.25 |
| Observed pilot means | 1.5 | 297 / 1772 | 67.34 | 143.80 |
| Observed pilot means | 2 | 515 / 3118 | 118.09 | 253.03 |

Even a hypothetical 25% SD reduction does not make the conservative zero-effect
case a short run (~4.90 unequal hours). These multipliers are sensitivity
assumptions, not demonstrated engineering improvements. Target-window changes,
extra warmup offers, pairing changes or time adjustments would alter the
measurement/comparator contract or require new empirical variance evidence;
none is authorized as a live experiment by this offline audit. Do not remove
outliers, relax margins or choose post-hoc covariates to rescue generation-01.

## Reproduction and preservation

The additive [planning program](../../../analysis/worker_wait_precision_cost.py)
uses only Python's standard library. Numerical checks use Cauchy/exponential and
df5 analytic CDF oracles, independent normal-model simulation, and
[NIST Student-t](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3672.htm)
and [chi-square](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3674.htm)
quantile tables. All six checks pass. No workload test is involved.

```bash
python3 -B analysis/worker_wait_precision_cost.py --verify analysis/runtime_io_worker_wait_precision_cost/20261010/planning.json
```

[Machine-readable scenarios](planning.json), input hashes, source snapshots,
test/verification receipts and an assessment seal preserve this calculation.
The prior qualification, empirical manuscript and friend-owned V31 remain
unchanged. This audit does not establish a reliability method or novelty.
