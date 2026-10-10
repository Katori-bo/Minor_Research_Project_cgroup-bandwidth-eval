# Focused response-timing diagnostic protocol

Revision 2, 2026-09-28. Written before diagnostic collection. This is a separate session from the completed 300-trial study and 50-trial follow-up. Its purpose is to locate the large client-observed delay remaining after subtracting server queue wait and elapsed SHA processing. No mitigation or mechanism is assumed in advance.

## Existing evidence and competing explanations

The completed follow-up shows that, at 100 ms quota period and four workers under bursty load, the mean trial p99 end-to-end latency is 4131.7 ms. The mean trial p99 of the **per-request** remainder is 4085.7 ms; among each trial's slowest 1% successful requests, the mean remainder share is 97.8%. These two p99 values do not necessarily select the same requests. The source audit is `diagnostic/analysis/existing_report.md` and its 50-trial CSV. All original attempt file hashes and request/event ID matches were checked.

Possible locations include client connection/request preparation, server handler work before admission, a handler waiting to resume after the SHA worker finishes, response writing and transport, and client response-body completion. These are hypotheses, not findings. The original service starts server timing immediately before enqueue and stops it immediately after the SHA computation. The client times through full body consumption.

## Frozen diagnostic matrix

The research matrix is 100/250 ms periods × one/four application workers × five repetitions, all at 0.5 CPU (`quota_us = period_us / 2`). Each trial uses `GOMAXPROCS=2`, original 44,000 SHA-256 iterations, original high rate 113.21/s, 5-second low/high burst phases at 0.5/1.5 times the mean, 20-second warmup and 60-second measurement. The four conditions have 20 trials in one random order seeded with 20260928. Pilot data are excluded from research estimates.

The diagnostic pilot has seven 20-second measurements with 10-second warmup: four 100 ms/four-worker overhead trials in on/off/off/on order, and one instrumented trial of each remaining condition. On/off switches both server timing and client HTTP tracing. The pilot must validate all attempts and observe server timing and at least 99% usable client traces among successful responses in each instrumented trial. Three median on/off ratios must each be no greater than 1.10: service cgroup CPU microseconds per completed job, load-generator process CPU microseconds per scheduled request, and client end-to-end p99 latency. Two observations per arm give a coarse perturbation screen, not proof of negligible overhead. A failed screen stops collection for review.

## New timing boundaries

Server: handler entry → admission, admission → worker start, worker start → SHA completion, and SHA completion → handler resume. These server durations use one monotonic clock. The existing worker events and new handler events retain request IDs and offsets from one service-local origin. Response headers duplicate durations and are checked against server events. The handler-resume timestamp precedes header formatting and response writing.

Client: dispatched request start → connection acquired, request written, first response byte, headers returned, and body fully consumed. `net/http/httptrace` records the first three boundaries; the client records the latter two. Trace callbacks use a separate synchronized recorder, frozen before a request result is published. Missing, repeated or late callbacks are classified in each raw request; an unusual callback order does not invalidate an otherwise sound trial. The analyzer reports trace coverage and leaves client trace quantiles unavailable below 99% usable successful requests. These offsets use one client-local clock. Never subtract an absolute server timestamp from a client timestamp. The per-request remainder after all four server durations still contains dispatch, transport, response writing and client completion. Even if it narrows substantially, the measurement does not by itself distinguish kernel throttling from Go scheduling; cgroup counters are aggregate corroborating evidence.

## Outcomes and analysis

Retain every request and server event. Report per-trial nearest-rank p50/p95/p99 of end-to-end and each measured duration, plus rejection and timeout fractions, throughput, cgroup throttling, sampled queue depth, and each repetition. Derive residual durations per successful request; never add or subtract independently computed quantiles. For the four-cell comparison, use the same interaction definition as the follow-up and bootstrap five independent trial values per cell with 10,000 resamples and fixed seed 761. Analyze residual, handler wait, client request-to-first-byte and end-to-end metrics separately. Any mechanistic claim requires matching the recorded stages and environmental/cgroup evidence. Failed application requests remain outcomes, not exclusions.

## Environment, integrity and operation

Reuse the follow-up's power, temperature, CPU topology, affinity, quota, zero `cpu.max.burst`, monitor coverage and generator-lag checks. Both clients and server use the same affinities as the completed follow-up. The launcher shares `.experiment.lock`; it builds and runs tests, then the pilot, then full collection only after the pilot passes. It uses systemd sleep inhibition when available. Sessions are under `results/diagnostic/`, with separate pilot/full raw attempts, numbered retries, logs, status and completion markers. Existing sessions cannot be rebuilt or have source/protocol changed on resume. No existing experiment evidence is overwritten.

Allow roughly 2–4 hours including settling, cooling and retries. The mathematical minimum for the 20 full trials is 20 × (60 s settling + 20 s warmup + 60 s measurement) = 46.7 minutes, plus initial idle, pilot and drains. Prepare while the laptop is in use; start the unattended performance batch only when it can remain plugged in, on Balanced, with its lid open and other active applications closed.
