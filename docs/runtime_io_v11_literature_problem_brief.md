# Problem brief for literature research after V11

## The problem in plain language

An HTTP goroutine becomes ready to run, but can wait several seconds before Go gives it its first turn. During that same interval, CPU workers, other HTTP goroutines, and HTTP background readers receive many turns.

The question is: **what prevents this particular ready goroutine from getting a timely turn, and how does the CPU quota amplify that delay?**

This is a scheduling opportunity problem to investigate. The recorded interval starts when network I/O wakes a goroutine and ends at its first runtime dispatch, subsequently linked to a valid HTTP handler entry. It is not simply the time spent doing the application's hashing work, and it is not the complete client response time.

## Experimental setting

- Go 1.26.1 on Linux, using cgroup v2.
- Aggregate CPU budget: 50 ms per 100 ms period, nominally half of one CPU.
- GOMAXPROCS=2, with four CPU worker goroutines.
- Each admitted request requires 44,000 SHA-256 iterations; application job channel capacity is 128.
- Bursty traffic averaging 113.21 requests/s, alternating approximately 56.6 and 169.8 requests/s in five-second phases.
- V11 has four pairs of trials, with 10 seconds warmup and 20 seconds measurement per trial.
- Native Go runtime tracing is off. A bounded custom scheduler recorder is enabled in one arm and disabled in the other.
- Both arms use the same experimental pending-preemption fairness policy. This experiment tests observation overhead and records behavior; it is not a stock-Go-versus-patch performance comparison.

## Evidence that a proposed explanation should account for

1. The longest retained matched example waits **4.4166 seconds** from network readiness to first dispatch. During that interval, **2,407 other dispatches** occur: 592 workers, 1,221 HTTP goroutines, 593 HTTP background readers, and one runtime background goroutine.
2. Of those 2,407 choices, **1,768 use runnext**, 629 use the regular local queue, and 10 use the periodic global-fairness branch. The waiting goroutine is finally selected through a global batch. That final source does not reveal its earlier queue residence.
3. Across the observed captures, runnext supplies **66.29% of 43,886 selections**. Runnext is a processor-local preferred slot whose selected goroutine can inherit the current scheduling time slice.
4. The experimental correction acts when a preemption request is pending at scheduler entry. It produces only **181 forced choices (0.412%)**. None occur during the longest example's wait. Ordinary periodic global checks do occur in that interval.
5. Among **3,278 explicitly linked pre-handler waits**, 524 last at least one second and 327 last at least two seconds. These counts describe the linked cohort, not all requests, and some waiting intervals overlap.

The recorder passes its predeclared descriptive overhead screens, but four pairs do not establish zero observer effect. Runtime dispatch also does not establish continuous execution on a physical CPU; kernel scheduling and quota throttling remain relevant.

## What we still cannot locate

We have not recorded the delayed goroutine's complete queue history. Network-ready work can enter a global queue, a local queue, or a direct selection path, and can subsequently move between processors. We therefore cannot yet distinguish:

- Waiting in a global queue with insufficient opportunities to reach it.
- Waiting in a local regular queue while preferred handoffs receive turns.
- Delays caused by queue transfers or placement on another processor.
- Interaction between runtime scheduling opportunities, preemption, and cgroup throttling.

Runnext's high share is evidence of scheduler behavior, not proof that it causes every long wait. Lost wakeups, a strict FIFO violation, and a purely kernel-level cause have not been established.

## Useful literature searches

- User-level scheduler fairness and starvation under CPU quotas.
- Work-stealing schedulers: local versus global queue fairness.
- Continuation or handoff priority, runnext, and time-slice inheritance.
- Scheduling fairness measured in dispatches versus time slices.
- Linux CFS bandwidth control / cgroup CPU throttling and tail latency.
- Hierarchical scheduling: interaction between language runtimes and OS CPU budgets.
- Age-based scheduling or bounded bypass for latency-sensitive runnable tasks.

For each paper, look for a mechanism that explains **both the seconds-long wait and the many turns given to other goroutines**. Identify its assumptions about queue placement, fairness checks, preemption, and available CPU time. A particularly useful paper will predict something measurable in the next experiment: where the delayed goroutine should be waiting, which event should release it, and what changes when quota, processor count, burstiness, or handoff frequency changes.

## One paragraph to copy into notes or a research query

We are investigating Go HTTP tail latency under a Linux cgroup CPU quota of 50 ms per 100 ms, with GOMAXPROCS=2 and four CPU workers. Instrumentation shows that some network-woken HTTP goroutines remain runnable for several seconds before first runtime dispatch while thousands of other goroutine dispatches occur. Preferred local runnext selections dominate the captures, and a pending-preemption-triggered fairness correction is sparse and does not prevent long waits. We need to determine whether queue placement, preferred handoff/time-slice inheritance, fairness-check cadence, or interaction with CPU throttling explains the delay. The missing evidence is the waiting goroutine's queue residence and migration history.

Evidence: [derived V11 review](../analysis/runtime_io_v11_decision_probe_review/report.md). Proposed measurement: [V12 queue-history plan](runtime_io_v12_queue_history_plan.md).
