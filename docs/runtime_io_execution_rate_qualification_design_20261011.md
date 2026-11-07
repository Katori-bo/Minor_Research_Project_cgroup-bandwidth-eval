# Bounded execution-rate qualification design and go/no-go decision

11 October 2026. The user authorized defining the study after the read-only
[candidate audit](runtime_io_execution_rate_candidate_20261011.md). This is an
offline design, with arithmetic and a pre-implementation decision. No observer,
launcher, hardware event, root action, service or manuscript edit is produced.
Existing qualification and scientific results retain their original decisions.

**Decision: no-go for observer implementation or external qualification within
the current budget.** A bounded qualification is specified below, but existing
precision/cost evidence does not justify collecting it. This holds the candidate;
it does not show that clock measurements are inaccurate, harmful or useless.

## What qualification would and would not establish

Question: can task-attached APERF/MPERF and worker CPU runtime provide sufficiently
precise, correctly bounded 25-offer warmup measurements at affordable observer
cost for this NGINX workload?

Qualification would establish only the declared measurement contract and bounded
observer equivalence under P0, at 4/s and 8/s, on this host. It would not establish
future-state persistence, a reliability selector, causal frequency attribution,
absolute GHz accuracy, a general distribution guarantee or method novelty.
P1 and other workloads require their own scope; P1 data below supplies only a
conservative engineering sensitivity scale. There is no automatic predictive
discovery or confirmation after qualification.

## Apparatus and information boundary

Retain stock NGINX/native zlib, 1 MiB gzip-6, one guarded single-thread worker on
CPU2, Q25 ms/P100 ms, control CPUs0/1 and the existing source/process/cgroup,
watchdog, outcome and owned-cleanup contracts. Keep P0 powersave with
balance_performance and sched_schedstats=0. Require the unchanged baseline;
do not set EPP, load an MSR module, alter paranoia, assign persistent capabilities
or isolate/change the SMT sibling. CPU3 sharing the core remains an explicit
limitation and an observed baseline, not a controlled absence of interference.

Counter access would be through a bounded privileged helper in an external quiet
terminal, with exact owned task identity and file descriptors. Design for
perf_event_open with worker PID, CPU2, inherit=0, count-only APERF/MPERF group,
no user/kernel exclusions, no sampling or periodic polling. Installed-kernel
support remains a qualification question. Failure is retained and stops; do not
silently use CPU-wide counts or change perf_event_paranoid. A CPU-wide proposal
would be a different attribution contract and need a new design.

Common controls in both arms: stock initial status, complete drain, 100 ms quiet
interval, identity/executable/parent/starttime/CPU2-affinity guards and client/
cgroup counters. No status request is allowed inside the counter window. Start
and finish boundaries require quiescent worker state with identity brackets.
Charge the shared controls separately; equivalence concerns the incremental
observer under this common contract, not its absolute cost versus old campaigns.

On adds event installation while the worker is quiescent, group enable/baseline,
identity-bracketed group counts and schedstat runtime around the complete 25-offer
warmup including drain, disable/final group read, descriptor close, F/C calculation
and raw/provisional serialization. Capture count IDs, ordering, monotonic times,
enabled/running times, identities and status. F = delta_APERF/delta_MPERF;
C = delta_worker_runtime/25. Preserve zero/invalid/failure cases as unavailable;
never turn missing counters into F=0. Off adds none of these operations.

The full on observer includes scheduling-boundary counter work, remote reads,
open/enable/disable/close and serialization. Two application reads do not imply
two kernel operations. Counter activity ends before the following 300-offer
window; any induced state carryover is still included in the overhead comparison.
No target counters or outcomes enter provisional warmup features. Seal the
feature/closed-descriptor receipt before target start. There is no reliability
forecast or future-state rule in this qualification.

## Precision goals and their explicit assumptions

The earlier calibration-only sensitivity audit found symmetric location radii
47.708 us (P0) and 43.496 us (P1) before any of its five empirical probabilities
changed by more than 5 pp. These are finite-sample geometry, not future error
bounds. Use the smaller r=43.496 us as a conservative design scale, not a tuned
classification threshold. Allocate r/2=21.748 us to clock-measurement error and
r/2 to the difference of two CPU-accounting windows.

