# Deadline sensitivity: completed bounded investigation

10 October 2026. All 78 saved NGINX validation cohorts retained across original,
power, rate and fresh deadline-panel campaigns. This is known-outcome exploratory
development, not prospective confirmation. Eight numerical tests pass; original
54-cohort panel scores and every new panel error reconcile. No new traffic,
collector, host setting, scientific acceptance decision or manuscript is changed.

The [fixed protocol](runtime_io_deadline_sensitivity_protocol_20261010.md) asks
whether calibration agreement, local CDF sensitivity and warmup-implied location
drift can warn about larger panel errors at existing acquisition cost, against
ordinary warmup-CDF disagreement. All features are computed from calibration and
25-offer warmup before target records are loaded by this program. The outcomes
were already known when the investigation was selected; that programming order
cannot turn development into confirmation. No threshold, cutoff or parameter
search is performed.

## Decision

**These fixed timing checks do not supply a demonstrated useful advance
reliability selector, and do not justify another hardware campaign in their
current form.** The investigation adds a concrete scope/cost boundary: steep
CDFs make a small timing stress large in probability units, but sensitivity alone
refuses every cohort; stable calibration and a near-matching warmup median can
still precede a larger error. Median location correction helps one older episode
and worsens the other three. This is an empirical finding, not a novel method,
causal physical-state explanation or population drift test.

Close this bounded screen. Preserve the negative controls and the one episode's
improvement together. Any further advance-reliability candidate needs an
independently motivated feature, defensible measurement cost and an equal-cost
ordinary comparator before fresh collection. Changing thresholds or fitting to
these outcomes would be further development and require separate confirmation.
Worker-wait remains held and the friend-owned independent V31 remains pending.
The user requested investigation before integration, so the manuscript remains
unchanged here.

## Fixed warnings, and their cost in coverage

The exploratory error label is each cohort's largest absolute miss-probability
error across its five calibration-defined cutoff labels; larger means >5 pp.
This label differs from the campaigns' unchanged primary block accuracy tests.
It does not assert a true population reliability state. All methods receive full
campaign calibration and the same 25-offer warmup; no acquisition is added.
The rate campaign uses its ordinary 5/s calibration panel/baseline, consistent
with the preceding scope assessment; rate-matched CDF is also reported.

| Campaign | Median-shift flag accepts | Accepted errors >5 pp | Rejected errors <=5 pp | Largest accepted error (pp) |
|---|---:|---:|---:|---:|
| Original | 9/18 | 6 | 3 | 9.667 |
| Power | 1/24 | 1 | 0 | 9.000 |
| Rate | 3/12 | 1 | 5 | 5.667 |
| New panel | 10/24 | 3 | 8 | 19.667 |

The median-shift flag accepts when the largest probability change implied by
median(warmup)-median(reference) is <=5 pp across the panel. In the new campaign,
P0 accepts 5/12 with two larger-error cohorts and four false warnings; P1 accepts
5/12 with one larger-error cohort and four false warnings. Adding calibration
agreement leaves those decisions unchanged, because both policies already pass
that constant group-level check.

Ordinary warmup-CDF disagreement accepts 2/18 original cohorts, one with larger
error, and refuses all power, rate and new panel cohorts. The fixed +/-100 us
sensitivity check refuses all 78 cohorts. These rules can avoid missed warnings
by refusing everything, but that supplies no useful answer coverage. Refusing
all new panel cohorts also rejects all 15 observed within-5-pp cohorts.

Calibration agreement accepts all power, rate and new panel cohorts. Nonetheless,
all 24 power cohorts, 5/12 rate cohorts and 9/24 new panel cohorts exceed the
exploratory 5 pp error label. Original calibration disagreement exceeds the
margin and refuses all 18, including six observed within the margin. Agreement
alone does not assure later transfer, and a calibration-only check cannot
select changing windows within a reference group.

## Sensitivity and the counterexample

Maximum reference probability change for a fixed one-sided 100 us cutoff stress:

