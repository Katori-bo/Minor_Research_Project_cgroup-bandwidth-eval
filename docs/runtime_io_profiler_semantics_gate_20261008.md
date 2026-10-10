# Fixed-quota causal profiling: bounded offline gate

8 October 2026. Follow-up to the
[third-avenue screen](runtime_io_third_avenue_novelty_screen_20261008.md).

**Verdict: stop custom-profiler development and new collection for this candidate.**
We found a conditional mismatch in CPU-only virtual-speedup accounting, but no
additional capability beyond established blocked-time profiling and ordinary
periodic-budget replay. This closes the authorized gate; it does not prove that
quota-aware profiling is impossible or that every deployed profiler is adequate.
The paper and original evidence are preserved.

## What was inspected and executed

Both repositories were pinned using their remote HEADs and selected source files
were saved with SHA-256 and Git blob hashes:

| Artifact | Pinned commit | Coverage |
|---|---|---|
| Coz | `256e3c389424d6a1691ee5d18b5ecb5a6c1001ec` | Linux sampling, delay counters, synchronization, experiment records, progress points, browser reporting and text reporting |
| BCOZ | `2836bd096e1c5d07ab5fed83a69977e1e3a94a97` | Weighted blocked/on-CPU sample processing, subclass selection, delay counters, blocking hooks, experiment records, progress points and browser reporting |

The [127-file source manifest](../analysis/runtime_io_profiler_semantics_gate/20261008/sources/manifest.json)
records exact URLs and hashes. The full correction pipeline relevant to the
declared single-worker case was examined. The patched kernel/glibc sampling
implementation was not rebuilt or executed; quota-specific blocked-stack
attribution remains unverified.

We executed the pinned viewers' actual parser, aggregation and numeric reporting
code on synthetic profiles, plus the Coz text reporter's pure parsing and
calculation functions. UI/network functions and profiler entry points were
excluded. The runtime C++ counter rules were inspected and modeled conditionally,
not run as an instrumented service. Consequently, this is a source/reporting
semantics comparison, not a measured failure of Coz/BCOZ on Linux.

## Correction rules that change the comparison

| Rule | What the pinned source does | Implication |
|---|---|---|
| Coz selection and delays | Linux task-clock samples credit the selected thread's local counter. A thread ahead of global advances global; one behind sleeps. Samples are processed in batches of ten at a nominal 1 ms interval. | A single selected worker need not physically sleep; global credit can still be subtracted. In the ideal case, credits depend on sampled running time. |
| BCOZ weighted samples | Credits use delay size times sample weight plus one. Line selection can include non-lock blocked samples; explicit on-CPU subclass selection excludes blocked samples. | CPU-only and line-level BCOZ are different interventions. Treating all BCOZ as CPU-only was inadequate. |
| Dependency handling | Pre/post blocking hooks and catch-up rules credit delays already inherited through wakeups. BCOZ handles pending blocked samples around wakeups. | These rules cannot be discarded in a multithread comparison. The declared cases have no locks, I/O or wakeup dependencies. |
| Experiment normalization | Effective duration is elapsed time minus accumulated global credit. Current Coz rejects nonpositive effective duration and insufficient progress; BCOZ clamps negative duration and adapts experiment length. | Synthetic records use positive durations and at least 40 completions; low-count filtering does not explain the results. |
| Throughput reporting | Aggregate duration divided by aggregate completion count is compared with the zero-speedup baseline. | Reported “program speedup” here is fractional reduction in completion period, not throughput increase. A 60% period reduction corresponds to 2.5× throughput. |
| Latency reporting | Begin/end counts and an outstanding-request difference feed an aggregate Little's-law calculation. | Native profiles do not retain individual deadline outcomes. Mean latency cannot be substituted for all-offer miss fraction. |
| Phase correction | The paper discusses phase correction. Both pinned viewers ignore emitted `runtime` and `samples` records; the Coz text reporter parses metadata but does not use it in speedup calculation. | Phase metadata did not change the tested outputs. This finding applies to these reporting paths and commits; it is not a claim about every historical artifact. |

