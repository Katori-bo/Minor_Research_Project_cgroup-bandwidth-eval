# V23: work-size and burst-timescale transfer

Revision 1, 2026-10-07. Follow-up to V22, authorized as a small novelty/generality
study. This design is fixed before V23 collection. V22 evidence and decisions
remain sealed. The separate short working draft is mutable interpretation.

## Question

Can independently calibrated busy capacity predict all-offer 500 ms misses and
the paired long-minus-short burst effect within 3 pp in every validation trial
and block at two request work sizes under the retained half-CPU contract?

The candidate addition is a controlled empirical capacity-estimate comparison
with prospective prediction errors. Existing FIFO/busy-calibration methods are
baselines. Passing is limited to the tested host/service/kernel and parameter
range; increasing SHA iterations is not an independent workload or algorithm.

## Fixed contract and factors

Retain the original V20 generation-03 image/server/loadgen/gate, Go 1.26.1,
one worker/GOMAXPROCS=1, queue128, yielding off, CPUs2/4, client/controller0/1,
cpu.max=50000 100000, burst credits0 and original memory/PID defaults. No new
observer, rebuild, GC, power or quota-period treatment is used. The existing
HTTP iterations parameter changes work size. Verify every client URL and asset.

| Work size | Iterations/job | Low/high offers/s | Offers/60 s |
|---|---:|---:|---:|
| small | 44,000 | 56.6 / 169.8 | 6,792 |
| large | 88,000 | 28.3 / 84.9 | 3,396 |

Each cohort schedules 298,848,000 SHA iterations. HTTP request counts differ,
so total CPU demand need not match exactly. This normalization is declared
before collection. V22's slightly different 6,793-offer vector is not overwritten
or pooled into V23 block replications.

A has a 3 s burst cycle (1.5 s low/high); B has a 12 s cycle (6 s low/high).
Both divide the 60 s measurement window and have exactly the stated cohorts.
Warmup is the same size-specific canonical 20 s/10 s-cycle pattern for both
arms. Retain full warmup drain, empty reset, measurement and full final drain,
concurrency512, timeout5 s and existing client/HTTP stage records.

## Order and calibration

Four technical qualification slots cover smallA, smallB, largeA, largeB.
Four independent calibration slots follow: two small and two large, each using
the size-specific 10 s pattern. No qualification, V22 or validation data fits
capacity. Both size-specific prediction packages are sealed together before
the first validation slot. There are no validation-dependent parameter choices.

Calibration uses the same six fixed [6.5+10k,9.5+10k) s windows (18 s/trial),
requiring admitted-but-not-started queue>5 throughout all shared-clock placements.
Busy capacity=(C1+C2)/36 at the clock midpoint; trial-rate disagreement<=5%.
Nominal CPU/job capacity=0.5/mean(c1,c2), with c from post-reset-through-drain
cgroup usage seconds/completed jobs. Estimate both separately at each size;
do not assume doubling iterations halves capacity. Zero/invalid capacity or
inadequate/unstable calibration stops before validation, with no alternate windows.
Sensitivity uses [0.95 min(C_low/18),1.05 max(C_high/18)], 101 evenly spaced
capacities plus the busy point. This is engineering sensitivity, not a confidence
interval. Retain point per-ID predictions for both models at each size/pattern.

Four validation blocks use a balanced four-cell order, with a=smallA,
b=smallB,c=largeA,d=largeB:

1. a,b,d,c
2. b,c,a,d
3. c,d,b,a
4. d,a,c,b

Every cell occupies every position once; each size has two AB and two BA pairs.
Validation comprises16 trials and8 size-specific paired contrasts.

## Model, outcomes and frozen rules

Use the same initially empty constant-service FIFO, one active+128 waiting;
completion precedes admission at equal timestamps, and model response equals
completion. Entry/HTTP/publication/cancellation/quota pulses are omissions.
Scheduled offers determine arrivals and deadline origin. All unsuccessful offers
and rejections count as misses; denominator is the size-specific entire cohort.

Primary pass requires busy-model absolute miss error<=3 pp in every16 trial and
absolute error of miss_B-minus-miss_A<=3 pp in every8 size/block contrast: all24
checks. No pooling can rescue a cell or size. Additionally report each size's
separate primary pass/fail; failure does not erase a passing narrower subset.

Supporting queue checks require every trial's peak error<=10 jobs and rejected
fraction error<=0.5 pp. Ordinary recovery is the last return to Q<=5 after each
high-to-low boundary strictly before60 s, with no rebound>5 before the next high
phase. Horizons are half the size's assigned burst cycle, not fixed5 s.
Recovery means use all complete internal cycles; censored recovery cannot pass.
Worst admissible shared-clock error must be<=250 ms in every validation trial.
Final recovery after60 s is a separate drain diagnostic. Boundaries/horizons and
the fixed100 ms queue grid are sealed before collection.

For each size/block, baseline score is mean of the two absolute trial miss errors.
A demonstrated busy-model advantage requires its score strictly below the
nominal model in all8 size/block pairs and mean improvement>=1 pp separately at
each size. This is supporting evidence; absence of advantage is retained and
does not invalidate accurate busy forecasts. A novel or universally best
estimator is not established by this comparison.

Record 100/500/1000 ms all-offer outcomes, successful p99, response-stage residuals,
coverage, cancellations, CPU/job, delivered CPU, queue trajectory and final drain.
Only500 ms is the primary endpoint; diagnostic thresholds are not selected from
validation. Capacity and request-timing errors have different interpretations.

## Technical acceptance and bounds

Retain exact IDs/offsets and conservation, zero client drops/missed arrivals,
dispatch p99<=2 ms, warmup/measurement clock widths<=1 ms, host/server anchors,
empty reset/full drain, actual settings/assets/resources and ownership cleanup.
Record 1 s host-monitor samples with at least80 per full trial and desktop app
absent. Refresh a read-only root observer inventory/ownership review after
preparation and before collection; authenticate locally in the external terminal.

Keep initial idle600 s, sampling5 s, stable windows>=60 s, range<=2 C,
slope<=1 C/min, baseline tolerance3 C and settling timeout1200 s. Power settings
and sensor inventory stay fixed. Total24 planned slots imply32 minutes of
warmup/measurement plus at least24 minutes inter-slot settling and10 initial idle:
at least66 minutes, excluding setup/drain/replay. Bound the session to90 minutes,
with120 s cleanup grace. Time exhaustion preserves an incomplete result.
Client allowance=duration+30 s; each service drain<=100 s. Permit one total
technical retry only for a failed slot, preserving its attempt; no accepted,
adverse or unstable-calibration replacement. Source/design/boot/asset changes
stop the generation. Scientific failures finish the fixed schedule if technically
valid and within bounds. Incomplete evidence cannot receive the full-pass label.

## Selection provenance and interpretation

V22 informed this follow-up's factor selection. An offline planning calculation
using its152.47 jobs/s suggests3 s cycles should produce little500 ms loss and
12 s cycles appreciable loss. This is disclosed exploratory selection, not V23
prediction evidence. V23 capacities and forecasts use only its fresh calibration.
The two work sizes/burst cycles are now fixed and are not optimized after results.

The extension adds parameter-range evidence on one host. It cannot establish
other-service/algorithm/host transfer, a yielding boundary or a historical
quota-period cause. After this bounded test, report success or failure and write
the short empirical note; do not expand the search merely to obtain a pass.
