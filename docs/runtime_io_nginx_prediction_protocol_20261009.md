# Prospective stock-NGINX complete-response prediction protocol

Date: 2026-10-09. Generation 01. Freeze this document and the executable bundle
after engineering preparation and before the external campaign. No historical
qualification observation enters a scientific fit or validation outcome.

## Scientific question

Can a fresh reference-rate empirical CDF predict full-response deadline misses
at rates held out from calibration, for this stock application on this host?
The predictor is deliberately rate invariant. Waiting is part of the measured
response time. There is no observed server queue, queue subtraction, FIFO-domain
claim, periodic/residual comparator, new-algorithm claim or hardware replication.

Reuse unchanged NGINX 1.30.5, the signed source and native binary, pinned 1 MiB
NDJSON input, dynamic gzip level 6, immutable runtime image and full-body Go
client from the verified generation-02 qualification. Preserve every old bundle
and failed candidate. Master and single event-loop worker remain single-threaded
on logical CPU 2; service quota is 25,000 us/100,000 us, burst zero. Supervisor
and client use CPUs 0,1. Keep all frozen startup, runtime-file identity, procfs,
ownership, watchdog, desktop exclusion and cleanup checks.

## Collection, in fixed order

Each cohort uses a fresh owned stock service, 25 warmup offers, then the stated
measurement offers. Wait 10 seconds before each external service. No retries,
resumption, replacement, optional stopping on accuracy, or post-result rate
tuning. Stop at the first technical or applicability exit and preserve all raw
records, including unsuccessful offers and any partially completed cohort.

1. Engineering preparation with the desktop open: 20 measurement offers at each
   validation schedule, ordered A/B/C. Check all scheduling/body/accounting paths
   and sealed replay, then seal the separate scientific bundle. These 60 offers
   are excluded from science and do not qualify performance.
2. External runner performance qualification: three fresh 100-offer cohorts at
   A/B/C, once each. All outcomes must succeed and all applicability gates pass.
   These 300 observations never enter calibration. Failure stops the campaign.
3. Fresh scientific calibration: four 400-offer cohorts at 5 requests/s, exactly
   200,000,000 ns spacing. Require all 1,600 outcomes successful and eligible.
4. Freeze calibration evidence, the sorted full-response samples, deadlines and
   forecasts in a separate sealed directory. Validate the calibration-only fit
   and seal hashes before any validation service starts. Record the forecast-seal
   digest and monotonic barrier in every validation cohort.
5. Held-out validation: 300 offers per cohort, six blocks with orders ABC, BCA,
   CAB, ACB, CBA, BAC. Exactly 18 cohorts and 5,400 offers. A spacing is
   250,000,000 ns (4 requests/s); B is 166,666,667 ns (approximately 6 requests/s,
   with its exact rational rate retained); C is 125,000,000 ns (8 requests/s).
6. Replay all raw evidence, prerequisites, frozen forecasts and final analysis.

Rates straddle the qualified 5 requests/s reference and increase offered traffic
up to 60%. They test a deliberately modest operational range without needing
an unqualified busy-window capacity estimate. The original pilot informed the
choice of application/reference setting, but no pilot CDF, deadline or forecast
is reused. The rate choices are frozen before any new-rate engineering timing;
they must not be changed because a new-rate check or forecast is unfavorable.

Use the same bounded client: at most 1,000 offers per invocation, 32 in flight,
10-second HTTP timeout and bounded compressed/decoded bodies. Completion is the
full encoded-body receipt timestamp, before decoding/hash validation. Every
expected request ID and scheduled offset must exist exactly once. A missing,
duplicate or foreign row is a technical failure, not a smaller denominator.

Each service retains the inherited independent 120-second active watchdog and
owned PID/start-time and container-nonce cleanup. The entire external campaign,
including root observer inventory, settling and cleanup, has a 2,700-second
limit (45 minutes), reserving 120 seconds for final cleanup. Admit no new service
unless 130 seconds plus the cleanup reserve remain. Ordinary elapsed time is
about 30 minutes; no result is guaranteed by that estimate. A stopped campaign
cannot be rerun or overwritten under this generation.

## Applicability and outcome accounting

