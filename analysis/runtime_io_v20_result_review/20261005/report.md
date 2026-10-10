# V20 verified findings

Reviewed 2026-10-05. All four qualification rehearsals and sixteen trials completed. Independent raw completion replay was rerun successfully: `guardrail_tradeoff_requires_review`. No interrupted discovery blocks. This review does not modify the frozen protocol, analysis or decision rules.

The new evidence is that the existing post-publication yield flag almost eliminates the residual completion-to-handler delay even with one worker/GOMAXPROCS=1, while overall 500 ms success does not improve. This is a local measurement of a known scheduling control, not a claim to discovering yielding or a new scheduler mechanism.

| Configuration | All-offer 500 ms success | All-offer 1000 ms success | Failures | Mean completion-to-handler gap | Mean successful E2E p99 |
|---|---:|---:|---:|---:|---:|
| A: 100 ms period, yield off | 82.14% | 100% | 0% | 17.280 ms | 641.0 ms |
| B: 100 ms period, yield on | 82.05% | 100% | 0% | 0.0579 ms | 652.8 ms |
| C: 20 ms period, yield off | 54.86% | 97.49% | 2.33% | Whole-cohort unknown | 973.8 ms |
| D: 20 ms period, yield on | 56.00% | 97.67% | 2.33% | Whole-cohort unknown | 949.4 ms |

Values are averages across four equal-offer trials per arm; each arm retained 27,172 offers. P99 values are averages of trial p99 values, not a pooled p99. C/D each have 633 rejections, whose computation/handler intervals do not exist; observed-subset gaps are not substituted for whole-cohort means.

## Yielding at the unchanged quota/period

B−A completion-to-resume mean reduction was 99.58–99.78% across the four blocks (median 99.65%). Mean absolute reduction was 17.223 ms. Completion-before-deadline/handler-after-deadline cases with publication bounded before the deadline dropped from 819 to zero. This count comparison does not imply the same 819 individual requests were recovered: changing execution order changes later queue history.

All-offer 500 ms success changed by -0.44, +0.43, -0.71 and +0.37 percentage points across blocks (mean -0.088 pp; exploratory block mean 95% interval -1.00 to +0.82 pp). This is no demonstrated net deadline benefit, not proof of equivalence. Average queue waiting increased from 217.724 to 232.802 ms, +15.078 ms, increasing in every block. Computations finishing after the deadline increased from 4,019 to 4,865; total misses were 4,853 and 4,877. Average E2E mean improved modestly by 6.53 ms, while successful p99 rose about 1.8% and CPU/job about 0.46%.

B passed every frozen guardrail, but failed the useful-signal rule because the median 500 ms change was negative. The aggregate outcome is consistent with redistributing delay between stages rather than recovering deadlines. This does not establish per-request attribution or prove a runtime scheduler defect.

## Shorter periods

C and D worsened 500 ms success by approximately 27.28 and 26.14 pp relative to A. Each produced 633 rejections (2.33% of offers), versus none in A/B. Mean successful E2E p99 rose to 974/949 ms; CPU per completed computation rose from 3.630 ms to about 3.834 ms (+5.6%). Average observed queue waiting was about 407/408 ms. Both shorter-period arms failed guardrails in every block. The 20 ms period is therefore not an acceptable remedy under this frozen workload.

The higher CPU/job is an observation, not an attribution to kernel accounting overhead, frequency, runtime costs or any other particular cause. Its components increased mainly in recorded user CPU. The mechanism gap primary and gap interaction cannot be assessed over all offers for C/D because rejected requests have no such interval. Observed long-gap counts cannot remove that limitation.

## What this resolves

The delayed-handler symptom responds strongly to execution order at the original quota contract. Removing it does not materially improve the chosen 500 ms target; most remaining misses concern computation finishing too late. Changing average-preserving quota period can substantially worsen capacity-related outcomes, so shorter periods are not a universal fix.

The paper's resource/overcommitment explanation remains compatible with these results, but V20 does not directly observe throttle intervals, handler runnable readiness or remaining quota. It neither proves quota pauses are the sole cause nor rules them out. Yielding can change which work runs before quota exhaustion.

Retain the original 100 ms configuration as the best observed 500 ms baseline. Do not automatically launch another handoff intervention: the completed-result delay is no longer supported as an isolated path to deadline improvement. Review earlier queue/computation losses and the observed CPU-cost change using existing data before declaring another experiment.
