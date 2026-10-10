# When Whole-Run CPU per Job Underpredicts Busy Capacity

### A reproducible case study of deadline forecasts under a fractional CPU quota

Short working draft, 7 October 2026. Based on completed V22, V23 and V25
studies. This is a modest empirical research note; publication-level novelty
remains to be assessed against prior work.

## Abstract

Capacity planning for a CPU-limited service may divide its nominal CPU allowance
by measured whole-run CPU per completed job. We study a controlled service for
which this substitution differs from throughput measured during backlog. In
prospective validation across two job sizes and two burst durations, a simple
FIFO model calibrated with busy capacity predicted 500 ms deadline misses
within the predefined tolerance, while substituting the whole-run CPU/job
estimate substantially overpredicted misses under sustained bursts. A separate
repeated-control diagnostic found that whole-run CPU/job underpredicted measured
busy capacity by approximately 6–7%, with busy CPU delivery near the nominal
0.5 CPU allocation. However, deadline comparability with the sampler remains
unresolved, and the intended unthrottled low-load baseline was not established.
The contribution is a reproducible, scoped measurement comparison and its
documented limits. The cause of the mismatch remains exploratory.

## 1. Question and contribution

Our question is whether whole-run CPU/job represents the capacity of the same
service while requests are waiting. These measurements describe different
intervals: the whole cohort includes changing load and final drain, whereas
busy capacity counts completions in fixed backlogged windows. A small capacity
difference can matter when sustained arrivals approach that capacity.

We provide two complementary pieces of evidence: predictions frozen before
fresh deadline-validation trials, and separate phase CPU/completion measurements
with recording-quality and repeated-control checks. The empirical finding is
that the tested whole-run substitution understates busy capacity and produces
much larger sustained-burst miss forecasts. The phase measurements make the
input mismatch visible but do not identify its cause.

This contribution concerns one declared substitution and a reproducible case.
It does not establish a new queueing law, a universally superior estimator or
a defect in the Linux CPU controller.

## 2. Measurements and experimental design

The retained containerized Go service has one worker, `GOMAXPROCS=1`, a waiting
queue of 128 jobs and yielding disabled. Its CPU quota is 50 ms per 100 ms,
with no burst credit. The service is restricted to CPUs 2 and 4; the
client/controller uses CPUs 0 and 1. Power, resource limits, application
binaries and offered schedules are recorded and checked. All studies use the
same host and service; kernel and boot identities are retained in each manifest.

Let `q = 0.5` denote nominal CPU-seconds per wall-second, and let `c_whole` be
cgroup CPU-seconds accumulated from measurement start through full drain,
divided by completed jobs. The declared substitution is:

```text
mu_whole = q / c_whole                  jobs per wall-second
```

Busy capacity, `mu_busy`, is completions divided by elapsed time over six fixed
three-second windows in a ten-second calibration cycle. V22/V23 calibration
requires more than five waiting jobs throughout the clock-expanded windows.
Two independent calibration trials determine each estimate. Both estimates
feed the same initially empty, constant-service FIFO model, with one active
job and 128 waiting slots. It uses the exact offered schedule; modeled response
occurs at completion. Entry delays, HTTP/runtime effects and quota pulses are
omitted. The comparison therefore tests a capacity-input substitution, rather
than different forecasting algorithms.

Deadline origin is the scheduled offer time. Unsuccessful offers count as
misses, and the denominator is the entire scheduled cohort. Capacity estimates
and forecasts are sealed before validation; there is no validation-derived
refit. The primary tolerance is three percentage points for every trial's
500 ms miss fraction and every declared paired contrast.

V22 contains eight validation trials comparing bursty and even arrivals at
44,000 SHA iterations per job. V23 contains sixteen validation trials in four
balanced blocks, crossing 44,000/88,000 iterations with 3 s/12 s burst cycles.
Within each size, the two cycles have identical low/high rates and offer counts
over 60 seconds. Larger jobs receive half the offer rates. Each size receives
fresh calibration. This is work-size and timescale transfer within one
computation, rather than independent-application generality.