Both nr_throttled and throttled_usec measurement increments must be zero.
Dispatch p99 must be <=2 ms and maximum <=10 ms. Require stable process/thread,
affinity, cgroup, image, packaged runtime, source and input identities, root
observer eligibility, drained stock status and verified owned cleanup. Warmup
must succeed; its timing observations are excluded from the measurement CDF.

CPU windows enclose measured requests and common post-drain status checks;
startup and warmup counters remain separate. No HTTP observer polls during
the workload. Request-count deltas subtract the known post-drain control
queries. With all responses received the workload count must match exactly.
With ordinary transport failures, retain the observed count and bounds from
responses with headers through all dispatched offers; never claim exact
conservation when only bounds are observable.

Wrong identity/content or corrupt decoding invalidates trusted measurement.
Ordinary HTTP/transport failures and timeouts in validation remain all-offer
misses; a client in-flight drop is also a miss but exits the load-generator
applicability gate. A complete but unsuccessful calibration or qualification
offer makes the relevant prerequisite unavailable. Preserve raw unsuccessful
outcomes and their all-offer miss classifications even when a cohort exits.

The measurement endpoint is BodyDoneNs minus ScheduledNs. A successful response
misses exactly when this integer duration is greater than the deadline; equality
is a success. Every unsuccessful offer is a miss, at every reported deadline.
No queue filter, sample trimming or outlier removal is allowed.

## Frozen forecast and analysis

Pool the four equal-size fresh calibration cohorts; sort the 1,600 durations.
The primary deadline is sample index (1600-1)//2, using zero-based indexing:
the lower median, retained as an exact integer nanosecond value. Forecast the
fraction strictly greater than that deadline. Ties therefore need not yield
exactly 50% misses. Use this same frozen probability at every validation rate.
Secondary deadlines are fixed 10, 25 and 50 ms, reported without separate
confirmatory gates. Also retain the entire sorted calibration sample/CDF.

For each held-out cohort, calculate the all-offer miss fraction and signed and
absolute errors in percentage points. Equally average the three absolute errors
within each block. The primary accuracy criterion is that the upper endpoint
of the two-sided, model-based 95% t interval for the six block mean absolute
errors is <=5 percentage points. Use multiplier 2.571 with five degrees of
freedom: mean +/- 2.571 * sample_standard_deviation / sqrt(6). Do not clip its
lower endpoint. Report individual cohorts and per-rate mean errors alongside
the primary summary so averaging cannot hide rate dependence.

Five percentage points is a declared practical tolerance of five misses per
100 offers, not a discovered optimum, a 5% admission threshold, or the historical
3-point V31 gate. Under independent Bernoulli sampling a 300-offer median-region
cohort would have approximately 2.89-point standard error; pooling six cohorts
at one rate would give approximately 1.18 points, and 1,600 calibration samples
approximately 1.25 points. These are sample-size scale checks only. Requests
may be dependent and the chosen deadline is estimated; these approximations
are not power guarantees or the study's inferential units. The study has six
validation blocks and four calibration cohorts, not 7,000 independent trials.

The t interval assumes approximately independent, normally distributed block
means and conditions on the finite sealed forecast. It does not propagate
calibration uncertainty or guarantee population-level accuracy. Report each
calibration cohort's miss fraction at the pooled deadline and re-evaluate the
validation MAE using each of those four alternative probabilities as descriptive
sensitivity. Do not call this range a confidence interval or alter the primary
deadline/prediction from it. A stronger unconditional statistical claim would
need a separately justified design with more independent calibration cohorts.

## Decisions and claims

A complete eligible campaign satisfying the conditional accuracy criterion is
reported as full_response_prediction_accuracy_supported. A complete eligible
campaign failing it is full_response_prediction_accuracy_not_supported; failing
this precision criterion alone does not prove the unknown population error
exceeds five points. Technical/applicability exits stop collection and report
campaign_stopped with the phase, retained outcomes and reason. Neither incomplete
collection nor post-result tuning can support the prospective accuracy claim.

A positive outcome supports this particular empirical forecast across the three
tested rates for a second independently developed application on the same host.
It could strengthen an empirical manuscript extension. It does not establish
V31's paired-stage comparator advantage, universal rate invariance, novelty,
independent physical-host replication or independent-team reproduction.
