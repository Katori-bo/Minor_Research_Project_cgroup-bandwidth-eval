# V24 revision3: native acquisition and prospective window-quality qualification

Fixed before generation-03 runtime preparation or collection, 2026-10-07.
Generations01/02 remain incomplete under their original rules. No historical
sample, accepted marker, source or report is changed or reused as a new trial.
This revises instrumentation and measurement quality, retaining the scientific
question, workload, fixed phase windows and scientific decision thresholds.

## Acquisition contract

A normal-user native C collector uses the service's existing `cpu.stat`, CPUs0/1,
20ms requested cadence and110-second bound. It allocates/touches6000 raw records
of at most4096 bytes before recording, opens the input once, and brackets seek/
read with CLOCK_MONOTONIC and CLOCK_THREAD_CPUTIME_ID. Parsing and serialization
occur after capture. A single READY pipe message after the first acquisition
allows startup qualification; there is no periodic output during capture.
Absolute monotonic deadlines skip missed slots instead of issuing catch-up
bursts. All observed raw text, timestamps, CPU times and skipped slots are kept.
The collector has no tracing, HTTP, priority, realtime or host-setting changes.

The verifier re-decodes raw text and rejects read errors, empty/truncated text,
duplicate/missing keys, negative/noninteger or backwards counters, overlapping
time brackets, backwards sampler CPU time, foreign command/process/path/affinity,
and stale source/binary receipts. Wall minus sampler thread CPU is descriptive
waiting/descheduling evidence, not a scheduler or kernel causal attribution.

## Prospective quality rule

An isolated acquisition longer than2ms is reported, not automatically rejected.
The previous global2ms rule remains binding for generations01/02. New data must
satisfy the retained50ms adjacent gap rule during the60-second measurement and
the retained60ms total enclosure span at every fixed phase boundary. The last
read wholly before the earliest boundary and first wholly after the latest
boundary enclose the counter; no interpolation, sample deletion or alternative
window selection is allowed. Long acquisitions can widen or eliminate those
enclosures and thereby fail this rule.

At each phase, CPU/completion's conservative interval must have width at most
4% of its lower bound. The busy delivered-CPU interval must have absolute width
at most0.02 CPU. These quality budgets are selected prospectively following the
failed collection reviews:4% is below the5% minimum scientific cost separation,
and0.02 is half the0.04-wide scientific delivery band. These choices are
engineering budgets, not statistical confidence or exact instantaneous kernel
accounting guarantees. All scientific comparisons still use conservative lower
bounds; adequate precision alone cannot make the hypothesis pass. Historical
data motivated the revision but are not reclassified using it.

The same host unit-slope clock joining, microsecond accounting, aggregate
container scope and in-flight boundary limitations remain documented. The
enclosures bound the observed accounting counters and clock/completion alignment;
they do not prove zero kernel accounting lag or per-job CPU attribution.

## Scientific contract retained

Use the same retained image/server/client/gate,44k/88k work sizes, half-rate
scaling, CPU quota50000/100000, CPUs2/4 service and0/1 client/controller,
one worker/GOMAXPROCS1, queue128, yield off, 20-second warmup/drain/reset,
60-second10-second-cycle patterns and full drains. The scientific12-slot order,
six busy[6.5+10k,9.5+10k) windows and low[1+10k,4+10k) windows are retained.
All six off/on pairs must satisfy2% capacity/whole-cost and1pp deadline screens.
All six on trials must satisfy phase states, both cost-ratio lower bounds>=1.05,
and busy delivery entirely inside[0.48,0.52]. No novel method is claimed.

## Qualification before full collection

The offline package includes a110-second regular-file recording and native build
provenance. These are software checks only. The external `qualify` launch first
repeats real image/resource checks and four short normal/cancellation cases,
then obtains a fresh read-only root observer inventory and ownership review.
Actual qualification records four separate60-second trials in this fixed order:
small off, small on, large on, large off. It retains the original10-minute
initial idle, thermal/power/topology checks, per-trial>=60-second settling,
dispatch/clock/cleanup rules and sampler bounds. Its collector comparisons must
pass2% busy capacity,2% whole CPU/job and1pp500ms-miss differences at both sizes,
and both on trials must provide eligible fixed phases and pass quality budgets.
Cost separation and nominal delivery need not pass the scientific hypothesis
to qualify instrumentation; screening them here would condition the experiment.

Qualification is bounded to30 minutes including initial idle, with120 seconds
cleanup grace, independent360-second active-trial bounds, and at most one total
technical retry. It never automatically resumes. Its four raw/sealed trials,
environment, source/boot/binary/observer identities and bounded receipt are
independently replayed. Its one-pair-per-size comparability check is engineering
readiness, not equivalence or scientific confirmation.

The `qualify` command stops after that report. The separate `run` command refuses
unless qualification passed and independently replays it before any full-study
trial. The four qualification trials are never pooled into the twelve scientific
trials. Full collection retains60 minutes including renewed10-minute settling,
one independent technical retry and separate10-minute analysis bound. Runtime
preparation retains10 minutes. Reboot, source change, qualification failure or
measurement interruption requires a new generation rather than an extension.
The app must be fully quit and local sudo authentication is required only for
the external read-only observer inventory. No live qualification runs in the app.
