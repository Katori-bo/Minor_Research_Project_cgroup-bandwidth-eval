# Stopped NGINX power-policy study: verified partial results

10 October 2026. Original generation and all sealed evidence remain unchanged.

## Stop and restoration

The campaign intentionally stopped at validation cohort 12: P0 at 8 requests/s,
block 3. It recorded one throttled period and 11,793 us (11.793 ms) of
aggregate throttle time during the measurement counter window. This violates
the declared zero-throttling domain. All 300 responses in that cohort
succeeded; success and deadline compliance are different endpoints.

Hardware qualification, source/evidence seals, four fresh calibration cohorts,
global forecast and pre-measurement warmup forecast barriers, and all twelve
validation raw replays verify. All collected validation cases record verified
policy restoration and no owned-cleanup errors. The last policy journal
restored the original full policy snapshot. Current-host readback was also
checked separately during review; it is not a new performance measurement.

The scientific campaign lasted about 20.94 minutes before stopping. It
contains 1,600 calibration and 3,600 validation measurement offers, plus
their original warmup records. Twelve of the twenty-four planned validation
cohorts were collected: three balanced blocks, with the third containing
the domain exit. Only two complete blocks satisfy the intended domain.

## What the partial evidence shows

At the unchanged 20.565395 ms deadline, the fresh P0 calibration prediction
was 80.875% misses and P1 was 0%. Across the twelve collected validation
cohorts, P0 averaged 80.167% misses and P1 0%; mean full responses were
20.543 and 16.695 ms respectively. These are descriptive policy contrasts
on this interrupted, single-host study. A preference readback does not
measure fixed frequency or isolate the physical mechanism.

| Forecast | Partial MAE (pp) | Maximum error (pp) | Errors >5 pp |
|---|---:|---:|---:|
| Pooled CDF | 40.083 | 41.562 | 12/12 |
| Policy-matched CDF | 0.562 | 2.542 | 0/12 |
| P0-only CDF | 41.000 | 80.875 | 6/12 |
| 25-offer warmup CDF | 3.083 | 12.000 | 4/12 |
| Matched + warmup samples | 0.487 | 2.394 | 0/12 |
| Pooled + warmup samples | 39.514 | 40.954 | 12/12 |

All twelve cohorts are retained in these numbers, including cohort 12.
Pooling responses from two different assigned policies produced a poor
forecast here; ordinary policy-matched calibration transferred much better
over the observed prefix. Warmup-only profiling was less accurate than
the larger matched reference. This does not establish a new estimator.

## Interpretation and research decision

**The planned six-block acceptance test is unavailable.** Do not run the
complete-campaign comparator on an invented twenty-four-row dataset, apply
the six-block criterion to three blocks, drop the throttled cohort, or
call the stopped prefix a successful non-throttled experiment. Stopping
depends on an observed outcome, so confidence statements cannot ignore it.

The observed benefit is strong exploratory evidence for the value of
matching an explicitly controlled policy in this configuration. It does
not establish that policy explains the original unobserved NGINX excursion,
a general transfer guarantee, or a novel reliability diagnostic. The pooled
comparator deliberately combines both policies; the finding supports an
ordinary calibration condition rather than superiority over an existing
state-aware method.

Preserve generation-01 and do not resume, replace, relax its gate or rerun
until it passes. There is no collector bug demonstrated by this traceback.
A subsequent scientific run would need a separately justified and frozen
contract, such as predicting all-offer outcomes while explicitly allowing
quota throttling. That would answer a broader question than the original
zero-throttling pilot; changing the population after seeing this outcome
must be disclosed. No new campaign is launched by this review.

## Reproduction

```bash
python3 -B analysis/review_nginx_power_stopped.py --verify
```

`report.json` contains every collected cohort and comparator. The original
runner sources and original campaign records are not edited by this review.