For a declared CPU-service scale S=20 ms, assume *for planning only* that a log
execution-speed error u translates into at most S*(exp(abs(u))-1) CPU-service
time error, and that this transfers additively to response time. This assumption
does not account for queueing, stalls, quota waiting or downstream delays and
has not been validated. If each clock window has bounded absolute log error a,
the comparison has <=2a error, so require

`a <= 0.5*log(1+r/(2*S)) = 0.000543405`,

or approximately 0.05436% upper relative error per window. The CPU-accounting
allocation is <=r/4=10.874 us per offer per window (271.850 us per 25-offer
window). These are deterministic engineering targets under a hypothetical
mapping; they are not sampling confidence intervals, observed accuracy, necessary
sample sizes or a validated predictive requirement. If S differs, use the
declared formula and report the resulting scope rather than claiming the 20 ms
scale covers all requests. Large event counts do not imply many independent
warmup observations.

For uncertain positive counts A in [A-eA,A+eA] and M in [M-eM,M+eM], the ratio
lies in [(A-eA)/(M+eM),(A+eA)/(M-eM)]. Require eA<A, eM<M; unsupported uncertainty
bounds stop qualification. Counts alone do not provide eA/eM. They need a justified
hardware/attachment/window-alignment bound, including read skew and any leakage.
Repeated identical reads of a stopped group check consistency, not absolute
accuracy or future repeatability. No accessible independent clock oracle or
verified response-time mapping currently establishes these accuracy targets.

Declare the observer mean-latency equivalence allowance +/-20 us before any
hardware data, below the half-radius engineering allocation. This is a new
allowance for this candidate, not a revision of the old +/-100 us worker-wait
decision. Mean equivalence cannot certify every quantile or probability, so the
deadline-panel probability checks below are separate. The choice is an engineering
allocation, not a theorem that 20 us mean disturbance implies <=2 pp tail error.

## Stage A: scope and boundary qualification, cap 600 seconds

Four owned services/fixtures, no repeat or substitution:

1. Task-scope fixture: a CPU2-pinned owned helper executes a bounded active
   segment, then parks. During a second parked segment a separately owned helper
   executes on CPU2 for <=200 ms. With the target still parked, APERF/MPERF task
   counts and runtime must remain unchanged. Record active positive increments
   and stopped-group consistency. This distinguishes task attribution from
   counting a foreign task, not immunity to interrupts while the target runs.
2. Lifecycle fixture: verify failure closed on task exit/changed identity and
   unavailable group, with exact descriptor/helper cleanup. No replacement task
   is accepted as the same worker; no CPU-wide fallback. The fixture's deliberately
   invalid evidence must be rejected, not included as a qualified reading.
3. NGINX at 4/s: 25 warmup plus 20 subsequent offers, then owned cleanup.
4. NGINX at 8/s: the identical offer contract, then owned cleanup.

The two workload probes acquire 90 offers; helper fixtures have no HTTP offers
but their CPU/wall cost and privilege usage belong in the ledger. Four <=120 s
lifetimes, four 10 s settling allowances and a 60 s closing reserve total 580 s,
inside the 600 s phase cap. These are caps, not observed times. A later executable
must verify startup/drain/cleanup feasibility with its enclosing deadline.

Operational requirements: stable worker identity and CPU placement; no count
reversal; positive active APERF/MPERF/runtime; exact group IDs; nonzero equal
enabled/running coverage without multiplex scaling; no activity during parked
foreign-task control; consistent stopped reads. Record API limitations and stop
if this exact attachment/group mode is unsupported. Per-boundary control read
bracket <=2 ms and total synchronous on operation <=20 ms are watchdog limits,
not accuracy or behavioral-equivalence evidence.

