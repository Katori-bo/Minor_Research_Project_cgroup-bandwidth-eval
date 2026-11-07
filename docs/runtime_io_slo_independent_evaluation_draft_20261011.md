# Independent SLO decision evaluation: bounded draft

11 October 2026. Offline planning only. **Not registered, not launchable and not
authorization to collect.** This is separate from pending friend-owned V31 and
the held observer routes. The [contribution review](runtime_io_slo_contribution_review_20261011.md)
leaves originality provisional.

## Question and falsifiable result

Does the observed disconnect between small forecast error and wrong SLO
assurance recur in fresh calibration-transfer episodes with positive forecast
slack? What do ordinary recent-response updates and sampling-based abstention
trade for fewer wrong assurances?

An adverse or null result remains informative. If failures occur only at the
constructed zero-margin deadline, disappear in the new episodes, or yield no
insight beyond existing prediction/decision studies, narrow the contribution.
Do not add endpoints, modify rates or repeat until a failure appears.

The target is the empirical decision for the next complete measured window.
This draft does not test a deployed controller, a causal mechanism, or a certified
future population risk. Separate workload performance from forecast correctness.

## Proposed finite scope and resource ceiling

Proposed ceiling: **four new host/application campaigns**, two independent
physical hosts crossed with the retained Go and NGINX services. Each uses its
own fresh calibration and six counterbalanced blocks of three target rates:
18 target windows per campaign, at most 72 total. One attempted scientific
campaign per cell; failed calibration, domain exits and interruption consume
the cell and remain reported. These are four calibration-transfer histories,
not 72 independent histories or independent population-risk trials.

This ceiling is a bounded design choice, not a power calculation. Preserve the
Go V31 work/quota/service/rates (5/11/19 per second), its 20 s warmups and 60 s
windows for the new Go study. Use the [original NGINX protocol](runtime_io_nginx_prediction_protocol_20261009.md):
stock NGINX 1.30.5, pinned 1 MiB NDJSON, dynamic gzip level 6, single event-loop
worker, 25,000/100,000 us quota and zero configured burst. Four fresh 400-offer
calibration cohorts at 5/s precede six validation blocks ABC/BCA/CAB/ACB/CBA/BAC.
A/B/C spacings are 250,000,000/166,666,667/125,000,000 ns (4/~6/8 per second);
each target has 25 warmup and 300 measurement offers. Transfer affinity by
physical topology rather than copying historical CPU indices. Copy retained
client, qualification, applicability and cleanup contracts into the final design;
never choose between old schedules using new target outcomes.
Power policy stays one declared stable host policy per campaign;
this first stage does not retest a policy-matching advantage or change host
settings automatically.

Use proposed inherited maxima of 3 h 30 min per Go campaign and 45 min per
NGINX campaign, including qualification, calibration, warmups, settling and
cleanup: **8 h 30 min aggregate collection ceiling**. Initial host/package
engineering is additional and must be separately costed. These reuse historical
protocol ceilings, **not measured new-host portability cost or an approved new
budget**. Offline timing accounting must establish feasibility;
otherwise reduce or redesign before registration, not during collection.
No additional profiling, observer counters or tuning is hidden outside the cap.

Two hardware hosts only support a narrow hardware replication claim. Repeated
blocks share state and calibration. A broader operating-boundary claim would
need a separately justified design with more independent episodes.

## Decision contract to freeze

All scheduled offers are in the denominator. Failed or missing completions,
including timeouts, count as misses. End-to-end time starts at scheduled offer
and ends after the full client response. Latency exactly D is timely; a miss
fraction exactly 5% meets the illustrative budget. Store integer counts and
nanosecond deadlines; compare rational fractions without rounding.

Use a **standardized stress test**: retain the illustrative 5% budget and a
calibration-only nearest-rank grid q90/q95/q97.5/q99/q99.5. Do not call these
externally meaningful customer SLOs. An operational deadline supplied by an
external user would require a separately frozen extension; it is not a missing
field to be filled from favorable new outcomes.

