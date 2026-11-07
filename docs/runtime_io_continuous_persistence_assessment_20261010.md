# Continuous probe persistence: decision

10 October 2026. The user-authorized offline first-100/next-200 screen is complete.
All 54 completed NGINX cohorts were retained. No new traffic was generated.
Earlier evidence and the manuscript remain unchanged.

**A continuous 100-offer probe improves some forecasts, but does not supply a
reliable selector across these campaigns.** It substantially improves average
power-study accuracy, yet still misses a large subsequent timing excursion.
The fixed probe-agreement check accepts that case. The candidate fails the
predeclared coverage/error screen; a fresh confirmation run is not justified
by this result.

| Campaign | Original forecast MAE | Recent-100 MAE | Weighted-update MAE | Recent-100 maximum | Recent errors >5 pp |
|---|---:|---:|---:|---:|---:|
| Original NGINX | 6.167 | 5.167 | 5.941 | 10.000 | 9/18 |
| Power confirmation | 15.521 | 2.729 | 14.025 | 31.500 | 4/24 |
| Rate transfer | 2.542 | 3.708 | 2.616 | 13.000 | 2/12 |

Errors are percentage points of all-offer deadline-miss probability at the
unchanged 20.565395 ms deadline. Every method is evaluated on the same final
200 offers, so the original column differs from its historical 300-offer
result. Forecasts use original calibration, matched-policy power calibration,
or ordinary fixed-5/s rate calibration. The sample-weighted update combines
that same reference with the same 100 probe offers.

The difficult P0 power cases have recent-100 MAE **5.458 pp**, versus **31.042 pp**
for the original reference, with four errors above 5 pp among twelve cohorts.
The twelve P1 cases have zero observed misses and zero errors for all methods;
they lower the overall power-study average but do not validate the selector for
P0. Recent profiling worsens the already accurate rate-transfer reference.

## The specific persistence failure

Power cohort 23, P0 at 8 requests/s, has 46% misses in its first 50 offers and
50% in its next 50. Their 4 pp difference passes the frozen <=5 pp agreement
check. The probe forecasts **48%**, but the following 200 offers have **79.5%**
misses, giving **31.5 pp error**. The original calibration happens to predict
79.5% in this case. Agreement within a probe therefore does not assure that
the next window will resemble it.

This is an observed prefix-to-suffix distribution difference. It does not
identify frequency, scheduler, queue or other physical causes. A figure of
50-offer bins is a diagnostic selected after scoring; it is not another
predictor or a new window search.

The guard accepts 7/18 original-study cases, retaining four errors above 5 pp;
18/24 power cases, retaining three; and 8/12 rate cases, retaining none. P0 power
has 6/12 accepted cases, three wrong above tolerance. The useful-signal screen
requires >=50% coverage overall and in the 10–90% miss transition region,
with no accepted error above 5 pp in every campaign and separately P0 power.
It fails. Accepted-subset comparisons for all methods and six-block paired
descriptive gains are preserved in the numerical package.

## What this does and does not establish

This test examines a later decision than the original forecast: 100 offers
of continuous target traffic are consumed before predicting 200 subsequent
offers. It tests within-cohort persistence at this cost. It cannot certify an
unrelated future deployment, a population error bound or a novel estimator.
Recent empirical profiling and pooled updating are ordinary methods.

Finite probe and target samples also introduce noise. For scale only, under
independent stationary Bernoulli misses with probability 0.5, the difference
between a 100-offer and a 200-offer fraction has standard deviation about
6.12 pp. Those assumptions are not established here. Thus modest errors above
5 pp do not, by themselves, identify physical drift. The larger excursion is
a stronger observed mismatch, while the accepted-error/coverage criterion
remains the frozen practical screen rather than a statistical risk guarantee.

All first-100 response bodies finish before offer 101 is scheduled in the saved
records, with at least 0.103 seconds of body-timing slack. However, the client
emits JSON at the end of all 300 offers and does not record when integrity
checks or a hypothetical online forecast finish. This establishes an offline
body-timing boundary, not a qualified live observer. No pause, drain or reset
is inserted at the split; an eventual online implementation must qualify its
overhead under that same continuous contract.

## Acquisition cost and preservation

A 100-offer scheduled probe occupies about 12.5–25 seconds at 8–4 requests/s,
plus any observation/decision overhead. It is additional to the initial
25-offer warmup and selected calibration. The full acquired calibration is
1,600 offers in original NGINX, 1,600 in power, and 2,400 in rate, plus calibration
warmups, qualification, settling and startup. An 800-offer selected reference
does not erase the other pools actually acquired.

Across these records, the replay consumes 5,400 probe offers and evaluates
10,800 suffix offers. The 54 cohorts share one host, references and chronology;
they are known development evidence, not 54 independent reliability episodes.
No threshold, window, deadline or blend was tuned after scoring.

## Next decision

Close this fixed 100/200 feasibility test. Preserve the average improvement and
the adverse persistence case together. No generic stability guard, longer-window
search or new confirmation run follows automatically. The unresolved prerequisite
is an advance observable whose relation to subsequent change is established at
fair cost. The current record supports an empirical finding that recent profiling
can help substantially while an internally agreeing probe still fails to predict
its next window. It supplies no general reliability certificate.

The existing empirical manuscript and the friend's independent V31 replication
remain separate. A future proposal needs a concrete measurement-to-future relation
and independent episodes; these known suffix outcomes cannot become fresh validation
of a rule selected from them.

## Reproduction

Seven contract tests pass. The verifier reconstructs the calibration references
from sealed raw records, checks all-offer conservation and timestamp boundaries,
reconciles the complete 300-offer outcomes with previous reviews, and reproduces
the exact scores and report hashes. Tests cover strict deadline equality, failed
offers, sample weighting, the exact 5 pp boundary, suffix isolation, and a stable
probe followed by a bad accepted forecast.

```bash
python3 -B analysis/screen_continuous_persistence.py --verify
python3 -B -m unittest discover -s analysis -p test_continuous_persistence.py -v
```

[Frozen protocol](runtime_io_continuous_persistence_protocol_20261010.md),
[numerical results](../analysis/runtime_io_continuous_persistence/20261010/screen.json),
[generated report](../analysis/runtime_io_continuous_persistence/20261010/report.md),
[diagnostic figure](../analysis/runtime_io_continuous_persistence/20261010/persistence.png).
