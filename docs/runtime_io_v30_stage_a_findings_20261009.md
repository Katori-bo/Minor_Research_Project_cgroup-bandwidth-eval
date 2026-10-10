# Extension Stage A: ordinary timing-model comparison

Date: 9 October 2026. Offline discovery is complete. V1 and all frozen V29
scientific files remain unchanged; no additional service experiment ran.

The next research question is **which information is sufficient to forecast a
deadline miss fraction at each time resolution under a fractional CPU quota?**
An accurate busy-throughput estimate remains useful, but treating it as an
instantaneous processing speed imposes a latency floor that some real requests
beat. Ordinary periodic-budget replay provides a credible reference model.

## Completed comparison

All four V29 contexts were compared at six deadlines. Capacity inputs remained
their original independently calibrated values. The additional non-queue delay
distribution uses only four low-rate calibration trials per context. An ideal
work-conserving periodic server consumes budget when work is present, refills at
period boundaries, discards unused global budget and uses effective demand
`(quota/period)/busy_capacity`. Its phase is not measured: the main diagnostic
averages 100 shared phase scenarios at 1 ms spacing with full initial credit.
Separate sampled ranges include empty/full initial credit and calibration
capacity extremes. These are model-scenario ranges, not hard Linux bounds.

| Context | Fluid busy: 25 ms MAE pp | Periodic + calibrated delay: 25 ms MAE pp | Fluid busy: 500 ms MAE pp | Periodic + calibrated delay: 500 ms MAE pp |
|---|---:|---:|---:|---:|
| 50% CPU, small | 3.451 | 2.354 | 0.479 | 1.636 |
| 25% CPU, small | 3.158 | 1.690 | 1.359 | 6.973 |
| 50% CPU, large | 5.176 | 1.385 | 0.672 | 1.774 |
| 25% CPU, large | 20.624 | 1.386 | 1.295 | 5.756 |

The non-queue delay term alone leaves the final condition's 25 ms error at
20.624 pp. A nonnegative delay cannot repair the constant-rate model's 28.691 ms
service floor. In that condition, 14,239 validation offers miss 25 ms: 14,220
have computation certainly after the deadline, 16 finish computation certainly
within it but miss at the client, and three are clock-boundary ambiguous.
This stage decomposition is descriptive; it does not prove a quota-phase cause.

Ordinary periodic replay substantially explains the short-deadline discrepancy,
but it worsens medium/long deadline forecasts. Merely choosing a different
unknown phase or starting credit is insufficient: at 500 ms, none of the sixteen
25%-CPU/small trials and none of the sixteen 25%-CPU/large trials fall inside the
sampled phase/credit/calibration-capacity range. This is a failure of the sampled
approximation, not a rigorous exclusion of every continuous phase or Linux
runtime behavior.

A second ordinary baseline tried to infer on-speed from median low-rate worker
processing wall time while retaining busy throughput. It would need effective
worker service budgets of 69.400, 31.312, 68.385 and 30.783 ms per 100 ms period,
respectively, exceeding configured quotas of 50, 25, 50 and 25 ms. The baseline
was marked unavailable in every context rather than clipping its parameter or
choosing a fast quantile to improve the result. This rejects the assumption that
lightly loaded processing wall time can be identified with transferable CPU
demand/on-speed. Wall time is not isolated CPU time; frequency changes, external
scheduling and runtime effects remain hypotheses, not measured causes.

Seven numerical tests passed, including an independent discrete CPU-slot oracle
on 40 randomized aligned systems, spillover across budgets, retained credit
within a period, continuous-service equivalence, finite FIFO rejection and
empirical delay-CDF counting. A separate input check rejects validation records
as delay-calibration inputs. Original fluid-model errors reproduce at every
deadline. Reports retain source hashes, source snapshots and output seals.

## Gate and next experiment

**Proceed with prospective prediction/decision validation; do not yet run a
phase-causal experiment or claim a universal correction.** The ordinary model
is sufficiently useful at 25 ms to test on unseen traffic; its medium/long
failures and unknown phase must remain visible. A custom algorithm is not yet
justified. A measured replenishment phase still needs its own qualified,
cost-controlled observation contract before any phase intervention.

The new [confirmation specification](runtime_io_v30_confirmation_protocol_20261009.md)
uses one retained resource/request-size condition, fresh calibration and traffic
patterns not used in V29. It tests a benchmark decision: can at least 95% of
offered requests complete within 25 ms? This is a declared experimental target,
not a production application's established SLO. A new collector/analysis adapter
must pass runtime and timing qualification before launch. Sealed schedules alone
do not make that campaign ready to run.

## Prior-method boundary

[Linux bandwidth-control documentation](https://docs.kernel.org/scheduler/sched-bwc.html)
describes periodic ceilings, per-CPU allocation and retained local runtime.
Our ideal single-budget server omits local slice carry, migrations, competition
among service threads and execution-cost variation. A ceiling does not provide
a lower CPU-service guarantee.

[Cucinotta et al., Section 4.2](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf)
derives an average-speed approximation for guaranteed hierarchical reservations
with a sufficiently small period relative to processing work. Its reservation
premises and stochastic traffic assumptions differ from this benchmark. The
comparison here neither reproduces that full model nor establishes its failure.
Periodic service and average-speed approximations are established; any paper
contribution must be a verified, useful empirical boundary with fresh evidence.

Artifacts: [ordinary models](../analysis/runtime_io_v2_extension/20261009-v29-ordinary-models/report.md),
[two-rate baseline](../analysis/runtime_io_v2_extension/20261009-v29-two-rate-models-revision02/report.md).
The first two-rate attempt stopped at its admissibility check and is preserved
as a sealed failed attempt; revision 02 reports every unavailable context.
