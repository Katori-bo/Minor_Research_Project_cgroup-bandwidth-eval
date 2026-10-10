# Native gzip qualification implementation

This implements the fixed candidate selected in
docs/runtime_io_gzip_candidate_qualification_plan_20261009.md. The selection
seal, all imgproxy results and V30/V31 inputs remain unchanged. This bundle is
engineering apparatus, not scientific calibration or held-out prediction.

Two C wrappers are compiled from one source with OBSERVED=0 or 1. Both have the
same bounded FIFO, single job worker, fresh unchanged gzip executable, output
drain/reap/full-response path and mandatory child-identity audit. Reference
disables extra per-request timestamps, event storage and timing headers; it is
a reference research wrapper, not a stock production web server. Native gzip
1.15 compresses the pinned 1 MiB corpus at level 6 with -n, -c, and file input.

Each forked child waits on a private pipe while its parent verifies actual PID,
start ticks, one-thread state, CPU-2 affinity and same cgroup. A pidfd identifies
that unreaped child. After a release byte, the child uses only async-signal-safe
operations and execve with the fixed executable, arguments and minimal locale
environment. A close-on-exec proof pipe distinguishes an exec failure; bounded
stdout must drain, the child must exit zero and be reaped, and the entire gzip
body must be written before the worker can begin another job. Native job timeout
is 10 seconds; failure kills only the pidfd-identified or unreaped known child.
The independent outer watchdog removes the owned immutable container and
process namespace on parent death or the 120-second service deadline.

Both arms retain at most 1,024 common native lifecycle records. Only observed
retains stage times: enqueue, acquisition, fork before/after, drain, reap,
response before/after and release. Queue time excludes HTTP/kernel input wait.
Process time includes spawn, identity gate, exec, compression, pipes and reap;
worker hold also includes response writing. This does not isolate deflate CPU
time. Whole-cgroup CPU counters include the C dispatcher, worker and native child.

Gzip runs as the launching user's resolved numeric UID:GID, sealed in the
protocol, allowing host-side inspection of actual executable/thread identities.
The packaged binary paths, input, loader and libc are immutable in a read-only
scratch runtime. An initial single-thread FIFO gate lets the supervisor verify
actual resource limits and packaged server/gzip hashes before execution.
Host supervision permits exactly the persistent wrapper and at most one direct
native child, handles child exec/reap races, rejects unexpected executables,
parents or thread masks, and checks CPU 2 and immutable resource settings.
It does not call the old two-CPU or sole-PID measurement helpers.

Use the sealed candidate's limits: 25 ms/100 ms quota, burst zero, CPU 2,
memory 512 MiB, PID limit 128; control/client CPUs 0,1; FIFO 128; in-flight cap 32.
All HTTP jobs are fixed GET requests and fully read responses, with no cached
compressed body. Input page-cache warmth is allowed; fresh gzip execution still
occurs on every job. The Go client uses a fresh schema, gzip content type and
2 MiB cap, receives the full body before completion timestamp, then hashes it.
No timing-counter sampler is added.

In preparation, two services each execute one decoded-output check, 25 warmup
and 25 diagnostic offers at 5 req/s. The same native-child scan, pre/post counters,
client validation, mandatory audit, event export, raw joins, classification,
cleanup and offline replay used in the pilot all execute. Preparation with Codex
open records domain exits but never qualifies cost or the scientific domain.
Missing outcomes, native identity/reap failures and incorrect output still fail
preparation. No service retries or replacement are permitted. Total preparation
budget 300 seconds, including 120 reserved for cleanup; active service 120 seconds.

Every cohort confirms its worker/native jobs have drained with the common audit
endpoint. The measurement CPU window ends after this one common idle/audit
confirmation and before the final raw audit/event export. This endpoint adds
common service work to both arms' accounting, which is included in the measured
cost endpoints. Guard checks themselves use host procfs rather than polling
service HTTP during the workload. Raw records and counters precede all domain
classification. Best-effort export also runs on early failure before cleanup,
and inability to export is retained explicitly.

External qualification is twelve services, six pairs with alternating
reference-observed / observed-reference orders, ten seconds settling per
service, 25 warmup and 200 measurement offers at 5 req/s. Preserve all outcomes
and enforce zero measurement throttled periods, all successful matching full
bodies/IDs, dispatch p99 <=2 ms/max <=10 ms, and observed queue<=100 us for
>=99% of offers. Any gate failure stops qualification. No resume/overwrite/retry.
Overall cap 1,200 seconds, including 120 for cleanup, and 120 seconds per service.

Both CPU per offered request and median offered-to-full-body relative observer
cost use six pairs and upper bound mean+2.571*sample_sd/sqrt(6) <=5%. Replay
reconstructs all native audits, joins, counters, runtime identities, cleanup and
paired confidence bounds. Even a passing engineering pilot leaves scientific
collection disabled pending model/stage review and fresh sealed calibration.

Launch externally: bash diagnostic/start_gzip_qualification.sh.
Evidence: analysis/runtime_io_gzip_qualification/generation-01/.
Offline successful/incomplete-cost-pilot replay:
python3 -B diagnostic/gzip_qualify.py replay.
