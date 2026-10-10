# V12 tradeoff audit and comparison with prior work

Reviewed 2026-10-03. This is an offline, post-hoc review of the eight completed stock-Go trials. No new performance trial was run. The original result directory remains unchanged; the audit verifies its completion seals and hashes every result file before and after reading it.

**The remedy succeeds for the original long-entry symptom, with a tradeoff concentrated in the high-load part of the burst cycle. Overall successful-request p50 worsens in every pair, but low-phase p50 slightly improves in every pair. High-phase p50 worsens in three pairs and improves in one. Waiting around the median shifts into both the application queue and the interval between worker completion and handler resumption. Mean successful latency, tail latency and failure outcomes improve. The broad median-versus-tail tradeoff already has a direct published engineering precedent.**

The [prior-work comparison](prior_work_comparison.md) records what each close source explains, its tested conditions and the limits of the match. The differences identified there are differences in coverage, not established research novelty.

![Paired medians, burst-cycle behavior and same-request stage accounting](tradeoff.png)

## 1. Evidence and measurement definitions

Inputs are the sealed [V12 report](../../results/diagnostic/runtime-io-v12-bursty-parallelism-1/session/analysis/report.md), its raw load-generator requests and server entry/worker/handler events. [audit_tradeoff.py](audit_tradeoff.py) reproduces the original p50 and p99 exactly, verifies complete offered-ID and admitted-work linkage, checks identical scheduled arrival positions within each pair, and retains original clock brackets. [summary.json](summary.json) contains statistics, validation checks and before/after input hashes. Every result file had the same hash after the audit.

Both arms have the same 0.5-CPU quota, 100 ms quota period, zero extra bandwidth burst allowance, four application workers, queue capacity 128 and 44,000 SHA iterations. The mean arrival rate is 113.21 requests/s. Each 10-second arrival cycle has five seconds at 56.605 requests/s and five at 169.815 requests/s. Each trial contains six cycles after warmup, with 6,793 offered requests: 1,699 scheduled in low phases and 5,094 in high phases. Thus about three quarters of requests belong to high phases, despite equal phase durations.

Primary phase grouping uses each request's **scheduled arrival**, not its eventual admission or completion. Intervals are half-open: seconds [0,5) of each cycle are low, [5,10) are high. Server entry and worker-start phase transitions are also retained using the full clock interval; a bracket crossing a boundary is ambiguous. The stage clock uncertainty is 0.100–0.153 ms across trials. No midpoint is substituted.

Successful E2E percentiles are conditional on success. Failures are separately counted over all offered requests; their client terminal-event latency is retained but is not presented as successful service. Work durations for all admitted jobs, including timeouts, come from server events. Four trial pairs remain the replication units; neither 54,344 requests nor six cycles per trial are treated as independent experimental replicates. All phase, rank-cohort and deadline analyses here are exploratory and were not part of the original predeclared screen.

## 2. Is the median penalty consistent?

Values are milliseconds, nearest-rank percentiles of successful requests. Each row compares one pair; the trial order was 2/1, 1/2, 1/2, 2/1.

| Pair | Overall p50, two → one | Low-phase p50, two → one | High-phase p50, two → one | Overall p99, two → one |
|---|---:|---:|---:|---:|
| 1 | 240.43 → 355.81 | 5.68 → 5.53 | **567.99 → 448.50** | 2449.21 → 882.30 |
| 2 | 156.58 → 348.36 | 5.70 → 5.52 | 173.92 → 442.97 | 4131.53 → 873.17 |
| 3 | 159.91 → 355.12 | 5.68 → 5.56 | 177.88 → 450.97 | 4124.47 → 887.26 |
| 4 | 158.69 → 359.66 | 5.68 → 5.52 | 178.50 → 452.77 | 4025.70 → 878.52 |

The overall p50 penalty is present in 4/4 pairs. A universal phase-level penalty is unsupported: low-phase medians are slightly better in 4/4 pairs, and high-phase pair 1 also improves. The small low-phase differences are descriptive observations, not a significance claim.

| Median of the four trial statistics | Two processors | One processor |
|---|---:|---:|
| Overall successful p50 | 159.30 ms | 355.47 ms |
| Overall successful p99 | 4075.09 ms | 880.41 ms |
| Low-phase successful p50 | 5.68 ms | 5.52 ms |
| Low-phase successful p99 | 1124.29 ms | 801.07 ms |
| High-phase successful p50 | 178.19 ms | 449.73 ms |
| High-phase successful p99 | 4167.42 ms | 891.67 ms |

These are medians of trial quantiles, not quantiles of pooled requests. A whole-trial quantile is not an average of the low- and high-phase quantiles. Pair 1 is a concrete example: its overall median worsens even though both separate phase medians improve. Quantiles describe distribution shape and cannot identify how every individual arrival position changes.

