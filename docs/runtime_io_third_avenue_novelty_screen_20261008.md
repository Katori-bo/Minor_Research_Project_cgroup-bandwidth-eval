# Third avenue: optimization-benefit profiling under a fixed CPU quota

8 October 2026. Bounded literature and offline assumption screen. No service
experiment, profiler installation, kernel change or new collection was performed.
The completed empirical manuscript and the two preceding assessments are preserved.

**Verdict: proceed only to one bounded profiler-semantics and prior-art check.**
The strongest lead screened is:

> Can causal profiling correctly predict which CPU-saving optimization improves
> offered-request deadline attainment under an unchanged periodic CPU quota?

There is a concrete timing assumption to investigate, but no demonstrated failure
of a published profiler and no established novelty. A simple quota replay already
answers the toy case below. Building a new profiler, or collecting another campaign,
is premature. This question concerns optimization benefits with quota and period
fixed; quota-period selection remains on hold and FIFO theorem work remains closed.

## Why this is a different question

The calibration-cost route asked whether accurate deadline forecasts could use
less calibration. Ordinary single busy trials sufficed on the retained cases.
The passive route asked whether normal traffic could forecast later burst misses
and support useful refusal. A distinctive, validated capability was not established.
Those results remain recorded in the
[calibration-cost assessment](runtime_io_calibration_cost_assessment_20261008.md)
and [passive-baseline assessment](runtime_io_passive_baseline_assessment_20261008.md).

The third question asks what happens after a **specified optimization**. Its
output is the change in deadline attainment, or a ranking of two interventions,
at the same offered arrivals, quota, period and deadline. Observing a large stage
delay does not by itself answer this question.

Our [original V20](runtime_io_v20_findings.md) and
[repeat V20](runtime_io_v20_repeat_findings.md) supply motivation: yielding reduced
the measured post-computation interval by about 99.5%, while the 100 ms-period
deadline change was approximately −0.088 percentage points in the original and
+1.638 points in the repeat. This is a measured stage response with conditional
end-to-end benefit. It does not identify quota timing as its cause or constitute
a failure of an optimization-benefit profiler. The yield change also does not
supply a known isolated CPU saving for the new question.

## Alternatives screened before selecting the lead

| Avenue | Closest established capability | Decision at this screen |
|---|---|---|
| Attribute each delayed request to Go scheduling, throttling or host contention | Go execution traces expose runtime events; SchedBlame attributes container CPU contention; wPerf and BCOZ connect waiting to optimization opportunities. | Do not build another tracer merely to combine these signals. No additional capability identified. |
| Cancel expired work or change admission to avoid wasted CPU | Breakwater controls overload; RAJOMON explicitly discusses wasted computation after timeouts. | Do not pursue generic shedding/cancellation novelty. No distinctive decision capability identified. |
| Predict behavior during quota changes | Kscaler already controls quota and period. Our retained experiments do not identify quota-transition behavior. | Do not select this avenue or reopen the held period route. |
| Predict optimization benefits under a fixed periodic quota | Coz and BCOZ already provide causal profiling; the interaction of timing normalization with periodic budget refill is the narrower unresolved premise. | Select for a bounded source/assumption check only. |

