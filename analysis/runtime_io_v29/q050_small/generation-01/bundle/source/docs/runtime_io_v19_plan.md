# V19 proposal: test worker concurrency before adding another observer

Prepared overnight 2026-10-04–05, before V19 data collection. **Plan only: no V19 runner or
performance trial has been implemented or launched.** The user will request
implementation after reviewing it.

## Decision and question

The [overnight retained-data analysis](../analysis/runtime_io_v19_planning/offline-20261004/report.md)
finds 3,565 untraced 500 ms misses whose computation finished before deadline but
whose handler resumed afterward. All these gaps contain other job starts; the
median is 14. Queue growth and post-computation waits concentrate late in the
high-rate burst. V18's full kernel observer failed its original practical screen.

**Next question:** at GOMAXPROCS=1 under the unchanged fractional CPU quota, does
reducing CPU-worker concurrency from four to one improve timely client responses
and reduce the measured completion-to-resume interval, or just move waiting into
the computation queue?

Use an existing configuration control in the exact retained service. This tests
the configuration's total effect on observable outcomes. It does not identify
publication/readiness, establish scheduler unfairness, or compare runtimes.
The missing worker control is worth answering before rebuilding the service for
another observer or inventing an acknowledgment policy.

## Hypotheses and discriminating outcomes

| Explanation | Expected response to one worker | Interpretation |
|---|---|---|
| Multiple CPU workers materially prolong result handoff | Smaller completion-to-resume gaps and fewer corresponding crossings; improved timely success | Worker concurrency contributes under this workload; exact readiness mechanism still unknown |
| CPU supply/capacity dominates, with little net benefit from fewer workers | Queue waiting grows enough to offset any handoff reduction, or all outcomes remain similar | A static worker cap is insufficient; report the tradeoff rather than call the interval recovered |
| The observed interval mainly reflects another unchanged path | Gap distribution remains broadly unchanged | Narrow the next investigation toward publication/bookkeeping or periodic execution behavior |
| Current launch/environment variation is larger than small effects | Identical four-worker arms exceed the repeatability screen | Stop small-effect attribution and design a separate reproducibility/phase study |

These hypotheses can coexist. A gain is not proof of one exclusive cause.
Different CPU/job costs are measured mediators/confounds for a scheduler-only claim.

## Smallest useful matrix

Use **six independent blocks, three trials per block: 18 measured trials**.

| Arm | GOMAXPROCS | CPU workers | Purpose |
|---|---:|---:|---|
| A: four_a | 1 | 4 | Original configuration |
| B: four_b | 1 | 4 | Identical configuration and launch procedure; repeatability control |
| C: one | 1 | 1 | Existing worker limit |

A/B labels appear only in runner metadata, container names and evidence paths.
They must not alter service arguments, executable bytes, image, environment
variables, requests, endpoint calls, startup barrier or warmup. C changes only
`WORKERS=1`. The original binary already reads `WORKERS`; confirm its snapshot
reports the requested setting. No build, shared-file loading treatment, yield,
runtime trace, BPF attachment, extra inline timestamp or new event storage.

Freeze all six permutations in this order, giving each arm each ordinal position
twice and each pair of arms three orderings in each direction:

| Block | Order |
|---|---|
| 1 | A B C |
| 2 | B C A |
| 3 | C A B |
| 4 | A C B |
| 5 | C B A |
| 6 | B A C |

Each trial starts a fresh container and client and drains fully. Blocks, not
requests, are the experimental units. No new GOMAXPROCS=2 arm, period factor,
worker=2 tuning, admission policy or burst-history treatment in this first batch.

## Frozen inputs and procedure

Start from V18 generation-04's verified original image, packaged executable,
client and FIFO startup gate. Preserve the original retained build/source seals.
Write a distinct V19 session, preparation snapshot and implementation source
set. Do not edit the 95 V18-frozen source paths to implement V19; new modules can
reuse unchanged helper functions where their frozen semantics match.

| Setting | Required value |
|---|---|
| Go/service | Exact V18 original image and executable; stock Go 1.26.1; existing `INSTRUMENT=1` |
| Runtime/worker settings | GOMAXPROCS=1; workers as matrix above; queue=128 |
| Work | 44,000 SHA iterations per request |
| Service placement | Effective cpuset CPUs 2,4; do not claim exclusive isolation |
| CPU allowance | `cpu.max=50000 100000`; `cpu.max.burst=0`; uncapped ancestors |
| Other resources | Omit historical memory/PID overrides; freeze actual defaults using an unreleased preflight container |
| Controller/client/monitor | CPUs 0,1 as V18 off procedure |
| Warmup/measurement | 20 s / 60 s; complete drain and metrics reset between them |
| Arrival schedule | V18 exact 6,793-position schedule; low 56.605/s for 5 s, high 169.815/s for 5 s, repeated six times; mean 113.21/s |
| Client | Exact retained binary; concurrency=512; request timeout=5 s; existing HTTP timing capture |
| Environment | New sealed idle temperature/power baseline; V18 settling and quiet-host checks |