The **mean** successful latency improves in every pair: 501.22 → 342.53, 530.11 → 336.67, 523.52 → 343.89 and 510.53 → 343.91 ms. The worse median therefore coexists with a lower mean and a much shorter tail.

## 3. Where in the burst does this happen?

The one-second buckets below group requests by scheduled second within the 10-second cycle, pool the six such buckets inside each trial, and then take the median of the four trial p50 values. They do not classify load at the moment a handler finally runs.

| Scheduled second within cycle | Two processors p50 | One processor p50 |
|---|---:|---:|
| 0–1, early low | 592.88 ms | 424.73 ms |
| 1–2, low recovery | 204.20 ms | 5.47 ms |
| 2–3, low | 5.49 ms | 5.42 ms |
| 3–4, low | 5.42 ms | 5.40 ms |
| 4–5, low | 5.40 ms | 5.39 ms |
| 5–6, early high | 65.91 ms | 47.00 ms |
| 6–7, high | 176.25 ms | 284.07 ms |
| 7–8, high | 185.09 ms | 437.58 ms |
| 8–9, high | 190.97 ms | 584.70 ms |
| 9–10, late high | 455.09 ms | 736.63 ms |

This localizes the median cost mainly to the middle/later part of high phases. It also shows quicker recovery in the next low phase with one processor. A low arrival rate does not imply an empty system: work from earlier high phases remains outstanding. In the first low phase of each trial, p99 is around 6 ms in both arms; later low-phase p99s are much larger. The scheduled-phase grouping and retained worker-start transitions support a carryover interpretation without equating phase labels to instantaneous queue occupancy.

Across all four trials, 2,267 high-phase offered requests with two processors enter in a subsequent low phase, compared with 372 with one. This includes all client outcomes. Another 221 versus 72 enter during the final drain. A few low-phase arrivals close to a boundary enter in high phases, and uncertain boundary crossings remain explicit. These are transition counts, not exact network-ready or scheduler-residence measurements.

## 4. How much waiting moves into the application?

| Median of four trial statistics | Two processors | One processor |
|---|---:|---:|
| Overall queue p50, all completed jobs | 0.002 ms | 127.22 ms |
| Overall queue p99, all completed jobs | 909.17 ms | 609.02 ms |
| Overall mean queue wait, all completed jobs | 92.86 ms | 192.64 ms |
| Low-phase mean queue wait, all completed jobs | 71.97 ms | 48.68 ms |
| High-phase mean queue wait, all completed jobs | 102.55 ms | 240.48 ms |

Queue waiting becomes more common, while its tail falls. Mean queue waiting is not worse in every pair: pair 1 improves from approximately 253.70 to 192.15 ms; the other three increase. This is another reason to retain pairs rather than rely only on an aggregate.

For a request-level explanation, select each trial's successful requests at E2E ranks 45–55%, calculate stage **means within that same cohort**, then weight the four trials equally. This illustrates requests near each arm's own median. It is not a decomposition of the reported p50 and is not a matched-request causal estimate.

| Stage mean for the median-rank cohort | Two processors | One processor |
|---|---:|---:|
| Scheduled arrival → handler entry, clock lower–upper | 151.675–151.799 ms | 130.170–130.284 ms |
| Handler entry → admission | 0.003 ms | 0.080 ms |
| Admission → worker start | **4.358 ms** | **147.202 ms** |
| Worker-start → completion wall span | 20.867 ms | 18.357 ms |
| Worker completion → handler resume | **2.232 ms** | **58.080 ms** |
| Handler resume → client completion residual, clock lower–upper | 0.079–0.203 ms | 0.085–0.199 ms |
| Mean E2E for this rank cohort | 179.338 ms | 354.088 ms |

The increase in queue mean is approximately 143 ms and in post-work mean approximately 56 ms in this cohort comparison. Entry waiting decreases by about 21.5 ms. The audit checks the complete duration identity for each successful request: entry upper bound plus response lower bound and all internal stages equals its E2E duration (likewise entry lower plus response upper). It never adds separately calculated stage percentiles. Signed residuals are retained.

The post-work marker is recorded when the handler executes the receive-result path, not the instant it becomes runnable. Its interval can contain event storage, reply publication, handler scheduling and quota pauses. Worker spans are wall time, not CPU time. Neither measurement proves a particular runtime-queue policy.

An additional check matches the identical scheduled request IDs across each pair, retaining only positions that succeeded in both trials. The fraction faster with one processor is 64.3%, 41.2%, 45.9% and 43.2% across the four pairs. Mean E2E differences remain favorable in every pair, approximately −169, −196, −185 and −170 ms. These match offered positions across separate executions; they do not turn requests into independent replicates. The excluded positions are exactly the failed outcomes reported next, not discarded evidence about overall service quality.

## 5. Failures and late completions

Counts sum the four trials per arm; each arm offered 27,172 requests.

