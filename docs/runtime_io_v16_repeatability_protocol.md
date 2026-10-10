# V16: original-image repeatability and exact-source rebuild

Prepared 2026-10-04 after the [V15 review](../analysis/runtime_io_v15_marker_review/report.md).
Stay in Step 1. V15's marker and zero-call rebuild comparisons failed; clock count was not monotonic.
This pilot checks whether a trustworthy baseline can be reproduced. It does not fix or localize the
remaining post-computation misses. Preserve all V12–V15 evidence and margins.

## Question and arms

Can the exact legacy service repeat its deadline outcomes under the same procedure, and can an
exact-source rebuild reproduce it without V15's extra health/metrics metadata?

| Runner label | Service |
|---|---|
| legacy_a | Exact retained V12 service image |
| legacy_b | The identical V12 image ID, under a second runner label |
| exact_rebuild | Frozen prepared V12 service source and Dockerfile, copied verbatim and rebuilt without cache |

No new service code, observer fields, runtime dispatch, recorder or metadata is added. Labels occur
only in runner/output paths. All arms use identical service environment variables, HTTP control-plane
calls, fresh-container lifecycle, monitoring, client and drain procedures. Image hashes are frozen;
the independently rebuilt image may have the same ID as the original. That is an audit result,
not grounds for replacing or dropping an arm. Container names differ by trial as in the retained runner.

The build uses the retained Go 1.26.1 compiler image
`sha256:2389ebfa5b7f43eeafbd6be0c3700cc46690ef842ad962f6c5bd6be49ed82039`, the original module,
tests, `/src` work directory, `CGO_ENABLED=0`, `go build -trimpath`, scratch image and labels.
`docker build --no-cache --pull=false --network none` forces a fresh offline compile using the original
Dockerfile. Do not change build flags to manufacture identity. Preserve full binary hashes, build IDs,
`go version -m`, main-package disassembly, image configuration and source hashes. Audit the retained
V15 metadata-only zero-call binary as historical evidence; it is not a performance arm. Static identity
alone cannot establish equal timing or explain V15's gap.

## Four matched three-arm blocks: 12 trials

Orders are declared before collection:

1. legacy_a, legacy_b, exact_rebuild
2. exact_rebuild, legacy_b, legacy_a
3. legacy_b, exact_rebuild, legacy_a
4. legacy_a, exact_rebuild, legacy_b

Every pair appears twice in each relative order. These deterministic orders are not randomized and
do not fully balance position or immediate carryover. Four blocks are a small discovery/precision
pilot, not an equivalence study. Collect A/A and rebuilding in the same blocks to avoid a different
session becoming a confound; interpret A/A first. If A/A fails, rebuild attribution remains unresolved.

Fixed workload: GOMAXPROCS=1, four workers, queue128, 44,000 SHA iterations/job; 50 ms quota per
100 ms period, zero burst credits, uncapped ancestors; retained server/client affinity. Exact V12 client.
Identical offered IDs/scheduled offsets within each block, deterministic five-second low/high phases
at 56.605/169.815 requests/s, mean 113.21/s. Each trial: at least 60 seconds settling, 20 seconds
warmup, 60 seconds offered arrivals, five-second timeout and full worker/client/handler drain.

## Outcomes, precision and decisions

Primary: successful responses within 500 ms of scheduled arrival divided by **all offered IDs**.
Guardrails: 1,000 ms timely success, failure fraction, CPU/job, successful end-to-end p99. Retain failed,
rejected, cancelled, timed-out, late and drained requests, missing events and clock uncertainty.

Three declared contrasts, with signed paired deltas for every block:

1. legacy_a → legacy_b: same-image procedural repeatability.
2. legacy_a → exact_rebuild: exact-source rebuild comparison.
3. legacy_b → exact_rebuild: rebuild comparison against the second original-image run.

Unchanged practical margins, **every block**: absolute timely delta ≤1 percentage point at both
deadlines; failure delta ≤0.1 point; CPU/job ±5%; successful p99 ±10%. Missing or non-finite
guardrails fail. Report each contrast's median, minimum, maximum and sample standard deviation
across blocks. These summaries inform a separately designed precision study if needed; the number
of requests does not increase the replication count. No pooled-request confidence intervals or
statistical-equivalence claim. Median/range cannot hide an out-of-margin block.

