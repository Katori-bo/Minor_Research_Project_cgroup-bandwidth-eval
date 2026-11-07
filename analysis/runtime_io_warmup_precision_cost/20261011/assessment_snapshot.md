# Warmup precision and collection cost: completed audit

11 October 2026. Authorized offline investigation before manuscript integration.
All 78 NGINX warmup/reference pairs are retained. Nine numerical tests pass,
including exact binomial coverage, tied/failed observations, shift direction,
step-function sensitivity and strict lifetime limits. No measurement targets
are loaded for precision, no new traffic or settings occur, and the manuscript
and original acceptance decisions remain unchanged. All outcomes are already
known; this is planning, not independent confirmation.

**Decision: hold longer-warmup hardware collection.** The present 25 offers give
coarse interval geometry under IID assumptions. Increasing sample count could
improve contemporaneous estimation, but a conservative sufficient CDF count is
incompatible with the current service limits, and improved precision would still
need a demonstrated relation between warmup state and the later target window.
This audit does not establish actual IID uncertainty, a minimum necessary
sample count, a novel reliability method or a reason to run a longer campaign.

The [frozen protocol](runtime_io_warmup_precision_cost_protocol_20261011.md)
separates median interval geometry, conditional distribution estimation and
collection cost. The package is
`analysis/runtime_io_warmup_precision_cost/20261011/`.

## Median precision at 25 offers

We use the binomial coverage of a noninterpolated median order-statistic interval:
choose the largest 1-based k with 2*P(Bin(n,1/2)<=k-1)<=alpha and take
[X_k,X_(n-k+1)]. This is the conservative outer-rank construction behind
[NIST's median confidence discussion](https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/mediancl.htm);
we do not use its interpolation. For n=25, the 95% interval is [X_8,X_18],
with continuous-IID coverage 95.671%. These coverage claims require the specified
sampling assumptions; independence/stationarity of this workload is unestablished.

| Campaign | Median full warmup 95% interval span (us) | Median full mapped probability span (pp) | Mapped span >5 pp |
|---|---:|---:|---:|
| Original | 564.638 | 57.094 | 18/18 |
| Older power | 523.626 | 54.062 | 24/24 |
| Rate | 538.177 | 61.688 | 12/12 |
| New panel | 525.452 | 58.438 | 24/24 |

The mapped span uses two 97.5% median intervals, one from warmup and one from
its reference, subtracts endpoints to give a >=95% median-difference interval
under the assumptions, then evaluates the observed reference CDF at D-delta.
It holds the empirical reference shape fixed and omits its CDF uncertainty,
shape changes and later drift. These spans are not confidence intervals for
future miss probabilities or forecast errors. There is no joint 78-window
coverage statement or new acceptance flag. Failure-containing medians are
unavailable without dropping their cohort; no actual inputs failed here.

In the new campaign, the median warmup span is 574.284 us for P0 and 489.814 us
for P1. The corresponding median mapped probability spans are 61.938 and
56.438 pp. All 24 hypothetical median-difference intervals include zero; that
does not establish zero drift or equivalence. Older power P0 has all 12
illustrative difference intervals excluding zero, which is descriptive context
for the earlier location-correction improvement, not a validated physical-state
or independence claim.

The calibrated step functions tolerate only small symmetric location shifts
before some panel probability changes by more than 5 pp:

| Reference | Largest symmetric radius staying within 5 pp (us) |
|---|---:|
| Original pooled | 56.624 |
| Older power P0 | 52.210 |
| Older power P1 | 45.438 |
| Rate ordinary 5/s | 49.218 |
| New panel P0 | 47.708 |
| New panel P1 | 43.496 |

These are exact empirical sensitivity radii, including equality and jumps, not
bounds on actual future state changes. Their small size relative to the full
median spans shows why a small estimated median difference cannot certify a
precise correction from 25 offers under this construction.

New P0/8/s cohort 1 illustrates the limitation. Its warmup median point difference
is -20.851 us, as reported in the preceding screen. Here its full warmup 95%
interval spans 434.632 us; the illustrative median-difference interval is
[-430.593, 355.029] us. Mapping that interval through the reference gives a
maximum 60.125 pp probability span. The previous prospective 19.667 pp error
remains unchanged; this audit does not claim to explain its physical cause.

## Conservative CDF estimation and acquisition

The one-sample IID DKWM inequality bounds the uniform empirical-CDF error by
sqrt(log(2/alpha)/(2*n)). The constant 2 and IID scope are stated by
[Wei and Dudley](https://arxiv.org/abs/1107.5356).
At n=25 and alpha=.05 this gives a 27.162 pp halfwidth. Our inversion gives
738 as a sufficient count for a <=5 pp 95% uniform-CDF halfwidth. This is
neither a minimum necessary count nor expected error, power or future-transfer
reliability. It concerns a contemporaneous sampled distribution; it cannot
certify the subsequent window. No independence assumption is established here.

For two latent window distributions, our conservative triangle/union calculation
uses alpha=.025 for each CDF and sums their halfwidths. With 800 calibration
offers its floor is 5.233 pp as warmup tends to infinity, so no finite warmup
count reaches 5 pp under this specific equal-alpha bound. With 1,600 calibration
offers the floor is 3.701 pp and the sufficient warmup count is 12,975.
Those are limitations of this particular bound/allocation, not universal sample
requirements or evidence that every possible procedure is incapable of 5 pp.
This is derived from one-sample bounds, not an asserted sharp unequal-sample
DKWM inequality. No new population shift test follows.

For the latest 24-service science schedule, replacing each 25-offer target warmup
by 738 offers, with other counts unchanged, adds:

- 17,112 offered requests; science rises from 9,500 to 26,612 offers, or 27,642
  including the unchanged 1,030 qualification offers.
- 53.475 minutes of nominal schedule time: 12 windows at 4/s and 12 at 8/s.
- A conditional science-time projection of 89.148 minutes, versus the observed
  35.673 minutes, assuming every other duration and behavior stays unchanged.

These are cost scenarios, not an implemented protocol or certified timing.
They exclude preflight, new design/qualification, extra startup/cleanup and
behavioral effects of longer warmup. The existing 45-minute science limit fails.

The service lifetime also fails, even ignoring startup/drain costs. Warmup plus
300 measurement offers and the 8-second reserve requires 267 seconds at 4/s
and 137.5 seconds at 8/s for 738 warmup offers, exceeding 120 seconds at both.
Under this optimistic necessary constraint the largest integer counts are 149
at 4/s and 597 at 8/s. Actual startup, drain, cleanup and enclosing per-cohort
reserves tighten feasibility; those maxima are not authorized or qualified
settings. The existing launcher, watchdog and frozen evidence stay unchanged.

## What remains unresolved

The previous investigation found that calibration agreement and a small warmup
median difference can precede larger panel errors. This audit shows why the
present warmup may be too imprecise for fine median-based inference under the
chosen statistical construction. It does not determine whether sampling noise,
shape differences, chronology or unmeasured server state caused those errors.
Nor does it show that a longer warmup would predict the future better: longer
measurement changes the decision time and potentially the state being measured.

Any next method candidate must justify both within-window precision and a
window-to-future stability mechanism at acceptable cost, then face an equal-cost
ordinary comparator on fresh evidence. More repetitions of the same diagnostic
or a tuned threshold are not automatically justified by this audit. No new
hardware collection is selected. Worker-wait remains held; the friend's
independent V31 replication is pending; the open manuscript remains unchanged.

Replay: `python3 -B analysis/warmup_precision_cost.py --verify`.
