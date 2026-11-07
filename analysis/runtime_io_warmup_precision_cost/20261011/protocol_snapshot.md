# Warmup precision and collection cost: bounded offline audit

11 October 2026. Authorized continuation before manuscript integration. No fresh
traffic, setting changes, predictor fitting, outcome-dependent thresholds or
scientific acceptance revision. Existing outcomes are known. Freeze analysis
specification and sources before computing new per-cohort precision summaries.

Retain the same 78 NGINX cohorts as the sealed deadline-sensitivity screen,
using only each declared reference, its five calibration-only cutoffs and
25-offer warmup. Rate uses its ordinary 5/s reference, matching that screen.
The targets are not read to calculate precision. Preserve all prior input seals.

Compute noninterpolated median order-statistic intervals using exact integer
Bin(n,1/2) tails. Choose the largest 1-based k with
2*P(B<=k-1)<=alpha; use [X_k,X_(n-k+1)]. Under IID continuous within-window
sampling this has coverage >=1-alpha. Ties can make coverage conservative.
If no finite k exists or any input offer failed, report unavailable, retaining
the cohort. Do not silently select successful-only medians. Report each warmup's
95% interval width. For a difference of warmup and reference medians, use two
97.5% intervals and subtract endpoints; union bound yields >=95% coverage of
the median difference under the stated within-sample assumptions. No independence
between the two samples is needed for that union step. Calibrations share cohorts;
IID/stationarity within each pooled reference is not established here.

Transform difference endpoints through the observed reference CDF at D-delta.
Report largest resulting probability-range width across five cutoffs. This is
conditional interval geometry of a median-based correction with empirical
reference shape held fixed, not an interval for future miss probability or error.
It ignores distribution-shape change, dependence, new-window drift and reference
CDF estimation uncertainty. No guard is accepted from these intervals.

For each reference report largest integer-nanosecond symmetric location radius
whose empirical probability change stays <=5 pp at all five cutoffs. Compute
both directions exactly, retaining deadline equality and step discontinuities.
This is a calibration sensitivity quantity, not a measured or justified bound
on future drift. Relate that radius to the observed median interval widths.

Use the one-sample DKWM bound eps(n,alpha)=sqrt(log(2/alpha)/(2*n)) under IID
sampling. At alpha=.05 report the 25-offer uniform-CDF precision illustration
and sufficient n to make eps<=.05. These are sufficient bounds, not minimum
necessary sample sizes, power or actual noise estimates. For a comparison of
two latent window CDFs, a triangle/union illustration is
 eps(ncal,.025)+eps(nwarm,.025).
Compute its warmup requirement for <=.05 with calibration fixed at 800 and
1,600, and the floor as warmup tends to infinity. Inability to attain 5 pp under
this particular conservative equal-alpha bound is not information-theoretic
impossibility. The bound estimates contemporaneous distributions, not future
transfer. One-window 95% coverage is not simultaneous coverage of 78 windows.

Fixed count grid: 25,50,100,149,200,400,597,738,800,1600. For a hypothetical
repeat of the newest 24-service science campaign, hold the four calibration
services and qualification counts fixed. Charge extra warmup offers and
nominal scheduled time at the existing 12 services at 4/s and 12 at 8/s.
Add nominal time to the observed original campaign elapsed as an explicitly
conditional linear scenario. Exclude preflight and any new design/qualification;
more warmup may itself change workload state, lifetime or overhead.

Check the optimistic necessary service constraint, ignoring startup/drain costs:
 (nwarm-1)/rate + (300-1)/rate + 8 seconds <120 seconds.
Report maximum integer warmup counts at 4/s and 8/s under that constraint.
These maxima are optimistic, not permitted counts or qualified protocols.
Check projected campaign elapsed against 2,700 seconds, but do not treat a
passing total as passing per-cohort reserve or startup/cleanup requirements.
The existing no-retry launcher and sources stay unchanged.

Primary methods: NIST's binomial/order-statistic median discussion (use exact
outer ranks, no interpolation) and Wei/Dudley's statement of the one-sample
DKWM inequality with constant 2. Preserve links and paraphrased formulas.
No population uncertainty guarantees are asserted for this dependent workload.
The final decision must distinguish measured precision limitations, conditional
cost geometry and untested post-warmup stability. No new hardware run is selected
merely because a longer warmup narrows an IID bound. Worker-wait stays held;
friend-owned V31 stays pending; manuscript stays unchanged.