V25 is a separate sixteen-trial diagnostic: four sampler-off and four sampler-on
runs at each size. Consecutive same-condition repeats and opposite-order group
contrasts measure observed variation. Its native collector requests 20 ms
counter reads and records acquisition wall time and thread CPU time separately.
Clock alignment and enclosing monotonic reads bound CPU use and completion
counts at fixed endpoints, without interpolation. Quality limits include
4% relative CPU/completion bound width and 0.02 CPU busy-delivery bound width.
These accounting bounds are not statistical confidence intervals.

V25 prospectively defines busy state as a guaranteed positive waiting queue,
separately from the earlier greater-than-five margin. Its low-state definition
requires at most one waiting job and an upper bound of zero on throttled
periods. Valid records remain available when these state checks fail. V25 is
descriptive; it is not pooled with prospective validation or used to refit it.

## 3. Results

### 3.1 Prospective deadline forecasts

V22's busy estimate was 152.47 jobs/s. It predicted 10.38% burst misses against
10.97–11.92% observed; the whole-run substitution predicted 44.05%. Even
arrivals had zero 500 ms misses despite approximately 14.8% higher whole-run
CPU/job. All twelve trial/contrast checks passed, with maximum error 1.55
percentage points. These outcomes do not identify the CPU-cost difference's
cause.

V23 extended the comparison:

| Job size | Burst cycle | Mean observed misses | Busy-capacity forecast | Whole-run CPU/job forecast |
|---|---:|---:|---:|---:|
| Small | 3 s | 0.00% | 0.00% | 0.00% |
| Small | 12 s | 22.56% | 22.76% | 49.23% |
| Large | 3 s | 0.00% | 0.00% | 0.00% |
| Large | 12 s | 16.13% | 17.26% | 46.85% |

Each row summarizes four fresh validation trials. All sixteen trial checks and
eight paired-contrast checks passed; maximum error was 1.83 percentage points.
Supporting peak-queue and recovery checks passed. All 81,504 validation offers
succeeded, with no rejections or responses longer than one second. The reported
misses are therefore late successful responses. Zero short-cycle misses does
not establish exact latency or satisfaction of tighter deadlines.

### 3.2 The separately measured capacity mismatch

V25 completed all sixteen trials with no technical retry. All eight native
recordings passed quality checks: 33,260 readings, no skipped sampling slots,
and maximum acquisition wall time 0.274 ms. All eight busy phases were eligible;
their delivered CPU bounds lay approximately within 0.4933–0.5067 CPU.

| Job size | `0.5 / mean(c_whole)` | Mean measured busy capacity | Capacity underprediction |
|---|---:|---:|---:|
| Small | 138.82 jobs/s | 149.42 jobs/s | 7.09% |
| Large | 70.53 jobs/s | 75.06 jobs/s | 6.03% |

These descriptive calculations use the four sampler-on trials per size; they
are not fresh prospective forecasts. Whole-run CPU/job exceeded busy-window
CPU/completion in every on trial. The envelopes of per-trial whole/busy cost
bounds were 1.06033–1.09140 for small jobs and 1.04997–1.07879 for large jobs.
One large trial's conservative lower bound was 4.997%, just below the earlier
5% scientific threshold. Seven of eight exceeded that threshold. The envelopes
describe accounting bounds, not confidence intervals.

Matching CPU use, completion counts and elapsed time is an accounting identity;
it is not independent validation of a new predictor. The useful observation
is the difference between whole-cohort and backlogged-window measurements,
alongside the separately prospective deadline results.

### 3.3 Controls and adverse findings

V25's mean off/on differences in busy capacity were +0.252% and +0.130% for
small and large jobs; whole-run CPU/job differed by approximately -0.094% at
both sizes. Deadline behavior was less comparable:

| Job size | Off mean misses | On mean misses | On-minus-off | Largest consecutive same-condition difference |
|---|---:|---:|---:|---:|
| Small | 24.18% | 22.65% | -1.53 percentage points | 0.62 percentage points |
| Large | 21.58% | 20.49% | -1.09 percentage points | 3.12 percentage points |

Small-job miss contrasts were -1.45 and -1.60 percentage points in opposite
order directions, both exceeding the largest observed repeat difference. This
signal cannot simply be dismissed as repeat variation. Large-job contrasts
were -2.28 and +0.10 points, leaving the comparison unresolved. Four trials per
condition do not establish statistical equivalence or causal sampler effects;
balanced order does not remove every host-state difference.