Sources: [Go trace](https://pkg.go.dev/runtime/trace),
[SchedBlame, September 2026 preprint](https://arxiv.org/html/2609.02052v1),
[wPerf, OSDI 2018](https://www.usenix.org/system/files/osdi18-zhou.pdf),
[Breakwater, OSDI 2020](https://www.usenix.org/conference/osdi20/presentation/cho),
[RAJOMON, NSDI 2025](https://www.usenix.org/system/files/nsdi25-xing.pdf),
and [Kscaler](https://tianyin.github.io/pub/kscaler.pdf).
SchedBlame's evaluation is preliminary; attribution accuracy is listed as planned
work. Its result must not be treated as established request-level causal ground truth.

## Closest comparison for the selected question

| Method | Assumptions and required information | Existing output | What the next gate must resolve |
|---|---|---|---|
| Coz | Selected code, CPU samples, progress points and virtual delays; synchronization handling and phase correction are part of the method. Latency mode estimates mean latency through progress counters. | Predicted throughput/mean-latency benefit from speeding selected code. | Does the complete timing correction preserve a fixed periodically replenished CPU allowance? Adding a deadline counter alone would not establish novelty. |
| BCOZ | Blocked samples include on- and off-CPU activity; special handling preserves blocking/wakeup dependencies. Supplied artifacts require a modified kernel/glibc. | Code/subclass optimization benefits, including scheduling-related benefits. | Its published CPU-contention case varies allocated core count. Check the implementation under a fixed fractional quota before asserting a separate gap. |
| COZ+ | Causal profiling adapted to Chromium stages and browser dependencies. | What-if effects of computation stages on page load time. | External dependencies and end-to-end optimization analysis already have prior art; inspect its semantics before claiming that fixed external clocks are an unaddressed issue. |
| SchedCoz proposal | Scheduler-based virtual slowdown with service-debt accounting, including multiprocess/container scope. | Proposed profiler and validation goals, rather than an evaluated paper on the cited page. | Container-scoped causal profiling is already proposed. Investigate any implementation and quota semantics. |
| Ordinary periodic-budget replay | Known CPU demand, release times, scheduling policy, quota and refill phase. | Direct conditional counterfactual completion times. | This adequate simple alternative solves our synthetic example. Any custom method must provide a useful capability beyond replay, at matched information and measurement cost. |

Coz's virtual-speedup argument subtracts accumulated delays from elapsed time;
it also handles suspended threads and sampling/phase bias. The current Linux
source calculates effective experiment duration using elapsed time minus global
delay and filters experiments with insufficient progress. These are relevant
starting points, not a source-faithful reproduction. The inspected source is
mutable `master`; the next gate must pin a revision and include the reporting
pipeline. Go wrappers already exist. Sources:
[Coz paper, §§3.3–3.4](https://arxiv.org/pdf/1608.03676),
[profiler.cpp](https://raw.githubusercontent.com/plasma-umass/coz/master/libcoz/profiler.cpp),
and [official repository](https://github.com/plasma-umass/coz).

BCOZ already demonstrates CPU-contention optimization analysis, including
32-thread workloads with varied available cores, and acknowledges that actual
optimizations can have side effects. A critique must isolate unchanged unrelated
work; an inaccurate prediction after changing other work would be a known
limitation. Sources:
[BCOZ, §§3.3 and 4.3](https://www.usenix.org/system/files/osdi24-ahn.pdf)
and [official artifacts](https://github.com/s3yonsei/blocked_samples).
The BCOZ source subdirectory could not be retrieved through this session's web
tool; its delay/reporting implementation remains uninspected.

COZ+ is established browser optimization analysis; only its primary abstract and
indexed introduction were accessible here, so its full equivalence treatment is
an outstanding close-work check. Sources:
[COZ+ publication](https://doi.org/10.1145/3341617.3326142) and
[author PDF](https://hpcforge.eng.uci.edu/publication/sigmetrics19-coz%2B/sigmetrics19-coz%2B.pdf).
The PDF's direct open returned an error. The
[SchedCoz project idea](https://eunomia.dev/others/ideas/)
is close prior art at proposal level, not evidence of a validated quota result.

## Small conditional assumption check

The separate [saved calculation](../analysis/runtime_io_third_avenue_screen/20261008/assumption_check.json)
tests only this rule: subtract cumulative CPU savings from original completion
times without recomputing quota depletion and refills. It does **not** execute
Coz/BCOZ or map their complete estimator to request deadlines.

Assume ten jobs available at time zero, one continuously runnable serial worker,
50 ms CPU work per job, a full initial 50 ms budget replenished every 100 ms,
no competing work, overhead, carryover or burst credit. A real optimization
reduces each job's CPU work to 20 ms. Every job has a 500 ms absolute deadline,
with completion at exactly 500 ms timely.

| Calculation | Final completion | Miss fraction |
|---|---:|---:|
| Original periodic execution | 950 ms | 50% |
| Original completions minus cumulative 30 ms/job saving | 650 ms | 30% |
| Recompute execution with genuinely reduced CPU work | 350 ms | 0% |

Original completions are 50, 150, …, 950 ms. Subtract-only completions are
20, 90, 160, 230, 300, 370, 440, 510, 580, 650 ms. Real optimized completions
are 20, 40, 110, 130, 150, 220, 240, 310, 330, 350 ms. Actual CPU savings
allow work to avoid refill waits; subtracting CPU time afterward misses that effect.

Three declared controls agree exactly: nonbinding budget over the workload,
short nonthrottled execution, and reduced work that leaves the two completion
times in their original budget periods. Eight completion vectors were checked
against an independent inverse cumulative-supply formula; every period respects
its CPU budget. The design and script hash were saved before generating results.
These are designed examples, not prospective workload evidence.

This illustrates non-equivalence in a simple periodic server. It is **not** a new
theorem, published-method defeat, optimization-ranking reversal, or Linux result.
Linux uses distributed runtime slices and other details absent here; see
[CFS bandwidth documentation](https://docs.kernel.org/scheduler/sched-bwc.html).
The simple replay comparator obtains the correct answer with the same toy inputs.

## Necessary and sufficient next gate

One offline deliverable, before a new prototype or campaign:

1. Pin Coz and BCOZ source revisions; inspect delay accounting, synchronization,
   blocked samples, phase correction, progress counters and final reporting.
   Resolve COZ+ and SchedCoz applicability. Do not substitute the toy subtraction
   rule for a published method.
2. Construct the smallest source-faithful case, retaining absolute arrivals,
   deadline clocks and quota refills. Compare known actual CPU-saving execution,
   full profiler correction and ordinary periodic-budget replay. Include
   nonbinding-quota controls and account for sampling/profiler CPU consumption.
   State whether the profiler's output even supports the requested endpoint.
3. Give one proceed/stop verdict. Proceed only if a specific capability survives
   prior art and adequate replay—for example, reliable intervention ranking from
   substantially less event information with a validated error/cost advantage.
   The advantage is a proposed requirement, not a result. Establish that any
   discrepancy arises from periodic budgeting rather than side effects or a
   mismatch between mean latency and deadline attainment.

**Stop** if full correction resolves the witness, close work already provides
the capability, or ordinary replay suffices at comparable information and cost.
A budget-aware replay implementation, another trace view, a Go port or changing
the output metric alone is insufficient justification for a research method.

If the gap survives, the first new data would need isolated actual CPU-saving
interventions with matched arrivals/quota, appropriate binding and nonbinding
controls, and qualified profiler/observer effects. Retained elapsed worker times
and coarse counters do not identify isolated CPU savings or quota refill state.
Collect additional runnable/throttle/budget information only when the surviving
method demonstrably needs it. Repeating the old campaigns does not supply these
missing counterfactuals. Collection remains stopped.

## Preservation and audit

The computation checked all 1,911 protected scientific paths and separately
preserved the earlier screen artifacts and eight paper/background documents.
Every previously sealed file remains intact. The calibration-cost artifact
directory already contains one extra unsealed verifier bytecode cache; therefore
its exact directory inventory no longer matches its root seal. The cache is
reported and preserved, without deleting it or rewriting the original seal.
The other two screen inventories match. See the
[prior seal audit](../analysis/runtime_io_third_avenue_screen/20261008/design/prior_seal_audit.json)
and [verification](../analysis/runtime_io_third_avenue_screen/20261008/verification.json).
Only current-status pointers are updated; their previous contents are retained
with the new screen. No original empirical result, threshold or paper was edited.
