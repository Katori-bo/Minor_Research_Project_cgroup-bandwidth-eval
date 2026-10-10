# Small contribution and bounded generality review

2026-10-07, following verified V22 completion. The user wants a short working
draft and a modest claim with additional experimentation where needed.
This review narrows the target and defines V23 rather than certifying novelty.

## Current choice

Lead with **which capacity measurement predicts deadline loss under a retained
CPU quota**, illustrated by a reproducible prospective comparison. Keep earlier
yielding/stage findings as motivation. A joint yielding-boundary claim would
require an additional matched yielding experiment and is outside V23.

The short [working draft](runtime_io_short_working_draft.md) makes a concrete
current statement: V22 busy-capacity forecasts passed all12 frozen checks,
while its nominal quota/whole-trial CPU-job substitution greatly overpredicted
burst loss. The latter is one declared practical substitution, not the strongest
available model or a test disproving CPU-based performance modelling in general.
The difference's causal explanation remains unisolated.

## Closest-work check and what can be added

| Primary source | Existing contribution / reviewed material | Our remaining narrow target |
|---|---|---|
| [Shetty et al., SoCC 2025](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf), §3.2 | Empirical limit-induced queues and microbursts despite modest average utilization. | Retained strict contract, exact all-offer deadline accounting and prospective prediction errors. Bursts causing queues are already established. |
| [Mi et al., JISA 2010](https://link.springer.com/content/pdf/10.1007/s13174-010-0012-9.pdf), §§3.2–3.3 | Conventional-model errors under burstiness and busy-period completion characterization for service-process models. | Controlled comparison of two declared capacity estimates in this service; work-size/timescale transfer and failures. Busy calibration and estimator choice are not new principles. |
| [Cucinotta et al., TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf), §4.2 | Isolated processing demand and guaranteed reservations lead to CPU/response approximations with stated timescale assumptions. | Loaded whole-service CPU/job versus observed wall busy completion under a bandwidth ceiling. This is a different input/contract, not a refutation of their reservation result. |
| [Casale et al., Middleware 2009](https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf), introduction and service-demand characterization passages | Controlled bursty benchmark construction and resource-demand characterization from coarse CPU observations. | A transparent strict-quota deadline artifact with predictions frozen before new parameter cells. Benchmarking burstiness and limits of aggregate measurement are precedents. |
| [argos-edge release notes](https://cmos486.github.io/argos-edge/release-notes/v1.3.41.1/), Gosched/pacing comparison | Author-reported export improvement while an interactive latency gate still failed. | Paired stage/deadline measurements are useful case-study evidence; “yielding can be insufficient” is not an uncovered idea. |

This is our inference from selected primary passages, not evidence that these
authors cannot express the case. The earlier17-source matrix and two abstract
screens remain relevant. We did not execute competing artifacts or complete
proof/algorithm audits. Targeted searches found adjacent precedents and a further
2009 benchmarking source; search misses do not establish an absent predecessor.

## What the smallest follow-up addresses

The [V23 frozen design](runtime_io_v23_frozen_question.md) crosses two existing
request work sizes (44k/88k SHA iterations) with3 s/12 s burst cycles. Both sizes
receive separate fresh calibration. Within a size, offered jobs/work are matched
across burst periods; across sizes, scheduled SHA iterations are normalized by
halving offer rates. HTTP request counts legitimately differ. V22's old capacity
is used only for disclosed exploratory factor selection and is not fitted into
the V23 forecasts.

Four balanced blocks supply16 validation trials and8 size-specific contrasts;
four qualification and four calibration slots bring the external session to24.
The code must preserve the500 ms/3 pp primary criterion, technical gates,
period-aware recovery, both estimators and every adverse cell. All forecasts
are sealed together before any validation. No workload is replaced for an
unfavorable result. A90-minute bound keeps the extension finite.

If the full prediction screen passes, the scope expands to two work sizes and
two further burst timescales on this host. A baseline advantage is separately
declared at each size; its absence must remain visible. If only one size passes,
claim that subset and show the failing cells. If transfer fails, characterize
the error and keep V22's narrower result. No validation-derived refit can turn
that failure into a prospective pass.

## A claim we can point to

Current: “We provide a reproducible prospective comparison of two capacity
estimates for all-offer deadline failure under a fixed fractional CPU contract;
the busy-window estimate predicted the tested burst/even outcomes, while the
declared whole-trial CPU/job substitution substantially overpredicted burst loss.”

Conditional on V23: add the tested work-size/timescale range, or the observed
failure boundary, with every primary and supporting error disclosed. Call it an
empirical measurement/case-study contribution. A reproducible artifact is a
tangible output but is not, alone, proof of scientific novelty.

Generality still excludes independent algorithms/services/hosts, different CPU
quotas, mixed job sizes, stochastic arrivals and yielding. Two iteration counts
of one hash kernel are work-size evidence only. A wider independent-workload
study is justified only if the short note's claim requires it; it is not an
automatic next batch. After V23, synthesize the note using the result obtained.
