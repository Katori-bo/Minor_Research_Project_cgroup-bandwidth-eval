# Calibration-cost assessment: simple alternatives and stop verdict

8 October 2026. The user authorized the bounded offline adequacy comparison
after the first literature screen. That authorization covers retrospective
subset fits; it does not start collection or a custom calibration algorithm.
The earlier question contract's no-fitting statement described the initial
literature-screen stage. The empirical manuscript and its outcomes are unchanged.

## Verdict

**Stop development of a custom method for the current calibration-cost candidate.**
Each of the four existing busy calibration trials, used separately, forecasts
all 16 retained deadline cases within the existing 3-percentage-point reference.
The earliest trial already meets the requested forecasting accuracy. All six
ordinary two-trial averages also meet it and pass the retained repeatability
range screen. No specific extra capability beyond ordinary direct calibration
has survived this assessment.

This closes the current candidate on the evidence available; it does not prove
optimal calibration cost, universal adequacy or the impossibility of another
research contribution. Single-trial forecasts are retrospective sensitivity
results, not a newly validated one-trial collection policy. A single trial cannot
establish across-trial repeatability or future confidence coverage.

## Decision, baselines and information discipline

The question is the [fixed-quota forecasting capability](runtime_io_calibration_cost_question_20261008.md):
forecast all-offer 500 ms deadline-miss fractions for supplied schedules at
materially lower total calibration cost than the cheapest adequate alternative.
The service, quota, FIFO model and accuracy reference remain the existing ones.
No quota period was chosen or changed.

A single busy estimate uses the four predefined backlogged 3-second windows
inside one 60-second mixed trial. The 12 seconds of counted windows do not
constitute a separately run 12-second calibration procedure.

The assessment declared 30 labels before calculating subset forecasts:

- All four single busy trials, all six two-trial averages and the four-trial
  average. The primary singleton is the earliest chronological mixed trial,
  not the singleton with the most favorable deadline error.
- Quadratic fits at equally spaced rates 0/60/120; standard D-optimal and
  A-optimal three- and four-rate designs; and all six existing rates. Each is
  fitted to calibration block 1, block 2 and both blocks pooled.
- The original whole-run CPU/job estimate as a historical negative reference.

The information-design choices use only the known offered-rate grid and
features `[1,r/120,(r/120)^2]`, with equal nominal per-trial wall cost. D-optimal
means maximizing information determinant; A-optimal means minimizing the trace
of its inverse. These are ordinary design baselines under a polynomial,
homoscedastic-noise assumption, not deadline-error optimizers. They are not a
reproduction of Ernest. Offered rate is a design proxy; observed completion
throughput is the fitted variable, so their relation must qualify in calibration.

All three-rate choices select 0/60/120. D-optimal four-rate design selects
0/30/60/120; A-optimal selects 0/60/90/120. Duplicate labels are explicitly
retained, not counted as independent evidence. The unchanged V28 quadratic
candidate rules choose admissible intercept/zero-intercept fits and a linear
fallback using calibration residuals alone. No intercept is forcibly set to
zero and no subset is chosen using validation errors.

All 16 validation outcomes were already known. Sealing these new subset
forecasts before the scoring operation prevents accidental score-time changes;
it does not restore prospective status. All declared cases, unsuccessful fits
and refusals would be retained. Here every fit was available and answered all
16 cases. Eight cases have zero observed misses and eight have nonzero misses.

## Forecast comparison

Representative predeclared comparisons are below. The
[complete 30-label table](../analysis/runtime_io_calibration_cost_assessment/20261008/comparison.md)
retains both calibration-block sensitivities and pooled results.

| Ordinary calibration | Trials | Capacity, jobs/s | Deadline MAE, pp | Maximum error, pp | Cases within 3 pp | Recorded selected lifecycle, s |
|---|---:|---:|---:|---:|---:|---:|
| Earliest single busy trial | 1 | 149.500 | 0.407 | 1.571 | 16/16 | 202.3 |
| Earliest two busy trials | 2 | 149.458 | 0.425 | 1.604 | 16/16 | 379.3 |
| All busy trials | 4 | 149.417 | 0.453 | 1.714 | 16/16 | 738.4 |
| Quadratic 0/60/120, block 1 | 3 | 160.696 | 16.119 | 35.952 | 8/16 | 420.9 |
| Quadratic D-optimal four rates, block 1 | 4 | 152.771 | 3.503 | 9.262 | 8/16 | 561.5 |
| Quadratic A-optimal four rates, block 1 | 4 | 126.084 | 31.147 | 37.690 | 0/16 | 561.6 |
| Quadratic all six rates, block 1 | 6 | 148.369 | 1.224 | 3.738 | 13/16 | 837.6 |
| Original quadratic, both blocks | 12 | 148.463 | 1.169 | 3.619 | 13/16 | 1710.7 |

