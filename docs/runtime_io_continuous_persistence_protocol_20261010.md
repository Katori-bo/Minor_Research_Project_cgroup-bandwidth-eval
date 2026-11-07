# Continuous probe persistence: offline protocol

10 October 2026. User authorized the first100/next200 offline test. Historical whole-campaign outcomes and prior screens are known; the new prefix/suffix scores have not yet been computed. Freeze this design before numerical scoring.

Use all54 completed300-offer NGINX validation cohorts: original18, power24 and rate12. Keep D=20.565395ms. Probe offers0..99 in scheduled order, then evaluate offers100..299 from the same continuous traffic invocation. Retain failures and throttling. The reference is original pooled calibration, policy-matched power calibration, or ordinary fixed5/s rate calibration. Reconstruct each from sealed raw calibration rows.

Forecasts are original CDF, recent100 CDF, and calibration+100 sample-weighted CDF. Every recent method receives the same100 responses, same reference and decision time. Do not tune weighting or probe length. All three are ordinary methods.

Report all-answer MAE/max/errors>5pp by campaign and P0/P1; separate10%-90% transition cases. A predeclared ordinary persistence guard accepts the recent100 forecast when the first50 and second50 probe miss fractions differ by<=5pp and all first100 response bodies complete before offer101's scheduled time. Report the identical subset for all three forecasts, coverage, bad accepted predictions, caught errors and false warnings. This check is an empirical selector, not a calibrated future-error bound.

A candidate survives the provisional useful-signal screen only if every accepted recent100 error is<=5pp and coverage is>=50% overall and among transition cases for every campaign and separately for P0 power. Report descriptive paired six-block gains without pooling requests or claiming independent replications. Good aggregate performance cannot hide difficult-cohort failures or P1 endpoint saturation.

Check the timestamp boundary: maxBodyDone(first100) must precede ScheduledNs(offer101). Any violation is retained and flagged; the guard abstains rather than silently deleting the cohort. Raw JSON is emitted only after the full cohort, and client decode/check completion and online inference timestamps are absent. Thus this is a simulated information contract, not qualification of an existing live observer. Hypothetical online correctness/inference overhead needs future qualification if the candidate survives.

Charge100 probe offers, initial25 warmup offers, full acquired calibration and controls. Scheduled100-offer windows take12.5-25seconds at8-4/s; also record the actual99interval body-completion span and boundary slack. Compare the original forecast on the same200-offer suffix, not on its earlier300-offer endpoint. Reconcile the full300 outcomes with earlier reviews separately.

No fresh traffic, threshold/window/endpoint search, new method claim or manuscript gate change. Original artifacts stay intact. These cohorts share one host, chronology and references; all are known development evidence. A survivor requires a separately frozen independent episode and fair-cost confirmation plan before any new experiment.
