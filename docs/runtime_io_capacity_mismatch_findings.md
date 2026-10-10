# Capacity mismatch: what the existing data suggests and what V24 will test

Offline review, 2026-10-07. No Docker, root command, new observation or workload
was used. V22/V23 sources, predictions and raw trials remain unchanged.

## The concrete lead

V23 measured busy throughput of152.17 small jobs/s and76.89 large jobs/s.
Multiplying those rates by whole-cohort CPU/job implies about0.546 and0.540 CPU.
Those products mix measurements from different time windows. They do not show
that the service exceeded its half-CPU allowance during busy periods.

Exploratory alignment and linear interpolation of retained one-second cgroup
counters suggest the following ranges across the two calibration trials per size:

| Quantity | Small jobs | Large jobs |
|---|---:|---:|
| Whole-cohort cgroup CPU/job | 3.589–3.591 ms | 7.0188–7.0196 ms |
| Approximate busy-window CPU/completion | 3.285–3.289 ms | 6.488–6.494 ms |
| Approximate low-window CPU/completion | 4.796–4.808 ms | 9.012–9.055 ms |
| Approximate busy CPU delivery | 0.5000–0.5004 CPU | 0.4989–0.4992 CPU |

The old monitor records rounded epoch labels before later counter reads, without
actual monotonic read brackets. Alignment also assumes wall-clock constancy.
Consequently the interpolated phase numbers are exploratory estimates without
measurement bounds. They motivate V24 and cannot establish its explanation in
advance. The exact whole-cohort values and original capacity estimates remain
independently verified V23 results.

## Why this is not simply wasted CPU

The retained worker records also show different processing-wall distributions:
small jobs have busy-window medians around2.98 ms versus low-window medians
around4.53 ms; large jobs around5.99 ms versus8.82 ms. Busy-window means are
much higher because their tails include quota stalls. These are wall times,
not per-job CPU times; neither subtracting them nor treating the medians as
CPU demand identifies an overhead component.

Possible explanations include phase-dependent execution speed, scheduling or
cache effects, runtime/HTTP/kernel overhead and background service work.
Existing one-second frequency samples are not attributed to the CPU executing
each job. They cannot prove a frequency explanation. Kernel documentation also
warns that scaling_cur_freq may describe a requested operating state rather than
the actual instantaneous hardware frequency. See
[CPU performance scaling](https://www.kernel.org/doc/html/latest/admin-guide/pm/cpufreq.html).

The focused next question is therefore whether aggregate CPU/completion changes
with operating state. A specific spinning, GC, DVFS or kernel mechanism remains
unisolated.

## Closest work and contribution boundary

Busy-period service characterization is established: Mi et al. estimate service
process properties from completions conditioned on busy periods. We cannot
claim to invent busy calibration.
[Mi et al., JISA2010, section3.3](https://link.springer.com/content/pdf/10.1007/s13174-010-0012-9.pdf).

Casale et al. discuss utilization-based demand estimation and information lost
by aggregate utilization samples. Matching CPU use with completion counts is
ordinary accounting, not a new equation.
[Casale et al., Middleware2009, section3.1](https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf).

Cucinotta et al. model isolated service CPU demand under a guaranteed reservation
and discuss fixed-speed measurement. Our whole loaded-service CPU/job under a
Linux bandwidth ceiling has different assumptions; failure of our substitution
does not refute their model.
[Cucinotta et al., TCC2023, section4.2](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf).

Kscaler makes a broader argument about the mismatch between userspace CPU units,
application periodicity and kernel bandwidth behaviour, and implements an
in-kernel autoscaler. It is adjacent precedent, not a baseline we executed.
General CPU-interface or periodicity mismatch is not an uncovered idea.
[Sampat et al., APSys2025, sections2–3](https://tianyin.github.io/pub/kscaler.pdf).

Linux documents bounded CPU-local quota carryover. This warrants checking actual
CPU delivery rather than assuming every short window uses exactly0.5 CPU; it
does not establish that carryover caused our results.
[CFS bandwidth caveats](https://www.kernel.org/doc/html/latest/scheduler/sched-bwc.html).

A useful small contribution could be a carefully scoped, independently measured
state-mixing failure mode with a reproducible diagnostic and its limitations,
linked to the prospective deadline errors already demonstrated. V24 could
support that explanation. It will not automatically create an algorithmic
novelty claim or certify the absence of a predecessor. The targeted literature
review is not exhaustive and competing implementations were not executed.

## Prepared next test

[V24's frozen protocol](runtime_io_v24_frozen_question.md) uses12 trials:
two work sizes, counter sampler off/on, three paired blocks. The service and
traffic kernel remain pinned. New20 ms counter reads get monotonic brackets;
fixed busy/low windows get conservative CPU and completion bounds without
interpolation. Every off/on pair must pass a perturbation screen before the
phase-cost explanation can receive support. All results, including failures,
are retained.

If the test succeeds, we can say that whole-cohort CPU/job does not transfer
unchanged to the tested busy state, while busy CPU delivery remains close to
nominal. If it fails, distinguish sampling perturbation, insufficient phase
separation, different CPU delivery and an undemonstrated cost shift. Do not
silently replace windows or thresholds.

The offline bundle is ready; actual image/resource/sampler functional
qualification remains deliberately deferred. The
[external launch guide](runtime_io_v24_execution.md) has the complete command.

Receipts: [exploratory counter review](../analysis/runtime_io_capacity_mismatch_review/20261007/report.json),
[processing-wall/frequency details](../analysis/runtime_io_capacity_state_details/20261007/report.json),
[V23 verified findings](runtime_io_v23_findings.md).
