# Independent SLO decision evaluation: frozen scientific contract v1

11 October 2026. Local pre-outcome design registration. The companion JSON,
schedule vectors, evaluation code and source hashes are sealed together. The
previous draft remains unchanged as provenance. This is not a public or
third-party timestamped preregistration, a runnable collector, or a collection
authorization. No future calibration or validation outcomes have been acquired.

## Feasibility verdict

**GO for the bounded scientific design and offline evaluator; NO-GO for launching
collection with the current apparatus.** The retained schedules fit the inherited
caps under normal timing. The new decision barrier has numerical and lifecycle
tests. Neither an integrated, portable SLO collector nor its runtime qualification
exists yet. The pending Intel V31 package remains unchanged and cannot be used
as the launcher for this different study.

Host slots are the known local AMD Ryzen 5 5600H laptop and the friend's Intel
Core i5-10300H laptop. These are planning allocations, not confirmed availability
or fresh readiness checks. Use one new Go and one new NGINX campaign per host:
four attempted campaigns, each with 18 planned target windows, 72 total.
Within the local host use Go then NGINX; within the Intel host use NGINX then Go.
Do not run two campaigns concurrently on one host. Both use the same recorded
stable host power policy for their respective host, selected before either run.
The host preference is pending; a requested change requires v2 before collection,
with v1 preserved. No new collection proceeds by treating silence as approval.

Caps: 12,600 s for each Go campaign and 2,700 s for each NGINX campaign, including
their runtime preparation, qualification, calibration, warmups, settling,
analysis and cleanup. Aggregate acquired campaign time is capped at 30,600 s
(8 h 30 min), even if hosts run concurrently. Offline package engineering is
additional, must be logged, and is not silently treated as zero cost. There is
no automatic extension for unstable hosts or failed qualification.

## Scientific question and scope

Does a small error still yield a wrong complete-window SLO assurance in fresh
calibration-transfer episodes when forecast slack is positive? How do the
three declared ordinary procedures trade wrong assurances for rejections,
inconclusive decisions, availability and acquisition cost?

The primary event is at the calibration q97.5 deadline: the ordinary reference
predicts <=5% misses, actual slack is >0, the observed complete-window miss
fraction exceeds 5%, and absolute forecast error is <=5 percentage points.
Report its count and every window, regardless of whether the event occurs.
One such window on the independent Intel host is a finite-window hardware
replication of this particular failure pattern. A local-only event is a fresh
same-host recurrence. Events on both hosts or both services broaden the recorded
scope; they are not population-rate estimates or a universal operating boundary.
If none occur, say the primary pattern was not reproduced in these attempts.
If qualification prevents observation, say it was unavailable, not disproved.

The q95 zero-margin control cannot satisfy the positive-slack event unless its
actual finite-sample slack is positive. No zero-margin event is substituted for
the primary result. No minimum event count is used to claim statistical
significance. Population noncompliance, a causal quota mechanism and certified
future safety are outside this contract.

## Frozen offers, services and calibration

Go retains the V31 SHA-256 service, 88,000 rounds, one worker, GOMAXPROCS=1,
128 waiting slots, no yielding, quota 25,000 us / period 100,000 us, zero
configured burst, and the exact 16 calibration-slot schedule. Its ordinary
reference uses **all client offers** from the four prescribed 30 s timing
cohorts at 3.75 and 7.5/s. Do not select by successful response or queue wait.
All 16 calibration slots, their warmups and prerequisites are acquired and
charged. Original capacity/timing qualification remains a prerequisite; it
cannot remove inconvenient offers from the complete-response reference.

Go targets retain six blocks ABC/BCA/CAB/ACB/CBA/BAC, rates 5/11/19 per second,
20 s warmup then 60 s measurement, and the retained integer schedule-rounding
rule. There are 300/660/1,140 target offers per profile, 12,600 per campaign.
Export all retained compiled client vectors without network/workload and
reconcile with an independent rational oracle before freeze.

NGINX retains the original [complete-response protocol](runtime_io_nginx_prediction_protocol_20261009.md):
stock 1.30.5, signed pinned source and runtime, pinned 1 MiB NDJSON input,
dynamic gzip level 6, single event-loop worker, and the same 25,000/100,000 us
bandwidth with zero configured burst. The three 100-offer A/B/C external
qualification cohorts are excluded from calibration. Four 400-offer calibration
cohorts at exactly 200,000,000 ns spacing provide all 1,600 reference outcomes.
Each service has 25 warmup offers. Targets retain the same six block orders,
300 offers each and A/B/C intervals 250,000,000 / 166,666,667 / 125,000,000 ns.
The exact B interval, not a rounded 6/s label, determines every offset.

Host-relative affinity is fixed by topology: on local AMD, Go service CPUs 2,4;
on Intel, Go service CPUs 2,3; client/control 0,1 on each. NGINX uses service CPU
2 and control CPUs 0,1. Validate actual distinct physical cores, SMT siblings
and allowed affinity before release. Affinity is not exclusive isolation.
Fresh boot, cgroup-ancestor, power and thermal baselines replace historical
host state. No historical response times supply a new calibration.

## Endpoints and permitted information

This is a standardized stress test, not a claim about a customer's chosen SLO.
Use the illustrative 5% miss budget and the full calibration-only nearest-rank
grid q90/q95/q97.5/q99/q99.5. The rank is ceil(q*n)-1 with failures ordered at
infinity. Record unavailable deadlines and tied/duplicate labelled cutoffs.
Retain fixed secondary Go 10/11/12 ms and NGINX 20.565395 ms deadlines. Never
select an endpoint after a target result or count duplicate labels as new trials.