| Reference | Maximum change (pp) | Maximum cohort deviation from reference (pp) |
|---|---:|---:|
| Original pooled | 8.375 | 6.250 |
| Older power P0 | 10.875 | 3.000 |
| Older power P1 | 10.000 | 1.750 |
| Rate ordinary 5/s | 9.375 | 2.500 |
| New panel P0 | 9.000 | 1.250 |
| New panel P1 | 11.250 | 1.500 |

All exceed the 5 pp stress margin. This identifies sensitivity near the declared
CDF transitions. It neither establishes that a 100 us physical drift occurred
nor justifies 100 us as a bound on future changes. The constant sensitivity score
cannot distinguish later cohorts within the same reference group.

Descriptive counterexample: new panel cohort 1, P0 at 8/s. Its warmup median is
only 20.851 us earlier than the calibration median; the implied largest miss
probability change is 1.875 pp, so the median flag accepts. Calibration cohort
deviation is 1.250 pp, so that flag also accepts. Nevertheless, at the frozen
3/4 cutoff 21.341755 ms, reference predicts 25% versus 44.667% observed misses,
a 19.667 pp error. Ordinary warmup-CDF disagreement is 6 pp and warns here,
but also warns on every other new panel cohort. The one recorded throttled
period in this cohort remains included; aggregate counters cannot explain its
individual errors. This example was selected after scoring and is descriptive.

## Ordinary forecast corrections

Panel-average mean absolute error in percentage points:

| Campaign | Unchanged reference | Warmup-only | Weighted reference + warmup | Median-shift correction |
|---|---:|---:|---:|---:|
| Original | 5.437 | 7.452 | 5.418 | 7.200 |
| Power | 18.514 | 6.553 | 18.031 | 4.930 |
| Rate (ordinary 5/s) | 2.617 | 8.106 | 2.533 | 6.466 |
| New panel | 3.275 | 7.986 | 3.291 | 6.709 |

Location correction predicts the reference CDF at D-delta, with exact median
half-nanosecond arithmetic. It improves the older power episode, P0 22.656 to
5.924 pp and P1 14.372 to 3.935 pp, but worsens the other campaigns. Even in
power, 18/24 location-corrected cohorts have some panel error >5 pp. In the new
panel, location correction increases MAE for both P0 (3.483 to 7.584) and P1
(3.067 to 5.834); 21/24 corrected cohorts exceed 5 pp at some cutoff versus 9/24
with the unchanged reference. This does not repair transfer generally.
The rate-matched forecast on the same panel has MAE 2.618 pp, essentially its
ordinary 5/s comparator's 2.617 pp. No new decision is based on these differences.

## Ranking and inference limits

The median-shift feature's descriptive ranking AUC in the new campaign is 0.626;
within P0 it is 0.471 (5 larger / 7 smaller errors) and within P1 0.719 (4/8).
Original is 0.556 and rate 0.629. Power has no within-5-pp reference cohorts,
so ranking between larger and smaller errors is unavailable. A seemingly
favorable P1 ordering is a development observation in twelve correlated cohorts,
not a selected confirmed rule or useful fixed-threshold result. No optimized
threshold, confidence interval or independence-based significance is reported.

All 390 quantile-labelled errors retain their cohort membership and shared
references. They are not 390 independent replicates. Policy/rate/block and
signed per-quantile summaries, unavailable-case accounting, failure handling,
all flags and every cohort are saved in screen.json. Failed offers remain mass
at infinity; location quantities refuse unavailable input medians rather than
renormalizing successes. No failed offers occur in these actual records.
Offline computation cost is unqualified for live deployment; acquisition cost
is equal and the feature-value calculation adds no traffic. No general future
risk certificate, latent-distribution shift, new-method novelty or independent
host replication is established.

Replay with `python3 -B analysis/screen_deadline_sensitivity.py --verify`.
The sealed package is `analysis/runtime_io_deadline_sensitivity/20261010/`.
