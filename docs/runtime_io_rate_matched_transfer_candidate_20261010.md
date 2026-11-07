# Next candidate: rate-matched response calibration across fresh instances

**Completed outcome, 10 October 2026:** Full qualification and campaign replay
verify. Rate-matched accuracy passes, but its incremental advantage over 5/s
calibration does not: matched MAE 1.194 pp versus 1.972 pp, improvement 0.778 pp
with conditional interval [-0.375, 1.931] pp. Ordinary 5/s also passes the accuracy
target. Both throttled cohorts remain included. Close this bounded collection
branch; this does not establish rate mismatch as the earlier failure's cause
or a novel method. See the [sealed assessment](../analysis/runtime_io_nginx_rate_transfer_review/20261010-generation01/report.md).
All preparation and candidate text below is historical.

**Subsequent execution decision, 10 October 2026:** The user authorized this
study. The separate [frozen protocol](runtime_io_nginx_rate_transfer_protocol_20261010.md)
and `diagnostic/start_nginx_rate_transfer.sh` are prepared and sealed; 21 checks
pass. Hardware qualification and collection are pending. The candidate
assessment below is the historical pre-authorization decision, not the current
execution contract.

10 October 2026. Question and preliminary feasibility assessment after known
power-confirmation outcomes. This is not a frozen collection protocol, new
method, implemented collector or authorization to launch a campaign.

## Decision and exact question

Assess one remaining ordinary alternative before new reliability-method work:

> Under fixed P0, can a full response-CDF reference acquired at the known target
> rate predict a later fresh instance at that same rate accurately enough,
> compared with the ordinary 5/s calibration reference?

The immediate scope is the stock-NGINX workload at the unchanged 20.565395 ms
deadline and 25 ms / 100 ms CPU quota. Keep P0 fixed; no additional policy
intervention, boost/governor/idle-state sweep or quota-period change. If later
collection is justified, use a separately named generation and qualify its
wrapper against the retained binaries and lifecycle checks.

## What existing evidence does and does not resolve

In the confirmation, P0 calibration at 5/s predicted 79.5% misses. Validation
P0 averages were 50.167% at 4/s and 47.611% at 8/s. Their difference is only
2.556 pp; the conditional six-block interval is [-23.837, 28.948] pp. There is
no established monotonic rate effect, and neither validation rate was 5/s.
The apparent calibration-to-validation difference cannot identify a rate effect
separately from time, service instances, physical state or response-shape changes.

Two 5/s calibration cohorts agreed to within 3 pp but transferred poorly;
calibration agreement alone is not sufficient. Full 25-offer target-rate warmup
gave lower aggregate error than policy matching in confirmation, but still
missed the accuracy-upper-bound reference. Its earlier saved Go/NGINX results
were not consistently better. Longer target-rate calibration remains untested;
this neither predicts that it will work nor demonstrates a new capability.

The existing records contain no independent full target-rate calibration pool
that can be used to confirm this question. Dividing the known validation cases
into training and test would be retrospective development and would consume
the confirmation's already observed labels. Use those records only to describe
the gap and budget, not to declare prospective success.

## Prior-work and novelty check

Primary sources were rechecked on 10 October 2026:

- Li et al., [Tales of the Tail, SoCC 2014](https://syslab.cs.washington.edu/papers/latency-socc14.pdf),
  Sections 3.2 and 4.6: workload arrivals and hardware/OS policies affect
  response distributions; low-utilization power effects include NGINX.
- [ReTail, HPCA 2022](https://people.csail.mit.edu/delimitrou/papers/2022.hpca.retail.pdf):
  feature/frequency-conditioned latency prediction and online retraining
  constrain broad state-aware-prediction novelty. It is not the same endpoint
  or implemented baseline as our empirical miss-probability CDF.
- The [extension prior-work review](runtime_io_deadline_boundary_prior_work_review_20261010.md)
  also records load-conditioned latency profiling and its scope differences.

Rate-matched empirical calibration is an ordinary control in this proposed
study. These references do not prove that the exact scoped question is already
answered, or that existing full methods fail. A success would improve an
empirical calibration condition; a failure would sharpen its boundary. Neither
would establish a novel algorithm or first-ever result by itself.

## Minimal prospective comparison to assess

If this empirical control is worth its acquisition cost, the candidate design
is six fresh calibration cohorts, two each at 4, 5 and 8 requests/s, 400 measured
offers per cohort under fixed P0. Randomize the balanced order and freeze a
fresh seed before collection. This gives 800 offers per rate: target-rate and
5/s references have equal sample counts and share one declared acquisition
procedure. Disclose all acquired calibration offers, including those unused
by a particular forecast, rather than claiming standalone cost equality.

Then collect six fresh validation blocks containing 4/s and 8/s once each in
random order, 300 measurement offers per cohort. Global references freeze
before validation; the 25-offer target-rate warmup comparator freezes before
each measurement. Retain all failures and throttling as outcomes, with integrity,
resource identity, accounting, watchdog and restoration failures as technical
stops. No retries or replacement scientific cohorts.

This outline uses 2,400 calibration and 3,600 validation measurement offers,
450 warmup offers, or 6,450 total scientific offers, plus separate bounded
qualification. Nominal offer schedules consume about 20 minutes including
warmup; settling, startup, verification, drain and cleanup are additional.
A proposed 45-minute campaign ceiling must be checked in implementation; it
is not a measured completion estimate or power calculation. Keep the inherited
bounded service watchdog, and ensure the longest 4/s calibration fits it.

Before implementation, declare the primary comparison and criteria in the
new contract. The candidate retains the existing 5 pp accuracy upper-bound
reference and uses >=2 pp mean improvement with a positive paired interval
lower bound against 5/s calibration as an improvement reference. Report the
six block means, per-rate errors, maximum error, count >5 pp, calibration-cohort
sensitivity and acquisition cost. Do not replace the primary method afterward
with whichever comparator wins. Numerical criteria are design references,
not evidence that six blocks can certify a broad reliability claim.

## Information boundary and outcomes

Available before prediction: the declared target offered rate, P0 readback,
fresh calibration outcomes, software/resource identity, and warmup only for
the separately timed warmup methods. Future response times, CPU usage,
throttle counters or validation drift cannot select the reference or issue an
advance assurance.

- Accurate matched-rate transfer would support an ordinary empirical fix in
  this configuration and close custom-method development for that problem.
- Failure would show that assigned policy and rate matching alone were
  insufficient in the fresh evaluated episodes. It would not identify the
  cause or defeat all richer state-aware models.
- A technical stop or an uninformative endpoint remains a preserved partial
  or nondiscriminating outcome; no automatic sweep follows.

## Current proceed/stop verdict

**The question is unanswered and empirically testable, but is not a demonstrated
new-method opportunity.** Its purpose is to resolve an ordinary calibration
alternative left open by the completed design. Planning can proceed without
waiting for the friend's independent Go V31 result. A new campaign should only
follow a deliberate choice to pursue this empirical question and completion
of its frozen, bounded, qualified package. No campaign has been prepared or
scheduled here. If the immediate priority is a novel method, keep collection
stopped and identify a distinct information-to-decision capability with an
adequate published-method comparison before spending this measurement budget.
