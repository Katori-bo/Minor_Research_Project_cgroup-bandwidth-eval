# V19 worker-control execution protocol

Implemented from the [V19 proposal](runtime_io_v19_plan.md), 2026-10-05.
This document is part of the preparation source seal. The proposal remains the
historical preimplementation plan. No discovery outcome has been observed.

## Experiment

Six blocks contain `four_a`, `four_b`, `one` in orders ABC, BCA, CAB, ACB, CBA,
BAC. Runtime execution parallelism remains GOMAXPROCS=1. Only CPU-worker count
changes (4/4/1). The original packaged V18 image/server, load generator and FIFO
gate are reused. No service build, extra observer marker, BPF collector, runtime
trace or root supervisor is used. Each trial has fresh service/client instances.

The resource contract remains CPUs2,4, 50,000/100,000 microseconds, zero burst,
queue128, 44,000 iterations. Controller/client/monitor/watchdog use CPUs0,1.
Historical memory/PID overrides stay omitted; current effective defaults must
match the retained generation-04 contract and are observed in an unreleased
preflight container. Ancestors are uncapped. The gate mount is the sole mount.

Twenty-second warmup is drained, metrics reset, then 60 seconds of the exact
retained bursty arrival vector are measured through full drain: 6,793 offers,
low56.605/high169.815 per second, 5 seconds each, mean113.21. Concurrency512 and
5-second request timeout remain. All arms use the same endpoint/monitor sequence.
Initial cooling is at least600 seconds; per-trial stable windows are at least60
seconds. Existing V18 thermal/power/quiet-host policy is inherited without changes.

## Preparation and functional verification

Preparation snapshots the exact fixed 95-source V18 set plus the new V19 files,
assets, original image inspection, offered schedule, resource defaults and tests.
Every old source hash must match generation-04. Adding new files is permitted.
The original executable is copied from the actual Docker image and hashed.

Three two-second HTTP checks exercise four workers, one worker and one worker
with a1 ms cancellation timeout. These allow normal desktop activity, are clearly
marked functional and never enter discovery or qualification. All-offer accounting
and existing clocks are exercised; canceled handlers may legitimately lack resume
records while their admitted jobs still finish. The two success controls require
all successful responses. The cancellation control requires failures, completed
computations and missing handler records. All owned containers/cgroups are removed.

Normal users cannot necessarily dereference a root-owned service's `/proc/exe`.
Each attempt therefore hashes Docker's copy of its actual `/server` before FIFO
release, verifies the frozen gate and original image/mount/command, then requires
the same PID/start-time identity to exec into `server` and report the exact service
settings. This is explicit transitive executable verification through Docker and
the verified gate; it adds no service code, process or mount. Copies remain sealed.

## Independent full-duration qualification

One `four_a` and one `one` rehearsal follow the full quiet-host procedure and all
technical evidence gates. They qualify startup/resources, accounting, clock,
drain and client operational capacity, without screening treatment performance.
Require no client-dropped or missed arrivals and dispatch-lag p99≤2 ms. Rehearsals
never count as discovery trials. A capacity failure stays sealed and requires a
new generation; valid rehearsals are not rerun to obtain preferred timings.

`run` combines qualification and18 discovery trials in one foreground session
after the initial cooling. A fresh resumed invocation repeats the initial idle
settle against its sealed baseline. No accepted trial is replaced or rerun.

## Accounting and decisions

The primary is successful completion by500 ms from scheduled offer / all offers.
One-second timely success, failures, successful p99, CPU/job and drain throughput
are guardrails. Late successes, rejections, errors, timeouts and client drops are
retained. A missing client row is represented as a dropped offer only when exact
ID/total conservation matches the client's dropped counter. Its scheduled offset
is explicitly inferred from the frozen vector; no dispatch, latency or server
marker is invented. Missed arrivals already occur in the offered denominator and
are reported without double counting. Missing handler records for canceled offers
remain unknown. Unsuccessful outcomes never become successful deadline crossings.

Direct client/server clock intersections retain uncertainty, with six distinct
anchors and a single generation; mapping width greater than1 ms or contradictory
ordering is technically invalid, as in the reused V18 mapping. Entry, worker,
handler, durations and per-request end-to-end budget are checked. The original
entry-exit marker precedes the separate handler-exit marker; they are not equated.
Backlogs are marker-defined intervals, not exact channel occupancy/runnable counts.

