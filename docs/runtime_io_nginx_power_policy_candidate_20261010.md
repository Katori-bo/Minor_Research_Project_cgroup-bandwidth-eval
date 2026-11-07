# Candidate experiment: power-policy matching and response-CDF transfer

10 October 2026. Design proposal after historical outcomes are known, before
any new intervention or collection. Read with the
[research decision](runtime_io_nginx_mechanism_decision_20261010.md).
This is not an executable or fully qualified prospective protocol. A separately
sealed implementation, qualification record and generation are prerequisites.

## Question, hypothesis and estimand

At identical application, input, quota, client and affinity, does assigned server
energy/performance preference change deadline-miss fractions, their dependence
on offered rate, or the accuracy of a calibration forecast?

H1 (candidate): the assigned server policy changes the complete-response
distribution enough that conditioning calibration on the known policy improves
future-cohort prediction at the fixed deadline. An idle-related rate interaction
is a subsidiary hypothesis: the 8/s minus 4/s response/miss contrast is attenuated
under the performance preference. No direction is guaranteed under active EPP.

H0 includes no practically useful policy or matching benefit. Nonstationarity
within a policy, client/body-read variability or shared-resource interference
can leave the state-conditioned prediction inaccurate. A result must report
these alternatives rather than selecting only the favorable contrast.

Primary forecasting estimand: equally weighted cohort absolute error in
all-offer miss fraction, averaged over the four policy/rate cells within each
block. Primary comparison: ordinary policy-conditioned CDF versus ordinary
pooled CDF with the same total calibration acquisition budget.

Primary causal estimand: performance-minus-baseline miss fraction averaged over
both offered rates within a randomized block. Secondary: difference between the
two policies' 8/s-minus-4/s miss contrasts. A policy effect is a causal effect
of the assigned policy bundle; it is not proof of a pure frequency mechanism.

## Fixed treatment and resources

- Baseline P0: CPU 2's `powersave` governor, EPP `balance_performance`.
- Alternative P1: same governor, EPP `performance`; keep min/max settings.
- Do not change governor, boost, idle-state availability, quota or quota period.
- Stock original NGINX binary, gzip level 6, fixed 1 MiB input, one worker,
  CPU 2 affinity, quota 25,000 us per 100,000 us and original resource limits.
- Original client binary and timed endpoint: `BodyDoneNs - ScheduledNs`, before
  the subsequent verification decode/hash. Keep its original placement on the
  controller/client CPU set, and keep integrity verification enabled.
- Client source inspection shows decode/hash is after the response endpoint;
  its allocations could still affect subsequent requests. Do not label the
  endpoint as unaffected by client runtime activity.
- CPU 3 is CPU 2's SMT sibling. Record its activity/context and retain the
  limitation. Do not equate task placement with a CPU reservation or silently
  introduce isolation/offlining as another treatment.

The old configuration is a challenge setting, not a fresh optimum. Do not tune
work size, deadline or resource policy to create separation. Normal host activity
must be declared; no other owned performance campaign may run concurrently.

## Qualification before scientific collection

1. Implement a separate reversible policy-control fixture. Capture original
   governor, EPP, min/max and related-policy scope; require the expected P0
   baseline. Refuse a foreign baseline. Write only the declared CPU 2 EPP.
   Read back P0/P1 before and after each phase. Use an owned restoration journal
   and watchdog that survive client/server failure and runner termination;
   verify restoration even when qualification or collection fails.
2. Validate it on the actual topology. Record CPU 2/3 sibling relationship and
   policy scope. Check that governor/min/max and other policies did not receive
   unintended writes. A verified readback proves the preference setting,
   not fixed frequency. Restore after the fixture. At most two P0/P1 cycles;
   failure stops this route.
3. Qualify the exact application/client under the new wrapper, preserving their
   sealed hashes. Four smoke cohorts, one per policy/rate cell, each 25 warmup
   and 20 measured offers (180 offers total), with a ten-minute elapsed ceiling.
   Smoke outcomes are engineering checks, not calibration or efficacy evidence.
   Do not choose a policy, rate, deadline or forecast using their outcomes.
4. Verify request/output integrity, ownership, cleanup, limits, PID/thread
   identities, dispatch bounds and policy restoration. A failing smoke cohort
   ends qualification with all records retained. No retry or replacement.

Reuse existing client/cgroup observation only. No periodic sysfs polling, perf,
BPF, scheduler tracing or rebuilt timed client in the primary collection.
Additional instrumentation would need separately declared observer qualification
and would change this candidate design.

## Calibration, schedule and budget

Four fresh calibration cohorts: two per policy at 5/s, each 400 measurement
offers after 25 warmup offers. Randomize among the six orders containing two P0
and two P1 assignments using a seed sealed before smoke collection. No reuse of
old measured responses as fresh calibration.

Validation: six complete blocks, each containing the four cells P0-4/s,
P0-8/s, P1-4/s and P1-8/s exactly once. Each cohort has 25 warmup and 300
measurement offers. Within each block use a uniform random permutation,
generated from the sealed seed before smoke/calibration. Keep all six blocks;
do not terminate early for a favorable outcome. Fresh service/client instances
and the original settling/drain/identity procedure are used in every cohort.
Settings are applied before settling and held through warmup/measurement.