| Result | Research decision |
|---|---|
| A/A outside margins | Review host/order/lifecycle variation; do not attribute rebuilding or qualify markers |
| A/A within margins; either rebuild contrast outside | Investigate actual binary/container/build differences before adding observers |
| All three within margins | Baseline discovery result for manual review; prepare the smallest persistent recorder only if justified |

If full rebuilt binary and image configuration are identical, an apparent rebuild penalty cannot be
attributed to changed binary bytes; evaluate repeatability/lifecycle/environment instead. If identity
and discovery repeatability hold, V15's extra metadata/generated-code differences remain candidates,
not established causes. Do not infer pure per-clock costs. The pilot does not add publication brackets,
runnable-readiness events or request-level throttling intervals. No scheduler remedy, worker matrix,
larger precision batch or recorder experiment is automatically launched.

## Environment, acceptance and preservation

Establish this session's own baseline after at least ten minutes quiet idle and an accepted stable
60-second window. Retain ±3°C baseline tolerance, ≤2°C window range, ≤1°C/min absolute slope,
existing timeout, AC power, Balanced profile, lid open and quiet-host acceptance. Keep monitor cost
identical across arms. These gates do not prove hardware thermal equivalence. No pooling with V14/V15
as matched trials, copied baseline or silent rebaseline on resume.

Freeze source/protocol/analysis, original prepared source, full build/audit/fixture bundle, images,
client, matrix, calibration and baseline/idle seals. Verify host/container time namespaces, actual
limits/affinities, clock generations and ≤1 ms mapping uncertainty, conservation and environment.
Raw attempts and rejected evidence remain preserved. Stop on a technical failure; do not retry
automatically, relax margins or repeat valid trials to obtain a pass. A user-triggered resume preserves
all attempts, rechecks original frozen evidence and skips accepted trials. Changed source/environment
requires explicit review and a separate session. Completed evidence verifies against frozen source
independently of later working-source edits. Seal report/CSV/JSON and retain every attempt audit.

## Preparation and collection

Preparation can run during normal desktop use. The exact rebuild executes original Go tests; six
short unquotaed HTTP fixtures cover three labels × GOMAXPROCS1/2. Fixtures check conservation,
original runtime/schema and clock joins; they are not performance measurements. No new Go code
is introduced, so an additional modified-service race suite is not required.

Build and verify:

```bash
cd /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency
python3 diagnostic/build_repeatability.py build
python3 diagnostic/repeatability_study.py verify-build
```

After saving work, start collection from a normal external terminal:

```bash
bash /home/Aditya/Desktop/Research_project/cpu-quota-tail-latency/diagnostic/start_repeatability_batch.sh
```

The launcher verifies the prepared build before closing ChatGPT/Codex, waits for shutdown, starts
the detached sleep-inhibited finite 12-trial pilot and displays temperatures, baseline, phase,
completed/12, remaining, elapsed and log path every five seconds. Closing the display leaves collection
running. Keep AC power, Balanced profile and lid open; leave the desktop app closed during collection.
Arithmetic minimum: 12×(60+20+60) + 600 seconds = **38 minutes**, excluding startup, drains,
extended cooling and analysis. A **1–2 hour quiet window** is a planning allowance, not a timing guarantee.

```bash
python3 diagnostic/repeatability_study.py status
python3 diagnostic/repeatability_study.py watch
python3 diagnostic/repeatability_study.py stop
python3 diagnostic/repeatability_study.py verify-completion
```

Stop checks the worker/launch identity before TERM and preserves completed trials. Rerunning the
launcher resumes valid remaining trials with the same frozen baseline/build; it never duplicates
an active study. Results: `results/diagnostic/runtime-io-v16-repeatability-1/session/analysis/`
contains `report.md`, `trials.csv`, `requests.csv`, `repeatability_screen.json`, `validation.json`
and `attempt_audit.json`; root `completion.json` binds analysis, environment and raw attempt seals.