The global original-binary hash is
`b7d249454d5477ffa0ade7cf1d90ba0eee8157ee166bb6e3f71d4cf912400efd`;
implementation must verify it against retained provenance rather than trust this
text alone. The frozen generation-04 original image is the authority for loading.
Do not change paths/loading between A/B/C to resolve V17's image question here.

Preserve V18's minimum 600 s initial settle and stable 60 s window, its per-trial
settling/cooling rules, power checks, bounded timeouts and exact effective resource
checks. Absence of an explicit Docker PID limit does not mean `pids.max=max`;
generation-04 observed 18,088. Re-observe and freeze the current default before
launch; reject an unexpected difference rather than forcing it to that value.

Do not align trials by wall clock modulo 100 ms or claim matched quota phase.
Identical offered offsets do not fix the cgroup's release phase. Record existing
clock anchors and launch brackets; report completion-waveform phase as exploratory.
This batch tests repeatability through A/B rather than silently selecting favorable
phase alignments or adding a phase measurement treatment.

## Outcomes and accounting, declared before collection

**Primary:** successful client responses completed by 500 ms from scheduled offer,
divided by all offers. Rejections, dropped/missed arrivals, errors, timeouts and
late responses remain in the denominator. The performance outcome can be negative
without making a technically complete trial invalid.

**Guardrails:** timely success at 1,000 ms, failure fraction, successful-response
p99, service CPU microseconds per completed computation, all-offer outcome counts
and drain throughput. Report client/monitor host costs separately where available.
Missing/nonfinite p99 or zero completed work means the guardrail cannot pass.

**Mechanism descriptions:** completion-to-resume mean/p50/p90/p99 and fraction
over 50 ms; all-offer fraction of certain computation-before/handler-after 500 ms
crossings; crossing count with at least 50 ms completion margin; certain computation
after deadline; explicit clock ambiguities; queue, computation wall and entry
intervals; strict interior starts/completions by other jobs; logical backlog peaks
and areas. Report low/high phase, all ten offered seconds and all six cycles.

Use direct client/server bounded clocks and the same unit-slope monotonic assumption
as the offline review. Stage timestamps remain existing observations. The new
analyzer must support unsuccessful, canceled and missing-worker/handler outcomes;
it must not inherit the offline script's assumption that all V18 requests succeeded.
Missing markers are unobserved, not zero waiting. Keep broader uncertainty bounds
when a mapping is unavailable; do not manufacture classification.

For each block compute C minus mean(A,B) for fractions and per-trial summaries.
For ratios use C divided by mean(A,B). Also report C versus A and C versus B
separately; a gain must not depend entirely on choosing one duplicate baseline.
Do not pair per-request IDs as independent causal replications. Provide all six
block effects, median/range/sample SD, and a Student-t 95% interval for the mean
block primary effect (five degrees of freedom), labeled a small-sample summary.
No request bootstrap, optional stopping or pooling with V12/V16/V17/V18.

## Prospective decision rules

### 1. Technical completion

Require frozen inputs/configuration, exact offers and vectors within a block,
all-outcome conservation, drain and admission/computation accounting, valid clock
generations, effective CPU/resource/ancestor checks, unchanged power settings,
accepted cooling/quiet-host checks, bounded lifecycle and verified owned cleanup.
Cancellation-related missing handler timing is accounted for, not grounds to delete
failed requests. Distinguish technical capture loss from an adverse service outcome.

Retain every failed/interrupted attempt and the reason. Resume only technically
invalid trials under the frozen policy; do not rerun valid unfavorable outcomes.
If a block is interrupted or an arrival vector changes, preserve it, flag the
block and do not mix accepted trials across an environment-baseline change.

### 2. Repeatability gate

For every A/B block require absolute timely-success differences at 500 ms and
1,000 ms ≤1 percentage point, failure difference ≤0.1 point, CPU/job difference
≤5% and successful p99 difference ≤10%. These retain the existing practical
screen sizes as prospective repeatability tolerances; passing is not equivalence.

If any block fails, report every treatment effect but mark small-effect/mechanism
interpretation **inconclusive**. Stop automatic advancement. Do not solve this by
relaxing the tolerances, deleting a block, rerunning valid A/B trials or adding
publication instrumentation. The next design would address reproducibility and
launch/periodic-supply alignment, separately.

### 3. Useful worker-control signal

Proceed to independent confirmation only if the repeatability gate passes and:

- Median block C improvement at 500 ms is **at least 3 percentage points**.
- Improvement is positive in at least five of six blocks and the mean block
  effect's 95% interval is above zero. Show comparisons to both A and B.
