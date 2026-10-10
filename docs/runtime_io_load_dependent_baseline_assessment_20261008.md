# Load-dependent baseline assessment after V28

8 October 2026. Targeted primary-source assessment, performed after V28
outcomes were known. No new scientific measurements, prior-method fits or
validation forecasts were produced. Historical evidence and thresholds remain
unchanged. Collection is stopped.

## Decision for the paper

Proceed with the consolidated empirical draft. The evidence establishes the
tested whole-run substitution's substantial prediction error and busy
calibration's prospective accuracy. It also shows that a simple nonlinear
CPU-based benchmark recovers nearly the same capacity. It does not establish
a novel estimator or superiority over published load-dependent methods.

The closest methods are conceptually relevant competitors. Their queueing
assumptions need adaptation and checking for this quota-limited FIFO service;
that requirement is not evidence that they are inapplicable. Calling V28 a
comparison against their algorithms would be inaccurate. No additional
experiment is needed to state the existing narrow result honestly. A stronger
contribution requires a specific unresolved question and declared baseline
implementation before further collection is justified.

## What the closest papers actually estimate

[Kumar, Zhang and Tantawi, *Enhanced Inferencing: Estimation of a Workload
Dependent Performance Model*, VALUETOOLS 2009](https://eudl.eu/pdf/10.4108/ICST.VALUETOOLS2009.7799),
§2 and §3, Eqs. 10–20: service-demand and CPU-overhead functions depend on
arrival load. Queueing relations connect demand to mean response time and
utilization. Constrained optimization fits both kinds of observations, rather
than utilization alone. The discussed response relation includes processor
sharing, network/routing terms and CPU multiplicity. Polynomial and transformed
load families make it a relevant alternative to a constant-demand fit.
The conference was in 2009; the publisher landing page was posted in 2010.

[Zhang, Li and Zhou, *Estimate Load-dependent Service Demand for Modern CPU*,
Information Technology Journal 12(4), 2013](https://scialert.net/fulltext/amp.php?doi=itj.2013.632.639),
load-dependent estimation section, Eqs. 1–5: demand is a polynomial of CPU
utilization, with quadratic/cubic forms. Utilization-law relations and soft
mean-response constraints inform a quadratic-program formulation. The response
bounds use multicore queueing alternatives; slack accommodates noise and
burstiness. The paper discusses CPU frequency/SMT effects and workload-mix
limits. Those mechanisms were not identified in our service.

The [Spinner et al. 2015 survey's author-hosted abstract](https://se.informatik.uni-wuerzburg.de/en/tools/librede/)
explicitly treats load level, monitoring windows and model mismatch as
estimation-comparison factors. That supports evaluating method assumptions,
not presenting a constant linear fit as the only established CPU-based route.
Full publisher text was unavailable during this assessment; detailed algorithm
claims below come from the two primary full texts above, not this abstract.

## Method mapping

| Dimension | V28 declared benchmark | Kumar et al. | Zhang et al. |
|---|---|---|---|
| Load variable | Measured completion throughput `X=N/T` | Arrival load in demand and overhead functions | CPU utilization in the demand function |
| Functional target | `U(X)=b+dX+eX²` | Separate demand and overhead functions | `D(U)` polynomial |
| Fitting observations | Twelve idle/steady CPU and completion aggregates | Utilization and mean response time | Utilization, throughput/class information and mean response constraints |
| Objective/constraints | Equal-run utilization residuals; declared admissibility checks and finite candidate family | Joint constrained queueing inference | Utilization-law constraints plus soft response bounds in a quadratic program |
| Response prediction in this project | Capacity root passed to exact-offer constant-rate FIFO | Published mean-response queueing relations | Published mean-response bounds |
| Evaluation status | Frozen before sixteen fresh V28 trials | Not implemented or evaluated here | Not implemented or evaluated here |

This mapping is an assessment of correspondence, not a mathematical proof
that a restricted special case cannot coincide with a published method.

“Quadratic” must specify the dependent variable. For positive throughput,
V28's relation implies an effective non-background CPU cost:

```text
U(X) = b + dX + eX²
D_X(X) = (U(X) - b) / X = d + eX
whole CPU/job = U(X) / X = b/X + d + eX
```

Thus a quadratic utilization curve implies a linear effective demand in
throughput after subtracting a constant background. It is not the quadratic
demand-in-utilization family in Zhang et al. In V28 the selected quadratic
intercept is zero. The fit lacks both papers' response-time information and
joint constraints. It is a meaningful restricted CPU-only benchmark, with
different inputs and assumptions; it is not a faithful reproduction.

## Applicability to a fractional quota

The recorded `U` is CPU-seconds per wall-second, and `q=0.5` is a bandwidth
ceiling. It is not a count of continuously available physical servers.
The worker is single-threaded but can experience periodic quota stalls. One
cannot insert `q` as a multicore server count, or silently substitute `U/q`
for physical utilization in a published response formula.

A CPU-only adaptation of a load-dependent demand law is plausible: declare
the aggregate accounting scope, model demand/overhead, and solve the quota
capacity equation. Reproducing the full published algorithms additionally
requires explicit mappings for CPU multiplicity, utilization, arrival versus
completion rate, mean response scope and scheduling. Our deterministic bursts,
finite FIFO queue and periodic resource ceiling do not establish their
processor-sharing or multicore response assumptions. Soft bounds can tolerate
some burstiness; their existence prevents dismissing a method merely because
arrivals vary.

Existing raw records provide CPU, counts, durations and client/server timings.
They may support retrospective applicability diagnostics or a clearly labelled
adaptation. Client end-to-end response, server residency and isolated service
demand have different scopes; choosing among them needs justification. Mean
response inference and 500 ms all-offer miss prediction are also different
tasks. A poor tail forecast would not automatically refute an estimator's
published mean-response result.

Both papers are plausible candidates for further assessment. Full applicability
and faithful implementation have not been established. Equation images in the
Zhang HTML and unavailable PDF screenshots limit verification of exact
constraint coefficients. Do not implement supposedly faithful constraints from
partial text extraction or infer coefficient signs from ambiguous prose.

## Claims to retain and claims to withhold

| Claim | Assessment |
|---|---|
| The tested whole-run substitution materially overpredicts sustained-burst misses | Supported prospectively by V22/V23/V28 within the declared service, quota and model. |
| Direct live-idle correction repairs the gap | Unsupported: V28 capacity moves only 139.669→139.743 jobs/s. This concerns the declared additive correction, not loaded overhead generally. |
| Composition changes whole cost while busy capacity stays within its stability margin | Directional V27 evidence supports the measured pattern; the full ≥3% screen remains inconclusive. |
| Busy beats every declared V28 alternative by the required minimum | Unsupported: the quadratic improvement interval [0.086, 1.346] pp fails the lower-bound ≥1 pp rule. |
| CPU-only nonlinear estimation can approach busy accuracy | Supported for V28's particular benchmark: capacity 148.463 versus 149.417 jobs/s, deadline MAE 1.169 versus 0.453 pp. |
| A new load-dependent demand estimator or selection rule has been established | Unsupported. Load-dependent inference and estimator comparison precede this work; no new rule was prospectively validated. |
| Published load-dependent algorithms fail on this service | Untested; V28 did not reproduce them. |
| CPU frequency, cache, runtime or controller behavior causes the cost difference | Unidentified; cohort observations do not isolate mechanisms. |

The revised paper should state the nonlinear benchmark prominently, retain
both inconclusive screens, and describe the contribution as the forecasting
consequences of a measured mismatch. Avoid making whole-run accounting a
surrogate for all prior estimation work.

## Stop point and conditions for stronger work

The immediate recommendation is writing and reviewing the scoped paper, with
collection stopped. No rerun-to-pass, transfer workload or new experiment is
authorized by this assessment.

If we later seek estimator superiority, first resolve source equations and
choose a faithful implementation or explicitly justified adaptation. Declare
units, required data, identifiability, fitting objective, constraints,
calibration budget and failures. An offline fit to existing data is useful
retrospective work, but a specification selected after seeing V28 cannot be
presented as that study's frozen prospective comparison. A genuinely new
comparison would need a fresh frozen validation design and a bounded budget.

If nonlinear alternatives remain adequate, retain the empirical note and close
the superiority route. If a distinct useful failure boundary appears, specify
and validate that diagnostic before limited workload/quota transfer. A causal
mechanism is a separate optional route. None follows automatically from these
results.

The review is targeted rather than exhaustive. See the
[consolidated draft](runtime_io_short_working_draft_v4.md),
[V28 findings](runtime_io_v28_findings.md) and
[source/evidence audit](../analysis/runtime_io_paper_consolidation_review/20261008/report.json).
