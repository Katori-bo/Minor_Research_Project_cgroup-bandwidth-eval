# Forecast reliability: initial feasibility verdict

10 October 2026. The
[discovery protocol](runtime_io_forecast_reliability_protocol_20261010.md) was
recorded before this new numerical screen, after original outcomes were known.
The [primary-source audit](runtime_io_forecast_reliability_prior_work_20261010.md)
and raw saved-data screen are now complete at their bounded scope.

## Decision

**Keep the reliability question as an empirical research question; hold custom
diagnostic development and new collection at this gate.** A rule based on
calibration stability alone has insufficient support, and we have not identified
an additional capability beyond ordinary uncertainty/profile/state methods.
This does not prove that no useful diagnostic is possible or that established
methods already solve every case. It tells us what these data justify pursuing.

The useful question remains whether information available before future traffic
can distinguish reliable and unreliable empirical deadline forecasts at a useful
answer rate. Generic confidence intervals or refusing uncertain cases would not
be a new contribution. A specific new input-to-reliability relationship is
missing, along with independent forecasting episodes for its evaluation.

## Evidence reconstructed

The screen reads original sealed client records from four timing-calibration
cohorts and all eighteen validation cohorts in each campaign. Complete-response
CDF probabilities and all-offer observed misses are independently recounted.
The Go point result agrees with the existing retrospective control; NGINX agrees
with its original frozen forecast and errors. Original study gates are unchanged.
This is not another whole-campaign replay, an independent-host replication or
prospective confirmation of the ordinary Go control.

| Calibration / forecast quantity | Go V31, 10 ms | NGINX, 20.565395 ms |
|---|---:|---:|
| Complete-response calibration samples | 676 | 1600 |
| Pooled predicted miss fraction | 67.456% | 50.000% |
| Calibration cohort probability range | 13.274 pp | 11.750 pp |
| Largest cohort deviation from pooled forecast | 9.933 pp | 6.250 pp |
| Descriptive four-cohort t half-width | 9.754 pp | 7.802 pp |
| Request-iid DKW half-width, illustration only | 5.223 pp | 3.395 pp |
| Mean validation absolute error | 1.802 pp | 5.981 pp |
| Maximum validation error | 5.350 pp | 38.333 pp |
| Validation cohorts with error >5 pp | 1/18 | 7/18 |

All errors are percentage points of all-offer miss fraction. The common 5 pp
screen tolerance differs from V31's original <=3 pp aggregate criterion. Go's
good mean does not make every future-cohort error small. NGINX's failed original
upper-interval gate does not prove that its unknown population mean error is >5 pp.
Different endpoints and calibration designs prevent a controlled application
effect interpretation or a pooled general model ranking.

Go's cohort miss probabilities are 70.796, 69.333, 68.889 and 57.522%; NGINX's
are 44.500, 56.250, 48.500 and 50.750%. Go has the wider observed calibration
spread despite much smaller later average error. Thus smaller spread cannot
be assumed to rank these two campaigns' forecast reliability correctly.

## Fixed ordinary checks

Checks were declared in the protocol and not trained on validation errors.
The table shows cohort answer counts, not independent guard-trial counts.
A calibration-only campaign flag makes the same decision for eighteen cohorts.

| Check | Go answers /18 | NGINX answers /18 | What this resolves |
|---|---:|---:|---|
| Always forecast | 18 | 18 | Retains 1 and 7 errors >5 pp respectively |
| Zero recorded calibration throttling | 18 | 18 | This alone supplies no warning about the transfer error |
| Future rate within timing-calibration range | 6 | 0 | Go has 33.3% coverage; insufficient for proposed 50% usefulness target |
| Every calibration cohort within 5 pp of pool | 0 | 0 | Conservative warning, no useful answer coverage here |
| Descriptive four-cohort t half-width <=5 pp | 0 | 0 | Also flags both; it is not a future-error interval |
| Request-iid sampling half-width <=5 pp | 0 | 18 | Accepts the less accurate campaign; assumptions are unestablished |
| 100 us deadline-stress deviation <=5 pp | 0 | 0 | Flags both; 100 us is not an observed bound on future shifts |
| Maximum chronological calibration-fold error <=5 pp | 0 | 0 | Internal predictability check flags both; only three folds each |

The iid row is an assumption illustration, not an admissible risk certificate.
DKW bounds deviation from the same population CDF under iid sampling. It does
not bound unobserved distribution drift or add the sampling noise of a finite
future response cohort. Neither t intervals nor cohort ranges establish those
transfer assumptions. A valid interval may be broad; useful answer coverage
must be reported separately from statistical validity.

The rate-support guard uses the original timing pools: 3.75/7.5 requests/s for
Go and 5 requests/s for NGINX. It accepts only Go's 5 requests/s profile, whose
MAE is 1.793 pp and whose six cohort errors are <=5 pp. These six dependent
cohorts do not certify future risk. Profiling at informative target rates is
an ordinary alternative; its acquisition cost must be compared before pursuing
a custom extrapolation warning.

## Sensitivity and additional calibration

| Deadline stress offset | Go maximum one-sided probability change | NGINX maximum one-sided probability change |
|---|---:|---:|
| 50 us | 2.071 pp | 4.375 pp |
| 100 us | 5.917 pp | 8.375 pp |
| 250 us | 21.302 pp | 20.188 pp |

