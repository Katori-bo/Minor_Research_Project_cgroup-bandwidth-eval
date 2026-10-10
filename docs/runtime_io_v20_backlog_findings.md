# V20 offline backlog account and testable hypotheses

2026-10-05. Analysis of the existing sixteen V20 trials only. No V21, new
performance collection, service change or quota change was launched. The sealed
V20 protocol, outcomes and original `guardrail_tradeoff_requires_review` decision
remain unchanged.

The main result is that **burst demand exceeding observed service capacity
adequately predicts the bulk of the deadline losses, queue buildup and recovery**.
This is a conditional resource/queueing explanation: it predicts outcomes from
measured capacity, but does not explain capacity itself from the quota contract.
The cause of the shorter-period CPU increase remains unresolved.

## Evidence and reproduction

The offline reviewer verifies every file in all sixteen trial seals and freshly
joins raw client/server records with the original V20 validation. All 108,688
offers are retained, including 1,266 rejections. Fresh joins match the sealed
derived request rows and clock mappings. Single-worker FIFO ordering and the
identity between the integral of logical queue occupancy and total recorded
queue waiting also pass. There are no new performance observations.

Run from the repository root:

```bash
venv/bin/python analysis/review_v20_backlog.py
```

Machine-readable results, per-cycle summaries, a 100 ms cumulative timeline,
burst-stage summaries, held-out request predictions, plots and hashes are in
[`analysis/runtime_io_v20_backlog_review/20261005`](../analysis/runtime_io_v20_backlog_review/20261005).
The reviewer is [`analysis/review_v20_backlog.py`](../analysis/review_v20_backlog.py).

The logical queue counts admitted-but-not-started intervals. Admission is
timestamped immediately before channel insertion; worker start follows dequeue.
Thus this is an exact count of recorded waiting intervals, not an independently
observed channel-occupancy trace. Admission-time channel depth remains a distinct
sample. Reconstruction uses server timestamps; assigning events to offered
burst time uses the midpoint of the shared client/server clock bracket. Per-offer
absolute stages and deadline classifications retain both bounds, approximately
0.1 ms apart. Midpoint timeline binning is descriptive, not additional precision.

## Where the waiting is

All successful deadline misses entered HTTP and were admitted certainly before
500 ms. None crossed the deadline before admission. For the 4,661 yield-on cases
already late at worker start, the deadline crossed **after admission and before
worker computation**. The application queue is therefore the location of those
losses; this does not identify which scheduling or CPU-supply intervals caused
the worker to fall behind.

Pooled descriptive counts across four blocks:

| Arm | Successful 500 ms misses | Deadline crossed while queued | During computation | After computation / before handler resume | Clock-boundary ambiguous | After handler resume |
|---|---:|---:|---:|---:|---:|---:|
| A: 100 ms, yield off | 4,853 | 3,781 | 232 | 819 | 15 | 6 |
| B: 100 ms, yield on | 4,877 | 4,661 | 198 | 0 | 13 | 5 |
| C: 20 ms, yield off | 11,633 | 11,206 | 141 | 277 | 7 | 2 |
| D: 20 ms, yield on | 11,324 | 11,177 | 143 | 1 | 3 | 0 |

C and D each also have 633 rejected offers, retained separately because they have
no admission/worker interval. Counts are descriptions, not independent request
replications. The 819 A cases also have the original program-order publication
bound; the broader stage table itself uses completion and resume markers.

Mean stages in ms, averaged across the equal-offer trials:

| Arm | Offered arrival to HTTP entry, lower–upper bound | Entry to admission | Queue | Processing wall time | Completion to handler resume |
|---|---:|---:|---:|---:|---:|
| A | 19.636–19.755 | 0.0063 | 217.724 | 6.075 | 17.280 |
| B | 15.277–15.397 | 0.0039 | 232.802 | 6.049 | 0.0579 |
| C | 11.014–11.143 | 0.0056 | 406.987 | 6.662 | 10.522 |
| D | 8.584–8.703 | 0.0049 | 408.155 | 6.577 | 0.0591 |

Queue, processing and resume summaries for C/D describe admitted computations;
they are not imputed over rejected offers. Entry covers all offers. Arrival to
entry includes client dispatch, connection/HTTP work and server entry scheduling.
Entry to admission is small on average, and its complete bounded arrival-to-
admission interval is before the deadline even for every successful miss.

