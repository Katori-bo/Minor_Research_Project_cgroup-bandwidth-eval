# Worker runnable-wait hypothesis: read-only capability follow-up

10 October 2026. Addendum to the completed
[stage-signal assessment](runtime_io_stage_signal_assessment_20261010.md).
The stage screen and its sealed assessment remain unchanged.

**The proposed wait measurement is not currently enabled.** A read-only
current-session check found kernel 7.2.8-arch1-2 and
/proc/sys/kernel/sched_schedstats present with value 0. This is current-session
capability evidence, not a reconstruction of historical experiment settings.
No worker counters, traffic or performance samples were collected and no setting
was changed. [Saved readback](../analysis/runtime_io_stage_signal/20261010/kernel_capability_readback.json).

Linux documents this switch as enabling/disabling scheduler statistics and
states that enabling it adds scheduler overhead. File existence alone therefore
does not establish that runnable-wait counters are usable or cost-free.
[Kernel sysctl documentation](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html#sched-schedstats).
We do not interpret a zero or unavailable wait increment as absence of contention.

The exact candidate remains the paired feature (C/n, R/n): worker running time
and runnable-wait increments per scheduled offer, relative to corresponding
calibration warmups, with early/late increments. Runnable waiting is not every
off-CPU interval. The predictive hypothesis is increased waiting despite similar
CPU duration; it has not been demonstrated by the saved data.

A concrete feasibility qualification would first verify worker identity,
counter behavior and exact acquisition boundaries. Any change to the scheduler
statistics switch needs an owned restoration path and independent observer
qualification, counting the cost of enabled statistics as well as counter reads.
Only an externally collected, separately declared development study could test
the state-to-future relation. Its ordinary state-conditioned comparator must
receive the same counters, history, warmup budget and decision time. No predictor,
cutoff, instrumentation-overhead allowance or confirmation schedule is frozen
by this addendum. No host-setting command or launcher is prepared.

Decision: the source/capability audit is complete at this boundary. The feature
is measurable in principle but currently unavailable under unchanged settings;
the record neither establishes useful prediction nor justifies a confirmation
experiment. Keep this instrumentation prerequisite distinct from the empirical
paper and the friend's pending V31 replication.