Every scheduled offer is in the denominator. Ordinary failed/missing completions
are misses. Successful complete-client response duration >D is a miss; equality
is timely. A miss fraction exactly 5% meets the empirical budget. Preserve
integer ns and rational fractions. Wrong content, identity, framing or corrupted
accounting invalidates measurement; do not relabel corruption as ordinary
transport failure or silently reduce the denominator.

Compare the ordinary reference CDF, the last 25 acquired warmup offers, and their
sample-size-weighted concatenation. The latter two decide later. Charge the
entire acquired warmup, including Go's full 20 s. At the later common decision
time, compare the unchanged reference to both updates on the same windows.
Store point decisions and the ordinary two-sided 95% DKW band for every method:
radius sqrt(log(40)/(2n)), clipped to [0,1]; meets if upper<=.05, exceeds if
lower>.05, otherwise inconclusive. Pooling requires a common population;
independence and future stationarity are unverified. These are sampling-only
illustrations, not drift protection. No custom predictor or drift allowance is
introduced, and no unexecuted published method is ranked.

## Pre-target barrier and collector qualification

Seal calibration cutoffs and forecasts before any target warmup. For each
window, finish warmup readback, validate the whole offered schedule and drain,
then record the supervisor's `warmup_available_ns`. Before creating the target
client process, durably write the three methods' predictions and a target-start
permit; record their byte hashes, plan identity and boot identity. The supervisor
records the monotonic timestamp immediately **before** target process creation.
The first request can only occur after that parent event. Reconcile those events
with sealed collector sources and raw scheduled offsets during return replay.

The engineering allowance is at most one second from warmup availability to
target child creation. This is **not** one second from the last HTTP body
completion: the retained NGINX client exposes relative timestamps, not the
absolute supervisor origin. Report warmup readback/drain and process boundaries
separately. Do not invent a physical warmup-to-target gap from these clocks.
The allowance is a frozen pipeline bound, not measured equivalence or guaranteed
absence of workload perturbation. All methods receive the same resulting state.

Stop before target creation if decision calculation, durable write or permit
checks fail. A late child creation invalidates applicability and consumes the
attempt; retain any emitted outcomes. Hash changes, boot changes, target-before-
forecast ordering or reused attempts invalidate prospective provenance.

The evaluator implements this barrier, but it is **not yet integrated into either
collector**. Before collection, isolated adapters must demonstrate with synthetic
inputs: exact call ordering, ordinary all-offer extraction, no target-file access
in forecast code, raw/receipt replay, host-relative affinity, watchdog cleanup,
budget enforcement and refusal to resume or overwrite an attempt. Adapter source
identity must be registered in a preserved apparatus supplement before any new
qualification/calibration outcome. Qualification data never choose scientific
parameters, cutoffs or comparison rules. If implementation needs to change this
scientific contract, register v2 before any outcomes rather than rewriting v1.

## Availability, stopped attempts and report

Maintain 18 planned window slots per attempted campaign even if calibration or
qualification fails. A trusted complete window has every scheduled offer
accounted for, a valid forecast barrier and response/accounting integrity.
Partial or corrupt windows are unavailable for full-window decisions; preserve
their raw counts and reasons. Do not extrapolate their missing future requests
into a complete-window label. A trusted complete applicability-exit window is
shown in a separate retained adverse table; it is outside the inherited primary
domain and is never retried or deleted. Report complete-trusted and primary-domain
views separately, both against the unchanged 72 planned slots.

For each campaign, block, rate, deadline and method report raw meets/exceeds/
inconclusive/unavailable counts; wrong assurances per meets and per trusted
complete window; unnecessary rejections per observed-compliant window;
answer coverage, assurance coverage and unavailable fractions. Show coverage
using both completed and all-planned denominators. Undefined denominators are
null, not zero. Unobserved windows are not assumed safe. Include signed error,
actual slack, budget excess and the <=5 pp event label. No pooled request-level
or cross-deadline confidence interval is used to rank methods.

The primary result is the observed finite-window event and its availability.
Compare remedies through the full joint table; no winning method or acceptable
safety/coverage operating point is selected from new outcomes. Conditional
request-level binomial sensitivity intervals, if subsequently added, require a
separate labelled analysis and cannot change this primary result. Four histories
and two hosts do not certify a false-assurance rate. Even an idealized zero-error
IID calculation needs 59 independent assurance decisions for a one-sided 95%
upper bound <=5%; request count does not supply those decisions.

Retain exact acquired offers, selected offers, wall time for every stage, setup
time, barrier delay, qualification, settling and cleanup. Stop at the first
inherited technical/applicability exit or the time ceiling; one attempt per
host/service. An unavailable host consumes its allocated unavailable cell when
the study is closed. No optional reruns, parameter changes, new observers or
deadline tuning. Report the fixed study when all four allocations are closed,
including negative and unavailable outcomes.

## Registration and next operational gate

The frozen package includes deterministic vectors, a dependency/portability
audit, budget arithmetic, evaluation code, synthetic tests and SHA-256 seals.
The local receipt's UTC timestamp is a reproducibility record, not an independent
timestamp authority. Public registration or publication is separate.

The remaining operational gate is **build and qualify the isolated SLO collector
adapters under this frozen contract**. Actual host availability, portable runtime
behavior and observer/quiet-host eligibility are not established offline. Do
not start either historical launcher for this study. Friend-owned V31 remains
under its original handoff; its data never enter these four fresh campaigns.
