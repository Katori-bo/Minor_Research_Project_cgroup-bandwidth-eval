# Controlled mechanism benchmark: proposal

Date: 2026-10-09. Status: design proposal only. No new runner, sealed
experimental protocol, or collection. The original V31 result and stopped
imgproxy/gzip qualification attempts remain unchanged.

## Question and permitted claim

Build our own small benchmark to ask when average busy capacity is insufficient
for deadline prediction, and when a freshly calibrated response distribution
remains useful. Control computational work, deliberate non-computational delay,
and offered traffic separately. The useful result is a reproducible mechanism
test with stated boundaries, not a benchmark guaranteed to pass a favored model.

The original Go/SHA server and gzip C wrapper already contain custom research
apparatus. A new synthetic benchmark therefore cannot supply independent
application, physical-host, or research-team replication. V18 also already
verified sleep/CPU/quota observer fixtures; merely repeating those is not a new
contribution. The added question must concern prospectively predicted HTTP
deadline outcomes across controlled changes, beyond basic observer functionality.

## Minimal apparatus

Use one bounded request dispatcher and one serial job worker, with fixed
CPU-bound work and a separately switchable explicit wait. All accepted requests
execute their declared task and return an ID and independently checkable output.
No cached responses, hidden concurrent work, or outcome-based work/rate searches.
Retain the worker handoff rather than assigning it zero duration by definition.

Record enqueue, worker acquisition, computation start/end, explicit wait
start/end, response write and worker release, plus scheduled offer and complete
client body receipt. Distinguish worker CPU time from worker elapsed time and
whole-cgroup CPU accounting. Instrumentation needs its own bounded overhead,
clock, completeness and cleanup qualification before scientific use.

In particular, enqueue-to-acquisition can include wakeup/acquisition delay even
without an earlier job occupying the worker. The gzip outcome demonstrates that
these definitions need explicit treatment. Do not silently relabel this interval
or adopt a larger threshold because the previous pilot missed its bound.

## Prospective comparisons

Use CPU-only and CPU-plus-explicit-wait workloads, each tested with an uncapped
and fractional-quota resource contract. In each, include a low-load steady
condition and a separately declared burst/backlog stress condition. These are
controls for different applicability regimes, not interchangeable repetitions.

Measure fresh capacity and calibration response records for each contract.
Freeze all model parameters, numeric deadlines, validation offer schedules,
sample sizes, analysis rules and predicted outcomes before held-out collection.
Specify both absolute forecast accuracy and comparator contrasts in advance;
report ties, incorrect predictions and uncertainty. A model is allowed to win,
tie or lose. An intentionally stressed cell can show a domain exit without
being discarded or presented as a valid low-queue confirmation.

Retain all offers, dropped/failed responses, queue distributions, throttling,
overlap and accounting evidence. Keep the old 100 us/99% result fixed. Any new
eligibility definition must follow the new question and a written independent
justification, with the old criterion reported alongside it where comparable.
Do not define eligibility by which requests produce a favorable model error.

## Work required before a launch command

Finalize exact demand/wait settings, resource identities, traffic schedules,
trial/block counts and precision rationale; write finite preparation/run caps.
Implement and exercise the actual collection paths and failure handling, then
seal sources, inputs and analysis rules. Separate technical qualification,
fresh calibration, forecast sealing and held-out testing. No result from the
stopped gzip pilot can substitute for these stages.

A successful study could strengthen the mechanism explanation and locate its
failure boundary on this host. Synthetic control alone does not establish
novelty, production generality or independent replication. Any novelty claim
still needs a distinct contribution and an appropriate related-work review.
