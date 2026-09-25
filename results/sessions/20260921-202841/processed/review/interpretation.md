# Completed experiment: interpretation and audit

Session `20260921-202841`. All 300 trials and all 60 conditions are included, with five
repetitions per condition. The 10% CV threshold below is a descriptive variability
screen added during analysis, not an exclusion rule or a predeclared hypothesis test.

## Main interpretation

The effect of quota period depends on offered load, traffic pattern, and worker count.
Moderate traffic usually has p99 near 6–7 ms. High steady traffic is sensitive to the
10 ms period. Under high bursty traffic, every capped condition has much higher tails
than its uncapped comparison. The 100 ms period with four workers is especially poor.
The data do not support a universal claim that a longer period always improves latency.

## Measurement audit

- Matrix/configuration and raw request accounting checks: 0 discrepancies.
- Scheduled requests: 1,618,350; successful: 1,595,274.
- HTTP 503 queue rejections: 23,059; request errors: 17.
- Successful-request p50, p95 and p99 were recalculated from every trial's raw requests
  using the generator's nearest-rank rule and checked against both saved summaries.
- No generator missed arrivals or client drops; worst run dispatch-lag p99:
  1.095 ms. Monitor coverage: 58–60 samples per run.
- All accepted pretrial means were within the original temperature band; observed
  range: 37.89–43.49 C.
- Cgroup limits, CPU affinity, uncapped recorded ancestors, power consistency within
  each trial, and counter deltas were checked. Unlimited trials have zero own throttling.
- Original experiment source/binary hash mismatches: 0.

These checks establish internal consistency, not absence of all measurement bias.
The latency summaries cover successful requests only. Failures remain separate outcomes;
the study does not claim a p99 for all offered requests including timeouts or rejections.

## High steady traffic

Arithmetic mean of five run p99 values, in milliseconds; this is not a pooled request p99.

| Period | 1 worker | 2 workers | 4 workers |
| --- | --- | --- | --- |
| 10 ms | 23.65 | 355.77 | 429.83 |
| 50 ms | 7.35 | 6.97 | 6.88 |
| 100 ms | 6.06 | 6.09 | 5.98 |
| 250 ms | 5.97 | 5.95 | 5.92 |
| Unlimited | 5.93 | 5.93 | 5.94 |

The 10 ms two-worker and four-worker means are influenced by rare severe runs. Their
median run p99 values are 127.96 and 215.01 ms, while maxima are 1296.25 and 1423.29 ms.
Those two severe runs also contain all 810 steady-traffic queue rejections. Keep those
observations; do not remove them as inconvenient outliers.

## High bursty traffic

Arithmetic mean of five run p99 values (ms):

| Period | 1 worker | 2 workers | 4 workers |
| --- | --- | --- | --- |
| 10 ms | 1075.01 | 1306.87 | 1248.33 |
| 50 ms | 1005.99 | 1246.51 | 1382.65 |
| 100 ms | 828.76 | 2500.33 | 4302.71 |
| 250 ms | 478.78 | 722.37 | 1157.63 |
| Unlimited | 6.46 | 6.45 | 6.46 |

Failed requests as a percentage of all scheduled requests, summed over five trials:

| Period | 1 worker | 2 workers | 4 workers |
| --- | --- | --- | --- |
| 10 ms | 5.71% | 13.90% | 7.22% |
| 50 ms | 6.26% | 13.82% | 13.43% |
| 100 ms | 0.00% | 4.77% | 0.44% |
| 250 ms | 0.00% | 0.00% | 0.00% |
| Unlimited | 0.00% | 0.00% | 0.00% |

The 250 ms period improves high-burst tails over 10 ms most clearly for one and two
workers. With four workers, those periods overlap in their repeated-run distributions.
At 100 ms, moving from one to four workers raises mean run p99 from 828.76 to 4302.71 ms.
This comparison is an observed interaction. Scheduler runtime allocation, queue dynamics,
and application/runtime scheduling are possible mechanisms; this experiment alone does
not isolate their individual contributions.

