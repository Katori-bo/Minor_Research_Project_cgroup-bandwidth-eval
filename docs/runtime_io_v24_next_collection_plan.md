# Next collection plan after both V24 generations stopped

2026-10-07. This is a planning note, not a frozen revision3 protocol or a claim
that another package is ready. Generation-01 and generation-02 remain incomplete.
V22/V23 results and every existing source/design/data seal remain unchanged.

## What data the question actually requires

For each fixed busy or low window, measure the change in the owned container's
cumulative CPU usage, count server completions in the same clock-bounded window,
and retain evidence of the queue state. CPU delta divided by completions is
aggregate container CPU/completion; CPU delta divided by elapsed wall time is
delivered CPU fraction. It includes runtime/HTTP/kernel work and is not isolated
SHA CPU demand. Job counts must remain bounded at both window endpoints.

Linux documents `cpu.stat` usage/user/system counters for cgroup processes and
descendants, and the bandwidth/throttling fields. This supports continuing to
use the retained counter interface. It does not promise a maximum read latency
or certify arbitrary sub-millisecond boundary accuracy.

Primary reference: [Linux cgroup v2 CPU interface](https://cdn.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html#cpu-interface-files).

## Established examples and alternatives

- Docker's published CPU-percentage calculation uses the change between current
  and previous cumulative CPU statistics. This is an interval measurement.
  [Docker Engine API example](https://docs.docker.com/reference/api/engine/version/v1.40/).
- FIRM (OSDI2020), section3.1/Table2, collected cumulative CPU telemetry via
  cAdvisor/Prometheus, alongside application tracing and Linux perf hardware
  events. The paper also measured collection overhead. Its instrumentation
  validates the general source/method family; it is not evidence that those
  tools meet our fixed3-second phase precision requirements.
  [FIRM paper](https://www.usenix.org/system/files/osdi20-qiu.pdf).
- Perf supports task-clock events and cgroup-scoped monitoring. Its scope,
  permission, inheritance and kernel/user accounting would have to be checked
  before using it as a comparable independent baseline.
  [perf_event_open manual](https://man7.org/linux/man-pages/man2/perf_event_open.2.html).
- Scheduler traces can record switches/wakeups for causal timing diagnosis.
  Their setup and overhead make them a separate qualified diagnostic rather
  than an automatic substitute for this experiment's aggregate counters.
  [Linux tracing documentation](https://cdn.kernel.org/doc/html/latest/trace/index.html).

These are documented examples, not a survey showing that every researcher uses
one method or tolerates a particular amount of jitter.

## Proposed sequence

1. Prepare a small native collector with preallocated raw-record storage.
   Bracket acquisition itself with CLOCK_MONOTONIC timestamps; move text parsing
   and serialization outside the timed acquisition and defer output until stop.
   Retain the20ms requested cadence and bounded lifetime unless a new protocol
   explicitly justifies a change. Native code removes Python allocation/GC
   costs; it does not guarantee a read deadline under ordinary scheduling.
2. Record sampler thread CPU time alongside acquisition wall time and retain
   per-read timing. A long wall interval with little thread CPU suggests waiting
   or descheduling; it does not alone identify a kernel cause. Linux documents
   CLOCK_THREAD_CPUTIME_ID as the calling thread's consumed CPU time.
   [clock_gettime manual](https://man7.org/linux/man-pages/man2/clock_gettime.2.html).
3. Keep every raw record and explicitly report slow reads, missing records,
   monotonicity, coverage and collector cost. Before collection, specify how
   acquisition intervals support bounds at fixed phase endpoints. Evaluate a
   prospective quality rule for the actual accounting windows and their total
   CPU/completion uncertainty, rather than treating an unrelated warmup/interior
   read as automatically invalidating the scientific measurement. The numeric
   limits must be justified and frozen before new measurements; existing rules
   continue to bind both failed generations. No post-hoc sample deletion,
   window reselection or acceptance of these generations is allowed.
4. Gate any complete experiment behind a separately bounded qualification on
   the actual retained service/cgroup under both work sizes, including collector
   off/on comparisons. This needs an external quiet window. Synthetic regular-
   file checks remain useful software checks but are insufficient qualification.
5. Only after qualification passes, freeze new sources/protocol/receipts and
   prepare a fresh full12-trial generation. Retain the workload, scientific5%
   cost-separation criteria, busy-delivery range and observer-comparability
   requirements unless a separately documented scientific revision is needed.

No collector, live qualification or new full experiment was run while producing
this plan. Generation-02 had zero GC collections in both failed recordings,
excluding that mechanism for those pauses; their exact remaining cause is
unresolved. All three slow reads were outside the set used to enclose the fixed
phase boundaries. That observation motivates a prospective design review and
does not reclassify failed evidence.
