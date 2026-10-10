# Next step: follow delayed HTTP goroutines through runtime queues

Plan prepared 2026-10-03 after the validated v11 decision-recorder study.
This is a proposed diagnostic, not a built recorder or launched experiment.

## Question

For an HTTP goroutine that becomes runnable and waits seconds, where is it
waiting, which scheduler paths move it, and what work receives turns while it
remains there? V11 observes wake, selection and dispatch but does not record
queue membership or transfers. The selected source at first dispatch does not
identify where the goroutine spent the entire preceding wait.

The source audit confirms that network-ready work can enter global or local
queues through injectglist, depending on whether the waking thread owns a P and
whether other Ps are idle. Global batches can migrate work to a local queue;
local overflow and draining can move it back; another P can steal it. A runnext
entry can also be displaced into regular local FIFO. Every relevant route must
be covered before calling a reconstructed queue history complete.

## 1. Extract more from v11 without another collection

Use sealed records to compare dispatch counts, inherited time slices, scheduler
tick progress and periodic versus forced global checks in the selected long
waits. Reuse the reviewed correction that excludes a delayed G's own final
selection from counts of other work selected ahead. Keep derived outputs outside
the sealed sessions. These records can characterize fairness opportunities;
they cannot fill in missing enqueue or migration events retrospectively.

## 2. Prepare a separate bounded queue-history recorder

Preserve the pinned compiler and pending-preemption-fairness-v1 policy. Extend
the observational build to record queue admission, removal and transfers for
network-ready goroutines through their first dispatch, retaining the HTTP request
join from v11. If safe selective tracking cannot cover the relevant paths, use
a bounded complete capture and assess its observer cost rather than silently
omitting transitions.

Required destinations are global queue, regular local queue with owning P,
runnext with owning P, and explicitly labelled transit/direct-selection states.
Required routes include runqput, displaced runnext, runqputslow overflow,
runqputbatch, global single/batch insertion and removal, runqgetPolicy,
runqdrain, runqgrab/runqsteal and direct netpoll selection. Preserve the reason
and source/destination of each transfer, with the existing pending/fairness,
inheritance, selection and dispatch observations.

Do not scan queues unsafely or add scheduling policy changes. Existing ownership
and publication rules must govern hooks. Record operation identities and timing
brackets where concurrent publication/removal overlaps; retain ambiguous timing
rather than inventing an exact global order from reservation indices. Choose
the fixed buffer budget before collection. Overflow or missing transitions must
prevent a claim of complete queue history.

## 3. Verify before measurements

Test FIFO and runnext ordering, displacement, overflow, batching, stealing,
draining, queue wraparound, concurrent ownership transfers and conservation.
Check per-G histories for duplicate queue membership, missing removals and
impossible transfers. Verify HTTP request zero, connection reuse, stopped
snapshot immutability and explicit overflow. Source and image hashes must be
sealed independently of v11. The unobserved arm must keep the same policy.

## 4. Collect a small paired diagnostic

Proposed design: eight trials in four control/observed pairs, AB/BA/BA/AB.
Keep the original CPU quota, affinity, four workers, GOMAXPROCS=2, 128-entry
application queue, 44,000 SHA iterations, arrivals, warmup and duration.
Runtime tracing and worker yielding remain OFF; custom recording stays ON.
Use the original quiet-host, power, settling and request-accounting checks.
No recalibration, new correction or automatic larger collection.

Apply the existing observer screens to CPU/job, client CPU/request, successful
p99, failures and trace coverage, with throughput reported alongside them.
Allow approximately 30–60 minutes for the measurement and analysis once prepared;
cooling can extend this. Preparation/build time is separate. Collection requires
the desktop app closed and an external-terminal launch.

## 5. Use residence evidence to choose one correction

| Observed pattern | What it would motivate investigating |
|---|---|
| Long global residence while local handoffs continue | How often global work receives actual selection opportunities |
| Long local FIFO residence while runnext repeatedly wins | A bounded bypass of runnext or a wait-age rule |
| Much of the delay occurs across transfers/batches | Placement and migration rules, with complete transit accounting |
| Queues receive prompt selections but dispatch is delayed | The selection-to-dispatch interval and OS/quota context |

Only choose and predeclare a concrete scheduling candidate after this review.
A dispatch budget is a bound on selection opportunities, not a promise of a
wall-clock latency bound under CPU quota. A subsequent comparison must keep
observation comparable between policies and report client tails, every failure,
throughput and CPU cost. The queue-history diagnostic itself does not establish
an accepted fix or qualify full collection.

## Intended output

For each selected slow and typical HTTP request: a timeline from network wake
through queue admissions/transfers and first dispatch to handler entry; residence
time brackets by queue/P; other dispatches during each residence interval; and
the fairness decisions taken there. Report incomplete/ambiguous histories and
all observer outcomes separately. Use this evidence to target the next change.
