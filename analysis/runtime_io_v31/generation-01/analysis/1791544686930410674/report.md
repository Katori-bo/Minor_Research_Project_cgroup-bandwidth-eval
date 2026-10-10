# V31 fresh low-queue timing confirmation

**Decision: low_queue_timing_prediction_confirmed**

One service and host in a declared low-queue unthrottled domain. Unknown phase has an assumed uniform prior. Six block t interval assumes approximately independent normal contrasts. Calibration requests are not replicates. No causal phase claim or hard guarantee.

| Model | 10 ms MAE pp | Maximum error pp | SLO decisions matching |
|---|---:|---:|---:|
| joint_calibration_cdf | 1.8444367897809195 | 5.05450015571472 | 18 |
| independent_worker_response_convolution | 7.585324671991891 | 10.764396087905418 | 18 |
| median_worker_plus_response | 8.104120725578213 | 13.486452818436618 | 18 |
| fluid_busy | 32.512404749246855 | 37.89473684210526 | 18 |
| fluid_quadratic | 32.512404749246855 | 37.89473684210526 | 18 |
| periodic_zero_phase_full_budget | 67.48759525075315 | 70.66666666666667 | 0 |
| periodic_uniform_phase_calibrated_delay | 67.3396662566703 | 70.51873767258382 | 0 |

| CDF decision deadline ms | Matching trials |
|---|---:|
| 10 | 18 |
| 12 | 18 |

Primary gates: {"all_trial_slo_decisions_match_10ms": true, "all_trial_slo_decisions_match_12ms": true, "all_trials_inside_scientific_domain": true, "cdf_mean_block_mae_le_3": true, "complete_technically_qualified_trials": true, "every_block_positive": true, "improvement_95_lower_ge_5": true, "some_profile_meets_12ms_slo_every_block": true}
Paired block improvement: {"df": 5, "mean_pp": 65.49522946688938, "model_based_95_interval": [63.925435993108664, 67.0650229406701], "t_multiplier": 2.571}
Scientific domain exits (retained trials): []

Fresh calibration, every per-offer forecast, all eleven deadline diagnostics and failed technical attempts remain in sealed JSON.
No further collection starts automatically. A positive result does not establish novelty, a phase cause, a hard guarantee or transfer to other applications.
