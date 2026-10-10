# Which capacity measurement predicts deadline failures under a fixed CPU quota?

Working research note, 2026-10-07. This is a short draft around a candidate
empirical contribution, with a bounded follow-up rather than a finished paper.

## Question and candidate contribution

A CPU allowance, average CPU cost per job, and measured busy completion capacity
are different measurements. We investigate how choosing between two such
capacity estimates changes predictions of queued requests missing a deadline.
Our candidate contribution is a reproducible empirical comparison under a
retained fractional CPU limit, with predictions sealed before fresh trials and
their errors exposed across arrival timing and work sizes. The FIFO simulator,
busy-period calibration and burst-induced queueing are established methods.
The addition would be the controlled comparison, scoped transfer evidence and
documented failures, rather than a new queueing law or scheduling algorithm.

## Completed evidence

The service is a pinned Go HTTP service, one worker/GOMAXPROCS=1, a 128-job
waiting queue and a half-CPU allowance of 50 ms per 100 ms with no burst credit.
In V22, two independent calibration trials measured busy capacity at
152.47 jobs/s; their disagreement was 0.26%. The same calibration records
gave 139.39 jobs/s when substituting nominal allowance divided by whole-trial
cgroup CPU/job. Both estimates parameterized the same finite FIFO simulator.

Predictions were sealed before eight validation trials in four paired blocks.
Every trial offered 6,793 jobs of 44,000 SHA iterations over 60 seconds. Bursty
arrivals alternated five-second low/high phases; evenly spaced arrivals offered
the same jobs. Busy-capacity predictions passed every frozen trial and paired
contrast check at a three-percentage-point margin.

| Metric | Frozen prediction | Observed validation |
|---|---:|---:|
| Bursty 500 ms miss percentage, busy-capacity estimate | 10.38% | 10.97–11.92% |
| Even 500 ms miss percentage, busy-capacity estimate | 0% | 0% in all four trials |
| Bursty peak queue | 87 jobs | 88–92 jobs |
| Bursty mean ordinary recovery | 0.848 s | 0.802–0.829 s, with clock ranges retained |
| Bursty 500 ms miss percentage, nominal CPU/job substitution | 44.05% | 10.97–11.92% |

All requests succeeded; none exceeded one second in this validation. The largest
primary error was 1.55 pp, queue-peak error at most five jobs, and recovery error
below 47 ms. Request timing is less precise: individual burst-response prediction
errors reached about 98 ms. Even arrivals used about 15% more measured cgroup
CPU/job than bursty arrivals despite much lower latency. These observations do
not identify why CPU/job or capacity differ; no per-job CPU measurement exists.

Earlier V20 original/repeat experiments motivate this question: the existing
post-publication yield control sharply reduced completion-to-handler delay while
500 ms deadline benefits varied. Those are separate sessions and interventions.
V22 kept yielding off and validates the queue component, not a yielding boundary.

## Relation to existing work

CPU-limit-induced queues and microburst latency already have empirical support
in [Shetty et al., SoCC 2025](https://sarthak-chakraborty.github.io/publications/YAAS_SoCC25.pdf).
Busy-period service characterization and model error under burstiness are
established in [Mi et al., 2010](https://link.springer.com/content/pdf/10.1007/s13174-010-0012-9.pdf).
Reservation-based CPU-to-response approximations appear in
[Cucinotta et al., TCC 2023](https://retis.santannapisa.it/people/nino/publication/TCC23.pdf).
Their isolated service cost and guaranteed reservation assumptions differ from
our loaded whole-service CPU/job substitution and bandwidth ceiling; our result
does not refute their model. [Casale et al., Middleware 2009](https://dl.ifip.org/db/conf/middleware/middleware2009/CasaleKKR09.pdf)
also studies controlled burstiness and service-demand characterization.
These precedents rule out novelty claims based merely on bursts, busy calibration
or a CPU-versus-wall-time distinction. The reviewed sections do not certify the
absence of an exact preceding comparison. See the retained closest-work matrix.

## Small generality test

V23 extends the prospective comparison to two job sizes (44,000 and 88,000 SHA
iterations) and two new burst periods (3 and 12 seconds). At each job size,
independent ten-second-pattern calibration supplies both capacities. Halving
arrival rates for double-sized jobs preserves the scheduled number of SHA
iterations, while request counts and HTTP overhead legitimately differ.
Neither capacity is borrowed from V22 nor assumed to scale by two.

Four balanced validation blocks contain all four size/pattern combinations.
The existing 500 ms/three-pp primary criterion remains fixed, with queue,
rejection, recovery, stage/tail and baseline errors recorded. Both capacities
are frozen before any V23 validation. This tests transfer across work size and
burst timescale on one host, using the same hash kernel. It does not establish
transfer to other algorithms, machines or services.

## Claims after the follow-up

If V23 passes, report a scoped empirical comparison across the tested job sizes
and burst timescales, with a reproducible prospective artifact. If it fails,
report the failing cells and the limit of constant-capacity transfer; retain
V22's narrower pass. A nominal-baseline advantage is reported only if its
predeclared comparison passes. A result already supplied by the closest work
should be framed as a replication/case study. These are possible outcomes,
not promised findings or publication acceptance.

Evidence: [V22 frozen report](../analysis/runtime_io_v22/generation-02/analysis/1791352638937269784/report.md),
[frozen design](runtime_io_v22_frozen_question.md),
[closest-work matrix](runtime_io_contribution_matrix.md).
