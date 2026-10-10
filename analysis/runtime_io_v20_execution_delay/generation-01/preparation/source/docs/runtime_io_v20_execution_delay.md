# V20 execution-delay protocol

Implemented from the [approved proposal](runtime_io_v20_execution_delay_plan.md),
2026-10-05. This protocol and the proposal are frozen by preparation before new
measurements. V20 is an exploratory comparison of known controls. It does not
establish a novel scheduler mechanism, exact handler readiness, or per-request
quota availability.

## Four-arm experiment

All arms use **one worker, GOMAXPROCS=1**, the exact original packaged Go 1.26.1
service/image, queue 128, 44,000 SHA iterations, service CPUs 2/4, controller/client
CPUs 0/1, zero burst credits and historical memory/PID defaults. No server rebuild,
new marker, acknowledgement policy, runtime tracing, kernel attachment or root
supervisor is used. The existing `WORKER_YIELD` flag is explicitly set in every arm.

| Arm | Quota / period, microseconds | WORKER_YIELD |
|---|---|---|
| A | 50000 / 100000 | false |
| B | 50000 / 100000 | true |
| C | 10000 / 20000 | false |
| D | 10000 / 20000 | true |

Both resource levels allow 0.5 CPU on average; their temporal resource contracts
are different. Affinity, uncapped ancestors, namespace offsets, actual image and
executed binary, quota/period and default memory/PID settings are verified. The
live guard rechecks the limits at every observation. Period changes must not be
called an unchanged quota contract or a measurement of remaining CPU budget.

Four independent blocks use A B C D; B A D C; C D A B; D C B A. Each arm occupies
each position once and every pair occurs in each order twice: **16 fresh trials**.
Blocks, not requests, are replications. There is no A/A arm; the V19 A/A screen
does not establish V20 repeatability or equivalence.

Each trial has a fresh container/client, 20-second warmup and full drain, metrics
reset, then the exact retained 60-second offered vector and full drain. There are
6,793 offers, 56.605/169.815 rps for alternating 5-second halves, mean 113.21 rps,
concurrency 512, timeout 5 seconds. Both factors use the same clock/endpoint/monitor
sequence. Initial idle is at least 600 seconds; trial cooling has stable windows
of at least 60 seconds, following the unchanged V19 thermal/power/quiet policy.

## Preparation and qualification

Preparation preserves all 105 V19-frozen source paths and adds only V20 files.
It snapshots source, protocol, original image inspection, assets, offered vector,
original build/source evidence for publication ordering, tests and resource checks.
Four unreleased preflight containers verify both quota contracts and startup;
no service workload is released in these checks.

Six two-second HTTP checks use all four arms plus queued cancellation at A and D.
Normal controls require successful accounting for all 114 offers. Cancellation
uses only functional demand 226.42 rps (453 offers) and a 1 ms timeout, requiring
failures, completed computations and missing handler records. Functional load is
never used for qualification/discovery. All owned containers/cgroups are removed.

Four full-duration quiet-host rehearsals, one per arm, qualify startup, capacity,
clock/accounting, monitoring and drain. Require no client drops or missed arrivals
and dispatch-lag p99 at most 2 ms. Do not screen favorable service latency, choose
successful treatment outcomes, or count rehearsals as discovery replications.
Capacity failure is preserved and requires a new generation after correction.

## Accounting and publication bounds

Every offer is retained, including drops, errors, timeouts, rejections, late
responses and work after cancellation. Missing client rows are inferred as drops
only with exact native ID/counter conservation; inferred schedule offsets are
labeled. Missing handler timing is unknown. Successful responses require all
stock server markers, valid durations and conserved per-request stage budgets.
Direct client/server clock brackets retain uncertainty and the inherited 1 ms
maximum width; six host/server endpoint anchors are also checked.

The original sole worker sends a buffered reply before its next job starts.
Thus the next start bounds prior publication from above. Sorted computation
intervals must not overlap. The prepared source hash is checked against its
original build manifest, whose image matches the actual frozen service image.
No such proof is allowed for multiple workers.

