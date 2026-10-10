# How to pursue an empirical contribution

Date: 8 October 2026. Status: preparation protocol, not a collection launcher.
Following the user's clarification, the proposed Memcached direction below is
not adopted. The immediate discussion concerns how to use the existing evidence
and finish the current research. Retain this document only as a planning record.
No new service trials, installations or model fits accompany this document.
The existing manuscript and closed novelty assessments remain preserved.

## Objective and boundary

Find a consequential, reproducible actual-system finding that the closest
existing work has not already established. A new algorithm is optional. A
benchmark transfer, a surprising plot, or failure of an intentionally weak
baseline is insufficient by itself.

The current paper can be finished in parallel. Its completion is not a
technical prerequisite for this preparation. Its established claims must not
be enlarged using exploratory results.

FIFO theory stays closed; fixed-average quota-period selection stays on hold.
The recent calibration, passive forecasting, profiler correction, attribution
and quota-update screens do not become new candidates merely by changing the
application. Collection remains stopped until a specific pilot passes the
preparation gate below.

## 1. Select a practical decision and qualify one service

Proposed first testbed: one Memcached server with a rate-controlled client.
CloudSuite Data Caching supplies a real application and workload framework:
it exposes server threads, request rate, get/set mix and dataset scaling.
Its documented endpoint is p99 below 1 ms and its recommended dataset is
approximately 10 GB. These are reference settings, not automatically our
experimental contract. [Official benchmark documentation](https://github.com/parsa-epfl/cloudsuite/blob/main/docs/benchmarks/data-caching.md).

Working decision: **at a declared offered workload and fixed CPU quota, which
of 1, 2 or 4 server threads satisfies a declared deadline-miss budget?**
The decision is useful but is not a novelty claim. Quota-aware parallelism
already has established implementations; for example Go explicitly accounts
for CPU limits when setting its default parallelism. That is background,
not a Memcached comparator. [Go's runtime explanation](https://go.dev/blog/container-aware-gomaxprocs).

First inspect the pinned server and client sources. Record actual request
generation, pacing under congestion, timeout/error accounting, available
latency timestamps, thread controls, and memory/network requirements. Pin
source commits and image digests before any performance comparisons.

The current host reports about 15 GB total RAM, so do not adopt the reference
dataset without checking headroom for the client, OS and instrumentation.
A smaller dataset or same-host client changes the benchmark conditions and
must be declared. Inspect CPU topology and client capacity rather than assuming
the old affinity is suitable.

**Output:** a service/decision contract with workload, offered schedule, quota,
period, burst credit, affinity, dataset, warm-up, threads, deadline, miss budget,
and why that endpoint matters. Keep quota settings fixed. Do not copy the SHA
service's 500 ms deadline or claim CloudSuite compliance with another endpoint.

**Stop/revise:** if the client cannot support auditable offered-request outcomes,
the host cannot support the declared setup, or the decision has no practical
meaning. This is qualification, not a research finding.

## 2. Write the strongest ordinary comparison first

Use direct measurement of all three thread settings as the reference decision.
Include service defaults and ordinary workload-specific recalibration. If
testing forecasts, include busy-capacity and nonlinear utilization calibration,
and request-class/mixture-aware estimation when the workload mixes operations.
The existing paper's quadratic benchmark is a starting comparator, not a
complete reproduction of every published estimator.

List each method's assumptions, observations, calibration cost and output.
Separate an invalid extrapolation from a failure inside the method's claimed
scope. Give a baseline information it legitimately requires. If a fresh sweep
solves the decision affordably, a replacement method needs a demonstrable
additional capability; being more elaborate does not help.

**Output:** one comparison table and one precise potential disagreement worth
testing. No such disagreement is established by this protocol.

**Stop:** if the proposed novelty is merely generic quota throttling,
microbursts, oversubscribed threads, changed request costs, or an already-closed
claim without new causal evidence. Perform a targeted primary-source screen
before treating any of these as an original mechanism.

## 3. Freeze the smallest discriminating discovery pilot

Only after steps 1 and 2, write a bounded pilot manifest. Select one condition
and one controlled perturbation that distinguish the suspected explanations.
Do not search a large workload/configuration matrix without a hypothesis.

A possible structural cap is three thread settings, two conditions and three
balanced repeat blocks: 18 discovery trials. This is an example budget, not
an approved design, power calculation, or guarantee of sufficient evidence.
Count qualification/calibration trials separately and cap them too. If the
smallest useful design exceeds that budget, explain why before collecting.

Freeze rates, duration, warm-up/reset rules, order, exclusions, expected baseline
behavior and a decision-relevant minimum effect before observing results.
Derive the minimum effect from the chosen deadline/miss budget; do not reuse
the old study's percentage-point thresholds automatically.

For each offered request retain scheduled offer, actual send, operation class,
completion/error/timeout and deadline outcome. Retain cgroup CPU consumption,
throttling counters, memory/cache statistics, settings and client saturation
evidence. Aggregate counters do not identify per-request causes or quota phase.
Add detailed timing instrumentation only if needed to distinguish a particular
mechanism, and assess its measurement cost.

**Output:** frozen manifest, qualified recorder and bounded launch procedure.
No existing historical diagnostic command is authorized by this document.

## 4. Decide whether an anomaly deserves explanation

Compare decisions and all-offer outcomes, not just successful-request p99.
Analyze independent run/block contrasts; thousands of requests in one run are
not thousands of independent experimental replicates. Report uncertainty and
client/accounting qualification failures.

Check whether an apparent difference disappears after ordinary recalibration,
mixture-aware accounting, corrected client pacing, or comparable resource use.
A single bad run or an explanation already in the closest literature fails
the contribution gate. Preserve negative results and stop that candidate.

**Output:** proceed/stop report. Proceed requires a reproducible, material
disagreement that survives adequate controls, plus a specific unresolved cause.

## 5. Test cause and precise originality

For a surviving anomaly, state two competing causal explanations and an
intervention that predicts different outcomes. Change one relevant factor;
hold the offered schedule and resource contract comparable. For example, a
client-side explanation needs a client-capacity/pacing control, whereas a
cache explanation needs controlled cache state. Neither explanation is new
merely because the intervention succeeds.

Read complete methods and correction rules of the closest work. Write the
claim in one sentence specifying service, conditions, effect and mechanism.
Then record exactly what prior work does and does not establish. The possible
claim is a new causal finding or a useful measured boundary of an established
method, not that the entire topic is unexplored.

**Output:** causal evidence and an originality comparison. Stop if the finding
is already covered or ordinary alternatives remove its practical consequence.

## 6. Confirm independently, then write the contribution

Freeze the surviving hypothesis, analysis and meaningful-effect criterion.
Use fresh confirmation trials that do not select the hypothesis or fit its
comparator. Choose replication scope to match the intended claim; one service
and host support a limited claim, not a general systems result. Assess the
required repeat count from discovery variability rather than inventing power.

Build a method only if the finding exposes a capability existing alternatives
cannot provide. Compare usefulness, information required, uncertainty and
measurement cost. Otherwise publish the scoped empirical finding if it is
substantial enough, or retain it as supporting evidence and stop.

## What preparation can reuse

Reuse the existing study's preservation, source hashing, environment recording,
resource accounting, independent calibration/validation separation and outcome
auditing practices. Requalify their implementation for the new service.
The Go HTTP request recorder and constant-service FIFO forecast are not
automatically valid for the Memcached protocol or a multithreaded service.
Older launchers contain historical assumptions and must not be run unchanged.

The immediate next deliverable is **the pinned client/server feasibility audit
and baseline table from steps 1 and 2**, with a verdict on whether a specific
discriminating pilot is justified. This protocol establishes a way to decide
what to do next; it does not establish a sixth novel avenue or promise novelty.
