# Supporting Material: Accounting Controls and Investigation History

8 October 2026. Supporting record for the [version-5 manuscript](runtime_io_short_working_draft_v5.md).
This editorial extraction preserves the numerical findings, frozen decisions and
limitations of the audited [version 4](runtime_io_short_working_draft_v4.md).
No new measurements, models or thresholds are introduced. Study identifiers
are artifact provenance, not separate scientific contributions.

## S1. Study inventory and measurement definitions

Busy eligibility in V22/V23 requires more than five waiting jobs in six
three-second windows. Later designs require a guaranteed positive waiting
queue in their separately frozen windows. These definitions are not
retroactively harmonized. Native phase-counter brackets bound CPU and
completion counts without interpolation; accounting bounds differ from
statistical intervals.

| Study | Purpose and retained design |
|---|---|
| V22 | Two calibration runs; eight fresh validation trials comparing bursty/even small-job arrivals; four paired contrasts. |
| V23 | Fresh calibration per work size; sixteen validation trials in four balanced blocks crossing two sizes and 3/12 s burst cycles; eight paired contrasts. |
| V25 | Sixteen diagnostic runs: four sampler-off and four sampler-on per size, repeated controls and bounded phase accounting. |
| V26 | Four sampler-on steady runs at 15/30/30/15 jobs/s; fixed low-load windows qualify queue and throttling conditions. |
| V27 generation-03 | Sixteen runs in four balanced blocks crossing low rates 15/30 and sampler off/on, with identical high arrivals at 169.8 jobs/s. |
| V28 | Sixteen calibration slots, a forecast freeze, then sixteen sampler-off validation slots in four balanced blocks crossing low rates 15/30 and 6/12 s cycles, with high arrivals at 180 jobs/s. |

V27 changes low-phase arrivals while holding high-phase offers fixed. Each
60 s measurement has four 15 s cycles, comprising 10 s low and 5 s high.
The high-phase cohort contains 3,396 offers; low cohorts contain 600 or 1,200.
Busy windows are fixed at 11.5–14.5 s in each cycle. Sampler-on low windows
at 3–8 s qualify separately. The frozen composition screen requires both
95% cost-increase interval lower bounds to reach 3%, busy-capacity intervals
within ±2%, and sampler-interaction intervals within ±2 percentage points.

## S2. Accounting evidence and sampler limitations

V25 completed sixteen diagnostic trials with no retry. Its eight native
recordings passed quality checks: 33,260 readings, no skipped slots, maximum
acquisition wall time 0.274 ms. All eight busy phases qualified; delivered CPU
bounds were approximately 0.4933–0.5067 CPU.

| V25 size | Whole-run capacity | Measured busy capacity | Underprediction |
|---|---:|---:|---:|
| Small | 138.82 jobs/s | 149.42 jobs/s | 7.09% |
| Large | 70.53 jobs/s | 75.06 jobs/s | 6.03% |

These descriptive values use four sampler-on runs per size. Whole-run cost
exceeded busy-window cost in all eight recordings. One conservative lower
bound was 4.997%, below the 5% screen; seven of eight met it. Matching CPU,
counts and duration is an accounting identity, not independent validation.

Deadline sampler comparability remains unresolved. Small-job off/on means
were 24.18%/22.65%, with opposite-order differences of −1.45/−1.60 percentage
points against a largest consecutive repeat difference of 0.62. Large-job
means were 21.58%/20.49%, with opposite-order differences of −2.28/+0.10 and
largest repeat difference 3.12. Neither causal sampler effects nor equivalence
are established. None of V25's eight intended low phases qualified: seven
had waiting-queue maxima above one and all eight had positive throttling upper
bounds. Later qualification does not change those outcomes.

## S3. Qualified low load and composition sensitivity

V26 qualified all four low windows: waiting queue at most one, bounded
throttled-period count zero, positive completions. All 2,700 measurement offers
succeeded with zero 500 ms misses; 10,233 native readings passed quality
checks. This establishes the measurement condition for steady sampler-on
traffic, without a busy arm or sampler-off comparison.

V27 generation-03 completed sixteen accepted runs without retries. All 68,736
measurement offers succeeded and all required mixed states qualified.
Doubling low arrivals from 15 to 30 jobs/s increased whole-run cost in every
one of the eight paired comparisons:

