# Prior work, existing remedies, and the next unanswered question

Reviewed 2026-10-03. This is a focused comparison of primary papers, Go issues and versioned source, kernel documentation, and our existing measurements. It is not a completed systematic literature review or certification of novelty. No new performance collection was launched.

## Decision

**Test an existing configuration remedy in the unresolved bursty case before building another queue recorder.** Generic CPU-quota tail latency, CPU parallelism tuning, scheduling fairness, cooperative yielding, and latency-aware admission all have precedents. We should not claim their discovery.

The important local finding is that the completed follow-up already compared `GOMAXPROCS=1` and `2` under steady overload. It improved several outcomes. That comparison did not include `GOMAXPROCS=1` with the bursty workload used in the delayed-handler investigation. The next experiment should fill that specific hole, rather than repeat the steady comparison or assume tuning has been exhausted.

## 1. Mechanism and solution map

“Implemented” below identifies an available implementation; it does not mean verified efficacy for our workload. “Proposed” does not establish a released fix. Our relevance assessments are inferences from the cited sources and local evidence.

| Prior work / primary source | Mechanism and remedy | Status and tested workload | Match and remaining limitation |
|---|---|---|---|
| [Go issue #73964](https://github.com/golang/go/issues/73964), 2025 | Repeated `runnext` selection can bypass regular local work; a short-running goroutine may park before preemption is honored. Proposed remedies include periodic local FIFO service and honoring pending preemption at scheduler entry. | Retrieved issue is open, marked NeedsInvestigation. Reproducer uses very short sleeps, `GOMAXPROCS=2`, with a reported pause exceeding one second. | Closest runtime mechanism precedent, but timer wakeups differ from our HTTP/channel path. Final global selection does not establish earlier local or global residence. No verified released fix for this exact mechanism was found in this review. |
| [Go issue #52934](https://github.com/golang/go/issues/52934), 2022 | Continuous new goroutine launches can delay existing runnable work. | Retrieved issue remains open. Reproducer reports Go 1.18/development 1.19 on Darwin arm64; delay occurs with `GOMAXPROCS=1` as well as other settings. | Establishes earlier Go scheduling reports. It also prevents treating `GOMAXPROCS=1` as a universal fairness cure. No fractional-quota HTTP workload is established by this reproducer. |
| [Go's container-aware default](https://go.dev/blog/container-aware-gomaxprocs), shipped in Go 1.25; [pinned Go 1.26.1 quota calculation](https://raw.githubusercontent.com/golang/go/go1.26.1/src/runtime/cgroup_linux.go), [runtime API documentation/source](https://raw.githubusercontent.com/golang/go/go1.26.1/src/runtime/debug.go) | Default parallelism incorporates CPU quota and affinity; explicit configuration disables automatic adjustment. The pinned quota calculation rounds up and retains a minimum of two when affinity permits. | Implemented runtime policy. With our two-CPU affinity and 0.5-CPU quota, its default calculation returns two. | Our explicit setting of two is not evidence of an old failure to detect containers. Automatic detection alone would not necessarily change this experiment. The minimum is a policy choice, not proof that two minimizes latency here. |
| [Uber automaxprocs](https://github.com/uber-go/automaxprocs); v1.6.0 [rounding source](https://raw.githubusercontent.com/uber-go/automaxprocs/v1.6.0/internal/runtime/runtime.go) and [configuration source](https://raw.githubusercontent.com/uber-go/automaxprocs/v1.6.0/maxprocs/maxprocs.go) | Default rounding floors quota-derived parallelism, with minimum one. An explicit `GOMAXPROCS` environment setting is honored. | Implemented library. README reports load-balancer throughput and tail-latency measurements under a two-CPU quota; tuning has a latency/throughput tradeoff there. | At 0.5 CPU, its default can select one if our explicit setting is removed. Directly setting one tests that resource choice without installing the library. Its published load-balancer numbers do not predict our bursty result. |
| [Jeffery, Jensen and Mortier, 2024](https://arxiv.org/html/2407.11582v1), *Reducing Tail Latencies Through Environment- and Neighbour-aware Thread Management* | CPU/thread overcommitment and quota enforcement worsen latency; manually align thread counts, allow bursting, or adapt to neighbors. | Go/Rust Fibonacci workers, uniform open-loop demand, five-second trials with five repeats on one 16-logical-CPU machine. Later analysis excludes application queue delay; a neighbor-aware pool trades latency against throughput. | Direct quota/parallelism precedent. Its default-Go discussion predates Go 1.25. It does not provide a queue-residence account for our network-ready HTTP cohort, but supports testing existing tuning first. |
| [Kernel bandwidth control](https://docs.kernel.org/scheduler/sched-bwc.html), [cgroup v2 interface](https://docs.kernel.org/admin-guide/cgroup-v2.html) | Quota exhaustion throttles execution until replenishment; parent limits and CPU-local accounting matter. Burst support accumulates unused bandwidth. | Implemented kernel interfaces. `cpu.max.burst` is available in cgroup v2; our diagnostic target uses zero burst allowance. | Period/quota/burst changes are existing remedies to evaluate, with different burst permissions and accounting costs. Removing the quota grants more resources. Aggregate throttled time cannot attribute each HTTP wait. |
| [Muller, Westrick and Acar, ICFP 2019](https://cs.nyu.edu/~shw8119/19/icfp-fairness.pdf), *Fairness in Responsive Parallelism* | Explicit priority shares and scheduling opportunities can combine responsiveness with progress for lower-priority work. | Formal scheduling principle and a Parallel MLton implementation; interactive and CPU benchmarks on up to 70 cores. Section 4.5 leaves proof of the practical algorithm's specific guarantees to future work. | Fair scheduling and bounded response are established research directions. This is not a Go patch or a validation under our half-CPU bandwidth contract. It informs what to measure, not an automatic bound on our waits. |
| [Li et al., 2016](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/06/paper-1.pdf), *Work Stealing for Interactive Services to Meet Target Latency* | Tail-aware scheduling balances admitting new requests and assigning parallel execution to existing requests. | Implemented in TBB 4.3; open-loop synthetic work with Bing/finance-derived work distributions, Poisson and heavy-tailed arrivals, on 16 cores. | Admission versus execution is already a studied tradeoff. Our four workers run fixed serial jobs, and the unresolved interval precedes handler entry. This source does not establish a remedy for that interval under a fractional quota. |
| [Shinjuku, NSDI 2019](https://www.usenix.org/conference/nsdi19/presentation/kaffes) | Fine-grained preemption prevents short requests waiting behind long execution. | Research OS using virtualization support; mixed-service-time workloads including RocksDB point/range queries. | Shows that preemption for tail latency has implemented precedents. Replacing the OS/runtime is a substantially different intervention from configuring stock Go with a fixed quota. |
| [Shenango, NSDI 2019](https://www.usenix.org/system/files/nsdi19-ousterhout.pdf) | Rapid core allocation responds to runnable work and incoming packets under variable demand. | Implemented runtime/IOKernel, dedicated control core and kernel-bypass networking; includes memcached and batch colocation. | Bursty demand and delayed reaction are established problems. Dynamic allocation and dedicated control resources differ from preserving our strict half-CPU budget and ordinary Go networking. |
| [Caladan, OSDI 2020](https://www.usenix.org/conference/osdi20/presentation/fried) | Fast core placement controls cache, memory-bandwidth and hyperthread interference under changing resource demand. | Research scheduler with dedicated control core and kernel module; memcached with colocated best-effort workloads. | Useful alternate cause/solution class. Our current evidence does not establish neighbor interference; affinity is not exclusive isolation. This implementation is not a configuration-only fix for our setup. |
| [Wang et al., Autothrottle, NSDI 2024](https://www.usenix.org/system/files/nsdi24-wang-zibo.pdf) | Use throttling and application SLO feedback to adjust microservice CPU allocations. | Implemented bi-level controller; Train-Ticket, Social-Network, Hotel-Reservation; constant/noisy/diurnal/bursty traces and longer production traces. | Direct evidence that quota-related SLO control is studied. It changes CPU allocations, whereas our immediate comparison preserves a fixed 0.5-CPU allocation. |
| [hnes/cpuworker](https://github.com/hnes/cpuworker) | Application-level CPU task scheduling separates CPU-heavy tasks from interactive work. | Repository labels itself work in progress; demonstrates checksum tasks mixed with a short HTTP delay endpoint, including an AWS example at `GOMAXPROCS=16`. | An implemented prototype precedent for cooperative application remedies. Its demo is not a controlled validation at our quota, and the documented execution-resource assumptions differ. |

Additional screened match: [Han, 2025, *AI-Driven Predictive Modeling for System Performance and Resource Management in Microservice Architectures*](https://ashpress.org/index.php/jcts/article/download/229/182/377) mentions quota and preemption variations. Its inspected sections evaluate response-time **prediction error** with a Transformer model. They do not supply a Go queue-service fix or a measured runnable-to-handler causal explanation. Treat this as adjacent prediction work; this review did not independently verify its dataset or reproduce its results.

## 2. Compare the remedies with our existing results

The historical [follow-up trial report](../results/followup/all-in-one-v2/full/analysis/report.md), frozen [matrix](../results/followup/all-in-one-v2/full/matrix.json) and passing validation contain five trials per setting at 176.41 requests/s **steady overload**, four workers, 44,000 iterations, a 128-slot queue and `50000 100000` quota. Frozen build source specifies Go 1.26.1. Each trial measured 60 seconds after 20 seconds of warmup.

| Median across five trials | GOMAXPROCS=2 | GOMAXPROCS=1 | Observed change |
|---|---:|---:|---:|
| Successful request E2E p99 | 2,429.97 ms | 1,181.66 ms | 51.4% lower |
| Successful requests/s in measurement window | 134.40 | 152.33 | 13.3% higher |
| Rejection fraction | 22.54% | 12.21% | 10.34 percentage points lower |
| Server CPU per completed job | 3,722.98 us | 3,280.30 us | 11.9% lower |
| Achieved CPU usage | 0.5001 cores | 0.4997 cores | Essentially the same nominal-budget utilization |
| Fraction of periods with throttling | 99.84% | 99.84% | Throttling persists |

These are ratios/differences of trial medians, not paired effect estimates or percentiles of pooled requests. They are existing measurements, not a new experiment. The lower CPU cost increases effective service capacity, so this is **not a fairness-only intervention**. Lower rejection alongside lower successful latency is encouraging, but the service is still overloaded in that study.

The summary was independently recomputed with [this read-only script](../analysis/runtime_io_prior_art_review/summarize_existing.py); [JSON](../analysis/runtime_io_prior_art_review/existing_followup_summary.json) records ranges, selected trial IDs, configuration checks and unchanged input hashes. The frozen 50-trial matrix has no bursty `GOMAXPROCS=1` cell. This establishes a gap in that matrix, not an assertion that no researcher has tried such a configuration.

Other evidence restricts the interpretation:

- V8 worker yielding improved pre-handler delay but moved pressure into application queueing/rejection. An improvement in one interval is not sufficient to accept a fix.
- The audited V9 pending-preemption policy was insufficient. A negative result for that policy does not disprove the separate FIFO-service proposal or runtime scheduling generally.
- V11 compares observation on/off under the same candidate policy. It is not a stock-versus-patch experiment.
- The [offline V11 decomposition](../analysis/runtime_io_v11_causal_planning/report.md) places essentially all of the seconds-long linked waits before final selection; the maximum selection-to-dispatch interval is 31.94 microseconds. This localizes the symptom, but does not identify its earlier queue path or remove possible quota pauses before selection.
- Earlier period comparisons are workload-dependent. Do not treat “shorter quota period fixes the tail” as established, or repeat a broad period sweep without a mechanism question.

## 3. The specific question and falsifiable hypothesis

**Question:** In this bursty half-CPU HTTP service, does an existing parallelism setting resolve the long pre-handler symptom while preserving useful throughput and admission outcomes? If delay remains, which queue-service pathway accounts for it?

**Initial hypothesis:** Changing stock Go from two execution processors to one substantially reduces long handler-entry delays in the original bursty workload at the same quota. This is suggested by the steady results and parallelism literature. It is not established by them.

One processor still multiplexes HTTP and CPU goroutines and remains subject to bandwidth throttling. Success would identify an effective configuration remedy for this workload, not automatically prove a particular `runnext` mechanism. Failure or residual long entry waits would justify localization under the residual condition.

The reviewed sources do not answer this exact combination of workload, version, resource contract, interval and outcome accounting. That is a **candidate gap**, not a claim of globally unaddressed prior work. Before presenting it as novel, follow citations and related implementations around the closest matching mechanism, including subsequent Go changes.

## 4. Small comparison before further instrumentation

Prepare eight stock-Go 1.26.1 trials, four pairs: A=two processors, B=one; AB/BA/BA/AB. Keep four application workers, queue 128, iterations 44,000, 0.5 CPU at 100 ms, burst allowance zero, affinity and the 113.21 requests/s mean with the original five-second low/high phases. Keep yielding, candidate scheduler patches, native Go tracing and decision/queue observers off. Use identical application/client stage instrumentation in both arms.

Use 20-second warmup and 60-second measurement, giving six full burst cycles per trial, with the established thermal settling and drains. Preserve arrival schedules/seeds across paired cells. Record actual send timing so client delays cannot be mistaken for server scheduling delay. Read back configuration and child/ancestor limits, and freeze sources, trial order and analysis before launch. First validate the stock build and the existing handler-entry clock mapping; these preparations are not yet performed.

Primary observations are the rate of handler-entry delays at least one second, and bounded scheduled/send-to-entry timing. Report how many offered requests have certainly/possibly entered by the fixed one- and five-second horizons. Requests with no observed entry remain explicit missing/censored or no-entry outcomes; they cannot disappear from denominators. Separate client send delay from server entry delay.

Also report successful E2E p99, successful throughput, rejection, timeout/error fractions, application queue waiting, late completions, CPU/job, cgroup usage and throttled-period fraction. Entry timing is not exact network-ready-to-selection timing: this stock comparison tests remedy sufficiency, not exact ready-queue causality.

Proposed practical screen, to freeze before collection: each of the four pairs must show fewer certainly long entry waits, the ratio of median per-trial long-entry rate must be <=0.5, and median successful p99 must fall by >=50%, without failure fraction rising by >0.001 or success throughput falling by >5%. Classifications must remain valid under the clock bounds and coverage checks. These are diagnostic acceptance criteria, not statistical significance or production SLO certification. A baseline without the symptom or inadequate coverage makes the comparison inconclusive. A smaller effect remains evidence of partial mitigation, not proof of no effect.

## 5. What the outcome permits us to claim

| Outcome | Next action and permitted contribution |
|---|---|
| Existing tuning passes the screen | Report known remedy validated for this case; do not claim a new scheduler fix. Decide whether a minimal reproducer or a clearly different limitation merits further research. |
| Entry improves but CPU/job changes materially | Quantify capacity improvement and scheduling changes together; do not attribute the entire benefit to fairness. |
| Entry improves but queueing or failures worsen | Remedy is insufficient for service outcomes; investigate admission/delay migration with the already measured boundaries. |
| Long entry waits remain with valid stock measurements | Build the bounded queue-history observer for that residual symptom, with its own observer control. Verify residence before choosing a global/local service intervention. |
| No baseline symptom, unstable environment or missing linkage | Fix the named measurement problem; no unrelated parameter sweep. |

Only after a verified queue pathway should the scheduler/period factorial in the [causal investigation plan](runtime_io_causal_investigation_plan.md) proceed. If an existing remedy is sufficient, acknowledge that result and redirect or narrow the contribution. If a limitation survives, novelty may lie in a demonstrated failure condition, causal interaction, measurement method or minimal remedy—each must be checked against the closest prior work before being claimed.

## Review coverage and what remains

Search families included Go quota/HTTP tail latency, goroutine/runnext starvation, issue fixes and Gerrit references, container parallelism libraries, quota-period/burst mechanisms, and interactive/fair/preemptive scheduling. The strongest matches above were checked in primary text or versioned source. Some issue comments and a historical kernel mailing-list page were not fully retrievable; no absence-of-fix conclusion rests on those fetch failures. Current issue status reflects retrieved pages, not a complete release-history audit.

Remaining literature work is targeted citation-following around whichever mechanism survives the known-remedy comparison, plus an explicit check of later Go fixes and matching implementations before claiming originality. Help from the user is optional: candidate paper titles/links or a venue requirement would sharpen that review. None is required to prepare this bounded comparison.

## Implementation update, 2026-10-03

The bounded stock-Go comparison is now built and functionally verified. The [frozen-design protocol and launch instructions](runtime_io_v12_parallelism_commands.md) make the screen conservative under clock uncertainty and unknown entries. [Preparation evidence](runtime_io_v12_parallelism_verification.md) records 105 passing Python tests, build-time Go tests and two short no-quota HTTP fixtures. No research trials have started. The earlier proposal above remains the rationale; the implementation protocol supplies the executable details and refined bounds.
