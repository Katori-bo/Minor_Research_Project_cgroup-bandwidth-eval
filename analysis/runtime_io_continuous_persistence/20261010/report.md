# Continuous probe persistence: offline assessment

10 October 2026. First100 scheduled offers forecast the next200 in every completed NGINX cohort. Historical outcomes were known; this is development evidence.

| Campaign | Cohorts | Original MAE | Recent100 MAE | Update MAE | Recent100 max | Recent100 errors >5 pp |
|---|---:|---:|---:|---:|---:|---:|
| NGINX original | 18 | 6.167 | 5.167 | 5.941 | 10.000 | 9 |
| NGINX power | 24 | 15.521 | 2.729 | 14.025 | 31.500 | 4 |
| NGINX rate | 12 | 2.542 | 3.708 | 2.616 | 13.000 | 2 |

All errors are percentage points of all-offer deadline-miss probability at20.565395ms, scored on the same200-offer suffix. The original method is original calibration for the first campaign, matched-policy calibration for power, and fixed5/s calibration for rate. The sample-weighted update pools that reference with the same100 probe offers. No window, threshold or blend was fitted.

## Difficult power-policy cases

| Population | Original MAE | Recent100 MAE | Update MAE | Recent100 max | Errors >5 pp |
|---|---:|---:|---:|---:|---:|
| P0 | 31.042 | 5.458 | 28.051 | 31.500 | 4 |
| P1 | 0.000 | 0.000 | 0.000 | 0.000 | 0 |

Keep P1 zero-miss endpoints separate; they cannot establish useful performance for P0 transition cases.

## Predeclared probe agreement guard

Accept recent100 only if the first50 and second50 probe miss fractions differ by<=5pp and all first100 bodies finish before offer101 is scheduled. It is an ordinary stability check, not a future-risk bound.

| Campaign | Accepted / total | Coverage | Transition coverage | Bad accepted | Caught errors | False warnings | Accepted recent100 max |
|---|---:|---:|---:|---:|---:|---:|---:|
| NGINX original | 7/18 | 38.9% | 41.2% | 4 | 5 | 6 | 8.000 |
| NGINX power | 18/24 | 75.0% | 50.0% | 3 | 1 | 5 | 31.500 |
| NGINX rate | 8/12 | 66.7% | 66.7% | 0 | 2 | 2 | 3.500 |

P0 power guard: 6/12 answers, 50.0% coverage, 3 bad accepted forecasts. Transition cases have observed suffix misses between10% and90%; that outcome-side label never enters the guard.

The frozen usefulness screen requires>=50% overall and transition coverage and no accepted error>5pp in every campaign and separately P0 power. Candidate survives: **False**. Accepted-subset errors for all three methods and six-block paired descriptive gains are in screen.json. Cohorts share references and chronology; no pooled significance or independent-risk claim is made.

## Boundary and costs

- NGINX original: 0 body-timing domain flags; probe body completion span 12.395–24.771s; minimum boundary slack 0.104s. Acquisition: 1600 calibration measurement +100 calibration warmup offers, +450 initial validation warmup offers, +1800 probe offers, with 3600 suffix offers evaluated.
- NGINX power: 0 body-timing domain flags; probe body completion span 12.391–24.772s; minimum boundary slack 0.104s. Acquisition: 1600 calibration measurement +100 calibration warmup offers, +600 initial validation warmup offers, +2400 probe offers, with 4800 suffix offers evaluated.
- NGINX rate: 0 body-timing domain flags; probe body completion span 12.396–24.772s; minimum boundary slack 0.103s. Acquisition: 2400 calibration measurement +150 calibration warmup offers, +300 initial validation warmup offers, +1200 probe offers, with 2400 suffix offers evaluated.

100 scheduled offers occupy a12.5–25s window at8–4/s. The actual completion span is99 intervals plus completion, reported above. Qualification, settling, setup and inference/observer overhead add cost. Offline computing a forecast is not evidence of a deployed cost reduction.

The saved client emits its JSON after the whole300-offer cohort. BodyDoneNs precedes decompression/correctness checking, whose completion timestamp is not retained. The timestamp test therefore establishes body-timing availability for a hypothetical online observer, not a qualified live integrity/inference barrier. No service reset or traffic pause is inserted at the100/200 split. A future live design must qualify observation/correctness/inference without silently adding a pause that changes the population.

## Outcome interpretation

A close first100/next200 match is evidence of within-cohort persistence for this cost and endpoint. It cannot certify a later unrelated deployment, a future state jump, production SLO compliance or a novel estimator. These are ordinary recent empirical forecasts. Cases with errors above tolerance remain retained; the probe guard cannot be declared reliable from its mean alone.

## Reproduction

```bash
python3 -B analysis/screen_continuous_persistence.py --verify
python3 -B -m unittest discover -s analysis -p test_continuous_persistence.py -v
```

The verifier reconstructs permitted calibration from sealed raw files, checks the fixed100/200 all-offer split and timestamp boundary, reconciles unchanged300-offer results with previous reviews, and recomputes every score and hash. Tests exercise strict deadlines/failures, translation-free empirical forecasting, exact5pp boundaries, suffix-outcome isolation and insufficient probe coverage. Original experiments and manuscript gates remain intact.
