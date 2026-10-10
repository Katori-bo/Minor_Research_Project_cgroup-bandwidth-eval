# NGINX prospective prediction: complete, accuracy not supported

All sealed raw records and the prospective comparison replay verify. The
campaign completed in 1,742.660 seconds (29 minutes 2.660 seconds): three
new-rate qualification services, four fresh calibration services and
eighteen held-out validation services. All 7,300 measured offers and 625
warmup offers returned correct complete compressed bodies. All measurement
throttle increments were zero; dispatch, source/runtime identity, process
stability, exact request accounting, observer inventory and owned cleanup
verify. There were no technical or applicability exits.

The calibration-only lower-median deadline was 20,565,395 ns (20.565395 ms).
The sealed forecast was 50% misses at all three validation rates. The
primary equal-profile/block mean absolute error was 5.981481 percentage
points. Its declared conditional model-based 95% interval was
[1.320988, 10.641975] points; the required upper endpoint was <=5.
The accuracy criterion failed. This interval does not establish that the
unknown population mean error exceeds five points, and does not propagate
calibration uncertainty.

| Rate requests/s | Mean observed miss % | Frozen forecast % | Mean absolute error pp |
|---:|---:|---:|---:|
| 4 | 48.833 | 50.000 | 1.389 |
| 6 | 52.611 | 50.000 | 10.167 |
| 8 | 43.611 | 50.000 | 6.389 |

At 8 requests/s, all six trials had fewer misses than forecast (41.000–
46.667%), giving 6.389-point mean absolute error. At approximately 6
requests/s, block 2 had 88.333% misses and 38.333-point error; the other
five trials had 40.333–48.333% misses. Retain that excursion in every
primary calculation. Block 2 mean error was 14.778 points.

The excursion cohort median full-response latency was 21.438653 ms.
Median scheduled-to-dispatch time was 0.541647 ms and median dispatch-to-
full-body time was 20.857623 ms. The latter includes server waiting,
compression and delivery; it is not an observed processing stage. These
records locate a longer response interval without diagnosing its cause.

The fresh reference-rate calibration itself varied: miss fractions at
the pooled deadline were 44.500%, 56.250%, 48.500% and 50.750%. Its cohort
medians ranged from 20.510439 to 20.621183 ms. A steep deadline region can
turn small duration shifts into substantial miss-fraction differences;
the observed calibration variation limits a stationarity claim. The
predeclared cohort-probability sensitivity MAEs were 5.296, 11.463, 5.111
and 6.574 points. These are descriptive and do not change the pooled fit.

At the secondary 10 ms deadline, forecast and observation were all misses;
at 25 and 50 ms, both were zero observed misses. These broad secondary
matches do not rescue the failed primary transition-region prediction or
guarantee zero future misses.

This is a scientific accuracy limitation for the newly scoped full-response
NGINX forecast, rather than another unavailable qualification. It adds
negative application-transfer evidence to the manuscript extension: zero
measurement throttling and successful apparatus checks were insufficient
to ensure the declared rate-invariant forecast accuracy in this campaign.
The original queue-adjusted V31 confirmation remains valid in its own
tested domain; NGINX did not observe that queue or test its paired-stage
comparator. No new algorithm, universal counterexample, identified scheduler
mechanism, novelty or independent-host replication has been established.

Preserve this completed generation. Do not rerun it, remove block 2,
select another deadline, relax the gate or replace calibration with pilot
data. The next step is consolidation and saved-evidence diagnosis before
any separately justified prospective follow-up.