The 50 us, <=5 pp check would accept both, retaining the adverse NGINX errors;
the 100 and 250 us checks refuse both. Choosing another tolerance or offset to
separate these known cases would be method development after outcomes, not
validation. These values quantify ordinary CDF sensitivity and do not identify
a quota, scheduler or frequency mechanism. No permissible signal bounds the
future shift by the chosen offset.

Chronological calibration fold errors are 1.463/0.934/11.927 pp for Go and
9.750/2.000/1.000 pp for NGINX. Each fold predicts a new cohort using earlier
calibration cohorts only. NGINX's fold deadlines are chosen from those earlier
samples, so these scores do not retroactively validate its final pooled deadline.

| Number of calibration cohorts pooled | Go later MAE | NGINX later MAE |
|---|---:|---:|
| 1 | 3.309 pp | 5.296 pp |
| 2 | 2.559 pp | 6.273 pp |
| 3 | 2.351 pp | 5.815 pp |
| 4 | 1.802 pp | 5.981 pp |

These descriptive prefix comparisons retain the original full-calibration
deadline. They do not simulate choosing an earlier NGINX deadline or show
what a new matched-rate calibration would accomplish. More reference-rate
samples improve Go here but do not monotonically improve NGINX. No preferred
prefix is selected.

## Is the proposed path worth pursuing?

**Calibration-dispersion-only diagnostic: stop at this gate.** The fixed checks
either flag both campaigns or do not warn about the adverse transfer. A new
threshold would not establish a new capability, and two known campaigns cannot
justify a trained reliability model.

**General uncertainty wrapper: no established novelty.** The primary-source
audit identifies selective regression, conformal and online uncertainty,
profile-based tail prediction, RScale and MPORA as close precedents. None has
been shown inferior under a matched contract. An endpoint or quota change is
not sufficient evidence of a literature gap.

**Narrow state-informed candidate: unresolved, no prototype yet.** Before
reopening custom development, specify one observable available before future
traffic, explain how it constrains response-distribution changes, compare it
with an ordinary state/profile model, and account for its measurement cost.
The current NGINX milestones locate longer time after response headers, but do
not observe server queue, per-request CPU, scheduler service or thermal/frequency
state sufficient to identify the cause. A post-outcome latency excursion is
not an advance warning. No new measurement campaign is justified by naming
these absent signals alone.

## Evaluation contract for any surviving future proposal

- Unit: an independently acquired calibration-history-to-future episode, not a
  request or another deadline on the same requests.
- Inputs: only observations available at the declared decision time; a live
  feedback method must account for its observation delay and earlier failures.
- Comparisons: ordinary complete-response prediction, cohort/support checks,
  independently calibrated uncertainty, a compatible state-conditioned model
  and additional informative calibration at matched cost.
- Metrics: accepted MAE and maximum error, fraction of accepted episodes with
  error >5 pp, answer coverage, transition-region coverage, false SLO assurances
  if a real miss budget is supplied, and acquisition/observer cost.
- Development and error calibration must be separate from held-out evaluation.
  Use history-to-future episodes from multiple conditions; do not reuse known
  Go/NGINX outcomes as fresh confirmation or split individual requests into
  nominal independent deployment tasks.
- Provisional feasibility target: >=50% answer coverage overall and for cases
  with observed 10%-90% misses, with <=5 pp error. A statistical risk claim
  requires a separate sampling/power plan, not these provisional thresholds.

For scale only, 59 independent accepted episodes with zero failures are needed
for a one-sided 95% binomial upper risk below 5%, for an independently fixed
guard. Even two independent zero-failure episodes would have a 77.6% upper
risk; our two campaigns are not established independent sampling units. Nineteen
exchangeable residual-calibration episodes are a minimum for a finite 95%
split-conformal empirical quantile, not for useful interval width or selective
risk. Current timing cohorts do not supply that episode contract.

## Concrete next action

Continue the separately planned friend-host replication of the existing V31
comparison, including the ordinary response-CDF control prospectively if its
qualified package includes it. It can improve the empirical paper's external
evidence; it is not automatic validation of a new guard. If its outcomes inform
guard development, retain them as discovery and reserve other fresh data for
confirmation. This audit does not prepare or launch his portable collector.

On our side, use this completed protocol and verdict as the go/no-go document.
Do not start a generic stability guard or a larger dataset search. Reopen the
method route only with the concrete observable-to-future-shift relationship
and fair comparator specified above. Otherwise retain the scoped empirical
paper, including the reliability limitation and adverse result.

## Reproduction

[Screen implementation](../analysis/screen_forecast_reliability.py),
[numerical results](../analysis/runtime_io_forecast_reliability/20261010/screen.json),
[calibration-only features](../analysis/runtime_io_forecast_reliability/20261010/calibration_features.json)
and consumed-input hashes are preserved separately from the original evidence.
From the repository root:

```bash
python3 -B analysis/screen_forecast_reliability.py --verify
```

The verifier recomputes the screen, checks consumed raw records against original
seals, reconciles both campaigns' saved results, checks strict deadline counting
with an independent count/bisect calculation and verifies consumed-input/output
hashes. It does not launch workloads or certify literature novelty.
