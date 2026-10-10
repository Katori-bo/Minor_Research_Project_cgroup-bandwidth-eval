# NGINX saved-evidence diagnosis

Date: 2026-10-10. Exploratory analysis of the preserved generation-01 campaign.
No workload was run; the prospective deadline, forecast, trial inclusion,
accuracy criterion and unsupported result remain unchanged. All sealed
campaign records and the comparison replay verify.

## 1. The large excursion persisted within the measurement window

Validation cohort 4 (block 2, approximately 6 requests/s) had 88.333% misses.
Its 25 warmup offers had median 20.476486 ms and 36% misses at the fixed
20.565395 ms deadline. The first 30 measurement offers had 56.667% misses;
the remaining 270 had 91.852% misses and median 21.485907 ms. Thus a single
slow request or the first request cannot explain the cohort result. These
post-hoc segments describe persistence, not a statistically estimated change point.

| Offer indices (zero-based) | Median full response ms | Miss % |
|---|---:|---:|
| 0–29 | 20.767 | 56.667 |
| 30–59 | 21.385 | 96.667 |
| 60–89 | 21.530 | 90.000 |
| 90–119 | 21.314 | 100.000 |
| 120–149 | 21.571 | 96.667 |
| 150–179 | 21.594 | 90.000 |
| 180–209 | 21.236 | 80.000 |
| 210–239 | 21.481 | 90.000 |
| 240–269 | 21.800 | 93.333 |
| 270–299 | 21.434 | 90.000 |

## 2. Observed timing locates the longer interval

Compare the excursion with all 1,500 offers in the other five same-rate
cohorts, retaining every offer. Differences of means add exactly across
these client milestones; component medians would not generally add.

| Observed interval | Other five mean ms | Excursion mean ms | Difference ms |
|---|---:|---:|---:|
| Scheduled offer to dispatch | 0.590110 | 0.554672 | -0.035438 |
| Dispatch to headers | 2.696829 | 2.886520 | +0.189690 |
| Headers to complete body | 16.801299 | 17.922920 | +1.121621 |
| Entire full response | 20.088239 | 21.364112 | +1.275873 |

About 87.9% of the extra mean duration occurs after headers arrive. Client
dispatch delay is slightly smaller in the excursion. This excludes a larger
offer-to-dispatch delay as the explanation for its longer mean response.
Headers-to-body time includes streaming compression, server scheduling,
client scheduling and delivery. It is not an observed server processing
time and does not identify which component slowed.

The identical encoded output in all 7,300 measured responses is 251,268
bytes with SHA256 09c01067d654a0d044672211cc80919f1a71116554ccd5b5da35dab9da0318af.
Application/input hashes, runtime resources, PID/start identities and thread
sets also verify. No response/output-size change explains the excursion.

No measured client response windows overlap in any of the 25 cohorts.
The next dispatch occurs more than 100 ms after the preceding complete
body across validation. This rules out overlapping client HTTP response
windows in the saved record; it does not establish an internal FIFO queue
measurement or exclusive CPU execution.

## 3. CPU and timing distributions show variation without a traced cause

The excursion uses 19.013133 ms cgroup CPU per measured offer. Other
same-rate cohorts span 18.408100–19.039043 ms. Cohorts 9 and 12 have
comparable or larger average CPU use but only 47.667% and 44% misses.
Aggregate CPU per offer therefore does not uniquely explain the miss
excursion. CPU accounting includes the declared common drain controls
and cannot assign CPU time to individual requests.

An exploratory <18 ms response threshold exposes differing lower tails:
same-rate cohorts 2/4/9/12/14/16 contain 57/1/2/1/58/57 such offers.
The threshold was selected after inspecting the saved distributions and
is not a new scientific gate. The entire excursion distribution shifted;
cohorts 9 and 12 also lost most fast responses without its large central
shift. A single common stationary response distribution is not demonstrated.

Both measurement throttle counters remain zero in all cohorts. The saved
ancestor CPU limit is unlimited; stable affinity confines the service to
CPU 2 but records no competing-task timeline or CPU reservation. No saved
scheduler trace, per-request CPU stages, client GC timeline, thermal/frequency
timeline or network event trace resolves the longer interval.

## 4. Tight-deadline sensitivity and balanced-rate patterns

The pooled calibration has 50% misses at the frozen deadline. At diagnostic
offsets of -100/-50/+50/+100 us, its miss fractions are 57.750/53.938/
45.625/41.625%. Moving by only 0.1 ms crosses roughly eight percentage
points of this steep CDF region. This explains how small timing shifts can
produce substantial probability errors; these alternative deadlines are
post-hoc arithmetic, not substitute endpoints or new validated forecasts.

At the unchanged deadline, 8 requests/s has fewer misses than 4 requests/s
in every balanced block. The six C-minus-A differences are
-7.333, -0.667, -8.667, -4.667, -6.000, -4.000 percentage points.
Their mean is -5.222 points. This is an observed within-block association,
not proof that increasing load causally improves latency.

Relative scheduled offsets modulo 100 ms differ: the 5/s reference repeats
one residue, 4/s alternates two, approximately 6/s nearly cycles three
(with 1 ns drift per three offers), and 8/s cycles four. There is no saved
exact client-clock origin or quota-replenishment trace to map those grids
onto actual quota phase. All six same-rate cohorts share the same grid but
show different distributions. Cadence alone is therefore not a demonstrated
explanation for the block-2 excursion.

## 5. What this diagnosis resolves

The unsupported accuracy outcome survives a correct evidence replay.
Its largest excursion is persistent and mainly visible after response
headers, with unchanged output/runtime and no recorded measurement
throttling or client response overlap. Together with calibration variation
and steep-deadline sensitivity, this identifies a stationarity limitation
of the tested complete-response forecast. It does not identify a scheduler,
compression, client, frequency, networking or quota-phase mechanism.

Record this diagnosis with the negative transfer result. Do not rerun this
generation, discard the excursion or retune its deadline. Any future
mechanism study would need measurements that can separate the observed
headers-to-body interval and client/server state; defining one remains
a separate prospective task. No further experiment is proposed here.