Every singleton passes every capacity reference as well. Across all four
singletons, deadline MAE ranges from 0.407 to 0.544 pp, maximum error from
1.571 to 2.071 pp and nonzero-case MAE from 0.815 to 1.089 pp. Zero-miss cases
are predicted correctly by all singleton busy estimates. The earliest
singleton's nonzero-case MAE is 0.815 pp, so its overall accuracy is not solely
an artifact of including the eight zero-miss cases. All six pairs pass the
5% repeatability range reference; the full four-trial range is about 0.168%.

Reduced three- and four-rate polynomial fits do not meet the deadline reference
in either block or pooled. Three-rate interpolation achieves an essentially
zero calibration residual but extrapolates capacity to about 160 jobs/s and
fails all eight nonzero-miss checks. That is a concrete warning against treating
an exact small-sample polynomial fit as reliable capacity extrapolation.
The four-rate A-optimal design chooses the declared linear fallback. These
results do not show that all nonlinear estimators or other designs must fail.

The original full-budget busy, quadratic and whole estimates and their deadline
MAEs reproduce the sealed V28 results. V28's prospective finding and its
inconclusive minimum-advantage decision are not changed by this assessment.

## Calibration expense and disruption

The table's lifecycle cost is the sum of the selected trials' recorded
start-to-finish times. Each includes per-trial settling, startup, warmup,
measurement/drain accounting, replay and cleanup. It is a measured component
sum from the original campaign, not the elapsed time of a newly run smaller
calibration procedure. All sixteen original calibration trials were acquired;
this retrospective work saved no historical collection time.

For the earliest busy singleton, nominal warmup plus measurement is 80 s,
whereas recorded lifecycle is 202.3 s, including 116.1 s settling. The original
shared initial collection overhead is another 602.2 s, including 601.3 s initial
settling. Their sum is 804.5 s before separate preparation/prior-asset costs.
Because the original study collected four other trials first, that busy
observation actually became available 1364.6 s after collection began. Neither
number demonstrates that a standalone procedure would take 202.3 s or save a
claimed factor. Reordering could change thermal state and qualification costs.

Six shared functional-trial lifecycles total 48.0 s; unmeasured preparation
overhead, observer qualification and acquisition of retained software/workload
knowledge are additional costs. There were no failed scientific attempts in
V28. Baseline fitting took less than 0.2 ms per variant on this offline run;
this excludes parsing, record verification, forecasting, design enumeration and
prior algorithm development. The [inventory](../analysis/runtime_io_calibration_cost_assessment/20261008/inventory.md)
and [full report](../analysis/runtime_io_calibration_cost_assessment/20261008/report.json)
retain the available cost vector and original chronological availability.

Busy calibration is deliberately disruptive. The earliest single trial offers
4596 measurement requests and 600 warmup requests, consumes 16.694 measurement
CPU seconds, reaches 104 waiting jobs, and produces 992 measurement requests
over 500 ms. All requests succeed; these are deadline misses, not HTTP failures.
Across the four singleton candidates, measurement misses range from 909 to
1000. The idle/steady regression calibrations have no measured misses and peak
at one waiting job. Thus direct calibration is adequate for the declared
accuracy question, but is not an adequate answer to a new requirement forbidding
calibration-induced backlog or deadline misses. Such a requirement would change
the decision problem and would need its own prior-art and feasibility screen.

Whole-trial CPU endpoints, service/client events and counter-clock bounds were
checked. The host monitor also contains coarse CPU observations: enclosing
record brackets are at most about 46.8 ms wide, sample intervals at most about
1.05 s, and coverage surrounds every measurement interval. Native sub-period
counter files are absent. Coarse observations are potentially useful after
their own state/window analysis; this assessment did not fit shortened windows
or infer quota-phase-resolved CPU delivery from whole-run totals.

## Verification and disposition

The [independent check](../analysis/runtime_io_calibration_cost_assessment/20261008/verification.json)
passes high-precision moment-equation/Cramer-rule checks for all 18 quadratic
labels, information-design selection, 270 cost sums, 480 case-error calculations
and 32 raw trial lifecycles. Two FIFO recurrences agree on each forecast. All
1911 protected scientific files and nine additional document/report checks
remain unchanged. No scientific collection, custom selector or new scientific
threshold was introduced.

Recheck the arithmetic and preservation without changing original records:

```bash
python3 -B analysis/runtime_io_calibration_cost_assessment/20261008/verify_assessment.py
```

**Proceed/stop result: stop this calibration-cost novelty route, preserve the
negative screen, and retain the current empirical paper as its independent
contribution.** There is no basis here for another campaign or a custom
prototype. A further novelty search would need a different specific capability,
not a relabeling of ordinary calibration or more repetitions of this screen.
