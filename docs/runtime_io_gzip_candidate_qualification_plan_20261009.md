# Fresh GNU gzip candidate and qualification plan

Date: 2026-10-09. Status: candidate selection and fixed-input correctness;
no service implementation, external performance qualification, calibration or
held-out validation. This plan is independent of the stopped imgproxy candidates.
Their binaries, failed trials, code defect and diagnostic records remain intact.
V30/V31's sealed evidence and confirmed claims remain unchanged.

## Selection and permitted claim

Select GNU gzip 1.15 as the next application operation: compress a fixed 1 MiB
structured-text corpus using `gzip -n -6 -c -- /input/corpus.ndjson`. Keep the
native application executable unchanged. It is a finite compression job with a
clear process-completion boundary. A new, small C HTTP wrapper will queue and
serialize jobs; it is research apparatus, not an existing production server.
The intent is to test compression workload and execution-stack transfer from the
Go/SHA service on the same host. There is no independent-team, hardware-transfer
or off-the-shelf HTTP-application replication claim.

This selection uses code/measurement suitability, not observed model advantage
or successful quota behavior. Native execution and process completion simplify
the audit question, but do not guarantee zero throttling or stable latencies.
Do not infer that imgproxy's prior throttle was caused by GC, native parallelism,
its observer, or periodic memory freeing. Those causes were not established.

References: GNU project's description https://www.gnu.org/software/gzip/;
option semantics https://www.gnu.org/s/gzip/manual/gzip.html;
maintainer's 1.15 announcement
https://www.mail-archive.com/info-gnu%40gnu.org/msg03570.html.
Release commit: e6263160768c73f6117f3c1de78291a60f2cb796.
Source archive: https://ftp.gnu.org/gnu/gzip/gzip-1.15.tar.xz.
Published SHA256: 9aa0cc780dec156b8282844833b342ab7cb08c25d2cd9a1869cdd0df31deff48.

The retained installed executable is Arch Linux gzip 1.15-1. Preserve its version,
package provenance and actual binary hash; package metadata alone does not prove
source-reproducible build identity. Archive the upstream source for inspection.
Freeze the executable's loader/libc closure and container image before service
qualification; do not change the host installation. Source audit must examine
the selected compression path; absence of a thread symbol alone is not a full
proof of behavior. The CPU-2 cgroup restriction applies to all service processes.

## Fixed operation before any timing

Use the generator in diagnostic/gzip_candidate_prepare.py. It creates 4,096
ASCII NDJSON records of exactly 256 bytes each, including whitespace padding
and LF. Record fields contain public synthetic metrics and deterministic
xorshift32 values, seed 0x6d2b79f5, ten 8-hex words per record. No private corpus
or user file is used. Pin the generator and generated input hashes. Fix level 6,
input size and contents, native version, file input and output cap before any
candidate timing. Do not run size/level/rate searches to find favorable results.

Selection-stage correctness permits exactly three native calls, without retries:
two complete compressions and one native decompression. Confirm matching gzip
bytes, omitted name/timestamp metadata, native and independent Python round-trip
equality, all record IDs and framing, zero errors and <=2 MiB output. These calls
have 15-second process timeouts and record no duration, CPU-cost or quota outcomes.
They are not qualification, capacity calibration, or scientific evidence.

## New service contract: implementation required

Build an auditable C service, not a modified copy of the frozen imgproxy runner.
One network dispatcher parses bounded local HTTP requests and places IDs/sockets
in a preallocated bounded FIFO (capacity 128). One worker executes one gzip job
at a time, drains bounded stdout, reaps the child, writes the entire HTTP body,
then releases the worker. Use the fixed packaged executable and arguments;
no client-chosen paths, flags, commands or payloads. Every accepted job must
perform compression; no cached compressed response. Read-only input page-cache
warmth is permitted and must be documented. Do not add a long-lived Go/Python
process to the measured service cgroup. A subprocess-per-job design includes
spawn/exec, pipes, file reading, process exit and response writing in its contract.
It does not measure an isolated in-memory deflate kernel.

Define server milestones with one monotonic clock: full request parsed/enqueued,
worker acquired, spawn-before/after, compression-output drained, child reaped,
response-write-before/after and worker release. Queue wait is FIFO enqueue to
worker acquisition; it excludes kernel/HTTP input waiting. Report that boundary
explicitly and preserve client residual dependence in later paired calibration.
Never label process wall time as CPU demand. Whole-cgroup counters include both
wrapper and children. Worker hold includes the full job and response lifecycle.

The reference arm has the identical FIFO, execution and response semantics with
per-request timing observation disabled. The observed arm adds only bounded,
preallocated events and ID-linked queue/process timing headers. GNU gzip itself
remains unchanged in both arms. Export only after traffic drains. Retain raw
events and counters before classification, including failed/overflowed records.
Export completeness: one correctness job, 25 warmup jobs and 200 measurement
jobs = 226 records in a 1,024-record buffer. Header and raw durations must agree;
every native job must exit zero and every complete response must match the pinned
gzip hash. Verify gzip decompression/output correctness during preparation.