| Native sampler | Mean CPU/job increase | Model-based 95% interval |
|---|---:|---:|
| Off | 3.194% | [2.720%, 3.669%] |
| On | 3.419% | [2.989%, 3.849%] |

Busy capacity remained 149.167–150.333 jobs/s. Both busy-stability and
sampler-interaction screens passed. Both cost interval lower bounds fall
below the frozen 3% minimum; retain `composition_inconclusive`. The evidence
supports a directional composition effect in this service, without establishing
the required minimum magnitude. Cost/capacity interaction checks do not prove
deadline sampler neutrality or isolate why CPU/job changes.

## S4. Detailed idle correction and retained collection failures

The two live-idle captures consume 7.668/8.056 ms CPU over approximately
30.11 s each. Mean idle rate is 0.000261092 CPU, or 0.0261% of one CPU.
The additive correction reduces mixed CPU/job by only 0.105% and increases
estimated capacity by 0.0739 jobs/s. That correction cannot repair the observed
gap. Loaded overhead remains unidentified. Steady calibration costs are
approximately 4.50–4.53 ms/job at 15/30 jobs/s and 3.679–3.691 at 120; all
ten steady runs have zero throttled periods and queue peak one. These are
cohort costs, not isolated SHA demand or a measured runtime mechanism.

Earlier V24 generations stopped under their frozen timing/qualification rules.
V27 generation-01 failed because client clock anchors were absent;
generation-02 exhausted its retry with 79 monitor records against a minimum
80. Generation-03 used a separately frozen bounded monitor-lifetime repair.
Failed recordings remain failed. V23's report completed before its watchdog
interrupted final replay; subsequent verification passed without new collection.
Neither technical repairs nor software tests add scientific effects.

## S5. Earlier investigations and closed routes

The initial period/concurrency/arrival matrix remains a separate completed
empirical record in [the original paper](../paper/paper_draft.md). Its
successful-request percentile endpoint differs from the all-offer deadline
endpoint of the current manuscript; it is not pooled into the prospective
capacity-input comparison.

The earlier delayed-handler intervention is recorded in [V20 findings](runtime_io_v20_findings.md)
and [the repeat](runtime_io_v20_repeat_findings.md). Yielding strongly reduced
the measured completion-to-handler interval; deadline benefit was negligible
in the original and modest/conditional in the repeat. Those observations
motivate scrutiny of end-to-end outcomes but do not establish a scheduler
mechanism or enter the final yield-off comparison.

The [historical period reversal](runtime_io_period_reversal_closing_findings.md)
remains closed with its cause unresolved. The [FIFO theorem review](runtime_io_fifo_reviewer_verdict_20261008.md)
closed the admission-only route as the lead for a stronger contribution.
The theorem and solvers remain research assets; they are not advertised as
novel foundations for this empirical paper. The [quota-period selection proposal](runtime_io_next_research_decision_20261008.md)
is on hold at the user's instruction. None of these records authorizes new
collection or reopening a closed route.

## S6. Artifact and evidence index

Saved artifacts retain exact offers, raw events, clock/counter brackets,
configuration and binary identities, forecast seals and cleanup receipts.
The main paper's numerical results and these controls refer to the following
saved reviews and frozen protocols:

- [V22 result review](../analysis/runtime_io_v22_result_review/20261007/report.json) and [V23 result review](../analysis/runtime_io_v23_result_review/20261007/report.json).
- [V25 result review](../analysis/runtime_io_v25_result_review/20261007/report.json) and [V26 result review](../analysis/runtime_io_v26_result_review/20261007/report.json).
- [V27 generation-03 result review](../analysis/runtime_io_v27r3_result_review/20261008/report.json) and [V28 result review](../analysis/runtime_io_v28_result_review/20261008/report.json).
- [V28 frozen protocol](runtime_io_v28_protocol.md) and [V28 findings](runtime_io_v28_findings.md).
- [Closest-method assessment](runtime_io_load_dependent_baseline_assessment_20261008.md).
- [Original version-4 consolidation audit](../analysis/runtime_io_paper_consolidation_review/20261008/report.json), whose document hashes describe that earlier editorial state.
- [Version-5 editorial verification](../analysis/runtime_io_paper_focus_review/20261008/report.json).

The original audit, version-4 draft, source/result seals and scientific
thresholds are preserved. The new editorial verification checks tables,
links and preservation; it does not repeat scientific collection or establish
novelty. Collection remains stopped.
