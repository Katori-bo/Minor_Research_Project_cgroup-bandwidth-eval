# V15 marker progression review — 2026-10-04

**All 24 trials and original frozen-source, build-bundle, environment, attempt and analysis seals verified. Technical completion succeeded; the marker cost screen failed.** Derived review files are outside the sealed result session.

| Arm | Median timely 500 ms | Median CPU/job µs | Median successful p99 ms | Median queue p99 ms | Median post-work p99 ms |
|---|---:|---:|---:|---:|---:|
| legacy | 74.38% | 3656.08 | 768.08 | 497.75 | 161.83 |
| rebuilt_zero | 68.36% | 3686.31 | 831.07 | 551.83 | 161.35 |
| before_one | 60.15% | 3749.46 | 956.10 | 695.36 | 161.06 |
| bracket_two | 61.56% | 3750.95 | 942.96 | 674.69 | 161.05 |
| boundary_five | 61.05% | 3750.89 | 951.38 | 687.32 | 161.59 |
| v14_clocks | 60.22% | 3756.02 | 955.10 | 695.35 | 161.65 |

Values are medians across four independent trial blocks, not pooled request percentiles. Use paired deltas in the sealed report for treatment comparisons. All six arms offer 27,172 requests; all 163,032 offered requests eventually succeed. Zero failures does not imply zero deadline misses.

## Findings and attribution limits

1. **The rebuild control fails.** Legacy→rebuilt_zero loses 3.62–7.42 percentage points of 500 ms timely success in all four blocks (paired median loss 6.42 points), with CPU/job +0.68–1.02%. This happens with zero added calls and matching normalized worker/job/SHA-work instructions in the static audit. The original and rebuilt full binaries are different; health/metrics metadata and binary layout/build details still differ. Normalized hot-function identity was insufficient to establish a behaviorally neutral control. These observations do not identify whether layout, runtime state, control-plane effects or host/order variability causes the gap.

2. **Moving the five markers into the original job path does not recover legacy performance.** Legacy→boundary_five loses 12.91–13.56 points (paired median 13.42), CPU/job rises 2.56–2.64%, and successful p99 rises 23.31–24.06%. Both primary timely success and p99 exceed declared margins in every pair. The remaining V14 worker-path/order-check bundle changes timely success by −1.22 to +0.19 points versus five inline calls. It is a smaller difference than the main deficit, though it does not pass every practical pair. This weakens the replacement worker loop as a sufficient explanation of the large penalty.

3. **There is no monotonic clock-count penalty.** Rebuilt_zero→before_one loses 6.70–9.64 points and adds 1.49–1.83% CPU/job, but the first treatment also caches the origin and changes generated code. Adding a post-send call improves timely success by 0.62–1.97 points in all four pairs while CPU/job stays nearly flat (−0.009% to +0.217%). Adding three event-boundary calls then changes timely success by −2.00 to +0.35 points, also with nearly flat CPU/job. Do not infer that clock calls are harmless, that a second call is a remedy, or that each call has the same measured marginal cost. Failed rebuild control and placement/generated-code/host ambiguity prevent a pure clock-cost conclusion.

4. **Most of the observed end-to-end penalty accompanies a larger queue.** Median trial queue p99 goes from about 498 ms in legacy to 552 ms in rebuilt_zero and 675–695 ms in marked arms. Median trial post-work p99 remains about 161–162 ms. Cumulative throttled-period fractions also rise from median 0.584 in legacy to approximately 0.613–0.616 in marked arms. This is consistent with small service-demand differences being amplified during the overloaded burst under fixed quota. It does not establish an exact request-level throttle mechanism, and marginal stage percentiles cannot be summed as request accounting.

5. **The original post-computation issue persists.** Legacy retains 2,341 successful late responses whose main computation certainly finishes before the 500 ms deadline, across the four blocks. Five inline calls retain 1,768, but more misses move before computation finishes; the lower count is not an improvement in total deadline success. This screen exports no publication brackets, so it cannot localize those waits relative to actual publication or distinguish runnable readiness from handler execution.

## Environment and validity

The separate V15 baseline is 42.04°C. Accepted trial idle-window means span 41.78–43.97°C; collection k10temp samples span 53.75–62.25°C. All 24 trials pass the frozen thermal, power, quiet-host, quota/affinity, conservation and clock checks, with no rejected attempts or client failures. Those checks do not prove thermal equivalence or absence of other host effects. The warmer V14 and cooler V15 sessions must not be pooled as matched repetitions; absolute legacy performance changed between sessions. Within-session paired comparisons are the main evidence.

## Next research decision

Stay in measurement qualification. First establish same-image A/A repeatability using the exact legacy image under two trial labels, then check an exact-source/no-extra-metadata rebuild against it. Audit full binary/build and control-plane differences rather than relying only on normalized worker instructions. If A/A variability is large, revise host/order/precision design explicitly before treatment comparisons; if exact-source rebuilding changes performance, resolve that reproducibility issue. Only after a trustworthy control is established should a minimal persistent recorder be qualified. Do not launch worker/parallelism controls, a scheduling remedy or another broad marker sweep from these results. This review launches no performance trials and does not alter frozen protocols or margins.

[Sealed V15 report](../../results/diagnostic/runtime-io-v15-inline-markers-1/session/analysis/report.md)
[Detailed derived evidence](review.json)