Require a documented ratio/window uncertainty bound meeting the planning goals,
and worker versus isolated cgroup CPU discrepancy <=10.874 us per offer. The
latter is a cross-scope consistency check, not an independent runtime or clock
truth oracle. After workload warmup, an extra 100 ms quiet diagnostic interval
with no status request checks residual worker CPU <=10.874 us per original offer.
Task-clock increments must have a justified alignment/leakage bound; do not
infer a valid F ratio from an almost-zero MPERF denominator. These extra reads
and quiet diagnostic interval are Stage A only, not the later on observer.

Even passing all mechanical controls would leave absolute ratio accuracy
unverified if the hardware/window uncertainty bound cannot be supplied. Mark
that result `execution_rate_scope_incomplete`, not measurement-qualified.
Any identity, boundary, source, budget or integrity failure stops and preserves
the complete attempt. Stage A is not currently authorized for collection by the
offline design decision; no scope-only launcher is prepared as a workaround.

## Stage B: bounded randomized on/off comparison, cap 2700 seconds

Only if Stage A passes **and** an independently justified precision/cost design
revisits the current no-go decision: eight paired blocks at each rate, fresh
services, 25 warmup plus 300 targets per arm. Each block includes both rates;
randomize rate order and off/on order once from a sealed seed. Both arms keep
identical request, host and common guard contracts. No within-service toggle is
substituted without separately addressing state carryover and attachment cost.

32 services x325 offers =10,400 overhead offers, plus 90 Stage A HTTP offers
=10,490 new offers. Helpers, initialization and preflight remain separately
charged. Each service has a 120 s lifetime; the global overhead phase reserves
120 s for closing. Check remaining global/per-service time before launching
each service. A budget stop is incomplete, not a complete smaller-n analysis.
No resume, replacement, automatic extension or second generation is selected.

Use the five already sealed P0 calibration-only deadlines:
17.433213, 20.683338, 21.041565, 21.341755 and 21.562926 ms. These were selected
from 800 P0 calibration offers, not from qualification outcomes; no fresh
calibration is claimed. The original source campaign acquired 1,600 calibration
measurement and 100 calibration warmup offers across both policies. Borrowing
its cutoff definitions incurs historical acquisition cost and supplies neither
new F/C reference measurements nor an independently fresh forecasting calibration.

For each rate form eight paired on-minus-off differences in five all-offer
target miss percentages, target mean complete-response time and warmup mean
complete-response time. These are 14 gates. Miss margins are +/-2 pp at each
cutoff; both mean margins are +/-20 us. Use conditional two-sided intervals
`mean +/- t_(1-.05/(2*14),7) * paired_SD/sqrt(8)`.
Require all 14 intervals wholly inside their margins. The family of intervals
has >=95% coverage only under the stated normal/independent paired-block model;
one chronological host session does not establish that model. No independence
across deadlines/gates is required for the Bonferroni bound. This is a conservative
simultaneous-interval construction, not a minimum-cost equivalence test.

Require pooled target misses at the median cutoff to be between 10% and 90% at
both rates. Retain and report saturated other cutoffs: equivalence there covers
only the observed regime and cannot establish meaningful tail sensitivity.
No alternative cutoff is substituted after observing saturation. Probabilities
use every offered request, strict deadline exceedance and failed-offer mass.
Any failed offer makes the finite all-offer mean unavailable and therefore
qualification technically incomplete; do not use successful-only means.
Record quota throttling, dispatch/overlap and sibling/host annotations and retain
the cohort. Identity/source violations, corrupt responses, missing data or time
limits stop; noisy intact blocks remain included.

Possible statuses after a separately implemented authorized attempt:
`execution_rate_measurement_qualification_supported` only if both stages and all
gates pass; `execution_rate_overhead_inconclusive` for a complete valid comparison
that fails interval containment; `execution_rate_scope_incomplete` for unresolved
accuracy/attribution; and `execution_rate_qualification_stopped` for a technical/
integrity/budget failure. None licenses automatic prediction work, repeats,
relaxed margins or selecting favorable rates/deadlines.

## Offline cost and precision assessment: why no-go now