The bound is informative for waiting only if that next start precedes handler
resume. Otherwise, or for the last job, it remains uninformative/unknown, not
zero. Actual publication and runnable readiness are unobserved. Bound-supported
available-result deadline crossings and publication-to-resume lower bounds are
supporting descriptions, never primary treatment comparisons conditioned on
post-treatment misses. Every row records its bound status and available coverage.

The mechanism primary is **whole-offer completion-to-resume mean**. It is available
only if all offered requests have observed completion/resume intervals. With any
missing gap, report the observed-only distribution, coverage and missing count,
but do not claim a whole-cohort mean or impute missing intervals. The >50 ms
observed count/all-offer fraction is a lower bound when coverage is incomplete.
Zero baseline mean cannot support a relative reduction. Poor performance remains
a valid measured result and is not a reason to rerun a trial.

## Contrasts, uncertainty and decisions

Within each block compute B−A (yield at 100 ms), D−C (yield at 20 ms), C−A (period
without yield), D−B (period with yield), and D−A (combined, supporting). Absolute
interaction is (D−C)−(B−A), including gap mean/p99 and timely success; positive gap
interaction indicates less reduction than an additive absolute-gap prediction.
Report all four block effects, median, mean, range, sample SD and a Student-t
95% mean interval with 3 degrees of freedom, labeled an exploratory summary.
No request bootstrap, optional stopping, pooling with old studies or automatic
confirmation follows a signal.

A contrast passes the proposed descriptive signal only with four assessable
whole-cohort means: median gap-mean reduction at least 25%, reduction positive
in at least three blocks, and median all-offer 500 ms success change nonnegative
relative to that contrast's baseline. Gap p99, distribution, >50 ms fraction and
bounded deadline crossings remain supporting outcomes. No CI significance gate
or new primary metric is chosen after observing results.

In **every block**, B, C and D must pass the proposed guardrails against A: loss
at 1,000 ms at most 1 pp, failure increase at most 0.1 pp, CPU/job increase at
most 5%, successful p99 increase at most 10%. Unknown/nonfinite guard metrics
cannot pass. All effects stay reported even when guards fail.

Decision precedence: incomplete evidence; interrupted blocks; guardrail tradeoff;
unassessable whole-cohort gap metric; then descriptive factor branches. Yield at
100 ms is the execution-opportunity screen. Temporal supply requires period
signals both with and without yield. Both passing gives a mixed signal. Signals
only at one factor level or only for the combination are explicitly conditional
and require review. None passing means no clear execution-delay signal.
The complete factorial comparison must have assessable contrasts before an
interpretation is eligible; raw individual screens are still displayed.

These are scoped responses to interventions, not exclusive causal attribution.
Yielding can change admission and CPU use; period changes can affect capacity and
scheduling. Continue to report those mediators. No positive result proves a Go
scheduler defect or instantaneous quota pause.

## Lifecycle and launch

Normal-user Docker orchestration uses a unique ownership nonce, immutable container
ID cleanup, PID/start-time identity checks, an independent bounded watchdog and
sealed cleanup receipts. An intervention invalidates its attempt. Technically
failed/interrupted attempts are preserved; accepted adverse trials are never
replaced. Interrupted discovery blocks suppress interpretation even after resume.
Resuming repeats initial idle against the sealed environmental baseline.

After preparation, fully quit Codex/ChatGPT and run externally as the normal user:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_execution_delay.sh run \
  "$PWD/analysis/runtime_io_v20_execution_delay/generation-01"
```

`run` performs four rehearsals before the sixteen trials, then exports request,
trial, phase and block CSVs, JSON/Markdown reports, PNG/SVG plots and independently
verifies raw completion. Preparation alone does not mean qualification passed.
No sudo is required. Allow roughly 75–100 minutes, longer when cooling requires it.

```bash
python3 diagnostic/execution_delay_study.py status \
  --directory "$PWD/analysis/runtime_io_v20_execution_delay/generation-01"
python3 diagnostic/execution_delay_study.py verify-completion \
  --directory "$PWD/analysis/runtime_io_v20_execution_delay/generation-01"
```

Use `resume` after reviewing retained interruption evidence; use `stop` for bounded
owned cleanup. `status`/`watch` read small progress markers rather than hashing or
replaying data during measurement. Independent offline verification never calls
Docker or the runner. A failed generation remains preserved; fixes prepare a new
generation and require the corresponding launch directory.