None of the eight planned low phases met the low-state definition. Seven had
queue maxima above one, six had positive throttling lower bounds, and all
eight had positive upper bounds. The recordings remain valid aggregate
measurements, but they do not establish the intended uniformly unthrottled,
shallow-queue baseline. Consequently, the proposed pure low/busy state-mixing
explanation is unconfirmed.

## 4. Relation to prior work and interpretation

Busy-period characterization and burst-aware capacity planning have established
precedents. Mi et al. use busy-time information and temporal-dependence models
for system sizing; this study does not introduce busy-period calibration.
[Mi et al., *Sizing multi-tier systems with temporal dependence: benchmarks and analytic models*, JISA 2010](https://link.springer.com/article/10.1007/s13174-010-0012-9), §3.3.

Casale et al. describe utilization-based demand characterization and the
information lost in aggregate CPU observations. CPU/completion accounting
itself is established.
[Casale et al., *Automatic Stress Testing of Multi-Tier Systems by Dynamic Bottleneck Switch Generation*, Middleware 2009](https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf), §3.1.

Reservation-based response-time models use isolated processing demand and stated
reservation/timescale assumptions. Our loaded whole-container cost under a
bandwidth ceiling has a different measurement scope and scheduling contract.
The observed substitution failure does not refute such models.
[Cucinotta et al., *Strong Temporal Isolation Among Containers in OpenStack for NFV Services*, IEEE TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), §4.2.

Kscaler documents mismatches between userspace CPU abstractions, application
periodicity and kernel bandwidth behavior. Broad CPU-interface mismatch is
therefore adjacent prior art; we have not evaluated its implementation as a
baseline.
[Sampat et al., *CPU Autoscaling With a Kernel of Truth*, APSys 2025](https://tianyin.github.io/pub/kscaler.pdf), §§2–3.

Our addition is the controlled empirical comparison, prospective forecast
errors, bounded phase-accounting artifact and explicit adverse controls for
this service. The reviewed literature is targeted, not exhaustive. The present
note claims a reproducible case rather than a first discovery or new algorithm.

## 5. Limits and reproducibility

Generality covers two sizes of one SHA computation and the tested traffic
patterns on one host. It excludes independent applications, other machines,
other quotas, mixed job sizes and stochastic traffic. Aggregate cgroup CPU/job
includes application, runtime, HTTP and kernel work; it is not isolated per-job
SHA demand. Clock/counter bounds do not prove zero kernel accounting lag, and
phase endpoints retain in-flight-work limitations. Frequency, cache, scheduling
and runtime mechanisms were not isolated.

Earlier V24 generations stopped under their frozen timing or qualification
rules. Their outcomes remain preserved; later instrumentation/state revisions
do not retroactively accept them. V23's collection and report completed before
its watchdog interrupted final replay; a separate verification passed without
new measurements. V25 completed collection and independent replay normally.

The retained artifacts contain exact schedules, raw events, configuration and
binary identities, prediction seals, native read brackets, cleanup receipts
and independent replay tools. Evidence used in this draft:

- [V22 verification receipt](../analysis/runtime_io_v22_result_review/20261007/report.json).
- [V23 verification receipt](../analysis/runtime_io_v23_result_review/20261007/report.json).
- [V25 diagnostic review](../analysis/runtime_io_v25_result_review/20261007/report.json).
- [V23 frozen design](runtime_io_v23_frozen_question.md) and [V25 frozen design](runtime_io_v25_protocol.md).

Saved-data checks, requiring no new experiment:

```bash
python3 diagnostic/v22_study.py verify-completion --directory analysis/runtime_io_v22/generation-02
python3 diagnostic/v23_study.py verify-completion --directory analysis/runtime_io_v23/generation-01
python3 diagnostic/v25_study.py verify-completion --directory analysis/runtime_io_v25/generation-01
```

The defensible current claim is that whole-run CPU/job can understate busy
capacity and mislead the tested deadline forecast under a fixed fractional CPU
quota. A pure operating-state explanation and broader transfer remain open.
Collection is stopped while this modest claim and its limitations are reviewed.
