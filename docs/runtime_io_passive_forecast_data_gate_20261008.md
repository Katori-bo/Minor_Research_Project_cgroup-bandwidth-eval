# Passive forecast candidate: data needs and collection gate

8 October 2026. The user is open to new useful data. This document identifies
what could change the [novelty/feasibility verdict](runtime_io_passive_forecast_novelty_screen_20261008.md);
it is not a frozen execution protocol or a campaign launch. Collection is stopped.

## Data already sufficient for the next offline step

V28 contains twelve idle/steady calibration observations in two blocks, including
four strict-low 15/30 runs, request event/clock records, enclosing CPU counters,
host state and coarse CPU samples. Its sixteen burst outcomes are available
as retrospective checks. V22/V23 provide earlier scoped work-size/timescale
validation. No future scientific rule may inherit their prospective status
when selected after those outcomes became known.

These inputs suffice to map units, required observations and source assumptions
for ordinary CPU, response/event and transient demand baselines. Lack of an
implemented fair competitor is not solved by collecting more trials.

## Measurements that could change the decision

| Priority and data | Question it resolves | Minimum contents | Collection condition |
|---|---|---|---|
| First: paired history-to-future outcomes | Can a reliability/refusal rule work before seeing burst error, with useful coverage? | Permitted prior traffic/low-load observations; exact information available at decision time; frozen forecasts/refusals; subsequent full offered-cohort outcomes and resource/configuration state | A specific guard capability survives the baseline comparison and its development/fresh-test split is fixed. |
| First: informative histories and boundary schedules | Does the rule distinguish sufficient from insufficient evidence rather than recognize only easy zero-miss cases? | Narrow versus broader but permissible load histories; observed state variation; both sides of a declared miss/error boundary; include failures/refusals | Conditions selected by a declared calibration-only/design rule, not a favorable validation pilot. Actual ordinary/natural traffic if production applicability is claimed. |
| Conditional: measured worker/request CPU | Can elapsed processing time separate CPU demand from scheduling/wait/other work? | Worker CPU consumption with defined request attribution, enclosing clock bounds and overhead control; retain unattributable work | A proposed baseline/guard genuinely needs CPU attribution unavailable in saved traces. Qualify observer cost before use. |
| Conditional: quota/runnable-service timing | Does within-period availability explain or bound forecast unreliability? | Explicit quota replenishment/throttle and execution/runnable events with identities, loss checks and clock mapping | A specific timing-based capability survives cheaper alternatives. Coarse polling is not a phase trace; neutrality is unestablished. |
| Later: independent workload/host transfer | Does an established rule generalize outside the SHA case? | Independently specified workload/request classes and resource states, same scoped outcomes and calibration accounting | A useful method already exists. Transfer collection is not the first attempt to manufacture a method. |

The most informative first future data would be matched allowable history and
future-outcome pairs. More repetitions of the same steady 15/30 loads can
estimate variability there but do not by themselves identify loaded demand,
future quota service or model error. Extra metrics need an explicit information
gain claim and a comparator with equal access.

Cold-start prediction and previously trained deployment require different data.
Historical burst/profile labels can be allowed in the latter, but their offline
acquisition cost and transfer assumptions must be disclosed. A guard trained
using loaded experiments is not an observation-only cold-start method.

## A future dataset's information boundary

For each independent prediction episode, retain:

1. Workload/request class, application identity, quota/period/burst/affinity,
   initial queue and relevant host state.
2. The complete permitted history, acquisition timestamps, counter brackets,
   request clocks and qualification outcomes. Mark natural requests and probes.
3. The future schedule supplied to the method and the caller's accuracy or
   allowable-miss target. The target must exist before scoring.
4. The model, guard and baseline version; all training/calibration references;
   forecast/uncertainty or refusal; a decision-time seal.
5. Subsequent offered-request outcomes, including rejections/timeouts, and any
   observed resource drift. These are labels, never inputs to the same prediction.
6. Full expense: setup, settling, warmup, probes, drains, failed qualification,
   CPU/requests, late offers, monitoring and offline training/tuning.

Burst validation can deliberately exercise a research test instance after
freezing predictions. That is separate from deliberately overloading a live
service to calibrate a deployment-time predictor. If only natural future traffic
is available, retain its actual arrival trace and uncertainty about the schedule;
do not silently pretend it was known exactly beforehand.

## What must be fixed before collection

- One practical capability beyond established estimation plus ordinary
  uncertainty/abstention. A different endpoint alone is insufficient.
- A fair published baseline implementation or explicit justified adaptation;
  resource/response units and quota assumptions; no free historical profiles.
- Output contract, data-supported model assumptions, accepted-case error,
  minimum answer coverage, nonzero-case coverage, refusal handling and disruption
  budget. A guard that answers nothing is not successful.
- Separate model development, error calibration and untouched prospective test
  episodes. Split by meaningful history/state blocks; request-level random splits
  and overlapping windows are not independent evidence.
- Sample-size rationale, bounded time/trial budget, technical failure handling,
  observer qualification and one proceed/stop criterion. Preserve adverse results.

For scale only: if one chose a claim of at most 5% bad accepted predictions
at 95% confidence, a one-sided binomial calculation with zero bad outcomes
would require at least 59 independent accepted prediction episodes. That is
not 59 HTTP requests, a chosen study budget, or a valid guarantee under arbitrary
state/distribution shift. Four validation blocks cannot justify that claim just
because they contain thousands of requests. The eventual claim determines the
necessary data, rather than collecting a large dataset first.

## Present disposition

Do the next published-baseline/guard-contract assessment with existing data.
Do not start phase tracing, instrumentation repair, new workloads or a new
campaign simply because more measurements are possible. Once a distinct
capability survives, prepare its concrete bounded protocol and collect only
the data needed to test it. The empirical paper and its outcomes are preserved.