Create a fresh client or independently qualified generic client: JPEG-specific
validators are inappropriate. Complete latency ends after receipt of all bytes;
body hashing follows that timestamp. Use unique IDs and integer open-loop offers,
maximum 32 in flight, bounded drains and no replacement for drops/timeouts.
The client/supervisor run on CPUs 0,1 and outside service accounting.

The old helpers requiring CPUs 2,4 or exactly one cgroup PID cannot be copied
unchanged. The service now has a tracked native child as well as the wrapper.
Enforce CPU 2 and the same cgroup for every live parent/child thread, sole active
job, actual packaged executable identity, immutable resource settings and no
unknown child. Handle short-lived child exits without PID-reuse ambiguity and
preserve job lifecycle evidence. Keep nonce/immutable-container ownership,
separate client-session identity, finite subprocess deadlines, independently
executing owner-death/service-deadline cleanup and verified removal. Exercise
these native-child paths before external qualification; no claim follows merely
from successful compilation.

## Bounded prospective engineering qualification

Resource contract: CPU 2 only, quota 25 ms/100 ms, burst zero, memory 512 MiB,
PID limit 128. A one-CPU allowance is not exclusive host-core reservation and
does not eliminate background interference. Record uncapped ancestors and time
namespace semantics. Fresh privileged read-only observer inventory and closed
Codex/ChatGPT are required for external performance collection. Do not change
host tracing/frequency configuration or hide an active observer. No high-rate
CPU-counter sampler is added to the observer-cost pilot.

Allow at most two preparation services, one reference and one observed, without
retries. Preparation must exercise every measurement-only path: warmup, actual
parent/child affinity/cgroup checks, before/after CPU counters, complete-client
validation, event export, raw joins, domain classification, cleanup and replay.
Use one decoded output check, 25 warmup offers and 25 diagnostic offers at
5 req/s per arm; preparation with Codex open never qualifies cost or the domain.
Verify gates in failure-focused tests and preserve any preparation domain exits.
Exercise the strict resource/PID and watchdog checks on real jobs. Freeze final
sources, runtime/container identity, input/output hashes, protocol, tests and all
preparation evidence before external collection. Declare total preparation limit
300 seconds, active service limit 120 seconds and cleanup reserve 120 seconds.

External pilot: six pairs, alternating reference-observed and observed-reference
orders; twelve services maximum, no retries/resume/replacement. Ten seconds
settling before each service. Each has 25 warmup and 200 measurement offers at
5 req/s, exactly 200,000,000 ns spacing. Active-service cap 120 seconds and total
campaign cap 1,200 seconds, reserving 120 seconds for cleanup. Expected normal
path roughly 12 minutes; it is an engineering estimate, not a measured duration.

All offers must succeed with identical complete gzip output and echoed IDs.
Dispatch p99 <=2 ms and maximum <=10 ms; observed queue<=100 us for >=99% of
measurement offers; zero recorded measurement throttled periods in either arm.
Counters bracket measurement before export and include child CPU usage. A failed
gate terminates this candidate and is retained. Do not discard a terminal trial
or weaken the rule after observing it.

For both CPU microseconds per offered request and median offered-to-full-body
latency, compute six observed/reference relative changes. Each 95% t upper bound
mean + 2.571*sample_sd/sqrt(6) must be <=5%. All twelve cohorts must meet the
other gates. These practical cost margins are not a power calculation for science.
Offline replay must reconstruct each full-response outcome, native-job identity,
queue/process/worker join, counter delta, runtime identity, cleanup and paired
confidence bounds. Preserve an evidence seal on failure as well as success.

If any necessary execution or measurement contract cannot be met, stop this
candidate and report the limitation. No guarantee is made that gzip will pass.

## After qualification

Even a passing cost pilot leaves scientific collection disabled. Review whether
the wrapper's queue, full job lifecycle and child CPU demand meet the prediction
model's assumptions. Document any CPU/worker-wall mismatch; do not silently
reuse the SHA model's stage definitions. Only then freeze a separate fresh
capacity/calibration/held-out protocol. No V31 capacity or response samples are
imported. Fresh calibration must seal forecasts before the eighteen proposed
unseen-rate trials. The earlier median-deadline and capacity-fraction design is
still a proposal requiring exact numeric rules, sample precision and uncertainty
justification. Do not claim a 5% admission endpoint from a median-deadline test.

No external launch command exists yet. The selection/correctness seal is not a
qualified runner bundle. Implement and qualify the service and collector against
this plan before asking the user to close applications for another experiment.