Freeze the schedule, runtime/source identities and the fresh forecasts before
validation. Baseline/policy readbacks are available at the forecasting decision;
future timing, CPU deltas and integrity outcomes are unavailable.

| Budget | Ceiling |
|---|---:|
| Scientific calibration cohorts | 4 |
| Scientific validation cohorts | 24 |
| Measurement offers | 8,800 = 4 x 400 + 24 x 300 |
| Warmup offers | 700 = 28 x 25 |
| Scientific-run total offers | 9,500 |
| Nominal offer-span budget, including warmup | Less than 1,803 s |
| Scientific campaign elapsed | 45 min including cleanup reserve |
| Qualification smoke | 4 cohorts, 180 offers, 10 min maximum |
| Scientific retries/replacements | 0 |

Nominal spans sum count/rate, slightly conservatively; settling, startup, guard
checks and restoration add overhead. The elapsed ceiling takes precedence over
finishing a schedule. These are cost ceilings, not a statistical power result.

## Endpoint and ordinary comparators

Fixed primary deadline: **20,565,395 ns**, the original NGINX challenge deadline.
Unsuccessful offers count as misses; successful offers miss if the full response
is strictly greater than the deadline. This new declaration does not reclassify
the old deadline as selected prospectively for this new hypothesis.

At the same deadline, freeze from the fresh calibration:

1. Pooled complete-response CDF: all four calibration cohorts, 1,600 responses.
2. Policy-conditioned complete-response CDF: 800 responses for each known policy.
3. Baseline-only CDF: both P0 calibration cohorts, 800 responses, used for every
   validation cell to quantify cross-policy transfer.
4. Recent target-rate CDF: that cohort's full 25-offer warmup. Decision is after
   warmup, before measurement; it has a later decision time than 1-3.
5. Sample-weighted update of the policy-conditioned CDF with the 25 warmup
   responses, and the analogous pooled update. No fitted weights or thresholds.

All methods use ordinary empirical distributions. Pooled and conditioned models
have the same total acquisition budget; per-cell effective sample sizes differ
and must be reported. Show same-policy and cross-policy predictions separately.
Do not present a policy label/CDF lookup as a new estimator. Online methods
that consume validation response labels require a different sequential contract;
none is reproduced or refuted by this cohort-level comparison.

Secondary fixed deadlines are 10, 25 and 50 ms. Report them as a declared
sensitivity panel with no independent pass criterion or post-hoc replacement of
the primary endpoint. Report dispatch-to-headers, headers-to-body, full-response
mean/median/p99, failures, cgroup CPU/offer and recorded throttling. Client-stage
means add; component medians do not generally add.

## Inclusion, domain and inference

Retain every assigned cohort and every offer. Infrastructure failure, wrong
output/identity or foreign policy readback stops collection and prevents a
trusted causal/forecast conclusion; preserve completed and partial records.
No recorded measurement throttling, no observed client response overlap and
the original dispatch gate define the intended low-overlap domain. If these
conditions fail, report the domain exit and all-offer result; do not delete the
cohort or claim a clean within-domain comparison.

Use blocks, not individual requests, as the replication units. Describe block
contrasts, their spread and temporal order. A conditional t interval with six
blocks uses df=5 and two-sided 95% multiplier 2.571; its interpretation requires
adequate independence/stability of block contrasts. Randomized assignment does
not make requests or consecutive blocks iid. Include an assignment-based
randomization test of the sharp no-policy-effect null if the final collector
preserves the declared randomization and no interference/carryover assumptions
are credible. Qualification must assess restoration/settling; otherwise causal
inference remains limited. Do not substitute an iid request bootstrap.

Planning criteria, fixed here before any new outcomes:

- Useful forecast improvement: policy-conditioned MAE improves pooled MAE by
  at least 2 pp on average, with conditional 95% block interval excluding zero
  improvement. Report uncertainty in the 2 pp effect separately; this rule
  does not establish a 2 pp lower confidence bound.
- Useful absolute accuracy: policy-conditioned mean error has conditional
  95% upper bound <=5 pp, with per-cohort maximum and all errors >5 pp shown.
  This is an aggregate feasibility criterion, not an assurance for each cohort.
- A policy effect without these forecast criteria is explanatory evidence only.
  An improvement without credible policy scope/assignment is not causal evidence.
- The rate-interaction hypothesis remains secondary; show its interval without
  turning it into another route to a primary success declaration.

If assumptions fail or intervals are too broad, mark the pilot inconclusive.
Six blocks are a capped exploratory mechanism/transfer pilot, not a powered
confirmatory evaluation or a selective-risk certificate. No cutoff, weight,
calibration length or policy may be tuned on these outcomes for confirmation.

## Branches after the result

If ordinary policy-matched calibration succeeds, add a scoped calibration-control
finding to the empirical paper. It removes motivation for a custom guard for
this controlled condition. Independent-host or independently sampled state
episodes would still be needed to extend its scope; the friend's original V31
replication does not validate this new NGINX hypothesis.

If a policy contrast exists but forecasts still fail, retain the practical
failure and require a new concrete pre-outcome variable before designing a
diagnostic. Post-measurement counters cannot become an advance predictor.

If there is no useful contrast or qualification fails, stop this branch and
finish the empirical comparison. Do not automatically add tracing, policy
combinations or further applications. A tracing study would be a new decision
with its own measurement and literature justification.