| Outcome | Two processors | One processor |
|---|---:|---:|
| Successful responses | 26,795 | 27,172 |
| Queue-full HTTP rejections | **371** | **0** |
| Client timeouts | **6** | **0** |
| Other client errors | 0 | 0 |
| Observed entries delayed at least one second | 2,675 | 0 |
| Missing handler entries | 0 | 0 |
| Successful responses completed after the 60-second window | 619 | 480 |
| Server context already gone at work completion | 6 | 0 |
| Server work certainly finished after the client's terminal event | 6 | 0 |
| Server work finished after the window, clock certain–possible | 585–585 | 439–440 |

Two-processor rejections by pair are 178, 43, 87 and 63; timeouts are 0, 2, 3 and 1. Four rejections were scheduled in low phases (all in pair 3), the other 367 in high phases. All six timeouts were scheduled in high phases. None of these failures occurs with one processor.

All admitted jobs eventually complete in both arms, including the six jobs whose clients time out. Their measured entry delays are approximately 4.04–4.25 seconds and their queue waits approximately 0.889–1.177 seconds; original timestamps and outcomes are retained in [failed_requests.csv](failed_requests.csv). The server's cancellation-at-completion flag and clock-bounded comparisons both establish six completions after the client has ended its request.

The possible-after-client upper bound is 796 with two processors and 5 with one, because a 0.1–0.15 ms clock bracket can overlap client completion even for otherwise successful responses. These possible counts are **not** counts of proven wasted work. Clock uncertainty matters for closely spaced completion events, although it cannot explain the seconds-long entry delays.

Finishing after the measurement boundary is a normal drain outcome and differs from finishing after a client timeout. The one-processor setting reduces both successful response carryover and proven abandoned completions. Measurement-window throughput and full offered-cohort accounting therefore support the remedy together.

## 6. The answer depends on the response-time target

These exploratory deadline fractions count **successful completions within the named E2E deadline over every offered request**. Rejections and timeouts never count as timely successes. Values below are medians of four per-trial fractions; deadlines were selected for this review, not predeclared SLOs.

| Deadline | Two processors timely success | One processor timely success |
|---|---:|---:|
| 100 ms | 36.43% | 33.76% |
| 500 ms | **73.75%** | **65.71%** |
| 1 second | **82.52%** | **99.99%** |
| 5 seconds | 98.87% | 100.00% |

Thus one processor is excellent for eliminating the long tail here, but it does not dominate every deadline. Choosing a tighter latency objective could change which tradeoff is preferable. This observation is not itself novel: the literature comparison includes an existing p50-versus-tail example and explicit burst-parallelism policy discussions.

## 7. What is established, and what remains unresolved?

Established locally: the original remedy screen passes; the whole-trial median cost is consistent; its phase-level form is uneven; the median-rank cost includes queue and post-work waiting; fewer long delays coexist with fewer failures and fewer completions after the window. This establishes a service-outcome tradeoff under one fixed workload/resource contract.

Unresolved locally: how much improvement comes from changed effective capacity, quota timing, Go scheduling, or other efficiency effects. Median CPU time per completed job falls from approximately 3.902 to 3.663 ms. This includes accounting-window overhead and is not a direct measurement of peak service capacity. The server uses about 0.429 versus 0.409 CPU on average; throttled-period fractions remain approximately 68.0% versus 60.6%. These aggregate counters cannot assign a particular pause to a request.

The run passes the retained environment checks, but affinity is not exclusive CPU isolation. Median sampled package temperatures are higher in the one-processor trials (about 71.9–72.9°C versus 66.3–68.4°C). These are retained observations, not proof of thermal throttling or an explanation of CPU/job changes. No direct frequency/GC/scheduler attribution or observer-equivalence test is supplied by this audit. Native runtime observers were disabled; application/client stage instrumentation and host monitoring remained present in both arms.

The evidence supports comparison with existing knowledge before any further instrumentation. The [focused literature review](prior_work_comparison.md) finds direct precedent for the broad tradeoff and leaves the detailed local mechanism unassigned. It does not establish a new scheduler defect, a globally missing solution, or a publication claim. No follow-up experiment is automatically launched.

## Reproduce this offline review

From the repository root:

```bash
python3 analysis/runtime_io_v12_tradeoff_review/audit_tradeoff.py
MPLCONFIGDIR=/tmp/v12-tradeoff-mpl venv/bin/python analysis/runtime_io_v12_tradeoff_review/plot_tradeoff.py
```

The first command reads and verifies existing results and writes only review outputs. The second plots those outputs with the existing project environment. The audit CSVs cover trial/phase statistics, cycle/phase statistics, second-of-cycle statistics, paired phase comparisons, same-cohort stage means and every failed request. [figure_provenance.json](figure_provenance.json) records the plotting inputs and generated figure hashes. The human interpretation in this report and the literature review is distinct from generated statistics.