Only the existing, separately inconclusive worker-wait observer provides paired
noise/cost observations. It is a different observer, so its moments are
conditional planning inputs, not predicted APERF/MPERF behavior. Historical pair
costs including service/gap work are 186.621 s at 4/s and 105.510 s at 8/s.
With a 120 s phase reserve, their linear extrapolation permits at most eight
balanced pairs per rate within 2700 s; overhead projects to 2337.048 s, with
242.952 s spare after reserve. Adding the full Stage A cap gives 48.951 minutes,
excluding preflight and unmeasured new counter costs. Service budgets still need
qualification; average cost is not a certified wall-time bound.

| Conditional zero-center interval geometry | 4/s | 8/s |
|---|---:|---:|
| Historical warmup paired SD | 176.857 us | 172.752 us |
| 14-gate halfwidth with 8 pairs | 268.804 us | 262.564 us |
| Warmup margin | 20 us | 20 us |
| Largest substituted SD fitting that margin | 13.159 us | 13.159 us |
| Reduction from historical SD needed | 92.56% | 92.38% |
| Zero-center width-only pairs for the warmup gate | 669 | 639 |
| Width-only pairs with a looser 100 us margin | 32 | 31 |

Even an illustrative single ordinary 95% interval at eight pairs has roughly
145--148 us substituted halfwidth, exceeding the earlier 100 us allowance;
this budget concern does not arise solely from the new 14-gate construction.
Reducing the historical SD by 90% still misses the 20 us simultaneous geometry;
95% reduction would fit its width, but no mechanism supporting that reduction
has been demonstrated. Old means are not treated as new-observer effects: if the
old -67.336 us 8/s mean did persist, the new 20 us allowance could not pass merely
by increasing sample size. This does not identify observer-induced harm.

Balancing the zero-center warmup geometry at 669 pairs per rate would acquire
869,790 new HTTP offers and project to 54.454 hours including a fresh Stage A
cap, excluding new counter/preflight/rest costs. This substitutes hypothetical
future SD and mean into an interval. It is **not power, a minimum sample size,
actual new-observer variance or an overall pass probability**. The remaining
12 gates, counter accuracy, lifetime/domain and endpoint informativeness are not
qualified by that arithmetic. No such larger run is selected.

The budget and mapping uncertainty together give no-go now. A smaller proposed
observer does not establish a >92% reduction in warmup variance, and no verified
state-to-response mapping establishes the clock precision target. Do not perform
an unchanged small repeat or a scope-only hardware run just to produce more data.
Reopen only for an independently justified redesign that reduces measurement/
comparison noise while preserving the intended input and time boundary, or an
explicitly changed research budget; then re-evaluate and freeze a new package.

## Preservation and next research gate

Eight numerical/invalid-input checks pass; the sealed planning JSON replays from
its hashed inputs. Original counter audit, both prior qualification/scientific
review manifests, live paper and earlier precision/cost evidence are preserved.
No source under an existing seal is edited. The earlier candidate remains a
historical proposal; this later design records its current collection hold.

After any eventual genuine qualification, the equal-cost ordinary comparator
must receive F, C, calibration, identical offers and decision time. It needs its
own specified model/development budget before a fresh discovery campaign.
Development then must demonstrate a relation from pre-validation state to later
forecast error at useful coverage; separate fresh evidence would confirm a
frozen rule. Measurement qualification alone never supplies that relation.

For now carry the complete empirical findings forward; a fresh-clock method
experiment is not selected. Manuscript integration remains a separate next task.
Longer warmups and worker-wait stay held; friend-owned V31 remains pending.

Evidence: `analysis/runtime_io_execution_rate_qualification_design/20261011/`.
Read-only replay: `python3 -B analysis/plan_execution_rate_qualification.py --verify`.
Statistical references: [NIST paired observations](https://www.itl.nist.gov/div898/handbook/prc/section3/prc311.htm)
and [NIST TN 2106, equivalence chapter](https://nvlpubs.nist.gov/nistpubs/TechnicalNotes/NIST.TN.2106.pdf).
Measurement references: [upstream MSR PMU](https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/events/msr.c)
and [perf access controls](https://docs.kernel.org/admin-guide/perf-security.html).