The stress-test grid is fully reported.
For this bounded question, q97.5 is the primary positive-slack stress endpoint;
q95 is the declared zero-margin control. This choice comes from development
evidence and must precede fresh outcomes. Each cutoff uses the entire selected
ordinary calibration pool, failures as infinity. Retain unavailable cutoffs,
ties and duplicates; duplicates are labels, not additional evidence. Report
actual slack: q97.5 does not guarantee exactly 2.5 pp on every finite sample.

Historical fixed endpoints (Go 10/11/12 ms and NGINX 20.565395 ms) remain
secondary context. They do not become operational SLOs merely by being old.

## Information and comparison boundary

Use the ordinary full-client-response calibration CDF, the last 25 acquired
warmup offers, and their sample-size-weighted combination. Include the ordinary
two-sided 95% DKW band with radius sqrt(log(40)/(2n)), clipped to [0,1]. Decide
meets if its upper bound <= budget, exceeds if its lower bound > budget,
otherwise inconclusive. Apply the same declared band arithmetic to all three
references, but label pooling/stationarity assumptions. Recent-only updates
have only 25 selected samples; charge full warmup acquisition.

Publish decisions twice where applicable: calibration-only before target
warmup, and warmup-informed immediately before the target window. Freeze cutoff
selection and calibration forecasts before warmup; seal updated forecasts after
warmup and before the first target offer. Inputs must include no target response,
later throttle result or future counter. Retain method failures and abstention.

This evaluates the tested ordinary remedies. Galileo, RScale, MPORA and Sinan
are literature comparators, not executed baselines. No superiority claim is
permitted. A published-method comparison would require a separate compatible
implementation/input/cost design; a quantile cannot silently become a full CDF.
No drift allowance or custom guard is fitted in this evaluation.

## Scores, dependence and statistical ceiling

Report every campaign, rate and chronological block with:

- Wrong assurances / all eligible windows and / all meets decisions; undefined
  when no assurance was made, never zero by convention.
- Unnecessary rejections / observed-compliant windows; undefined when none exist.
- Answer coverage = (meets + exceeds) / eligible windows, and assurance coverage
  = meets / eligible windows; report inconclusive and unavailable separately.
- Signed and absolute probability error, actual forecast slack and observed
  excess over budget. Label every wrong assurance with absolute error <=5 pp.
- Full wall time, acquired calibration/warmup offers, selected offers, qualification
  and cleanup costs. Selected-sample counts do not replace acquisition counts.

Give a complete-case view and an all-planned view of availability; apparatus
failure cannot disappear from coverage. Show paired decisions on the same windows
at common decision times. Coverage curves are descriptive evaluations of a
predeclared rule, not a target-outcome-selected operating point. A method that
assures nothing establishes no useful assurance capability. Do not declare a
winning remedy based on a selected campaign or an unregistered coverage threshold.

Request-level binomial intervals, if shown, are conditional sensitivity checks
only. Resampling requests or deadlines does not generate independent campaigns.
Show finite campaign counts directly; four campaigns and two hosts cannot justify
a stable population-risk bound or a precise method ranking.

For perspective, with zero errors among M independent identically distributed
assurance decisions under a fixed process, a one-sided 95% binomial upper bound
is 1 - 0.05^(1/M). Certifying a rate <=5% in that idealized scenario requires
at least 59 such decisions. Even treating four histories as independent trials
would give about 52.7%; the history-level event is also a different estimand.
This is a planning warning, not a sample-size or power recommendation. The new
study can confirm particular finite-window failures and their tradeoffs; it
cannot certify safety from a small set of favorable windows.

## Finalization and stopping gate

Before preregistration, resolve and record: host identities and availability,
portable NGINX apparatus with complete dependencies and the selected retained
schedule, acquired costs within the ceiling, exact eligible
window/availability denominators, deterministic schedules, evaluator numerical
checks, software hashes and a timestamped registration independent of results.
Qualification outcomes must never choose scientific parameters. A technical
preflight is not scientific calibration or a reason to silently retry a domain exit.

Stop after the declared cells or resource ceiling. Preserve all partial records.
No post-outcome endpoint changes, larger warmups, new predictors, observer work
or favorable retries. Any changed question receives another development label
and requires separate confirmation.

The existing host02 V31 package remains under its original independent contract.
Its returned outcomes can confirm that contract after complete verification.
They are not evidence that this draft was registered. This draft currently has
unresolved feasibility fields, so it must not be advertised as preregistered.