Each block reports C−mean(A,B), C−A and C−B; CPU and p99 ratios use the arithmetic
mean of baseline per-trial metrics. Six blocks are the independent units. Retain
mean/median/range/SD and the Student-t95% mean interval with5 degrees of freedom.
No request bootstrap or pooling with earlier studies.

Every A/B block must satisfy the planned ±1 pp timely500/1000, ±0.1 pp failure,
±5% CPU and ±10% p99 screens. Failure means inconclusive repeatability, while all
treatment effects remain reported. Missing/nonfinite ratio metrics cannot pass.

Useful signal requires median500 ms gain≥3 pp, positive in≥5/6 blocks, positive
lower mean95% interval, and positive C−A and C−B in≥5/6 each (the explicit check
that benefit does not depend on choosing one duplicate baseline). All blocks must
lose≤1 pp at1000 ms, increase failures≤0.1 pp, CPU/job≤5%, and p99≤10%.

The post-computation signal additionally requires median relative reductions≥50%
in both >50 ms gap/all-offer fraction and certain crossover/all-offer fraction,
with reductions in≥5/6 blocks each. Zero baseline counts make that secondary
reduction unassessable, never an invented100% reduction. Gap improvement alone
does not advance if the primary or guardrails fail. Publication/readiness and
scheduler-only attribution remain unobserved in every decision branch.

Interruptions are retained and blocks flagged. An interrupted discovery block
suppresses automatic confirmation even if all accepted trials are later present;
its effects remain reported as `inconclusive_interrupted_blocks`. Environment
baseline changes are rejected; a new session cannot borrow accepted trials.
Only technically invalid attempts can be resumed. A complete poor-performance
trial is valid evidence. Zero successful responses or completed computations can
make guardrails fail without hiding the trial or pretending collection is incomplete.

## Bounded ownership and cleanup

Normal-user orchestration owns only uniquely labeled V19 containers. Cleanup
checks the nonce label and uses the immutable Docker ID after inspection. A
separate normal-user watchdog covers the active service lifecycle (360 seconds)
and owner-process death, independently of the collector loop. It removes only
the owned container and records invalidation. Controller signals stop client and
monitor, finalize logs, remove the container and verify cgroup disappearance.
No tracing resources are created. Stop checks owner UID and PID start ticks and
refuses a reused PID. Concurrent foreground workers are rejected by a file lock.

Full verification is offline: raw trial replay, frozen inputs/configuration,
environment and qualification, exported requests/trials/blocks/phases, every
interrupted attempt, ownership/cleanup records and the prospective decision.
Status/watch read small markers and never hash completed captures during a run.

## Commands

Preparation can be run with the desktop app open (Docker and local HTTP access
are required):

```bash
python3 diagnostic/worker_control_study.py prepare \
  --directory "$PWD/analysis/runtime_io_v19_worker_control/generation-01"
```

After preparation verifies, **fully quit Codex/ChatGPT** and run from an external
terminal as the normal user:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
bash diagnostic/start_worker_control.sh run \
  "$PWD/analysis/runtime_io_v19_worker_control/generation-01"
```

This performs full-duration qualification, then the18 trials only if qualification
passes, then analysis and independent completion verification. It needs Docker
access and a sleep inhibitor, without sudo or kernel tracing. Keep the app closed
until completion. Expected quiet measurement time is roughly75–100 minutes,
subject to cooling. `qualify` and `start` can also be run separately; each new
foreground invocation includes initial idle settling. After interruption use
`qualify` for incomplete rehearsal qualification or `resume` for discovery.

```bash
python3 diagnostic/worker_control_study.py status --directory DIRECTORY
python3 diagnostic/worker_control_study.py stop --directory DIRECTORY
python3 diagnostic/worker_control_study.py analyze --directory DIRECTORY
python3 diagnostic/worker_control_study.py verify-completion --directory DIRECTORY
```

`DIRECTORY` must be a direct generation directory under
`analysis/runtime_io_v19_worker_control`. Preserve failed generations. New source,
protocol, baseline or resource defaults require fresh preparation. The independent
verifier requires the loaded Python analysis implementation to match its snapshot.