All 17 recorded request errors are HTTP client timeouts while awaiting headers, in high
bursty 100 ms conditions with two or four workers. The client timeout is five seconds.
High burst peaks are 169.815 requests/s, above the 133.19 requests/s calibration reference.
Thus transient overload is deliberately possible even though the mean rate is 113.21.
That reference capacity was measured for one worker at a 100 ms period, not every condition.

## Moderate traffic and repeatability

Moderate steady means range from 6.57 to 6.63 ms. Moderate bursty means are approximately
6.50–6.64 ms except 10 ms with two workers (18.37 ms; individual runs 6.54–40.92 ms).
No moderate trial recorded a rejection or request error. Six conditions have a run-p99
CV above 10%; all are listed below. Small differences of a few hundredths of a millisecond
should not be promoted to general operational recommendations.

| Period (us) | Workers | Load | Pattern | Min p99 | Mean p99 | Max p99 | CV |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10000 | 1 | high | steady | 13.44 | 23.65 | 51.26 | 66.5% |
| 10000 | 2 | high | steady | 83.75 | 355.77 | 1296.25 | 148.0% |
| 10000 | 2 | moderate | bursty | 6.54 | 18.37 | 40.92 | 77.3% |
| 10000 | 4 | high | steady | 106.98 | 429.83 | 1423.29 | 129.6% |
| 100000 | 2 | high | bursty | 1082.12 | 2500.33 | 3903.52 | 54.1% |
| 250000 | 4 | high | bursty | 962.90 | 1157.63 | 1614.85 | 23.1% |

## Exploratory uncertainty and interruption sensitivity

`exploratory_contrasts.csv` reports geometric-mean p99 ratios for 62 comparisons:
12 period contrasts (250/10 ms), 20 worker contrasts (4/1), and 30 burst/steady contrasts.
Welch t intervals and tests use log(run p99), with five independent repetitions per side.
Repetition labels are not treated as matched pairs. P values are adjusted together with
Holm's method across all 62 comparisons. The 95% intervals are unadjusted, pointwise
intervals. These comparisons were selected after data collection and are exploratory.
With five trials, distributional assumptions are weakly checkable; retain the raw dots.

For high bursty traffic, 250/10 ms ratios are 0.446 (95% interval 0.425–0.467) with one
worker and 0.553 (0.534–0.572) with two workers. Their Holm-adjusted p values are below
0.00001. With four workers the ratio is 0.912 (0.704–1.180), which does not establish
a reliable advantage for either period.

There are five collection segments: trials 1–93, 94–95, 96–99, 100–177, and 178–300.
The saved USB-C inventory amendment begins at trial 94. A post hoc model of log p99
using a separate mean for every condition, plus segment and starting temperature,
changes standardized condition geometric means by -1.59% to +2.90%. The last-segment
multiplier relative to the first is 0.993 (95% interval 0.919–1.072).
A separate model's order multiplier per 100 trials is 1.013 (p=0.523).
These checks find no clear overall shift, but do not establish equivalence across
reboots or rule out condition-specific confounding. Segments with two and four trials
provide little independent information. Under-load temperatures are shown as outcomes,
not adjusted away as if they necessarily preceded the treatment.

The original automatic regression is an exploratory saturated factor model. Its high
R-squared does not establish causality or generalization; its individual coefficient
p values are not the main evidence used here. Throttled-period fraction is a ratio of
counter increments, not the fraction of requests throttled or wall-clock time stalled.

## Reproduction and files

From the repository root, run:

```bash
venv/bin/python analysis/review_completed.py results/sessions/20260921-202841
```

This script only reads the session inputs and writes `processed/review/`. It does not
alter the experiment runner or its preserved provenance. `raw_sha256.json` records raw
trial file hashes; `audit.json` records checks; `condition_summary.csv` gives all 60 cells;
`trial_review.csv` retains trial order, segment and environmental summaries. PNG and PDF
latency and failure figures show all repetitions. `collection_diagnostics.png` shows
starting and under-load temperature plus residuals in trial order.

## Next research step

Use these completed-session findings to replace the exploratory draft's legacy rates,
tables and universal recommendations. Before submission, complete related work and
independently replicate the variable or extreme conditions (10 ms high steady, 10 ms
moderate bursty with two workers, and 100/250 ms high bursty with multiple workers).
Any new protocol or baseline belongs in a separate session with its own provenance.
