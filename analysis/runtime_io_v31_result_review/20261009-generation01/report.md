# Verified V31 prospective timing confirmation

**All frozen confirmation gates pass; completion replay and independent raw-outcome/block calculations agree.**

Sixteen fresh calibration trials precede eighteen validation trials at new steady rates 5/11/19 requests/s (12600 offers). Four calibration cohorts supply 676 paired timing samples. There are no technical retries or scientific domain exits.

| 10 ms method | Mean trial/block MAE pp | Maximum trial error pp |
|---|---:|---:|
| joint_calibration_cdf | 1.844 | 5.055 |
| independent_worker_response_convolution | 7.585 | 10.764 |
| median_worker_plus_response | 8.104 | 13.486 |
| fluid_busy | 32.512 | 37.895 |
| fluid_quadratic | 32.512 | 37.895 |
| periodic_zero_phase_full_budget | 67.488 | 70.667 |
| periodic_uniform_phase_calibrated_delay | 67.340 | 70.519 |

Mean paired periodic-minus-CDF improvement: 65.495 pp; declared 95% six-block t interval [63.925, 67.065] pp (df=5, multiplier 2.571). Every block improves.

All eighteen trials record zero measurement throttled periods. The lowest trial observed queue<=100 us fraction is 99.825% of all offers. All 12600 offers complete successfully; observed 10 ms misses still total 8429. Forty released containers and one unreleased preflight have successful owned cleanup. The campaign takes 113.0 minutes within its fixed bound.

| Profile | Rate requests/s | Observed mean 10 ms miss % | CDF prediction % | CDF MAE pp |
|---|---:|---:|---:|---:|
| A | 5 | 68.611 | 67.160 | 1.891 |
| B | 11 | 68.106 | 67.160 | 1.212 |
| C | 19 | 65.746 | 67.160 | 2.430 |

The CDF classifies all eighteen trials correctly at both 10 and 12 ms. All fail the 5% budget at 10 ms; all have zero observed misses at 12 ms. Those decisions are well separated from 5%, rather than a precision test near the miss-budget boundary. Zero observed misses do not guarantee zero future misses.

| Deadline ms | Paired CDF MAE pp | Independent convolution MAE pp | Periodic+delay MAE pp |
|---|---:|---:|---:|
| 9 | 1.940 | 1.180 | 69.519 |
| 9.5 | 1.738 | 2.811 | 77.478 |
| 10 | 1.844 | 7.585 | 67.340 |
| 10.5 | 3.852 | 4.645 | 24.838 |
| 11 | 0.607 | 0.628 | 2.243 |
| 12 | 0.000 | 0.113 | 0.000 |
| 20 | 0.000 | 0.000 | 0.000 |
| 25 | 0.000 | 0.000 | 0.000 |
| 50 | 0.000 | 0.000 | 0.000 |
| 100 | 0.000 | 0.000 | 0.000 |
| 500 | 0.000 | 0.000 | 0.000 |

The paired CDF has 3.852 pp error at 10.5 ms, above the numerical 3 pp target used only for the primary 10 ms gate. Maximum 10 ms trial error is 5.055 pp. The independent convolution is better at secondary 9 ms; no universal method dominance is established. At 12–25 ms both paired CDF and periodic forecasts have zero error, so those endpoints supply no accuracy discrimination.

Cohort-only 10 ms forecasts range from 57.522% to 69.912%. Leaving each cohort out gives validation MAE 1.974–2.268 pp; this sensitivity is descriptive and never refits the frozen primary result. Hundreds of calibration requests are not hundreds of independent experiment replicates.

| Deadline ms | Misses | Computation certainly after | Computation certainly within, client missed | Clock ambiguous |
|---|---:|---:|---:|---:|
| 10 | 8429 | 4813 | 2264 | 1352 |
| 10.5 | 3070 | 754 | 1594 | 722 |
| 11 | 279 | 12 | 233 | 34 |
| 12 | 0 | 0 | 0 | 0 |

Stage counts retain material clock ambiguity and are descriptive, not causal CPU/runtime/HTTP attribution. The V30 burst failure of the empirical CDF remains separate negative scope evidence. V31 confirms the low-queue 10 ms forecast on this service/host; it does not establish a new estimator, phase mechanism, overload predictor or independent-service transfer.

The next research step is to consolidate this scoped claim and design one independent service or host replication before any new collection. The completed V31 design, sources, binaries, predictions and raw records remain unchanged.
