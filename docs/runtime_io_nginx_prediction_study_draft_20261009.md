# Fresh NGINX response-prediction study: design draft

Date: 2026-10-09. Status: historical planning draft, superseded by
`docs/runtime_io_nginx_prediction_protocol_20261009.md` and the sealed runner
in `analysis/runtime_io_nginx_prediction/generation-01/`. Stock measurement
suitability and new-runner engineering preparation passed separately. No
scientific collection has started; this historical draft does not authorize it.

## Question and scope

Does a fresh empirical distribution of complete stock-NGINX response times
predict deadline misses at previously untested steady request rates on this host?
Keep the signed NGINX 1.30.5 build, pinned 1 MiB input, dynamic gzip level 6,
one event-loop worker, CPU 2, and 25 ms/100 ms quota with zero configured burst.
Any revision requires a separately identified and justified protocol.

Measure scheduled-offer to receipt of the entire encoded body, as in the
qualified client. Include dispatch, server waiting, compression and delivery;
retain decoding/hash checks outside that timed endpoint. NGINX's internal
queue is unobserved. Do not subtract a guessed queue, claim queue-free samples,
or use the V31 paired-stage periodic/residual comparison.

Qualification supports this measurement at 5 req/s. It does not establish its
applicability at every rate, forecast accuracy, or novelty. The 600 pilot
observations are excluded from future calibration and validation.

## Proposed sequence

1. Finalize the prospective protocol and implement a separately named scientific
   runner. Declare rates, sample counts, time caps, order, gates, outcomes and
   analysis before collection. Pin the prior qualification as provenance;
   preserve its scripts, binary, bundles and raw evidence.
2. Qualify the new runner's offer scheduling, body endpoint, identity/resource
   checks, failure accounting, evidence preservation and owned cleanup. Its
   engineering records cannot become scientific observations.
3. Collect fresh calibration cohorts at a declared reference rate. Use only
   these new observations to construct the full-response empirical CDF.
   This model predicts rate-invariant latency inside the declared applicability
   conditions; held-out traffic will test that assumption.
4. Select the primary deadline by a predeclared integer order-statistic rule on
   fresh calibration (candidate: median). Seal the resolved deadline, sample
   manifest, CDF and numerical forecasts before validation begins. Do not choose
   a deadline from the qualification's approximately 20.5 ms median.
5. Candidate validation structure: three distinct rates different from the
   reference rate, six balanced blocks ordered ABC, BCA, CAB, ACB, CBA, BAC.
   This gives 18 fresh trial cohorts. Numeric rates and sample counts remain
   undecided; this structure alone is not a precision or power justification.
6. Replay all sealed evidence. Report all attempted cohorts, applicability exits
   and prediction outcomes. Preserve an unfavorable or invalid campaign without
   replacing its trials or tuning a second campaign to obtain a favorable result.

## Outcomes and decisions to finalize before collection

Define a deadline miss using the full timed endpoint, with exact integer
boundary semantics. Count failed, dropped and timed-out offers as misses in
the all-offer validation outcome; specify separately how calibration failures
make the forecast unavailable. Missing offered requests must never silently
disappear from the denominator.

Candidate primary summary: equally weight rate profiles within each block,
then summarize block-level absolute error between the sealed miss prediction
and observed all-offer miss fraction. Also report signed errors and each rate's
result. Requests are repeated observations within cohorts, not independent
experimental replications. Specify calibration uncertainty and block-level
validation uncertainty; do not adopt the historical 3-percentage-point gate
without a sample-size and precision justification.

Retain zero recorded measurement throttling as a candidate applicability gate,
along with qualified dispatch, request conservation, body correctness and
stable runtime/resource identity. Finalize how each gate applies to calibration
and validation and whether any failure stops further collection. All exits
must remain visible. The original 100 us/99% FIFO queue gate is unavailable
and cannot be replaced by the client overlap statistic.

Choose validation rates prospectively using an explicit operational rationale;
do not try several and retain only favorable ones. A busy-window capacity
experiment is unnecessary for a direct empirical-CDF forecast unless the final
design explicitly uses capacity; adding it would need a separate measurement
contract. Keep any secondary deadlines or comparators explicitly prespecified.

## Interpretation

Accurate held-out predictions would extend evidence for this specific empirical
forecast to a second, independently developed HTTP application on this host.
Inaccurate predictions inside the declared applicability conditions would limit
that transfer claim. Measurement or applicability exits would leave the planned
scientific question unresolved while documenting the limit.

This is a new application-transfer study, not an exact replication of V31's
queue-adjusted model comparison. An ordinary empirical CDF is not a new
algorithm. A positive result could strengthen an empirical manuscript extension;
novelty still needs a supported comparison with prior work. Independent hardware
and independent research-team reproduction remain untested.
