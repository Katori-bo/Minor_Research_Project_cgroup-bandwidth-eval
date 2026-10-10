# V20 proposal: execution after a result is available

2026-10-05. Proposal only; no V20 runner or performance collection is implemented.
This revises the earlier default recommendation of confirming worker count next:
the user's priority is explaining the remaining issue. Independent confirmation
of a final practical configuration remains separate future work.

## Reason for this experiment

The [offline residual review](runtime_io_v19_residual_findings.md) gives a source
and timestamp bound: all 1,182 one-worker deadline crossings had an available
result before 500 ms, yet the handler resumed afterward. Typical conservative
post-publication wait is at least about 54 ms. This narrows the question beyond
"fewer workers help," without adding a publication observer.

Next question: how does this residual execution delay respond to a worker
scheduling opportunity after publication, and to more frequent CPU replenishment?
The factors test contributions and interaction; neither individually identifies
an exclusive cause or proves runnable readiness/scheduler unfairness.

Yielding and quota-period tuning are known controls. V8 yielding concerned
different pre-handler waits, GOMAXPROCS=2 and four workers, with perturbative
runtime tracing. Earlier period comparisons also used different settings. The
new objective is the already-available-result residual at GOMAXPROCS=1/one worker,
with the exact original executable and no extra observer. This is not a novelty
claim about either control.

## Proposed minimum discriminating matrix

Keep **one worker and GOMAXPROCS=1 in every arm**. Reuse the same original image,
44,000-iteration work, queue 128, service/controller affinities, zero burst,
packaged loading, exact offered arrival vector, 20 s warmup, 60 s measurement,
complete drain and V19 quiet/thermal/resource policy.

| Arm | Period | Quota | Existing worker yield flag |
|---|---:|---:|---|
| A | 100 ms | 50 ms | Off: current one-worker baseline |
| B | 100 ms | 50 ms | On |
| C | 20 ms | 10 ms | Off |
| D | 20 ms | 10 ms | On |

Both period levels allow 0.5 CPU on average, but provide different temporal CPU
supply. This is explicitly a changed quota/period contract, not the unchanged
V19 contract. Linux documents quota as CPU time per period and discusses the
effect of shorter periods on latency:
[CFS bandwidth documentation](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html).
Do not assume an exact blackout duration, matched replenishment phase, or that
wall time modulo period is a budget measurement.

The retained binary already reads `WORKER_YIELD` and calls `runtime.Gosched()`
after `runJob` returns, hence after result publication. No rebuild, new marker,
sleep, acknowledgement protocol or kernel attachment is proposed. Go documents
Gosched as a scheduling opportunity for other goroutines, not a guarantee that a
particular handler runs: [runtime source](https://go.dev/src/runtime/proc.go).

Propose four fresh independent four-arm blocks (**16 measured trials**), with
orders A B C D; B A D C; C D A B; D C B A. Each arm occupies each position once;
each pair has both order directions twice. This is an exploratory mechanism
probe, not confirmation or a promise of four-block precision. Before implementing,
freeze the complete protocol and analysis. Qualification uses full-duration
operational checks of each arm without screening favorable performance.

## Evidence and prespecified interpretation

Compute paired yield effects at each period, period effects at each yield state,
and their interaction within each block. Blocks, not requests, are replications.
Report every block and retain all offers, adverse outcomes and failed attempts.

Main mechanism outcomes: completion-to-resume mean and p99, >50 ms gap/all-offer
fraction, and available-result deadline crossings where conservatively bounded.
Also report the full gap distribution, queue/processing/entry stages, successful
500/1,000 ms fractions, failures, CPU/job, throughput and successful p99.
For yield arms, a handler may resume before the next job starts; that next-start
bound then becomes uninformative. Do not turn missing bounds into zero delay or
compare only favorable post-treatment crossing subsets as a causal effect.

Use the whole offered cohort for treatment summaries. Retain V19's practical
outcome guardrails against A in every block: no more than 1 pp loss at 1,000 ms,
0.1 pp failure increase, 5% CPU/job increase or 10% successful-p99 increase.
These do not suppress reporting adverse mechanism effects.

Before collecting, freeze a conservative descriptive signal rule: median paired
whole-cohort gap-mean reduction at least 25%, same direction in at least three
of four blocks, with all-offer 500 ms success not worse in the median. Show paired
block uncertainty and every guardrail; a screen pass is exploratory evidence,
not proof of a mechanism. Keep p99/distribution and deadline-crossing changes
as supporting outcomes rather than choosing a different primary afterward.

Expected branches:

- Yield materially reduces delay at the original period with little CPU/job
  change: execution opportunities after worker publication contribute. This does
  not reveal the exact runtime/OS readiness path.
- Shorter periods materially reduce delay with yield both off and on: temporal
  CPU supply contributes. Period changes can also affect scheduling and capacity,
  so this is not per-request proof of quota throttling.
- Both contribute or interact: report a mixed explanation; do not pick one cause.
- Neither gives a clear effect, effects reverse across blocks, or capacity/cost
  changes dominate: remain inconclusive. Do not expand into a tuning sweep or
  infer a cause from whichever deadline outcome looks best. Revisit what minimal
  readiness/CPU observation can be qualified for this specific residual.
- Adverse guardrails: retain the result as a tradeoff rather than recommend a fix.

V19 A/A evidence supports its own procedure; it does not automatically establish
repeatability or precise effects for V20. Preserved originals, independently
replayed raw data, frozen inputs, operational qualification and the balanced
block contrasts remain required. Fresh technical attempts follow V19's retention
and interruption rules. No new performance run is authorized by this document.