- In every block, C loses no more than 1 point at 1,000 ms, raises failures by no
  more than 0.1 point, raises CPU/job by no more than 5%, and raises p99 by no more
  than 10%, relative to mean(A,B).

Three points is a deliberately useful discovery target (about 204 offers/trial),
larger than the ±1-point repeatability tolerance. V18's 1.85-point paired SD warns
that six blocks may still be inconclusive; this is not a promised power calculation.

Call the result consistent with reducing the observed post-computation interval
only if the median block reduction in both the >50 ms gap fraction and the
crossover/all-offer fraction is at least 50%, with reductions in five of six
blocks. Primary success must also improve: moving completion past the deadline
can reduce crossover counts while making the service worse.

Interpret other outcomes explicitly:

- Gap shrinks but primary fails: report a queue/handoff tradeoff; no useful remedy
  is demonstrated. Do not claim the original misses were recovered.
- Primary improves but gap criterion fails: configuration benefit is supported;
  the proposed post-computation explanation is not established.
- Neither changes usefully with accepted A/B: one-worker cap is insufficient;
  investigate the remaining measured intervals before proposing a new controller.
- Guardrails fail: report the cost of the gain and stop this remedy route.

Do not require all eighteen trials to be error-free to call collection complete.
Guardrails determine whether an improvement is useful, not whether evidence exists.

## Implementation work when authorized

Create separate `diagnostic/worker_control_study.py`,
`worker_control_analysis.py`, `verify_worker_control.py`,
`start_worker_control.sh` and meaningful guard/accounting tests. A separate helper
may encapsulate preparation/configuration. Avoid modifying frozen V18 helpers.
These are proposed names, not files that already exist.

The runner should expose prepare, verify-preparation, qualify, start, resume,
status, stop, analyze and verify-completion. Preparation seals protocol, original
assets, actual resource defaults, arrival schedule, matrix and analyzer sources.
Qualification uses one full-duration A and one full-duration C rehearsal to check
startup/resource/accounting/drain and operational capacity; do not reuse them as
discovery trials or screen/select treatment benefit from their timings.

Use normal-user orchestration and the original FIFO gate through Docker. With no
BPF attachment, implement no new root tracing supervisor and request no tracing
privileges. Preserve the same off-arm lifecycle/monitoring behavior for every arm.
The implementation must verify the user's Docker access rather than assume it.

Verification before declaring the launcher ready:

1. Source/binary/image/client/gate provenance and complete six-permutation matrix.
2. Boundary tests for deadlines, unsuccessful offers, late drain, cancellations,
   duplicate/missing IDs, invalid clock brackets and CPU-counter accounting.
3. Meaningful lifecycle tests for changed resources, changed source/seal,
   interruption/resume, owned cleanup, and stop refusing a reused PID identity.
4. Unprivileged functional HTTP preflights for workers=1/4 using existing binary,
   verifying actual service settings and unchanged resource contract. These are
   compatibility tests, not accepted performance data.
5. Independent offline raw replay, export/seal tamper rejection and decision-rule
   examples that include adverse outcomes and inconclusive A/B.

After implementation and qualification, provide the exact external-terminal
launch command. Measurement requires fully quitting the desktop app, as before.
Do not automatically launch performance from the implementation session or ask
the user to approve an unfinished design.

## After V19

If the worker cap passes the useful-signal rules, freeze the winning setting and
confirm it in a new six-pair session against the original four-worker baseline,
with a separately declared repeatability/precision policy. Do not reuse discovery
data as confirmation. Then test GOMAXPROCS=2 with the selected worker setting as a
distinct question about execution parallelism; the current batch holds it fixed.

If one worker is an adequate existing control, state that plainly and postpone
new completion-priority algorithms. If a material residual remains, the next
intervention must distinguish a named publication/execution ambiguity and be
compared against this static baseline. It still needs binary/measurement controls.
No readiness claim follows automatically from either result.

Defer another kernel-cost batch, publication timestamps, runtime patches,
acknowledgment policies, large period/arrival sweeps and cross-runtime work until
the first decision is available. V18's successful functional fixtures do not need
repeating; its failed practical screen stays in the record.

## Expected time and deliverables

V18 accepted trial starts were about 3.2–3.7 minutes apart, including setup and
settling. Eighteen trials, two qualification rehearsals and the initial ten-minute
settle suggest **roughly 75–100 minutes of quiet-machine measurement**, with longer
cooling extending that time. This excludes implementation and functional
verification; do not give a guaranteed finish time before preparation.

Deliver the new frozen protocol/preparation report, ready external launcher,
all eighteen raw trial records, independent completion verification, block-level
effect table, explicit stop/advance decision and offered-phase stage plots.
The endpoint is an answer to the worker-control question, even if negative or
inconclusive; it is not a promise to find a scheduler bug in the next iteration.
