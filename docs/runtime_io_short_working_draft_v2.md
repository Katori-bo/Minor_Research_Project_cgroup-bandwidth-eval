# CPU cost depends on the operating state: a small research note

Working draft2, 2026-10-07. V22/V23 results are complete; the explanation below
is a hypothesis awaiting V24. The original draft and its review seals remain
preserved. This is a short contribution outline, not a finished paper.

## Problem

Under a fixed half-CPU limit, the tested service's busy capacity predicts
deadline failures substantially better than dividing nominal CPU allowance
by whole-cohort cgroup CPU/job. The practical question is why two plausible
measurements produce such different forecasts, and how a measurement diagnostic
can expose an invalid assumption before it is used for planning.

## Completed evidence

The retained Go service has one worker/GOMAXPROCS=1, a128-job waiting queue,
50 ms CPU allowance per100 ms, no burst credit and yielding off. V22 sealed
calibration-only predictions before eight burst/even validation trials. Its
busy model predicted10.38% bursty500 ms misses against10.97–11.92% observed;
the declared CPU/job substitution predicted44.05%. Even arrivals had zero
500 ms misses, despite approximately15% more whole-cohort CPU/job.

V23 used separate fresh calibration at44k/88k SHA iterations per job and
sealed predictions before sixteen validation trials. Within each size,3-second
and12-second burst cycles had identical offer counts and low/high/average rates.

| Job size / cycle | Mean observed500 ms misses | Busy forecast | CPU/job forecast |
|---|---:|---:|---:|
| Small /3 s | 0% | 0% | 0% |
| Small /12 s | 22.56% | 22.76% | 49.23% |
| Large /3 s | 0% | 0% | 0% |
| Large /12 s | 16.13% | 17.26% | 46.85% |

Every V23 trial and paired-contrast check met the frozen3 pp tolerance; maximum
error was1.83 pp. Queue/rejection/recovery checks and the declared baseline
comparison passed. All81,504 validation requests succeeded; none exceeded1 s.
The90-minute limit interrupted final replay after collection/report sealing;
separate independent verification passed without repeating measurements.

## Candidate explanation and diagnostic

Whole-cohort CPU/job averages lightly loaded, backlogged and drain intervals.
Busy capacity comes from fixed backlogged windows. Exploratory old counters
suggest CPU/completion is lower during backlog than during light load, with
busy delivery near0.5 CPU. Thus a state-invariant demand assumption may be
invalid for the tested deployment. Historical counter timestamps are too coarse
to confirm this interpretation. Wall-processing distributions also change;
the cause cannot be assigned to overhead, frequency or a runtime mechanism.

V24 will measure CPU and completion counts over the same fixed busy/low windows,
retain conservative clock/counter bounds, and check sampler perturbation with
off/on pairs. Its diagnostic tests whether whole-cohort CPU/job can represent
busy-state CPU/completion. Matched-window CPU and throughput identities are
accounting relationships, not a new independent predictor.

## Contribution if confirmed

The possible contribution is a scoped failure-mode demonstration: state-mixed
CPU/job produces misleading deadline forecasts in this controlled CPU-limited
service, while an audited measurement diagnostic exposes the state dependence.
The artifact combines prospective forecast comparisons, phase accounting,
measurement-cost checks and explicit limits. A distinct causal intervention
would still be needed to attribute the underlying execution/runtime mechanism.

Busy-period characterization, utilization-based demand estimation and CPU
interface/periodicity mismatches have prior art. See the
[updated analysis and primary-source comparison](runtime_io_capacity_mismatch_findings.md).
No new queueing law, universally best estimator, kernel defect or established
algorithmic novelty is claimed. Generality currently covers two sizes of one
hash kernel, several traffic patterns and one host; it does not cover independent
services or machines.

If V24 does not support the explanation, retain the V22/V23 empirical comparison
and report exactly which diagnostic failed. Do not rewrite the hypothesis as a
discovery or enlarge the experiment merely to obtain a pass.