For B's successful misses, mean arrival-to-entry is bounded at 18.965–19.085 ms,
mean queue waiting is 549.167 ms and mean processing is 7.004 ms. This supports
queue waiting as the dominant stage directly, rather than inferring it from a
late completion alone.

Yielding reduces arrival-to-entry and post-computation delay, while average queue
waiting rises 15.078 ms. Its effect on overall 500 ms success remains negligible
and inconsistent across blocks. This is consistent with changed execution order
and queue history, not proof of a scheduler defect or per-request displacement.
[Go's documented scheduling opportunity](https://pkg.go.dev/runtime#Gosched)
does not promise that a particular handler runs next.

## Buildup and recovery across bursts

The high phase offers 169.815 jobs/s for five seconds; the low phase offers
56.605 jobs/s for five seconds. The actual vector has 6,793 offers in 60 seconds.
Its average rate is 113.217 jobs/s, below observed backlogged service capacity in
both period arms. The problem is transient overload during the high phase.

Every one of the 96 recorded burst cycles has **zero logical queue at its
high-phase start**. Backlog grows during a burst and clears during the following
low phase; it does not ratchet upward from cycle to cycle under this vector.

- A high-phase peaks range from 88 to 102 jobs; B from 94 to 104.
- C and D reach the 128-job logical limit in every burst and reject offers.
- After the high-to-low switch, the queue falls to five or fewer jobs in
  0.844–0.996 s for A and 0.889–1.026 s for B in ordinary inter-burst recovery.
- C/D take 1.418–1.528 s in ordinary recovery. Final drain is faster because no
  new low-phase arrivals follow: 0.529–0.611 s for A/B, 0.893–0.937 s for C/D.

The threshold of five jobs avoids treating ordinary enqueue/dequeue noise as a
new backlog episode. Each cycle and final drain are reported separately in
`cycles.csv`; averages in model comparisons include final drain consistently.
The 100 ms misses concentrate in the last part of the high phase and carry into
the first low-phase second. At 20 ms, losses begin earlier in the high phase and
carry into low-phase recovery.

## Prediction from separate blocks

Fit blocks 1–2; predict blocks 3–4. Parameters use completions during a fixed
busy window, seconds 6.5–9.5 of each ten-second cycle: 18 seconds per trial.
No held-out admission, worker, response, CPU or miss record enters the prediction.
The primary model uses **one common effective capacity per quota period**, shared
by yield off/on:

- 100 ms period: 150.306 jobs/s.
- 20 ms period: 138.681 jobs/s.

The simulator is an initially empty FIFO with one job in service, 128 queue
slots and constant wall-time service duration `1/capacity`. It uses the exact
offered arrival vector, explicitly rejects overflow and approximates response
time by service completion. It omits entry delay, supply pulses, variable work
cost and completion-to-response delay. Capacity is trained from observed service,
not derived from the nominal 0.5 CPU allowance.

| Held-out trial | Observed 500 ms misses, % all offers | Predicted, % | Observed / predicted peak | Observed / predicted rejections |
|---|---:|---:|---:|---:|
| b3_A | 17.224 | 18.975 | 95 / 98 | 0 / 0 |
| b4_A | 17.562 | 18.975 | 98 / 98 | 0 / 0 |
| b3_B | 17.930 | 18.975 | 103 / 98 | 0 / 0 |
| b4_B | 17.194 | 18.975 | 99 / 98 | 0 / 0 |
| b3_C | 45.267 | 45.061 | 128 / 128 | 155 / 168 |
| b4_C | 44.605 | 45.061 | 128 / 128 | 146 / 168 |
| b3_D | 44.222 | 45.061 | 128 / 128 | 170 / 168 |
| b4_D | 44.310 | 45.061 | 128 / 128 | 152 / 168 |

Maximum held-out miss-rate error is 1.782 percentage points; peak error is five
jobs; mean recovery error is 81.8 ms. Grid queue-count MAE ranges from 1.9 to
6.2 jobs. Successful p99 error ranges from -54.8 to +14.3 ms. Mean absolute E2E
prediction error is 12.6–16.9 ms among requests successful in both the observed
and predicted admission cohorts; that conditional metric is not a whole-offer
latency metric. The full rejection/deadline predictions use all offers.

Descriptive macro tolerances were chosen retrospectively: 3 pp miss-rate error,
10 jobs peak error, 250 ms mean recovery error, 75 ms p99 error and 0.5 pp
rejection error. All eight primary predictions pass. These are **not frozen
V20 decision rules, equivalence margins or confirmatory acceptance criteria**.
The outcomes were already known before this analysis; withholding target-block
records from parameter fitting provides a useful prediction check, not a blind
prospective validation. Blocks remain the units of replication.

Two sensitivity checks prevent hiding a failed simple account:

1. A model using `0.5 CPU / whole-trial CPU per completed job` fails badly.
   It predicts approximately 46–47% misses and 198–217 rejections at 100 ms,
   where the held-out trials observed about 17–18% misses and no rejections.
   At 20 ms it overpredicts misses by about 9–10 pp. Whole-trial average CPU/job
   is not a reliable saturated burst service-cost parameter.
2. Fitting separate capacities by yield arm gives similar broad predictions but
   one B trial has 3.61 pp miss-rate error. Leave-one-block-out fits of the common
   period model give at most 2.25 pp miss-rate error across all sixteen targets;
   one rejection prediction, b2_D, exceeds the 0.5 pp descriptive rejection
   tolerance. All misses and failed checks stay in `report.json`.

The simple balance `dQ/dt ≈ arrival rate − service rate` predicts roughly 98
jobs accumulated in the 100 ms high phase. At 20 ms it predicts an unconstrained
156-job accumulation, causing the 128-slot queue to fill about 4.11 seconds into
the burst. Its idealized 500 ms crossing begins about 3.80 seconds into the high
phase at 100 ms and 2.20 seconds at 20 ms. The ledger shows the corresponding late
burst / early recovery losses.

## What remains unexplained

The model establishes a useful **service-to-backlog-to-miss** account. It does
not establish a **quota-to-service** account, predict replenishment phase, or
assign cumulative throttle time to an individual request. The
[Linux bandwidth contract](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html)
specifies quota per period; it does not supply a constant wall-time completion
rate for this application's mix of computation and HTTP/runtime work.

Finer discrepancies remain:

- The idealized queue is smoother than the observed queue and does not reproduce
  admission/worker ordering within CPU-supply pulses.
- A worker-start bias of approximately 20–25 ms in the held-out A trials is partly
  canceled by omitted handler delay when predicting E2E. Good E2E totals alone
  must not be read as exact stage prediction.
- The 20 ms, yield-off p99 is underpredicted by about 49–55 ms. In b3_C/b4_C,
  28/14 successful responses exceed one second; the model predicts none among
  accepted jobs. It predicts the broad queue losses but misses that rare tail.
- It does not explain why the busy service rate is lower at 20 ms, or why capacity
  trained from bursts would transfer to a different arrival pattern.

These gaps concern cost, supply/ordering detail and extrapolation. They do not
restore a demonstrated overall deadline benefit for the isolated delayed-handler
intervention. More precise attribution would require qualified observation that
the current records do not contain.

## Audit of the CPU increase

Measured cgroup CPU per completed computation, ms:

| Arm | Total CPU | User CPU | System CPU |
|---|---:|---:|---:|
| A | 3.6301 | 3.5499 | 0.0802 |
| B | 3.6468 | 3.5662 | 0.0806 |
| C | 3.8332 | 3.7511 | 0.0822 |
| D | 3.8338 | 3.7509 | 0.0830 |

C−A is +0.2031 ms/job, with 99.0% of the increment in user CPU. D−B is +0.1871
ms/job, with 98.7% in user CPU. This is not evidence for attributing the increment
to kernel accounting overhead alone. The denominator is completed computations;
the numerator also includes HTTP/runtime/recording overhead and rejected-offer
handling. There is no recorded CPU counter around each SHA computation.

Existing processing records add a constraint. In settled low-phase seconds 2–4,
processing-wall medians are approximately 4.563/4.581/4.575/4.583 ms for A/B/C/D.
In high-phase seconds 6–9, the processing-wall 10th percentiles are
2.901/2.947/3.053/3.042 ms. Thus the shorter-period difference appears in the fast
part of the busy-phase distribution while low-phase medians remain similar.
Wall time includes possible interruptions; these quantiles are **not per-job
CPU time** or proof of uninterrupted execution.

Frequency evidence is present, but coarse. The monitor retained about 60
measurement-range samples per trial, selected using cumulative cgroup usage
between measurement-start and measurement-stop observations. It did not retain
a direct real-time/monotonic bridge for precisely labeling each monitor sample by
burst phase. Power policy remains `amd-pstate-epp`, `powersave`,
`balance_performance`, balanced platform profile, on AC, constant in these samples.

Mean sampled temperatures are about 64.3/64.1/60.1/60.2°C for A/B/C/D. The shorter
period is cooler in these records, so an explanation based simply on a hotter
shorter-period host is unsupported. Mean core-4 frequency snapshots are about
3001/2953/3513/3472 MHz; core-2 snapshots are about 2331/2405/2499/2594 MHz. The
coarse observations do not show a general lower frequency in C/D. They also do
not identify the worker's active core or frequency while executing each job.

Linux documents that
[`scaling_cur_freq`](https://docs.kernel.org/admin-guide/pm/cpufreq.html)
may differ from instantaneous hardware frequency. AMD's
[EPP documentation](https://docs.kernel.org/admin-guide/pm/amd-pstate.html)
describes hardware performance preferences, rather than a fixed operating
frequency. Neither source establishes the mechanism in these trials.

Missing evidence: worker thread CPU/cycles/instructions per computation,
execution-weighted frequency, cache behavior, GC/runtime CPU breakdown and actual
runnable/throttle intervals. Keep the CPU-increase cause **unknown**. Potential
paths include changed user-space work, execution efficiency under repeated
pauses, frequency/core behavior and admitted-cohort composition; none is proved.

## Decision and hypotheses worth testing

Close the **isolated delayed-handler remedy investigation** for this workload
and 500 ms objective. The intervention removed its symptom without net deadline
benefit, and an ordinary queue model using independently trained capacity
predicts the main losses and recovery. Retain A—one worker, GOMAXPROCS=1, 100 ms
period, yield off—as the best observed baseline. Do not launch V21 or another
yield/worker/period sweep automatically.

The following hypotheses have different evidential status:

| Hypothesis | Current answer | Discriminating observation |
|---|---|---|
| Transient burst demand exceeding service produces the main 500 ms losses. | Supported within this collected burst pattern by held-out buildup, recovery and miss predictions. | Compare identical work/CPU settings with the same offers spread evenly; check backlog and misses along with cost. |
| Effective service capacity transfers from bursty to evenly spread arrivals. | Untested; this is the main extrapolation assumption. | If even arrivals remain late and CPU/job changes enough to reduce service, the constant-capacity extension fails even though queueing may still explain the losses. |
| Shorter periods change user-side execution cost or efficiency, beyond adding off-CPU waiting. | Compatible with the user CPU increment; exact cause unknown. | If the cost question becomes necessary, qualify worker CPU/cycles/instructions measurement and compare periods with verified operating-frequency control. Separate SHA work from runtime/HTTP CPU before attributing a cause. |

### Smallest candidate validation, if independent validation is desired

Use **A only**, keeping the exact binary, 44,000 iterations, one worker,
GOMAXPROCS=1, 128 queue slots, 50/100 ms quota contract, affinities, warmup, monitor,
thermal policy and full drain unchanged. Compare the retained burst vector with
6,793 offers at offsets `i * 60 / 6793` seconds. This keeps total offers and work
requested fixed at 113.217 jobs/s; actual completed work can still differ if an
arm rejects, and every rejection must be retained.

The current model's numerical predictions are:

- Bursty: 18.975% all-offer 500 ms misses, peak logical queue 98, no rejection;
  about one second ordinary recovery to five queued jobs or fewer.
- Even: zero misses and rejections and zero waiting jobs in the idealized model.
  Treat this as a sharp model prediction, not a promised measured p99.

A practical prospective check could require burst prediction error within
3 pp, queue peak within 10 jobs and ordinary recovery within 250 ms; for even
arrivals, at least 99% all-offer 500 ms success, no rejections and peak queue at
most ten jobs. These are candidate criteria to freeze with a complete protocol
before any collection, not new conditions attached to the completed V20 results.
Balanced fresh paired blocks, all retained offers and operational qualification
are needed; the old blocks are not new replications.

Record CPU/job in both arms. At 113.217 jobs/s, a constant CPU cost above
**4.416 ms/job** would itself require more than 0.5 CPU on average. The observed
low-phase processing-wall median is around 4.57 ms, but is not a CPU measurement;
it is a reason to test cost/capacity transfer rather than assume it. If the even
arm fails while cost rises, update the service-cost account before proposing a
new scheduler mechanism. If it fails with comparable cost and unexplained long
waiting, use that specific discrepancy to select a qualified readiness/supply
observation. The experiment tests burst backlog and model transfer, not exclusive
attribution to quota throttling.

The rare >1 s tail in C is documented as a remaining model limitation. It does
not justify returning to a failed shorter-period remedy unless that tail itself
becomes a separate research objective.
