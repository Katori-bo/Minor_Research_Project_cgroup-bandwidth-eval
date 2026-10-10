# V30 fresh short-deadline confirmation

**Decision: short_deadline_prediction_confirmed**

One service and host; fresh held-out traffic patterns. Unknown phase is an assumed uniform prior. Six block t interval assumes approximately independent normal contrasts. No causal phase claim or hard service guarantee.

| Model | 25 ms MAE pp | Maximum error pp | SLO decisions matching |
|---|---:|---:|---:|
| fluid_busy | 73.59903381642512 | 100.0 | 6 |
| fluid_busy_calibrated_delay | 73.59903381642512 | 100.0 | 6 |
| fluid_quadratic | 73.59903381642512 | 100.0 | 6 |
| periodic_zero_phase_full_budget | 0.9017713365539445 | 6.08695652173914 | 18 |
| periodic_uniform_phase | 2.729468599033816 | 13.26086956521739 | 18 |
| periodic_uniform_phase_calibrated_delay | 2.341465854843779 | 12.09686133264728 | 18 |
| discovery_switch | 2.341465854843779 | 12.09686133264728 | 18 |

Primary gates: {"all_trial_slo_decisions_match": true, "complete_qualified_trials": true, "every_block_positive": true, "improvement_95_lower_ge_5": true, "periodic_mean_block_mae_le_3": true, "some_profile_meets_slo_every_block": true}
Paired block improvement: {"df": 5, "mean_pp": 71.25756796158134, "model_based_95_interval": [68.90032913723064, 73.61480678593205], "t_multiplier": 2.571}

Fresh calibration, every per-offer forecast, all nine deadline diagnostics and failed technical attempts remain in sealed JSON.
No further collection starts automatically. A positive result does not establish novelty, a phase cause, a hard guarantee or transfer to other applications.