Primary source anchors:
[Coz runtime](https://github.com/plasma-umass/coz/blob/256e3c389424d6a1691ee5d18b5ecb5a6c1001ec/libcoz/profiler.cpp),
[Coz blocking rules](https://github.com/plasma-umass/coz/blob/256e3c389424d6a1691ee5d18b5ecb5a6c1001ec/libcoz/profiler.h),
[Coz viewer](https://github.com/plasma-umass/coz/blob/256e3c389424d6a1691ee5d18b5ecb5a6c1001ec/viewer/js/profile.js),
[Coz text reporter](https://github.com/plasma-umass/coz/blob/256e3c389424d6a1691ee5d18b5ecb5a6c1001ec/coz),
[BCOZ runtime](https://github.com/s3yonsei/blocked_samples/blob/2836bd096e1c5d07ab5fed83a69977e1e3a94a97/bcoz/libcoz/profiler.cpp),
[BCOZ hooks](https://github.com/s3yonsei/blocked_samples/blob/2836bd096e1c5d07ab5fed83a69977e1e3a94a97/bcoz/libcoz/profiler.h),
[BCOZ viewer](https://github.com/s3yonsei/blocked_samples/blob/2836bd096e1c5d07ab5fed83a69977e1e3a94a97/bcoz/viewer/js/profile.js).
The [Coz paper, §3.4](https://arxiv.org/pdf/1608.03676) describes the original
sampling, synchronization and phase arguments. Source details supersede an
assumed generic subtract-only rule in this gate.

## Controlled source-model comparison

The [design](../analysis/runtime_io_profiler_semantics_gate/20261008/design/plan.json)
was saved before the numerical comparison. Assume one indefinitely backlogged
worker, homogeneous 50 ms CPU jobs, perfect aligned 1 ms samples with flushed
batches, full initial periodic supply, and no unrelated work except a declared
controller reservation. Genuinely reduce each modeled job to 20 ms CPU work,
holding quota, period and any controller reservation fixed. Observe a 10 s
window containing complete quota periods.

| Quota / period | Controller CPU charged per period | Genuine modeled completion-period reduction | CPU-only credits through native reporting | Conditional BCOZ line credits including all blocked time |
|---|---:|---:|---:|---:|
| 100 / 100 ms | 0 ms | 60% | 60% | 60% |
| 50 / 100 ms | 0 ms | 60% | 30% | 60% |
| 20 / 100 ms | 0 ms | 60% | 12% | 60% |
| 50 / 100 ms | 1 ms | 60% | 29.4% | 60% |
| 50 / 100 ms | 5 ms | 60% | 27% | 60% |

The first row is a nonbinding-quota control. In the half-CPU row, original work
completes 100 jobs and optimized work completes 250 in 10 s. CPU-only credit is
60% of 5 s running time: 3 s. Native reporting uses the effective 7 s duration
with 100 progress visits, yielding a 30% completion-period reduction. Including
all 5 s of blocked time as selected-line samples gives 6 s of credit and a 60%
reported reduction, equal to the genuine modeled benefit.

**The blocked-time column is conditional.** Linux quota waits must actually be
sampled, weighted and attributed to the selected non-lock line for that mapping
to apply. The source permits that path; this gate did not establish its occurrence
on our kernel. Feeding the same hypothetical credit into the Coz viewer was a
numeric control, not a supported off-CPU Coz mode. No claim that BCOZ always fixes
quota predictions follows from the table.

The controller rows charge 100 or 500 ms of CPU over the window. This tests
explicit overhead accounting rather than assuming observations are free.
Reservations are illustrative, not measured profiler costs. A real sampler,
profiling thread, batching delay, scheduler or changed intervention could behave
differently. Ordinary replay is exact for all five declared cases using the
same known work and supply assumptions. For homogeneous jobs it needs scalar
demand and supply information, not a new per-request tracer.

## Deadline ranking and the adequate alternative

Use ten jobs released at time zero, a 50/100 ms budget and a 500 ms absolute
deadline. Compare two known interventions saving 150 ms CPU overall:

| Intervention | CPU demand sequence | Last completion | Deadline misses |
|---|---|---:|---:|
| Save 30 ms on each of the first five jobs | Five 20 ms jobs, then five 50 ms jobs | 650 ms | 20% |
| Save 30 ms on each of the last five jobs | Five 50 ms jobs, then five 20 ms jobs | 650 ms | 50% |

Both execute 350 ms CPU and have equal batch throughput. Their deadline effects
differ because savings occur at different positions. This is a direct
counterexample to deriving deadline ranking from total savings and batch
throughput alone, not a defeat of native mean-latency profiling or a new theorem.
Ordinary per-job periodic-budget replay gives both vectors and the correct
ranking when the intervention's job mapping is known. That mapping is additional
information beyond aggregate throughput; the candidate has no demonstrated way
to avoid it while remaining accurate.

The earlier 950→350 ms illustration remains preserved. Its completion-time
subtraction rule was never a full Coz/BCOZ algorithm. We do not convert either
illustration into an empirical finding about the retained Go service.

## Close work and novelty judgment

BCOZ already analyzes on/off-CPU optimization benefits and CPU contention; its
published allocated-core experiment is a different intervention from fixed-quota
CPU savings. Its scope prevents generic “handle scheduler delays” novelty.
[BCOZ paper](https://www.usenix.org/system/files/osdi24-ahn.pdf).

COZ+ extends causal profiling to large browser workloads. Its indexed primary
§3.2 states that the delay-insertion module is retained; its experiments include
controlled network bandwidth/delay. Thus end-to-end stages and external resources
already have close prior art. The direct author PDF/implementation could not be
retrieved; this is an applicability screen, not an implementation audit of COZ+.
[COZ+](https://hpcforge.eng.uci.edu/publication/sigmetrics19-coz%2B/sigmetrics19-coz%2B.pdf).

SCOZ extends virtual speedup to CPU cores, multiprocess workloads and kernel code,
with explicit idle/wakeup dependency handling.
[SCOZ, §§3.1–3.5](https://onlinelibrary.wiley.com/doi/full/10.1002/spe.2930).
VCoz already addresses causal-profile transfer by preserving relative component
speeds through CPU/memory/I/O scaling. Its reported assumption does not establish
fixed periodic-quota equivalence.
[VCoz](https://www.performance2020.deib.polimi.it/wp-content/uploads/2020/11/Performance_2020_paper_86.pdf).
The [SchedCoz proposal](https://eunomia.dev/others/ideas/) already targets
scheduler-level service debt and cgroup scope. The cited page remains a proposal;
this search did not establish a completed implementation or evaluated quota result.

The conditional CPU-only mismatch is an assumption-boundary lead, not sufficient
evidence for a new method. We have neither an empirically validated failure of
the full profilers nor reliable ranking from less information than replay.
Adding request deadlines, quota state or a refusal rule would require a further
nonroutine mechanism and evidence; no such mechanism emerged here.

**Stop this candidate at the authorized gate.** Do not build a custom profiler,
install BCOZ's modified kernel, run a new campaign or collect traces merely to
continue searching. A future reopening would need a concrete capability and an
adequate-comparator case, rather than more repetitions of this model. The useful
result now is a documented correction to our initial comparison and a clear
boundary on what aggregate optimization-benefit reporting can answer.

## Verification and preservation

The [assessment](../analysis/runtime_io_profiler_semantics_gate/20261008/assessment.json)
contains five supply cases and two deadline completion vectors. Independent
closed-form supply checks agree with the millisecond replay. All 22 native viewer
records and 11 Coz text-report checks agree with the expected report arithmetic.
Changing phase metadata leaves the inspected reporting outputs unchanged.

An initial synthetic record used CPU-plus-blocked sample metadata even for
CPU-only credit. Originals are preserved; corrected CPU-only counts were fed
through both viewers, and all 22 outputs remained identical. This correction
affects no conclusion and is recorded in the
[metadata note](../analysis/runtime_io_profiler_semantics_gate/20261008/metadata_correction.json).

All 1,911 protected scientific paths and 63 separately preserved paths remain
unchanged. The original cache-inventory caveat remains recorded in the previous
screen. Source downloads, offline arithmetic and isolated reporting functions
were the only executions; no service experiment or system setting was changed.
See the [verification](../analysis/runtime_io_profiler_semantics_gate/20261008/verification.json).
